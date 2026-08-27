"""AI 架构安全验证规则引擎（Shield 式确定性检查器）。

设计说明
--------
本模块是「AI 生成架构安全验证」的确定性规则引擎：只消费结构化架构
（``architecture_object``，与 ``contract_spec.ArchitecturePlan`` 对齐），
**不解析 markdown**，避免解析漂移；输出结构化 ``SecurityFinding`` /
``SecurityReport``，供审批关口一（approve_architecture）展示与裁决。

核心设计约束（纯标准库深模块，不依赖 langchain/pydantic）：
- **纯函数**：``validate_architecture`` 同输入同输出、无 IO、无随机、无墙钟。
  ``SecurityReport.generated_at`` 固定为纪元时间戳（确定性），由集成层在
  落盘/展示时覆写真实时间。
- **不可信数据处理**（威胁 T-ENG-6）：``interfaces`` / ``depends_on`` 等引用字段
  只做字符串模式匹配，**绝不按引用值做任何 IO**。
- **输出守卫**（威胁 T-ENG-5）：证据/整改文本一律截断（200 字符）+ markdown 转义
  （``|``、反引号、换行→空格）；SARIF 输出为合法 JSON 且 evidence 脱敏截断。
- **LLM 发现不可单独判死**（威胁 T-ENG-2）：``policy.llm_verdict_requires_rule``
  为真时，仅 LLM 提出且与规则发现无共识的 critical/high 发现降级为 medium 并附注。
- **单一事实源**：循环依赖检测复用 ``scheduler.validate_dependency_graph``，
  不重复实现环检测算法；敏感模式复用 ``data_compliance.DEFAULT_MASK_RULES``。
- **确定性 id**：``F-{threat_id}-{n:03d}``，按每威胁出现次序编号，同输入必同输出。

依赖：仅标准库（dataclasses/re/json/pathlib）+ 项目内契约模块
``agent_hive.threat_model``（ThreatCatalog/ValidationPolicy/apply_policy）、
``agent_hive.scheduler``（validate_dependency_graph）、
``agent_hive.data_compliance``（DEFAULT_MASK_RULES）。
"""
from __future__ import annotations

import dataclasses
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from agent_hive.data_compliance import DEFAULT_MASK_RULES
from agent_hive.scheduler import validate_dependency_graph
from agent_hive.threat_model import (
    ThreatCatalog,
    ValidationPolicy,
    apply_policy,
    load_threat_catalog,
)

__all__ = [
    "SecurityFinding",
    "SecurityReport",
    "check_hallucinated_references",
    "check_dependency_cycle",
    "check_missing_security_controls",
    "check_architectural_anti_patterns",
    "merge_findings",
    "validate_architecture",
    "render_security_report_md",
    "check_dist_artifacts",
]

_SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}

# 纯函数不读墙钟：generated_at 固定为纪元时间戳（确定性），集成层落盘时可覆写真实时间。
_GENERATED_AT_EPOCH = "1970-01-01T00:00:00+00:00"

# 幻觉引用：interfaces 中「引用:/调用:/依赖:」后跟的名称，或反引号包裹的名称。
_REF_PREFIX_RE = re.compile(r"(?:引用|调用|依赖)[:：]\s*([^\s，,；;、。:：]+)")
_BACKTICK_RE = re.compile(r"`([^`]+)`")

# 缺失控制检查：从 threat.control 抽取中文关键词（按常见标点/分隔符切分）。
_CONTROL_SPLIT_RE = re.compile(r"[/，。、；;：:\s|（）()\[\]【】]+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")

# dist 静态扫描：敏感文件名与危险调用模式。
_SENSITIVE_FILENAME_RE = re.compile(r"(\.env$|\.pem$|\.key$|id_rsa)", re.IGNORECASE)
_DANGEROUS_CALL_RE = re.compile(r"shell\s*=\s*True|os\.system\s*\(|\beval\s*\(|\bexec\s*\(")
_MAX_TEXT_FILE_BYTES = 1024 * 1024

