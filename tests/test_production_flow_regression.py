from __future__ import annotations

import sqlite3

import agent_hive.graph as graph_module
from agent_hive.contract_spec import PackageSpec
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command


def test_production_graph_runs_dependency_layers_before_downstream_wave(monkeypatch):
    waves: list[list[str]] = []

    def fake_plan(state):
        return {"architecture": "# fake architecture", "architecture_approved": False}

    def fake_split(state):
        packages = [
            PackageSpec(
                id="root-a", title="A", role="调研", goal="A", contract="report",
                expected_output="report", acceptance=["done"], deliverable="workspace/root-a/",
            ).model_dump(),
            PackageSpec(
                id="root-b", title="B", role="调研", goal="B", contract="report",
                expected_output="report", acceptance=["done"], deliverable="workspace/root-b/",
            ).model_dump(),
            PackageSpec(
                id="child", title="child", role="调研", goal="child", contract="report",
                expected_output="report", depends_on=["root-a", "root-b"],
                acceptance=["done"], deliverable="workspace/child/",
            ).model_dump(),
        ]
        return {
            "packages": packages,
            "batch_approved": False,
            "retry_counts": {},
            "retry_ids": [],
            "passed_ids": [],
            "active_ids": [],
            "blocked_ids": [],
            "blown_ids": [],
            "review_feedback": {},
            "reject_count": 0,
        }

    def fake_specialist(state):
        pid = state["current_package"]["id"]
        return {
            "reports": {pid: f"report:{pid}"},
            "report_objects": {
                pid: {"parse_ok": True, "completion": ["done"], "deliverables": []}
            },
        }

    def fake_review(state):
        active = list(state["active_ids"])
        waves.append(active)
        passed = sorted(set(state.get("passed_ids", [])) | set(active))
        return {
            "review": "reviewed",
            "passed_ids": passed,
            "retry_ids": [],
            "retry_counts": state.get("retry_counts", {}),
            "review_feedback": {},
            "active_ids": [],
            "blocked_ids": [],
            "blown_ids": [],
        }

    def fake_integrate(state):
        return {"final_report": "integrated", "cost": {"model_calls": 0}}

    monkeypatch.setattr(graph_module, "plan_architecture", fake_plan)
    monkeypatch.setattr(graph_module, "split_packages", fake_split)
    monkeypatch.setattr(graph_module, "specialist_node", fake_specialist)
    monkeypatch.setattr(graph_module, "review", fake_review)
    monkeypatch.setattr(graph_module, "integrate", fake_integrate)
    monkeypatch.setattr(graph_module, "_write_board", lambda state, statuses=None: "board")

    connection = sqlite3.connect(":memory:", check_same_thread=False)
    checkpointer = SqliteSaver(connection)
    checkpointer.setup()
    compiled = graph_module.build_graph().compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "production-flow"}}

    result = compiled.invoke({"goal": "dependency flow", "run_id": "flow-test"}, config)
    while "__interrupt__" in result:
        result = compiled.invoke(Command(resume={"approved": True}), config)

    assert waves == [["root-a", "root-b"], ["child"]]
    assert result["final_report"] == "integrated"
