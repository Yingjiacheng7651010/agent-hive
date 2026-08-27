"""Tests for card-distributed-engine: TaskScheduler, WorkerNode, SharedStateStore."""
from __future__ import annotations

import time

import pytest

from agent_hive.distributed_engine import (
    MemorySharedStateStore,
    RunTask,
    TaskResult,
    TaskScheduler,
    WorkerNode,
)


class TestMemorySharedStateStore:
    """MemorySharedStateStore 测试。"""

    def test_save_and_load_checkpoint(self):
        store = MemorySharedStateStore()
        store.save_checkpoint("run_001", {"state": "test"})
        assert store.load_checkpoint("run_001") == {"state": "test"}

    def test_load_nonexistent(self):
        store = MemorySharedStateStore()
        assert store.load_checkpoint("nonexistent") is None

    def test_list_runs(self):
        store = MemorySharedStateStore()
        store.save_checkpoint("run_a", {})
        store.save_checkpoint("run_b", {})
        assert len(store.list_runs()) == 2

    def test_acquire_and_release_lock(self):
        store = MemorySharedStateStore()
        assert store.acquire_lock("run_001") is True
        assert store.acquire_lock("run_001") is False  # 已锁定
        store.release_lock("run_001")
        assert store.acquire_lock("run_001") is True  # 释放后可重新获取

    def test_lock_expiry(self):
        store = MemorySharedStateStore()
        assert store.acquire_lock("run_001", ttl_ms=100) is True
        time.sleep(0.15)
        assert store.acquire_lock("run_001") is True  # 锁已过期


class TestTaskScheduler:
    """TaskScheduler 调度器测试。"""

    def test_submit_and_get_task(self):
        scheduler = TaskScheduler()
        task = RunTask(run_id="run_001", role="编码")
        task_id = scheduler.submit(task)
        assert task_id.startswith("task_")
        retrieved = scheduler.get_task(task_id)
        assert retrieved is not None
        assert retrieved.status == "pending"

    def test_assign_task(self):
        scheduler = TaskScheduler()
        scheduler.register_worker("worker_1")
        task_id = scheduler.submit(RunTask(run_id="run_001", role="编码"))
        assigned = scheduler.assign("worker_1")
        assert assigned is not None
        assert assigned.task_id == task_id
        assert assigned.status == "running"

    def test_assign_no_pending_tasks(self):
        scheduler = TaskScheduler()
        scheduler.register_worker("worker_1")
        assert scheduler.assign("worker_1") is None

    def test_cancel_pending_task(self):
        scheduler = TaskScheduler()
        task_id = scheduler.submit(RunTask(run_id="run_001"))
        assert scheduler.cancel(task_id) is True
        task = scheduler.get_task(task_id)
        assert task is not None
        assert task.status == "failed"

    def test_cancel_running_task(self):
        scheduler = TaskScheduler()
        scheduler.register_worker("worker_1")
        task_id = scheduler.submit(RunTask(run_id="run_001"))
        scheduler.assign("worker_1")
        assert scheduler.cancel(task_id) is False  # 运行中的任务不可取消

    def test_complete_task(self):
        scheduler = TaskScheduler()
        scheduler.register_worker("worker_1")
        task_id = scheduler.submit(RunTask(run_id="run_001"))
        assigned = scheduler.assign("worker_1")
        assert assigned is not None

        result = TaskResult(
            task_id=task_id, run_id="run_001",
            worker_id="worker_1", success=True,
            output={"result": "ok"},
        )
        scheduler.complete(result)
        task = scheduler.get_task(task_id)
        assert task is not None
        assert task.status == "completed"

    def test_fail_task(self):
        scheduler = TaskScheduler()
        scheduler.register_worker("worker_1")
        task_id = scheduler.submit(RunTask(run_id="run_001"))
        scheduler.assign("worker_1")
        scheduler.fail(task_id, "出错了")
        task = scheduler.get_task(task_id)
        assert task is not None
        assert task.status == "failed"

    def test_pending_count(self):
        scheduler = TaskScheduler()
        scheduler.submit(RunTask(run_id="run_001"))
        scheduler.submit(RunTask(run_id="run_001"))
        scheduler.submit(RunTask(run_id="run_002"))
        assert scheduler.pending_count() == 3
        assert scheduler.pending_count("run_001") == 2
        assert scheduler.pending_count("run_002") == 1

    def test_priority_order(self):
        """高优先级任务先分配。"""
        scheduler = TaskScheduler()
        scheduler.register_worker("worker_1")
        scheduler.submit(RunTask(run_id="run_001", priority=3))  # 低优先级
        scheduler.submit(RunTask(run_id="run_001", priority=1))  # 高优先级
        first = scheduler.assign("worker_1")
        assert first is not None
        assert first.priority == 1

    def test_dependency_ordering(self):
        """依赖未满足的任务不分配。"""
        scheduler = TaskScheduler()
        scheduler.register_worker("worker_1")
        task_a = scheduler.submit(RunTask(run_id="run_001", role="编码"))
        task_b = scheduler.submit(RunTask(run_id="run_001", role="测试", depends_on=[task_a]))

        # 先分配 task_a
        assigned = scheduler.assign("worker_1")
        assert assigned is not None
        assert assigned.task_id == task_a

        # task_b 依赖 task_a，task_a 未完成时不能分配
        assert scheduler.assign("worker_1") is None

        # 完成 task_a
        scheduler.complete(TaskResult(
            task_id=task_a, run_id="run_001",
            worker_id="worker_1", success=True,
        ))

        # 现在可以分配 task_b
        assigned = scheduler.assign("worker_1")
        assert assigned is not None
        assert assigned.task_id == task_b

    def test_worker_offline_reassign(self):
        """worker 离线后任务重新分配。"""
        scheduler = TaskScheduler()
        scheduler.register_worker("worker_1")
        scheduler.register_worker("worker_2")
        task_id = scheduler.submit(RunTask(run_id="run_001"))
        scheduler.assign("worker_1")

        # worker_1 离线
        scheduler.unregister_worker("worker_1")

        # task 应该被重新分配
        assigned = scheduler.assign("worker_2")
        assert assigned is not None
        assert assigned.task_id == task_id

    def test_get_workers(self):
        scheduler = TaskScheduler()
        scheduler.register_worker("worker_1")
        scheduler.register_worker("worker_2")
        workers = scheduler.get_workers()
        assert len(workers) == 2

    def test_get_tasks_by_run(self):
        scheduler = TaskScheduler()
        scheduler.submit(RunTask(run_id="run_001", role="编码"))
        scheduler.submit(RunTask(run_id="run_001", role="测试"))
        scheduler.submit(RunTask(run_id="run_002", role="编码"))
        tasks = scheduler.get_tasks_by_run("run_001")
        assert len(tasks) == 2

    def test_heartbeat_check(self):
        """心跳超时后任务重新分配。"""
        scheduler = TaskScheduler()
        scheduler.register_worker("worker_1")
        scheduler.register_worker("worker_2")
        task_id = scheduler.submit(RunTask(run_id="run_001"))
        scheduler.assign("worker_1")

        # 手动把 worker_1 的心跳设为旧时间
        worker = scheduler._workers["worker_1"]
        worker.last_heartbeat = 0.0

        # 检查心跳超时
        scheduler.check_heartbeats(timeout_ms=1)

        # 任务应该被重新分配
        assigned = scheduler.assign("worker_2")
        assert assigned is not None
        assert assigned.task_id == task_id


