"""contract-lint CLI 测试：合法/非法、目录递归、markdown 提取、悬空依赖、--schema。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LINT = [sys.executable, str(REPO_ROOT / "scripts" / "contract_lint.py")]
EXAMPLES = REPO_ROOT / "contracts" / "examples" / "packages.example.json"

VALID_PKG = {
    "id": "storage-impl",
    "title": "存储模块实现",
    "role": "编码",
    "goal": "交付后可持久化数据",
    "contract": "save(item: dict) -> bool",
    "expected_output": "python 模块 + 自测说明.md",
    "depends_on": [],
    "size": "M",
    "priority": 2,
    "acceptance": ["端到端主路径可执行并返回正确结果"],
    "deliverable": "workspace/storage-impl/",
}


def _run(*args: str):
    return subprocess.run(
        LINT + list(args),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=REPO_ROOT,
    )


def _write(tmp_path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# 1. 合法样例 → 退出 0 且无输出
# ---------------------------------------------------------------------------


class TestValid:
    def test_examples_file_exit_zero_no_output(self):
        r = _run(str(EXAMPLES))
        assert r.returncode == 0
        assert r.stdout == ""
        assert r.stderr == ""

    def test_single_package_object_file(self, tmp_path):
        p = _write(tmp_path, "pkg.json", json.dumps(VALID_PKG, ensure_ascii=False))
        r = _run(str(p))
        assert r.returncode == 0
        assert r.stderr == ""

    def test_array_document(self, tmp_path):
        doc = [dict(VALID_PKG, id="a"), dict(VALID_PKG, id="b", depends_on=["a"])]
        p = _write(tmp_path, "plan.json", json.dumps(doc, ensure_ascii=False))
        r = _run(str(p))
        assert r.returncode == 0

    def test_optional_feedback_accepted(self, tmp_path):
        pkg = dict(VALID_PKG, feedback="返工：补齐单测")
        p = _write(tmp_path, "pkg.json", json.dumps(pkg, ensure_ascii=False))
        r = _run(str(p))
        assert r.returncode == 0


# ---------------------------------------------------------------------------
# 2. 非法样例 → 退出 1，stderr 含 path/field/原因 三要素
# ---------------------------------------------------------------------------


class TestInvalid:
    def test_exit_one_with_path_field_reason(self, tmp_path):
        pkg = dict(VALID_PKG, id="Bad_ID_1", role="打杂")
        del pkg["goal"]  # 必填缺失
        p = _write(tmp_path, "bad.json", json.dumps({"packages": [pkg]}, ensure_ascii=False))
        r = _run(str(p))
        assert r.returncode == 1
        err = r.stderr
        assert str(p) in err                        # PATH 要素
        assert "packages[0].id" in err              # field 要素
        assert "kebab-case" in err                  # 原因
        assert "packages[0].role" in err
        assert "不在枚举" in err
        assert "packages[0].goal" in err
        assert "缺少必填字段 goal" in err

    def test_dangling_dependency_detected(self, tmp_path):
        pkg = dict(VALID_PKG, id="a", depends_on=["ghost"])
        p = _write(tmp_path, "dangling.json", json.dumps({"packages": [pkg]}, ensure_ascii=False))
        r = _run(str(p))
        assert r.returncode == 1
        assert "packages[0].depends_on: 引用了不存在的包 id 'ghost'" in r.stderr

    def test_duplicate_id_detected(self, tmp_path):
        doc = {"packages": [dict(VALID_PKG, id="dup"), dict(VALID_PKG, id="dup")]}
        p = _write(tmp_path, "dup.json", json.dumps(doc, ensure_ascii=False))
        r = _run(str(p))
        assert r.returncode == 1
        assert "packages[1].id" in r.stderr
        assert "重复" in r.stderr

    def test_invalid_json_exit_one(self, tmp_path):
        p = _write(tmp_path, "broken.json", "{ not json")
        r = _run(str(p))
        assert r.returncode == 1
        assert "JSON 解析失败" in r.stderr

    def test_acceptance_empty_rejected(self, tmp_path):
        pkg = dict(VALID_PKG, acceptance=[])
        p = _write(tmp_path, "empty_acc.json", json.dumps({"packages": [pkg]}, ensure_ascii=False))
        r = _run(str(p))
        assert r.returncode == 1
        assert "acceptance 至少需要 1 项" in r.stderr

    def test_priority_out_of_range_and_size_enum(self, tmp_path):
        pkg = dict(VALID_PKG, priority=9, size="XL")
        p = _write(tmp_path, "bad.json", json.dumps({"packages": [pkg]}, ensure_ascii=False))
        r = _run(str(p))
        assert r.returncode == 1
        assert "priority 9 超出范围 1..3" in r.stderr
        assert "size 'XL' 不在枚举" in r.stderr


# ---------------------------------------------------------------------------
# 3. 目录递归
# ---------------------------------------------------------------------------


class TestDirectory:
    def test_directory_recursive_finds_nested_violations(self, tmp_path):
        nested = tmp_path / "sub" / "deep"
        nested.mkdir(parents=True)
        (tmp_path / "ok.json").write_text(json.dumps({"packages": [VALID_PKG]}, ensure_ascii=False), encoding="utf-8")
        bad = nested / "bad.json"
        bad.write_text(json.dumps({"packages": [dict(VALID_PKG, role="打杂")]}, ensure_ascii=False), encoding="utf-8")
        r = _run(str(tmp_path))
        assert r.returncode == 1
        assert str(bad) in r.stderr          # 递归命中嵌套目录
        assert "packages[0].role" in r.stderr
        assert str(tmp_path / "ok.json") not in r.stderr  # 合法文件不报

    def test_directory_all_valid_exit_zero(self, tmp_path):
        (tmp_path / "a.json").write_text(json.dumps(VALID_PKG, ensure_ascii=False), encoding="utf-8")
        (tmp_path / "b.json").write_text(json.dumps({"packages": [dict(VALID_PKG, id="b")]}, ensure_ascii=False), encoding="utf-8")
        r = _run(str(tmp_path))
        assert r.returncode == 0
        assert r.stderr == ""


# ---------------------------------------------------------------------------
# 4. markdown ```json 代码块提取
# ---------------------------------------------------------------------------


class TestMarkdown:
    def test_markdown_json_blocks_extracted(self, tmp_path):
        md = _write(tmp_path, "pkgs.md", """# 包清单

