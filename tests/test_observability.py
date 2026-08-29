"""OTel 兼容 JSONL 导出测试（agent_hive.observability.export_run_otel_jsonl）。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from agent_hive.observability import export_run_otel_jsonl

COST = {"model_calls": 5, "input_tokens": 1200, "output_tokens": 340}
EVENT = {
    "type": "agent_start",
    "timestamp": 1725000000.5,
    "data": {"agent_id": "编码", "run_id": "run_20260829_abc123"},
    "run_id": "run_20260829_abc123",
    "agent_id": "编码",
}


def _make_run(tmp_path, cost=None, events=None, name="run_20260829_abc123") -> Path:
    run = tmp_path / name
    run.mkdir()
    if cost is not None:
        (run / "cost.json").write_text(json.dumps(cost, ensure_ascii=False), encoding="utf-8")
    if events is not None:
        text = "".join(
            json.dumps(e, ensure_ascii=False) + "\n" for e in events
        )
        (run / "stream_events.jsonl").write_text(text, encoding="utf-8")
    return run


def _records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


class TestCostOnly:
    def test_one_record_with_correct_fields(self, tmp_path):
        run = _make_run(tmp_path, cost=COST)
        out = tmp_path / "otel" / "nested" / "out.jsonl"  # 父目录需自动创建
        n = export_run_otel_jsonl(run, out)
        assert n == 1
        assert out.parent.is_dir()
        rec = _records(out)[0]
        assert rec["name"] == "agent.event"
        assert rec["attributes"]["kind"] == "cost"
        assert rec["attributes"]["model_calls"] == 5
        assert rec["attributes"]["input_tokens"] == 1200
        assert rec["attributes"]["output_tokens"] == 340
        assert rec["start_time_unix_nano"] == 0
        assert rec["end_time_unix_nano"] == 0
        assert rec["span_id"] == "0000000000000001"


class TestEventsOnly:
    def test_n_records_with_event_types(self, tmp_path):
        events = [
            dict(EVENT, type="agent_start"),
            dict(EVENT, type="tool_call"),
            dict(EVENT, type="agent_end"),
        ]
        run = _make_run(tmp_path, events=events)
        out = tmp_path / "out.jsonl"
        n = export_run_otel_jsonl(run, out)
        assert n == 3
        recs = _records(out)
        assert [r["attributes"]["kind"] for r in recs] == ["stream_event"] * 3
        assert [r["attributes"]["event_type"] for r in recs] == [
            "agent_start", "tool_call", "agent_end",
        ]
        assert [r["span_id"] for r in recs] == [
            "0000000000000001", "0000000000000002", "0000000000000003",
        ]
        # 时间戳：秒 → 纳秒
        assert recs[0]["start_time_unix_nano"] == int(1725000000.5 * 1_000_000_000)
        assert recs[0]["end_time_unix_nano"] == recs[0]["start_time_unix_nano"]
        assert recs[0]["attributes"]["agent_id"] == "编码"
        assert '"编码"' in out.read_text(encoding="utf-8")  # ensure_ascii=False 生效


class TestBoth:
    def test_cost_plus_events(self, tmp_path):
        events = [dict(EVENT, type="agent_start"), dict(EVENT, type="agent_end")]
        run = _make_run(tmp_path, cost=COST, events=events)
        out = tmp_path / "out.jsonl"
        assert export_run_otel_jsonl(run, out) == 3  # 1 + N
        recs = _records(out)
        assert [r["attributes"]["kind"] for r in recs] == [
            "cost", "stream_event", "stream_event",
        ]
        assert recs[1]["span_id"] == "0000000000000002"  # 序号贯穿两种事件


class TestEmpty:
    def test_empty_dir_zero_records_no_exception(self, tmp_path):
        run = tmp_path / "empty_run"
        run.mkdir()
        out = tmp_path / "nested" / "dir" / "out.jsonl"
        n = export_run_otel_jsonl(run, out)
        assert n == 0
        assert out.exists()  # 空 JSONL 文件仍创建
        assert out.read_text(encoding="utf-8") == ""
        assert out.parent.is_dir()  # 父目录自动创建


class TestDeterminism:
    def test_two_exports_byte_identical(self, tmp_path):
        events = [EVENT, dict(EVENT, type="tool_call")]
        run = _make_run(tmp_path, cost=COST, events=events)
        out = tmp_path / "out.jsonl"
        export_run_otel_jsonl(run, out)
        first = out.read_bytes()
        export_run_otel_jsonl(run, out)  # 覆盖写第二遍
        second = out.read_bytes()
        assert first == second


class TestTraceId:
    def test_trace_id_stable_from_run_id(self, tmp_path):
        run = _make_run(tmp_path, cost=COST)
        out = tmp_path / "out.jsonl"
        export_run_otel_jsonl(run, out)
        expected = hashlib.sha256(run.name.encode("utf-8")).hexdigest()[:32]
        rec = _records(out)[0]
        assert rec["trace_id"] == expected
        assert len(rec["trace_id"]) == 32
        # 再次导出稳定
        out2 = tmp_path / "out2.jsonl"
        export_run_otel_jsonl(run, out2)
        assert _records(out2)[0]["trace_id"] == expected
        # 不同 run_id → 不同 trace_id
        run2 = _make_run(tmp_path, cost=COST, name="other_run")
        out3 = tmp_path / "out3.jsonl"
        export_run_otel_jsonl(run2, out3)
        assert _records(out3)[0]["trace_id"] != expected


class TestTruncation:
    def test_data_truncated_to_500(self, tmp_path):
        big_data = {"x": "y" * 600}
        run = _make_run(tmp_path, events=[dict(EVENT, type="agent_thought", data=big_data)])
        out = tmp_path / "out.jsonl"
        export_run_otel_jsonl(run, out)
        data = _records(out)[0]["attributes"]["data"]
        assert data.startswith("{'x': 'yyy")
        assert data.endswith("…")
        assert len(data) == 501  # 500 字符 + 省略号


class TestMalformedTolerance:
    def test_bad_cost_json_skipped(self, tmp_path):
        run = tmp_path / "bad_cost"
        run.mkdir()
        (run / "cost.json").write_text("{ broken", encoding="utf-8")
        out = tmp_path / "out.jsonl"
        assert export_run_otel_jsonl(run, out) == 0

    def test_non_dict_cost_skipped(self, tmp_path):
        run = tmp_path / "bad_cost2"
        run.mkdir()
        (run / "cost.json").write_text("[1, 2]", encoding="utf-8")
        out = tmp_path / "out.jsonl"
        assert export_run_otel_jsonl(run, out) == 0

    def test_malformed_event_line_skipped(self, tmp_path):
        run = tmp_path / "bad_events"
        run.mkdir()
        (run / "stream_events.jsonl").write_text(
            '{"type":"agent_start","timestamp":1,"data":{},"agent_id":"a"}\nnot json\n',
            encoding="utf-8",
        )
        out = tmp_path / "out.jsonl"
        assert export_run_otel_jsonl(run, out) == 1
        rec = _records(out)[0]
        assert rec["attributes"]["event_type"] == "agent_start"


def test_each_line_is_valid_json(tmp_path):
    events = [EVENT, dict(EVENT, type="tool_call", data={"cmd": "ls"})]
    run = _make_run(tmp_path, cost=COST, events=events)
    out = tmp_path / "out.jsonl"
    export_run_otel_jsonl(run, out)
    for line in out.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)  # 任何一行非法都会抛异常
        assert rec["name"] == "agent.event"
        assert set(rec) == {"name", "trace_id", "span_id",
                            "start_time_unix_nano", "end_time_unix_nano", "attributes"}
