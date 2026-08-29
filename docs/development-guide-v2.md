# agent-hive 后续开发指南 v2（基于行业评估最终决策）

> 版本：v2.0 | 依据：`docs/industry-impact-assessment.md` v1.1 + `docs/market-research-2026.md`
> 用途：供后续调用 flash 模型**逐包编译实现**的可执行指南。每个工作包给出精确接口签名、文件布局、验收标准、验证命令与「不要做」清单。
> 铁律：flash 模型每包只做包内的事；改共享文件前必须先读；交付后运行包内验证命令，不回传口头成功。

---

## 0. 战略决策摘要（改动方案的来源）

1. **重注四个空白维度**：①契约一等公民+防漂移 ②契约级 HITL 验收回流强闭环 ③架构级安全验证内嵌审批 ④成本预算/模型熔断一等原语。
2. **组件化拆包**：把 ③ 拆成 `hive-security`、④ 拆成 `hive-cost`，标准输出（SARIF / OTel JSONL），可被任何框架消费。
3. **证据先行**：golden 语料 14→100+，benchmark 可复现，再谈推广。
4. **冻结重复区**：分布式引擎、多租户、工具注册表、流式、Prompt AB、官网五批次方案全部冻结/降级（见 §8 冻结清单）。
5. **对齐标准**：SARIF 携带 CWE + OWASP LLM Top 10 映射。

---

## 1. 实施批次总览（拓扑顺序）

```
批次 A（并行，无依赖）                    批次 B（依赖 A）             批次 C（依赖 B，发布）
┌──────────────────────────────┐   ┌──────────────────────────┐   ┌──────────────────────┐
│ WP-A1 hive-security 组件化    │   │ WP-B1 CWE/OWASP 映射     │   │ WP-C1 真实项目审计    │
│ WP-A2 hive-cost 组件化        │──▶│ WP-B2 契约公开 spec+lint  │──▶│ WP-C2 发布（PyPI+单页）│
│ WP-A3 golden 语料 100+ 与基准 │   │ WP-B3 benchmark 报告框架   │   │ WP-C3 可观测导出标准   │
└──────────────────────────────┘   └──────────────────────────┘   └──────────────────────┘
```

- 批次 A 三包可并行（各自独立目录，无共享文件冲突）。
- 批次 B/C 逐包串行，每包验收后再开下一包。
- 冻结清单（§8）在任何批次都不允许触碰。

---

## 2. WP-A1：hive-security 组件化拆包

### 2.1 目标

把架构安全验证从 agent-hive 中拆出为**纯标准库、零依赖**的独立 PyPI 包 `hive-security`，以 SARIF/JSON 为唯一输出契约，任何 agent 框架（LangGraph/CrewAI/自研）可 `pip install hive-security` 直接调用。agent-hive 内部改为薄壳引用，保持 390 项测试全绿。

### 2.2 新包文件布局（全部新建）

```text
hive_security/
├── pyproject.toml              # name="hive-security", version="0.1.0",
│                               # requires-python=">=3.11", license=MIT,
│                               # dependencies=[]（纯标准库！禁止 langchain/pydantic）
├── README.md                   # 30 秒上手 + 输出契约 + 检查范围/未覆盖范围声明
├── src/hive_security/
│   ├── __init__.py             # 重导出全部公共名，__all__ 与旧模块一致
│   ├── threat_model.py         # 从 agent_hive/threat_model.py 复制（去掉 agent_hive 相对导入）
│   ├── arch_security.py        # 从 agent_hive/arch_security.py 复制
│   │                           # 注意：去掉两个外部依赖——
│   │                           # ① agent_hive.scheduler.validate_dependency_graph
│   │                           #    → 内置 _validate_dependency_graph(packages)（环检测三色 DFS，
│   │                           #      签名与语义照抄，约 40 行）
│   │                           # ② agent_hive.data_compliance.DEFAULT_MASK_RULES
│   │                           #    → 内置 _DEFAULT_MASK_PATTERNS: list[str]（复制 5 条正则字符串）
│   └── cli.py                  # 见 2.3
└── tests/
    ├── test_threat_model.py    # 从 agent_hive tests 移植（37 用例）
    ├── test_arch_security.py   # 移植（34 用例）
    ├── test_cli.py             # 新增 CLI 契约测试
    └── golden/                 # 先复制 14 样例（WP-A3 再扩 100+）
```

### 2.3 CLI 契约（精确）

