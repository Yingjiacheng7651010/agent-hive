# LangGraph / LangChain Platform / LangSmith 竞争评估调研笔记

> 调研时间：2026 年 8 月（信息截至 2026-08，个别 2025 年事件含精确日期）
> 调研人：市场研究子代理（agent-hive 竞争评估项目）
> 标注口径：【事实】= 官方文档/官方博客/GitHub 仓库/官方定价页可查证；【推断】= 基于多方来源的合理推断；【未证实】= 未能找到权威来源或来源间冲突。
> 每条关键结论后附 `[来源: URL]` 与年份。

---

## 0. 口径与重要更正（先读）

1. **LangChain 的"State of AI Agents"报告实际公开于 2025 年 12 月**（调查窗口 2025-11-18 ~ 12-02，有效样本 1,340 份），官方页 `langchain.com/state-of-agent-engineering` 最后更新于 2025-12-16；第三方解读多称其为 "State of AI Agents 2025"。【事实】【来源: https://www.langchain.com/state-of-agent-engineering】2025
   - 任务书中的"2025 年 10 月发布"未获证实——官方报告方法论显示的调查时间为 11-12 月。2025 年 10 月（10-21~25 前后）LangChain 做的是 "Launch Week"（OSS 1.0 GA、Insights Agent、无代码 Agent Builder 等产品发布），不是报告发布。【事实】【来源: https://forum.langchain.com/t/we-launched-1-0-versions-of-langchain-and-langgraph/1904】2025
2. **"86% 的试点永远进不了生产 / 只有 14% 进入生产 / 78% 在做试点"这组数字出自 AI2 Incubator（艾伦人工智能研究所孵化器）的《State of AI Agents 2025》报告，不是 LangChain 的报告**。二者常被混淆，任务书要求的是 LangChain 一方的数据，本笔记两者都列但明确区分。【事实】【来源: https://agentmarketcap.ai/blog/2026/04/08/ai2-incubator-state-of-ai-agents-2025-deployment-reality】2026
3. LangGraph / LangChain / LangSmith 三者的产品边界 2025 年发生了重大改名：**LangGraph Platform 已于 2025 年 10 月更名为 "LangSmith Deployment"**，LangGraph Studio 更名为 LangSmith Studio；LangChain 公司把产品线统一到 LangSmith 品牌（Observability / Evaluation / Deployment 三大支柱）+ 开源框架（langchain、langgraph、deepagents）。【事实】【来源: https://www.langchain.com/blog/langgraph-platform-ga】2025（博客内注："As of October 2025, LangGraph Platform has been re-named to 'LangSmith Deployment'"）

---

## 1. LangGraph（开源库）与 LangGraph Platform（LangSmith Deployment，商业云/自托管）

### 定位
- **LangGraph（OSS 库）**：底层（low-level）agent 编排运行时，把 agent 定义为显式有状态图（节点/边/状态），内建 durable execution（checkpoint 持久化）、内存、流式输出与 human-in-the-loop，是 LangChain 官方"构建可靠 agent"的推荐层。【事实】【来源: https://www.langchain.com/blog/langchain-langgraph-1dot0】2025
- **LangGraph Platform（2025-10 起更名 LangSmith Deployment）**：托管部署与管理层，提供 1 键部署、30 个 API 端点、水平扩展、持久化层、异步任务队列、Agent Registry、RBAC 等"从开发到生产"的基础设施，含 Cloud / Hybrid / Self-Hosted 三种部署模式（控制面/数据面分离）。【事实】【来源: https://www.langchain.com/blog/langgraph-platform-ga】2025

### 编排模型
- 显式**图驱动**编排：StateGraph（状态、节点、边、条件边），支持循环（cycle）与 DAG；通过 `Send` API 做动态扇出（fan-out），`Command` API 在运行时更新状态/恢复；子图（subgraphs）嵌套；官方 supervisor 模式库 `langgraph-supervisor-py`（`create_supervisor`，分层多 agent 编排）。【事实】【来源: https://docs.langchain.com/oss/python/langgraph/ 系列；https://github.com/langchain-ai/langgraph-supervisor-py】2025-2026
- 注意：官方自 2025 年末起**推荐用"工具调用式 supervisor 模式"替代 supervisor 专用库**（更利于上下文工程）。【事实】【来源: https://github.com/langchain-ai/langgraph-supervisor-py/blob/main/README.md】2025
- 与 agent-hive 的对照价值：LangGraph 是"显式图 = 依赖感知调度"的执行模型，而非自动任务图/规划器；agent 间协作（multi-agent）官方提供 supervisor、swarm（pre-built）等模式。【事实】【来源: https://blog.langchain.com/interrupt-2025-recap/】2025

