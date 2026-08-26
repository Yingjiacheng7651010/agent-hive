"""首脑程序入口。

用法（项目根目录，用项目 venv）：
    uv run python -m agent_hive run --goal "项目目标"
    uv run python -m agent_hive run --goal "..." --yes          # 自动批准（无头/测试）
    uv run python -m agent_hive run --goal "..." --tier T2      # 顾问模式：只产出架构+工程提示词包
    uv run python -m agent_hive run --goal "..." --tier T1      # 回填分工：先出包，再收专家信息收集表
    uv run python -m agent_hive run --run-id 20260823_xxxxxx --thread-id hive-20260823_xxxxxx  # 断点续跑
    HIVE_ALLOW_SHELL=1 uv run python -m agent_hive run --goal "..." --yes  # 允许专家真实执行命令（默认禁用）

安全：goal 经过输入守卫（危险操作需 --allow-danger）；审批驳回有上限（3 次）。
"""
import argparse
import json
import re
import sqlite3
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.errors import GraphInterrupt
from langgraph.types import Command

from .chief import (TRACKER, _run_dir, plan_architecture, reset_usage,
                    split_packages)
from .graph import build_graph
from .paths import safe_run_dir

_DANGER_PATTERNS = (
    # 文件系统破坏
    "rm -rf", "rm -r ", "rm -fr", "rm -rf ", "del /", "rd /s",
    "format ", "mkfs", "dd if=", "fdisk", "parted",
    "chmod 777", "chown -R",
    # 系统操作
    "shutdown", "reboot", "poweroff", "halt", "init 0", "init 6",
    "taskkill", "kill -9", "pkill -9",
    # 网络外联
    "curl ", "wget ", "nc ", "netcat", "telnet ", "ssh ",
    # Shell 执行
    "powershell", "cmd /c", "pwsh", "bash -c", "sh -c",
    "eval ", "exec ", "source ", ".bashrc", ".profile",
    # 数据库
    "drop table", "drop database", "truncate table",
    "delete from", "alter table", "sp_configure",
    # 中文危险操作
    "删库", "删表", "格式化", "清空数据", "删除数据",
    # 数据外发
    "外发", "转账", "转出", "发送到外部", "export to remote",
    # 英文变体
    "wipe database", "wipe table", "purge records", "purge data",
    "erase all", "scramble data", "truncate database",
    "exfiltrate", "exfil", "data leak",
    # 危险编译/脚本
    "base64 -d", "base64 --decode", "python -c \"import os",
    "perl -e", "ruby -e",
)


def _guard_goal(goal: str, allow_danger: bool) -> None:
    if not goal or not goal.strip():
        raise SystemExit("目标不能为空")
    if len(goal) > 2000:
        raise SystemExit("目标过长（>2000 字符）")
    low = goal.lower()
    for p in _DANGER_PATTERNS:
        if p in low:
            if not allow_danger:
                raise SystemExit(
                    f"目标疑似危险操作（命中「{p}」）。如确认安全，请加 --allow-danger 重跑。"
                )
    # 额外检查：base64 编码命令检测
    b64_patterns = [
        r'(?:echo|printf)\s+[A-Za-z0-9+/]{20,}={0,2}\s*\|',
        r'[A-Za-z0-9+/]{30,}={0,2}\s*\|?\s*(?:bash|sh|powershell|cmd)',
    ]
    for pat in b64_patterns:
        if re.search(pat, low):
            if not allow_danger:
                raise SystemExit(
                    "目标疑似包含 base64 编码的可执行命令，请确认安全后加 --allow-danger 重跑。"
                )
    print("输入守卫：目标检查通过")


def _checkpointer(run_id: str):
    try:
        run_dir = safe_run_dir(run_id)
    except ValueError as exc:
        raise SystemExit(f"run_id 非法：{exc}") from exc
    run_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(run_dir / "checkpoint.db"), check_same_thread=False)
    cp = SqliteSaver(conn)
    cp.setup()
    return cp


