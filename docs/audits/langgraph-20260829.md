# LangGraph 架构安全审计（hive-security 规则引擎）

## 0. 摘要

本次对开源项目 **LangGraph**（langchain-ai/langgraph @ `11ee185999b86bfea2d8c0e69cef9a5e37acf686`，MIT 协议）执行**文档级、负责任、只读**的架构安全审计：不解析源码、不执行目标代码、不修改目标仓库。审计输入为仓库内公开文档（根 README、各库 README、`docs/llms.txt` 概念清单、`AGENTS.md`/`CLAUDE.md` 架构说明），按固定输入契约构造结构化架构 `arch.json`（8 个模块），交由 hive-security 0.1.0 确定性规则引擎扫描（威胁目录版本 1.0.0，SARIF 与 JSON 双格式，退出码均为 0，verdict=pass）。

**结论**：引擎检出 **0 条 finding**（0 真阳性 / 0 误报），未发现需要私下披露的产品级漏洞。人工复核补充了 **5 条文档级观察**（OBS-1~5），其中最重要的 1 条（checkpoint 反序列化默认宽松、可经 `LANGGRAPH_STRICT_MSGPACK`/`allowed_msgpack_modules` 加固）已通过克隆源码 grep **证实**（`_msgpack.py:12` 默认关闭、`jsonplus.py:112` permissive 默认），属于**文档明确声明并配套了加固控制项的安全设计属性**，未判定为可利用漏洞。本报告是设计层面的静态观察记录，**不构成任何形式的安全保证**。

## 1. 检查范围

### 1.1 输入来源文档清单（全部只读）

| 文档 | 行号范围 | 用途 |
|---|---|---|
| `README.md`（仓库根） | 1–82 | overview 引言（L24）、特性列表（L37–43）、安装命令（L27） |
| `libs/langgraph/README.md` | 1–46 | 核心库职责（L22） |
| `docs/llms.txt` | 1–35 | 概念清单（Graph API / Streaming / Persistence / Memory / Subgraphs 等，已迁往 docs.langchain.com） |
| `AGENTS.md` | 1–65 | 库清单（L32–39）与依赖图（L46–61） |
| `CLAUDE.md` | 1–65 | 与 AGENTS.md 同内容 |
| `libs/checkpoint/README.md` | 1–121 | BaseCheckpointSaver 接口（L58–66）、线程配置（L33–43）、serde 安全说明（L49–50） |
| `libs/checkpoint-postgres/README.md` | 1–126 | Security 段（L27–30）、用法代码（L56–116） |
| `libs/checkpoint-sqlite/README.md` | 1–123 | Security 段（L25–28）、用法代码（L32–113） |
| `libs/prebuilt/README.md` | 1–160 | `create_react_agent`（L30–58）、`ToolNode`（L62–86）、`ValidationNode`（L88–118）、Agent Inbox / `interrupt`（L120–150） |
| `libs/sdk-py/README.md` | 1–98 | 职责（L19）、默认 localhost（L21）、Known Limitations（L52–57） |
| `libs/sdk-js/README.md` | 1–11 | 已迁移至 langchain-ai/langgraphjs |
| `libs/cli/README.md` | 1–136 | 命令与默认绑定（L46–52、L60–67） |

### 1.2 结构化输入与摘录规则

- **arch.json 路径**：`C:\Users\10104\Desktop\code\agent_audit_tmp\langgraph\_audit\arch.json`（UTF-8）
- **摘录规则**：
  - `overview` = README.md:24 引言原文（英文原句）；
  - `modules`（8 个） = 文档中的组件名，按 AGENTS.md 库清单（L32–39）与各 README 实际描述命名：`langgraph` / `checkpoint` / `checkpoint-postgres` / `checkpoint-sqlite` / `prebuilt` / `sdk-py` / `sdk-js` / `cli`。注意：README 已不包含 StateGraph/Node/Edge/Store/Command 等 API 级文档（完整文档迁往 docs.langchain.com），因此未编造这些名称；
  - `responsibility` = 各 README 职责段英文原文摘录；
  - `interfaces` = 文档代码片段中的公开 API 签名文本（如 `create_react_agent(model, tools)`、`BaseCheckpointSaver.put`、`interrupt([request])[0]`、`langgraph dev [OPTIONS]` 等）；
  - `owner_role` = `"编码"`（输入契约必填字段，**非目标文档内容**，报告特此注明）；
  - `depends_on` = 仅写 AGENTS.md 依赖图（L46–61）明确声明的依赖：`checkpoint→(checkpoint-postgres, checkpoint-sqlite, prebuilt, langgraph)`、`prebuilt→langgraph`（即 langgraph 依赖 prebuilt）、`sdk-py→(langgraph, cli)`、`sdk-js` standalone；未声明的依赖不编造；
  - `risks` = 从文档摘录的风险/限制/安全表述原文（见 1.4）。

