# 竞争评估调研笔记：CrewAI / AutoGen（AG2、Microsoft Agent Framework）/ MetaGPT

> 用途：2026 年竞争评估报告（我方基于 LangGraph 自研多智能体编排框架，下称 agent-hive）。
> 调研截止：2026 年 8 月。方法：优先官方文档、官方博客、GitHub 仓库与官方论文；共执行 15 次 web_search。
> 置信度标注：【事实】= 有官方/一手来源直接支撑；【推断】= 基于来源的合理外推或二手可信来源；【未证实】= 本次检索未能核实，需进一步确认。
> 引文格式：[来源: 标题, URL, 年份]。

---

## 1. CrewAI

### 1.1 定位
- 【事实】官方定位为「角色化（role-based）多智能体协作编排框架」：以 Crew（有目标与分工的 agent 团队）为基本组织单位，agent 具备 role/goal/backstory，任务（Task）被分配给对应角色，形成「团队协作」范式。[来源: CrewAI Documentation Introduction, https://docs.crewai.com/en/introduction, 2025–2026]
- 【事实】官方宣传语为「AI agent 团队（crews）编排框架」，与 LangGraph 的「底层图/状态机」定位错位竞争：CrewAI 主打高层抽象与开箱即用，LangGraph 主打底层可控。[来源: CrewAI 官网与官方文档, https://docs.crewai.com, 2025–2026；此对比表述见第三方分析，标【推断】]

### 1.2 编排模型
- 【事实】三套编排抽象并存：
  1. **Crews（任务驱动）**：Crew 内 Task 通过 `context`（依赖其他 task 的输出）形成依赖图；任务可并行（`async_execution=True`），Crew 执行有 `sequential`/`hierarchical` 流程，层级流程含 manager agent。[来源: Tasks 概念文档, https://docs.crewai.com/en/concepts/tasks, 2025–2026]
  2. **Flows（事件驱动）**：2024 年起引入，用 `@start`/`@listen`/`@router` 装饰器把任意函数/agent 组织成事件驱动 DAG；支持 `@human_feedback` 人类反馈节点，可精确控制并行分支与重试。[来源: Build Your First Flow 指南, https://docs.crewai.com/en/guides/flows/first-flow, 2026；human_feedback 源码, https://github.com/crewAIInc/crewAI/blob/main/lib/crewai/src/crewai/flow/human_feedback.py, 2025]
  3. **Events（平台事件）**：AMP/平台侧以事件流贯穿 agent 生命周期（见 1.6、1.9）。【推断：Events 主要指平台遥测/编排事件，而非独立于 Flows 的编码抽象，官方文档未单列，标【推断】】
- 【事实】任务间依赖与并行：Task 级 `context` 依赖 + `async_execution`；Flow 级靠监听/路由天然并行。官方文档明确支持「并行任务」。[来源: Tasks 文档同上]

### 1.3 版本动态
- 【事实】v0.x（2023-11 起）→ **v1.0 GA（2025 年 10 月）**：官方博客宣布「CrewAI OSS 1.0 — We are going GA」，进入稳定/生产可用阶段；MCP 原生支持自 v1.0（2025-10）起。[来源: CrewAI OSS 1.0 博客, https://crewai.com/blog/crewai-oss-1-0---we-are-going-ga, 2025；aiwiki 版本表, https://aiwiki.ai/wiki/crewai, 2026]
- 【事实】截至 2026-08 文档已到 **v1.15.x 系列**（检索可见 v1.15.0–v1.15.13 多版本文档），即 1.0 GA 后约 10 个月内发布 15+ 个次版本，迭代极快。[来源: CrewAI 文档版本化 URL, https://docs.crewai.com/en/changelog, 2026]

### 1.4 HITL（人工介入）
- 【事实】Task 级 `human_input=True`：任务执行到该步会暂停并向用户征询输入/确认，可配合 `async_execution` 使用。[来源: Tasks 概念文档（含 human_input 参数）, https://docs.crewai.com/en/concepts/tasks, 2025–2026]
- 【事实】Flow 级 `@human_feedback` 装饰器：在 Flow 中声明人类反馈节点，暂停流水线等待人工输入。[来源: human_feedback.py 源码与 HITL 文档, https://github.com/crewAIInc/crewAI/blob/main/lib/crewai/src/crewai/flow/human_feedback.py, 2025；https://docs.crewai.com/en/learn/human-in-the-loop, 2026]
- 【事实】官方文档设专门 HITL 章节（human-input-on-execution / human-in-the-loop workflows）。[来源: https://docs.crewai.com/en/learn/human-input-on-execution, 2025–2026]
- 【推断】后端异步 HITL（如 web 后台轮询人工输入）仍是社区痛点：GitHub issue #2051「How to design asynchronous human-in-the-loop Crews running on the backend」反映该需求未一等公民化。[来源: crewAIInc/crewAI issue #2051, https://github.com/crewAIInc/crewAI/issues/2051, 2025]
- 【未证实】Task 之外是否存在独立的「审批（approval）门」对象（区别于 human_input 征询）未在官方文档中检索到；平台/企业版的审批能力未证实。

### 1.5 守卫（Guardrails）与评估
- 【事实】Task 级 **guardrails**：`guardrail` 参数接受校验函数，返回 `(is_valid, feedback)` 二元组，失败可重试/降级；文档描述为「在任务输出进入下一环节前校验与转换」。[来源: Tasks 概念文档（guardrails 小节）, https://docs.crewai.com/en/concepts/tasks, 2025–2026]
- 【事实】企业版提供 **Hallucination Guardrail**（幻觉护栏）等托管守卫能力。[来源: Hallucination Guardrail 企业特性文档, https://docs.crewai.com/v1.15.4/en/enterprise/features/hallucination-guardrail, 2026]
- 【未证实】与第三方护栏产品（如 Guardrails AI 等）的官方集成未在检索中证实；未见内置评估（eval）框架，评估主要靠外部（Langfuse 等平台评测）。标【未证实】。

### 1.6 可观测性
- 【事实】内置匿名 telemetry（可用 `enable_telemetry` 开关关闭）。[来源: Telemetry 文档, https://docs.crewai.com/en/telemetry, 2026]
- 【事实】官方提供 Langfuse 集成指南（追踪/成本/评估面板）。[来源: Langfuse Integration, https://docs.crewai.com/en/observability/langfuse, 2026]
- 【事实】平台/企业版支持 OpenTelemetry 遥测导出。[来源: OpenTelemetry Export（CrewAI Platform 文档）, https://docs-platform.crewai.com/platform/en/guides/capture_telemetry_logs, 2026]
- 【未证实】与 Arize（Phoenix）的官方集成未在检索中证实（Langfuse 为当前文档主打集成）。

### 1.7 成本控制
- 【事实】官方博客有 token 花费优化专题（缓存、模型路由、任务裁剪等），并宣传「agentic ROI」。[来源: How to Optimize Token Spend, https://crewai.com/blog/how-to-optimize-token-spend-for-better-agentic-roi, 2025]
- 【事实】社区出现把 agent token 花费当作 CI 成本门禁的实践（CrewAI 官方社区帖子），也有第三方「cost guardrails」库同时覆盖 CrewAI/AutoGen/LangGraph。[来源: 社区帖, https://community.crewai.com/t/field-note-treating-your-agents-token-spend-like-a-ci-cost-gate/7725, 2025；第三方库 sapph1re/agent-cost-guardrails, https://github.com/sapph1re/agent-cost-guardrails, 2025]
- 【推断】成本控制在开源侧是「指导实践 + 记账数据」而非强制配额；配额类能力主要在 AMP/平台侧，细节未证实。

### 1.8 许可证与生态
- 【事实】开源核心 **MIT 许可证**（GitHub 仓库 LICENSE），文档/平台为企业付费部分。[来源: crewAIInc/crewAI, https://github.com/crewAIInc/crewAI, 2025–2026]
- 【事实】GitHub stars 为多智能体框架第一梯队（量级约 3 万+，2026 年中）。【推断：精确数值未在检索中核实，标【推断】】[来源: GitHub 仓库页, https://github.com/crewAIInc/crewAI, 2026]
- 【事实】v1.0 起原生 MCP 支持；第三方报道称 2026-04 时「日生产执行 1200 万次」并支持 MCP/A2A（营销口径，二手来源）。[来源: aiwiki 版本表, https://aiwiki.ai/wiki/crewai, 2026；AgentMarketCap 博客, https://agentmarketcap.ai/blog/2026/04/18/crewai-12m-daily-executions-mcp-a2a-production-scale, 2026]
- 【事实】2025 年与 OpenAI、Anthropic 等一同入选「2025 IA Enablers」名单（企业采用度佐证，二手宣传口径）。[来源: CrewAI 官网转载, https://crewai.org.cn/blog/crewai-on-2025-ia-enablers-list-with-openai-and-anthropic, 2025]

### 1.9 2025–2026 关键动态
- 【事实】2025-10：OSS 1.0 GA + MCP 原生支持。[来源: 1.0 博客同上, 2025]
- 【事实】2025：发布 **AMP（Agent Management Platform）**——agent 管理云平台（部署、监控、治理），官方博客 + 企业文档章节；配套 webinar「OSS Updates & the Agent Management Platform」。[来源: AMP 博客, https://crewai.com/blog/crewai-amp---the-agent-management-platform, 2025；webinar 页, https://crewai.com/webinar/whats-new-in-crewai-oss-updates-and-the-agent-management-platform, 2025]
- 【未证实】「CrewAI Studio」是否为 AMP 的后续品牌迭代，本次检索未见官方来源确认（仅见 AMP），标【未证实】。
- 【事实】2025-2026：版本线 1.0 → 1.15.x，功能面扩展（Flows 成熟、企业护栏、平台遥测导出）。[来源: changelog, https://docs.crewai.com/en/changelog, 2025–2026]

### 1.10 来源列表（CrewAI）
1. CrewAI Documentation（Introduction / Concepts: Tasks / Guides: Flows / Learn: HITL / Telemetry / Observability: Langfuse）— https://docs.crewai.com — 2025–2026
2. CrewAI OSS 1.0 — We are going GA — https://crewai.com/blog/crewai-oss-1-0---we-are-going-ga — 2025
3. CrewAI AMP — The Agent Management Platform — https://crewai.com/blog/crewai-amp---the-agent-management-platform — 2025
4. How to Optimize Token Spend for Better Agentic ROI — https://crewai.com/blog/how-to-optimize-token-spend-for-better-agentic-roi — 2025
5. Hallucination Guardrail（Enterprise）— https://docs.crewai.com/v1.15.4/en/enterprise/features/hallucination-guardrail — 2026
6. human_feedback.py（源码）— https://github.com/crewAIInc/crewAI/blob/main/lib/crewai/src/crewai/flow/human_feedback.py — 2025
7. Issue #2051（异步 HITL 设计）— https://github.com/crewAIInc/crewAI/issues/2051 — 2025
8. OpenTelemetry Export（Platform）— https://docs-platform.crewai.com/platform/en/guides/capture_telemetry_logs — 2026
9. GitHub: crewAIInc/crewAI — https://github.com/crewAIInc/crewAI — 2025–2026
10. aiwiki CrewAI 版本表（MCP 自 v1.0/2025-10）— https://aiwiki.ai/wiki/crewai — 2026
11. AgentMarketCap：CrewAI 12M 日执行（二手宣传口径）— https://agentmarketcap.ai/blog/2026/04/18/crewai-12m-daily-executions-mcp-a2a-production-scale — 2026
12. 社区 token 成本门禁实践 — https://community.crewai.com/t/field-note-treating-your-agents-token-spend-like-a-ci-cost-gate/7725 — 2025

---

## 2. AutoGen / AG2 / Microsoft Agent Framework

> 说明：这一组有三条线——微软原 AutoGen（0.2 → 0.4+，后称 AutoGen 1.x）、社区分叉 AG2、以及微软 2025-10 发布的 Microsoft Agent Framework（AutoGen 的官方后继）。

### 2.1 定位
- 【事实】AutoGen 0.2：微软研究院（2023-08 开源）的「多 agent 对话式」框架，以 ConversableAgent + GroupChat 著称；0.4 起重写为「事件驱动、异步 actor 模型」的通用 agent 编程框架（Core API + AgentChat API 两层）。[来源: AutoGen reimagined: Launching AutoGen 0.4, https://devblogs.microsoft.com/autogen/autogen-reimagined-launching-autogen-0-4/, 2025-01]
- 【事实】AG2：2024 年 AutoGen 0.2 停更后由社区接手的**官方分叉**（原名 AutoGen，后改名 AG2），维护方为 ag2ai 社区（org: ag2ai/ag2，官网 ag2.ai），延续 0.2 的「AgentOS」路线。[来源: GitHub ag2ai/ag2, https://github.com/ag2ai/ag2, 2024–2026；「Which autogen is the official」讨论, https://github.com/microsoft/autogen/discussions/4216, 2024]
- 【事实】Microsoft Agent Framework：2025-10 预览发布（.NET/Python/TypeScript 三端），被官方定义为 AutoGen 与 Semantic Kernel 能力融合后的**下一代 agent 框架**；AutoGen 1.x 提供官方迁移指南。[来源: InfoWorld, https://www.infoworld.com/article/4067500/microsoft-unveils-framework-for-building-agentic-ai-apps.html, 2025-10；官方迁移指南 from AutoGen, https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-autogen/, 2025–2026]

### 2.2 编排模型
- 【事实】AutoGen 0.4+：事件驱动、asyncio 原生；Core 层为 actor 式 runtime（支持分布式/Dapr worker）；AgentChat 层提供 **Teams**：RoundRobinGroupChat、SelectorGroupChat（选择器发言）、MagenticOneGroupChat、Swarm（handoff 工作流）、Workflow（顺序/有向图）等。[来源: AutoGen 0.4 发布博客同上, 2025；autogen_agentchat.teams 0.6.x 参考文档, https://microsoft.github.io/autogen/0.6.2/reference/python/autogen_agentchat.teams.html, 2025–2026]
- 【事实】**Magentic-One**：微软 2024-11 发布的多 agent 通用系统（Orchestrator + WebSurfer/FileSurfer/Coder/ComputerTerminal 等），已内建为 AutoGen 0.4 的团队模式；GAIA 等基准报告性能。[来源: Magentic-One 论文, https://arxiv.org/html/2411.04468v1, 2024-11]
- 【事实】Agent Framework：以 **AgentThread + AgentChat + AgentRuntime** 为编排原语，工作流（workflows）为代码优先的图式定义，支持并行分支与事件流；可运行在托管 runtime（Azure AI Foundry Agent Service 等）。[来源: Agent Framework Overview, https://learn.microsoft.com/en-us/agent-framework/overview/agent-framework-overview, 2025–2026]
- 【事实】与 Semantic Kernel 的关系：.NET/Python 侧基于/兼容 Semantic Kernel 的 AI 服务抽象（官方提供 SK → Agent Framework 迁移指南；微软 AI 决策框架将两者并列）。[来源: SK 迁移指南, https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-semantic-kernel/, 2025–2026]
- 【推断】AutoGen 1.x 2026 年进入维护模式、新特性开发转向 Agent Framework：微软官方未发明确公告，但官方迁移指南 + LangChain 官方文章（2026）均以「维护/迁移」口径表述，标【推断】。[来源: LangChain vs AutoGen, https://www.langchain.com/resources/langchain-vs-autogen, 2026；Atlan AutoGen Status, https://atlan.com/know/ai-agent/what-is-autogen/, 2026]

### 2.3 HITL
- 【事实】AutoGen 0.4+：`UserProxyAgent`（带输入工厂 `input_func`）与任务 `interrupt`（`Task.interrupt()`/agent 中断）为内置 HITL 通道；core 层支持取消与恢复。[来源: AutoGen 0.4 发布博客与 agentchat 文档, https://devblogs.microsoft.com/autogen/autogen-reimagined-launching-autogen-0-4/, 2025；https://microsoft.github.io/autogen/0.6.2/reference/python/autogen_agentchat.teams.html, 2025–2026]
- 【事实】Agent Framework：内置**函数调用审批内容类型 `FunctionApprovalRequestContent`**（工具调用需人工审批的内容载体），说明审批式 HITL 为内建机制；AgentThread 支持按需暂停/恢复（workflow 中的人工介入点）。[来源: microsoft/agent-framework issue #1318（提及 FunctionApprovalRequestContent 序列化）, https://github.com/microsoft/agent-framework/issues/1318, 2026；【推断】暂停/恢复细节据 AgentThread 模型，标【推断】]

### 2.4 守卫与评估
- 【事实】AutoGen 无一等公民 guardrails API；2025 年社区提出「Governance extension（策略执行与 agent 身份）」特性提案（issue #7613，未合并/未定稿）。[来源: microsoft/autogen issue #7613, https://github.com/microsoft/autogen/issues/7613, 2025]
- 【未证实】Agent Framework 是否有内置 guardrails/评估组件，本次检索未证实（官方主打 trace 与运行时；评估多靠外部工具）。标【未证实】。
- 【事实】AutoGen/Magentic-One 以 GAIA、HumanEval、MATH 等公开基准做评估（论文与 PR 均有记录），属框架级基准实验而非内建 eval 框架。[来源: Magentic-One 论文同上, 2024；autogen PR #3433（GAIA 基准评估）, https://github.com/microsoft/autogen/pull/3433, 2024]

### 2.5 可观测性
- 【事实】AutoGen 0.4+：内置 trace（OpenTelemetry 兼容）与 CLI/日志；agentchat 运行时有 span 记录。[来源: AutoGen 0.4 发布博客, 2025]
- 【事实】Agent Framework：官方 Observability 文档——内置 tracing（控制台/文件/VS Code 输出），可导出 Azure Monitor / Application Insights，并支持第三方（Dynatrace 提供官方集成文档）。[来源: Agent Framework Observability, https://learn.microsoft.com/en-us/agent-framework/agents/observability, 2025–2026；Dynatrace 集成, https://docs.dynatrace.com/docs/observe/dynatrace-for-ai-observability/integrations/microsoft-agent-framework, 2026]

### 2.6 成本控制
- 【事实】AutoGen 0.4+ 提供 token/usage 记账与成本估算（模型客户端层 usage 统计）。【推断：成本配额/门禁仍靠外部（如 community 成本护栏库、平台预算），标【推断】】[来源: agent-cost-guardrails（覆盖 AutoGen）, https://github.com/sapph1re/agent-cost-guardrails, 2025]
- 【未证实】Agent Framework 侧内建成本控制机制未证实。

### 2.7 许可证与生态
- 【事实】AutoGen（microsoft/autogen）与 AG2（ag2ai/ag2）均为 **MIT**；Microsoft Agent Framework（microsoft/agent-framework）亦为开源（仓库公开，许可证 MIT，官方以开源+托管服务双轨发布）。【推断：Agent Framework 许可证标注为 MIT 依据仓库 LICENSE 与微软开源公告，未逐字核验文件内容，标【推断】】[来源: 三仓库 GitHub, https://github.com/microsoft/autogen / https://github.com/ag2ai/ag2 / https://github.com/microsoft/agent-framework, 2024–2026]
- 【推断】生态量级（2026-08 约数，未精确核验）：AutoGen ~4 万 stars；AG2 数千级；Agent Framework 为新仓库（2025-10 起步）数千级。标【推断】。[来源: 各 GitHub 仓库页, 2026]
- 【事实】AG2 现状：v0.7.5（2026 年初）、v0.8.x 系列（2026，如 v0.8.5）持续发布，专注 0.2 兼容路线 + 文档/向量库等增强，官网发布页可见版本史。[来源: ag2ai/ag2 releases, https://github.com/ag2ai/ag2/releases/tag/v0.7.5, 2026；https://www.ag2.ai/developers/releases, 2026；gitcode 报道（二手）, https://blog.gitcode.com/ab4b894df9dcd4a4f49b5b0bbfc7f656.html, 2026]

### 2.8 2025–2026 关键动态
- 【事实】2024-10：AutoGen 0.4 架构预览发布；2025-01-17：AutoGen 0.4 正式发布（异步 actor 重写）。[来源: 0.4 预览, https://microsoft.github.io/autogen/0.2/blog/2024/10/02/new-autogen-architecture-preview/, 2024；0.4 发布博客, 2025-01]
- 【事实】2024-11：AG2 社区分叉成立；2025–2026：AG2 独立演进至 v0.8.x。[来源: 同 2.7]
- 【事实】2025-10：Microsoft Agent Framework 预览发布（.NET/Python/TS，与 Semantic Kernel 同源）；提供 from-AutoGen 与 from-Semantic-Kernel 官方迁移指南；AutoGen 官方教程系列（ai-agents-for-beginners）新增 Agent Framework 模块。[来源: InfoWorld, 2025-10；迁移指南, 2025–2026；ai-agents-for-beginners Module 14, https://microsoft.github.io/ai-agents-for-beginners/14-microsoft-agent-framework/, 2025–2026]
- 【未证实】Agent Framework 1.0 GA 日期：第三方 wiki 记 2026-04-03 达 GA，官方公告未在本次检索中直接证实，标【未证实】。[来源: aiwiki raw 记录, https://aiwiki.ai/wiki/autogen/raw, 2026]

### 2.9 来源列表（AutoGen / AG2 / Agent Framework）
1. New AutoGen Architecture Preview — https://microsoft.github.io/autogen/0.2/blog/2024/10/02/new-autogen-architecture-preview/ — 2024
2. AutoGen reimagined: Launching AutoGen 0.4 — https://devblogs.microsoft.com/autogen/autogen-reimagined-launching-autogen-0-4/ — 2025-01
3. autogen_agentchat.teams 0.6.2 参考 — https://microsoft.github.io/autogen/0.6.2/reference/python/autogen_agentchat.teams.html — 2025–2026
4. Magentic-One 论文 — https://arxiv.org/html/2411.04468v1 — 2024-11
5. microsoft/autogen Discussion #4216（官方之争）— https://github.com/microsoft/autogen/discussions/4216 — 2024
6. ag2ai/ag2 仓库与 Releases（v0.7.5 等）— https://github.com/ag2ai/ag2 — 2024–2026；https://www.ag2.ai/developers/releases — 2026
7. Microsoft Agent Framework Overview — https://learn.microsoft.com/en-us/agent-framework/overview/agent-framework-overview — 2025–2026
8. 迁移指南：from AutoGen / from Semantic Kernel — https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-autogen/ 、https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-semantic-kernel/ — 2025–2026
9. Agent Framework Observability — https://learn.microsoft.com/en-us/agent-framework/agents/observability — 2025–2026
10. InfoWorld：Microsoft unveils framework for building agentic AI apps — https://www.infoworld.com/article/4067500/microsoft-unveils-framework-for-building-agentic-ai-apps.html — 2025-10
11. LangChain vs AutoGen（维护公告解读，二手）— https://www.langchain.com/resources/langchain-vs-autogen — 2026
12. Atlan：AutoGen Explained: Status, Architecture and Alternatives — https://atlan.com/know/ai-agent/what-is-autogen/ — 2026
13. microsoft/autogen issue #7613（Governance 扩展提案）— https://github.com/microsoft/autogen/issues/7613 — 2025
14. microsoft/agent-framework issue #1318（FunctionApprovalRequestContent）— https://github.com/microsoft/agent-framework/issues/1318 — 2026
15. ai-agents-for-beginners Module 14 — https://microsoft.github.io/ai-agents-for-beginners/14-microsoft-agent-framework/ — 2025–2026
16. Dynatrace × Agent Framework 集成文档 — https://docs.dynatrace.com/docs/observe/dynatrace-for-ai-observability/integrations/microsoft-agent-framework — 2026

---

## 3. MetaGPT

### 3.1 定位
- 【事实】官方定位为「SOP（标准操作流程）驱动的多智能体元编程框架」——把一个软件公司流水线（产品经理→架构师→工程师→QA…）固化为多角色 SOP，输入一行需求，输出 PRD、设计、任务、代码仓库。[来源: MetaGPT README（FoundationAgents/MetaGPT）, https://github.com/FoundationAgents/MetaGPT, 2024–2026；原始论文 MetaGPT: Meta Programming for a Multi-Agent Collaborative Framework, arXiv:2308.00352, 2023]
- 【事实】论文（2023-08）提出 SOP 编码进 prompt、角色间以结构化消息传递，解决「对话式多 agent 漂移/一致性差」问题。[来源: arXiv:2308.00352, 2023]

### 3.2 编排模型
- 【事实】核心原语：**Role**（角色，含 SOP 化 prompt）+ **Environment**（环境，消息路由）+ **Message**（结构化消息）+ **Subscription**（订阅/收发）；消息带 `send_to`/`cause_by`/`role` 等字段，消息即角色间**契约**。[来源: DeepWiki: Message Passing System, https://deepwiki.com/geekan/MetaGPT/2.2-message-passing-system, 2025；Message Schema and Memory, https://deepwiki.com/FoundationAgents/MetaGPT/2.3-message-schema-and-memory, 2025]
- 【事实】执行方式为 **SOP 流水线**：按角色工序串行推进（PM 产出需求文档 → 架构师产出设计 → 工程师产出代码 → QA 测试），而非自由对话；`Team` 提供 `run_project` 高层入口。[来源: README 同上, 2024–2026]
- 【推断】并行能力弱于对话式框架：SOP 串行为主（流水线工序天然顺序依赖），异步/并行需自定义，标【推断】。

### 3.3 HITL
- 【事实】MetaGPT 提供有限人工介入点（如人工角色/投资决策角色示例、`invest` 环节反馈）。【推断：无 Task 级 human_input 那样的内建一等 HITL 抽象，标【推断】】[来源: README 与 NEWS, https://github.com/FoundationAgents/MetaGPT, 2024–2026]
- 【未证实】是否存在官方文档化的 HITL/审批机制，本次检索未证实。

### 3.4 守卫与评估
- 【事实】无内建 guardrails API（检索未见官方文档）。[来源: 同上（未检索到，按缺失记录）]
- 【事实】评估以论文/基准实验为主：Data Interpreter 在数据科学任务（含 MATH 等）上报告指标；框架本身无内建 eval 框架。【推断：社区多依赖外部评测，标【推断】】[来源: Data Interpreter 论文, https://arxiv.org/abs/2402.18679, 2024-02]
- 【未证实】「MetaGPT 内置评估组件」未证实。

### 3.5 可观测性
- 【事实】内置日志（含 token 花费、角色行动记录）与轻量可视化；无官方 Langfuse 等集成文档（未检索到）。【推断：可观测性能力弱于 CrewAI/AutoGen，标【推断】】[来源: README/仓库, https://github.com/FoundationAgents/MetaGPT, 2024–2026]

### 3.6 成本控制
- 【事实】日志层记录 LLM 调用与 token 用量；无内建预算/配额机制。【推断：同社区实践，靠外部记账，标【推断】】[来源: 仓库, 2024–2026]

### 3.7 许可证与生态
- 【事实】开源核心 **MIT 许可证**。[来源: GitHub LICENSE, https://github.com/FoundationAgents/MetaGPT, 2024–2026]
- 【事实】GitHub stars 居多智能体框架头部（量级约 5 万，2025 年前后为同品类最高之一）。【推断：精确数值未在检索中核实，标【推断】】[来源: GitHub 仓库页, https://github.com/FoundationAgents/MetaGPT, 2026]
- 【事实】仓库已从 geekan 组织迁移至 **FoundationAgents** 组织（持续维护中）。[来源: https://github.com/FoundationAgents/MetaGPT 与 geekan/MetaGPT NEWS.md, 2025]

### 3.8 2025–2026 关键动态
- 【事实】**Data Interpreter**（多模态数据科学 agent，2024-02 论文、2024 年进入主仓库）成为 2024–2025 主推能力；【推断】2025–2026 版本主线为 v0.7/v0.8.x 系列（v0.8.0 发布有据），标【事实（v0.8.0 存在）】。[来源: Data Interpreter 论文同上, 2024；v0.8.0 发布记录, https://github.com/FoundationAgents/MetaGPT/releases, 2025]
- 【未证实】「MetaGPT 2.0」官方公告：检索未见官方来源（仅社区同名内容与镜像），标【未证实】。
- 【未证实】2026 年内最新版本号与活跃度（stars 增速、commit 频率）未在检索中精确核实。

### 3.9 来源列表（MetaGPT）
1. FoundationAgents/MetaGPT README — https://github.com/FoundationAgents/MetaGPT — 2024–2026
2. MetaGPT 原始论文（SOP + 多角色）— arXiv:2308.00352 — 2023-08
3. DeepWiki: Message Passing System — https://deepwiki.com/geekan/MetaGPT/2.2-message-passing-system — 2025
4. DeepWiki: Message Schema and Memory — https://deepwiki.com/FoundationAgents/MetaGPT/2.3-message-schema-and-memory — 2025
5. Data Interpreter 论文 — https://arxiv.org/abs/2402.18679 — 2024-02
6. FoundationAgents/MetaGPT Releases（v0.8.0 等）— https://github.com/FoundationAgents/MetaGPT/releases — 2025
7. geekan/MetaGPT NEWS.md — https://raw.githubusercontent.com/geekan/MetaGPT/main/docs/NEWS.md — 2025
8. PyPI metagpt 版本史（0.6.x 等）— https://pypi.org/project/metagpt/0.6.0/ — 2024

---

## 4. 与 agent-hive「首脑统筹 + 角色专家 + 契约工作包」模式的相似性分析（事实层面）

> agent-hive 模式假设：一个首脑 agent 负责架构设计与任务分包，把工作拆成带接口/验收标准的**契约工作包**派发给角色专家 agent 并行执行，首脑验收并集成。以下按「事实对照」与「推断启示」两级呈现。

### 4.1 事实对照
- 【事实】**MetaGPT 与 agent-hive 最接近**：MetaGPT = SOP（工序/角色）+ Role（角色专家）+ Message 协议（结构化消息即角色间契约，字段含 send_to/cause_by）。对应关系：首脑 ≈ MetaGPT 的 SOP 编排/PM-架构师环节；角色专家 ≈ Role；契约工作包 ≈ 结构化 Message（产出物文档/PRD/代码即交付契约）。[来源: MetaGPT README 与 DeepWiki, 2023–2026]
  - 差异（事实层面）：MetaGPT 是**流水线串行 + 订阅路由**，角色间靠消息总线自动流转，无中央「首脑」对象；agent-hive 是**首脑集中分包 + 并行验收**，统筹权在单个 chief。
- 【事实】**CrewAI 部分接近**：角色化（role/goal/backstory）≈ 角色专家；Task 的 `expected_output` + `context` 依赖 ≈ 弱契约（描述性而非强类型）；无中央首脑（对等协作，层级流程中 manager 近似首脑但为可选）。[来源: CrewAI Tasks 文档, 2025–2026]
- 【事实】**AutoGen/Agent Framework 最不像**：以 GroupChat 会话式发言 / 事件驱动 actor 为中心，角色与契约均非一等公民（Agent Framework 的 workflow 为图式编排，可近似契约流但语义不同）。[来源: AutoGen 0.4 发布博客, 2025；Agent Framework Overview, 2025–2026]

### 4.2 推断启示（供报告论证）
- 【推断】MetaGPT 是三者中唯一「把消息协议当契约」的框架，与 agent-hive「契约工作包」哲学同源；其弱点（SOP 串行、无首脑回环验收、HITL/eval 弱）恰是 agent-hive 声称的差异化空间（首脑统筹 + 并行 + 验收闭环）。
- 【推断】CrewAI 的 Task 依赖/guardrails/Flows 事件模型可作为 agent-hive「契约执行」能力的对标参照系；AutoGen/Agent Framework 的 trace 与审批内容类型（FunctionApprovalRequestContent）可作为 agent-hive 可观测性/HITL 的功能下限参考。
- 【未证实】三者均无与 agent-hive 完全同构的「首脑 + 契约工作包 + 验收」官方模式；此为 agent-hive 的差异化论述点，需在报告中以「模式对比」而非「功能缺失」表述。

---

## 5. 一页对照矩阵（2026-08）

| 维度 | CrewAI | AutoGen 0.4+ / AG2 | Microsoft Agent Framework | MetaGPT |
|---|---|---|---|---|
| 定位 | 角色化 crew 编排（高层易用） | 事件驱动 agent 编程框架（底层可控） | AutoGen+SK 融合的官方后继（三端） | SOP 驱动的多角色流水线 |
| 编排模型 | Crews（任务依赖/并行）+ Flows（事件） | Teams（GroupChat 系/Swarm/Magentic-One）+ Workflow | AgentThread/AgentChat/AgentRuntime + Workflow | Role + Environment + 结构化 Message 订阅路由，SOP 串行 |
| 与 agent-hive 相似度 | 中（角色化+弱契约） | 低（会话/事件中心） | 低（会话/事件中心，workflow 图式） | 高（角色+消息契约，无首脑） |
| HITL | Task human_input、Flow @human_feedback | UserProxyAgent、interrupt | FunctionApprovalRequestContent、AgentThread 暂停/恢复 | 有限（无一等 HITL） |
| Guardrails | Task 级 guardrail 函数 + 企业幻觉护栏 | 无一等 API（治理提案未定稿） | 未证实 | 无 |
| 内置 eval | 未证实（靠外部） | 基准实验（GAIA 等），非内建 eval 框架 | 未证实 | 无内建（论文基准实验） |
| 可观测性 | 内置 telemetry + Langfuse/OTel | 内置 trace（OTel 兼容） | 内置 tracing（控制台/文件/VS Code/Azure Monitor） | 日志级，弱 |
| 成本控制 | 记账 + 指导实践（平台侧配额未证实） | usage 记账（配额靠外部） | 未证实 | token 日志，无配额 |
| 许可证 | MIT | MIT / MIT | MIT（据仓库，推断） | MIT |
| 版本线 | v1.0 GA（2025-10）→ v1.15.x | AutoGen 0.4 GA（2025-01）→ 0.6.x；AG2 v0.8.x | 2025-10 预览 → 1.0 GA（2026-04?，未证实） | v0.8.x（2025）；无 2.0 官方证据 |
| 生态量级（约数，推断） | ~3 万+ stars，MCP 原生 | AutoGen ~4 万 stars；AG2 数千 | 新仓库，数千级 | ~5 万 stars（头部） |

---

## 6. 给报告撰写者的关键结论

1. **CrewAI 是「易用性 + 商业化」标杆**：MIT 开源 + 1.0 GA（2025-10）+ AMP 平台 + Langfuse/OTel 可观测 + 任务级 HITL/guardrail，是对 agent-hive「产品化完整度」的主要对标对象。
2. **AutoGen 系正处于权力交接期**：AutoGen 0.4+（事件驱动）→ Agent Framework（2025-10 起）为官方主线，AG2（v0.8.x）走社区 0.2 兼容线；三者并存造成生态碎片化，是报告中「选型不确定性」论点的素材。
3. **MetaGPT 与 agent-hive 哲学同源但工程供给弱**：SOP+角色+消息契约最接近「首脑+契约工作包」，但其串行流水线、无首脑回环、弱 HITL/eval/可观测，恰好构成 agent-hive 的差异化论证空间。
4. **共同空白（可作 agent-hive 卖点）**：三组框架均无「首脑统筹 + 契约工作包 + 验收闭环」的一等模式；guardrails/eval 普遍靠外部；HITL 多停留在「征询/审批点」而非「契约级人工验收」。
5. **引用注意**：star 数、Agent Framework GA 日期、AG2 最新版本号为【推断/未证实】，报告中引用前建议以 GitHub API 复核精确值。

---

*调研方法说明：共 15 次 web_search；优先官方文档（docs.crewai.com、learn.microsoft.com、microsoft.github.io/autogen）、官方博客（crewai.com/blog、devblogs.microsoft.com/autogen）、GitHub 仓库与 arXiv 论文；二手来源（InfoWorld、LangChain 官网文章、aiwiki、第三方对比文）仅在标注后引用。*