def _parse_integration_checks(
    raw_checks: list[str] | None,
    check_files: list[str] | None = None,
) -> list[dict]:
    """Parse explicit integration checks without allowing shell strings.

    Each inline CLI value must be a JSON object such as:
    {"name":"tests","argv":["python","-m","pytest","-q"]}.
    On PowerShell, prefer ``--integration-check-file`` because native command
    argument quoting can strip embedded JSON quotes. A file may contain one
    object or a JSON array of objects. The adapter always uses shell=False;
    malformed values fail before the graph starts.
    """
    values: list[object] = []
    for raw in raw_checks or []:
        try:
            values.append(json.loads(raw))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"--integration-check 必须是 JSON 对象：{exc}") from exc
    for filename in check_files or []:
        try:
            loaded = json.loads(Path(filename).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"--integration-check-file 无法读取有效 JSON：{filename}：{exc}") from exc
        values.extend(loaded if isinstance(loaded, list) else [loaded])

    checks: list[dict] = []
    for value in values:
        if not isinstance(value, dict) or not isinstance(value.get("argv"), list) \
                or not value.get("argv") or not all(isinstance(x, str) for x in value["argv"]):
            raise SystemExit("集成检查格式无效：需要含非空字符串 argv 数组的 JSON 对象")
        checks.append(value)
    return checks


def _ask(interrupt_value: dict, auto_yes: bool) -> dict:
    kind = interrupt_value.get("kind", "")
    if kind.startswith("审批单：架构"):
        print("\n" + "=" * 60)
        print("【审批单：架构方案】\n")
        print(interrupt_value.get("architecture", ""))
    else:
        print("\n" + "=" * 60)
        print("【审批单：批次表】\n")
        for b in interrupt_value.get("batch", []):
            deps = ", ".join(b.get("depends_on") or []) or "无"
            acc = b.get("acceptance") or []
            print(f"  - [{b['role']}] {b['id']}  {b['title']}  (依赖:{deps}，size:{b.get('size','M')})")
            print(f"      目标：{b['goal']}")
            print(f"      验收(前2条)：{acc[0][:40]}…" if acc else "      验收：无")
        print("\n  （完整验收标准与成本估算见 runs/<id>/dispatch_plan.md 与 packages.json）")
    if auto_yes:
        print("\n[--yes] 自动批准")
        return {"approved": True}
    ans = input("\n批准？(y=批准 / 其他输入=驳回并附理由): ").strip()
    if ans.lower().startswith("y"):
        return {"approved": True}
    return {"approved": False, "feedback": ans or "不同意，请重做"}


def _handle_interrupt(result: dict, auto_yes: bool) -> Command | None:
    interrupts = result.get("__interrupt__")
    if not interrupts:
        return None
    return Command(resume=_ask(interrupts[0].value, auto_yes))