```text
用法: hive-security scan --input ARCH.json [--policy POLICY.json] [--format json|sarif|markdown] [--output PATH|-]

--input     必填。结构化架构 JSON 文件路径（与 agent_hive ArchitecturePlan.model_dump() 对齐）：
            {"overview": str, "modules": [{name, responsibility, interfaces, owner_role, depends_on?}], "risks": [str]}
--policy    选填。策略 JSON，白名单字段 = fail_on_severity/max_warnings/llm_enabled/
            llm_verdict_requires_rule/exclusions/max_findings_per_threat；
            fail_on_severity 只允许 "critical"|"high"，否则拒绝启动（SystemExit 非零）。
--format    默认 sarif。三种输出均为确定性（同输入同输出）。
--output    默认 "-"（stdout）。

退出码契约（CI 语义）：
  0 = verdict in (pass, pass_with_warnings)
  2 = verdict == fail（存在活跃 high/critical 发现）
  3 = 扫描执行错误（文件不存在/JSON 非法/策略非法）
```

实现要求：`cli.py` 只用 `argparse + json + sys`，入口 `main() -> int`，`pyproject [project.scripts] hive-security = "hive_security.cli:main"`。

### 2.4 agent-hive 侧薄壳改造（改 3 处，务必保持兼容）

```python
# agent_hive/threat_model.py 整体替换为：
"""兼容薄壳：单一事实源已迁至 hive_security.threat_model。"""
from hive_security.threat_model import *  # noqa: F401,F403
from hive_security.threat_model import __all__  # noqa: F401

# agent_hive/arch_security.py 同理指向 hive_security.arch_security
# pyproject.toml dependencies 增加 "hive-security>=0.1.0"，并加
#   [tool.uv.sources]
#   hive-security = { path = "hive_security", editable = true }
#   （发布 PyPI 后再改为版本依赖；本地开发用 path 源）
```

验证命令（必须全绿）：

```bash
cd hive_security && uv run pytest -q
cd .. && uv run pytest tests/test_threat_model.py tests/test_arch_security.py tests/test_threat_catalog_extension.py -q
uv run python scripts/security_golden.py          # 原有 14 样例仍全绿
uv run python scripts/verify.py                   # 全量门禁（390 项）
```

### 2.5 不要做（红线）

- 不引入 pydantic/langchain 进 hive_security（保持零依赖卖点）。
- 不改 `SecurityFinding/SecurityReport` 字段名与 `validate_architecture()` 签名（下游 graph.py/arch_security_llm.py 依赖）。
- 不删 agent_hive 旧模块文件（先做薄壳，兼容期至少一个版本）。
- 不在本包实现动态执行/ScopeAuthorizer（scope_auth 留 agent_hive，后续单独评估）。

---

## 3. WP-A2：hive-cost 组件化拆包

### 3.1 目标

把成本预算与模型容错拆为独立包 `hive-cost`，提供 **CostGate 一等原语** 与 **OTel 兼容 JSONL 导出**，回答行业空白问题（四强 SDK 均无预算/熔断原语）。

### 3.2 文件布局

```text
hive_cost/
├── pyproject.toml              # name="hive-cost", version="0.1.0", dependencies=[]（纯标准库）
├── README.md
├── src/hive_cost/
│   ├── __init__.py
│   ├── budget.py               # 从 cost_control.py 复制：CostBudget/CostSnapshot/CostAlert/
│   │                           # BudgetDecision/TokenEstimator/CostTracker/CostController
│   ├── resilience.py           # 从 model_resilience.py 复制：ModelFallbackConfig/CircuitBreakerState/
│   │                           # ModelCallResult/RetryStrategy/CircuitBreaker/ResilientModelClient/
│   │                           # ModelFallbackRegistry
│   ├── gate.py                 # 新：CostGate 统一入口（见 3.3）
│   └── otel.py                 # 新：export_cost_otel_jsonl(path, events) -> int（写入条数）
└── tests/
    ├── test_budget.py          # 移植 23 用例
    ├── test_resilience.py      # 移植 22 用例
    ├── test_gate.py            # 新增
    └── test_otel.py            # 新增
```

### 3.3 CostGate 精确契约

```python
# gate.py
class CostGate:
    def __init__(self, budget: CostBudget | None = None,
                 pricing: dict[str, dict[str, float]] | None = None,
                 degradation_chain: list[str] | None = None): ...

    def check_before_call(self, model: str, role: str) -> BudgetDecision: ...
    def record_after_call(self, model: str, role: str,
                          input_tokens: int, output_tokens: int,
                          latency_ms: float = 0.0) -> CostSnapshot: ...
    def snapshot(self) -> CostSnapshot: ...
    def alerts(self) -> list[CostAlert]: ...
    def to_otel_events(self) -> list[dict]: ...
        # 每个模型调用一条事件，字段固定：
        # {"name": "agent.model_call", "start_time_unix_nano": int, "end_time_unix_nano": int,
        #  "attributes": {"model": str, "role": str, "input_tokens": int, "output_tokens": int,
        #                 "cost_usd": float, "downgraded": bool, "action": "proceed|downgrade|block"}}

# otel.py
def export_cost_otel_jsonl(path: str | Path, events: list[dict]) -> int:
    # 逐行 JSON 写入（UTF-8，无中文转义），返回写入条数；父目录不存在则创建。
```

