"""LangGraph 首脑编排图。

流程：定架构 → 审批：架构 → 分包 → 审批：批次 → 并行派发专家（拓扑序）→
验收评审（评估-优化回路：守卫先行、只重审未通过包、缺陷可归因、逐包熔断）→ 集成交付。
两个审批关口用 interrupt() 暂停，等待用户 Command(resume=...) 恢复；
resume 值用 ApprovalDecision 做 schema 校验；驳回次数有上限。
"""
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send, interrupt

from .chief import _write_board, integrate, plan_architecture, review, split_packages
from .prompts import MAX_REJECT_COUNT, ApprovalDecision
from .specialists import specialist_node
from .state import HiveState


def _parse_decision(decision) -> ApprovalDecision:
    """resume 值 schema 校验：非法值一律视为驳回（保守默认），拒绝静默放行。"""
    try:
        d = ApprovalDecision.model_validate(decision) if isinstance(decision, dict) else None
        if d is None:
            raise ValueError
        return d
    except Exception:
        return ApprovalDecision(approved=False,
                                feedback=f"审批值非法（收到 {decision!r}），按驳回处理")


def approve_architecture(state):
    """关口一：把架构方案呈交用户。"""
    decision = _parse_decision(interrupt({
        "kind": "审批单：架构方案",
        "architecture": state.get("architecture", ""),
    }))
    if decision.approved:
        return {"architecture_approved": True, "approval_feedback": "",
                "reject_count": 0}
    reject = state.get("reject_count", 0) + 1
    if reject > MAX_REJECT_COUNT:
        raise RuntimeError(f"架构方案已驳回 {MAX_REJECT_COUNT} 次，停止运行。请直接给首脑明确修改意见后再试。")
    return {"architecture_approved": False,
            "approval_feedback": decision.feedback or "不同意，请重做",
            "reject_count": reject}


def route_after_architecture(state):
    return "plan_architecture" if not state.get("architecture_approved") else "split_packages"


def approve_batch(state):
    """关口二：把批次表（工作包 × 角色 × 依赖 × 成本）呈交用户。"""
    batch = [
        {"id": p["id"], "title": p["title"], "role": p["role"], "goal": p["goal"],
         "depends_on": p.get("depends_on") or [], "size": p.get("size", "M"),
         "acceptance": p.get("acceptance", []), "deliverable": p.get("deliverable", ""),
         "expected_output": p.get("expected_output", "")}
        for p in state["packages"]
    ]
    decision = _parse_decision(interrupt({"kind": "审批单：批次表", "batch": batch}))
    if decision.approved:
        return {"batch_approved": True, "approval_feedback": "", "reject_count": 0}
    reject = state.get("reject_count", 0) + 1
    if reject > MAX_REJECT_COUNT:
        raise RuntimeError(f"批次表已驳回 {MAX_REJECT_COUNT} 次，停止运行。请直接给首脑明确修改意见后再试。")
    return {"batch_approved": False,
            "approval_feedback": decision.feedback or "不同意，请重做",
            "reject_count": reject}


def route_after_batch(state):
    return "dispatch" if state.get("batch_approved") else "split_packages"


def _topo_order(packages: list[dict]) -> list[dict]:
    """按 depends_on 拓扑排序：依赖在前、下游在后（同波内尽力保证上游先执行）。"""
    by_id = {p["id"]: p for p in packages}
    emitted: set[str] = set()
    ordered: list[dict] = []
    remaining = list(packages)
    while remaining:
        progress = False
        for p in list(remaining):
            if all(d in emitted for d in (p.get("depends_on") or [])):
                ordered.append(p)
                emitted.add(p["id"])
                remaining.remove(p)
                progress = True
        if not progress:  # 环（split_packages 已校验，此处兜底）
            ordered.extend(remaining)
            break
    return ordered


def dispatch(state):
    """派发占位节点：把看板状态置为「进行中」（修复：进行中状态此前从未写入）。"""
    packages = state.get("packages", [])
    retry_ids = state.get("retry_ids") or []
    statuses = {}
    if retry_ids:
        statuses = {p["id"]: f"返工中" for p in packages if p["id"] in retry_ids}
    else:
        statuses = {p["id"]: "进行中" for p in packages}
    board = _write_board(state, statuses)
    return {"board": board}


def continue_to_specialists(state):
    """把工作包并行派发：拓扑序 + 返工时只重派未通过包（带驳回反馈）。"""
    retry_ids = state.get("retry_ids") or []
    feedback_map = state.get("review_feedback") or {}
    packages = state.get("packages", [])
    if retry_ids:
        targets = [p for p in packages if p["id"] in retry_ids]
    else:
        targets = packages
    targets = _topo_order(targets)
    if not targets:
        raise RuntimeError("派发列表为空：工作包为空或 retry_ids 全部无效")
    sends = []
    for pkg in targets:
        pkg = dict(pkg)
        pkg["feedback"] = feedback_map.get(pkg["id"], "")
        sends.append(Send("specialist", {**state, "current_package": pkg}))
    return sends


def route_after_review(state):
    """评估-优化回路：仍有未通过包（且未熔断）→ 回派；否则集成。"""
    if state.get("retry_ids"):
        return "dispatch"
    return "integrate"


def build_graph():
    g = StateGraph(HiveState)
    g.add_node("plan_architecture", plan_architecture)
    g.add_node("approve_architecture", approve_architecture)
    g.add_node("split_packages", split_packages)
    g.add_node("approve_batch", approve_batch)
    g.add_node("dispatch", dispatch)
    g.add_node("specialist", specialist_node)
    g.add_node("review", review)
    g.add_node("integrate", integrate)

    g.add_edge(START, "plan_architecture")
    g.add_edge("plan_architecture", "approve_architecture")
    g.add_conditional_edges(
        "approve_architecture",
        route_after_architecture,
        {"plan_architecture": "plan_architecture", "split_packages": "split_packages"},
    )
    g.add_edge("split_packages", "approve_batch")
    g.add_conditional_edges(
        "approve_batch",
        route_after_batch,
        {"dispatch": "dispatch", "split_packages": "split_packages"},
    )
    # fan-out：dispatch 的条件边返回 list[Send]，并行进入 specialist，全部完成后汇合到 review
    g.add_conditional_edges("dispatch", continue_to_specialists, ["specialist"])
    g.add_edge("specialist", "review")
    g.add_conditional_edges(
        "review",
        route_after_review,
        {"dispatch": "dispatch", "integrate": "integrate"},
    )
    g.add_edge("integrate", END)
    return g
