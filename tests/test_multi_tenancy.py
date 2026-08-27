"""Tests for card-multi-tenancy: TenantManager, QuotaEnforcer, ApiKeyAuth."""
from __future__ import annotations

import time

import pytest

from agent_hive.multi_tenancy import (
    ApiKeyAuth,
    QuotaCheckResult,
    QuotaEnforcer,
    Tenant,
    TenantConfig,
    TenantManager,
    safe_run_dir_with_tenant,
)


class TestApiKeyAuth:
    """ApiKeyAuth 认证测试。"""

    def test_generate_and_authenticate(self):
        auth = ApiKeyAuth()
        key = auth.generate_key("tenant_abc")
        assert key.startswith("hive_")
        assert auth.authenticate(key) == "tenant_abc"
        assert auth.authenticate("invalid_key") is None

    def test_revoke_key(self):
        auth = ApiKeyAuth()
        key = auth.generate_key("tenant_abc")
        assert auth.revoke_key(key) is True
        assert auth.authenticate(key) is None

    def test_list_keys(self):
        auth = ApiKeyAuth()
        k1 = auth.generate_key("tenant_a")
        k2 = auth.generate_key("tenant_a")
        auth.generate_key("tenant_b")
        keys_a = auth.list_keys("tenant_a")
        assert len(keys_a) == 2
        all_keys = auth.list_keys()
        assert len(all_keys) == 3


class TestTenantManager:
    """TenantManager 租户管理器测试。"""

    def test_register_and_get(self):
        manager = TenantManager()
        tenant = Tenant(id="tenant_abc", name="测试租户", tier="pro")
        assert manager.register(tenant) is True
        assert manager.get("tenant_abc") is tenant
        assert manager.get("nonexistent") is None

    def test_register_duplicate(self):
        manager = TenantManager()
        manager.register(Tenant(id="tenant_abc"))
        assert manager.register(Tenant(id="tenant_abc")) is False  # 重复

    def test_authenticate(self):
        manager = TenantManager()
        tenant = Tenant(id="tenant_abc", name="测试租户")
        manager.register(tenant)
        key = manager.generate_api_key("tenant_abc")
        assert key is not None
        authed = manager.authenticate(key)
        assert authed is not None
        assert authed.id == "tenant_abc"

    def test_authenticate_invalid_key(self):
        manager = TenantManager()
        assert manager.authenticate("invalid_key") is None

    def test_update_config(self):
        manager = TenantManager()
        manager.register(Tenant(id="tenant_abc"))
        config = TenantConfig(max_concurrent_runs=10)
        assert manager.update_config("tenant_abc", config) is True
        tenant = manager.get("tenant_abc")
        assert tenant is not None
        assert tenant.config.max_concurrent_runs == 10

    def test_update_config_nonexistent(self):
        manager = TenantManager()
        assert manager.update_config("nonexistent", TenantConfig()) is False

    def test_enable_disable(self):
        manager = TenantManager()
        manager.register(Tenant(id="tenant_abc"))
        assert manager.enable("tenant_abc", False) is True
        tenant = manager.get("tenant_abc")
        assert tenant is not None
        assert tenant.enabled is False

    def test_list_tenants(self):
        manager = TenantManager()
        manager.register(Tenant(id="tenant_a"))
        manager.register(Tenant(id="tenant_b"))
        assert len(manager.list_tenants()) == 2

    def test_generate_api_key_nonexistent(self):
        manager = TenantManager()
        assert manager.generate_api_key("nonexistent") is None


