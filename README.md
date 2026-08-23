# agent-hive 蜂群 —— 首脑统筹的多智能体编排框架

由一个「首脑」统一统筹多个角色专家：**首脑只做三件事——定架构、分包派发、验收集成**；编码/测试/评审/调研四个专家各司其职、并行实现；架构方案与批次表两个关口人工审批；验收采用**评估-优化回路**（不通过自动带反馈返工，满 3 轮熔断，缺陷可跨包归因）。

本仓库同时包含两个宿主，共用同一套契约（`skill/contracts.md`）：

| 宿主 | 位置 | 用法 |
|---|---|---|
| **DSH 技能**（会话内主模型当首脑） | `skill/` | 复制到 `~/.dsh/skills/agent-hive/`，对话中提到「首脑/统筹/智能体军团」即触发 |
| **LangGraph 程序**（独立运行） | `agent_hive/` | `uv run python -m agent_hive run --goal "..."` |

## 特性

- **首脑协议**：盘点兵力 → 定架构 → 审批① → 分包（契约化工作包）→ 审批② → 并行派发 → 验收评审 → 集成
- **契约先行**：每个工作包带接口契约、`expected_output`、`depends_on`、可逐项打勾的验收标准
- **评估-优化回路**：验收不通过自动回派（带具体差距），逐包计数、满 3 轮熔断；支持把缺陷**归因到责任包**（`reassign_to`）
- **守卫规则**：输入守卫（危险目标拦截）、输出守卫（交付物存在性程序化校验，先于 LLM 评审）、熔断守卫
- **项目看板**：工件状态机全程可审计（待派发→进行中→待验收→通过/返工→熔断）
- **权限分层 T0/T1/T2**：全开放（定位提示+窄探测）/ 只开放工作区（先出工程提示词包再回填分工）/ 零披露（顾问模式）
- **派发资格评审**：调用外部智能体必须「能力胜出 + 省时高效」双关通过（证据不足一律不派）
- **成本可观测**：每次运行落盘 `cost.json`（模型调用次数与 token 用量）
- **断点续跑**：`--run-id` + `--thread-id` 恢复中断的运行

## 快速开始

```bash
# 1. 安装 uv（https://docs.astral.sh/uv/）后同步依赖
uv sync

# 2. 配置 API 密钥（见下一节「配置 API 密钥」）
cp .env.example .env   # 然后编辑 .env 填入你的密钥

# 3. 运行
uv run python -m agent_hive run --goal "做一个命令行待办事项管理器（Python）"
# 无头自动审批（测试用）：--yes
# 顾问模式（不派发，只出架构+工程提示词包）：--tier T2
# 断点续跑：--run-id 20260824_xxxxxx_abcd --thread-id hive-20260824_xxxxxx_abcd
```

## 配置 API 密钥（密钥只保留本地，绝不上传仓库）

本项目沿用主流开源 AI 项目的做法（[openai-quickstart-python](https://github.com/LinggarM/openai-quickstart-python) 的 `.env.example` 拷贝模式、[gpt-engineer](https://github.com/AntonOsika/gpt-engineer/blob/main/.env.template) 的 `.env.template` 模式）：

1. **复制模板**：`cp .env.example .env`（Windows: `copy .env.example .env`）
2. **改哪一个文件**：只改 `.env`，不要改 `.env.example`。`.env` 已被 `.gitignore` 排除，任何情况下不会进入 git 历史。
3. **每个变量的作用与获取方式**：

| 变量 | 作用 | 获取方式 |
|---|---|---|
| `DEEPSEEK_API_KEY` | 首脑与专家的模型（deepseek-chat） | https://platform.deepseek.com → API Keys |
| `TAVILY_API_KEY` | 调研专家的联网搜索工具 | https://app.tavily.com → API Keys（有免费额度） |
| `DASHSCOPE_API_KEY` / `DASHSCOPE_BASE_URL` | （可选）阿里云百炼模型，按需替换模型供应商 | https://bailian.console.aliyun.com → API-KEY |
| `HIVE_ALLOW_SHELL` | 是否允许编码/测试专家真实执行命令（默认 `0` 禁用） | 本地安全开关，见 SECURITY.md |

4. **代码在哪里读密钥**：`agent_hive/main.py` 入口调用 `load_dotenv()` 从项目根目录 `.env` 读取；专家子进程环境**自动剔除一切密钥变量**（`agent_hive/specialists.py` 的 `_safe_env()`），防止经命令执行泄露。
5. **验证密钥是否生效**：运行后看产物目录 `agent_hive/runs/<run_id>/cost.json` 与 `final_report.md` 正常生成即可。

## 目录结构

```
├── skill/               # DSH 技能（SKILL.md 协议 / registry.md 注册表 / contracts.md 契约）
├── agent_hive/          # LangGraph 首脑程序
│   ├── graph.py         # 编排图（含两个 interrupt 审批关口、fan-out 派发、评估-优化回路）
│   ├── chief.py         # 首脑节点（架构/分包/评审/集成、看板、用量统计）
│   ├── specialists.py   # 专家节点（角色提示词 + 受限文件/命令工具，最小权限裁剪）
│   ├── prompts.py       # 提示词与结构化 schema（contracts.md 的落地镜像）
│   ├── state.py         # 图状态
│   └── main.py          # CLI 入口（输入守卫、T0/T1/T2、断点续跑）
├── .env.example         # 环境变量模板（密钥修改处）
└── SECURITY.md          # 安全模型与信任边界
```

## 设计依据（借鉴的开源项目）

- [MetaGPT](https://github.com/FoundationAgents/MetaGPT)（共享消息池/类型化工件）→ 项目看板 + 结构化回传 + 共享工作区
- [CrewAI](https://github.com/crewAIInc/crewAI)（Manager 评估返工、expected_output、任务依赖）→ 评估-优化回路 + 工作包结构化字段
- [LangGraph](https://github.com/langchain-ai/langgraph)（supervisor、Send 并行、interrupt 人机协同）→ 图编排与审批关口
- [OpenAI Agents SDK](https://github.com/openai/openai-agents-python)（guardrails、max_turns）→ 守卫规则与熔断
- [Anthropic 多智能体模式](https://claude.com/blog/common-workflow-patterns-for-ai-agents-and-when-to-use-them)（orchestrator-workers、evaluator-optimizer）→ 首脑-专家 + 评审回路
- Claude Code 子代理（交接文档、文件所有权、上下文经济）→ 受限工具与交接文档

## 安全

本项目让 LLM 持有文件与命令工具，**默认禁用命令执行**，完整安全模型见 [SECURITY.md](SECURITY.md)。

## License

[MIT](LICENSE)
