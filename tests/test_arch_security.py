"""Tests for card-ai-arch-security: 确定性规则引擎 arch_security（批次 1 回归）。

覆盖：幻觉引用 / 循环依赖 / 缺失安全控制 / 架构反模式 四类规则检查、
merge_findings 去重排序确定性、validate_architecture 主入口纯函数确定性、
render_security_report_md 渲染确定性（转义防注入）、to_sarif 合法 JSON、
exit_code 裁决映射、check_dist_artifacts 静态扫描。
"""
from __future__ import annotations

import json

from agent_hive.arch_security import (
    SecurityFinding,
    SecurityReport,
    check_architectural_anti_patterns,
    check_dependency_cycle,
    check_dist_artifacts,
    check_hallucinated_references,
    check_missing_security_controls,
    merge_findings,
    render_security_report_md,
    validate_architecture,
)
from agent_hive.threat_model import Threat, ThreatCatalog, ThreatCategory, ValidationPolicy


# ---------------------------------------------------------------------------
# 测试用受控威胁目录（只依赖公开契约，不依赖内置目录的具体内容）
# ---------------------------------------------------------------------------


def _catalog() -> ThreatCatalog:
    """受控目录：T-PATT-1 为 critical（验证 fail 裁决）；关键词与控件词分离设计。"""
    return ThreatCatalog(version="test-1.0", threats=(
        Threat(
            id="T-PATT-1",
            category=ThreatCategory.AI_PATTERN,
            name="结构反模式",
            description="循环依赖/单点/risks 空缺/无 owner",
            affected_asset="结构",
            control="合理的模块划分与依赖方向",
            remediation="调整模块划分或依赖方向，补齐风险对策与 owner",
            severity="critical",
            keywords=("绝无匹配关键字",),
        ),
        Threat(
            id="T-SPOOF-1",
            category=ThreatCategory.SPOOFING,
            name="身份假冒",
            description="缺乏认证导致身份冒用",
            affected_asset="认证/身份",
            control="架构应设计认证、鉴权与身份管理",
            remediation="为涉及身份/凭据的模块设计统一认证、鉴权与身份管理",
            severity="high",
            keywords=("登录", "密码"),
        ),
        Threat(
            id="T-SAFE-1",
            category=ThreatCategory.AI_SAFEGUARD,
            name="缺失守卫",
            description="无输入/输出守卫与失败降级",
            affected_asset="守卫/降级",
            control="输入守卫、输出守卫与失败降级",
            remediation="补充输入校验、输出过滤与失败降级机制",
            severity="high",
            keywords=("另一个绝不匹配词",),
        ),
    ))


def _finding(
    threat_id: str = "T-SPOOF-1",
    module: str = "mod",
    severity: str = "high",
    evidence: str = "证据",
    source: str = "rule",
    category: str = "spoofing",
) -> SecurityFinding:
    return SecurityFinding(
        id=f"F-{threat_id}-001",
        module=module,
        threat_id=threat_id,
        category=category,
        severity=severity,  # type: ignore[arg-type]
        evidence=evidence,
        remediation="整改建议",
        source=source,  # type: ignore[arg-type]
    )


def _report(verdict: str = "fail") -> SecurityReport:
    return SecurityReport(
        verdict=verdict,
        findings=[_finding(module="auth", evidence="模块「auth」缺少认证设计")],
        checks=["check_hallucinated_references: 0 findings", "check_dependency_cycle: 0 findings"],
        summary="测试摘要",
        policy_version="test-1.0",
        generated_at="1970-01-01T00:00:00+00:00",
    )


# ---------------------------------------------------------------------------
# 1. 幻觉引用
# ---------------------------------------------------------------------------


class TestHallucinatedReferences:
    def test_undefined_prefix_reference_flagged(self):
        arch = {
            "overview": "o",
            "modules": [
                {"name": "auth", "responsibility": "认证", "interfaces": ["login()", "调用: 不存在的模块"], "owner_role": "编码"},
                {"name": "gateway", "responsibility": "路由", "interfaces": ["route()", "依赖: `nonexistent`"], "owner_role": "编码"},
            ],
            "risks": ["r"],
        }
        findings = check_hallucinated_references(arch)
        assert findings
        assert all(f.threat_id == "T-HALL-1" for f in findings)
        assert all(f.severity == "high" for f in findings)
        evidence = " ".join(f.evidence for f in findings)
        assert "不存在的模块" in evidence
        assert "nonexistent" in evidence

    def test_backtick_undefined_reference_flagged(self):
        arch = {
            "overview": "o",
            "modules": [
                {"name": "auth", "responsibility": "认证", "interfaces": ["login()", "对接 `fake_module`"], "owner_role": "编码"},
            ],
            "risks": ["r"],
        }
        findings = check_hallucinated_references(arch)
        assert any("fake_module" in f.evidence for f in findings)

    def test_defined_references_pass(self):
        arch = {
            "overview": "o",
            "modules": [
                {"name": "auth", "responsibility": "认证", "interfaces": ["login()", "调用: auth", "引用: gateway"], "owner_role": "编码"},
                {"name": "gateway", "responsibility": "路由", "interfaces": ["route()", "依赖: auth"], "owner_role": "编码"},
            ],
            "risks": ["r"],
        }
        assert check_hallucinated_references(arch) == []


