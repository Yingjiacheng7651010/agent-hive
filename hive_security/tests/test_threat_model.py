"""hive_security.threat_model —— AI 架构安全验证威胁模型库测试（独立包移植版）。"""
from __future__ import annotations

import pytest

from hive_security.threat_model import (
    Finding,
    ThreatCategory,
    ValidationPolicy,
    apply_policy,
    load_threat_catalog,
)

STRIDE_CATEGORIES = [
    ThreatCategory.SPOOFING,
    ThreatCategory.TAMPERING,
    ThreatCategory.REPUDIATION,
    ThreatCategory.INFORMATION_DISCLOSURE,
    ThreatCategory.DENIAL_OF_SERVICE,
    ThreatCategory.ELEVATION_OF_PRIVILEGE,
]

AI_CATEGORIES = [
    ThreatCategory.AI_HALLUCINATION,
    ThreatCategory.AI_SAFEGUARD,
    ThreatCategory.AI_PATTERN,
]

FIXED_THREAT_IDS = [
    "T-SPOOF-1",
    "T-SPOOF-2",
    "T-TAMP-1",
    "T-TAMP-2",
    "T-REPU-1",
    "T-DISC-1",
    "T-DISC-2",
    "T-DOS-1",
    "T-ELEV-1",
    "T-HALL-1",
    "T-SAFE-1",
    "T-PATT-1",
]


def _make_report(findings=(), warnings=()):
    """构造 apply_policy 可接受的字典形态报告。"""
    return {"findings": list(findings), "warnings": list(warnings)}


class TestCatalogIntegrity:
    """1. 目录完整性：STRIDE 六类 + AI 三类每类 ≥1 条威胁；id 唯一。"""

    def test_each_stride_category_has_at_least_one_threat(self):
        catalog = load_threat_catalog()
        for category in STRIDE_CATEGORIES:
            assert catalog.by_category(category), (
                f"STRIDE 类别 {category.value} 缺少威胁条目"
            )

    def test_each_ai_category_has_at_least_one_threat(self):
        catalog = load_threat_catalog()
        for category in AI_CATEGORIES:
            assert catalog.by_category(category), (
                f"AI 类别 {category.value} 缺少威胁条目"
            )

    def test_threat_ids_are_unique(self):
        catalog = load_threat_catalog()
        ids = [t.id for t in catalog.threats]
        assert len(ids) == len(set(ids)), f"存在重复威胁 id: {ids}"

    def test_catalog_contains_all_fixed_ids(self):
        catalog = load_threat_catalog()
        assert {t.id for t in catalog.threats} >= set(FIXED_THREAT_IDS)


class TestMatchKeywords:
    """2. match_keywords：命中与不命中；大小写不敏感。"""

    def test_hit_auth_keyword(self):
        catalog = load_threat_catalog()
        # 含「认证」关键词的威胁应被命中（T-SPOOF-1）
        result = catalog.match_keywords("系统缺少认证机制，任何人都能发起调用")
        assert any(t.id == "T-SPOOF-1" for t in result)

    def test_hit_audit_keyword(self):
        catalog = load_threat_catalog()
        # 含「审计」关键词的威胁应被命中（T-REPU-1）
        result = catalog.match_keywords("当前没有审计日志，无法追溯操作来源")
        assert any(t.id == "T-REPU-1" for t in result)

    def test_no_match_returns_empty_list(self):
        catalog = load_threat_catalog()
        assert catalog.match_keywords("今天天气很好，适合出去散步") == []

    def test_empty_text_returns_empty_list(self):
        catalog = load_threat_catalog()
        assert catalog.match_keywords("") == []

    def test_keyword_matching_is_case_insensitive(self):
        catalog = load_threat_catalog()
        # 关键词 "sql注入" 以大写 S 出现在文本中，小写化后仍应命中（T-TAMP-1）
        result = catalog.match_keywords("外部输入被直接拼接进 Sql注入语句")
        assert any(t.id == "T-TAMP-1" for t in result)

    def test_keyword_matching_is_deterministic_and_deduplicated(self):
        catalog = load_threat_catalog()
        text = "缺少认证、审计与限流，且无降级机制"
        first = catalog.match_keywords(text)
        second = catalog.match_keywords(text)
        assert [t.id for t in first] == [t.id for t in second]
        assert len(first) == len({t.id for t in first})


class TestByCategory:
    """3. by_category 过滤正确。"""

    def test_by_category_returns_only_matching_category(self):
        catalog = load_threat_catalog()
        for category in STRIDE_CATEGORIES + AI_CATEGORIES:
            threats = catalog.by_category(category)
            assert threats
            assert all(t.category is category for t in threats)

    def test_by_category_accepts_string_value(self):
        catalog = load_threat_catalog()
        threats = catalog.by_category("spoofing")
        assert threats
        assert all(t.category is ThreatCategory.SPOOFING for t in threats)

    def test_by_category_preserves_catalog_order(self):
        catalog = load_threat_catalog()
        ids = [t.id for t in catalog.by_category(ThreatCategory.SPOOFING)]
        assert ids == ["T-SPOOF-1", "T-SPOOF-2"]


