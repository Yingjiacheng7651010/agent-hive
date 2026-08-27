"""Tests for card-streaming: StreamManager, StreamContext, SSE format."""
from __future__ import annotations

import json
import time

import pytest

from agent_hive.streaming import (
    MemoryStreamStore,
    StreamContext,
    StreamEvent,
    StreamManager,
    StreamSession,
)


class TestStreamEvent:
    """StreamEvent 事件测试。"""

    def test_create_event(self):
        event = StreamEvent(
            type="agent_thought",
            data={"text": "开始分析需求..."},
            run_id="run_001",
            agent_id="chief",
        )
        assert event.type == "agent_thought"
        assert event.data["text"] == "开始分析需求..."

    def test_to_sse_format(self):
        event = StreamEvent(
            type="agent_thought",
            data={"text": "思考中..."},
            timestamp=1234567890.0,
        )
        sse = event.to_sse()
        assert sse.startswith("event: agent_thought")
        assert "data:" in sse
        # SSE 格式：每行以 \n 结尾，空行分隔事件
        assert sse.endswith("\n\n")


class TestMemoryStreamStore:
    """MemoryStreamStore 存储测试。"""

    def test_append_and_replay(self):
        store = MemoryStreamStore()
        event = StreamEvent(type="agent_thought", data={"text": "test"})
        store.append("session_1", event)
        events = store.replay("session_1")
        assert len(events) == 1
        assert events[0].type == "agent_thought"

    def test_replay_empty(self):
        store = MemoryStreamStore()
        assert store.replay("nonexistent") == []

    def test_list_sessions(self):
        store = MemoryStreamStore()
        store.append("session_a", StreamEvent(type="agent_start"))
        store.append("session_b", StreamEvent(type="agent_start"))
        sessions = store.list_sessions()
        assert len(sessions) == 2


class TestStreamManager:
    """StreamManager 流式管理器测试。"""

    def test_create_session(self):
        manager = StreamManager()
        session_id = manager.create_session()
        assert session_id.startswith("session_")
        session = manager.get_session(session_id)
        assert session is not None
        assert session.closed is False

    def test_create_session_with_id(self):
        manager = StreamManager()
        sid = manager.create_session("my_session")
        assert sid == "my_session"

    def test_close_session(self):
        manager = StreamManager()
        sid = manager.create_session()
        manager.close_session(sid)
        session = manager.get_session(sid)
        assert session is not None
        assert session.closed is True

    def test_publish_and_subscribe(self):
        manager = StreamManager()
        sid = manager.create_session()

        collected = []

        import threading
        def subscribe():
            for event in manager.subscribe(sid, timeout_ms=1000):
                collected.append(event)
                if event.type == "agent_end":
                    break

        t = threading.Thread(target=subscribe)
        t.start()
        time.sleep(0.1)

        # 订阅后发布事件
        event = StreamEvent(type="agent_thought", data={"text": "思考中..."})
        manager.publish(sid, event)
        time.sleep(0.1)
        manager.publish(sid, StreamEvent(type="agent_end", data={"reason": "done"}))
        t.join(timeout=2)

        assert len(collected) >= 1
        assert collected[0].type == "agent_thought"

    def test_publish_during_subscription(self):
        manager = StreamManager()
        sid = manager.create_session()

        collected = []

        def subscribe():
            for event in manager.subscribe(sid, timeout_ms=500):
                collected.append(event)
                if event.type == "agent_end":
                    break

        import threading
        t = threading.Thread(target=subscribe)
        t.start()

        time.sleep(0.1)
        manager.publish(sid, StreamEvent(type="agent_thought", data={"text": "step 1"}))
        time.sleep(0.1)
        manager.publish(sid, StreamEvent(type="agent_thought", data={"text": "step 2"}))
        time.sleep(0.1)
        manager.publish(sid, StreamEvent(type="agent_end", data={"reason": "done"}))
        t.join(timeout=2)

        assert len(collected) >= 2

    def test_subscribe_filtered(self):
        manager = StreamManager()
        sid = manager.create_session()

        collected = []

        import threading
        def subscribe():
            for event in manager.subscribe(sid, event_types=["agent_thought"], timeout_ms=1000):
                collected.append(event)
                if event.type == "agent_end":
                    break

        t = threading.Thread(target=subscribe)
        t.start()
        time.sleep(0.1)

        # 订阅后发布事件
        manager.publish(sid, StreamEvent(type="agent_thought", data={"text": "t1"}))
        manager.publish(sid, StreamEvent(type="tool_call", data={"tool": "read"}))
        manager.publish(sid, StreamEvent(type="agent_thought", data={"text": "t2"}))
        manager.publish(sid, StreamEvent(type="agent_end", data={"reason": "done"}))
        t.join(timeout=2)

        for e in collected:
            if e.type != "checkpoint":
                assert e.type == "agent_thought"

    def test_subscribe_sse(self):
        manager = StreamManager()
        sid = manager.create_session()

        manager.publish(sid, StreamEvent(
            type="agent_thought", data={"text": "思考中..."},
        ))

        sse_messages = list(manager.subscribe_sse(sid, timeout_ms=100))
        assert len(sse_messages) >= 1
        # SSE 格式验证
        for msg in sse_messages:
            if msg.startswith("event: "):
                assert "\ndata: " in msg

    def test_list_sessions(self):
        manager = StreamManager()
        manager.create_session("s1")
        manager.create_session("s2")
        sessions = manager.list_sessions()
        assert len(sessions) == 2

    def test_replay(self):
        manager = StreamManager()
        sid = manager.create_session()
        manager.publish(sid, StreamEvent(type="agent_start", data={"agent": "chief"}))
        manager.publish(sid, StreamEvent(type="agent_thought", data={"text": "analysis"}))
        manager.publish(sid, StreamEvent(type="agent_end", data={"reason": "done"}))

        events = manager.replay(sid)
        assert len(events) == 3
        assert events[0].type == "agent_start"
        assert events[1].type == "agent_thought"
        assert events[2].type == "agent_end"

    def test_multiple_subscribers(self):
        """多个消费者可同时订阅同一会话。"""
        manager = StreamManager()
        sid = manager.create_session()
        collected1 = []
        collected2 = []

        import threading

        def sub1():
            for e in manager.subscribe(sid, timeout_ms=300):
                collected1.append(e)
                if e.type == "agent_end":
                    break

        def sub2():
            for e in manager.subscribe(sid, timeout_ms=300):
                collected2.append(e)
                if e.type == "agent_end":
                    break

        t1 = threading.Thread(target=sub1)
        t2 = threading.Thread(target=sub2)
        t1.start()
        t2.start()

        time.sleep(0.1)
        manager.publish(sid, StreamEvent(type="agent_thought", data={"text": "test"}))
        time.sleep(0.1)
        manager.publish(sid, StreamEvent(type="agent_end", data={"reason": "done"}))
        t1.join(timeout=2)
        t2.join(timeout=2)

        assert len(collected1) >= 1
        assert len(collected2) >= 1


