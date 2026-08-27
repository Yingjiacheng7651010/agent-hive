"""Tests for card-prompt-management: PromptRegistry, PromptABTest, PromptMonitor."""
from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import pytest

from agent_hive.prompt_management import (
    FilePromptLoader,
    PromptABTest,
    PromptEvalResult,
    PromptMonitor,
    PromptRegistry,
    PromptTemplate,
    PromptVariant,
)


class TestPromptTemplate:
    """PromptTemplate 数据结构测试。"""

    def test_create_template(self):
        tmpl = PromptTemplate(
            name="role.coder",
            version="1.0.0",
            template="你是 {{ role }}，负责 {{ task }}",
            variables=["role", "task"],
            description="编码角色提示词",
            tags=["role", "coder"],
        )
        assert tmpl.name == "role.coder"
        assert tmpl.hash  # 自动计算 hash

    def test_hash_auto_compute(self):
        tmpl1 = PromptTemplate(name="test", template="hello {{ name }}")
        tmpl2 = PromptTemplate(name="test", template="hello {{ name }}")
        assert tmpl1.hash == tmpl2.hash  # 相同内容 hash 相同


class TestFilePromptLoader:
    """FilePromptLoader 文件加载器测试。"""

    def test_load_from_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)
            (template_dir / "role.coder.j2").write_text(
                "你是 {{ role }}，负责 {{ task }}", encoding="utf-8"
            )

            loader = FilePromptLoader(template_dir)
            tmpl = loader.load("role.coder")
            assert tmpl is not None
            assert tmpl.name == "role.coder"
            assert "role" in tmpl.variables
            assert "task" in tmpl.variables

    def test_load_nonexistent(self):
        loader = FilePromptLoader()
        assert loader.load("nonexistent") is None

    def test_list_available(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)
            (template_dir / "role.coder.j2").write_text("coder template", encoding="utf-8")
            (template_dir / "role.tester.j2").write_text("tester template", encoding="utf-8")

            loader = FilePromptLoader(template_dir)
            available = loader.list_available()
            assert "role.coder" in available
            assert "role.tester" in available

    def test_hot_reload(self):
        """文件修改后自动重载。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)
            filepath = template_dir / "role.coder.j2"
            filepath.write_text("v1: {{ role }}", encoding="utf-8")

            loader = FilePromptLoader(template_dir)
            tmpl1 = loader.load("role.coder")
            assert tmpl1 is not None
            assert tmpl1.template == "v1: {{ role }}"

            # 修改文件
            time.sleep(0.1)  # 确保 mtime 不同
            filepath.write_text("v2: {{ role }} - {{ task }}", encoding="utf-8")

            tmpl2 = loader.load("role.coder")
            assert tmpl2 is not None
            assert tmpl2.template == "v2: {{ role }} - {{ task }}"


class TestPromptRegistry:
    """PromptRegistry 注册表测试。"""

    def test_register_and_get(self):
        registry = PromptRegistry()
        tmpl = PromptTemplate(name="test", version="1.0.0", template="hello {{ name }}")
        assert registry.register(tmpl) is True
        result = registry.get("test")
        assert result is not None
        assert result.version == "1.0.0"

    def test_register_hash_conflict(self):
        registry = PromptRegistry()
        t1 = PromptTemplate(name="test", version="1.0.0", template="hello {{ name }}")
        t2 = PromptTemplate(name="test", version="2.0.0", template="hello {{ name }}")
        assert registry.register(t1) is True
        assert registry.register(t2) is False  # hash 冲突

    def test_get_latest_version(self):
        registry = PromptRegistry()
        registry.register(PromptTemplate(name="test", version="1.0.0", template="v1"))
        registry.register(PromptTemplate(name="test", version="2.0.0", template="v2"))
        result = registry.get("test")
        assert result is not None
        assert result.version == "2.0.0"

    def test_get_specific_version(self):
        registry = PromptRegistry()
        registry.register(PromptTemplate(name="test", version="1.0.0", template="v1"))
        registry.register(PromptTemplate(name="test", version="2.0.0", template="v2"))
        result = registry.get("test", "1.0.0")
        assert result is not None
        assert result.template == "v1"

    def test_list_all(self):
        registry = PromptRegistry()
        registry.register(PromptTemplate(name="role.coder", version="1.0.0", template="c"))
        registry.register(PromptTemplate(name="role.tester", version="1.0.0", template="t"))
        assert len(registry.list()) == 2

    def test_list_by_name(self):
        registry = PromptRegistry()
        registry.register(PromptTemplate(name="role.coder", version="1.0.0", template="v1"))
        registry.register(PromptTemplate(name="role.coder", version="2.0.0", template="v2"))
        versions = registry.list("role.coder")
        assert len(versions) == 2

    def test_diff(self):
        registry = PromptRegistry()
        registry.register(PromptTemplate(name="test", version="1.0.0", template="hello {{ name }}"))
        registry.register(PromptTemplate(name="test", version="2.0.0", template="hello {{ name }}, welcome to {{ place }}"))
        diff = registry.diff("test", "1.0.0", "2.0.0")
        assert "{{ place }}" in diff or "place" in diff

    def test_diff_nonexistent(self):
        registry = PromptRegistry()
        diff = registry.diff("nonexistent", "1.0.0", "2.0.0")
        assert "不存在" in diff

    def test_render(self):
        registry = PromptRegistry()
        registry.register(PromptTemplate(name="greet", version="1.0.0", template="Hello, {{ name }}!"))
        result = registry.render("greet", {"name": "World"})
        assert result == "Hello, World!"

    def test_render_missing_variable(self):
        registry = PromptRegistry()
        registry.register(PromptTemplate(name="greet", version="1.0.0", template="Hello, {{ name }}!"))
        # 缺失变量
        with pytest.raises(Exception):
            registry.render("greet", {"wrong_key": "World"})

    def test_render_nonexistent_template(self):
        registry = PromptRegistry()
        with pytest.raises(ValueError):
            registry.render("nonexistent", {})

    def test_has_template(self):
        registry = PromptRegistry()
        assert registry.has_template("test") is False
        registry.register(PromptTemplate(name="test", version="1.0.0", template="t"))
        assert registry.has_template("test") is True

    def test_clear(self):
        registry = PromptRegistry()
        registry.register(PromptTemplate(name="test", version="1.0.0", template="t"))
        registry.clear()
        assert len(registry.list()) == 0


class TestPromptABTest:
    """PromptABTest A/B 测试框架测试。"""

    def test_register_variant(self):
        registry = PromptRegistry()
        ab = PromptABTest(registry)
        variant = PromptVariant(template_name="role.coder", variant_name="control", version="1.0.0", weight=1.0)
        ab.register_variant(variant)
        variants = ab.get_variants("role.coder")
        assert len(variants) == 1

    def test_select_variant(self):
        registry = PromptRegistry()
        ab = PromptABTest(registry)
        ab.register_variant(PromptVariant("role.coder", "control", "1.0.0", weight=1.0))
        selected = ab.select_variant("role.coder")
        assert selected is not None
        assert selected.variant_name == "control"

    def test_select_variant_weighted(self):
        """权重分布符合预期。"""
        registry = PromptRegistry()
        ab = PromptABTest(registry)
        ab.register_variant(PromptVariant("test", "control", "1.0.0", weight=0.8))
        ab.register_variant(PromptVariant("test", "variant_a", "2.0.0", weight=0.2))

        selected_counts = {"control": 0, "variant_a": 0}
        n_trials = 1000
        for _ in range(n_trials):
            v = ab.select_variant("test")
            if v:
                selected_counts[v.variant_name] += 1

        # 权重分布应该在合理范围内
        control_ratio = selected_counts["control"] / n_trials
        assert 0.7 <= control_ratio <= 0.9  # 80% 附近

    def test_select_variant_no_variants(self):
        registry = PromptRegistry()
        ab = PromptABTest(registry)
        assert ab.select_variant("nonexistent") is None

    def test_record_and_evaluate(self):
        registry = PromptRegistry()
        ab = PromptABTest(registry)
        ab.register_variant(PromptVariant("test", "control", "1.0.0", weight=1.0))

        # 记录结果
        for i in range(10):
            ab.record_result("test", "control", {
                "rework_count": 0 if i < 7 else 1,
                "passed": i < 8,
                "tokens": 100 + i * 10,
                "latency_ms": 50 + i * 5,
                "cost_usd": 0.01,
            })

        results = ab.evaluate("test")
        assert len(results) >= 1
        control_result = [r for r in results if r.variant_name == "control"]
        assert len(control_result) == 1
        assert control_result[0].total_calls == 10
        assert control_result[0].pass_rate == pytest.approx(0.8)
        assert control_result[0].rework_rate == pytest.approx(0.3)


class TestPromptMonitor:
    """PromptMonitor 效果监控测试。"""

    def test_record_and_report(self):
        monitor = PromptMonitor()
        monitor.record_call("role.coder", "control", "1.0.0",
                            rework_count=0, tokens=100, latency_ms=50, passed=True, cost_usd=0.01)
        monitor.record_call("role.coder", "control", "1.0.0",
                            rework_count=1, tokens=200, latency_ms=100, passed=False, cost_usd=0.02)

        report = monitor.report("role.coder")
        assert report["total_calls"] == 2
        assert report["pass_rate"] == 0.5
        assert report["rework_rate"] == 0.5
        assert report["avg_tokens"] == 150
        assert report["avg_latency_ms"] == 75

    def test_report_empty(self):
        monitor = PromptMonitor()
        report = monitor.report("nonexistent")
        assert report["total_calls"] == 0