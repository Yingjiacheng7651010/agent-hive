"""分布式执行引擎 —— 调度器（scheduler）→ 工作节点池（worker pool）→ 共享状态存储。

核心策略：
1. TaskScheduler：任务队列、分配、完成/失败标记，支持 worker pull 模式
2. WorkerNode：工作节点，从调度器领取任务并执行
3. SharedStateStore：共享状态存储抽象（Redis/内存），替代 SQLite checkpointer
4. DistributedGraphAdapter：兼容现有 LangGraph 图，转换为分布式任务
5. 单机降级：Redis 不可用时使用内存后端，零依赖运行
"""
from __future__ import annotations

import abc
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

__all__ = [
    "RunTask",
    "WorkerInfo",
    "TaskResult",
    "TaskScheduler",
    "WorkerNode",
    "SharedStateStore",
    "MemorySharedStateStore",
    "DistributedGraphAdapter",
]

# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class RunTask:
    """一个可调度的工作单元（对应一次 agent 调用）。"""
    task_id: str = ""
    run_id: str = ""
    tenant_id: str = ""
    kind: Literal["chief", "specialist", "review"] = "specialist"
    role: str = ""
    payload: dict = field(default_factory=dict)
    priority: int = 2                    # 1=紧急, 2=普通, 3=低优先级
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    created_at: float = field(default_factory=time.time)
    assigned_worker: str = ""
    timeout_ms: int = 300000
    depends_on: list[str] = field(default_factory=list)  # 依赖的 task_id 列表


@dataclass
class WorkerInfo:
    """工作节点信息。"""
    worker_id: str
    host: str = "localhost"
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


# ---------------------------------------------------------------------------
# SharedStateStore
# ---------------------------------------------------------------------------

class SharedStateStore(abc.ABC):
    """共享状态存储（Redis/内存后端），替代 SQLite checkpointer。"""

    @abc.abstractmethod
    def save_checkpoint(self, run_id: str, state: dict):
        ...

    @abc.abstractmethod
    def load_checkpoint(self, run_id: str) -> dict | None:
        ...

    @abc.abstractmethod
    def list_runs(self, tenant_id: str = "") -> list[str]:
        ...

    @abc.abstractmethod
    def acquire_lock(self, run_id: str, ttl_ms: int = 30000) -> bool:
        ...

    @abc.abstractmethod
    def release_lock(self, run_id: str):
        ...


class MemorySharedStateStore(SharedStateStore):
    """内存共享状态存储（单机调试用，零依赖）。"""

    def __init__(self):
        self._checkpoints: dict[str, dict] = {}
        self._locks: dict[str, float] = {}  # run_id -> expiry timestamp
        self._lock = threading.Lock()

    def save_checkpoint(self, run_id: str, state: dict):
        with self._lock:
            self._checkpoints[run_id] = state

    def load_checkpoint(self, run_id: str) -> dict | None:
        with self._lock:
            return self._checkpoints.get(run_id)

    def list_runs(self, tenant_id: str = "") -> list[str]:
        with self._lock:
            if tenant_id:
                return [r for r in self._checkpoints if r.startswith(tenant_id)]
            return list(self._checkpoints.keys())

    def acquire_lock(self, run_id: str, ttl_ms: int = 30000) -> bool:
        with self._lock:
            now = time.time()
            if run_id in self._locks:
                if self._locks[run_id] > now:
                    return False
                # 锁已过期
            self._locks[run_id] = now + ttl_ms / 1000
            return True

    def release_lock(self, run_id: str):
        with self._lock:
            self._locks.pop(run_id, None)


# ---------------------------------------------------------------------------
# TaskScheduler
# ---------------------------------------------------------------------------

