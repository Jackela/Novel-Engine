"""Fallback strategies for service degradation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Generic, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class FallbackStrategy(ABC, Generic[T]):
    """Base class for fallback strategies."""

    @abstractmethod
    async def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute function with fallback."""
        raise NotImplementedError


class StaticFallback(FallbackStrategy[T]):
    """Return static value on failure."""

    def __init__(self, fallback_value: T):
        self.fallback_value = fallback_value

    async def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.warning(
                "Function failed, returning static fallback",
                error=str(e),
                fallback_type=type(self.fallback_value).__name__,
            )
            return self.fallback_value


class CachedFallback(FallbackStrategy[T]):
    """Return cached value on failure."""

    def __init__(
        self,
        cache: dict[str, Any],
        cache_key: str,
        default_value: T | None = None,
    ):
        self.cache = cache
        self.cache_key = cache_key
        self.default_value = default_value

    async def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        try:
            result = await func(*args, **kwargs)
            # Update cache
            self.cache[self.cache_key] = result
            return result
        except Exception as e:
            logger.warning(
                "Function failed, returning cached fallback",
                error=str(e),
                cache_key=self.cache_key,
                has_cache=self.cache_key in self.cache,
            )
            if self.cache_key in self.cache:
                return self.cache[self.cache_key]
            if self.default_value is not None:
                return self.default_value
            raise


class AlternativeServiceFallback(FallbackStrategy[T]):
    """Try alternative service on failure."""

    def __init__(
        self,
        alternative_func: Callable[..., T],
        fallback_on_alternative_error: bool = True,
    ):
        self.alternative_func = alternative_func
        self.fallback_on_alternative_error = fallback_on_alternative_error

    async def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.warning(
                "Primary service failed, trying alternative",
                error=str(e),
            )
            try:
                return await self.alternative_func(*args, **kwargs)
            except Exception as alt_e:
                if not self.fallback_on_alternative_error:
                    raise
                logger.error(
                    "Alternative service also failed",
                    error=str(alt_e),
                )
                raise


class ChainedFallback(FallbackStrategy[T]):
    """Try multiple fallback strategies in sequence."""

    def __init__(self, strategies: list[FallbackStrategy[T]]):
        self.strategies = strategies

    async def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        last_error: Exception | None = None

        for i, strategy in enumerate(self.strategies):
            try:
                if i == 0:
                    # First strategy wraps the original function
                    return await strategy.execute(func, *args, **kwargs)
                else:
                    # Subsequent strategies wrap the previous fallback
                    return await strategy.execute(
                        lambda *a, **kw: self._raise_last_error(last_error),  # type: ignore
                    )
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Fallback strategy {i} failed",
                    strategy_type=type(strategy).__name__,
                    error=str(e),
                )

        if last_error:
            raise last_error
        raise RuntimeError("All fallback strategies failed")

    def _raise_last_error(self, error: Exception | None) -> None:
        """Helper to raise the last error."""
        if error:
            raise error
        raise RuntimeError("No error to raise")


class RetryWithFallback(FallbackStrategy[T]):
    """Retry with exponential backoff, then fallback."""

    def __init__(
        self,
        fallback_strategy: FallbackStrategy[T],
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
    ):
        self.fallback_strategy = fallback_strategy
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    async def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        import asyncio

        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = min(
                        self.base_delay * (self.exponential_base**attempt),
                        self.max_delay,
                    )
                    logger.warning(
                        f"Attempt {attempt + 1} failed, retrying in {delay}s",
                        error=str(e),
                    )
                    await asyncio.sleep(delay)

        # All retries exhausted, use fallback
        logger.error(
            f"All {self.max_retries} retries failed, using fallback",
            error=str(last_error),
        )
        return await self.fallback_strategy.execute(
            lambda *a, **kw: self._raise_last_error(last_error)  # type: ignore
        )

    def _raise_last_error(self, error: Exception | None) -> None:
        """Helper to raise the last error."""
        if error:
            raise error
        raise RuntimeError("All retries exhausted")


class NullFallback(FallbackStrategy[T]):
    """No fallback, just raises the exception."""

    async def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        return await func(*args, **kwargs)


# Convenience function for common fallback patterns
async def with_fallback(
    func: Callable[..., T],
    fallback_value: T,
    *args: Any,
    **kwargs: Any,
) -> T:
    """Execute function with static fallback value."""
    strategy: StaticFallback[T] = StaticFallback(fallback_value)
    return await strategy.execute(func, *args, **kwargs)


async def with_cache_fallback(
    func: Callable[..., T],
    cache: dict[str, Any],
    cache_key: str,
    default_value: T | None = None,
    *args: Any,
    **kwargs: Any,
) -> T:
    """Execute function with cached fallback."""
    strategy: CachedFallback[T] = CachedFallback(cache, cache_key, default_value)
    return await strategy.execute(func, *args, **kwargs)
