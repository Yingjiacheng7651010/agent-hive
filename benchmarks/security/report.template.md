# 安全验证基准报告（hive-security 规则引擎通道）

> 生成时间：{{generated_at}}（本行与「延迟」两行为环境相关字段；其余字段确定性可复现）

## 方法

- 基准脚本：`{{script}}`（`ValidationPolicy(llm_enabled=False)`，纯确定性规则引擎，不调用任何模型、无网络）
- 版本：hive-security {{hive_security_version}} / hive-cost {{hive_cost_version}} / agent-hive {{agent_hive_version}} / Python {{python_version}}
- 判定阈值（全部满足 → 基准退出码 0）：detection_rate ≥ 0.95 且 false_positive_rate ≤ 0.05 且 verdict_accuracy ≥ 0.95
- 判定规则：must_hit 全部命中才计检出；干净样例（无 must_hit）出现任何 finding 计误报；must_not_hit 被违反计误报

## 语料规模

- 总样例：{{total_samples}} = 手工样例 {{hand_written}} + 模板生成 {{generated}}（`tests/golden/generate_corpus.py` 确定性生成，序号变异、无 random）
- 家族分布：幻觉引用 20 / 循环依赖 10 / 缺失认证 10 / 缺失审计 10 / 命令执行无白名单 10 / 密钥·隐私·越权 15 / 执行无守卫降级 10 / 结构反模式 10 / 提示注入 dogfood 5 / 干净架构 15

## 结果

| 指标 | 值 |
|---|---|
| 达标样例 passed | {{passed}} / {{total_samples}} |
| 检出率 detection_rate | {{detection_rate}} |
| 误报率 false_positive_rate | {{false_positive_rate}} |
| verdict 准确率 | {{verdict_accuracy}} |
| 平均延迟 avg_latency_ms | {{avg_latency_ms}}（单机环境相关，见 meta） |
| P99 延迟 p99_latency_ms | {{p99_latency_ms}}（单机环境相关，见 meta） |

## 按家族

| 家族 | 达标/总数 |
|---|---|
{{families_table}}

## 未覆盖范围

- 仅测规则引擎通道：LLM 语义验证（`llm_enabled` 通道）不纳入本基准，不调用任何模型；
- 不对第三方产品（ASTRIDE / Agentic Radar / DeepSec 等）做未经授权实测，本报告不含任何第三方产品对比数据；
- 检出率/误报率与语料分布强相关：语料（`tests/golden/`）变更后必须重新生成并重跑本基准；
- 不覆盖 scope_auth / 动态代码执行 / 真实攻击面验证；延迟为单机测量值，跨机器不可比。
