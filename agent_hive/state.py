"""HiveState —— 首脑与专家共享的图状态。"""
from typing import Annotated, TypedDict


class WorkPackage(TypedDict, total=False):
    id: str
    title: str
    role: str  # 编码 / 测试 / 评审 / 调研
    goal: str
    contract: str  # 接口契约
    expected_output: str  # 产出类型与格式（输出守卫依据）
    depends_on: list[str]  # 依赖的工作包 id（拓扑分批依据）
    size: str  # S / M / L
    priority: int  # 1 最高
    acceptance: list[str]  # 验收标准，可逐项打勾
    deliverable: str  # 交付物路径
    feedback: str  # 驳回反馈（返工时带入）


def merge_dict(left: dict, right: dict) -> dict:
    """并行专家回传合并（fan-out 多分支写不同包 id，合并语义安全）。"""
    out = dict(left)
    out.update(right)
    return out


class HiveState(TypedDict, total=False):
    goal: str
    run_id: str
    tier: str  # T0 全流程 / T1 回填分工 / T2 顾问模式
    architecture: str  # 架构文档 markdown
    architecture_approved: bool
    approval_feedback: str  # 用户驳回反馈（重做时吸收）
    reject_count: int  # 审批关口累计驳回次数（防无限驳回烧钱）
    packages: list[WorkPackage]
    batch_approved: bool
    current_package: WorkPackage  # fan-out 时当前专家要处理的包
    reports: Annotated[dict[str, str], merge_dict]  # 包 id -> 成果回传 markdown
    report_objects: Annotated[dict[str, dict], merge_dict]  # 包 id -> 结构化回传（守卫消费）
    retry_counts: dict[str, int]  # 逐包返工次数（替换全局 retry_round）
    retry_ids: list[str]  # 本轮需要重派的工作包 id
    review_feedback: dict[str, str]  # 包 id -> 驳回反馈（每轮全量覆写，不累积）
    passed_ids: list[str]  # 已验收通过的包 id（后续轮次不再重审）
    board: str  # 项目看板 markdown（首脑唯一维护者）
    board_statuses: dict[str, str]  # 看板各包状态（integrate 归档时保留）
    review: str  # 首脑评审结论
    final_report: str  # 最终交付报告
    cost: dict  # token/成本统计
