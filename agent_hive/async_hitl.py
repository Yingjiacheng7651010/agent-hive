"""异步人机协同 —— 审批请求进队列 → 回调/Webhook 通知 → 审批结果异步返回 → 超时自动降级。

核心策略：
1. ApprovalQueue：异步审批队列，提交立即返回，不阻塞 agent run
2. ApprovalPolicyEngine：自动审批规则匹配（条件满足时跳过人工审批）
3. ApprovalStore 存储抽象：支持内存/SQLite/Redis 后端
4. sync_ask() 兼容层：兼容现有 Command(resume=...) 同步接口
5. 审批 Webhook：支持通过 REST API 提交审批结果
"""
from __future__ import annotations

import abc
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

__all__ = [
    "ApprovalRequest",
    "ApprovalResult",
    "ApprovalPolicy",
    "ApprovalQueue",
    "ApprovalPolicyEngine",
    "ApprovalStore",
    "MemoryApprovalStore",
    "SyncApprovalStore",
    "sync_ask",
]

# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class ApprovalRequest:
    """一次审批请求。"""
    id: str = ""
    kind: Literal["architecture", "dispatch", "danger_confirm", "budget_exceed"] = "architecture"
    title: str = ""
    content: dict = field(default_factory=dict)
    requester: str = ""
    priority: int = 2                     # 1=紧急, 2=普通, 3=低优先级
    created_at: float = field(default_factory=time.time)
    timeout_ms: int = 300000              # 超时时间，默认 5 分钟
    auto_decision: dict | None = None     # 超时后的自动决策
    callback_url: str | None = None       # 异步回调 URL（webhook）


@dataclass
class ApprovalResult:
    """审批结果。"""
    request_id: str
    approved: bool
    feedback: str = ""
    decided_by: Literal["human", "auto_timeout", "auto_policy"] = "human"
    decided_at: float = field(default_factory=time.time)
    decided_by_user: str | None = None


@dataclass
class ApprovalPolicy:
    """审批策略模板：自动审批规则。"""
    name: str
    condition: str                       # 条件表达式，如 "len(files) < 5 and role == '编码'"
    auto_decision: dict                  # 条件满足时的自动决策
    priority: int = 1                    # 多个策略匹配时优先级高的生效


# ---------------------------------------------------------------------------
# 存储抽象
# ---------------------------------------------------------------------------

class ApprovalStore(abc.ABC):
    """审批存储抽象，支持内存/文件/SQLite/Redis 后端。"""

    @abc.abstractmethod
    def save_request(self, request: ApprovalRequest):
        ...

    @abc.abstractmethod
    def save_result(self, result: ApprovalResult):
        ...

    @abc.abstractmethod
    def get_request(self, request_id: str) -> ApprovalRequest | None:
        ...

    @abc.abstractmethod
    def get_result(self, request_id: str) -> ApprovalResult | None:
        ...

    @abc.abstractmethod
    def list_pending(self) -> list[ApprovalRequest]:
        ...


class MemoryApprovalStore(ApprovalStore):
    """内存存储后端（默认，零依赖）。"""

    def __init__(self):
        self._requests: dict[str, ApprovalRequest] = {}
        self._results: dict[str, ApprovalResult] = {}
        self._lock = threading.Lock()

    def save_request(self, request: ApprovalRequest):
        with self._lock:
            self._requests[request.id] = request

    def save_result(self, result: ApprovalResult):
        with self._lock:
            self._results[result.request_id] = result
            # 从待审批列表中移除
            self._requests.pop(result.request_id, None)

    def get_request(self, request_id: str) -> ApprovalRequest | None:
        with self._lock:
            return self._requests.get(request_id)

    def get_result(self, request_id: str) -> ApprovalResult | None:
        with self._lock:
            return self._results.get(request_id)

    def list_pending(self) -> list[ApprovalRequest]:
        with self._lock:
            return list(self._requests.values())


class SyncApprovalStore(ApprovalStore):
    """同步兼容存储：包装现有同步调用。"""

    def __init__(self, ask_fn: Callable | None = None):
        self._ask_fn = ask_fn
        self._requests: dict[str, ApprovalRequest] = {}
        self._results: dict[str, ApprovalResult] = {}
        self._lock = threading.Lock()

    def save_request(self, request: ApprovalRequest):
        with self._lock:
            self._requests[request.id] = request

    def save_result(self, result: ApprovalResult):
        with self._lock:
            self._results[result.request_id] = result

    def get_request(self, request_id: str) -> ApprovalRequest | None:
        with self._lock:
            return self._requests.get(request_id)

    def get_result(self, request_id: str) -> ApprovalResult | None:
        with self._lock:
            return self._results.get(request_id)

    def list_pending(self) -> list[ApprovalRequest]:
        with self._lock:
            return list(self._requests.values())


