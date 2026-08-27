"""模型调用容错 —— Retry + Exponential Backoff → Circuit Breaker → Fallback 链。

架构：
- RetryStrategy：指数退避 + 抖动，区分可重试/不可重试异常
- CircuitBreaker：每个模型端点独立熔断（closed → open → half-open）
- ModelFallbackRegistry：按优先级配置 fallback 链
- ResilientModelClient：统一入口，集成 retry + circuit breaker + fallback

验收标准：
- 主模型 429 时自动重试最多 3 次，指数退避+抖动
- 连续 5 次失败后熔断器打开，后续请求直接走 fallback
- 熔断器 30s 后 half-open，成功一次恢复，失败一次重置
- 所有模型都失败时返回失败结果，不抛异常崩溃整个 run
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

__all__ = [
    "ModelFallbackConfig",
    "CircuitBreakerState",
    "ModelCallResult",
    "ResilientModelClient",
    "ModelFallbackRegistry",
    "RetryStrategy",
    "CircuitBreaker",
]

# ---------------------------------------------------------------------------
# 可重试的 HTTP 状态码
# ---------------------------------------------------------------------------
RETRYABLE_STATUS_CODES = {429, 502, 503, 504}

# 不可重试的异常关键字（匹配 error 字符串）
NON_RETRYABLE_KEYWORDS = [
    "400", "bad request",
    "401", "unauthorized",
    "403", "forbidden",
    "context length exceeded",
    "context_length_exceeded",
]


def _is_retryable(error: str) -> bool:
    """判断错误是否可重试。"""
    lower = error.lower()
    for kw in NON_RETRYABLE_KEYWORDS:
        if kw in lower:
            return False
    return True


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class ModelFallbackConfig:
    """模型 fallback 链配置。"""
    primary: str = "deepseek-chat"
    fallbacks: list[str] = field(default_factory=lambda: ["deepseek-chat-lite", "gpt-4o-mini"])
    timeout_ms: int = 60000
    max_retries: int = 3
    base_delay_ms: float = 1000.0
    max_delay_ms: float = 30000.0


@dataclass
class CircuitBreakerState:
    """熔断器状态。"""
    name: str
    state: Literal["closed", "open", "half-open"] = "closed"
    failure_count: int = 0
    last_failure_time: float = 0.0
    failure_threshold: int = 5
    recovery_timeout_ms: int = 30000


@dataclass
class ModelCallResult:
    """模型调用结果（成功或失败，含 fallback 链路追踪）。"""
    success: bool
    response: str | None
    model_used: str
    total_latency_ms: float
    retry_count: int
    fallback_chain: list[str]
    error: str | None = None
    downgraded: bool = False


# ---------------------------------------------------------------------------
# RetryStrategy
# ---------------------------------------------------------------------------

class RetryStrategy:
    """重试策略：指数退避 + 抖动。"""

    def __init__(self, config: ModelFallbackConfig):
        self._config = config

    def should_retry(self, error: str, attempt: int) -> bool:
        """判断是否应该重试。"""
        if attempt >= self._config.max_retries:
            return False
        return _is_retryable(error)

    def delay_ms(self, attempt: int) -> float:
        """计算第 attempt 次重试前的等待时间（毫秒）。"""
        base = self._config.base_delay_ms * (2 ** attempt)
        capped = min(base, self._config.max_delay_ms)
        # 添加 ±20% 抖动
        jitter = capped * 0.2
        return capped + random.uniform(-jitter, jitter)


# ---------------------------------------------------------------------------
# CircuitBreaker
# ---------------------------------------------------------------------------

class CircuitBreaker:
    """熔断器：每个模型/端点独立实例。"""

    def __init__(self, name: str, failure_threshold: int = 5, recovery_timeout_ms: int = 30000):
        self._state = CircuitBreakerState(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout_ms=recovery_timeout_ms,
        )

    def state(self) -> CircuitBreakerState:
        return self._state

    def allow_request(self) -> bool:
        """判断是否允许请求通过。"""
        if self._state.state == "closed":
            return True

        if self._state.state == "open":
            # 检查是否到了 half-open 的时间
            elapsed = (time.time() - self._state.last_failure_time) * 1000
            if elapsed >= self._state.recovery_timeout_ms:
                self._state.state = "half-open"
                return True
            return False

        # half-open: 允许一个试探请求
        return True

    def record_success(self):
        """记录成功，复位熔断器。"""
        self._state.state = "closed"
        self._state.failure_count = 0
        self._state.last_failure_time = 0.0

    def record_failure(self):
        """记录失败。"""
        self._state.failure_count += 1
        self._state.last_failure_time = time.time()

        if self._state.state == "half-open":
            # half-open 状态失败 → 立即回到 open
            self._state.state = "open"
            return

        if self._state.failure_count >= self._state.failure_threshold:
            self._state.state = "open"

    def reset(self):
        """手动复位。"""
        self._state.state = "closed"
        self._state.failure_count = 0
        self._state.last_failure_time = 0.0


# ---------------------------------------------------------------------------
# ModelFallbackRegistry
# ---------------------------------------------------------------------------

class ModelFallbackRegistry:
    """模型 fallback 链注册表，支持动态配置。"""

    @classmethod
    def default_config(cls) -> ModelFallbackConfig:
        return ModelFallbackConfig(
            primary="deepseek-chat",
            fallbacks=["deepseek-chat-lite", "gpt-4o-mini"],
        )

    @classmethod
    def from_env(cls) -> ModelFallbackConfig:
        """从环境变量读取配置。"""
        import os
        primary = os.environ.get("HIVE_MODEL_PRIMARY", "deepseek-chat")
        fallbacks_str = os.environ.get("HIVE_MODEL_FALLBACKS", "deepseek-chat-lite,gpt-4o-mini")
        fallbacks = [m.strip() for m in fallbacks_str.split(",") if m.strip()]
        timeout_ms = int(os.environ.get("HIVE_MODEL_TIMEOUT_MS", "60000"))
        return ModelFallbackConfig(
            primary=primary,
            fallbacks=fallbacks,
            timeout_ms=timeout_ms,
        )


# ---------------------------------------------------------------------------
# ResilientModelClient
# ---------------------------------------------------------------------------

class ResilientModelClient:
    """带容错的模型客户端：retry → circuit breaker → fallback。

    使用方式：
        client = ResilientModelClient(config)
        result = client.invoke(messages, tools)
        if not result.success:
            # 处理失败，但不崩溃
            ...
    """

    def __init__(
        self,
        config: ModelFallbackConfig | None = None,
        invoke_fn: Callable | None = None,
    ):
        """
        Args:
            config: fallback 链配置。None 时使用默认配置。
            invoke_fn: 实际的模型调用函数。signature: (model, messages, tools) -> (response, error)
                None 时使用默认的 LLM 调用（需后续 set_invoke_fn）。
        """
        self._config = config or ModelFallbackRegistry.default_config()
        self._invoke_fn = invoke_fn
        self._retry = RetryStrategy(self._config)
        self._breakers: dict[str, CircuitBreaker] = {}

    def set_invoke_fn(self, fn: Callable):
        """设置模型调用函数。

        签名: fn(model: str, messages: list, tools: list | None) -> (response: str | None, error: str | None)
        """
        self._invoke_fn = fn

    def _get_breaker(self, model: str) -> CircuitBreaker:
        if model not in self._breakers:
            self._breakers[model] = CircuitBreaker(
                name=model,
                failure_threshold=self._config.max_retries + 2,  # 连续失败超过重试次数+2 才熔断
                recovery_timeout_ms=self._config.recovery_timeout_ms
                if hasattr(self._config, 'recovery_timeout_ms')
                else 30000,
            )
        return self._breakers[model]

    def invoke(
        self,
        messages: list,
        tools: list | None = None,
    ) -> ModelCallResult:
        """带容错的模型调用。"""
        start_time = time.time()
        models_to_try = [self._config.primary] + list(self._config.fallbacks)
        fallback_chain: list[str] = []
        total_retries = 0

        for model in models_to_try:
            breaker = self._get_breaker(model)

            # 检查熔断器
            if not breaker.allow_request():
                fallback_chain.append(f"{model}(熔断)")
                continue

            # 尝试调用（带重试）
            for attempt in range(self._config.max_retries + 1):
                try:
                    if self._invoke_fn is None:
                        raise RuntimeError("invoke_fn not set")

                    response, error = self._invoke_fn(model, messages, tools)

                    if error is None and response is not None:
                        # 成功
                        breaker.record_success()
                        elapsed = (time.time() - start_time) * 1000
                        fallback_chain.append(model)
                        return ModelCallResult(
                            success=True,
                            response=response,
                            model_used=model,
                            total_latency_ms=elapsed,
                            retry_count=total_retries,
                            fallback_chain=fallback_chain,
                            downgraded=(model != self._config.primary),
                        )

                    # 有错误
                    breaker.record_failure()
                    total_retries += 1

                    if not self._retry.should_retry(error or "", attempt):
                        break  # 不可重试，换 fallback

                    # 等待后重试
                    delay = self._retry.delay_ms(attempt) / 1000
                    time.sleep(delay)

                except Exception as e:
                    error_str = str(e)
                    breaker.record_failure()
                    total_retries += 1
                    if not self._retry.should_retry(error_str, attempt):
                        break
                    delay = self._retry.delay_ms(attempt) / 1000
                    time.sleep(delay)

            fallback_chain.append(f"{model}(失败)")

        # 全部失败
        elapsed = (time.time() - start_time) * 1000
        return ModelCallResult(
            success=False,
            response=None,
            model_used=models_to_try[-1],
            total_latency_ms=elapsed,
            retry_count=total_retries,
            fallback_chain=fallback_chain,
            error=f"所有模型调用失败: {' → '.join(fallback_chain)}",
        )

    def record_failure(self, model: str, error: str):
        """记录一次失败，更新 circuit breaker 状态。"""
        breaker = self._get_breaker(model)
        breaker.record_failure()

    def record_success(self, model: str):
        """记录一次成功，复位 circuit breaker。"""
        breaker = self._get_breaker(model)
        breaker.record_success()

    def circuit_state(self) -> dict[str, CircuitBreakerState]:
        """返回所有熔断器状态。"""
        return {name: cb.state() for name, cb in self._breakers.items()}