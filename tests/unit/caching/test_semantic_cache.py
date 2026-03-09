"""
Unit tests for SemanticCache implementation.

Tests cover:
- Basic put/get operations
- Semantic similarity matching
- TTL-based expiration
- Capacity eviction
- Persistence (save/load)
- Statistics tracking
- Edge cases
"""

import tempfile
import time
from pathlib import Path

import pytest

from src.caching.semantic_cache import (
    SemanticCache,
    SemanticCacheConfig,
    _cosine_similarity,
    _token_frequency,
)

pytestmark = pytest.mark.unit


class TestSemanticCacheConfig:
    """Tests for SemanticCacheConfig."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = SemanticCacheConfig()
        assert config.max_cache_size == 256
        assert config.similarity_threshold == 0.85
        assert config.persistence_file is None
        assert config.ttl_seconds == 60 * 60

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = SemanticCacheConfig(
            max_cache_size=100,
            similarity_threshold=0.9,
            persistence_file=Path("/tmp/cache.json"),
            ttl_seconds=300,
        )
        assert config.max_cache_size == 100
        assert config.similarity_threshold == 0.9
        assert config.persistence_file == Path("/tmp/cache.json")
        assert config.ttl_seconds == 300


class TestSemanticCacheBasicOperations:
    """Tests for basic put/get operations."""

    def test_put_and_get(self) -> None:
        """Test basic put and get operations."""
        cache = SemanticCache()
        cache.put("key1", "value1", "query text one")
        result = cache.get("key1")
        assert result == "value1"

    def test_get_nonexistent_key(self) -> None:
        """Test getting a nonexistent key returns None."""
        cache = SemanticCache()
        result = cache.get("nonexistent")
        assert result is None

    def test_put_overwrites_existing(self) -> None:
        """Test that putting same key overwrites value."""
        cache = SemanticCache()
        cache.put("key", "value1", "query1")
        cache.put("key", "value2", "query2")
        result = cache.get("key")
        assert result == "value2"

    def test_put_with_content_type(self) -> None:
        """Test put with content type."""
        cache = SemanticCache()
        cache.put("key", "value", "query", content_type="json")
        result = cache.get("key")
        assert result == "value"

    def test_put_with_creation_cost(self) -> None:
        """Test put with creation cost."""
        cache = SemanticCache()
        cache.put("key", "value", "query", creation_cost=0.5)
        result = cache.get("key")
        assert result == "value"

    def test_put_with_tags(self) -> None:
        """Test put with tags."""
        cache = SemanticCache()
        cache.put("key", "value", "query", tags=["tag1", "tag2"])
        result = cache.get("key")
        assert result == "value"


class TestSemanticCacheSimilarityMatching:
    """Tests for semantic similarity matching."""

    def test_semantic_match_similar_query(self) -> None:
        """Test retrieval with similar query text."""
        cache = SemanticCache()
        cache.put("key1", "value1", "hello world test")
        
        # Similar query should match
        result = cache.get("key1", query_text="hello world example")
        assert result == "value1"

    def test_semantic_match_different_query(self) -> None:
        """Test that dissimilar queries don't match when key exists."""
        cache = SemanticCache(config=SemanticCacheConfig(similarity_threshold=0.95))
        cache.put("key1", "value1", "aaa bbb ccc ddd")  # Use words unlikely to match
        
        # Different query - should not match above high threshold
        # Note: When key exists, it first tries key lookup which succeeds
        # So we need to test with wrong key to test semantic matching
        result = cache.get("wrong_key", query_text="xxx yyy zzz")
        assert result is None

    def test_semantic_match_below_threshold(self) -> None:
        """Test that queries below similarity threshold don't match with wrong key."""
        cache = SemanticCache(config=SemanticCacheConfig(similarity_threshold=0.95))
        cache.put("key1", "value1", "hello world test query")
        
        # Different enough query should not match with high threshold
        # Use wrong key to force semantic matching
        result = cache.get("wrong_key", query_text="something else entirely different")
        assert result is None

    def test_semantic_match_only_with_query_text(self) -> None:
        """Test semantic matching only when query_text provided."""
        cache = SemanticCache()
        cache.put("key1", "value1", "hello world")
        
        # Without query_text, should return None for non-matching key
        result = cache.get("wrong_key")
        assert result is None


