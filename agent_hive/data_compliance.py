"""数据合规与隐私保护 —— 日志策略 → 敏感数据脱敏 → 内容审核 → 审计日志。

核心策略：
1. DataMasker：敏感数据脱敏器，支持正则模式匹配 + 字段路径过滤
2. DataLifecycleManager：数据生命周期管理，清理过期数据
3. ContentModerator：内容审核，关键词/正则/模式匹配
4. AuditLogger：不可变审计日志
5. 向后兼容：不配置任何合规策略时行为与现有代码一致
"""
from __future__ import annotations

import json
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

__all__ = [
    "DataRetentionPolicy",
    "MaskRule",
    "AuditRecord",
    "CleanupReport",
    "DeleteReport",
    "ModerationResult",
    "ModerationFlag",
    "DataMasker",
    "DataLifecycleManager",
    "ContentModerator",
    "AuditLogger",
    "MemoryAuditStore",
]

# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class DataRetentionPolicy:
    """数据保留策略。"""
    run_logs_days: int = 30
    checkpoints_days: int = 7
    audit_logs_days: int = 365
    cost_records_days: int = 90
    auto_cleanup_enabled: bool = True


@dataclass
class MaskRule:
    """敏感数据脱敏规则。"""
    pattern: str
    replacement: str = "***"
    field_paths: list[str] | None = None
    severity: str = "medium"


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
    # 邮箱地址（低风险）
]


@dataclass
class AuditRecord:
    """审计记录。"""
    id: str = ""
    timestamp: float = field(default_factory=time.time)
    event_type: str = ""
    actor: str = ""
    resource: str = ""
    details: dict = field(default_factory=dict)
    ip_address: str = ""
    immutable: bool = True


@dataclass
class CleanupReport:
    """清理报告。"""
    cleaned_runs: int = 0
    cleaned_checkpoints: int = 0
    freed_space_bytes: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class DeleteReport:
    """删除报告。"""
    deleted_runs: int = 0
    deleted_checkpoints: int = 0
    preserved_audit_logs: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class ModerationResult:
    """审核结果。"""
    passed: bool
    flags: list["ModerationFlag"] = field(default_factory=list)


@dataclass
class ModerationFlag:
    """审核标记。"""
    type: str = ""
    severity: Literal["low", "medium", "high"] = "medium"
    matched: str = ""
    suggestion: str = ""


# ---------------------------------------------------------------------------
# DataMasker
# ---------------------------------------------------------------------------

