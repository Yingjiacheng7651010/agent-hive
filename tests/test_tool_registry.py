"""Tests for card-tool-registry: ToolRegistry, ToolCallTracker, MonitoredToolWrapper."""
from __future__ import annotations

import time

import pytest

from agent_hive.tool_registry import (
    MonitoredToolWrapper,
    ToolCallRecord,
    ToolCallTracker,
    ToolParameter,
    ToolRegistry,
    ToolSpec,
    tool_to_spec,
)


class TestToolSpec:
    """ToolSpec 工具定义测试。"""

    def test_create_spec(self):
        spec = ToolSpec(
            name="read_file",
            description="读取文件内容",
            version="1.0.0",
            parameters=[
                ToolParameter(name="path", type="string", description="文件路径"),
            ],
            categories=["file", "read", "core"],
            danger_level="safe",
        )
        assert spec.name == "read_file"
        assert spec.version == "1.0.0"
        assert len(spec.parameters) == 1
        assert spec.parameters[0].name == "path"

    def test_to_dict(self):
        spec = ToolSpec(name="test", description="测试工具")
        d = spec.to_dict()
        assert d["name"] == "test"
        assert d["description"] == "测试工具"


class TestToolRegistry:
    """ToolRegistry 工具注册表测试。"""

    def test_register_and_get(self):
        registry = ToolRegistry()
        spec = ToolSpec(name="read_file", version="1.0.0", description="读取文件")
        impl = lambda path: "content"
        assert registry.register(spec, impl) is True
        result = registry.get("read_file")
        assert result is not None
        assert result[0].name == "read_file"
        assert result[0].version == "1.0.0"

    def test_register_version_conflict(self):
        registry = ToolRegistry()
        spec1 = ToolSpec(name="read_file", version="1.0.0")
        spec2 = ToolSpec(name="read_file", version="1.0.0")  # 同版本号
        registry.register(spec1, lambda: None)
        assert registry.register(spec2, lambda: None) is False  # 拒绝

    def test_get_latest_version(self):
        registry = ToolRegistry()
        registry.register(ToolSpec(name="tool", version="1.0.0"), lambda: None)
        registry.register(ToolSpec(name="tool", version="2.0.0"), lambda: None)
        result = registry.get("tool")
        assert result is not None
        assert result[0].version == "2.0.0"

    def test_get_specific_version(self):
        registry = ToolRegistry()
        registry.register(ToolSpec(name="tool", version="1.0.0"), lambda: None)
        registry.register(ToolSpec(name="tool", version="2.0.0"), lambda: None)
        result = registry.get("tool", "1.0.0")
        assert result is not None
        assert result[0].version == "1.0.0"

    def test_unregister_all_versions(self):
        registry = ToolRegistry()
        registry.register(ToolSpec(name="tool", version="1.0.0"), lambda: None)
        registry.register(ToolSpec(name="tool", version="2.0.0"), lambda: None)
        assert registry.unregister("tool") is True
        assert registry.get("tool") is None

    def test_unregister_specific_version(self):
        registry = ToolRegistry()
        registry.register(ToolSpec(name="tool", version="1.0.0"), lambda: None)
        registry.register(ToolSpec(name="tool", version="2.0.0"), lambda: None)
        assert registry.unregister("tool", "1.0.0") is True
        result = registry.get("tool")
        assert result is not None
        assert result[0].version == "2.0.0"

    def test_list_all(self):
        registry = ToolRegistry()
        registry.register(ToolSpec(name="read_file", categories=["file"]), lambda: None)
        registry.register(ToolSpec(name="write_file", categories=["file"]), lambda: None)
        registry.register(ToolSpec(name="search", categories=["web"]), lambda: None)
        specs = registry.list()
        assert len(specs) == 3

    def test_list_filtered(self):
        registry = ToolRegistry()
        registry.register(ToolSpec(name="read_file", categories=["file", "read"]), lambda: None)
        registry.register(ToolSpec(name="write_file", categories=["file", "write"]), lambda: None)
        registry.register(ToolSpec(name="search", categories=["web"]), lambda: None)
        specs = registry.list(filter_by={"category": "file"})
        assert len(specs) == 2

    def test_get_for_role(self):
        registry = ToolRegistry()
        registry.register(ToolSpec(
            name="read_file", required_roles=["编码", "测试"],
        ), lambda: None)
        registry.register(ToolSpec(
            name="admin_tool", required_roles=["管理员"],
        ), lambda: None)
        registry.register(ToolSpec(
            name="public_tool", required_roles=[],
        ), lambda: None)

        coder_tools = registry.get_for_role("编码")
        assert len(coder_tools) == 2  # read_file + public_tool

        admin_tools = registry.get_for_role("管理员")
        assert len(admin_tools) == 2  # admin_tool + public_tool

        tester_tools = registry.get_for_role("测试")
        assert len(tester_tools) == 2  # read_file + public_tool

    def test_has_tool(self):
        registry = ToolRegistry()
        assert registry.has_tool("nonexistent") is False
        registry.register(ToolSpec(name="test"), lambda: None)
        assert registry.has_tool("test") is True

    def test_clear(self):
        registry = ToolRegistry()
        registry.register(ToolSpec(name="tool1"), lambda: None)
        registry.register(ToolSpec(name="tool2"), lambda: None)
        registry.clear()
        assert len(registry.list()) == 0


