"""
Intelligent Caching System and Data Prefetching
===============================================

Advanced multi-layer caching system with intelligent prefetching strategies
for Novel Engine performance optimization.

Wave 5.2 - Smart Caching Infrastructure
"""

import asyncio
import hashlib
import json
import logging
import pickle
import threading
import time
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiofiles
import psutil

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """Cache hierarchy levels."""

    L1_MEMORY = "l1_memory"  # Fastest, smallest
    L2_COMPRESSED = "l2_compressed"  # Medium speed, compressed
    L3_DISK = "l3_disk"  # Slower, persistent


class CacheStrategy(Enum):
    """Cache replacement strategies."""

    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out
    ADAPTIVE = "adaptive"  # AI-driven adaptive strategy


@dataclass
class CacheEntry:
    """Cache entry with metadata."""

    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    size_bytes: int = 0
    ttl_seconds: Optional[int] = None
    cache_level: CacheLevel = CacheLevel.L1_MEMORY

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.ttl_seconds is None:
            return False
        return (datetime.now() - self.created_at).total_seconds() > self.ttl_seconds

    def touch(self):
        """Update access metadata."""
        self.last_accessed = datetime.now()
        self.access_count += 1


@dataclass
class CacheStats:
    """Cache performance statistics."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size_bytes: int = 0
    entry_count: int = 0
    hit_rate: float = 0.0

    def calculate_hit_rate(self):
        """Calculate hit rate percentage."""
        total = self.hits + self.misses
        self.hit_rate = (self.hits / total * 100) if total > 0 else 0.0


class IntelligentCache:
    """
    Multi-level intelligent cache with adaptive strategies.

    Features:
    - 3-level cache hierarchy (L1/L2/L3)
    - Multiple eviction strategies
    - TTL support
    - Compression for L2 cache
    - Async disk persistence for L3
    - AI-driven prefetching
    """

    def __init__(
        self,
        l1_max_size: int = 1000,
        l2_max_size: int = 5000,
        l3_max_size: int = 50000,
        default_ttl: int = 3600,
        strategy: CacheStrategy = CacheStrategy.ADAPTIVE,
    ):

        self.l1_max_size = l1_max_size
        self.l2_max_size = l2_max_size
        self.l3_max_size = l3_max_size
        self.default_ttl = default_ttl
        self.strategy = strategy

        # Cache storage
        self.l1_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.l2_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.l3_cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # Cache statistics
        self.l1_stats = CacheStats()
        self.l2_stats = CacheStats()
        self.l3_stats = CacheStats()

        # Thread safety
        self._lock = threading.RLock()

        # Prefetching system
        self.access_patterns = defaultdict(list)
        self.prefetch_queue = asyncio.Queue(maxsize=1000)
        self.prefetch_enabled = True
        self.prefetch_task = None

        # Background maintenance
        self._maintenance_active = True
        self._maintenance_thread = threading.Thread(
            target=self._maintenance_loop, daemon=True
        )
        self._maintenance_thread.start()

        logger.info(
            f"IntelligentCache initialized: L1={l1_max_size}, L2={l2_max_size}, L3={l3_max_size}"
        )

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with intelligent lookup across levels."""
        with self._lock:
            # Try L1 first (fastest)
            if key in self.l1_cache:
                entry = self.l1_cache[key]
                if not entry.is_expired():
                    entry.touch()
                    self.l1_stats.hits += 1
                    self._promote_to_l1(key, entry.value)
                    self._record_access_pattern(key)
                    return entry.value
                else:
                    del self.l1_cache[key]

            # Try L2 (compressed)
            if key in self.l2_cache:
                entry = self.l2_cache[key]
                if not entry.is_expired():
                    entry.touch()
                    self.l2_stats.hits += 1
                    value = self._decompress_value(entry.value)
                    self._promote_to_l1(key, value)
                    self._record_access_pattern(key)
                    return value
                else:
                    del self.l2_cache[key]

            # Try L3 (disk)
            if key in self.l3_cache:
                entry = self.l3_cache[key]
                if not entry.is_expired():
                    entry.touch()
                    self.l3_stats.hits += 1
                    value = await self._load_from_disk(key)
                    if value is not None:
                        self._promote_to_l1(key, value)
                        self._record_access_pattern(key)
                        return value
                else:
                    del self.l3_cache[key]

            # Cache miss
            self.l1_stats.misses += 1
            return None

    async def put(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store value in cache with intelligent placement."""
        try:
            ttl = ttl or self.default_ttl
            size_bytes = self._calculate_size(value)

            with self._lock:
                # Create cache entry
                entry = CacheEntry(
                    key=key,
                    value=value,
                    created_at=datetime.now(),
                    last_accessed=datetime.now(),
                    access_count=1,
                    size_bytes=size_bytes,
                    ttl_seconds=ttl,
                    cache_level=CacheLevel.L1_MEMORY,
                )

                # Store in L1 with eviction if needed
                if len(self.l1_cache) >= self.l1_max_size:
                    self._evict_from_l1()

                self.l1_cache[key] = entry
                self.l1_stats.entry_count = len(self.l1_cache)
                self.l1_stats.size_bytes += size_bytes

                # Trigger prefetching for related items
                if self.prefetch_enabled:
                    await self._trigger_prefetch(key)

                return True

        except Exception as e:
            logger.error(f"Cache put failed for key {key}: {e}")
            return False

    def _evict_from_l1(self):
        """Evict items from L1 cache using configured strategy."""
        if not self.l1_cache:
            return

        if self.strategy == CacheStrategy.LRU:
            # Remove least recently used
            key, entry = self.l1_cache.popitem(last=False)
        elif self.strategy == CacheStrategy.LFU:
            # Remove least frequently used
            min_key = min(
                self.l1_cache.keys(), key=lambda k: self.l1_cache[k].access_count
            )
            entry = self.l1_cache.pop(min_key)
            key = min_key
        elif self.strategy == CacheStrategy.FIFO:
            # Remove first inserted
            key, entry = self.l1_cache.popitem(last=False)
        else:  # ADAPTIVE
            # AI-driven adaptive eviction
            key, entry = self._adaptive_eviction()

        # Promote to L2 if valuable enough
        if entry.access_count > 1:
            self._demote_to_l2(key, entry)

        self.l1_stats.evictions += 1
        self.l1_stats.size_bytes -= entry.size_bytes
        logger.debug(f"Evicted from L1: {key} (strategy: {self.strategy.value})")

    def _adaptive_eviction(self) -> Tuple[str, CacheEntry]:
        """AI-driven adaptive eviction strategy."""
        # Score each entry based on multiple factors
        scored_entries = []

        for key, entry in self.l1_cache.items():
            # Calculate composite score
            recency_score = (datetime.now() - entry.last_accessed).total_seconds()
            frequency_score = 1.0 / max(1, entry.access_count)
            size_penalty = entry.size_bytes / 1024  # Penalize larger items

            # Pattern-based prediction
            pattern_score = self._predict_future_access(key)

            # Composite score (lower = more likely to evict)
            score = (
                recency_score * 0.4
                + frequency_score * 0.3
                + size_penalty * 0.2
                - pattern_score * 0.1
            )

            scored_entries.append((score, key, entry))

        # Sort by score and evict highest scoring (least valuable)
        scored_entries.sort(reverse=True)
        _, key, entry = scored_entries[0]

        return key, self.l1_cache.pop(key)

    def _predict_future_access(self, key: str) -> float:
        """Predict likelihood of future access based on patterns."""
        if key not in self.access_patterns:
            return 0.0

        access_times = self.access_patterns[key]
        if len(access_times) < 2:
            return 0.0

        # Calculate access intervals
        intervals = [
            access_times[i] - access_times[i - 1] for i in range(1, len(access_times))
        ]

        if not intervals:
            return 0.0

        # Predict next access based on average interval
        avg_interval = sum(intervals) / len(intervals)
        time_since_last = time.time() - access_times[-1]

        # Score based on predicted next access time
        if time_since_last < avg_interval:
            return 1.0 - (time_since_last / avg_interval)
        else:
            return 0.0

    def _demote_to_l2(self, key: str, entry: CacheEntry):
        """Demote entry from L1 to L2 with compression."""
        if len(self.l2_cache) >= self.l2_max_size:
            self._evict_from_l2()

        # Compress value for L2 storage
        compressed_value = self._compress_value(entry.value)
        entry.value = compressed_value
        entry.cache_level = CacheLevel.L2_COMPRESSED

        self.l2_cache[key] = entry
        self.l2_stats.entry_count = len(self.l2_cache)
        logger.debug(f"Demoted to L2: {key}")

    def _evict_from_l2(self):
        """Evict items from L2 cache."""
        if not self.l2_cache:
            return

        # Use LRU for L2 eviction
        key, entry = self.l2_cache.popitem(last=False)

        # Demote to L3 if still valuable
        if entry.access_count > 3:
            asyncio.create_task(self._demote_to_l3(key, entry))

        self.l2_stats.evictions += 1
        logger.debug(f"Evicted from L2: {key}")

    async def _demote_to_l3(self, key: str, entry: CacheEntry):
        """Demote entry from L2 to L3 with disk persistence."""
        if len(self.l3_cache) >= self.l3_max_size:
            self._evict_from_l3()

        # Save to disk
        await self._save_to_disk(key, entry.value)

        # Store metadata in L3 cache
        entry.cache_level = CacheLevel.L3_DISK
        self.l3_cache[key] = entry
        self.l3_stats.entry_count = len(self.l3_cache)
        logger.debug(f"Demoted to L3: {key}")

    def _evict_from_l3(self):
        """Evict items from L3 cache."""
        if not self.l3_cache:
            return

        # Use LRU for L3 eviction
        key, entry = self.l3_cache.popitem(last=False)

        # Remove from disk
        asyncio.create_task(self._remove_from_disk(key))

        self.l3_stats.evictions += 1
        logger.debug(f"Evicted from L3: {key}")

    def _promote_to_l1(self, key: str, value: Any):
        """Promote frequently accessed item to L1."""
        if len(self.l1_cache) >= self.l1_max_size:
            self._evict_from_l1()

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            access_count=1,
            size_bytes=self._calculate_size(value),
            cache_level=CacheLevel.L1_MEMORY,
        )

        self.l1_cache[key] = entry
        self.l1_stats.entry_count = len(self.l1_cache)
        logger.debug(f"Promoted to L1: {key}")

    def _record_access_pattern(self, key: str):
        """Record access pattern for predictive caching."""
        current_time = time.time()
        self.access_patterns[key].append(current_time)

        # Keep only recent access times (last 100 accesses)
        if len(self.access_patterns[key]) > 100:
            self.access_patterns[key] = self.access_patterns[key][-100:]

    async def _trigger_prefetch(self, key: str):
        """Trigger prefetching for related items."""
        try:
            # Add to prefetch queue for background processing
            await self.prefetch_queue.put(key)
        except asyncio.QueueFull:
            logger.debug("Prefetch queue full, skipping prefetch trigger")

    def _compress_value(self, value: Any) -> bytes:
        """Compress value for L2 storage."""
        try:
            import zlib

            serialized = pickle.dumps(value)
            return zlib.compress(serialized)
        except Exception as e:
            logger.warning(f"Compression failed, using raw pickle: {e}")
            return pickle.dumps(value)

    def _decompress_value(self, compressed_data: bytes) -> Any:
        """Decompress value from L2 storage."""
        try:
            import zlib

            decompressed = zlib.decompress(compressed_data)
            return pickle.loads(decompressed)
        except Exception:
            # Fallback to raw pickle
            return pickle.loads(compressed_data)

    async def _save_to_disk(self, key: str, value: Any):
        """Save value to disk for L3 storage."""
        try:
            cache_dir = Path("cache_l3")
            cache_dir.mkdir(exist_ok=True)

            filename = hashlib.md5(key.encode()).hexdigest()
            filepath = cache_dir / f"{filename}.cache"

            async with aiofiles.open(filepath, "wb") as f:
                data = pickle.dumps(value)
                await f.write(data)

        except Exception as e:
            logger.error(f"Failed to save to disk: {key} - {e}")

    async def _load_from_disk(self, key: str) -> Optional[Any]:
        """Load value from disk for L3 storage."""
        try:
            cache_dir = Path("cache_l3")
            filename = hashlib.md5(key.encode()).hexdigest()
            filepath = cache_dir / f"{filename}.cache"

            if not filepath.exists():
                return None

            async with aiofiles.open(filepath, "rb") as f:
                data = await f.read()
                return pickle.loads(data)

        except Exception as e:
            logger.error(f"Failed to load from disk: {key} - {e}")
            return None

    async def _remove_from_disk(self, key: str):
        """Remove value from disk storage."""
        try:
            cache_dir = Path("cache_l3")
            filename = hashlib.md5(key.encode()).hexdigest()
            filepath = cache_dir / f"{filename}.cache"

            if filepath.exists():
                filepath.unlink()

        except Exception as e:
            logger.error(f"Failed to remove from disk: {key} - {e}")

    def _calculate_size(self, value: Any) -> int:
        """Calculate approximate size of value in bytes."""
        try:
            return len(pickle.dumps(value))
        except Exception:
            return 1024  # Default size estimate

    def _maintenance_loop(self):
        """Background maintenance for cache cleanup and optimization."""
        while self._maintenance_active:
            try:
                with self._lock:
                    # Clean expired entries
                    self._clean_expired_entries()

                    # Update statistics
                    self._update_statistics()

                    # Optimize cache levels if needed
                    self._optimize_cache_levels()

                # Sleep for maintenance interval
                time.sleep(300)  # 5 minutes

            except Exception as e:
                logger.error(f"Cache maintenance error: {e}")
                time.sleep(60)  # Shorter sleep on error

    def _clean_expired_entries(self):
        """Remove expired entries from all cache levels."""
        datetime.now()

        # Clean L1
        expired_l1 = [key for key, entry in self.l1_cache.items() if entry.is_expired()]
        for key in expired_l1:
            entry = self.l1_cache.pop(key)
            self.l1_stats.size_bytes -= entry.size_bytes

        # Clean L2
        expired_l2 = [key for key, entry in self.l2_cache.items() if entry.is_expired()]
        for key in expired_l2:
            self.l2_cache.pop(key)

        # Clean L3
        expired_l3 = [key for key, entry in self.l3_cache.items() if entry.is_expired()]
        for key in expired_l3:
            self.l3_cache.pop(key)
            asyncio.create_task(self._remove_from_disk(key))

        if expired_l1 or expired_l2 or expired_l3:
            logger.debug(
                f"Cleaned expired entries: L1={len(expired_l1)}, "
                f"L2={len(expired_l2)}, L3={len(expired_l3)}"
            )

    def _update_statistics(self):
        """Update cache statistics."""
        self.l1_stats.entry_count = len(self.l1_cache)
        self.l1_stats.calculate_hit_rate()

        self.l2_stats.entry_count = len(self.l2_cache)
        self.l2_stats.calculate_hit_rate()

        self.l3_stats.entry_count = len(self.l3_cache)
        self.l3_stats.calculate_hit_rate()

    def _optimize_cache_levels(self):
        """Optimize cache level distributions based on access patterns."""
        # This could include dynamic resizing of cache levels
        # based on hit rates and access patterns
        pass

    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        return {
            "l1_stats": {
                "hits": self.l1_stats.hits,
                "misses": self.l1_stats.misses,
                "hit_rate": self.l1_stats.hit_rate,
                "entries": self.l1_stats.entry_count,
                "size_bytes": self.l1_stats.size_bytes,
                "evictions": self.l1_stats.evictions,
            },
            "l2_stats": {
                "hits": self.l2_stats.hits,
                "misses": self.l2_stats.misses,
                "hit_rate": self.l2_stats.hit_rate,
                "entries": self.l2_stats.entry_count,
                "evictions": self.l2_stats.evictions,
            },
            "l3_stats": {
                "hits": self.l3_stats.hits,
                "misses": self.l3_stats.misses,
                "hit_rate": self.l3_stats.hit_rate,
                "entries": self.l3_stats.entry_count,
                "evictions": self.l3_stats.evictions,
            },
            "config": {
                "l1_max_size": self.l1_max_size,
                "l2_max_size": self.l2_max_size,
                "l3_max_size": self.l3_max_size,
                "strategy": self.strategy.value,
                "default_ttl": self.default_ttl,
            },
            "patterns": {
                "tracked_keys": len(self.access_patterns),
                "prefetch_enabled": self.prefetch_enabled,
            },
        }

    async def clear_cache(self, level: Optional[CacheLevel] = None):
        """Clear cache at specified level or all levels."""
        with self._lock:
            if level is None or level == CacheLevel.L1_MEMORY:
                self.l1_cache.clear()
                self.l1_stats = CacheStats()

            if level is None or level == CacheLevel.L2_COMPRESSED:
                self.l2_cache.clear()
                self.l2_stats = CacheStats()

            if level is None or level == CacheLevel.L3_DISK:
                self.l3_cache.clear()
                self.l3_stats = CacheStats()

                # Remove all disk cache files
                cache_dir = Path("cache_l3")
                if cache_dir.exists():
                    for cache_file in cache_dir.glob("*.cache"):
                        try:
                            cache_file.unlink()
                        except Exception as e:
                            logger.error(
                                f"Failed to remove cache file {cache_file}: {e}"
                            )

    def stop(self):
        """Stop cache maintenance and cleanup."""
        self._maintenance_active = False
        if self._maintenance_thread.is_alive():
            self._maintenance_thread.join(timeout=2.0)

        if self.prefetch_task and not self.prefetch_task.done():
            self.prefetch_task.cancel()

        logger.info("IntelligentCache stopped")


class LLMResponseCache(IntelligentCache):
    """
    Specialized cache for LLM responses with intelligent key generation.

    Optimized for PersonaAgent LLM calls with context-aware caching.
    """

    def __init__(self):
        super().__init__(
            l1_max_size=500,  # Keep 500 recent LLM responses in memory
            l2_max_size=2000,  # 2000 compressed responses
            l3_max_size=10000,  # 10000 responses on disk
            default_ttl=7200,  # 2 hours TTL
            strategy=CacheStrategy.ADAPTIVE,
        )

        self.semantic_similarity_threshold = 0.8  # For fuzzy matching

    def generate_cache_key(
        self, agent_id: str, prompt: str, character_context: Dict[str, Any]
    ) -> str:
        """Generate intelligent cache key for LLM requests."""
        # Normalize prompt for better cache hits
        normalized_prompt = self._normalize_prompt(prompt)

        # Create stable hash from context
        context_hash = self._hash_context(character_context)

        # Combine into cache key
        key_data = f"{agent_id}:{normalized_prompt}:{context_hash}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _normalize_prompt(self, prompt: str) -> str:
        """Normalize prompt text for better cache hits."""
        # Remove extra whitespace
        normalized = " ".join(prompt.split())

        # Convert to lowercase for case-insensitive matching
        normalized = normalized.lower()

        # Remove common variations that don't affect meaning
        replacements = [
            ("  ", " "),
            (" .", "."),
            (" ,", ","),
            (" !", "!"),
            (" ?", "?"),
        ]

        for old, new in replacements:
            normalized = normalized.replace(old, new)

        return normalized.strip()

    def _hash_context(self, context: Dict[str, Any]) -> str:
        """Create stable hash from character context."""
        # Sort keys for stable hashing
        sorted_items = sorted(context.items())

        # Create stable string representation
        context_str = json.dumps(sorted_items, sort_keys=True, default=str)

        return hashlib.md5(context_str.encode()).hexdigest()[:8]

    async def get_similar_response(
        self, key: str, similarity_threshold: float = 0.8
    ) -> Optional[Any]:
        """
        Get similar cached response using fuzzy matching.

        This enables cache hits for slightly different but semantically similar prompts.
        """
        # First try exact match
        exact_response = await self.get(key)
        if exact_response is not None:
            return exact_response

        # Try fuzzy matching if exact match fails
        # This is a simplified approach - in production, you'd use embedding similarity
        similar_keys = self._find_similar_keys(key, similarity_threshold)

        for similar_key in similar_keys:
            response = await self.get(similar_key)
            if response is not None:
                logger.debug(
                    f"Cache hit via similarity: {key[:16]}... -> {similar_key[:16]}..."
                )
                return response

        return None

    def _find_similar_keys(self, target_key: str, threshold: float) -> List[str]:
        """Find similar cache keys using simple string similarity."""
        similar_keys = []

        # Check L1 cache for similar keys
        for cached_key in self.l1_cache.keys():
            if self._calculate_similarity(target_key, cached_key) >= threshold:
                similar_keys.append(cached_key)

        return similar_keys[:5]  # Return top 5 similar keys

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate simple string similarity (Jaccard similarity)."""
        set1 = set(str1.lower().split())
        set2 = set(str2.lower().split())

        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        return intersection / union if union > 0 else 0.0


class WorldStatePrefetcher:
    """
    Intelligent prefetching system for world state data.

    Predicts and preloads world state information based on agent behavior patterns.
    """

    def __init__(self, cache: IntelligentCache):
        self.cache = cache
        self.agent_behavior_patterns = defaultdict(dict)
        self.prefetch_enabled = True

        logger.info("WorldStatePrefetcher initialized")

    async def analyze_agent_pattern(
        self, agent_id: str, world_state_request: Dict[str, Any]
    ):
        """Analyze agent request patterns for predictive prefetching."""
        if not self.prefetch_enabled:
            return

        try:
            # Record request pattern
            pattern_key = f"agent_{agent_id}_requests"
            current_time = datetime.now()

            if pattern_key not in self.agent_behavior_patterns:
                self.agent_behavior_patterns[pattern_key] = {
                    "request_history": [],
                    "common_queries": defaultdict(int),
                    "time_patterns": [],
                }

            pattern_data = self.agent_behavior_patterns[pattern_key]

            # Record request
            pattern_data["request_history"].append(
                {"timestamp": current_time, "request": world_state_request}
            )

            # Keep only recent history
            if len(pattern_data["request_history"]) > 100:
                pattern_data["request_history"] = pattern_data["request_history"][-100:]

            # Analyze common query patterns
            query_signature = self._create_query_signature(world_state_request)
            pattern_data["common_queries"][query_signature] += 1

            # Trigger prefetching for predicted next requests
            await self._prefetch_predicted_requests(agent_id, pattern_data)

        except Exception as e:
            logger.error(f"Pattern analysis failed for {agent_id}: {e}")

    def _create_query_signature(self, request: Dict[str, Any]) -> str:
        """Create signature for world state query pattern."""
        # Extract key components of the request
        components = []

        if "turn_range" in request:
            components.append(f"turns:{request['turn_range']}")

        if "agent_filter" in request:
            components.append(f"agents:{len(request['agent_filter'])}")

        if "query_type" in request:
            components.append(f"type:{request['query_type']}")

        return "|".join(sorted(components))

    async def _prefetch_predicted_requests(
        self, agent_id: str, pattern_data: Dict[str, Any]
    ):
        """Prefetch data for predicted future requests."""
        try:
            # Analyze recent request patterns
            recent_requests = pattern_data["request_history"][-10:]  # Last 10 requests

            if len(recent_requests) < 3:
                return  # Need more data for prediction

            # Simple prediction: if agent frequently requests turn N, prefetch turn N+1
            for request_data in recent_requests:
                request = request_data["request"]

                # Predict next turn data
                if "current_turn" in request:
                    next_turn = request["current_turn"] + 1
                    prefetch_key = f"world_state_turn_{next_turn}"

                    # Check if not already cached
                    cached_value = await self.cache.get(prefetch_key)
                    if cached_value is None:
                        # Trigger background prefetch
                        asyncio.create_task(
                            self._background_prefetch(prefetch_key, request)
                        )

                # Predict related agent data
                if "requesting_agent" in request:
                    related_agents = self._predict_related_agents(
                        agent_id, pattern_data
                    )
                    for related_agent in related_agents:
                        prefetch_key = f"agent_state_{related_agent}"
                        asyncio.create_task(
                            self._background_prefetch(prefetch_key, request)
                        )

        except Exception as e:
            logger.error(f"Prefetch prediction failed for {agent_id}: {e}")

    def _predict_related_agents(
        self, agent_id: str, pattern_data: Dict[str, Any]
    ) -> List[str]:
        """Predict which other agents this agent commonly interacts with."""
        # This is a simplified prediction - in production you'd use more sophisticated ML
        related_agents = []

        # Analyze request history for agent interaction patterns
        for request_data in pattern_data["request_history"]:
            request = request_data["request"]
            if "other_agents" in request:
                related_agents.extend(request["other_agents"])

        # Return most common related agents
        from collections import Counter

        agent_counts = Counter(related_agents)
        return [agent for agent, count in agent_counts.most_common(3)]

    async def _background_prefetch(
        self, prefetch_key: str, sample_request: Dict[str, Any]
    ):
        """Background task to prefetch predicted data."""
        try:
            # This is where you'd generate the predicted data
            # For now, we'll create a placeholder
            prefetched_data = {
                "prefetched_at": datetime.now().isoformat(),
                "prediction_based_on": sample_request,
                "data_type": "predicted_world_state",
            }

            # Store in cache with shorter TTL since it's predicted data
            await self.cache.put(prefetch_key, prefetched_data, ttl=1800)  # 30 minutes

            logger.debug(f"Prefetched data for key: {prefetch_key}")

        except Exception as e:
            logger.error(f"Background prefetch failed for {prefetch_key}: {e}")


# Global cache instances
_global_llm_cache: Optional[LLMResponseCache] = None
_global_world_state_cache: Optional[IntelligentCache] = None
_global_prefetcher: Optional[WorldStatePrefetcher] = None


def get_llm_cache() -> LLMResponseCache:
    """Get or create global LLM response cache."""
    global _global_llm_cache
    if _global_llm_cache is None:
        _global_llm_cache = LLMResponseCache()
    return _global_llm_cache


def get_world_state_cache() -> IntelligentCache:
    """Get or create global world state cache."""
    global _global_world_state_cache
    if _global_world_state_cache is None:
        _global_world_state_cache = IntelligentCache(
            l1_max_size=200,
            l2_max_size=1000,
            l3_max_size=5000,
            default_ttl=1800,  # 30 minutes
            strategy=CacheStrategy.LRU,
        )
    return _global_world_state_cache


def get_world_state_prefetcher() -> WorldStatePrefetcher:
    """Get or create global world state prefetcher."""
    global _global_prefetcher
    if _global_prefetcher is None:
        _global_prefetcher = WorldStatePrefetcher(get_world_state_cache())
    return _global_prefetcher


def setup_intelligent_caching() -> Dict[str, Any]:
    """Setup comprehensive intelligent caching system."""
    llm_cache = get_llm_cache()
    world_state_cache = get_world_state_cache()
    prefetcher = get_world_state_prefetcher()

    logger.info("Intelligent caching system setup completed")

    return {
        "llm_cache": llm_cache,
        "world_state_cache": world_state_cache,
        "prefetcher": prefetcher,
        "status": "active",
    }


async def get_comprehensive_caching_report() -> Dict[str, Any]:
    """Get comprehensive report of all caching systems."""
    report = {"timestamp": datetime.now().isoformat(), "status": "active"}

    # LLM Cache stats
    if _global_llm_cache:
        report["llm_cache"] = _global_llm_cache.get_comprehensive_stats()

    # World State Cache stats
    if _global_world_state_cache:
        report["world_state_cache"] = (
            _global_world_state_cache.get_comprehensive_stats()
        )

    # System memory usage
    process = psutil.Process()
    memory_info = process.memory_info()
    report["system_memory"] = {
        "rss_mb": memory_info.rss / 1024 / 1024,
        "vms_mb": memory_info.vms / 1024 / 1024,
        "percent": process.memory_percent(),
    }

    return report


