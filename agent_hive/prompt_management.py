"""Prompt 管理基础设施 —— 版本化存储 → 模板引擎 → A/B 测试 → 效果监控。

核心策略：
1. PromptRegistry：版本化存储、检索、对比、渲染
2. PromptABTest：A/B 测试框架，按权重分配变体
3. PromptMonitor：效果监控，记录调用效果
4. Jinja2 模板引擎（Python 生态最成熟的模板库）
5. 模板文件热加载（修改文件后不重启进程即可生效）
"""
from __future__ import annotations

import hashlib
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

try:
    import jinja2
    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False

__all__ = [
    "PromptTemplate",
    "PromptVariant",
    "PromptEvalResult",
    "PromptRegistry",
    "PromptABTest",
    "PromptMonitor",
    "FilePromptLoader",
]

# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class PromptTemplate:
    """Prompt 模板：带版本管理的结构化提示词。"""
    name: str
    version: str = "1.0.0"
    template: str = ""
    variables: list[str] = field(default_factory=list)
    description: str = ""
    tags: list[str] = field(default_factory=list)
    author: str = ""
    created_at: float = field(default_factory=time.time)
    parent_version: str | None = None
    hash: str = ""

    def __post_init__(self):
        if not self.hash:
            self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        content = f"{self.name}:{self.template}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class PromptVariant:
    """Prompt 变体：同一个模板的不同版本，用于 A/B 测试。"""
    template_name: str
    variant_name: str = "control"
    version: str = "1.0.0"
    weight: float = 1.0
    active: bool = True


@dataclass
class PromptEvalResult:
    """Prompt 效果评估结果。"""
    template_name: str
    variant_name: str
    version: str
    period: tuple[float, float] = (0.0, 0.0)
    total_calls: int = 0
    avg_attempts: float = 0.0
    rework_rate: float = 0.0
    pass_rate: float = 0.0
    avg_tokens: float = 0.0
    avg_latency_ms: float = 0.0
    total_cost_usd: float = 0.0


# ---------------------------------------------------------------------------
# FilePromptLoader
# ---------------------------------------------------------------------------

class FilePromptLoader:
    """从文件系统加载模板的加载器，支持热加载。"""

    def __init__(self, template_dir: str | Path | None = None):
        self._template_dir = Path(template_dir) if template_dir else None
        self._cache: dict[str, PromptTemplate] = {}
        self._mtime_cache: dict[str, float] = {}
        self._lock = threading.Lock()

    def set_template_dir(self, path: str | Path):
        self._template_dir = Path(path)
        self._cache.clear()
        self._mtime_cache.clear()

    def load(self, name: str) -> PromptTemplate | None:
        """加载模板文件。先检查缓存，文件变更时自动重载。"""
        if self._template_dir is None:
            return None

        filepath = self._template_dir / f"{name}.j2"
        if not filepath.exists():
            return None

        current_mtime = filepath.stat().st_mtime
        with self._lock:
            cached_mtime = self._mtime_cache.get(name)
            if cached_mtime is not None and cached_mtime == current_mtime and name in self._cache:
                return self._cache[name]

        # 文件变更或未缓存，重新加载
        template_text = filepath.read_text(encoding="utf-8")
        variables = self._extract_variables(template_text)

        template = PromptTemplate(
            name=name,
            template=template_text,
            variables=variables,
            description=f"从 {filepath.name} 加载",
        )

        with self._lock:
            self._cache[name] = template
            self._mtime_cache[name] = current_mtime

        return template

    def _extract_variables(self, template: str) -> list[str]:
        """从模板中提取变量名。"""
        import re
        # 匹配 {{ variable_name }} 或 {{ variable_name }}
        variables = set(re.findall(r'\{\{\s*(\w+)\s*\}\}', template))
        return sorted(variables)

    def list_available(self) -> list[str]:
        """列出可用的模板文件。"""
        if self._template_dir is None or not self._template_dir.exists():
            return []
        return sorted(
            f.stem for f in self._template_dir.glob("*.j2")
        )


# ---------------------------------------------------------------------------
# PromptRegistry
# ---------------------------------------------------------------------------

