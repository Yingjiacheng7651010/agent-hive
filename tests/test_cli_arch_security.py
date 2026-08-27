"""架构安全验证 CLI 策略回归测试（card-ai-arch-security 批次 2）。

只测 main 模块的纯函数 seam（策略加载 / 审计留痕），不真跑 CLI 入口。
"""
from __future__ import annotations

import json

import pytest

from agent_hive import main as main_module


class TestLoadSecurityPolicy:
    def test_none_returns_empty(self):
        assert main_module._load_security_policy(None) == {}

    def test_valid_policy_file(self, tmp_path):
        p = tmp_path / "policy.json"
        p.write_text(json.dumps({
            "fail_on_severity": "critical",
            "llm_enabled": False,
            "exclusions": ["T-DISC-1"],
        }), encoding="utf-8")
        out = main_module._load_security_policy(str(p))
        assert out["fail_on_severity"] == "critical"
        assert out["llm_enabled"] is False

    def test_relaxed_fail_on_severity_rejected(self, tmp_path):
        for bad in ("low", "medium", "none"):
            p = tmp_path / "policy.json"
            p.write_text(json.dumps({"fail_on_severity": bad}), encoding="utf-8")
            with pytest.raises(SystemExit):
                main_module._load_security_policy(str(p))

    def test_unknown_field_rejected(self, tmp_path):
        p = tmp_path / "policy.json"
        p.write_text(json.dumps({"fail_on_severity": "high", "bogus": 1}), encoding="utf-8")
        with pytest.raises(SystemExit):
            main_module._load_security_policy(str(p))

    def test_malformed_json_rejected(self, tmp_path):
        p = tmp_path / "policy.json"
        p.write_text("{not json", encoding="utf-8")
        with pytest.raises(SystemExit):
            main_module._load_security_policy(str(p))

    def test_missing_file_rejected(self, tmp_path):
        with pytest.raises(SystemExit):
            main_module._load_security_policy(str(tmp_path / "nope.json"))


class TestWriteSecurityAudit:
    def test_no_audit_when_nothing_flagged(self, tmp_path, monkeypatch):
        def fake_srd(run_id):
            return tmp_path / run_id

        monkeypatch.setattr(main_module, "safe_run_dir", fake_srd)
        main_module._write_security_audit("run-a", False, False)
        assert not (tmp_path / "run-a" / "security-audit.md").exists()

    def test_audit_written_when_skip_or_allow(self, tmp_path, monkeypatch):
        monkeypatch.setattr(main_module, "safe_run_dir", lambda run_id: tmp_path / run_id)
        main_module._write_security_audit("run-b", True, False)
        audit = tmp_path / "run-b" / "security-audit.md"
        assert audit.exists()
        text = audit.read_text(encoding="utf-8")
        assert "skip_arch_security" in text
        assert "如实标注" in text