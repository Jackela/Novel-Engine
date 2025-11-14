"""Caching subsystem exports for Novel Engine.

This module intentionally keeps the public surface area extremely small so the
rest of the codebase can rely on semantic caching, state hashing, and token
budget primitives without needing to know the underlying modules.
"""

from .interfaces import CacheEntryMeta
from .semantic_cache import SemanticCache, SemanticCacheConfig
from .state_hasher import HashingConfig, StateHasher
from .token_budget import (
    BudgetLimit,
    BudgetPeriod,
    OperationType,
    TokenBudgetConfig,
    TokenBudgetManager,
)

__all__ = [
    "HashingConfig",
    "StateHasher",
    "BudgetLimit",
    "BudgetPeriod",
    "OperationType",
    "TokenBudgetConfig",
    "TokenBudgetManager",
    "SemanticCache",
    "SemanticCacheConfig",
    "CacheEntryMeta",
]
