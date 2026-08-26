"""契约文档生成器 + 漂移检测（contract-source 工作包）。

用法（在任意工作目录下均可，脚本自身定位交付目录，不依赖 CWD）：
    python scripts/generate_contracts.py             # 重新生成 skill/contracts.md
    python scripts/generate_contracts.py --check     # 检测漂移（有漂移时退出码 1）
    python scripts/generate_contracts.py --stdout    # 打印将生成的内容到 stdout
    python scripts/generate_contracts.py --out PATH  # 覆盖输出路径

资源路径策略：
- 交付目录根 = 本脚本的上一级上一级（scripts/ 的父目录），由 __file__ 推导；
- 生成目标默认是 <交付根>/skill/contracts.md；
- 全程不依赖进程当前工作目录，也不依赖安装环境。
"""
import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_DELIV_ROOT = _HERE.parent.parent

# 让交付目录内的 agent_hive 包可导入（优先于可能存在的其他同名包）
if str(_DELIV_ROOT) not in sys.path:
    sys.path.insert(0, str(_DELIV_ROOT))

from agent_hive.contract_spec import CONTRACT_VERSION, check_contracts_drift, render_contracts_md  # noqa: E402

DEFAULT_OUT = _DELIV_ROOT / "skill" / "contracts.md"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="契约文档生成与漂移检测")
    ap.add_argument("--check", action="store_true", help="检测漂移（存在漂移时退出码 1）")
    ap.add_argument("--stdout", action="store_true", help="输出到 stdout 而非写文件")
    ap.add_argument("--out", default=None, help=f"覆盖输出路径（默认 {DEFAULT_OUT}）")
    args = ap.parse_args(argv)

    rendered = render_contracts_md()

    if args.stdout:
        sys.stdout.write(rendered)
        return 0

    out_path = Path(args.out) if args.out else DEFAULT_OUT

    if args.check:
        diffs = check_contracts_drift(out_path)
        if diffs:
            print(f"[DRIFT] 契约文档与 contract_spec 不一致：{out_path}", file=sys.stderr)
            for line in diffs[:120]:
                sys.stderr.write(line + "\n")
            if len(diffs) > 120:
                print(f"…（共 {len(diffs)} 行差异，仅显示前 120 行）", file=sys.stderr)
            return 1
        print(f"[OK] 契约文档与 contract_spec 一致（版本 {CONTRACT_VERSION}）：{out_path}")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")
    print(f"[OK] 已生成 {out_path}（契约版本 {CONTRACT_VERSION}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