class PromptRegistry:
    """Prompt 注册表：版本化存储、检索、对比、渲染。"""

    def __init__(self, loader: FilePromptLoader | None = None):
        self._templates: dict[str, dict[str, PromptTemplate]] = {}  # name -> version -> template
        self._loader = loader or FilePromptLoader()
        self._lock = threading.Lock()

    def register(self, template: PromptTemplate) -> bool:
        """注册/更新 prompt 模板。hash 冲突时拒绝。"""
        with self._lock:
            if template.name not in self._templates:
                self._templates[template.name] = {}
            versions = self._templates[template.name]
            # 检查 hash 冲突
            for existing in versions.values():
                if existing.hash == template.hash and existing.name == template.name:
                    return False
            versions[template.version] = template
            return True

    def get(self, name: str, version: str | None = None) -> PromptTemplate | None:
        """获取指定版本的模板。version=None 返回最新版本。"""
        # 先尝试从文件加载
        file_template = self._loader.load(name)
        if file_template is not None and version is None:
            return file_template

        with self._lock:
            if name not in self._templates:
                return file_template
            versions = self._templates[name]
            if version is not None:
                return versions.get(version)
            # 返回最新版本
            sorted_versions = sorted(versions.keys(), key=lambda v: [int(x) for x in v.split(".")], reverse=True)
            if not sorted_versions:
                return file_template
            return versions[sorted_versions[0]]

    def list(self, name: str | None = None) -> list[PromptTemplate]:
        """列出所有模板（或指定名称的所有版本）。"""
        with self._lock:
            if name is not None:
                if name not in self._templates:
                    return []
                return list(self._templates[name].values())

            result = []
            for versions in self._templates.values():
                result.extend(versions.values())
            return result

    def diff(self, name: str, v1: str, v2: str) -> str:
        """对比两个版本的差异。"""
        t1 = self.get(name, v1)
        t2 = self.get(name, v2)
        if t1 is None and t2 is None:
            return f"模板 {name} 的两个版本均不存在"
        if t1 is None:
            return f"版本 {v1} 不存在"
        if t2 is None:
            return f"版本 {v2} 不存在"

        lines1 = t1.template.splitlines(keepends=True)
        lines2 = t2.template.splitlines(keepends=True)

        import difflib
        diff_lines = list(difflib.unified_diff(
            lines1, lines2,
            fromfile=f"{name} ({v1})",
            tofile=f"{name} ({v2})",
            lineterm="",
        ))
        return "".join(diff_lines)

    def render(self, name: str, variables: dict, version: str | None = None) -> str:
        """渲染 prompt 模板（替换变量）。"""
        template = self.get(name, version)
        if template is None:
            raise ValueError(f"模板 {name} 不存在")

        if HAS_JINJA2:
            env = jinja2.Environment(
                undefined=jinja2.StrictUndefined,  # 缺失变量时明确报错
            )
            jinja_template = env.from_string(template.template)
            return jinja_template.render(**variables)
        else:
            # 简单替换（无 Jinja2 时的回退）
            result = template.template
            for key, value in variables.items():
                result = result.replace("{{ " + key + " }}", str(value))
                result = result.replace("{{" + key + "}}", str(value))
                result = result.replace("{{ " + key + "}}", str(value))
                result = result.replace("{{" + key + " }}", str(value))
            return result

    def has_template(self, name: str) -> bool:
        with self._lock:
            return name in self._templates

    def clear(self):
        with self._lock:
            self._templates.clear()


# ---------------------------------------------------------------------------
# PromptABTest
# ---------------------------------------------------------------------------

