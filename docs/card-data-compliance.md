# 工作卡片：card-data-compliance —— 数据合规与隐私保护

> 优先级：P2 | 类型：合规 | 依赖：card-multi-tenancy（建议先完成）
> 负责人：安全工程 / 合规团队 | 轮次上限：3

---

## 1. 问题陈述

当前架构没有任何数据合规机制：
- agent 执行日志永久保留，无自动清理策略
- 敏感数据（API Key、PII）在日志中明文存储，无脱敏处理
- agent 输出内容未经审核，可能包含不当内容
- 模型训练数据可能被 agent 产生的数据污染
- 没有数据导出/删除接口（无法满足 GDPR 合规要求）

## 2. 目标

建立完整的数据合规体系：日志策略 → 敏感数据脱敏 → 内容审核 → 数据生命周期管理 → 合规审计，让 agent-hive 可以满足 GDPR 等合规要求。

## 3. 接口契约

### 3.1 核心数据结构

```python
# agent_hive/data_compliance.py

@dataclass
class DataRetentionPolicy:
    """数据保留策略。"""
    run_logs_days: int = 30              # run 日志保留天数
    checkpoints_days: int = 7            # checkpoint 保留天数
    audit_logs_days: int = 365           # 审计日志保留天数（不可删除）
    cost_records_days: int = 90          # 成本记录保留天数
    auto_cleanup_enabled: bool = True    # 是否自动清理

@dataclass
class MaskRule:
    """敏感数据脱敏规则。"""
    pattern: str                         # 正则表达式
    replacement: str = "***"             # 替换字符串
    field_paths: list[str] | None = None
    # 指定字段路径，如 ["logs.content", "cost.api_key"]
    # None 表示全局匹配

@dataclass
class AuditRecord:
    """审计记录。"""
    id: str
    timestamp: float
    event_type: str                      # "run_start", "run_end", "data_export", "data_delete"
    actor: str                           # 操作者（tenant_id / user_id）
    resource: str                        # 操作资源（run_id / file_path）
    details: dict = field(default_factory=dict)
    ip_address: str = ""
    immutable: bool = True               # 审计记录不可删除
```

### 3.2 核心接口

```python
class DataMasker:
    """敏感数据脱敏器。"""

    def register_rule(self, rule: MaskRule):
        """注册脱敏规则。"""

    def mask(self, data: str, context: str = "") -> str:
        """对数据进行脱敏处理。"""

    def mask_dict(self, data: dict, path: str = "") -> dict:
        """对字典数据进行脱敏处理（递归遍历字段）。"""


class DataLifecycleManager:
    """数据生命周期管理器。"""

    def __init__(self, policy: DataRetentionPolicy):
        ...

    def cleanup_expired(self) -> CleanupReport:
        """清理过期数据。返回清理报告。"""

    def export_tenant_data(self, tenant_id: str, formats: list[str]) -> str:
        """导出租户数据（GDPR 数据可移植性要求）。"""

    def delete_tenant_data(self, tenant_id: str) -> DeleteReport:
        """删除租户所有数据（GDPR 被遗忘权要求）。"""


@dataclass
class CleanupReport:
    cleaned_runs: int = 0
    cleaned_checkpoints: int = 0
    freed_space_bytes: int = 0
    errors: list[str] = field(default_factory=list)

@dataclass
class DeleteReport:
    deleted_runs: int = 0
    deleted_checkpoints: int = 0
    preserved_audit_logs: int = 0        # 审计日志不可删除
    errors: list[str] = field(default_factory=list)


class ContentModerator:
    """Agent 输出内容审核。"""

    def __init__(self, rules: list[dict]):
        """
        rules: [
            {"type": "pii", "patterns": [...]},
            {"type": "toxic", "keywords": [...]},
            {"type": "code_injection", "patterns": [...]},
        ]
        """

    def check(self, content: str) -> ModerationResult:
        """检查内容是否合规。"""


@dataclass
class ModerationResult:
    passed: bool
    flags: list[ModerationFlag] = field(default_factory=list)

@dataclass
class ModerationFlag:
    type: str                            # "pii", "toxic", "code_injection"
    severity: Literal["low", "medium", "high"]
    matched: str                         # 匹配的内容片段
    suggestion: str = ""                 # 处理建议
```

## 4. 实现方案

### 4.1 脱敏规则

