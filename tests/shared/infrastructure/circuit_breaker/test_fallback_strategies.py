"""Tests for fallback strategies."""

from __future__ import annotations

import asyncio

import pytest

from src.shared.infrastructure.fallback import (
    AlternativeServiceFallback,
    CachedFallback,
    ChainedFallback,
    NullFallback,
    RetryWithFallback,
    StaticFallback,
    with_cache_fallback,
    with_fallback,
)


class TestStaticFallback:
    """Test suite for static fallback strategy."""

    @pytest.mark.asyncio
    async def test_successful_execution(self):
        """Test that successful function execution returns result."""
        fallback_value = "fallback"
        strategy = StaticFallback(fallback_value)

        async def success_func():
            return "success"

        result = await strategy.execute(success_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_fallback_on_failure(self):
        """Test that fallback value is returned on failure."""
        fallback_value = "fallback"
        strategy = StaticFallback(fallback_value)

        async def failing_func():
            raise ValueError("Test error")

        result = await strategy.execute(failing_func)
        assert result == fallback_value

    @pytest.mark.asyncio
    async def test_fallback_with_different_types(self):
        """Test fallback with different types."""
        # Test with list
        strategy = StaticFallback([1, 2, 3])

        async def failing_func():
            raise ValueError("Test error")

        result = await strategy.execute(failing_func)
        assert result == [1, 2, 3]

        # Test with dict
        strategy = StaticFallback({"key": "value"})
        result = await strategy.execute(failing_func)
        assert result == {"key": "value"}


class TestCachedFallback:
    """Test suite for cached fallback strategy."""

    @pytest.mark.asyncio
    async def test_success_caches_result(self):
        """Test that successful result is cached."""
        cache = {}
        strategy = CachedFallback(cache, "test_key")

        async def success_func():
            return "cached_value"

        result = await strategy.execute(success_func)
        assert result == "cached_value"
        assert cache["test_key"] == "cached_value"

    @pytest.mark.asyncio
    async def test_returns_cached_on_failure(self):
        """Test that cached value is returned on failure."""
        cache = {"test_key": "cached_value"}
        strategy = CachedFallback(cache, "test_key")

        async def failing_func():
            raise ValueError("Test error")

        result = await strategy.execute(failing_func)
        assert result == "cached_value"

    @pytest.mark.asyncio
    async def test_raises_when_no_cache(self):
        """Test that exception is raised when no cache and no default."""
        cache = {}
        strategy = CachedFallback(cache, "missing_key")

        async def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await strategy.execute(failing_func)

    @pytest.mark.asyncio
    async def test_returns_default_when_no_cache(self):
        """Test that default value is returned when no cache."""
        cache = {}
        strategy = CachedFallback(cache, "missing_key", default_value="default")

        async def failing_func():
            raise ValueError("Test error")

        result = await strategy.execute(failing_func)
        assert result == "default"

    @pytest.mark.asyncio
    async def test_cache_is_updated(self):
        """Test that cache is updated on successful execution."""
        cache = {"test_key": "old_value"}
        strategy = CachedFallback(cache, "test_key")

        async def success_func():
            return "new_value"

        result = await strategy.execute(success_func)
        assert result == "new_value"
        assert cache["test_key"] == "new_value"


class TestAlternativeServiceFallback:
    """Test suite for alternative service fallback."""

    @pytest.mark.asyncio
    async def test_primary_success(self):
        """Test primary service success."""

        async def primary():
            return "primary_result"

        async def alternative():
            return "alternative_result"

        strategy = AlternativeServiceFallback(alternative)
        result = await strategy.execute(primary)
        assert result == "primary_result"

    @pytest.mark.asyncio
    async def test_fallback_to_alternative(self):
        """Test fallback to alternative service."""

        async def primary():
            raise ValueError("Primary failed")

        async def alternative():
            return "alternative_result"

        strategy = AlternativeServiceFallback(alternative)
        result = await strategy.execute(primary)
        assert result == "alternative_result"

    @pytest.mark.asyncio
    async def test_alternative_also_fails(self):
        """Test when both services fail."""

        async def primary():
            raise ValueError("Primary failed")

        async def alternative():
            raise ValueError("Alternative failed")

        strategy = AlternativeServiceFallback(alternative)

        with pytest.raises(ValueError) as exc_info:
            await strategy.execute(primary)

        assert "Alternative failed" in str(exc_info.value)


class TestRetryWithFallback:
    """Test suite for retry with fallback strategy."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Test success on first attempt."""
        fallback = StaticFallback("fallback")
        strategy = RetryWithFallback(fallback, max_retries=3, base_delay=0.01)

        async def success_func():
            return "success"

        result = await strategy.execute(success_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_success_after_retry(self):
        """Test success after retry."""
        attempt_count = 0
        fallback = StaticFallback("fallback")
        strategy = RetryWithFallback(fallback, max_retries=3, base_delay=0.01)

        async def succeeds_on_second():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ValueError("Temporary error")
            return "success"

        result = await strategy.execute(succeeds_on_second)
        assert result == "success"
        assert attempt_count == 2

    @pytest.mark.asyncio
    async def test_fallback_after_all_retries(self):
        """Test fallback after all retries exhausted."""
        fallback = StaticFallback("fallback")
        strategy = RetryWithFallback(fallback, max_retries=2, base_delay=0.01)

        async def always_fails():
            raise ValueError("Persistent error")

        result = await strategy.execute(always_fails)
        assert result == "fallback"


class TestChainedFallback:
    """Test suite for chained fallback strategy."""

    @pytest.mark.asyncio
    async def test_first_strategy_succeeds(self):
        """Test first strategy succeeds."""
        strategy1 = StaticFallback("fallback1")
        strategy2 = StaticFallback("fallback2")
        chained = ChainedFallback([strategy1, strategy2])

        async def success_func():
            return "success"

        result = await chained.execute(success_func)
        assert result == "success"


class TestNullFallback:
    """Test suite for null fallback strategy."""

    @pytest.mark.asyncio
    async def test_passes_through_success(self):
        """Test that success passes through."""
        strategy = NullFallback()

        async def success_func():
            return "success"

        result = await strategy.execute(success_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_passes_through_failure(self):
        """Test that failure passes through."""
        strategy = NullFallback()

        async def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await strategy.execute(failing_func)


class TestConvenienceFunctions:
    """Test suite for convenience functions."""

    @pytest.mark.asyncio
    async def test_with_fallback(self):
        """Test with_fallback convenience function."""

        async def failing_func():
            raise ValueError("Test error")

        result = await with_fallback(failing_func, "fallback_value")
        assert result == "fallback_value"

    @pytest.mark.asyncio
    async def test_with_fallback_success(self):
        """Test with_fallback with successful function."""

        async def success_func():
            return "success"

        result = await with_fallback(success_func, "fallback_value")
        assert result == "success"

    @pytest.mark.asyncio
    async def test_with_cache_fallback(self):
        """Test with_cache_fallback convenience function."""
        cache = {"key": "cached"}

        async def failing_func():
            raise ValueError("Test error")

        result = await with_cache_fallback(failing_func, cache, "key")
        assert result == "cached"


class TestFallbackEdgeCases:
    """Test suite for edge cases."""

    @pytest.mark.asyncio
    async def test_async_function_with_args(self):
        """Test fallback with async function that takes arguments."""
        strategy = StaticFallback("fallback")

        async def func_with_args(a: int, b: str) -> str:
            raise ValueError("Test error")

        result = await strategy.execute(func_with_args, 1, "test")
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_async_function_with_kwargs(self):
        """Test fallback with async function that takes kwargs."""
        strategy = StaticFallback("fallback")

        async def func_with_kwargs(a: int, b: str = "default") -> str:
            raise ValueError("Test error")

        result = await strategy.execute(func_with_kwargs, 1, b="test")
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_nested_exceptions(self):
        """Test handling of nested exceptions."""
        strategy = StaticFallback("fallback")

        async def deeply_failing():
            try:
                raise ValueError("Inner")
            except ValueError:
                raise RuntimeError("Outer")

        result = await strategy.execute(deeply_failing)
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_concurrent_fallback_access(self):
        """Test concurrent access to fallback strategies."""
        cache = {}
        strategy = CachedFallback(cache, "key")

        async def slow_success():
            await asyncio.sleep(0.01)
            return "success"

        # Multiple concurrent calls
        tasks = [strategy.execute(slow_success) for _ in range(5)]
        results = await asyncio.gather(*tasks)

        assert all(r == "success" for r in results)
        assert cache["key"] == "success"
