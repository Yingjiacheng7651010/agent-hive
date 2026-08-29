"""Run the repository's deterministic Card 20 verification gates.

This script deliberately uses argv lists and ``shell=False`` so it can also be
used as an explicit integration check. It does not require API keys or invoke a
model.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(label: str, argv: list[str]) -> None:
    print(f"== {label}: {' '.join(argv)}")
    subprocess.run(argv, cwd=ROOT, check=True)


def main() -> int:
    run("pytest", [sys.executable, "-m", "pytest", "-q"])
    run("compileall", [sys.executable, "-m", "compileall", "-q", "agent_hive", "tests"])
    run("contract drift", [sys.executable, "scripts/generate_contracts.py", "--check"])
    run("contract lint", [sys.executable, "scripts/contract_lint.py", "contracts/examples/packages.example.json"])
    run("security golden regression", [sys.executable, "scripts/security_golden.py"])
    print("verification: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
