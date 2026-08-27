# 工作卡片：card-multi-tenancy —— 多租户隔离与资源配额

> 优先级：P2 | 类型：架构/安全 | 依赖：card-distributed-engine（可选，可先独立实现）
> 负责人：系统架构师 / 基础设施 | 轮次上限：3

---

## 1. 问题陈述

当前架构完全不支持多租户：
- 所有 run 共享同一个 SQLite checkpointer（并发读写会崩）
- 没有租户级别的数据隔离（A 租户的 agent 能看到 B 租户的 context）
- 没有资源配额（一个租户的 runaway agent 可以耗尽所有资源）
- 没有运行时 side-channel 攻击防护

## 2. 目标

建立多租户隔离体系：租户标识 → 数据隔离 → 资源配额 → 公平调度，让 agent-hive 可以安全地服务多个租户。

## 3. 接口契约

### 3.1 核心数据结构

```python
# agent_hive/multi_tenancy.py

@dataclass
class Tenant:
    """租户定义。"""
    id: str                              # 租户 ID，如 "tenant_abc123"
    name: str                            # 租户名称
    tier: Literal["free", "pro", "enterprise"] = "free"
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    config: "TenantConfig" = field(default_factory=lambda: TenantConfig())

@dataclass
class TenantConfig:
    """租户配置。"""
    max_concurrent_runs: int = 5         # 最大并发 run 数
    max_tokens_per_run: int = 100000     # 单次 run 最大 token 数
    max_tokens_per_day: int = 1000000    # 每日最大 token 数
    allowed_models: list[str] = field(default_factory=lambda: ["deepseek-chat"])
    allowed_roles: list[str] = field(default_factory=list)
    # 空列表表示所有角色可用
    data_retention_days: int = 30        # 数据保留天数
    allowed_tools: list[str] = field(default_factory=list)
    # 空列表表示所有工具可用

@dataclass
class ResourceQuota:
    """资源配额快照。"""
    tenant_id: str
    runs_today: int = 0
    tokens_today: int = 0
    concurrent_runs: int = 0
    last_reset_time: float = field(default_factory=time.time)
```

### 3.2 核心接口

```python
class TenantManager:
    """租户管理器：注册、认证、配置。"""

    def register(self, tenant: Tenant) -> bool:
        """注册新租户。"""

    def get(self, tenant_id: str) -> Tenant | None:
        """获取租户信息。"""

    def authenticate(self, api_key: str) -> Tenant | None:
        """通过 API Key 认证租户。"""

    def update_config(self, tenant_id: str, config: TenantConfig) -> bool:
        """更新租户配置。"""


class QuotaEnforcer:
    """配额执行器：在每次 run 启动前检查配额。"""

    def __init__(self, tenant_manager: TenantManager):
        ...

    def check_before_run(self, tenant_id: str) -> QuotaCheckResult:
        """检查是否允许启动新 run。

        检查项：并发数、每日 token 限额、模型白名单。
        """

    def record_run_start(self, tenant_id: str):
        """记录 run 启动。"""

    def record_run_end(self, tenant_id: str, tokens_used: int):
        """记录 run 结束，释放配额。"""

    def reset_daily_quotas(self):
        """重置每日配额（定时任务调用）。"""


@dataclass
class QuotaCheckResult:
    allowed: bool
    reason: str = ""
    current: ResourceQuota | None = None
    suggested_action: str = ""  # "wait", "upgrade", "reduce_scope"
```

## 4. 实现方案

### 4.1 数据隔离策略

```
存储层隔离（按租户分目录/分数据库）：
  runs/
  ├── tenant_abc123/
  │   ├── 20261015_abc123/       # run 目录
  │   │   ├── checkpoint.db      # 独立 checkpoint
  │   │   └── workspace/
  │   └── 20261015_def456/
  └── tenant_xyz789/
      ├── 20261015_ghi789/
      └── ...

实现方式：在为每个 run 创建目录时，路径前缀带上 tenant_id。
safe_run_dir(run_id, tenant_id) 返回 runs/<tenant_id>/<run_id>/
```

### 4.2 资源配额策略

```
公平调度（Fair Scheduling）：
  1. 每个租户有独立的配额计数器（内存中 + 持久化到 SQLite）
  2. 配额按天重置（定时任务或 lazy reset）
  3. 配额超限时返回明确的拒绝原因 + 建议操作
  4. 企业版租户的配额是免费版的 10 倍

配额检查链：
  run 启动 → 检查并发数 → 检查每日 token → 检查模型白名单 → 允许/拒绝
```

### 4.3 认证策略

```python
# 简单 API Key 认证（第一阶段）
# 后续可扩展为 OAuth 2.0 / JWT

class ApiKeyAuth:
    def __init__(self):
        self.keys: dict[str, str] = {}  # api_key -> tenant_id

    def generate_key(self, tenant_id: str) -> str:
        key = f"hive_{uuid.hex()}_{secrets.token_hex(16)}"
        self.keys[key] = tenant_id
        return key

    def authenticate(self, api_key: str) -> str | None:
        return self.keys.get(api_key)
```

## 5. 交付物清单

| 工件 | 位置 | 说明 |
|------|------|------|
| 租户管理器 | `agent_hive/multi_tenancy.py` | TenantManager + Tenant/TenantConfig |
| 配额执行器 | 同上 | QuotaEnforcer + ResourceQuota |
| API Key 认证 | 同上 | ApiKeyAuth 简单认证 |
| 路径隔离 | 更新 `agent_hive/paths.py` | `safe_run_dir` 增加 tenant_id 参数 |
| 单元测试 | `tests/test_multi_tenancy.py` | 覆盖注册/认证/配额/隔离 |
| 配置示例 | `.env.example` 补充 | `HIVE_TENANT_ID`、`HIVE_API_KEY` |

## 6. 验收标准

- [ ] 不同租户的 run 目录完全隔离（路径前缀不同）
- [ ] 租户 A 无法读取租户 B 的 run 数据
- [ ] 并发 run 数超限时拒绝新 run，返回明确错误
- [ ] 每日 token 限额超限时拒绝新 run，返回"已用 x/x，建议升级套餐或明日再试"
- [ ] 租户配置白名单生效（禁止的模型/角色/工具不可用）
- [ ] API Key 认证可工作，无效 key 被拒绝
- [ ] 配额按天自动重置（第一次检查时 lazy reset）
- [ ] 不配置租户时，行为与现有代码一致（默认单租户，向后兼容）

## 7. 联动关系

| 联动卡片 | 关系 | 说明 |
|---------|------|------|
| card-distributed-engine | 配合 | 分布式引擎中租户隔离需跨节点一致的配额计数器（Redis） |
| card-cost-control | 数据源 | 成本控制器的数据按租户分拆 |
| card-data-compliance | 配合 | 数据保留策略按租户配置执行 |
| card-tool-registry | 配合 | 工具注册表的 `required_roles` 结合租户的 `allowed_tools` |

## 8. 实现效果

**改造前**：支持单用户，多用户并发使用会互相干扰。无法区分不同用户的成本消耗。

**改造后**：支持多租户，每个租户有独立的存储空间、资源配额、配置白名单。可以按租户追踪成本消耗。"免费版租户最多 5 个并发 run、每天 100 万 token"——产品化 SaaS 的基础能力。