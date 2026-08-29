# 竞争评估调研：Pydantic AI / AWS Bedrock AgentCore / 扣子 Coze（含 Dify、Qwen-Agent）

> 调研时间：2026 年 8 月。依据：官方文档、官方博客、GitHub、AWS 官方页面、权威媒体报道（web_search 一手/准一手来源）。
> 标注约定：【事实】有来源支撑的陈述；【推断】基于事实的合理推论，无直接来源；【未证实】检索未获权威来源，需进一步核实。
> 所有关键结论后附 `[来源: URL]` 与年份。

---

## 1. Pydantic AI（pydantic/pydantic-ai）

### 定位
- 【事实】Pydantic 团队（pydantic 校验库/ FastAPI 生态同一社区）出品的 **类型安全 Python agent 框架**：以 Pydantic 模型作为 LLM 输入输出契约，模型即 schema，输出自动校验/重试（structured outputs），官方卖点是 "Type-safe Python framework for building AI agents"。2026-04 第三方分析称其为"重写 Python agent 栈的类型安全框架"。[来源: https://pydantic.dev/docs/ai/ (2025-2026)；https://agentmarketcap.ai/blog/2026/04/06/pydanticai-python-agent-framework-langgraph-crewai-comparison (2026-04)]
- 【事实】2024 年 12 月前后正式对外（InfoQ 报道 "PydanticAI: a New Python Framework for Streamlined Generative AI Development"）。[来源: https://www.infoq.com/news/2024/12/pydanticai-framework-gen-ai/ (2024-12)]
- 【推断】2025 年"大火"与 LangChain/LangGraph 的"重抽象"形成反差，走轻量 + 类型安全 + FastAPI 工程文化路线；Pydantic 是 FastAPI 的数据校验基石，Pydantic AI 顺理成章承接 Python 服务端生态。

### 版本时间线（2025-2026）
- 【事实】**Graph API（pydantic-graph，DAG 编排）**：2025 年 5 月前后加入（任务书口径 2025-05）；官方文档有 Graphs 章节、独立文档站 graph.pydantic-ai.pages.dev。[来源: https://ai.pydantic.dev/graph/ (2025-2026)；https://graph.pydantic-ai.pages.dev/graph/ (2025)]
- 【事实】**v1.0 于 2025 年 9 月发布**：官方 changelog/升级指南明确 "In September 2025, Pydantic AI reached V1"，并承诺 API 稳定性。[来源: https://raw.githubusercontent.com/pydantic/pydantic-ai/f4154dfb0104085038b57e1742370595cc59ef20/docs/changelog.md (2025-09)]
- 【事实】2026 年进入 v2 世代：v1.96.0（2026-05-13）→ v2（官方文章 "Pydantic AI v2: capabilities, a leaner core, and the Harness"，pydantic-graph beta API 转正、核心精简）→ v2.34.0（2026-08-24）。[来源: https://github.com/pydantic/pydantic-ai/releases/tag/v1.96.0 (2026-05)；https://pydantic.dev/articles/pydantic-ai-v2 (2026)；https://github.com/pydantic/pydantic-ai/releases/tag/v2.34.0 (2026-08)；https://mcp.directory/blog/pydantic-ai-v2-harness-2026 (2026)]
- 【事实】`pip install pydantic-ai` 现默认安装 slim 核心 + openai/anthropic/google/cli/mcp/evals 等扩展（v2 起安装模型变化）。[来源: https://github.com/pydantic/pydantic-ai/commit/6001a4549018ad5509f2c11ed6c38d2385159506 (2026)]
- 【未证实】v0.x→v1.0 的具体里程碑日期表（仅确认 2025-09 达 v1）。

### Agent 类 / tools / deps
- 【事实】核心抽象 `Agent`；支持 tools（含 deferred tools 延迟注册）、dependency injection（deps）、结构化输出、streaming、MCP 工具接入。[来源: https://pydantic.dev/docs/ai/ (2025-2026)]

### HITL（人工介入）
- 【事实】官方提供 AG-UI（Agent User Interaction）示例，支持外部前端与 agent 交互；GitHub issue #3274 "Human in the Loop Approval for Multi Agent Systems"（2026 仍在讨论）。[来源: https://pydantic.dev/docs/ai/examples/ag-ui/ (2026)；https://github.com/pydantic/pydantic-ai/issues/3274 (2026)]
- 【推断】v1/v2 无统一 first-class 人工审批原语，HITL 通常以"中断/恢复 + 外部 UI（AG-UI）"或 Graph 节点的外部介入实现。
- 【未证实】官方是否已发布标准 human-approval API。

### 守卫与评估
- 【事实】**pydantic-ai evals**：仓库文档 docs/evals.md 覆盖 LLM-as-judge、对比评测、回归测试；官方文章 "LLM-as-a-Judge: A Practical Guide with Pydantic Evals"。[来源: https://github.com/pydantic/pydantic-ai/blob/main/docs/evals.md (2025-2026)；https://pydantic.dev/articles/llm-as-a-judge (2025-2026)]
- 【事实】类型校验本身构成"守卫"：输出不符合 Pydantic 模型即报错/重试（validate 机制）。

### 可观测性
- 【事实】与 **Pydantic Logfire** 深度集成（官方文档 logfire.md "Pydantic Logfire Debugging and Monitoring"），提供 tracing/调试/监控。[来源: https://github.com/pydantic/pydantic-ai/blob/main/docs/logfire.md (2025-2026)；https://pydantic.dev/docs/ai/ (2025-2026)]
- 【推断】可观测性绑定自家 Logfire，自研编排框架若需对位，需提供等效的 trace/监控方案。

### 成本控制
- 【未证实】官方文档未见显著 token 预算/成本上限原语。
- 【推断】成本控制依赖模型侧配额、外部监控与自研层；这对"成本控制"对标项是缺口。

### 许可证与生态
- 【事实】**MIT 许可证**开源（GitHub 仓库与 PyPI 包元数据一致），商用友好。[来源: https://github.com/pydantic/pydantic-ai (2024-2026)；https://security.snyk.io/package/pip/pydantic-ai (2025-2026)]
- 【事实】生态热度：2026-05 第三方 GitHub 榜单列为增长最快的 agent 框架之一；Thoughtworks Technology Radar 收录。[来源: https://presenc.ai/research/ai-agent-framework-github-rankings-2026 (2026-05)；https://www.thoughtworks.com/en-br/radar/languages-and-frameworks/pydantic-ai (2026)]
- 【未证实】2026-08 精确 star 数（未取一手数据；公开报道约 4 万+ 量级）。

### 2025-2026 关键动态
- 2025-05：Graph API / pydantic-graph（DAG 编排）。
- 2025-09：v1.0，承诺 API 稳定。
- 2026 年中：v2——精简核心、Graph API 转正、引入 Harness。
- 2026-08：v2.34.0，仍处于高速迭代期（约每月数个 minor 版本）。

### 来源列表（Pydantic AI）
- Pydantic AI 官方文档（Agent/tools/deps/Graph/AG-UI）：https://pydantic.dev/docs/ai/ （2025-2026）
- Pydantic AI v1 官方文章：https://pydantic.dev/articles/pydantic-ai-v1 （2025-09）
- Pydantic AI v2 官方文章：https://pydantic.dev/articles/pydantic-ai-v2 （2026）
- LLM-as-a-Judge 官方文章：https://pydantic.dev/articles/llm-as-a-judge （2025-2026）
- Graph 文档站：https://graph.pydantic-ai.pages.dev/graph/ （2025）
- GitHub 仓库/Releases：https://github.com/pydantic/pydantic-ai （2024-2026，v1.96.0 2026-05、v2.34.0 2026-08）
- 官方 changelog/升级指南：https://raw.githubusercontent.com/pydantic/pydantic-ai/f4154dfb0104085038b57e1742370595cc59ef20/docs/changelog.md （2025-09）
- InfoQ 发布报道：https://www.infoq.com/news/2024/12/pydanticai-framework-gen-ai/ （2024-12）
- Presenc AI 框架排行：https://presenc.ai/research/ai-agent-framework-github-rankings-2026 （2026-05）
- AgentMarketCap v1 分析：https://agentmarketcap.ai/blog/2026/04/06/pydanticai-python-agent-framework-langgraph-crewai-comparison （2026-04）

---

## 2. AWS Bedrock AgentCore

### 定位
- 【事实】AWS 托管的 **agent 运行时**：在 Bedrock 内统一管理 agent 状态（state management）、动作组（action groups/工具）、记忆（memory）、guardrails、策略（policy）与可观测性，官方表述 "Securely deploy and operate AI agents at scale"；可与开源框架（LangGraph 等）互操作，把外部框架构建的 agent 部署到 AgentCore 托管运行。[来源: https://venturebeat.com/ai/aws-unveils-bedrock-agentcore-a-new-platform-for-building-enterprise-ai-agents-with-open-source-frameworks-and-tools (2024-12)；https://aws.amazon.com/bedrock/agentcore/ (2025-2026)]
- 【推断】定位类似"AI agent 的运行时/控制面（K8s 之于容器）"，与自研编排框架（如 LangGraph）互补而非替代；框架负责编排逻辑，AgentCore 负责托管、状态、安全与运维。

### 发布时间线
- 【事实】2024-12 re:Invent **预览（preview）发布**（VentureBeat 报道）。[来源: https://venturebeat.com/ai/aws-unveils-bedrock-agentcore-a-new-platform-for-building-enterprise-ai-agents-with-open-source-frameworks-and-tools (2024-12)]
- 【事实】**2025-10 正式 GA（generally available）**：AWS what's-new "Amazon Bedrock AgentCore の一般提供を開始"（2025/10），**东京区域同步可用**。[来源: https://aws.amazon.com/jp/about-aws/whats-new/2025/10/amazon-bedrock-agentcore-available/ (2025-10)；https://ascii.jp/elem/000/004/329/4329896/ (2025-10)]
- 【事实】2025-10 发布官方 **MCP server**（awslabs.amazon-bedrock-agentcore-mcp-server）加速开发。[来源: https://aihub.hkuspace.hku.hk/2025/10/03/accelerate-development-with-the-amazon-bedrock-agentcore-mcp-server/ (2025-10)；https://pypi.org/project/awslabs.amazon-bedrock-agentcore-mcp-server/ (2025)]
- 【事实】2026-06：AWS Step Functions 新增由 AgentCore 驱动的 agentic reasoning step。[来源: https://aws.amazon.com/about-aws/whats-new/2026/06/aws-step-functions-agentcore/ (2026-06)]
- 【事实】2026-08：**多 agent 协作获得 persistent compute**（常驻运行时实例）——InfoQ 报道。[来源: https://www.infoq.com/news/2026/08/aws-bedrock-agentcore-runtime/ (2026-08)]

### 能力
- 【事实】能力覆盖：state management（会话/agent 状态管理）、action groups（工具调用）、memory（记忆）、guardrails 集成、policy 服务（release notes 称 Gateway/Policy 服务在已开通区域全部 AZ 可用）、observability 配置（CDK/Terraform 可配 CloudWatch/ADOT tracing）、cross-region 部署。[来源: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/release-notes.html (2025-2026)；https://github.com/aws/aws-cdk/pull/36689 (2025)；https://github.com/uday-bala/-bedrock-agentcore-observability (2026)]
- 【事实】**AgentCore vs Bedrock Agents**：Bedrock Agents 是 AWS 内置 agent 构建器（偏低代码、平台内建）；AgentCore 是更底层的托管运行时，可承载 Bedrock Agents 与外部框架 agent；官方 re:Post 问答与社区讨论对两者差异有专门条目。[来源: https://repost.aws/questions/QUjkf4WbikQ6WrpuH9sppjnw/bedrock-agents-vs-bedrock-agentcore (2025)]
- 【事实】**multi-agent collaboration**：AWS 官方示例仓库 aws-samples/sample-multi-agent-on-agentcore；2026-08 起多 agent 协作支持 persistent compute 常驻运行时。[来源: https://github.com/aws-samples/sample-multi-agent-on-agentcore (2025-2026)；https://www.infoq.com/news/2026/08/aws-bedrock-agentcore-runtime/ (2026-08)]
- 【推断/报道】2026 年 Bedrock Agents 与 AgentCore 进一步整合（第三方文章称 "what changed with AgentCore"）；具体整合关系未核实官方原文。【未证实】

### HITL（人工介入）
- 【事实】AWS 提供 sample-human-in-the-loop-patterns 示例仓库；业界通行做法是先用 LangGraph 等外部框架实现 HITL，再部署到 AgentCore 托管。[来源: https://github.com/aws-samples/sample-human-in-the-loop-patterns (2025-2026)；https://agentswarms.fyi/blog/hitl-langgraph-bedrock-agentcore (2025-2026)]
- 【未证实】AgentCore 本身是否提供 first-class 人工审批/回调原语（未检索到官方统一 API；疑似依赖 guardrails/外部编排实现）。

### 可观测性
- 【事实】支持 CloudWatch 指标/日志与 X-Ray/ADOT tracing（Runtime 可配 observability），社区有完整 CDK/Terraform 可观测性方案。[来源: https://github.com/aws/aws-cdk/pull/36689 (2025)；https://github.com/uday-bala/-bedrock-agentcore-observability (2026)；https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/release-notes.html (2025-2026)]

### 成本控制
- 【事实】AWS 官方定价页存在，按用量（调用）计费，非固定订阅。[来源: https://aws.amazon.com/bedrock/agentcore/pricing/ (2025-2026)]
- 【未证实】具体单价与计价维度细节（第三方 cloudburn.io 有"12 组件"拆解，但未与官方价格逐一核对）。[来源: https://cloudburn.io/blog/amazon-bedrock-agentcore-pricing (2025-2026)]
- 【推断】按调用（per-invocation）+ 状态/记忆存储组合计费；2026-08 新增 persistent compute（常驻计算）后成本结构将变化（具体计费【未证实】）。

### 多租户与合规
- 【事实】AWS 托管商业服务：region 化部署（含东京）、IAM/Policy 治理、AWS 企业级合规背书。[来源: https://aws.amazon.com/bedrock/agentcore/ (2025-2026)；https://ascii.jp/elem/000/004/329/4329896/ (2025-10)]
- 【事实】AWS 对 Bedrock 系列的标准承诺：不将客户数据用于训练底层模型（通用承诺层面）。[来源: AWS Bedrock 文档/页面 (2024-2026)]
- 【未证实】AgentCore 专属数据驻留/合规白皮书细节（GA 后是否有专属 SOC/ISO 文档未检索到）。

### 许可证 / 商业
- 【事实】AWS 商业托管服务（非开源），按 AWS 账号随用随付；生态配套有 aws-samples 与 starter toolkit（Apache 风格示例代码，非产品本体）。[来源: https://aws.amazon.com/bedrock/agentcore/pricing/ (2025-2026)；https://aws.github.io/bedrock-agentcore-starter-toolkit/ (2025-2026)]

### 2025-2026 关键动态
- 2024-12：re:Invent 预览发布。
- 2025-10：GA（含东京区域）+ 官方 MCP server。
- 2026-06：Step Functions 集成 agentic reasoning（AgentCore 驱动）。
- 2026-08：多 agent 协作 persistent compute（常驻运行时）。

### 来源列表（Bedrock AgentCore）
- AWS 产品页：https://aws.amazon.com/bedrock/agentcore/ （2025-2026）
- AWS 定价页：https://aws.amazon.com/bedrock/agentcore/pricing/ （2025-2026）
- AWS what's-new（GA，2025-10）：https://aws.amazon.com/jp/about-aws/whats-new/2025/10/amazon-bedrock-agentcore-available/ （2025-10）
- AWS 开发者指南 release notes：https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/release-notes.html （2025-2026）
- VentureBeat 预览发布报道：https://venturebeat.com/ai/aws-unveils-bedrock-agentcore-a-new-platform-for-building-enterprise-ai-agents-with-open-source-frameworks-and-tools （2024-12）
- InfoQ persistent compute：https://www.infoq.com/news/2026/08/aws-bedrock-agentcore-runtime/ （2026-08）
- AWS Step Functions what's-new：https://aws.amazon.com/about-aws/whats-new/2026/06/aws-step-functions-agentcore/ （2026-06）
- re:Post Agents vs AgentCore：https://repost.aws/questions/QUjkf4WbikQ6WrpuH9sppjnw/bedrock-agents-vs-bedrock-agentcore （2025）
- aws-samples 多 agent 示例：https://github.com/aws-samples/sample-multi-agent-on-agentcore （2025-2026）
- aws-samples HITL 示例：https://github.com/aws-samples/sample-human-in-the-loop-patterns （2025-2026）
- 东京区域 GA（ascii.jp）：https://ascii.jp/elem/000/004/329/4329896/ （2025-10）
- cloudburn 定价拆解（二手）：https://cloudburn.io/blog/amazon-bedrock-agentcore-pricing （2025-2026）

---

## 3. 扣子 Coze（字节跳动）

### 定位
- 【事实】字节跳动旗下"一站式 AI 开发平台"/AI Agent 平台：低代码/无代码构建 bot、智能体与工作流；**国内版扣子（coze.cn，火山引擎体系）+ 国际版 coze.com** 双版本。[来源: http://www.163.com/dy/article/IQ2C2K190511B8LM.html (2023-2024)；https://baike.baidu.com/item/Coze%E6%89%A3%E5%AD%90/65707499 (2025)]
- 【事实】2023-12 国际版上线时主打"30 秒无代码生成 AI 机器人"。[来源: https://m.ithome.com/html/748811.htm (2023-12)]
- 【未证实】国内版"扣子"的确切上线日期（约 2024 年初，未取得官方一手公告）。
- 【事实】2025-08 与小米应用商店达成合作，打通智能体一键发布能力。[来源: https://news.hexun.com/2025-08-01/220695990.html (2025-08-01)]

### 编排模型
- 【事实】核心编排：**可视化工作流（workflow，DAG 节点图）+ 单 agent 会话（对话式）**；节点含插件/工具、知识库（RAG）、数据库、定时任务、多模型切换等；有社区/官方标准开发流程文档。[来源: https://docs.coze.cn (2024-2026)；https://developer.aliyun.com/article/1724307 (2025)]
- 【推断】编排模型是"工作流 DAG + 单 agent 会话"组合：比纯代码编排（LangGraph/Pydantic AI）更偏产品化、模板化，复杂动态编排能力弱于代码框架。

### HITL（人工介入）
- 【事实】工作流提供**人工审核节点**：流程中暂停、接入审批流、人工确认后继续。[来源: https://www.php.cn/faq/2599787.html (2025)；docs.coze.cn 工作流文档（2025-2026）]
- 【未证实】官方文档中人工审核节点说明的直接 URL。

### 守卫与评估
- 【事实】平台有内容安全/审核体系：智能体可启用"大模型应用防火墙"插件；2025 年推出"AI 全链路功能安全统一配置体系"（媒体报道）。[来源: https://bytedance.larkoffice.com/wiki/ECFZwGJVZi1wGYkPLntca4oXnEg (2025)；https://www.toutiao.com/article/7665241896776516139/ (2025)]
- 【推断】依托字节跳动内容安全/审核能力（豆包大模型安全体系），国内版受国内监管约束强；安全配置为平台内建而非框架 API。

### 可观测性
- 【事实】平台内提供运行调试/trace；开源组件 **coze-loop** 提供 agent 运行日志与 trace 集成（官方文档 trace_integrate）。[来源: https://www.coze.cn/open/docs/cozeloop/trace_integrate (2025-2026)；https://github.com/coze-dev/coze-loop (2025)]
- 【推断】自托管/开源侧可观测性以 coze-loop 为主，云版平台内 trace 能力为黑盒。

### 成本控制
- 【事实】平台按 **token/模型调用**计费：官方"模型费用"文档与"内置集成费用"页；另有订阅套餐（扣子订阅、企业版套餐），2025-2026 多次调整（2026-01-19 订阅升级公告、企业版套餐定价调整公告）。[来源: https://docs.coze.cn/api/open/docs/coze_pro/model_fee (2025-2026)；https://docs.coze.cn/coze_pro_internal_integrations_fee (2025)；https://docs.coze.cn/guides_20260119_coze_premium_upgraded (2026-01-19)；https://docs.coze.cn/guides_enterprise_plan_pricing_adjustment (2025)]
- 【推断】成本模型 = 平台订阅/企业版费用 + 模型 token 用量 + 集成调用费用；对自研框架而言，云平台成本可控性取决于套餐设计。

### 开源 coze-studio
- 【事实】**2025 年字节跳动将 Coze 两大核心项目开源：Coze Studio（可视化 agent 开发平台）与 Coze Loop（agent 运行/trace 组件）**，**Apache-2.0** 协议；仓库 github.com/coze-dev/coze-studio、github.com/coze-dev/coze-loop；上线两天 GitHub Star 破万。[来源: https://www.chinaz.com/ainews/19989.shtml (2025)；https://www.geekpark.net/news/352159 (2025)；https://www.e-com-net.com/article/1949350223876780032.htm (2025)；https://github.com/coze-dev/coze-studio/releases (2025-2026)]
- 【事实】开源版可 Docker 自托管（社区教程丰富）。[来源: https://developer.aliyun.com/article/1674357 (2025)]
- 【未证实】开源具体日期（任务书称 2025-04 前后；未取得一手日期公告）；开源版与云版功能对齐关系（云版企业安全/审核等闭源能力是否在开源版，官方未明确说明）。
- 【推断】开源动作是 B 端商业化/生态扩张策略：以 Apache-2.0 自托管切入企业私有化部署市场，与"扣子企业版"形成 开源引流 → 云版/企业版变现 的路径。

### 多租户与合规
- 【事实】国内版数据存储于国内、受国内监管；国际版 coze.com 面向海外、数据域分离；跨境合规对比文章以"数据出域、加密、训练承诺"四维度对比。[来源: https://www.yun88.com/news/11551.html (2025-2026)]
- 【未证实】coze.com 具体数据中心属地（如新加坡/美区）的官方文档确认；平台是否承诺不训练（字节/火山侧未见公开等价承诺原文）。

### 2025-2026 关键动态
- 2025：coze-studio / coze-loop 开源（Apache-2.0）；"扣子空间"（AI Office 产品线，36kr 报道）；扣子精选；企业版套餐定价调整；小米应用商店合作（2025-08）。
- 2026-01-19：订阅套餐升级公告。
- 2026：企业版与 B 端商业化持续演进（docs.coze.cn 企业版套餐/订阅文档更新）。

### 来源列表（Coze）
- 官方文档/费用：https://docs.coze.cn （模型费用 https://docs.coze.cn/api/open/docs/coze_pro/model_fee ；集成费用 https://docs.coze.cn/coze_pro_internal_integrations_fee ；订阅升级 https://docs.coze.cn/guides_20260119_coze_premium_upgraded ；企业版定价 https://docs.coze.cn/guides_enterprise_plan_pricing_adjustment ）（2024-2026）
- coze-loop trace 文档：https://www.coze.cn/open/docs/cozeloop/trace_integrate （2025-2026）
- coze-studio 仓库：https://github.com/coze-dev/coze-studio （2025-2026）
- coze-loop 仓库：https://github.com/coze-dev/coze-loop （2025-2026）
- chinaz 开源报道：https://www.chinaz.com/ainews/19989.shtml （2025）
- 极客公园（两天破万 star）：https://www.geekpark.net/news/352159 （2025）
- 网易 一站式 AI 平台报道：http://www.163.com/dy/article/IQ2C2K190511B8LM.html （2023-2024）
- ithome 30 秒无代码：https://m.ithome.com/html/748811.htm （2023-12）
- 小米应用商店合作：https://news.hexun.com/2025-08-01/220695990.html （2025-08-01）
- 大模型应用防火墙插件（lark 文档）：https://bytedance.larkoffice.com/wiki/ECFZwGJVZi1wGYkPLntca4oXnEg （2025）
- AI 全链路安全配置（今日头条）：https://www.toutiao.com/article/7665241896776516139/ （2025）
- 人工审核节点：https://www.php.cn/faq/2599787.html （2025）
- 扣子空间（百度百科/36kr）：https://baike.baidu.com/item/%E6%89%A3%E5%AD%90%E7%A9%BA%E9%97%B4/65605720 ；https://m.36kr.com/p/3457962457470345 （2025）
- 跨境数据合规横评：https://www.yun88.com/news/11551.html （2025-2026）
- Docker 自托管教程（阿里云）：https://developer.aliyun.com/article/1674357 （2025）

---

## 4. Dify（简述）

- 【事实】开源 LLMOps 平台（LangGenius 团队）：构建/部署/运营 LLM 应用，含可视化 workflow、agent 框架、RAG、插件生态；2025-02 发布 v1.0.0（"Building a Vibrant Plugin Ecosystem"）。[来源: https://dify.ai/blog/dify-v1-0-building-a-vibrant-plugin-ecosystem (2025-02)]
- 【事实】商业化：云端 + 企业版（自托管付费）；2026-03 宣布 **3000 万美元 Pre-A 轮**融资，聚焦企业级 agentic workflows。[来源: https://investor.wedbush.com/wedbush/article/bizwire-2026-3-9-dify-raises-30-million-series-pre-a-to-power-enterprise-grade-agentic-workflows (2026-03-09)]
- 【事实】生态热度高：公开报道 Docker 拉取量超 1 亿、GitHub star 约 7.75 万（2026 年口径）。[来源: https://cloud.tencent.cn/developer/article/2513458 (2026)]
- 【推断】Dify 与 Coze 定位高度重叠（低代码 LLM 应用/agent 编排），是开源阵营对 Coze 的主要竞品；对自研框架公司而言，Dify 属"应用平台层"竞品而非编排框架层。

## 5. Qwen-Agent（简述）

- 【事实】阿里通义团队（QwenLM）开源的 agent 框架，**Apache-2.0**；基于 Qwen 模型，提供工具调用、浏览器、代码解释器、多 agent 协作等能力；官方文档站点与 README 齐全。[来源: https://qwenlm.github.io/Qwen-Agent/ (2024-2026)；https://raw.githubusercontent.com/QwenLM/Qwen-Agent/refs/heads/main/README_CN.md (2025)]
- 【事实】国内媒体早于 2023 年底即报道"阿里发布 Qwen-Agent 框架，赋能开发者构建复杂 AI 智能体"。[来源: http://www.c114.net.cn/ai/104441.html (2023-2024)]
- 【推断】定位为 **Qwen 模型生态官方 agent 开发栈**：与 Pydantic AI（框架中立）不同，Qwen-Agent 强绑定 Qwen 模型能力，优势在模型-框架协同优化。

---

## 附：对自研 LangGraph 编排框架公司的对标启示（推断汇总）

1. Pydantic AI：类型安全 + Graph DAG + evals/Logfire 是 2026 年 Python 侧最锋利组合；自研框架需补齐"契约式输出校验 + 内置评测 + 可观测性"三位一体体验。
2. Bedrock AgentCore：证明"编排框架 ≠ 运行时"——托管运行时（状态/记忆/guardrails/多租户/合规）是云厂商卡位点；自研框架应预留 AgentCore 式托管接入（如 MCP/运行时适配器）。
3. Coze/Dify：低代码工作流平台蚕食"简单 agent 场景"；自研框架的价值锚点应在复杂编排、深度定制与可编程性。
4. HITL 三家中均非 first-class 原语（Coze 有人工审核节点、AWS 靠外部框架、Pydantic AI 靠 AG-UI/issue 讨论）→ 这是差异化机会。

> 数据说明：所有【事实】均附来源 URL 与年份；凡未获一手来源支撑处均标注【未证实】。星数/单价等易变数字建议上线前复核。