def _run_tier_mode(goal: str, tier: str, run_id: str) -> None:
    """T1/T2：不派发。产出架构 + 工程提示词包（T1 额外产出专家信息收集表）。"""
    state = {"goal": goal, "run_id": run_id, "tier": tier}
    reset_usage()
    print(f"=== 首脑顾问模式（{tier}）：先出架构与工程提示词包，不派发 ===\n")
    s1 = plan_architecture(state)
    state.update(s1)
    print("架构方案：\n" + state["architecture"])
    s2 = split_packages(state)
    state.update(s2)
    run_dir = _run_dir(state)

    # 工程提示词包（contracts.md §11）
    lines = ["# 工程提示词包\n", f"项目目标：{goal}\n", state["architecture"]]
    for p in state["packages"]:
        acc = "\n".join(f"- [ ] {a}" for a in p.get("acceptance", []))
        deps = ", ".join(p.get("depends_on") or []) or "无"
        lines.append(
            f"\n## 工作包 {p['id']}（角色：{p.get('role')}）\n"
            f"- 目标：{p.get('goal')}\n"
            f"- 接口契约：{p.get('contract')}\n"
            f"- expected_output：{p.get('expected_output')}\n"
            f"- depends_on：{deps}\n"
            f"- 验收标准：\n{acc}\n"
            f"- 交付物：{p.get('deliverable')}\n"
            f"- 执行提示词：你是{p.get('role')}角色专家，严格按上述契约与验收标准执行，"
            f"交付物写入 {p.get('deliverable')}，完成后按「成果回传」格式提交。"
        )
    (run_dir / "engineering-prompt-pack.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    if tier == "T1":
        (run_dir / "agent-collection-form.md").write_text(
            "# 专家信息收集表（请回填后交回首脑）\n\n"
            "1. 名称/形态：\n2. 它最擅长的一件事：\n3. 怎么调用：\n"
            "4. 它能看到什么：\n5. 能力证据（官网/评测链接）：\n6. 成本：\n",
            encoding="utf-8",
        )
    print(f"\n产物目录：{run_dir}/")
    print(f"  - engineering-prompt-pack.md（工程提示词包）")
    if tier == "T1":
        print("  - agent-collection-form.md（专家信息收集表，回填后运行 T0 流程分工派发）")
    cost = TRACKER.snapshot()
    print(f"本次消耗：{cost['model_calls']} 次模型调用，"
          f"{cost['input_tokens']} in / {cost['output_tokens']} out tokens")


def run(goal: str, auto_yes: bool, thread_id: str | None, run_id: str | None,
        tier: str, allow_danger: bool, allow_integration_checks: bool = False,
        integration_checks: list[dict] | None = None):
    _guard_goal(goal, allow_danger)
    reset_usage()
    run_id = run_id or time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:4]
    thread_id = thread_id or f"hive-{run_id}"

    if tier in ("T1", "T2"):
        _run_tier_mode(goal, tier, run_id)
        return

    cp = _checkpointer(run_id)
    graph = build_graph().compile(checkpointer=cp)
    config = {"configurable": {"thread_id": thread_id}}

    payload = {
        "goal": goal,
        "run_id": run_id,
        "tier": tier,
        "allow_integration_checks": allow_integration_checks,
        "integration_checks": integration_checks or [],
    }
    print(f"=== 首脑启动：{goal} ===\nrun_id: {run_id}\nthread_id: {thread_id}\n")
    while True:
        try:
            result = graph.invoke(payload, config)
        except GraphInterrupt as e:
            interrupts = getattr(e, "interrupts", None) or []
            if not interrupts:
                raise RuntimeError("GraphInterrupt 未携带中断信息") from e
            payload = Command(resume=_ask(interrupts[0].value, auto_yes))
            continue
        cmd = _handle_interrupt(result, auto_yes)
        if cmd is not None:
            payload = cmd
            continue
        print("\n" + "=" * 60)
        print("【首脑最终交付】\n")
        print(result.get("final_report", "（无）"))
        cost = result.get("cost") or TRACKER.snapshot()
        print(f"\n成本：{cost['model_calls']} 次模型调用，"
              f"{cost['input_tokens']} in / {cost['output_tokens']} out tokens")
        print(f"产物目录：agent_hive/runs/{run_id}/")
        break


def main():
    load_dotenv()  # 从项目根目录 .env 读取 DEEPSEEK_API_KEY / TAVILY_API_KEY
    ap = argparse.ArgumentParser(prog="agent_hive", description="首脑统筹多智能体编排程序")
    sub = ap.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run", help="启动首脑，从项目目标开始统筹")
    run_p.add_argument("--goal", default="", help="项目目标（断点续跑时可省略）")
    run_p.add_argument("--yes", action="store_true", help="自动批准所有审批单（无头运行）")
    run_p.add_argument("--allow-danger", action="store_true", help="确认目标中的危险操作是安全的")
    run_p.add_argument("--tier", default="T0", choices=["T0", "T1", "T2"],
                       help="权限分层：T0 全流程 / T1 先出包再回填分工 / T2 顾问模式仅交付提示词包")
    run_p.add_argument("--thread-id", default=None, help="会话 thread id（断点续跑用）")
    run_p.add_argument("--run-id", default=None, help="续跑时指定原 run_id（与 --thread-id 配套）")
    run_p.add_argument(
        "--allow-integration-checks", action="store_true",
        help="显式允许集成阶段运行 JSON argv 检查（默认只做静态验证）",
    )
    run_p.add_argument(
        "--integration-check", action="append", default=[], metavar="JSON",
        help="集成检查 JSON（可重复；PowerShell 建议使用 --integration-check-file）",
    )
    run_p.add_argument(
        "--integration-check-file", action="append", default=[], metavar="PATH",
        help="从 UTF-8 JSON 文件读取一个检查对象或对象数组；可重复",
    )
    args = ap.parse_args()
    if args.cmd == "run":
        if args.thread_id and not args.run_id:
            raise SystemExit("断点续跑需要同时提供 --run-id（checkpoint 与产物按 run_id 存放）")
        checks = _parse_integration_checks(args.integration_check, args.integration_check_file)
        if checks and not args.allow_integration_checks:
            raise SystemExit("提供集成检查时必须同时显式指定 --allow-integration-checks")
        run(
            args.goal, args.yes, args.thread_id, args.run_id, args.tier,
            args.allow_danger, args.allow_integration_checks, checks,
        )


if __name__ == "__main__":
    main()
