# 工作卡片：card-model-resilience —— 模型调用容错

> 优先级：P0.5 | 类型：可靠性 | 依赖：无
> 负责人：系统架构师 / 后端工程 | 轮次上限：3

---

## 1. 问题陈述

当前代码中模型调用直接调用 `create_agent().invoke()`，没有任何容错机制。如果 deepseek-chat API 返回 429（限流）、503（服务不可用）、或超时，整个 agent run 直接崩溃。在字节生产环境，线上模型 API 的 p99 延迟抖动和间歇性故障是常态，没有容错的 agent 框架无法上线。

## 2. 目标

建立多层次的模型调用容错机制：retry + exponential backoff → circuit breaker → fallback 链，确保任何单点模型故障不会导致整个 agent run 失败。

## 3. 接口契约

### 3.1 核心数据结构

```python
# agent_hive/model_resilience.py

@dataclass
class ModelFallbackConfig:
    """模型 fallback 链配置。"""
    primary: str                        # 主模型，如 "deepseek-chat"
    fallbacks: list[str]               # 备选模型列表，按优先级排列
    timeout_ms: int = 60000            # 单次调用超时
    max_retries: int = 3               # 最大重试次数
    base_delay_ms: float = 1000.0      # 指数退避初始延迟
    max_delay_ms: float = 30000.0      # 最大延迟上限

@dataclass
class CircuitBreakerState:
    """熔断器状态。"""
    name: str                          # 熔断器名称（按模型+端点）
    state: Literal["closed", "open", "half-open"]
    failure_count: int = 0
    last_failure_time: float = 0.0
    failure_threshold: int = 5         # 连续失败次数阈值
    recovery_timeout_ms: int = 30000   # 半开状态等待时间

@dataclass
class ModelCallResult:
    """模型调用结果（成功或失败，含 fallback 链路追踪）。"""
    success: bool
    response: str | None
    model_used: str
    total_latency_ms: float
    retry_count: int
    fallback_chain: list[str]          # 尝试过的模型列表
    error: str | None = None
```

### 3.2 核心接口

```python
class ResilientModelClient:
    """带容错的模型客户端：retry + circuit breaker + fallback。"""

    def __init__(self, config: ModelFallbackConfig):
        ...

    async def invoke(
        self,
        messages: list,
        tools: list | None = None,
        budget_decision: BudgetDecision | None = None,
    ) -> ModelCallResult:
        """带容错的模型调用。

        执行流程：
        1. 检查 circuit breaker → open 则直接降级
        2. 尝试 primary 模型（带 retry + exponential backoff）
        3. 主模型失败 → 沿 fallback 链依次尝试
        4. 全部失败 → 返回失败结果（含所有尝试链路）
        """

    def record_failure(self, model: str, error: str):
        """记录一次失败，更新 circuit breaker 状态。"""

    def record_success(self, model: str):
        """记录一次成功，复位 circuit breaker。"""

    def circuit_state(self) -> dict[str, CircuitBreakerState]:
        """返回所有熔断器状态。"""


class ModelFallbackRegistry:
    """模型 fallback 链注册表，支持动态配置。"""

    @classmethod
    def default_config(cls) -> ModelFallbackConfig:
        """返回默认配置（deepseek-chat → deepseek-chat-lite → gpt-4o-mini）。"""

    @classmethod
    def from_env(cls) -> ModelFallbackConfig:
        """从环境变量读取配置：HIVE_MODEL_PRIMARY / HIVE_MODEL_FALLBACKS。
        格式: HIVE_MODEL_FALLBACKS="model1,model2,model3"
        """
```

## 4. 实现方案

### 4.1 Retry 策略（RetryStrategy）

