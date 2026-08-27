"""多租户隔离与资源配额 —— 租户标识 → 数据隔离 → 资源配额 → 公平调度。

核心策略：
1. TenantManager：租户注册、认证、配置管理
2. QuotaEnforcer：配额执行器，在每次 run 启动前检查配额
3. ApiKeyAuth：简单 API Key 认证
4. 路径隔离：按租户分目录存储
5. 向后兼容：不配置租户时行为与现有代码一致
"""
from __future__ import annotations

import secrets
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Literal

__all__ = [
    "Tenant",
    "TenantConfig",
    "ResourceQuota",
    "QuotaCheckResult",
    "TenantManager",
    "QuotaEnforcer",
    "ApiKeyAuth",
]

# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class TenantConfig:
    """租户配置。"""
    max_concurrent_runs: int = 5
    max_tokens_per_run: int = 100000
    max_tokens_per_day: int = 1000000
    allowed_models: list[str] = field(default_factory=lambda: ["deepseek-chat"])
    allowed_roles: list[str] = field(default_factory=list)
    data_retention_days: int = 30
    allowed_tools: list[str] = field(default_factory=list)


@dataclass
class Tenant:
    """租户定义。"""
    id: str
    name: str = ""
    tier: Literal["free", "pro", "enterprise"] = "free"
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    config: TenantConfig = field(default_factory=TenantConfig)


@dataclass
class ResourceQuota:
    """资源配额快照。"""
    tenant_id: str
    runs_today: int = 0
    tokens_today: int = 0
    concurrent_runs: int = 0
    last_reset_time: float = field(default_factory=time.time)


@dataclass
class QuotaCheckResult:
    """配额检查结果。"""
    allowed: bool
    reason: str = ""
    current: ResourceQuota | None = None
    suggested_action: str = ""


# ---------------------------------------------------------------------------
# ApiKeyAuth
# ---------------------------------------------------------------------------

class ApiKeyAuth:
    """简单 API Key 认证（第一阶段）。
    后续可扩展为 OAuth 2.0 / JWT。
    """

    def __init__(self):
        self._keys: dict[str, str] = {}  # api_key -> tenant_id
        self._lock = threading.Lock()

    def generate_key(self, tenant_id: str) -> str:
        """生成 API Key。"""
        key = f"hive_{uuid.uuid4().hex[:8]}_{secrets.token_hex(16)}"
        with self._lock:
            self._keys[key] = tenant_id
        return key

    def authenticate(self, api_key: str) -> str | None:
        """认证 API Key，返回 tenant_id。"""
        with self._lock:
            return self._keys.get(api_key)

    def revoke_key(self, api_key: str) -> bool:
        """吊销 API Key。"""
        with self._lock:
            if api_key in self._keys:
                del self._keys[api_key]
                return True
            return False

    def list_keys(self, tenant_id: str | None = None) -> list[str]:
        """列出 API Key（可选按租户过滤）。"""
        with self._lock:
            if tenant_id is None:
                return list(self._keys.keys())
            return [k for k, v in self._keys.items() if v == tenant_id]


# ---------------------------------------------------------------------------
# TenantManager
# ---------------------------------------------------------------------------

class TenantManager:
    """租户管理器：注册、认证、配置。"""

    def __init__(self, auth: ApiKeyAuth | None = None):
        self._tenants: dict[str, Tenant] = {}
        self._auth = auth or ApiKeyAuth()
        self._lock = threading.Lock()

    def register(self, tenant: Tenant) -> bool:
        """注册新租户。"""
        with self._lock:
            if tenant.id in self._tenants:
                return False
            self._tenants[tenant.id] = tenant
            return True

    def get(self, tenant_id: str) -> Tenant | None:
        """获取租户信息。"""
        with self._lock:
            return self._tenants.get(tenant_id)

    def authenticate(self, api_key: str) -> Tenant | None:
        """通过 API Key 认证租户。"""
        tenant_id = self._auth.authenticate(api_key)
        if tenant_id is None:
            return None
        return self.get(tenant_id)

    def update_config(self, tenant_id: str, config: TenantConfig) -> bool:
        """更新租户配置。"""
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if tenant is None:
                return False
            tenant.config = config
            return True

    def list_tenants(self) -> list[Tenant]:
        with self._lock:
            return list(self._tenants.values())

    def enable(self, tenant_id: str, enabled: bool = True) -> bool:
        """启用/禁用租户。"""
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if tenant is None:
                return False
            tenant.enabled = enabled
            return True

    def generate_api_key(self, tenant_id: str) -> str | None:
        """为租户生成 API Key。"""
        with self._lock:
            if tenant_id not in self._tenants:
                return None
            return self._auth.generate_key(tenant_id)


# ---------------------------------------------------------------------------
# QuotaEnforcer
# ---------------------------------------------------------------------------