### 人机协同 HITL 方式
- 原生 `interrupt()` + checkpoint 机制：节点中断后状态持久化，之后用 `Command(resume=...)` 恢复执行；官方 human-in-the-loop 文档覆盖"审批/编辑/评论"等模式；配合 checkpoint 可做时间旅行（time travel）、回滚到任意点重放。【事实】【来源: https://docs.langchain.com/oss/python/langgraph/interrupts；https://docs.langchain.com/oss/python/langgraph/checkpointers】2025
- LangChain 1.0 提供预置 `HumanInTheLoopMiddleware`（敏感工具调用需审批，可 approve/edit/reject）。【事实】【来源: https://raw.githubusercontent.com/langchain-ai/docs/933a2f92/src/oss/python/releases/langchain-v1.mdx】2025
- Platform 层支持异步协作（agent 等待人在未来某个时刻回复/批准，状态保持）。【事实】【来源: https://www.langchain.com/blog/langgraph-platform-ga】2025

### 评估与守卫能力
- **评估**：OSS 库本身无评估器，评估在 LangSmith 完成（datasets/experiments/offline-online evals）。【事实】
- **守卫（guardrails）**：LangGraph 核心无内置 guardrail 引擎，官方提供组合式方案：LangChain middleware 的 `after_model` 钩子做输出校验/guardrail、prebuilt `ValidationNode`（工具参数校验）、官方示例仓库 `langchain-ai/langgraph-guardrails-example`；第三方框架 NVIDIA NeMo Guardrails 有**官方 LangGraph 集成文档**（docs.nvidia.com）；Lakera Guard 通过 langchain 集成（LakeraChainGuard）接入（第三方生态）。【事实】【来源: https://docs.nvidia.com/nemo/guardrails/integration-with-third-party-libraries/langchain/langgraph-integration；https://github.com/langchain-ai/langgraph-guardrails-example；https://reference.langchain.com/python/langgraph.prebuilt/tool_validator/ValidationNode】2025-2026

### 可观测性
- 官方可观测性 = LangSmith 原生集成（tracing、projects、threads、agent 专属指标）。OSS 侧无自带可观测服务。【事实】【来源: https://docs.langchain.com/langsmith/】2025

### 成本控制
- OSS 运行时无成本控制；成本能力在 LangSmith（cost tracking、告警、evaluator 花费上限）；Platform 按 LCU（LangChain Compute Unit）计费。【事实】【来源: https://docs.langchain.com/langsmith/cost-tracking；https://docs.langchain.com/langsmith/evaluator-spend】2025

### 许可证与生态
- **MIT 许可证**（LICENSE 文件，Copyright 2024 LangChain, Inc.）。【事实】【来源: https://github.com/langchain-ai/langgraph/blob/main/LICENSE】2026
- GitHub：`langchain-ai/langgraph` 约 **40.6k stars / 6.8k forks**（2026-08 抓取 GitHub 页面）。【事实】【来源: https://github.com/langchain-ai/langgraph】2026
- 生态地位：LangChain 生态整体下载量 **>7,000 万次/月（2025-05 口径，超过 OpenAI SDK 同期下载）**；LangChain 已发布 3 个稳定大版本（截至 2025-05）。【事实】【来源: https://blog.langchain.com/interrupt-2025-recap/】2025

