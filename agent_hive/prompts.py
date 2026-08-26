"""提示词与结构化输出 schema —— 契约单一事实源的重导出层。

本文件不再重复定义任何契约常量：版本、角色、限制、状态流、字段元数据、
提示词与结构化 schema 全部来自 `agent_hive.contract_spec`（单一事实源）。
保留原模块的公开名字，使 chief.py / graph.py / specialists.py 无需改动即可导入。

- 改契约：只改 `agent_hive/contract_spec.py`，本文件自动跟进（无需手工同步）。
- 文档：`skill/contracts.md` 由 contract_spec.render_contracts_md() 生成。
"""
from .contract_spec import (  # noqa: F401  (re-export for backward compatibility)
    # 版本与限制
    CONTRACT_VERSION,
    DEFAULT_ROLE,
    ROLE_NAMES,
    MAX_RETRY_ROUNDS,
    MAX_REJECT_COUNT,
    PROBE_CALL_BUDGET,
    BOARD_STATES,
    STATE_FLOW_LINE,
    # 结构化 schema（字段元数据）
    ModulePlan,
    ArchitecturePlan,
    PackageSpec,
    PackagePlan,
    ReportSpec,
    Verdict,
    ReviewVerdicts,
    ApprovalDecision,
    # 首脑提示词
    CHIEF_ARCHITECT_PROMPT,
    CHIEF_PACKAGER_PROMPT,
    CHIEF_REVIEWER_PROMPT,
    CHIEF_INTEGRATOR_PROMPT,
    CHIEF_SYSTEM_PROMPT,
    # 角色专家提示词
    ROLE_PROMPTS,
    ROLE_SUMMARIES,
    # 渲染/校验接口
    render_model_fields,
    render_role_summaries,
    render_contracts_md,
    check_contracts_drift,
)

__all__ = [
    "CONTRACT_VERSION",
    "DEFAULT_ROLE",
    "ROLE_NAMES",
    "MAX_RETRY_ROUNDS",
    "MAX_REJECT_COUNT",
    "PROBE_CALL_BUDGET",
    "BOARD_STATES",
    "STATE_FLOW_LINE",
    "ModulePlan",
    "ArchitecturePlan",
    "PackageSpec",
    "PackagePlan",
    "ReportSpec",
    "Verdict",
    "ReviewVerdicts",
    "ApprovalDecision",
    "CHIEF_ARCHITECT_PROMPT",
    "CHIEF_PACKAGER_PROMPT",
    "CHIEF_REVIEWER_PROMPT",
    "CHIEF_INTEGRATOR_PROMPT",
    "CHIEF_SYSTEM_PROMPT",
    "ROLE_PROMPTS",
    "ROLE_SUMMARIES",
    "render_model_fields",
    "render_role_summaries",
    "render_contracts_md",
    "check_contracts_drift",
]
