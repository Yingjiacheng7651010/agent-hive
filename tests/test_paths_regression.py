from __future__ import annotations

from pathlib import Path

import pytest

import agent_hive.chief as chief
from agent_hive.paths import safe_package_dir, safe_run_dir, validate_package_id, validate_run_id


@pytest.mark.parametrize("value", ["", ".", "..", "../escape", "a/b", "a\\b", "C:drive", "x\x00y"])
def test_path_policy_rejects_path_like_ids(value):
    with pytest.raises(ValueError):
        validate_run_id(value)
    with pytest.raises(ValueError):
        validate_package_id(value)


def test_safe_paths_are_inside_expected_roots(tmp_path: Path):
    run_dir = safe_run_dir("run-1", tmp_path / "runs")
    package_dir = safe_package_dir(run_dir, "pkg-a")

    assert run_dir == (tmp_path / "runs" / "run-1").resolve()
    assert package_dir == (run_dir / "workspace" / "pkg-a").resolve()


def test_chief_run_dir_rejects_untrusted_run_id():
    with pytest.raises(ValueError):
        chief._run_dir({"run_id": "../../outside"})


def test_invalid_report_keys_cannot_escape_reports_directory(monkeypatch, tmp_path: Path):
    run_dir = tmp_path / "run"
    monkeypatch.setattr(chief, "_run_dir", lambda state: run_dir)

    chief.integrate({
        "packages": [],
        "passed_ids": [],
        "reports": {"../escaped": "must not be written"},
        "report_objects": {},
    })

    assert not (tmp_path / "escaped.md").exists()
    assert not (run_dir.parent / "escaped.md").exists()
