"""动态验证授权清单（ScopeManifest / ScopeAuthorizer）。

借鉴 DeepSec scope.json 的硬门禁思想：任何授权决策都必须同时满足
白名单、禁用网段、时间窗、清单配置等全部条件，缺一即拒绝（fail-closed），
不存在任何可绕过的捷径（例如私网地址即使被显式列入 targets 也一律拒绝）。

纯标准库实现（dataclasses / ipaddress / json / time / pathlib / socket），
不依赖 langchain / pydantic；审计记录复用 data_compliance.AuditLogger。
"""
from __future__ import annotations

import ipaddress
import json
import socket
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent_hive.data_compliance import AuditLogger, AuditRecord

__all__ = ["ScopeManifest", "ScopeDecision", "ScopeAuthorizer"]

# 硬门禁：目标地址一旦命中下列地址类别，无论是否列入白名单一律拒绝
RESERVED_ADDRESS_CHECKS = (
    "is_loopback",      # 回环 127.0.0.0/8、::1
    "is_link_local",    # 链路本地 169.254.0.0/16、fe80::/10
    "is_multicast",     # 组播 224.0.0.0/4、ff00::/8
    "is_unspecified",   # 未指定 0.0.0.0、::
    "is_reserved",      # 保留地址
)


@dataclass
class ScopeManifest:
    """动态验证授权清单（一次授权的全部硬门禁条件）。"""
    scope_id: str
    tenant_id: str = ""
    targets: list[str] = field(default_factory=list)      # 目标白名单（IP 或 hostname）
    valid_from: float = 0.0
    valid_until: float = 0.0                               # 0=长期（需审批）
    prohibited_cidrs: list[str] = field(default_factory=lambda: [
        "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
        "127.0.0.0/8", "169.254.0.0/16", "224.0.0.0/4",
    ])
    allowed_ports: list[int] = field(default_factory=list)
    signer: str = ""
    approver: str = ""
    reason: str = ""


@dataclass
class ScopeDecision:
    """授权决策结果。"""
    allowed: bool
    reason: str
    is_private_network: bool = False


