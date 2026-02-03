#!/usr/bin/env python3
"""
Caching Service Adapter for AI Gateway

Provides intelligent response caching to optimize performance and reduce costs
for LLM operations. Supports multiple caching strategies and TTL management.
"""

import asyncio
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from ...application.ports.cache_port import ICacheService
from ...domain.services.llm_provider import LLMRequest, LLMResponse


@dataclass(frozen=True)
class CacheKey:
    """
    Immutable cache key for LLM requests.

    Generates deterministic keys based on request content while
    excluding non-deterministic fields like request_id and timestamps.
    """

    model_name: str
    request_type: str
    content_hash: str
    parameters_hash: str

    @classmethod
    def from_request(cls, request: LLMRequest) -> "CacheKey":
        """Generate cache key from LLM request."""
        # Create deterministic content representation
        content_data = {
            "prompt": request.prompt,
            "system_prompt": request.system_prompt,
            "request_type": request.request_type.value,
        }

        # Create deterministic parameters representation
        params_data = {
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
            "presence_penalty": request.presence_penalty,
            "frequency_penalty": request.frequency_penalty,
            "stop_sequences": (
                tuple(request.stop_sequences) if request.stop_sequences else None
            ),
        }

        # Generate hashes
        content_hash = hashlib.sha256(
            json.dumps(content_data, sort_keys=True).encode()
        ).hexdigest()[:16]

        params_hash = hashlib.sha256(
            json.dumps(params_data, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]

        return cls(
            model_name=request.model_id.model_name,
            request_type=request.request_type.value,
            content_hash=content_hash,
            parameters_hash=params_hash,
        )

    def to_string(self) -> str:
        """Convert cache key to string representation."""
        return f"{self.model_name}:{self.request_type}:{self.content_hash}:{self.parameters_hash}"


@dataclass
class CacheEntry:
    """
    Cache entry with TTL and metadata.
    """

    response: LLMResponse
    created_at: datetime
    ttl_seconds: int
    access_count: int = 0
    last_accessed: Optional[datetime] = None

    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        if self.ttl_seconds <= 0:
            return False  # Never expires

        expiry_time = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.now() > expiry_time

    def mark_accessed(self) -> None:
        """Mark entry as accessed for statistics."""
        self.access_count += 1
        self.last_accessed = datetime.now()


class InMemoryCacheService(ICacheService):
    """
    In-memory implementation of cache service.

    Provides thread-safe caching with TTL support and statistics tracking.
    Suitable for single-process applications and testing.
    """

    def __init__(self, max_entries: int = 1000):
        """
        Initialize in-memory cache.

        Args:
            max_entries: Maximum number of cache entries to maintain
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._max_entries = max_entries
        self._lock = asyncio.Lock()

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    async def get_async(self, request: LLMRequest) -> Optional[LLMResponse]:
        """Retrieve cached response with thread safety."""
        cache_key = CacheKey.from_request(request)
        key_str = cache_key.to_string()

        async with self._lock:
            entry = self._cache.get(key_str)

            if entry is None:
                self._misses += 1
                return None

            if entry.is_expired:
                # Remove expired entry
                del self._cache[key_str]
                self._misses += 1
                return None

            # Update access statistics
            entry.mark_accessed()
            self._hits += 1

            return entry.response

    async def put_async(
        self, request: LLMRequest, response: LLMResponse, ttl_seconds: int = 3600
    ) -> None:
        """Cache response with eviction policy."""
        cache_key = CacheKey.from_request(request)
        key_str = cache_key.to_string()

        async with self._lock:
            # Check if we need to evict entries
            if len(self._cache) >= self._max_entries and key_str not in self._cache:
                await self._evict_lru()

            # Create and store cache entry
            entry = CacheEntry(
                response=response, created_at=datetime.now(), ttl_seconds=ttl_seconds
            )

            self._cache[key_str] = entry

    async def invalidate_async(self, request: LLMRequest) -> bool:
        """Remove specific cache entry."""
        cache_key = CacheKey.from_request(request)
        key_str = cache_key.to_string()

        async with self._lock:
            if key_str in self._cache:
                del self._cache[key_str]
                return True
            return False

    async def clear_async(self) -> int:
        """Clear all cache entries."""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()

            # Reset statistics
            self._hits = 0
            self._misses = 0
            self._evictions = 0

            return count

    async def get_stats_async(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        async with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests) if total_requests > 0 else 0.0

            # Calculate cache health metrics
            active_entries = len(self._cache)
            expired_entries = sum(
                1 for entry in self._cache.values() if entry.is_expired
            )

            return {
                "hits": self._hits,
                "misses": self._misses,
                "total_requests": total_requests,
                "hit_rate": hit_rate,
                "evictions": self._evictions,
                "active_entries": active_entries,
                "expired_entries": expired_entries,
                "max_entries": self._max_entries,
                "utilization": (
                    active_entries / self._max_entries if self._max_entries > 0 else 0.0
                ),
            }

    async def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return

        # Find LRU entry (never accessed or oldest last_accessed)
        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_accessed or self._cache[k].created_at,
        )

        del self._cache[lru_key]
        self._evictions += 1

    async def cleanup_expired_async(self) -> int:
        """Remove all expired entries and return count removed."""
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() if entry.is_expired
            ]

            for key in expired_keys:
                del self._cache[key]

            return len(expired_keys)
