# Agent 智能体方向转型路线图（LangChain / LangGraph 技术栈深化）

> 适用读者：项目维护者与后续开发者。
> 本文档回答一个问题：**项目如何往 Agent 智能体方向转化，并持续用好 LangChain / LangGraph 技术栈？**
> 结论先行：**项目已具备 Agent 化的完整骨架**——LangGraph 图编排 + 角色专家 + 人工审批关口（HITL）+ 安全/成本一等原语；后续深化方向不是「从零造 Agent」，而是**接入 LangChain 生态（观测/服务化/模型抽象）与补齐部署形态（平台/MCP/桌面/移动）**。

---

## 1. 一句话结论

项目已经是一个真实运行的 LangGraph 多智能体编排框架（首脑统筹 + 角色专家 + 契约化工作包 + 双审批关口 + 依赖感知并行派发 + 评估-优化回路），Agent 化的「内核」已完成；转型的下一步是把这套内核接入 LangChain 生态（LangSmith 观测、LangServe 服务化、OpenAI 兼容供应商抽象）并扩展部署形态（LangGraph Platform、MCP、桌面 Tauri、移动 PWA/TestFlight、PyPI）。

## 2. 现状盘点：模块 → LangChain/LangGraph 技术点

下表为**基于当前源码的真实映射**（文件名与类名与 `agent_hive/`、`hive_cost/`、`hive_security/` 一致）。

| 模块/文件 | LangChain/LangGraph 技术点 | 说明 |
|---|---|---|
| `agent_hive/graph.py` | `StateGraph` / `Send` / `interrupt` | 首脑编排图：`plan_architecture → validate_architecture → 审批① → split_packages → 审批② → dispatch → specialist（Send 按依赖层并行 fan-out）→ review → integrate`；`interrupt()` 在「架构方案」「批次表」两个审批关口暂停，等 `Command(resume=...)` 恢复，resume 值经 `ApprovalDecision` schema 校验 |
| `agent_hive/chief.py` | `init_chat_model` / `with_structured_output` / `BaseCallbackHandler` | 首脑节点（架构/分包/评审/集成）：`init_chat_model("deepseek-chat", temperature=0, timeout=300)`；结构化输出带 3 次重试；`_UsageTracker`（`BaseCallbackHandler` 子类）汇总 token 用量写 `cost.json` |
| `agent_hive/specialists.py` | `create_agent` / `@tool` / `TavilySearch` | 专家节点：`create_agent("deepseek-chat", system_prompt=..., tools=...)`；受限文件工具（`read_file`/`write_file`/`list_files`/`run_command`，`HIVE_ALLOW_SHELL=1` 才启用命令）；调研角色动态接入 `langchain_tavily.TavilySearch(max_results=5)`，失败自动降级；`_safe_env()` 白名单剔除子进程一切密钥 |
| `agent_hive/main.py` | `SqliteSaver` / `Command` / `GraphInterrupt` | `langgraph-checkpoint-sqlite` 断点续跑（`--run-id` + `--thread-id`）；捕获 `GraphInterrupt` 后 `Command(resume=...)` 恢复；入口 `load_dotenv()` 从根目录 `.env` 读密钥 |
| `agent_hive/observability.py` | OTel 兼容 JSONL | `export_run_otel_jsonl()`：把 `cost.json` / `stream_events.jsonl` 导出为 OTel 兼容 JSONL（trace_id 由 run_id 派生、确定性输出），**可被 Langfuse / LangSmith 等消费** |
| `agent_hive/tool_registry.py` | 工具生命周期管理 | `ToolSpec → ToolRegistry → ToolCallTracker`：声明式工具规范、按角色分配（`get_for_role`）、`MonitoredToolWrapper` 自动记录调用指标、`tool_to_spec()` 从 `@tool` 自动生成规范——是 MCP 接入前的「工具治理」地基 |
| `agent_hive/streaming.py` | SSE / 事件流 | `StreamManager` + `StreamContext` + `subscribe_sse()`：`agent_start/thought/tool_call/…` 事件流，为 HTTP 流式输出（LangServe/前端）预留传输层 |
| `agent_hive/async_hitl.py` | 异步 HITL | `ApprovalQueue` / `ApprovalPolicyEngine` / `ApprovalStore`（内存/SQLite/Redis）：审批入队 → Webhook 回调 → 异步返回 → 超时自动降级；`sync_ask()` 兼容现有 `Command(resume=...)` 同步接口 |
| `agent_hive/distributed_engine.py` | 分布式适配 | `TaskScheduler` / `WorkerNode` / `SharedStateStore`（Redis/内存） / `DistributedGraphAdapter`：把 LangGraph 图转换为分布式任务，Redis 不可用时单机降级 |
| `agent_hive/multi_tenancy.py` | 多租户原语 | `TenantManager` / `QuotaEnforcer` / `ApiKeyAuth`：租户注册、API Key 认证、并发/每日 token 配额、按租户隔离 run 目录（`safe_run_dir_with_tenant`） |
| `hive_security/`（独立包） | 确定性规则引擎 + SARIF | 架构安全验证：威胁目录（12 条，映射 CWE + OWASP LLM Top 10 2025）+ 规则引擎（幻觉引用/循环依赖/缺失控制/反模式）+ LLM 语义验证双通道；`hive-security scan --format sarif` 输出可进 CI（退出码 0/2/3） |
| `hive_cost/`（独立包） | 成本/熔断一等原语 | `CostGate`（预算检查/降级链/阻断）+ `ResilientModelClient`（`RetryStrategy`/`CircuitBreaker`/`ModelFallbackRegistry`）；`export_cost_otel_jsonl()` 导出 OTel 兼容事件 |

