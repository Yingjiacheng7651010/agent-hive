"""架构安全验证的图集成回归测试（card-ai-arch-security 批次 2）。

只通过公开模块接口与图 seam 验证；LLM 调用一律 monkeypatch 为空（不真调模型）。
"""
from __future__ import annotations

import sqlite3

import pytest

import agent_hive.graph as graph_module
from agent_hive.contract_spec import PackageSpec
from agent_hive.threat_model import ValidationPolicy, load_threat_catalog
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

# 一个确定会触发规则引擎 fail 的缺陷架构（幻觉引用 + risks 空 + 缺失认证/校验）
_BAD_ARCH = {
    "overview": "一个接收外部输入并执行命令的系统，没有任何防护设计。",
    "modules": [
        {
            "name": "api",
            "responsibility": "接收外部请求，调用命令执行器完成任务",
            "interfaces": ["handle(request)", "调用: 不存在的模块X"],
            "owner_role": "编码",
        },
        {
            "name": "executor",
            "responsibility": "执行系统命令",
            "interfaces": ["run(cmd)"],
            "owner_role": "编码",
        },
    ],
    "risks": [],
}

# 一个规则引擎应判定无缺陷的干净架构
_GOOD_ARCH = {
    "overview": "带认证、审计、限流与降级设计的待办事项系统。",
    "modules": [
        {
            "name": "api",
            "responsibility": "对外接口：完成用户身份认证与输入校验，限流保护，失败降级返回明确错误",
            "interfaces": ["handle(request)"],
            "owner_role": "编码",
        },
        {
            "name": "store",
            "responsibility": "持久化存储，所有操作写入不可变审计日志",
            "interfaces": ["save(item)", "list()"],
            "owner_role": "编码",
        },
    ],
    "risks": ["模型输出未命中 schema 时按不可信数据处理并重试"],
}


def _patch_llm_off(monkeypatch):
    """LLM 语义验证一律返回空（规则引擎纯确定性跑）。"""
    monkeypatch.setattr(graph_module, "run_llm_validation", lambda arch, catalog: [])


def test_graph_compiles_with_validate_node():
    compiled = graph_module.build_graph().compile()
    graph = compiled.get_graph()
    assert "validate_architecture" in graph.nodes
    assert "plan_architecture" in graph.nodes


def test_validate_node_skips_when_skip_flag(monkeypatch):
    _patch_llm_off(monkeypatch)
    state = {"skip_arch_security": True, "architecture_object": _BAD_ARCH}
    out = graph_module.validate_architecture(state)
    assert out["security_verdict"] == "pass"
    assert "跳过" in out["security_report"]
    assert out["security_report_object"]["skipped"] is True


def test_validate_node_skips_when_no_structured_arch(monkeypatch):
    """向后兼容：state 无 architecture_object 时不验证、不报错。"""
    _patch_llm_off(monkeypatch)
    out = graph_module.validate_architecture({})
    assert out["security_verdict"] == "pass"


def test_validate_node_fail_sets_remediation_feedback(monkeypatch):
    _patch_llm_off(monkeypatch)
    state = {"architecture_object": _BAD_ARCH, "reject_count": 0}
    out = graph_module.validate_architecture(state)
    assert out["security_verdict"] == "fail"
    assert "整改" in out["approval_feedback"]
    assert out["reject_count"] == 1


def test_validate_node_fail_allowed_no_feedback(monkeypatch):
    """显式放行时 verdict 仍为 fail（如实呈现），但不再回流。"""
    _patch_llm_off(monkeypatch)
    state = {"architecture_object": _BAD_ARCH, "allow_insecure_architecture": True}
    out = graph_module.validate_architecture(state)
    assert out["security_verdict"] == "fail"
    assert "approval_feedback" not in out


def test_validate_node_pass_clean_arch(monkeypatch):
    _patch_llm_off(monkeypatch)
    out = graph_module.validate_architecture({"architecture_object": _GOOD_ARCH})
    assert out["security_verdict"] in ("pass", "pass_with_warnings")
    assert "security_report" in out
    assert "approval_feedback" not in out