### 2025-2026 关键动态
- 2025-05-14：**LangGraph Platform GA**（beta 期约 400 家公司试用；1 键部署、30 API 端点、Cloud/Hybrid/Self-Hosted）【事实】【来源: https://www.langchain.com/blog/langgraph-platform-ga】2025
- 2025-05：Interrupt 2025（LangChain 首届大会，旧金山，约 800 人参会；GA 发布、Open Agent Platform 无代码构建器、**LangGraph Studio v2**（本地运行、拉取 trace、把示例加入 eval 数据集、UI 内改 prompt）、Pre-Builts（Swarm/Supervisor 等预置架构）、LangSmith agent 指标、Open Evals 开源评估器目录、聊天模拟、LLM-as-Judge 校准（私有预览））【事实】【来源: https://blog.langchain.com/interrupt-2025-recap/】2025
- 2025-10-21~25：Launch Week——**LangChain 1.0 与 LangGraph 1.0 GA（2025-10-22，Python+TypeScript）**：稳定性优先、核心图 API 不变、API 稳定性承诺（2.0 前无破坏性变更，二手来源转述）；`create_react_agent` 弃用、迁移到 LangChain `create_agent`；所有文档统一到 docs.langchain.com。【事实】【来源: https://forum.langchain.com/t/we-launched-1-0-versions-of-langchain-and-langgraph/1904；https://raw.githubusercontent.com/langchain-ai/docs/933a2f92/src/oss/python/releases/langgraph-v1.mdx】2025
- 2025-10：LangGraph Platform 更名 LangSmith Deployment；Studio → LangSmith Studio。【事实】
- 2026：LangGraph 迭代至 1.2+（节点级 timeout 与节点级 error handler 需 langgraph ≥ 1.2）；官方文档新增完整 "Fault tolerance" 章节（retry_policy / timeout / 错误处理 / 优雅停机）。【事实】【来源: https://docs.langchain.com/oss/python/langgraph/fault-tolerance】2026
- 2026：Interrupt 2026 计划于秋季在纽约与伦敦举办。【事实】【来源: https://docs.langchain.com/（页头公告）】2026

---

## 2. LangChain（框架本体现状）与 LangSmith（可观测性/评估/提示词管理/成本）

### 定位
- **LangChain（框架）**：2025 年起定位明确转向"**agent 工具生态与集成层**"——官方口径 "The LangChain package today is mostly about giving companies model optionality"（多模型可选性、集成广度与深度）；1.0 用 `create_agent` 统一 agent 构建入口（内部跑在 LangGraph 上）。【事实】【来源: https://blog.langchain.com/interrupt-2025-recap/；https://raw.githubusercontent.com/langchain-ai/docs/933a2f92/src/oss/python/releases/langchain-v1.mdx】2025
- **LangSmith**：官方定位 "Agent Improvement Engine + Observability + Evaluation + Deployment" 的**平台产品**（观测、评估、Prompt 管理、成本追踪、LLM Gateway、沙箱、无代码 Agent Builder、Fleet 自托管）。【事实】【来源: https://www.langchain.com/blog/langsmith-llm-gateway-runtime-controls-for-production-agents】2025

### 编排模型
- LangChain 1.0 `create_agent` 基于 LangGraph 基本 agent 循环（模型→选工具→执行→结束），自带动 checkpoint、流式、HITL、回放；自定义编排仍下沉到 LangGraph 图。即：**LangChain = 高层封装，编排引擎 = LangGraph**。【事实】【来源: langchain-v1 release notes】2025

### 人机协同 HITL 方式
- `HumanInTheLoopMiddleware`（审批式）；底层同 LangGraph interrupt/checkpoint 机制。【事实】

### 评估与守卫能力
- LangSmith：datasets / experiments（离线评估）、在线评估（online evals）、LLM-as-judge（含 2025-05 起私有预览的"judge 校准与对齐"）、Open Evals 开源评估器目录（代码/抽取/RAG/agent 轨迹）、聊天模拟（多轮）。【事实】【来源: https://blog.langchain.com/interrupt-2025-recap/】2025
- 守卫：同第 1 节（middleware `after_model` 校验 + ValidationNode + 官方 guardrails 示例仓库 + NeMo 集成）。【事实】

### 可观测性
- LangSmith tracing：trace tree（token 与成本明细）、projects、threads、dashboards、agent 专属指标（工具调用/轨迹，2025-05 起）。【事实】【来源: https://docs.langchain.com/langsmith/；Interrupt 2025 recap】2025

### 成本控制
- LangSmith 自动记录主流模型 token 用量与成本（trace tree / project stats / dashboards 三处视图），支持自定义成本数据；支持成本告警（Alerts）与 evaluator 花费上限（spend limits）。【事实】【来源: https://docs.langchain.com/langsmith/cost-tracking；https://docs.langchain.com/langsmith/alerts；https://docs.langchain.com/langsmith/evaluator-spend】2025
- 组织级"预算（budget）"强制管控：**未证实为原生功能**（未见官方预算上限功能文档）。【未证实】