# ---------------------------------------------------------------------------
# 2. 循环依赖（复用 scheduler.validate_dependency_graph 语义）
# ---------------------------------------------------------------------------


class TestDependencyCycle:
    def test_cycle_flagged(self):
        arch = {
            "overview": "o",
            "modules": [
                {"name": "A", "responsibility": "a", "interfaces": ["a()"], "owner_role": "编码", "depends_on": ["B"]},
                {"name": "B", "responsibility": "b", "interfaces": ["b()"], "owner_role": "编码", "depends_on": ["A"]},
            ],
            "risks": ["r"],
        }
        findings = check_dependency_cycle(arch)
        assert len(findings) == 1
        assert findings[0].threat_id == "T-PATT-1"
        assert "环" in findings[0].evidence

    def test_no_cycle_passes(self):
        arch = {
            "overview": "o",
            "modules": [
                {"name": "A", "responsibility": "a", "interfaces": ["a()"], "owner_role": "编码"},
                {"name": "B", "responsibility": "b", "interfaces": ["b()"], "owner_role": "编码", "depends_on": ["A"]},
            ],
            "risks": ["r"],
        }
        assert check_dependency_cycle(arch) == []


# ---------------------------------------------------------------------------
# 3. 缺失安全控制
# ---------------------------------------------------------------------------


class TestMissingSecurityControls:
    def test_missing_control_flagged(self):
        arch = {
            "overview": "o",
            "modules": [
                {"name": "user", "responsibility": "负责用户登录与密码校验", "interfaces": ["login()", "reset_password()"], "owner_role": "编码"},
            ],
            "risks": ["r"],
        }
        findings = check_missing_security_controls(arch, _catalog())
        spoof = [f for f in findings if f.threat_id == "T-SPOOF-1"]
        assert spoof, f"应命中 T-SPOOF-1，实际: {[f.threat_id for f in findings]}"
        assert "user" in spoof[0].evidence  # 证据引用模块名
        assert spoof[0].severity == "high"  # severity = 威胁 severity

    def test_control_present_passes(self):
        arch = {
            "overview": "o",
            "modules": [
                {"name": "user", "responsibility": "负责登录与密码校验，提供统一认证、鉴权与身份管理", "interfaces": ["login()"], "owner_role": "编码"},
            ],
            "risks": ["r"],
        }
        findings = check_missing_security_controls(arch, _catalog())
        assert not any(f.threat_id == "T-SPOOF-1" for f in findings)

    def test_no_match_passes(self):
        arch = {
            "overview": "o",
            "modules": [
                {"name": "util", "responsibility": "纯工具函数", "interfaces": ["fmt()"], "owner_role": "编码"},
            ],
            "risks": ["r"],
        }
        assert check_missing_security_controls(arch, _catalog()) == []


# ---------------------------------------------------------------------------
# 4. 架构反模式
# ---------------------------------------------------------------------------


class TestArchitecturalAntiPatterns:
    def test_risks_empty_flagged(self):
        arch = {
            "overview": "o",
            "modules": [{"name": "m", "responsibility": "r", "interfaces": ["i()"], "owner_role": "编码"}],
            "risks": [],
        }
        findings = check_architectural_anti_patterns(arch, _catalog())
        assert any(f.threat_id == "T-PATT-1" and "risks" in f.evidence for f in findings)

    def test_missing_owner_role_flagged(self):
        arch = {
            "overview": "o",
            "modules": [{"name": "m", "responsibility": "r", "interfaces": ["i()"]}],
            "risks": ["r"],
        }
        findings = check_architectural_anti_patterns(arch, _catalog())
        assert any(f.threat_id == "T-PATT-1" and f.module == "m" for f in findings)

    def test_module_count_overflow_flagged(self):
        modules = [
            {"name": f"m{i}", "responsibility": "r", "interfaces": ["i()"], "owner_role": "编码"}
            for i in range(31)
        ]
        arch = {"overview": "o", "modules": modules, "risks": ["r"]}
        findings = check_architectural_anti_patterns(arch, _catalog())
        assert any(f.threat_id == "T-PATT-1" and "30" in f.evidence for f in findings)

    def test_no_fail_safe_with_execute_flagged(self):
        arch = {
            "overview": "o",
            "modules": [
                {"name": "runner", "responsibility": "r", "interfaces": ["执行任务()", "run_command()"], "owner_role": "编码"},
            ],
            "risks": ["r"],
        }
        findings = check_architectural_anti_patterns(arch, _catalog())
        assert any(f.threat_id == "T-SAFE-1" for f in findings)

    def test_normal_architecture_passes(self):
        arch = {
            "overview": "o 含失败处理、降级与守卫设计",
            "modules": [
                {"name": "m", "responsibility": "r", "interfaces": ["read()"], "owner_role": "编码"},
            ],
            "risks": ["r"],
        }
        assert check_architectural_anti_patterns(arch, _catalog()) == []