_SEVERITY_ORDER: tuple[str, ...] = ("critical", "high", "medium", "low")


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


@dataclass
class SecurityFinding:
    """一条安全发现（规则引擎或 LLM 语义验证产出）。"""

    id: str
    module: str
    threat_id: str
    category: str
    severity: Literal["critical", "high", "medium", "low"]
    evidence: str
    remediation: str
    source: Literal["rule", "llm"] = "rule"


@dataclass
class SecurityReport:
    """架构安全验证报告（确定性渲染与裁决载体）。"""

    verdict: str
    findings: list[SecurityFinding]
    checks: list[str]
    summary: str
    policy_version: str
    generated_at: str

    def to_dict(self) -> dict:
        """确定性序列化为 dict（findings 按字段顺序展开）。"""
        return {
            "verdict": self.verdict,
            "findings": [dataclasses.asdict(f) for f in self.findings],
            "checks": list(self.checks),
            "summary": self.summary,
            "policy_version": self.policy_version,
            "generated_at": self.generated_at,
        }

    def to_json(self) -> str:
        """确定性序列化为 JSON 字符串（utf-8，不转义中文）。"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def to_sarif(self) -> str:
        """输出 SARIF 2.1.0 最小有效结构（合法 JSON，evidence 脱敏截断）。"""
        results = []
        for f in self.findings:
            results.append({
                "ruleId": f.threat_id,
                "level": _sarif_level(f.severity),
                "message": {"text": _truncate(_mask_sensitive(f.evidence), 200)},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": _sarif_uri(f.module)},
                        "region": {"startLine": 1, "startColumn": 1},
                    },
                }],
            })
        sarif = {
            "$schema": (
                "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/"
                "master/Schemata/sarif-schema-2.1.0.json"
            ),
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "agent-hive arch_security",
                        "version": "0.1.0",
                        "informationUri": "https://github.com/pikachu/agent-hive",
                    },
                },
                "results": results,
            }],
        }
        return json.dumps(sarif, ensure_ascii=False, indent=2)

    def exit_code(self) -> int:
        """verdict == "fail" → 2（阻断），否则 0。"""
        return 2 if self.verdict == "fail" else 0


# ---------------------------------------------------------------------------
# 内部工具（确定性辅助）
# ---------------------------------------------------------------------------


def _assign_ids(findings: list[SecurityFinding]) -> list[SecurityFinding]:
    """按每威胁出现次序赋确定性 id：F-{threat_id}-{n:03d}。"""
    counters: dict[str, int] = {}
    out: list[SecurityFinding] = []
    for f in findings:
        n = counters.get(f.threat_id, 0) + 1
        counters[f.threat_id] = n
        out.append(dataclasses.replace(f, id=f"F-{f.threat_id}-{n:03d}"))
    return out


def _truncate(text: str, limit: int) -> str:
    text = str(text)
    return text if len(text) <= limit else text[:limit] + "…"


def _mask_sensitive(text: str) -> str:
    """复用 data_compliance 脱敏模式对文本脱敏（确定性）。"""
    masked = text
    for rule in DEFAULT_MASK_RULES:
        masked = re.sub(rule.pattern, rule.replacement, masked)
    return masked


def _sarif_level(severity: str) -> str:
    return {"critical": "error", "high": "error", "medium": "warning", "low": "note"}.get(severity, "note")


def _sarif_uri(module: str) -> str:
    m = module or "overview"
    if m == "*":
        return "architecture/overview.json"
    if re.search(r"\.[A-Za-z0-9]{1,8}$", m):
        return m  # 文件路径型 module（dist 扫描产出）直接用相对 URI
    return f"architecture/{m}"


def _category_value(category: object) -> str:
    return getattr(category, "value", None) or str(category)


def _first_hit_keyword(keywords: tuple[str, ...], text: str) -> str:
    for kw in keywords:
        if kw and kw in text:
            return kw
    return keywords[0] if keywords else "(未知关键词)"


def _control_keywords(control: str) -> list[str]:
    """从 control 文本抽取中文关键词（去首尾非中文字符，防“(认证)”类括号残留）。"""
    tokens: list[str] = []
    for seg in _CONTROL_SPLIT_RE.split(control or ""):
        token = re.sub(rf"^[^\u4e00-\u9fff]+|[^\u4e00-\u9fff]+$", "", seg)
        if token:
            tokens.append(token)
    return tokens


def _threat_severity(catalog: ThreatCatalog, threat_id: str, fallback: str) -> str:
    """从目录取威胁 severity，缺失/非法时回退。"""
    for t in catalog.threats:
        if getattr(t, "id", None) == threat_id and getattr(t, "severity", None) in _SEVERITY_RANK:
            return t.severity
    return fallback


# ---------------------------------------------------------------------------
# 规则检查器（Shield 式，全部纯函数）
# ---------------------------------------------------------------------------


def check_hallucinated_references(architecture: dict) -> list[SecurityFinding]:
    """幻觉引用检查：interfaces 中出现「引用:/调用:/依赖:」或反引号包裹的未定义名称。

    只做字符串模式匹配，绝不按引用值做任何 IO（威胁 T-ENG-6）。
    未定义 = 名称既不在模块名集合、也不在接口名集合中。
    向后兼容：空架构对象（``{}``）直接返回零 finding，不抛异常。
    """
    if not architecture:
        return []
    modules = [m for m in (architecture.get("modules") or []) if isinstance(m, dict)]
    names = {m.get("name") for m in modules}
    interfaces: set[str] = set()
    for m in modules:
        for iface in m.get("interfaces") or []:
            interfaces.add(iface)
    defined = names | interfaces

    findings: list[SecurityFinding] = []
    for m in modules:
        module_name = m.get("name") or "(未命名模块)"
        for iface in m.get("interfaces") or []:
            iface = str(iface)
            # 前缀引用（引用:/调用:/依赖:）
            for match in _REF_PREFIX_RE.finditer(iface):
                ref = match.group(1)
                if ref.startswith("`"):
                    continue  # 反引号包裹的名称交给反引号规则处理，避免重复
                if ref and ref not in defined:
                    findings.append(_hallucination_finding(module_name, iface, ref))
            # 反引号包裹的名称
            for match in _BACKTICK_RE.finditer(iface):
                ref = match.group(1)
                if ref and ref not in defined:
                    findings.append(_hallucination_finding(module_name, iface, ref))
    return _assign_ids(findings)


def _hallucination_finding(module_name: str, iface: str, ref: str) -> SecurityFinding:
    return SecurityFinding(
        id="",
        module=module_name,
        threat_id="T-HALL-1",
        category="ai_hallucination",
        severity="high",
        evidence=f"模块「{module_name}」接口「{iface}」引用了未定义名称「{ref}」",
        remediation=(
            f"修正幻觉引用：将「{ref}」补充为真实模块/接口，或删除该引用；"
            "接口契约即安全契约，悬空引用会传染全部下游工作包。"
        ),
        source="rule",
    )


def check_dependency_cycle(architecture: dict) -> list[SecurityFinding]:
    """循环依赖检查：投影 modules → packages，复用 scheduler.validate_dependency_graph。

    环检测算法不重复实现（单一事实源）；仅当 ValueError 含「环」时产出 T-PATT-1，
    其他非法图（空/重复 id/悬空依赖）不在此处报，避免与其它检查器重复。
    向后兼容：空架构对象（``{}``）直接返回零 finding，不抛异常。
    """
    if not architecture:
        return []
    modules = [m for m in (architecture.get("modules") or []) if isinstance(m, dict)]
    packages = [
        {"id": m.get("name"), "depends_on": list(m.get("depends_on") or [])}
        for m in modules
        if m.get("name")
    ]
    try:
        validate_dependency_graph(packages)
    except ValueError as exc:
        message = str(exc)
        if "环" in message:
            return _assign_ids([
                SecurityFinding(
                    id="",
                    module="*",
                    threat_id="T-PATT-1",
                    category="ai_pattern",
                    severity="high",
                    evidence=f"检测到循环依赖：{message}",
                    remediation="打破循环依赖：调整模块依赖方向或拆分环形模块，保证依赖为 DAG。",
                    source="rule",
                )
            ])
    return []


def check_missing_security_controls(architecture: dict, catalog: ThreatCatalog) -> list[SecurityFinding]:
    """缺失安全控制检查：模块文本命中威胁关键词，但缺少该威胁的 control 关键词。

    对每个模块的 responsibility+interfaces 合并文本跑 ``catalog.match_keywords``：
    命中某威胁（其任一 keywords 出现）但文本不含该威胁 control 中抽取的中文关键词，
    即判定缺失对应安全控制；severity 取威胁 severity。

    控制存在判定（二选一，防目录用整句描述 control 时的误报）：
    1. 任一 control 关键词（标点切分的中文片段）出现在模块文本；
    2. 任一命中关键词本身属于 control 词汇（命中词出现在 control 字符串中）——
       例如 control「强制认证：…并对每次调用校验身份」中命中词「认证/身份」，
       说明模块已使用控制词汇，视为已设计该控制。
    向后兼容：空架构对象（``{}``）直接返回零 finding，不抛异常。
    """
    if not architecture:
        return []
    findings: list[SecurityFinding] = []
    for m in (architecture.get("modules") or []):
        if not isinstance(m, dict):
            continue
        module_name = m.get("name") or "(未命名模块)"
        text = " ".join([
            str(m.get("responsibility") or ""),
            *(str(i) for i in (m.get("interfaces") or [])),
        ])
        for threat in catalog.match_keywords(text):
            control = getattr(threat, "control", "") or ""
            control_tokens = _control_keywords(control)
            hit_keywords = [k for k in (getattr(threat, "keywords", ()) or ()) if k and k in text]
            control_present = any(tok in text for tok in control_tokens) or any(
                k in control for k in hit_keywords
            )
            if control_present:
                continue  # 已设计对应控制
            hit = hit_keywords[0] if hit_keywords else _first_hit_keyword(getattr(threat, "keywords", ()) or (), text)
            severity = threat.severity if threat.severity in _SEVERITY_RANK else "medium"
            findings.append(SecurityFinding(
                id="",
                module=module_name,
                threat_id=threat.id,
                category=_category_value(threat.category),
                severity=severity,
                evidence=(
                    f"模块「{module_name}」命中威胁 {threat.id} 的关键词「{hit}」，"
                    f"但缺少其控制设计（{threat.control}）"
                ),
                remediation=threat.remediation,
                source="rule",
            ))
    return _assign_ids(findings)


def check_architectural_anti_patterns(architecture: dict, catalog: ThreatCatalog) -> list[SecurityFinding]:
    """架构反模式检查：risks 空缺 / 模块无 owner / 模块数越界 / 无失败处理却含执行类接口。

    - ``risks`` 为空 → T-PATT-1
    - 模块缺少 ``owner_role`` → T-PATT-1（每模块一条）
    - 模块数 > 30 或 == 0 → T-PATT-1
    - overview 无「失败处理/降级/守卫」且模块接口含「执行/命令」→ T-SAFE-1

    向后兼容：空架构对象（``{}``）直接返回零 finding（graph 层已对空对象做跳过，
    引擎本身也对空 dict 保持安静），不抛异常；显式给出 ``modules``/``risks`` 键的
    真实架构对象（即便值为空列表）仍按上述规则检查。
    """
    if not architecture:
        return []
    findings: list[SecurityFinding] = []
    modules = [m for m in (architecture.get("modules") or []) if isinstance(m, dict)]
    patt_severity = _threat_severity(catalog, "T-PATT-1", "high")
    safe_severity = _threat_severity(catalog, "T-SAFE-1", "high")

    if not architecture.get("risks"):
        findings.append(SecurityFinding(
            id="",
            module="*",
            threat_id="T-PATT-1",
            category="ai_pattern",
            severity=patt_severity,
            evidence="risks 为空：未声明任何风险与对策",
            remediation="在 architecture.risks 中声明至少一条风险及对应对策，供审批关口证伪。",
            source="rule",
        ))
    if not modules:
        findings.append(SecurityFinding(
            id="",
            module="*",
            threat_id="T-PATT-1",
            category="ai_pattern",
            severity=patt_severity,
            evidence="模块列表为空：无法构建可交付架构",
            remediation="定义至少一个模块（name/responsibility/interfaces/owner_role）。",
            source="rule",
        ))
    elif len(modules) > 30:
        findings.append(SecurityFinding(
            id="",
            module="*",
            threat_id="T-PATT-1",
            category="ai_pattern",
            severity=patt_severity,
            evidence=f"模块数量 {len(modules)} 超过上限 30",
            remediation="拆分或合并模块，控制在 30 个以内。",
            source="rule",
        ))
    for m in modules:
        if not str(m.get("owner_role") or "").strip():
            findings.append(SecurityFinding(
                id="",
                module=m.get("name") or "(未命名模块)",
                threat_id="T-PATT-1",
                category="ai_pattern",
                severity=patt_severity,
                evidence=f"模块「{m.get('name') or '(未命名模块)'}」缺少 owner_role",
                remediation="为每个模块指定 owner_role，明确责任归属。",
                source="rule",
            ))

    overview = str(architecture.get("overview") or "")
    has_fail_safe = any(kw in overview for kw in ("失败处理", "降级", "守卫"))
    executes = any(
        "执行" in str(i) or "命令" in str(i)
        for m in modules
        for i in (m.get("interfaces") or [])
    )
    if not has_fail_safe and executes:
        findings.append(SecurityFinding(
            id="",
            module="*",
            threat_id="T-SAFE-1",
            category="ai_safeguard",
            severity=safe_severity,
            evidence="overview 未描述失败处理/降级/守卫，但存在含「执行/命令」的接口",
            remediation="补充输入守卫、输出校验与失败降级机制，明确单点故障的处理路径。",
            source="rule",
        ))
    return _assign_ids(findings)


def merge_findings(*groups: list[SecurityFinding]) -> list[SecurityFinding]:
    """发现聚合：按 (threat_id, module, evidence 前 80 字符) 去重，severity 降序确定排序。

    完全确定性：同 severity 按 (module, threat_id) 升序；完全相同时保持输入顺序
    （稳定排序），同输入必同输出。
    """
    merged: list[SecurityFinding] = []
    seen: set[tuple[str, str, str]] = set()
    for group in groups:
        for f in group:
            key = (f.threat_id, f.module, f.evidence[:80])
            if key in seen:
                continue
            seen.add(key)
            merged.append(f)
    merged.sort(key=lambda f: (-_SEVERITY_RANK.get(f.severity, 0), f.module, f.threat_id))
    return merged


def validate_architecture(
    architecture: dict,
    catalog: ThreatCatalog | None = None,
    policy: ValidationPolicy | None = None,
    llm_findings: list[SecurityFinding] | None = None,
) -> SecurityReport:
    """主入口（纯函数，可离线单测）：规则检查 → 合并 LLM 发现 → 截断 → apply_policy。

    - ``catalog`` / ``policy`` 缺省时用 ``load_threat_catalog()`` / ``ValidationPolicy()``。
    - LLM 发现 source 归一为 "llm"；``llm_verdict_requires_rule`` 为真时，LLM 的
      critical/high 若与任一规则发现无同 threat_id 共识，降级为 medium 并附注。
    - 每威胁按 ``max_findings_per_threat`` 截断；id 按 ``F-{threat_id}-{n:03d}`` 重编号。
    - checks 列出实际执行的检查名与各检查 finding 数（可审计）。
    """
    catalog = catalog if catalog is not None else load_threat_catalog()
    policy = policy if policy is not None else ValidationPolicy()
    architecture = architecture or {}  # 空/缺省架构对象：检查器全部零 finding（向后兼容）

    checks: list[str] = []
    rule_groups: list[list[SecurityFinding]] = []
    check_defs: list[tuple[str, object, tuple]] = [
        ("check_hallucinated_references", check_hallucinated_references, (architecture,)),
        ("check_dependency_cycle", check_dependency_cycle, (architecture,)),
        ("check_missing_security_controls", check_missing_security_controls, (architecture, catalog)),
        ("check_architectural_anti_patterns", check_architectural_anti_patterns, (architecture, catalog)),
    ]
    for name, fn, args in check_defs:
        group = fn(*args)  # type: ignore[operator]
        rule_groups.append(group)
        checks.append(f"{name}: {len(group)} findings")
    rule_findings = merge_findings(*rule_groups)
    rule_threat_ids = {f.threat_id for f in rule_findings}

    merged = list(rule_findings)
    if llm_findings:
        for f in llm_findings:
            if f.source != "llm":
                f = dataclasses.replace(f, source="llm")
            if (
                policy.llm_verdict_requires_rule
                and f.severity in ("critical", "high")
                and f.threat_id not in rule_threat_ids
            ):
                f = dataclasses.replace(
                    f,
                    severity="medium",
                    evidence=f"{f.evidence}（LLM 发现，与规则发现无共识，按策略降级为 medium）",
                )
            merged.append(f)
        checks.append(f"merge llm_findings: {len(llm_findings)} findings")
    merged = merge_findings(merged)

    # 每威胁截断（保持合并后顺序，确定性）
    cap = policy.max_findings_per_threat
    counts: dict[str, int] = {}
    truncated: list[SecurityFinding] = []
    for f in merged:
        n = counts.get(f.threat_id, 0)
        if n < cap:
            counts[f.threat_id] = n + 1
            truncated.append(f)
    truncated = _assign_ids(truncated)

    report = SecurityReport(
        verdict="",
        findings=truncated,
        checks=checks,
        summary="",
        policy_version=catalog.version,
        generated_at=_GENERATED_AT_EPOCH,
    )
    verdict = apply_policy(report, policy)
    n_rule = sum(1 for f in truncated if f.source == "rule")
    n_llm = sum(1 for f in truncated if f.source == "llm")
    summary = (
        f"架构安全验证完成：verdict={verdict}，共 {len(truncated)} 条发现"
        f"（rule {n_rule} / llm {n_llm}），执行 {len(checks)} 项检查"
    )
    report.verdict = verdict
    report.summary = summary
    return report


# ---------------------------------------------------------------------------
# 报告渲染
# ---------------------------------------------------------------------------


def _escape_md(text: str) -> str:
    """markdown 转义：``|``、反引号；换行→空格（防渲染注入，T-ENG-5）。"""
    return (
        text.replace("|", "\\|")
        .replace("`", "\\`")
        .replace("\r\n", " ")
        .replace("\n", " ")
        .replace("\r", " ")
    )


def render_security_report_md(report: SecurityReport) -> str:
    """确定性渲染 SecurityReport 为 markdown（审批单/看板/最终报告共用）。

    证据/整改截断 200 字符并转义；模块名同样转义，保证表格结构不被破坏。
    """
    lines = [
        "# 架构安全验证报告",
        "",
        f"- 裁决（verdict）：**{report.verdict}**",
        f"- 摘要：{_escape_md(report.summary)}",
        f"- 策略版本：{report.policy_version}",
        f"- 生成时间：{report.generated_at}",
        f"- 发现总数：{len(report.findings)}",
        "",
        "## 发现清单",
        "",
        "| 模块 | 威胁 | 级别 | 证据 | 整改建议 | 来源 |",
        "|---|---|---|---|---|---|",
    ]
    for f in report.findings:
        lines.append(
            "| {} | {} | {} | {} | {} | {} |".format(
                _escape_md(f.module),
                _escape_md(f.threat_id),
                _escape_md(f.severity),
                _escape_md(_truncate(f.evidence, 200)),
                _escape_md(_truncate(f.remediation, 200)),
                _escape_md(f.source),
            )
        )
    lines += ["", "## 检查清单", ""]
    lines += [f"- {check}" for check in report.checks]
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# dist 交付树静态扫描（批次 3 扩展）
# ---------------------------------------------------------------------------


def check_dist_artifacts(
    dist_dir: str,
    manifest: dict,
    mask_patterns: list[str] | None = None,
) -> list[SecurityFinding]:
    """对 dist 交付树做静态安全扫描：硬编码密钥 / 危险调用 / 敏感文件。

    - 递归扫描 dist_dir，仅处理文本文件（<=1MB，含 NUL 或非 UTF-8 的按二进制跳过）。
    - 硬编码密钥：复用 ``data_compliance.DEFAULT_MASK_RULES`` 的 pattern
      （或传入 ``mask_patterns`` 覆盖），命中即 T-DISC-1。
    - 危险调用：``shell=True`` / ``os.system(`` / ``eval(`` / ``exec(`` → T-TAMP-2。
    - 敏感文件：``.env`` / ``*.pem`` / ``*.key`` / ``*id_rsa*`` → T-DISC-1。
    - ``manifest`` 为预留参数（供集成层核对文件清单），本函数不消费其内容；
      引用字段/文件名只做模式匹配，绝不按值做 IO。
    """
    patterns = list(mask_patterns) if mask_patterns is not None else [r.pattern for r in DEFAULT_MASK_RULES]
    compiled = [re.compile(p) for p in patterns]
    root = Path(dist_dir)
    if not root.exists() or not root.is_dir():
        return []

    findings: list[SecurityFinding] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        # 敏感文件名（先于内容扫描，二进制密钥文件也能命中）
        if _SENSITIVE_FILENAME_RE.search(path.name):
            findings.append(SecurityFinding(
                id="",
                module=rel,
                threat_id="T-DISC-1",
                category="information_disclosure",
                severity="high",
                evidence=f"敏感文件落盘：{rel}",
                remediation="敏感文件不应随 dist 交付：移入受保护的密钥/配置存储，并从交付清单剔除。",
                source="rule",
            ))
        try:
            if path.stat().st_size > _MAX_TEXT_FILE_BYTES:
                continue
            data = path.read_bytes()
        except OSError:
            continue
        if b"\x00" in data[:8192]:
            continue  # 二进制
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue  # 非 UTF-8 文本按二进制跳过
        if any(p.search(text) for p in compiled):
            findings.append(SecurityFinding(
                id="",
                module=rel,
                threat_id="T-DISC-1",
                category="information_disclosure",
                severity="high",
                evidence=f"疑似硬编码密钥：{rel}（命中 data_compliance 脱敏模式）",
                remediation="移除硬编码凭据，改用环境变量/密钥管理服务注入。",
                source="rule",
            ))
        if _DANGEROUS_CALL_RE.search(text):
            findings.append(SecurityFinding(
                id="",
                module=rel,
                threat_id="T-TAMP-2",
                category="tampering",
                severity="high",
                evidence=f"危险调用模式：{rel}（shell=True/os.system/eval/exec）",
                remediation="移除 shell 执行与动态求值，改用受白名单约束的安全 API。",
                source="rule",
            ))
    return _assign_ids(findings)
