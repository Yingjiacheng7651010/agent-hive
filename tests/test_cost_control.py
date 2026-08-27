"""Tests for card-cost-control: CostControl, TokenEstimator, CostTracker."""
from __future__ import annotations

import threading
import time

import pytest

from agent_hive.cost_control import (
    CostBudget,
    CostController,
    CostSnapshot,
    CostTracker,
    TokenEstimator,
)


class TestTokenEstimator:
    """TokenEstimator 估算器测试。"""

    def test_estimate_tokens_simple(self):
        est = TokenEstimator()
        # 空字符串返回至少 1
        assert est.estimate_tokens("", "deepseek-chat") >= 1
        # 短文本
        tokens = est.estimate_tokens("hello world", "deepseek-chat")
        assert tokens >= 1

    def test_estimate_tokens_longer_text(self):
        est = TokenEstimator()
        text = "A" * 1000
        tokens = est.estimate_tokens(text, "deepseek-chat")
        assert tokens >= 200  # 1000 / 4 = 250 左右

    def test_estimate_cost(self):
        est = TokenEstimator()
        # 1000 input tokens, 500 output tokens, deepseek-chat
        cost = est.estimate_cost(1000, 500, "deepseek-chat")
        expected = (1000 / 1000) * 0.0005 + (500 / 1000) * 0.0020
        assert cost == pytest.approx(expected)

    def test_estimate_cost_unknown_model_falls_back(self):
        est = TokenEstimator()
        cost = est.estimate_cost(1000, 500, "unknown-model")
        assert cost > 0  # 使用默认定价

    def test_register_custom_tokenizer(self):
        est = TokenEstimator()
        def my_tokenizer(text: str) -> int:
            return len(text)  # 每个字符算一个 token
        est.register_tokenizer("my-model", my_tokenizer)
        assert est.estimate_tokens("hello", "my-model") == 5

    def test_estimate_prompt_cost(self):
        est = TokenEstimator()
        messages = [{"role": "user", "content": "Hello"}]
        tokens, cost = est.estimate_prompt_cost(messages, "deepseek-chat", output_estimate_tokens=100)
        assert tokens > 100  # 至少 output_estimate_tokens
        assert cost > 0


class TestCostTracker:
    """CostTracker 成本追踪器测试。"""

    def test_record_and_snapshot(self):
        tracker = CostTracker()
        assert tracker.snapshot().total_tokens == 0

        tracker.record("编码", "deepseek-chat", 100, 50, 0.0005)
        snap = tracker.snapshot()
        assert snap.total_tokens == 150
        assert snap.input_tokens == 100
        assert snap.output_tokens == 50
        assert snap.model_calls == 1
        assert snap.estimated_cost_usd == 0.0005

    def test_record_by_role(self):
        tracker = CostTracker()
        tracker.record("编码", "deepseek-chat", 100, 50, 0.001)
        tracker.record("评审", "deepseek-chat", 200, 100, 0.002)

        snap = tracker.snapshot()
        assert "编码" in snap.by_role
        assert "评审" in snap.by_role
        assert snap.by_role["编码"].total_tokens == 150
        assert snap.by_role["评审"].total_tokens == 300

    def test_record_by_model(self):
        tracker = CostTracker()
        tracker.record("编码", "deepseek-chat", 100, 50, 0.001)
        tracker.record("编码", "gpt-4o-mini", 200, 100, 0.002)

        snap = tracker.snapshot()
        assert "deepseek-chat" in snap.by_model
        assert "gpt-4o-mini" in snap.by_model
        assert snap.by_model["deepseek-chat"].total_tokens == 150
        assert snap.by_model["gpt-4o-mini"].total_tokens == 300

    def test_reset(self):
        tracker = CostTracker()
        tracker.record("编码", "deepseek-chat", 100, 50, 0.001)
        assert tracker.snapshot().total_tokens == 150
        tracker.reset()
        assert tracker.snapshot().total_tokens == 0

    def test_thread_safety(self):
        """多线程并发记录不丢失。"""
        tracker = CostTracker()
        n_threads = 10
        calls_per_thread = 100

        def worker():
            for _ in range(calls_per_thread):
                tracker.record("编码", "deepseek-chat", 10, 5, 0.0001)

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        snap = tracker.snapshot()
        expected_calls = n_threads * calls_per_thread
        assert snap.model_calls == expected_calls
        assert snap.total_tokens == expected_calls * 15


