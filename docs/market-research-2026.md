# 2025–2026 AI Agent 开发框架市场调研与竞争评估论据库

> **编制时间**：2026-08-28 ｜ **服务对象**：agent-hive 竞争评估报告（agent-hive = 基于 LangGraph 自研的「首脑统筹 + 角色专家 + 契约工作包 + 评估优化回路」多智能体编排框架）
> **覆盖范围**：10 个主流框架/平台 + 2 项特别调研 + 13 维能力对照表
> **工作区**：`C:\Users\10104\Desktop\code\agent-hive\docs\market-research-2026.md`

---

## 0. 报告说明、方法与标注约定

### 0.1 时间窗口

本报告面向「当下（2025–2026）」的市场事实，所有版本号、发布时间、报告数据均以 **2026 年 8 月 28 日** 为止的公开可查信息为准。标注年份的方式为 `[来源: URL, 年份]`。

### 0.2 调研方法

- **一手优先**：官方文档（docs.*、learn.microsoft.com、code.claude.com 等）、官方博客、GitHub 仓库（LICENSE/pyproject/README）、PyPI JSON API（验证当前版本与上传日期）、AWS/Azure/Google 官方产品页与定价页、arXiv 论文。
- **行业报告**：LangChain《State of AI Agents / State of Agent Engineering 2025》原文、Gartner 新闻稿、Menlo Ventures 报告、ZenML LLMOps 博客、McKinsey/Sequoia 公开内容。
- **二手佐证**：权威媒体（InfoWorld、VentureBeat、TechTarget、IT Brief 等）与第三方评估（AgentMarketCap、CostBench、SMF Clearinghouse 等），一律标注为二手并谨慎引用。
- **实证手段**：通过 PyPI JSON API 与 GitHub raw 抓取验证版本号、许可证与文档片段；通过工作区 `docs/_research_notes/` 下的调研笔记保存中间证据。

### 0.3 三级标注约定（全报告通用）

| 标注 | 含义 | 引用要求 |
|---|---|---|
| 【事实】 | 有一手/权威来源直接支撑 | 附 `[来源: URL, 年份]` |
| 【推断】 | 基于事实的合理分析外推 | 明确说明推理链 |
| 【未证实】 | 本次检索未能核实 | 禁止在正式报告中当事实引用 |

> ⚠️ 引用纪律：凡标【未证实】的条目，使用前必须补充一手来源；易变数字（star 数、单价、版本号）建议上线前用 GitHub API / PyPI 复核。

### 0.4 与 agent-hive 的关系

本报告为 agent-hive 竞争评估提供**外部市场论据**。agent-hive 自身能力以仓库 `docs/card-*.md` 与 `agent_hive/*.py` 源码为准（README 声明 385 项回归测试全绿；`arch_security.py / cost_control.py / contract_spec.py / scheduler.py / graph.py / async_hitl.py` 等模块均已在代码库中存在）。第 7 节对照表加入 agent-hive 一列作为基准参照，其能力标注来自项目自身文档与源码，非外部评测。

---

## 1. 执行摘要（10 条关键结论）