class DataMasker:
    """敏感数据脱敏器。"""

    def __init__(self, rules: list[MaskRule] | None = None):
        if rules is None:
            self._rules = list(DEFAULT_MASK_RULES)
        else:
            self._rules = list(rules)
        self._compiled: list[tuple[re.Pattern, MaskRule]] = []
        self._lock = threading.Lock()
        self._compile_rules()

    def _compile_rules(self):
        with self._lock:
            self._compiled = [
                (re.compile(rule.pattern), rule) for rule in self._rules
            ]

    def register_rule(self, rule: MaskRule):
        """注册脱敏规则。"""
        with self._lock:
            self._rules.append(rule)
            self._compiled.append((re.compile(rule.pattern), rule))

    def mask(self, data: str, context: str = "") -> str:
        """对数据进行脱敏处理。"""
        result = data
        with self._lock:
            for pattern, rule in self._compiled:
                if rule.field_paths and context:
                    # 检查 context 是否匹配 field_paths
                    if not self._match_field_path(context, rule.field_paths):
                        continue
                result = pattern.sub(rule.replacement, result)
        return result

    def mask_dict(self, data: dict, path: str = "") -> dict:
        """对字典数据进行脱敏处理（递归遍历字段）。"""
        result = {}
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            if isinstance(value, str):
                result[key] = self.mask(value, context=current_path)
            elif isinstance(value, dict):
                result[key] = self.mask_dict(value, path=current_path)
            elif isinstance(value, list):
                result[key] = [
                    self.mask(item, context=current_path) if isinstance(item, str)
                    else self.mask_dict(item, path=current_path) if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def _match_field_path(self, context: str, field_paths: list[str]) -> bool:
        """检查 context 是否匹配任意 field_path。"""
        for fp in field_paths:
            if fp.endswith(".*"):
                prefix = fp[:-2]
                if context.startswith(prefix):
                    return True
            elif context == fp:
                return True
        return False

    def list_rules(self) -> list[MaskRule]:
        with self._lock:
            return list(self._rules)


# ---------------------------------------------------------------------------
# DataLifecycleManager
# ---------------------------------------------------------------------------

class DataLifecycleManager:
    """数据生命周期管理器。"""

    def __init__(self, policy: DataRetentionPolicy | None = None,
                 data_root: str | Path | None = None):
        self._policy = policy or DataRetentionPolicy()
        self._data_root = Path(data_root) if data_root else Path.cwd()

    def set_policy(self, policy: DataRetentionPolicy):
        self._policy = policy

    def cleanup_expired(self) -> CleanupReport:
        """清理过期数据。返回清理报告。"""
        report = CleanupReport()
        now = time.time()

        try:
            # 清理过期 run 日志
            run_logs_dir = self._data_root / "runs"
            if run_logs_dir.exists():
                for run_dir in run_logs_dir.iterdir():
                    if run_dir.is_dir():
                        age_days = (now - run_dir.stat().st_mtime) / 86400
                        if age_days > self._policy.run_logs_days:
                            import shutil
                            shutil.rmtree(run_dir, ignore_errors=True)
                            report.cleaned_runs += 1
        except Exception as e:
            report.errors.append(f"清理 run 日志失败: {e}")

        return report

    def export_tenant_data(self, tenant_id: str, formats: list[str] | None = None) -> str:
        """导出租户数据（GDPR 数据可移植性要求）。"""
        export_path = self._data_root / "exports" / f"{tenant_id}_{int(time.time())}"
        export_path.mkdir(parents=True, exist_ok=True)

        # 导出 run 数据
        run_logs_dir = self._data_root / "runs" / tenant_id
        if run_logs_dir.exists():
            import shutil
            for run_dir in run_logs_dir.iterdir():
                if run_dir.is_dir():
                    dest = export_path / "runs" / run_dir.name
                    shutil.copytree(run_dir, dest, dirs_exist_ok=True)

        return str(export_path)

    def delete_tenant_data(self, tenant_id: str) -> DeleteReport:
        """删除租户所有数据（GDPR 被遗忘权要求）。"""
        report = DeleteReport()

        # 删除 run 数据
        run_logs_dir = self._data_root / "runs" / tenant_id
        if run_logs_dir.exists():
            import shutil
            for run_dir in run_logs_dir.iterdir():
                if run_dir.is_dir():
                    shutil.rmtree(run_dir, ignore_errors=True)
                    report.deleted_runs += 1
            try:
                run_logs_dir.rmdir()
            except OSError:
                pass

        # 审计日志不可删除
        report.preserved_audit_logs = 0

        return report


# ---------------------------------------------------------------------------
# ContentModerator
# ---------------------------------------------------------------------------

class ContentModerator:
    """Agent 输出内容审核。"""

    def __init__(self, rules: list[dict] | None = None):
        self._rules = rules or []
        self._compiled: list[dict] = []
        self._lock = threading.Lock()
        self._compile_rules()

    def _compile_rules(self):
        with self._lock:
            self._compiled = []
            for rule in self._rules:
                rule_type = rule.get("type", "")
                patterns = rule.get("patterns", [])
                compiled_patterns = [re.compile(p) for p in patterns]
                self._compiled.append({
                    "type": rule_type,
                    "patterns": compiled_patterns,
                    "keywords": rule.get("keywords", []),
                })

    def check(self, content: str) -> ModerationResult:
        """检查内容是否合规。"""
        flags = []
        lower_content = content.lower()

        for rule in self._compiled:
            # 检查关键词
            for keyword in rule.get("keywords", []):
                if keyword.lower() in lower_content:
                    flags.append(ModerationFlag(
                        type=rule["type"],
                        severity="high",
                        matched=keyword,
                        suggestion=f"内容包含敏感词: {keyword}",
                    ))

            # 检查正则模式
            for pattern in rule["patterns"]:
                matches = pattern.findall(content)
                for match in matches[:5]:  # 最多记录 5 个匹配
                    matched_str = match if isinstance(match, str) else match[0]
                    flags.append(ModerationFlag(
                        type=rule["type"],
                        severity="medium",
                        matched=matched_str,
                        suggestion=f"匹配到 {rule['type']} 模式",
                    ))

        return ModerationResult(
            passed=len(flags) == 0,
            flags=flags,
        )


# ---------------------------------------------------------------------------
# 审计日志存储
# ---------------------------------------------------------------------------

class AuditStore:
    """审计日志存储抽象。"""

    def append(self, record: AuditRecord):
        raise NotImplementedError

    def query(self, filter_by: dict, time_range: tuple[float, float]) -> list[AuditRecord]:
        raise NotImplementedError

    def export(self, time_range: tuple[float, float]) -> str:
        raise NotImplementedError


class MemoryAuditStore(AuditStore):
    """内存审计日志存储。"""

    def __init__(self):
        self._records: list[AuditRecord] = []
        self._lock = threading.Lock()

    def append(self, record: AuditRecord):
        record.immutable = True
        with self._lock:
            self._records.append(record)

    def query(self, filter_by: dict, time_range: tuple[float, float]) -> list[AuditRecord]:
        with self._lock:
            result = []
            for record in self._records:
                if not (time_range[0] <= record.timestamp <= time_range[1]):
                    continue
                match = True
                for k, v in filter_by.items():
                    if getattr(record, k, None) != v:
                        match = False
                        break
                if match:
                    result.append(record)
            return result

    def export(self, time_range: tuple[float, float]) -> str:
        records = self.query({}, time_range)
        return json.dumps(
            [{
                "id": r.id,
                "timestamp": r.timestamp,
                "event_type": r.event_type,
                "actor": r.actor,
                "resource": r.resource,
                "details": r.details,
                "ip_address": r.ip_address,
            } for r in records],
            ensure_ascii=False, indent=2,
        )


# ---------------------------------------------------------------------------
# AuditLogger
# ---------------------------------------------------------------------------

class AuditLogger:
    """审计日志记录器（日志不可删除、不可修改）。"""

    def __init__(self, store: AuditStore | None = None):
        self._store = store or MemoryAuditStore()

    def record(self, event: AuditRecord):
        """记录审计事件。"""
        if not event.id:
            event.id = f"audit_{uuid.uuid4().hex[:12]}"
        event.immutable = True
        self._store.append(event)

    def query(self, filter_by: dict | None = None,
              time_range: tuple[float, float] | None = None) -> list[AuditRecord]:
        """查询审计日志。"""
        if time_range is None:
            time_range = (0, time.time() + 1)
        if filter_by is None:
            filter_by = {}
        return self._store.query(filter_by, time_range)

    def export(self, time_range: tuple[float, float] | None = None) -> str:
        """导出审计日志（合规审计用）。"""
        if time_range is None:
            time_range = (0, time.time() + 1)
        return self._store.export(time_range)