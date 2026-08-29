"""威胁目录 → CWE / OWASP Top 10 for LLM（2025）标准映射。

- ``CWE_MAP``：threat_id → CWE 编号列表（[cwe.mitre.org](https://cwe.mitre.org) 复核；
  无对应 CWE 的威胁给空列表，绝不伪造编号）。
- ``OWASP_LLM_MAP``：threat_id → OWASP Top 10 for LLM 2025 编号列表
  （[genai.owasp.org](https://genai.owasp.org) 2025 版语义复核；无直接对应的给空列表）。

映射依据逐条见 README「标准映射」小节（threat_id → 编号 → 依据一句话）。
"""
from __future__ import annotations

__all__ = ["CWE_MAP", "OWASP_LLM_MAP"]

# CWE 映射：12 条内置威胁全覆盖；T-HALL-1（幻觉）无对应 CWE，如实给空列表。
CWE_MAP: dict[str, list[str]] = {
    "T-SPOOF-1": ["CWE-287"],   # Improper Authentication
    "T-SPOOF-2": ["CWE-284"],   # Improper Access Control
    "T-TAMP-1":  ["CWE-74"],    # Improper Neutralization of Special Elements in Output ('Injection')
    "T-TAMP-2":  ["CWE-78"],    # OS Command Injection
    "T-REPU-1":  ["CWE-778"],   # Insufficient Logging
    "T-DISC-1":  ["CWE-798"],   # Use of Hard-coded Credentials
    "T-DISC-2":  ["CWE-359"],   # Exposure of Private Personal Information
    "T-DOS-1":   ["CWE-400"],   # Uncontrolled Resource Consumption
    "T-ELEV-1":  ["CWE-269"],   # Improper Privilege Management
    "T-SAFE-1":  ["CWE-693"],   # Protection Mechanism Failure
    "T-PATT-1":  ["CWE-1047"],  # Modules with Circular Dependencies
    "T-HALL-1":  [],            # 幻觉（hallucination）无对应 CWE，空列表而非伪造编号
}

# OWASP Top 10 for LLM（2025）映射。
# 2025 版分类（genai.owasp.org）：LLM01 Prompt Injection / LLM02 Sensitive Information
# Disclosure / LLM03 Supply Chain / LLM04 Data and Model Poisoning / LLM05 Improper
# Output Handling / LLM06 Excessive Agency / LLM07 System Prompt Leakage / LLM08 Vector
# and Embedding Weaknesses / LLM09 Misinformation / LLM10 Unbounded Consumption。
# 认证缺失/多租户隔离/审计缺失/循环依赖在 2025 分类中无直接对应，如实给空列表。
OWASP_LLM_MAP: dict[str, list[str]] = {
    "T-TAMP-1":  ["LLM01"],   # 提示注入 ↔ Prompt Injection
    "T-DISC-1":  ["LLM02"],   # 密钥/机密泄露 ↔ Sensitive Information Disclosure
    "T-DISC-2":  ["LLM02"],   # 隐私/个人信息泄露 ↔ Sensitive Information Disclosure
    "T-SAFE-1":  ["LLM05"],   # 无输出守卫/降级 ↔ Improper Output Handling
    "T-ELEV-1":  ["LLM06"],   # 越权/最小权限缺失 ↔ Excessive Agency
    "T-HALL-1":  ["LLM09"],   # 幻觉 ↔ Misinformation
    "T-DOS-1":   ["LLM10"],   # 无限流/配额/预算耗尽 ↔ Unbounded Consumption
    "T-SPOOF-1": [],          # 认证/身份缺失：2025 分类无直接对应
    "T-SPOOF-2": [],          # 多租户隔离缺失：2025 分类无直接对应
    "T-TAMP-2":  [],          # 工具执行无白名单：属工程防护控制，2025 分类无直接对应
    "T-REPU-1":  [],          # 审计日志缺失：2025 分类无直接对应
    "T-PATT-1":  [],          # 循环依赖/结构反模式：2025 分类无直接对应
}
