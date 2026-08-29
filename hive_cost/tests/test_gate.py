"""CostGate 一等原语测试：预算三态 / 降级链耗尽 / per-role 限额 / 线程安全。"""
from __future__ import annotations

import threading

import pytest

from hive_cost.budget import CostBudget
from hive_cost.gate import CostGate


class TestBudgetTristate:
    """预算三态：proceed / downgrade / block。"""

    def test_proceed_when_no_budget(self):
        gate = CostGate()
        decision = gate.check_before_call("deepseek-chat", "编码")
        assert decision.action == "proceed"

    def test_proceed_when_budget_available(self):
        gate = CostGate(budget=CostBudget(max_tokens=1000))
        gate.record_after_call("deepseek-chat", "编码", 100, 50)
        assert gate.check_before_call("deepseek-chat", "编码").action == "proceed"

    def test_block_when_token_budget_exhausted(self):
        gate = CostGate(budget=CostBudget(max_tokens=100))
        gate.record_after_call("deepseek-chat", "编码", 60, 40)  # 刚好 100
        decision = gate.check_before_call("deepseek-chat", "编码")
        assert decision.action == "block"
        assert "预算上限" in decision.reason

    def test_block_when_cost_budget_exhausted(self):
        gate = CostGate(budget=CostBudget(max_cost_usd=0.001))
        gate.record_after_call("deepseek-chat", "编码", 1000, 500)  # ≈ $0.0015
        assert gate.check_before_call("deepseek-chat", "编码").action == "block"

    def test_block_when_model_calls_exhausted(self):
        gate = CostGate(budget=CostBudget(max_model_calls=2))
        for _ in range(2):
            assert gate.check_before_call("deepseek-chat", "编码").action == "proceed"
            gate.record_after_call("deepseek-chat", "编码", 10, 5)
        assert gate.check_before_call("deepseek-chat", "编码").action == "block"

    def test_downgrade_when_near_limit(self):
        gate = CostGate(
            budget=CostBudget(max_tokens=100, warn_ratio=0.8),
            degradation_chain=["deepseek-chat", "deepseek-chat-lite"],
        )
        gate.record_after_call("deepseek-chat", "编码", 80, 1)  # 81 ≥ 80%
        decision = gate.check_before_call("deepseek-chat", "编码")
        assert decision.action == "downgrade"
        assert decision.fallback_model == "deepseek-chat-lite"


class TestDegradationChainExhausted:
    """降级链耗尽 → block。"""

    def test_block_when_chain_exhausted(self):
        gate = CostGate(
            budget=CostBudget(max_tokens=50, warn_ratio=0.5),
            degradation_chain=["deepseek-chat-lite"],  # 只剩最便宜的
        )
        gate.record_after_call("deepseek-chat-lite", "编码", 30, 1)
        decision = gate.check_before_call("deepseek-chat-lite", "编码")
        assert decision.action == "block"
        assert "最便宜的模型" in decision.reason

    def test_downgrade_then_block_across_chain(self):
        gate = CostGate(
            budget=CostBudget(max_tokens=100, warn_ratio=0.5),
            degradation_chain=["deepseek-chat", "deepseek-chat-lite"],
        )
        gate.record_after_call("deepseek-chat", "编码", 60, 1)
        # 第一次：降级到 deepseek-chat-lite
        assert gate.check_before_call("deepseek-chat", "编码").action == "downgrade"
        # 再次接近上限：链已到底 → block
        gate.record_after_call("deepseek-chat-lite", "编码", 30, 1)
        assert gate.check_before_call("deepseek-chat-lite", "编码").action == "block"


class TestPerRoleLimit:
    """per-role 限额：只约束指定角色。"""

    def test_role_limit_blocks_only_that_role(self):
        gate = CostGate(budget=CostBudget(per_agent_limits={"编码": 100}))
        gate.record_after_call("deepseek-chat", "编码", 60, 40)  # 刚好 100
        assert gate.check_before_call("deepseek-chat", "编码").action == "block"
        # 其他角色不受限
        assert gate.check_before_call("deepseek-chat", "评审").action == "proceed"

    def test_role_limit_counts_role_tokens_only(self):
        gate = CostGate(budget=CostBudget(per_agent_limits={"编码": 100}))
        gate.record_after_call("deepseek-chat", "评审", 500, 500)  # 评审大量消耗
        assert gate.check_before_call("deepseek-chat", "编码").action == "proceed"


class TestThreadSafety:
    """10 线程 × 100 调用：计数与事件不丢失。"""

    N_THREADS = 10
    CALLS_PER_THREAD = 100

    def test_concurrent_calls_counts_not_lost(self):
        gate = CostGate()
        errors: list[Exception] = []

        def worker():
            try:
                for _ in range(self.CALLS_PER_THREAD):
                    gate.check_before_call("deepseek-chat", "编码")
                    gate.record_after_call("deepseek-chat", "编码", 10, 5)
            except Exception as exc:  # pragma: no cover
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(self.N_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        expected = self.N_THREADS * self.CALLS_PER_THREAD
        snap = gate.snapshot()
        assert snap.model_calls == expected
        assert snap.total_tokens == expected * 15
        assert len(gate.to_otel_events()) == expected
        # 事件按 (model, role) 细分也齐全
        assert snap.by_model["deepseek-chat"].model_calls == expected
        assert snap.by_role["编码"].model_calls == expected


class TestEvents:
    """CostGate → OTel 事件配对与字段。"""

    def test_event_action_matches_decision(self):
        gate = CostGate(
            budget=CostBudget(max_tokens=100, warn_ratio=0.8),
            degradation_chain=["deepseek-chat", "deepseek-chat-lite"],
        )
        gate.record_after_call("deepseek-chat", "编码", 80, 1)
        decision = gate.check_before_call("deepseek-chat", "编码")
        assert decision.action == "downgrade"
        gate.record_after_call("deepseek-chat-lite", "编码", 10, 5, latency_ms=12.5)
        events = gate.to_otel_events()
        assert [e["attributes"]["action"] for e in events] == ["proceed", "downgrade"]
        assert [e["attributes"]["downgraded"] for e in events] == [False, True]
        assert events[1]["attributes"]["model"] == "deepseek-chat-lite"

    def test_record_returns_merged_snapshot(self):
        gate = CostGate()
        snap = gate.record_after_call("deepseek-chat", "编码", 100, 50)
        assert snap.total_tokens == 150
        assert snap.model_calls == 1
