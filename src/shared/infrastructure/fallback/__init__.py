"""Fallback strategies for service degradation."""

from src.shared.infrastructure.fallback.fallback_strategy import (
    AlternativeServiceFallback,
    CachedFallback,
    ChainedFallback,
    FallbackStrategy,
    NullFallback,
    RetryWithFallback,
    StaticFallback,
    with_cache_fallback,
    with_fallback,
)

__all__ = [
    # Base class
    "FallbackStrategy",
    # Strategies
    "StaticFallback",
    "CachedFallback",
    "AlternativeServiceFallback",
    "ChainedFallback",
    "RetryWithFallback",
    "NullFallback",
    # Convenience functions
    "with_fallback",
    "with_cache_fallback",
]
