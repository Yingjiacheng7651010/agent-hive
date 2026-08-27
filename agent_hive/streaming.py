"""流式输出 —— StreamManager + StreamContext + SSE 传输。

核心策略：
1. StreamManager：管理会话，发布/订阅事件，线程安全
2. StreamContext：上下文管理器，在 agent 执行期间自动发布事件
3. StreamStore 存储抽象：支持内存/文件/Redis 后端
4. SSE 格式输出：`subscribe_sse()` 输出 SSE 格式文本流
5. 事件可回放（replay），用于调试和审计
"""
from __future__ import annotations

import abc
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from queue import Empty, Queue
from typing import Any, Generator, Literal

__all__ = [
    "StreamEvent",
    "StreamSession",
    "StreamManager",
    "StreamContext",
    "StreamStore",
    "MemoryStreamStore",
]

# ---------------------------------------------------------------------------
# 事件类型
# ---------------------------------------------------------------------------

STREAM_EVENT_TYPES = {
    "agent_start",
    "agent_thought",
    "tool_call",
    "tool_result",
    "agent_end",
    "phase_change",
    "error",
    "progress",
    "checkpoint",
}


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class StreamEvent:
    """流式事件：agent 执行过程中的一个可观察时刻。"""
    type: str = "agent_thought"
    timestamp: float = field(default_factory=time.time)
    data: dict = field(default_factory=dict)
    run_id: str = ""
    agent_id: str = ""

    def to_sse(self) -> str:
        """转换为 SSE 格式字符串。"""
        payload = json.dumps({
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp,
            "run_id": self.run_id,
            "agent_id": self.agent_id,
        }, ensure_ascii=False)
        return f"event: {self.type}\ndata: {payload}\n\n"


@dataclass
class StreamSession:
    """一个流式会话：连接多个 StreamEvent 到同一个消费者。"""
    session_id: str
    created_at: float = field(default_factory=time.time)
    closed: bool = False


# ---------------------------------------------------------------------------
# 存储抽象
# ---------------------------------------------------------------------------

class StreamStore(abc.ABC):
    """流式事件存储抽象，支持内存/文件/Redis 后端。"""

    @abc.abstractmethod
    def append(self, session_id: str, event: StreamEvent):
        ...

    @abc.abstractmethod
    def replay(self, session_id: str) -> list[StreamEvent]:
        ...

    @abc.abstractmethod
    def list_sessions(self) -> list[str]:
        ...


class MemoryStreamStore(StreamStore):
    """内存流式事件存储（默认，零依赖）。"""

    def __init__(self):
        self._events: dict[str, list[StreamEvent]] = {}
        self._lock = threading.Lock()

    def append(self, session_id: str, event: StreamEvent):
        with self._lock:
            if session_id not in self._events:
                self._events[session_id] = []
            self._events[session_id].append(event)

    def replay(self, session_id: str) -> list[StreamEvent]:
        with self._lock:
            return list(self._events.get(session_id, []))

    def list_sessions(self) -> list[str]:
        with self._lock:
            return list(self._events.keys())


# ---------------------------------------------------------------------------
# StreamManager
# ---------------------------------------------------------------------------

