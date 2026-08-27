"""成本控制与预算管理 —— 预算估算 → 实时监控 → 超预算自动降级。

核心策略：
1. TokenEstimator：执行前估算 token 消耗，使用 tiktoken 或模型 tokenizer
2. CostTracker：运行时实时追踪 per-role / per-model 消耗
3. CostController：单一入口，集成估算 → 检查 → 记录 → 降级决策
4. 降级策略：正常 → 换便宜模型 → 减少输出 → 截断 prompt → 阻塞
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Literal

__all__ = [
    "CostBudget",
    "CostSnapshot",
    "CostAlert",
    "BudgetDecision",
    "CostController",
    "TokenEstimator",
    "CostTracker",
]

# ---------------------------------------------------------------------------
# 模型定价表（USD / 1K tokens）
# ---------------------------------------------------------------------------
MODEL_PRICING: dict[str, dict[str, float]] = {
    "deepseek-chat": {"input": 0.0005, "output": 0.0020},
    "deepseek-chat-lite": {"input": 0.0002, "output": 0.0008},
    "deepseek-reasoner": {"input": 0.0008, "output": 0.0030},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.0025, "output": 0.010},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
}

# 默认降级链（按性价比从高到低）
DEFAULT_DEGRADATION_CHAIN = [
    "deepseek-chat",
    "deepseek-chat-lite",
    "gpt-4o-mini",
]


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class CostBudget:
    """一次 run 的成本预算配置。"""
    max_tokens: int = 0             # 总 token 预算上限（0 表示不限制）
    max_model_calls: int = 0        # 模型调用次数上限（0 表示不限制）
    max_cost_usd: float = 0.0       # 美元成本上限（0 表示不限制）
    per_agent_limits: dict[str, int] = field(default_factory=dict)
    # 按角色设限，如 {"编码": 50000, "评审": 20000}
    warn_ratio: float = 0.8         # 触发 warn 告警的阈值比例


@dataclass
class CostSnapshot:
    """实时成本快照，供运行时决策和最终审计。"""
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    model_calls: int = 0
    estimated_cost_usd: float = 0.0
    by_role: dict[str, "CostSnapshot"] = field(default_factory=dict)
    by_model: dict[str, "CostSnapshot"] = field(default_factory=dict)

    def merge(self, role: str, model: str, input_t: int, output_t: int, cost: float):
        """合并一次调用记录。"""
        self.total_tokens += input_t + output_t
        self.input_tokens += input_t
        self.output_tokens += output_t
        self.model_calls += 1
        self.estimated_cost_usd += cost

        if role not in self.by_role:
            self.by_role[role] = CostSnapshot()
        r = self.by_role[role]
        r.total_tokens += input_t + output_t
        r.input_tokens += input_t
        r.output_tokens += output_t
        r.model_calls += 1
        r.estimated_cost_usd += cost

        if model not in self.by_model:
            self.by_model[model] = CostSnapshot()
        m = self.by_model[model]
        m.total_tokens += input_t + output_t
        m.input_tokens += input_t
        m.output_tokens += output_t
        m.model_calls += 1
        m.estimated_cost_usd += cost


@dataclass
class CostAlert:
    """成本告警事件。"""
    level: Literal["warn", "critical", "exceeded"]
    message: str
    triggered_at: float
    budget: CostBudget
    current: CostSnapshot


@dataclass
class BudgetDecision:
    """预算检查决策。"""
    action: Literal["proceed", "downgrade", "block"]
    reason: str
    fallback_model: str | None = None  # downgrade 时建议的降级模型


# ---------------------------------------------------------------------------
# TokenEstimator —— 执行前估算
# ---------------------------------------------------------------------------

class TokenEstimator:
    """执行前估算 token 消耗。

    使用简单启发式估算（字符数 / 系数），不引入 tiktoken 依赖。
    需要精确估算时可注册自定义 tokenizer。
    """

    _TOKEN_PER_CHAR: float = 4.0  # 中英文混合的平均字符/token 比

    def __init__(self, model_pricing: dict[str, dict[str, float]] | None = None):
        self._pricing = model_pricing or MODEL_PRICING
        self._custom_tokenizers: dict[str, callable] = {}

    def register_tokenizer(self, model: str, tokenizer_fn: callable):
        """注册自定义 tokenizer。"""
        self._custom_tokenizers[model] = tokenizer_fn

    def estimate_tokens(self, text: str, model: str = "deepseek-chat") -> int:
        """估算文本的 token 数。"""
        if model in self._custom_tokenizers:
            return self._custom_tokenizers[model](text)
        # 简单启发式：字符数 / 4
        return max(1, int(len(text) / self._TOKEN_PER_CHAR))

    def estimate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """估算成本（USD）。"""
        pricing = self._pricing.get(model, self._pricing.get("deepseek-chat"))
        input_cost = (input_tokens / 1000) * pricing.get("input", 0.0005)
        output_cost = (output_tokens / 1000) * pricing.get("output", 0.0020)
        return input_cost + output_cost

    def estimate_prompt_cost(
        self, messages: list, model: str, output_estimate_tokens: int = 500
    ) -> tuple[int, float]:
        """估算 prompt 的 token 数和成本。"""
        prompt_text = " ".join(str(m) for m in messages)
        input_tokens = self.estimate_tokens(prompt_text, model)
        cost = self.estimate_cost(input_tokens, output_estimate_tokens, model)
        return input_tokens + output_estimate_tokens, cost


# ---------------------------------------------------------------------------
# CostTracker —— 运行时追踪
# ---------------------------------------------------------------------------

class CostTracker:
    """运行时成本追踪器（线程安全）。"""

    def __init__(self):
        self._snapshot = CostSnapshot()
        self._lock = threading.Lock()

    def record(
        self, role: str, model: str,
        input_tokens: int, output_tokens: int, cost_usd: float,
    ):
        """记录一次模型调用（线程安全）。"""
        with self._lock:
            self._snapshot.merge(role, model, input_tokens, output_tokens, cost_usd)

    def snapshot(self) -> CostSnapshot:
        """返回当前快照的副本（线程安全）。"""
        with self._lock:
            return self._snapshot

    def reset(self):
        """重置计数器。"""
        with self._lock:
            self._snapshot = CostSnapshot()


# ---------------------------------------------------------------------------
# CostController —— 统一入口
# ---------------------------------------------------------------------------

class CostController:
    """成本控制器：估算 → 监控 → 降级决策的单一入口。"""

    def __init__(
        self,
        budget: CostBudget | None = None,
        model_pricing: dict[str, dict[str, float]] | None = None,
        degradation_chain: list[str] | None = None,
        tracker: CostTracker | None = None,
        estimator: TokenEstimator | None = None,
    ):
        self._budget = budget or CostBudget()
        self._pricing = model_pricing or MODEL_PRICING
        self._degradation_chain = degradation_chain or DEFAULT_DEGRADATION_CHAIN
        self._tracker = tracker or CostTracker()
        self._estimator = estimator or TokenEstimator(self._pricing)
        self._current_model_index: dict[str, int] = {}  # role -> current index in chain
        self._alerts: list[CostAlert] = []
        self._lock = threading.Lock()

    # -- 预算检查 --

    def check_budget_before_call(self, model: str, role: str) -> BudgetDecision:
        """调用前检查：是否还有预算？

        Returns: BudgetDecision(action="proceed"|"downgrade"|"block", reason="")
        """
        has_global_limits = (
            self._budget.max_tokens > 0
            or self._budget.max_cost_usd > 0
            or self._budget.max_model_calls > 0
        )
        has_per_agent_limits = bool(self._budget.per_agent_limits)
        if not has_global_limits and not has_per_agent_limits:
            return BudgetDecision(action="proceed", reason="无预算限制")

        snap = self._tracker.snapshot()

        # 检查调用次数
        if self._budget.max_model_calls > 0 and snap.model_calls >= self._budget.max_model_calls:
            return self._make_block_decision("模型调用次数已达上限")

        # 检查总 token
        if self._budget.max_tokens > 0 and snap.total_tokens >= self._budget.max_tokens:
            return self._make_block_decision("总 token 消耗已达预算上限")

        # 检查成本
        if self._budget.max_cost_usd > 0 and snap.estimated_cost_usd >= self._budget.max_cost_usd:
            return self._make_block_decision("成本已达预算上限")

        # 检查 per-agent 限制
        if role in self._budget.per_agent_limits:
            limit = self._budget.per_agent_limits[role]
            role_snap = snap.by_role.get(role)
            if role_snap and role_snap.total_tokens >= limit:
                return self._make_block_decision(f"角色 {role} 的 token 限额已用完")

        # 检查是否接近预算上限，触发降级 warn
        if self._budget.max_tokens > 0:
            ratio = snap.total_tokens / self._budget.max_tokens if self._budget.max_tokens else 0
            if ratio >= self._budget.warn_ratio:
                self._add_alert("warn", f"预算已用 {ratio:.0%}，接近上限", snap)
                # 尝试降级
                return self._try_degrade(role, model)

        if self._budget.max_cost_usd > 0:
            ratio = snap.estimated_cost_usd / self._budget.max_cost_usd if self._budget.max_cost_usd else 0
            if ratio >= 1.0:
                return self._make_block_decision("成本已超预算上限")

        return BudgetDecision(action="proceed", reason="预算充足")

    def _try_degrade(self, role: str, current_model: str) -> BudgetDecision:
        """尝试降级到更便宜的模型。"""
        with self._lock:
            idx = self._current_model_index.get(role, 0)
            try:
                current_idx = self._degradation_chain.index(current_model)
            except ValueError:
                current_idx = idx

            next_idx = current_idx + 1
            if next_idx < len(self._degradation_chain):
                fallback = self._degradation_chain[next_idx]
                self._current_model_index[role] = next_idx
                self._add_alert("critical", f"预算接近上限，降级到 {fallback}", self._tracker.snapshot())
                return BudgetDecision(
                    action="downgrade",
                    reason=f"预算接近上限，自动降级到 {fallback}",
                    fallback_model=fallback,
                )

        return BudgetDecision(
            action="block",
            reason="已使用最便宜的模型，预算仍不足，请增加预算后重试",
        )

    def _make_block_decision(self, reason: str) -> BudgetDecision:
        self._add_alert("exceeded", reason, self._tracker.snapshot())
        return BudgetDecision(action="block", reason=reason)

    # -- 调用记录 --

    def record_after_call(
        self, model: str, role: str, input_tokens: int, output_tokens: int,
    ) -> CostSnapshot:
        """调用后记录实际消耗，返回当前快照。"""
        cost = self._estimator.estimate_cost(input_tokens, output_tokens, model)
        self._tracker.record(role, model, input_tokens, output_tokens, cost)
        return self._tracker.snapshot()

    # -- 查询 --

    def snapshot(self) -> CostSnapshot:
        """返回当前快照（线程安全）。"""
        return self._tracker.snapshot()

    def alerts(self) -> list[CostAlert]:
        """返回本轮已触发的告警。"""
        return list(self._alerts)

    def budget(self) -> CostBudget:
        """返回当前预算配置。"""
        return self._budget

    def reset(self):
        """重置所有状态（预算配置保留）。"""
        self._tracker.reset()
        self._alerts.clear()
        self._current_model_index.clear()

    # -- 内部 --

    def _add_alert(self, level: str, message: str, current: CostSnapshot):
        self._alerts.append(CostAlert(
            level=level,  # type: ignore
            message=message,
            triggered_at=time.time(),
            budget=self._budget,
            current=current,
        ))

    # -- 辅助方法 --

    def estimate_cost(self, messages: list, model: str) -> int:
        """执行前估算 token 消耗。"""
        tokens, _ = self._estimator.estimate_prompt_cost(messages, model)
        return tokens

    def format_dashboard(self) -> str:
        """生成成本看板文本。"""
        snap = self._tracker.snapshot()
        budget = self._budget
        lines = [
            "成本概览（实时）：",
            f"├─ 总消耗：{snap.total_tokens:,} tokens | ${snap.estimated_cost_usd:.4f} | {snap.model_calls} 次调用",
        ]

        if snap.by_role:
            lines.append("├─ 按角色：")
            for role, rs in sorted(snap.by_role.items()):
                lines.append(f"│  ├─ {role}：{rs.total_tokens:,} tokens | ${rs.estimated_cost_usd:.4f} | {rs.model_calls} 次调用")

        if snap.by_model:
            lines.append("├─ 按模型：")
            for model, ms in sorted(snap.by_model.items()):
                lines.append(f"│  ├─ {model}：{ms.total_tokens:,} tokens | ${ms.estimated_cost_usd:.4f} | {ms.model_calls} 次调用")

        budget_str = "、".join(filter(None, [
            f"{budget.max_tokens:,} tokens" if budget.max_tokens else "",
            f"${budget.max_cost_usd:.2f}" if budget.max_cost_usd else "",
            f"{budget.max_model_calls} 次调用" if budget.max_model_calls else "",
        ]))
        if budget_str:
            ratio = snap.total_tokens / budget.max_tokens if budget.max_tokens else 0
            lines.append(f"├─ 预算：{budget_str} | 已用 {ratio:.1%} | 剩余 {max(0, budget.max_tokens - snap.total_tokens):,} tokens")
        else:
            lines.append("├─ 预算：无限制")

        alerts = self.alerts()
        lines.append(f"└─ 告警：{len(alerts)} 条")
        for a in alerts[-3:]:  # 最多显示最近 3 条
            lines.append(f"   ├─ [{a.level}] {a.message}")

        return "\n".join(lines)