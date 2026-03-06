"""Tests for Semantic Cache module.

Tests cover:
- Store and retrieve by key
- Cache hit with similarity threshold
- Cache miss when below threshold
- Cache stats tracking
- TTL expiration
- Persistence (save/load)
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Generator

import pytest

pytestmark = pytest.mark.unit

from src.caching.semantic_cache import (
    SemanticCache,
    SemanticCacheConfig,
    _SemanticEntry,
    _cosine_similarity,
    _token_frequency,
)
from src.caching.interfaces import CacheEntryMeta


@pytest.fixture
def temp_cache_file(tmp_path: Path) -> Path:
    """Create a temporary cache file path."""
    return tmp_path / "test_cache.json"


@pytest.fixture
def semantic_cache() -> SemanticCache:
    """Create a semantic cache with default config."""
    return SemanticCache()


@pytest.fixture
def semantic_cache_with_persistence(temp_cache_file: Path) -> SemanticCache:
    """Create a semantic cache with file persistence."""
    config = SemanticCacheConfig(persistence_file=temp_cache_file)
    return SemanticCache(config)


class TestSemanticCacheBasicOperations:
    """Test basic cache put/get operations."""

    def test_put_and_get_by_key(self, semantic_cache: SemanticCache) -> None:
        """Test storing and retrieving by key."""
        semantic_cache.put("key1", "value1", "query text")
        
        result = semantic_cache.get("key1")
        
        assert result == "value1"

    def test_get_missing_key_returns_none(self, semantic_cache: SemanticCache) -> None:
        """Test that get returns None for missing key."""
        result = semantic_cache.get("missing_key")
        
        assert result is None

    def test_put_returns_true(self, semantic_cache: SemanticCache) -> None:
        """Test that put returns True on success."""
        result = semantic_cache.put("key1", "value1", "query text")
        
        assert result is True

    def test_put_with_all_parameters(self, semantic_cache: SemanticCache) -> None:
        """Test put with all optional parameters."""
        result = semantic_cache.put(
            key="key1",
            value="value1",
            query_text="query text",
            content_type="article",
            creation_cost=1.5,
            tags=["tag1", "tag2"]
        )
        
        assert result is True
        assert semantic_cache.get("key1") == "value1"


class TestSemanticCacheSimilarity:
    """Test semantic similarity-based retrieval."""

    def test_get_by_similar_query_text(self, semantic_cache: SemanticCache) -> None:
        """Test retrieving by similar query text with common terms."""
        # Store with original query - use terms that will have high overlap
        semantic_cache.put("key1", "value1", "the quick brown fox jumps over")
        
        # Retrieve with very similar query (significant term overlap)
        result = semantic_cache.get("different_key", "the quick brown fox jumps over lazy dog")
        
        # Should find similar entry due to term overlap
        assert result == "value1"

    def test_similarity_below_threshold_returns_none(self, semantic_cache: SemanticCache) -> None:
        """Test that dissimilar queries return None."""
        # Store with specific query
        semantic_cache.put("key1", "value1", "machine learning algorithms")
        
        # Try to retrieve with completely different query
        result = semantic_cache.get("different_key", "baking chocolate cake recipes")
        
        # Should not find similar entry (below threshold)
        assert result is None

    def test_custom_similarity_threshold(self) -> None:
        """Test cache with custom similarity threshold."""
        config = SemanticCacheConfig(similarity_threshold=0.5)
        cache = SemanticCache(config)
        
        cache.put("key1", "value1", "machine learning algorithms and data science methods")
        
        # Should find with lower threshold - use query with overlapping terms
        result = cache.get("different_key", "machine learning algorithms data")
        
        assert result == "value1"

    def test_exact_query_match(self, semantic_cache: SemanticCache) -> None:
        """Test exact query text match."""
        semantic_cache.put("key1", "value1", "exact query text")
        
        result = semantic_cache.get("different_key", "exact query text")
        
        assert result == "value1"


class TestSemanticCacheStats:
    """Test cache statistics tracking."""

    def test_stats_tracks_hits(self, semantic_cache: SemanticCache) -> None:
        """Test that stats track cache hits."""
        semantic_cache.put("key1", "value1", "query text")
        semantic_cache.get("key1")  # Hit
        semantic_cache.get("key1")  # Hit
        
        stats = semantic_cache.get_stats()
        
        assert stats["hit_count"] == 2

    def test_stats_tracks_misses(self, semantic_cache: SemanticCache) -> None:
        """Test that stats track cache misses."""
        semantic_cache.get("missing1")  # Miss
        semantic_cache.get("missing2")  # Miss
        
        stats = semantic_cache.get_stats()
        
        assert stats["miss_count"] == 2

    def test_stats_tracks_cache_size(self, semantic_cache: SemanticCache) -> None:
        """Test that stats track cache size."""
        semantic_cache.put("key1", "value1", "query1")
        semantic_cache.put("key2", "value2", "query2")
        
        stats = semantic_cache.get_stats()
        
        assert stats["cache_size"] == 2

    def test_initial_stats_are_zero(self, semantic_cache: SemanticCache) -> None:
        """Test that initial stats are all zero."""
        stats = semantic_cache.get_stats()
        
        assert stats["cache_size"] == 0
        assert stats["hit_count"] == 0
        assert stats["miss_count"] == 0


class TestSemanticCacheTTL:
    """Test TTL (Time-To-Live) expiration."""

    def test_ttl_expiration_removes_entry(self, tmp_path: Path) -> None:
        """Test that entries expire after TTL."""
        config = SemanticCacheConfig(ttl_seconds=0.1)
        cache = SemanticCache(config)
        
        cache.put("key1", "value1", "query text")
        assert cache.get("key1") == "value1"
        
        # Wait for TTL to expire
        time.sleep(0.15)
        
        # Entry should be expired
        assert cache.get("key1") is None

    def test_zero_ttl_means_no_expiration(self) -> None:
        """Test that zero TTL means entries don't expire."""
        config = SemanticCacheConfig(ttl_seconds=0)
        cache = SemanticCache(config)
        
        cache.put("key1", "value1", "query text")
        
        # Entry should still be there (no expiration)
        assert cache.get("key1") == "value1"


