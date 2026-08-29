"""成本预算基准运行器：三档预算跑 CostGate，落盘确定性 results.json。

- 轨迹：``benchmarks/cost/trace_generator.py``（seed 固定、序号派生、无 random）；
- 三档预算：宽松（无上限）/ 中等（总 token 上限 = 轨迹总量 70%）/ 严格（50%），warn_ratio=0.8；
- 每档统计：完成率（被 block 前完成的调用占比）、任务成本均值、任务成本方差
  （``statistics.pvariance``，按任务聚合）、降级次数、block 次数、告警数；
- 全部统计来自确定性规则计算（与墙钟无关）→ ``results.json`` 两次运行逐字节一致；
  时间戳/Python 版本落在 ``results.meta.json`` sidecar；
- 用 ``report.template.md`` 渲染 ``report.md``（占位符缺失即报错，杜绝残留）。

用法：``uv run python benchmarks/cost/run.py``
"""
from __future__ import annotations

import datetime
import json
import os
import re
import statistics
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import trace_generator  # 脚本目录在 sys.path[0]（uv run 直接执行时）

from hive_cost.budget import CostBudget
from hive_cost.gate import CostGate

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]  # benchmarks/cost/ → 仓库根（HERE 已是文件所在目录）

RESULTS = HERE / "results.json"
META = HERE / "results.meta.json"
TEMPLATE = HERE / "report.template.md"
REPORT = HERE / "report.md"

WARN_RATIO = 0.8
MEDIUM_RATIO = 0.7
STRICT_RATIO = 0.5


def _pkg_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "unknown"


def _simulate(trace, budget: CostBudget) -> dict:
    """按轨迹顺序跑 CostGate；任务在首次 block 后停止（剩余调用不计入）。"""
    gate = CostGate(budget=budget)
    executed = 0
    downgrades = 0
    blocks = 0
    task_costs: list[float] = []
    for task in trace:
        task_cost = 0.0
        for call in task:
            decision = gate.check_before_call(call["model"], call["role"])
            if decision.action == "block":
                blocks += 1
                break  # 任务终止：剩余调用不执行
            if decision.action == "downgrade":
                downgrades += 1
                model = decision.fallback_model or call["model"]
            else:
                model = call["model"]
            before = gate.snapshot().estimated_cost_usd
            gate.record_after_call(model, call["role"], call["input_tokens"],
                                   call["output_tokens"], call["latency_ms"])
            task_cost += gate.snapshot().estimated_cost_usd - before
            executed += 1
        task_costs.append(task_cost)
    total_calls = sum(len(task) for task in trace)
    cost_mean = statistics.fmean(task_costs) if task_costs else 0.0
    cost_variance = statistics.pvariance(task_costs) if len(task_costs) > 1 else 0.0
    return {
        "completion_rate": executed / total_calls,
        "cost_mean_usd": cost_mean,
        "cost_variance_usd": cost_variance,
        "downgrade_count": downgrades,
        "block_count": blocks,
        "alert_count": len(gate.alerts()),
    }