注意：`ResilientModelClient` 的 `invoke_fn` seam 必须保留签名 `fn(model, messages, tools) -> (response, error)`，测试用假 fn 注入，不真调模型。

### 3.4 agent-hive 侧薄壳

`agent_hive/cost_control.py` 与 `agent_hive/model_resilience.py` 整体替换为 `from hive_cost.budget import *` / `from hive_cost.resilience import *` 薄壳；pyproject 加 path 源（同 2.4）。

验证：

```bash
cd hive_cost && uv run pytest -q
cd .. && uv run pytest tests/test_cost_control.py tests/test_model_resilience.py -q
uv run python scripts/verify.py
```

### 3.5 不要做

- 不做成本面板/前端（LangSmith 已垄断）。
- 不改 TRACKER 语义（agent_hive/chief.py 的 _UsageTracker 不动）。
- OTel 导出只出 JSONL 工件，不实现 OTLP 网络上报。

---

## 4. WP-A3：golden 语料 100+ 与 benchmark 脚本

### 4.1 目标

把安全验证基准从 14 样例扩到 ≥100 样例（模板化生成，确定性可复现），产出检出率/误报率/延迟统计脚本，作为对外 benchmark 的证据底座。

### 4.2 交付物

```text
tests/golden/generate_corpus.py    # 模板 × 变异生成器（纯函数、确定性、seed 固定）
tests/golden/generated/*.json      # 生成产物 ≥100 个（提交入库，不靠运行时生成）
scripts/security_benchmark.py      # 基准运行器（见 4.3）
```

### 4.3 语料家族分布（必须覆盖，规则引擎可确定性判定）

| 家族 | 目标 threat | 期望 verdict | 数量 | 变异维度 |
|---|---|---|---|---|
| 幻觉引用 | T-HALL-1 | fail | 20 | 引用前缀（引用:/调用:/依赖:）、反引号、模块名 |
| 循环依赖 | T-PATT-1 | fail | 10 | 2/3/4 节点环、depends_on 顺序 |
| 缺失认证 | T-SPOOF-1 | fail | 10 | 触发词（登录/令牌/鉴权） |
| 缺失审计 | T-REPU-1 | fail | 10 | 触发词（溯源/追责） |
| 命令执行无白名单 | T-TAMP-2 | fail | 10 | 触发词（shell/命令执行） |
| 密钥/隐私/越权 | T-DISC-1 / T-DISC-2 / T-ELEV-1 | fail | 15 | 触发词（机密/泄露/敏感信息/个人信息/隐私/gdpr/越权/权限提升） |
| 执行无守卫降级 | T-SAFE-1 | fail | 10 | overview 无降级 + 接口含执行/命令 |
| 结构反模式 | T-PATT-1 | pass_with_warnings | 10 | risks 空、无 owner、模块数边界(0/31) |
| 提示注入 dogfood | T-HALL-1 | fail | 5 | overview 注入恶意指令但真实缺陷仍在 |
| 干净架构（零误报） | — | pass | 15 | 各控制词全覆盖的变体 |

合计 ≥115。每个生成样例字段与现有格式完全一致：`{name, architecture, expect_verdict, must_hit, must_not_hit}`。

### 4.4 benchmark 脚本契约

```text
scripts/security_benchmark.py
  输出（stdout，确定性）：
    total_samples / passed / detection_rate(=must_hit 命中率) /
    false_positive_rate(=must_not_hit 违规率 + 干净样例误报率) /
    avg_latency_ms / p99_latency_ms / verdict_accuracy
  退出码：全绿 0；任一统计指标低于阈值（检测率<0.95 或误报率>0.05）→ 1
```

验证：`uv run python scripts/security_golden.py`（原有 14 样例全绿）+ `uv run python scripts/security_benchmark.py`（≥100 样例达标）。

### 4.5 不要做

- 生成器不引入随机非确定性（seed 固定或用序号变异）。
- 不把 LLM 通道纳入基准（基准只测规则引擎确定性通道；LLM 通道另测）。
- 不改动现有 14 个手工样例文件。