class TestQuotaEnforcer:
    """QuotaEnforcer 配额执行器测试。"""

    def test_check_before_run_allowed(self):
        manager = TenantManager()
        manager.register(Tenant(id="tenant_abc", tier="free"))
        enforcer = QuotaEnforcer(manager)
        result = enforcer.check_before_run("tenant_abc")
        assert result.allowed is True

    def test_check_before_run_nonexistent(self):
        manager = TenantManager()
        enforcer = QuotaEnforcer(manager)
        result = enforcer.check_before_run("nonexistent")
        assert result.allowed is False

    def test_check_before_run_disabled(self):
        manager = TenantManager()
        manager.register(Tenant(id="tenant_abc"))
        manager.enable("tenant_abc", False)
        enforcer = QuotaEnforcer(manager)
        result = enforcer.check_before_run("tenant_abc")
        assert result.allowed is False
        assert "禁用" in result.reason

    def test_concurrent_run_limit(self):
        manager = TenantManager()
        config = TenantConfig(max_concurrent_runs=2)
        manager.register(Tenant(id="tenant_abc", config=config))
        enforcer = QuotaEnforcer(manager)

        # 启动 2 个 run
        enforcer.record_run_start("tenant_abc")
        assert enforcer.check_before_run("tenant_abc").allowed is True
        enforcer.record_run_start("tenant_abc")

        # 第 3 个应该被拒绝
        result = enforcer.check_before_run("tenant_abc")
        assert result.allowed is False
        assert "并发" in result.reason

    def test_daily_token_limit(self):
        manager = TenantManager()
        config = TenantConfig(max_tokens_per_day=1000)
        manager.register(Tenant(id="tenant_abc", config=config))
        enforcer = QuotaEnforcer(manager)

        # 消耗 1000 tokens
        enforcer.record_run_start("tenant_abc")
        enforcer.record_run_end("tenant_abc", 1000)

        # 新的 run 应该被拒绝
        result = enforcer.check_before_run("tenant_abc")
        assert result.allowed is False
        assert "限额" in result.reason or "已用" in result.reason

    def test_record_run_end_releases_concurrent(self):
        manager = TenantManager()
        config = TenantConfig(max_concurrent_runs=1)
        manager.register(Tenant(id="tenant_abc", config=config))
        enforcer = QuotaEnforcer(manager)

        enforcer.record_run_start("tenant_abc")
        assert enforcer.check_before_run("tenant_abc").allowed is False
        enforcer.record_run_end("tenant_abc", 100)
        assert enforcer.check_before_run("tenant_abc").allowed is True

    def test_reset_daily_quotas(self):
        manager = TenantManager()
        manager.register(Tenant(id="tenant_abc"))
        enforcer = QuotaEnforcer(manager)
        enforcer.record_run_start("tenant_abc")
        enforcer.record_run_end("tenant_abc", 500)
        enforcer.reset_daily_quotas()
        quota = enforcer.get_quota("tenant_abc")
        assert quota is not None
        assert quota.tokens_today == 0
        assert quota.runs_today == 0

    def test_check_model_allowed(self):
        manager = TenantManager()
        config = TenantConfig(allowed_models=["deepseek-chat"])
        manager.register(Tenant(id="tenant_abc", config=config))
        enforcer = QuotaEnforcer(manager)
        assert enforcer.check_model_allowed("tenant_abc", "deepseek-chat") is True
        assert enforcer.check_model_allowed("tenant_abc", "gpt-4o") is False

    def test_check_model_allowed_empty_list(self):
        """空列表表示所有模型可用。"""
        manager = TenantManager()
        config = TenantConfig(allowed_models=[])
        manager.register(Tenant(id="tenant_abc", config=config))
        enforcer = QuotaEnforcer(manager)
        assert enforcer.check_model_allowed("tenant_abc", "any-model") is True

    def test_check_role_allowed(self):
        manager = TenantManager()
        config = TenantConfig(allowed_roles=["编码", "测试"])
        manager.register(Tenant(id="tenant_abc", config=config))
        enforcer = QuotaEnforcer(manager)
        assert enforcer.check_role_allowed("tenant_abc", "编码") is True
        assert enforcer.check_role_allowed("tenant_abc", "评审") is False

    def test_backward_compatibility_no_tenant(self):
        """不配置租户时，行为与现有代码一致。"""
        manager = TenantManager()
        enforcer = QuotaEnforcer(manager)
        # 未注册的租户返回 not allowed
        result = enforcer.check_before_run("default")
        assert result.allowed is False
        assert "不存在" in result.reason


class TestSafeRunDirWithTenant:
    """safe_run_dir_with_tenant 路径隔离测试。"""

    def test_without_tenant(self):
        path = safe_run_dir_with_tenant("run_001")
        assert "run_001" in path

    def test_with_tenant(self):
        path = safe_run_dir_with_tenant("run_001", tenant_id="tenant_abc")
        assert "tenant_abc" in path
        assert "run_001" in path