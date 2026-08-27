"""LangGraph 首脑编排图。

流程：定架构 → **架构安全验证** → 审批：架构 → 分包 → 审批：批次 → 按层并行派发专家
（严格依赖分层）→ 验收评审（评估-优化回路：守卫先行、只重审本波 active_ids、逐包熔断、
阻塞传播）→ 集成交付。两个审批关口用 interrupt() 暂停，等待用户 Command(resume=...) 恢复；
resume 值用 ApprovalDecision 做 schema 校验；驳回次数有上限。

架构安全验证（card-ai-arch-security）：
- validate_architecture 节点在 plan_architecture 之后、审批①之前执行；
- 规则引擎（确定性，纯标准库）+ LLM 语义验证（异常降级为空）双通道；
- verdict=fail 且未显式放行时，不进入审批，把整改建议汇总为驳回反馈自动回流重做架构；
- skip_arch_security 显式跳过时行为与旧管线一致（向后兼容）。

依赖分层（见 scheduler.py）：
- dispatch 节点用 select_ready_packages 选出当前波次（返工重派 or 下一就绪层），写 active_ids。
- 条件边只把 active_ids 作为 Send 并行派发；同层并发，该层所有分支汇合后才进入 review。
- review 更新 passed/blown/blocked；route_after_review 依据「是否还有未终态包」决定继续或集成。
"""
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send, interrupt

from .arch_security import (
    render_security_report_md,
    validate_architecture as run_security_validation,
)
from .arch_security_llm import run_llm_validation
from .chief import (
    _write_board,
    compute_board_statuses,
    integrate,
    plan_architecture,
    review,
    split_packages,
)
from .prompts import MAX_REJECT_COUNT, ApprovalDecision
from .scheduler import pending_package_ids, select_ready_packages
from .specialists import specialist_node
from .state import HiveState
from .threat_model import ValidationPolicy, load_threat_catalog


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


def _load_policy(raw: dict | None) -> ValidationPolicy:
    """从 state 反序列化 ValidationPolicy；非法/放宽值回退保守默认（绝不静默放宽）。"""
    if not raw:
        return ValidationPolicy()
    try:
        kwargs = dict(raw)
        if isinstance(kwargs.get("exclusions"), list):
            kwargs["exclusions"] = tuple(kwargs["exclusions"])
        policy = ValidationPolicy(**kwargs)
        if not ValidationPolicy.validate_fail_on_severity(policy.fail_on_severity):
            return ValidationPolicy()
        return policy
    except (TypeError, ValueError):
        return ValidationPolicy()


def validate_architecture(state):
    """架构安全验证：规则引擎（确定性）+ LLM 语义验证 → SecurityReport → 裁决。

    verdict=fail 且未显式放行时，把全部整改建议汇总为驳回反馈写入 approval_feedback，
    由 route_after_validate 回流 plan_architecture（评估-优化回路闭环，防无限回流靠
    reject_count 上限）。
    """
    if state.get("skip_arch_security"):
        return {
            "security_verdict": "pass",
            "security_report": "（已显式跳过架构安全验证，此结论已入审计）",
            "security_report_object": {"verdict": "pass", "skipped": True},
        }

    arch = state.get("architecture_object") or {}
    if not arch:
        # 无结构化架构时无验证对象（向后兼容：旧测试/旧 state 未产出 architecture_object）
        return {
            "security_verdict": "pass",
            "security_report": "（无结构化架构输入，跳过安全验证）",
            "security_report_object": {"verdict": "pass", "skipped": True},
        }
    policy = _load_policy(state.get("security_policy"))
    catalog = load_threat_catalog()

    llm_findings: list = []
    if policy.llm_enabled:
        try:
            llm_findings = run_llm_validation(arch, catalog)
        except Exception:  # noqa: BLE001 —— LLM 失败不阻断，规则引擎兜底
            llm_findings = []

    report = run_security_validation(arch, catalog, policy, llm_findings)
    md = render_security_report_md(report)

    updates = {
        "security_report": md,
        "security_report_object": report.to_dict(),
        "security_verdict": report.verdict,
    }
    if report.verdict == "fail" and not state.get("allow_insecure_architecture"):
        reject = state.get("reject_count", 0) + 1
        if reject > MAX_REJECT_COUNT:
            raise RuntimeError(
                f"架构安全验证连续 {MAX_REJECT_COUNT} 次未通过，停止运行。"
                "请直接给首脑明确的安全整改意见后再试。"
            )
        remediations = "\n".join(
            f"- [{f.module}] {f.threat_id}：{f.remediation}"
            for f in report.findings
            if f.severity in ("critical", "high")
        ) or "（无高危发现，请重新生成架构）"
        updates["approval_feedback"] = (
            f"架构安全验证未通过（verdict=fail），必须逐条整改：\n{remediations}"
        )
        updates["reject_count"] = reject
    return updates


