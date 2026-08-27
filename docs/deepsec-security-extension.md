# DeepSec 安全增强扩展方案

> 版本：v1.0 | 状态：待架构审批
> 目标：在 agent-hive 的“架构生成 → 专家实现 → 评审 → 集成”链路中增加可审计、可阻断、可回归的 AI 安全验证闭环。

## 0. 设计结论

本方案**只借鉴公开项目的产品思想与安全工作流，不复制 DeepSec 源码**。DeepSec 公开仓库将产品定位为 AI Security Offense & Defense Platform，并强调 Shield 对 AI 生成代码进行审计、发现幻觉依赖和缺失防护，Spear 用于授权的渗透测试与技能包编排。具体实现、许可证和当前接口必须以其仓库实际内容为准：

- [DeepSec GitHub](https://github.com/Unclecheng-li/DeepSec)
- [DeepSec README](https://github.com/Unclecheng-li/DeepSec/blob/main/README.md)
- [DeepSec 中文快速开始](https://github.com/Unclecheng-li/DeepSec/blob/main/docs/QUICKSTART.zh-CN.md)
- [DeepSec Shield 指南](https://github.com/Unclecheng-li/DeepSec/blob/main/docs/shield-guide.md)

### 采用的思想

1. **Shield 思路**：对 AI 生成的代码、依赖、配置、工具调用和架构决策进行安全审计。
2. **Spear 思路**：把授权安全测试拆成可选择、可审计、可限制的技能包；不默认对外发起攻击。
3. **攻防闭环**：静态扫描 → 风险归因 → 人工审批 → 安全修复 → 回归验证 → 证据归档。
4. **安全结果是一等工件**：安全报告进入看板、manifest、审计日志和最终交付报告，而不是只打印文本。

### DeepSec 组件 → agent-hive 模块映射（防实现走偏）

| DeepSec 已核实组件 | 本项目落点 | 继承什么 | 不继承什么 |
|---|---|---|---|
| Shield L1 正则/熵 + L2 AST 扫描 | SEC-03 静态审计内置规则 | 分层检测思路、evidence/rule_id 结构 | 其规则文件与实现代码 |
| Shield `--format json/sarif` + 退出码 2 | SEC-10 CLI/SARIF 契约 | 机器可读输出 + CI 退出码语义 | 其 CLI 参数与品牌 |
| Spear `scope.json` targets 白名单 + 私网拒绝 | SEC-11 ScopeManifest + ScopeAuthorizer | 硬门禁思想：白名单/私网拒绝/审计日志 | 其"签名可选"的宽松化处理 |
| Spear 渗透执行引擎 | 不落地（仅授权动态验证隔离于 SEC-06） | — | 攻击引擎、外部工具链（nmap/sqlmap） |
| 技能包 SKILL.md（Domain/Boundaries/Exit Evidence） | 未来 F2 安全技能包生态 | 受限自主 agent 的 prompt 工程化思想 | 技能包正文与 warstories |
| dsh 插件（子进程薄封装） | 可选适配器参考 | 子进程调用 + JSON 采集边界 | developer preview 契约硬依赖 |
| GitHub Action（Node/TS） | **明确不采用** | — | VibeGuard 品牌、双实现漂移 |

### 明确不采用的做法

- 不在默认流程中进行真实目标扫描、漏洞利用或外部网络探测。
- 不允许 LLM 自由生成并执行任意安全工具命令。
- 不把“扫描器没有发现问题”表述为“绝对安全”。
- 不将 DeepSec 的实现代码、提示词、规则库或未确认许可证内容直接复制入本项目。

---

## 1. 目标架构

```text
用户目标
   │
   ▼
Chief 架构/分包
   │
   ▼
专家实现与集成 ───────► artifacts/dist
   │                         │
   │                         ▼
   └──────────────► Security Gateway
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
       Static Audit   Dependency   Policy/Threat
       (代码/配置)     Audit        Model Audit
             │            │            │
             └────────────┼────────────┘
                          ▼
                  Risk Normalizer
                          │
                ┌─────────┴─────────┐
                ▼                   ▼
        HITL Approval Queue   Auto Remediation
                │                   │
                └─────────┬─────────┘
                          ▼
                   Security Regression
                          │
                          ▼
            Release Gate / Partial Delivery
```

### 核心原则

- **默认 fail-closed**：高危且证据充分的发现阻断集成；低置信度发现进入人工复核。
- **分层扫描**：先无副作用静态审计，再显式开启动态验证。
- **证据优先**：每条风险必须含 rule、位置、证据摘要、置信度、修复建议。
- **租户隔离**：安全报告、扫描目标、规则配置和审计事件必须带 tenant_id。
- **成本受控**：扫描预算接入现有 CostController；LLM-as-judge 不是无限重试。
- **可回放**：扫描事件接入 StreamManager，完整结果写入 DataCompliance 审计链。

---

## 2. 模块与接口契约

新增模块建议：

```text
agent_hive/security/
├── __init__.py
├── models.py              # SecurityFinding、ScanRequest、ScanReport
├── policy.py              # 安全策略与 release gate
├── scanner.py             # Scanner 抽象与静态扫描编排
├── dependency_audit.py    # 依赖幻觉/供应链检查
├── threat_model.py        # 架构威胁建模
├── remediation.py         # 修复建议与安全补丁工作包
├── regression.py          # 安全回归基线
├── evidence.py            # 证据、hash、报告归档
└── adapters/              # 外部工具适配器，默认禁用网络副作用
```

### 2.1 数据结构

```python
@dataclass
class ScanRequest:
    scan_id: str
    run_id: str
    tenant_id: str = ""
    target_dir: str = ""
    mode: Literal["static", "dependency", "threat_model", "dynamic"] = "static"
    policy_name: str = "default"
    enabled_rules: list[str] = field(default_factory=list)
    budget_tokens: int = 0
    allow_network: bool = False
    allow_dynamic_execution: bool = False

@dataclass
class SecurityFinding:
    id: str
    scan_id: str
    severity: Literal["critical", "high", "medium", "low", "info"]
    category: Literal[
        "secret", "injection", "authn", "authz", "ssrf", "unsafe_deserialization",
        "dependency", "supply_chain", "data_leak", "missing_control", "threat_model",
    ]
    title: str
    description: str
    evidence: str
    file_path: str = ""
    line_start: int = 0
    line_end: int = 0
    rule_id: str = ""
    confidence: float = 0.0
    cwe: str = ""
    fix_suggestion: str = ""
    false_positive: bool = False

@dataclass
class ScanReport:
    scan_id: str
    run_id: str
    tenant_id: str
    status: Literal["passed", "failed", "partial", "error"]
    findings: list[SecurityFinding] = field(default_factory=list)
    checks: list[dict] = field(default_factory=list)
    started_at: float = 0.0
    completed_at: float = 0.0
    tool_versions: dict[str, str] = field(default_factory=dict)
    evidence_hash: str = ""

@dataclass
class SecurityPolicy:
    name: str = "default"
    block_severities: list[str] = field(default_factory=lambda: ["critical", "high"])
    min_confidence_to_block: float = 0.85
    require_human_approval_for: list[str] = field(default_factory=lambda: ["critical", "high"])
    max_findings_before_partial: int = 0
    allow_dynamic_by_default: bool = False
    excluded_rules: list[str] = field(default_factory=list)

@dataclass
class ScopeManifest:
    """动态验证授权清单（借鉴 DeepSec scope.json 的硬门禁思想）。"""
    scope_id: str
    tenant_id: str
    targets: list[str]                 # 允许的目标白名单
    valid_from: float = 0.0            # 授权生效时间
    valid_until: float = 0.0           # 授权过期时间，0 表示长期（需审批）
    prohibited_cidrs: list[str] = field(default_factory=lambda: ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8", "169.254.0.0/16", "224.0.0.0/4"])
    allowed_ports: list[int] = field(default_factory=list)
    signer: str = ""                   # 授权人
    approver: str = ""                 # 审批人
    reason: str = ""                   # 授权理由（入审计日志）
```

### 2.2 公共接口

```python
class SecurityScanner:
    def scan(self, request: ScanRequest) -> ScanReport: ...

class SecurityPolicyEngine:
    def evaluate(self, report: ScanReport, policy: SecurityPolicy) -> ReleaseDecision: ...

class ReleaseDecision:
    action: Literal["allow", "block", "needs_approval", "partial"]
    reason: str
    blocking_findings: list[str]
    approval_request_id: str | None

class ThreatModeler:
    def analyze(self, architecture: str, packages: list[dict]) -> list[SecurityFinding]: ...

class SecurityRegressionStore:
    def save_baseline(self, report: ScanReport): ...
    def compare(self, report: ScanReport) -> RegressionResult: ...

class ScopeAuthorizer:
    """动态验证目标授权器：白名单 + 私网/回环/组播/保留地址拒绝。"""
    def authorize_target(self, manifest: ScopeManifest, target: str) -> ScopeDecision: ...
    def write_audit_log(self, manifest: ScopeManifest, target: str, command_hash: str): ...

class ScopeDecision:
    allowed: bool
    reason: str
    is_private_network: bool
```

SARIF 与退出码契约（对齐 DeepSec 已核实的机器可读行为）：

```python
class ScanReport:
    def to_sarif(self) -> str: ...       # SARIF 2.1.0 输出
    def to_json(self) -> str: ...

# CLI 退出码契约：allow=0；存在活跃 high/critical 发现 block=2；扫描执行错误 error=3
```

---

## 3. 详细工作流程卡片

## SEC-01：安全架构源与契约

- **优先级**：P0
- **依赖**：无
- **负责人**：架构/安全工程
- **目标**：把安全结果、风险等级、策略决策、证据结构纳入 agent-hive 单一契约。
- **交付物**：`security/models.py`、`security/policy.py`、contract 更新、类型校验测试。
- **步骤**：
  1. 定义 ScanRequest、SecurityFinding、ScanReport、SecurityPolicy。
  2. 统一 severity/category/action 枚举，拒绝自由文本漂移。
  3. 规定 file_path 必须经过现有 `paths.py` 围栏。
  4. 将 tenant_id、run_id、scan_id 设为审计主键。
  5. 更新 `contract_spec.py`，生成 `skill/contracts.md`。
- **验收**：JSON 往返不丢字段；非法 severity 被拒绝；契约漂移检查通过。

## SEC-02：安全网关与发布门禁

- **优先级**：P0
- **依赖**：SEC-01、现有 integration.py、card-async-hitl（低置信度审批）、card-tool-registry（扫描器注册）
- **目标**：将安全扫描结果接入集成过程，避免“代码合并成功但存在高危漏洞”。
- **步骤**：
  1. 集成 staging 后触发 static scan。
  2. PolicyEngine 按 severity + confidence + rule exception 计算决策。
  3. critical/high 且置信度达到阈值时返回 block。
  4. 低置信度高危发现进入 async HITL，不静默放行。
  5. 将 decision 写入 `manifest.json` 和 `integration` 结构。
  6. block 时保留原有 dist，不污染已知良好交付物。
- **验收**：高危阻断；低置信度进入审批；部分结果为 partial；旧 dist 不变。

## SEC-03：静态代码安全审计

- **优先级**：P0
- **依赖**：SEC-01
- **目标**：审计 AI 生成代码中的危险调用、身份校验缺失、数据泄露和注入风险。
- **步骤**：
  1. 仅扫描 integration staging 目录。
  2. 先使用 AST/正则等无副作用规则；LLM 只做解释和归因。
  3. 规则最小集合：`eval/exec`、命令拼接、路径穿越、硬编码密钥、未校验外部输入、危险反序列化、SSRF、弱认证。
  4. 每条 finding 记录 rule_id、文件行号、证据摘要和修复建议。
  5. 通过 DataMasker 脱敏 evidence，不存储密钥原文。
  6. 报告导出 SARIF 2.1.0 与 JSON（`to_sarif()`/`to_json()`），供 SEC-02 门禁与 CI 归档。
  7. 可选 DeepSec 适配器走 Python CLI（`deepsec shield scan --format sarif --output -`），未安装时优雅降级为内置规则（见 §10）。
- **验收**：已知样例可检出；误报不阻断；敏感证据脱敏；扫描无网络副作用；SARIF/JSON 双格式可导出。

## SEC-04：依赖与供应链审计

- **优先级**：P0.5
- **依赖**：SEC-01、ToolRegistry、CostController
- **目标**：识别 AI 生成代码中的幻觉包、拼写相似包、未锁定版本和高风险依赖。
- **步骤**：
  1. 解析 `pyproject.toml`、lockfile、requirements 文件。
  2. 校验依赖是否存在于允许的内部/公开索引；网络访问必须显式配置。
  3. 检查版本是否锁定、许可证是否允许、依赖是否超出 tenant 白名单。
  4. 对“无法确认存在”的包标为 dependency/high-confidence-low，交人工确认。
  5. 依赖检查结果纳入 manifest 和安全回归基线。
- **验收**：幻觉包可标记；不因网络不可用崩溃；网络关闭时明确返回 unknown，而非假定安全。

## SEC-05：架构威胁建模

- **优先级**：P0.5
- **依赖**：SEC-01、现有 architecture/package 工件
- **目标**：在实现前发现模型架构层面的信任边界、权限、数据流和失效模式缺口。
- **步骤**：
  1. 从 architecture markdown 和 WorkPackage 提取组件、数据流、外部系统、角色。
  2. 建立 trust boundary、资产、攻击面、滥用场景。
  3. 检查认证、授权、租户隔离、密钥管理、日志脱敏、模型输出校验、工具权限。
  4. 输出 threat finding，并映射到具体工作包。
  5. 对阻断项自动生成 security-remediation 工作包，不直接修改原包。
- **验收**：同一输入结果稳定；每条风险可映射到组件/包；高危缺口能进入评审回路。

## SEC-06：动态安全验证隔离

- **优先级**：P1
- **依赖**：SEC-02、SEC-03、SEC-11（ScopeManifest 授权）、现有 integration 动态检查守卫、card-async-hitl（越权目标审批）、card-multi-tenancy（manifest 绑定租户）
- **目标**：在明确授权的测试环境执行动态验证，默认不接触真实外部目标。
- **步骤**：
  1. 动态模式必须同时满足 `allow_dynamic_execution=True` 和显式 argv 配置。
  2. 目标必须先通过 ScopeAuthorizer（SEC-11）：targets 白名单 + 私网/回环/组播/保留地址硬拒绝 + 授权时间窗。
  3. 使用 sandbox/container、资源限制、网络 deny-by-default、密钥剔除，作为签名缺失时的补偿控制。
  4. 超时、OOM、异常均转结构化 finding/error，不影响首脑进程。
  5. 记录命令 hash、环境策略、工具版本和退出码，不记录 secrets；每次执行前写不可变审计日志（绑 tenant_id/run_id/scan_id）。
- **验收**：默认不执行动态命令；shell=False；越权目标被拒绝；未授权目标即使列入 argv 也被 ScopeAuthorizer 拦截；失败可观察。

## SEC-07：安全修复工作包生成

- **优先级**：P1
- **依赖**：SEC-02、SEC-03、SEC-05
- **目标**：把安全发现转为可执行、可验收、可回滚的修复包。
- **步骤**：
  1. 按 finding 聚合，避免同一根因生成多个重复任务。
  2. 自动生成 `security-remediation-*` WorkPackage。
  3. 包含漏洞位置、最小修复范围、禁止扩大改动、回归测试要求。
  4. 修复包只写独立 workspace，禁止覆盖原包交付物。
  5. 通过现有 review loop 验收，未通过按责任归因返工。
- **验收**：每个 blocking finding 都有修复包或明确豁免；修复前后 diff 可追踪。

## SEC-08：安全回归基线

- **优先级**：P1
- **依赖**：SEC-02～SEC-07
- **目标**：防止后续 prompt、模型、工具或依赖升级重新引入已修复风险。
- **步骤**：
  1. 保存 finding 的规范化指纹：rule + path + normalized evidence + location。
  2. 新扫描与 baseline 对比，区分 new/fixed/regressed/accepted-risk。
  3. accepted-risk 必须带到期时间、审批人和理由。
  4. 在 CI 中执行静态安全回归，禁止依赖真实模型和网络。
  5. 将安全回归结果加入 `scripts/verify.py` 可选门禁。
- **验收**：新增高危失败；已修复风险不误报为新风险；基线变更可审计。

## SEC-09：安全可观测与数据合规

- **优先级**：P1
- **依赖**：现有 streaming、data_compliance、multi_tenancy
- **目标**：使安全过程可见、可回放、可按租户查询，同时避免敏感信息泄露。
- **步骤**：
  1. 发布 `security_scan_start/progress/finding/decision/end` 事件。
  2. finding evidence 写入前使用 DataMasker。
  3. 审计记录绑定 tenant_id、actor、run_id、scan_id。
  4. 高危 decision 进入 ApprovalQueue。
  5. 按租户 retention policy 清理普通扫描日志，保留不可变审计记录。
- **验收**：SSE 可消费；敏感 evidence 脱敏；租户不可读取他人报告；审计可导出。

## SEC-10：安全 API 与 CLI

- **优先级**：P1.5
- **依赖**：SEC-02、SEC-09、card-multi-tenancy（ApiKeyAuth/租户隔离）
- **目标**：提供稳定的本地/服务化入口，便于 Harness 逐卡实现。
- **建议接口**：

```text
POST /api/v1/security/scans
GET  /api/v1/security/scans/{scan_id}
GET  /api/v1/security/scans/{scan_id}/events
POST /api/v1/security/scans/{scan_id}/approve
GET  /api/v1/security/findings?run_id=...
POST /api/v1/security/baselines
```

- **CLI**：`agent-hive security scan --run-id ... --mode static [--format json|sarif] [--output -]`。
- **退出码契约**：`0`=allow；`2`=存在活跃 high/critical 发现（block）；`3`=扫描执行错误。
- **SARIF**：报告必须可导出 SARIF 2.1.0 与 JSON；manifest 中记录 SARIF 产物路径。
- **验收**：API Key/tenant 校验；无权限返回 403；路径、参数、模式严格校验；CLI 默认静态模式；`--format sarif --output -` 输出可被 CI 直接归档。

## SEC-11：动态验证授权清单（ScopeManifest）

- **优先级**：P0.5
- **依赖**：SEC-01、card-multi-tenancy、card-data-compliance（审计）
- **目标**：继承 DeepSec scope.json 的硬门禁思想——任何动态验证目标都必须通过白名单授权，私网与未授权目标即使写入参数也拒绝。
- **步骤**：
  1. 实现 `ScopeManifest`（targets/valid_from/valid_until/prohibited_cidrs/allowed_ports/signer/approver/reason）。
  2. `ScopeAuthorizer.authorize_target()`：目标不在 targets 白名单 → 拒绝；命中 prohibited_cidrs、回环、链路本地、组播、保留地址 → 拒绝（不可通过白名单绕过）；检查时间窗。
  3. 每次动态执行前 `write_audit_log()` 写不可变审计记录（target/command_hash/timestamp/signer/scope_id/reason）。
  4. manifest 绑 tenant_id，修改 manifest 必须走 HITL 审批并记录 approver。
  5. 未配置 manifest 时，dynamic 模式一律拒绝（fail-closed）。
- **验收**：白名单外目标被拒；私网 IP 即使在白名单中也被拒；过期 manifest 被拒；无 manifest 时动态模式不可用；审计日志完整且不可修改。

---

## 8. 安全策略矩阵

| 风险 | 默认动作 | 是否需 HITL | 是否允许自动修复 |
|---|---|---:|---:|
| 硬编码密钥 | block + 脱敏 | 是 | 否，先生成修复包 |
| `eval/exec` 外部输入 | block | 是 | 否 |
| 路径穿越 | block | 是 | 仅限低风险机械修复 |
| 未锁定依赖 | needs_approval | 是 | 可生成锁版本包 |
| 无法确认依赖是否存在 | partial/needs_approval | 是 | 否 |
| 低置信度架构缺口 | needs_approval | 是 | 否 |
| 测试 fixture 中的模拟密钥 | allow + 标记 | 否 | 否 |
| 动态测试失败 | failed/partial | 视策略 | 否 |
| 动态目标不在 ScopeManifest 白名单 | block（fail-closed） | 否（硬拒绝） | 否 |
| 动态目标命中私网/回环/组播 CIDR | block（不可绕过） | 否（硬拒绝） | 否 |
| ScopeManifest 过期或未配置 | block（动态模式禁用） | 需审批后补授权 | 否 |

---

## 9. 分批执行计划

### 批次 S1：安全底座（SEC-01 先行，随后并行）

> 契约是规则/依赖/威胁建模的共同类型基础，必须先落地；SEC-01 验收通过后 03/04/05 同批并行。

1. **先**：SEC-01 安全契约
2. **后**（并行）：SEC-03 静态扫描规则、SEC-04 依赖审计、SEC-05 威胁建模、SEC-11 ScopeManifest 授权

### 批次 S2：安全门禁（串行）

- SEC-02 安全网关与发布门禁
- SEC-06 动态验证隔离
- SEC-09 可观测与合规

### 批次 S3：修复闭环（并行）

- SEC-07 修复工作包
- SEC-08 安全回归基线
- SEC-10 安全 API/CLI

### 批次 S4：端到端验收

1. 生成含故意漏洞的 fixture 项目。
2. 运行 agent-hive 架构与分包流程。
3. 集成 staging，触发静态扫描。
4. 断言高危风险阻断，敏感证据已脱敏。
5. 通过审批或修复包解除阻断。
6. 重新扫描并比较 baseline。
7. 运行 `scripts/verify.py`。

---

## 10. 参考实现边界与许可证核查

DeepSec 研究报告基于公开仓库主分支的本地浅克隆与公开文档核对，记录了以下事实：其 Python 核心采用 Shield 的 L1 正则/熵、L2 AST、L3 opt-in LLM 分层，支持 JSON/SARIF/NDJSON 输出；Spear 是授权渗透引擎，包含 targets 白名单、私网拒绝和审计日志；其 dsh 插件通过子进程薄封装 CLI。上述内容只作为设计参考。

落地前必须执行：

1. 复核 [DeepSec LICENSE](https://github.com/Unclecheng-li/DeepSec/blob/main/LICENSE) 与仓库版权归属差异（LICENSE 文件写 `Copyright (c) 2026 VibeGuard contributors`，README 页脚写 "MIT © 2026 DeepSec contributors"）；若复用必须以 LICENSE 文件为准并原样保留版权行与 MIT 通知，将审查结论记录到 ADR。
2. 不复制 DeepSec 的源代码、规则文件、提示词、技能包正文（含 warstories 引用外部目标的内容）或未确认可再分发的资产。
3. **Spear 的 VulnClaw 来源需单独核实**：其 MIT 版权/原作者/原始仓库未经确认，属于未确认许可证内容，不得复用其引擎代码或规则。
4. 若直接运行 `deepsec` CLI 或 dsh 插件，使用进程隔离、超时、网络 allowlist、密钥剔除和明确授权范围；默认只接入 Shield 静态扫描。
5. **Python-first 适配器契约**（推荐）：子进程调用 `deepsec shield scan --format sarif --output -`（或 `--format json`），解析退出码（`2`=存在活跃 high/critical），通过环境变量约束产物目录（如 `DEEPSEC_RUNS_DIR`）；明确**不采用** action.yml 的 Node/TS 扫描路径（仍是 VibeGuard 品牌、与 Python 核心为两套实现，行为可能不一致）。
6. **优雅降级**：未安装 `deepsec` 时适配器返回 `unavailable`，自动降级为内置纯 Python 静态规则，不影响主流程。
7. 对 DeepSec 文档中已发现的 config（toml vs yaml）、签名（可选 vs 强签名）、MCP server 说法、action 品牌和测试数字漂移，以代码实际行为为准，并在适配器测试中锁定版本。
8. **不依赖 dsh developer preview 契约**：SEC-10 的 API/CLI 自持稳定接口，DeepSec 的 dsh 插件只作为可选参考，不作为硬依赖。

## 11. 测试工作包

### SEC-TEST-01：安全规则单测

覆盖：规则命中、路径行号、证据脱敏、置信度、误报标记、空目录和非法路径。

### SEC-TEST-02：策略门禁测试

覆盖：critical/high block、低置信度 HITL、accepted-risk、partial、原子 dist 保留。

### SEC-TEST-03：安全回归测试

覆盖：new/fixed/regressed/accepted-risk 四种状态和基线指纹稳定性。

### SEC-TEST-04：租户与审计集成测试

覆盖：报告隔离、API Key、SSE、审计导出、retention cleanup、DataMasker。

### SEC-TEST-05：动态执行守卫与 ScopeAuthorizer 测试

覆盖：默认禁用、argv 类型、shell=False、网络权限、超时、密钥剔除、targets 白名单、私网/回环/组播/保留地址硬拒绝、时间窗过期、无 manifest fail-closed、审计日志完整性。

### SEC-TEST-06：SARIF 与退出码测试

覆盖：`to_sarif()` 符合 SARIF 2.1.0、`to_json()` 往返一致、CLI 退出码 0/2/3 契约、manifest 记录 SARIF 产物路径。

### SEC-TEST-07：端到端 fixture 测试

使用本地 fixture，不访问网络、不调用真实模型，证明“生成架构 → 集成 → 扫描 → 阻断/审批 → 修复 → 回归”。

---

## 12. 终验标准

- [ ] 任何安全 finding 都能映射到 scan/run/tenant 和证据。
- [ ] critical/high 高置信度发现无法进入 success dist。
- [ ] 低置信度风险不会静默放行，进入 HITL 或 partial。
- [ ] 静态扫描默认无网络、无 shell、无真实目标副作用。
- [ ] 动态验证目标必须通过 ScopeManifest 白名单，私网/回环/组播地址不可绕过；无 manifest 时动态模式禁用。
- [ ] 报告支持 SARIF 2.1.0 与 JSON 导出，CLI 退出码契约（0/2/3）生效。
- [ ] 敏感证据在日志、SSE、manifest、审计导出中均已脱敏。
- [ ] 安全报告按租户隔离，API/CLI 权限校验有效。
- [ ] 修复包遵循现有依赖调度、评审、返工、熔断和集成守卫。
- [ ] baseline 能识别新增回归，accepted-risk 有审批和过期时间。
- [ ] 端到端 fixture 测试通过，且不依赖真实模型或网络。
- [ ] DeepSec 仅作为设计参考来源；第三方代码许可证审查记录完整（含 LICENSE 版权归属分歧与 VulnClaw 出处核实）；未安装 deepsec 时优雅降级为内置规则。

---

## 13. 未来展望

### F1：规则与模型双层审计

短期使用 AST、依赖元数据、策略规则；中期增加受控 LLM-as-judge，要求输出结构化 finding，并由确定性策略最终裁决。

### F2：安全技能包生态

参考 Spear 的技能包思想，定义只读 reconnaissance、配置审计、API contract audit、prompt injection test 等技能包。每个技能包必须声明权限、网络能力、成本、证据格式和停止条件。

### F3：企业安全平台接入

适配内部漏洞库、依赖镜像、审批平台、SIEM/SOC；所有外部适配器保持接口隔离，默认关闭，按租户启用。

### F4：分布式安全扫描

利用 distributed_engine 将不同扫描器分发到隔离 worker，报告通过 SharedStateStore 汇聚；对扫描器设置 CPU、内存、时间和 token 配额。

### F5：风险驱动的 Agent 自优化

将安全 finding 与 prompt 版本、工具调用、模型 fallback、返工率关联，回答“哪个 prompt 更容易生成危险代码”“哪个工具组合增加风险”。

### F6：安全能力度量

建立指标：高危发现率、误报率、修复平均时长、回归率、阻断逃逸率、扫描成本、审批等待时长、租户隔离违规数。

### F7：可验证的安全声明

未来输出“已执行的检查范围、工具版本、规则版本、未覆盖区域和风险接受记录”，而不是笼统宣称“安全”或“符合某认证”。
