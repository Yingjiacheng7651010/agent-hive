"""Tests for card-async-hitl: ApprovalQueue, ApprovalPolicyEngine, sync_ask."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from agent_hive.async_hitl import (
    ApprovalPolicy,
    ApprovalPolicyEngine,
    ApprovalQueue,
    ApprovalRequest,
    ApprovalResult,
    MemoryApprovalStore,
    SyncApprovalStore,
    sync_ask,
)


class TestMemoryApprovalStore:
    """MemoryApprovalStore 存储测试。"""

    def test_save_and_get_request(self):
        store = MemoryApprovalStore()
        req = ApprovalRequest(id="req_1", kind="architecture", title="审批架构方案")
        store.save_request(req)
        assert store.get_request("req_1") is req
        assert store.get_request("nonexistent") is None

    def test_save_and_get_result(self):
        store = MemoryApprovalStore()
        req = ApprovalRequest(id="req_1", kind="architecture")
        store.save_request(req)
        result = ApprovalResult(request_id="req_1", approved=True)
        store.save_result(result)
        assert store.get_result("req_1") is result
        # 保存结果后从待审批中移除
        assert len(store.list_pending()) == 0

    def test_list_pending(self):
        store = MemoryApprovalStore()
        store.save_request(ApprovalRequest(id="req_1", kind="architecture"))
        store.save_request(ApprovalRequest(id="req_2", kind="dispatch"))
        assert len(store.list_pending()) == 2


class TestApprovalPolicyEngine:
    """ApprovalPolicyEngine 策略引擎测试。"""

    def test_register_and_evaluate(self):
        engine = ApprovalPolicyEngine()
        policy = ApprovalPolicy(
            name="auto-approve-architecture",
            condition="kind == 'architecture'",
            auto_decision={"approved": True, "feedback": "自动批准架构方案"},
        )
        engine.register_policy(policy)
        request = ApprovalRequest(id="req_1", kind="architecture")
        result = engine.evaluate(request)
        assert result is not None
        assert result.approved is True
        assert result.decided_by == "auto_policy"

    def test_no_match(self):
        engine = ApprovalPolicyEngine()
        policy = ApprovalPolicy(
            name="auto-approve-architecture",
            condition="kind == 'architecture'",
            auto_decision={"approved": True},
        )
        engine.register_policy(policy)
        request = ApprovalRequest(id="req_1", kind="dispatch")
        result = engine.evaluate(request)
        assert result is None  # 不匹配

    def test_priority_order(self):
        """高优先级策略先匹配。"""
        engine = ApprovalPolicyEngine()
        engine.register_policy(ApprovalPolicy(
            name="low-priority",
            condition="kind == 'architecture'",
            auto_decision={"approved": False},
            priority=2,
        ))
        engine.register_policy(ApprovalPolicy(
            name="high-priority",
            condition="kind == 'architecture'",
            auto_decision={"approved": True},
            priority=1,  # 高优先级
        ))
        request = ApprovalRequest(id="req_1", kind="architecture")
        result = engine.evaluate(request)
        assert result is not None
        assert result.approved is True  # 高优先级生效

    def test_unregister_policy(self):
        engine = ApprovalPolicyEngine()
        policy = ApprovalPolicy(
            name="test-policy",
            condition="kind == 'architecture'",
            auto_decision={"approved": True},
        )
        engine.register_policy(policy)
        assert len(engine.list_policies()) == 1
        engine.unregister_policy("test-policy")
        assert len(engine.list_policies()) == 0

    def test_condition_content_field(self):
        """测试 content 字段匹配。"""
        engine = ApprovalPolicyEngine()
        engine.register_policy(ApprovalPolicy(
            name="auto-approve-small-change",
            condition="len(files) < 5",
            auto_decision={"approved": True, "feedback": "变更文件少，自动批准"},
        ))
        # 匹配：files 只有 3 个
        request = ApprovalRequest(
            id="req_1", kind="architecture",
            content={"files": ["a.py", "b.py", "c.py"]},
        )
        result = engine.evaluate(request)
        assert result is not None
        assert result.approved is True

        # 不匹配：files 有 10 个
        request2 = ApprovalRequest(
            id="req_2", kind="architecture",
            content={"files": [f"f{i}.py" for i in range(10)]},
        )
        result2 = engine.evaluate(request2)
        assert result2 is None


class TestApprovalQueue:
    """ApprovalQueue 审批队列测试。"""

    def test_submit_and_get_request(self):
        queue = ApprovalQueue()
        req_id = queue.submit(ApprovalRequest(kind="architecture", title="测试"))
        assert req_id.startswith("approval_")
        request = queue.get_request(req_id)
        assert request is not None
        assert request.title == "测试"

    def test_resolve(self):
        queue = ApprovalQueue()
        req_id = queue.submit(ApprovalRequest(kind="architecture"))
        result = ApprovalResult(request_id=req_id, approved=True, feedback="批准")
        success = queue.resolve(result)
        assert success is True
        # 再次 resolve 返回 False
        assert queue.resolve(result) is False

    def test_poll_before_resolve_returns_none(self):
        queue = ApprovalQueue()
        req_id = queue.submit(ApprovalRequest(
            kind="architecture", timeout_ms=60000, auto_decision={"approved": True},
        ))
        result = queue.poll(req_id, timeout_ms=100)
        assert result is None  # 还没超时，也没结果

    def test_poll_after_resolve(self):
        queue = ApprovalQueue()
        req_id = queue.submit(ApprovalRequest(kind="architecture"))
        result = ApprovalResult(request_id=req_id, approved=True)
        queue.resolve(result)
        poll_result = queue.poll(req_id)
        assert poll_result is not None
        assert poll_result.approved is True

    def test_auto_timeout(self):
        """超时后自动决策。"""
        queue = ApprovalQueue()
        req_id = queue.submit(ApprovalRequest(
            kind="architecture",
            timeout_ms=50,  # 50ms 超时
            auto_decision={"approved": True},
        ))
        # 等待超时
        time.sleep(0.1)
        result = queue.poll(req_id, timeout_ms=100)
        assert result is not None
        assert result.decided_by == "auto_timeout"
        assert result.approved is True

    def test_pending_requests(self):
        queue = ApprovalQueue()
        queue.submit(ApprovalRequest(kind="architecture", title="架构审批"))
        queue.submit(ApprovalRequest(kind="dispatch", title="派发审批"))
        pending = queue.pending_requests()
        assert len(pending) == 2

    def test_pending_requests_filtered(self):
        queue = ApprovalQueue()
        queue.submit(ApprovalRequest(kind="architecture", title="架构审批"))
        queue.submit(ApprovalRequest(kind="dispatch", title="派发审批"))
        pending = queue.pending_requests(filter_by={"kind": "architecture"})
        assert len(pending) == 1
        assert pending[0].kind == "architecture"

    def test_auto_policy(self):
        """策略引擎自动批准。"""
        engine = ApprovalPolicyEngine()
        engine.register_policy(ApprovalPolicy(
            name="auto-approve-architecture",
            condition="kind == 'architecture'",
            auto_decision={"approved": True},
        ))
        queue = ApprovalQueue(policy_engine=engine)
        req_id = queue.submit(ApprovalRequest(kind="architecture"))
        # 应该立即有结果
        result = queue.get_result(req_id)
        assert result is not None
        assert result.decided_by == "auto_policy"

    def test_on_resolve_callback(self):
        """resolve 回调。"""
        callback_results = []

        def on_resolve(result):
            callback_results.append(result)

        queue = ApprovalQueue(on_resolve=on_resolve)
        req_id = queue.submit(ApprovalRequest(kind="architecture"))
        result = ApprovalResult(request_id=req_id, approved=True)
        queue.resolve(result)
        assert len(callback_results) == 1
        assert callback_results[0].approved is True

    def test_stats(self):
        queue = ApprovalQueue()
        queue.submit(ApprovalRequest(kind="architecture"))
        queue.submit(ApprovalRequest(kind="dispatch"))
        stats = queue.stats()
        assert stats["pending_count"] == 2

    def test_multiple_concurrent_requests(self):
        """多个审批请求互不影响。"""
        queue = ApprovalQueue()
        id1 = queue.submit(ApprovalRequest(kind="architecture"))
        id2 = queue.submit(ApprovalRequest(kind="dispatch"))
        id3 = queue.submit(ApprovalRequest(kind="budget_exceed"))

        assert len(queue.pending_requests()) == 3

        # 批准第一个和第三个
        queue.resolve(ApprovalResult(request_id=id1, approved=True))
        queue.resolve(ApprovalResult(request_id=id3, approved=False))

        # 第二个还在等待
        pending = queue.pending_requests()
        assert len(pending) == 1
        assert pending[0].id == id2


class TestSyncAsk:
    """sync_ask 兼容层测试。"""

    def test_sync_ask_auto_timeout(self):
        """超时自动决策。"""
        queue = ApprovalQueue()
        result = sync_ask(
            interrupt_value={"kind": "architecture", "title": "测试"},
            auto_yes=True,
            timeout_ms=50,  # 快速超时
            queue=queue,
        )
        assert result["approved"] is True
        assert "自动决策" in result["feedback"]

    def test_sync_ask_resolved(self):
        """在超时前被 resolve。"""
        from agent_hive.async_hitl import ApprovalResult as AR

        queue = ApprovalQueue()
        resolved_ids = []

        original_submit = queue.submit
        def auto_resolve_submit(request):
            rid = original_submit(request)
            # 立即批准
            queue.resolve(AR(
                request_id=rid, approved=True, feedback="已批准",
            ))
            resolved_ids.append(rid)
            return rid

        queue.submit = auto_resolve_submit  # type: ignore[assignment]

        result = sync_ask(
            interrupt_value={"kind": "architecture", "title": "测试"},
            auto_yes=True,
            timeout_ms=5000,
            queue=queue,
        )
        assert result["approved"] is True
        assert result["feedback"] == "已批准"