class TaskScheduler:
    """分布式任务调度器。"""

    def __init__(self, state_store: SharedStateStore | None = None):
        self._state_store = state_store or MemorySharedStateStore()
        self._tasks: dict[str, RunTask] = {}
        self._results: dict[str, TaskResult] = {}
        self._workers: dict[str, WorkerInfo] = {}
        self._pending_queue: list[str] = []  # 按优先级排序的 task_id 列表
        self._lock = threading.RLock()

    def submit(self, task: RunTask) -> str:
        """提交任务到队列，返回 task_id。"""
        if not task.task_id:
            task.task_id = f"task_{uuid.uuid4().hex[:12]}"
        task.status = "pending"
        task.created_at = time.time()

        with self._lock:
            self._tasks[task.task_id] = task
            self._pending_queue.append(task.task_id)
            # 按优先级排序
            self._pending_queue.sort(
                key=lambda tid: (self._tasks[tid].priority, self._tasks[tid].created_at)
            )
        return task.task_id

    def cancel(self, task_id: str) -> bool:
        """取消任务。"""
        with self._lock:
            if task_id in self._tasks and self._tasks[task_id].status == "pending":
                self._tasks[task_id].status = "failed"
                self._pending_queue = [t for t in self._pending_queue if t != task_id]
                return True
            return False

    def assign(self, worker_id: str) -> RunTask | None:
        """为工作节点分配一个任务（worker pull 模式）。"""
        with self._lock:
            # 更新 worker 心跳
            if worker_id in self._workers:
                self._workers[worker_id].last_heartbeat = time.time()

            for tid in list(self._pending_queue):
                task = self._tasks.get(tid)
                if task is None:
                    self._pending_queue.remove(tid)
                    continue
                if task.status != "pending":
                    self._pending_queue.remove(tid)
                    continue

                # 检查依赖是否满足
                if task.depends_on:
                    all_deps_met = all(
                    dep in self._results and self._results[dep].success
                    for dep in task.depends_on
                )
                    if not all_deps_met:
                        continue

                # 分配任务
                task.status = "running"
                task.assigned_worker = worker_id
                self._pending_queue.remove(tid)

                if worker_id in self._workers:
                    self._workers[worker_id].status = "busy"
                    self._workers[worker_id].current_tasks.append(tid)

                return task
            return None

    def complete(self, result: TaskResult):
        """标记任务完成。"""
        with self._lock:
            self._results[result.task_id] = result
            if result.task_id in self._tasks:
                self._tasks[result.task_id].status = "completed" if result.success else "failed"

            # 更新 worker 状态
            worker_id = result.worker_id
            if worker_id in self._workers:
                worker = self._workers[worker_id]
                if result.task_id in worker.current_tasks:
                    worker.current_tasks.remove(result.task_id)
                if not worker.current_tasks:
                    worker.status = "idle"

    def fail(self, task_id: str, error: str):
        """标记任务失败。"""
        result = TaskResult(
            task_id=task_id,
            run_id=self._tasks[task_id].run_id if task_id in self._tasks else "",
            worker_id=self._tasks[task_id].assigned_worker if task_id in self._tasks else "",
            success=False,
            error=error,
        )
        self.complete(result)

    def pending_count(self, run_id: str | None = None) -> int:
        """查询待处理任务数。"""
        with self._lock:
            if run_id is None:
                return len(self._pending_queue)
            return sum(
                1 for tid in self._pending_queue
                if self._tasks.get(tid) and self._tasks[tid].run_id == run_id
            )

    def get_task(self, task_id: str) -> RunTask | None:
        with self._lock:
            return self._tasks.get(task_id)

    def get_result(self, task_id: str) -> TaskResult | None:
        with self._lock:
            return self._results.get(task_id)

    def register_worker(self, worker_id: str, max_concurrent: int = 4) -> WorkerInfo:
        with self._lock:
            worker = WorkerInfo(
                worker_id=worker_id,
                status="idle",
                max_concurrent=max_concurrent,
            )
            self._workers[worker_id] = worker
            return worker

    def unregister_worker(self, worker_id: str):
        with self._lock:
            self._workers.pop(worker_id, None)
            # 重新分配该 worker 的任务
            for tid, task in list(self._tasks.items()):
                if task.assigned_worker == worker_id and task.status == "running":
                    task.status = "pending"
                    task.assigned_worker = ""
                    self._pending_queue.append(tid)

    def get_workers(self) -> list[WorkerInfo]:
        with self._lock:
            return list(self._workers.values())

    def get_tasks_by_run(self, run_id: str) -> list[RunTask]:
        with self._lock:
            return [t for t in self._tasks.values() if t.run_id == run_id]

    def check_heartbeats(self, timeout_ms: int = 30000):
        """检查心跳超时的 worker，重新分配其任务。"""
        now = time.time()
        with self._lock:
            for worker_id, worker in list(self._workers.items()):
                elapsed = (now - worker.last_heartbeat) * 1000
                if elapsed > timeout_ms:
                    worker.status = "offline"
                    # 重新分配任务
                    for tid, task in list(self._tasks.items()):
                        if task.assigned_worker == worker_id and task.status == "running":
                            task.status = "pending"
                            task.assigned_worker = ""
                            self._pending_queue.append(tid)

    def state_store(self) -> SharedStateStore:
        return self._state_store