### 1.3 工具与版本

- 规则引擎：**hive-security 0.1.0**（CLI driver：SARIF 输出 `tool.driver.version=0.1.0`，name=`agent-hive arch_security`）
- 威胁目录版本：**1.0.0**（实测命令 `uv run python -c "from hive_security.threat_model import THREAT_CATALOG_VERSION; print(THREAT_CATALOG_VERSION)"` 输出 `1.0.0`，exit 0）
- 目标：`langchain-ai/langgraph` @ `11ee185999b86bfea2d8c0e69cef9a5e37acf686`（git log 确认，2026-08-28 commit，MIT）
- 审计日期：**2026-08-29**

### 1.4 arch.json 关键字段出处（证据列）

| 字段 | 内容摘要 | 出处 |
|---|---|---|
| overview | "Trusted by companies shaping the future of agents … stateful agents." | README.md:24 |
| modules[0] langgraph 职责 | "LangGraph is a low-level orchestration framework … memory, and more." | libs/langgraph/README.md:22 |
| modules[1] checkpoint 职责 | "This library defines the base interface for LangGraph checkpointers … durable execution, and more." | libs/checkpoint/README.md:19 |
| modules[1] 接口 | put/put_writes/get_tuple/list/delete_thread()/get_next_version()、InMemorySaver()、thread_id 配置 | libs/checkpoint/README.md:58–66、41、72 |
| modules[2] checkpoint-postgres 职责 | "Postgres implementation of LangGraph's checkpoint saver …" | libs/checkpoint-postgres/README.md:19 |
| modules[3] checkpoint-sqlite 职责 | "SQLite implementation of LangGraph's checkpoint saver …" | libs/checkpoint-sqlite/README.md:19 |
| modules[4] prebuilt 职责/接口 | "high-level APIs for creating and executing LangGraph agents and tools …"；create_react_agent(model, tools)、ToolNode([search])、ValidationNode([SelectNumber])、interrupt([request])[0] | libs/prebuilt/README.md:19、53、79、108、146 |
| modules[5] sdk-py 职责/接口 | "Python SDK for interacting with the LangGraph API …"；get_client(url=...)、client.threads.create()、client.runs.stream(...) | libs/sdk-py/README.md:19、32–48 |
| modules[6] sdk-js 职责 | "JS/TS SDK for interacting with the LangGraph REST API."（已迁移） | AGENTS.md:38、libs/sdk-js/README.md:7 |
| modules[7] cli 职责/接口 | "official command-line interface for LangGraph …"；langgraph new/dev/up/build/dockerfile | libs/cli/README.md:19、38–87 |
| depends_on | AGENTS.md 依赖图 | AGENTS.md:46–61 |
| risks[0] | "Checkpoint deserialization security: By default the serializer allows any Python type found in checkpoint data …" | libs/checkpoint/README.md:50 |
| risks[1] | "… preventing code execution if the database is compromised." | libs/checkpoint-postgres/README.md:30（同文亦见 checkpoint-sqlite/README.md:28） |
| risks[2] | "… the SDK will automatically point at http://localhost:8123 …" | libs/sdk-py/README.md:21 |
| risks[3] | "Reconnect attempts are limited to 5 by default …" | libs/sdk-py/README.md:57 |

### 1.5 扫描执行（工作目录 `C:\Users\10104\Desktop\code\agent-hive`，`uv run`）