class TestSemanticCacheEviction:
    """Test cache eviction when max size is exceeded."""

    def test_lru_eviction_when_maxsize_exceeded(self) -> None:
        """Test that oldest entries are evicted when max size exceeded."""
        config = SemanticCacheConfig(max_cache_size=2)
        cache = SemanticCache(config)
        
        cache.put("key1", "value1", "query1")
        cache.put("key2", "value2", "query2")
        cache.put("key3", "value3", "query3")  # Should trigger eviction
        
        stats = cache.get_stats()
        assert stats["cache_size"] == 2

    def test_accessed_entry_not_evicted(self) -> None:
        """Test that accessed entries are not evicted."""
        config = SemanticCacheConfig(max_cache_size=2)
        cache = SemanticCache(config)
        
        cache.put("key1", "value1", "query1")
        cache.put("key2", "value2", "query2")
        cache.get("key1")  # Access key1 to make it recently used
        cache.put("key3", "value3", "query3")  # Should evict key2
        
        # key1 should still be there
        assert cache.get("key1") == "value1"


class TestSemanticCachePersistence:
    """Test cache persistence (save/load)."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        """Test that save creates a persistence file."""
        cache_file = tmp_path / "cache.json"
        config = SemanticCacheConfig(persistence_file=cache_file)
        cache = SemanticCache(config)
        
        cache.put("key1", "value1", "query text")
        cache.save_cache()
        
        assert cache_file.exists()

    def test_save_without_persistence_file_does_nothing(self, semantic_cache: SemanticCache) -> None:
        """Test that save does nothing if no persistence file configured."""
        semantic_cache.put("key1", "value1", "query text")
        
        # Should not raise
        semantic_cache.save_cache()

    def test_load_restores_cache(self, tmp_path: Path) -> None:
        """Test that load restores cache from file."""
        cache_file = tmp_path / "cache.json"
        
        # Create and save cache
        config1 = SemanticCacheConfig(persistence_file=cache_file)
        cache1 = SemanticCache(config1)
        cache1.put("key1", "value1", "query text")
        cache1.save_cache()
        
        # Load cache in new instance
        config2 = SemanticCacheConfig(persistence_file=cache_file)
        cache2 = SemanticCache(config2)
        
        assert cache2.get("key1") == "value1"

    def test_load_with_corrupted_file(self, tmp_path: Path) -> None:
        """Test that load handles corrupted file gracefully."""
        cache_file = tmp_path / "cache.json"
        cache_file.write_text("invalid json")
        
        config = SemanticCacheConfig(persistence_file=cache_file)
        cache = SemanticCache(config)
        
        # Should not raise and cache should be empty
        assert cache.get_stats()["cache_size"] == 0

    def test_load_with_nonexistent_file(self, tmp_path: Path) -> None:
        """Test that load handles nonexistent file gracefully."""
        cache_file = tmp_path / "nonexistent" / "cache.json"
        
        config = SemanticCacheConfig(persistence_file=cache_file)
        cache = SemanticCache(config)
        
        # Should not raise and cache should be empty
        assert cache.get_stats()["cache_size"] == 0

    def test_load_expired_entries_not_loaded(self, tmp_path: Path) -> None:
        """Test that expired entries are not loaded from file."""
        cache_file = tmp_path / "cache.json"
        
        # Create cache with very short TTL
        config1 = SemanticCacheConfig(
            persistence_file=cache_file,
            ttl_seconds=0.1
        )
        cache1 = SemanticCache(config1)
        cache1.put("key1", "value1", "query text")
        cache1.save_cache()
        
        # Wait for TTL to expire
        time.sleep(0.15)
        
        # Load cache
        config2 = SemanticCacheConfig(
            persistence_file=cache_file,
            ttl_seconds=0.1
        )
        cache2 = SemanticCache(config2)
        
        # Expired entry should not be loaded
        assert cache2.get("key1") is None


class TestSemanticEntry:
    """Test _SemanticEntry internal class."""

    def test_entry_creation(self) -> None:
        """Test creating a semantic entry."""
        entry = _SemanticEntry(
            key="key1",
            value="value1",
            query_text="query text",
            content_type="article",
            creation_cost=1.5,
            created_ts=time.time()
        )
        
        assert entry.key == "key1"
        assert entry.value == "value1"
        assert entry.query_text == "query text"

    def test_entry_expired_with_positive_ttl(self) -> None:
        """Test expired check with positive TTL."""
        entry = _SemanticEntry(
            key="key1",
            value="value1",
            query_text="query",
            content_type="generic",
            creation_cost=0.0,
            created_ts=time.time() - 10  # Created 10 seconds ago
        )
        
        assert entry.expired(time.time(), ttl=5) is True  # 5 sec TTL expired
        assert entry.expired(time.time(), ttl=20) is False  # 20 sec TTL not expired

    def test_entry_not_expired_with_zero_ttl(self) -> None:
        """Test expired check with zero TTL (no expiration)."""
        entry = _SemanticEntry(
            key="key1",
            value="value1",
            query_text="query",
            content_type="generic",
            creation_cost=0.0,
            created_ts=time.time() - 1000  # Created long ago
        )
        
        assert entry.expired(time.time(), ttl=0) is False

    def test_entry_with_metadata(self) -> None:
        """Test entry with CacheEntryMeta."""
        meta = CacheEntryMeta(tags=["tag1", "tag2"])
        entry = _SemanticEntry(
            key="key1",
            value="value1",
            query_text="query",
            content_type="generic",
            creation_cost=0.0,
            created_ts=time.time(),
            meta=meta
        )
        
        assert entry.meta.tags == ["tag1", "tag2"]


class TestCosineSimilarity:
    """Test _cosine_similarity function."""

    def test_identical_texts_have_similarity_one(self) -> None:
        """Test identical texts have cosine similarity of 1.0."""
        text = "machine learning algorithms"
        
        similarity = _cosine_similarity(text, text)
        
        # Use approximate equality due to floating point precision
        assert abs(similarity - 1.0) < 0.0001

    def test_completely_different_texts_have_low_similarity(self) -> None:
        """Test completely different texts have low similarity."""
        text1 = "abc xyz"
        text2 = "def uvw"
        
        similarity = _cosine_similarity(text1, text2)
        
        assert similarity < 0.5

    def test_empty_text_returns_zero(self) -> None:
        """Test empty text returns zero similarity."""
        assert _cosine_similarity("", "some text") == 0.0
        assert _cosine_similarity("some text", "") == 0.0
        assert _cosine_similarity("", "") == 0.0

    def test_partially_similar_texts(self) -> None:
        """Test partially similar texts have medium similarity."""
        text1 = "machine learning algorithms for data"
        text2 = "machine learning models for prediction"
        
        similarity = _cosine_similarity(text1, text2)
        
        assert 0 < similarity < 1


class TestTokenFrequency:
    """Test _token_frequency function."""

    def test_token_frequency_counts(self) -> None:
        """Test token frequency counting."""
        text = "the quick brown fox jumps over the lazy dog"
        
        freq = _token_frequency(text)
        
        assert freq["the"] == 2
        assert freq["quick"] == 1
        assert freq["brown"] == 1

    def test_token_frequency_case_insensitive(self) -> None:
        """Test token frequency is case insensitive."""
        text = "The THE the"
        
        freq = _token_frequency(text)
        
        assert freq["the"] == 3

    def test_token_frequency_empty_string(self) -> None:
        """Test token frequency with empty string."""
        freq = _token_frequency("")
        
        assert freq == {}


class TestSemanticCacheConfig:
    """Test SemanticCacheConfig dataclass."""

    def test_config_defaults(self) -> None:
        """Test config with default values."""
        config = SemanticCacheConfig()
        
        assert config.max_cache_size == 256
        assert config.similarity_threshold == 0.85
        assert config.persistence_file is None
        assert config.ttl_seconds == 3600

    def test_config_custom_values(self) -> None:
        """Test config with custom values."""
        config = SemanticCacheConfig(
            max_cache_size=100,
            similarity_threshold=0.75,
            ttl_seconds=600
        )
        
        assert config.max_cache_size == 100
        assert config.similarity_threshold == 0.75
        assert config.ttl_seconds == 600
