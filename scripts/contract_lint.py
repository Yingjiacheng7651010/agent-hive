"""工作包契约 lint —— 独立 CLI（stdlib json+re+sys 自实现，不引 jsonschema 库）。

用法::

    python scripts/contract_lint.py PATH [--schema contracts/workpackage.schema.json]

PATH 支持三种输入：
- 单个 JSON 文件：``{"packages": [...]}``（PackagePlan 形态）/ 裸数组 / 单包对象；
- 目录：递归扫描 ``*.json``（每个文件独立文档）；
- markdown 文件：提取全部 ```json 代码块，合并为一份文档校验。

校验规则（约束从 ``contracts/workpackage.schema.json`` 读取，与 PackageSpec 同源）：
- 必填字段齐全（id/title/role/goal/contract/expected_output/depends_on/size/priority/acceptance/deliverable）；
- id 格式 ``^[a-z][a-z0-9-]*$``（kebab-case）且文档内唯一；
- role 枚举（编码/测试/评审/调研/安全）、size 枚举（S/M/L）、priority 整数 1..3；
- depends_on 为字符串数组且引用的包 id 必须存在（悬空引用违规）；
- acceptance 非空且为字符串数组；feedback 可选（若出现须为字符串）。

退出码：0 = 全部合法（无输出）；1 = 存在违规。
违规逐条输出 stderr，格式：``PATH:field: 原因``
（如 ``packages[2].depends_on: 引用了不存在的包 id 'ghost'``）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCHEMA = REPO_ROOT / "contracts" / "workpackage.schema.json"

# markdown ```json 代码块提取（语言标签 json，块内任意多行）。
_JSON_FENCE_RE = re.compile(r"```json[ \t]*\r?\n(.*?)\r?\n```", re.DOTALL)


class CliError(Exception):
    """执行错误（schema 缺失 / JSON 非法等）→ 退出码 1。"""


def _load_schema(schema_path: Path) -> dict:
    if not schema_path.exists():
        raise CliError(f"schema 文件不存在：{schema_path}")
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise CliError(f"schema JSON 非法：{schema_path}（{exc}）") from exc
    if not isinstance(schema, dict):
        raise CliError(f"schema 必须是 JSON 对象：{schema_path}")
    return schema


def _packages_of(doc, path: str):
    """从文档提取包列表；返回 (packages, 文档级违规消息)。"""
    if isinstance(doc, list):
        return doc, []
    if isinstance(doc, dict):
        if "packages" in doc:
            pkgs = doc["packages"]
            if not isinstance(pkgs, list):
                return [], [f"{path}:packages: packages 字段必须是数组"]
            return pkgs, []
        return [doc], []  # 单包对象文档
    return [], [f"{path}:(document): 文档根必须是对象或数组"]


def _validate_packages(packages: list, schema: dict, path: str) -> list[str]:
    """按 schema 派生约束逐包校验（约束与 contract_spec.PackageSpec 同源）。"""
    msgs: list[str] = []
    props = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    id_pattern = (props.get("id") or {}).get("pattern") or r"^[a-z][a-z0-9-]*$"
    id_re = re.compile(id_pattern)
    role_enum = (props.get("role") or {}).get("enum") or ["编码", "测试", "评审", "调研", "安全"]
    size_enum = (props.get("size") or {}).get("enum") or ["S", "M", "L"]
    pri_min = (props.get("priority") or {}).get("minimum", 1)
    pri_max = (props.get("priority") or {}).get("maximum", 3)
    acc_min = (props.get("acceptance") or {}).get("minItems", 1)

    ids: dict[str, int] = {}
    # 第一遍：结构校验 + 收集 id
    for i, pkg in enumerate(packages):
        base = f"packages[{i}]"
        if not isinstance(pkg, dict):
            msgs.append(f"{path}:{base}: 工作包必须是对象，实际为 {type(pkg).__name__}")
            continue
        for field in sorted(required):
            if field not in pkg or pkg[field] is None:
                msgs.append(f"{path}:{base}.{field}: 缺少必填字段 {field}")
        pid = pkg.get("id")
        if pid is None:
            pass  # 必填缺失已报
        elif not isinstance(pid, str):
            msgs.append(f"{path}:{base}.id: id 必须是字符串，实际为 {type(pid).__name__}")
        elif not id_re.match(pid):
            msgs.append(f"{path}:{base}.id: id '{pid}' 不符合 kebab-case 模式 {id_pattern}")
        elif pid in ids:
            msgs.append(f"{path}:{base}.id: 与 packages[{ids[pid]}] 的 id '{pid}' 重复")
        else:
            ids[pid] = i
        role = pkg.get("role")
        if role is not None and role not in role_enum:
            msgs.append(f"{path}:{base}.role: role '{role}' 不在枚举 {list(role_enum)} 中")
        size = pkg.get("size")
        if size is not None and size not in size_enum:
            msgs.append(f"{path}:{base}.size: size '{size}' 不在枚举 {list(size_enum)} 中")
        priority = pkg.get("priority")
        if priority is not None:
            if type(priority) is not int:
                msgs.append(f"{path}:{base}.priority: priority 必须是整数，实际为 {type(priority).__name__}")
            elif not (pri_min <= priority <= pri_max):
                msgs.append(f"{path}:{base}.priority: priority {priority} 超出范围 {pri_min}..{pri_max}")
        acceptance = pkg.get("acceptance")
        if acceptance is not None:
            if not isinstance(acceptance, list):
                msgs.append(f"{path}:{base}.acceptance: acceptance 必须是数组，实际为 {type(acceptance).__name__}")
            else:
                if len(acceptance) < acc_min:
                    msgs.append(f"{path}:{base}.acceptance: acceptance 至少需要 {acc_min} 项（当前 {len(acceptance)}）")
                for j, item in enumerate(acceptance):
                    if not isinstance(item, str):
                        msgs.append(f"{path}:{base}.acceptance[{j}]: 验收项必须是字符串，实际为 {type(item).__name__}")
        feedback = pkg.get("feedback")
        if feedback is not None and not isinstance(feedback, str):
            msgs.append(f"{path}:{base}.feedback: feedback 必须是字符串，实际为 {type(feedback).__name__}")

    # 第二遍：depends_on 悬空引用（id 全集收集完后再判）
    for i, pkg in enumerate(packages):
        if not isinstance(pkg, dict):
            continue
        deps = pkg.get("depends_on")
        if deps is None:
            continue  # 必填缺失已报
        if not isinstance(deps, list):
            msgs.append(f"{path}:packages[{i}].depends_on: depends_on 必须是数组，实际为 {type(deps).__name__}")
            continue
        for d in deps:
            if not isinstance(d, str):
                msgs.append(f"{path}:packages[{i}].depends_on: 依赖项必须是字符串，实际为 {type(d).__name__}")
            elif d not in ids:
                msgs.append(f"{path}:packages[{i}].depends_on: 引用了不存在的包 id '{d}'")
    return msgs


def _lint_json_file(target: Path, schema: dict) -> list[str]:
    path = str(target)
    try:
        doc = json.loads(target.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        return [f"{path}:(document): 文件读取失败：{exc}"]
    except json.JSONDecodeError as exc:
        return [f"{path}:(document): JSON 解析失败：{exc}"]
    packages, doc_msgs = _packages_of(doc, path)
    return doc_msgs + _validate_packages(packages, schema, path)


def _lint_markdown(target: Path, schema: dict) -> list[str]:
    path = str(target)
    try:
        text = target.read_text(encoding="utf-8-sig")
    except OSError as exc:
        return [f"{path}:(document): 文件读取失败：{exc}"]
    msgs: list[str] = []
    packages: list = []
    blocks = list(_JSON_FENCE_RE.finditer(text))
    if not blocks:
        return [f"{path}:(document): 未找到 ```json 代码块"]
    for match in blocks:
        block = match.group(1)
        try:
            doc = json.loads(block)
        except json.JSONDecodeError as exc:
            msgs.append(f"{path}:(json-block): JSON 解析失败：{exc}")
            continue
        pkgs, doc_msgs = _packages_of(doc, path)
        msgs.extend(doc_msgs)
        packages.extend(pkgs)
    return msgs + _validate_packages(packages, schema, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="contract-lint",
        description="工作包契约校验（stdlib 自实现，约束来自 contracts/workpackage.schema.json）",
    )
    parser.add_argument("path", help="JSON 文件 / 目录（递归 *.json）/ markdown 文件（提取 ```json 代码块）")
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA),
                        help=f"JSON Schema 文件（默认 {DEFAULT_SCHEMA}）")
    args = parser.parse_args(argv)

    try:
        schema = _load_schema(Path(args.schema))
    except CliError as exc:
        print(f"contract-lint: {exc}", file=sys.stderr)
        return 1

    target = Path(args.path)
    if not target.exists():
        print(f"contract-lint: 路径不存在：{args.path}", file=sys.stderr)
        return 1

    if target.is_dir():
        msgs: list[str] = []
        for p in sorted(target.rglob("*.json")):
            msgs.extend(_lint_json_file(p, schema))
    elif target.suffix.lower() == ".md":
        msgs = _lint_markdown(target, schema)
    else:
        msgs = _lint_json_file(target, schema)

    for message in msgs:
        print(message, file=sys.stderr)
    if msgs:
        print(f"contract-lint: {len(msgs)} 条违规", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
