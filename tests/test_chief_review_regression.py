from __future__ import annotations

from pathlib import Path

import agent_hive.chief as chief
from agent_hive.contract_spec import ReviewVerdicts, Verdict


def package(pid: str, role: str = "调研") -> dict:
    return {
        "id": pid,
        "title": pid,
        "role": role,
        "expected_output": "report",
        "acceptance": ["accepted facts"],
        "depends_on": [],
    }


def base_state(tmp_path: Path, packages: list[dict], active_ids: list[str]) -> dict:
    return {
        "run_id": str(tmp_path / "run"),
        "packages": packages,
        "active_ids": active_ids,
        "passed_ids": [],
        "blocked_ids": [],
        "blown_ids": [],
        "retry_counts": {},
        "reports": {p["id"]: "facts" for p in packages},
        "report_objects": {
            p["id"]: {"parse_ok": True, "completion": ["done"], "deliverables": []}
            for p in packages
        },
    }


def isolate_run_dir(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(chief, "_run_dir", lambda state: tmp_path / "run")


def test_review_only_uses_active_ids_and_keeps_previous_passes_frozen(monkeypatch, tmp_path):
    packages = [package("old"), package("active"), package("future")]
    state = base_state(tmp_path, packages, ["active"])
    state["passed_ids"] = ["old"]
    seen = {}
    isolate_run_dir(monkeypatch, tmp_path)

    def fake_review(schema, messages):
        seen["prompt"] = messages[-1].content
        return ReviewVerdicts(verdicts=[
            Verdict(package_id="old", passed=False, feedback="outside scope"),
            Verdict(package_id="active", passed=True),
            Verdict(package_id="future", passed=True),
        ])

    monkeypatch.setattr(chief, "_invoke_structured", fake_review)

    result = chief.review(state)

    assert set(result["passed_ids"]) == {"old", "active"}
    assert result["retry_ids"] == []
    assert "工作包 active" in seen["prompt"]
    assert "工作包 old" not in seen["prompt"]
    assert "工作包 future" not in seen["prompt"]


def test_missing_llm_verdict_is_a_failure_not_silent_pass(monkeypatch, tmp_path):
    packages = [package("a"), package("b")]
    state = base_state(tmp_path, packages, ["a", "b"])
    isolate_run_dir(monkeypatch, tmp_path)
    monkeypatch.setattr(
        chief,
        "_invoke_structured",
        lambda schema, messages: ReviewVerdicts(verdicts=[Verdict(package_id="a", passed=True)]),
    )

    result = chief.review(state)

    assert result["passed_ids"] == ["a"]
    assert result["retry_ids"] == ["b"]
    assert result["retry_counts"] == {"b": 1}
    assert "未返回" in result["review_feedback"]["b"]


def test_delivery_guard_rejects_escape_and_missing_paths_without_model_call(monkeypatch, tmp_path):
    packages = [package("escape", "测试"), package("missing", "编码")]
    state = base_state(tmp_path, packages, ["escape", "missing"])
    run_dir = tmp_path / "run"
    (run_dir / "workspace" / "escape").mkdir(parents=True)
    (run_dir / "workspace" / "missing").mkdir(parents=True)
    state["report_objects"]["escape"]["deliverables"] = ["../outside.txt"]
    state["report_objects"]["missing"]["deliverables"] = ["not-created.py"]
    isolate_run_dir(monkeypatch, tmp_path)

    def must_not_call_model(*args, **kwargs):
        raise AssertionError("guard failures must not call the model")

    monkeypatch.setattr(chief, "_invoke_structured", must_not_call_model)

    result = chief.review(state)

    assert set(result["retry_ids"]) == {"escape", "missing"}
    assert "路径非法" in result["review_feedback"]["escape"]
    assert "文件缺失" in result["review_feedback"]["missing"]


def test_execution_error_is_a_guard_failure_for_non_coding_roles(monkeypatch, tmp_path):
    state = base_state(tmp_path, [package("research", "调研")], ["research"])
    state["report_objects"]["research"]["execution_error"] = "provider unavailable"
    isolate_run_dir(monkeypatch, tmp_path)

    def must_not_call_model(*args, **kwargs):
        raise AssertionError("execution failures must not reach content review")

    monkeypatch.setattr(chief, "_invoke_structured", must_not_call_model)

    result = chief.review(state)

    assert result["retry_ids"] == ["research"]
    assert "专家执行失败" in result["review_feedback"]["research"]


def test_failure_after_three_automatic_retries_fuses_the_package(monkeypatch, tmp_path):
    state = base_state(tmp_path, [package("limited", "编码")], ["limited"])
    state["retry_counts"] = {"limited": chief.MAX_RETRY_ROUNDS}
    isolate_run_dir(monkeypatch, tmp_path)
    monkeypatch.setattr(
        chief, "_invoke_structured",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("guard should short-circuit")),
    )

    result = chief.review(state)

    assert result["retry_counts"] == {"limited": chief.MAX_RETRY_ROUNDS + 1}
    assert result["retry_ids"] == []
    assert result["blown_ids"] == ["limited"]


def test_review_round_is_monotonic_and_does_not_overwrite_prior_audit(monkeypatch, tmp_path):
    state = base_state(tmp_path, [package("wave")], ["wave"])
    state["review_round"] = 7
    isolate_run_dir(monkeypatch, tmp_path)
    monkeypatch.setattr(
        chief, "_invoke_structured",
        lambda *args, **kwargs: ReviewVerdicts(verdicts=[Verdict(package_id="wave", passed=True)]),
    )

    result = chief.review(state)

    assert result["review_round"] == 8
    assert (tmp_path / "run" / "review_round_8.md").is_file()


def test_cross_wave_reassignment_is_audited_but_does_not_reopen_frozen_package(monkeypatch, tmp_path):
    packages = [package("old"), package("active")]
    state = base_state(tmp_path, packages, ["active"])
    state["passed_ids"] = ["old"]
    isolate_run_dir(monkeypatch, tmp_path)
    monkeypatch.setattr(
        chief, "_invoke_structured",
        lambda *args, **kwargs: ReviewVerdicts(verdicts=[
            Verdict(package_id="active", passed=True, reassign_to=["old"])
        ]),
    )

    result = chief.review(state)

    assert result["passed_ids"] == ["active", "old"]
    assert result["retry_ids"] == []
    assert any("跨波通过包保持冻结" in warning for warning in result["review_warnings"])
    assert "需返工" not in result["review"]
