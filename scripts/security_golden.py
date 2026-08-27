"""架构安全验证 golden 回归（card-ai-arch-security 批次 3）。

用法：
    uv run python scripts/security_golden.py

语料：tests/golden/*.json，每个文件形如：
{
    "name": "样例名",
    "architecture": { ...结构化 architecture_object... },
    "expect_verdict": "fail",          # pass / pass_with_warnings / fail
    "must_hit": ["T-HALL-1"],          # 必须出现的 threat_id（至少一条）
    "must_not_hit": []                 # 不得出现的 threat_id
}

纯规则引擎（llm_enabled=False）跑，无模型、无网络、确定性；防止提示词/规则改动
引入漏报（must_hit 缺失）或误报（must_not_hit 出现 / 干净样例零 finding）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_DIR = REPO_ROOT / "tests" / "golden"

sys.path.insert(0, str(REPO_ROOT))

from agent_hive.arch_security import validate_architecture  # noqa: E402
from agent_hive.threat_model import ValidationPolicy, load_threat_catalog  # noqa: E402


def main() -> int:
    samples = sorted(GOLDEN_DIR.glob("*.json"))
    if not samples:
        print(f"[FAIL] 未找到 golden 语料：{GOLDEN_DIR}")
        return 1

    catalog = load_threat_catalog()
    policy = ValidationPolicy(llm_enabled=False)
    failures: list[str] = []

    for sample_path in samples:
        sample = json.loads(sample_path.read_text(encoding="utf-8"))
        name = sample.get("name", sample_path.stem)
        report = validate_architecture(sample["architecture"], catalog, policy, None)
        hit = {f.threat_id for f in report.findings}

        must_hit = set(sample.get("must_hit") or [])
        must_not = set(sample.get("must_not_hit") or [])
        missing = must_hit - hit
        unexpected = must_not & hit
        verdict_ok = report.verdict == sample.get("expect_verdict", "fail")

        problems = []
        if missing:
            problems.append(f"漏报（期望命中未检出）：{sorted(missing)}")
        if unexpected:
            problems.append(f"误报（不应命中）：{sorted(unexpected)}")
        if not verdict_ok:
            problems.append(f"verdict 期望 {sample.get('expect_verdict')!r} 实际 {report.verdict!r}")
        if not must_hit and not must_not and not verdict_ok:
            problems.append("干净样例出现 finding（零误报约束）")

        if problems:
            failures.append(f"{name}：{'；'.join(problems)}")
        else:
            print(f"[OK] {name}：verdict={report.verdict}，findings={len(report.findings)}")

    if failures:
        print("\n[FAIL] golden 回归未通过：")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"\n[OK] golden 回归通过：{len(samples)} 个样例全部符合预期")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