## 3. 深化路线图

> 工作量：S（≤1 周）/ M（1–3 周）/ L（≥1 个月）。每项均给出「做什么 / 怎么做 / 验收标准 / 工作量」。

### M1 近期：接入 LangChain 生态（观测 + 服务化 + 模型抽象）

#### M1-1 LangSmith 追踪接入

- **做什么**：把每次 LangGraph run 的完整执行轨迹（节点、span、token 用量、interrupt 断点）上报到 LangSmith。
- **怎么做**：LangChain 对 LangSmith 的接入是**环境变量透传**——在 `.env`（以及 `.env.example`）新增 `LANGCHAIN_TRACING_V2=true`、`LANGCHAIN_API_KEY=...`、`LANGCHAIN_PROJECT=agent-hive`，`agent_hive/main.py` 已有 `load_dotenv()` 链路，无需改业务代码；如需按 run_id 细分 project，可在 `run()` 入口用 `langsmith` SDK 设置。未配置时自动降级为不追踪（零成本）。
- **验收标准**：配置环境变量后执行一次 `uv run python -m agent_hive run --goal "<任意目标>" --yes`，LangSmith 面板可见完整图：节点级 span、每节点 token 用量、两个 `interrupt` 断点位置；不配置时行为与现状完全一致。
- **工作量**：S

#### M1-2 LangServe 把首脑暴露为 HTTP API

- **做什么**：让外部系统（Web 前端、移动端、其他服务）能通过 HTTP 发起 run、订阅流式事件、异步完成审批。
- **怎么做**：新增 `agent_hive/server.py`：用 `langserve` 的 `add_routes`（或纯 FastAPI + `graph.astream`）包装 `build_graph().compile(...)`；审批关口从「stdin 交互」切换为 `async_hitl.ApprovalQueue` + `create_resolve_endpoint()` Webhook；流式输出复用 `streaming.subscribe_sse()`；断点续跑以 `thread_id` 作为会话键。
- **验收标准**：`POST /invoke` 提交 goal 返回 `final_report`；`GET /stream`（或 `/events`）输出 SSE 事件流；审批单通过 `POST /approvals/<id>/resolve` 异步完成；同 `thread_id` 可从中断点恢复。
- **工作量**：M

#### M1-3 OpenAI 兼容供应商抽象

