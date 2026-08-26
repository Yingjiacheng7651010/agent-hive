from __future__ import annotations

import json
import sys
from pathlib import Path

import agent_hive.integration as integration


def put(run_dir: Path, package_id: str, rel: str, content: str) -> Path:
    path = run_dir / "workspace" / package_id / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def packages(*ids: str) -> list[dict]:
    return [{"id": pid} for pid in ids]


def test_flat_merge_deduplicates_identical_content_and_writes_manifest(tmp_path):
    put(tmp_path, "a", "src/shared.py", "VALUE = 1\n")
    put(tmp_path, "a", "README.md", "A\n")
    put(tmp_path, "b", "src/shared.py", "VALUE = 1\n")
    put(tmp_path, "b", "docs/b.md", "B\n")

    result = integration.integrate_packages(tmp_path, packages("a", "b"), {"a", "b"})

    assert result.status == integration.STATUS_SUCCESS
    assert (tmp_path / "dist" / "src" / "shared.py").read_text(encoding="utf-8") == "VALUE = 1\n"
    assert (tmp_path / "dist" / "README.md").is_file()
    assert (tmp_path / "dist" / "docs" / "b.md").is_file()
    shared = next(f for f in result.files if f.rel_path == "src/shared.py")
    assert shared.deduplicated is True
    assert shared.packages == ["a", "b"]
    manifest = json.loads((tmp_path / "dist" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["merged_packages"] == ["a", "b"]
    assert {f["rel_path"] for f in manifest["files"]} == {"README.md", "docs/b.md", "src/shared.py"}


def test_conflict_rejected_and_existing_dist_is_unchanged(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "sentinel.txt").write_text("old-dist", encoding="utf-8")
    put(tmp_path, "a", "same.txt", "from-a")
    put(tmp_path, "b", "same.txt", "from-b")

    result = integration.integrate_packages(tmp_path, packages("a", "b"), {"a", "b"})

    assert result.status == integration.STATUS_CONFLICT
    assert [(c.rel_path, c.packages) for c in result.conflicts] == [("same.txt", ["a", "b"])]
    assert (dist / "sentinel.txt").read_text(encoding="utf-8") == "old-dist"
    assert not (dist / "same.txt").exists()


def test_python_compile_failure_does_not_pollute_existing_dist(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "sentinel.txt").write_text("old-dist", encoding="utf-8")
    put(tmp_path, "broken", "broken.py", "def broken(:\n")

    result = integration.integrate_packages(tmp_path, packages("broken"), {"broken"})

    assert result.status == integration.STATUS_VALIDATION_FAILED
    assert any("编译失败 broken.py" in error for error in result.validation_errors)
    assert (dist / "sentinel.txt").read_text(encoding="utf-8") == "old-dist"
    assert not (dist / "broken.py").exists()


def test_dynamic_checks_are_disabled_by_default(monkeypatch, tmp_path):
    put(tmp_path, "a", "ok.txt", "ok")

    def forbidden(*args, **kwargs):
        raise AssertionError("dynamic checks unexpectedly ran")

    monkeypatch.setattr(integration, "run_dynamic_checks", forbidden)

    result = integration.integrate_packages(
        tmp_path,
        packages("a"),
        {"a"},
        dynamic_checks=[{"name": "forbidden", "argv": ["python", "-c", "raise SystemExit(1)"]}],
    )

    assert result.status == integration.STATUS_SUCCESS
    assert (tmp_path / "dist" / "ok.txt").read_text(encoding="utf-8") == "ok"


def test_dynamic_check_results_are_recorded_in_manifest_when_explicitly_enabled(tmp_path):
    put(tmp_path, "a", "ok.txt", "ok")

    result = integration.integrate_packages(
        tmp_path,
        packages("a"),
        {"a"},
        enable_dynamic_checks=True,
        dynamic_checks=[{
            "name": "probe",
            "argv": [sys.executable, "-c", "print('dynamic-pass')"],
        }],
    )

    assert result.status == integration.STATUS_SUCCESS
    assert any(check.name == "probe" and check.status == "passed" for check in result.checks)
    manifest = json.loads((tmp_path / "dist" / "manifest.json").read_text(encoding="utf-8"))
    assert any(check["name"] == "probe" for check in manifest["checks"])


def test_failed_dynamic_check_preserves_previous_dist(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "sentinel.txt").write_text("old", encoding="utf-8")
    put(tmp_path, "a", "new.txt", "new")

    result = integration.integrate_packages(
        tmp_path,
        packages("a"),
        {"a"},
        enable_dynamic_checks=True,
        dynamic_checks=[{
            "name": "failing",
            "argv": [sys.executable, "-c", "raise SystemExit(7)"],
        }],
    )

    assert result.status == integration.STATUS_VALIDATION_FAILED
    assert any(check.name == "failing" and check.status == "failed" for check in result.checks)
    assert (dist / "sentinel.txt").read_text(encoding="utf-8") == "old"
    assert not (dist / "new.txt").exists()


def test_path_like_package_id_is_rejected_without_touching_existing_dist(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "sentinel.txt").write_text("keep", encoding="utf-8")
    result = integration.integrate_packages(tmp_path, packages("../escape"), {"../escape"})

    assert result.status == integration.STATUS_VALIDATION_FAILED
    assert any("非法" in error for error in result.validation_errors)
    assert (dist / "sentinel.txt").read_text(encoding="utf-8") == "keep"
    assert not (tmp_path / "escape").exists()


def test_unpassed_packages_are_reported_as_partial_without_being_silently_claimed_success(tmp_path):
    put(tmp_path, "passed", "ok.txt", "ok")
    result = integration.integrate_packages(
        tmp_path,
        packages("passed", "blocked"),
        {"passed"},
    )

    assert result.status == integration.STATUS_PARTIAL
    assert result.ok is False
    assert result.unresolved_packages == ["blocked"]
    assert (tmp_path / "dist" / "ok.txt").exists()
    manifest = json.loads((tmp_path / "dist" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == integration.STATUS_PARTIAL
    assert manifest["unresolved_packages"] == ["blocked"]


def test_malformed_integration_inputs_return_structured_failure(tmp_path):
    put(tmp_path, "a", "ok.txt", "ok")
    result = integration.integrate_packages(
        tmp_path,
        packages("a"),
        {"a"},
        report_objects={"a": {"deliverables": "not-an-array"}},
    )

    assert result.status == integration.STATUS_VALIDATION_FAILED
    assert any("deliverables 必须是数组" in error for error in result.validation_errors)
    assert not (tmp_path / "dist").exists()


def test_non_string_package_id_returns_structured_failure(tmp_path):
    result = integration.integrate_packages(tmp_path, [{"id": []}], [])

    assert result.status == integration.STATUS_VALIDATION_FAILED
    assert result.validation_errors
    assert not (tmp_path / "dist").exists()
