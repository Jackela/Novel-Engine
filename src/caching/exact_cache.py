"""Simple in-memory exact cache with tag-based invalidation."""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from typing import Dict, Optional, Sequence

from .interfaces import CacheEntryMeta


@dataclass(slots=True)
class _CacheEntry:
    """Internal cache entry.

    Attributes:
        value: Cached value
        created_ts: Creation timestamp
        meta: Entry metadata
        ttl_seconds: Time-to-live (None = no expiry)
    """

    value: str
    created_ts: float
    meta: CacheEntryMeta
    ttl_seconds: int | None

    def is_expired(self, now: float) -> bool:
        """Check if entry has expired.

        Args:
            now: Current timestamp

        Returns:
            True if expired
        """
        if self.ttl_seconds is None:
            return False
        return (now - self.created_ts) >= self.ttl_seconds


class ExactCache:
    """Thread-safe LRU cache with optional TTL and tag metadata."""

    def __init__(
        self, max_size: int = 512, default_ttl_seconds: int | None = 3600
    ) -> None:
        """Initialize exact cache.

        Args:
            max_size: Maximum entries to store
            default_ttl_seconds: Default TTL (None = no expiry)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl_seconds
        self._store: "OrderedDict[str, _CacheEntry]" = OrderedDict()
        self._lock = RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[str]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        now = time.time()
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                self._misses += 1
                return None
            if entry.is_expired(now):
                self._store.pop(key, None)
                self._misses += 1
                return None
            self._store.move_to_end(key)
            self._hits += 1
            return entry.value

    def put(
        self,
        key: str,
        value: str,
        meta: CacheEntryMeta | None = None,
        ttl_seconds: int | None = None,
    ) -> None:
        """Store a value in cache.

        Args:
            key: Cache key
            value: Value to store
            meta: Optional metadata
            ttl_seconds: Optional TTL override
        """
        with self._lock:
            entry = _CacheEntry(
                value=value,
                created_ts=time.time(),
                meta=meta or CacheEntryMeta(),
                ttl_seconds=(
                    ttl_seconds if ttl_seconds is not None else self.default_ttl
                ),
            )
            self._store[key] = entry
            self._store.move_to_end(key)
            self._evict_if_needed()

    def invalidate(self, tags: Sequence[str]) -> int:
        """Invalidate entries matching any tag.

        Args:
            tags: Tags to match

        Returns:
            Number of entries removed
        """
        if not tags:
            return 0
        removed = 0
        tags_set = {t for t in tags if t}
        if not tags_set:
            return 0
        with self._lock:
            keys_to_remove = [
                key
                for key, entry in self._store.items()
                if entry.meta.match_tags(tags_set)
            ]
            for key in keys_to_remove:
                self._store.pop(key, None)
                removed += 1
        return removed

    def clear(self) -> None:
        """Clear all entries from cache."""
        with self._lock:
            self._store.clear()

    def stats(self) -> Dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with size, hits, misses
        """
        with self._lock:
            return {
                "size": len(self._store),
                "hits": self._hits,
                "misses": self._misses,
            }

    def _evict_if_needed(self) -> None:
        """Evict oldest entries if cache is full."""
        with self._lock:
            while len(self._store) > self.max_size:
                self._store.popitem(last=False)
