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
    """并行专家回传合并（fan-out 多分支写不同包 id，合并语义安全）。

    并发安全前提：单个波次内 active_ids 互异，每个专家只回写自己包 id 对应的
    ``reports`` / ``report_objects`` 键，因此同波内不存在键冲突；跨波（返工）对同一键
    的覆写发生在顺序阶段（review 之后），last-write-wins 语义正确。active_ids /
    blocked_ids / blown_ids / retry_ids / passed_ids 由单实例节点（dispatch / review）
    顺序写，不经过本 reducer。
    """
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
    retry_ids: list[str]  # 本轮需要重派的工作包 id（返工波次只重派这些）
    review_feedback: dict[str, str]  # 包 id -> 驳回反馈（每轮全量覆写，不累积）
    passed_ids: list[str]  # 已验收通过的包 id（冻结，后续轮次不再重审）
    active_ids: list[str]  # 当前波次正在执行的包 id（dispatch 写入，review 消费）
    blocked_ids: list[str]  # 永久阻塞的包 id（上游熔断/阻塞的传递闭包，永不执行）
    blown_ids: list[str]  # 熔断的包 id（返工轮次耗尽，终态失败）
    board: str  # 项目看板 markdown（首脑唯一维护者）
    board_statuses: dict[str, str]  # 看板各包状态（integrate 归档时保留）
    review: str  # 首脑评审结论
    review_round: int  # 全局单调评审波次（审计文件命名，避免跨包计数覆盖）
    review_warnings: list[str]  # 无效归因等不改变状态但需审计的问题
    final_report: str  # 最终交付报告
    integration: dict  # 集成深模块的结构化结果（IntegrationResult.to_dict）
    allow_integration_checks: bool  # 显式允许动态全局检查
    integration_checks: list[dict]  # shell=False 的 argv 检查定义
    integration_check_timeout: int  # 动态检查单项超时秒数
    cost: dict  # token/成本统计