# ---------------------------------------------------------------------------
# 5. merge_findings 去重 + 排序确定性
# ---------------------------------------------------------------------------


class TestMergeFindings:
    def test_dedup_and_sort_deterministic(self):
        a = _finding(threat_id="T-SPOOF-1", module="mod", severity="high", evidence="证据甲")
        b = _finding(threat_id="T-SPOOF-1", module="mod", severity="high", evidence="证据甲")  # 与 a 重复
        c = _finding(threat_id="T-SPOOF-1", module="aaa", severity="critical", evidence="证据乙")
        d = _finding(threat_id="T-PATT-1", module="mod", severity="high", evidence="证据丙", category="ai_pattern")

        merged1 = merge_findings([a, b, c, d])
        merged2 = merge_findings([d, c, b, a])  # 不同输入顺序
        merged3 = merge_findings([a, b, c, d])  # 同输入跑第二遍

        assert len(merged1) == 3  # 去重：4 条 → 3 条
        assert merged1[0].severity == "critical"  # severity 降序
        assert [f.id for f in merged1] == [f.id for f in merged2]
        assert [f.id for f in merged1] == [f.id for f in merged3]
        # 同 severity 按 (module, threat_id) 升序：T-PATT-1 < T-SPOOF-1
        assert [f.threat_id for f in merged1[1:]] == ["T-PATT-1", "T-SPOOF-1"]

    def test_dedup_key_uses_evidence_prefix(self):
        a = _finding(threat_id="T-SPOOF-1", module="mod", severity="high", evidence="x" * 90)
        b = _finding(threat_id="T-SPOOF-1", module="mod", severity="high", evidence="x" * 90 + "suffix")
        merged = merge_findings([a, b])
        assert len(merged) == 1  # evidence 前 80 字符相同 → 去重


# ---------------------------------------------------------------------------
# 6. validate_architecture 主入口（纯函数 + 裁决）
# ---------------------------------------------------------------------------