1. **框架格局已收敛为"四强 + 多梯队"**：【推断，依据一家 2026-08 第三方评估】SMF Clearinghouse 认为生产级框架收敛为 **LangGraph / Microsoft Agent Framework / OpenAI Agents SDK / Claude Agent SDK** 四强；CrewAI（易用性）、Google ADK（云绑定）、Pydantic AI（类型安全）为第二梯队 [来源: https://www.smfclearinghouse.com/guides/agent-framework-landscape-august-2026/, 2026-08]。
2. **生产采用在加速，但质量是头号障碍**：【事实】LangChain 2025 年 12 月调查（1,340 人）：57.3% 组织已有 agent 上线生产（上年 51%），10k+ 人企业达 67%；质量列为首要生产障碍（32%），延迟第二（20%），成本担忧同比下降 [来源: https://www.langchain.com/state-of-agent-engineering, 2025-12]。
3. **可观测性已成标配，评估仍在追赶**：【事实】89% 组织已建可观测性（生产组 94%、71.5% 有完整 trace），而离线评估仅 52.4%、在线评估 37.3%——"看得见但评不了"的剪刀差是评估/守卫类产品与自研框架评估能力的机会窗口 [来源: 同上]。
4. **安全关切显著上升**：【事实】2k+ 人企业中安全成为生产第二大障碍（24.9%）；Gartner 2025-06 预测到 2027 年底 **40%+ 的 agentic AI 项目将被取消**；CrowdStrike 报告 2025 年提示注入攻击波及 90+ 家企业 [来源: https://www.gartner.com/en/newsroom/press-releases/2025-06-25-gartner-predicts-over-40-percent-of-agentic-ai-projects-will-be-canceled-by-end-of-2027, 2025-06；https://dataconomy.com/2026/06/29/crowdstrike-prompt-injection-attacks-90-firms-2025/, 2026-06]。
5. **三大模型厂商 SDK 在 2025 年集中入场并快速迭代**：【事实】OpenAI Agents SDK（2025-03-11，取代 Swarm，MIT，当前 0.22.0）、Claude Agent SDK（2025-09-29，Claude Code 无头封装，MIT，当前 0.2.145）、Google ADK（2025-04，Apache-2.0，当前 2.8.0）[来源: https://community.openai.com/t/new-tools-for-building-agents-responses-api-web-search-file-search-computer-use-and-agents-sdk/1140896, 2025；https://www.pymnts.com/news/artificial-intelligence/2025/anthropic-claude-sonnet-4-5-introduces-claude-agent-sdk/, 2025；https://developers.googleblog.com/en/agent-development-kit-easy-to-build-multi-agent-applications/, 2025]。
6. **企业级工程能力普遍缺失，平台层补位**：【事实/推断】三家官方 SDK 均**无独立成本预算原语**（仅 usage 追踪）；多租户、合规、prompt A/B、审计等几乎全部依赖平台层（LangGraph Platform / LangSmith、CrewAI AMP、Azure、AWS 托管）或自建 [来源: openai-agents-python docs/usage.md, 2026；claude-agent-sdk README, 2026；google/adk-docs, 2026]。
7. **HITL 主流形态是"工具调用审批/权限提示"，而非"契约级人工验收"**：【推断】Claude hooks "ask"、Agent Framework `FunctionApprovalRequestContent`、OpenAI 工具中断、ADK 回调、CrewAI human_input、Coze 人工审核节点均属前者；对工作包验收标准的逐项人工勾选仍是行业空白（详见第 6 节）。
8. **特别调研 A：架构/设计级安全验证无直接商业对标**：【事实/推断】Vercel deepsec 与 Unclecheng-li/DeepSec 扫描的是 **AI 生成的代码/依赖**；威胁建模平台（IriusRisk Jeff、ThreatModeler AI）独立于编排流水线；「规则引擎 + LLM 语义威胁建模」双通道、内嵌审批关口的**架构级**验证未见同构产品（详见第 5 节）。
9. **特别调研 B：四要素组合趋同，但三点取舍构成差异化**：【事实/推断】首脑统筹（LangGraph supervisor、AutoGen manager、Claude chief-of-staff cookbook、ADK 层级）、角色专家、契约/工作包（MetaGPT 消息协议、CrewAI task context、spec-kit）、评估优化回路（DSPy、LangSmith evals）单项均已普及；「显式契约字段一等公民 + 验收回流≤3 轮强闭环 + 架构安全验证内嵌审批关口」的组合截至 2026-08 未见完全同构产品（详见第 6 节）。
10. **对 agent-hive 的含义**：【推断】竞争焦点不是"有没有这些机制"，而是**产品化完整度**（可观测/评估/成本/断点/看板等工程能力）与**差异化卖点**（契约、验收闭环、架构安全验证）；市场数据支持"生产缺口 = 质量 + 评估 + 安全"的定位叙事（详见第 8 节）。

---

## 2. 市场全景：权威行业报告数据（2024–2026）

### 2.1 LangChain《State of AI Agents / State of Agent Engineering 2025》【事实为主】

> **命名说明**：官方页面为 `langchain.com/state-of-agent-engineering`（2025 年版，中文译《智能体工程现状》）；2024 年版名为《State of AI Agents》。用户任务中"State of AI Agents 2025"即指该 2025 年版系列报告。调查窗口 2025-11-18 至 2025-12-02，共 **1,340 份**回复（63% 技术行业、10% 金融），2025-12-16 发布 [来源: https://www.langchain.com/state-of-agent-engineering, 2025-12]。
> ⚠️ **同名区分**：坊间流传的"78% 做试点 / 仅 14% 进生产 / 86% 试点走不通"出自 **AI2 Incubator《State of AI Agents 2025》**（另一份报告），**不是 LangChain 报告**，引用时切勿混淆（详见 3.2 节）[来源: https://agentmarketcap.ai/blog/2026/04/08/ai2-incubator-state-of-ai-agents-2025-deployment-reality, 2026-04]。

**关键数据**（全部【事实】，来源同上）：

| 维度 | 数据 |
|---|---|
| 生产采用 | 57.3% 已有 agent 生产（去年 51%）；30.4% 开发中且有部署计划；10k+ 人组织 67% |
| 首要生产障碍 | 质量 32%（含准确性/相关性/一致性）；延迟 20%；成本提及率**同比下降** |
| 企业安全关切 | 2k+ 人组织中安全为第二大障碍（24.9%），超过延迟 |
| 可观测性 | 89% 已实施（62% 有详细 trace）；生产组 94%（71.5% 详细 trace） |
| 评估（离线） | 52.4% 在测试集上跑离线评估；生产组中 22.8% 完全不评估 |
| 评估（在线） | 37.3%（生产组 44.8%）；LLM-as-judge 53.3%、人工审查 59.8% |
| 模型格局 | 2/3+ 用 OpenAI GPT；**3/4+ 多模型并用**；33% 投资自托管模型（数据驻留/主权动因）；57% 未微调 |
| 主要用例 | 客服居首，研究/数据分析，内部工作流自动化 18% |

**推论**【推断】：① 可观测性（89%）与评估（52%/37%）的采用剪刀差说明"部署快、验证慢"，评估体系与守卫工具是缺口市场；② 多模型并用（75%+）意味着框架的**模型中立性**与**成本路由**能力是选型要素；③ 自托管/私有化（33%）说明合规与数据主权是真实需求，开源 + 自托管路线有市场。

### 2.2 Gartner【事实】

- **2025-06-25** 新闻稿：到 2027 年底，**超过 40% 的 agentic AI 项目将被取消**，主因范围蔓延、成本、价值不清晰 [来源: https://www.gartner.com/en/newsroom/press-releases/2025-06-25-gartner-predicts-over-40-percent-of-agentic-ai-projects-will-be-canceled-by-end-of-2027, 2025-06]。
- **2026-04-02** 新闻稿：到 2028 年，多数企业将放弃"辅助式 AI"（assistive AI），转向"成果导向工作流"（outcome-focused workflow）[来源: https://www.gartner.com/en/newsroom/press-releases/2026-04-02-gartner-expects-most-enterprises-to-abandon-assistive-ai-for-outcome-focused-workflow-by-2028, 2026-04]。
- 2026-06 媒体转述：Gartner AI 编码工具评估中 AI 原生厂商挤占云厂商领导者象限（行业转向信号，二手）[来源: https://virtualizationreview.com/articles/2026/06/05/ai-firms-push-cloud-giants-from-leaders-quadrant-in-gartner-ai-coding-report.aspx, 2026-06]。

### 2.3 Menlo Ventures【事实】

- **2024 版**（2024-11-20）：企业 GenAI 支出 2024 年达 **$13.8B，是 2023 年 $2.3B 的 6 倍**；72% 决策者预期扩大采用 [来源: https://menlovc.com/2024-the-state-of-generative-ai-in-the-enterprise/, 2024]。
- **2025 版**（第三期年度报告）：企业 GenAI 支出 **2025 年 $37B（2024 修订值 $11.5B，同比 3.2x；2023 年 $1.7B）**，占全球 SaaS 市场 6%+；至少 10 个产品 ARR 超 $10 亿；应用层 $19B / 基础设施层 $18B（模型 API $12.5B、训练基建 $4.0B）[来源: https://menlovc.com/perspective/2025-the-state-of-generative-ai-in-the-enterprise/, 2025]。
- **代码 agent 细分**：代码 agent/AI 应用构建从近零增长到 2025 年约 **$4B（2024 年 $550M）**；Agent 平台（Agentforce、Writer、Glean 等）占应用层约 10%（$750M）[来源: 同上, 2025]。
- **审计预期**：报告展望自主决策增加后，"可解释决策与 agent 结果审计日志"将成为政府/企业刚需 [来源: 同上, 2025]。

### 2.4 其他权威口径

- **Sequoia《AI's $600B Question》**（2024-06，David Cahn）：为支撑 AI 基建投资，AI 应用需产生约 **$600B 年收入**（系列前作 2023-09《$200B Question》）【事实】；**2025 更新**：超大规模厂商 2025 年 AI 资本开支约 **$750B**，需在其生命周期内产生约 **$1.5T 终端收入**回本、累计约 **$3T**【事实：数字经媒体引述】；"$750B Question"确切标题【未证实】[来源: https://sequoiacap.com/article/ais-600b-question, 2024；https://www.edgen.tech/zh/news/post/ai-boom-reshapes-us-economy-as-750b-buildout-raises-stability-risks, 2026]。
- **Stanford HAI《AI Index 2025》**：SWE-bench 从 2023 年 4.4% → 2024 年 **71.7%**；企业 AI 采用 2024 年 78%（2023 年 55%）；OpenAI o1 比 GPT-4o 贵近 6 倍、慢约 30 倍（推理成本/延迟警告）【事实：媒体转述】[来源: https://aiindex.stanford.edu/report/, 2025-04]。
- **McKinsey《The State of AI in 2025》**（n=1,491）：23% 企业正在规模化 agentic AI、39% 在试验、仅 6% 为"AI 高绩效者"；2026-03 转述约 **10% 的企业职能正在使用 AI agents**【事实：官方报告 + 媒体转述】[来源: https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai, 2025；https://www.forbes.com/sites/josipamajic/2026/03/22/10-of-enterprise-functions-use-ai-agents-mckinsey-finds/, 2026-03]。
- **Deloitte / Forrester**：Deloitte 2025 显示印度 80%+ 企业探索 agentic AI（区域样本）；Tech Trends 2026 称企业"普遍撞墙"（规模化准备不足）；Forrester 将 agentic AI 列为从"实验"转向"业务必选项"【事实：定性转述】[来源: https://www.deloitte.com/us/en/insights/topics/technology-management/tech-trends/2026/agentic-ai-strategy.html, 2026]。
- **ZenML LLMOps 数据库**：以 1,200 个生产部署案例总结 LLMOps 2025 成熟度；数据集合计 **2,089 条**生产案例记录，按可观测/评估/网关/编排分类 [来源: https://www.zenml.io/blog/what-1200-production-deployments-reveal-about-llmops-in-2025, 2025；https://huggingface.co/datasets/zenml/llmops-database, 2026]。
- **评估/可观测市场**：AI agent 评估与仿真平台市场 2025 年约 **$769.2M**（FactMR，二手）；**Langfuse 于 2026-01 被 ClickHouse 收购**（33.6k stars、90B+ 观测/月）；**Portkey $15M Series A**（2026-02，自述托管 $500K+/日支出、1,600+ 模型）——可观测/网关赛道持续整合 [来源: https://www.factmr.com/report/ai-agent-evaluation-and-simulation-platforms-market, 2025；https://clickhouse.com/blog/clickhouse-acquires-langfuse-open-source-llm-observability, 2026-01；https://portkey.ai/blog/series-a-funding/, 2026-02]。

### 2.5 中国企业市场（补充视角）

- **信通院**：2025-06-22 与华为联合发布《智能体技术和应用研究报告（2025 年）》（发展概述/关键技术/产业应用/问题挑战/发展建议）[来源: http://www.cww.net.cn/article?id=601665, 2025]。
- **IDC**（《AI Agent 企业级应用现状与推荐，2025》）：中国受访企业 **34% 处于测试验证阶段、30% 进入"较大投入+采购培训"**；预测 **2028 年中国企业级 Agent 应用市场保守达 270+ 亿美元**；**66% 中国企业偏好"基于业务成果计费"（全球 52.7%）**；2025 年智能体开发平台**私有化市场收入 17.5 亿元**【事实】[来源: https://my.idc.com/getdoc.jsp?containerId=prCHC53669525, 2025-07；https://hk.investing.com/news/stock-market-news/article-1506910, 2026]。
- **艾瑞咨询**（《中国金融智能体发展研究与厂商评估报告 2025》）：2025 年中国金融智能体签约 **9.5 亿元**，预计 2030 年 **193 亿元（CAGR 82.6%）**；但 **96% 应用实践仍处早期探索**，预计 2026 年底 20-25% 金融机构将动摇投资信心【事实：经济观察报转述】[来源: http://www.eeo.com.cn/ai/2026/0221/799147.shtml, 2026-02]。
- **国内平台格局（公开数据）**：扣子截至 2025-06 月访问用户约 **458 万**（非凡产研），2025-07 开源 Coze Studio/Loop；Dify 2025 年 stars 破 90K、支撑 400 万+ 部署、2026-03 完成 $30M Pre-A（红杉中国领投）；阿里云百炼截至 2025-01 底调用通义 API 企业与开发者超 29 万；文心智能体平台 2024-04 时 3 万+ 智能体（数据较旧）[来源: https://www.infoq.cn/article/a4ikxoqf5tfq24izedcl, 2025；https://baike.baidu.com/item/Dify/66266114, 2026；http://jjckb.xinhuanet.com/20250415/13aa9fd799994698bac03d407fb5b9f5/c.html, 2025]。
- 【推断】国内格局小结：扣子=低代码/C 端 + 开源生态；文心=流量分发 + 免费模型；百炼=云生态 + MCP/Agent 工厂；Dify=开源 + 企业版出海与私有化。自研框架的差异化空间 = 私有化/信创、企业身份与审计集成、可观测 + 评估闭环。

---

## 3. 企业级选型痛点与论据

> 本节回答"客户在生产落地 agent 时真正在意什么"，每条给出事实/论据。这是竞争评估中"需求侧"的核心论据。

### 3.1 可观测性（trace 全覆盖）

- 【事实】89% 组织已建可观测性、62% 有详细 trace；生产组 94%——**没有可观测性无法调试/优化/建立信任** [来源: https://www.langchain.com/state-of-agent-engineering, 2025-12]。
- 【事实】主流框架的可观测性形态：OpenAI Agents SDK 内置 tracing 默认开启（platform.openai.com/traces 在线看板）；Claude Agent SDK 官方支持 OpenTelemetry 且有 LangSmith/Arize 官方集成；ADK 基于 OTel + Arize 指南；CrewAI 内置 telemetry + Langfuse 集成；AutoGen 0.4+ 内置 OTel trace；Agent Framework 内置 tracing 可导出 Azure Monitor；MetaGPT 仅日志级（弱）[来源: 各官方文档，2025-2026，详见第 4 节]。

### 3.2 评估体系（evals）

- 【事实】离线评估 52.4%、在线 37.3%、**29.5% 完全不评估**；生产组在线评估升至 44.8%、完全不评估降至 22.8%——**评估是最大的实践缺口之一** [来源: https://www.langchain.com/state-of-agent-engineering, 2025-12]。
- 【事实】横向参照：AI2 Incubator《State of AI Agents 2025》称约 78% 企业有 agent 试点、仅 14% 规模化到全组织（约 **86% 试点未走通全组织生产**）；G2 2025-08 调查 57% 公司已投产 agent [来源: https://agentmarketcap.ai/blog/2026/04/08/ai2-incubator-state-of-ai-agents-2025-deployment-reality, 2026-04；https://learn.g2.com/enterprise-ai-agents-report, 2025-08]。
- 【事实】评估方法：LLM-as-judge 53.3%、人工审查 59.8%；传统指标（ROUGE/BLEU）采用率有限 [来源: 同上]。
- 【事实】内置 eval 成体系的仅 Google ADK（`adk eval` CLI，轨迹校验 + LLM-as-judge）；OpenAI 2026 年补 agent-evals 指南；Pydantic AI 提供 evals + LLM-as-judge 官方文章；其余多靠 LangSmith/Langfuse/Braintrust/Arize 外部补齐 [来源: google/adk-docs evaluate 文档, 2025-2026；https://developers.openai.com/api/docs/guides/agent-evals.md, 2026；pydantic.dev/articles/llm-as-a-judge, 2025-2026]。
- 【事实】评估赛道热度：agent 评估基础设施出现 "$800M 级押注"与"成为 AI 的 Datadog"之争（Braintrust/Langfuse/Arize/Patronus 等），第三方评估正替代内部测试 [来源: https://agentmarketcap.ai/blog/2026/04/10/ai-agent-eval-infrastructure-market-2026, 2026-04]。

### 3.3 守卫与安全护栏（guardrails）

- 【事实】安全成为 2k+ 人企业生产的第二大障碍（24.9%）[来源: https://www.langchain.com/state-of-agent-engineering, 2025-12]。
- 【事实】威胁面实证：CrowdStrike 称 2025 年提示注入攻击波及 90+ 家企业；OWASP 2025 年发布 LLM Top 10（2025 版），2025-12 新增《Top Ten AI Agent Threats》agent 特有威胁清单 [来源: https://dataconomy.com/2026/06/29/crowdstrike-prompt-injection-attacks-90-firms-2025/, 2026-06；https://genai.owasp.org/download/45674/, 2025；https://securityboulevard.com/2025/12/owasp-project-publishes-list-of-top-ten-ai-agent-threats/, 2025-12]。
- 【事实】守卫能力现状：OpenAI 内置输入/输出 guardrail 函数；CrewAI 任务级 guardrail + 企业版幻觉护栏；Claude SDK 靠 hooks 拦截 + 权限策略；AutoGen 无一等 guardrails API（治理提案未定稿）；Coze 平台侧内容安全/防火墙插件；运行时防护成熟品类包括 Cloudflare for AI、Lakera、NVIDIA NeMo Guardrails、Cisco（收购 Robust Intelligence 后）等（详见第 5 节）[来源: 各官方文档与第 5 节来源]。

### 3.4 成本失控与预算

- 【事实】LangChain 调查中成本被提及频率同比**下降**（模型降价 + 提效），但仍是生产障碍之一；质量/速度成为新焦点 [来源: https://www.langchain.com/state-of-agent-engineering, 2025-12]。
- 【事实】三大官方 SDK 均提供 usage/token 追踪（OpenAI `result.context_wrapper.usage`、Claude 消息级 usage、ADK 用量），但**均无独立"预算上限（budget cap）"原语**——成本上限靠应用层实现；社区存在"agent 成本失控"讨论（"runaway agent costs"）[来源: openai-agents-python docs/usage.md, 2026；https://community.openai.com/t/has-anyone-actually-solved-runaway-agent-costs-looking-for-patterns-beyond-logging/1383094, 2026]。
- 【事实】成本管理是刚需的侧面证据：LLM 网关/控制面厂商 Portkey 自述托管 $500K+/日支出、1,600+ 模型（2026-02 $15M Series A）；IDC 中国调查 **66% 企业偏好"基于业务成果计费"（全球 52.7%）**——预算与计费治理是企业采购的核心议题 [来源: https://portkey.ai/blog/series-a-funding/, 2026-02；https://my.idc.com/getdoc.jsp?containerId=prCHC53669525, 2025-07]。
- 【事实】平台侧成本模式：LangGraph Platform / LangSmith 按席位 + 用量（Developer $0 / Plus $39/席 + 用量）；Bedrock AgentCore 按调用计费；Coze 按 token/调用 + 订阅/企业版；CrewAI AMP 平台订阅 [来源: https://costbench.com/software/ai-agent-platforms/langgraph-platform/, 2026；https://aws.amazon.com/bedrock/agentcore/pricing/, 2025-2026；https://docs.coze.cn/api/open/docs/coze_pro/model_fee, 2025-2026]。
- 【推断】自研/开源框架在成本侧的机会：提供**预算估算 → 实时监控 → 超预算自动降级**的闭环（agent-hive `cost_control.py` 即此思路），这是主流框架未内建的空缺。

### 3.5 幻觉与输出质量

- 【事实】质量（准确性/相关性/一致性/幻觉）是生产头号障碍（32%）；10k+ 人企业书面反馈将**"幻觉与输出一致性"**列为首要质量挑战，多步推理使错误逐级累积 [来源: https://www.langchain.com/state-of-agent-engineering, 2025-12]。
- 【事实】AI 生成物有特有失败模式：幻觉依赖包（hallucinated packages）、缺失安全防护、AI 模式错误——Unclecheng-li/DeepSec（Shield）将其定义为独立审计对象 [来源: https://github.com/Unclecheng-li/DeepSec, 2025-2026]。
- 【推断】缓解路径 = 结构化输出校验（Pydantic AI 类型契约）+ 评估回流（验收-返工）+ 守卫（规则引擎）；三者组合正是 agent-hive 的架构。

### 3.6 合规与数据主权

- 【事实】33% 组织投资自托管模型，动因含数据驻留、主权要求、监管限制 [来源: https://www.langchain.com/state-of-agent-engineering, 2025-12]。
- 【事实】云平台合规背书差异：Bedrock（AWS）region 化部署 + IAM/Policy + "不用于训练"承诺；Coze 国内版数据在国内、国际版 coze.com 数据域分离（跨境合规横评）[来源: https://aws.amazon.com/bedrock/agentcore/, 2025-2026；https://www.yun88.com/news/11551.html, 2025-2026]。
- 【事实】中国市场数据：IDC 称中国受访企业 34% 处于测试验证阶段、30% 进入"较大投入+采购培训"（整体落后于全球）；2025 年智能体开发平台私有化市场收入 17.5 亿元——私有化/信创是真实市场 [来源: https://my.idc.com/getdoc.jsp?containerId=prCHC53669525, 2025-07；https://hk.investing.com/news/stock-market-news/article-1506910, 2026]。
- 【推断】对自研框架：开源 + 自托管 = 数据主权卖点；但需要配套脱敏/日志保留策略（agent-hive `data_compliance.py` 卡片即此），否则无法通过国内等地的合规审查。

### 3.7 多租户与隔离

- 【事实】OSS 框架本身几乎都无多租户：LangGraph OSS 默认 SQLite checkpointer 不支持并发写/租户隔离（需自建或上 Platform）；多租户隔离主要在平台层（LangGraph Platform deployments、AWS 托管、Coze/Dify SaaS）[来源: agent-hive 内部对标；docs.crewai.com / docs.langchain.com 均未见多租户一等抽象（经检索未见官方多租户文档），2025-2026]。
- 【推断】企业级售卖（尤其私有化）几乎必然面对"多租户 + 配额"诉求，是自研框架的工程分水岭。

### 3.8 失败重试 / 熔断 / 断点恢复

- 【事实】LangGraph 以 checkpointer + thread 提供**断点续跑**（其标志能力）；1.2 加入 per-node 超时/重试策略、graceful shutdown + checkpoint 恢复 [来源: https://dev.to/x4nent/langgraph-12-deep-dive-per-node-timeouts-error-handlers-graceful-shutdown-deltachannel--2mp2, 2026-06]。
- 【事实】OpenAI Agents SDK 2026 强化 RunState 中断快照（interruption snapshots）；Bedrock AgentCore 2026-08 为多 agent 协作提供 persistent compute（常驻运行时）；ADK 会话/checkpoint 可持久化恢复 [来源: https://www.smfclearinghouse.com/guides/agent-framework-landscape-august-2026/, 2026-08；https://www.infoq.com/news/2026/08/aws-bedrock-agentcore-runtime/, 2026-08；google/adk-python 架构文档, 2025-2026]。
- 【推断】"熔断向依赖下游传播 + 返工只重派目标包"这类**编排级容错语义**（agent-hive scheduler.py 已实现）在主流框架中仍属空白，多为图/对话级基础重试。

### 3.9 延迟

- 【事实】延迟是生产第二大障碍（20%）；客服/代码生成等面向客户场景对响应时间敏感；推理模型进一步放大延迟压力——Stanford AI Index 2025 显示 OpenAI o1 比 GPT-4o 慢约 30 倍（贵约 6 倍）[来源: https://www.langchain.com/state-of-agent-engineering, 2025-12；https://aiindex.stanford.edu/report/, 2025-04]。
- 【推断】流式输出、并行 fan-out、节点级缓存（LangGraph 1.0 node caching）是缓解手段 [来源: https://www.smfclearinghouse.com/guides/agent-framework-landscape-august-2026/, 2026-08]。

### 3.10 身份认证 / 审计集成

- 【事实】企业平台普遍要求 SSO/审计：LangGraph Platform 企业版、CrewAI AMP、Azure 侧均有企业特性；Bedrock 以 IAM/Policy 治理；Coze 企业版面向 B 端 [来源: 各平台企业文档，2025-2026]。
- 【事实】Menlo 2025 明确预期"自主决策增加后，可解释决策与 agent 结果**审计日志**将成为政府/企业刚需"；Langfuse、Dify 企业版均把权限管理/合规方案作为企业版卖点 [来源: https://menlovc.com/perspective/2025-the-state-of-generative-ai-in-the-enterprise/, 2025；https://langfuse.com/press/press, 2026]。
- 【推断】自研框架需提供审批单/审计日志（agent-hive：架构安全报告随审批单、`cost.json` 落账、`--skip-arch-security` 写入审计），才能满足企业"可追溯、可追责"要求。

### 3.11 LLMOps / 可观测性工具生态简表（2025-2026）

| 工具 | 定位（一句话） | 2025-2026 动态 |
|---|---|---|
| **ZenML LLMOps Database** | 全球最大的 LLMOps 生产案例/工具开放数据库 | 数据集合计 **2,089 条**记录，按可观测/评估/网关/编排分类【事实】[来源: https://huggingface.co/datasets/zenml/llmops-database, 2026] |
| **Langfuse** | 开源 AI 工程平台：tracing + prompt 管理 + LLM-as-Judge 评估 | GitHub 33.6k stars、90B+ 观测/月；**2026-01 被 ClickHouse 收购**【事实】[来源: https://clickhouse.com/blog/clickhouse-acquires-langfuse-open-source-llm-observability, 2026-01] |
| **Arize Phoenix** | 开源 LLM/agent 可观测与评估（tracing/drift/evals） | GitHub 破 10,000 stars（2025）【事实】[来源: https://arize.com/blog/phoenix-10k/, 2025] |
| **W&B Weave** | W&B 开源 LLMOps 工具包（tracing/datasets/evals） | 定位转向"Eval-centric"生产评估【事实（定位）】[来源: https://wandb.ai/site/weave] |
| **AgentOps** | agent 专用监控/会话回放/成本评分平台 | 融资情况【未证实】[来源: https://agentops.ai/] |
| **LangSmith** | LangChain 官方商业平台（tracing/eval/prompt/网关） | 与 LangGraph 深度绑定；可观测性 89% 普及的生态基础【事实（定位）】[来源: https://www.langchain.com/state-of-agent-engineering, 2025] |
| **Portkey** | LLM 网关/控制面：路由、治理、成本管理 | **2026-02 $15M Series A**；自述 1,600+ 模型【事实（自述）】[来源: https://portkey.ai/blog/series-a-funding/, 2026-02] |
| **Kong AI Gateway** | API 网关扩展的 AI 网关（路由/治理/MCP） | AI Gateway 3.13（2025）主打 agentic 工作负载上生产【事实】[来源: https://konghq.com/blog/product-releases/ai-gateway-3-13, 2025] |
| **LiteLLM proxy** | 开源"通用 LLM 翻译层"：统一 100+ 家供应商，成本/限流/fallback | 社区事实标准之一【事实（定位）】[来源: https://futureagi.com/blog/what-is-litellm-2026/, 2026] |

【推断】可观测/评估/网关赛道 2025-2026 持续整合（ClickHouse 收购 Langfuse、Braintrust/Langfuse/Arize 争夺"AI 的 Datadog"），说明**企业愿意为"看得见 + 评得了 + 控得住"付费**——这也是自研框架需要对齐或自建的能力面。

---

## 4. 主流框架逐一分析

> 每节统一按 8 个字段组织：定位 / 编排模型 / HITL / 守卫与评估 / 可观测性 / 成本控制 / 许可证与生态 / 2025–2026 关键动态。每条结论带【事实/推断/未证实】标注与来源。

### 4.1 LangGraph / LangChain Platform / LangSmith

- **定位**：【事实】LangGraph = 底层 agent 编排运行时（显式有状态图：节点/边/状态），内建 durable execution（checkpoint 持久化）、内存、流式与 HITL；LangGraph 1.0 与 LangChain 1.0 于 **2025-10-22** 同步 GA（Python + TS）；LangGraph Platform（托管部署层）2025-05-14 GA，**2025-10 更名 "LangSmith Deployment"**（Studio 更名 LangSmith Studio），LangChain 公司产品线统一为 LangSmith Platform（Observability / Evaluation / Deployment 三支柱）+ 开源框架 [来源: https://www.langchain.com/blog/langchain-langgraph-1dot0, 2025-10；https://www.langchain.com/blog/langgraph-platform-ga, 2025-05；https://forum.langchain.com/t/we-launched-1-0-versions-of-langchain-and-langgraph/1904, 2025-10]。
- **编排模型**：【事实】显式图驱动：StateGraph + TypedDict 状态契约 + 条件边/循环 + `Send` API（动态 fan-out）+ `Command`（运行时更新/恢复）+ 子图；官方 supervisor 库 `langgraph-supervisor-py`（create_supervisor 首脑-子代理模式），官方自 2025 年末起推荐改用"工具调用式 supervisor 模式"（利于上下文工程）；1.0 新增节点级缓存、deferred nodes、content-block streaming、MCP endpoint 暴露；1.2 新增 per-node 超时/重试策略、错误处理器、graceful shutdown + checkpoint 恢复 [来源: https://docs.langchain.com/oss/python/langgraph/, 2025-2026；https://github.com/langchain-ai/langgraph-supervisor-py, 2025；https://www.smfclearinghouse.com/guides/agent-framework-landscape-august-2026/, 2026-08]。注意：依赖是**开发者显式编码**的图，非自动任务图规划器【事实】。
- **HITL**：【事实】`interrupt()` + checkpointer 持久化 + `Command(resume=...)` 恢复 + 时间旅行（time travel，回滚重放）；LangChain 1.0 提供预置 `HumanInTheLoopMiddleware`（敏感工具调用审批，approve/edit/reject）；Platform 支持跨异步时间的审批（agent 等待人在未来回复）[来源: https://docs.langchain.com/oss/python/langgraph/interrupts, 2025；langchain-v1 release notes, 2025]。
- **守卫与评估**：【事实】核心无内置 guardrail 引擎，官方组合式方案 = middleware `after_model` 输出校验 + prebuilt `ValidationNode`（工具参数校验）+ 官方示例仓库 langgraph-guardrails-example；NVIDIA NeMo Guardrails 有官方 LangGraph 集成文档；Lakera 走第三方 langchain 集成；评估体系在 LangSmith（datasets/experiments/offline-online evals、Open Evals 开源评估器目录、LLM-as-Judge 校准（2025-05 私有预览）、聊天模拟）[来源: https://docs.nvidia.com/nemo/guardrails/integration-with-third-party-libraries/langchain/langgraph-integration, 2025；https://github.com/langchain-ai/langgraph-guardrails-example, 2025；https://blog.langchain.com/interrupt-2025-recap/, 2025]。
- **可观测性**：【事实】LangSmith 原生集成（trace tree / projects / threads / dashboards / agent 专属指标 / 成本视图）；OSS 侧无自带可观测服务；自托管观测用 LangSmith Fleet [来源: https://docs.langchain.com/langsmith/, 2025-2026]。
- **成本控制**：【部分事实】LangSmith 自动成本追踪 + 告警 + evaluator 花费上限；Platform 按 LCU（LangChain Compute Unit）+ 席位计费；**组织级预算强制管控【未证实】** [来源: https://docs.langchain.com/langsmith/cost-tracking, 2025；https://docs.langchain.com/langsmith/evaluator-spend, 2025]。
- **许可证与生态**：【事实】LangGraph 与 LangChain 均 **MIT**；GitHub：langgraph 约 40.6k stars、langchain 约 145.1k stars（2026-08 抓取）；LangChain 生态下载量 >7,000 万/月（2025-05，超过 OpenAI SDK 同期）；LangChain 公司 2025-10 完成 **$125M B 轮（IVP 领投），估值 $1.25B（独角兽）** [来源: https://github.com/langchain-ai/langgraph, 2026；https://www.langchain.com/blog/series-b, 2025]。
- **定价**：【事实】LangSmith：Developer 免费（前 5,000 traces/月，超出按量）、Plus **$39/seat/月** + 按量、Enterprise 定制（SSO/合规/SLA）；LangGraph Platform（LangSmith Deployment）：Developer 免费（1 seat/5k traces/5 LCU）、Plus 按量 + seat $39/月 + LCU 计量、Enterprise 定制（ABAC/RBAC/SSO/SLA；Cloud/Hybrid/Self-Hosted 三部署模式）[来源: https://support.langchain.com/articles/6889482332-how-am-i-charged-for-langsmith-plus-plan-and-where-can-i-view-my-billing-details, 2025；https://costbench.com/software/ai-agent-platforms/langgraph-platform/, 2026]。
- **2025–2026 关键动态**：【事实】2025-05-14 Platform GA（beta 期约 400 公司）+ Interrupt 2025（Studio v2、Pre-Builts、Open Evals、LLM-as-Judge 校准）；2025-10-22 LangChain/LangGraph 1.0 GA（Launch Week，create_agent 统一入口、API 稳定性承诺）；2025-10 更名 LangSmith Deployment；2025-12 发布《State of Agent Engineering 2025》；2026：fault-tolerance 文档章节（retry_policy/timeout，节点级 timeout 需 ≥1.2）、Agent Builder 无代码工具注册表（2026 Q1）、编码 agent 产品 dcode [来源: https://blog.langchain.com/interrupt-2025-recap/, 2025；https://www.langchain.com/blog/new-in-agent-builder-all-new-agent-chat-file-uploads-tool-registry, 2026]。
- **与 agent-hive 的关系**：【推断】agent-hive 以 LangGraph 为执行底座（graph.py/scheduler.py），LangGraph 提供图/checkpoint/interrupt 基础能力；agent-hive 差异化为"契约工作包 + 验收回流 + 架构安全验证 + 看板"等编排语义层，与 LangGraph 是"引擎之上补产品化"，与 LangSmith Platform 是"自研 vs 商业平台"的竞合关系。

### 4.2 CrewAI

- **定位**：【事实】角色化（role-based）多智能体编排框架：以 Crew（角色团队）为组织单位，agent 有 role/goal/backstory，Task 分配给对应角色；主打高层抽象、开箱即用（相对 LangGraph 的底层可控）[来源: https://docs.crewai.com/en/introduction, 2025-2026]。
- **编排模型**：【事实】三套抽象：① Crews（Task `context` 依赖 + `async_execution` 并行，sequential/hierarchical 流程）；② Flows（事件驱动，`@start/@listen/@router` 装饰器）；③ 平台事件（AMP 侧）[来源: https://docs.crewai.com/en/concepts/tasks, 2025-2026；https://docs.crewai.com/en/guides/flows/first-flow, 2026]。
- **HITL**：【事实】Task 级 `human_input=True`；Flow 级 `@human_feedback` 装饰器；异步后端 HITL 仍是社区痛点（issue #2051）[来源: https://github.com/crewAIInc/crewAI/blob/main/lib/crewai/src/crewai/flow/human_feedback.py, 2025；https://github.com/crewAIInc/crewAI/issues/2051, 2025]。
- **守卫与评估**：【事实】Task 级 `guardrail` 校验函数（返回 is_valid/feedback，失败可重试）；企业版 Hallucination Guardrail；无内置 eval 框架【未证实：与第三方护栏集成未见官方文档】[来源: https://docs.crewai.com/en/concepts/tasks, 2025-2026；https://docs.crewai.com/v1.15.4/en/enterprise/features/hallucination-guardrail, 2026]。
- **可观测性**：【事实】内置匿名 telemetry（可关）+ Langfuse 官方集成 + 平台 OTel 导出 [来源: https://docs.crewai.com/en/telemetry, 2026；https://docs.crewai.com/en/observability/langfuse, 2026]。
- **成本控制**：【推断】开源侧为"指导实践 + 记账数据"（官方 token 优化博客、社区 CI 成本门禁实践）；配额类在 AMP 平台侧 [来源: https://crewai.com/blog/how-to-optimize-token-spend-for-better-agentic-roi, 2025；https://community.crewai.com/t/field-note-treating-your-agents-token-spend-like-a-ci-cost-gate/7725, 2025]。
- **许可证与生态**：【事实】MIT 开源；stars 第一梯队（约 3 万+，2026 年中，推断精确值未核）；v1.0 起 MCP 原生；第三方称 2026-04 日生产执行 1200 万次（营销口径，二手）[来源: https://github.com/crewAIInc/crewAI, 2025-2026；https://agentmarketcap.ai/blog/2026/04/18/crewai-12m-daily-executions-mcp-a2a-production-scale, 2026-04]。
- **2025–2026 关键动态**：【事实】2025-10 OSS 1.0 GA；发布 AMP（Agent Management Platform）；版本线 1.0 → v1.15.x（10 个月 15+ 次 minor）[来源: https://crewai.com/blog/crewai-oss-1-0---we-are-going-ga, 2025；https://crewai.com/blog/crewai-amp---the-agent-management-platform, 2025]。

### 4.3 AutoGen / AG2 / Microsoft Agent Framework

- **定位**：【事实】三条线：微软原 AutoGen（0.4 起为事件驱动 actor 模型）；社区分叉 **AG2**（2024-11 成立，延续 0.2 路线）；**Microsoft Agent Framework**（2025-10 预览，AutoGen 与 Semantic Kernel 融合后的官方后继，.NET/Python/TS 三端，1.0 GA 于 2026-04【未证实：仅第三方 wiki 记录】）[来源: https://devblogs.microsoft.com/autogen/autogen-reimagined-launching-autogen-0-4/, 2025-01；https://www.infoworld.com/article/4067500/microsoft-unveils-framework-for-building-agentic-ai-apps.html, 2025-10；https://github.com/ag2ai/ag2, 2024-2026]。
- **编排模型**：【事实】AutoGen 0.4+：Teams（RoundRobin/SelectorGroupChat、MagenticOneGroupChat、Swarm、Workflow）；Magentic-One（2024-11 论文）内建为团队模式；Agent Framework：AgentThread/AgentChat/AgentRuntime + 代码优先 workflows（图式），可跑在 Azure AI Foundry Agent Service [来源: https://microsoft.github.io/autogen/0.6.2/reference/python/autogen_agentchat.teams.html, 2025-2026；https://arxiv.org/html/2411.04468v1, 2024-11；https://learn.microsoft.com/en-us/agent-framework/overview/agent-framework-overview, 2025-2026]。
- **HITL**：【事实】AutoGen `UserProxyAgent` + `interrupt`；Agent Framework 内置 `FunctionApprovalRequestContent`（工具调用审批内容载体）+ AgentThread 暂停/恢复 [来源: https://github.com/microsoft/agent-framework/issues/1318, 2026]。
- **守卫与评估**：【事实/未证实】AutoGen 无一等 guardrails API（Governance 扩展提案 issue #7613 未定稿）；Agent Framework guardrails/eval 未证实；评估以 GAIA 等外部基准实验为主 [来源: https://github.com/microsoft/autogen/issues/7613, 2025]。
- **可观测性**：【事实】AutoGen 0.4+ 内置 OTel trace；Agent Framework 内置 tracing（控制台/文件/VS Code/Azure Monitor/App Insights，Dynatrace 有官方集成文档）[来源: https://learn.microsoft.com/en-us/agent-framework/agents/observability, 2025-2026；https://docs.dynatrace.com/docs/observe/dynatrace-for-ai-observability/integrations/microsoft-agent-framework, 2026]。
- **成本控制**：【推断】usage 记账有、预算配额靠外部；Agent Framework 侧未证实 [来源: https://github.com/sapph1re/agent-cost-guardrails, 2025]。
- **许可证与生态**：【事实】AutoGen/AG2/Agent Framework 均 MIT（Agent Framework 的 MIT 为据仓库推断）；AutoGen 约 4 万 stars（推断）；生态处于"AutoGen 维护/迁移 → Agent Framework"交接期（官方迁移指南 + LangChain 2026 文章口径）[来源: https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-autogen/, 2025-2026；https://www.langchain.com/resources/langchain-vs-autogen, 2026]。
- **2025–2026 关键动态**：【事实】2024-10 预览 0.4 → 2025-01-17 0.4 GA；2024-11 AG2 分叉；2025-10 Agent Framework 预览；2026 Agent Framework 1.0 GA（4 月，第三方口径）、BUILD 2026 加 Agent Harness/Hosted Agents/CodeAct；AG2 至 v0.8.x [来源: https://aiwiki.ai/wiki/autogen/raw, 2026；https://www.smfclearinghouse.com/guides/agent-framework-landscape-august-2026/, 2026-08]。

### 4.4 MetaGPT

- **定位**：【事实】"SOP（标准操作流程）驱动的多智能体元编程框架"：把软件公司流水线（PM→架构师→工程师→QA）固化为多角色 SOP，一行需求 → PRD/设计/任务/代码；论文 arXiv:2308.00352（2023-08）[来源: https://github.com/FoundationAgents/MetaGPT, 2024-2026；https://arxiv.org/abs/2308.00352v2, 2023]。
- **编排模型**：【事实】Role + Environment + 结构化 Message（`send_to`/`cause_by` 字段，消息即角色间契约）+ Subscription 订阅路由；执行方式为 SOP 串行流水线，并行弱【推断】[来源: https://deepwiki.com/FoundationAgents/MetaGPT/2.3-message-schema-and-memory, 2025]。
- **HITL**：【推断】有限人工介入（投资决策示例等），无 Task 级一等 HITL 抽象；官方文档化审批机制【未证实】。
- **守卫与评估**：【事实】无内建 guardrails API；评估以论文基准实验为主（Data Interpreter，arXiv:2402.18679）；无内置 eval 框架【推断】[来源: https://arxiv.org/abs/2402.18679, 2024-02]。
- **可观测性**：【推断】日志级（含 token 花费记录），弱于 CrewAI/AutoGen。
- **成本控制**：【事实】日志记录 token 用量，无内建预算/配额【推断】。
- **许可证与生态**：【事实】MIT；stars 约 5 万（推断，同品类头部）；仓库由 geekan 迁移至 FoundationAgents 组织；2025-2026 版本主线 v0.8.x（v0.8.0 有据）；"MetaGPT 2.0"官方公告【未证实】[来源: https://github.com/FoundationAgents/MetaGPT/releases, 2025]。
- **与 agent-hive 相似度**：【事实/推断】四框架中哲学最接近（角色专家 + 消息契约 ≈ 契约工作包），但**无中央首脑、串行流水线、无验收回环、HITL/eval/可观测弱**——恰好构成 agent-hive 的差异化论证空间（详见第 6 节）。

### 4.5 OpenAI Agents SDK

- **定位**：【事实】OpenAI 官方开源 agent SDK（Python/TS），2025-03-11 随 "New tools for building agents" 发布，正式取代实验框架 Swarm [来源: https://community.openai.com/t/new-tools-for-building-agents-responses-api-web-search-file-search-computer-use-and-agents-sdk/1140896, 2025]。
- **编排模型**：【事实】Agent（tools/handoffs/guardrails）+ Runner（run/run_sync/run_streamed）+ Sessions（SQLiteSession 等会话记忆）；默认基于 Responses API（openai>=3.0.0）；MCP 一等公民；多 agent 靠 handoffs 交接（无 DAG 编排）[来源: https://openai.github.io/openai-agents-python/, 2025-2026]。
- **HITL**：【推断】工具中断/人工审批指南（HITL 指南 + 2026 "Guardrails and human review" 指南），无 hooks 式生命周期原语，属轻量 HITL [来源: https://github.com/openai/openai-agents-python/blob/main/docs/human_in_the_loop.md, 2025-2026；https://developers.openai.com/api/docs/guides/agents/guardrails-approvals, 2026]。
- **守卫与评估**：【事实】内置输入/输出 guardrail 函数（含 TripwireTriggeredException）；2026 新增 agent-evals 指南 [来源: https://developers.openai.com/api/docs/guides/agent-evals.md, 2026]。
- **可观测性**：【事实】内置 tracing **默认开启**，traces 在 platform.openai.com/traces 在线查看；支持自定义 trace processor；ZDR 组织不可用官方 tracing [来源: https://github.com/openai/openai-agents-python/blob/main/docs/tracing.md, 2025-2026]。
- **成本控制**：【事实】自动跟踪 token 用量（input/output/cached/reasoning），官方文档称可用于"监控成本、强制执行限制"；**无独立预算上限原语**【未证实】[来源: https://github.com/openai/openai-agents-python/blob/main/docs/usage.md, 2026]。
- **许可证与生态**：【事实】MIT；生态绑定 Responses API + o 系列推理模型；适配器可接 AnyLLM/LiteLLM 第三方模型 [来源: https://github.com/openai/openai-agents-python/blob/main/LICENSE, 2025]。
- **2025–2026 关键动态**：【事实】2025-03-11 发布；2026 年 0.8→0.22 高频迭代（0.22.0 @2026-08-19）；v0.14 Sandbox Agents GA；仍为 0.x 线【推断：1.0 未发布】[来源: https://pypi.org/pypi/openai-agents/json, 2026]。

### 4.6 Claude Agent SDK

- **定位**：【事实】Anthropic 官方 agent SDK（Python/TS），**2025-09-29** 随 Claude Sonnet 4.5 发布；本质是 Claude Code agent loop 的**无头（headless）编程封装**（Python 包自动捆绑 Claude Code CLI）[来源: https://www.pymnts.com/news/artificial-intelligence/2025/anthropic-claude-sonnet-4-5-introduces-claude-agent-sdk/, 2025-09；https://claude.com/blog/building-agents-with-the-claude-agent-sdk, 2025]。
- **编排模型**：【事实】`query()` + `ClaudeAgentOptions`；hooks 生命周期（PreToolUse/PostToolUse/UserPromptSubmit/SubagentStart/Stop）；**subagents**（自定义子代理，官方 Cookbook 有 "chief of staff" 首脑式示例）；MCP 支持；权限体系（permission_mode/can_use_tool/allowed_tools）[来源: https://code.claude.com/docs/en/hooks, 2025-2026；https://platform.claude.com/cookbook/claude-agent-sdk-01-the-chief-of-staff-agent, 2025-2026]。
- **HITL**：【事实】hooks 返回 "ask" 触发权限提示（人工审批）；`can_use_tool` 回调做工具级决策；社区对显式审批工具仍有诉求（issue #96）[来源: https://code.claude.com/docs/en/agent-sdk/permissions, 2025-2026；https://github.com/anthropics/claude-agent-sdk-python/issues/96, 2025]。
- **守卫与评估**：【推断】无独立 guardrail API，靠 hooks 拦截 + 权限策略；无内置 evals，评估靠 LangSmith 等第三方。
- **可观测性**：【事实】官方 OpenTelemetry 支持；LangSmith 官方集成（langsmith-sdk integrations/claude_agent_sdk）；Arize OpenInference 插桩包 [来源: https://code.claude.com/docs/en/agent-sdk/observability, 2025-2026；https://docs.langchain.com/langsmith/trace-claude-agent-sdk, 2025-2026]。
- **成本控制**：【事实】消息事件含 usage 信息；`max_turns` 可限制步数；**无预算原语**【未证实】[来源: https://github.com/anthropics/claude-agent-sdk-python/blob/main/README.md, 2025-2026]。
- **许可证与生态**：【事实】MIT（(c) 2025 Anthropic PBC）；生态锚点 = Claude Code + MCP 发起方 [来源: https://github.com/anthropics/claude-agent-sdk-python/blob/main/LICENSE, 2025]。
- **2025–2026 关键动态**：【事实】2025-09-29 发布；2026 年迭代至 0.2.145（2026-08-27）；第三方评估称 subagent 层级深达 5 层/200 上限、A2A 一等支持（SMF Clearinghouse 口径，与官方版本线有出入，谨慎引用）[来源: https://pypi.org/pypi/claude-agent-sdk/json, 2026；https://www.smfclearinghouse.com/guides/agent-framework-landscape-august-2026/, 2026-08]。

### 4.7 Google ADK（Agent Development Kit）

- **定位**：【事实】Google 官方开源 agent 开发框架，**2025-04** Cloud Next 2025 发布（与 A2A 协议同期；**与 Gemini 3 并不同期**——Gemini 3 于 2025-11 发布，ADK 首发于 Gemini 2.5 时代）[来源: https://developers.googleblog.com/en/agent-development-kit-easy-to-build-multi-agent-applications/, 2025；https://aibusiness.com/foundation-models/google-out-with-gemini-3-foundation-model, 2025-11]。
- **编排模型**：【事实】BaseAgent 层级：LlmAgent/SequentialAgent/ParallelAgent/LoopAgent + transfer（显式转交）→ hierarchical agents；**ADK 2.0**（2026）新增 graph-based workflow 引擎（DAG）；session/checkpoint 持久化；工具含 MCP [来源: https://github.com/google/adk-python/blob/main/.agents/skills/adk-architecture/SKILL.md, 2025-2026；https://developers.googleblog.com/announcing-adk-go-20/, 2026]。
- **HITL**：【事实】内置生命周期回调（before/after_agent、before/after_model、before/after_tool、on_error）；ADK 2.0 宣称内建 human-in-the-loop；`session.user_content_callback` 确切 API 命名【未证实】[来源: https://github.com/google/adk-docs/blob/main/docs/callbacks/types-of-callbacks.md, 2025-2026]。
- **守卫与评估**：【事实】**内置 evals 模块**（`adk eval` CLI）：test files（轨迹校验）+ datasets（批量），groundtruth/rubric + LLM-as-judge 最终回答质量评分；可联动 Vertex AI Agent Engine [来源: https://github.com/google/adk-docs/blob/main/docs/evaluate/index.md, 2025-2026]。
- **可观测性**：【事实】基于 OpenTelemetry；Arize 官方指南（含 Phoenix）；Vertex AI/Agent Engine 深度集成；Cloud Trace/Langfuse 官方集成【未证实】[来源: https://arize.com/blog/tracing-evaluation-and-observability-for-google-adk-how-to/, 2025]。
- **成本控制**：【未证实】未见预算原语；成本靠用量监控 + evals 约束。
- **许可证与生态**：【事实】Apache-2.0；多语言 Python/TS/Go/Java；生态锚点 = Gemini/AI Studio + Vertex AI + A2A [来源: https://github.com/google/adk-python/blob/main/LICENSE, 2025]。
- **2025–2026 关键动态**：【事实】2025-04 发布；2026 ADK 2.0 / ADK Go 2.0（图式工作流 + 内建 HITL）；google-adk 迭代至 2.8.0（2026-08-26）[来源: https://pypi.org/pypi/google-adk/json, 2026]。

### 4.8 Pydantic AI

- **定位**：【事实】Pydantic 团队（FastAPI 生态）出品的**类型安全 Python agent 框架**：Pydantic 模型即 LLM 输入输出契约，输出自动校验/重试（structured outputs）；2024-12 正式对外 [来源: https://pydantic.dev/docs/ai/, 2025-2026；https://www.infoq.com/news/2024/12/pydanticai-framework-gen-ai/, 2024-12]。
- **编排模型**：【事实】核心 `Agent`（tools/deps/结构化输出/streaming/MCP）；**Graph API**（pydantic-graph，DAG 编排）2025-05 加入，v2 转正 [来源: https://ai.pydantic.dev/graph/, 2025-2026]。
- **HITL**：【推断】无统一 first-class 人工审批原语；官方提供 AG-UI（Agent User Interaction）交互示例；issue #3274 讨论多 agent HITL 审批 [来源: https://pydantic.dev/docs/ai/examples/ag-ui/, 2026；https://github.com/pydantic/pydantic-ai/issues/3274, 2026]。
- **守卫与评估**：【事实】evals 文档（LLM-as-judge/对比评测/回归测试）+ 官方 LLM-as-Judge 文章；类型校验本身构成输出守卫 [来源: https://github.com/pydantic/pydantic-ai/blob/main/docs/evals.md, 2025-2026]。
- **可观测性**：【事实】与 **Pydantic Logfire** 深度集成（tracing/调试/监控）[来源: https://github.com/pydantic/pydantic-ai/blob/main/docs/logfire.md, 2025-2026]。
- **成本控制**：【未证实】官方文档未见 token 预算/成本上限原语。
- **许可证与生态**：【事实】MIT；2026-05 第三方榜单为增长最快 agent 框架之一；Thoughtworks Radar 收录；star 约 4 万+ 量级（推断）[来源: https://presenc.ai/research/ai-agent-framework-github-rankings-2026, 2026-05；https://www.thoughtworks.com/en-br/radar/languages-and-frameworks/pydantic-ai, 2026]。
- **2025–2026 关键动态**：【事实】**v1.0 于 2025-09**；2026 年中 v2（精简核心、Graph 转正、Harness）；2026-08 已至 v2.34.0 [来源: https://raw.githubusercontent.com/pydantic/pydantic-ai/f4154dfb0104085038b57e1742370595cc59ef20/docs/changelog.md, 2025-09；https://github.com/pydantic/pydantic-ai/releases/tag/v2.34.0, 2026-08]。

### 4.9 AWS Bedrock AgentCore

- **定位**：【事实】AWS 托管 **agent 运行时/控制面**：统一管理状态（state management）、action groups（工具）、记忆（memory）、guardrails、policy 与可观测性；可与 LangGraph 等外部框架互操作（把外部框架 agent 部署到 AgentCore 托管），定位"框架编排 + 平台托管"互补而非替代【推断】[来源: https://aws.amazon.com/bedrock/agentcore/, 2025-2026；https://venturebeat.com/ai/aws-unveils-bedrock-agentcore-a-new-platform-for-building-enterprise-ai-agents-with-open-source-frameworks-and-tools, 2024-12]。
- **发布时间线**：【事实】2024-12 re:Invent 预览 → **2025-10 GA（含东京区域）** → 2025-10 官方 MCP server → 2026-06 Step Functions agentic reasoning 集成 → 2026-08 多 agent persistent compute [来源: https://aws.amazon.com/jp/about-aws/whats-new/2025/10/amazon-bedrock-agentcore-available/, 2025-10；https://www.infoq.com/news/2026/08/aws-bedrock-agentcore-runtime/, 2026-08]。
- **编排模型**：【事实】AgentCore 是底层托管运行时（区别于低代码构建器 Bedrock Agents）；多 agent 协作经官方示例仓库 + 2026-08 persistent compute 常驻运行时支撑 [来源: https://repost.aws/questions/QUjkf4WbikQ6WrpuH9sppjnw/bedrock-agents-vs-bedrock-agentcore, 2025；https://github.com/aws-samples/sample-multi-agent-on-agentcore, 2025-2026]。
- **HITL**：【未证实】AgentCore 本身无 first-class 人工审批 API；官方仅示例仓库（sample-human-in-the-loop-patterns），常借外部框架（LangGraph）实现后部署 [来源: https://github.com/aws-samples/sample-human-in-the-loop-patterns, 2025-2026]。
- **守卫与评估**：【事实】guardrails 集成（Bedrock Guardrails 体系）与 policy 服务；架构级安全验证无（见第 5 节）[来源: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/release-notes.html, 2025-2026]。
- **可观测性**：【事实】CloudWatch 指标/日志 + X-Ray/ADOT tracing（CDK/Terraform 可配）[来源: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/release-notes.html, 2025-2026]。
- **成本控制**：【事实】官方定价页存在，按调用（per-invocation）计费；单价细节未核实【未证实】[来源: https://aws.amazon.com/bedrock/agentcore/pricing/, 2025-2026]。
- **多租户与合规**：【事实】AWS 托管商业服务：region 化部署（含东京）、IAM/Policy 治理、AWS 企业合规背书、"不用于训练"承诺（Bedrock 通用层面）[来源: https://aws.amazon.com/bedrock/agentcore/, 2025-2026]。
- **许可证**：【事实】非开源，AWS 商业服务（随用随付）；配套 aws-samples/starter-toolkit 为示例代码。
- **2025–2026 关键动态**：【事实】预览（2024-12）→ GA（2025-10）→ Step Functions 集成（2026-06）→ persistent compute（2026-08）[来源: 同上各条]。

### 4.10 扣子 Coze（字节跳动）与开源 coze-studio

- **定位**：【事实】字节跳动"一站式 AI 开发平台"：低代码构建 bot/智能体/工作流；国内版扣子（coze.cn，火山引擎体系）+ 国际版 coze.com 双版本；2025-08 与小米应用商店合作 [来源: https://docs.coze.cn, 2024-2026；https://news.hexun.com/2025-08-01/220695990.html, 2025-08]。
- **编排模型**：【事实/推断】可视化工作流（DAG 节点图）+ 单 agent 会话；比代码编排（LangGraph/Pydantic AI）更产品化、模板化，复杂动态编排弱于代码框架【推断】[来源: https://docs.coze.cn, 2024-2026]。
- **HITL**：【事实】工作流提供**人工审核节点**（流程暂停、接入审批流、人工确认后续）[来源: https://www.php.cn/faq/2599787.html, 2025]。
- **守卫与评估**：【事实】平台内容安全/审核体系（字节审核能力）、"大模型应用防火墙"插件、2025 年"AI 全链路功能安全统一配置体系"；无公开 eval 框架 [来源: https://bytedance.larkoffice.com/wiki/ECFZwGJVZi1wGYkPLntca4oXnEg, 2025]。
- **可观测性**：【事实/推断】云版平台内运行调试/trace（黑盒）；开源 coze-loop 组件提供日志与 trace 集成 [来源: https://www.coze.cn/open/docs/cozeloop/trace_integrate, 2025-2026]。
- **成本控制**：【事实】平台按 token/模型调用计费 + 订阅套餐 + 企业版（2026-01-19 订阅升级公告、企业版套餐定价调整公告）[来源: https://docs.coze.cn/api/open/docs/coze_pro/model_fee, 2025-2026；https://docs.coze.cn/guides_20260119_coze_premium_upgraded, 2026-01]。
- **开源 coze-studio**：【事实】**2025 年 7 月下旬**字节宣布将 Coze Studio（可视化 agent 开发平台）与 Coze Loop（运行/trace 组件）开源，**Apache-2.0**，支持商用（媒体 7-26/7-28 报道）；上线两天 GitHub star 破万；可 Docker 自托管；Coze Loop 主打"评测 + 线上观测 + 优化迭代"闭环；截至 2025-06 扣子月访问用户约 458 万（非凡产研数据）[来源: https://m.ithome.com/html/870904.htm, 2025-07；https://www.chinaz.com/ainews/19989.shtml, 2025-07-28；https://www.geekpark.net/news/352159, 2025；https://www.infoq.cn/article/a4ikxoqf5tfq24izedcl, 2025；https://github.com/coze-dev/coze-studio, 2025-2026]。
- **多租户与合规**：【事实/未证实】国内版数据在国内、国际版数据域分离；跨境合规横评存在；数据中心属地/训练承诺原文【未证实】[来源: https://www.yun88.com/news/11551.html, 2025-2026]。
- **2025–2026 关键动态**：【事实】2025 开源双件套；"扣子空间"（AI Office 产品线）；企业版 B 端商业化演进；2026-01 订阅升级 [来源: 同上各条]。

**简述：Dify 与 Qwen-Agent**
- **Dify**：【事实】开源 LLMOps 平台（LangGenius）：可视化 workflow、agent 框架、RAG、插件生态；2025-02 v1.0.0；2026-03 **$30M Pre-A**；公开口径 Docker 拉取超 1 亿、star 约 7.75 万；定位为"应用平台层"竞品（与 Coze 高度重叠）[来源: https://dify.ai/blog/dify-v1-0-building-a-vibrant-plugin-ecosystem, 2025-02；https://investor.wedbush.com/wedbush/article/bizwire-2026-3-9-dify-raises-30-million-series-pre-a-to-power-enterprise-grade-agentic-workflows, 2026-03]。
- **Qwen-Agent**：【事实】阿里通义（QwenLM）开源 agent 框架，**Apache-2.0**：工具调用/浏览器/代码解释器/多 agent；强绑定 Qwen 模型生态（模型-框架协同优化）[来源: https://qwenlm.github.io/Qwen-Agent/, 2024-2026]。

### 4.11 一页式框架速览表（2026-08 快照）

| 框架 | 发布 | 当前版本（2026-08） | 许可证 | 编排核心 | 生态锚点 | 一句话点评 |
|---|---|---|---|---|---|---|
| LangGraph | 2023-01（1.0：2025-10-22） | 1.2.x | MIT（库）/商业平台 | 显式图 + supervisor | LangChain/LangSmith 生态 | 生态最深、可控性最强 |
| CrewAI | 2023-11 | v1.15.x | MIT + AMP 商业 | Crews + Flows（事件） | 企业 AMP 平台 | 易用性标杆、商业化快 |
| AutoGen | 2023-08（0.4：2025-01） | 0.6.x（维护中） | MIT | Teams/事件驱动 actor | 微软生态 | 进入迁移交接期 |
| AG2 | 2024-11（分叉） | v0.8.x | MIT | GroupChat（0.2 路线） | 社区 | 社区接盘线，生态碎片 |
| Microsoft Agent Framework | 2025-10（1.0：2026-04） | 1.0+ | MIT（推断） | AgentThread/Workflow | .NET/Azure | .NET 与 Azure 原生 |
| MetaGPT | 2023-08 | v0.8.x | MIT | SOP + Role + Message | 学术/开源社区 | 哲学同源、工程供给弱 |
| OpenAI Agents SDK | 2025-03-11 | 0.22.0 | MIT | Agent + Runner + handoffs | Responses API + o 系列 | OpenAI 栈最轻路径 |
| Claude Agent SDK | 2025-09-29 | 0.2.145 | MIT | Claude Code 无头 + hooks | Claude Code + MCP | 编码 agent 能力最强 |
| Google ADK | 2025-04 | 2.8.0（2.0 系） | Apache-2.0 | BaseAgent 层级 + graph | Gemini/Vertex/A2A | 内置 evals 成体系 |
| Pydantic AI | 2024-12 | v2.34.0 | MIT | Agent + pydantic-graph | FastAPI/Pydantic 生态 | 类型安全增长最快 |
| Bedrock AgentCore | 2024-12（预览） | GA（2025-10） | AWS 商业服务 | 托管运行时（状态/工具/记忆） | AWS 合规/region | "编排框架 + 平台托管"分工 |
| 扣子 Coze | 2023-12 | 云版 + coze-studio 开源 | 平台 + Apache-2.0（开源件） | 工作流 DAG + 单 agent | 字节/火山生态 | 低代码 + 国内合规 |

> 注：版本号为 PyPI/官方发布实证（见第 9.3 核查清单）；"当前版本"随发布节奏变化，引用前请复核。

### 4.12 关键能力横向对比（HITL / 守卫 / 评估 / 可观测 / 成本 / 断点）

| 框架 | HITL 形态 | 守卫（guardrails） | 内置评估 | 可观测性 | 成本预算原语 | 断点续跑 |
|---|---|---|---|---|---|---|
| LangGraph/Platform | interrupt + checkpoint（审批式，最成熟） | ◐ 组合式（middleware/ValidationNode/NeMo 集成） | ◐ LangSmith 侧 | ✅ LangSmith 原生 | ◐ 追踪+告警，无组织级预算 | ✅ checkpoint/时间旅行 |
| CrewAI | ◐ human_input/@human_feedback | ✅ Task 级 guardrail + 企业幻觉护栏 | ✖（靠外部） | ◐ telemetry + Langfuse/OTel | ◐ 记账/指导 | ◐ |
| AutoGen/AG2 | ◐ UserProxy/interrupt | ✖（提案未定稿） | ✖（外部基准） | ◐ OTel trace | ◐ usage 记账 | ◐ 会话 |
| MS Agent Framework | ✅ FunctionApprovalRequestContent | 【未证实】 | 【未证实】 | ✅ tracing（Azure Monitor） | 【未证实】 | ◐ |
| MetaGPT | ✖ | ✖ | ✖ | ◐ 日志级 | ✖ | ✖ |
| OpenAI Agents SDK | ◐ 工具中断/审批指南 | ✅ 输入/输出 guardrail 函数 | ◐ 2026 agent-evals 指南 | ✅ 内置 tracing 默认开 | ◐ usage 跟踪（无预算） | ◐ sessions |
| Claude Agent SDK | ◐ hooks "ask" 权限提示 | ◐ hooks 拦截 + 权限策略 | ✖ | ◐ OTel + LangSmith/Arize | ◐ usage + max_turns | ◐ |
| Google ADK | ◐ 回调 + 2.0 内建 | ◐ 回调 | ✅ `adk eval` CLI（轨迹 + LLM-as-judge） | ◐ OTel + Arize/Vertex | ✖ | ✅ session/checkpoint |
| Pydantic AI | ◐ AG-UI/中断恢复 | ✅ 类型校验即守卫 | ✅ evals + LLM-as-Judge | ◐ Logfire | ✖ | ◐ |
| Bedrock AgentCore | ◐ 示例仓库（无 first-class） | ◐ Bedrock Guardrails | ✖ | ◐ CloudWatch + X-Ray | ◐ 按调用计费 | ✅ 托管状态管理 |
| 扣子 Coze | ◐ 工作流人工审核节点 | ◐ 平台安全/防火墙插件 | ✖ | ◐ coze-loop trace | ◐ 套餐 + 计费 | ◐ 会话恢复 |
| agent-hive（本项目） | ✅ 双审批关口 + async_hitl | ✅ 输入/输出守卫 + 熔断守卫 | ◐ 验收评审（评估-优化回路） | ◐ 成本落账（cost.json，trace 待补） | ✅ 预算→监控→降级 | ✅ SQLite checkpoint |

> 注：本表为第 7 节 13 维表的"能力摘要版"，图例与判定依据一致；agent-hive 列依据项目源码与文档（自评口径）。

---

## 5. 特别调研 A：AI 生成架构/设计的安全验证类产品

> 目标：确认市场上是否存在与 agent-hive「AI 生成架构安全验证」模块（规则引擎查幻觉引用/循环依赖/缺失安全控制 + LLM 语义威胁建模 STRIDE，插入审批关口前）对标的成熟产品。本节省略来源细节，完整来源见 `docs/_research_notes/special-research.md`。

### 5.1 DeepSec 系（AI 生成代码扫描）

- 【事实】**Vercel deepsec**（noeljackson/deepsec，2025-08 发布）：基于 coding agent 的代码库漏洞扫描安全 harness（语义扫描、定位并修复漏洞）；2026-05 有报道称 Vercel 将其开源 [来源: https://vercel.com/blog/introducing-deepsec-find-and-fix-vulnerabilities-in-your-code-base, 2025-08；https://devops.com/vercels-deepsec-brings-ai-powered-security-scanning-into-the-development-workflow/, 2025-2026]。
- 【事实】**Unclecheng-li/DeepSec**：Shield 模块实时审计 AI 生成代码的**幻觉依赖包、缺失安全防护、AI 模式错误**；Spear 为自动化授权渗透测试——Shield 三查与 agent-hive 规则引擎（幻觉引用/循环依赖/缺失安全控制）**高度同构**，但作用于**代码**层面 [来源: https://github.com/Unclecheng-li/DeepSec, 2025-2026]。
- 【推断】二者均扫描"已生成的代码/依赖"，**未见专门验证"AI 生成的架构/设计方案（依赖图、威胁模型）"并插入审批关口前**的产品化形态；「Vercel AI Security」独立产品线【未证实】。

### 5.2 威胁建模 agent 与安全扫描生态

- 【事实】威胁建模平台：**IriusRisk「Jeff: AI Assistant」**（AI 辅助威胁建模）+ iriusrisk-cli；**ThreatModeler AI**（持续更新）——覆盖"LLM 语义威胁建模"的成熟商业替代，但**独立于编排流水线**，不做验收回流闭环 [来源: https://www.globalsecuritymag.fr/iriusrisk-has-announced-the-launch-of-jeff-ai-assistant.html, 2024-2025；https://threatmodeler.com/products/platform/, 2025-2026]。
- 【事实】框架/标准：MITRE ATLAS；OWASP LLM Top 10（2025 版）；**OWASP Top Ten AI Agent Threats**（2025-12 发布，agent 特有威胁清单，可作规则来源）；微软 2025 开源 agent 网络安全调查评测基准 [来源: https://genai.owasp.org/download/45674/, 2025；https://securityboulevard.com/2025/12/owasp-project-publishes-list-of-top-ten-ai-agent-threats/, 2025-12；https://www.scworld.com/news/microsoft-announces-open-source-benchmark-for-ai-agent-cybersecurity-investigations, 2025]。
- 【事实】运行时防护/红队成熟品类：Cloudflare for AI（AI 防火墙）、Lakera Guard、NVIDIA NeMo Guardrails、Cisco（2024 收购 Robust Intelligence，2025-2026 以 Foundation AI 延续）、garak（NVIDIA）与 PyRIT（微软）为开源 LLM 漏洞扫描主流（ICSE 2025 RAIE 有比较研究）[来源: https://delphisecurity.ai/blog/best-ai-firewalls-2026, 2026；https://conf.researchr.org/details/icse-2025/raie-2025-papers/7/Insights-and-Current-Gaps-in-Open-Source-LLM-Vulnerability-Scanners-A-Comparative-An, 2025]。
- 【事实】agent 安全评测基准（2024-2026 新增）：AgentDojo、AgentThreatBench（OWASP Agentic Threats）、AgentBench、HarmBench 等；InspectorBench（微软）官方一手来源【未证实】[来源: https://www.floriantramer.com/publications/agentdojo24/, 2024-2025；https://ukgovernmentbeis.github.io/inspect_evals/evals/agent_threat_bench/, 2025-2026]。

### 5.3 contract-driven development agents

- 【事实】**GitHub Spec Kit**（github/spec-kit，2025-09 开源）："Spec-Driven Development"工具包（workspace → spec → plan → 实现），spec 先行 [来源: https://github.com/github/spec-kit, 2025-09]。
- 【事实】微软开源项目 hve-core 存在"System Architecture Reviewer for ADR"的真实企业需求（issue #92）——**架构评审 agent + ADR** 的需求实例 [来源: https://github.com/microsoft/hve-core/issues/92, 2025]。
- 【推断】成熟商业"契约驱动开发 agent"产品**未见**；该方向处于早期（工具侧 spec-first 脚手架 + 企业自研为主），尚无把"契约（接口/expected_output/depends_on）+ 自动验收回流"产品化为通用契约层的商业产品。

### 5.4 Part A 结论

- 【事实】三个相邻赛道均有成熟产品：① AI 生成**代码**安全扫描（Vercel deepsec、Unclecheng-li DeepSec Shield）；② LLM/agent 运行时防护与红队（Cloudflare/Lakera/garak/PyRIT/Cisco）；③ 威胁建模辅助与安全标准（IriusRisk/ThreatModeler/OWASP/MITRE/评测基准）。
- 【推断】**「架构级（非代码级）双通道验证 + 编排内嵌 + 审批关口 + 验收回流联动」无直接商业对标**；现有产品要么作用于代码/运行时，要么独立于编排。这是 agent-hive 安全验证模块的差异化空间。
- 【未证实】「Vercel AI Security」产品线、TrojAI/Bedrock Guardrails/rebuff 一手页面、InspectorBench 官方来源。

---

## 6. 特别调研 B：「首脑统筹 + 角色专家 + 契约工作包 + 评估优化回路」组合的行业出现情况

> 目标：确认该组合（agent-hive 核心架构）在哪些产品/论文中出现过、趋同程度如何。完整来源见 `docs/_research_notes/special-research.md`。

### 6.1 四要素在各产品中的出现情况【事实】

| 产品/框架 | 首脑统筹 | 角色专家 | 契约/工作包 | 评估-优化回路 | 来源 |
|---|---|---|---|---|---|
| **MetaGPT**（2023） | △ SOP 编排无中央首脑 | ✅ 多角色（PM/架构/工程/QA） | △ 结构化 Message 协议（send_to/cause_by）≈契约 | △ 论文含反馈迭代，非强闭环 | [arXiv:2308.00352](https://arxiv.org/abs/2308.00352v2), 2023 |
| **CrewAI** | △ 层级流程 manager（可选） | ✅ crews（role/goal/backstory） | △ Task expected_output + context 依赖 | △ 自校正仍为 issue 诉求（[#3015](https://github.com/crewAIInc/crewAI/issues/3015), 2025） | [docs.crewai.com](https://docs.crewai.com/en/concepts/tasks), 2025-2026 |
| **LangGraph** | ✅ supervisor 模式（官方 langgraph-supervisor） | ✅ subagents | △ TypedDict state schema（面向图状态非工作包） | △ 无内建验收-回流，需自建 | [reference.langchain.com](https://reference.langchain.com/python/langgraph-supervisor), 2025 |
| **AutoGen/AG2** | ✅ GroupChat manager/发言者选择 | ✅ 多 agent | △ 会话/消息流 | △ | [AG2 docs](https://docs.ag2.ai/latest/docs/user-guide/advanced-concepts/groupchat/custom-group-chat/), 2025 |
| **Microsoft Agent Framework** | △ Teams 为容器，无强制 supervisor | ✅ | △ workflow 图式 | △ | [microsoft/agent-framework](https://github.com/microsoft/agent-framework/discussions/6858), 2025 |
| **OpenAI Agents SDK** | ✅ triage/handoffs（轻量首脑） | ✅ | △ function schema | △ | [openai-agents-python handoffs](https://github.com/openai/openai-agents-python/blob/db68d1c3/docs/handoffs.md), 2025 |
| **Claude Agent SDK** | ✅ Cookbook "chief of staff" 首脑示例 | ✅ subagents | △ | △ | [Claude Cookbook](https://platform.claude.com/cookbook/claude-agent-sdk-01-the-chief-of-staff-agent), 2025-2026 |
| **Google ADK** | ✅ hierarchical agents + transfer | ✅ | △ 类型化状态 | △ evals 有、回流无 | [google/adk-docs multi-agents](https://github.com/google/adk-docs/blob/90250a53d8a8ba2671733b2c143a7888ba347766/docs/agents/multi-agents.md), 2025 |

### 6.2 评估-优化回路与契约/工作包类工具【事实】

- **自动优化**：DSPy / TextGrad / AdalFlow（prompt/程序自动优化框架族，PyCon DE 2025 综述）；LangSmith evals + prompt optimization（Align Evals）；CrewAI 自校正为特性诉求（见上表）[来源: https://2025.pycon.de/talks/GURXPK/, 2025]。
- **工作包/计划**：GitHub Copilot Workspace（issue→计划→实现→PR）；Claude Code tasks/sub-agents（plan/do 分离）；Aider architect 模式（ask/architect 双模式）；spec-kit（spec 先行）；Plan-and-Solve 论文（arXiv:2305.04091, 2023）为经典规划范式 [来源: https://github.blog/ai-and-ml/github-copilot/from-idea-to-pr-a-guide-to-github-copilots-agentic-workflows/, 2025；https://simonwillison.net/2025/Oct/11/sub-agents/, 2025-10]。

### 6.3 结论【事实 + 推断】

- 【事实】四大要素**每一项单独**均已在 2023–2026 年主流框架/产品中出现；2025–2026 各大框架都在向「orchestrator + 角色 + 结构化交接 + 评测闭环」补齐（CrewAI 加 Flows、微软加 Teams/Sessions、Anthropic 出 subagents+hooks）。
- 【推断】agent-hive 的相对差异点不在"有没有这些机制"，而在三点产品化取舍：① **显式契约字段一等公民**（接口契约/expected_output/depends_on，而非隐含状态）；② **验收-回流≤3 轮的强闭环**（而非软评测/prompt 优化）；③ **架构安全验证模块内嵌审批关口**（第 5 节：无直接商业对标）。三者组合截至 2026-08 未见完全同构产品。
- 【未证实】2026 年 H2 是否存在新发布的完全同构商业/开源产品（检索窗口有限）。

---

## 7. 能力维度对照表（13 维 × 12 框架）

> 图例：**✅** 内置/一等支持 ｜ **◐** 部分支持或需自建 ｜ **✖** 无 ｜ **🔌** 主要靠第三方/插件补齐
> 判定依据：第 4–6 节的事实与来源；"agent-hive（本项目）"列依据仓库 `docs/card-*.md` 与 `agent_hive/*.py` 源码（自评，非外部评测）。

| # | 能力维度 | LangGraph/Platform | CrewAI | AutoGen/AG2 | MS Agent Framework | MetaGPT | OpenAI Agents SDK | Claude Agent SDK | Google ADK | Pydantic AI | Bedrock AgentCore | 扣子 Coze | agent-hive（本项目） |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 依赖感知任务调度 | ✅ 图/DAG+Send fan-out（1.0 deferred nodes） | ◐ Task context 依赖 + Flows 事件 | ◐ GroupChat/Workflow 图式 | ✅ 代码优先 workflows | ◐ SOP 串行（并行弱） | ✖ handoffs 无 DAG | ✖ subagent 层级 | ✅ 层级 + graph 2.0 | ✅ pydantic-graph DAG | ◐ action groups / multi-agent | ◐ 工作流 DAG | ✅ scheduler 依赖图 + 同层 fan-out + 返工依赖门 |
| 2 | HITL 审批队列 | ✅ interrupt + checkpoint（平台 HITL API） | ◐ human_input / @human_feedback | ◐ UserProxyAgent / interrupt | ✅ FunctionApprovalRequestContent + 暂停/恢复 | ✖ 有限介入 | ◐ 工具中断/审批指南 | ◐ hooks "ask" 权限提示 | ◐ 回调 + 2.0 内建 | ◐ AG-UI / 中断恢复 | ◐ 仅示例仓库（无 first-class） | ◐ 工作流人工审核节点 | ✅ async_hitl + 双审批关口（审批①/②） |
| 3 | Prompt 版本化 + A/B | ◐ LangSmith 侧（版本化/playground/A-B 实验） | ✖ | ✖ | ✖ | ✖ | ✖ | ✖ | ✖ | ✖ | ✖ | ◐ 平台内版本管理 | ◐ prompt_management 卡片（规划） |
| 4 | 成本预算与降级 | ◐ LangSmith 成本追踪（无预算原语） | ◐ 记账 + 指导实践 | ◐ usage 记账 | ◐ Azure 侧 | ✖ 仅日志 | ◐ usage 跟踪（无预算原语） | ◐ usage + max_turns | ✖ | ✖ | ◐ 按调用计费 | ◐ 套餐 + token 计费 | ✅ cost_control（预算→监控→降级，已实现） |
| 5 | 模型容错/熔断 | ◐ 1.2 per-node 超时/重试策略 | ◐ 任务重试 | ◐ SDK 重试 | ◐ 运行时重试 | ✖ | ◐ SDK 重试/backoff | ✖ 靠 CLI 层 | ◐ on_error 回调 | ◐ 输出校验重试 | ◐ 托管重试 | ◐ 平台重试 | ✅ model_resilience（429/503/超时降级，已实现） |
| 6 | 工具注册表 | ◐ 函数/MCP（无中央注册表） | ◐ tools | ◐ tools | ◐ tools/MCP | ✖ | ◐ tools/MCP | ◐ tools/MCP | ✅ toolkits | ◐ tools/MCP | ✅ action groups | ✅ 插件/工具市场 | ◐ tool_registry 卡片（规划） |
| 7 | 流式输出 | ✅ streaming（1.2 streaming v3） | ✅ | ✅ | ✅ | ◐ | ✅ run_streamed | ✅ | ✅ | ✅ | ◐ | ◐ | ◐ streaming 卡片（规划） |
| 8 | 多租户 | ◐ Platform 部署级（OSS 无） | ◐ AMP | ✖ | ◐ Azure 托管 | ✖ | ✖ | ✖ | ✖ | ✖ | ✅ AWS 托管（账号/region） | ✅ SaaS 平台 | ◐ multi_tenancy 卡片（规划） |
| 9 | 数据合规 | ◐ 自托管 BYO / Platform 区域 | ◐ 平台侧 | ✖ | ✅ Azure 合规体系 | ✖ | ✖ | ✖ | ✖ | ✖ | ✅ region + IAM + 不训练承诺 | ◐ 国内/国际数据域分离 | ◐ data_compliance 卡片（规划） |
| 10 | 架构安全验证 | ✖ | ✖ | ✖ | ✖ | ✖ | ✖ | ✖ | ✖ | ✖ | ◐ guardrails（运行时，非架构级） | ◐ 防火墙插件（非架构级） | ✅ arch_security（规则引擎 + LLM 语义威胁建模，已实施） |
| 11 | 契约单一事实源 | ◐ TypedDict state schema | ◐ expected_output 描述 | ✖ | ◐ workflow schema | ◐ Message 协议 | ◐ function schema | ✖ | ◐ 类型化状态 | ✅ Pydantic 模型即契约 | ✖ | ✖ | ✅ contract_spec 机器可读源 + 漂移检查（已实施） |
| 12 | 项目看板 | ✖ | ✖ | ✖ | ✖ | ✖ | ✖ | ✖ | ✖ | ✖ | ✖ | ◐ 平台控制台 | ✅ 工件状态机全程可审计（待派发→进行中→待验收→通过/返工→熔断/阻塞） |
| 13 | 断点续跑 | ✅ checkpointer/thread（标志能力） | ◐ | ◐ 会话状态 | ◐ | ✖ | ◐ sessions（对话记忆） | ◐ | ✅ session/checkpoint | ◐ | ✅ 托管状态管理 | ◐ 会话恢复 | ✅ SQLite checkpoint + --run-id/--thread-id（已实施） |

**读表要点**【推断】：
1. **13 维中"绿色"最少的是 MetaGPT（6 ✖），最全的是 LangGraph/Platform 与 agent-hive**——前者靠商业平台（LangSmith/Platform）补位，后者靠自研模块；
2. **架构安全验证（维度 10）与项目看板（维度 12）全行业空白**，agent-hive 目前是唯一"已实施"的对照项（自评口径）；
3. **契约单一事实源（维度 11）** 只有 Pydantic AI（类型契约）与 agent-hive（工作包契约）做到"一等公民"；
4. **成本预算（维度 4）、模型熔断（维度 5）** 在所有主流框架中均无一等原语，属自研框架的机会区；
5. 多租户/合规（维度 8/9）的答案几乎全在"平台层"（LangGraph Platform、AMP、Azure、AWS、Coze SaaS），**开源框架 + 自托管的企业级能力依赖自研**。

---

## 8. 竞争格局结论与 agent-hive 定位建议

### 8.1 格局判断【推断】

1. **需求侧**：生产采用加速（57.3%）、质量是头号障碍（32%）、评估与安全缺口明显（52%/24.9%）、成本关注度下降但预算能力缺失——市场需要"**质量/评估/安全/工程化**"四位一体的框架与平台。
2. **供给侧**：四强（LangGraph/Agent Framework/OpenAI/Claude SDK）各有模型或平台绑定；CrewAI 靠易用性 + AMP 商业化；MetaGPT 哲学接近但工程供给弱；Pydantic AI 靠类型安全 + 增长势能；AgentCore/Coze 卡位托管与低代码；**没有一家把"契约工作包 + 验收回流 + 架构安全验证"做成产品主线**。
3. **趋同方向**：各大框架都在补 orchestrator/交接/评测闭环，但"显式契约 + 强验收回路 + 架构级安全验证"的组合仍是空白（第 5、6 节）。

### 8.2 对 agent-hive 的定位建议【推断】

1. **差异化叙事**：从"又一个编排框架"转向"**契约驱动的多智能体工程平台**"——首脑统筹 + 契约工作包（一等公民）+ 验收回流（≤3 轮熔断）+ 架构安全验证（内嵌审批关口），用第 7 节"空白维度"（10/11/12 及 4/5）做竞争地图。
2. **工程化补齐**：可观测性/评估是行业标配（89%/52%），agent-hive 需提供等价物（trace/evals 对齐 LangSmith 体验）；多租户、合规、流式、分布式（card-*.md 规划项）决定企业级可售性。
3. **生态兼容**：借鉴 AgentCore 的"框架编排 + 平台托管"分工，预留 MCP/A2A 与托管运行时接入；借鉴 Pydantic AI 的"契约即校验"、ADK 的"内置 evals"。
4. **证据引用纪律**：对外材料只引用【事实】条目；【未证实】项（star 数、单价、Agent Framework GA 日期等）上线前复核。

---

## 9. 来源统计与附录

### 9.1 来源数量统计

- 本报告正文引用的唯一来源 URL 数：**174 个**（正则去重统计，2026-08-28）。
- 调研中间证据（`docs/_research_notes/`，保留供审计）：
  - `special-research.md`：12 次 web_search，28 项来源清单；
  - `framework-crewai-autogen-metagpt.md`：15 次 web_search；
  - `framework-openai-claude-adk.md`：13 次 web_search + GitHub raw/PyPI JSON 实证；
  - `framework-pydantic-bedrock-coze.md`：16 次 web_search；
  - `framework-langgraph.md`：15+ 次 web_search，36 项来源清单；
  - `enterprise-pain-points.md`：12+ 次 web_search + 原文页面抓取核验；
  - `primary-langchain-report-2025.md`：LangChain 2025 报告全文（转译，原文 langchain.com/state-of-agent-engineering）；
  - `agent-framework-landscape-2026-08.md`：SMF Clearinghouse 2026-08 框架对比原文快照。
- 合计：8 份笔记 + 本报告，**web_search 调用 85+ 次**，引用来源去重后 **174 个 URL（正文）**，笔记内另含约 200 个来源条目。

### 9.2 主要来源分组

| 类别 | 代表来源 |
|---|---|
| 行业报告 | langchain.com/state-of-agent-engineering（2025-12）；gartner.com 新闻稿（2025-06/2026-04）；menlovc.com 2025；zenml.io LLMOps（2025） |
| 官方文档 | docs.langchain.com；docs.crewai.com；learn.microsoft.com/agent-framework；openai.github.io/openai-agents-python；code.claude.com；github.com/google/adk-docs；pydantic.dev/docs/ai；docs.aws.amazon.com/bedrock-agentcore；docs.coze.cn |
| 官方博客/公告 | claude.com/blog（Agent SDK）；community.openai.com（2025-03-11）；developers.googleblog.com（ADK/ADK 2.0）；aws.amazon.com/whats-new（AgentCore GA）；crewai.com/blog（1.0/AMP）；vercel.com/blog（deepsec） |
| 一手实证 | PyPI JSON API（openai-agents/claude-agent-sdk/google-adk/pydantic-ai 版本）；GitHub LICENSE/pyproject raw（许可证） |
| 安全/标准 | OWASP LLM Top 10（2025）；OWASP Top Ten AI Agent Threats（2025-12）；MITRE ATLAS；ICSE 2025 RAIE；CrowdStrike（2026-06 报道） |
| 二手综述 | smfclearinghouse.com（2026-08）；agentmarketcap.ai；costbench.com；aiwiki.ai；InfoWorld/VentureBeat/TechTarget |

### 9.3 事实核查清单（重点条目复核状态）

| 条目 | 状态 | 说明 |
|---|---|---|
| LangChain 2025 报告 57.3% 生产/32% 质量/89% 可观测/52.4% 离线评估 | ✅ 已核 | 原文全文转译保存于 `docs/_research_notes/primary-langchain-report-2025.md` |
| Gartner 40% 项目取消（2027 底） | ✅ 已核 | 官方新闻稿 2025-06-25 |
| OpenAI Agents SDK 2025-03-11 / MIT / 0.22.0 | ✅ 已核 | 官方社区公告 + PyPI JSON |
| Claude Agent SDK 2025-09-29 / MIT / 0.2.145 | ✅ 已核 | PYMNTS + PyPI JSON（注意：**非 1.x**，修正了第三方口径） |
| Google ADK 2025-04 / Apache-2.0 / 2.8.0 | ✅ 已核 | Google 博客 + PyPI JSON（注意：**与 Gemini 3 不同期**） |
| Bedrock AgentCore GA 2025-10（含东京） | ✅ 已核 | AWS what's-new + ascii.jp |
| Coze Studio/Loop 开源（Apache-2.0） | ✅ 已核 | ithome/chinaz 2025-07-28（修正"2025-04 前后"的猜测） |
| LangGraph/LangChain 1.0 = 2025-10-22 | ✅ 已核 | LangChain 官方博客 + forum 时间戳 |
| CrewAI 1.0 GA = 2025-10 | ✅ 已核 | crewai.com 官方博客 |
| LangGraph Platform GA = 2025-05-14，2025-10 更名 LangSmith Deployment | ✅ 已核 | LangChain 官方博客（Platform GA 页内注明更名） |
| LangChain 报告命名勘误（2025 版 =《State of Agent Engineering》，2025-12-16） | ✅ 已核 | 官方页 + 方法论文档；"86%/14% 生产差距"属 AI2 Incubator 另一报告，已区分 |
| Coze Studio/Loop 开源 = 2025-07（非"2025-04 前后"） | ✅ 已核 | ithome/chinaz/InfoQ 2025-07-26/28 |
| Claude Agent SDK 版本线 = 0.2.x（非"1.x"） | ✅ 已核 | PyPI JSON（0.2.145 @2026-08-27） |
| ADK 与 Gemini 3 不同期（ADK 2025-04，Gemini 3 2025-11） | ✅ 已核 | Google 博客 + AI Business |
| Langfuse 被 ClickHouse 收购（2026-01） | ✅ 已核 | ClickHouse 官方博客 |
| "四强"框架论（2026-08） | ⚠️ 二手 | SMF Clearinghouse 单方观点，与 PyPI 版本证据存在出入（如"SDK v1.x"），已交叉修正 |
| 各框架精确 star 数 / AgentCore 单价 / Agent Framework GA 日期 / 组织级预算功能 | ⚠️ 未证实 | 报告中已标注，使用前需 GitHub API/官方复核 |

### 9.4 免责声明

本报告为公开信息调研，非厂商背书；标注【推断】【未证实】的条目不构成事实主张。市场数据随时间变化，重大决策前请以官方来源复核。

---

*报告结束。中间调研笔记见 `docs/_research_notes/`（8 份，UTF-8 中文），作为证据链保留。*