```json
{"packages": [{"id": "a", "title": "t", "role": "编码", "goal": "g", "contract": "c", "expected_output": "e", "depends_on": [], "size": "S", "priority": 1, "acceptance": ["x"], "deliverable": "d"}]}
```

```json
{"id": "b", "title": "t", "role": "测试", "goal": "g", "contract": "c", "expected_output": "e", "depends_on": ["a"], "size": "M", "priority": 2, "acceptance": ["x", "y"], "deliverable": "d"}
```
""")
        r = _run(str(md))
        assert r.returncode == 0  # 跨代码块 depends_on 引用 "a" 可解析

    def test_markdown_invalid_block_detected(self, tmp_path):
        md = _write(tmp_path, "bad.md", """# 包清单

```json
{"packages": [{"id": "a", "title": "t", "role": "编码", "goal": "g", "contract": "c", "expected_output": "e", "depends_on": ["ghost"], "size": "S", "priority": 1, "acceptance": ["x"], "deliverable": "d"}]}
```
""")
        r = _run(str(md))
        assert r.returncode == 1
        assert "packages[0].depends_on: 引用了不存在的包 id 'ghost'" in r.stderr

    def test_markdown_broken_block_reported(self, tmp_path):
        md = _write(tmp_path, "broken.md", """# 包清单

```json
{ broken
```
""")
        r = _run(str(md))
        assert r.returncode == 1
        assert "JSON 解析失败" in r.stderr

    def test_markdown_without_blocks_exit_one(self, tmp_path):
        md = _write(tmp_path, "plain.md", "# 没有代码块\n")
        r = _run(str(md))
        assert r.returncode == 1
        assert "未找到 ```json 代码块" in r.stderr


# ---------------------------------------------------------------------------
# 5. --schema 与路径错误
# ---------------------------------------------------------------------------


class TestSchemaFlag:
    def test_custom_schema_relaxes_required(self, tmp_path):
        pkg = dict(VALID_PKG)
        del pkg["goal"]  # 默认 schema 下必填
        p = _write(tmp_path, "pkg.json", json.dumps(pkg, ensure_ascii=False))
        schema = tmp_path / "loose.schema.json"
        schema.write_text(json.dumps({
            "type": "object",
            "properties": {"goal": {"type": "string"}},
            "required": ["id", "title", "role", "contract", "expected_output",
                         "depends_on", "size", "priority", "acceptance", "deliverable"],
        }), encoding="utf-8")
        # 默认 schema：缺 goal → 违规
        assert _run(str(p)).returncode == 1
        # 自定义 schema：goal 非必填 → 合法
        r = _run(str(p), "--schema", str(schema))
        assert r.returncode == 0
        assert r.stderr == ""

    def test_missing_schema_file_exit_one(self, tmp_path):
        p = _write(tmp_path, "pkg.json", json.dumps(VALID_PKG, ensure_ascii=False))
        r = _run(str(p), "--schema", str(tmp_path / "nope.schema.json"))
        assert r.returncode == 1
        assert "schema 文件不存在" in r.stderr

    def test_missing_path_exit_one(self):
        r = _run(str(REPO_ROOT / "no-such-path.json"))
        assert r.returncode == 1
        assert "路径不存在" in r.stderr
