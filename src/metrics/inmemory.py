from dataclasses import dataclass
from datetime import UTC, datetime

from . import MetricsPublisher, MetricsSnapshot


@dataclass
class _Counters:
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
    def __init__(self) -> None:
        self._c = _Counters()

    def record_hit(self, kind: str) -> None:
        if kind == "exact":
            self._c.exact += 1
        elif kind == "semantic":
            self._c.semantic += 1
        elif kind == "tool":
            self._c.tool += 1

    def record_eviction(self, count: int = 1) -> None:
        self._c.evictions += count

    def record_invalidation(self, count: int = 1) -> None:
        self._c.invalidations += count

    def record_single_flight_merged(self, count: int = 1) -> None:
        self._c.single_flight += count

    def record_replay_hit(self, count: int = 1) -> None:
        self._c.replays += count

    def record_savings(self, tokens: int, cost: float) -> None:
        self._c.saved_tokens += tokens
        self._c.saved_cost += cost

    def set_cache_size(self, size: int) -> None:
        self._c.cache_size = size

    def snapshot(self) -> MetricsSnapshot:
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
