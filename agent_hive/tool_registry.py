"""工具注册表与生命周期管理 —— ToolSpec → ToolRegistry → ToolCallTracker。

核心策略：
1. ToolSpec：声明式工具规范，独立于实现
2. ToolRegistry：注册、发现、按角色分配、版本管理
3. ToolCallTracker：调用记录、统计、告警
4. MonitoredToolWrapper：自动包装工具调用，记录指标
5. 兼容包装器：从现有 @tool 自动生成 ToolSpec
"""
from __future__ import annotations

import copy
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

__all__ = [
    "ToolSpec",
    "ToolParameter",
    "ToolCallRecord",
    "ToolRegistry",
    "ToolCallTracker",
    "MonitoredToolWrapper",
    "tool_to_spec",
]

# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class ToolParameter:
    """工具参数定义。"""
    name: str
    type: Literal["string", "integer", "boolean", "array", "object"] = "string"
    description: str = ""
    required: bool = True
    default: Any = None


@dataclass
class ToolSpec:
    """工具定义（独立于实现的声明式规范）。"""
    name: str
    description: str = ""
    version: str = "1.0.0"
    parameters: list[ToolParameter] = field(default_factory=list)
    returns: str = "string"
    categories: list[str] = field(default_factory=list)
    required_roles: list[str] = field(default_factory=list)
    timeout_ms: int = 30000
    danger_level: Literal["safe", "caution", "dangerous"] = "safe"
    owner: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "parameters": [p.__dict__ for p in self.parameters],
            "categories": self.categories,
            "required_roles": self.required_roles,
            "danger_level": self.danger_level,
        }


@dataclass
class ToolCallRecord:
    """一次工具调用的记录。"""
    tool_name: str
    tool_version: str
    arguments: dict
    result: str = ""
    success: bool = True
    latency_ms: float = 0.0
    error: str | None = None
    agent_role: str = ""
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# ToolRegistry
# ---------------------------------------------------------------------------

class ToolRegistry:
    """工具注册表：注册、发现、分配、版本管理。"""

    def __init__(self):
        self._tools: dict[str, dict[str, tuple[ToolSpec, Callable]]] = {}  # name -> version -> (spec, impl)
        self._lock = threading.Lock()

    def register(self, spec: ToolSpec, impl: Callable) -> bool:
        """注册工具。版本冲突时拒绝（需先 unregister）。"""
        with self._lock:
            if spec.name not in self._tools:
                self._tools[spec.name] = {}
            if spec.version in self._tools[spec.name]:
                return False  # 版本冲突
            self._tools[spec.name][spec.version] = (spec, impl)
            return True

    def unregister(self, name: str, version: str | None = None) -> bool:
        """注销工具。version=None 时注销所有版本。"""
        with self._lock:
            if name not in self._tools:
                return False
            if version is None:
                del self._tools[name]
                return True
            if version in self._tools[name]:
                del self._tools[name][version]
                if not self._tools[name]:
                    del self._tools[name]
                return True
            return False

    def get(self, name: str, version: str | None = None) -> tuple[ToolSpec, Callable] | None:
        """获取指定版本的工具。version=None 返回最新版本。"""
        with self._lock:
            if name not in self._tools:
                return None
            versions = self._tools[name]
            if version is not None:
                return versions.get(version)
            # 返回最新版本（按语义版本号排序）
            sorted_versions = sorted(versions.keys(), key=lambda v: [int(x) for x in v.split(".")], reverse=True)
            if not sorted_versions:
                return None
            return versions[sorted_versions[0]]

    def list(self, filter_by: dict | None = None) -> list[ToolSpec]:
        """按条件查询工具列表。返回每个工具的最新版本。"""
        with self._lock:
            result = []
            for name, versions in self._tools.items():
                # 最新版本
                sorted_versions = sorted(versions.keys(), key=lambda v: [int(x) for x in v.split(".")], reverse=True)
                if not sorted_versions:
                    continue
                spec, _ = versions[sorted_versions[0]]
                if filter_by:
                    match = True
                    for k, v in filter_by.items():
                        if k == "category":
                            if v not in spec.categories:
                                match = False
                        elif k == "danger_level":
                            if spec.danger_level != v:
                                match = False
                        elif k == "required_roles":
                            if not set(v).intersection(set(spec.required_roles)) and spec.required_roles:
                                match = False
                        elif getattr(spec, k, None) != v:
                            match = False
                    if match:
                        result.append(spec)
                else:
                    result.append(spec)
            return result

    def get_for_role(self, role: str) -> list[tuple[ToolSpec, Callable]]:
        """获取指定角色可用的工具列表（自动过滤 required_roles）。"""
        with self._lock:
            result = []
            for name, versions in self._tools.items():
                sorted_versions = sorted(versions.keys(), key=lambda v: [int(x) for x in v.split(".")], reverse=True)
                if not sorted_versions:
                    continue
                spec, impl = versions[sorted_versions[0]]
                # 如果 required_roles 为空，所有角色可用
                if not spec.required_roles or role in spec.required_roles:
                    result.append((spec, impl))
            return result

    def has_tool(self, name: str) -> bool:
        """检查工具是否已注册。"""
        with self._lock:
            return name in self._tools

    def clear(self):
        """清空所有工具。"""
        with self._lock:
            self._tools.clear()