class ScopeAuthorizer:
    """动态验证授权清单的硬门禁裁决器。

    全部条件缺一即拒绝（fail-closed）：
    1. 清单必须配置 scope_id，否则「未配置授权清单」；
    2. 目标必须能解析为 IP，否则「目标解析失败」；
    3. 解析出的任一 IP 命中禁用 CIDR / 回环 / 链路本地 / 组播 / 未指定 /
       保留地址 → 「私网/保留地址禁止」（即使该 IP 被显式列入 targets）；
    4. 当前时刻必须落在 valid_from..valid_until 时间窗内
       （valid_until==0 视为长期授权，需审批），否则「授权已过期」；
    5. 解析出的任一 IP 必须命中 targets 白名单，否则「不在白名单」。
    """

    def __init__(self, audit_logger: AuditLogger | None = None):
        self._audit_logger = audit_logger if audit_logger is not None else AuditLogger()

    # ------------------------------------------------------------------
    # 授权裁决
    # ------------------------------------------------------------------

    def authorize_target(self, manifest: ScopeManifest, target: str) -> ScopeDecision:
        """裁决 target 是否被 manifest 授权。缺任一硬门禁条件即拒绝。"""
        if not manifest.scope_id:
            return ScopeDecision(allowed=False, reason="未配置授权清单")

        ips = self._resolve_ips(target)
        if not ips:
            return ScopeDecision(allowed=False, reason="目标解析失败")

        if any(self._is_prohibited(ip, manifest) for ip in ips):
            return ScopeDecision(
                allowed=False,
                reason="私网/保留地址禁止",
                is_private_network=True,
            )

        if not self._in_time_window(manifest, time.time()):
            return ScopeDecision(allowed=False, reason="授权已过期")

        if any(self._ip_in_whitelist(ip, manifest.targets) for ip in ips):
            return ScopeDecision(allowed=True, reason="白名单命中")

        return ScopeDecision(allowed=False, reason="不在白名单")

    # ------------------------------------------------------------------
    # 审计
    # ------------------------------------------------------------------

    def write_audit_log(self, manifest: ScopeManifest, target: str,
                        command_hash: str) -> AuditRecord:
        """记录一次动态授权审计事件（审计不可变，交由 AuditLogger 持久化）。"""
        record = AuditRecord(
            event_type="dynamic_scope_audit",
            actor=manifest.tenant_id or manifest.signer,
            resource=target,
            details={
                "scope_id": manifest.scope_id,
                "command_hash": command_hash,
                "signer": manifest.signer,
                "reason": manifest.reason,
                "approver": manifest.approver,
            },
        )
        self._audit_logger.record(record)
        return record

    # ------------------------------------------------------------------
    # 清单序列化
    # ------------------------------------------------------------------

    def load_manifest(self, path: str | Path) -> ScopeManifest:
        """从 JSON 文件加载授权清单。

        校验（不满足即 ValueError）：JSON 必须可解析且为对象、
        scope_id 必须是非空字符串、targets 必须是非空 list。
        """
        manifest_path = Path(path)
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"授权清单 JSON 解析失败: {exc}") from exc
        if not isinstance(raw, dict):
            raise ValueError("授权清单必须是 JSON 对象")

        scope_id = raw.get("scope_id", "")
        if not isinstance(scope_id, str) or not scope_id.strip():
            raise ValueError("授权清单缺少 scope_id")

        targets = raw.get("targets")
        if not isinstance(targets, list) or not targets:
            raise ValueError("授权清单 targets 必须是非空列表")

        manifest = ScopeManifest(
            scope_id=scope_id,
            tenant_id=raw.get("tenant_id", "") or "",
            targets=[str(t) for t in targets],
            valid_from=float(raw.get("valid_from", 0.0) or 0.0),
            valid_until=float(raw.get("valid_until", 0.0) or 0.0),
            signer=raw.get("signer", "") or "",
            approver=raw.get("approver", "") or "",
            reason=raw.get("reason", "") or "",
        )
        if isinstance(raw.get("prohibited_cidrs"), list):
            manifest.prohibited_cidrs = [str(c) for c in raw["prohibited_cidrs"]]
        if isinstance(raw.get("allowed_ports"), list):
            manifest.allowed_ports = [int(p) for p in raw["allowed_ports"]]
        return manifest

    def to_json(self, manifest: ScopeManifest) -> str:
        """将授权清单序列化为 JSON 字符串（与 load_manifest 往返一致）。"""
        return json.dumps(
            {
                "scope_id": manifest.scope_id,
                "tenant_id": manifest.tenant_id,
                "targets": list(manifest.targets),
                "valid_from": manifest.valid_from,
                "valid_until": manifest.valid_until,
                "prohibited_cidrs": list(manifest.prohibited_cidrs),
                "allowed_ports": list(manifest.allowed_ports),
                "signer": manifest.signer,
                "approver": manifest.approver,
                "reason": manifest.reason,
            },
            ensure_ascii=False,
            indent=2,
        )

    # ------------------------------------------------------------------
    # 内部工具（纯函数，无网络副作用；getaddrinfo 仅本地解析）
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_ips(target: Any) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
        """把目标解析为 IP 列表；目标是 IP 直接返回，hostname 用 getaddrinfo 解析全部 IP。"""
        if not isinstance(target, str):
            return []
        try:
            return [ipaddress.ip_address(target)]
        except ValueError:
            pass
        try:
            infos = socket.getaddrinfo(target, None)
        except OSError:
            return []
        ips: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
        for info in infos:
            try:
                ips.append(ipaddress.ip_address(info[4][0]))
            except ValueError:
                continue
        return ips

    @classmethod
    def _is_prohibited(
        cls,
        ip: ipaddress.IPv4Address | ipaddress.IPv6Address,
        manifest: ScopeManifest,
    ) -> bool:
        """命中禁用 CIDR / 回环 / 链路本地 / 组播 / 未指定 / 保留地址 → True。"""
        for attr in RESERVED_ADDRESS_CHECKS:
            if getattr(ip, attr):
                return True
        for cidr in manifest.prohibited_cidrs:
            try:
                network = ipaddress.ip_network(cidr, strict=False)
            except ValueError:
                continue
            if ip in network:
                return True
        return False

    @classmethod
    def _ip_in_whitelist(
        cls,
        ip: ipaddress.IPv4Address | ipaddress.IPv6Address,
        targets: list[str],
    ) -> bool:
        """IP 是否命中 targets 白名单（支持精确 IP、CIDR 网段、hostname 条目）。"""
        for entry in targets:
            entry_s = str(entry).strip()
            try:
                addr = ipaddress.ip_address(entry_s)
            except ValueError:
                try:
                    network = ipaddress.ip_network(entry_s, strict=False)
                except ValueError:
                    # hostname 条目：解析后比对
                    if any(candidate == ip for candidate in cls._resolve_ips(entry_s)):
                        return True
                    continue
                if ip in network:
                    return True
                continue
            if ip == addr:
                return True
        return False

    @staticmethod
    def _in_time_window(manifest: ScopeManifest, now: float) -> bool:
        """当前时刻是否落在授权时间窗内；valid_until==0 视为长期授权。"""
        if manifest.valid_until == 0:
            return True  # 长期（需审批）
        return manifest.valid_from <= now <= manifest.valid_until
