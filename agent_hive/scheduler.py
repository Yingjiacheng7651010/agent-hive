"""依赖感知调度核心（deep module）。

本模块是调度策略的单一事实源，全部为纯函数：无 I/O、无网络、无模型调用、无 LangGraph 依赖，
便于独立单测与复用。图状态字段（passed_ids / blown_ids / blocked_ids / active_ids / retry_ids）
的读写约定见 ``state.py``。

接口（少而语义清晰）：
- ``validate_dependency_graph``   依赖图校验（空 / 重复 id / 悬空依赖 / 环）→ 非法即 ValueError
- ``build_execution_layers``      静态分层（Kahn 分层，层 i+1 只依赖严格更早的层）
- ``select_ready_packages``       动态就绪选择（返工重派优先，否则下一就绪层）
- ``classify_blocked_packages``   阻塞传播（熔断/阻塞上游的传递闭包）
- ``pending_package_ids``         尚未到终态（通过/熔断/阻塞）的包 id，供路由判断

状态机语义：
- ``passed_ids``   已通过（冻结，后续轮次不再重审）
- ``blown_ids``    熔断（返工轮次耗尽，终态失败）
- ``blocked_ids``  阻塞（上游熔断/阻塞的传递闭包，永不执行，不无限等待、不伪装通过）
- ``active_ids``   当前波次正在执行的包（同层并发派发）
- ``retry_ids``    本轮评审失败、需返工重派的包（只重派这些，不推进下一层）

并发安全：active_ids / blocked_ids / blown_ids / retry_ids / passed_ids 均由单实例节点
（dispatch / review）顺序写，不存在 fan-out 竞争；fan-out 的分支合并只发生在
reports / report_objects（按包 id 为键，单波键互异，见 state.merge_dict）。
"""
from __future__ import annotations

from typing import Iterable

from .paths import validate_package_id


def _ids(packages: Iterable[dict]) -> list[object]:
    ids: list[object] = []
    for package in packages:
        if not isinstance(package, dict):
            raise ValueError(f"工作包必须是对象：{package!r}")
        ids.append(package.get("id"))
    return ids


def validate_dependency_graph(packages: list[dict]) -> None:
    """校验依赖图，非法则抛 ``ValueError``（信息含具体原因）。

    规则：非空；包 id 全局唯一；``depends_on`` 引用的 id 必须存在；无环。
    """
    if not packages:
        raise ValueError("工作包列表为空")
    ids = _ids(packages)
    for pid in ids:
        validate_package_id(pid)
    if len(set(ids)) != len(ids):
        raise ValueError(f"工作包 id 重复：{ids}")
    id_set = set(ids)
    for p in packages:
        for d in p.get("depends_on") or []:
            if d not in id_set:
                raise ValueError(f"工作包 {p['id']} 依赖了不存在的包 {d!r}")

    # 环检测（三色 DFS）
    by_id = {p["id"]: p for p in packages}
    color: dict[str, int] = {}  # 0=未访问 1=访问中 2=完成

    def dfs(pid: str) -> None:
        if color.get(pid) == 1:
            raise ValueError(f"依赖成环，涉及：{pid}")
        if color.get(pid) == 2:
            return
        color[pid] = 1
        for d in by_id[pid].get("depends_on") or []:
            dfs(d)
        color[pid] = 2

    for pid in ids:
        dfs(pid)


def build_execution_layers(packages: list[dict]) -> list[list[str]]:
    """静态分层（Kahn 分层）：层 i 的每个包只依赖严格更早的层。

    返回 ``list[list[str]]``，每层内按 id 升序（确定性）。同层包互不依赖，可并发派发。
    非法图（空 / 重复 id / 悬空依赖 / 环）抛 ``ValueError``。
    """
    validate_dependency_graph(packages)
    indeg = {p["id"]: len(p.get("depends_on") or []) for p in packages}
    dependents: dict[str, list[str]] = {p["id"]: [] for p in packages}
    for p in packages:
        for d in p.get("depends_on") or []:
            dependents[d].append(p["id"])

    layers: list[list[str]] = []
    frontier = sorted(pid for pid, deg in indeg.items() if deg == 0)
    while frontier:
        layers.append(frontier)
        nxt: list[str] = []
        for pid in frontier:
            for child in dependents[pid]:
                indeg[child] -= 1
                if indeg[child] == 0:
                    nxt.append(child)
        frontier = sorted(nxt)

    # validate 已排除环，frontier 耗尽应覆盖全部；防御性兜底
    if sum(len(layer) for layer in layers) != len(packages):
        raise ValueError("依赖成环，分层未能覆盖全部工作包")
    return layers


