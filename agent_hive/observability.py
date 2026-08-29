"""运行产物 → OTel 兼容 JSONL 导出（可观测性工件，可被 Langfuse/LangSmith 等消费）。

输入（均为可选）：
- ``<run_dir>/cost.json``：run 结束时的用量快照（``chief.TRACKER.snapshot()`` 产物，
  字段 ``model_calls`` / ``input_tokens`` / ``output_tokens``）；
- ``<run_dir>/stream_events.jsonl``：流式事件日志（每行一个 ``StreamEvent`` 的 JSON
  形态，字段 ``type`` / ``timestamp`` / ``data`` / ``run_id`` / ``agent_id``，
  与 ``streaming.StreamEvent.to_sse()`` 的 payload 同构；目前运行时不落盘，本函数
  定义该约定供写入方对齐）。

输出：OTel 兼容 JSONL（每条记录一行 ``json.dumps(ensure_ascii=False)``，UTF-8）：
``{"name": "agent.event", "trace_id": str, "span_id": str,
  "start_time_unix_nano": int, "end_time_unix_nano": int, "attributes": {...}}``

确定性（同输入同输出）：
- ``trace_id`` = ``sha256(run_id)[:32]``（run_id 取 run_dir.name）；
- ``span_id`` = 输出序号 16 位零填充 hex（1 起）；
- cost 事件无墙钟信息，时间戳固定 0（确定性优先，消费方可按落盘时间覆写）；
  stream 事件使用其自带 ``timestamp``（秒 → 纳秒）；
- cost 事件 attributes = ``{"kind": "cost", "model_calls", "input_tokens", "output_tokens"}``；
  stream 事件 attributes = ``{"kind": "stream_event", "event_type", "agent_id",
  "data"（str 化，截断 500 字符）}``。

容错：cost.json 缺失/非法 JSON/非对象 → 跳过；stream_events.jsonl 缺失/损坏行 → 跳过；
无任何有效记录时仍创建空 JSONL 文件并返回 0，不抛异常。父目录自动创建。

边界：本模块只做**落盘工件导出**——不做 OTLP 网络上报、不引入第三方 SDK、不做面板。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

__all__ = ["export_run_otel_jsonl"]

_COST_FILE = "cost.json"
_EVENTS_FILE = "stream_events.jsonl"
_DATA_TRUNCATE_LIMIT = 500

_EVENT_NAME = "agent.event"


def _trace_id(run_id: str) -> str:
    """trace_id：sha256(run_id) 前 32 位 hex（与 run_id 一一对应，稳定可复现）。"""
    return hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:32]


def _span_id(seq: int) -> str:
    """span_id：序号 16 位零填充 hex（如 1 → 0000000000000001）。"""
    return f"{seq:016x}"


def _truncate(text: str, limit: int = _DATA_TRUNCATE_LIMIT) -> str:
    return text if len(text) <= limit else text[:limit] + "…"


def _as_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _as_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _load_cost_record(run_dir: Path, trace_id: str, seq: int) -> dict | None:
    """读取 cost.json（可选）；缺失/非法 → None。"""
    cost_path = run_dir / _COST_FILE
    if not cost_path.is_file():
        return None
    try:
        cost = json.loads(cost_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(cost, dict):
        return None
    return {
        "name": _EVENT_NAME,
        "trace_id": trace_id,
        "span_id": _span_id(seq),
        "start_time_unix_nano": 0,  # cost.json 无墙钟信息，确定性取 0
        "end_time_unix_nano": 0,
        "attributes": {
            "kind": "cost",
            "model_calls": _as_int(cost.get("model_calls", 0)),
            "input_tokens": _as_int(cost.get("input_tokens", 0)),
            "output_tokens": _as_int(cost.get("output_tokens", 0)),
        },
    }


def _load_stream_records(run_dir: Path, trace_id: str, seq: int) -> list[dict]:
    """读取 stream_events.jsonl（可选）；损坏行跳过，保持文件行序。"""
    events_path = run_dir / _EVENTS_FILE
    if not events_path.is_file():
        return []
    try:
        lines = events_path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return []
    records: list[dict] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue  # 容错：损坏行跳过
        if not isinstance(event, dict):
            continue
        ts_ns = int(_as_float(event.get("timestamp", 0.0)) * 1_000_000_000)
        seq += 1
        records.append({
            "name": _EVENT_NAME,
            "trace_id": trace_id,
            "span_id": _span_id(seq),
            "start_time_unix_nano": ts_ns,
            "end_time_unix_nano": ts_ns,
            "attributes": {
                "kind": "stream_event",
                "event_type": str(event.get("type", "") or ""),
                "agent_id": str(event.get("agent_id", "") or ""),
                "data": _truncate(str(event.get("data", "") or "")),
            },
        })
    return records


def export_run_otel_jsonl(run_dir, out_path) -> int:
    """导出运行产物为 OTel 兼容 JSONL，返回写入条数（0 条时仍创建空文件，不抛异常）。

    Args:
        run_dir: 运行产物目录（取 ``run_dir.name`` 作为 run_id 派生 trace_id）。
        out_path: 输出 JSONL 路径；父目录不存在时自动创建。
    """
    run_dir = Path(run_dir)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    run_id = run_dir.name
    trace_id = _trace_id(run_id)

    records: list[dict] = []
    cost_record = _load_cost_record(run_dir, trace_id, seq=1)
    if cost_record is not None:
        records.append(cost_record)
    records.extend(_load_stream_records(run_dir, trace_id, seq=len(records)))

    with out.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return len(records)
