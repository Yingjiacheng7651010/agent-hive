# 特别调研：AI 生成架构安全验证产品盘点 + 「首脑统筹」组合行业对照

> 调研范围：截至 **2026 年 8 月**（含 2025 下半年新动向）
> 调研方式：12 次 web_search（2026 年 8 月执行），以一手来源（官方博客/文档/仓库/arXiv）优先，二手来源明确标注
> 标注约定：每条结论区分【事实】（来源可核）/【推断】（基于事实的分析）/【未证实】（未找到可核来源）；`[来源: URL]` + 年份
> 背景参照物：agent-hive = 首脑统筹（orchestrator）+ 角色专家（role agents）+ 契约工作包（contracts：接口契约/expected_output/depends_on）+ 评估-优化回路（验收不过自动回流，≤3 轮）；另有 DeepSec 启发的「AI 生成架构安全验证」模块（规则引擎：幻觉引用/循环依赖/缺失安全控制 + LLM 语义威胁建模 STRIDE，插入审批关口前）

---

## Part A：市面上「AI 生成架构/设计的安全验证」类产品盘点

### A1. DeepSec 系

| 项目 | 定位 | 相关度 | 来源/年份 |
|---|---|---|---|
| Vercel deepsec（noeljackson/deepsec） | 基于 coding agent 的代码库漏洞扫描安全 harness（semantic 扫描、定位并修复漏洞） | 高：与 agent-hive「AI 生成物安全验证」同为扫描-修复回路，但作用于**代码**而非架构/设计 | [Vercel 官方博客: Introducing deepsec](https://vercel.com/blog/introducing-deepsec-find-and-fix-vulnerabilities-in-your-code-base) 2025-08（博客存在【事实】；具体月份以任务方给定为准）；[noeljackson/deepsec](https://github.com/noeljackson/deepsec) 2025 |
| Unclecheng-li/DeepSec | "AI Security Offense & Defense Platform"：**Shield** 实时审计 AI 生成代码的**幻觉依赖包、缺失安全防护、AI 模式错误**；**Spear** 自动化授权渗透测试（40+ skill packs） | 极高：Shield 的「幻觉依赖包/缺失安全防护/AI 模式错误」三查与 agent-hive 规则引擎（幻觉引用/循环依赖/缺失安全控制）**同构**，且同为 Offense+Defense 双模块 | [github.com/Unclecheng-li/DeepSec](https://github.com/Unclecheng-li/DeepSec) 2025-2026【事实：仓库与描述存在】 |
| 同名镜像（zp6/umeshchandra-rao/felipetruman/stevewithington 等） | Vercel deepsec 的 fork/镜像传播 | 佐证 deepsec 热度，无独立价值 | [zp6/deepsec](https://github.com/zp6/deepsec) 等 2025【事实】 |
| Vercel 侧产品化核实 | 2026-05 报道：Vercel 作为「AI 开发时代 DevSecOps 自动化公司」将 deepsec 开源；DevOps.com 称其把 AI 安全扫描带入开发工作流 | 高：表明 deepsec 由商业工具转为开源，但**未见「Vercel AI Security」独立商业产品线的一手公告** | [atpartners.co.jp 报道](https://atpartners.co.jp/news/2026-05-11-vercel-a-devsecops-company-for-security-automation-in-the-age-of-ai-development-open-sources-its-ai-vulnerability-detection-tool-deepsec) 2026-05-11；[DevOps.com: Vercel's deepsec](https://devops.com/vercels-deepsec-brings-ai-powered-security-scanning-into-the-development-workflow/) 2025-2026【事实：报道存在】 |

**A1 小结**：【事实】deepsec（Vercel）与 DeepSec（Unclecheng-li）两个同名项目确实存在，前者聚焦「coding agent 扫描代码漏洞」，后者（Shield）聚焦「AI 生成物特有缺陷」（幻觉依赖包/缺失防护/AI 模式错误）——后者与 agent-hive 的规则引擎查幻觉引用/循环依赖/缺失安全控制高度对应。【推断】但二者均作用于**已生成的代码/依赖**层面，未见专门验证「AI 生成的架构/设计方案（设计文档、依赖图、威胁模型）」并插入审批关口前的产品化形态。【未证实】「Vercel AI Security」作为独立产品线的官方公告未检索到。

### A2. 架构威胁建模 agent 与 AI 应用安全扫描

**威胁建模平台（AI 辅助）**
- **IriusRisk「Jeff: AI Assistant」**：AI 辅助威胁建模（对话生成/完善威胁模型）。【事实】[Global Security Mag 报道](https://www.globalsecuritymag.fr/iriusrisk-has-announced-the-launch-of-jeff-ai-assistant.html)（年份未从来源确认，约 2024-2025，具体日期【未证实】）；配套 CLI [iriusrisk-cli (PyPI)](https://pypi.org/project/iriusrisk-cli/)（AI-powered threat modeling integration）。
- **ThreatModeler AI**：AI 辅助威胁建模平台，持续更新（AI 相关功能见 What's New）。【事实】[threatmodeler.com/products/whats-new](https://threatmodeler.com/products/whats-new/)、[Platform](https://threatmodeler.com/products/platform/) 2025-2026。
- 与 agent-hive 对应关系：威胁建模平台覆盖「LLM 语义威胁建模 STRIDE」这一步的成熟商业替代，但**不内嵌于多智能体编排**，也不做「验收不过自动回流」的闭环。【推断】

**MITRE 相关工作**
- **MITRE ATLAS**（Adversarial Threat Landscape for Artificial-Intelligence Systems）：AI 威胁框架，非 agent 产品。【事实】[ATLAS 文档转载](https://github.com/Twodragon0/claudesec/blob/82f8f3dffcdf1625c755551c0f1b486713b2eb69/docs/ai/mitre-atlas.md)（框架存在）。
- **Agentic LLM 威胁狩猎（IEEE 2025）**：基于 MITRE ATT&CK 知识图谱的 agentic 威胁狩猎研究。【事实】[IEEE Xplore 论文](https://ieeexplore.ieee.org/document/11518378) 2025。

**微软 Security Copilot**
- Agentic SOC 方向（Security Copilot Agents）。【事实】[azinsider 博客: Microsoft Security Copilot Agents](https://blog.azinsider.net/microsoft-security-copilot-agents-inside-the-agentic-soc-fcf7bd081afd)。
- 微软发布开源「AI agent 网络安全调查评测基准」。【事实】[SC World 报道](https://www.scworld.com/news/microsoft-announces-open-source-benchmark-for-ai-agent-cybersecurity-investigations) 2025。
- 「架构评审类能力（如对设计文档做威胁评审）」：未直接检索到 Copilot 官方架构评审功能文档 →【未证实】。

**OWASP**
- **OWASP Top 10 for LLM Applications (2025)**：2025 版已发布（LLM01-LLM10，含供应链、过度代理等）。【事实】[genai.owasp.org TOP 10 下载页](https://genai.owasp.org/download/45674/) 2025。
- **OWASP Top Ten AI Agent Threats**：2025-12 发布 Agentic AI 威胁清单（agent 特有风险）。【事实】[Security Boulevard 报道](https://securityboulevard.com/2025/12/owasp-project-publishes-list-of-top-ten-ai-agent-threats/) 2025-12；配套规则包 [agent-threat-rules (npm)](https://socket.dev/npm/package/agent-threat-rules/overview/3.5.11)。
- 对应关系：这两份清单可作为 agent-hive 安全验证模块的**规则来源/检查项清单**，但清单本身不是验证产品。【事实→推断】

**AI 防火墙 / 运行时防护**
- **Cloudflare for AI**（含 AI 防火墙）：保护 AI 模型/应用/数据。【事实】[codezine 报道](https://codezine.jp/news/detail/21219)；[Delphi Security 2026 综述: Best AI Firewalls](https://delphisecurity.ai/blog/best-ai-firewalls-2026) 2026。
- **Lakera Guard / Prompt Guard**：LLM 输入输出防护（广泛产品，本调研未取一手官方页 → 定位为【事实：行业内知名品类，经 2026 综述间接佐证】）。【未证实：具体官方 URL 未在本轮检索中核实】
- **rebuff**：提示注入防护开源项目，本轮未检索到来源 →【未证实】。
- **NVIDIA NeMo Guardrails** 与 **Protect AI**（guardrails/供应链安全）对比市场。【事实】[respan.ai 对比页](https://www.respan.ai/market-map/compare/nemo-guardrails-vs-protect-ai) 2026。

**红队 / 扫描器**
- **garak（NVIDIA）** 与 **PyRIT（微软红队）** 属于开源 LLM 漏洞扫描器主流；ICSE 2025 RAIE 论文对开源 LLM 漏洞扫描器做了比较研究（含能力与缺口）。【事实】[ICSE 2025 RAIE 论文](https://conf.researchr.org/details/icse-2025/raie-2025-papers/7/Insights-and-Current-Gaps-in-Open-Source-LLM-Vulnerability-Scanners-A-Comparative-An) 2025。
- **Robust Intelligence → Cisco**：Cisco 收购 Robust Intelligence（2024）后并入 AI 安全路线；2025-2026 状态：Cisco「Foundation AI」安全战略延续其检测能力。【事实：Cisco 官方博客 [Foundation AI](https://blogs.cisco.com/security/foundation-ai-building-the-intelligent-future-of-cybersecurity)；[silicon.es 报道](https://www.silicon.es/cisco-refuerza-la-seguridad-en-la-era-de-la-inteligencia-artificial-2567395)】【推断：具体产品线形态（原 Robust Intelligence 独立产品 vs 融合）以 Cisco 官方为准】
- **TrojAI**（模型木马扫描）、**Bedrock Guardrails**（AWS）：本轮未直接核实一手来源 →【未证实】（行业内知名，需官方页确认）。

**agent 安全评测基准（2025-2026 新增为主）**
- **AgentDojo**：动态环境评测 LLM agent 攻防（Debenedetti 等）。【事实】[Florian Tramèr 主页 publications](https://www.floriantramer.com/publications/agentdojo24/) 2024-2025；[agentdojo PyPI](https://pypi.org/project/agentdojo/0.1.18/)。
- **AgentThreatBench**：评测 LLM agent 对 OWASP Agentic Threats 的韧性（英国政府 BEIS inspect_evals）。【事实】[inspect_evals 页面](https://ukgovernmentbeis.github.io/inspect_evals/evals/agent_threat_bench/) 2025-2026。
- **AgentBench**：通用 agent 评测。【事实】[inspect_evals AgentBench 页](https://ukgovernmentbeis.github.io/inspect_evals/evals/agent_bench/index.html)。
- **HarmBench**：越狱/红队基准，本轮仅获二手提及（中文文章称现有越狱基准覆盖不足）→【事实：基准存在，二手佐证】[今日头条文章（间接）](https://m.toutiao.com/article/7643643582066295323/) 2025-2026；【未证实：本轮未取一手论文页】。
- **InspectorBench（微软）**：2025 年发布、评测 agent 完成真实用户任务；本轮未直接检索到论文/官方页 →【未证实】（微软 agent 安全评测相关见上 [SC World 报道](https://www.scworld.com/news/microsoft-announces-open-source-benchmark-for-ai-agent-cybersecurity-investigations)）。

### A3. contract-driven development agents（契约驱动开发 agent）

- **GitHub Spec Kit（github/spec-kit）**：「Spec-Driven Development」工具包，帮助用规范驱动开发（workspace → spec → plan → 实现）。【事实】[github.com/github/spec-kit](https://github.com/github/spec-kit) 2025-09 开源（[atmarkit 报道](https://atmarkit.itmedia.co.jp/ait/articles/2509/09/news014.html) 2025-09）；[Xebia 解读: Building Software With Spec Kit](https://xebia.com/blog/building-software-with-spec-kit/) 2025。
- **ADR agents**：微软开源项目 hve-core 的 issue「集成 System Architecture Reviewer，用于 ADR 创建与技术决策文档」——企业级「架构评审 agent + ADR」的真实需求实例。【事实】[microsoft/hve-core#92](https://github.com/microsoft/hve-core/issues/92)。
- **阶段判断**：【事实】成熟商业「契约驱动开发 agent」产品未见；【推断】该方向处于早期：工具侧以 spec-first 脚手架（spec-kit）为主，agent 侧以企业自研（如 hve-core 类）和编码 agent 的 plan 能力为主，尚无把「契约（接口/expected_output/depends_on）+ 自动验收回流」产品化为通用契约层的商业产品。

### A4. Part A 结论

- 【事实】三个相邻赛道均有成熟/近成熟产品：① AI 生成**代码**安全扫描（Vercel deepsec：2025-08 发布、2026-05 开源；Unclecheng-li DeepSec Shield 直击幻觉依赖包/缺失防护/AI 模式错误）；② LLM/agent 运行时防护与红队（Cloudflare for AI、Lakera、garak、PyRIT、Cisco Foundation AI）；③ 威胁建模辅助（IriusRisk Jeff、ThreatModeler AI、OWASP LLM Top10 2025 + Agentic Threats 2025-12、MITRE ATLAS、AgentDojo/AgentThreatBench 等基准）。
- 【推断】专门针对「AI 生成的**架构/设计方案**」做「规则引擎 + LLM 语义威胁建模」双通道验证、并与多智能体编排深度耦合、插入审批关口前的产品，**未发现直接商业对标**；现有产品要么作用于代码/运行时，要么独立于编排流水线。agent-hive 安全验证模块的差异化空间 = 架构级（非代码级）+ 编排内嵌 + 审批关口 + 与验收回流联动。
- 【未证实】「Vercel AI Security」独立产品线、TrojAI/Bedrock Guardrails/rebuff 等的一手页面、InspectorBench 官方来源，本轮未核实。

---

## Part B：「首脑统筹 + 角色专家 + 契约工作包 + 评估优化回路」组合的行业出现情况

### B1. MetaGPT —— 最接近的组合先行者

- 机制：**SOP（标准化作业程序）驱动** + 角色分工（PM/架构师/工程师/QA）+ **结构化通信协议**（消息池、assembly-line 范式、结构化输出传递）+ 需求反馈回路；仓库定位「给一行需求，返回 PRD、设计、任务、仓库」。
- 与组合对应：角色专家（✓ 多角色 agent 并行）；契约工作包（△ 结构化消息/共享产出物近似契约，但无显式 expected_output/depends_on 字段）；评估优化回路（△ 论文含反馈/迭代环节，非「验收-回流≤3轮」的强闭环）。
- 【事实】[arXiv 2308.00352: MetaGPT: Meta Programming for Multi-Agent Collaborative Framework](https://arxiv.org/abs/2308.00352v2) 2023-08（后续更新至 2024）；仓库（镜像 [voidking/MetaGPT](https://github.com/voidking/MetaGPT)、[stophobia/MetaGPT](https://github.com/stophobia/MetaGPT) 等）持续维护。

### B2. CrewAI —— 角色 crew + 事件驱动 Flows + 任务依赖 + 人工输入

- 机制：role-based crews（角色化 agent 团队）；**Flows**（事件驱动编排，处理跨 crew 复杂流程）；任务 **context/dependency**（任务间上下文与依赖）；human input（人工介入点）。
- 与组合对应：角色专家（✓ crews）；契约工作包（△ task context/dependency ≈ depends_on 雏形，无强类型 expected_output 契约层）；评估优化回路（△ 社区诉求：issue「Auto Improvement Agentic Pipeline」2025 提出自动改进流水线，说明自校正回路在 CrewAI 尚非核心内置）。
- 【事实】[crewai PyPI](https://pypi.org/project/crewai/0.203.1/) 2025；[CrewAI Flows 文档](https://docs.crewai.com/en/enterprise/features/webhook-streaming)（企业功能页，2025-2026）；[crewAIInc/crewAI#3015](https://github.com/crewAIInc/crewAI/issues/3015) 2025。

### B3. LangGraph —— supervisor 模式 + 状态契约 + HITL + checkpoint

- 机制：官方 **langgraph-supervisor**（create_supervisor 快速构建首脑-子代理）；multi-agent patterns（supervisor/层级/网络式）；状态契约（TypedDict state schema）；**interrupt**（HITL 挂起/恢复）；**checkpointer**（状态持久化/断点续跑）。
- 与组合对应：首脑统筹（✓ supervisor 即官方首脑模式）；角色专家（✓ subagents）；契约工作包（△ state schema 是强类型契约，但面向图状态而非「工作包」语义）；评估优化回路（△ 无内建验收-回流，需自建图回路——恰是 agent-hive 用 contracts + 回流实现的部分）。
- 【事实】[langgraph-supervisor 参考文档](https://reference.langchain.com/python/langgraph-supervisor) 2025；[interrupt 文档](https://reference.langchain.com/python/langgraph/types/interrupt) 2025；多智能体模式综述（社区维护 [multi-agent-patterns.md](https://github.com/SpillwaveSolutions/mastering-langgraph-agent-skill/blob/main/references/multi-agent-patterns.md)）。

### B4. 其他编排框架

| 框架 | 机制 | 与组合的对应 | 来源/年份 |
|---|---|---|---|
| AutoGen / AG2 | GroupChat **speaker selection 管理器（manager）≈ 首脑**；**user proxy ≈ HITL**；自定义 GroupChat flows | 首脑统筹 ✓；HITL ✓；契约/回流 △ | [AG2 docs: Custom GroupChat flows](https://docs.ag2.ai/latest/docs/user-guide/advanced-concepts/groupchat/custom-group-chat/) 2025；[martimfasantos/ai-agents-frameworks AG2 示例](https://github.com/martimfasantos/ai-agents-frameworks/blob/main/ag2/04_multi_agent.py) |
| Microsoft Agent Framework | **Teams + Sessions**（团队级多 agent 会话编排） | 首脑统筹 △（团队为容器，无强制 supervisor）；契约/回流 △ | [microsoft/agent-framework 讨论 #6858: Multi agent sessions](https://github.com/microsoft/agent-framework/discussions/6858) 2025；[learn.microsoft.com 构建指南](https://learn.microsoft.com/ka-ge/microsoftteams/platform/teams-sdk/in-depth-guides/ai-integrations/build-agent-microsoft-agent-framework) 2025 |
| OpenAI Agents SDK | **triage agent + handoffs**（交接式路由 ≈ 轻量首脑） | 首脑统筹 ✓（triage/handoffs）；契约 △ | [openai-agents-python docs/handoffs.md](https://github.com/openai/openai-agents-python/blob/db68d1c3/docs/handoffs.md) 2025 |
| Claude Agent SDK | **subagents + hooks**（子代理与生命周期钩子）；官方 Cookbook「chief of staff agent」示例 = 首脑式编排 | 首脑统筹 ✓（示例即首脑）；角色专家 ✓；契约/回流 △ | [Claude Cookbook: chief of staff agent](https://platform.claude.com/cookbook/claude-agent-sdk-01-the-chief-of-staff-agent) 2025-2026；[claude-agent-sdk-python commit: subagent 执行控制](https://github.com/anthropics/claude-agent-sdk-python/commit/bd6299617ffd5cd7250c8292dcd98dbb37ec6b5e) 2025 |
| Google ADK | **hierarchical agents + transfer**（层级 agent 与显式转移控制） | 首脑统筹 ✓（层级）；契约 △ | [google/adk-docs: multi-agents.md](https://github.com/google/adk-docs/blob/90250a53d8a8ba2671733b2c143a7888ba347766/docs/agents/multi-agents.md) 2025；[Google 论坛: Manually transfer to agent](https://discuss.google.dev/t/manually-transfer-to-agent/244748) 2025 |

### B5. 评估-优化回路（自校正循环）类

- **DSPy / TextGrad / AdalFlow**：prompt/程序自动优化框架族；PyCon DE 2025 演讲「Is Prompt Engineering Dead? How Auto-Optimization is Changing the Game」综述该趋势。【事实】[2025.pycon.de 演讲页](https://2025.pycon.de/talks/GURXPK/) 2025；[PyData Amsterdam 2025 同名演讲](https://cfp.pydata.org/pydata-amsterdam-2025/talk/9VD97Y/) 2025。
- **LangSmith evals + prompt optimization（Align Evals）**：评测 + 人类修正校准 + 持续优化闭环。【事实（二手综述）】[腾讯云文章第 15 篇：评估体系——Benchmark、Evals 与持续优化闭环](https://cloud.tencent.cn/developer/article/2724364) 2025-2026（二手来源，官方页未直接核实→具体 API 细节以官方为准）。
- **CrewAI 自校正**：见 B2（[issue #3015](https://github.com/crewAIInc/crewAI/issues/3015)，2025）——「自动改进 agentic pipeline」仍为特性诉求。
- 与组合对应：【事实】「评测→优化→回流」作为独立能力在 DSPy/LangSmith 等已成熟；【推断】但「验收不过自动回流重做，最多 N 轮」这种**强约束的验收契约回路**（非 prompt 优化、非软评测）未见框架级内置，多为自建。

### B6. 契约/工作包类（plan → work package → implement）

- **GitHub Copilot Workspace**：issue → 计划 → 实现 → PR 的 agentic 工作流。【事实】[GitHub Blog: From idea to PR](https://github.blog/ai-and-ml/github-copilot/from-idea-to-pr-a-guide-to-github-copilots-agentic-workflows/) 2025；[Java Code Geeks 2026-02: Copilot Workspace & The Agentic Era](https://www.javacodegeeks.com/2026/02/github-copilot-workspace-the-agentic-era.html) 2026-02；[pc.watch.impress.co.jp 报道](https://pc.watch.impress.co.jp/docs/news/1588521.html)。
- **Claude Code tasks / sub-agents**：任务分解 + 子代理执行（plan/do 分离）。【事实】[simonwillison.net: Claude Code sub-agents](https://simonwillison.net/2025/Oct/11/sub-agents/) 2025-10-11；[Claude Code agents 指南（社区）](https://github.com/ai-infra-curriculum/ai-agent-guidebook/blob/main/guides/claude-code/agents.md)。
- **Aider architect 模式**：ask/architect 双模式（architect 规划、code 实现）。【事实】[aider#3624: Can agent mode be added?](https://github.com/Aider-AI/aider/issues/3624)；[教程: ask/architect 模式重构](https://openclawhub.tools/tutorial/how-to-use-aider-to-refactor-a-python-repo-with-ask-and-architect-modes/) 2026。
- **Cursor agent mode**：官方文档未直接核实 →【未证实】（仅见第三方 MCP 工具支持列表提及 Cursor 等客户端，[devplan-mcp-server#113](https://github.com/mmorris35/devplan-mcp-server/issues/113)）。
- **spec-kit**：见 A3（spec 先行 + 计划 + 实现）。【事实】[github.com/github/spec-kit](https://github.com/github/spec-kit) 2025。
- **Plan-and-Solve / plan-and-execute 类论文**：Plan-and-Solve Prompting（Wang et al. 2023）为经典规划论文。【事实（论文引用佐证）】[arXiv 2305.04091（经 langchain arxiv_references 收录）](https://huggingface.co/spaces/anpigon/langchain-qa-bot/blame/857c8eec5a8e4596869e18383bcf8854607376c0/docs/langchain/docs/docs/additional_resources/arxiv_references.mdx) 2023；【推断】plan-and-execute 已内化为各编码 agent 的默认范式（Copilot/Claude Code/Aider），独立产品形态不再存在。
- 与组合对应：【事实】「工作包 = 计划切分 + 上下文 + 依赖」已普遍；【推断】「工作包带显式验收契约（expected_output）+ 失败自动回流」仍是 agent-hive 的特色组合。

### B7. Part B 结论

- 【事实】四大要素**每一项单独**都已在 2023-2026 年主流框架/产品中出现：首脑统筹（LangGraph supervisor、AutoGen manager、Claude Cookbook chief-of-staff、Google ADK 层级、OpenAI triage）；角色专家（MetaGPT SOP 分工、CrewAI crews、各 SDK subagents）；契约/工作包（LangGraph state schema、CrewAI task context/dependency、Copilot Workspace/Claude Code/Aider 的 plan→work package、spec-kit 的 spec-first）；评估优化回路（MetaGPT 反馈、DSPy/TextGrad/AdalFlow 自动优化、LangSmith evals+prompt optimization、CrewAI 自校正诉求）。
- 【推断】**组合本身正快速趋同**：2025-2026 各大框架都在向「orchestrator + 角色 + 结构化交接 + 评测闭环」补齐（CrewAI 加 Flows、微软加 Teams/Sessions、Anthropic 出 subagents+hooks）。agent-hive 的相对差异点不在「有没有这些机制」，而在三点产品化取舍：① **显式契约字段**（接口契约/expected_output/depends_on 作为一等公民，而非隐含状态）；② **验收-回流≤3 轮的强闭环**（而非软评测/prompt 优化）；③ **架构安全验证模块内嵌审批关口**（Part A 结论：无直接商业对标）。这三点的组合未见行业完全同构产品（截至 2026-08）。
- 【未证实】是否存在 2026 年 H2 新发布的、与 agent-hive 完全同构的商业/开源产品，本调研未覆盖（检索窗口有限）。

---

## 附：主要来源清单

1. [Vercel Blog: Introducing deepsec](https://vercel.com/blog/introducing-deepsec-find-and-fix-vulnerabilities-in-your-code-base)（2025-08，任务方给定日期）
2. [noeljackson/deepsec](https://github.com/noeljackson/deepsec)（2025）
3. [Unclecheng-li/DeepSec](https://github.com/Unclecheng-li/DeepSec)（2025-2026）
4. [atpartners.co.jp: Vercel 开源 deepsec](https://atpartners.co.jp/news/2026-05-11-vercel-a-devsecops-company-for-security-automation-in-the-age-of-ai-development-open-sources-its-ai-vulnerability-detection-tool-deepsec)（2026-05-11）
5. [DevOps.com: Vercel's deepsec](https://devops.com/vercels-deepsec-brings-ai-powered-security-scanning-into-the-development-workflow/)
6. [IriusRisk Jeff: AI Assistant（Global Security Mag）](https://www.globalsecuritymag.fr/iriusrisk-has-announced-the-launch-of-jeff-ai-assistant.html)
7. [ThreatModeler What's New](https://threatmodeler.com/products/whats-new/) / [Platform](https://threatmodeler.com/products/platform/)
8. [OWASP LLM Top 10 (2025)](https://genai.owasp.org/download/45674/)；[OWASP Top Ten AI Agent Threats（Security Boulevard）](https://securityboulevard.com/2025/12/owasp-project-publishes-list-of-top-ten-ai-agent-threats/)（2025-12）
9. [Cloudflare for AI（codezine）](https://codezine.jp/news/detail/21219)；[Delphi: Best AI Firewalls 2026](https://delphisecurity.ai/blog/best-ai-firewalls-2026)
10. [ICSE 2025 RAIE: 开源 LLM 漏洞扫描器比较研究](https://conf.researchr.org/details/icse-2025/raie-2025-papers/7/Insights-and-Current-Gaps-in-Open-Source-LLM-Vulnerability-Scanners-A-Comparative-An)
11. [Cisco Blog: Foundation AI](https://blogs.cisco.com/security/foundation-ai-building-the-intelligent-future-of-cybersecurity)；[silicon.es](https://www.silicon.es/cisco-refuerza-la-seguridad-en-la-era-de-la-inteligencia-artificial-2567395)
12. [AgentDojo（Tramèr publications）](https://www.floriantramer.com/publications/agentdojo24/)；[agentdojo PyPI](https://pypi.org/project/agentdojo/0.1.18/)
13. [AgentThreatBench（UK BEIS inspect_evals）](https://ukgovernmentbeis.github.io/inspect_evals/evals/agent_threat_bench/)；[AgentBench](https://ukgovernmentbeis.github.io/inspect_evals/evals/agent_bench/index.html)
14. [github/spec-kit](https://github.com/github/spec-kit)（2025-09）；[atmarkit 报道](https://atmarkit.itmedia.co.jp/ait/articles/2509/09/news014.html)；[Xebia 解读](https://xebia.com/blog/building-software-with-spec-kit/)
15. [microsoft/hve-core#92: System Architecture Reviewer for ADR](https://github.com/microsoft/hve-core/issues/92)
16. [MetaGPT 论文（arXiv 2308.00352）](https://arxiv.org/abs/2308.00352v2)（2023）
17. [CrewAI PyPI](https://pypi.org/project/crewai/0.203.1/)（2025）；[crewAI#3015 Auto Improvement Pipeline](https://github.com/crewAIInc/crewAI/issues/3015)（2025）
18. [langgraph-supervisor 官方文档](https://reference.langchain.com/python/langgraph-supervisor)（2025）；[interrupt](https://reference.langchain.com/python/langgraph/types/interrupt)
19. [AG2: Custom GroupChat flows](https://docs.ag2.ai/latest/docs/user-guide/advanced-concepts/groupchat/custom-group-chat/)
20. [microsoft/agent-framework#6858: Multi agent sessions](https://github.com/microsoft/agent-framework/discussions/6858)（2025）
21. [openai-agents-python: handoffs](https://github.com/openai/openai-agents-python/blob/db68d1c3/docs/handoffs.md)（2025）
22. [Claude Cookbook: chief of staff agent](https://platform.claude.com/cookbook/claude-agent-sdk-01-the-chief-of-staff-agent)
23. [google/adk-docs: multi-agents.md](https://github.com/google/adk-docs/blob/90250a53d8a8ba2671733b2c143a7888ba347766/docs/agents/multi-agents.md)（2025）
24. [PyCon DE 2025: Auto-Optimization](https://2025.pycon.de/talks/GURXPK/)
25. [GitHub Blog: Copilot agentic workflows](https://github.blog/ai-and-ml/github-copilot/from-idea-to-pr-a-guide-to-github-copilots-agentic-workflows/)；[Java Code Geeks 2026-02](https://www.javacodegeeks.com/2026/02/github-copilot-workspace-the-agentic-era.html)
26. [simonwillison.net: Claude Code sub-agents](https://simonwillison.net/2025/Oct/11/sub-agents/)（2025-10-11）
27. [aider#3624](https://github.com/Aider-AI/aider/issues/3624)；[Aider ask/architect 教程](https://openclawhub.tools/tutorial/how-to-use-aider-to-refactor-a-python-repo-with-ask-and-architect-modes/)
28. [SC World: 微软开源 agent 网络安全调查基准](https://www.scworld.com/news/microsoft-announces-open-source-benchmark-for-ai-agent-cybersecurity-investigations)（2025）
