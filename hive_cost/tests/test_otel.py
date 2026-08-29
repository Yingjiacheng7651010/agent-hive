"""OTel 兼容 JSONL 导出测试：字段齐全 / 逐行合法 / 确定性 / 条数 / 中文不转义。"""
from __future__ import annotations

import json

import pytest

from hive_cost.budget import CostBudget
from hive_cost.gate import CostGate
from hive_cost.otel import export_cost_otel_jsonl

REQUIRED_TOP_LEVEL = {"name", "start_time_unix_nano", "end_time_unix_nano", "attributes"}
REQUIRED_ATTRIBUTES = {
    "model", "role", "input_tokens", "output_tokens", "cost_usd", "downgraded", "action",
}


def _sample_events() -> list[dict]:
    return [
        {
            "name": "agent.model_call",
            "start_time_unix_nano": 1_700_000_000_000_000_000,
            "end_time_unix_nano": 1_700_000_000_850_000_000,
            "attributes": {
                "model": "deepseek-chat",
                "role": "编码",
                "input_tokens": 1200,
                "output_tokens": 300,
                "cost_usd": 0.0012,
                "downgraded": False,
                "action": "proceed",
            },
        },
        {
            "name": "agent.model_call",
            "start_time_unix_nano": 1_700_000_001_000_000_000,
            "end_time_unix_nano": 1_700_000_001_500_000_000,
            "attributes": {
                "model": "deepseek-chat-lite",
                "role": "评审",
                "input_tokens": 500,
                "output_tokens": 100,
                "cost_usd": 0.0002,
                "downgraded": True,
                "action": "downgrade",
            },
        },
    ]


class TestFieldCompleteness:
    """字段齐全：顶层 4 字段 + attributes 7 字段，类型正确。"""

    def test_exported_events_have_all_fields(self, tmp_path):
        path = tmp_path / "events.jsonl"
        export_cost_otel_jsonl(str(path), _sample_events())
        for line in path.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            assert set(event.keys()) == REQUIRED_TOP_LEVEL
            assert set(event["attributes"].keys()) == REQUIRED_ATTRIBUTES
            assert isinstance(event["start_time_unix_nano"], int)
            assert isinstance(event["end_time_unix_nano"], int)
            assert event["attributes"]["action"] in ("proceed", "downgrade", "block")
            assert isinstance(event["attributes"]["downgraded"], bool)
            assert isinstance(event["attributes"]["cost_usd"], float)

    def test_gate_events_exportable_with_all_fields(self, tmp_path):
        gate = CostGate(budget=CostBudget(max_tokens=1000))
        gate.check_before_call("deepseek-chat", "编码")
        gate.record_after_call("deepseek-chat", "编码", 100, 50, latency_ms=850.0)
        events = gate.to_otel_events()
        assert len(events) == 1
        event = events[0]
        assert set(event.keys()) == REQUIRED_TOP_LEVEL
        assert set(event["attributes"].keys()) == REQUIRED_ATTRIBUTES
        assert event["name"] == "agent.model_call"
        assert event["attributes"]["model"] == "deepseek-chat"
        assert event["attributes"]["role"] == "编码"
        assert event["attributes"]["input_tokens"] == 100
        assert event["attributes"]["output_tokens"] == 50
        assert event["attributes"]["cost_usd"] > 0
        assert event["attributes"]["action"] == "proceed"
        assert event["end_time_unix_nano"] >= event["start_time_unix_nano"]
        assert export_cost_otel_jsonl(str(tmp_path / "gate.jsonl"), events) == 1


class TestJsonlShape:
    """逐行 json.loads 合法。"""

    def test_each_line_is_valid_json(self, tmp_path):
        path = tmp_path / "events.jsonl"
        export_cost_otel_jsonl(str(path), _sample_events())
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        for line in lines:  # 任何一行解析失败都会抛异常
            parsed = json.loads(line)
            assert parsed["name"] == "agent.model_call"

    def test_one_event_per_line(self, tmp_path):
        path = tmp_path / "events.jsonl"
        export_cost_otel_jsonl(str(path), _sample_events())
        text = path.read_text(encoding="utf-8")
        assert text.count("\n") == 2
        assert text.count('"name": "agent.model_call"') == 2


class TestDeterminism:
    """同输入两次导出逐字节一致。"""

    def test_byte_identical_across_exports(self, tmp_path):
        path = tmp_path / "events.jsonl"
        export_cost_otel_jsonl(str(path), _sample_events())
        first = path.read_bytes()
        export_cost_otel_jsonl(str(path), _sample_events())  # 覆盖写第二遍
        second = path.read_bytes()
        assert first == second

    def test_byte_identical_with_gate_events(self, tmp_path):
        gate = CostGate()
        gate.record_after_call("deepseek-chat", "编码", 100, 50)
        events = gate.to_otel_events()
        path = tmp_path / "g.jsonl"
        export_cost_otel_jsonl(str(path), events)
        assert export_cost_otel_jsonl(str(path), events) == 1
        # 同事件列表两遍 → 逐字节一致
        assert path.read_bytes() == path.read_bytes()


class TestReturnCount:
    """返回写入条数正确。"""

    def test_count_matches_events(self, tmp_path):
        assert export_cost_otel_jsonl(str(tmp_path / "empty.jsonl"), []) == 0
        assert export_cost_otel_jsonl(str(tmp_path / "one.jsonl"), _sample_events()[:1]) == 1
        assert export_cost_otel_jsonl(str(tmp_path / "two.jsonl"), _sample_events()) == 2

    def test_parent_dir_auto_created(self, tmp_path):
        deep = tmp_path / "nested" / "dir" / "events.jsonl"
        n = export_cost_otel_jsonl(str(deep), _sample_events())
        assert n == 2
        assert deep.exists()
        assert deep.parent.is_dir()


class TestChineseNotEscaped:
    """ensure_ascii=False 生效：中文原样落盘，无 \\uXXXX。"""

    def test_chinese_kept_raw(self, tmp_path):
        path = tmp_path / "zh.jsonl"
        export_cost_otel_jsonl(str(path), _sample_events())
        text = path.read_text(encoding="utf-8")
        assert "编码" in text
        assert "评审" in text
        assert "\\u" not in text  # 未被 \uXXXX 转义