---

## 5. WP-B1：CWE / OWASP LLM Top 10 映射

### 5.1 目标

威胁目录映射到 CWE 与 OWASP LLM Top 10（2025），SARIF 输出携带映射，对齐 GitHub Code Scanning 消费端。

### 5.2 精确契约

```python
# hive_security/src/hive_security/cwe_map.py
CWE_MAP: dict[str, list[str]] = {
    "T-SPOOF-1": ["CWE-287"],            # Improper Authentication
    "T-SPOOF-2": ["CWE-284"],            # Improper Access Control
    "T-TAMP-1":  ["CWE-74"],             # Improper Neutralization of Special Elements (Injection)
    "T-TAMP-2":  ["CWE-78"],             # OS Command Injection
    "T-REPU-1":  ["CWE-778"],            # Insufficient Logging
    "T-DISC-1":  ["CWE-798"],            # Hard-coded Credentials
    "T-DISC-2":  ["CWE-359"],            # Exposure of Private Personal Information
    "T-DOS-1":   ["CWE-400"],            # Uncontrolled Resource Consumption
    "T-ELEV-1":  ["CWE-269"],            # Improper Privilege Management
    "T-SAFE-1":  ["CWE-693"],            # Protection Mechanism Failure
    "T-PATT-1":  ["CWE-1047"],           # Modules with Circular Dependencies
    "T-HALL-1":  [],                     # 无对应 CWE（幻觉属 AI 特有）
}
OWASP_LLM_MAP: dict[str, list[str]] = {
    "T-TAMP-1": ["LLM01"], "T-SPOOF-1": ["LLM08"], "T-DISC-1": ["LLM06"],
    "T-DOS-1": ["LLM04"], "T-ELEV-1": ["LLM08"], "T-SAFE-1": ["LLM08"],
    "T-HALL-1": ["LLM09"], "T-DISC-2": ["LLM06"], "T-SPOOF-2": ["LLM08"],
}
# to_sarif() 每个 result 增加：
# "properties": {"cwe": CWE_MAP.get(threat_id, []), "owasp_llm_top10": OWASP_LLM_MAP.get(threat_id, [])}
```

> 映射依据以 CWE 官网（cwe.mitre.org）与 OWASP Top 10 for LLM 2025（genai.owasp.org）为准；实现时在 README 附映射依据表，允许评审修正个别条目。

验证：`hive_security/tests/test_cwe_map.py`——断言 to_sarif() 的每个 result 含 properties 且 threat_id 未知时映射为空列表不崩溃。

### 5.3 不要做

- 不伪造 CWE 编号（无对应就空列表，不得编造）。
- 不改 SARIF 顶层结构（仍为 2.1.0 合法结构）。

---

## 6. WP-B2：契约工作包公开 spec + 漂移 lint

### 6.1 目标

把工作包契约沉淀为公开 JSON Schema，任何 agent（Claude Code 子代理 / DSH 子智能体 / LangGraph 节点）可消费；契约漂移检查抽成独立 CLI。

### 6.2 交付物

```text
contracts/workpackage.schema.json   # JSON Schema draft 2020-12，字段与 PackageSpec 一一对应：
                                    # id(required,kebab-case)/title/role(enum 编码|测试|评审|调研|安全)/
                                    # goal/contract/expected_output/depends_on(array of id)/
                                    # size(enum S|M|L)/priority(int 1-3)/acceptance(array,minItems 1)/
                                    # deliverable/feedback(optional)
contracts/examples/packages.example.json  # 2-3 个合法样例 + 1 个非法样例（文档化）
scripts/contract_lint.py            # CLI：contract-lint PATH [--schema contracts/workpackage.schema.json]
                                    #   PATH 支持单个 JSON / 目录递归 / markdown 文件中的 ```json 块
                                    #   退出码：0 全部合法；1 有违规（stderr 逐条输出 path/field/原因）
