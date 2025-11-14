"""Bucketed semantic cache adapter used by PersonaAgent."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import DefaultDict, Iterable, List, Optional, Sequence, Tuple


@dataclass
class _BucketEntry:
    prompt: str
    value: str
    tags: List[str] = field(default_factory=list)
    created_ts: float = field(default_factory=time.time)


class SemanticCacheBucketed:
    def __init__(self, ttl_seconds: int = 60 * 60):
        self.ttl_seconds = ttl_seconds
        self._buckets: DefaultDict[str, List[_BucketEntry]] = defaultdict(list)

    def put(
        self,
        bucket: str,
        prompt: str,
        response: str,
        tags: Optional[Iterable[str]] = None,
    ) -> None:
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
        now = time.time()
        entries = self._buckets.get(bucket) or []
        best: Tuple[float, Optional[_BucketEntry]] = (0.0, None)
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
            if similarity > best[0]:
                best = (similarity, entry)
                if similarity >= high_threshold:
                    break
        entry = best[1]
        if not entry:
            return None, 0.0
        return entry.value, best[0]

    def invalidate(self, tags: Sequence[str]) -> int:
        if not tags:
            return 0
        tags_set = {t for t in tags if t}
        removed = 0
        for bucket, entries in list(self._buckets.items()):
            kept = []
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
