# 项目看板：卡片 20 修补

| 工件 | 类型 | 负责人 | 依赖 | 状态 | 位置 |
|---|---|---|---|---|---|
| architecture-card20 | 架构文档 | 首脑 | - | 已批准 | `docs/architecture-card20.md` |
| contract-source | 契约模块 | 编码 agent | - | 验收通过并已整合 | `agent_hive/contract_spec.py`, `scripts/generate_contracts.py` |
| scheduler-core | 调度模块 | 编码 agent | - | 验收通过并已整合 | `agent_hive/scheduler.py`, `agent_hive/graph.py` |
| integration-core | 集成模块 | 编码 agent | - | 验收通过并已整合 | `agent_hive/integration.py`, `agent_hive/chief.py` |
| regression-tests | 回归测试 | 测试 agent | contract-source, scheduler-core, integration-core | 验收通过并已整合 | `tests/` |
| runtime-integration | 主目录集成 | 首脑 | 上述全部 | 验收通过 | 项目根目录 |

状态机：待派发 → 进行中 → 待验收 → 通过 / 返工(n/3) →（第 3 次返工仍失败则熔断）；熔断/阻塞包不进入 dist

## 派发资格记录

当前未登记外部程序 agent；三个批次 1 工作包派给已登记的 DSH 编码 agent，原因是工作包分别精确命中模块实现能力，且隔离交付可降低首脑交接成本。共享根目录由首脑唯一维护。

## 终验证据

- `uv run python scripts/verify.py`：通过（pytest 59 passed + compileall + contract drift）
- `uv run pytest -q`：59 passed
- `uv run python -m compileall -q agent_hive tests`：通过
- `uv run python scripts/generate_contracts.py --check`：通过（契约版本 1.2.2）
- 真实 LangGraph `Send` + `threading.Barrier` fan-out：通过，两个分支重叠执行且 reducer 不丢包
- SQLite `interrupt()`/`Command(resume=...)` checkpoint：通过