### 许可证与生态
- `langchain-ai/langchain`：MIT；约 **145.1k stars / 24.2k forks**（2026-08 抓取）。【事实】【来源: https://github.com/langchain-ai/langchain】2026
- 集成数量：历史长期宣传 700+ 集成，2026 年官方数字未核实。【未证实】【来源: https://github.com/langchain-ai/langchain（README）】2026
- 商业化：LangChain 公司 2025-10-20~21 宣布 **$125M B 轮（IVP 领投），估值 $1.25B（独角兽）**；总融资约 $150M+（B 轮前另有一轮）。【事实】【来源: https://fortune.com/2025/10/20/exclusive-early-ai-darling-langchain-is-now-a-unicorn-with-a-fresh-125-million-in-funding/；https://www.langchain.com/blog/series-b】2025

### 2025-2026 关键动态
- 2025-10-22：LangChain 1.0 GA（create_agent、middleware、content_blocks 统一多模型内容、legacy 移入 langchain-classic）。【事实】
- 2025-10：产品线统一为 LangSmith Platform（Observability / Evaluation / Deployment）；LangGraph Platform → LangSmith Deployment。【事实】
- 2025-11~12：State of Agent Engineering 调研（下节）。【事实】
- 2026 上半年：LangSmith Agent Builder（无代码）新增聊天、文件上传与 **tool registry（工具注册表）**（官方博客 Q1 2026）；另发布 dcode（编码 agent 产品）。【事实】【来源: https://www.langchain.com/blog/new-in-agent-builder-all-new-agent-chat-file-uploads-tool-registry】2026

---

## 3. LangChain《State of AI Agents》（官方页名 State of Agent Engineering）关键数字

> 官方报告页：https://www.langchain.com/state-of-agent-engineering （2025-12-16 更新）；调查 2025-11-18~12-02，N=1,340；行业分布：技术 63%、金融 10%、医疗 6%、教育 4%；公司规模 <100 人占 49%。【事实】【来源: 官方页（经 raw.githubusercontent 全文抓取 + 官方页）】2025

| 主题 | 数字 | 标注 |
|---|---|---|
| 生产落地 | **57.3% 已在生产运行 agent**（去年 51%，+6.3pp）；另有 30.4% 在开发且有部署计划 | 事实 |
| 规模化差异 | 万人以上组织 67% 生产（24% 开发中）；百人以下 50% 生产（36% 开发中） | 事实 |
| 生产最大障碍 | **质量 32%**（第一）；**延迟 20%**（第二）；成本担忧较去年下降 | 事实 |
| 企业（2k+ 人）障碍 | 质量第一，**安全 24.9%** 为第二障碍（超过延迟） | 事实 |
| 可观测性 | **89% 有某种可观测性，62% 有详细 tracing**；生产组织更高：94% / 71.5% | 事实 |
| 评估 | **离线 evals 52.4%，在线 evals 37.3%**；做评估的团队约 1/4 线上线下结合；不评估比例 29.5%（生产组织 22.8%） | 事实 |
| 评估方法 | 人工评审 59.8%、**LLM-as-judge 53.3%**、ROUGE/BLEU 采用有限 | 事实 |
| 模型格局 | **>2/3 用 OpenAI GPT 模型**；**>75% 多模型并用**（不押注单一供应商）；1/3 自托管/开源模型；57% 未微调（靠 prompt 工程 + RAG） | 事实 |
| 主要用例 | 客服 26.5%、研究与数据分析 24.4%、内部工作流自动化 18.0%（万人以上组织：内部生产力 26.8% 居首） | 事实 |
| OpenAI o 系列 / AI SDK 采用率 | 官方报告文本中未检索到明确分项数字 | 未证实 |
| 多智能体（multi-agent）采用率 | 官方报告文本中未见明确百分比 | 未证实 |
| 对比参照（非 LangChain 报告） | AI2 Incubator《State of AI Agents 2025》：78% 企业做试点、仅 14% 进生产、86% 试点未达生产 | 事实（另一份报告） |

---

## 4. 许可证与成本（定价）

### 许可证
- LangGraph OSS：**MIT**（LICENSE 文件实查）。【事实】2026
- LangChain OSS：**MIT**（GitHub 页面标注 "MIT license"）。【事实】2026

