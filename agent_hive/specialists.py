"""专家节点：按角色提示词执行工作包，结构化回传成果。

安全设计（红队审查后加固）：
- 路径围栏用 Path.is_relative_to（防同级目录前缀绕过）
- run_command 默认禁用（HIVE_ALLOW_SHELL=1 显式开启），子进程环境剔除一切密钥
- 按角色最小权限裁剪工具：编码/测试可用 shell（开启时）；评审/调研不可用 shell
- 工具内部吞异常返回错误文本，不抛穿 agent 循环
"""
import os
import subprocess
from pathlib import Path

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage

from .chief import TRACKER, _invoke_structured
from .paths import safe_package_dir, safe_run_dir
from .prompts import DEFAULT_ROLE, ROLE_PROMPTS, ReportSpec

ALLOW_SHELL = os.getenv("HIVE_ALLOW_SHELL", "0") == "1"
_SENSITIVE_MARKERS = ("KEY", "TOKEN", "SECRET", "PASS", "CREDENTIAL")


def _safe_env() -> dict:
    """剔除敏感环境变量后再交给子进程。"""
    env = dict(os.environ)
    for k in list(env):
        if any(m in k.upper() for m in _SENSITIVE_MARKERS):
            env.pop(k, None)
    return env


def _make_file_tools(run_dir: Path, own_dir: Path):
    """受限文件工具：读全工作区，只写自己的目录（Claude Code 子代理文件所有权思路）。"""
    run_root = run_dir.resolve()
    own_root = own_dir.resolve()

    def _resolve(path: str, base: Path) -> Path:
        p = Path(path)
        if not p.is_absolute():
            p = base / p
        return p.resolve()

    def _in(p: Path, root: Path) -> bool:
        try:
            return p.is_relative_to(root)
        except ValueError:
            return False

    @tool
    def read_file(path: str) -> str:
        """读取 run 工作区内任意文件（架构、看板、其他专家交付物）；目录则返回其文件清单。大文件截断。"""
        max_chars = 8000
        try:
            p = _resolve(path, run_dir)
            if not _in(p, run_root):
                return f"拒绝访问：{path} 超出工作区"
            if not p.exists():
                return f"文件不存在：{path}"
            if p.is_dir():
                lines = []
                for f in sorted(p.rglob("*")):
                    if f.is_file():
                        try:
                            rel = f.relative_to(run_dir)
                        except ValueError:
                            rel = f
                        lines.append(str(rel))
                return "（目录，共 %d 个文件，仅显示前 100 个）\n" % len(lines) + (
                    "\n".join(lines[:100]) if lines else "（空目录）")
            text = p.read_text(encoding="utf-8", errors="replace")
            if len(text) > max_chars:
                text = text[:max_chars] + f"\n…（已截断，原文 {len(text)} 字符，请用分段续读）"
            return text
        except Exception as e:  # noqa: BLE001
            return f"【工具失败】读取失败：{type(e).__name__}: {e}"

    @tool
    def write_file(path: str, content: str) -> str:
        """把文件写入自己的交付物目录 workspace/<包id>/。"""
        try:
            p = _resolve(path, own_dir)
            if not _in(p, own_root):
                return f"拒绝访问：只能写自己的工作区 workspace/<包id>/（尝试写入 {p}）"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return f"已写入 {p.relative_to(run_dir)}"
        except Exception as e:  # noqa: BLE001
            return f"【工具失败】写入失败：{type(e).__name__}: {e}"

    @tool
    def list_files(path: str = ".") -> str:
        """列出 run 工作区内某目录的内容（默认工作区根目录）。"""
        try:
            p = _resolve(path, run_dir)
            if not _in(p, run_root) or not p.exists():
                return f"目录不可用：{path}"
            lines = []
            for f in sorted(p.rglob("*")):
                if f.is_file():
                    try:
                        rel = f.relative_to(run_dir)
                    except ValueError:
                        rel = f
                    lines.append(str(rel))
            return "\n".join(lines[:200]) if lines else "（空目录）"
        except Exception as e:  # noqa: BLE001
            return f"【工具失败】列出失败：{type(e).__name__}: {e}"

    @tool
    def run_command(command: str) -> str:
        """在 run 工作区目录执行一条命令（如运行 python 脚本或 pytest）。120 秒超时。

        注意：默认禁用，需设置环境变量 HIVE_ALLOW_SHELL=1 才可用；子进程环境已剔除密钥；
        含危险关键词的命令（rm -rf / curl / wget / shutdown / 格式化等）会被拒绝。
        """
        if not ALLOW_SHELL:
            return "run_command 已禁用：设置环境变量 HIVE_ALLOW_SHELL=1 后重试。"
        low = command.lower()
        for bad in ("rm -rf", "rm -r ", "del /", "rd /s", "format ", "shutdown",
                    "curl ", "wget ", "powershell", "cmd /c", "> nul", "taskkill"):
            if bad in low:
                return f"【工具失败】命令被拒绝：包含危险片段「{bad.strip()}」"
        try:
            proc = subprocess.run(
                command, shell=True, cwd=str(run_dir),
                capture_output=True, text=True, timeout=120,
                encoding="utf-8", errors="replace", env=_safe_env(),
            )
            out = (proc.stdout or "")[-4000:]
            err = (proc.stderr or "")[-2000:]
            return f"exit={proc.returncode}\nSTDOUT:\n{out}\nSTDERR:\n{err}"
        except subprocess.TimeoutExpired:
            return "【工具失败】命令超时（120 秒）"
        except Exception as e:  # noqa: BLE001
            return f"【工具失败】执行失败：{type(e).__name__}: {e}"

    return [read_file, write_file, list_files, run_command]


