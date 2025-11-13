"""Shared dataclasses and interfaces used by the caching system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Sequence


@dataclass(slots=True)
class CacheEntryMeta:
    """Metadata stored alongside cache entries.

    Only the small subset that is required by the current production code and
    tests is implemented. Additional fields can be added without affecting the
    callers because every field is optional.
    """

    ttl_seconds: int | None = None
    tags: List[str] = field(default_factory=list)
    sensitive: bool = False

    def match_tags(self, required: Sequence[str]) -> bool:
        if not required:
            return True
        entry_tags = {t for t in self.tags if t}
        return all(tag in entry_tags for tag in required)

    def with_additional_tags(self, tags: Iterable[str]) -> "CacheEntryMeta":
        merged = list(dict.fromkeys([*(self.tags or []), *(tags or [])]))
        return CacheEntryMeta(
            ttl_seconds=self.ttl_seconds,
            tags=merged,
            sensitive=self.sensitive,
        )
