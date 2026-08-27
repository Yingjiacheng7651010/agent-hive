# agent-hive 蜂群 —— 首脑统筹的多智能体编排框架

由一个「首脑」统一统筹多个角色专家：**首脑只做三件事——定架构、分包派发、验收集成**；编码/测试/评审/调研四个专家各司其职、并行实现；架构方案与批次表两个关口人工审批；验收采用**评估-优化回路**（不通过自动带反馈返工，最多返工 3 次后熔断，当前波次内可归因责任包）。

本仓库同时包含两个宿主，共用同一套契约（`skill/contracts.md`）：

| 宿主 | 位置 | 用法 |
|---|---|---|
| **DSH 技能**（会话内主模型当首脑） | `skill/` | 复制到 `~/.dsh/skills/agent-hive/`，对话中提到「首脑/统筹/智能体军团」即触发 |
| **LangGraph 程序**（独立运行） | `agent_hive/` | `uv run python -m agent_hive run --goal "..."` |

## 特性

- **首脑协议**：盘点兵力 → 定架构 → 审批① → 分包（契约化工作包）→ 审批② → 按依赖层派发 → 验收评审 → 集成
- **契约先行**：每个工作包带接口契约、`expected_output`、`depends_on`、可逐项打勾的验收标准
- **评估-优化回路**：验收不通过自动回派（带具体差距），逐包计数、最多返工 3 次后熔断；`reassign_to` 支持当前 active wave 内归因，跨波归因记录警告且前序通过包保持冻结
- **守卫规则**：输入守卫（危险目标拦截）、输出守卫（交付物存在性与路径程序化校验，先于 LLM 评审）、熔断守卫
- **依赖感知 fan-out**：同层 `Send` 分支真实并发；下游必须等待依赖通过；返工只重派目标包；熔断向下游传播为阻塞
- **整体集成守卫**：通过包扁平合并到统一 `dist/`，同路径冲突拒绝覆盖，Python 静态编译、`manifest.json`、staging 原子替换
- **项目看板**：工件状态机全程可审计（待派发→进行中→待验收→通过/返工→熔断/阻塞）
- **权限分层 T0/T1/T2**：全开放（定位提示+窄探测）/ 只开放工作区（先出工程提示词包再回填分工）/ 零披露（顾问模式）
- **派发资格评审**：调用外部智能体必须「能力胜出 + 省时高效」双关通过（证据不足一律不派）
- **成本可观测**：每次运行落盘 `cost.json`（模型调用次数与 token 用量）
- **架构安全验证**：审批①之前自动做「规则引擎（幻觉引用/循环依赖/缺失安全控制/架构反模式）+ LLM 语义验证」双通道校验；fail 自动回流重做，安全报告随审批单展示；`--skip-arch-security`/`--allow-insecure-architecture` 显式开关且写入审计
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
# 架构安全验证（默认开启，LLM 语义验证失败自动降级为纯规则引擎）：
#   显式跳过：--skip-arch-security（写入审计，报告如实标注）
#   fail 放行：--allow-insecure-architecture（写入审计）
#   自定义策略：--security-policy-file policy.json（fail_on_severity 不允许低于 high）
# 显式开启一个全局检查（默认不会执行任意动态命令；argv 始终 shell=False）
# PowerShell 推荐先创建 checks.json，避免原生参数转义吞掉 JSON 引号：
# [{"name":"verify","argv":["python","scripts/verify.py"]}]
uv run python -m agent_hive run --goal "..." --yes \
  --allow-integration-checks --integration-check-file checks.json
# Bash 也可直接传 JSON：--integration-check '{"name":"tests","argv":["python","-m","pytest","-q"]}'
```

## 重新修正结果

后续发现的四个缺口已在当前 MVP 中落地：

1. **测试体系**：根目录 `tests/` 包含 385 项回归测试，覆盖调度、真实 LangGraph fan-out、首脑验收守卫、整体集成、契约漂移、SQLite checkpoint、CLI 校验与架构安全验证。
2. **依赖与并发**：`agent_hive/scheduler.py` 提供纯函数依赖图校验、ready 层、返工依赖门和熔断阻塞传播；`graph.py` 只发送 `active_ids`，同层分支汇合后才进入 review。
3. **整体集成**：`agent_hive/integration.py` 负责统一 `dist/`、冲突拒绝、静态编译、manifest、动态检查显式开关和原子替换；`chief.integrate()` 不再复制包目录或覆盖冲突文件。
4. **契约单一事实源**：`agent_hive/contract_spec.py` 是机器可读源；`prompts.py` 为兼容重导出层；`skill/contracts.md` 由 `scripts/generate_contracts.py` 生成并可 `--check` 漂移。

验证命令：

```bash
uv run python scripts/verify.py          # pytest + compileall + contract drift 一键验收
uv run pytest -q                         # 当前：385 passed
uv run python -m compileall -q agent_hive tests
uv run python scripts/generate_contracts.py --check
```

### 当前明确的边界

- 默认集成只做无副作用静态检查；动态测试/构建必须同时使用 `--allow-integration-checks` 和 JSON `--integration-check`。
- 部分集成状态使用 `partial`，未通过、熔断或阻塞的包会列在 `unresolved_packages`，不会被报告为完整成功。
- 已验证同层 fan-out 的真实并发；生产负载下 executor/SQLite checkpointer 的压力调优仍是后续工作。

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
│   ├── graph.py         # 编排图（审批、依赖层 fan-out、评估-优化回路）
│   ├── scheduler.py     # 依赖图校验、ready 层、返工与阻塞传播（纯函数深模块）
│   ├── threat_model.py  # STRIDE + AI 特有威胁目录与验证策略（架构安全验证单一事实源）
│   ├── arch_security.py # 确定性规则引擎：幻觉引用/循环依赖/缺失控制/反模式 + SARIF 报告
│   ├── arch_security_llm.py # LLM 语义验证薄 seam（异常降级为空，不阻断规则引擎）
│   ├── scope_auth.py    # 动态验证授权清单（白名单 + 私网硬拒绝 + 审计）
│   ├── paths.py         # run/package id 与 workspace 路径围栏（单一安全策略）
│   ├── chief.py         # 首脑节点（架构/分包/评审/集成、看板、用量统计）
│   ├── integration.py   # 统一 dist、冲突检测、manifest、原子集成与可选全局检查
│   ├── specialists.py   # 专家节点（角色提示词 + 受限文件/命令工具，最小权限裁剪）
│   ├── contract_spec.py # 契约机器可读单一事实源
│   ├── prompts.py       # 契约源兼容重导出层
│   ├── state.py         # 图状态
│   └── main.py          # CLI 入口（输入守卫、T0/T1/T2、断点续跑）
├── tests/               # 回归测试（当前 385 项，含架构安全验证与 golden 语料）
├── scripts/             # 契约生成、漂移检查与全局验收
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