class QuotaEnforcer:
    """配额执行器：在每次 run 启动前检查配额。"""

    def __init__(self, tenant_manager: TenantManager):
        self._tenant_manager = tenant_manager
        self._quotas: dict[str, ResourceQuota] = {}  # tenant_id -> quota
        self._lock = threading.RLock()

    def check_before_run(self, tenant_id: str) -> QuotaCheckResult:
        """检查是否允许启动新 run。

        检查项：租户启用状态、并发数、每日 token 限额、模型白名单。
        """
        tenant = self._tenant_manager.get(tenant_id)
        if tenant is None:
            return QuotaCheckResult(allowed=False, reason=f"租户 {tenant_id} 不存在")

        if not tenant.enabled:
            return QuotaCheckResult(allowed=False, reason="租户已禁用")

        config = tenant.config
        quota = self._get_or_create_quota(tenant_id)

        # 检查并发数
        if quota.concurrent_runs >= config.max_concurrent_runs:
            return QuotaCheckResult(
                allowed=False,
                reason=f"并发 run 数已达上限 ({config.max_concurrent_runs})",
                current=quota,
                suggested_action="wait",
            )

        # 检查每日 token 限额
        if quota.tokens_today >= config.max_tokens_per_day:
            return QuotaCheckResult(
                allowed=False,
                reason=f"每日 token 限额已用完 ({quota.tokens_today}/{config.max_tokens_per_day})",
                current=quota,
                suggested_action="upgrade",
            )

        return QuotaCheckResult(
            allowed=True,
            reason="配额充足",
            current=quota,
        )

    def record_run_start(self, tenant_id: str):
        """记录 run 启动。"""
        with self._lock:
            quota = self._get_or_create_quota(tenant_id)
            quota.concurrent_runs += 1
            quota.runs_today += 1

    def record_run_end(self, tenant_id: str, tokens_used: int):
        """记录 run 结束，释放配额。"""
        with self._lock:
            quota = self._get_or_create_quota(tenant_id)
            quota.concurrent_runs = max(0, quota.concurrent_runs - 1)
            quota.tokens_today += tokens_used

    def reset_daily_quotas(self):
        """重置每日配额（定时任务调用）。"""
        with self._lock:
            now = time.time()
            for quota in self._quotas.values():
                quota.runs_today = 0
                quota.tokens_today = 0
                quota.last_reset_time = now

    def get_quota(self, tenant_id: str) -> ResourceQuota | None:
        with self._lock:
            return self._quotas.get(tenant_id)

    def _get_or_create_quota(self, tenant_id: str) -> ResourceQuota:
        """获取或创建配额，自动 lazy reset。"""
        with self._lock:
            now = time.time()
            if tenant_id not in self._quotas:
                self._quotas[tenant_id] = ResourceQuota(tenant_id=tenant_id)
                return self._quotas[tenant_id]

            quota = self._quotas[tenant_id]
            # Lazy reset: 检查是否跨天
            last_reset = quota.last_reset_time
            if (now - last_reset) > 86400:  # 24 小时
                quota.runs_today = 0
                quota.tokens_today = 0
                quota.last_reset_time = now

            return quota

    def check_model_allowed(self, tenant_id: str, model: str) -> bool:
        """检查模型是否在租户白名单中。"""
        tenant = self._tenant_manager.get(tenant_id)
        if tenant is None:
            return False
        config = tenant.config
        if not config.allowed_models:
            return True  # 空列表表示所有模型可用
        return model in config.allowed_models

    def check_role_allowed(self, tenant_id: str, role: str) -> bool:
        """检查角色是否在租户白名单中。"""
        tenant = self._tenant_manager.get(tenant_id)
        if tenant is None:
            return False
        config = tenant.config
        if not config.allowed_roles:
            return True  # 空列表表示所有角色可用
        return role in config.allowed_roles


# ---------------------------------------------------------------------------
# 路径隔离辅助
# ---------------------------------------------------------------------------

def safe_run_dir_with_tenant(
    run_id: str,
    tenant_id: str = "",
    root: str | None = None,
) -> str:
    """按租户隔离的 run 目录路径。

    格式：runs/<tenant_id>/<run_id>/
    无 tenant_id 时保持原有行为：runs/<run_id>/
    """
    from pathlib import Path
    from .paths import safe_run_dir as _safe_run_dir

    if not tenant_id:
        return str(_safe_run_dir(run_id, root))

    if root is None:
        root = Path(__file__).resolve().parent.parent / "agent_hive" / "runs"
    root_path = Path(root).resolve()
    tenant_dir = root_path / tenant_id
    tenant_dir.mkdir(parents=True, exist_ok=True)
    return str(_safe_run_dir(run_id, str(tenant_dir)))