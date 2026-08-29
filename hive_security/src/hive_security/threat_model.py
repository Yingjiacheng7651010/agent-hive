"""AI 架构安全验证威胁模型库。

基于 STRIDE（伪装/篡改/抵赖/信息泄露/拒绝服务/权限提升）扩展 AI 三类
（幻觉 / 安全护栏 / AI 模式缺陷），提供：

- ``ThreatCategory`` / ``Threat`` / ``ThreatCatalog``：威胁目录数据模型
- ``load_threat_catalog()``：加载并校验内置威胁目录
- ``ValidationPolicy`` / ``apply_policy()``：按策略对验证报告做通过/警告/失败裁决
- ``SEVERITY_RANK``：严重度排序常量（critical=4 > high=3 > medium=2 > low=1）

纯标准库实现，不依赖 langchain / pydantic。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Literal

__all__ = [
    "SEVERITY_RANK",
    "THREAT_CATALOG_VERSION",
    "ThreatCategory",
    "Threat",
    "Finding",
    "ThreatCatalog",
    "ValidationPolicy",
    "load_threat_catalog",
    "apply_policy",
]

# 严重度排序常量：数值越大越严重。
SEVERITY_RANK: dict[str, int] = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}

# 内置威胁目录版本。
THREAT_CATALOG_VERSION = "1.0.0"

_Severity = Literal["critical", "high", "medium", "low"]


class ThreatCategory(str, Enum):
    """威胁类别：STRIDE 六类 + AI 三类。"""

    SPOOFING = "spoofing"
    TAMPERING = "tampering"
    REPUDIATION = "repudiation"
    INFORMATION_DISCLOSURE = "information_disclosure"
    DENIAL_OF_SERVICE = "denial_of_service"
    ELEVATION_OF_PRIVILEGE = "elevation_of_privilege"
    AI_HALLUCINATION = "ai_hallucination"
    AI_SAFEGUARD = "ai_safeguard"
    AI_PATTERN = "ai_pattern"


@dataclass(frozen=True)
class Threat:
    """单条威胁条目。"""

    id: str
    category: ThreatCategory
    name: str
    description: str
    affected_asset: str
    control: str
    remediation: str
    severity: _Severity
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class ThreatCatalog:
    """威胁目录：版本 + 威胁条目集合，支持按类别过滤与关键词匹配。"""

    version: str
    threats: tuple[Threat, ...]

    def by_category(self, category) -> list[Threat]:
        """按类别过滤；category 接受 ThreatCategory 或其字符串值（如 "spoofing"）。"""
        if not isinstance(category, ThreatCategory):
            category = ThreatCategory(category)
        return [t for t in self.threats if t.category is category]

    def match_keywords(self, text: str) -> list[Threat]:
        """text 小写后，任一 keyword 作为子串命中即返回该威胁。

        保持目录顺序且每个威胁至多返回一次；大小写不敏感（中文不受影响）。
        """
        lowered = text.lower()
        matched: list[Threat] = []
        seen: set[str] = set()
        for threat in self.threats:
            if threat.id in seen:
                continue
            for keyword in threat.keywords:
                if keyword.lower() in lowered:
                    matched.append(threat)
                    seen.add(threat.id)
                    break
        return matched


@dataclass(frozen=True)
class Finding:
    """单条验证发现：引用威胁条目 id，并携带严重度与说明。"""

    threat_id: str
    severity: _Severity
    message: str = ""


@dataclass(frozen=True)
class ValidationPolicy:
    """验证策略：决定 apply_policy 的裁决阈值与限制。"""

    fail_on_severity: str = "high"
    max_warnings: int = 10
    llm_enabled: bool = True
    llm_verdict_requires_rule: bool = True
    exclusions: tuple[str, ...] = ()
    max_findings_per_threat: int = 5

    def __post_init__(self):
        # 构造时即校验，非法阈值（放宽到低于 high）直接拒绝。
        self.validate_fail_on_severity(self.fail_on_severity)

    @staticmethod
    def validate_fail_on_severity(value: str) -> bool:
        """校验 fail_on_severity：仅允许 "critical" 或 "high"。

        低于 high 的放宽值会削弱验证强度，一律拒绝并抛 ValueError 说明原因。
        """
        allowed = ("critical", "high")
        if value not in allowed:
            raise ValueError(
                f"fail_on_severity 仅允许 {'/'.join(allowed)}（当前为 {value!r}），"
                "低于 high 的放宽值会削弱威胁模型验证强度，必须拒绝"
            )
        return True


def _iter_findings(report) -> list:
    """取出报告中的发现列表：report 可为对象（.findings）或字典（"findings" 键）。"""
    if isinstance(report, dict):
        return list(report.get("findings") or [])
    return list(getattr(report, "findings") or [])


def _iter_warnings(report) -> list:
    """取出报告中的警告列表（可选）：report 可为对象（.warnings）或字典（"warnings" 键）。"""
    if isinstance(report, dict):
        return list(report.get("warnings") or [])
    return list(getattr(report, "warnings", None) or [])


def _severity_of(finding) -> str:
    if isinstance(finding, dict):
        return finding["severity"]
    return finding.severity


def _threat_id_of(finding) -> str | None:
    if isinstance(finding, dict):
        return finding.get("threat_id")
    return getattr(finding, "threat_id", None)


def apply_policy(report, policy: ValidationPolicy) -> str:
    """按策略对验证报告裁决，返回 "pass" | "pass_with_warnings" | "fail"。

    report 支持两类形态：
    - 对象：暴露 ``.findings``（必选）与 ``.warnings``（可选）属性；
    - 字典：``{"findings": [...], "warnings": [...]}``。

    finding 可为对象（含 ``.severity`` 与可选 ``.threat_id``）或字典
    （``{"severity": ..., "threat_id": ...}``）。

    裁决规则：
    1. 按 policy.exclusions（threat_id）过滤后，存在 severity 排名
       >= fail_on_severity 的 finding → "fail"；
    2. warning 级发现（低于阈值的 finding 与 report.warnings 合计）超过
       max_warnings → "fail"；
    3. 仍存在任何发现 → "pass_with_warnings"；否则 → "pass"。
    """
    fail_rank = SEVERITY_RANK[policy.fail_on_severity]
    excluded = set(policy.exclusions)

    findings = [
        f for f in _iter_findings(report) if _threat_id_of(f) not in excluded
    ]
    warnings = list(_iter_warnings(report))

    for finding in findings:
        if SEVERITY_RANK.get(_severity_of(finding), 0) >= fail_rank:
            return "fail"

    warning_count = (
        sum(
            1 for f in findings
            if SEVERITY_RANK.get(_severity_of(f), 0) < fail_rank
        )
        + len(warnings)
    )
    if warning_count > policy.max_warnings:
        return "fail"

    if findings or warnings:
        return "pass_with_warnings"
    return "pass"


# ---------------------------------------------------------------------------
# 内置威胁目录
# ---------------------------------------------------------------------------

_BUILTIN_THREATS: tuple[Threat, ...] = (
    Threat(
        id="T-SPOOF-1",
        category=ThreatCategory.SPOOFING,
        name="认证/身份缺失",
        description="系统未对调用方做身份认证或认证强度不足，任何人可伪装成合法用户或系统组件发起调用。",
        affected_asset="Agent 入口 API / 身份令牌",
        control="强制认证：API Key、OAuth2、mTLS 等至少一种，并对每次调用校验身份。",
        remediation="为所有入口接入统一认证中间件，禁止匿名调用；内部组件间启用服务身份（mTLS）。",
        severity="high",
        keywords=("认证", "鉴权", "身份", "登录", "令牌"),
    ),
    Threat(
        id="T-SPOOF-2",
        category=ThreatCategory.SPOOFING,
        name="多租户隔离缺失",
        description="多租户场景下租户数据/会话/资源未隔离，租户 A 可伪装或越界访问租户 B 的数据与资源。",
        affected_asset="租户数据 / 会话存储",
        control="租户标识贯穿数据与资源，按租户做数据隔离与访问控制。",
        remediation="引入租户 ID 隔离键、每租户独立密钥与配额，并把隔离校验纳入安全测试。",
        severity="high",
        keywords=("租户隔离", "多租户", "租户"),
    ),
    Threat(
        id="T-TAMP-1",
        category=ThreatCategory.TAMPERING,
        name="外部输入无注入防护",
        description="外部输入未经校验/转义直接拼入提示词、SQL 或命令，可被提示注入、SQL 注入等攻击篡改系统行为。",
        affected_asset="提示词上下文 / 数据库 / 外部命令",
        control="输入校验、参数化查询、提示词边界标记与注入检测。",
        remediation="全链路输入校验并白名单化；对外部内容加边界标记并限制其指令权限。",
        severity="high",
        keywords=("注入", "sql注入", "提示注入", "输入校验", "校验"),
    ),
    Threat(
        id="T-TAMP-2",
        category=ThreatCategory.TAMPERING,
        name="工具执行无白名单/最小权限",
        description="Agent 可调用任意工具或命令，且执行环境权限过大，攻击者可通过工具链篡改系统状态。",
        affected_asset="工具注册表 / 执行环境",
        control="工具白名单 + 最小权限运行 + 高危执行前审批。",
        remediation="收敛工具列表为白名单，以沙箱/最小权限用户运行，高危操作要求人工确认。",
        severity="high",
        keywords=("白名单", "工具白名单", "命令执行", "shell"),
    ),
    Threat(
        id="T-REPU-1",
        category=ThreatCategory.REPUDIATION,
        name="无审计日志",
        description="系统不记录关键操作日志，出现安全事件时无法溯源与追责，操作方可以抵赖。",
        affected_asset="审计日志",
        control="关键操作写入不可篡改的审计日志，并支持查询与导出。",
        remediation="启用审计日志并做写保护，定期导出归档用于合规审计与溯源。",
        severity="high",
        keywords=("审计", "审计日志", "日志", "溯源", "追责"),
    ),
    Threat(
        id="T-DISC-1",
        category=ThreatCategory.INFORMATION_DISCLOSURE,
        name="密钥管理/脱敏缺失",
        description="密钥硬编码或明文存储，敏感数据未脱敏即输出或落盘，导致信息泄露。",
        affected_asset="密钥存储 / 敏感输出",
        control="密钥托管（KMS/环境变量）+ 敏感数据脱敏。",
        remediation="密钥统一托管并定期轮换，输出与日志链路接入脱敏规则。",
        severity="high",
        keywords=("密钥", "脱敏", "敏感信息", "泄露", "机密"),
    ),
    Threat(
        id="T-DISC-2",
        category=ThreatCategory.INFORMATION_DISCLOSURE,
        name="数据合规缺失",
        description="未识别或未遵守数据合规要求（个人信息、GDPR 等），数据处理链路违规。",
        affected_asset="个人数据 / 合规数据",
        control="数据分类分级 + 合规策略（保留、导出、删除）。",
        remediation="建立数据合规策略，落地脱敏、保留期与数据可删除能力。",
        severity="high",
        keywords=("合规", "数据合规", "隐私", "个人信息", "gdpr"),
    ),
    Threat(
        id="T-DOS-1",
        category=ThreatCategory.DENIAL_OF_SERVICE,
        name="无限流/配额",
        description="Agent 调用无速率限制、无预算/配额控制，可被高频请求或失控循环拖垮（资源与成本耗尽）。",
        affected_asset="推理服务 / 预算 / 计算资源",
        control="限流、配额、预算上限与超时重试策略。",
        remediation="接入限流与配额控制，设置硬性预算上限与重试退避。",
        severity="medium",
        keywords=("限流", "配额", "预算", "重试", "超时"),
    ),
    Threat(
        id="T-ELEV-1",
        category=ThreatCategory.ELEVATION_OF_PRIVILEGE,
        name="无最小权限/授权",
        description="未按最小权限授权，普通角色可执行管理员操作，存在权限提升风险。",
        affected_asset="角色权限模型",
        control="RBAC/ABAC + 最小权限 + 敏感操作二次授权。",
        remediation="收敛角色权限到最小集，敏感操作强制二次授权并记录审计。",
        severity="high",
        keywords=("最小权限", "权限提升", "授权", "越权"),
    ),
    Threat(
        id="T-HALL-1",
        category=ThreatCategory.AI_HALLUCINATION,
        name="幻觉引用",
        description="模型可能编造不存在的引用、数据或事实（幻觉），误导下游决策。",
        affected_asset="模型输出 / 引用内容",
        control="输出事实性校验 + 引用溯源。",
        remediation="对关键输出做检索佐证与引用校验，高风险场景要求人工复核。",
        severity="high",
        keywords=("幻觉", "引用", "编造", "虚构", "事实性"),
    ),
    Threat(
        id="T-SAFE-1",
        category=ThreatCategory.AI_SAFEGUARD,
        name="无输入/输出守卫、无降级",
        description="缺少输入/输出守卫（内容安全、格式约束）与故障降级机制，异常输入或输出可直接冲击下游。",
        affected_asset="输入/输出链路",
        control="输入输出守卫（内容审核/格式校验）+ 降级与熔断。",
        remediation="部署输入/输出守卫，配置降级预案与熔断器。",
        severity="high",
        keywords=("守卫", "输入守卫", "输出守卫", "降级", "护栏", "安全阀"),
    ),
    Threat(
        id="T-PATT-1",
        category=ThreatCategory.AI_PATTERN,
        name="循环依赖/单点/risks 空缺",
        description="架构存在循环依赖或单点故障，或风险清单（risks）空缺，隐患难以被发现与消解。",
        affected_asset="架构图 / 风险清单",
        control="架构评审校验循环依赖与单点，强制维护 risks 清单。",
        remediation="静态检查依赖图，消除循环与单点；补齐 risks 字段并纳入评审。",
        severity="medium",
        keywords=("循环依赖", "单点", "risks", "依赖", "风险清单"),
    ),
)


def load_threat_catalog(extension_path: str | None = None) -> ThreatCatalog:
    """加载内置威胁目录（可选合并外部扩展包），并校验完整性。

    - ``extension_path``：JSON 文件路径，形如
      ``{"version": "企业威胁目录 1.0", "threats": [{...Threat 字段...}]}``。
    - 扩展条目 id 与内置目录冲突（或扩展包内部重复）→ ValueError 拒绝加载，
      防止扩展包静默覆盖内置威胁（投毒防护）。
    - 完整性校验：9 个类别各 ≥1 条（合并后仍须满足）、id 唯一、严重度合法。
    """
    threats = list(_BUILTIN_THREATS)
    version = THREAT_CATALOG_VERSION
    if extension_path:
        import json

        raw = json.loads(Path(extension_path).read_text(encoding="utf-8"))
        ext_threats_raw = raw.get("threats") or []
        ext_threats: list[Threat] = []
        for item in ext_threats_raw:
            try:
                ext_threats.append(Threat(
                    id=item["id"],
                    category=ThreatCategory(item["category"]),
                    name=item.get("name", item["id"]),
                    description=item.get("description", ""),
                    affected_asset=item.get("affected_asset", ""),
                    control=item.get("control", ""),
                    remediation=item.get("remediation", ""),
                    severity=item.get("severity", "medium"),
                    keywords=tuple(item.get("keywords") or []),
                ))
            except (KeyError, ValueError) as exc:
                raise ValueError(f"扩展威胁条目非法：{item!r}（{exc}）") from exc
        builtin_ids = {t.id for t in threats}
        for t in ext_threats:
            if t.id in builtin_ids:
                raise ValueError(f"扩展威胁 id 与内置目录冲突：{t.id}")
        if len({t.id for t in ext_threats}) != len(ext_threats):
            raise ValueError("扩展威胁目录内部存在重复 id")
        threats.extend(ext_threats)
        if ext_threats:
            version = f"{THREAT_CATALOG_VERSION}+{raw.get('version', 'extension')}"

    catalog_threats = tuple(threats)
    _validate_catalog(catalog_threats)
    return ThreatCatalog(version=version, threats=catalog_threats)


def _validate_catalog(threats: tuple[Threat, ...]) -> None:
    """校验威胁目录完整性，失败时抛 ValueError。"""
    ids = [t.id for t in threats]
    if len(ids) != len(set(ids)):
        seen: set[str] = set()
        dupes = sorted({tid for tid in ids if tid in seen or seen.add(tid)})
        raise ValueError(f"威胁目录存在重复 id: {dupes}")

    present = {t.category for t in threats}
    missing = [c.value for c in ThreatCategory if c not in present]
    if missing:
        raise ValueError(f"威胁目录缺失类别: {missing}")

    invalid = [t.id for t in threats if t.severity not in SEVERITY_RANK]
    if invalid:
        raise ValueError(f"威胁目录存在非法严重度: {invalid}")