def test_route_after_validate():
    assert graph_module.route_after_validate({"skip_arch_security": True}) == "approve_architecture"
    assert graph_module.route_after_validate({"security_verdict": "fail"}) == "plan_architecture"
    assert graph_module.route_after_validate(
        {"security_verdict": "fail", "allow_insecure_architecture": True}
    ) == "approve_architecture"
    assert graph_module.route_after_validate({"security_verdict": "pass"}) == "approve_architecture"


def test_load_policy_defaults_and_rejects_relaxed():
    assert graph_module._load_policy(None).fail_on_severity == "high"
    # 放宽到低于 high 的策略文件回退保守默认
    policy = graph_module._load_policy({"fail_on_severity": "low", "llm_enabled": False})
    assert policy.fail_on_severity == "high"
    assert policy.llm_enabled is True
    # 合法策略生效
    policy = graph_module._load_policy({"fail_on_severity": "critical", "llm_enabled": False})
    assert policy.fail_on_severity == "critical"
    assert policy.llm_enabled is False


def test_load_policy_exclusions_list_to_tuple():
    policy = graph_module._load_policy({"exclusions": ["T-DISC-1"]})
    assert policy.exclusions == ("T-DISC-1",)


def test_full_flow_backward_compatible_when_monkeypatched(monkeypatch):
    """旧生产流回归模式：plan 被替换（无 architecture_object）时管线照常走到集成。"""
    def fake_plan(state):
        return {"architecture": "# fake", "architecture_approved": False}

    def fake_split(state):
        pkg = PackageSpec(
            id="solo", title="solo", role="调研", goal="g", contract="c",
            expected_output="report", acceptance=["done"], deliverable="workspace/solo/",
        ).model_dump()
        return {
            "packages": [pkg], "batch_approved": False, "retry_counts": {},
            "retry_ids": [], "passed_ids": [], "active_ids": [], "blocked_ids": [],
            "blown_ids": [], "review_feedback": {}, "reject_count": 0,
        }

    def fake_specialist(state):
        pid = state["current_package"]["id"]
        return {
            "reports": {pid: f"r:{pid}"},
            "report_objects": {pid: {"parse_ok": True, "completion": ["done"], "deliverables": []}},
        }

    def fake_review(state):
        return {
            "review": "ok", "passed_ids": list(state["active_ids"]),
            "retry_ids": [], "retry_counts": state.get("retry_counts", {}),
            "review_feedback": {}, "active_ids": [], "blocked_ids": [], "blown_ids": [],
        }

    def fake_integrate(state):
        return {"final_report": "integrated", "cost": {"model_calls": 0}}

    monkeypatch.setattr(graph_module, "plan_architecture", fake_plan)
    monkeypatch.setattr(graph_module, "split_packages", fake_split)
    monkeypatch.setattr(graph_module, "specialist_node", fake_specialist)
    monkeypatch.setattr(graph_module, "review", fake_review)
    monkeypatch.setattr(graph_module, "integrate", fake_integrate)
    monkeypatch.setattr(graph_module, "_write_board", lambda state, statuses=None: "board")
    monkeypatch.setattr(graph_module, "run_llm_validation", lambda arch, catalog: [])

    connection = sqlite3.connect(":memory:", check_same_thread=False)
    checkpointer = SqliteSaver(connection)
    checkpointer.setup()
    compiled = graph_module.build_graph().compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "arch-sec-back-compat"}}
    result = compiled.invoke({"goal": "x", "run_id": "arch-sec-test"}, config)
    while "__interrupt__" in result:
        result = compiled.invoke(Command(resume={"approved": True}), config)
    assert result["final_report"] == "integrated"
    assert result["security_verdict"] == "pass"  # 无结构化架构 → 跳过


def test_catalog_and_policy_roundtrip():
    catalog = load_threat_catalog()
    assert len(catalog.threats) >= 12
    policy = ValidationPolicy()
    assert policy.fail_on_severity == "high"