"""发布验收辅助：README/官网链接检查 + 工作流 YAML 解析（本地运行，非 CI）。"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # 仓库根（脚本位于 site/）

FILES = ["README.md", "README_EN.md", "site/index.html"]
WORKFLOWS = [".github/workflows/publish-packages.yml", ".github/workflows/pages.yml"]

LINK_RES = [
    re.compile(r"\[[^\]]*\]\(([^)]+)\)"),   # markdown 链接
    re.compile(r'(?:href|src)="([^"]+)"'),  # html 链接
]


def check_links() -> int:
    rc = 0
    for fname in FILES:
        text = (ROOT / fname).read_text(encoding="utf-8")
        links = [m for r in LINK_RES for m in r.findall(text)]
        missing = []
        for link in links:
            if link.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = (ROOT / fname).parent / link
            if not target.exists():
                missing.append(link)
        status = "OK" if not missing else f"MISSING {missing}"
        if missing:
            rc = 1
        print(f"[links] {fname}: {len(links)} links -> {status}")
    return rc


def check_workflows() -> int:
    try:
        import yaml
    except ImportError:
        print("[warn] PyYAML 不可用，跳过工作流解析")
        return 0
    rc = 0
    for f in WORKFLOWS:
        data = yaml.safe_load((ROOT / f).read_text(encoding="utf-8"))
        on_key = "on" if "on" in data else True  # PyYAML 1.1 把 on 解析为 True
        on = data.get(on_key)
        jobs = sorted((data.get("jobs") or {}).keys())
        perms = data.get("permissions") or {}
        print(f"[yaml] {f}: on={list(on) if isinstance(on, dict) else on} jobs={jobs} permissions={sorted(perms)}")
        # 红线自查：仓库内不出现 token/密钥 —— 只拦 ${{ secrets.* }} 引用与字面量凭据；
        # "id-token: write"（OIDC 权限声明）不是密钥，不误报。
        text = (ROOT / f).read_text(encoding="utf-8")
        bad = re.findall(r"\$\{\{\s*secrets\.[^}]+\}\}", text)
        literal = re.findall(r"(?im)^\s*(?:api[_-]?key|password|secret|token)\s*[:=]\s*[\"'][^\"']+[\"']\s*$", text)
        if bad or literal:
            print(f"[FAIL] {f} 出现疑似密钥引用（红线）：secrets={bad} literal={literal}")
            rc = 1
    return rc


def main() -> int:
    rc = check_links()
    rc |= check_workflows()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
