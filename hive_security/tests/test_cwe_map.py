"""CWE / OWASP Top 10 for LLM（2025）映射与 SARIF properties 测试。"""
from __future__ import annotations

import json

import pytest

from hive_security.arch_security import SecurityFinding, SecurityReport
from hive_security.cwe_map import CWE_MAP, OWASP_LLM_MAP
from hive_security.threat_model import load_threat_catalog


def _report(threat_id: str = "T-SPOOF-1", severity: str = "high") -> SecurityReport:
    return SecurityReport(
        verdict="fail",
        findings=[SecurityFinding(
            id=f"F-{threat_id}-001",
            module="mod",
            threat_id=threat_id,
            category="spoofing",
            severity=severity,  # type: ignore[arg-type]
            evidence="证据",
            remediation="整改建议",
            source="rule",
        )],
        checks=["check_hallucinated_references: 0 findings"],
        summary="测试摘要",
        policy_version="test-1.0",
        generated_at="1970-01-01T00:00:00+00:00",
    )


# ---------------------------------------------------------------------------
# 1. 映射表本身
# ---------------------------------------------------------------------------


class TestMaps:
    def test_cwe_map_covers_all_builtin_threats(self):
        catalog = load_threat_catalog()
        assert set(CWE_MAP) == {t.id for t in catalog.threats}

    def test_owasp_map_keys_are_known_threat_ids(self):
        catalog = load_threat_catalog()
        known = {t.id for t in catalog.threats}
        assert set(OWASP_LLM_MAP) <= known

    def test_cwe_entries_verified(self):
        assert CWE_MAP["T-SPOOF-1"] == ["CWE-287"]   # Improper Authentication
        assert CWE_MAP["T-SPOOF-2"] == ["CWE-284"]   # Improper Access Control
        assert CWE_MAP["T-TAMP-1"] == ["CWE-74"]     # Injection
        assert CWE_MAP["T-TAMP-2"] == ["CWE-78"]     # OS Command Injection
        assert CWE_MAP["T-REPU-1"] == ["CWE-778"]    # Insufficient Logging
        assert CWE_MAP["T-DISC-1"] == ["CWE-798"]    # Hard-coded Credentials
        assert CWE_MAP["T-DISC-2"] == ["CWE-359"]    # Private Personal Information
        assert CWE_MAP["T-DOS-1"] == ["CWE-400"]     # Uncontrolled Resource Consumption
        assert CWE_MAP["T-ELEV-1"] == ["CWE-269"]    # Improper Privilege Management
        assert CWE_MAP["T-SAFE-1"] == ["CWE-693"]    # Protection Mechanism Failure
        assert CWE_MAP["T-PATT-1"] == ["CWE-1047"]   # Circular Dependencies

    def test_hallucination_has_no_cwe(self):
        # 不伪造编号：幻觉无对应 CWE → 空列表
        assert CWE_MAP["T-HALL-1"] == []

    def test_owasp_entries_verified_2025(self):
        assert OWASP_LLM_MAP["T-TAMP-1"] == ["LLM01"]   # Prompt Injection
        assert OWASP_LLM_MAP["T-DISC-1"] == ["LLM02"]   # Sensitive Information Disclosure
        assert OWASP_LLM_MAP["T-DISC-2"] == ["LLM02"]   # Sensitive Information Disclosure
        assert OWASP_LLM_MAP["T-SAFE-1"] == ["LLM05"]   # Improper Output Handling
        assert OWASP_LLM_MAP["T-ELEV-1"] == ["LLM06"]   # Excessive Agency
        assert OWASP_LLM_MAP["T-HALL-1"] == ["LLM09"]   # Misinformation
        assert OWASP_LLM_MAP["T-DOS-1"] == ["LLM10"]    # Unbounded Consumption

    def test_no_direct_owasp_counterpart_is_empty(self):
        # 2025 分类无直接对应 → 空列表而非伪造编号
        for tid in ("T-SPOOF-1", "T-SPOOF-2", "T-TAMP-2", "T-REPU-1", "T-PATT-1"):
            assert OWASP_LLM_MAP[tid] == []


# ---------------------------------------------------------------------------
# 2. SARIF properties
# ---------------------------------------------------------------------------


class TestSarifProperties:
    def test_each_result_has_properties_with_known_mapping(self):
        data = json.loads(_report("T-SPOOF-1").to_sarif())
        result = data["runs"][0]["results"][0]
        assert "properties" in result
        assert result["properties"] == {
            "cwe": ["CWE-287"],
            "owasp_llm_top10": [],
        }

    def test_mapped_threat_carries_both_lists(self):
        data = json.loads(_report("T-TAMP-1").to_sarif())
        props = data["runs"][0]["results"][0]["properties"]
        assert props["cwe"] == ["CWE-74"]
        assert props["owasp_llm_top10"] == ["LLM01"]

    def test_unknown_threat_id_empty_lists_no_crash(self):
        data = json.loads(_report("T-UNKNOWN-9").to_sarif())
        props = data["runs"][0]["results"][0]["properties"]
        assert props == {"cwe": [], "owasp_llm_top10": []}

    def test_all_catalog_threats_get_properties(self):
        catalog = load_threat_catalog()
        findings = [
            SecurityFinding(
                id=f"F-{t.id}-001", module="m", threat_id=t.id,
                category="c", severity="high", evidence="e", remediation="r",
                source="rule",
            )
            for t in catalog.threats
        ]
        report = SecurityReport(
            verdict="fail", findings=findings, checks=[], summary="s",
            policy_version="v", generated_at="g",
        )
        data = json.loads(report.to_sarif())
        results = data["runs"][0]["results"]
        assert len(results) == len(catalog.threats)
        by_rule = {r["ruleId"]: r for r in results}
        for tid in catalog.threats:
            props = by_rule[tid.id]["properties"]
            assert isinstance(props["cwe"], list)
            assert isinstance(props["owasp_llm_top10"], list)
        # 抽查：T-HALL-1 无 CWE；T-TAMP-1 带 LLM01
        assert by_rule["T-HALL-1"]["properties"]["cwe"] == []
        assert by_rule["T-TAMP-1"]["properties"]["owasp_llm_top10"] == ["LLM01"]

    def test_sarif_still_valid_json_version_210(self):
        text = _report().to_sarif()
        data = json.loads(text)  # 合法 JSON
        assert data["version"] == "2.1.0"
        assert data["$schema"].startswith("https://")
        assert data["runs"][0]["tool"]["driver"]["name"]

    def test_sarif_deterministic_with_properties(self):
        r1 = _report("T-DISC-1").to_sarif()
        r2 = _report("T-DISC-1").to_sarif()
        assert r1 == r2  # properties 为静态查表，不影响确定性