```python
# 默认脱敏规则
DEFAULT_MASK_RULES = [
    MaskRule(pattern=r'[A-Za-z0-9+/]{20,}={0,2}', replacement="***",
             field_paths=["logs.content", "prompt.content"]),
    # 疑似 API Key 的 base64 字符串
    MaskRule(pattern=r'[A-Za-z0-9_\-]{20,}', replacement="***",
             field_paths=["cost.api_key", "env.*"]),
    # 疑似密钥的字符串
    MaskRule(pattern=r'\b\d{17,19}\b', replacement="***"),
    # 疑似银行卡/信用卡号
    MaskRule(pattern=r'\b\d{3}-\d{2}-\d{4}\b', replacement="***"),
    # 疑似美国 SSN
    MaskRule(pattern=r'\b[\w\.-]+@[\w\.-]+\.\w+\b', replacement="***",
             severity="low"),
    # 邮箱地址（低风险，根据场景决定是否脱敏）
]
```

### 4.2 数据保留策略

```python
# 默认保留策略
DEFAULT_RETENTION_POLICY = DataRetentionPolicy(
    run_logs_days=30,          # run 日志保留 30 天
    checkpoints_days=7,        # checkpoint 只保留 7 天
    audit_logs_days=365,       # 审计日志保留 1 年
    cost_records_days=90,      # 成本记录保留 90 天
    auto_cleanup_enabled=True,
)
```

### 4.3 内容审核策略

```
第一阶段（基本）：关键词黑名单 + 正则表达式模式匹配
  - 敏感词过滤（暴力、色情、仇恨言论等）
  - 代码注入检测（eval, exec, os.system 等）
  - PII 检测（邮箱、手机号、身份证号等）

第二阶段（进阶）：LLM-as-judge 内容审核
  - 调用专门的审核模型或 API 进行语义级别审核
  - 上下文敏感的判断（"我打你" vs "你打我" 语义不同）
```

### 4.4 审计日志

```python
class AuditLogger:
    """审计日志记录器（日志不可删除、不可修改）。"""

    def __init__(self, store: AuditStore):
        self.store = store

    def record(self, event: AuditRecord):
        """记录审计事件。"""
        event.immutable = True  # 确保不可修改
        self.store.append(event)

    def query(self, filter_by: dict, time_range: tuple[float, float]) -> list[AuditRecord]:
        """查询审计日志。"""

    def export(self, time_range: tuple[float, float]) -> str:
        """导出审计日志（合规审计用）。"""
```

## 5. 交付物清单

| 工件 | 位置 | 说明 |
|------|------|------|
| 数据脱敏器 | `agent_hive/data_compliance.py` | DataMasker + 默认脱敏规则 |
| 数据生命周期管理器 | 同上 | DataLifecycleManager + 清理/导出/删除 |
| 内容审核器 | 同上 | ContentModerator + 审核规则 |
| 审计日志记录器 | 同上 | AuditLogger + 不可变日志存储 |
| 单元测试 | `tests/test_data_compliance.py` | 覆盖脱敏/清理/审核/审计 |
| 合规文档 | `docs/compliance-guide.md` | GDPR 合规指南 + 数据流图 |

## 6. 验收标准

- [ ] 默认脱敏规则可识别并脱敏 API Key、邮箱、银行卡号等敏感信息
- [ ] 脱敏处理在日志写入前完成，不存储明文敏感数据
- [ ] 数据生命周期管理器可清理过期 run 日志和 checkpoint
- [ ] 支持按租户导出所有数据（GDPR 数据可移植性）
- [ ] 支持按租户删除所有数据（GDPR 被遗忘权），审计日志除外
- [ ] 内容审核可检测并标记不当内容，不阻止 agent 执行但记录
- [ ] 审计日志不可删除、不可修改，可查询和导出
- [ ] 不配置任何合规策略时，行为与现有代码一致（向后兼容）

## 7. 联动关系

| 联动卡片 | 关系 | 说明 |
|---------|------|------|
| card-multi-tenancy | 依赖 | 租户级别数据隔离是合规的基础 |
| card-streaming | 消费 | 流式事件日志需经过脱敏处理 |
| card-tool-registry | 消费 | 工具调用记录需经过脱敏和审计 |
| card-cost-control | 消费 | 成本记录需经过脱敏处理 |
| card-async-hitl | 消费 | 审批记录需入审计日志 |

## 8. 实现效果

**改造前**：所有数据永久保留，敏感信息在日志中明文存储。无法满足 GDPR 合规要求。无法应对"请删除我的数据"的合规请求。

**改造后**：敏感数据自动脱敏（API Key 在日志中显示为 `***`）。数据按策略自动清理（run 日志保留 30 天）。支持一键导出/删除租户数据。审计日志完整记录所有操作，满足合规审计要求。可以对外宣称"符合 GDPR 合规标准"。