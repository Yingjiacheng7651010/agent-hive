"""integration —— 整体集成深模块（integration-core 工作包）。

把多个通过验收的工作包交付物合并成统一 dist 交付树，并拒绝静默冲突 / 缺失 / 损坏。

设计目标（深模块）：
- 小接口：对外只暴露 ``integrate_packages``、``normalize_artifact_path``、
  ``run_dynamic_checks`` 与结构化数据类 ``IntegrationResult`` / ``Conflict`` /
  ``CheckResult`` / ``IntegratedFile``。
- 安全：所有交付物路径必须落在 ``run_dir/workspace/<package_id>`` 内；
  拒绝绝对路径越界、``..``、符号链接与前缀绕过；合并只从物理目录树读取，
  绝不按不可信的报告路径做 IO。
- 可观察：返回结构化结果，并写 ``manifest.json``（包/文件/冲突/检查/状态）。
- 可测试：纯标准库、无模型/网络调用、默认零副作用（只做 py 静态编译 + 文件结构检查）。
- 原子性：先写 staging 目录，校验全过后再原子替换 dist；失败不污染已有 dist。

本模块不含相对导入、不含 langchain 依赖，可独立作为 ``agent_hive.integration``
或单文件 ``integration`` 导入（便于离线单测）。
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

try:  # Keep the module importable as a standalone file for offline tests.
    from .paths import safe_package_dir, validate_package_id
except ImportError:  # pragma: no cover - only used by copied standalone delivery trees.
    def validate_package_id(package_id: object) -> str:
        if not isinstance(package_id, str) or not package_id or len(package_id) > 128:
            raise ValueError("工作包 id 非法")
        if package_id != package_id.strip() or package_id in {".", ".."} \
                or any(char in package_id for char in ("/", "\\", ":", "\x00")):
            raise ValueError("工作包 id 含非法路径字符")
        return package_id

    def safe_package_dir(run_dir: str | Path, package_id: object) -> Path:
        safe_id = validate_package_id(package_id)
        run_root = Path(run_dir).resolve()
        workspace_lexical = run_root / "workspace"
        workspace = workspace_lexical.resolve()
        if workspace != workspace_lexical:
            raise ValueError("workspace 路径不是运行目录内的物理目录")
        candidate = (workspace / safe_id).resolve()
        try:
            candidate.relative_to(workspace)
        except ValueError as exc:
            raise ValueError("工作包 id 导致工作区越界") from exc
        return candidate


__all__ = [
    "IntegrationResult",
    "Conflict",
    "CheckResult",
    "IntegratedFile",
    "STATUS_SUCCESS",
    "STATUS_PARTIAL",
    "STATUS_CONFLICT",
    "STATUS_VALIDATION_FAILED",
    "STATUS_NO_PACKAGES",
    "normalize_artifact_path",
    "integrate_packages",
    "run_dynamic_checks",
]

# ---------- 状态常量 ----------

STATUS_SUCCESS = "success"
STATUS_PARTIAL = "partial"
STATUS_CONFLICT = "conflict"
STATUS_VALIDATION_FAILED = "validation_failed"
STATUS_NO_PACKAGES = "no_packages"

# 保留名：合并到 dist 根后会与 manifest.json 冲突，禁止作为交付物
RESERVED_RELPATHS = {"manifest.json"}

# 跳过目录（构建缓存 / VCS / 虚拟环境）；与旧 integrate() 的 ignore 语义对齐并略增
_SKIP_DIRS = {"__pycache__", ".git", ".pytest_cache", ".venv", ".mypy_cache", ".tox"}
_SKIP_SUFFIXES = (".pyc", ".pyo")

# 动态检查子进程环境需剔除的敏感变量（与 specialists._safe_env 对齐，本地复制避免依赖）
_SENSITIVE_MARKERS = ("KEY", "TOKEN", "SECRET", "PASS", "CREDENTIAL")
_MIN_DYNAMIC_TIMEOUT = 1
_MAX_DYNAMIC_TIMEOUT = 3600


def _normalize_timeout(value: object) -> int:
    try:
        timeout = int(value)
    except (TypeError, ValueError):
        timeout = 120
    return max(_MIN_DYNAMIC_TIMEOUT, min(timeout, _MAX_DYNAMIC_TIMEOUT))


# ---------- 结构化结果 ----------

@dataclass
class Conflict:
    """同一相对路径被多个包以不同内容占据（禁止覆盖，整次集成失败）。"""

    rel_path: str
    packages: list[str]
    digests: dict[str, str]  # package_id -> sha256


@dataclass
class CheckResult:
    """一次检查（静态编译 / 文件结构 / 动态检查）的结论。"""

    name: str
    status: str  # "passed" | "failed"
    package: str = ""
    detail: str = ""


@dataclass
class IntegratedFile:
    """合并进 dist 的一个文件（同内容多包可去重）。"""

    rel_path: str
    packages: list[str]
    digest: str
    size: int
    deduplicated: bool = False


@dataclass
class IntegrationResult:
    """集成结果：结构化、可序列化、可审计。"""

    status: str = STATUS_NO_PACKAGES
    merged_packages: list[str] = field(default_factory=list)
    missing_packages: list[str] = field(default_factory=list)
    unresolved_packages: list[str] = field(default_factory=list)
    files: list[IntegratedFile] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)
    checks: list[CheckResult] = field(default_factory=list)
    manifest_path: str | None = None
    dist_dir: str | None = None
    summary: str = ""

    @property
    def ok(self) -> bool:
        return self.status == STATUS_SUCCESS

    def to_dict(self) -> dict:
        d = asdict(self)
        d["ok"] = self.ok
        return d


# ---------- 路径围栏 ----------

def _is_within(child: Path, root: Path) -> bool:
    try:
        child.relative_to(root)
        return True
    except ValueError:
        return False


def _package_id_error(package_id: object) -> str | None:
    """Package ids become directory names; reject path-like values first."""
    try:
        validate_package_id(package_id)
    except ValueError as exc:
        return f"工作包 id 非法：{package_id!r}（{exc}）"
    return None


def normalize_artifact_path(raw, run_dir, package_id):
    """校验并归一化一个（不可信的）交付物路径，只校验、绝不 IO。

    接受三种常见写法：
      - 绝对路径（必须落在 ``run_dir/workspace/<package_id>`` 内）
      - run_dir 相对路径 ``workspace/<package_id>/<rel>``
      - 包内相对路径 ``<rel>``（相对 ``workspace/<package_id>``）

    返回 ``(resolved, rel_posix, error)``；失败时前两者为 ``None``，``error`` 为可读原因。
    """
    if raw is None or not str(raw).strip():
        return None, None, "路径为空"
    raw = str(raw).strip()
    try:
        package_root = safe_package_dir(run_dir, package_id)
    except ValueError as exc:
        return None, None, f"工作包路径非法：{exc}"

    # 跨包引用守卫：workspace/<其他id>/... 一律拒绝
    pparts = Path(raw).parts
    if len(pparts) >= 2 and pparts[0].lower() == "workspace" and pparts[1] != str(package_id):
        return None, None, (
            f"跨包引用被拒绝：{raw!r}（只接受 workspace/{package_id}/... 或包内相对路径）"
        )

    try:
        p = Path(raw)
        if p.is_absolute():
            resolved = p.resolve()
        else:
            candidate = (Path(run_dir) / p).resolve()
            if _is_within(candidate, package_root):
                resolved = candidate
            else:
                resolved = (package_root / p).resolve()
    except (OSError, ValueError) as e:
        return None, None, f"路径非法：{type(e).__name__}: {e}"

    if not _is_within(resolved, package_root):
        return None, None, f"路径越界（不在 workspace/{package_id}/ 内）：{raw!r}"

    rel = resolved.relative_to(package_root).as_posix()
    return resolved, rel, None


# ---------- 校验辅助 ----------

def hash_file(path: Path) -> str:
    """分块读取文件的 sha256 十六进制摘要。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def check_python_compile(path: Path, rel: str) -> str | None:
    """无副作用静态编译检查：只把源码 parse 成内存字节码，不执行、不落盘 .pyc。

    返回错误字符串或 ``None``（通过）。
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        compile(text, rel, "exec")
        return None
    except (SyntaxError, ValueError, OSError) as e:
        return f"{type(e).__name__}: {e}"


def _safe_env(extra: dict | None = None) -> dict:
    """剔除敏感环境变量后再交给子进程（动态检查用）。"""
    env = dict(os.environ)
    if extra:
        env.update(extra)
    for k in list(env):
        if any(m in k.upper() for m in _SENSITIVE_MARKERS):
            env.pop(k, None)
    return env


def _skip_rel(rel: str) -> bool:
    parts = rel.split("/")
    if any(p in _SKIP_DIRS for p in parts):
        return True
    return rel.endswith(_SKIP_SUFFIXES)


# ---------- 动态检查（默认关闭） ----------

def run_dynamic_checks(dist_dir, checks, *, timeout=120, env=None) -> list[CheckResult]:
    """可选动态检查（pytest/build 等），默认不被调用；显式开启后才执行。

    ``checks`` 每一项：``{"name": str, "argv": [str, ...]}``，可选 ``"cwd"``（相对 dist）。

    安全：``shell=False``、argv 列表参数、subprocess 超时、敏感环境裁剪。
    返回 ``CheckResult`` 列表，由调用方决定失败语义。
    """
    results: list[CheckResult] = []
    try:
        dist = Path(dist_dir).resolve()
    except (TypeError, ValueError, OSError) as exc:
        return [CheckResult(
            name="dynamic", status="failed",
            detail=f"dist_dir 非法：{type(exc).__name__}: {exc}",
        )]
    timeout = _normalize_timeout(timeout)
    for index, c in enumerate(checks or []):
        if not isinstance(c, dict):
            results.append(CheckResult(
                name=f"dynamic:{index}", status="failed", detail="检查定义必须是对象",
            ))
            continue
        name = c.get("name", "dynamic")
        try:
            argv = list(c.get("argv") or [])
        except TypeError:
            argv = []
        cwd_rel = c.get("cwd") or "."
        try:
            cwd = (Path(dist_dir) / cwd_rel).resolve()
        except (TypeError, ValueError, OSError) as exc:
            results.append(CheckResult(
                name=name, status="failed", detail=f"cwd 非法：{type(exc).__name__}: {exc}",
            ))
            continue
        if not argv:
            results.append(CheckResult(name=name, status="failed", detail="argv 为空"))
            continue
        if not _is_within(cwd, dist):
            results.append(CheckResult(name=name, status="failed", detail=f"cwd 越界: {cwd}"))
            continue
        try:
            proc = subprocess.run(
                argv, shell=False, cwd=str(cwd), capture_output=True, text=True,
                timeout=timeout, encoding="utf-8", errors="replace", env=_safe_env(env),
            )
            out = (proc.stdout or "").strip()
            err = (proc.stderr or "").strip()
            detail = f"exit={proc.returncode}"
            if out:
                detail += f" out={out[:500]}"
            if err:
                detail += f" err={err[:500]}"
            results.append(CheckResult(
                name=name,
                status="passed" if proc.returncode == 0 else "failed",
                detail=detail,
            ))
        except subprocess.TimeoutExpired:
            results.append(CheckResult(name=name, status="failed", detail=f"超时（>{timeout}s）"))
        except Exception as e:  # noqa: BLE001
            results.append(CheckResult(name=name, status="failed",
                                       detail=f"{type(e).__name__}: {e}"))
    return results


# ---------- 主入口 ----------

def integrate_packages(run_dir, packages, passed_ids, report_objects=None, *,
                       enable_dynamic_checks=False, dynamic_checks=None,
                       dynamic_timeout=120) -> IntegrationResult:
    """把通过验收的包交付物合并进 ``run_dir/dist``，返回结构化结果。

    - 合并：剥离 ``workspace/<package_id>`` 前缀到 dist 根；同相对路径同内容去重；
      同路径不同内容 → conflict，整次失败（禁止覆盖）。
    - 校验：路径围栏、报告路径校验、符号链接拒绝、保留名、``.py`` 静态编译。
    - 写盘：仅 ``status == success`` 时用 staging 原子替换；任何冲突/校验错误都不碰已有 dist。
    - 动态检查默认关闭；显式开启时用 ``shell=False`` 列表参数 + 超时 + 敏感环境裁剪。
    """
    result = IntegrationResult()
    try:
        run_dir = Path(run_dir)
    except TypeError as exc:
        result.status = STATUS_VALIDATION_FAILED
        result.validation_errors.append(f"run_dir 非法：{exc}")
        result.summary = "集成目录输入非法，拒绝集成（dist 未改动）。"
        return result
    try:
        package_list = list(packages or [])
    except TypeError as exc:
        result.status = STATUS_VALIDATION_FAILED
        result.validation_errors.append(f"packages 不可迭代：{exc}")
        result.summary = "工作包输入结构非法，拒绝集成（dist 未改动）。"
        return result
    if any(not isinstance(package, dict) for package in package_list):
        result.status = STATUS_VALIDATION_FAILED
        result.validation_errors.append("工作包列表含非对象项")
        result.summary = "工作包输入结构非法，拒绝集成（dist 未改动）。"
        return result
    package_id_list = [p.get("id") for p in package_list]
    for pid in package_id_list:
        error = _package_id_error(pid)
        if error:
            result.validation_errors.append(error)
    valid_id_values = [pid for pid in package_id_list if isinstance(pid, str)]
    duplicate_ids = sorted(
        {pid for pid in valid_id_values if valid_id_values.count(pid) > 1},
        key=str,
    )
    if duplicate_ids:
        result.validation_errors.append(f"工作包 id 重复：{duplicate_ids}")
    if result.validation_errors:
        result.status = STATUS_VALIDATION_FAILED
        result.summary = "工作包标识不安全或不唯一，拒绝集成（dist 未改动）。"
        return result

    package_ids = set(package_id_list)
    if isinstance(passed_ids, (str, bytes)):
        result.status = STATUS_VALIDATION_FAILED
        result.validation_errors.append("passed_ids 必须是 id 数组，不能是字符串")
        result.summary = "集成状态输入非法，拒绝集成（dist 未改动）。"
        return result
    try:
        passed = package_ids & set(passed_ids or [])
    except TypeError as exc:
        result.status = STATUS_VALIDATION_FAILED
        result.validation_errors.append(f"passed_ids 不可迭代：{exc}")
        result.summary = "集成状态输入非法，拒绝集成（dist 未改动）。"
        return result
    result.unresolved_packages = sorted(package_ids - passed)

    if not passed:
        result.status = STATUS_NO_PACKAGES
        result.summary = "没有通过验收的工作包，未生成 dist。"
        return result

    # 1) 遍历每个包物理目录，建立 rel -> [(pkg, abs, digest)]
    index: dict[str, list[tuple[str, Path, str]]] = {}
    for pkg in package_list:
        pid = pkg.get("id")
        if pid not in passed:
            continue
        try:
            package_root = safe_package_dir(run_dir, pid)
        except ValueError as exc:
            result.validation_errors.append(f"[{pid}] 工作区路径非法：{exc}")
            continue
        if not package_root.is_dir():
            result.missing_packages.append(pid)
            result.validation_errors.append(f"[{pid}] workspace 目录缺失：{package_root}")
            continue
        result.merged_packages.append(pid)
        # 报告路径校验（不可信数据：只校验，不用于任何 IO）
        _validate_reported_deliverables(result, report_objects, pid, run_dir)
        # 物理文件遍历（只读包自己的目录树）
        for f in sorted(package_root.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(package_root).as_posix()
            if _skip_rel(rel):
                continue
            if f.is_symlink():
                result.validation_errors.append(f"[{pid}] 符号链接交付物被拒绝：{rel}")
                continue
            if rel in RESERVED_RELPATHS:
                result.validation_errors.append(f"[{pid}] 保留名 manifest.json 不可作为交付物：{rel}")
                continue
            index.setdefault(rel, []).append((pid, f, hash_file(f)))

    for pid in result.merged_packages:
        if not any(pid == owner for entries in index.values() for owner, _, _ in entries):
            result.validation_errors.append(f"[{pid}] workspace 中没有可交付文件")

    if result.missing_packages and not result.merged_packages:
        result.status = STATUS_VALIDATION_FAILED
        result.summary = "所有通过验收的包 workspace 目录均缺失。"
        return result

    # 2) 冲突检测 + 去重
    for rel in sorted(index):
        entries = index[rel]
        digests = {pid: d for pid, _, d in entries}
        pkg_ids = [pid for pid, _, _ in entries]
        if len(set(digests.values())) > 1:
            result.conflicts.append(Conflict(rel_path=rel, packages=pkg_ids, digests=digests))
        else:
            result.files.append(IntegratedFile(
                rel_path=rel,
                packages=pkg_ids,
                digest=entries[0][2],
                size=entries[0][1].stat().st_size,
                deduplicated=len(pkg_ids) > 1,
            ))

    # 3) 静态编译检查（无副作用）
    for f in result.files:
        if f.rel_path.endswith((".py", ".pyw")):
            src = index[f.rel_path][0][1]
            err = check_python_compile(src, f.rel_path)
            result.checks.append(CheckResult(
                name=f"compile:{f.rel_path}",
                status="passed" if err is None else "failed",
                package=",".join(f.packages),
                detail=err or "",
            ))
            if err:
                result.validation_errors.append(f"编译失败 {f.rel_path}: {err}")

    # 4) 状态裁决
    if result.conflicts:
        result.status = STATUS_CONFLICT
        result.summary = f"发现 {len(result.conflicts)} 个内容冲突，拒绝合并（dist 未改动）。"
    elif result.validation_errors:
        result.status = STATUS_VALIDATION_FAILED
        result.summary = f"发现 {len(result.validation_errors)} 个校验错误，拒绝合并（dist 未改动）。"
    else:
        result.status = STATUS_PARTIAL if result.unresolved_packages else STATUS_SUCCESS
        if result.status == STATUS_PARTIAL:
            result.summary = (
                f"部分合并 {len(result.files)} 个文件（来自 {len(result.merged_packages)} 个包）；"
                f"未进入集成的包：{', '.join(result.unresolved_packages)}。"
            )
        else:
            result.summary = f"成功合并 {len(result.files)} 个文件（来自 {len(result.merged_packages)} 个包）。"

    # 5) 写盘（成功或部分成功）；动态检查显式开启时对 staging 执行、未通过则不落盘
    if result.status in (STATUS_SUCCESS, STATUS_PARTIAL):
        try:
            _materialize_and_swap(
                run_dir, result, index,
                enable_dynamic_checks, dynamic_checks, dynamic_timeout,
            )
        except Exception as exc:  # noqa: BLE001
            # File-system failures are part of the integration result, not an
            # unstructured graph crash. _materialize_and_swap already cleans
            # staging and restores the previous dist when replacement fails.
            result.status = STATUS_VALIDATION_FAILED
            result.validation_errors.append(
                f"集成写盘失败：{type(exc).__name__}: {exc}"
            )
            result.summary = "集成写盘失败，已保留原 dist（如存在）。"
            result.manifest_path = None
            result.dist_dir = None

    return result


def _validate_reported_deliverables(result, report_objects, pid, run_dir):
    """校验包回传的交付物清单（不可信数据）。"""
    if report_objects is None:
        return
    if not isinstance(report_objects, dict):
        result.validation_errors.append(f"[{pid}] 结构化回传容器不是对象")
        return
    obj = report_objects.get(pid)
    if obj is None:
        return
    if not isinstance(obj, dict):
        result.validation_errors.append(f"[{pid}] 结构化回传不是对象")
        return
    deliverables = obj.get("deliverables")
    if deliverables is None:
        return
    if not isinstance(deliverables, list):
        result.validation_errors.append(f"[{pid}] deliverables 必须是数组")
        return
    for d in deliverables:
        resolved, rel, err = normalize_artifact_path(d, run_dir, pid)
        if err:
            result.validation_errors.append(f"[{pid}] 报告交付物路径非法：{d!r} → {err}")
            continue
        if not resolved.is_file():
            result.validation_errors.append(f"[{pid}] 报告交付物不是文件或缺失：{d!r}（{rel}）")


def _materialize_and_swap(run_dir, result, index, enable_dynamic_checks,
                          dynamic_checks, dynamic_timeout):
    """写 staging →（可选）动态检查 → 原子替换 dist。任何失败都不污染已有 dist。"""
    dist = run_dir / "dist"
    staging = run_dir / f".dist-staging-{uuid.uuid4().hex}"
    try:
        staging.mkdir(parents=False, exist_ok=False)
        for f in result.files:
            src = index[f.rel_path][0][1]
            dst = staging / f.rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
        (staging / "manifest.json").write_text(
            json.dumps(_manifest(result), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if enable_dynamic_checks:
            dyn = run_dynamic_checks(staging, dynamic_checks, timeout=dynamic_timeout)
            result.checks.extend(dyn)
            failed = [c for c in dyn if c.status != "passed"]
            if failed:
                for c in failed:
                    result.validation_errors.append(f"动态检查失败 {c.name}: {c.detail}")
                result.status = STATUS_VALIDATION_FAILED
                result.summary = "动态检查未通过，拒绝合并（dist 未改动）。"
                shutil.rmtree(staging, ignore_errors=True)
                return
            # Dynamic results are part of the audit record; refresh the
            # manifest after they complete so it cannot claim checks were
            # skipped when they actually ran.
            (staging / "manifest.json").write_text(
                json.dumps(_manifest(result), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        _swap_into_place(run_dir, staging, dist)
        result.manifest_path = str(dist / "manifest.json")
        result.dist_dir = str(dist)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _manifest(result: IntegrationResult) -> dict:
    return {
        "schema_version": 1,
        "generator": "agent_hive.integration",
        "status": result.status,
        "merged_packages": list(result.merged_packages),
        "missing_packages": list(result.missing_packages),
        "unresolved_packages": list(result.unresolved_packages),
        "files": [asdict(f) for f in result.files],
        "conflicts": [asdict(c) for c in result.conflicts],
        "validation_errors": list(result.validation_errors),
        "checks": [asdict(c) for c in result.checks],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "summary": result.summary,
    }


def _swap_into_place(run_dir: Path, staging: Path, dist: Path) -> None:
    """把 staging 原子替换成 dist；失败时回滚恢复旧 dist。"""
    backup = run_dir / f".dist-backup-{uuid.uuid4().hex}"
    if dist.exists():
        os.replace(dist, backup)
        try:
            os.replace(staging, dist)
        except Exception:
            if backup.exists() and not dist.exists():
                os.replace(backup, dist)
            raise
        shutil.rmtree(backup, ignore_errors=True)
    else:
        os.replace(staging, dist)
