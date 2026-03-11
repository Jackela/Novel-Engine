"""Global registry for cache instances used by invalidation endpoints.

Maintains weak references to all cache instances, enabling global
invalidation operations without preventing garbage collection.
"""

from __future__ import annotations

import weakref
from typing import Any, Sequence

from src.metrics.global_metrics import metrics as global_metrics

from .exact_cache import ExactCache
from .semantic_cache_adapter import SemanticCacheBucketed

_exact_caches: "weakref.WeakSet[ExactCache]" = weakref.WeakSet()

_semantic_caches: "weakref.WeakSet[SemanticCacheBucketed]" = weakref.WeakSet()


def register_exact(cache: ExactCache) -> None:
    """Register an exact cache for global invalidation.

    Args:
        cache: ExactCache instance to register
    """
    _exact_caches.add(cache)


def register_semantic(cache: "SemanticCacheBucketed") -> None:
    """Register a semantic cache for global invalidation.

    Args:
        cache: SemanticCacheBucketed instance to register
    """
    _semantic_caches.add(cache)


def invalidate_by_tags(tags: Sequence[str]) -> int:
    """Invalidate cache entries matching any of the given tags.

    Iterates through all registered caches and removes entries
    whose metadata tags match the provided tags.

    Args:
        tags: Sequence of tags to match for invalidation

    Returns:
        Total number of entries invalidated across all caches
    """
    normalized = [t for t in tags if t]
    if not normalized:
        return 0
    removed = 0
    for cache in list(_exact_caches):
        removed += cache.invalidate(normalized)
    for cache in list(_semantic_caches):
        removed += cache.invalidate(normalized)
    if removed:
        global_metrics.record_invalidation(removed)
    return removed