class TestApplyPolicy:
    """4. apply_policy 裁决：critical/high → fail；仅 medium/low → pass_with_warnings；
    无发现 → pass；exclusions 排除生效；max_warnings 超限 → fail。"""

    def test_critical_finding_fails(self):
        policy = ValidationPolicy()
        report = _make_report([Finding("T-SPOOF-1", "critical")])
        assert apply_policy(report, policy) == "fail"

    def test_high_finding_fails(self):
        policy = ValidationPolicy()
        report = _make_report([Finding("T-SPOOF-1", "high")])
        assert apply_policy(report, policy) == "fail"

    def test_medium_only_passes_with_warnings(self):
        policy = ValidationPolicy()
        report = _make_report([
            Finding("T-DOS-1", "medium"),
            Finding("T-PATT-1", "low"),
        ])
        assert apply_policy(report, policy) == "pass_with_warnings"

    def test_no_findings_passes(self):
        policy = ValidationPolicy()
        assert apply_policy(_make_report(), policy) == "pass"

    def test_excluded_critical_no_longer_fails(self):
        policy = ValidationPolicy(exclusions=("T-SPOOF-1",))
        report = _make_report([Finding("T-SPOOF-1", "critical")])
        assert apply_policy(report, policy) == "pass"

    def test_exclusions_only_suppress_matching_threat(self):
        policy = ValidationPolicy(exclusions=("T-SPOOF-2",))
        report = _make_report([Finding("T-SPOOF-1", "critical")])
        assert apply_policy(report, policy) == "fail"

    def test_excluded_finding_counts_as_no_finding(self):
        policy = ValidationPolicy(exclusions=("T-DOS-1",))
        report = _make_report([Finding("T-DOS-1", "medium")])
        assert apply_policy(report, policy) == "pass"

    def test_warnings_over_max_fails(self):
        policy = ValidationPolicy(max_warnings=2)
        report = _make_report([Finding("T-DOS-1", "low") for _ in range(3)])
        assert apply_policy(report, policy) == "fail"

    def test_warnings_within_max_passes_with_warnings(self):
        policy = ValidationPolicy(max_warnings=2)
        report = _make_report([
            Finding("T-DOS-1", "low"),
            Finding("T-PATT-1", "low"),
        ])
        assert apply_policy(report, policy) == "pass_with_warnings"

    def test_report_warnings_count_toward_max(self):
        policy = ValidationPolicy(max_warnings=1)
        report = _make_report([], warnings=["w1", "w2"])
        assert apply_policy(report, policy) == "fail"

    def test_accepts_object_report_with_findings(self):
        policy = ValidationPolicy()

        class Report:
            findings = [Finding("T-SPOOF-1", "high")]

        assert apply_policy(Report(), policy) == "fail"

    def test_accepts_dict_finding_entries(self):
        policy = ValidationPolicy()
        report = _make_report([{"threat_id": "T-SPOOF-1", "severity": "critical"}])
        assert apply_policy(report, policy) == "fail"


class TestFailOnSeverityValidation:
    """5. fail_on_severity 校验："high"/"critical" 合法；"medium"/"low"/"none" 非法。"""

    def test_high_is_valid(self):
        policy = ValidationPolicy(fail_on_severity="high")
        assert policy.fail_on_severity == "high"
        assert ValidationPolicy.validate_fail_on_severity("high") is True

    def test_critical_is_valid(self):
        policy = ValidationPolicy(fail_on_severity="critical")
        assert policy.fail_on_severity == "critical"
        assert ValidationPolicy.validate_fail_on_severity("critical") is True

    @pytest.mark.parametrize("value", ["medium", "low", "none"])
    def test_invalid_values_raise_value_error(self, value):
        # 构造策略时校验
        with pytest.raises(ValueError):
            ValidationPolicy(fail_on_severity=value)
        # 静态校验方法同样拒绝
        with pytest.raises(ValueError):
            ValidationPolicy.validate_fail_on_severity(value)


class TestDeterminism:
    """6. 确定性：两次 apply_policy 同输入同输出。"""

    def test_same_input_produces_same_verdict(self):
        policy = ValidationPolicy(max_warnings=5)
        report = _make_report(
            [
                Finding("T-SPOOF-1", "high"),
                Finding("T-DOS-1", "medium"),
                Finding("T-PATT-1", "low"),
            ],
            warnings=["w"],
        )
        assert apply_policy(report, policy) == apply_policy(report, policy)

    def test_repeated_calls_stable_across_verdicts(self):
        cases = [
            (ValidationPolicy(), _make_report([Finding("T-SPOOF-1", "critical")]), "fail"),
            (ValidationPolicy(), _make_report([Finding("T-DOS-1", "medium")]), "pass_with_warnings"),
            (ValidationPolicy(), _make_report(), "pass"),
        ]
        for policy, report, expected in cases:
            first = apply_policy(report, policy)
            second = apply_policy(report, policy)
            assert first == expected
            assert first == second
