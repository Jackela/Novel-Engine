"""Lightweight semantic cache implementation used by integration tests.

Provides approximate semantic similarity caching without heavy ML dependencies.
Uses word-frequency-based cosine similarity for matching.
"""

from __future__ import annotations

import json
import math
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .interfaces import CacheEntryMeta


@dataclass
class SemanticCacheConfig:
    """Configuration for semantic cache.
    
    Attributes:
        max_cache_size: Maximum entries to store
        similarity_threshold: Minimum cosine similarity (0.0-1.0)
        persistence_file: Path for cache persistence (None = no persistence)
        ttl_seconds: Entry time-to-live in seconds
    """
    max_cache_size: int = 256
    similarity_threshold: float = 0.85
    persistence_file: Path | None = None
    ttl_seconds: int = 60 * 60


@dataclass
class _SemanticEntry:
    """Internal cache entry for semantic storage.
    
    Attributes:
        key: Lookup key
        value: Cached response value
        query_text: Original query for similarity comparison
        content_type: Content type identifier
        creation_cost: Cost to generate this entry
        created_ts: Unix timestamp of creation
        meta: Entry metadata (tags, TTL, etc.)
    """
    key: str
    value: str
    query_text: str
    content_type: str
    creation_cost: float
    created_ts: float
    meta: CacheEntryMeta = field(default_factory=CacheEntryMeta)

    def expired(self, now: float, ttl: int) -> bool:
        """Check if entry has expired.
        
        Args:
            now: Current Unix timestamp
            ttl: TTL in seconds (0 = no expiry)
            
        Returns:
            True if entry has expired
        """
        return ttl > 0 and (now - self.created_ts) >= ttl


class SemanticCache:
    """A persistence-friendly semantic cache.

    The implementation does not depend on heavyweight ML libraries.  Instead we
    approximate similarity using cosine distance over word counts which is
    sufficient for contract and integration tests.
    """

    def __init__(self, config: SemanticCacheConfig | None = None) -> None:
        self.config = config or SemanticCacheConfig()
        self._store: "OrderedDict[str, _SemanticEntry]" = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._load_cache()

    def put(
        self,
        key: str,
        value: str,
        query_text: str,
        content_type: str = "generic",
        creation_cost: float = 0.0,
        tags: Optional[Iterable[str]] = None,
    ) -> bool:
        """Store a value in the semantic cache.
        
        Args:
            key: Primary lookup key
            value: Value to cache
            query_text: Original query text for similarity matching
            content_type: Content type identifier
            creation_cost: Cost to generate this value
            tags: Optional metadata tags
            
        Returns:
            True if stored successfully
        """
        entry = _SemanticEntry(
            key=key,
            value=value,
            query_text=query_text,
            content_type=content_type,
            creation_cost=creation_cost,
            created_ts=time.time(),
            meta=CacheEntryMeta(tags=list(tags or [])),
        )
        self._store[key] = entry
        self._store.move_to_end(key)
        self._evict_if_needed()
        return True

    def get(self, key: str, query_text: str | None = None) -> Optional[str]:
        """Get a value from cache by key or semantic similarity.
        
        First attempts exact key match, then falls back to semantic
        similarity matching if query_text is provided.
        
        Args:
            key: Primary lookup key
            query_text: Optional query for semantic matching
            
        Returns:
            Cached value or None if not found
        """
        now = time.time()
        entry = self._store.get(key)
        if entry and not entry.expired(now, self.config.ttl_seconds):
            self._hits += 1
            self._store.move_to_end(key)
            return entry.value
        if query_text:
            candidate = self._find_semantic_match(query_text)
            if candidate:
                self._hits += 1
                return candidate.value
        self._misses += 1
        return None

    def get_stats(self) -> Dict[str, int | float]:
        """Get cache statistics.
        
        Returns:
            Dictionary with size, hits, and misses
        """
        return {
            "cache_size": len(self._store),
            "hit_count": self._hits,
            "miss_count": self._misses,
        }

    def save_cache(self) -> None:
        """Save cache to persistence file if configured."""
        if not self.config.persistence_file:
            return
        data = [
            {
                "key": entry.key,
                "value": entry.value,
                "query_text": entry.query_text,
                "content_type": entry.content_type,
                "creation_cost": entry.creation_cost,
                "created_ts": entry.created_ts,
                "meta": {
                    "ttl_seconds": entry.meta.ttl_seconds,
                    "tags": entry.meta.tags,
                    "sensitive": entry.meta.sensitive,
                },
            }
            for entry in self._store.values()
        ]
        self.config.persistence_file.parent.mkdir(parents=True, exist_ok=True)
        self.config.persistence_file.write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )

    def _find_semantic_match(self, query_text: str) -> Optional[_SemanticEntry]:
        """Find a semantically similar entry.
        
        Args:
            query_text: Query text to match
            
        Returns:
            Best matching entry or None
        """
        if not self._store:
            return None
        scored: List[Tuple[float, _SemanticEntry]] = []
        for entry in self._store.values():
            sim = _cosine_similarity(entry.query_text, query_text)
            if sim >= self.config.similarity_threshold:
                scored.append((sim, entry))
        if not scored:
            return None
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1]

    def _evict_if_needed(self) -> None:
        """Evict oldest entries if cache exceeds max size."""
        while len(self._store) > self.config.max_cache_size:
            self._store.popitem(last=False)

    def _load_cache(self) -> None:
        """Load cache from persistence file if configured."""
        file_path = self.config.persistence_file
        if not file_path or not file_path.exists():
            return
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            return
        now = time.time()
        for item in payload:
            entry = _SemanticEntry(
                key=item["key"],
                value=item["value"],
                query_text=item.get("query_text", ""),
                content_type=item.get("content_type", "generic"),
                creation_cost=float(item.get("creation_cost", 0.0)),
                created_ts=float(item.get("created_ts", now)),
                meta=CacheEntryMeta(tags=item.get("meta", {}).get("tags", [])),
            )
            if not entry.expired(now, self.config.ttl_seconds):
                self._store[entry.key] = entry


def _cosine_similarity(a: str, b: str) -> float:
    """Calculate cosine similarity between two strings.
    
    Uses word frequency vectors for approximation.
    
    Args:
        a: First string
        b: Second string
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not a or not b:
        return 0.0
    vec_a = _token_frequency(a)
    vec_b = _token_frequency(b)
    shared = set(vec_a) & set(vec_b)
    numerator = sum(vec_a[t] * vec_b[t] for t in shared)
    if numerator == 0:
        return 0.0
    mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return numerator / (mag_a * mag_b)


def _token_frequency(text: str) -> Dict[str, int]:
    """Calculate word frequency in text.
    
    Args:
        text: Input text
        
    Returns:
        Dictionary of lowercase word -> count
    """
    freq: Dict[str, int] = {}
    for token in text.lower().split():
        freq[token] = freq.get(token, 0) + 1
    return freq