def select_ready_packages(
    packages: list[dict],
    passed_ids: Iterable[str] = (),
    blocked_ids: Iterable[str] = (),
    retry_ids: Iterable[str] = (),
    blown_ids: Iterable[str] = (),
) -> list[dict]:
    """选择当前波次应派发的包（返回包 dict 的浅拷贝，调用方按需再复制）。

    语义：
    - 若 ``retry_ids`` 非空：只返回其中的合法包（返工重派），**不推进下一层**。
    - 否则：返回「下一就绪层」= 依赖全部已通过、且自身未通过/未阻塞/未熔断的包（同层并发）。

    已通过、已阻塞、已熔断的包永远不会被选中；``blown_ids`` 是显式终态输入，
    不要求调用方把熔断包重复塞进 ``blocked_ids``。
    """
    validate_dependency_graph(packages)
    passed = set(passed_ids)
    blocked = set(blocked_ids)
    blown = set(blown_ids)
    by_id = {p["id"]: p for p in packages}
    retry_requested = list(retry_ids or [])

    # 返工重派：只重派 retry_ids，去重保序，且过滤已通过/已阻塞的包。
    # 返工也必须通过依赖门，不允许 reassign 元数据绕过调度。只要调用方
    # 明确带了 retry_ids，就绝不偷偷推进到无关的下一层；不一致状态返回空，
    # 由 dispatch 抛出可诊断错误。
    retry: list[str] = []
    seen: set[str] = set()
    for pid in retry_requested:
        if pid in by_id and pid not in passed and pid not in blocked and pid not in blown:
            if pid not in seen and all(d in passed for d in (by_id[pid].get("depends_on") or [])):
                seen.add(pid)
                retry.append(pid)
    if retry_requested:
        return [dict(by_id[pid]) for pid in retry]

    # 下一就绪层
    ready: list[dict] = []
    for p in packages:
        pid = p["id"]
        if pid in passed or pid in blocked or pid in blown:
            continue
        if all(d in passed for d in (p.get("depends_on") or [])):
            ready.append(dict(p))
    return ready


def classify_blocked_packages(
    packages: list[dict],
    passed_ids: Iterable[str] = (),
    blocked_ids: Iterable[str] = (),
    blown_ids: Iterable[str] = (),
) -> list[str]:
    """阻塞传播：返回「永久阻塞」包的完整集合（既有 + 新传播，按 id 升序）。

    定义：``dead = blown_ids ∪ blocked_ids``；一个包若依赖任一 dead 包且自身未通过，
    即为阻塞。逐层传播至不动点，保证熔断上游后下游不会无限等待、也不会伪装通过。
    已通过包永不被标记阻塞。
    """
    passed = set(passed_ids)
    dead = set(blown_ids) | set(blocked_ids)
    blocked = set(blocked_ids)

    changed = True
    while changed:
        changed = False
        for p in packages:
            pid = p["id"]
            if pid in passed or pid in dead:
                continue
            deps = p.get("depends_on") or []
            if any(d in dead for d in deps):
                blocked.add(pid)
                dead.add(pid)
                changed = True
    return sorted(blocked)


def pending_package_ids(
    packages: list[dict],
    passed_ids: Iterable[str] = (),
    blocked_ids: Iterable[str] = (),
    blown_ids: Iterable[str] = (),
) -> list[str]:
    """尚未到终态（通过/熔断/阻塞）的包 id，用于路由：非空则继续派发，空则集成。"""
    passed = set(passed_ids)
    blocked = set(blocked_ids)
    blown = set(blown_ids)
    return [p["id"] for p in packages
            if p["id"] not in passed and p["id"] not in blocked and p["id"] not in blown]
