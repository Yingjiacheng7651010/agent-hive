from __future__ import annotations

import threading
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from agent_hive.graph import build_graph, continue_to_specialists, dispatch
from agent_hive.state import merge_dict


class FanoutState(TypedDict, total=False):
    jobs: list[str]
    current_job: str
    packets: Annotated[dict[str, str], merge_dict]


def test_real_langgraph_send_fanout_runs_workers_concurrently_and_reducer_keeps_packets():
    # Sequential execution deadlocks at this barrier. Success is direct evidence
    # that two Send branches overlap, without timing assertions or arbitrary sleeps.
    barrier = threading.Barrier(2, timeout=3)

    def fanout(state: FanoutState):
        return [Send("worker", {**state, "current_job": job}) for job in state["jobs"]]

    def worker(state: FanoutState):
        barrier.wait()
        job = state["current_job"]
        return {"packets": {job: f"done:{job}"}}

    graph = StateGraph(FanoutState)
    graph.add_node("dispatch", lambda state: state)
    graph.add_node("worker", worker)
    graph.add_edge(START, "dispatch")
    graph.add_conditional_edges("dispatch", fanout, ["worker"])
    graph.add_edge("worker", END)

    result = graph.compile().invoke({"jobs": ["alpha", "beta"], "packets": {}})

    assert result["packets"] == {"alpha": "done:alpha", "beta": "done:beta"}


def test_continue_to_specialists_sends_only_active_ids_not_downstream_packages():
    state = {
        "goal": "regression",
        "packages": [
            {"id": "ready-a", "depends_on": []},
            {"id": "ready-b", "depends_on": []},
            {"id": "downstream", "depends_on": ["ready-a", "ready-b"]},
        ],
        "active_ids": ["ready-a", "ready-b"],
        "review_feedback": {"ready-b": "fix the seam", "downstream": "must not leak"},
    }

    sends = continue_to_specialists(state)
    sent_packages = [send.arg["current_package"] for send in sends]

    assert [p["id"] for p in sent_packages] == ["ready-a", "ready-b"]
    assert sent_packages[0]["feedback"] == ""
    assert sent_packages[1]["feedback"] == "fix the seam"
    assert all(send.node == "specialist" for send in sends)


def test_production_graph_compiles_with_dependency_aware_nodes():
    compiled = build_graph().compile()
    assert compiled is not None


def test_dispatch_never_requeues_a_blown_package(monkeypatch):
    monkeypatch.setattr("agent_hive.graph._write_board", lambda state, statuses: "board")
    result = dispatch({
        "run_id": "dispatch-test",
        "packages": [{"id": "blown", "depends_on": []}, {"id": "free", "depends_on": []}],
        "passed_ids": [],
        "blocked_ids": [],
        "blown_ids": ["blown"],
        "retry_ids": [],
        "retry_counts": {},
    })

    assert result["active_ids"] == ["free"]
