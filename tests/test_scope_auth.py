"""Tests for agent_hive.scope_auth: 动态验证授权清单 ScopeManifest / ScopeAuthorizer。

覆盖硬门禁语义：白名单命中、白名单外拒绝、私网/保留地址不可绕过、
时间窗、空 scope_id、hostname 目标回环拒绝、审计日志、清单加载与往返。
"""
from __future__ import annotations

import json
import time

import pytest

from agent_hive.data_compliance import AuditLogger
from agent_hive.scope_auth import ScopeAuthorizer, ScopeDecision, ScopeManifest

PUBLIC_IP = "93.184.216.34"  # example.com，公网地址


def make_manifest(**overrides) -> ScopeManifest:
    """构造默认授权清单；用 overrides 覆盖字段。"""
    base = {
        "scope_id": "scope-001",
        "targets": [PUBLIC_IP],
    }
    base.update(overrides)
    return ScopeManifest(**base)


class TestAuthorizeTarget:
    """authorize_target 硬门禁裁决。"""

    def test_whitelist_hit_allowed(self):
        """白名单命中：公网 IP 在 targets 内且非私网 → allowed=True。"""
        authorizer = ScopeAuthorizer()
        manifest = make_manifest()
        decision = authorizer.authorize_target(manifest, PUBLIC_IP)
        assert decision.allowed is True
        assert decision.is_private_network is False

    def test_outside_whitelist_denied(self):
        """白名单外 → 拒绝且 reason 含「白名单」。"""
        authorizer = ScopeAuthorizer()
        manifest = make_manifest()
        decision = authorizer.authorize_target(manifest, "1.1.1.1")
        assert decision.allowed is False
        assert "白名单" in decision.reason

    def test_private_network_hard_deny(self):
        """私网硬拒绝：192.168.1.10 即使在 targets 内 → 拒绝且 is_private_network=True（不可绕过）。"""
        authorizer = ScopeAuthorizer()
        manifest = make_manifest(targets=["192.168.1.10"])
        decision = authorizer.authorize_target(manifest, "192.168.1.10")
        assert decision.allowed is False
        assert decision.is_private_network is True

    @pytest.mark.parametrize("target", [
        "127.0.0.1",       # 回环
        "224.0.0.1",       # 组播
        "169.254.0.1",     # 链路本地
        "0.0.0.0",         # 未指定
    ])
    def test_reserved_ranges_hard_deny(self, target):
        """回环/组播/链路本地/未指定同样硬拒绝，即使被显式列入 targets。"""
        authorizer = ScopeAuthorizer()
        manifest = make_manifest(targets=[target])
        decision = authorizer.authorize_target(manifest, target)
        assert decision.allowed is False
        assert decision.is_private_network is True

    def test_expired_window_denied(self):
        """时间窗过期：valid_until 为过去时间 → 拒绝「过期」。"""
        authorizer = ScopeAuthorizer()
        manifest = make_manifest(valid_until=time.time() - 100)
        decision = authorizer.authorize_target(manifest, PUBLIC_IP)
        assert decision.allowed is False
        assert "过期" in decision.reason

    def test_long_term_window_valid(self):
        """valid_until==0 视为长期授权：公网白名单目标仍放行。"""
        authorizer = ScopeAuthorizer()
        manifest = make_manifest(valid_until=0)
        decision = authorizer.authorize_target(manifest, PUBLIC_IP)
        assert decision.allowed is True

    def test_empty_scope_id_denied(self):
        """空 scope_id → 拒绝「未配置授权清单」。"""
        authorizer = ScopeAuthorizer()
        manifest = make_manifest(scope_id="")
        decision = authorizer.authorize_target(manifest, PUBLIC_IP)
        assert decision.allowed is False
        assert "授权清单" in decision.reason

    def test_localhost_denied(self):
        """hostname 目标 'localhost' → 解析为回环 → 拒绝（即使列入 targets）。"""
        authorizer = ScopeAuthorizer()
        manifest = make_manifest(targets=["localhost"])
        decision = authorizer.authorize_target(manifest, "localhost")
        assert decision.allowed is False
        assert decision.is_private_network is True

    def test_hostname_in_whitelist_allowed(self):
        """hostname 解析出的公网 IP 命中 targets 内同名 hostname → 放行。"""
        authorizer = ScopeAuthorizer()
        manifest = make_manifest(targets=["example.com"])
        decision = authorizer.authorize_target(manifest, "example.com")
        # 依赖本地 DNS 解析（example.com 为公网地址，不得判私网）；解析失败则拒绝
        if decision.reason == "目标解析失败":
            pytest.skip("当前环境无法解析 example.com")
        assert decision.allowed is True

    def test_unresolvable_target_denied(self):
        """无法解析的目标 → 拒绝。"""
        authorizer = ScopeAuthorizer()
        manifest = make_manifest()
        decision = authorizer.authorize_target(manifest, "no-such-host.invalid")
        assert decision.allowed is False