### LangGraph Platform / LangSmith Deployment 定价（第三方定价聚合 CostBench，2026-08 核实，注明"limited confidence / 1 source"）【事实（含置信度提示）】【来源: https://costbench.com/software/ai-agent-platforms/langgraph-platform/】2026
| 层级 | 定价 | 内容 |
|---|---|---|
| Developer（免费） | 免费 | 5k 基础 traces/月后用多少付多少；限 1 seat；Fleet 5 LCU/月；沙箱 5 LCU+1 LSU/月（上限 10 个）；LLM Gateway 按量；社区支持。自托管免费档另见"10 万节点执行/月"上限（二手转述官方博客口径）【推断】 |
| Plus | 未公开价（usage-based） | 10k traces/月后按量；**额外 seat $39/seat/月**；含 1 个免费 Serverless(Small) 部署；Fleet 25 LCU/月；引擎按 LCU 计费；LLM Gateway 控制；邮件支持 |
| Enterprise | 联系销售（定制） | Cloud/Hybrid/Self-Hosted；定制 SSO、ABAC、RBAC；SLA、培训、架构咨询；年付发票 |

- 隐藏成本提示：使用 Platform 需 LangSmith Plus 订阅（CostBench 提示为强制项）。【推断】
- 自托管：官方提供控制面（control plane）与数据面（data plane）两套自托管部署文档（Docker/Helm）。【事实】【来源: https://github.com/langchain-ai/langgraph 文档（self_hosted_control_plane / self_hosted_data_plane）】2025

### LangSmith 定价（官方支持文章 2025-10-02 + 官方定价页）【事实】【来源: https://support.langchain.com/articles/6889482332-how-am-i-charged-for-langsmith-plus-plan-and-where-can-i-view-my-billing-details；https://www.langchain.com/pricing】2025
- **Developer 计划：免费，前 5,000 traces/月**；超出按 pay-as-you-go 计费（官方示例：单月 25 万 traces 可产生 $100+ 费用——超出免费额度即按量收费）。
- **Plus 计划：$39/seat/月**（按比例计费）+ 按量（usage）费用；含更多 traces 额度与协作功能。
- **Enterprise：定制**（SSO/合规/SLA 等）。
- 第三方 2026 年对比文章口径一致：Free / Plus（$39/seat）/ Enterprise。【事实】【来源: https://pecollective.com/blog/langsmith-pricing/】2026

---

## 5. 企业级能力事实核查（逐项对照）

| 能力 | 结论 | 依据 |
|---|---|---|
| 依赖感知调度（图即 DAG/循环） | 【事实】LangGraph 以显式 StateGraph（节点/边/状态）为执行模型，支持条件边、循环、Send API 动态扇出、子图；Platform 提供异步任务队列与水平扩展。注意：非自动"任务图规划器"，依赖是开发者显式编码的 | docs.langchain.com（Graph API / Subgraphs / Send）；Platform GA 博客，2025 |
| HITL（interrupt + checkpoint 审批式） | 【事实】`interrupt()`/`Command(resume=...)` + checkpointer 持久化；时间旅行/回滚重放；LangChain `HumanInTheLoopMiddleware`（approve/edit/reject）；Platform 支持跨异步时间的审批 | docs（interrupts/checkpointers/time-travel）；langchain-v1 release notes，2025 |
| Guardrails | 【部分事实】无内置 guardrail 引擎；官方方案 = middleware `after_model` 输出校验 + `ValidationNode`（tool 参数校验）+ 官方示例仓库；与 NVIDIA NeMo Guardrails 有官方集成文档；Lakera 走第三方 langchain 集成。属"组合式/需自建"，非开箱即用 | NeMo 官方集成文档；guardrails-example 仓库；reference.langchain.com，2025-2026 |
| 可观测性 | 【事实】LangSmith 原生集成（trace/project/thread/dashboard/agent 指标/成本视图）；自托管观测用 LangSmith Fleet | docs.langchain.com/langsmith，2025-2026 |
| 成本控制 | 【部分事实】LangSmith 自动成本追踪 + 告警 + evaluator 花费上限；**组织级预算（budget）强制管控未证实** | docs（cost-tracking/alerts/evaluator-spend），2025 |
| 多租户 | 【部分事实】Platform/LangSmith Deployment 提供 workspaces、deployments、RBAC；Enterprise 级 ABAC/RBAC/SSO；每租户模型配置/BYOK 有官方论坛实践讨论；底层隔离模型细节未在公开文档中完整披露 | CostBench 定价页；forum.langchain.com（per-tenant BYOK），2025-2026 |
| 断点续跑 | 【事实】checkpointers 持久化 + 恢复 + "rewind, edit, rerun failure points"（Platform 内置）；graph 可从任意 checkpoint 恢复 | docs（checkpointers）；Platform GA 博客，2025 |
| Prompt 版本化 + A/B | 【部分事实】Prompt Hub 版本化（commit/webhook）、playground 调试、experiments 离线对比（近似 A/B）；**生产流量在线 A/B 分配未证实为原生功能** | docs（manage-prompts）；langsmith-cookbook，2025-2026 |
| 模型容错（retry/fallback） | 【事实（部分）】LangGraph 节点级 `retry_policy`（按异常类型/退避）、run/idle timeout、错误处理器（重试耗尽后执行恢复函数）、优雅停机；节点级 timeout 需 langgraph ≥ 1.2；fallback 需通过 LangChain `with_retry`/`with_fallbacks` 或 middleware 自行配置，非图内默认 | docs（fault-tolerance）；fault-tolerance-in-langgraph 博客，2025-2026 |
| 工具注册表 | 【未证实/部分】OSS 无内置工具注册表产品；LangSmith Agent Builder（无代码）2026 Q1 新增 tool registry；工具生态主要通过 MCP/集成包组织 | LangChain 博客（agent builder tool registry），2026 |
| 流式输出 | 【事实】`stream`/`astream` 多模式（values/updates/messages/custom）；Platform 流式 API；Studio v2 实时可视化 | docs（streaming）；Interrupt 2025 recap，2025 |