def format_package(pkg: dict, run_dir: Path, own_dir: Path) -> str:
    """把工作包渲染成专家可读的交接文档（contracts.md §4 格式，只给必要材料）。"""
    acceptance = "\n".join(f"- [ ] {a}" for a in pkg.get("acceptance", []))
    deps = ", ".join(pkg.get("depends_on") or []) or "无"
    return (
        f"# 工作包：{pkg.get('title', pkg.get('id'))}\n"
        f"- 目标：{pkg.get('goal', '')}\n"
        f"- 工作区根目录（绝对路径）：{run_dir}\n"
        f"- 你的交付物目录（绝对路径）：{own_dir}\n"
        f"- 背景：架构方案见 {run_dir / 'architecture.md'}，项目看板见 {run_dir / 'board.md'}；"
        f"依赖工件的实际代码用 read_file 读取（depends_on 指向的包目录在 workspace/ 下）\n"
        f"- 接口契约：{pkg.get('contract', '')}\n"
        f"- expected_output：{pkg.get('expected_output', '')}\n"
        f"- depends_on：{deps}\n"
        f"- 验收标准：\n{acceptance}\n"
        f"- 交付物：{pkg.get('deliverable', '')}\n"
        f"- size：{pkg.get('size', 'M')}   priority：{pkg.get('priority', 2)}\n"
        f"- 轮次上限：3\n"
        f"- 约束：真实交付物必须用 write_file 写进你的交付物目录；自测要真的跑（可用工具）"
    )


def render_report_md(pkg: dict, report: ReportSpec) -> str:
    """把结构化回传渲染成 markdown（存 reports/ 与最终报告用）。"""
    comp = "\n".join(f"- {c}" for c in report.completion)
    dels = "\n".join(f"- {d}" for d in report.deliverables)
    opens = "\n".join(f"- {o}" for o in report.open_issues)
    sugs = "\n".join(f"- {s}" for s in report.suggestions)
    return (
        f"# 成果回传：{pkg.get('id')}\n\n"
        f"## 完成情况\n{comp}\n\n"
        f"## 交付物清单\n{dels}\n\n"
        f"## 自测\n{report.self_test}\n\n"
        f"## 遗留问题\n{opens}\n\n"
        f"## 问题与建议\n{sugs}\n"
    )