class PromptABTest:
    """Prompt A/B 测试框架。"""

    def __init__(self, registry: PromptRegistry):
        self._registry = registry
        self._variants: dict[str, list[PromptVariant]] = {}  # template_name -> [variants]
        self._results: dict[str, list[dict]] = {}  # template_name -> [results]
        self._lock = threading.Lock()

    def register_variant(self, variant: PromptVariant):
        """注册一个变体。"""
        with self._lock:
            if variant.template_name not in self._variants:
                self._variants[variant.template_name] = []
            # 检查是否已存在同名变体
            for i, v in enumerate(self._variants[variant.template_name]):
                if v.variant_name == variant.variant_name:
                    self._variants[variant.template_name][i] = variant
                    return
            self._variants[variant.template_name].append(variant)

    def select_variant(self, template_name: str) -> PromptVariant | None:
        """按权重选择一个变体（随机）。"""
        import random
        with self._lock:
            if template_name not in self._variants:
                return None
            variants = [v for v in self._variants[template_name] if v.active]
            if not variants:
                return None
            # 按权重选择
            total_weight = sum(v.weight for v in variants)
            r = random.uniform(0, total_weight)
            cumulative = 0.0
            for v in variants:
                cumulative += v.weight
                if r <= cumulative:
                    return v
            return variants[-1]

    def record_result(self, template_name: str, variant_name: str, result: dict):
        """记录一次执行结果。"""
        with self._lock:
            if template_name not in self._results:
                self._results[template_name] = []
            self._results[template_name].append({
                "variant_name": variant_name,
                **result,
                "timestamp": time.time(),
            })

    def evaluate(self, template_name: str) -> list[PromptEvalResult]:
        """评估各变体的效果对比。"""
        with self._lock:
            if template_name not in self._results:
                return []
            if template_name not in self._variants:
                return []

            results = self._results[template_name]
            variants = {v.variant_name: v for v in self._variants[template_name]}

            eval_results = []
            for vname, variant in variants.items():
                variant_results = [r for r in results if r.get("variant_name") == vname]
                if not variant_results:
                    continue

                total = len(variant_results)
                reworks = sum(1 for r in variant_results if r.get("rework_count", 0) > 0)
                passes = sum(1 for r in variant_results if r.get("passed", False))
                total_tokens = sum(r.get("tokens", 0) for r in variant_results)
                total_latency = sum(r.get("latency_ms", 0) for r in variant_results)
                total_cost = sum(r.get("cost_usd", 0) for r in variant_results)

                eval_results.append(PromptEvalResult(
                    template_name=template_name,
                    variant_name=vname,
                    version=variant.version,
                    period=(min(r.get("timestamp", 0) for r in variant_results),
                            max(r.get("timestamp", 0) for r in variant_results)),
                    total_calls=total,
                    avg_attempts=sum(r.get("rework_count", 0) for r in variant_results) / total,
                    rework_rate=reworks / total,
                    pass_rate=passes / total,
                    avg_tokens=total_tokens / total,
                    avg_latency_ms=total_latency / total,
                    total_cost_usd=total_cost,
                ))

            return eval_results

    def get_variants(self, template_name: str) -> list[PromptVariant]:
        with self._lock:
            return list(self._variants.get(template_name, []))


# ---------------------------------------------------------------------------
# PromptMonitor
# ---------------------------------------------------------------------------

class PromptMonitor:
    """Prompt 效果监控。"""

    def __init__(self):
        self._records: dict[str, list[dict]] = {}  # template_name -> [records]
        self._lock = threading.Lock()

    def record_call(
        self,
        template_name: str,
        variant_name: str = "control",
        version: str = "1.0.0",
        rework_count: int = 0,
        tokens: int = 0,
        latency_ms: float = 0.0,
        passed: bool = True,
        cost_usd: float = 0.0,
    ):
        """记录一次调用效果。"""
        with self._lock:
            if template_name not in self._records:
                self._records[template_name] = []
            self._records[template_name].append({
                "variant_name": variant_name,
                "version": version,
                "rework_count": rework_count,
                "tokens": tokens,
                "latency_ms": latency_ms,
                "passed": passed,
                "cost_usd": cost_usd,
                "timestamp": time.time(),
            })

    def report(self, template_name: str) -> dict:
        """生成 prompt 效果报告。"""
        with self._lock:
            if template_name not in self._records:
                return {"template_name": template_name, "total_calls": 0}

            records = self._records[template_name]
            total = len(records)
            if total == 0:
                return {"template_name": template_name, "total_calls": 0}

            passes = sum(1 for r in records if r.get("passed", False))
            reworks = sum(1 for r in records if r.get("rework_count", 0) > 0)
            total_tokens = sum(r.get("tokens", 0) for r in records)
            total_latency = sum(r.get("latency_ms", 0) for r in records)
            total_cost = sum(r.get("cost_usd", 0) for r in records)

            return {
                "template_name": template_name,
                "total_calls": total,
                "pass_rate": passes / total,
                "rework_rate": reworks / total,
                "avg_tokens": total_tokens / total,
                "avg_latency_ms": total_latency / total,
                "total_cost_usd": total_cost,
            }