"""威胁目录扩展包测试（独立包移植版，威胁目录扩展加载能力）。"""
from __future__ import annotations

import json

import pytest

from hive_security.threat_model import load_threat_catalog


def _write_extension(tmp_path, threats, version="企业扩展 1.0"):
    p = tmp_path / "ext.json"
    p.write_text(json.dumps({"version": version, "threats": threats}, ensure_ascii=False),
                 encoding="utf-8")
    return str(p)


def _ext_threat(tid="T-EXT-1"):
    return {
        "id": tid,
        "category": "tampering",
        "name": "扩展威胁",
        "severity": "high",
        "keywords": ["扩展关键词"],
    }


def test_extension_loads_and_merges(tmp_path):
    path = _write_extension(tmp_path, [_ext_threat("T-EXT-1")])
    catalog = load_threat_catalog(path)
    ids = [t.id for t in catalog.threats]
    assert "T-EXT-1" in ids
    assert len(ids) == 13  # 内置 12 + 扩展 1
    assert "+" in catalog.version  # 版本带扩展标识（策略哈希随报告可审计）


def test_extension_id_conflict_rejected(tmp_path):
    path = _write_extension(tmp_path, [_ext_threat("T-DISC-1")])  # 与内置冲突
    with pytest.raises(ValueError, match="冲突"):
        load_threat_catalog(path)


def test_extension_internal_duplicate_rejected(tmp_path):
    path = _write_extension(tmp_path, [_ext_threat("T-EXT-1"), _ext_threat("T-EXT-1")])
    with pytest.raises(ValueError, match="重复"):
        load_threat_catalog(path)


def test_extension_invalid_entry_rejected(tmp_path):
    path = _write_extension(tmp_path, [{"id": "T-BAD-1"}])  # 缺 category
    with pytest.raises(ValueError, match="非法"):
        load_threat_catalog(path)


def test_no_extension_backward_compatible():
    catalog = load_threat_catalog()
    assert len(catalog.threats) == 12
    assert catalog.version == "1.0.0"