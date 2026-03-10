"""Bucketed semantic cache adapter used by PersonaAgent.

Organizes cache entries into buckets with configurable similarity
thresholds and keyword-based guard conditions.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, DefaultDict, Iterable, List, Optional, Sequence, Tuple


@dataclass
class _BucketEntry:
    """Entry within a semantic cache bucket.

    Attributes:
        prompt: Original prompt text
        value: Cached response
        tags: Metadata tags for invalidation
        created_ts: Creation timestamp
    """

    prompt: str
    value: str
    tags: List[str] = field(default_factory=list)
    created_ts: float = field(default_factory=time.time)


class SemanticCacheBucketed:
    """Bucketed semantic cache with similarity thresholds.

    Groups entries into named buckets (e.g., by configuration hash)
    and performs similarity matching within buckets.
    """

    def __init__(self, ttl_seconds: int = 60 * 60) -> None:
        """Initialize the bucketed cache.

        Args:
            ttl_seconds: Entry time-to-live in seconds
        """
        self.ttl_seconds = ttl_seconds
        self._buckets: DefaultDict[str, List[_BucketEntry]] = defaultdict(list)

    def put(
        self,
        bucket: str,
        prompt: str,
        response: str,
        tags: Optional[Iterable[str]] = None,
    ) -> None:
        """Store a response in a bucket.

        Args:
            bucket: Bucket identifier (e.g., config hash)
            prompt: Original prompt
            response: Response to cache
            tags: Metadata tags for invalidation
        """
        entry = _BucketEntry(prompt=prompt, value=response, tags=list(tags or []))
        bucket_entries = self._buckets[bucket]
        bucket_entries.append(entry)
        # Keep most recent entries small to avoid unbounded growth
        if len(bucket_entries) > 32:
            self._buckets[bucket] = bucket_entries[-32:]

    def query(
        self,
        bucket: str,
        prompt: str,
        high_threshold: float,
        low_threshold: float,
        keyword_overlap_min: float,
        length_delta_pct: float,
    ) -> Tuple[Optional[str], float]:
        """Query for a semantically similar cached response.

        Args:
            bucket: Bucket to search
            prompt: Query prompt
            high_threshold: Similarity threshold for immediate return
            low_threshold: Minimum similarity to consider
            keyword_overlap_min: Minimum keyword overlap ratio
            length_delta_pct: Maximum length difference percentage

        Returns:
            Tuple of (cached_response or None, similarity_score)
        """
        now = time.time()
        entries = self._buckets.get(bucket) or []
        best_score = 0.0
        best_entry: Optional[_BucketEntry] = None
        for entry in entries:
            if self.ttl_seconds and (now - entry.created_ts) > self.ttl_seconds:
                continue
            similarity = SequenceMatcher(None, entry.prompt, prompt).ratio()
            if similarity < low_threshold:
                continue
            if not _guards_pass(
                entry.prompt, prompt, keyword_overlap_min, length_delta_pct
            ):
                continue
            if similarity > best_score:
                best_score = similarity
                best_entry = entry
                if similarity >= high_threshold:
                    break
        if not best_entry:
            return None, 0.0
        return best_entry.value, best_score

    def invalidate(self, tags: Sequence[str]) -> int:
        """Invalidate entries matching all tags.

        Args:
            tags: Tags to match (all must match)

        Returns:
            Number of entries removed
        """
        if not tags:
            return 0
        tags_set = {t for t in tags if t}
        removed = 0
        for bucket, entries in list(self._buckets.items()):
            kept: list[Any] = []
            for entry in entries:
                if tags_set.issubset(set(entry.tags)):
                    removed += 1
                    continue
                kept.append(entry)
            if kept:
                self._buckets[bucket] = kept
            else:
                self._buckets.pop(bucket, None)
        return removed


def _guards_pass(
    prompt_a: str, prompt_b: str, keyword_overlap_min: float, length_delta_pct: float
) -> bool:
    """Check if two prompts pass keyword overlap and length guards.

    Args:
        prompt_a: First prompt
        prompt_b: Second prompt
        keyword_overlap_min: Minimum Jaccard overlap for keywords >3 chars
        length_delta_pct: Maximum relative length difference

    Returns:
        True if prompts pass guard conditions
    """
    if not prompt_a or not prompt_b:
        return False
    words_a = [w for w in prompt_a.lower().split() if len(w) > 3]
    words_b = [w for w in prompt_b.lower().split() if len(w) > 3]
    if not words_a or not words_b:
        return False
    overlap = len(set(words_a) & set(words_b))
    union = len(set(words_a) | set(words_b)) or 1
    if (overlap / union) < keyword_overlap_min:
        return False
    len_a = len(prompt_a)
    len_b = len(prompt_b)
    avg_len = (len_a + len_b) / 2 or 1
    if abs(len_a - len_b) / avg_len > length_delta_pct:
        return False
    return True
