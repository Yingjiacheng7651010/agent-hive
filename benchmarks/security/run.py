"""安全验证基准运行器（WP-A3 产物的可复现封装）。

- 以子进程调用 ``scripts/security_benchmark.py``（llm_enabled=False，纯规则引擎通道）；
- 解析其 stdout，落盘 ``benchmarks/security/results.json``（**逐字节确定性**：不含墙钟
  测量值/时间戳——延迟与时间戳落在 ``results.meta.json`` sidecar）；
- 用 ``report.template.md`` 渲染 ``report.md``（占位符缺失即报错，杜绝残留）。

用法：``uv run python benchmarks/security/run.py``
"""
from __future__ import annotations

import datetime
import json
import re
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]  # benchmarks/security/ → 仓库根（HERE 已是文件所在目录）
BENCHMARK_SCRIPT = REPO_ROOT / "scripts" / "security_benchmark.py"
GOLDEN_DIR = REPO_ROOT / "tests" / "golden"

RESULTS = HERE / "results.json"
META = HERE / "results.meta.json"
TEMPLATE = HERE / "report.template.md"
REPORT = HERE / "report.md"

_METRIC_KEYS = {
    "total_samples", "passed", "detection_rate", "false_positive_rate",
    "avg_latency_ms", "p99_latency_ms", "verdict_accuracy",
}
_FAMILY_RE = re.compile(r"^([^:]+):\s*(\d+)/(\d+)$")


def _pkg_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "unknown"


def _parse_stdout(output: str) -> tuple[dict, dict]:
    """解析 security_benchmark 的 stdout → (指标, 家族表)。"""
    metrics: dict = {}
    families: dict = {}
    for line in output.splitlines():
        stripped = line.strip()
        if ":" not in stripped:
            continue
        key, _, raw = stripped.partition(":")
        key, raw = key.strip(), raw.strip()
        if key in _METRIC_KEYS:
            metrics[key] = float(raw) if "." in raw else int(raw)
        else:
            fam = _FAMILY_RE.match(stripped)
            if fam:
                families[fam.group(1)] = [int(fam.group(2)), int(fam.group(3))]
    return metrics, families


def _write_json(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _render(template: Path, values: dict[str, str]) -> str:
    """模板渲染：{{key}} 替换；缺失键或渲染后残留占位符 → 抛错（杜绝占位残留）。"""
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
    env = dict(__import__("os").environ)
    env["PYTHONUTF8"] = "1"  # 子进程 stdout 强制 UTF-8，避免 Windows 代码页差异
    proc = subprocess.run(
        [sys.executable, str(BENCHMARK_SCRIPT)],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, encoding="utf-8",
    )
    if proc.returncode != 0:
        print(proc.stdout, file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        return proc.returncode

    metrics, families = _parse_stdout(proc.stdout)
    missing = _METRIC_KEYS - set(metrics)
    if missing:
        print(f"[FAIL] 基准输出缺少指标：{sorted(missing)}", file=sys.stderr)
        return 1

    # 环境相关字段（墙钟/延迟）只进 meta，不进 results.json（保证逐字节确定性）
    latency = {k: metrics.pop(k) for k in ("avg_latency_ms", "p99_latency_ms")}
    hand_written = len(list(GOLDEN_DIR.glob("*.json")))
    total = metrics["total_samples"]

    results = {
        "benchmark": "security",
        "script": "scripts/security_benchmark.py",
        "corpus": {
            "total_samples": total,
            "hand_written": hand_written,
            "generated": total - hand_written,
            "families": families,
        },
        "metrics": {
            "passed": metrics["passed"],
            "detection_rate": metrics["detection_rate"],
            "false_positive_rate": metrics["false_positive_rate"],
            "verdict_accuracy": metrics["verdict_accuracy"],
        },
        "thresholds": {
            "detection_rate_min": 0.95,
            "false_positive_rate_max": 0.05,
            "verdict_accuracy_min": 0.95,
        },
        "ok": proc.returncode == 0,
        "versions": {
            "hive-security": _pkg_version("hive-security"),
            "hive-cost": _pkg_version("hive-cost"),
            "agent-hive": _pkg_version("agent-hive"),
            "python": sys.version.split()[0],
        },
    }
    _write_json(RESULTS, results)

    meta = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "avg_latency_ms": latency["avg_latency_ms"],
        "p99_latency_ms": latency["p99_latency_ms"],
        "benchmark_exit_code": proc.returncode,
    }
    _write_json(META, meta)

    families_table = "\n".join(
        f"| {name} | {ok}/{total_n} |" for name, (ok, total_n) in sorted(families.items())
    )
    values = {
        "generated_at": meta["generated_at"],
        "script": "scripts/security_benchmark.py",
        "hive_security_version": results["versions"]["hive-security"],
        "hive_cost_version": results["versions"]["hive-cost"],
        "agent_hive_version": results["versions"]["agent-hive"],
        "python_version": results["versions"]["python"],
        "total_samples": str(total),
        "hand_written": str(hand_written),
        "generated": str(total - hand_written),
        "passed": str(metrics["passed"]),
        "detection_rate": f"{metrics['detection_rate']:.4f}",
        "false_positive_rate": f"{metrics['false_positive_rate']:.4f}",
        "verdict_accuracy": f"{metrics['verdict_accuracy']:.4f}",
        "avg_latency_ms": f"{latency['avg_latency_ms']:.4f}",
        "p99_latency_ms": f"{latency['p99_latency_ms']:.4f}",
        "families_table": families_table,
    }
    REPORT.write_text(_render(TEMPLATE, values), encoding="utf-8")

    print(
        f"[OK] security benchmark：{total} 样例，detection_rate="
        f"{metrics['detection_rate']:.4f}，fp_rate={metrics['false_positive_rate']:.4f}，"
        f"verdict_accuracy={metrics['verdict_accuracy']:.4f}"
    )
    print(f"[OK] 落盘 {RESULTS.relative_to(REPO_ROOT)} / {REPORT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