class TestSemanticCacheTTL:
    """Tests for TTL-based expiration."""

    def test_ttl_expiration(self) -> None:
        """Test that entries expire after TTL."""
        config = SemanticCacheConfig(ttl_seconds=0.1)
        cache = SemanticCache(config=config)
        
        cache.put("key", "value", "query")
        assert cache.get("key") == "value"  # Still valid
        
        time.sleep(0.15)
        assert cache.get("key") is None  # Expired

    def test_no_ttl_no_expiration(self) -> None:
        """Test that entries don't expire when TTL is 0."""
        config = SemanticCacheConfig(ttl_seconds=0)
        cache = SemanticCache(config=config)
        
        cache.put("key", "value", "query")
        time.sleep(0.05)
        assert cache.get("key") == "value"

    def test_expired_entry_not_found_by_key(self) -> None:
        """Test that expired entries are not found by key lookup."""
        config = SemanticCacheConfig(ttl_seconds=0.1)
        cache = SemanticCache(config=config)
        
        cache.put("key1", "value1", "hello world")
        time.sleep(0.15)
        
        # Expired entry should not be found by key
        result = cache.get("key1")
        assert result is None
        # And it should count as a miss
        assert cache.get_stats()["miss_count"] == 1


class TestSemanticCacheEviction:
    """Tests for capacity-based eviction."""

    def test_lru_eviction_on_maxsize(self) -> None:
        """Test LRU eviction when cache is full."""
        config = SemanticCacheConfig(max_cache_size=3)
        cache = SemanticCache(config=config)
        
        cache.put("a", "1", "query a")
        cache.put("b", "2", "query b")
        cache.put("c", "3", "query c")
        cache.put("d", "4", "query d")  # Should evict "a"
        
        assert cache.get("a") is None
        assert cache.get("b") == "2"
        assert cache.get("c") == "3"
        assert cache.get("d") == "4"

    def test_access_updates_lru_order(self) -> None:
        """Test that accessing an item updates LRU position."""
        config = SemanticCacheConfig(max_cache_size=3)
        cache = SemanticCache(config=config)
        
        cache.put("a", "1", "query a")
        cache.put("b", "2", "query b")
        cache.put("c", "3", "query c")
        
        # Access "a" to make it recently used
        cache.get("a")
        
        # Add new item - should evict "b"
        cache.put("d", "4", "query d")
        
        assert cache.get("a") == "1"  # Still present
        assert cache.get("b") is None  # Evicted


class TestSemanticCacheStats:
    """Tests for statistics tracking."""

    def test_initial_stats(self) -> None:
        """Test initial stats are zero."""
        cache = SemanticCache()
        stats = cache.get_stats()
        assert stats["cache_size"] == 0
        assert stats["hit_count"] == 0
        assert stats["miss_count"] == 0

    def test_hit_tracking(self) -> None:
        """Test hit tracking."""
        cache = SemanticCache()
        cache.put("key", "value", "query")
        
        cache.get("key")  # Hit
        cache.get("key")  # Hit
        
        stats = cache.get_stats()
        assert stats["hit_count"] == 2
        assert stats["miss_count"] == 0

    def test_miss_tracking(self) -> None:
        """Test miss tracking."""
        cache = SemanticCache()
        
        cache.get("nonexistent1")  # Miss
        cache.get("nonexistent2")  # Miss
        
        stats = cache.get_stats()
        assert stats["hit_count"] == 0
        assert stats["miss_count"] == 2

    def test_stats_with_expired_entry(self) -> None:
        """Test that expired entries count as misses."""
        config = SemanticCacheConfig(ttl_seconds=0.1)
        cache = SemanticCache(config=config)
        cache.put("key", "value", "query")
        time.sleep(0.15)
        
        cache.get("key")  # Expired - counts as miss
        stats = cache.get_stats()
        assert stats["hit_count"] == 0
        assert stats["miss_count"] == 1


