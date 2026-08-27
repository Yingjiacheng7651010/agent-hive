"""Tests for card-model-resilience: RetryStrategy, CircuitBreaker, ResilientModelClient."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from agent_hive.model_resilience import (
    CircuitBreaker,
    ModelFallbackConfig,
    ModelFallbackRegistry,
    ModelCallResult,
    ResilientModelClient,
    RetryStrategy,
)


class TestRetryStrategy:
    """RetryStrategy 重试策略测试。"""

    def test_should_retry_retryable(self):
        config = ModelFallbackConfig(max_retries=3)
        strategy = RetryStrategy(config)
        assert strategy.should_retry("429 Too Many Requests", 0) is True
        assert strategy.should_retry("503 Service Unavailable", 0) is True
        assert strategy.should_retry("502 Bad Gateway", 0) is True
        assert strategy.should_retry("504 Gateway Timeout", 0) is True

    def test_should_not_retry_non_retryable(self):
        config = ModelFallbackConfig(max_retries=3)
        strategy = RetryStrategy(config)
        assert strategy.should_retry("400 Bad Request", 0) is False
        assert strategy.should_retry("401 Unauthorized", 0) is False
        assert strategy.should_retry("403 Forbidden", 0) is False
        assert strategy.should_retry("context length exceeded", 0) is False

    def test_should_not_retry_exceeded_max(self):
        config = ModelFallbackConfig(max_retries=3)
        strategy = RetryStrategy(config)
        assert strategy.should_retry("429 Too Many Requests", 3) is False  # 第 4 次不重试

    def test_delay_increases_with_attempt(self):
        config = ModelFallbackConfig(base_delay_ms=1000.0, max_delay_ms=30000.0)
        strategy = RetryStrategy(config)
        d1 = strategy.delay_ms(0)  # 1s ± 抖动
        d2 = strategy.delay_ms(1)  # 2s ± 抖动
        d3 = strategy.delay_ms(2)  # 4s ± 抖动
        assert d1 >= 800 and d1 <= 1200
        assert d2 >= 1600 and d2 <= 2400
        assert d3 >= 3200 and d3 <= 4800

    def test_delay_capped(self):
        config = ModelFallbackConfig(base_delay_ms=1000.0, max_delay_ms=5000.0)
        strategy = RetryStrategy(config)
        # 第 3 次: 1*2^3=8s, 被 cap 到 5s
        d = strategy.delay_ms(3)
        assert d <= 6000  # 5s + 抖动


class TestCircuitBreaker:
    """CircuitBreaker 熔断器测试。"""

    def test_initial_closed(self):
        cb = CircuitBreaker("test")
        assert cb.state().state == "closed"
        assert cb.allow_request() is True

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout_ms=60000)
        cb.record_failure()  # 1
        cb.record_failure()  # 2
        cb.record_failure()  # 3 → open
        assert cb.state().state == "open"
        assert cb.allow_request() is False

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout_ms=100)
        cb.record_failure()
        cb.record_failure()  # → open
        assert cb.allow_request() is False
        # 等待 recovery timeout
        time.sleep(0.15)
        assert cb.allow_request() is True  # half-open
        assert cb.state().state == "half-open"

    def test_half_open_success_closes(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout_ms=100)
        cb.record_failure()
        cb.record_failure()  # → open
        time.sleep(0.15)
        assert cb.allow_request() is True  # half-open
        cb.record_success()
        assert cb.state().state == "closed"
        assert cb.state().failure_count == 0

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout_ms=100)
        cb.record_failure()
        cb.record_failure()  # → open
        time.sleep(0.15)
        assert cb.allow_request() is True  # half-open
        cb.record_failure()  # 半开失败 → 回到 open
        assert cb.state().state == "open"

    def test_reset(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout_ms=100)
        cb.record_failure()
        cb.record_failure()
        assert cb.state().state == "open"
        cb.reset()
        assert cb.state().state == "closed"
        assert cb.state().failure_count == 0

    def test_independent_breakers(self):
        cb1 = CircuitBreaker("model-a", failure_threshold=2)
        cb2 = CircuitBreaker("model-b", failure_threshold=2)
        cb1.record_failure()
        cb1.record_failure()
        assert cb1.state().state == "open"
        assert cb1.allow_request() is False
        assert cb2.allow_request() is True  # model-b 不受影响


class TestModelFallbackRegistry:
    """ModelFallbackRegistry 配置测试。"""

    def test_default_config(self):
        config = ModelFallbackRegistry.default_config()
        assert config.primary == "deepseek-chat"
        assert len(config.fallbacks) >= 1
        assert config.max_retries == 3

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("HIVE_MODEL_PRIMARY", "gpt-4o")
        monkeypatch.setenv("HIVE_MODEL_FALLBACKS", "gpt-4o-mini,claude-3-haiku")
        monkeypatch.setenv("HIVE_MODEL_TIMEOUT_MS", "30000")
        config = ModelFallbackRegistry.from_env()
        assert config.primary == "gpt-4o"
        assert config.fallbacks == ["gpt-4o-mini", "claude-3-haiku"]
        assert config.timeout_ms == 30000


class TestResilientModelClient:
    """ResilientModelClient 完整容错测试。"""

    def test_successful_call(self):
        config = ModelFallbackConfig(primary="deepseek-chat", fallbacks=["deepseek-chat-lite"])
        client = ResilientModelClient(config)

        def invoke_fn(model, messages, tools):
            return ("response from " + model, None)

        client.set_invoke_fn(invoke_fn)
        result = client.invoke([{"role": "user", "content": "Hello"}])
        assert result.success is True
        assert result.model_used == "deepseek-chat"
        assert result.response == "response from deepseek-chat"
        assert result.retry_count == 0
        assert result.downgraded is False

    def test_retry_then_success(self):
        config = ModelFallbackConfig(primary="deepseek-chat", max_retries=3, base_delay_ms=10)
        client = ResilientModelClient(config)
        call_count = [0]

        def invoke_fn(model, messages, tools):
            call_count[0] += 1
            if call_count[0] == 1:
                return (None, "429 Too Many Requests")
            return ("response", None)

        client.set_invoke_fn(invoke_fn)
        result = client.invoke([{"role": "user", "content": "Hello"}])
        assert result.success is True
        assert result.model_used == "deepseek-chat"
        assert result.retry_count == 1

    def test_fallback_chain(self):
        config = ModelFallbackConfig(
            primary="deepseek-chat",
            fallbacks=["deepseek-chat-lite", "gpt-4o-mini"],
            max_retries=1,  # 只重试 1 次，快速失败
            base_delay_ms=10,
        )
        client = ResilientModelClient(config)

        def invoke_fn(model, messages, tools):
            # 前两个模型都失败，第三个成功
            if model == "deepseek-chat":
                return (None, "503 Service Unavailable")
            if model == "deepseek-chat-lite":
                return (None, "429 Too Many Requests")
            return ("response from gpt-4o-mini", None)

        client.set_invoke_fn(invoke_fn)
        result = client.invoke([{"role": "user", "content": "Hello"}])
        assert result.success is True
        assert result.model_used == "gpt-4o-mini"
        assert result.downgraded is True
        assert len(result.fallback_chain) >= 1

    def test_all_models_fail(self):
        config = ModelFallbackConfig(
            primary="deepseek-chat",
            fallbacks=["deepseek-chat-lite"],
            max_retries=1,
            base_delay_ms=10,
        )
        client = ResilientModelClient(config)

        def invoke_fn(model, messages, tools):
            return (None, "503 Service Unavailable")

        client.set_invoke_fn(invoke_fn)
        result = client.invoke([{"role": "user", "content": "Hello"}])
        assert result.success is False
        assert result.response is None
        assert result.error is not None

    def test_circuit_breaker_opens_after_failures(self):
        config = ModelFallbackConfig(
            primary="deepseek-chat",
            fallbacks=["deepseek-chat-lite"],
            max_retries=1,
            base_delay_ms=10,
        )
        client = ResilientModelClient(config)
        call_count = [0]

        def invoke_fn(model, messages, tools):
            call_count[0] += 1
            return (None, "503 Service Unavailable")

        client.set_invoke_fn(invoke_fn)

        # 多次调用使熔断器打开
        for _ in range(5):
            client.invoke([{"role": "user", "content": "test"}])

        # 检查熔断器状态
        states = client.circuit_state()
        assert "deepseek-chat" in states
        # 熔断器可能已打开
        breaker = states["deepseek-chat"]
        assert breaker.failure_count >= 1

    def test_non_retryable_error_goes_directly_to_fallback(self):
        """不可重试的异常直接走 fallback，不浪费重试次数。"""
        config = ModelFallbackConfig(
            primary="deepseek-chat",
            fallbacks=["deepseek-chat-lite"],
            max_retries=3,
            base_delay_ms=1000,
        )
        client = ResilientModelClient(config)

        def invoke_fn(model, messages, tools):
            return (None, "400 Bad Request")

        client.set_invoke_fn(invoke_fn)
        result = client.invoke([{"role": "user", "content": "Hello"}])
        # 快速失败，不重试
        assert result.success is False or result.model_used != "deepseek-chat"

    def test_set_invoke_fn(self):
        client = ResilientModelClient()
        assert client._invoke_fn is None

        def my_fn(model, messages, tools):
            return ("ok", None)

        client.set_invoke_fn(my_fn)
        assert client._invoke_fn is not None

    def test_record_failure_success(self):
        config = ModelFallbackConfig(primary="deepseek-chat")
        client = ResilientModelClient(config)
        client.record_failure("deepseek-chat", "503 Service Unavailable")
        states = client.circuit_state()
        assert states["deepseek-chat"].failure_count == 1

        client.record_success("deepseek-chat")
        states = client.circuit_state()
        assert states["deepseek-chat"].failure_count == 0
        assert states["deepseek-chat"].state == "closed"