| 命令 | 退出码 | 结果 |
|---|---|---|
| `uv run hive-security scan --input …\arch.json --format sarif --output …\out.sarif` | **0** | verdict=pass，results=[] |
| `uv run hive-security scan --input …\arch.json --format json --output …\out.json` | **0** | verdict=pass，findings=[] |

执行了 4 项确定性检查：`check_hallucinated_references`、`check_dependency_cycle`、`check_missing_security_controls`、`check_architectural_anti_patterns`，均为 0 findings。

## 2. 发现表

### 2.1 引擎检出 finding（全部）

**共 0 条**。以下为引擎 4 项检查的逐项说明：

| 检查 | 威胁 | 检出数 | 未检出原因（复核结论） |
|---|---|---|---|
| check_hallucinated_references | T-HALL-1 | 0 | 输入 interfaces 均为文档代码片段签名文本，无反引号包裹名称、无「引用:/调用:/依赖:」前缀 → 无幻觉引用 |
| check_dependency_cycle | T-PATT-1 | 0 | depends_on 严格取自 AGENTS.md 依赖图（L46–61），为无环 DAG |
| check_missing_security_controls | （目录 12 类） | 0 | 模块文本（responsibility+interfaces）为英文原文，威胁目录关键词为中文（含 risks/shell/gdpr 等少量英文子串均未命中）→ 无关键词命中，见 §3 误报分析 |
| check_architectural_anti_patterns | T-PATT-1 / T-SAFE-1 | 0 | risks 非空（4 条）；8 个模块均含 owner_role；模块数 ≤30；overview 为英文且无「执行/命令」接口 → 无 T-SAFE-1 |

### 2.2 人工复核补充：文档级观察（非引擎检出，明确标注）

以下为审计员在阅读文档后的人工观察，**不属于引擎 finding**，标注证据出处；OBS-1 额外做了源码抽查证实。

| # | 观察 | 证据摘录（出处:行号） | 复核结论 |
|---|---|---|---|
| OBS-1 | checkpoint 反序列化默认宽松：默认允许 checkpoint 数据中的任意 Python 类型，需 `LANGGRAPH_STRICT_MSGPACK=true` 或显式 `allowed_msgpack_modules` 收紧 | "By default the serializer allows any Python type found in checkpoint data. New applications should set the environment variable `LANGGRAPH_STRICT_MSGPACK=true` or pass an explicit `allowed_msgpack_modules` list …"（libs/checkpoint/README.md:50） | **文档级观察，源码证实**：`_msgpack.py:12` `os.getenv("LANGGRAPH_STRICT_MSGPACK", "false")` 默认关闭；`jsonplus.py:112` "Permissive (default): all types allowed with a warning"；`jsonplus.py:580–603` 存在未注册类型阻断逻辑。属「文档已声明 + 已提供加固控制」的安全设计属性，**未判定为可利用漏洞**（未做利用验证） |
| OBS-2 | Postgres/SQLite checkpointer 官方安全提示：数据库被攻破时反序列化可能导致代码执行 | "This restricts checkpoint deserialization to known-safe types, preventing code execution if the database is compromised."（libs/checkpoint-postgres/README.md:30；同文 libs/checkpoint-sqlite/README.md:28） | 文档级观察：维护者主动披露的威胁场景与缓解项，与 OBS-1 同源 |
| OBS-3 | sdk-py 本地默认端点 `http://localhost:8123`，隐含「本地开发无认证」假设 | "…the SDK will automatically point at `http://localhost:8123`; otherwise, specify the server URL when creating a client."（libs/sdk-py/README.md:21） | 文档级观察：部署远程 Server 时必须显式指定 URL 并自行配置认证；文档未声明 SDK 侧默认认证机制 |
| OBS-4 | SDK 流式可用性限制：SSE 重连仅 5 次、同步流占用后台线程 | "Reconnect attempts are limited to 5 by default …"（libs/sdk-py/README.md:57）；"Sync streaming drives the lifecycle watcher in a background thread …"（L56） | 文档级观察：可用性/资源限制，非安全漏洞；中断的流可能以 RuntimeError 失败 |
| OBS-5 | cli `langgraph dev` 提供远程调试开关 | "`--debug-port INTEGER` Enable remote debugging"（libs/cli/README.md:50）；默认绑定 `--host 127.0.0.1`、`--port 2024`（L47–48） | 文档级观察：远程调试端口暴露属部署注意项；默认仅回环绑定，未发现默认暴露面 |