---

## 6. 来源列表（URL + 标题 + 年份）

### 官方（LangChain/LangGraph/LangSmith）
1. https://www.langchain.com/blog/langchain-langgraph-1dot0 — LangChain and LangGraph Agent Frameworks Reach v1.0 Milestones — 2025
2. https://www.langchain.com/blog/langgraph-platform-ga — LangGraph Platform is now Generally Available（含 2025-10 更名 LangSmith Deployment 说明）— 2025
3. https://www.langchain.com/blog/langchain-langchain-1-0-alpha-releases — LangChain & LangGraph 1.0 alpha releases — 2025
4. https://blog.langchain.com/interrupt-2025-recap/ — Recap of Interrupt 2025（GA、Studio v2、Pre-Builts、Open Evals、LLM-as-judge 校准等发布）— 2025
5. https://www.langchain.com/state-of-agent-engineering — State of Agent Engineering（LangChain 官方报告页）— 2025
6. https://raw.githubusercontent.com/langchain-ai/docs/933a2f92/src/oss/python/releases/langgraph-v1.mdx — What's new in LangGraph v1 — 2025
7. https://raw.githubusercontent.com/langchain-ai/docs/933a2f92/src/oss/python/releases/langchain-v1.mdx — What's new in LangChain v1 — 2025
8. https://docs.langchain.com/oss/python/langgraph/fault-tolerance — Fault tolerance（retry/timeout/error handler）— 2026
9. https://docs.langchain.com/oss/python/langgraph/interrupts — Interrupts — 2025
10. https://docs.langchain.com/oss/python/langgraph/checkpointers — Checkpointers — 2025
11. https://docs.langchain.com/oss/python/langgraph/streaming — Streaming — 2025
12. https://docs.langchain.com/langsmith/cost-tracking — Cost tracking — 2025
13. https://docs.langchain.com/langsmith/alerts — Alerts in LangSmith — 2025
14. https://docs.langchain.com/langsmith/evaluator-spend — Track and limit evaluator spend — 2025
15. https://docs.langchain.com/langsmith/manage-prompts — Manage prompts — 2025
16. https://support.langchain.com/articles/6889482332-how-am-i-charged-for-langsmith-plus-plan-and-where-can-i-view-my-billing-details — LangSmith Plus 计费（$39/seat、5k traces 免费额度）— 2025
17. https://www.langchain.com/pricing — LangSmith Plans and Pricing — 2025-2026
18. https://www.langchain.com/blog/series-b — LangChain raises $125M（B 轮）— 2025
19. https://www.langchain.com/blog/langsmith-llm-gateway-runtime-controls-for-production-agents — LangSmith LLM Gateway — 2025
20. https://www.langchain.com/blog/new-in-agent-builder-all-new-agent-chat-file-uploads-tool-registry — Agent Builder tool registry — 2026
21. https://forum.langchain.com/t/we-launched-1-0-versions-of-langchain-and-langgraph/1904 — 1.0 GA 公告（2025-10-22）— 2025
22. https://reference.langchain.com/python/langgraph.prebuilt/tool_validator/ValidationNode — ValidationNode — 2025