class TestAuditLog:
    """write_audit_log 审计记录。"""

    def test_write_audit_log_queryable(self):
        """写入后 audit_logger.query 可查到记录（event_type='dynamic_scope_audit'）。"""
        logger = AuditLogger()
        authorizer = ScopeAuthorizer(audit_logger=logger)
        manifest = make_manifest(
            tenant_id="tenant_x", signer="alice", approver="bob",
            reason="渗透测试授权",
        )
        authorizer.write_audit_log(manifest, PUBLIC_IP, "hash123")

        records = logger.query({"event_type": "dynamic_scope_audit"})
        assert len(records) == 1
        record = records[0]
        assert record.actor == "tenant_x"
        assert record.resource == PUBLIC_IP
        assert record.details == {
            "scope_id": "scope-001",
            "command_hash": "hash123",
            "signer": "alice",
            "reason": "渗透测试授权",
            "approver": "bob",
        }

    def test_actor_falls_back_to_signer(self):
        """tenant_id 为空时 actor 回退为 signer。"""
        logger = AuditLogger()
        authorizer = ScopeAuthorizer(audit_logger=logger)
        manifest = make_manifest(tenant_id="", signer="alice")
        authorizer.write_audit_log(manifest, PUBLIC_IP, "hash456")
        records = logger.query({"event_type": "dynamic_scope_audit"})
        assert len(records) == 1
        assert records[0].actor == "alice"


class TestLoadManifest:
    """load_manifest / to_json。"""

    def test_load_valid_json(self, tmp_path):
        """合法 JSON 文件 → ScopeManifest。"""
        path = tmp_path / "manifest.json"
        path.write_text(
            json.dumps({
                "scope_id": "scope-abc",
                "tenant_id": "tenant_y",
                "targets": ["1.2.3.4", "example.com"],
                "valid_from": 100,
                "valid_until": 200,
                "prohibited_cidrs": ["10.0.0.0/8"],
                "allowed_ports": [443, 8443],
                "signer": "alice",
                "approver": "bob",
                "reason": "测试授权",
            }),
            encoding="utf-8",
        )
        manifest = ScopeAuthorizer().load_manifest(str(path))
        assert isinstance(manifest, ScopeManifest)
        assert manifest.scope_id == "scope-abc"
        assert manifest.tenant_id == "tenant_y"
        assert manifest.targets == ["1.2.3.4", "example.com"]
        assert manifest.valid_from == 100.0
        assert manifest.valid_until == 200.0
        assert manifest.prohibited_cidrs == ["10.0.0.0/8"]
        assert manifest.allowed_ports == [443, 8443]

    def test_load_invalid_json_raises(self, tmp_path):
        """非法 JSON → ValueError。"""
        path = tmp_path / "bad.json"
        path.write_text("{not valid json", encoding="utf-8")
        with pytest.raises(ValueError):
            ScopeAuthorizer().load_manifest(str(path))

    def test_load_missing_scope_id_raises(self, tmp_path):
        """缺 scope_id → ValueError。"""
        path = tmp_path / "no_scope.json"
        path.write_text(json.dumps({"targets": ["1.2.3.4"]}), encoding="utf-8")
        with pytest.raises(ValueError):
            ScopeAuthorizer().load_manifest(str(path))

    def test_load_empty_targets_raises(self, tmp_path):
        """targets 为空列表 → ValueError。"""
        path = tmp_path / "no_targets.json"
        path.write_text(json.dumps({"scope_id": "s1", "targets": []}), encoding="utf-8")
        with pytest.raises(ValueError):
            ScopeAuthorizer().load_manifest(str(path))

    def test_to_json_load_roundtrip(self, tmp_path):
        """to_json / load_manifest 往返一致。"""
        authorizer = ScopeAuthorizer()
        manifest = make_manifest(
            tenant_id="tenant_z",
            targets=[PUBLIC_IP, "example.com"],
            valid_from=0.0,
            valid_until=0.0,
            allowed_ports=[443],
            signer="alice",
            approver="bob",
            reason="往返测试",
        )
        path = tmp_path / "roundtrip.json"
        path.write_text(authorizer.to_json(manifest), encoding="utf-8")
        loaded = authorizer.load_manifest(str(path))
        assert loaded == manifest