class StreamManager:
    """流式管理器：生产事件、消费事件、管理会话。"""

    def __init__(self, store: StreamStore | None = None):
        self._store = store or MemoryStreamStore()
        self._sessions: dict[str, StreamSession] = {}
        self._queues: dict[str, list[Queue]] = {}  # session_id -> [subscriber queues]
        self._lock = threading.Lock()

    def create_session(self, session_id: str | None = None) -> str:
        """创建新的流式会话，返回 session_id。"""
        if session_id is None:
            session_id = f"session_{uuid.uuid4().hex[:12]}"
        with self._lock:
            self._sessions[session_id] = StreamSession(session_id=session_id)
            self._queues[session_id] = []
        return session_id

    def close_session(self, session_id: str):
        """关闭会话。"""
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].closed = True
            # 通知所有订阅者
            if session_id in self._queues:
                for q in self._queues[session_id]:
                    q.put(None)  # 发送结束信号

    def publish(self, session_id: str, event: StreamEvent):
        """向会话发布事件。线程安全。"""
        # 存储事件
        self._store.append(session_id, event)

        # 推送给所有订阅者
        with self._lock:
            if session_id in self._queues:
                for q in self._queues[session_id]:
                    try:
                        q.put_nowait(event)
                    except Exception:
                        pass

    def subscribe(
        self,
        session_id: str,
        event_types: list[str] | None = None,
        timeout_ms: int = 300000,
    ) -> Generator[StreamEvent, None, None]:
        """订阅会话的事件流。可指定事件类型过滤。"""
        q: Queue = Queue()
        with self._lock:
            if session_id not in self._queues:
                self._queues[session_id] = []
            self._queues[session_id].append(q)

        try:
            deadline = time.time() + timeout_ms / 1000
            while time.time() < deadline:
                try:
                    event = q.get(timeout=1.0)
                except Empty:
                    continue

                if event is None:
                    break  # 会话关闭

                if event_types is None or event.type in event_types:
                    yield event

            # 超时后返回结束信号
            yield StreamEvent(
                type="checkpoint",
                data={"reason": "timeout", "message": "订阅超时"},
            )
        finally:
            with self._lock:
                if session_id in self._queues:
                    try:
                        self._queues[session_id].remove(q)
                    except ValueError:
                        pass

    def subscribe_sse(
        self,
        session_id: str,
        event_types: list[str] | None = None,
        timeout_ms: int = 300000,
    ) -> Generator[str, None, None]:
        """订阅并返回 SSE 格式的文本流（用于 HTTP 接口）。"""
        for event in self.subscribe(session_id, event_types, timeout_ms):
            yield event.to_sse()

    def get_session(self, session_id: str) -> StreamSession | None:
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(self) -> list[StreamSession]:
        with self._lock:
            return list(self._sessions.values())

    def replay(self, session_id: str) -> list[StreamEvent]:
        """回放会话的事件历史。"""
        return self._store.replay(session_id)


# ---------------------------------------------------------------------------
# StreamContext
# ---------------------------------------------------------------------------

class StreamContext:
    """上下文管理器：在 agent 执行期间自动发布事件。

    使用方式：
        with StreamContext(session_id, manager) as ctx:
            ctx.thought("开始分析需求...")
            ctx.tool_call("read_file", {"path": "main.py"})
            ctx.progress(1, 3, "编码完成")
    """

    def __init__(self, session_id: str, manager: StreamManager,
                 run_id: str = "", agent_id: str = ""):
        self.session_id = session_id
        self.manager = manager
        self.run_id = run_id
        self.agent_id = agent_id

    def __enter__(self) -> "StreamContext":
        self.manager.publish(self.session_id, StreamEvent(
            type="agent_start", run_id=self.run_id, agent_id=self.agent_id,
            data={"agent_id": self.agent_id, "run_id": self.run_id},
        ))
        return self

    def __exit__(self, *args):
        self.manager.publish(self.session_id, StreamEvent(
            type="agent_end", run_id=self.run_id, agent_id=self.agent_id,
            data={"reason": "completed" if not any(args) else str(args[1]) if args[1] else "completed"},
        ))

    def _publish(self, event_type: str, data: dict):
        self.manager.publish(self.session_id, StreamEvent(
            type=event_type, run_id=self.run_id, agent_id=self.agent_id, data=data,
        ))

    def thought(self, text: str):
        """发布思考片段。"""
        self._publish("agent_thought", {"text": text})

    def tool_call(self, tool_name: str, arguments: dict):
        """发布工具调用事件。"""
        self._publish("tool_call", {"tool": tool_name, "arguments": arguments})

    def tool_result(self, tool_name: str, result: str):
        """发布工具返回事件。"""
        self._publish("tool_result", {"tool": tool_name, "result": result[:500]})

    def progress(self, current: int, total: int, message: str = ""):
        """发布进度事件。"""
        self._publish("progress", {"current": current, "total": total, "message": message})

    def phase(self, phase: str):
        """发布阶段变更事件。"""
        self._publish("phase_change", {"phase": phase})

    def error(self, error: str):
        """发布错误事件。"""
        self._publish("error", {"error": error})