class TestValidateArchitecture:
    def test_clean_architecture_pass(self):
        arch = {
            "overview": "系统包含认证、鉴权与身份管理、失败降级与守卫设计",
            "modules": [
                {"name": "auth", "responsibility": "提供统一认证、鉴权与身份管理服务", "interfaces": ["login()"], "owner_role": "编码"},
                {"name": "gateway", "responsibility": "请求路由与守卫", "interfaces": ["route()"], "owner_role": "编码", "depends_on": ["auth"]},
            ],
            "risks": ["网关故障时降级为只读", "密钥由平台密钥管理服务托管"],
        }
        report = validate_architecture(arch, catalog=_catalog())
        assert report.findings == []
        assert report.verdict == "pass"

    def test_critical_finding_fails(self):
        arch = {
            "overview": "o",
            "modules": [{"name": "m", "responsibility": "r", "interfaces": ["i()"]}],  # 无 owner_role
            "risks": [],  # 空
        }
        report = validate_architecture(arch, catalog=_catalog())
        assert report.verdict == "fail"
        assert any(f.severity == "critical" for f in report.findings)
        assert report.exit_code() == 2

    def test_deterministic_same_input_same_output(self):
        arch = {
            "overview": "o",
            "modules": [
                {"name": "m", "responsibility": "负责用户登录与密码校验", "interfaces": ["login()", "调用: ghost"]},
                {"name": "n", "responsibility": "r", "interfaces": ["i()"], "owner_role": "编码", "depends_on": ["m"]},
            ],
            "risks": [],
        }
        llm = [
            _finding(threat_id="T-LLM-1", module="m", severity="critical",
                     evidence="LLM 认为存在风险", source="llm", category="ai_pattern"),
        ]
        r1 = validate_architecture(arch, catalog=_catalog(), llm_findings=llm)
        r2 = validate_architecture(arch, catalog=_catalog(), llm_findings=llm)
        assert r1.to_dict() == r2.to_dict()
        assert r1.to_json() == r2.to_json()

    def test_default_catalog_policy_smoke(self):
        arch = {
            "overview": "o",
            "modules": [{"name": "m", "responsibility": "r", "interfaces": ["i()"], "owner_role": "编码"}],
            "risks": ["r"],
        }
        report = validate_architecture(arch)  # 走 load_threat_catalog()/ValidationPolicy() 默认
        assert report.verdict in ("pass", "pass_with_warnings", "fail")
        assert report.policy_version  # 目录版本进入报告

    def test_llm_finding_downgraded_without_rule_consensus(self):
        arch = {
            "overview": "o",
            "modules": [{"name": "m", "responsibility": "负责用户登录与密码校验", "interfaces": ["login()"], "owner_role": "编码"}],
            "risks": ["r"],
        }
        llm = _finding(threat_id="T-LLM-1", module="m", severity="critical",
                       evidence="LLM 提出单点风险", source="llm", category="ai_pattern")
        report = validate_architecture(arch, catalog=_catalog(), llm_findings=[llm])
        llm_f = [f for f in report.findings if f.threat_id == "T-LLM-1"]
        assert llm_f
        assert llm_f[0].severity == "medium"  # 无规则共识 → 降级
        assert "降级" in llm_f[0].evidence
        assert llm_f[0].source == "llm"

    def test_llm_finding_kept_with_rule_consensus(self):
        arch = {
            "overview": "o",
            "modules": [{"name": "m", "responsibility": "负责用户登录与密码校验", "interfaces": ["login()"], "owner_role": "编码"}],
            "risks": ["r"],
        }
        llm = _finding(threat_id="T-SPOOF-1", module="m", severity="critical",
                       evidence="LLM 复证认证缺失", source="llm")  # 与规则发现 T-SPOOF-1 共识
        report = validate_architecture(arch, catalog=_catalog(), llm_findings=[llm])
        llm_f = [f for f in report.findings if f.source == "llm"]
        assert llm_f
        assert llm_f[0].severity == "critical"  # 有共识 → 不降级

    def test_llm_finding_kept_when_policy_disabled(self):
        arch = {
            "overview": "o",
            "modules": [{"name": "m", "responsibility": "负责用户登录与密码校验", "interfaces": ["login()"], "owner_role": "编码"}],
            "risks": ["r"],
        }
        policy = ValidationPolicy(llm_verdict_requires_rule=False)
        llm = _finding(threat_id="T-LLM-1", module="m", severity="critical",
                       evidence="LLM 提出单点风险", source="llm", category="ai_pattern")
        report = validate_architecture(arch, catalog=_catalog(), policy=policy, llm_findings=[llm])
        llm_f = [f for f in report.findings if f.threat_id == "T-LLM-1"]
        assert llm_f and llm_f[0].severity == "critical"

    def test_max_findings_per_threat_truncated(self):
        arch = {
            "overview": "o",
            "modules": [
                {"name": f"m{i}", "responsibility": "负责用户登录与密码校验", "interfaces": ["login()"], "owner_role": "编码"}
                for i in range(7)
            ],
            "risks": ["r"],
        }
        policy = ValidationPolicy(max_findings_per_threat=3)
        report = validate_architecture(arch, catalog=_catalog(), policy=policy)
        spoof = [f for f in report.findings if f.threat_id == "T-SPOOF-1"]
        assert len(spoof) == 3


class TestEmptyArchitectureBackwardCompat:
    """向后兼容：空 architecture_object（{}）时四个检查器与主入口零 finding、不抛异常。"""

    def test_all_checkers_return_zero_on_empty_object(self):
        arch: dict = {}
        assert check_hallucinated_references(arch) == []
        assert check_dependency_cycle(arch) == []
        assert check_missing_security_controls(arch, _catalog()) == []
        assert check_architectural_anti_patterns(arch, _catalog()) == []

    def test_validate_architecture_empty_object_passes(self):
        report = validate_architecture({}, catalog=_catalog())
        assert report.findings == []
        assert report.verdict == "pass"
        assert report.exit_code() == 0

    def test_validate_architecture_none_passes(self):
        report = validate_architecture(None, catalog=_catalog())  # type: ignore[arg-type]
        assert report.findings == []
        assert report.verdict == "pass"


# ---------------------------------------------------------------------------
# 7. render_security_report_md 确定性 + 转义
# ---------------------------------------------------------------------------


