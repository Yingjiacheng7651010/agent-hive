# 卡片 20 修补架构方案

> 状态：架构方案已获用户批准
> 批准记录：用户选择“批准，按方案实施”
> 目标：建立可验证的测试体系，修正依赖感知调度与并发状态一致性，升级整体集成，统一契约事实源。

## 1. 现状审计

- 仓库没有 `tests/`，`uv run pytest -q` 返回 `no tests ran`。
- `agent_hive/graph.py` 的 `_topo_order()` 仅排序，`continue_to_specialists()` 仍一次性发送全部工作包；下游可能早于上游验收执行。
- `chief.integrate()` 将工作包复制到 `dist/<package_id>/`，没有统一路径合并、冲突检测、整体验证或结构化失败状态。
- `skill/contracts.md` 与 `agent_hive/prompts.py` 存在手工重复维护的契约内容。
- 全局用量统计器需要明确并发安全语义。

## 2. 目标架构

### 2.1 契约事实源

新增 `agent_hive/contract_spec.py` 作为机器可读契约规范；`prompts.py` 从该模块读取角色、限制、状态和 schema 元数据；`skill/contracts.md` 作为生成的 DSH 交接文档，并由同步测试防止漂移。

### 2.2 依赖感知调度

新增 `agent_hive/scheduler.py`，提供纯函数：依赖图校验、就绪层选择、阻塞传播和执行层构建；`paths.py` 集中校验 run/package id 与 workspace 围栏。图状态增加 `active_ids`、`blocked_ids`、`blown_ids`。每次只派发当前就绪层；该层验收完成后才计算下一层；熔断包自身不再重派，其下游标记为阻塞。

### 2.3 整体集成

新增 `agent_hive/integration.py`，将通过包的 workspace 交付物合并到统一 `dist/` 根目录，规范化路径，拒绝非同内容冲突，写出 `manifest.json`，执行安全的静态验证，并返回结构化 `IntegrationResult`。未通过/阻塞包以 `partial` 与 `unresolved_packages` 如实呈现；动态测试/构建检查必须显式开启，并使用 argv + `shell=False`。

### 2.4 测试 seam

测试只通过公开模块接口验证：调度选择、fan-out 同层并发、状态合并、返工/熔断/阻塞、文件合并冲突、整体验证、契约同步、路径守卫和 checkpoint 恢复。

## 3. 模块接口

```python
# scheduler.py（纯函数公开 seam）
validate_dependency_graph(packages) -> None
build_execution_layers(packages) -> list[list[str]]
select_ready_packages(
    packages, passed_ids=(), blocked_ids=(), retry_ids=(), blown_ids=()
) -> list[dict]
classify_blocked_packages(
    packages, passed_ids=(), blocked_ids=(), blown_ids=()
) -> list[str]
pending_package_ids(packages, passed_ids=(), blocked_ids=(), blown_ids=()) -> list[str]

# paths.py（集中路径策略）
validate_run_id(run_id) -> str
validate_package_id(package_id) -> str
safe_run_dir(run_id, root=...) -> Path
safe_package_dir(run_dir, package_id) -> Path

# integration.py（整体集成公开 seam）
@dataclass
class IntegrationResult:
    status: Literal["success", "partial", "conflict", "validation_failed", "no_packages"]
    merged_packages: list[str]
    unresolved_packages: list[str]
    files: list[IntegratedFile]
    conflicts: list[Conflict]
    validation_errors: list[str]
    checks: list[CheckResult]

integrate_packages(
    run_dir, packages, passed_ids, report_objects=None, *,
    enable_dynamic_checks=False, dynamic_checks=None, dynamic_timeout=120
) -> IntegrationResult
normalize_artifact_path(raw, run_dir, package_id) -> tuple
run_dynamic_checks(dist_dir, checks, *, timeout=120, env=None) -> list[CheckResult]
```

## 4. 工作包映射

| 工作包 | 角色 | 依赖 | 负责人 |
|---|---|---|---|
| contract-source | 编码 | [] | DSH 编码专家 |
| scheduler-core | 编码 | [] | DSH 编码专家 |
| integration-core | 编码 | [] | DSH 编码专家 |
| regression-tests | 测试 | [contract-source, scheduler-core, integration-core] | DSH 测试专家 |
| runtime-integration | 首脑自理 | [contract-source, scheduler-core, integration-core, regression-tests] | 首脑 |

## 5. 约束

- 共享根目录和最终集成只能由首脑修改；专家交付物写入各自工作区。
- 不自动覆盖跨包同路径且内容不同的文件。
- 不把“测试断言缺陷存在”视为通过。
- 生成代码的动态测试/构建检查默认关闭，需显式开关；`scripts/verify.py` 提供无模型 pytest + compileall + contract drift 全局验收。
- 所有失败必须在状态、manifest 或最终报告中如实呈现。
