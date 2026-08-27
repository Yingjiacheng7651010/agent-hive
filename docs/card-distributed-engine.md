# 工作卡片：card-distributed-engine —— 分布式执行引擎

> 优先级：P2 | 类型：架构 | 依赖：card-cost-control, card-model-resilience（建议先完成）
> 负责人：系统架构师 / 基础设施 | 轮次上限：3

---

## 1. 问题陈述

当前架构是单进程 LangGraph 执行：
- 所有 agent 在同一个进程里跑，无法利用多机资源
- SQLite checkpointer 不支持并发读写，多 run 同时执行会崩
- 没有连接池、没有请求合并、没有缓存
- 单点故障：一个 agent 的 OOM 会拖垮整个进程

## 2. 目标

将单进程执行引擎改造为分布式架构：调度器（scheduler）→ 工作节点池（worker pool）→ 共享状态存储（shared state store）。支持多 run 并发执行、水平扩展、故障隔离。

## 3. 接口契约

### 3.1 核心数据结构

```python
# agent_hive/distributed_engine.py

@dataclass
class RunTask:
    """一个可调度的工作单元（对应一次 agent 调用）。"""
    task_id: str
    run_id: str
    tenant_id: str = ""
    kind: Literal["chief", "specialist", "review"] = "specialist"
    role: str = ""
    payload: dict = field(default_factory=dict)
    priority: int = 2                    # 1=紧急, 2=普通, 3=低优先级
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    created_at: float = field(default_factory=time.time)
    assigned_worker: str = ""
    timeout_ms: int = 300000

@dataclass
class WorkerInfo:
    """工作节点信息。"""
    worker_id: str
    host: str
    status: Literal["idle", "busy", "offline"] = "idle"
    current_tasks: list[str] = field(default_factory=list)
    max_concurrent: int = 4
    started_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)

@dataclass
class TaskResult:
    """任务执行结果。"""
    task_id: str
    run_id: str
    worker_id: str
    success: bool
    output: dict = field(default_factory=dict)
    error: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0
    tokens_used: int = 0
```

### 3.2 核心接口

```python
class TaskScheduler:
    """分布式任务调度器。"""

    def submit(self, task: RunTask) -> str:
        """提交任务到队列，返回 task_id。"""

    def cancel(self, task_id: str) -> bool:
        """取消任务。"""

    def assign(self, worker_id: str) -> RunTask | None:
        """为工作节点分配一个任务（worker pull 模式）。"""

    def complete(self, result: TaskResult):
        """标记任务完成。"""

    def fail(self, task_id: str, error: str):
        """标记任务失败。"""

    def pending_count(self, run_id: str | None = None) -> int:
        """查询待处理任务数。"""


class WorkerNode:
    """工作节点：从调度器领取任务并执行。"""

    def __init__(self, worker_id: str, scheduler: TaskScheduler):
        ...

    async def start(self):
        """启动 worker 循环：领取任务 → 执行 → 报告结果。"""

    async def stop(self):
        """优雅停止。"""

    async def heartbeat(self):
        """发送心跳。"""


class SharedStateStore:
    """共享状态存储（Redis/etcd 后端），替代 SQLite checkpointer。"""

    @abstractmethod
    def save_checkpoint(self, run_id: str, state: dict): ...
    @abstractmethod
    def load_checkpoint(self, run_id: str) -> dict | None: ...
    @abstractmethod
    def list_runs(self, tenant_id: str = "") -> list[str]: ...
    @abstractmethod
    def acquire_lock(self, run_id: str, ttl_ms: int = 30000) -> bool: ...
    @abstractmethod
    def release_lock(self, run_id: str): ...
```

## 4. 实现方案

### 4.1 架构图

```
┌─────────────────────────────────────────────────────────┐
│                    Task Scheduler                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  Queue Store  │  │  State Store │  │  Lock Store   │   │
│  │  (Redis/AMQP) │  │  (Redis)     │  │  (Redis)      │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└──────────────────────┬──────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
   ┌──────────┐  ┌──────────┐  ┌──────────┐
   │ Worker 1 │  │ Worker 2 │  │ Worker 3 │
   │ (Python) │  │ (Python) │  │ (Python) │
   └──────────┘  └──────────┘  └──────────┘
```