class TestToolCallTracker:
    """ToolCallTracker 工具调用追踪器测试。"""

    def test_record_and_stats(self):
        tracker = ToolCallTracker()
        tracker.record(ToolCallRecord(
            tool_name="read_file", tool_version="1.0.0",
            arguments={"path": "test.txt"}, result="content",
            success=True, latency_ms=10.0,
        ))
        stats = tracker.stats("read_file")
        assert stats["total_calls"] == 1
        assert stats["success_rate"] == 1.0

    def test_stats_with_failures(self):
        tracker = ToolCallTracker()
        tracker.record(ToolCallRecord(tool_name="tool", tool_version="1.0.0", arguments={}, success=True, latency_ms=5.0))
        tracker.record(ToolCallRecord(tool_name="tool", tool_version="1.0.0", arguments={}, success=False, latency_ms=10.0, error="错误"))
        tracker.record(ToolCallRecord(tool_name="tool", tool_version="1.0.0", arguments={}, success=True, latency_ms=15.0))
        stats = tracker.stats("tool")
        assert stats["total_calls"] == 3
        assert stats["success_rate"] == pytest.approx(2/3)
        assert stats["total_failures"] == 1

    def test_top_failures(self):
        tracker = ToolCallTracker()
        for i in range(5):
            tracker.record(ToolCallRecord(
                tool_name=f"tool_{i}", tool_version="1.0.0",
                arguments={}, success=False, error=f"error_{i}",
            ))
        failures = tracker.top_failures(n=3)
        assert len(failures) == 3

    def test_stats_since_time(self):
        tracker = ToolCallTracker()
        now = time.time()
        tracker.record(ToolCallRecord(tool_name="tool", tool_version="1.0.0", arguments={}, success=True, latency_ms=5.0, timestamp=now - 100))
        tracker.record(ToolCallRecord(tool_name="tool", tool_version="1.0.0", arguments={}, success=True, latency_ms=5.0, timestamp=now))
        stats = tracker.stats("tool", since=now - 50)
        assert stats["total_calls"] == 1

    def test_clear(self):
        tracker = ToolCallTracker()
        tracker.record(ToolCallRecord(tool_name="tool", tool_version="1.0.0", arguments={}))
        assert tracker.records_count() == 1
        tracker.clear()
        assert tracker.records_count() == 0


class TestMonitoredToolWrapper:
    """MonitoredToolWrapper 监控包装器测试。"""

    def test_successful_call(self):
        tracker = ToolCallTracker()
        spec = ToolSpec(name="add", version="1.0.0")
        impl = lambda a, b: a + b
        wrapper = MonitoredToolWrapper(spec, impl, tracker)
        result = wrapper(a=1, b=2)
        assert result == 3
        assert tracker.records_count() == 1
        record = tracker.top_failures(1)
        # 成功调用不在 top_failures 中
        stats = tracker.stats("add")
        assert stats["total_calls"] == 1
        assert stats["success_rate"] == 1.0

    def test_failed_call(self):
        tracker = ToolCallTracker()
        spec = ToolSpec(name="fail_tool", version="1.0.0")

        def impl():
            raise ValueError("测试错误")

        wrapper = MonitoredToolWrapper(spec, impl, tracker)
        with pytest.raises(ValueError):
            wrapper()
        stats = tracker.stats("fail_tool")
        assert stats["total_calls"] == 1
        assert stats["success_rate"] == 0.0
        assert stats["total_failures"] == 1


class TestToolToSpec:
    """tool_to_spec 兼容包装器测试。"""

    def test_from_function(self):
        def read_file(path: str) -> str:
            """读取文件内容。"""
            return "content"

        spec = tool_to_spec(read_file)
        assert spec.name == "read_file"
        assert spec.description == "读取文件内容。"
        assert spec.version == "0.9.0"
        assert "legacy" in spec.categories
        assert len(spec.parameters) == 1
        assert spec.parameters[0].name == "path"
        assert spec.parameters[0].type == "string"

    def test_from_function_with_int_param(self):
        def calculate(x: int, y: int) -> int:
            return x + y

        spec = tool_to_spec(calculate)
        assert len(spec.parameters) == 2
        # 参数类型基于 annotation 推断
        assert spec.parameters[0].type in ("string", "integer")
        # 两个参数类型相同
        assert spec.parameters[0].type == spec.parameters[1].type