```

实现要求：`contract_lint.py` 用 stdlib `json + re + sys` 自实现校验（不引 jsonschema 依赖）；校验规则 = schema 语义（id 格式、role 枚举、depends_on 引用存在性、acceptance 非空、size/priority 范围）。

### 6.3 与现有体系打通

- `scripts/verify.py` 增加一步：`run("contract lint", [sys.executable, "scripts/contract_lint.py", "contracts/examples/packages.example.json"])`。
- `docs/development-guide-v2.md` 本文件附录 A 输出「工作包契约字段速查表」，供外部 agent 直接引用。

### 6.4 不要做

- 不改 PackageSpec 字段名（contract_spec.py 是运行时事实源）。
- 不实现 GUI/可视化；CLI 即可。

---

## 7. WP-B3：benchmark 报告框架（两大空白维度）

### 7.1 目标

产出可复现的对比报告模板：①架构安全验证基准（hive-security vs 相邻产品定位对比）②成本预算基准（回答"预算上限下成本方差与完成率"，四强 SDK 答不了）。

### 7.2 交付物

```text
benchmarks/
├── README.md                # 复现说明（版本/命令/环境）
├── security/
│   ├── run.py               # 调 scripts/security_benchmark.py 并把结果落盘 JSON
│   └── report.template.md   # 报告模板：方法/语料规模/检出率/误报率/延迟/局限声明
└── cost/
    ├── trace_generator.py   # 合成 agent 调用轨迹（确定性 seed）：N=100 任务 × 每任务 3-20 次模型调用
    ├── run.py               # 三档预算（宽松/中等/严格）跑 CostGate，统计：
    │                        #   完成率、成本均值/方差、降级次数、block 次数、告警数
    └── report.template.md
```

验收标准：
- `uv run python benchmarks/security/run.py` 与 `uv run python benchmarks/cost/run.py` 两次运行输出逐字节一致（确定性）。
- cost 报告能回答："同一批任务，无预算 vs 严格预算，成本方差下降 X%，完成率 Y%"。
- 每个报告模板底部必须含「未覆盖范围」声明。

### 7.3 不要做

- 不在本包对第三方产品（ASTRIDE/Agentic Radar/DeepSec）做未经授权的实测对比；只允许引用其公开文档并标注「未实测」。
- 不虚构性能数字。

---

## 8. 冻结清单（任何批次都不允许触碰）

| 模块/方案 | 状态 | 说明 |
|---|---|---|
| `agent_hive/distributed_engine.py` | ❄️ 冻结 | 只修 bug，不加功能；不宣传 |
| `agent_hive/multi_tenancy.py` | ❄️ 冻结 | 保留 API Key+配额最小集 |
| `agent_hive/tool_registry.py` / `streaming.py` / `prompt_management.py` | ❄️ 维持现状 | 内部依赖，不对外宣传 |
| `docs/card-website.md` 五批次方案 | ❄️ 取消 | 由 WP-C2 单页方案替代 |
| 动态执行/沙箱（SEC-06 实际落地） | ❄️ 冻结 | 保持默认禁用；scope_auth 维持现状 |
| 官网安全中心「DeepSec 增强页」 | ❄️ 冻结 | 等 hive-security 有 benchmark 证据后再做 |

---

## 9. WP-C1：真实开源项目审计（3 个，负责任披露）

- 目标：用 hive-security 扫描 3 个真实开源 agent 项目（建议候选：CrewAI、AutoGen、LangGraph 示例库之一——**以维护者授权/公开披露渠道为准**），产出脱敏审计报告。
- 验收：3 份报告 + 维护者确认回执（issue/邮件）；报告只陈述「检查范围/规则版本/发现/证据」，不做"绝对安全"结论；发现先私下披露（如项目有 SECURITY 政策按其流程），确认修复后公开。
- 不要做：不扫描未授权目标；不公开未修复的漏洞细节。

## 10. WP-C2：发布（PyPI + README 首屏 + 单页官网）

- 交付物：
  1. `hive-security`、`hive-cost` 发布 PyPI（版本 0.1.0，MIT），GitHub Actions 用 **Trusted Publishing**（不用 token 明文）。
  2. README 首屏重写：一句话定位 + 四空白维度卖点 + 30 秒演示 + benchmark 表格 + 「检查范围/未覆盖范围」声明。
  3. 单页官网：GitHub Pages + 最小静态页（README 内容 + benchmark 图表 + PyPI/星标徽章），**取代 card-website 五批次**。
  4. 英文 README（README_EN.md 或双语）。
- 验收：`pip install hive-security` 于干净 venv 可跑 CLI；PyPI 页面显示许可证与版本；单页站 CI 自动部署。
- 不要做：不做多语言 i18n 全站、不做需要密钥的在线 demo、不做遥测（默认零遥测）。

## 11. WP-C3：可观测/评估导出标准（补最大负债）

- 目标：不做面板，做「可被消费的工件」——现有 streaming 事件与 TRACKER 成本导出为 Langfuse/LangSmith 可摄入的 OTel 兼容 JSONL。
- 交付物：
  - `agent_hive/observability.py`（新）：
    ```python
    def export_run_otel_jsonl(run_dir: str | Path, out_path: str | Path) -> int
        # 读取 runs/<id>/cost.json 与 streaming 事件 → OTel 兼容 JSONL（span 字段：
        # name/start_time_unix_nano/end_time_unix_nano/attributes/trace_id/span_id）
        # trace_id = hash(run_id) 前 32 hex；span_id = 每事件序号。返回写入条数。
    ```
  - 测试：`tests/test_observability.py`（确定性、JSONL 每行合法、字段齐全）。
- 验证：`uv run python scripts/verify.py` 全绿。
- 不要做：不实现 OTLP 网络上报、不做面板、不引入第三方 SDK。

---

## 12. flash 模型调用提示词模板（逐包复制即用）

> 通用约定：工作目录 `C:\Users\10104\Desktop\code\agent-hive`；动手前先 `read` 包内「先读」清单；完成后运行「验证」命令并粘贴真实输出；只建/改本包列出的文件；若验证失败，修复后重跑，不得谎报。

### WP-A1 提示词

```text
你是编码专家。任务：把 agent-hive 的架构安全验证拆为独立零依赖包 hive-security。
先读：agent_hive/threat_model.py、agent_hive/arch_security.py、agent_hive/scheduler.py（validate_dependency_graph）、
      agent_hive/data_compliance.py（DEFAULT_MASK_RULES）、tests/test_threat_model.py、tests/test_arch_security.py、
      docs/development-guide-v2.md 的 §2。