def _parse_report(raw: str) -> ReportSpec:
    """把自由文本回传整理成结构化回传（二次结构化）。"""
    try:
        return _invoke_structured(ReportSpec, [
            SystemMessage("把下面的专家回传整理成指定结构，逐项提炼，不要编造内容。"),
            HumanMessage(raw),
        ])
    except Exception:
        return ReportSpec(
            completion=["未通过: 回传无法解析为结构化格式"],
            deliverables=[],
            self_test=raw or "（空回传）",
            open_issues=["结构化解析失败，需人工查看原文"],
            suggestions=[],
        )


def specialist_node(state):
    """fan-out 分支节点：每个工作包独立执行一次，结构化回传（类型化工件）。"""
    pkg = state.get("current_package") or {}
    role = pkg.get("role") or DEFAULT_ROLE
    system_prompt = ROLE_PROMPTS.get(role, ROLE_PROMPTS[DEFAULT_ROLE])

    run_dir = safe_run_dir(state.get("run_id", "run"))
    own_dir = safe_package_dir(run_dir, pkg.get("id"))
    own_dir.mkdir(parents=True, exist_ok=True)

    feedback = (pkg.get("feedback") or "").strip()
    fb_note = f"\n\n【上一轮驳回反馈，必须逐条修正】\n{feedback}" if feedback else ""
    human = format_package(pkg, run_dir, own_dir) + fb_note

    # 最小权限裁剪：按角色给工具
    file_tools = _make_file_tools(run_dir, own_dir)
    read_write_list = [t for t in file_tools if t.name != "run_command"]
    run_cmd = [t for t in file_tools if t.name == "run_command"]
    if role in ("编码", "测试"):
        tools = read_write_list + run_cmd  # 需要真实执行代码/测试
    elif role == "调研":
        try:
            from langchain_tavily import TavilySearch
            tools = [TavilySearch(max_results=5, topic="general")] + read_write_list
        except Exception:  # Tavily 不可用时降级：只读文件工具，不拖垮整个 run
            tools = read_write_list
    else:  # 评审等：只读+写报告
        tools = read_write_list

    agent = create_agent("deepseek-chat", system_prompt=system_prompt, tools=tools)
    try:
        resp = agent.invoke({"messages": [HumanMessage(human)]},
                            config={"recursion_limit": 30, "callbacks": [TRACKER]})
    except Exception as e:  # noqa: BLE001
        resp = None
        agent_error = f"{type(e).__name__}: {e}"
    else:
        agent_error = None

    # 取最后一条"真正的最终回复"（跳过工具调用残留的 AIMessage/空内容）
    raw = ""
    if resp is not None:
        for msg in reversed(resp["messages"]):
            if (isinstance(msg, HumanMessage) or getattr(msg, "type", "") == "ai") \
                    and getattr(msg, "content", "") and not getattr(msg, "tool_calls", None):
                raw = msg.content
                break
    if agent_error:
        raw = f"【专家执行失败】{agent_error}\n{raw}"

    if agent_error:
        structured = ReportSpec(
            completion=["未通过：专家执行失败"],
            deliverables=[],
            self_test=raw or "（空回传）",
            open_issues=[agent_error],
            suggestions=[],
        )
    else:
        structured = _parse_report(raw)
    structured_dict = structured.model_dump()
    parse_failed_marker = "未通过: 回传无法解析为结构化格式"
    structured_dict["parse_ok"] = bool(raw.strip()) \
        and agent_error is None \
        and parse_failed_marker not in structured.completion
    if agent_error:
        structured_dict["execution_error"] = agent_error

    report_md = render_report_md(pkg, structured)
    return {
        "reports": {pkg["id"]: report_md},
        "report_objects": {pkg["id"]: structured_dict},
    }
