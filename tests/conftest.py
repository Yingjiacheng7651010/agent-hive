"""Shared fixtures for card 20 public-seam regression tests."""
from __future__ import annotations

import sys
from pathlib import Path

# After migration this file is <repo>/tests/conftest.py.  In the isolated
# delivery tree it is <repo>/workspace/card20-regression-tests/tests/conftest.py.
def _find_repo_root() -> Path:
    start = Path(__file__).resolve().parent
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "agent_hive").is_dir():
            return candidate
    raise RuntimeError("could not locate agent-hive repository root")


PROJECT_ROOT = _find_repo_root()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