实现：按 §2.2 文件布局新建 hive_security/ 包（纯标准库）；arch_security.py 内两个外部依赖替换为内置实现
      （_validate_dependency_graph 三色 DFS 约 40 行；_DEFAULT_MASK_PATTERNS 5 条正则）；
      cli.py 按 §2.3 契约（退出码 0/2/3）；pyproject [project.scripts] hive-security。
兼容：agent_hive/threat_model.py 与 agent_hive/arch_security.py 整体替换为 §2.4 的薄壳 re-export；
      pyproject.toml 增加依赖与 [tool.uv.sources] path 源。
测试：移植 37+34 用例到 hive_security/tests/ 并新增 test_cli.py（覆盖退出码三态、--format 三态确定性、
      非法策略拒绝）。
验证：cd hive_security && uv run pytest -q；cd .. && uv run pytest tests/test_threat_model.py
      tests/test_arch_security.py tests/test_threat_catalog_extension.py -q；
      uv run python scripts/security_golden.py；uv run python scripts/verify.py（四步全绿才算完成）。
红线：不引 pydantic/langchain；不改 SecurityFinding/SecurityReport 字段与 validate_architecture 签名；
      不删 agent_hive 旧文件；不实现 scope_auth。
回传：文件清单 + 四条验证命令真实输出。
```

### WP-A2 提示词

```text
你是编码专家。任务：把成本控制与模型容错拆为独立零依赖包 hive-cost，并实现 CostGate 与 OTel JSONL 导出。
先读：agent_hive/cost_control.py、agent_hive/model_resilience.py、tests/test_cost_control.py、
      tests/test_model_resilience.py、docs/development-guide-v2.md 的 §3。
实现：按 §3.2 布局新建 hive_cost/；budget.py/resilience.py 为复制迁移（仅改包内相对导入）；
      gate.py 实现 CostGate（§3.3 契约）；otel.py 实现 export_cost_otel_jsonl；
      pyproject 零依赖 + [project.scripts] 不需要（库包，无 CLI）。
兼容：agent_hive/cost_control.py 与 agent_hive/model_resilience.py 替换为薄壳 re-export；
      pyproject.toml 加 path 源（同 WP-A1）。
测试：移植 23+22 用例；新增 test_gate.py（预算三态、降级链、线程安全）与 test_otel.py（字段齐全、
      JSONL 逐行合法、确定性）。
验证：cd hive_cost && uv run pytest -q；cd .. && uv run pytest tests/test_cost_control.py
      tests/test_model_resilience.py -q；uv run python scripts/verify.py（全绿）。
