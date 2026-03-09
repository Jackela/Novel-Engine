"""In-memory metrics implementation.

Thread-safe (GIL-protected) in-memory metrics collector suitable
for single-process deployments.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from . import MetricsPublisher, MetricsSnapshot


@dataclass
class _Counters:
    """Internal mutable counter storage.

    Attributes:
        exact: Exact cache hit counter
        semantic: Semantic cache hit counter
        tool: Tool cache hit counter
        evictions: Entry eviction counter
        invalidations: Cache invalidation counter
        single_flight: Single-flight merge counter
        replays: Replay hit counter
        saved_tokens: Token savings accumulator
        saved_cost: Cost savings accumulator
        cache_size: Current cache entry count
    """

    exact: int = 0
    semantic: int = 0
    tool: int = 0
    evictions: int = 0
    invalidations: int = 0
    single_flight: int = 0
    replays: int = 0
    saved_tokens: int = 0
    saved_cost: float = 0.0
    cache_size: int = 0


class InMemoryMetrics(MetricsPublisher):
    """In-memory implementation of MetricsPublisher.

    Stores all counters in memory. Not suitable for multi-process
    deployments but efficient for single-process applications.

    Note:
        Python's GIL ensures thread-safety for counter operations.
    """

    def __init__(self) -> None:
        """Initialize in-memory metrics with zeroed counters."""
        self._c = _Counters()

    def record_hit(self, kind: str) -> None:
        """Record a cache hit by type.

        Args:
            kind: One of 'exact', 'semantic', or 'tool'
        """
        if kind == "exact":
            self._c.exact += 1
        elif kind == "semantic":
            self._c.semantic += 1
        elif kind == "tool":
            self._c.tool += 1

    def record_eviction(self, count: int = 1) -> None:
        """Record cache eviction(s).

        Args:
            count: Number of entries evicted
        """
        self._c.evictions += count

    def record_invalidation(self, count: int = 1) -> None:
        """Record cache invalidation(s).

        Args:
            count: Number of entries invalidated
        """
        self._c.invalidations += count

    def record_single_flight_merged(self, count: int = 1) -> None:
        """Record single-flight merged requests.

        Args:
            count: Number of requests merged
        """
        self._c.single_flight += count

    def record_replay_hit(self, count: int = 1) -> None:
        """Record SSE replay hits.

        Args:
            count: Number of replay hits
        """
        self._c.replays += count

    def record_savings(self, tokens: int, cost: float) -> None:
        """Record cost savings from caching.

        Args:
            tokens: Tokens saved
            cost: Estimated cost saved
        """
        self._c.saved_tokens += tokens
        self._c.saved_cost += cost

    def set_cache_size(self, size: int) -> None:
        """Update current cache size metric.

        Args:
            size: Current number of cache entries
        """
        self._c.cache_size = size

    def snapshot(self) -> MetricsSnapshot:
        """Create a snapshot of current metrics.

        Returns:
            MetricsSnapshot with all current counter values
        """
        return MetricsSnapshot(
            ts=datetime.now(UTC).isoformat(),
            cache_exact_hits=self._c.exact,
            cache_semantic_hits=self._c.semantic,
            cache_tool_hits=self._c.tool,
            cache_size=self._c.cache_size,
            evictions=self._c.evictions,
            invalidations=self._c.invalidations,
            single_flight_merged=self._c.single_flight,
            replay_hits=self._c.replays,
            saved_tokens=self._c.saved_tokens,
            saved_cost=self._c.saved_cost,
        )
