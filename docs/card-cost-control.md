# 工作卡片：card-cost-control —— 成本控制与预算管理

> 优先级：P0 | 类型：工程/成本 | 依赖：无
> 负责人：系统架构师 / 平台工程 | 轮次上限：3

---

## 1. 问题陈述

当前 agent-hive **没有任何成本控制机制**：每次 run 不设 token 预算上限，不限制 per-agent/per-role 的调用次数，LLM 调用失败时没有优雅降级策略。在字节生产环境，一个 agent 跑飞的成本可达数万元/天，成本管控是 agent 框架上生产的第一道门槛。

## 2. 目标

建立从"预算估算→实时监控→超预算自动降级"的完整成本控制链路，让每个 agent run 都有明确的成本预期和兜底策略。

## 3. 接口契约

### 3.1 核心数据结构

```python
# agent_hive/cost_control.py

@dataclass
class CostBudget:
    """一次 run 的成本预算配置。"""
    max_tokens: int           # 总 token 预算上限（0 表示不限制）
    max_model_calls: int      # 模型调用次数上限（0 表示不限制）
    max_cost_usd: float       # 美元成本上限（按模型单价估算）
    per_agent_limits: dict[str, int] = field(default_factory=dict)
    # 按角色设限，如 {"编码": 50000, "评审": 20000}

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

@dataclass
class CostAlert:
    """成本告警事件。"""
    level: Literal["warn", "critical", "exceeded"]
    message: str
    triggered_at: float
    budget: CostBudget
    current: CostSnapshot
```

### 3.2 核心接口

```python
class CostController:
    """成本控制器：估算 → 监控 → 降级决策的单一入口。"""

    def __init__(self, budget: CostBudget, model_pricing: dict[str, float]):
        ...

    def estimate_cost(self, messages: list, model: str) -> int:
        """执行前估算 token 消耗，返回预估 token 数。"""

    def check_budget_before_call(self, model: str, role: str) -> "BudgetDecision":
        """调用前检查：是否还有预算？
        Returns: BudgetDecision(action="proceed"|"downgrade"|"block", reason="")
        """

    def record_after_call(self, model: str, role: str, tokens: dict) -> CostSnapshot:
        """调用后记录实际消耗，返回当前快照。"""

    def snapshot(self) -> CostSnapshot:
        """返回当前快照（线程安全）。"""

    def alerts(self) -> list[CostAlert]:
        """返回本轮已触发的告警。"""

@dataclass
class BudgetDecision:
    action: Literal["proceed", "downgrade", "block"]
    reason: str
    fallback_model: str | None = None  # downgrade 时建议的降级模型
```

## 4. 实现方案

### 4.1 预算估算器（TokenEstimator）

- 使用 `tiktoken` 或模型自带的 tokenizer 估算 prompt 和 expected output 的 token 数
- 支持按模型单价（USD/1K tokens）估算成本
- 配置化的模型定价表（`MODEL_PRICING`）

### 4.2 运行时成本追踪器（CostTracker）

- 在 `TRACKER` 基础上扩展，增加 per-role 和 per-model 的分拆
- 线程安全：使用 `threading.Lock` 保护计数器
- 每次模型调用前后打点，记录 `(role, model, input_tokens, output_tokens, latency_ms)`

### 4.3 降级策略（DegradationStrategy）

当预算接近上限时自动触发降级（按配置顺序尝试）：

```
1. 正常模式 → 2. 换更便宜模型（如 deepseek-chat → deepseek-chat-lite）
   → 3. 减少输出长度（max_tokens 减半）→ 4. 截断 prompt（丢弃非关键上下文）
   → 5. 阻塞当前调用并返回"预算不足，请增加预算后重试"
```

### 4.4 看板集成

```
成本概览（实时）：
├─ 总消耗：12,847 tokens | $0.064 | 23 次调用
├─ 按角色：
│  ├─ 首脑：5,201 tokens | $0.026 | 8 次调用
│  ├─ 编码：4,320 tokens | $0.022 | 7 次调用
│  └─ 评审：3,326 tokens | $0.017 | 8 次调用
├─ 按模型：
│  ├─ deepseek-chat：10,240 tokens | $0.051 | 18 次调用
│  └─ deepseek-chat-lite（降级）：2,607 tokens | $0.013 | 5 次调用
├─ 预算：100,000 tokens | 已用 12.8% | 剩余 87,152 tokens
└─ 告警：0 条
```

## 5. 交付物清单

| 工件 | 位置 | 说明 |
|------|------|------|
| 成本控制模块 | `agent_hive/cost_control.py` | 核心实现 |
| 单元测试 | `tests/test_cost_control.py` | 覆盖估算/监控/降级全链路 |
| 集成测试 | `tests/test_cost_control_integration.py` | 与真实 run 流程集成验证 |
| 成本看板 | `docs/cost-dashboard-spec.md` | 成本数据的结构化输出格式 |
| 配置示例 | `.env.example` 补充 | 新增 `HIVE_MAX_TOKENS`、`HIVE_MAX_COST_USD`、`HIVE_DEGRADATION_MODEL` |

## 6. 验收标准

- [ ] 执行前估算 token 成本，超过预算时拒绝执行并给出明确提示
- [ ] 运行时实时追踪 token 消耗，per-role 和 per-model 分拆正确
- [ ] 预算接近上限（80%）时触发 warn 告警
- [ ] 预算超限时自动降级（换模型/截断 prompt/阻塞），不抛异常崩溃
- [ ] 降级后调用记录标记 `downgraded=True`，便于审计
- [ ] 多线程并发下计数器不丢失、不重复
- [ ] 最终看板输出结构化成本数据，可被下游工具消费
- [ ] 不设预算时（`max_tokens=0`）行为与现有代码一致（向后兼容）

## 7. 联动关系

| 联动卡片 | 关系 | 说明 |
|---------|------|------|
| card-model-resilience | 依赖 | 降级策略需要 model fallback 链提供备选模型 |
| card-distributed-engine | 消费 | 分布式引擎需要成本追踪器支持跨进程汇总 |
| card-async-hitl | 数据源 | 成本告警可作为异步审批的触发条件（"预算超限，是否继续？"） |

## 8. 实现效果

**改造前**：一个 agent run 可能消耗 100 万 token 后才被注意到，无任何预警机制。

**改造后**：每个 run 有明确的预算上限，超限自动降级不崩溃，成本数据实时可见，支持 per-role 成本归因分析。团队可以基于成本数据做 ROI 决策——"编码角色消耗了 60% 预算，但返工率 40%，是否应该优化编码 prompt？"