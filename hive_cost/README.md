# hive-cost

成本控制与模型容错独立零依赖包：**纯标准库**（threading / time / dataclasses / json /
pathlib），不依赖 pydantic / langchain / opentelemetry SDK。事实源与 `agent-hive` 的
`cost_control` / `model_resilience` 同源：agent-hive 内部已改为薄壳引用本包。

模块：

- `hive_cost.budget` —— 成本预算原语（CostBudget / CostSnapshot / CostAlert /
  BudgetDecision / TokenEstimator / CostTracker / CostController / MODEL_PRICING）
- `hive_cost.resilience` —— 模型调用容错（RetryStrategy / CircuitBreaker /
  ModelFallbackRegistry / ResilientModelClient，`invoke_fn` seam 签名
  `fn(model, messages, tools) -> (response, error)`）
- `hive_cost.gate` —— `CostGate` 一等原语（检查 → 记录 → OTel 事件）
- `hive_cost.otel` —— `export_cost_otel_jsonl`（OTel 兼容 JSONL 导出）

## CostGate 30 秒上手

```python
from hive_cost.budget import CostBudget
from hive_cost.gate import CostGate

gate = CostGate(
    budget=CostBudget(max_tokens=100_000, warn_ratio=0.8,
                      per_agent_limits={"编码": 50_000}),
    degradation_chain=["deepseek-chat", "deepseek-chat-lite", "gpt-4o-mini"],
)

decision = gate.check_before_call("deepseek-chat", "编码")
if decision.action == "block":
    raise RuntimeError(decision.reason)          # 预算耗尽，拒绝调用
model = decision.fallback_model or "deepseek-chat"  # downgrade 时用便宜模型

# ... 实际调用模型 ...

gate.record_after_call(model, "编码", input_tokens=1200, output_tokens=300,
                       latency_ms=850.0)
snap = gate.snapshot()        # CostSnapshot：总量 / 按角色 / 按模型
alerts = gate.alerts()        # list[CostAlert]
events = gate.to_otel_events()  # OTel 兼容事件，可交给 export_cost_otel_jsonl
```

线程安全：`check_before_call` / `record_after_call` / `snapshot` 内部加锁，
10 线程 × 100 调用并发计数不丢失。

## OTel 事件字段表（`CostGate.to_otel_events` / JSONL 每行）

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | str | 固定 `"agent.model_call"` |
| `start_time_unix_nano` | int | 调用开始时间（纳秒，`end - latency_ms`） |
| `end_time_unix_nano` | int | 调用结束时间（纳秒，记录时刻） |
| `attributes.model` | str | 实际调用模型 |
| `attributes.role` | str | 调用角色（如「编码」「评审」） |
| `attributes.input_tokens` | int | 输入 token 数 |
| `attributes.output_tokens` | int | 输出 token 数 |
| `attributes.cost_usd` | float | 本次调用估算成本（USD，按 MODEL_PRICING） |
| `attributes.downgraded` | bool | 是否按降级决策执行 |
| `attributes.action` | str | `"proceed" \| "downgrade" \| "block"`（本次调用对应决策） |

`export_cost_otel_jsonl(path, events) -> int`：逐行 `json.dumps(..., ensure_ascii=False)`
写 UTF-8；父目录不存在自动创建；返回写入条数。**不做 OTLP 网络上报**（仅落盘 JSONL）。

## 检查范围 / 未覆盖范围

**覆盖**：预算估算与实时追踪、per-role/per-model 细分、超预算降级链（正常 → 换便宜模型
→ 减少输出 → 阻塞）、重试（指数退避+抖动）、熔断（closed → open → half-open）、
fallback 链、CostGate 检查/记录/事件导出。

**不覆盖**：不做 OTLP/HTTP 网络上报；不做面板/前端展示（`format_dashboard` 仅为文本辅助）；
不接入真实 LLM SDK（模型调用经 `invoke_fn` seam 注入）；tiktoken 精确计数（启发式估算，
可注册自定义 tokenizer）。