class TestRenderMarkdown:
    def test_deterministic_and_escaped(self):
        report = SecurityReport(
            verdict="fail",
            findings=[
                SecurityFinding(
                    id="F-T-SPOOF-1-001",
                    module="auth|模块",
                    threat_id="T-SPOOF-1",
                    category="spoofing",
                    severity="high",
                    evidence="证据含 `反引号` 与 |竖线| 与换行\n第二行",
                    remediation="整改：加`认证`|鉴权",
                    source="llm",  # type: ignore[arg-type]
                )
            ],
            checks=["check_hallucinated_references: 1 findings"],
            summary="摘要",
            policy_version="v1",
            generated_at="1970-01-01T00:00:00+00:00",
        )
        md1 = render_security_report_md(report)
        md2 = render_security_report_md(report)
        assert md1 == md2  # 确定性
        assert "证据含 \\`反引号\\` 与 \\|竖线\\| 与换行 第二行" in md1
        assert "整改：加\\`认证\\`\\|鉴权" in md1
        assert "auth\\|模块" in md1  # 模块名同样转义
        assert md1.startswith("# 架构安全验证报告")
        assert "## 检查清单" in md1

    def test_evidence_truncated_to_200(self):
        report = SecurityReport(
            verdict="fail",
            findings=[_finding(evidence="e" * 300)],
            checks=[],
            summary="s",
            policy_version="v",
            generated_at="g",
        )
        md = render_security_report_md(report)
        assert "e" * 200 + "…" in md
        assert "e" * 201 not in md


# ---------------------------------------------------------------------------
# 8. to_sarif / exit_code
# ---------------------------------------------------------------------------


class TestSarifAndExitCode:
    def test_to_sarif_valid_json(self):
        sarif_text = _report().to_sarif()
        data = json.loads(sarif_text)  # 合法 JSON
        assert "2.1.0" in sarif_text
        assert data["version"] == "2.1.0"
        assert data["$schema"].startswith("https://")
        run0 = data["runs"][0]
        assert run0["tool"]["driver"]["name"]
        results = run0["results"]
        assert results
        r0 = results[0]
        assert "ruleId" in r0
        assert r0["level"] in ("error", "warning", "note")
        assert "text" in r0["message"]
        loc = r0["locations"][0]["physicalLocation"]
        assert loc["artifactLocation"]["uri"]
        assert "startLine" in loc["region"]

    def test_to_dict_to_json_roundtrip(self):
        report = _report()
        assert json.loads(report.to_json()) == report.to_dict()

    def test_exit_code(self):
        assert _report(verdict="fail").exit_code() == 2
        assert _report(verdict="pass").exit_code() == 0
        assert _report(verdict="pass_with_warnings").exit_code() == 0


# ---------------------------------------------------------------------------
# 9. check_dist_artifacts 静态扫描
# ---------------------------------------------------------------------------


class TestDistArtifacts:
    def test_finds_secret_dangerous_call_and_sensitive_file(self, tmp_path):
        (tmp_path / "app.py").write_text(
            "token = 'sk-xxxxxxxxxxxxxxxxxxxxx'\nsubprocess.run(cmd, shell=True)\n",
            encoding="utf-8",
        )
        (tmp_path / ".env").write_text("TOKEN=sk-xxxxxxxxxxxxxxxxxxxxx\n", encoding="utf-8")
        nested = tmp_path / "nested"
        nested.mkdir()
        (nested / "id_rsa").write_text("-----BEGIN RSA PRIVATE KEY-----\n", encoding="utf-8")
        findings = check_dist_artifacts(str(tmp_path), manifest={})
        assert len(findings) >= 2
        threat_ids = {f.threat_id for f in findings}
        assert "T-DISC-1" in threat_ids  # 硬编码密钥 + 敏感文件
        assert "T-TAMP-2" in threat_ids  # shell=True
        evidence = " ".join(f.evidence for f in findings)
        assert "app.py" in evidence
        assert ".env" in evidence

    def test_clean_directory_no_findings(self, tmp_path):
        (tmp_path / "main.py").write_text("def hello():\n    return 'hi'\n", encoding="utf-8")
        (tmp_path / "notes.txt").write_text("just a clean short file\n", encoding="utf-8")
        assert check_dist_artifacts(str(tmp_path), manifest={}) == []

    def test_custom_mask_patterns(self, tmp_path):
        (tmp_path / "cfg.txt").write_text("secret=abc123\n", encoding="utf-8")
        findings = check_dist_artifacts(str(tmp_path), manifest={}, mask_patterns=[r"abc123"])
        assert len(findings) == 1
        assert findings[0].threat_id == "T-DISC-1"