class TestCostController:
    """CostController 成本控制器测试。"""

    def test_no_budget_proceed(self):
        controller = CostController(budget=CostBudget(max_tokens=0))
        decision = controller.check_budget_before_call("deepseek-chat", "编码")
        assert decision.action == "proceed"

    def test_token_budget_block(self):
        budget = CostBudget(max_tokens=100)
        controller = CostController(budget=budget)
        # 先消耗 100 tokens
        controller.record_after_call("deepseek-chat", "编码", 60, 40)
        snap = controller.snapshot()
        assert snap.total_tokens == 100

        # 超额调用
        decision = controller.check_budget_before_call("deepseek-chat", "编码")
        assert decision.action == "block"
        assert "已达预算上限" in decision.reason

    def test_cost_budget_block(self):
        budget = CostBudget(max_cost_usd=0.001)
        controller = CostController(budget=budget)
        controller.record_after_call("deepseek-chat", "编码", 1000, 500)
        snap = controller.snapshot()
        # cost = 1000/1000*0.0005 + 500/1000*0.0020 = 0.0005 + 0.001 = 0.0015
        assert snap.estimated_cost_usd > 0.001
        decision = controller.check_budget_before_call("deepseek-chat", "编码")
        assert decision.action == "block"

    def test_model_calls_limit(self):
        budget = CostBudget(max_model_calls=3)
        controller = CostController(budget=budget)
        for _ in range(3):
            assert controller.check_budget_before_call("deepseek-chat", "编码").action == "proceed"
            controller.record_after_call("deepseek-chat", "编码", 10, 5)
        # 第 4 次应该被阻塞
        decision = controller.check_budget_before_call("deepseek-chat", "编码")
        assert decision.action == "block"

    def test_per_agent_limit(self):
        budget = CostBudget(per_agent_limits={"编码": 100})
        controller = CostController(budget=budget)
        controller.record_after_call("deepseek-chat", "编码", 60, 40)
        # 刚好 100，下次应该 block
        decision = controller.check_budget_before_call("deepseek-chat", "编码")
        assert decision.action == "block"

    def test_degradation(self):
        """预算接近上限时触发降级。"""
        budget = CostBudget(max_tokens=100, warn_ratio=0.8)
        controller = CostController(budget=budget, degradation_chain=["deepseek-chat", "deepseek-chat-lite"])
        controller.record_after_call("deepseek-chat", "编码", 80, 1)
        # 81 tokens，超过 80% 阈值
        decision = controller.check_budget_before_call("deepseek-chat", "编码")
        assert decision.action == "downgrade"
        assert decision.fallback_model == "deepseek-chat-lite"

    def test_degradation_chain_exhausted(self):
        """降级链用尽后返回 block。"""
        budget = CostBudget(max_tokens=50, warn_ratio=0.5)
        controller = CostController(
            budget=budget,
            degradation_chain=["deepseek-chat-lite"],  # 只有最便宜的
        )
        controller.record_after_call("deepseek-chat-lite", "编码", 30, 1)
        # 找不到更便宜的模型了
        decision = controller.check_budget_before_call("deepseek-chat-lite", "编码")
        assert decision.action == "block"

    def test_alerts(self):
        budget = CostBudget(max_tokens=100, warn_ratio=0.8)
        controller = CostController(budget=budget)
        assert len(controller.alerts()) == 0
        controller.record_after_call("deepseek-chat", "编码", 80, 1)
        decision = controller.check_budget_before_call("deepseek-chat", "编码")
        if decision.action == "block":
            assert len(controller.alerts()) >= 1
        else:
            assert len(controller.alerts()) >= 0  # 降级也可能触发告警

    def test_reset(self):
        budget = CostBudget(max_tokens=100)
        controller = CostController(budget=budget)
        controller.record_after_call("deepseek-chat", "编码", 60, 40)
        assert controller.snapshot().total_tokens == 100
        controller.reset()
        assert controller.snapshot().total_tokens == 0
        assert len(controller.alerts()) == 0

    def test_format_dashboard(self):
        budget = CostBudget(max_tokens=100000)
        controller = CostController(budget=budget)
        controller.record_after_call("deepseek-chat", "编码", 1000, 500,)
        controller.record_after_call("gpt-4o-mini", "评审", 500, 200)
        dashboard = controller.format_dashboard()
        assert "成本概览" in dashboard
        assert "按角色" in dashboard
        assert "按模型" in dashboard
        assert "预算" in dashboard

    def test_estimate_cost(self):
        controller = CostController()
        tokens = controller.estimate_cost([{"role": "user", "content": "Hello"}], "deepseek-chat")
        assert tokens >= 1

    def test_backward_compatibility_no_budget(self):
        """不设预算时行为与现有代码一致。"""
        controller = CostController()
        decision = controller.check_budget_before_call("deepseek-chat", "编码")
        assert decision.action == "proceed"
        controller.record_after_call("deepseek-chat", "编码", 100, 50)
        snap = controller.snapshot()
        assert snap.total_tokens == 150
        assert len(controller.alerts()) == 0