"""hive-cost —— 成本控制与模型容错独立零依赖包（纯标准库）。

事实源模块：
- ``budget``：成本预算原语（CostBudget/CostSnapshot/CostAlert/BudgetDecision/
  TokenEstimator/CostTracker/CostController/MODEL_PRICING）
- ``resilience``：模型调用容错（ModelFallbackConfig/CircuitBreakerState/
  ModelCallResult/RetryStrategy/CircuitBreaker/ResilientModelClient/
  ModelFallbackRegistry）
- ``gate``：CostGate 一等原语（检查 → 记录 → OTel 事件）
- ``otel``：export_cost_otel_jsonl（OTel 兼容 JSONL 导出）

本包零运行时依赖（不依赖 pydantic / langchain / opentelemetry SDK），
Python >= 3.11；``__all__`` 覆盖 agent-hive 旧模块（cost_control /
model_resilience）全部公共名，并追加新公共名 CostGate 与 export_cost_otel_jsonl。
"""
from .budget import *  # noqa: F401,F403
from .resilience import *  # noqa: F401,F403
from .gate import CostGate  # noqa: F401
from .otel import export_cost_otel_jsonl  # noqa: F401
from .budget import __all__ as _budget_all
from .resilience import __all__ as _resilience_all
from .gate import __all__ as _gate_all
from .otel import __all__ as _otel_all

__all__ = _budget_all + _resilience_all + _gate_all + _otel_all