### 4.2 任务分配流程

```
1. 用户提交 run → 首脑节点分解为多个 RunTask
2. 每个 RunTask 提交到调度器队列
3. Worker 从调度器领取任务（pull 模式，避免调度器单点瓶颈）
4. Worker 执行任务（调用 LLM、工具）
5. 任务完成后，结果写回 SharedStateStore
6. 调度器检测到依赖满足，调度下一批任务
7. 所有任务完成 → run 结束
```

### 4.3 与现有架构的兼容

```python
# 兼容层：让现有 LangGraph 图在分布式模式下也能工作
class DistributedGraphAdapter:
    """将 LangGraph 图适配为分布式任务。"""

    def __init__(self, graph, scheduler: TaskScheduler):
        ...

    async def invoke(self, payload: dict, run_id: str) -> dict:
        """将 graph.invoke() 转换为分布式任务序列。"""
        # 1. 将图的每个节点映射为一个 RunTask
        # 2. 按依赖关系提交到调度器
        # 3. 等待所有任务完成
        # 4. 聚合结果
```

## 5. 交付物清单

| 工件 | 位置 | 说明 |
|------|------|------|
| 任务调度器 | `agent_hive/distributed_engine.py` | TaskScheduler + RunTask + TaskResult |
| 工作节点 | 同上 | WorkerNode + 执行循环 + 心跳 |
| 共享状态存储（Redis） | 同上 | SharedStateStore 的 Redis 实现 |
| 共享状态存储（内存） | 同上 | SharedStateStore 的内存实现（单机调试用） |
| 兼容适配器 | 同上 | DistributedGraphAdapter 兼容现有 LangGraph 图 |
| 单元测试 | `tests/test_distributed_engine.py` | 覆盖调度/执行/状态同步 |
| 集成测试 | `tests/test_distributed_engine_integration.py` | 多 worker 并行执行验证 |
| Docker Compose | `docker-compose.yml` | Redis + 多个 worker 的本地部署配置 |
| 部署文档 | `docs/deployment-guide.md` | 分布式部署的配置与运维指南 |

## 6. 验收标准

- [ ] 调度器可提交任务、分配任务、标记完成/失败
- [ ] Worker 可领取任务、执行、报告结果
- [ ] 多个 Worker 可并行处理不同 run 的任务
- [ ] 一个 Worker 崩溃不影响其他 Worker（任务重新分配）
- [ ] 共享状态存储支持并发读写，不丢失数据
- [ ] 同一 run 的任务按依赖顺序执行（依赖未满足的任务不分配）
- [ ] 兼容现有 LangGraph 图（DistributedGraphAdapter）
- [ ] Redis 后端可用时使用分布式模式，不可用时降级为单机模式（向后兼容）
- [ ] Worker 心跳超时（>30s 无心跳）后，任务自动重新分配

## 7. 联动关系

| 联动卡片 | 关系 | 说明 |
|---------|------|------|
| card-cost-control | 依赖 | 成本控制器需支持跨节点汇总 |
| card-model-resilience | 依赖 | 熔断器状态需跨节点共享（Redis 存储） |
| card-multi-tenancy | 配合 | 租户配额需跨节点一致（Redis 计数器） |
| card-streaming | 配合 | 流式事件需跨节点路由到正确的会话 |
| card-async-hitl | 配合 | 审批队列需跨节点共享 |
| card-tool-registry | 配合 | 工具注册表可集中注册，各 Worker 节点缓存 |

## 8. 实现效果

**改造前**：单进程，同一时间只能跑一个 run。一个 agent 的 OOM 拖垮整个进程。不支持水平扩展。

**改造后**：支持多 run 并发执行，可水平扩展 Worker 节点。一个 Worker 崩溃不影响其他 Worker。Redis 后端支持共享状态，Worker 可以部署在不同机器上。单机调试时使用内存后端，零依赖运行。