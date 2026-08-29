"""合成 agent 调用轨迹生成器（确定性，**无 random**）。

- ``TRACE_SEED = 20250617``：固定 seed（仅文档用途），全部取值由**序号算术**派生；
- N=100 任务，每任务 3-20 次模型调用：``calls = 3 + (i * 17) % 18``；
- 模型名按任务序号轮换：任务 i 的第 j 次调用用 ``deepseek-chat``（``(i + j) % 2 == 0``）
  否则 ``deepseek-chat-lite``；
- 角色按任务序号轮换（编码/测试/评审/调研/安全）；
- token 与延迟按序号派生：``input = 100 + (i*13 + j*7) % 900``、
  ``output = 20 + (i*11 + j*5) % 180``、``latency_ms = 50 + (i*7 + j*3) % 450``。

同输入两次调用返回完全相同的轨迹（纯函数）。
"""
from __future__ import annotations

TRACE_SEED = 20250617  # 固定 seed（文档用途；生成不使用 random）
N_TASKS = 100
ROLES = ("编码", "测试", "评审", "调研", "安全")
MODELS = ("deepseek-chat", "deepseek-chat-lite")


def generate_trace(n_tasks: int = N_TASKS) -> list[list[dict]]:
    """生成确定性合成调用轨迹：list[task]，task = list[call]。"""
    trace: list[list[dict]] = []
    for i in range(n_tasks):
        n_calls = 3 + (i * 17) % 18  # 每任务 3-20 次调用
        role = ROLES[i % len(ROLES)]
        calls: list[dict] = []
        for j in range(n_calls):
            calls.append({
                "model": MODELS[(i + j) % 2],
                "role": role,
                "input_tokens": 100 + (i * 13 + j * 7) % 900,
                "output_tokens": 20 + (i * 11 + j * 5) % 180,
                "latency_ms": float(50 + (i * 7 + j * 3) % 450),
            })
        trace.append(calls)
    return trace


def trace_summary(trace: list[list[dict]]) -> dict:
    """轨迹统计（确定性）：总调用数 / 总 token / 每模型调用数。"""
    total_calls = sum(len(task) for task in trace)
    total_tokens = sum(
        c["input_tokens"] + c["output_tokens"]
        for task in trace for c in task
    )
    by_model: dict[str, int] = {}
    for task in trace:
        for c in task:
            by_model[c["model"]] = by_model.get(c["model"], 0) + 1
    return {
        "tasks": len(trace),
        "total_calls": total_calls,
        "total_tokens": total_tokens,
        "by_model": by_model,
    }
