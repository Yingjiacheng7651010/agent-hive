from __future__ import annotations

import json
from pathlib import Path

from agent_hive import contract_spec, prompts
from agent_hive.state import merge_dict


def test_checked_in_contract_document_matches_single_source():
    contracts_md = Path(__file__).resolve().parents[1] / "skill" / "contracts.md"
    if not contracts_md.exists():
        # Isolated delivery location: walk to the repository rather than relying on CWD.
        contracts_md = next(
            parent / "skill" / "contracts.md"
            for parent in Path(__file__).resolve().parents
            if (parent / "skill" / "contracts.md").is_file()
        )

    assert contract_spec.check_contracts_drift(contracts_md) == []


def test_contract_drift_checker_detects_independent_mutation(tmp_path):
    changed = tmp_path / "contracts.md"
    changed.write_text(contract_spec.render_contracts_md() + "manual drift\n", encoding="utf-8")

    diff = contract_spec.check_contracts_drift(changed)

    assert diff
    assert any("manual drift" in line for line in diff)


def test_prompts_public_api_reexports_contract_source_objects():
    public_names = [
        "CONTRACT_VERSION",
        "MAX_RETRY_ROUNDS",
        "STATE_FLOW_LINE",
        "PackageSpec",
        "ReportSpec",
        "ReviewVerdicts",
        "ApprovalDecision",
        "ROLE_PROMPTS",
        "render_contracts_md",
        "check_contracts_drift",
    ]

    assert set(public_names).issubset(prompts.__all__)
    assert all(getattr(prompts, name) is getattr(contract_spec, name) for name in public_names)


def test_critical_state_fields_round_trip_through_json_and_reducer():
    state = {
        "packages": [{"id": "a", "depends_on": []}, {"id": "b", "depends_on": ["a"]}],
        "reports": merge_dict({"a": "report-a"}, {"b": "report-b"}),
        "report_objects": merge_dict({"a": {"parse_ok": True}}, {"b": {"parse_ok": True}}),
        "retry_counts": {"b": 2},
        "retry_ids": ["b"],
        "review_feedback": {"b": "fix"},
        "passed_ids": ["a"],
        "active_ids": ["b"],
        "blocked_ids": [],
        "blown_ids": [],
        "board_statuses": {"a": "通过", "b": "返工(2/3)"},
        "allow_integration_checks": False,
        "integration_checks": [],
        "integration_check_timeout": 120,
    }

    restored = json.loads(json.dumps(state, ensure_ascii=False))

    assert restored == state
    assert restored["reports"] == {"a": "report-a", "b": "report-b"}