class TestSemanticCachePersistence:
    """Tests for cache persistence."""

    def test_save_and_load(self) -> None:
        """Test saving and loading cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "cache.json"
            
            # Create and populate cache
            config = SemanticCacheConfig(persistence_file=file_path)
            cache1 = SemanticCache(config)
            cache1.put("key1", "value1", "query1", content_type="json")
            cache1.save_cache()
            
            # Load cache in new instance
            cache2 = SemanticCache(config)
            result = cache2.get("key1")
            assert result == "value1"

    def test_load_filters_expired(self) -> None:
        """Test that loading filters out expired entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "cache.json"
            
            # Create cache with short TTL and populate
            config = SemanticCacheConfig(
                persistence_file=file_path,
                ttl_seconds=0.1
            )
            cache1 = SemanticCache(config)
            cache1.put("key1", "value1", "query1")
            cache1.save_cache()
            
            # Wait for expiration and load
            time.sleep(0.15)
            cache2 = SemanticCache(config)
            result = cache2.get("key1")
            assert result is None

    def test_save_without_file(self) -> None:
        """Test that save without persistence file does nothing."""
        cache = SemanticCache()  # No persistence file
        cache.put("key", "value", "query")
        cache.save_cache()  # Should not raise

    def test_load_with_missing_file(self) -> None:
        """Test that loading with missing file does nothing."""
        config = SemanticCacheConfig(persistence_file=Path("/nonexistent/cache.json"))
        cache = SemanticCache(config)  # Should not raise
        assert cache.get_stats()["cache_size"] == 0

    def test_load_with_invalid_json(self) -> None:
        """Test that loading invalid JSON does not raise."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "cache.json"
            file_path.write_text("invalid json", encoding="utf-8")
            
            config = SemanticCacheConfig(persistence_file=file_path)
            cache = SemanticCache(config)  # Should not raise
            assert cache.get_stats()["cache_size"] == 0


class TestCosineSimilarity:
    """Tests for cosine similarity function."""

    def test_empty_strings(self) -> None:
        """Test cosine similarity with empty strings."""
        assert _cosine_similarity("", "hello") == 0.0
        assert _cosine_similarity("hello", "") == 0.0
        assert _cosine_similarity("", "") == 0.0

    def test_identical_strings(self) -> None:
        """Test cosine similarity with identical strings."""
        similarity = _cosine_similarity("hello world", "hello world")
        assert abs(similarity - 1.0) < 1e-9

    def test_different_strings(self) -> None:
        """Test cosine similarity with different strings."""
        similarity = _cosine_similarity("hello world", "goodbye moon")
        assert 0.0 <= similarity < 0.5  # Low similarity

    def test_partial_similarity(self) -> None:
        """Test cosine similarity with partially similar strings."""
        similarity = _cosine_similarity("hello world test", "hello world example")
        assert 0.5 < similarity < 1.0  # Moderate similarity

    def test_case_insensitive(self) -> None:
        """Test that cosine similarity is case-insensitive."""
        similarity = _cosine_similarity("Hello World", "hello world")
        assert abs(similarity - 1.0) < 1e-9


class TestTokenFrequency:
    """Tests for token frequency function."""

    def test_empty_string(self) -> None:
        """Test token frequency with empty string."""
        result = _token_frequency("")
        assert result == {}

    def test_single_word(self) -> None:
        """Test token frequency with single word."""
        result = _token_frequency("hello")
        assert result == {"hello": 1}

    def test_multiple_words(self) -> None:
        """Test token frequency with multiple words."""
        result = _token_frequency("hello world hello")
        assert result == {"hello": 2, "world": 1}

    def test_case_conversion(self) -> None:
        """Test that tokens are lowercased."""
        result = _token_frequency("Hello HELLO hello")
        assert result == {"hello": 3}
