from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict


@dataclass
class MetricsSnapshot:
    ts: str
    cache_exact_hits: int
    cache_semantic_hits: int
    cache_tool_hits: int
    cache_size: int
    evictions: int
    invalidations: int
    single_flight_merged: int
    replay_hits: int
    saved_tokens: int
    saved_cost: float

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


class MetricsPublisher:
    def record_hit(self, kind: str) -> None:
        raise NotImplementedError

    def record_eviction(self, count: int = 1) -> None:
        raise NotImplementedError

    def record_invalidation(self, count: int = 1) -> None:
        raise NotImplementedError

    def record_single_flight_merged(self, count: int = 1) -> None:
        raise NotImplementedError

    def record_replay_hit(self, count: int = 1) -> None:
        raise NotImplementedError

    def record_savings(self, tokens: int, cost: float) -> None:
        raise NotImplementedError

    def snapshot(self) -> MetricsSnapshot:
        raise NotImplementedError