def _write_json(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _render(template: Path, values: dict[str, str]) -> str:
    text = template.read_text(encoding="utf-8")

    def _repl(match: re.Match) -> str:
        key = match.group(1)
        if key not in values:
            raise KeyError(f"模板占位符 {{ {key} }} 缺少对应值")
        return values[key]

    rendered = re.sub(r"\{\{(\w+)\}\}", _repl, text)
    leftovers = re.findall(r"\{\{(\w+)\}\}", rendered)
    if leftovers:
        raise RuntimeError(f"渲染后仍存在未替换占位符：{sorted(set(leftovers))}")
    return rendered


def main() -> int:
    trace = trace_generator.generate_trace()
    summary = trace_generator.trace_summary(trace)
    total_tokens = summary["total_tokens"]

    tiers = {
        "loose": CostBudget(),  # 无上限
        "medium": CostBudget(max_tokens=int(total_tokens * MEDIUM_RATIO), warn_ratio=WARN_RATIO),
        "strict": CostBudget(max_tokens=int(total_tokens * STRICT_RATIO), warn_ratio=WARN_RATIO),
    }
    stats = {name: _simulate(trace, budget) for name, budget in tiers.items()}

    results = {
        "benchmark": "cost",
        "trace": {
            "seed": trace_generator.TRACE_SEED,
            "tasks": summary["tasks"],
            "total_calls": summary["total_calls"],
            "total_tokens": total_tokens,
            "by_model": summary["by_model"],
        },
        "tiers": {
            "loose": {
                "budget": "unlimited",
                "max_tokens": 0,
                "ratio_of_total": 1.0,
                **stats["loose"],
            },
            "medium": {
                "budget": f"max_tokens={int(total_tokens * MEDIUM_RATIO)} ({MEDIUM_RATIO:.0%} of total)",
                "max_tokens": int(total_tokens * MEDIUM_RATIO),
                "ratio_of_total": MEDIUM_RATIO,
                **stats["medium"],
            },
            "strict": {
                "budget": f"max_tokens={int(total_tokens * STRICT_RATIO)} ({STRICT_RATIO:.0%} of total)",
                "max_tokens": int(total_tokens * STRICT_RATIO),
                "ratio_of_total": STRICT_RATIO,
                **stats["strict"],
            },
        },
        "versions": {
            "hive-cost": _pkg_version("hive-cost"),
            "hive-security": _pkg_version("hive-security"),
            "python": sys.version.split()[0],
        },
    }
    _write_json(RESULTS, results)

    meta = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "warn_ratio": WARN_RATIO,
    }
    _write_json(META, meta)

    loose, strict = stats["loose"], stats["strict"]
    var_drop = (
        (loose["cost_variance_usd"] - strict["cost_variance_usd"]) / loose["cost_variance_usd"] * 100
        if loose["cost_variance_usd"] else 0.0
    )

    def _pct(rate: float) -> str:
        return f"{rate * 100:.1f}"

    values = {
        "generated_at": meta["generated_at"],
        "trace_tasks": str(summary["tasks"]),
        "total_calls": str(summary["total_calls"]),
        "total_tokens": str(total_tokens),
        "trace_seed": str(trace_generator.TRACE_SEED),
        "hive_cost_version": results["versions"]["hive-cost"],
        "python_version": results["versions"]["python"],
        **{f"{name}_completion_rate": _pct(s["completion_rate"]) for name, s in stats.items()},
        **{f"{name}_cost_mean": f"{s['cost_mean_usd']:.6f}" for name, s in stats.items()},
        **{f"{name}_cost_variance": f"{s['cost_variance_usd']:.8f}" for name, s in stats.items()},
        **{f"{name}_downgrade_count": str(s["downgrade_count"]) for name, s in stats.items()},
        **{f"{name}_block_count": str(s["block_count"]) for name, s in stats.items()},
        **{f"{name}_alert_count": str(s["alert_count"]) for name, s in stats.items()},
        "var_drop_pct": f"{var_drop:.1f}",
        "completion_loose_pct": _pct(loose["completion_rate"]),
        "completion_strict_pct": _pct(strict["completion_rate"]),
    }
    REPORT.write_text(_render(TEMPLATE, values), encoding="utf-8")

    print(
        f"[OK] cost benchmark：{summary['tasks']} 任务 / {summary['total_calls']} 次调用 / "
        f"{total_tokens} tokens"
    )
    for name in ("loose", "medium", "strict"):
        s = stats[name]
        print(
            f"  - {name:6s}: 完成率 {s['completion_rate']:.1%}，成本均值 ${s['cost_mean_usd']:.6f}，"
            f"方差 {s['cost_variance_usd']:.8f}，降级 {s['downgrade_count']}，block {s['block_count']}，"
            f"告警 {s['alert_count']}"
        )
    print(f"[OK] 落盘 {RESULTS.relative_to(REPO_ROOT)} / {REPORT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