- **做什么**：把模型供应商从「硬编码 deepseek」扩展为任意 OpenAI 兼容端点。
- **怎么做**：仓库已有先例——`.env.example` 的 `DASHSCOPE_API_KEY` / `DASHSCOPE_BASE_URL`（阿里云百炼 `compatible-mode/v1`）；推广为通用三元组 `MODEL_BASE_URL` / `MODEL_API_KEY` / `MODEL_NAME`，`chief._model()` 与 `specialists.create_agent` 改为按变量构造（`init_chat_model` 支持 base_url 透传），缺省回退现有 deepseek 行为。
- **验收标准**：仅改 `.env` 即可在 deepseek ↔ 百炼 ↔ 任意 OpenAI 兼容端点（vLLM / Ollama 兼容层等）间切换，`--tier T2` 顾问模式跑通且结构化输出正常。
- **工作量**：S

### M2 中期：平台化与生态互操作

#### M2-1 LangGraph Platform 部署形态评估

- **做什么**：评估是否将图部署到 LangGraph Platform（托管）或 `langgraph-api` 自托管，与 M1-2 的自建 FastAPI 方案对比后做取舍。
- **怎么做**：做一个可运行 PoC：把现有图（含 interrupt/checkpoint）部署到自托管 `langgraph-api`（checkpoint 从 SQLite 迁移到 Postgres），压测 `/invoke` + 断点恢复；对照 M1-2 方案比较运维成本、多租户接入（`multi_tenancy.py`）、流式支持。
- **验收标准**：产出书面评估结论（上/不上、理由、成本量级）；自托管 PoC 可运行 `/invoke`、`/threads/<id>`、断点恢复。
- **工作量**：M

#### M2-2 MCP（Model Context Protocol）工具接入

- **做什么**：让 hive-security / hive-cost 以 **MCP server** 形式暴露（任意 MCP 客户端可用），同时让专家能消费外部 MCP 工具。
- **怎么做**：新增 `hive_security/mcp_server.py`、`hive_cost/mcp_server.py`（`mcp` / `fastmcp` SDK）：把 `hive-security scan` 与 `CostGate.check_before_call` 暴露为 MCP tools（**只暴露只读/预算类能力，不暴露命令执行**）；专家侧用 `langchain-mcp-adapters` 把外部 MCP server 接入 `specialists.py` 的工具列表，受 `tool_registry.py` 治理。
- **验收标准**：`npx @modelcontextprotocol/inspector`（或等价客户端）能调用 hive-security 的 scan 工具并返回 SARIF 内容、调用 hive-cost 的预算检查工具返回 `proceed/downgrade/block` 决策；专家在不改动提示词的前提下多出可用工具。
- **工作量**：M

#### M2-3 多租户网关

- **做什么**：把 `multi_tenancy.py` 已有的租户/配额原语接到 HTTP 层，形成可对外服务的多租户网关。
- **怎么做**：FastAPI 中间件：API Key 认证（`ApiKeyAuth.authenticate`）→ 配额检查（`QuotaEnforcer.check_before_run`）→ 按租户隔离 run 目录（`safe_run_dir_with_tenant`）；与 M1-2 的 LangServe 路由整合，配额在 run 启动前拦截。
- **验收标准**：两个租户用各自 API Key 调用，彼此不可见对方 run 目录与审批单；超配额时返回明确错误（如 429 语义），配额随 `record_run_end` 正确释放。
- **工作量**：M

### M3 远期：部署形态扩展与正式发布

#### M3-1 桌面 Tauri 壳

- **做什么**：Windows/macOS/Linux 桌面应用，复用 CLI 能力并支持本地模型。
- **怎么做**：Tauri 2 壳 + 侧载 Python 运行时（或调用本机 `agent-hive` CLI / uv）；本地模型经 Ollama / vLLM 的 OpenAI 兼容端点接入——直接复用 M1-3 的供应商抽象；前端实时事件流复用 `streaming.subscribe_sse`。
- **验收标准**：桌面应用可发起 run、弹出审批单并批准/驳回、实时看到专家事件流与最终报告。
- **工作量**：L

#### M3-2 iOS 移动端（PWA 增强 → TestFlight）

