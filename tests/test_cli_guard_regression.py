from __future__ import annotations

import pytest

from agent_hive.main import _parse_integration_checks


def test_cli_integration_check_requires_json_argv_list():
    checks = _parse_integration_checks([
        '{"name":"tests","argv":["python","-m","pytest","-q"],"cwd":"."}'
    ])

    assert checks[0]["name"] == "tests"
    assert checks[0]["argv"][-1] == "-q"


def test_cli_integration_check_file_supports_shell_safe_windows_usage(tmp_path):
    check_file = tmp_path / "checks.json"
    check_file.write_text(
        '[{"name":"tests","argv":["python","-m","pytest","-q"]}]',
        encoding="utf-8",
    )

    checks = _parse_integration_checks([], [str(check_file)])

    assert checks == [{"name": "tests", "argv": ["python", "-m", "pytest", "-q"]}]


@pytest.mark.parametrize("raw", ["not-json", "[]", '{"name":"bad"}', '{"argv":[1]}'])
def test_cli_integration_check_rejects_ambiguous_or_unsafe_shape(raw):
    with pytest.raises(SystemExit):
        _parse_integration_checks([raw])
