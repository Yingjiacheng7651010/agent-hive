"""Tests for card-data-compliance: DataMasker, DataLifecycleManager, ContentModerator, AuditLogger."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from agent_hive.data_compliance import (
    AuditLogger,
    AuditRecord,
    CleanupReport,
    ContentModerator,
    DataLifecycleManager,
    DataMasker,
    DataRetentionPolicy,
    DeleteReport,
    MaskRule,
    MemoryAuditStore,
    ModerationFlag,
    ModerationResult,
)


class TestDataMasker:
    """DataMasker 脱敏器测试。"""

    def test_mask_api_key(self):
        masker = DataMasker()
        text = "my api key is sk-abc123def456ghi789jkl012"
        masked = masker.mask(text)
        # 20+ 字符的 base64 字符串应该被脱敏
        assert "sk-abc123def456ghi789jkl012" not in masked

    def test_mask_email(self):
        masker = DataMasker()
        text = "contact me at user@example.com"
        masked = masker.mask(text)
        assert "user@example.com" not in masked
        assert "***" in masked

    def test_mask_credit_card(self):
        masker = DataMasker()
        text = "card: 1234567890123456789"
        masked = masker.mask(text)
        # 17-19 位数字应该被脱敏
        assert "1234567890123456789" not in masked

    def test_mask_ssn(self):
        masker = DataMasker()
        text = "SSN: 123-45-6789"
        masked = masker.mask(text)
        assert "123-45-6789" not in masked

    def test_mask_dict(self):
        masker = DataMasker()
        data = {
            "logs": {
                "content": "my key is abc123def456ghi789jkl012",
            },
            "name": "John Doe",
            "cost": {
                "api_key": "sk-abc123def456ghi789jkl012mnopqr",
            },
        }
        masked = masker.mask_dict(data)
        # logs.content 字段被脱敏
        inner = masked["logs"]["content"]
        assert "abc123def456ghi789jkl012" not in inner
        # name 字段保留
        assert masked["name"] == "John Doe"
        # cost.api_key 字段被脱敏
        assert "sk-abc123def456ghi789jkl012mnopqr" not in masked["cost"]["api_key"]

    def test_mask_list(self):
        masker = DataMasker()
        data = {"items": ["user@example.com", "hello world"]}
        masked = masker.mask_dict(data)
        assert "user@example.com" not in masked["items"][0]
        assert masked["items"][1] == "hello world"

    def test_register_custom_rule(self):
        masker = DataMasker()
        masker.register_rule(MaskRule(pattern=r'\b\d{3}\b', replacement="[REDACTED]"))
        text = "code 123 and 456"
        masked = masker.mask(text)
        assert "123" not in masked
        assert "456" not in masked
        assert "[REDACTED]" in masked

    def test_field_path_filtering(self):
        """字段路径过滤：只脱敏特定路径的字段。"""
        rules = [
            MaskRule(pattern=r'secret', replacement="***",
                     field_paths=["data.password"]),
        ]
        masker = DataMasker(rules=rules)
        data = {"data": {"password": "my_secret_key", "name": "no_secret_here"}}
        masked = masker.mask_dict(data)
        # password 字段被脱敏
        assert "my_secret_key" not in masked["data"]["password"]
        # name 字段被保留
        assert masked["data"]["name"] == "no_secret_here"

    def test_list_rules(self):
        masker = DataMasker(rules=[])
        masker.register_rule(MaskRule(pattern=r'test', replacement="***"))
        assert len(masker.list_rules()) == 1

    def test_backward_compatibility(self):
        """不配置脱敏规则时使用默认规则。"""
        masker = DataMasker()
        text = "normal text without sensitive data"
        masked = masker.mask(text)
        assert masked == text  # 无敏感数据时不变


class TestDataLifecycleManager:
    """DataLifecycleManager 生命周期管理器测试。"""

    def test_cleanup_expired_empty(self):
        manager = DataLifecycleManager()
        report = manager.cleanup_expired()
        assert isinstance(report, CleanupReport)
        assert report.cleaned_runs == 0

    def test_export_tenant_data(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DataLifecycleManager(data_root=tmpdir)
            export_path = manager.export_tenant_data("tenant_abc")
            assert export_path is not None
            assert Path(export_path).exists()

    def test_delete_tenant_data(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DataLifecycleManager(data_root=tmpdir)
            report = manager.delete_tenant_data("tenant_abc")
            assert isinstance(report, DeleteReport)
            assert report.preserved_audit_logs == 0  # 审计日志不可删除

    def test_set_policy(self):
        manager = DataLifecycleManager()
        new_policy = DataRetentionPolicy(run_logs_days=60)
        manager.set_policy(new_policy)
        assert manager._policy.run_logs_days == 60


class TestContentModerator:
    """ContentModerator 内容审核测试。"""

    def test_clean_content_passes(self):
        moderator = ContentModerator(rules=[
            {"type": "toxic", "keywords": ["badword", "hate"]},
        ])
        result = moderator.check("hello world")
        assert result.passed is True
        assert len(result.flags) == 0

    def test_toxic_content_flagged(self):
        moderator = ContentModerator(rules=[
            {"type": "toxic", "keywords": ["badword", "hate"]},
        ])
        result = moderator.check("this contains badword")
        assert result.passed is False
        assert len(result.flags) >= 1

    def test_pii_detection(self):
        moderator = ContentModerator(rules=[
            {"type": "pii", "patterns": [r'\b\d{3}-\d{2}-\d{4}\b']},
        ])
        result = moderator.check("SSN: 123-45-6789")
        assert result.passed is False
        assert len(result.flags) >= 1

    def test_code_injection_detection(self):
        moderator = ContentModerator(rules=[
            {"type": "code_injection", "keywords": ["eval(", "exec("]},
        ])
        result = moderator.check("use eval(x) to execute")
        assert result.passed is False
        assert any(f.type == "code_injection" for f in result.flags)

    def test_multiple_flags(self):
        moderator = ContentModerator(rules=[
            {"type": "toxic", "keywords": ["badword", "hate"]},
            {"type": "pii", "patterns": [r'\b[\w\.-]+@[\w\.-]+\.\w+\b']},
        ])
        result = moderator.check("badword at user@example.com")
        assert result.passed is False
        assert len(result.flags) >= 2

    def test_no_rules_passes(self):
        moderator = ContentModerator(rules=[])
        result = moderator.check("any content")
        assert result.passed is True


class TestMemoryAuditStore:
    """MemoryAuditStore 审计存储测试。"""

    def test_append_and_query(self):
        store = MemoryAuditStore()
        record = AuditRecord(
            event_type="run_start", actor="tenant_abc",
            resource="run_001",
        )
        store.append(record)
        results = store.query({}, (0, time.time() + 1))
        assert len(results) == 1
        assert results[0].event_type == "run_start"

    def test_query_filtered(self):
        store = MemoryAuditStore()
        store.append(AuditRecord(event_type="run_start", actor="tenant_a", resource="run_1"))
        store.append(AuditRecord(event_type="run_end", actor="tenant_a", resource="run_1"))
        store.append(AuditRecord(event_type="run_start", actor="tenant_b", resource="run_2"))

        results = store.query({"event_type": "run_start"}, (0, time.time() + 1))
        assert len(results) == 2

        results = store.query({"actor": "tenant_b"}, (0, time.time() + 1))
        assert len(results) == 1

    def test_export(self):
        store = MemoryAuditStore()
        store.append(AuditRecord(event_type="run_start", actor="tenant_a", resource="run_1"))
        export_str = store.export((0, time.time() + 1))
        exported = json.loads(export_str)
        assert len(exported) == 1
        assert exported[0]["event_type"] == "run_start"


class TestAuditLogger:
    """AuditLogger 审计日志记录器测试。"""

    def test_record_and_query(self):
        logger = AuditLogger()
        logger.record(AuditRecord(
            event_type="run_start", actor="tenant_abc",
            resource="run_001", details={"goal": "test"},
        ))
        records = logger.query({"event_type": "run_start"})
        assert len(records) == 1
        assert records[0].actor == "tenant_abc"

    def test_auto_id(self):
        logger = AuditLogger()
        logger.record(AuditRecord(event_type="test", actor="user", resource="res"))
        records = logger.query({"event_type": "test"})
        assert len(records) == 1
        assert records[0].id.startswith("audit_")

    def test_immutable(self):
        logger = AuditLogger()
        record = AuditRecord(event_type="test", actor="user", resource="res")
        logger.record(record)
        assert record.immutable is True

    def test_export(self):
        logger = AuditLogger()
        logger.record(AuditRecord(event_type="run_start", actor="user", resource="run_1"))
        export_str = logger.export()
        exported = json.loads(export_str)
        assert len(exported) >= 1