# ---------------------------------------------------------------------------
# ToolCallTracker
# ---------------------------------------------------------------------------

class ToolCallTracker:
    """工具调用追踪器：记录、聚合、告警。"""

    def __init__(self):
        self._records: list[ToolCallRecord] = []
        self._lock = threading.Lock()

    def record(self, record: ToolCallRecord):
        """记录一次工具调用。"""
        with self._lock:
            self._records.append(record)

    def stats(
        self,
        tool_name: str | None = None,
        since: float | None = None,
    ) -> dict:
        """查询工具调用统计。"""
        with self._lock:
            records = self._records
            if tool_name:
                records = [r for r in records if r.tool_name == tool_name]
            if since is not None:
                records = [r for r in records if r.timestamp >= since]

            if not records:
                return {
                    "total_calls": 0,
                    "success_rate": 0.0,
                    "avg_latency_ms": 0.0,
                    "p99_latency_ms": 0.0,
                    "total_failures": 0,
                }

            total = len(records)
            successes = sum(1 for r in records if r.success)
            failures = total - successes
            latencies = sorted(r.latency_ms for r in records)

            p99_index = max(0, int(len(latencies) * 0.99) - 1)
            p99 = latencies[p99_index] if latencies else 0.0

            return {
                "total_calls": total,
                "success_rate": successes / total if total else 0.0,
                "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0.0,
                "p99_latency_ms": p99,
                "total_failures": failures,
            }

    def top_failures(self, n: int = 10) -> list[ToolCallRecord]:
        """查询失败率最高的工具。"""
        with self._lock:
            failed = [r for r in self._records if not r.success]
            return sorted(failed, key=lambda r: r.timestamp, reverse=True)[:n]

    def records_count(self) -> int:
        with self._lock:
            return len(self._records)

    def clear(self):
        with self._lock:
            self._records.clear()


# ---------------------------------------------------------------------------
# MonitoredToolWrapper
# ---------------------------------------------------------------------------

class MonitoredToolWrapper:
    """包装工具调用，自动记录指标。"""

    def __init__(self, spec: ToolSpec, impl: Callable, tracker: ToolCallTracker):
        self._spec = spec
        self._impl = impl
        self._tracker = tracker

    def __call__(self, **kwargs) -> Any:
        start = time.time()
        try:
            result = self._impl(**kwargs)
            self._tracker.record(ToolCallRecord(
                tool_name=self._spec.name,
                tool_version=self._spec.version,
                arguments=kwargs,
                result=str(result)[:200],
                success=True,
                latency_ms=(time.time() - start) * 1000,
            ))
            return result
        except Exception as e:
            self._tracker.record(ToolCallRecord(
                tool_name=self._spec.name,
                tool_version=self._spec.version,
                arguments=kwargs,
                result="",
                success=False,
                latency_ms=(time.time() - start) * 1000,
                error=str(e),
            ))
            raise


# ---------------------------------------------------------------------------
# 兼容包装器
# ---------------------------------------------------------------------------

def tool_to_spec(tool_func) -> ToolSpec:
    """从 @tool 装饰的函数自动推断 ToolSpec。"""
    import inspect

    name = getattr(tool_func, "__name__", "unknown")
    description = getattr(tool_func, "__doc__", "") or getattr(tool_func, "description", "")

    sig = inspect.signature(tool_func)
    parameters = []
    for param_name, param in sig.parameters.items():
        param_type = "string"
        param_annotation = param.annotation
        if param_annotation is not inspect.Parameter.empty:
            type_map = {
                int: "integer",
                str: "string",
                bool: "boolean",
                list: "array",
                dict: "object",
            }
            param_type = type_map.get(param_annotation, "string")

        parameters.append(ToolParameter(
            name=param_name,
            type=param_type,
            required=param.default is inspect.Parameter.empty,
            default=None if param.default is inspect.Parameter.empty else param.default,
        ))

    return ToolSpec(
        name=name,
        description=description,
        version="0.9.0",
        parameters=parameters,
        categories=["legacy"],
    )