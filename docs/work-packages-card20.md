# 卡片 20 修补工作包

> 批次状态：已获用户批准，按拓扑顺序执行
> 批次审批：用户选择“批准，开始派发”

## 批次 1

### contract-source
- 目标：建立契约单一事实源，减少 `contracts.md` 与 `prompts.py` 漂移。
- 接口契约：提供 `agent_hive.contract_spec` 的版本、角色、限制、结构化字段和文档渲染接口；`prompts.py` 可导入；生成文档可校验。
- expected_output：实现文件、生成/同步脚本或函数、契约同步测试说明。
- depends_on：[]
- 验收标准：契约版本可读取；关键常量不再在 prompts.py 重复定义；Skill 文档带生成标记；漂移能被自动发现。
- 交付物：`workspace/card20-contract-source/`
- size：M；priority：1；轮次上限：3

### scheduler-core
- 目标：让工作包严格按依赖层执行，并正确传播返工、熔断和阻塞状态。
- 接口契约：提供依赖图校验、就绪包选择、执行层构建和阻塞分类纯函数；图状态支持 active/blocked/blown 包集合，熔断包不得再次 ready。
- expected_output：`scheduler.py`、状态/图调度改动、设计说明。
- depends_on：[]
- 验收标准：依赖图非法时拒绝；下游不在上游通过前进入 ready；同层包可同时派发；熔断上游后下游标记阻塞；返工只重派目标包。
- 交付物：`workspace/card20-scheduler-core/`
- size：L；priority：1；轮次上限：3

### integration-core
- 目标：将通过包合并为可验证的统一交付树，而非按包复制目录。
- 接口契约：提供结构化 `IntegrationResult`；冲突、缺失交付物、静态验证错误必须可观察；动态检查需显式开关。
- expected_output：`integration.py`、集成说明、错误状态示例。
- depends_on：[]
- 验收标准：路径规范化；同路径不同内容拒绝覆盖；生成 manifest；Python 静态编译错误导致失败；不执行 shell 时仍可完成安全静态验证。
- 交付物：`workspace/card20-integration-core/`
- size：L；priority：1；轮次上限：3

## 批次 2

### regression-tests
- 目标：把卡片20的验收标准固化为可运行回归测试。
- 接口契约：仅通过公开模块接口与小型 LangGraph fan-out seam 验证，不测试私有实现细节。
- expected_output：`tests/` 测试文件、运行说明、失败复现说明。
- depends_on：[contract-source, scheduler-core, integration-core]
- 验收标准：`uv run pytest -q` 可收集并运行；覆盖依赖调度、真实同层重叠、状态隔离、返工/熔断/阻塞、集成冲突、契约同步、路径守卫。
- 交付物：根目录 `tests/` 与 `docs/card20-regression-tests.md`
- size：L；priority：1；轮次上限：3

## 批次 3

### runtime-integration
- 目标：由首脑将各交付物合并进共享根目录，补 CLI 和文档，执行终验。
- 接口契约：共享根目录只有首脑修改；所有模块必须通过统一测试和关键路径验证。
- expected_output：主目录实现、README/SECURITY 更新、终验报告。
- depends_on：[contract-source, scheduler-core, integration-core, regression-tests]
- 验收标准：`scripts/verify.py` 通过（pytest/compileall/契约漂移）；生产图依赖分层回归通过；无孤立重复实现；集成失败如实报告；文档与实现一致。
- 交付物：项目根目录
- size：L；priority：1；轮次上限：3
