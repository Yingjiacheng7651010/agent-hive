from __future__ import annotations

import pytest

from agent_hive.scheduler import (
    build_execution_layers,
    classify_blocked_packages,
    select_ready_packages,
    validate_dependency_graph,
)


def pkg(pid: str, *deps: str) -> dict:
    return {"id": pid, "depends_on": list(deps)}


@pytest.mark.parametrize(
    "packages, expected_fragment",
    [
        ([], "为空"),
        ([pkg("a"), pkg("a")], "重复"),
        ([pkg("a", "missing")], "不存在"),
        ([pkg("a", "b"), pkg("b", "a")], "成环"),
    ],
)
def test_dependency_graph_rejects_invalid_inputs(packages, expected_fragment):
    with pytest.raises(ValueError, match=expected_fragment):
        validate_dependency_graph(packages)


def test_scheduler_returns_same_ready_layer_and_waits_for_downstream():
    packages = [pkg("root-b"), pkg("root-a"), pkg("join", "root-a", "root-b")]

    assert build_execution_layers(packages) == [["root-a", "root-b"], ["join"]]
    assert {p["id"] for p in select_ready_packages(packages)} == {"root-a", "root-b"}
    assert [p["id"] for p in select_ready_packages(packages, passed_ids=["root-a"])] == ["root-b"]
    assert [p["id"] for p in select_ready_packages(
        packages, passed_ids=["root-a", "root-b"]
    )] == ["join"]


def test_retry_cannot_bypass_dependency_gate_or_advance_unrelated_work():
    packages = [pkg("upstream"), pkg("retry-child", "upstream"), pkg("other")]

    assert select_ready_packages(packages, retry_ids=["retry-child"]) == []
    assert [p["id"] for p in select_ready_packages(
        packages, passed_ids=["upstream"], retry_ids=["retry-child"]
    )] == ["retry-child"]


def test_blown_package_blocks_all_downstream_transitively():
    packages = [pkg("root"), pkg("child", "root"), pkg("grandchild", "child"), pkg("free")]

    blocked = classify_blocked_packages(packages, blown_ids=["root"])

    assert blocked == ["child", "grandchild"]
    assert [p["id"] for p in select_ready_packages(
        packages, blocked_ids=blocked, blown_ids=["root"]
    )] == ["free"]


@pytest.mark.parametrize("unsafe_id", ["../escape", "a/b", "a\\b", "C:drive", "", "."])
def test_dependency_graph_rejects_path_like_package_ids(unsafe_id):
    with pytest.raises(ValueError, match="id"):
        validate_dependency_graph([pkg(unsafe_id)])


def test_invalid_retry_metadata_never_advances_unrelated_work():
    packages = [pkg("ready"), pkg("other")]

    assert select_ready_packages(packages, retry_ids=["missing-id"]) == []