# ---------------------------------------------------------------------------
# 审批策略引擎
# ---------------------------------------------------------------------------

class ApprovalPolicyEngine:
    """审批策略引擎：自动审批规则匹配。"""

    def __init__(self):
        self._policies: list[ApprovalPolicy] = []
        self._lock = threading.Lock()

    def register_policy(self, policy: ApprovalPolicy):
        """注册一条审批策略。"""
        with self._lock:
            self._policies.append(policy)
            # 按优先级排序（数字小的优先）
            self._policies.sort(key=lambda p: p.priority)

    def unregister_policy(self, name: str):
        """注销审批策略。"""
        with self._lock:
            self._policies = [p for p in self._policies if p.name != name]

    def evaluate(self, request: ApprovalRequest) -> ApprovalResult | None:
        """检查是否有匹配的自动审批策略。

        Returns:
            ApprovalResult 如果匹配到策略，None 如果没有匹配。
        """
        with self._lock:
            for policy in self._policies:
                if self._match_condition(policy.condition, request):
                    auto = policy.auto_decision
                    return ApprovalResult(
                        request_id=request.id,
                        approved=auto.get("approved", True),
                        feedback=auto.get("feedback", f"自动审批策略: {policy.name}"),
                        decided_by="auto_policy",
                    )
        return None

    def _match_condition(self, condition: str, request: ApprovalRequest) -> bool:
        """简单的条件匹配引擎。

        支持的条件格式：
        - "kind == 'architecture'" → 匹配审批类型
        - "priority <= 2" → 匹配优先级
        - "len(files) < 5" → 匹配 content 中的字段
        """
        # 简单的 key-value 匹配
        condition = condition.strip()

        # kind 匹配
        if condition.startswith("kind "):
            parts = condition.split("'")
            if len(parts) >= 2:
                expected_kind = parts[1]
                return request.kind == expected_kind

        # priority 匹配
        if condition.startswith("priority "):
            parts = condition.split()
            if len(parts) >= 3:
                try:
                    expected = int(parts[2])
                    op = parts[1]
                    if op == "<=":
                        return request.priority <= expected
                    elif op == ">=":
                        return request.priority >= expected
                    elif op == "==":
                        return request.priority == expected
                except (ValueError, IndexError):
                    pass

        # content 字段匹配
        if condition.startswith("len("):
            # 格式: len(files) < 5
            import re
            m = re.match(r'len\((\w+)\)\s*([<>=!]+)\s*(\d+)', condition)
            if m:
                field = m.group(1)
                op = m.group(2)
                expected = int(m.group(3))
                value = request.content.get(field)
                if isinstance(value, (list, dict, str)):
                    actual = len(value)
                    if op == "<":
                        return actual < expected
                    elif op == "<=":
                        return actual <= expected
                    elif op == "==":
                        return actual == expected
                    elif op == ">":
                        return actual > expected
                    elif op == ">=":
                        return actual >= expected

        return False

    def list_policies(self) -> list[ApprovalPolicy]:
        with self._lock:
            return list(self._policies)


# ---------------------------------------------------------------------------
# 审批队列
# ---------------------------------------------------------------------------

