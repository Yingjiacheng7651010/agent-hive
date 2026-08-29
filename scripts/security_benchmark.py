"""架构安全验证 golden 语料基准（确定性规则引擎通道，无模型）。

用法：
    uv run python scripts/security_benchmark.py

遍历 ``tests/golden/`` 全部 JSON（含 ``generated/`` 子目录，共 ≥115 样例），
以 ``llm_enabled=False`` 跑 ``validate_architecture``（纯规则引擎，无 LLM 通道），
统计并输出：

    total_samples        样例总数
    passed               全部约束（must_hit 全命中 / must_not_hit 零违反 / 干净样例零 finding / verdict 一致）达标的样例数
    detection_rate       must_hit 样例中「全部期望威胁均被检出」的比例
    false_positive_rate  误报样例（干净样例出现 finding，或 must_not_hit 被违反）占比
    avg_latency_ms       单样例 validate_architecture 平均耗时（毫秒）
    p99_latency_ms       单样例耗时 P99（毫秒）
    verdict_accuracy     verdict 与 expect_verdict 一致的比例

退出码：detection_rate ≥ 0.95 且 false_positive_rate ≤ 0.05 且 verdict_accuracy ≥ 0.95 → 0，否则 1。
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_DIR = REPO_ROOT / "tests" / "golden"

sys.path.insert(0, str(REPO_ROOT))

from agent_hive.arch_security import validate_architecture  # noqa: E402
from agent_hive.threat_model import ValidationPolicy, load_threat_catalog  # noqa: E402

DETECTION_THRESHOLD = 0.95
FP_THRESHOLD = 0.05
VERDICT_THRESHOLD = 0.95


def iter_samples():
    """遍历 tests/golden 全部 json（含 generated/），返回 (相对路径, 样例)。"""
    for path in sorted(GOLDEN_DIR.rglob("*.json")):
        sample = json.loads(path.read_text(encoding="utf-8"))
        yield path.relative_to(GOLDEN_DIR), sample


def _family_of(path: Path) -> str:
    """按文件名首段归族（家族名不含下划线；手工样例按文件名本身）。"""
    parts = path.stem.split("_")
    return parts[0]


def main() -> int:
    samples = list(iter_samples())
    if not samples:
        print(f"[FAIL] 未找到 golden 语料：{GOLDEN_DIR}")
        return 1

    catalog = load_threat_catalog()
    policy = ValidationPolicy(llm_enabled=False)

    latencies: list[float] = []
    total_detection = 0
    detected = 0
    fp_samples = 0
    verdict_ok = 0
    passed = 0
    failures: list[str] = []
    family_stats: dict[str, list[int]] = {}  # 族名 -> [passed, total]

    for rel_path, sample in samples:
        family = _family_of(rel_path)
        fam = family_stats.setdefault(family, [0, 0])
        fam[1] += 1

        t0 = time.perf_counter()
        report = validate_architecture(sample["architecture"], catalog, policy, None)
        latencies.append((time.perf_counter() - t0) * 1000.0)

        hit = {f.threat_id for f in report.findings}
        must_hit = set(sample.get("must_hit") or [])
        must_not = set(sample.get("must_not_hit") or [])
        expect_verdict = sample.get("expect_verdict", "fail")
        problems: list[str] = []

        # 检测：must_hit 全部命中
        if must_hit:
            total_detection += 1
            missing = must_hit - hit
            if not missing:
                detected += 1
            else:
                problems.append(f"漏报 {sorted(missing)}")
        # 误报：干净样例（无 must_hit）出现 finding，或 must_not_hit 被违反
        is_fp = False
        if not must_hit and hit:
            is_fp = True
            problems.append(f"零误报样例出现 finding：{sorted(hit)}")
        if must_not & hit:
            is_fp = True
            problems.append(f"误报 {sorted(must_not & hit)}")
        if is_fp:
            fp_samples += 1
        # verdict 一致性
        if report.verdict == expect_verdict:
            verdict_ok += 1
        else:
            problems.append(f"verdict 期望 {expect_verdict!r} 实际 {report.verdict!r}")

        if problems:
            failures.append(f"{rel_path}：{'；'.join(problems)}")
        else:
            passed += 1
            fam[0] += 1

    total = len(samples)
    detection_rate = detected / total_detection if total_detection else 1.0
    fp_rate = fp_samples / total
    verdict_accuracy = verdict_ok / total
    avg_latency_ms = sum(latencies) / len(latencies)
    sorted_lat = sorted(latencies)
    p99_idx = max(0, int(math.ceil(len(sorted_lat) * 0.99)) - 1)
    p99_latency_ms = sorted_lat[p99_idx]

    print(f"total_samples: {total}")
    print(f"passed: {passed}")
    print(f"detection_rate: {detection_rate:.4f}")
    print(f"false_positive_rate: {fp_rate:.4f}")
    print(f"avg_latency_ms: {avg_latency_ms:.4f}")
    print(f"p99_latency_ms: {p99_latency_ms:.4f}")
    print(f"verdict_accuracy: {verdict_accuracy:.4f}")

    print("\n== 按家族 ==")
    for family in sorted(family_stats):
        ok, n = family_stats[family]
        print(f"  {family}: {ok}/{n}")

    if failures:
        print(f"\n[FAIL] {len(failures)} 个样例未达标（仅显示前 10）：")
        for line in failures[:10]:
            print(f"  - {line}")

    ok = (
        detection_rate >= DETECTION_THRESHOLD
        and fp_rate <= FP_THRESHOLD
        and verdict_accuracy >= VERDICT_THRESHOLD
    )
    print(
        f"\n{'[OK]' if ok else '[FAIL]'} benchmark 达标判定："
        f"detection_rate≥{DETECTION_THRESHOLD} / false_positive_rate≤{FP_THRESHOLD} / "
        f"verdict_accuracy≥{VERDICT_THRESHOLD} → {detection_rate:.4f} / {fp_rate:.4f} / {verdict_accuracy:.4f}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
