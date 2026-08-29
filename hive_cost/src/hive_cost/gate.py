"""CostGate —— 成本控制一等原语（预算检查 → 调用记录 → OTel 事件）。

在 ``budget.CostController`` 之上提供面向单次模型调用的门面：

- ``check_before_call``：调用前预算检查，返回 proceed / downgrade / block；
- ``record_after_call``：调用后记录实际消耗（按定价表估算成本），并生成
  OTel 兼容事件（``agent.model_call``）；
- ``snapshot`` / ``alerts``：实时快照与告警（委托 CostController，线程安全）；
- ``to_otel_events``：导出结构化事件，供 ``hive_cost.otel.export_cost_otel_jsonl`` 落盘。

线程安全：所有状态变更在锁内进行，并发 check/record 不丢计数、不丢事件。
纯标准库实现，不依赖 pydantic / langchain / opentelemetry SDK。
"""
from __future__ import annotations

import threading
import time

from .budget import (
    MODEL_PRICING,
    BudgetDecision,
    CostAlert,
    CostBudget,
    CostController,
    CostSnapshot,
    TokenEstimator,
)

__all__ = ["CostGate"]

# 事件名（OTel 兼容，语义与 agent.model.* 命名一致）。
_EVENT_NAME = "agent.model_call"


class CostGate:
    """成本闸门：调用前检查 → 调用后记录 → OTel 事件导出。

    Args:
        budget: 成本预算配置；None 时用 ``CostBudget()``（无限制）。
        pricing: 模型定价表（USD / 1K tokens），缺省 ``MODEL_PRICING``。
        degradation_chain: 降级链（按性价比从高到低），缺省内置链。
    """

    def __init__(
        self,
        budget: CostBudget | None = None,
        pricing: dict[str, dict[str, float]] | None = None,
        degradation_chain: list[str] | None = None,
    ):
        self._pricing = pricing or MODEL_PRICING
        self._estimator = TokenEstimator(self._pricing)
        self._controller = CostController(
            budget=budget,
            model_pricing=self._pricing,
            degradation_chain=degradation_chain,
            estimator=self._estimator,
        )
        self._lock = threading.Lock()
        # 未配对的检查决策：(model, role, decision)，按序 FIFO 配对给 record。
        self._pending: list[tuple[str, str, BudgetDecision]] = []
        # 已记录的 OTel 事件（按记录顺序）。
        self._events: list[dict] = []

    # -- 调用前 --

    def check_before_call(self, model: str, role: str) -> BudgetDecision:
        """调用前预算检查（线程安全）。

        返回 ``BudgetDecision(action="proceed"|"downgrade"|"block", ...)``；
        该决策会被记录并与后续 ``record_after_call`` 配对，进入 OTel 事件的
        ``attributes.action`` / ``attributes.downgraded`` 字段。
        """
        decision = self._controller.check_budget_before_call(model, role)
        with self._lock:
            self._pending.append((model, role, decision))
        return decision

    # -- 调用后 --

    def record_after_call(
        self,
        model: str,
        role: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float = 0.0,
    ) -> CostSnapshot:
        """调用后记录实际消耗并生成 OTel 事件，返回合并后的快照（线程安全）。

        - 成本按定价表估算：``cost_usd = in/1000*input + out/1000*output``；
        - 事件 ``start_time_unix_nano = end - latency_ms``，``end`` 为记录时刻；
        - ``action`` 取最近一次同 role 的检查决策（按 role 配对：降级决策后
          实际调用的是 fallback 模型，模型名会变、role 不变；无配对时默认 proceed）。
        """
        action = "proceed"
        with self._lock:
            for i, (m, r, decision) in enumerate(self._pending):
                if r == role:
                    action = decision.action
                    del self._pending[i]
                    break

        cost_usd = self._estimator.estimate_cost(input_tokens, output_tokens, model)
        snapshot = self._controller.record_after_call(model, role, input_tokens, output_tokens)

        end_ns = time.time_ns()
        start_ns = end_ns - int(max(0.0, latency_ms) * 1_000_000)
        event = {
            "name": _EVENT_NAME,
            "start_time_unix_nano": start_ns,
            "end_time_unix_nano": end_ns,
            "attributes": {
                "model": model,
                "role": role,
                "input_tokens": int(input_tokens),
                "output_tokens": int(output_tokens),
                "cost_usd": float(cost_usd),
                "downgraded": action == "downgrade",
                "action": action,
            },
        }
        with self._lock:
            self._events.append(event)
        return snapshot

    # -- 查询 --

    def snapshot(self) -> CostSnapshot:
        """返回当前成本快照（线程安全）。"""
        return self._controller.snapshot()

    def alerts(self) -> list[CostAlert]:
        """返回本轮已触发的告警。"""
        return self._controller.alerts()

    def to_otel_events(self) -> list[dict]:
        """导出 OTel 兼容事件（浅拷贝，线程安全）。

        每条事件字段固定：
        ``{"name":"agent.model_call","start_time_unix_nano":int,
        "end_time_unix_nano":int,"attributes":{"model":str,"role":str,
        "input_tokens":int,"output_tokens":int,"cost_usd":float,
        "downgraded":bool,"action":"proceed|downgrade|block"}}``
        """
        with self._lock:
            return [dict(e) for e in self._events]