红线：不动 agent_hive/chief.py 的 TRACKER；不实现 OTLP 网络上报；不做面板。
回传：文件清单 + 三条验证命令真实输出。
```

### WP-A3 提示词

```text
你是编码专家。任务：把安全验证 golden 语料扩到 ≥100 样例并实现基准脚本。
先读：tests/golden/*.json（14 个）、scripts/security_golden.py、tests/golden/README.md、
      agent_hive/arch_security.py（四个检查器的触发语义）、docs/development-guide-v2.md 的 §4。
实现：tests/golden/generate_corpus.py（模板×变异、seed 固定、确定性；按 §4.3 家族分布表 ≥115 样例）
      → 生成 tests/golden/generated/*.json 并提交入库；scripts/security_benchmark.py（§4.4 契约，
      检测率≥0.95、误报率≤0.05 为通过线）。
注意：只测规则引擎确定性通道（llm_enabled=False）；变异不得让样例逃出规则引擎可判定语义
      （触发词/控制词关系见 tests/golden/README.md「已知语义边界」）。
验证：uv run python scripts/security_golden.py（原 14 全绿）；
      uv run python scripts/security_benchmark.py（≥100 样例全达标）；
      uv run python scripts/verify.py（全绿）。
红线：不改动现有 14 个手工样例；生成器无随机非确定性；不把 LLM 通道纳入基准。
回传：文件清单 + 基准脚本完整输出（含检测率/误报率/延迟）。
```

### WP-B1 提示词

```text
你是编码专家。任务：威胁目录映射 CWE 与 OWASP LLM Top 10，并让 SARIF 携带映射。
先读：hive_security/src/hive_security/arch_security.py（to_sarif）、
      hive_security/src/hive_security/threat_model.py（12 条威胁）、docs/development-guide-v2.md 的 §5。
实现：hive_security/src/hive_security/cwe_map.py（§5.2 映射表，逐条按 CWE 官网与 OWASP Top 10 for LLM
      2025 复核，README 附映射依据表）；to_sarif() 每个 result 增加 properties.cwe 与
      properties.owasp_llm_top10（缺失给空列表）。
测试：hive_security/tests/test_cwe_map.py（SARIF properties 存在、未知 threat_id 不崩溃、
      SARIF 仍为合法 2.1.0 JSON）。
验证：cd hive_security && uv run pytest -q；cd .. && uv run python scripts/verify.py（全绿）。
红线：不伪造 CWE 编号；不改 SARIF 顶层结构。
回传：文件清单 + 验证输出 + 映射依据表摘要。
```

### WP-B2 提示词

```text
你是编码专家。任务：工作包契约公开 JSON Schema + 契约漂移 lint CLI。
先读：agent_hive/contract_spec.py（PackageSpec）、agent_hive/state.py（WorkPackage）、
      scripts/generate_contracts.py（--check 模式）、docs/development-guide-v2.md 的 §6。
实现：contracts/workpackage.schema.json（draft 2020-12，字段按 §6.2 契约）；
      contracts/examples/packages.example.json（3 合法 + 1 非法样例）；
      scripts/contract_lint.py（stdlib 自实现校验：id kebab-case、role 枚举含「安全」、
      depends_on 引用存在、acceptance 非空、size S|M|L、priority 1-3；支持 JSON 文件/目录递归/
      markdown ```json 块；退出码 0/1，违规逐条输出到 stderr）。
集成：scripts/verify.py 增加 contract lint 步骤。
测试：tests/test_contract_lint.py（合法样例 0、非法样例 1 且报错信息含 path/field/原因、
      目录递归、markdown 提取）。
验证：uv run pytest tests/test_contract_lint.py -q；uv run python scripts/verify.py（全绿）。
红线：不改 PackageSpec 字段名；不引第三方 schema 库。
回传：文件清单 + 验证输出。
```

### WP-B3 提示词

```text
你是编码专家。任务：benchmark 报告框架（安全 + 成本两个维度，确定性可复现）。
先读：scripts/security_benchmark.py（WP-A3 产物）、agent_hive/cost_control.py 或 hive_cost/、
      docs/development-guide-v2.md 的 §7。
实现：benchmarks/security/run.py（调 security_benchmark 并落盘 JSON）、
      benchmarks/cost/trace_generator.py（seed 固定：N=100 任务 × 3-20 次调用合成轨迹）、
      benchmarks/cost/run.py（宽松/中等/严格三档预算跑 CostGate，统计完成率/成本均值方差/
      降级次数/block 次数/告警数，输出 JSON）、两套 report.template.md（含方法与「未覆盖范围」声明）、
      benchmarks/README.md（复现说明）。
验证：连续两次运行 security/run.py 与 cost/run.py 输出逐字节一致；报告模板渲染成功。
红线：不对第三方产品做未经授权实测；不虚构数字。
回传：文件清单 + 两次运行 diff 结果 + cost 统计摘要。
```

### WP-C1 提示词

```text
你是调研+安全专家。任务：用 hive-security 对 3 个真实开源 agent 项目做负责任安全审计。
先读：docs/development-guide-v2.md 的 §9、hive_security/README.md（输出契约与检查范围声明）。
流程：①选 3 个项目（优先有 SECURITY 政策的知名 agent 项目）；②克隆到本机临时目录（不入库）；
      ③对项目「架构描述/文档/依赖声明」构造 architecture_object 输入（或直接扫其架构文档提取）；
      ④跑 hive-security scan --format sarif；⑤人工复核每条 finding 是否为真（证据必引原文）；
      ⑥先按项目披露流程私下报告，等待确认后再公开报告（脱敏）。
交付：docs/audits/<项目名>-<日期>.md ×3（检查范围/规则版本/发现表/复核结论/披露状态）。
红线：不公开未修复漏洞细节；不扫描未授权目标；不做绝对安全结论。
回传：3 份报告路径 + 披露状态摘要。
```

### WP-C2 提示词

```text
你是工程+文档专家。任务：发布 hive-security 与 hive-cost 到 PyPI，重写 README 首屏，做单页官网。
先读：docs/development-guide-v2.md 的 §10、docs/industry-impact-assessment.md 的 §4/§8、
      README.md 现状。
实现：①两个包的 GitHub Actions 工作流用 PyPI Trusted Publishing（.github/workflows/publish-*.yml，
      不用明文 token）；②README 首屏按「一句话定位 + 四空白维度 + 30 秒演示 + benchmark 表 +
      范围声明」重写；③README_EN.md；④GitHub Pages 单页（静态 HTML 或 mkdocs 最小配置，
      含 badge/benchmark 图/安装命令），工作流自动部署；⑤LICENSE/版本号对齐（0.1.0）。
验证：干净 venv 中 pip install hive-security 后 hive-security --help 可运行（本地 wheel 验证）；
      单页站 CI 构建通过；链接检查无死链。
红线：不建多语言全站；不做在线 demo/遥测；不宣称「合规认证」。
回传：文件清单 + 安装验证输出 + Pages 工作流名称。
```

### WP-C3 提示词

```text
你是编码专家。任务：可观测/评估导出标准（OTel 兼容 JSONL，不实现面板）。
先读：agent_hive/chief.py（TRACKER、cost.json 结构）、agent_hive/streaming.py（StreamEvent）、
      agent_hive/main.py（run 产物目录）、docs/development-guide-v2.md 的 §11。
实现：agent_hive/observability.py 的 export_run_otel_jsonl(run_dir, out_path) -> int
      （§11 契约：trace_id=hash(run_id) 前 32 hex、span_id 序号递增、字段固定、UTF-8 JSONL）；
      tests/test_observability.py（用 tmp_path 造 cost.json+事件 → 导出 → 逐行 json.loads 校验字段/
      trace_id 一致/确定性/返回条数正确）。
验证：uv run pytest tests/test_observability.py -q；uv run python scripts/verify.py（全绿）。
红线：不引入第三方 SDK；不实现 OTLP 网络上报；不改 TRACKER。
回传：文件清单 + 验证输出。
```

---

## 13. 每包完成后的总门禁（统一要求）

任何包交付前必须全部通过：

```bash
uv run pytest -q                      # 全量（当前基线 390 项，只增不减）
uv run python scripts/verify.py       # pytest+compileall+contract drift+golden（+contract lint）
uv run python scripts/security_golden.py   # 原 14 样例不回归
```

若 `scripts/verify.py` 因新增步骤（如 contract lint）需要更新，属于 WP-B2 包内允许改动，其余包不得擅改。

---

## 附录 A：工作包契约字段速查表（供外部 agent 消费，见 WP-B2）

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| id | string | ✅ | kebab-case，全局唯一 |
| title | string | ✅ | 一句话 |
| role | enum | ✅ | 编码/测试/评审/调研/安全 |
| goal | string | ✅ | 交付后用户能获得什么 |
| contract | string | ✅ | 接口契约：输入/输出/格式/依赖 |
| expected_output | string | ✅ | 产出类型与格式（输出守卫依据） |
| depends_on | string[] | ✅ | 引用的 id 必须存在；无依赖给 [] |
| size | enum | ✅ | S/M/L |
| priority | int | ✅ | 1-3，1 最高 |
| acceptance | string[] | ✅ | ≥1 条，可逐项打勾、可证伪的正向断言 |
| deliverable | string | ✅ | 路径，如 workspace/<id>/ |
| feedback | string | ❌ | 驳回反馈（返工时带入） |

## 附录 B：本指南自身版本与演进

- 本指南随批次验收更新：每完成一个 WP，在「实施批次总览」标注 ✅ 与验收日期。
- 若市场格局出现重大变化（如 LangGraph 原生加入架构评审），回到 `docs/industry-impact-assessment.md` 重评后再改本指南。
