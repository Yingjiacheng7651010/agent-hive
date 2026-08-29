"""hive-security CLI 契约测试（退出码三态 / 三格式确定性 / 策略校验 / 输出等价）。"""
from __future__ import annotations

import json

import pytest

from hive_security.cli import main

# 通过样例：零 finding → verdict=pass → 退出码 0（与 test_arch_security 干净样例同构）
CLEAN_ARCH = {
    "overview": "系统包含认证、鉴权与身份管理、失败降级与守卫设计",
    "modules": [
        {"name": "auth", "responsibility": "提供统一认证、鉴权与身份管理服务",
         "interfaces": ["login()"], "owner_role": "编码"},
        {"name": "gateway", "responsibility": "请求路由与守卫",
         "interfaces": ["route()"], "owner_role": "编码", "depends_on": ["auth"]},
    ],
    "risks": ["网关故障时降级为只读", "密钥由平台密钥管理服务托管"],
}

# 失败样例：命中 T-SPOOF-1（high，缺少认证控制设计）→ verdict=fail → 退出码 2
FAIL_ARCH = {
    "overview": "o",
    "modules": [
        {"name": "user", "responsibility": "负责用户登录与密码校验",
         "interfaces": ["login()", "reset_password()"], "owner_role": "编码"},
    ],
    "risks": ["r"],
}


def _write_json(tmp_path, name, data):
    p = tmp_path / name
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# 1. 退出码三态（0=pass/pass_with_warnings；2=fail；3=执行错误）
# ---------------------------------------------------------------------------


class TestExitCodes:
    def test_pass_exit_zero(self, tmp_path, capsys):
        arch = _write_json(tmp_path, "clean.json", CLEAN_ARCH)
        rc = main(["scan", "--input", arch, "--format", "json"])
        out = capsys.readouterr().out
        assert rc == 0
        assert '"verdict": "pass"' in out

    def test_fail_exit_two(self, tmp_path, capsys):
        arch = _write_json(tmp_path, "fail.json", FAIL_ARCH)
        rc = main(["scan", "--input", arch, "--format", "json"])
        out = capsys.readouterr().out
        assert rc == 2
        assert '"verdict": "fail"' in out

    def test_missing_input_file_exit_three(self, tmp_path, capsys):
        rc = main(["scan", "--input", str(tmp_path / "nope.json")])
        err = capsys.readouterr().err
        assert rc == 3
        assert "文件不存在" in err

    def test_invalid_json_exit_three(self, tmp_path, capsys):
        bad = tmp_path / "bad.json"
        bad.write_text("{ not json", encoding="utf-8")
        rc = main(["scan", "--input", str(bad)])
        err = capsys.readouterr().err
        assert rc == 3
        assert "JSON" in err

    def test_missing_required_input_exit_three(self):
        # argparse 参数错误同样归一为退出码 3
        with pytest.raises(SystemExit) as excinfo:
            main(["scan"])
        assert excinfo.value.code == 3


# ---------------------------------------------------------------------------
# 2. --format 三态输出确定性（同一输入跑两遍，逐字节相等）
# ---------------------------------------------------------------------------


class TestFormatDeterminism:
    @pytest.mark.parametrize("fmt", ["json", "sarif", "markdown"])
    def test_format_output_byte_identical_across_runs(self, tmp_path, capsys, fmt):
        arch = _write_json(tmp_path, "arch.json", FAIL_ARCH)
        rc1 = main(["scan", "--input", arch, "--format", fmt])
        out1 = capsys.readouterr().out
        rc2 = main(["scan", "--input", arch, "--format", fmt])
        out2 = capsys.readouterr().out
        assert rc1 == rc2 == 2
        assert out1 == out2  # 逐字节相等
        assert out1

    def test_default_format_is_sarif(self, tmp_path, capsys):
        arch = _write_json(tmp_path, "arch.json", CLEAN_ARCH)
        main(["scan", "--input", arch])
        out = capsys.readouterr().out
        assert json.loads(out)["version"] == "2.1.0"

    def test_markdown_output_shape(self, tmp_path, capsys):
        arch = _write_json(tmp_path, "arch.json", CLEAN_ARCH)
        main(["scan", "--input", arch, "--format", "markdown"])
        out = capsys.readouterr().out
        assert out.startswith("# 架构安全验证报告")
        assert "## 发现清单" in out


# ---------------------------------------------------------------------------
# 3. 策略文件：非法拒绝（退出码 3）、合法生效
# ---------------------------------------------------------------------------


class TestPolicy:
    def test_invalid_fail_on_severity_rejected(self, tmp_path, capsys):
        arch = _write_json(tmp_path, "arch.json", CLEAN_ARCH)
        policy = _write_json(tmp_path, "policy.json", {"fail_on_severity": "low"})
        rc = main(["scan", "--input", arch, "--policy", policy])
        err = capsys.readouterr().err
        assert rc == 3
        assert "策略" in err

    def test_unknown_policy_field_rejected(self, tmp_path, capsys):
        arch = _write_json(tmp_path, "arch.json", CLEAN_ARCH)
        policy = _write_json(tmp_path, "policy.json", {"fail_on_severity": "high", "bogus": 1})
        rc = main(["scan", "--input", arch, "--policy", policy])
        err = capsys.readouterr().err
        assert rc == 3
        assert "白名单外字段" in err

    def test_invalid_policy_json_rejected(self, tmp_path, capsys):
        arch = _write_json(tmp_path, "arch.json", CLEAN_ARCH)
        policy = tmp_path / "policy.json"
        policy.write_text("not json", encoding="utf-8")
        rc = main(["scan", "--input", arch, "--policy", str(policy)])
        assert rc == 3

    def test_valid_policy_accepted(self, tmp_path, capsys):
        arch = _write_json(tmp_path, "arch.json", CLEAN_ARCH)
        policy = _write_json(tmp_path, "policy.json", {
            "fail_on_severity": "critical",
            "max_warnings": 1,
            "llm_enabled": False,
            "llm_verdict_requires_rule": True,
            "exclusions": ["T-SPOOF-1"],
            "max_findings_per_threat": 3,
        })
        rc = main(["scan", "--input", arch, "--policy", policy, "--format", "json"])
        out = capsys.readouterr().out
        assert rc == 0
        assert '"verdict": "pass"' in out


# ---------------------------------------------------------------------------
# 4. --output 写文件与 stdout 逐字节等价
# ---------------------------------------------------------------------------


class TestOutput:
    def test_output_file_equals_stdout_bytes(self, tmp_path, capsys):
        arch = _write_json(tmp_path, "arch.json", FAIL_ARCH)
        out_file = tmp_path / "report.sarif"

        rc_stdout = main(["scan", "--input", arch, "--format", "sarif", "--output", "-"])
        stdout_text = capsys.readouterr().out
        rc_file = main(["scan", "--input", arch, "--format", "sarif", "--output", str(out_file)])
        capsys.readouterr()

        assert rc_stdout == rc_file == 2
        assert out_file.read_text(encoding="utf-8") == stdout_text  # 逐字节等价

    def test_output_file_written_for_json(self, tmp_path, capsys):
        arch = _write_json(tmp_path, "arch.json", CLEAN_ARCH)
        out_file = tmp_path / "report.json"
        rc = main(["scan", "--input", arch, "--format", "json", "--output", str(out_file)])
        capsys.readouterr()
        assert rc == 0
        data = json.loads(out_file.read_text(encoding="utf-8"))
        assert data["verdict"] == "pass"
