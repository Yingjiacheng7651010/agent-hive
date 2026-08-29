"""hive-security —— AI 架构安全验证独立零依赖包（纯标准库）。

事实源模块：
- ``threat_model``：威胁目录 / 策略裁决（STRIDE 六类 + AI 三类威胁模型）
- ``arch_security``：确定性规则引擎（Shield 式检查器，validate_architecture 主入口）
- ``cli``：``hive-security scan`` 命令行入口（``def main() -> int``）

本包零运行时依赖（不依赖 pydantic / langchain），Python >= 3.11；
``__all__`` 与 agent-hive 旧模块（threat_model / arch_security）公共名完全一致。
"""
from .arch_security import *  # noqa: F401,F403
from .threat_model import *  # noqa: F401,F403
from .arch_security import __all__ as _arch_security_all
from .threat_model import __all__ as _threat_model_all

__all__ = _threat_model_all + _arch_security_all
