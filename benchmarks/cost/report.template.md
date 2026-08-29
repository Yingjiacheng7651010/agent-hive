# 成本预算基准报告（hive-cost CostGate）

> 生成时间：{{generated_at}}

## 方法

- 合成轨迹：{{trace_tasks}} 个任务 × 每任务 3-20 次模型调用（共 {{total_calls}} 次调用、{{total_tokens}} tokens），
  模型在 `deepseek-chat` / `deepseek-chat-lite` 间按任务序号轮换，角色按 5 角色轮换；
- 轨迹生成器：`benchmarks/cost/trace_generator.py`（seed={{trace_seed}}，全部取值序号派生，**无 random**）；
- 三档预算跑 `CostGate`：宽松（无上限）/ 中等（总 token 上限 = 轨迹总量 70%）/ 严格（50%），`warn_ratio=0.8`；
- 完成率定义：被 block 前完成的调用占比；任务在首次 block 后停止，剩余调用不计入；
- 版本：hive-cost {{hive_cost_version}} / Python {{python_version}}；价格表为内置 `MODEL_PRICING` 静态数据。

## 三档对比

| 指标 | 宽松（无上限） | 中等（70%） | 严格（50%） |
|---|---|---|---|
| 完成率 | {{loose_completion_rate}} | {{medium_completion_rate}} | {{strict_completion_rate}} |
| 任务成本均值（USD） | {{loose_cost_mean}} | {{medium_cost_mean}} | {{strict_cost_mean}} |
| 任务成本方差 | {{loose_cost_variance}} | {{medium_cost_variance}} | {{strict_cost_variance}} |
| 降级次数 | {{loose_downgrade_count}} | {{medium_downgrade_count}} | {{strict_downgrade_count}} |
| block 次数 | {{loose_block_count}} | {{medium_block_count}} | {{strict_block_count}} |
| 告警数 | {{loose_alert_count}} | {{medium_alert_count}} | {{strict_alert_count}} |

## 结论

同一批任务，无预算 vs 严格预算：成本方差下降 {{var_drop_pct}}%，完成率 {{completion_strict_pct}}%（严格档；宽松档 {{completion_loose_pct}}%）。

## 未覆盖范围

- 仅覆盖 CostGate 规则通道（预算检查 / 降级链 / 阻断），不含真实模型调用成本（价格表为内置静态数据，不接入 LLM 计费 API）；
- 不包含多租户配额、动态定价、真实请求延迟分布；合成轨迹与真实 agent 负载的分布差异不在本基准内；
- 完成率为调用级定义（见「方法」），方差为按任务聚合的总体方差（`statistics.pvariance`）；
- 本基准的数字全部来自确定性规则计算，无 random、无虚构；轨迹生成参数（任务数/token 范围/预算比例）变更后需重新生成并重跑。