class TestStreamContext:
    """StreamContext 上下文管理器测试。"""

    def test_context_manager(self):
        manager = StreamManager()
        sid = manager.create_session()

        with StreamContext(sid, manager, run_id="run_001", agent_id="chief") as ctx:
            ctx.thought("开始分析需求...")
            ctx.tool_call("read_file", {"path": "main.py"})
            ctx.tool_result("read_file", "file content")
            ctx.progress(1, 3, "完成第一步")
            ctx.phase("编码阶段")
            ctx.error("临时错误，可恢复")

        events = manager.replay(sid)
        assert len(events) >= 6  # agent_start + 5 个事件 + agent_end

        # 检查事件类型
        types = [e.type for e in events]
        assert "agent_start" in types
        assert "agent_thought" in types
        assert "tool_call" in types
        assert "tool_result" in types
        assert "progress" in types
        assert "phase_change" in types
        assert "error" in types
        assert "agent_end" in types

    def test_context_agent_start_end(self):
        """进入时自动发布 agent_start，退出时发布 agent_end。"""
        manager = StreamManager()
        sid = manager.create_session()

        with StreamContext(sid, manager, run_id="run_001"):
            pass

        events = manager.replay(sid)
        assert len(events) == 2
        assert events[0].type == "agent_start"
        assert events[1].type == "agent_end"

    def test_tool_result_truncated(self):
        """tool_result 结果截断到 500 字符。"""
        manager = StreamManager()
        sid = manager.create_session()

        with StreamContext(sid, manager) as ctx:
            ctx.tool_result("test", "A" * 1000)

        events = manager.replay(sid)
        tool_result_event = [e for e in events if e.type == "tool_result"][0]
        assert len(tool_result_event.data["result"]) == 500

    def test_backward_compatibility(self):
        """不开启流式时，现有代码完全不受影响。"""
        manager = StreamManager()
        sid = manager.create_session()
        # 不创建 StreamContext，直接使用 manager
        sid2 = manager.create_session()
        assert sid != sid2
        assert manager.get_session(sid) is not None
        assert manager.get_session(sid2) is not None