- **做什么**：在官网 PWA（现状）基础上增强，并推进原生壳 TestFlight 内测。
- **怎么做**：现状为官网 PWA 安装（Safari → 分享 → 添加到主屏幕）；增强项：补齐 manifest 与 Service Worker 离线缓存、iOS 图标；远期用 Capacitor 包壳，经 TestFlight 分发。
- **验收标准**：PWA 离线可打开首页；TestFlight 内测版可发起 run 并完成异步审批（此条落地前保持「路线图」标注）。
- **工作量**：L

#### M3-3 PyPI 正式发布

- **做什么**：把 hive-security / hive-cost 与 agent-hive 发布到 PyPI。
- **怎么做**：`.github/workflows/publish-packages.yml` 已就绪（`v*` tag 触发、`uv build` 出 wheel + sdist、`pypa/gh-action-pypi-publish` 走 **Trusted Publishing / OIDC，仓库内零密钥**）；发布前在 PyPI 创建 `hive-security` / `hive-cost` 项目并配置 Trusted Publisher（owner / repository / workflow=publish-packages.yml / environment=pypi）。**现状说明：两个包尚未上 PyPI（workflow 检测到项目不存在时自动跳过，属预期行为）**。
- **验收标准**：`pip install hive-security hive-cost` 可安装且 CLI 可用；PyPI 页面可见对应版本；agent-hive 轮子可安装并 `agent-hive --help` 正常。
- **工作量**：M

## 4. 差异化定位（与主流 Agent 框架的一句话对比）

> 参考 README 定位：「一个首脑统一统筹多个角色专家——定架构、分包派发、验收集成；**契约是运行时一等公民**，架构安全验证与成本预算内嵌为审批关口的一等原语，全部以标准工件（JSON Schema / SARIF / OTel JSONL）对外输出。」

- **vs LangGraph**：LangGraph 是通用图编排原语；本项目在其之上固化了「首脑-专家」分工模式与**契约级审批关口**，开箱即用。
- **vs CrewAI**：同为角色分工，但本项目把「契约校验（防漂移）+ 架构安全验证 + 成本预算/熔断」作为一等原语内嵌，而非纯编排层。
- **vs AutoGen**：本项目不做对话式自由协商，采用**确定性依赖分层 + 程序化输出守卫**，可审计、可阻断。
- **vs OpenAI Agents SDK**：SDK 有 guardrails/max_turns，但**缺独立成本预算原语与模型熔断原语**（README 调研实证）；本项目以 `hive-cost` 补齐，且契约、SARIF、OTel JSONL 全部为标准工件。
- **一句话总结**：差异点是「**契约一等公民 + 架构安全验证 + 成本预算/熔断**」三者组合，且每条声明可证伪（可审计检查范围 + 规则版本 + 证据，见 `benchmarks/`）。

## 5. 风险与对策

| # | 风险 | 影响 | 对策 |
|---|---|---|---|
| 1 | **模型供应商锁定**：`chief._model()` 与 `specialists.create_agent` 硬编码 `deepseek-chat`，供应商故障/涨价会整体停摆 | 可用性与成本风险 | M1-3 供应商抽象（`MODEL_BASE_URL`/`MODEL_API_KEY`/`MODEL_NAME`），保留 deepseek 缺省兼容；`hive_cost.resilience` 的 `CircuitBreaker`/`ModelFallbackRegistry` 已有 fallback 链，接入抽象后即可按供应商配置降级 |
| 2 | **CLI 形态 → 服务形态的迁移成本**：`interrupt` 目前以 stdin `input()` 交互，LangServe/移动端无法用 | 服务化阻塞 | M1-2 以 `async_hitl.ApprovalQueue` 作为**统一审批入口**（CLI 的 `sync_ask` 与服务端 Webhook 共用同一队列语义），避免两套审批逻辑漂移；`streaming.py` 的 SSE 层已就位 |
| 3 | **安全边界随工具扩展而扩大**：MCP 接入后外部工具进入专家上下文，工具面变宽 | 注入/越权风险 | 沿用 `specialists.py` 最小权限裁剪 + `_safe_env()` 密钥白名单；MCP server 只暴露只读/预算类工具；`tool_registry.py` 的 `danger_level`/`required_roles` 作为治理入口；架构安全验证保持默认开启（`--skip-arch-security` 需显式且留审计痕） |
