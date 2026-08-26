from __future__ import annotations

from pathlib import Path

import agent_hive.chief as chief


def test_chief_integrate_uses_structured_flattened_integration_and_reports_status(monkeypatch, tmp_path: Path):
    run_dir = tmp_path / "run"
    package_root = run_dir / "workspace" / "pkg-a"
    package_root.mkdir(parents=True)
    (package_root / "agent_hive").mkdir()
    (package_root / "agent_hive" / "feature.py").write_text("VALUE = 7\n", encoding="utf-8")
    monkeypatch.setattr(chief, "_run_dir", lambda state: run_dir)

    state = {
        "goal": "integration seam",
        "packages": [{"id": "pkg-a", "role": "编码", "depends_on": []}],
        "passed_ids": ["pkg-a"],
        "blocked_ids": [],
        "blown_ids": [],
        "board_statuses": {"pkg-a": "通过"},
        "reports": {},
        "report_objects": {},
        "architecture": "# architecture",
        "review": "# review",
    }

    result = chief.integrate(state)

    assert result["integration"]["status"] == "success"
    assert (run_dir / "dist" / "agent_hive" / "feature.py").is_file()
    assert not (run_dir / "dist" / "pkg-a" / "agent_hive" / "feature.py").exists()
    assert "集成状态" in (run_dir / "final_report.md").read_text(encoding="utf-8")
    assert (run_dir / "integration.json").is_file()