# ---------------------------------------------------------------------------
# WorkerNode
# ---------------------------------------------------------------------------

class WorkerNode:
    """工作节点：从调度器领取任务并执行。"""

    def __init__(
        self,
        worker_id: str,
        scheduler: TaskScheduler,
        execute_fn: Callable[[RunTask], TaskResult] | None = None,
        max_concurrent: int = 4,
    ):
        self._worker_id = worker_id
        self._scheduler = scheduler
        self._execute_fn = execute_fn
        self._max_concurrent = max_concurrent
        self._running = False
        self._threads: list[threading.Thread] = []

    def set_execute_fn(self, fn: Callable[[RunTask], TaskResult]):
        self._execute_fn = fn

    def start(self):
        """启动 worker 循环。"""
        self._scheduler.register_worker(self._worker_id, self._max_concurrent)
        self._running = True
        for _ in range(self._max_concurrent):
            t = threading.Thread(target=self._worker_loop, daemon=True)
            t.start()
            self._threads.append(t)

    def stop(self):
        """优雅停止。"""
        self._running = False

    def heartbeat(self):
        """发送心跳。"""
        self._scheduler.register_worker(self._worker_id, self._max_concurrent)

    def _worker_loop(self):
        while self._running:
            task = None
            try:
                task = self._scheduler.assign(self._worker_id)
                if task is None:
                    time.sleep(0.5)
                    continue

                # 执行任务
                if self._execute_fn:
                    result = self._execute_fn(task)
                else:
                    result = TaskResult(
                        task_id=task.task_id,
                        run_id=task.run_id,
                        worker_id=self._worker_id,
                        success=True,
                        output={"message": "no execute_fn configured"},
                    )

                self._scheduler.complete(result)
            except Exception as e:
                # 任务失败但不崩溃
                error_result = TaskResult(
                    task_id=task.task_id if task else "unknown",
                    run_id=task.run_id if task else "",
                    worker_id=self._worker_id,
                    success=False,
                    error=str(e),
                )
                self._scheduler.complete(error_result)


# ---------------------------------------------------------------------------
# DistributedGraphAdapter
# ---------------------------------------------------------------------------

class DistributedGraphAdapter:
    """将 LangGraph 图适配为分布式任务。"""

    def __init__(self, graph, scheduler: TaskScheduler):
        """
        Args:
            graph: LangGraph StateGraph 实例
            scheduler: 任务调度器
        """
        self._graph = graph
        self._scheduler = scheduler

    async def invoke(self, payload: dict, run_id: str) -> dict:
        """将 graph.invoke() 转换为分布式任务序列。

        1. 将图的每个节点映射为一个 RunTask
        2. 按依赖关系提交到调度器
        3. 等待所有任务完成
        4. 聚合结果
        """
        # 创建根任务（对应整个 run）
        root_task = RunTask(
            run_id=run_id,
            kind="chief",
            role="chief",
            payload=payload,
            priority=1,
        )
        task_id = self._scheduler.submit(root_task)

        # 等待所有任务完成
        deadline = time.time() + root_task.timeout_ms / 1000
        while time.time() < deadline:
            result = self._scheduler.get_result(task_id)
            if result is not None:
                if result.success:
                    return result.output
                raise RuntimeError(f"任务 {task_id} 失败: {result.error}")
            time.sleep(0.5)

        raise TimeoutError(f"任务 {task_id} 执行超时")

    def get_graph(self):
        return self._graph