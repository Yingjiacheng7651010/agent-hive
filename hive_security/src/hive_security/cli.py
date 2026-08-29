"""hive-security CLI：``hive-security scan``（仅标准库 argparse+json+sys）。

用法::

    hive-security scan --input ARCH.json [--policy POLICY.json]
                       [--format json|sarif|markdown] [--output PATH|-]

- ``--input``  必填，结构化架构 JSON：
  ``{"overview":str,"modules":[{name,responsibility,interfaces,owner_role,depends_on?}],"risks":[str]}``
- ``--policy`` 选填；白名单字段 = fail_on_severity / max_warnings / llm_enabled /
  llm_verdict_requires_rule / exclusions / max_findings_per_threat；
  fail_on_severity 只允许 "critical"|"high"，否则退出码 3（策略非法）。
- ``--format`` 默认 sarif；三种输出均确定性（同输入逐字节同输出）。
- ``--output`` 默认 "-"（stdout）。

退出码：0 = verdict(pass/pass_with_warnings)；2 = verdict(fail)；3 = 执行错误
（文件缺失 / JSON 非法 / 策略非法 / 参数错误）。
"""
from __future__ import annotations

import argparse
import json
import sys

from .arch_security import render_security_report_md, validate_architecture
from .threat_model import ValidationPolicy, load_threat_catalog

EXIT_PASS = 0
EXIT_FAIL = 2
EXIT_ERROR = 3

_FORMATS = ("json", "sarif", "markdown")

# 策略文件白名单字段（白名单外字段一律拒绝，退出码 3）。
_POLICY_FIELDS = frozenset({
    "fail_on_severity",
    "max_warnings",
    "llm_enabled",
    "llm_verdict_requires_rule",
    "exclusions",
    "max_findings_per_threat",
})


class CliError(Exception):
    """执行错误（文件缺失 / JSON 非法 / 策略非法）→ 退出码 3。"""


def _read_json(path: str) -> object:
    try:
        # utf-8-sig：容忍 Windows 工具写入的 UTF-8 BOM（透明剥离，无 BOM 时行为与 utf-8 一致）
        with open(path, "r", encoding="utf-8-sig") as fh:
            return json.load(fh)
    except FileNotFoundError as exc:
        raise CliError(f"文件不存在：{path}") from exc
    except OSError as exc:
        raise CliError(f"文件读取失败：{path}（{exc}）") from exc
    except json.JSONDecodeError as exc:
        raise CliError(f"JSON 解析失败：{path}（{exc}）") from exc


def _load_policy(path: str | None) -> ValidationPolicy | None:
    """读取并校验策略文件；非法（白名单外字段 / 非法值）→ CliError（退出码 3）。"""
    if path is None:
        return None
    raw = _read_json(path)
    if not isinstance(raw, dict):
        raise CliError("策略文件必须是 JSON 对象")
    unknown = set(raw) - _POLICY_FIELDS
    if unknown:
        raise CliError(f"策略含白名单外字段：{sorted(unknown)}")
    kwargs: dict[str, object] = {}
    for key, value in raw.items():
        if key == "exclusions":
            if not isinstance(value, list) or not all(
                isinstance(v, str) for v in value
            ):
                raise CliError("策略字段 exclusions 必须是字符串数组")
            kwargs[key] = tuple(value)
        elif key in ("max_warnings", "max_findings_per_threat"):
            if not isinstance(value, int) or isinstance(value, bool):
                raise CliError(f"策略字段 {key} 必须是整数")
            kwargs[key] = value
        elif key in ("llm_enabled", "llm_verdict_requires_rule"):
            if not isinstance(value, bool):
                raise CliError(f"策略字段 {key} 必须是布尔值")
            kwargs[key] = value
        else:  # fail_on_severity
            if not isinstance(value, str):
                raise CliError("策略字段 fail_on_severity 必须是字符串")
            kwargs[key] = value
    try:
        return ValidationPolicy(**kwargs)  # type: ignore[arg-type]
    except ValueError as exc:
        raise CliError(f"策略非法：{exc}") from exc


def _render(report, fmt: str) -> str:
    if fmt == "json":
        return report.to_json()
    if fmt == "sarif":
        return report.to_sarif()
    return render_security_report_md(report)


def _install_error_exit(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """argparse 参数错误统一以退出码 3 退出（与「执行错误」契约一致）。"""

    def error(message: str) -> None:
        parser.print_usage(sys.stderr)
        parser.exit(EXIT_ERROR, f"{parser.prog}: error: {message}\n")

    parser.error = error  # type: ignore[method-assign]
    return parser


def _build_parser() -> argparse.ArgumentParser:
    parser = _install_error_exit(argparse.ArgumentParser(
        prog="hive-security",
        description="AI 架构安全验证（确定性规则引擎，零依赖纯标准库）",
    ))

    sub = parser.add_subparsers(dest="command", required=True)
    scan = _install_error_exit(sub.add_parser(
        "scan", help="扫描结构化架构 JSON 并输出安全报告"
    ))
    scan.add_argument("--input", required=True, help="结构化架构 JSON 文件路径")
    scan.add_argument("--policy", default=None, help="策略 JSON 文件路径（可选）")
    scan.add_argument(
        "--format",
        choices=_FORMATS,
        default="sarif",
        help=f"输出格式（默认 sarif）：{'/'.join(_FORMATS)}",
    )
    scan.add_argument("--output", default="-", help="输出路径（默认 - 表示 stdout）")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 主入口：返回退出码（0=pass/pass_with_warnings；2=fail；3=执行错误）。"""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command != "scan":
        parser.error(f"未知子命令：{args.command}")

    try:
        architecture = _read_json(args.input)
        if not isinstance(architecture, dict):
            raise CliError("架构 JSON 根必须是对象（overview/modules/risks）")
        policy = _load_policy(args.policy)
        report = validate_architecture(architecture, load_threat_catalog(), policy)
        text = _render(report, args.format)
    except CliError as exc:
        print(f"hive-security: 错误：{exc}", file=sys.stderr)
        return EXIT_ERROR

    payload = text if text.endswith("\n") else text + "\n"
    if args.output == "-":
        sys.stdout.write(payload)
    else:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(payload)
        except OSError as exc:
            print(f"hive-security: 错误：输出写入失败：{exc}", file=sys.stderr)
            return EXIT_ERROR
    return report.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