```
指数退避 + 抖动（jitter）：
  第 1 次重试：等待 base_delay(1s) ± 随机 20% 抖动
  第 2 次重试：等待 base_delay×2(2s) ± 抖动
  第 3 次重试：等待 base_delay×4(4s) ± 抖动
  最多 3 次重试，总计等待不超过 30s

可重试的异常：
  - 429 Too Many Requests（限流）
  - 503 Service Unavailable（服务不可用）
  - 502 Bad Gateway（网关错误）
  - 504 Gateway Timeout（网关超时）
  - 连接超时 / 读取超时

不可重试的异常（直接抛 fallback）：
  - 400 Bad Request（请求格式错误）
  - 401 Unauthorized（密钥无效）
  - 403 Forbidden（无权限）
  - 400 ContextLengthExceeded（上下文超长，需降级到长上下文模型）
```

### 4.2 熔断器策略（CircuitBreaker）

```
closed（正常）→ 连续 5 次失败 → open（断开）
open（断开）→ 等待 30s → half-open（半开）
half-open（半开）→ 1 次成功 → closed（恢复）
half-open（半开）→ 1 次失败 → open（再次断开，等待时间翻倍）
```

### 4.3 Fallback 链策略

```
尝试顺序：primary → fallback[0] → fallback[1] → ...
每个 fallback 也有自己的 retry + circuit breaker（独立计数器）
fallback 链的每个节点独立熔断，不互相影响
```

### 4.4 集成到现有流程

```python
# 在 chief.py / specialists.py 中替换直接调用：
# 旧：agent.invoke(messages)
# 新：
client = ResilientModelClient(config)
result = client.invoke(messages)
if not result.success:
    # 写入 board 告警，计入成本，继续流程而不是崩溃
    board.add_alert(f"模型调用失败：{result.error}")
    return {"error": result.error, "fallback_chain": result.fallback_chain}
```

## 5. 交付物清单

| 工件 | 位置 | 说明 |
|------|------|------|
| 容错模型客户端 | `agent_hive/model_resilience.py` | retry + circuit breaker + fallback 实现 |
| 单元测试 | `tests/test_model_resilience.py` | 覆盖 retry/熔断/fallback 全链路 |
| 集成测试 | `tests/test_model_resilience_integration.py` | 模拟 API 故障验证端到端容错 |
| 配置示例 | `.env.example` 补充 | `HIVE_MODEL_PRIMARY`、`HIVE_MODEL_FALLBACKS`、`HIVE_MODEL_TIMEOUT_MS` |

## 6. 验收标准

- [ ] 主模型 429 时自动重试最多 3 次，指数退避+抖动，重试间有时延变化
- [ ] 主模型连续 5 次失败后熔断器打开，后续请求直接走 fallback 模型
- [ ] 熔断器 30s 后自动进入 half-open，成功一次恢复，失败一次重置
- [ ] fallback 链按优先级依次尝试，前一个失败自动切到下一个
- [ ] 所有模型都失败时返回失败结果，不抛异常崩溃整个 run
- [ ] 成功/失败记录写入结构化日志，包含 `model_used`、`retry_count`、`fallback_chain`
- [ ] 每个模型/端点的熔断器状态独立，互不影响
- [ ] 不可重试的异常（400/401）直接抛 fallback，不浪费重试次数
- [ ] 默认配置从环境变量读取，可零配置运行（有合理的默认值）

## 7. 联动关系

| 联动卡片 | 关系 | 说明 |
|---------|------|------|
| card-cost-control | 消费 | fallback 链的模型选择受成本控制器影响（预算不足时从 fallback[0] 开始） |
| card-distributed-engine | 数据源 | 熔断器状态需要在分布式引擎中各节点共享（Redis 存储） |
| card-streaming | 配合 | stream 模式下的容错需要特殊处理（已发送的部分内容需缓存，fallback 后重发） |

## 8. 实现效果

**改造前**：模型 API 抖动 → 整个 agent run 异常退出 → 用户重跑 → 浪费 token 和时间。

**改造后**：模型 API 抖动 → 自动重试（对用户透明）→ 连续失败 → 自动切到备选模型 → 用户感知为"响应稍慢"而非"系统崩溃"。p99 可用性从 95% 提升到 99.9%。