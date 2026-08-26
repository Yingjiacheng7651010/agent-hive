from __future__ import annotations

import sqlite3
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class ApprovalState(TypedDict, total=False):
    value: int
    approved: bool


def test_sqlite_checkpoint_restores_interrupt_and_resume_state():
    def gate(state: ApprovalState):
        decision = interrupt({"kind": "test-approval", "value": state["value"]})
        return {"approved": bool(decision["approved"])}

    graph = StateGraph(ApprovalState)
    graph.add_node("gate", gate)
    graph.add_edge(START, "gate")
    graph.add_edge("gate", END)

    connection = sqlite3.connect(":memory:", check_same_thread=False)
    checkpointer = SqliteSaver(connection)
    checkpointer.setup()
    compiled = graph.compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "checkpoint-regression"}}

    paused = compiled.invoke({"value": 42}, config)
    assert paused["__interrupt__"][0].value == {"kind": "test-approval", "value": 42}

    resumed = compiled.invoke(Command(resume={"approved": True}), config)

    assert resumed["approved"] is True
    assert compiled.get_state(config).values == {"value": 42, "approved": True}