## 3. 误报分析

- **数量：0 条误报**（引擎 0 检出，无 finding 可复核为误报）。
- **原因归类**：
  1. **引擎语义限制（主因）**：hive-security 内置威胁目录（`threat_model.py` `_BUILTIN_THREATS`）的关键词几乎全为中文（`认证/鉴权/白名单/注入/限流…`），而目标文档为英文，模块文本（英文原文）无关键词命中，导致 `check_missing_security_controls` 与 `check_architectural_anti_patterns`（T-SAFE-1）的检出率为零。这属于「检出率受限」，**不构成证据矛盾型误报**，也不代表目标无风险（见 §2.2 观察表与 §5）。
  2. **输入构造诚实性**：为遵守审计契约（responsibility/interfaces/risks 均保留英文原文），未在 arch.json 中引入中文触发词、反引号引用或编造的接口名，因此不存在人为制造的幻觉引用（T-HALL-1）或缺失控制信号；若放宽该约束可提高检出，但会引入与目标文档无关的假阳性。
  3. **依赖图无环**：depends_on 严格取自 AGENTS.md 官方依赖图，为 DAG，故 T-PATT-1（循环依赖）不触发。
- **结论**：0 检出是「输入语言与规则语言不匹配」的确定性结果，而非证据被证伪或规则缺陷；**0 检出 ≠ 0 风险**。

## 4. 披露状态

- **SECURITY.md**：LangGraph 仓库根**无 `SECURITY.md`**（对克隆根目录递归 depth-2 扫描确认无该文件；仓库亦无 `.github/SECURITY.md`）。仓库未声明独立安全披露流程。
- **披露渠道**：GitHub 私有安全公告（GitHub Security Advisory）机制——即 GitHub 私有漏洞报告（Private vulnerability reporting）入口。
- **如实说明**：
  1. 本环境无 GitHub 提交/发布凭据，**无法实际提交私有公告**；本文档仅为审计记录，不发起任何披露动作。
  2. 若未来确认产品级缺陷，正确流程为：经 GitHub 私有公告**私下**报告维护者 → 观察 14 天（标准协调期）→ 维护者无响应或修复发布后再考虑公开；本报告不构成该流程的替代或启动。
  3. **本次结论：未发现需要私下披露的产品级漏洞**，全部发现为文档级观察（§2.2）；未向任何公开渠道发布任何内容。

## 5. 未覆盖范围声明

1. **公开文档非源码检查**：本审计以公开文档为唯一输入；仅对 OBS-1 的 1 项安全说明做了克隆源码 grep 证实（`_msgpack.py`、`jsonplus.py`）。其余模块的代码实现、逻辑缺陷、危险模式（eval/exec/shell、硬编码密钥等）不在本次范围内。
2. **不构成安全保证**：本文档是设计层面的静态观察记录；"0 引擎检出" 反映规则引擎对英文文档的检出边界，不代表目标系统安全，也不代表不存在未披露缺陷。
3. **不覆盖依赖/供应链/运行时**：未审计第三方依赖（psycopg、aiosqlite、pydantic 等）与供应链完整性；未审计 LangGraph Platform / LangGraph Server 的运行时认证、授权、网络边界与多租户隔离（仓库内无对应文档）；`langgraph.json` 配置、Docker 部署等运行时形态仅见 README 描述，未做验证。
4. **中文关键词目录对英文文档检出有限**：hive-security 威胁目录关键词以中文为主，对英文文档的自动检出率显著受限（见 §3），本报告的观察表（§2.2）即为此限制的人工补偿。
5. **检出率受输入构造影响**：模块选取（8 个库 vs 完整组件树）、接口摘录忠实度、risks 收录范围均影响结果；换用不同摘录粒度可能产生不同检出。

---
*附：工作产物（均在目标仓库外）*：`C:\Users\10104\Desktop\code\agent_audit_tmp\langgraph\_audit\arch.json`、`…\out.sarif`、`…\out.json`。
