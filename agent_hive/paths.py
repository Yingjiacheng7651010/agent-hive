"""安全的运行目录与工作包路径策略。

这是一个纯标准库深模块：调用方只需提供 run/package id，复杂的路径归一化、
路径段校验和 workspace 围栏集中在这里，避免 chief、specialist、集成器各自
实现一套容易漂移的规则。
"""
from __future__ import annotations

from pathlib import Path

__all__ = [
    "validate_run_id",
    "validate_package_id",
    "safe_run_dir",
    "safe_package_dir",
]

_MAX_SEGMENT_LENGTH = 128
_FORBIDDEN_SEGMENT_CHARS = ("/", "\\", ":", "\x00")


def _validate_segment(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > _MAX_SEGMENT_LENGTH:
        raise ValueError(f"{label} 非法：必须是 1-{_MAX_SEGMENT_LENGTH} 个字符的字符串")
    if value != value.strip() or value in {".", ".."}:
        raise ValueError(f"{label} 非法：不能是空白包围或路径特殊段")
    if any(char in value for char in _FORBIDDEN_SEGMENT_CHARS):
        raise ValueError(f"{label} 含非法路径字符：{value!r}")
    return value


def validate_run_id(run_id: object) -> str:
    """校验并返回可作为 runs 子目录名的 run id。"""
    return _validate_segment(run_id, "run_id")


def validate_package_id(package_id: object) -> str:
    """校验并返回可作为 workspace 子目录名的 package id。"""
    return _validate_segment(package_id, "工作包 id")


def _is_within(child: Path, root: Path) -> bool:
    try:
        child.relative_to(root)
        return True
    except ValueError:
        return False


def safe_run_dir(run_id: object, root: str | Path | None = None) -> Path:
    """返回围栏内的绝对运行目录，不创建目录。

    Args:
        run_id: 运行 id，需通过 validate_run_id 校验。
        root: 运行目录的根路径。为 None 时使用默认值
              ``<agent_hive 包目录>/runs``（自动基于当前文件位置确定，不依赖 CWD）。
    """
    safe_id = validate_run_id(run_id)
    if root is None:
        # 基于当前文件位置确定项目根，不依赖 CWD
        root = Path(__file__).resolve().parent.parent / "agent_hive" / "runs"
    root_path = Path(root).resolve()
    candidate = (root_path / safe_id).resolve()
    if not _is_within(candidate, root_path) or candidate == root_path:
        raise ValueError(f"run_id 导致运行目录越界：{run_id!r}")
    return candidate


def safe_package_dir(run_dir: str | Path, package_id: object) -> Path:
    """返回 ``run_dir/workspace/<package_id>`` 围栏内的绝对目录。"""
    safe_id = validate_package_id(package_id)
    run_root = Path(run_dir).resolve()
    workspace_lexical = run_root / "workspace"
    workspace = workspace_lexical.resolve()
    # A symlinked workspace would make a seemingly local package point outside
    # the run; reject it rather than silently redefining the trust root.
    if workspace != workspace_lexical or not _is_within(workspace, run_root):
        raise ValueError("workspace 路径不是运行目录内的物理目录")
    candidate = (workspace / safe_id).resolve()
    if not _is_within(candidate, workspace) or candidate == workspace:
        raise ValueError(f"工作包 id 导致工作区越界：{package_id!r}")
    return candidate