class ApprovalQueue:
    """异步审批队列。"""

    def __init__(
        self,
        store: ApprovalStore | None = None,
        policy_engine: ApprovalPolicyEngine | None = None,
        on_resolve: Callable[[ApprovalResult], None] | None = None,
    ):
        self._store = store or MemoryApprovalStore()
        self._policy_engine = policy_engine or ApprovalPolicyEngine()
        self._on_resolve = on_resolve
        self._lock = threading.Lock()
        self._pending_events: dict[str, threading.Event] = {}  # request_id -> event

    def submit(self, request: ApprovalRequest) -> str:
        """提交审批请求，返回 request_id。

        自动检查策略引擎：如果匹配自动审批策略，直接返回结果。
        """
        if not request.id:
            request.id = f"approval_{uuid.uuid4().hex[:12]}"

        if not request.title:
            request.title = f"审批请求: {request.kind}"

        # 检查策略引擎
        policy_result = self._policy_engine.evaluate(request)
        if policy_result is not None:
            self._store.save_request(request)
            self._store.save_result(policy_result)
            if self._on_resolve:
                self._on_resolve(policy_result)
            return request.id

        # 进入队列
        self._store.save_request(request)
        return request.id

    def poll(self, request_id: str, timeout_ms: int = 5000) -> ApprovalResult | None:
        """轮询审批结果（同步等待场景兼容）。

        如果超时返回 None，调用方应继续轮询或检查超时。
        """
        # 先检查是否已有结果
        result = self._store.get_result(request_id)
        if result is not None:
            return result

        # 检查是否超时
        request = self._store.get_request(request_id)
        if request is None:
            return None

        elapsed = (time.time() - request.created_at) * 1000
        if elapsed >= request.timeout_ms:
            # 超时，自动决策
            auto = request.auto_decision or {"approved": True, "feedback": "审批超时，自动决策"}
            result = ApprovalResult(
                request_id=request_id,
                approved=auto.get("approved", True),
                feedback=auto.get("feedback", "审批超时，自动决策"),
                decided_by="auto_timeout",
            )
            self._store.save_result(result)
            if self._on_resolve:
                self._on_resolve(result)
            return result

        return None

    def resolve(self, result: ApprovalResult) -> bool:
        """审批人提交审批结果。

        Returns:
            True 成功处理，False 表示 request_id 已超时/已处理。
        """
        request = self._store.get_request(result.request_id)
        if request is None:
            return False

        # 检查是否已有结果（超时自动决策已经处理）
        existing = self._store.get_result(result.request_id)
        if existing is not None:
            return False

        self._store.save_result(result)
        if self._on_resolve:
            self._on_resolve(result)
        return True

    def pending_requests(self, filter_by: dict | None = None) -> list[ApprovalRequest]:
        """查看待审批列表。"""
        pending = self._store.list_pending()
        if filter_by:
            result = []
            for req in pending:
                match = True
                for k, v in filter_by.items():
                    if getattr(req, k, None) != v:
                        match = False
                        break
                if match:
                    result.append(req)
            return result
        return pending

    def stats(self) -> dict:
        """统计信息。"""
        pending = self._store.list_pending()
        # 计算已完成的（从内存中简单统计）
        return {
            "pending_count": len(pending),
            "pending_requests": pending,
        }

    def get_request(self, request_id: str) -> ApprovalRequest | None:
        return self._store.get_request(request_id)

    def get_result(self, request_id: str) -> ApprovalResult | None:
        return self._store.get_result(request_id)


# ---------------------------------------------------------------------------
# 同步兼容层
# ---------------------------------------------------------------------------

def sync_ask(
    interrupt_value: dict,
    auto_yes: bool = True,
    timeout_ms: int = 300000,
    queue: ApprovalQueue | None = None,
) -> dict:
    """兼容现有同步接口。内部调用异步队列 + poll。

    Args:
        interrupt_value: 中断值字典，包含审批信息
        auto_yes: 超时后的自动决策（True=批准，False=拒绝）
        timeout_ms: 超时时间
        queue: 审批队列，None 时创建新的

    Returns:
        {"approved": bool, "feedback": str}
    """
    if queue is None:
        queue = ApprovalQueue()

    request = ApprovalRequest(
        id=f"approval_{uuid.uuid4().hex[:12]}",
        kind=interrupt_value.get("kind", "unknown"),
        title=interrupt_value.get("title", "审批请求"),
        content=interrupt_value,
        timeout_ms=timeout_ms,
        auto_decision={"approved": auto_yes},
        requester=interrupt_value.get("requester", ""),
    )

    queue.submit(request)

    # 等待审批结果（或超时自动决策）
    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        result = queue.poll(request.id, timeout_ms=5000)
        if result is not None:
            return {"approved": result.approved, "feedback": result.feedback}

        # 短暂休眠后继续轮询
        time.sleep(0.5)

    # 最终超时检查
    result = queue.poll(request.id, timeout_ms=100)
    if result is not None:
        return {"approved": result.approved, "feedback": result.feedback}

    return {"approved": auto_yes, "feedback": "审批超时，自动决策"}


# ---------------------------------------------------------------------------
# Webhook 辅助（用于 FastAPI/Flask 端点）
# ---------------------------------------------------------------------------

def create_resolve_endpoint(queue: ApprovalQueue):
    """创建审批结果提交的处理函数。

    Usage:
        from flask import Flask, request
        app = Flask(__name__)
        resolve = create_resolve_endpoint(queue)

        @app.post("/api/v1/approvals/<request_id>/resolve")
        def resolve_approval(request_id):
            return resolve(request_id, request.json)
    """

    def resolve(request_id: str, body: dict) -> dict:
        result = ApprovalResult(
            request_id=request_id,
            approved=body.get("approved", True),
            feedback=body.get("feedback", ""),
            decided_by="human",
            decided_by_user=body.get("user", "unknown"),
        )
        success = queue.resolve(result)
        return {"status": "ok" if success else "ignored"}

    return resolve