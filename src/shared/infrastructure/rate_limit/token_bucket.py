"""Lightweight in-memory token-bucket rate limiter.

This module provides a minimal, dependency-free rate limiter suitable for
single-node deployments. It is intentionally simple: keys live in memory only
and are not shared across processes.
"""

from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimit:
    """Parsed rate-limit specification."""

    limit: int
    window_seconds: float


_RATE_LIMIT_RE = re.compile(
    r"^(?P<limit>\d+)\s*/\s*"
    r"(?P<unit>s|sec|second|seconds|m|min|minute|minutes|"
    r"h|hr|hour|hours|d|day|days)$",
    re.IGNORECASE,
)

_UNIT_SECONDS: dict[str, float] = {
    "s": 1.0,
    "sec": 1.0,
    "second": 1.0,
    "seconds": 1.0,
    "m": 60.0,
    "min": 60.0,
    "minute": 60.0,
    "minutes": 60.0,
    "h": 3600.0,
    "hr": 3600.0,
    "hour": 3600.0,
    "hours": 3600.0,
    "d": 86400.0,
    "day": 86400.0,
    "days": 86400.0,
}


def parse_rate_limit(value: str) -> RateLimit:
    """Parse a human-readable rate limit string.

    Supported formats::

        5/minute
        10/second
        2/h
        1/day
        5 / min

    Args:
        value: The rate limit string to parse.

    Returns:
        A ``RateLimit`` value object.

    Raises:
        ValueError: If the value is not a supported rate limit string.
    """
    stripped = value.strip()
    match = _RATE_LIMIT_RE.match(stripped)
    if not match:
        raise ValueError(f"Invalid rate limit format: {stripped!r}")
    limit = int(match.group("limit"))
    if limit < 1:
        raise ValueError(f"Rate limit must be positive: {stripped!r}")
    unit = match.group("unit").lower()
    return RateLimit(limit=limit, window_seconds=_UNIT_SECONDS[unit])


class TokenBucketRateLimiter:
    """In-memory token-bucket rate limiter.

    Each key receives its own bucket. Requests are allowed while the bucket
    contains at least one token; otherwise they are rejected. Tokens refill
    continuously at the configured rate up to ``capacity``.

    Keys are expired and removed after ``key_ttl_seconds`` of inactivity to
    avoid unbounded memory growth. Per-key locks isolate different clients so
    that contention for one key does not serialize requests for others.
    """

    def __init__(
        self,
        *,
        rate: float,
        capacity: int,
        key_ttl_seconds: float = 3600.0,
        clock: Callable[[], float] = time.monotonic,
        cleanup_interval: int = 100,
    ) -> None:
        """Initialize the limiter.

        Args:
            rate: Tokens added per second.
            capacity: Maximum number of tokens a bucket can hold.
            key_ttl_seconds: Time after which an idle key is removed.
            clock: Callable returning the current monotonic time.
            cleanup_interval: Number of ``is_allowed`` calls between cleanups.
        """
        if rate <= 0:
            raise ValueError("rate must be positive")
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        if key_ttl_seconds <= 0:
            raise ValueError("key_ttl_seconds must be positive")
        self.rate = rate
        self.capacity = capacity
        self.key_ttl_seconds = key_ttl_seconds
        self.clock = clock
        self._cleanup_interval = cleanup_interval
        self._tokens: dict[str, float] = {}
        self._last_update: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._cleanup_lock = asyncio.Lock()
        self._calls = 0

    async def is_allowed(self, key: str) -> bool:
        """Return ``True`` if the request for ``key`` is within the limit."""
        now = self.clock()
        self._calls += 1
        if self._calls % self._cleanup_interval == 0:
            await self.cleanup_expired()

        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            tokens = self._tokens.get(key, float(self.capacity))
            last = self._last_update.get(key, now)
            tokens = min(float(self.capacity), tokens + (now - last) * self.rate)
            self._last_update[key] = now
            if tokens >= 1.0:
                self._tokens[key] = tokens - 1.0
                return True
            self._tokens[key] = tokens
            return False

    def retry_after(self, key: str) -> float:
        """Return the seconds until ``key`` will have at least one token.

        Returns ``0.0`` if the key currently has enough tokens.
        """
        now = self.clock()
        tokens = self._tokens.get(key, float(self.capacity))
        last = self._last_update.get(key, now)
        tokens = min(float(self.capacity), tokens + (now - last) * self.rate)
        if tokens >= 1.0:
            return 0.0
        return (1.0 - tokens) / self.rate

    async def cleanup_expired(self) -> None:
        """Remove keys that have not been updated within ``key_ttl_seconds``."""
        async with self._cleanup_lock:
            now = self.clock()
            expired = [
                k
                for k, last in self._last_update.items()
                if now - last > self.key_ttl_seconds
            ]
            for k in expired:
                self._tokens.pop(k, None)
                self._last_update.pop(k, None)