def route_after_validate(state):
    """fail 且未放行 → 自动回流重做架构；否则进入审批①。"""
    if state.get("skip_arch_security"):
        return "approve_architecture"
    verdict = state.get("security_verdict", "")
    if verdict == "fail" and not state.get("allow_insecure_architecture"):
        return "plan_architecture"
    return "approve_architecture"


def approve_architecture(state):
    """关口一：把架构方案与安全报告呈交用户。"""
    decision = _parse_decision(interrupt({
        "kind": "审批单：架构方案",
        "architecture": state.get("architecture", ""),
        "security_report": state.get("security_report", ""),
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


def dispatch(state):
    """派发节点：选出当前波次（返工重派 or 下一就绪层），写 active_ids 与看板。"""
    packages = state.get("packages", [])
    retry_ids = state.get("retry_ids") or []
    passed_ids = state.get("passed_ids") or []
    blocked_ids = state.get("blocked_ids") or []
    blown_ids = state.get("blown_ids") or []
    retry_counts = state.get("retry_counts", {})

    try:
        wave = select_ready_packages(
            packages, passed_ids, blocked_ids, retry_ids, blown_ids,
        )
    except ValueError as exc:
        raise RuntimeError(
            f"派发依赖图校验失败：{exc}（packages={len(packages)}，"
            f"passed={len(passed_ids)}，blocked={len(blocked_ids)}）"
        ) from exc
    active_ids = [p["id"] for p in wave]
    if not active_ids:
        raise RuntimeError("派发列表为空：无就绪工作包（依赖图或调度状态不一致）")

    statuses = compute_board_statuses(
        packages, active_ids, passed_ids, blocked_ids, blown_ids, retry_counts)
    board = _write_board(state, statuses)
    return {"active_ids": active_ids, "board": board, "board_statuses": statuses}


def continue_to_specialists(state):
    """fan-out 路由：只派发 active_ids（当前波次），同层并发；返工时带驳回反馈。"""
    packages = state.get("packages", [])
    pkg_by_id = {p["id"]: p for p in packages}
    active_ids = state.get("active_ids") or []
    feedback_map = state.get("review_feedback") or {}

    sends = []
    for pid in active_ids:
        pkg = pkg_by_id.get(pid)
        if pkg is None:
            continue
        pkg = dict(pkg)
        pkg["feedback"] = feedback_map.get(pid, "")
        sends.append(Send("specialist", {**state, "current_package": pkg}))
    if not sends:
        raise RuntimeError("派发列表为空：工作包为空或 active_ids 全部无效")
    return sends


def route_after_review(state):
    """评估-优化回路：仍有未终态包（通过/熔断/阻塞之外）→ 继续派发；否则集成。"""
    packages = state.get("packages", [])
    pending = pending_package_ids(
        packages,
        state.get("passed_ids") or [],
        state.get("blocked_ids") or [],
        state.get("blown_ids") or [],
    )
    return "dispatch" if pending else "integrate"


def build_graph():
    g = StateGraph(HiveState)
    g.add_node("plan_architecture", plan_architecture)
    g.add_node("validate_architecture", validate_architecture)
    g.add_node("approve_architecture", approve_architecture)
    g.add_node("split_packages", split_packages)
    g.add_node("approve_batch", approve_batch)
    g.add_node("dispatch", dispatch)
    g.add_node("specialist", specialist_node)
    g.add_node("review", review)
    g.add_node("integrate", integrate)

    g.add_edge(START, "plan_architecture")
    g.add_edge("plan_architecture", "validate_architecture")
    g.add_conditional_edges(
        "validate_architecture",
        route_after_validate,
        {"approve_architecture": "approve_architecture", "plan_architecture": "plan_architecture"},
    )
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
    # fan-out：dispatch 节点写 active_ids，条件边只派发当前就绪层，
    # 并行进入 specialist，全部完成后汇合到 review
    g.add_conditional_edges("dispatch", continue_to_specialists, ["specialist"])
    g.add_edge("specialist", "review")
    g.add_conditional_edges(
        "review",
        route_after_review,
        {"dispatch": "dispatch", "integrate": "integrate"},
    )
    g.add_edge("integrate", END)
    return g
