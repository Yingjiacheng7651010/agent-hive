# 企业级 Agent 生产落地选型痛点与权威行业报告数据

> **用途**：2026 年竞争评估报告（基于 LangGraph 自研多智能体编排框架的公司）之市场/痛点研究底稿
> **数据截止**：2026 年 8 月
> **方法**：12+ 次 web_search + 对 Menlo Ventures、LangChain、Gartner（转引）、IDC、信通院等原文页面的直接抓取核验
> **标注规则**：【事实】= 原文/官网/权威媒体可核实的数字与表述；【推断】= 基于上述数据的合理推论；【未证实】= 未能从一手来源核实，供后续核验
> **重要勘误**：任务书中"LangChain《State of AI Agents 2025》（2025-10 发布）"有误——2024 年 10 月发布的是《State of AI Agents》（2024 版）；2025 版实际标题为 **《State of Agent Engineering 2025》（智能体工程现状）**，2025 年 12 月 16 日发布，调查期 2025-11-18 至 12-02，1,340 份有效回复。【事实】[来源: https://blog.langchain.com/ 及 https://www.langchain.com/state-of-agent-engineering（中文全译：https://raw.githubusercontent.com/ForceInjection/AI-fundamentals/refs/heads/main/08_agentic_system/reports/langchain-state-of-agent-engineering.md，2025）]

---

## 一、权威报告数据采集

### 1.1 LangChain《State of Agent Engineering 2025》（即任务书所指《State of AI Agents 2025》）

调查 1,340 名工程师/产品经理/高管；行业构成：科技 63%、金融 10%、医疗 6%、教育 4%；公司规模 <100 人占 49%、10,000+ 人占 9%。【事实】[来源: 同上，2025]

**生产 vs 原型（差距）**
- 57.3% 受访者已有智能体在生产环境运行（较去年的 51% 上升 6.3pp）；另有 30.4% 在开发中且有明确部署计划。【事实】[来源: https://www.langchain.com/state-of-agent-engineering，2025]
- 10,000+ 人企业 67% 已投产（24% 开发中）；<100 人组织仅 50% 投产（36% 开发中）——大企业从试点到生产的迁移更快。【事实】[来源: 同上，2025]
- 横向参照：AI2 Incubator《Insights 15: The State of AI Agents in 2025》显示约 78% 企业技术负责人至少运行 1 个 agent 试点，仅 14% 成功规模化到全组织运营——即约 86% 的企业试点未走到全组织生产。【事实（二手转述）】[来源: https://agentmarketcap.ai/blog/2026/04/08/ai2-incubator-state-of-ai-agents-2025-deployment-reality，2026]
- G2 2025 年 8 月调查：57% 公司已投产 agent，22% 在 pilot，21% 在 pre-pilot。【事实】[来源: https://learn.g2.com/enterprise-ai-agents-report，2025]

**评估（Eval）采用率（与可观测性的显著落差）**
- 离线评估（测试集）52.4%、在线评估（生产监控）37.3%、未做评估 29.5%；投产组织中在线评估升至 44.8%、未评估降至 22.8%；同时做离线+在线的约 25%。【事实】[来源: 同上，2025]
- 评估方法：人工审查 59.8%、LLM-as-Judge 53.3%；ROUGE/BLEU 等传统指标采用有限。【事实】[来源: 同上，2025]

**可观测性**
- 89% 组织已为智能体建立某种可观测性，62% 具备细粒度 tracing；投产组织中 94% 有可观测性、71.5% 有完整 tracing。"可观测性已是标配（table stakes），明显领先于评估（52%）"。【事实】[来源: 同上，2025]

**成本/延迟**
- 质量（32%，约 1/3 受访者）是第一大生产障碍，延迟（20%）第二；**成本被提及频率低于往年**（模型降价与效率提升使关注点从"花多少"转向"质量与速度"）。【事实】[来源: 同上，2025]

**RAG 与多智能体**
- 报告未给出 RAG 或"多智能体架构"的硬性占比数字（正文仅说明微调未被广泛采用、团队"依赖基础模型+提示工程+RAG"）→ **RAG/多智能体采用率【未证实】**（可在 2024 版报告中进一步核实）。【推断/未证实】[来源: 同上，2025]
- 日常使用最多的智能体：编程智能体（Claude Code、Cursor、GitHub Copilot、Amazon Q、Windsurf、Antigravity）、研究/深度研究智能体（ChatGPT/Claude/Gemini/Perplexity）、以及基于 LangChain/LangGraph 构建的自定义智能体。【事实（定性）】[来源: 同上，2025]

**LLM 提供商份额**
- 超过 2/3 组织使用 OpenAI GPT 模型；**超过 3/4 组织使用多种模型**；约 1/3 组织部署自有/开源模型（动机含成本优化、数据驻留/主权、行业监管）；43% 做过微调（57% 未微调）。【事实】[来源: 同上，2025]

**AI SDK 采用**
- 报告未公布 OpenAI Agents SDK / LangGraph / CrewAI 等的框架份额硬数据 → 【未证实】；定性上"基于 LangChain 和 LangGraph 构建的自定义智能体也很受欢迎"。【事实（定性）/未证实（占比）】[来源: 同上，2025]

### 1.2 Menlo Ventures 企业生成式 AI 报告

**2024 版《2024: The State of Generative AI in the Enterprise》**（2024-11-20，作者 Tim Tully / Joff Redfern / Derek Xiao）
- 企业 GenAI 支出 2024 年达 **$13.8B，是 2023 年 $2.3B 的 6 倍以上**；72% 决策者预期近期扩大 GenAI 采用。【事实】[来源: https://menlovc.com/2024-the-state-of-generative-ai-in-the-enterprise/，2024]

**2025 版《2025: The State of Generative AI in the Enterprise》**（第三期年度报告，约 500 名美国企业决策者调查 + 自下而上市场模型）
- 企业 GenAI 支出 **2025 年 $37B，2024 年 $11.5B（修订值），同比 3.2x**；自 2023 年 $1.7B 起累计增长，占全球 SaaS 市场 6%+，为史上增速最快的软件品类。【事实】[来源: https://menlovc.com/perspective/2025-the-state-of-generative-ai-in-the-enterprise/，2025]
- 至少 10 个产品 ARR 超 $10 亿、50 个产品 ARR 超 $1 亿；应用层占 $19B，基础设施层 $18B（其中模型 API $12.5B、训练基建 $4.0B）。【事实】[来源: 同上，2025]
- 代码 agent/AI 应用构建从近零增长到 2025 年约 $4B（2024 年 $550M）；Agent 平台（Salesforce Agentforce、Writer、Glean 等）占应用层约 10%（$750M）。【事实】[来源: 同上，2025]
- 2025 报告展望：自主决策增加后，"可解释决策与 agent 结果审计日志"将成为政府/企业刚需。【事实】[来源: 同上，2025]

### 1.3 Sequoia《AI's $600B Question》（2024-06）及 2025 更新

- **《AI's $600B Question》**（2024-06，Sequoia 合伙人 David Cahn）：为支撑 AI 基础设施资本开支，AI 应用需要产生约 **$600B 年收入**；同期 OpenAI 年化收入约 $3.4B（2023 年 $1.6B），差距巨大。系列前作为 2023-09《AI's $200B Question》。【事实】[来源: https://sequoiacap.com/article/ais-600b-question，2024；转述核实 https://yespress.io/david-cahn，2026]
- **2025 更新**：Cahn 2025 年估算——超大规模厂商 **2025 年 AI 资本开支约 $750B**，需在其设备生命周期内产生约 **$1.5T 终端客户收入**才能回本；自 ChatGPT 发布以来的累计回本需求约 **$3T**。【事实（媒体转述）】[来源: https://www.edgen.tech/zh/news/post/ai-boom-reshapes-us-economy-as-750b-buildout-raises-stability-risks，2026 引述 2025 年报道]
- 任务书所问"《AI's $750B question》（2025-07）"标题本身：未能从 Sequoia 官网确认此确切标题 → **标题【未证实】**；但 $750B capex / $1.5T 收入需求 / $3T 累计回本等数字经媒体确认来自 Cahn 2025 年测算。【未证实（标题）/事实（数字）】

### 1.4 Gartner agentic AI 预测

- **到 2027 年底，超过 40% 的 agentic AI 项目将被取消**（Gartner 官方新闻稿，**实际发布日期 2025-06-25**，任务书所写"2025-11"有误）。【事实】[来源: https://www.gartner.com/en/newsroom/press-releases/2025-06-25-gartner-predicts-over-40-percent-of-agentic-ai-projects-will-be-canceled-by-end-of-2027，2025；Reuters 报道 https://www.reuters.com/business/over-40-agentic-ai-projects-will-be-scrapped-by-2027-gartner-says-2025-06-25/；中文版 https://www.gartner.com/cn/newsroom/press-releases/2025-ai-project-failure]
- **到 2028 年，33% 的企业软件应用将包含 agentic AI**（2024 年该比例约 1%）；agentic AI 到 2028 年将承担企业约 **15% 的日常工作决策**。【事实（媒体转述 Gartner 研究；Gartner 官网反爬无法直接抓取原文，建议采购前二次核实）】[来源: https://cio.economictimes.indiatimes.com/news/artificial-intelligence/from-data-to-decisions-to-dispositions-how-agentic-ai-is-rewiring-the-modern-c-suite/129943532，2026；另见 Gartner 文章页 https://www.gartner.com/en/articles/ai-agents-pc1]

### 1.5 Stanford HAI《AI Index 2025》（2025-04 发布）

- **SWE-bench（GitHub 真实编码问题）：2023 年 4.4% → 2024 年 71.7%**；MMMU +18.8pp、GPQA +48.9pp。【事实】[来源: AI Index 2025 新闻稿内容转述 https://www.longtermwiki.com/resources/1a26f870e37dcc68，2025；另一转述 https://theoutpost.ai/news-story/ai-in-2025-rapid-advancements-global-competition-and-societal-impact-14077/]
- 企业 AI 采用：**2024 年 78% 组织使用 AI（2023 年 55%）**。【事实】[来源: https://www.helpnetsecurity.com/2025/06/20/ai-index-2025/，2025，引 AI Index 2025]
- 推理成本/延迟警告：OpenAI o1 比 GPT-4o **贵近 6 倍、慢约 30 倍**。【事实】[来源: https://www.longtermwiki.com/resources/1a26f870e37dcc68，2025]
- AI Index 2025 设有"AI agents"章节（自主系统基准如 SWE-bench、Terminal-bench 等），但未提供企业级 agent 采用率百分比 → 该项【未证实】。【未证实】[来源: 同上，2025]

### 1.6 其他权威来源（McKinsey / Deloitte / Forrester）

- **McKinsey《The State of AI in 2025: Agents, innovation, and transformation》**（2025-11，n=1,491）：23% 企业正在规模化 agentic AI，39% 在试验；仅 6% 为"AI 高绩效者"（AI 贡献 >5% EBIT）。【事实】[来源: https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai，2025；解读 https://agentmodeai.com/the-mckinsey-23-percent-agentic-ai-scaling-gap/，2026]
- Forbes 引 McKinsey（2026-03）：约 **10% 的企业职能正在使用 AI agents**。【事实（转述）】[来源: https://www.forbes.com/sites/josipamajic/2026/03/22/10-of-enterprise-functions-use-ai-agents-mckinsey-finds/，2026]
- **Deloitte**《State of Generative AI in the Enterprise》（2025 版）：印度 80%+ 企业正在探索 agentic AI（区域样本）；Deloitte《The agentic reality check》（Tech Trends 2026）：企业正快速转向 agentic AI 但普遍"撞墙"（agent 规模化准备不足）。【事实（转述）】[来源: https://www.deloitte.com/in/en/about/press-room/india-rides-the-agentic-ai-wave.html，2025；https://www.deloitte.com/us/en/insights/topics/technology-management/tech-trends/2026/agentic-ai-strategy.html，2026]
- **Forrester**：2025 年十大新兴技术中将生成式/agentic AI 列为核心，指出 AI 创新正从"实验"转向"业务必选项"（无具体百分比数字）。【事实（定性）】[来源: https://investor.forrester.com/node/17371/pdf，2025]

---

## 二、企业选型痛点清单（每项 1-3 条带来源论据）

1. **可观测性（trace 覆盖率）**
   - 89% 已建可观测性、但仅 62% 有细粒度 tracing；投产组织 94%/71.5%。可观测性已被视为"标配"，差距在质量维度。【事实】[来源: LangChain 2025 报告，同上]
2. **评估（Eval）体系缺失**
   - 离线评估仅 52.4%、在线评估仅 37.3%、**29.5% 完全不做评估**；评估采用率（52%）明显落后于可观测性（89%）。【事实】[来源: LangChain 2025 报告，同上]
3. **Guardrails / 安全护栏**
   - 2,000+ 人企业中**安全是第二大生产障碍（24.9%）**，超过延迟；行业侧 2025 年报告解读亦称"安全已成为首要阻碍之一"。【事实】[来源: https://www.langchain.com/state-of-agent-engineering，2025；解读 https://amlalabs.com/blog/langchain-state-of-agents-2025/，2026]
4. **成本失控（token 成本、预算）**
   - 2025 报告显示成本担忧**同比下降**（模型降价），但成本管理仍是刚需：LLM 网关/控制面（如 Portkey）声称托管 $500K+/日支出、$180M+ 年化支出管理、1,600+ 模型——侧面说明预算失控是普遍痛点。【事实】[来源: LangChain 2025 报告；https://portkey.ai/blog/series-a-funding/，2026]
5. **幻觉与可靠性**
   - **质量（32%）是第一生产障碍**；10,000+ 人企业书面反馈将"幻觉与输出一致性"列为首要质量挑战，多步推理使错误逐级累积。【事实】[来源: LangChain 2025 报告，同上]
6. **数据合规与隐私（数据出境、region）**
   - 约 **1/3 组织自托管/部署开源模型**，动机包括大批量成本优化、**数据驻留与主权要求**、敏感行业监管限制——自研可本地/私有化部署的框架在此是选型加分项。【事实】[来源: LangChain 2025 报告，同上]
7. **多租户隔离**
   - 无权威公开数字 → 【未证实】；【推断】SaaS 交付模式下隔离/配额/资源抢占是必选项（参考：Menlo 2025 中企业采购强调"基于业务成果计费"与治理，IDC 中国 66% 企业偏好成果计费）。【推断】[来源: https://menlovc.com/perspective/2025-the-state-of-generative-ai-in-the-enterprise/，2025；IDC 中国报告见第四节]
8. **失败重试 / 熔断 / 断点恢复**
   - LangChain 2025 报告解释大企业（10k+，67% 投产）迁移更快"可能源于平台团队、安全与**可靠性基础设施**的更大投入"；无专门统计 → 部分【推断】。【事实（背景）/推断】[来源: LangChain 2025 报告，同上]
9. **延迟**
   - **延迟是第二大生产障碍（20%）**，面向客户的客服/代码生成场景尤甚；OpenAI o1 级推理模型比 GPT-4o 慢约 30 倍，进一步放大延迟压力。【事实】[来源: LangChain 2025 报告；AI Index 2025，同上]
10. **与企业身份认证/审计集成（SSO、审计日志）**
    - Menlo 2025 明确预期"政府将要求 agent 结果的可解释决策与审计日志"；Langfuse、Dify 企业版等均把权限管理/合规方案作为企业版卖点。【事实】[来源: https://menlovc.com/perspective/2025-the-state-of-generative-ai-in-the-enterprise/，2025；https://langfuse.com/press/press，2026]
11. **提示词与模型版本管理**
    - 报告显示 43% 团队微调、57% 不微调（依赖提示工程+RAG），提示词成为主战场；生态把 Prompt 版本管理列为标配（Langfuse 平台四大能力之一；字节扣子开源 Coze Loop 主打"Prompt 编写-调试-版本管理+评测+全链路可观测"闭环）。【事实】[来源: https://langfuse.com/press/press，2026；https://www.infoq.cn/article/a4ikxoqf5tfq24izedcl，2025]

---

## 三、LLMOps / 可观测性工具生态简表

| 工具 | 定位（一句话） | 2025-2026 动态 |
|---|---|---|
| **ZenML LLMOps Database**（llmops-database.zenml.io） | 全球最大的 LLMOps 生产案例/工具开放数据库，按应用场景+工具标签分类 | 数据集现含 **2,089 条**生产案例记录（HF 元数据核实），覆盖可观测、评估、网关、向量库、编排等类别【事实】[来源: https://huggingface.co/datasets/zenml/llmops-database，2026] |
| **Langfuse** | 开源 AI 工程平台：生产 tracing + prompt 管理 + LLM-as-Judge 评估 | GitHub 33.6k stars、90B+ 观测/月、100k+ 采用者；2023-11 $4M 种子轮（Lightspeed/General Catalyst/YC）；**2026-01 被 ClickHouse 收购**（并入其 $400M D 轮），v4 宣称快 165x【事实】[来源: https://langfuse.com/press/press，2026；https://clickhouse.com/blog/clickhouse-acquires-langfuse-open-source-llm-observability，2026] |
| **Arize Phoenix** | 开源 LLM/agent 可观测与评估（tracing、drift、evals），Arize 商业版 AX 承接企业化 | GitHub 破 **10,000 stars**（2025），主打社区驱动【事实】[来源: https://arize.com/blog/phoenix-10k/，2025] |
| **AgentOps** | agent 专用监控/会话回放/成本与信用评分平台 | 定位 agent 会话级可观测；融资情况【未证实】[来源: https://agentops.ai/（官方）] |
| **W&B Weave** | W&B 开源 LLMOps 工具包：tracing、datasets、LLM evals，深度集成 W&B 生态 | 定位"Eval-centric"时代的可观测性（W&B 侧重点从实验转向生产评估）【事实（定位）】[来源: https://wandb.ai/site/weave] |
| **Helicone** | 开源 LLM 日志/调试/成本分析（代理式插桩） | 有早期种子轮记录（约 $125K，数字待核）、PitchBook 收录；融资规模【未证实】[来源: https://www.trysignalbase.com/news/funding/helicone-secures-125k-seed-round-to-revolutionize-open-source-ai-logging-and-debugging-applications；https://pitchbook.com/profiles/company/520700-68] |
| **LangSmith** | LangChain 官方商业平台：tracing、评估、prompt 管理、LLM 网关 | LangChain 2025 报告中可观测性 89% 普及的生态基础；与 LangGraph 深度绑定【事实（定位）】[来源: https://www.langchain.com/state-of-agent-engineering，2025] |
| **Portkey**（LLM 网关/成本控制类） | "生产 AI 统一控制面"：AI 网关+治理+可观测+成本管理，模型路由与预算控制 | **2026-02 完成 $15M Series A**；自述日处理 500B+ tokens、1,600+ 模型、24,000+ 组织【事实（自述）】[来源: https://portkey.ai/blog/series-a-funding/，2026] |
| **Kong AI Gateway**（同类别） | 基于 Kong API 网关扩展的 AI 网关：模型路由、治理、自动化 RAG、MCP 支持 | AI Gateway 3.13（2025）主打 agentic 工作负载上生产【事实】[来源: https://konghq.com/blog/product-releases/ai-gateway-3-13，2025；https://siliconangle.com/2025/04/02/kong-api-expertise-ai-gateway-governance-cubeconversations/] |
| **LiteLLM proxy**（同类别） | 开源"通用 LLM API 翻译层/代理"：统一 100+ 家供应商接口，成本/限流/fallback | 社区事实标准之一；仓库规模未核实 → 数字【未证实】[来源: https://futureagi.com/blog/what-is-litellm-2026/，2026] |

---

## 四、中国企业市场补充

**权威机构报告/数据**
- **信通院**：2025-06-22 在华为开发者大会 2025 上，中国信通院人工智能研究所与华为联合发布《智能体技术和应用研究报告（2025年）》，覆盖智能体发展概述、关键技术、产业应用、问题挑战、发展建议五大方面。【事实】[来源: http://www.cww.net.cn/article?id=601665，2025]
- **IDC**《AI Agent 企业级应用现状与推荐，2025》（Doc#CHC53057525，2025-06，发布日 2025-07-08）：
  - 中国受访企业中 **34% 处于测试验证阶段、30% 进入"较大投入+采购培训"阶段**（整体仍落后于全球）；
  - 预测 **2028 年中国企业级 Agent 应用市场保守估计达 270+ 亿美元**；
  - **66% 中国企业偏好"基于业务成果计费"（全球 52.7%）**。【事实】[来源: https://my.idc.com/getdoc.jsp?containerId=prCHC53669525，2025]
- **IDC**：2025 年中国智能体开发平台**私有化市场收入达 17.5 亿元**（已具规模）。【事实（标题级）】[来源: https://hk.investing.com/news/stock-market-news/article-1506910，2026]
- **艾瑞咨询**《中国金融智能体发展研究与厂商评估报告（2025）》（经济观察报引述）：2025 年中国金融智能体平台及解决方案**签约总额 9.5 亿元**，预计 2030 年达 193 亿元（CAGR 82.6%）；但 **96% 的应用实践仍处早期探索阶段**，预计 2026 年底 20%-25% 金融机构将因预期落空而动摇投资信心。【事实（转述）】[来源: http://www.eeo.com.cn/ai/2026/0221/799147.shtml，2026]

**国内 Agent 平台竞争格局（公开数据）**
- **扣子（字节，Coze）**：2025-07-26 开源 Coze Studio + Coze Loop（Apache 2.0，无商业限制），开源两天 GitHub 超 6K stars；截至 2025-06 月访问用户约 **458 万**（非凡产研数据）；用户画像专业开发者:准专业:零基础 ≈ 1:1:1。Coze Loop 主打评测+线上观测+优化迭代闭环。【事实】[来源: https://www.infoq.cn/article/a4ikxoqf5tfq24izedcl，2025]
- **Dify**：GitHub stars 2025 年突破 **90K**（全球开源 Top 100）；截至 2025-04 服务全球 150 国用户、支撑 **400 万+ 次应用部署**；2026-03 完成 **$30M Pre-A**（红杉中国领投，高瓴创投等跟投）。【事实（百科等二手来源，建议对账官方公告）】[来源: https://baike.baidu.com/item/Dify/66266114，2026]
- **阿里云百炼**：截至 2025-01 底，百炼平台调用通义 API 的企业与开发者超 **29 万**；2025 年推出"百炼 MCP 服务"、定位"Agent 工厂"，深度挖掘企业级 AI 应用。【事实】[来源: http://jjckb.xinhuanet.com/20250415/13aa9fd799994698bac03d407fb5b9f5/c.html，2025；https://www.asiaeb.net/zh-CN/Web/EntPage/InformationDetail?userId=2a96bf21-196c-4142-925b-8db087d321fa&id=488bc430-5870-48c7-995b-5f295a4be4f4]
- **文心智能体平台（百度 AgentBuilder）**：2024-04 更名时已有 3 万+ 智能体、5 万+ 开发者、上万家企业入驻（数据较旧）；2025-07-03 与小米应用商店合作，实现智能体跨端分发（应用商店增设 AI 智能体专区）。【事实（数据较旧）】[来源: https://baike.baidu.com/item/文心智能体平台/64291598，2026]
- 【推断】竞争格局小结：字节扣子=低代码/C 端+开源生态（开源后与 Dify 正面竞争），百度文心=流量分发+免费模型，阿里百炼=云生态+企业 MCP/Agent 工厂，Dify=开源+企业版出海与私有化（2025-05 起与明略科技合作企业版）。自研编排框架公司的差异化空间：私有化/信创、企业身份与审计集成、可观测+评估闭环（对标 Coze Loop/LangSmith 缺口）。【推断】

---

## 五、最有说服力的硬数字速查（引用时建议直接使用）

1. 57.3% 组织已投产 agent（较去年 51% 上升），10k+ 大企业 67% —— LangChain，2025
2. 质量（32%）> 延迟（20%）> 成本（同比下降）为生产三大障碍；2k+ 企业安全 24.9% 排第二 —— LangChain，2025
3. 可观测性 89% vs 评估 52%（离线 52.4%/在线 37.3%/29.5% 无评估）—— LangChain，2025
4. >2/3 用 OpenAI GPT、>3/4 多模型并用、1/3 自托管开源模型（数据驻留/合规动机）—— LangChain，2025
5. 企业 GenAI 支出 2025 年 $37B（2024 $11.5B，3.2x；2023 $1.7B），占全球 SaaS 6%+ —— Menlo，2025
6. Gartner：>40% agentic AI 项目将于 2027 年底前被取消（2025-06-25）；2028 年 33% 企业软件含 agentic AI、承担 15% 日常工作决策 —— Gartner，2025
7. Sequoia/Cahn：2025 年 AI 资本开支约 $750B，需产生约 $1.5T 终端收入回本（$600B Question 2024 为前作）—— 2024/2025
8. McKinsey 2025：23% 规模化 agentic AI、39% 试验、6% 高绩效；约 10% 企业职能在用 agent —— 2025/2026
9. SWE-bench 4.4%（2023）→ 71.7%（2024）；o1 比 GPT-4o 贵 ~6x、慢 ~30x —— Stanford AI Index 2025
10. 中国：IDC 预测 2028 年中国企业级 Agent 市场 270+ 亿美元；私有化平台 2025 收入 17.5 亿元；金融智能体 2025 签约 9.5 亿元（96% 项目仍早期）—— IDC/艾瑞，2025-2026
11. 工具生态：Langfuse 被 ClickHouse 收购（2026-01，GitHub 33.6k stars）；Portkey $15M Series A（2026-02）；Arize Phoenix 10k stars（2025）；Dify >90K stars、400 万+ 部署（2025）；扣子 2025-07 开源 Coze Studio/Loop

---

## 附：主要来源 URL 汇总

- LangChain 2025 报告（官网）：https://www.langchain.com/state-of-agent-engineering ；中文全译（2025-12-16）：https://raw.githubusercontent.com/ForceInjection/AI-fundamentals/refs/heads/main/08_agentic_system/reports/langchain-state-of-agent-engineering.md
- LangChain 2024 报告：https://www.langchain.com/stateofaiagents
- Menlo 2024：https://menlovc.com/2024-the-state-of-generative-ai-in-the-enterprise/ ；Menlo 2025：https://menlovc.com/perspective/2025-the-state-of-generative-ai-in-the-enterprise/
- Sequoia：https://sequoiacap.com/article/ais-600b-question
- Gartner 新闻稿：https://www.gartner.com/en/newsroom/press-releases/2025-06-25-gartner-predicts-over-40-percent-of-agentic-ai-projects-will-be-canceled-by-end-of-2027 ；Reuters：https://www.reuters.com/business/over-40-agentic-ai-projects-will-be-scrapped-by-2027-gartner-says-2025-06-25/
- AI Index 2025：https://aiindex.stanford.edu/report/ （转述见 https://www.longtermwiki.com/resources/1a26f870e37dcc68 ）
- McKinsey：https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai
- IDC 中国：https://my.idc.com/getdoc.jsp?containerId=prCHC53669525 ；信通院：http://www.cww.net.cn/article?id=601665 ；艾瑞（经济观察报）：http://www.eeo.com.cn/ai/2026/0221/799147.shtml
- ZenML LLMOps 数据库：https://llmops-database.zenml.io ；HF 元数据：https://huggingface.co/api/datasets/zenml/llmops-database
- Langfuse：https://langfuse.com/press/press ；ClickHouse 收购：https://clickhouse.com/blog/clickhouse-acquires-langfuse-open-source-llm-observability
- Portkey：https://portkey.ai/blog/series-a-funding/ ；Kong：https://konghq.com/blog/product-releases/ai-gateway-3-13 ；Arize：https://arize.com/blog/phoenix-10k/
- 扣子开源（InfoQ）：https://www.infoq.cn/article/a4ikxoqf5tfq24izedcl ；Dify：https://baike.baidu.com/item/Dify/66266114 ；百炼（经济参考）：http://jjckb.xinhuanet.com/20250415/13aa9fd799994698bac03d407fb5b9f5/c.html

> 说明：Gartner 官网与 Reuters 原文页面存在反爬（403/401），相关数字经权威二手来源交叉核验后标注；Sequoia 2025 更新篇的准确标题未能核实，仅确认其数字经媒体引述。引用前如需绝对精确，建议对上述【未证实】项做一次人工复核。