class TestWorkerNode:
    """WorkerNode 工作节点测试。"""

    def test_worker_loop_executes_task(self):
        scheduler = TaskScheduler()
        results = []

        def execute_fn(task):
            results.append(task.task_id)
            return TaskResult(
                task_id=task.task_id, run_id=task.run_id,
                worker_id="test_worker", success=True,
                output={"message": "done"},
            )

        worker = WorkerNode("test_worker", scheduler, execute_fn, max_concurrent=1)
        worker.start()
        time.sleep(0.2)

        task_id = scheduler.submit(RunTask(run_id="run_001", role="编码"))
        time.sleep(0.5)

        # 检查任务被执行
        assert task_id in results
        result = scheduler.get_result(task_id)
        assert result is not None
        assert result.success is True

        worker.stop()

    def test_worker_handles_exception(self):
        scheduler = TaskScheduler()

        def execute_fn(task):
            raise ValueError("测试错误")

        worker = WorkerNode("test_worker", scheduler, execute_fn, max_concurrent=1)
        worker.start()
        time.sleep(0.2)

        task_id = scheduler.submit(RunTask(run_id="run_001"))
        time.sleep(0.5)

        # 任务失败但 worker 不崩溃
        result = scheduler.get_result(task_id)
        assert result is not None
        assert result.success is False

        worker.stop()

    def test_worker_heartbeat(self):
        scheduler = TaskScheduler()
        worker = WorkerNode("hb_worker", scheduler, max_concurrent=1)
        worker.heartbeat()
        workers = scheduler.get_workers()
        assert len(workers) == 1
        assert workers[0].worker_id == "hb_worker"

    def test_set_execute_fn(self):
        scheduler = TaskScheduler()
        worker = WorkerNode("test_worker", scheduler, max_concurrent=1)
        worker.set_execute_fn(lambda task: TaskResult(
            task_id=task.task_id, run_id=task.run_id,
            worker_id="test_worker", success=True,
        ))
        assert worker._execute_fn is not None