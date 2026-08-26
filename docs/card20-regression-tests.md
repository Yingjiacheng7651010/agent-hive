# Card 20 regression-tests 交付

本文件记录已迁移并整合到仓库根目录的回归测试；实现与测试均由首脑完成最终验收。

## 运行命令

```bash
uv run python scripts/verify.py
# 或只运行测试：uv run pytest -q
```

当前根目录共 57 个测试；测试不访问网络、不调用真实模型（SQLite checkpoint 测试只使用无模型的最小图）；chief 的模型 seam 通过 `monkeypatch` 替换。

## 公共 seam 与覆盖矩阵

| P0 / 修补接口 | 测试 seam | 主要验证 |
|---|---|---|
| scheduler / paths | `validate_dependency_graph`, `build_execution_layers`, `select_ready_packages`, `classify_blocked_packages`, `safe_run_dir` | 空/重复/悬空/环；同层 ready；下游等待；retry 依赖门；熔断包不重派；路径 id 围栏与阻塞传递 |
| LangGraph fan-out | 真实 `StateGraph` + `Send` + `HiveState` reducer 语义；`continue_to_specialists` | 两 worker 用 `threading.Barrier` 证明重叠执行；两个回传键均保留；只发送 `active_ids`，不提前发送下游 |
| chief review | `chief.review` 与公开状态字段 | 只评审 active wave、此前通过冻结、缺失 verdict 失败、越界/缺失交付物由守卫拒绝且不触发模型 |
| integration | `integrate_packages` + `chief.integrate` | 扁平合并、同内容去重、冲突拒绝、旧 dist 保留、Python 静态编译失败、manifest、显式动态检查记录、部分成功状态、包 id 路径守卫 |
| contract | `render_contracts_md`, `check_contracts_drift`, `prompts.__all__` | 已提交文档逐字节一致；人为漂移能被发现；prompts 对象身份重导出 |
| state restore | `merge_dict` + JSON + SQLite checkpointer | 调度/review/reducer 关键字段无损恢复；`interrupt()`/`Command(resume=...)` 断点状态恢复 |

## 并发测试稳定性

并发证据不用耗时阈值或任意 `sleep`。两个真实 LangGraph `Send` 分支进入同一个 `threading.Barrier(2, timeout=3)`；若运行时把分支串行化，第一个 worker 会超时，测试明确失败。完成后断言 reducer 同时保留两个互异包 id 的结果。

## 已知环境限制

- 测试覆盖的是无模型的最小 checkpoint 图，不启动完整业务图的真实模型/审批流程；完整业务运行仍需有效 API key 和人工审批或 `--yes`。
- 符号链接围栏因 Windows 创建 symlink 常需额外权限，跨环境回归未强制创建真实 symlink；越界、跨包和缺失路径守卫已有覆盖。
- 生产负载下的多进程 SQLite/executor 压力仍需在目标部署环境做容量验证。
