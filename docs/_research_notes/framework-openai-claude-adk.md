# 三大官方 Agent SDK 竞争评估调研笔记（截至 2026-08）

> 调研对象：OpenAI Agents SDK / Anthropic Claude Agent SDK / Google Agent Development Kit (ADK)
> 调研时间：2026 年 8 月（本文件所有"当前版本"均以此为准）
> 标注约定：【事实】= 官方文档/官方仓库/权威一手来源可查证；【推断】= 基于已证事实的合理推导；【未证实】= 本轮调研未能找到可靠来源，待后续核实。

---

## 一、OpenAI Agents SDK

### 定位
- 【事实】OpenAI 官方开源的 agent 编排 SDK（Python 与 TypeScript 双语言），2025-03-11 随 "New tools for building agents" 一同发布（同期还有 Responses API、web search、file search、computer use 等），作为对实验性框架 **Swarm** 的正式取代 [来源: https://community.openai.com/t/new-tools-for-building-agents-responses-api-web-search-file-search-computer-use-and-agents-sdk/1140896, 2025]。
- 【事实】仓库为 `openai/openai-agents-python` 与 `openai/openai-agents-js`；官方文档主页 openai.github.io/openai-agents-python/ [来源: https://openai.github.io/openai-agents-python/, 2025-2026]。

### 当前版本
- 【事实】PyPI `openai-agents` 当前版本 **0.22.0**（2026-08-19 上传）；GitHub 可见 v0.19.0、v0.20.0 等 release 标签 [来源: https://pypi.org/pypi/openai-agents/json, 2026; https://github.com/openai/openai-agents-python/releases/tag/v0.19.0, 2026; https://github.com/openai/openai-agents-python/releases/tag/v0.20.0, 2026]。
- 【事实】2026 年版本线从 0.8/0.9 起步（0.8.3 上传于 2026-02-10），年中进入 0.1x-0.2x 高速迭代，v0.14 使 Sandbox Agents 与 Model-Native Harness GA [来源: https://pypi.org/pypi/openai-agents/json, 2026; https://dev.to/_46ea277e677b888e0cd13/openai-agents-sdk-v014-sandbox-agents-and-the-model-native-harness-go-ga-49ej, 2026]。
- 【推断】版本号仍为 0.x，官方尚未发布 1.0 稳定版。

### 编排模型
- 【事实】核心原语为 **Agent（含 tools / handoffs / guardrails / model 配置）+ Runner（run / run_sync / run_streamed）+ Run / RunResult**；handoffs 实现智能体间任务交接；每次运行自动产生 trace/span 树 [来源: https://github.com/openai/openai-agents-python/blob/main/docs/tracing.md, 2025-2026]。
- 【事实】**Sessions** 提供会话级记忆与上下文管理（如 SQLiteSession、OpenAI Responses compaction session），支持多轮/长期记忆，官方有 session memory cookbook [来源: https://github.com/openai/openai-agents-python/blob/main/docs/sessions/index.md, 2025-2026; https://developers.openai.com/cookbook/examples/agents_sdk/session_memory, 2025]。
- 【事实】工具/函数调用与 **MCP** 集成是官方一等公民：依赖含 `mcp>=1.19.0`，MCP 服务器可作为工具接入；默认基于 **Responses API**（依赖 `openai>=3.0.0,<4`，即 openai-python v3 的 Responses 接口）[来源: https://github.com/openai/openai-agents-python/blob/main/pyproject.toml, 2026]。

### HITL（人工介入）
- 【事实】官方维护 human-in-the-loop 指南（Python: docs/human_in_the_loop.md；JS: guides/human-in-the-loop.mdx），机制以工具中断/人工审批为主 [来源: https://github.com/openai/openai-agents-python/blob/main/docs/human_in_the_loop.md, 2025-2026; https://github.com/openai/openai-agents-js/blob/main/docs/src/content/docs/guides/human-in-the-loop.mdx, 2025-2026]。
- 【事实】2026 年 developers.openai.com 新增 "Guardrails and human review"（agents API 层面的 guardrail + 人工审批指南）[来源: https://developers.openai.com/api/docs/guides/agents/guardrails-approvals, 2026]。
- 【推断】HITL 主要靠应用层实现（工具层拦截 + 审批），SDK 无类 hooks 的生命周期原语，属于"轻量 HITL"。

### 守卫与评估
- 【事实】内置 **输入/输出 guardrail 函数**（输出 guardrail 会以结构化方式校验并支持抛出 TripwireTriggeredException 终止运行）；guardrail 在 tracing 中生成独立 `guardrail_span` [来源: https://github.com/openai/openai-agents-python/blob/main/docs/tracing.md, 2025-2026]。
- 【事实】2026 年 developers.openai.com 上线 agent-evals 指南（评估 agent 性能）[来源: https://developers.openai.com/api/docs/guides/agent-evals.md, 2026]。

### 可观测性
- 【事实】**内置 tracing，默认开启**，无需额外配置；span 覆盖 LLM generation、工具调用、handoff、guardrail、语音（transcription/speech）等；traces 可在 **platform.openai.com/traces** 在线查看/调试/监控（生产与开发均可用）[来源: https://github.com/openai/openai-agents-python/blob/main/docs/tracing.md, 2025-2026]。
- 【事实】可通过自定义 trace processor 将 traces 转发到其他目的地（替代或并存）；Zero Data Retention（ZDR）策略的组织不可用官方 tracing [来源: 同上, 2025-2026]。

### 成本控制
- 【事实】SDK 自动跟踪每次运行的 token 用量：requests、input/output/total tokens、per-request 明细、cached tokens、reasoning tokens；经 `result.context_wrapper.usage` 读取；官方文档明确此数据"可用于监控成本、强制执行限制、记录分析" [来源: https://github.com/openai/openai-agents-python/blob/main/docs/usage.md, 2026]。
- 【未证实】未发现独立的一键"预算上限（budget cap）"API 原语；社区存在"agent 成本失控"的讨论，成本上限多靠应用层实现 [来源: https://community.openai.com/t/has-anyone-actually-solved-runaway-agent-costs-looking-for-patterns-beyond-logging/1383094, 2026]（该帖子为社区讨论，仅佐证现状）。

### 许可证与生态
- 【事实】**MIT 许可证**（LICENSE: Copyright (c) 2025 OpenAI；pyproject license = "MIT"）[来源: https://github.com/openai/openai-agents-python/blob/main/LICENSE, 2025; https://github.com/openai/openai-agents-python/blob/main/pyproject.toml, 2026]。
- 【事实】生态绑定：Responses API 逐步取代 Chat Completions 成为 OpenAI 官方推荐（SDK 默认模型适配器）；支持 o 系列推理模型（usage 明细含 reasoning tokens）；模型适配器支持 AnyLLM / LiteLLM 接入第三方模型 [来源: https://github.com/openai/openai-agents-python/blob/main/docs/usage.md, 2026; https://github.com/openai/openai-agents-python/blob/main/pyproject.toml, 2026]。

### 2025-2026 关键动态
- 【事实】2025-03-11 发布并取代 Swarm；2025-06 官方发布客服/应用测试 agent 演示 [来源: https://community.openai.com/t/new-tools-for-building-agents-responses-api-web-search-file-search-computer-use-and-agents-sdk/1140896, 2025; https://gihyo.jp/article/2025/06/openai-agent-demo, 2025]。
- 【事实】2026 年：0.8→0.22 高频迭代（0.22.0 于 2026-08-19）；v0.14 Sandbox Agents（沙盒执行）GA；新增 guardrails-and-human-review、agent-evals 指南；第三方（如 respan）称 2026 年 Swarm 已基本退出历史舞台 [来源: https://pypi.org/pypi/openai-agents/json, 2026; https://dev.to/_46ea277e677b888e0cd13/openai-agents-sdk-v014-sandbox-agents-and-the-model-native-harness-go-ga-49ej, 2026; https://www.respan.ai/articles/is-openai-swarm-still-worth-using, 2026]。

### 来源列表（OpenAI）
1. New tools for building agents: Responses API, web search, file search, computer use, and Agents SDK — OpenAI Developer Community（2025）https://community.openai.com/t/new-tools-for-building-agents-responses-api-web-search-file-search-computer-use-and-agents-sdk/1140896
2. OpenAI Agents SDK 官方文档（Python）— openai.github.io（2025-2026）https://openai.github.io/openai-agents-python/
3. openai/openai-agents-python — GitHub（pyproject.toml / LICENSE / docs/tracing.md / docs/usage.md / docs/sessions/index.md / docs/human_in_the_loop.md）（2025-2026）https://github.com/openai/openai-agents-python
4. PyPI: openai-agents（0.22.0, 2026-08-19）（2026）https://pypi.org/pypi/openai-agents/json
5. Release v0.19.0 / v0.20.0 — openai/openai-agents-python（2026）https://github.com/openai/openai-agents-python/releases
6. OpenAI Agents SDK v0.14 — Sandbox Agents and the Model-Native Harness Go GA — DEV Community（2026）https://dev.to/_46ea277e677b888e0cd13/openai-agents-sdk-v014-sandbox-agents-and-the-model-native-harness-go-ga-49ej
7. Guardrails and human review — OpenAI API docs（2026）https://developers.openai.com/api/docs/guides/agents/guardrails-approvals
8. Agent evals — OpenAI API docs（2026）https://developers.openai.com/api/docs/guides/agent-evals.md
9. Session memory cookbook — OpenAI developers（2025）https://developers.openai.com/cookbook/examples/agents_sdk/session_memory
10. Is OpenAI Swarm Still Worth Using in 2026? — Respan（2026）https://www.respan.ai/articles/is-openai-swarm-still-worth-using

---

## 二、Claude Agent SDK（Anthropic）

### 定位
- 【事实】Anthropic 官方 Agent SDK（Python 与 TypeScript），**2025-09-29** 随 Claude Sonnet 4.5 发布 [来源: https://www.pymnts.com/news/artificial-intelligence/2025/anthropic-claude-sonnet-4-5-introduces-claude-agent-sdk/, 2025; https://claude.com/blog/building-agents-with-the-claude-agent-sdk, 2025]。
- 【事实】本质上是 **Claude Code（agent loop）的编程化/无头（headless）封装**：Python 包自动捆绑 Claude Code CLI，`query()` 以异步迭代器返回消息 [来源: https://github.com/anthropics/claude-agent-sdk-python/blob/main/README.md, 2025-2026]。
- 【推断】因此它与 Claude Code 生态强绑定：SDK 能复用的能力（hooks、subagents、MCP、权限）即 Claude Code 的能力；业界有"Claude Agent SDK 取代早期 Claude Code SDK"的说法 [来源: https://tokenmix.ai/blog/claude-agent-sdk-replacement-guide-2026, 2026]。

### 当前版本
- 【事实】PyPI `claude-agent-sdk` 当前版本 **0.2.145**（2026-08-27 上传）[来源: https://pypi.org/pypi/claude-agent-sdk/json, 2026]。
- 【事实】⚠️ 注意：任务前提所述"当前版本 1.x"与事实不符——目前实际为 **0.2.x** 线（0.2.94 于 2026-06-08，0.2.99 于 2026-06-12，至 0.2.145）[来源: https://pypi.org/pypi/claude-agent-sdk/json, 2026]。
- 【事实】GitHub 仓库 `anthropics/claude-agent-sdk-python`（另有 TS/JS 版）[来源: https://github.com/anthropics/claude-agent-sdk-python, 2025-2026]。

### 编排模型
- 【事实】编程接口以 `query()` / Agent 选项为主：`ClaudeAgentOptions`（system_prompt、max_turns、cli_path 等）；底层复用 Claude Code 的 agent 循环与工具集（Read/Write/Edit/Bash 等）[来源: https://github.com/anthropics/claude-agent-sdk-python/blob/main/README.md, 2025-2026]。
- 【事实】**hooks 生命周期**：PreToolUse / PostToolUse / UserPromptSubmit / SubagentStart / Stop 等 hook 类型，与 Claude Code 同源 [来源: https://code.claude.com/docs/en/hooks, 2025-2026; https://github.com/takazudo/claude-resources/blob/main/skills/agents-sdk/references/human-in-the-loop.md, 2025]。
- 【事实】**subagents**：Claude Code 支持自定义 subagent（可为 subagent 单独定义 hooks），SDK 层面可触发/管理子代理 [来源: https://code.claude.com/docs/en/sub-agents, 2025-2026]。
- 【事实】**MCP 支持**：继承 Claude Code 的 MCP 集成能力；权限体系含 `permission_mode`、`can_use_tool` 回调、`allowed_tools` / `disallowed_tools` 白/黑名单 [来源: https://github.com/anthropics/claude-agent-sdk-python/blob/main/README.md, 2025-2026; https://code.claude.com/docs/en/agent-sdk/permissions, 2025-2026]。

### HITL（人工介入）
- 【事实】hooks 返回 "ask" 会触发**权限提示**（permission prompt）转交用户；`can_use_tool` 回调可对工具调用做编程式人工/策略决策；官方文档有 permissions 指南，社区有 HITL 参考实现 [来源: https://code.claude.com/docs/en/hooks, 2025-2026; https://code.claude.com/docs/en/agent-sdk/permissions, 2025-2026; https://github.com/takazudo/claude-resources/blob/main/skills/agents-sdk/references/human-in-the-loop.md, 2025]。
- 【事实】GitHub issue #96 提出 "Permission tool"（显式权限工具）需求，说明社区对审批机制仍有诉求 [来源: https://github.com/anthropics/claude-agent-sdk-python/issues/96, 2025]。

### 守卫与评估
- 【事实】无独立 guardrail 函数 API；守卫主要通过 **hooks 拦截**（PreToolUse 前审批/改写）+ **权限策略**（permission_mode / can_use_tool / disallowed_tools）实现 [来源: https://code.claude.com/docs/en/agent-sdk/permissions, 2025-2026]。
- 【推断】官方未提供内置 evals 模块；agent 评估通常借助 LangSmith 等第三方。

### 可观测性
- 【事实】官方支持 **OpenTelemetry** 可观测性（Claude Code Docs "Observability" 章节，含中文版"使用 OpenTelemetry 进行可观测性"）[来源: https://code.claude.com/docs/zh-CN/agent-sdk/observability, 2025-2026; https://code.claude.com/docs/en/agent-sdk/observability, 2025-2026]。
- 【事实】**LangSmith 提供官方集成**：LangChain 文档页 "Trace Claude Agent SDK applications"，langsmith-sdk 内含 `integrations/claude_agent_sdk` 包 [来源: https://docs.langchain.com/langsmith/trace-claude-agent-sdk, 2025-2026; https://github.com/langchain-ai/langsmith-sdk/blob/main/python/langsmith/integrations/claude_agent_sdk/__init__.py, 2025-2026]。
- 【事实】**Arize OpenInference** 提供 `openinference-instrumentation-claude-agent-sdk` 插桩包 [来源: https://github.com/Arize-ai/openinference/blob/main/js/packages/openinference-instrumentation-claude-agent-sdk/README.md, 2025-2026]。
- 【未证实】Anthropic 自有的 traces 在线看板/云 telemetry 产品（除 OpenTelemetry 导出外）本轮未证实。

### 成本控制
- 【事实】SDK 事件流中包含消息级 usage/token 信息（响应消息携带 usage 字段）[来源: 官方 SDK 文档 platform.claude.com/docs/en/agent-sdk/python, 2025-2026]（本轮通过 README/文档间接确认，细节标注为部分证实）。
- 【未证实】未发现独立"预算/成本上限"API 原语；max_turns 可作运行步数限制 [来源: https://github.com/anthropics/claude-agent-sdk-python/blob/main/README.md, 2025-2026]（max_turns 为【事实】；预算原语为【未证实】）。

### 许可证与生态
- 【事实】**MIT 许可证**（LICENSE: Copyright (c) 2025 Anthropic, PBC）[来源: https://github.com/anthropics/claude-agent-sdk-python/blob/main/LICENSE, 2025]。
- 【事实】生态：Claude Code 为 Anthropic 主推的编码 agent 产品（2025 年大规模采用），Agent SDK 是其可编程接口；Anthropic 是 **MCP（Model Context Protocol）** 生态的发起方之一，SDK 原生消费 MCP 工具 [来源: https://code.claude.com/docs/en/agent-sdk, 2025-2026; https://www.pymnts.com/news/artificial-intelligence/2025/anthropic-claude-sonnet-4-5-introduces-claude-agent-sdk/, 2025]。
- 【推断】2026 年出现面向"headless agents 生产化"的生态研究与实践（Atlas 等）[来源: https://github.com/Laoujin/Atlas/blob/main/research/2026-06-03-extending-claude-code-session-4-authoring-craft-operating-at-scale/claude-agent-sdk-headless-agents/index.md, 2026]。

### 2025-2026 关键动态
- 【事实】2025-09-29 发布（与 Claude Sonnet 4.5 同期）；2025-10 起高频迭代（v0.1.77 等）[来源: https://github.com/anthropics/claude-agent-sdk-python/blob/v0.1.77/LICENSE, 2025; https://www.pymnts.com/news/artificial-intelligence/2025/anthropic-claude-sonnet-4-5-introduces-claude-agent-sdk/, 2025]。
- 【事实】2026 年迭代至 0.2.145（2026-08-27）；文档迁至 platform.claude.com/docs/en/agent-sdk/python；权限/钩子/hitl 能力持续完善 [来源: https://pypi.org/pypi/claude-agent-sdk/json, 2026; https://github.com/anthropics/claude-agent-sdk-python/blob/main/README.md, 2026]。

### 来源列表（Claude）
1. Claude Agent SDK 官方文档 — platform.claude.com / code.claude.com（2025-2026）https://platform.claude.com/docs/en/agent-sdk/python ；https://code.claude.com/docs/en/agent-sdk
2. anthropics/claude-agent-sdk-python — GitHub（README / LICENSE / issues）（2025-2026）https://github.com/anthropics/claude-agent-sdk-python
3. PyPI: claude-agent-sdk（0.2.145, 2026-08-27）（2026）https://pypi.org/pypi/claude-agent-sdk/json
4. Anthropic Launches Claude Sonnet 4.5 and Introduces Claude Agent SDK — PYMNTS（2025-09-29）https://www.pymnts.com/news/artificial-intelligence/2025/anthropic-claude-sonnet-4-5-introduces-claude-agent-sdk/
5. Building agents with the Claude Agent SDK — Anthropic（2025）https://claude.com/blog/building-agents-with-the-claude-agent-sdk
6. Hooks reference — Claude Code Docs（2025-2026）https://code.claude.com/docs/en/hooks
7. Configure permissions — Claude Code Docs（2025-2026）https://code.claude.com/docs/en/agent-sdk/permissions
8. Observability（OpenTelemetry）— Claude Code Docs（2025-2026）https://code.claude.com/docs/en/agent-sdk/observability
9. Trace Claude Agent SDK applications — LangChain/LangSmith Docs（2025-2026）https://docs.langchain.com/langsmith/trace-claude-agent-sdk
10. OpenInference instrumentation for Claude Agent SDK — Arize（2025-2026）https://github.com/Arize-ai/openinference
11. Create custom subagents — Claude Code Docs（2025-2026）https://code.claude.com/docs/en/sub-agents

---

## 三、Google ADK（Agent Development Kit）

### 定位
- 【事实】Google 官方开源的 agent 开发框架，**2025 年 4 月**在 Google Cloud Next 2025 期间发布（与 A2A 协议、Ironwood TPU 等同批宣布）[来源: https://www.techtarget.com/searchenterpriseai/news/366622027/Google-intros-tools-for-building-agents-and-a-new-protocol, 2025; https://developers.googleblog.com/en/agent-development-kit-easy-to-build-multi-agent-applications/, 2025]。
- 【事实】⚠️ 核实结论：**ADK 与 Gemini 3 并非同期发布**——ADK 首发于 2025 年 4 月（Gemini 2.5 时代），**Gemini 3 于 2025 年 11 月**才发布 [来源: https://aibusiness.com/foundation-models/google-out-with-gemini-3-foundation-model, 2025]。
- 【推断】ADK 首发具体日期为 2025-04-09 前后（Cloud Next 2025 为 4 月 9-11 日），精确日期待核实。

### 当前版本
- 【事实】PyPI `google-adk` 当前版本 **2.8.0**（2026-08-26 上传）；2026 年版本线 2.6→2.8 高频迭代（2.6.1@2026-07-31、2.7.0@2026-08-13、2.8.0@2026-08-26）[来源: https://pypi.org/pypi/google-adk/json, 2026]。
- 【事实】GitHub 仓库 `google/adk-python`；**ADK 2.0** 于 2026 年推出（v2.0.0b1 起），引入图式工作流等新能力；多语言覆盖 Python/TypeScript/Go/Java [来源: https://newreleases.io/project/github/google/adk-python/release/v2.0.0b1, 2026; https://github.com/google/adk-docs/blob/main/docs/callbacks/types-of-callbacks.md, 2025-2026]。

### 架构与编排模型
- 【事实】**Agent 层级架构**：`BaseAgent` 派生 `LlmAgent`、`SequentialAgent`（顺序流）、`ParallelAgent`（并行流）、`LoopAgent`（循环流）等，可组合成**层级多智能体（hierarchical agents）**；支持 sub-agent 与 **transfer**（agent 间转移/转交）[来源: https://github.com/google/adk-python/blob/main/.agents/skills/adk-architecture/SKILL.md, 2025-2026; https://github.com/google/adk-docs/blob/main/docs/callbacks/types-of-callbacks.md, 2025-2026]。
- 【事实】**ADK 2.0 新增 graph-based workflow 引擎**（确定性图编排，DAG），并宣称内建 human-in-the-loop 与动态编排能力（Go 2.0 公告同款能力）[来源: https://developers.googleblog.com/announcing-adk-go-20/, 2026; https://adk.dev/2.0/, 2026]。
- 【事实】工具系统：function tools、MCP 工具、代码执行器等；**session/checkpoint**：会话状态可持久化、恢复与序列化（session state / checkpointing）[来源: https://github.com/google/adk-python/blob/main/.agents/skills/adk-architecture/SKILL.md, 2025-2026]。

### HITL（人工介入）
- 【事实】内置**生命周期回调机制**：`before_agent_callback` / `after_agent_callback`（所有 BaseAgent）、`before_model_callback` / `after_model_callback` / `on_model_error_callback` / `before_tool_callback` / `after_tool_callback` / `on_tool_error_callback`（LlmAgent），支持 sync/async 与回调列表；`before_model_callback` 可插入人工请求/审批 [来源: https://github.com/google/adk-docs/blob/main/docs/callbacks/types-of-callbacks.md, 2025-2026]。
- 【事实】ADK Go 2.0 公告明确"built-in human-in-the-loop"为 2.0 卖点；社区有 ADK HITL 示例（agent-runtime-patterns P6）[来源: https://developers.googleblog.com/announcing-adk-go-20/, 2026; https://github.com/vasundras/agent-runtime-patterns/blob/main/patterns/p6-human-in-the-loop/adk_example.py, 2025]。
- 【未证实】官方文档中"通过 `session.user_content_callback` 请求用户输入"的具体 API 命名，本轮未能在 adk-docs 仓库直接核实（AI Studio ADK 文档有 HITL 章节，建议后续核对 https://ai.google.dev/gemini-api/docs/adk）。

### 守卫与评估
- 【事实】内置 **evals 模块**（`adk.evaluation`，`adk eval` CLI）：两种模式——test files（单会话单元测试式，校验工具调用轨迹与中间/最终回答）与 datasets（批量评估）；评估维度覆盖**轨迹与工具使用**（groundtruth 与 rubric 两类指标）及**最终回答质量**（rubric/LLM-as-judge，如 rubric_based_final_response_quality）[来源: https://github.com/google/adk-docs/blob/main/docs/evaluate/index.md, 2025-2026]。
- 【事实】评估结果可与 Vertex AI Agent Engine 等托管平台联动（Google 官方 codelabs 亦演示 LLM-as-judge 评分）[来源: https://codelabs.developers.google.cn/agents-cli-agent-platform/agents-cli-agent-platform, 2025-2026]。

### 可观测性
- 【事实】基于 **OpenTelemetry** 的 tracing/可观测性；Arize 官方博客提供 "Tracing, Evaluation, and Observability for Google ADK" 指南（含 Arize Phoenix 集成）[来源: https://arize.com/blog/tracing-evaluation-and-observability-for-google-adk-how-to/, 2025]。
- 【事实】Google Cloud 侧与 **Vertex AI / Agent Engine** 深度集成（多系统 agent 的构建与管理）[来源: https://cloud.google.com/blog/en/products/ai-machine-learning/build-and-manage-multi-system-agents-with-vertex-ai, 2025-2026]。
- 【未证实】与 Cloud Trace / Langfuse 的具体官方集成文档本轮未直接核实（常见实践，但建议以官方文档为准）。

### 成本控制
- 【未证实】未发现官方"预算上限"原语；成本控制通常依赖用量监控 + 评估流程（evals）约束，具体机制待核实。

### 许可证与生态
- 【事实】**Apache License 2.0**（LICENSE 首页即 Apache License Version 2.0）[来源: https://github.com/google/adk-python/blob/main/LICENSE, 2025]。
- 【事实】生态：Gemini 开发者工具链（Gemini API / AI Studio / Gemini SDK）的一等公民；Vertex AI Agent Engine 托管；2025-04 与 **A2A（Agent2Agent）协议**同期发布；2026 年 ADK 2.0 / ADK Go 2.0 扩展至图式工作流 [来源: https://www.techtarget.com/searchenterpriseai/news/366622027/Google-intros-tools-for-building-agents-and-a-new-protocol, 2025; https://developers.googleblog.com/announcing-adk-go-20/, 2026]。

### 2025-2026 关键动态
- 【事实】2025-04：Cloud Next 2025 发布 ADK（与 A2A 协议、Ironwood TPU 同期）；2025 年：多语言 SDK（TS/Go/Java）扩展，开发者博客持续跟进 [来源: https://www.techtarget.com/searchenterpriseai/news/366622027/Google-intros-tools-for-building-agents-and-a-new-protocol, 2025; https://developers.googleblog.com/en/agent-development-kit-easy-to-build-multi-agent-applications/, 2025]。
- 【事实】2026 年：ADK 2.0（图式工作流、内建 HITL、动态编排）；google-adk 迭代至 2.8.0（2026-08-26）[来源: https://developers.googleblog.com/announcing-adk-go-20/, 2026; https://pypi.org/pypi/google-adk/json, 2026]。

### 来源列表（ADK）
1. Agent Development Kit: Making it easy to build multi-agent applications — Google Developers Blog（2025）https://developers.googleblog.com/en/agent-development-kit-easy-to-build-multi-agent-applications/
2. google/adk-python — GitHub（LICENSE / .agents/skills/adk-architecture/SKILL.md）（2025-2026）https://github.com/google/adk-python
3. google/adk-docs — GitHub（callbacks/types-of-callbacks.md；evaluate/index.md）（2025-2026）https://github.com/google/adk-docs
4. PyPI: google-adk（2.8.0, 2026-08-26）（2026）https://pypi.org/pypi/google-adk/json
5. ADK 2.0 文档 — adk.dev（2026）https://adk.dev/2.0/
6. Announcing ADK Go 2.0 — Google Developers Blog（2026）https://developers.googleblog.com/announcing-adk-go-20/
7. Google intros agent building tools and an agent protocol — TechTarget（2025）https://www.techtarget.com/searchenterpriseai/news/366622027/Google-intros-tools-for-building-agents-and-a-new-protocol
8. Tracing, Evaluation, and Observability for Google ADK — Arize（2025）https://arize.com/blog/tracing-evaluation-and-observability-for-google-adk-how-to/
9. Build and manage multi-system agents with Vertex AI — Google Cloud Blog（2025）https://cloud.google.com/blog/en/products/ai-machine-learning/build-and-manage-multi-system-agents-with-vertex-ai
10. Google Aims to Lead AI with Gemini 3 Foundation Model — AI Business（2025-11）https://aibusiness.com/foundation-models/google-out-with-gemini-3-foundation-model
11. Human in the Loop — Google ADK（社区示例, 2025）https://github.com/vasundras/agent-runtime-patterns/blob/main/patterns/p6-human-in-the-loop/adk_example.py

---

## 四、横向速览（供报告引用）

| 维度 | OpenAI Agents SDK | Claude Agent SDK | Google ADK |
|---|---|---|---|
| 发布 | 2025-03-11（取代 Swarm） | 2025-09-29（随 Sonnet 4.5） | 2025-04（Cloud Next 2025，非 Gemini 3 同期） |
| 当前版本（2026-08） | openai-agents 0.22.0 | claude-agent-sdk 0.2.145 | google-adk 2.8.0（2.0 系） |
| 语言 | Python / TS | Python / TS | Python / TS / Go / Java |
| 许可证 | MIT | MIT | Apache-2.0 |
| 编排原语 | Agent + Runner + handoffs + sessions | Agent/query + hooks + subagents（复用 Claude Code） | BaseAgent 层级 + flows（sequential/parallel/loop）+ graph（2.0）+ transfers |
| HITL | 工具中断/人工审批指南 | hooks（"ask" 权限提示）+ can_use_tool | 生命周期回调 + 2.0 内建 HITL |
| 守卫/评估 | 输入/输出 guardrail 函数；2026 新增 agent-evals | hooks 拦截 + 权限策略；无内置 evals | 内置 evals（轨迹/LLM-as-judge）+ `adk eval` CLI |
| 可观测性 | 内置 tracing（默认开）+ Traces 在线看板 | OpenTelemetry 官方支持 + LangSmith/Arize 集成 | OpenTelemetry + Arize/Vertex AI 集成 |
| 成本控制 | 自动 usage 跟踪（可读、可做限制）；无预算原语 | 事件含 usage；max_turns；无预算原语 | 未见预算原语 |
| 生态锚点 | Responses API + o 系列 + MCP | Claude Code + MCP 发起方 | Gemini/AI Studio + Vertex AI + A2A |

---

## 五、遗留待核实事项（【未证实】汇总）
1. OpenAI Agents SDK 是否出现独立的"预算上限（budget）"API 原语（当前只见 usage 跟踪）。
2. Anthropic 是否有自有的云端 traces 看板/telemetry 托管产品（官方仅确认 OpenTelemetry 导出 + 第三方集成）。
3. ADK 官方 `session.user_content_callback` 等 HITL API 的确切命名（adk-docs 仓库未直接命中）。
4. ADK 与 Cloud Trace / Langfuse 的官方集成文档。
5. ADK 首发精确日期（4 月 9 日前后为推断）。
6. OpenAI Agents SDK 1.0 稳定版发布时间（当前仍 0.x）。
