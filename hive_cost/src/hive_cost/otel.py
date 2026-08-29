"""OTel 兼容 JSONL 导出（零依赖落盘，不做 OTLP 网络上报）。

``export_cost_otel_jsonl(path, events)`` 将事件列表逐行 ``json.dumps``
（``ensure_ascii=False``，中文不转义）写入 UTF-8 文件；父目录不存在则自动创建；
返回写入条数。同输入两次导出逐字节一致（确定性）。
"""
from __future__ import annotations

import json
from pathlib import Path

__all__ = ["export_cost_otel_jsonl"]


def export_cost_otel_jsonl(path, events: list[dict]) -> int:
    """把事件列表导出为 OTel 兼容 JSONL 文件。

    Args:
        path: 输出文件路径；父目录不存在时自动创建。
        events: 事件字典列表（如 ``CostGate.to_otel_events()`` 的产物）。

    Returns:
        写入的事件条数。
    """
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for event in events:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    return len(events)