### 代码仓库
23. https://github.com/langchain-ai/langgraph — MIT LICENSE、40.6k stars（2026-08 抓取）— 2026
24. https://github.com/langchain-ai/langchain — MIT、145.1k stars（2026-08 抓取）— 2026
25. https://github.com/langchain-ai/langgraph-supervisor-py — 官方 supervisor 库 README（推荐工具调用式模式）— 2025
26. https://github.com/langchain-ai/langgraph-guardrails-example — 官方 guardrails 示例 — 2025
27. https://docs.nvidia.com/nemo/guardrails/integration-with-third-party-libraries/langchain/langgraph-integration — NVIDIA NeMo Guardrails × LangGraph 官方集成 — 2025

### 关键第三方（交叉验证/补充数字）
28. https://www.truefoundry.com/de/blog/langgraph-pricing — LangGraph Pricing: A Complete Breakdown for 2026 — 2026
29. https://costbench.com/software/ai-agent-platforms/langgraph-platform/ — LangGraph Platform Pricing 2026（Developer/Plus/Enterprise）— 2026
30. https://pecollective.com/blog/langsmith-pricing/ — LangSmith Pricing 2026（Free/Plus $39/Enterprise）— 2026
31. https://0h-n0.github.io/posts/blog-langchain-state-of-agents-2025/ — 调查报告解读（N=1,340、2025-11-18~12-02、57.3% 等数字复核）— 2026
32. https://0h-n0.github.io/posts/techblog-langgraph-platform-ga/ — LangGraph Platform GA 解读（2025-05-14、40 家→400 家 beta、三种部署模式、免费档 10 万节点执行/月）— 2026
33. https://dev.to/jangwook_kim_e31e7291ad98/langgraph-platform-ga-studio-v2-one-click-deploy-guide-4m10 — LangGraph 1.0（2025-10）与 Platform/LangSmith Deployment 命名梳理 — 2026
34. https://agentmarketcap.ai/blog/2026/04/08/ai2-incubator-state-of-ai-agents-2025-deployment-reality — AI2 Incubator《State of AI Agents 2025》86%/14% 数字（区分于 LangChain 报告）— 2026
35. https://fortune.com/2025/10/20/exclusive-early-ai-darling-langchain-is-now-a-unicorn-with-a-fresh-125-million-in-funding/ — Fortune：LangChain $125M B 轮、$1.25B 估值 — 2025
36. https://lawrencewu.net/posts/2025-05-13-andrew-ng-harrison-chase-fireside-chat/ — Interrupt 2025 时间锚点（2025-05-13 炉边对话记录）— 2025

---

## 附：给竞争评估报告的 5 条最值得引用的数字
1. LangGraph 1.0 / LangChain 1.0 于 2025-10-22 GA；LangGraph Platform 于 2025-05-14 GA、2025-10 更名 LangSmith Deployment。【事实】
2. LangGraph OSS 为 MIT 协议、约 40.6k stars；LangChain 约 145.1k stars；LangChain 下载量超 7,000 万/月（2025-05，超过 OpenAI SDK）。【事实】
3. LangChain《State of Agent Engineering》：57.3% 已生产、89% 可观测性、52.4% 离线评估、质量 32% 为第一障碍、延迟 20% 第二、>75% 多模型并用、>2/3 用 OpenAI。【事实】（注意：86%/14% 生产差距出自 AI2 Incubator 另一报告）
4. LangSmith：免费 5k traces/月，Plus $39/seat/月 + 按量；LangGraph Platform：Developer 免费 / Plus $39/seat + LCU 按量 / Enterprise 定制（SSO/ABAC/RBAC/SLA）。【事实】
5. LangChain 公司 2025-10 完成 $125M B 轮（IVP 领投），估值 $1.25B。【事实】
