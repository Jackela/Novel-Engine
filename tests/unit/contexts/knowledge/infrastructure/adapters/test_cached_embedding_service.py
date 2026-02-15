"""
Unit tests for CachedEmbeddingService.

Tests caching behavior, batch operations, fallback, and cache management.
"""


import pytest

from src.contexts.knowledge.application.ports.i_embedding_service import (
    EmbeddingError,
    IEmbeddingService,
)
from src.contexts.knowledge.application.services.embedding_cache_service import (
    EmbeddingCacheService,
)
from src.contexts.knowledge.infrastructure.adapters.cached_embedding_service import (
    CachedEmbeddingService,
)

pytestmark = pytest.mark.unit


class MockEmbeddingService(IEmbeddingService):
    """Mock embedding service for testing."""

    def __init__(self, dimension: int = 1536):
        self._dimension = dimension
        self.embed_count = 0
        self.batch_count = 0

    def _generate_embedding(self, text: str):
        """Generate deterministic mock embedding."""
        import hashlib

        seed = int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)
        import random

        random.seed(seed)
        embedding = [random.gauss(0, 1) for _ in range(self._dimension)]
        # Normalize
        magnitude = sum(x**2 for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]
        return embedding

    async def embed(self, text: str):
        self.embed_count += 1
        return self._generate_embedding(text)

    async def embed_batch(self, texts, batch_size=100):
        self.batch_count += 1
        return [self._generate_embedding(text) for text in texts]

    def get_dimension(self):
        return self._dimension

    def clear_cache(self):
        pass

    @property
    def call_count(self):
        """Total number of API calls made."""
        return self.embed_count + self.batch_count


class FailingEmbeddingService(IEmbeddingService):
    """Mock embedding service that always fails."""

    async def embed(self, text: str):
        raise EmbeddingError("Service unavailable", "SERVICE_ERROR")

    async def embed_batch(self, texts, batch_size=100):
        raise EmbeddingError("Service unavailable", "SERVICE_ERROR")

    def get_dimension(self):
        return 1536

    def clear_cache(self):
        pass


@pytest.fixture
def mock_service():
    """Fixture providing mock embedding service."""
    return MockEmbeddingService()


@pytest.fixture
def cache_service():
    """Fixture providing cache service."""
    return EmbeddingCacheService(max_size=100, default_ttl_seconds=3600)


@pytest.fixture
def cached_service(mock_service, cache_service):
    """Fixture providing cached embedding service."""
    return CachedEmbeddingService(
        delegate=mock_service,
        cache_service=cache_service,
        model="test-model",
    )


class TestCachedEmbeddingService:
    """Test CachedEmbeddingService behavior."""

    @pytest.mark.asyncio
    async def test_init_default_cache(self, mock_service):
        """Test initialization with default cache."""
        cached = CachedEmbeddingService(mock_service)
        assert cached._delegate is mock_service
        assert cached._model == "text-embedding-ada-002"
        assert isinstance(cached._cache, EmbeddingCacheService)

    @pytest.mark.asyncio
    async def test_init_custom_cache(self, mock_service, cache_service):
        """Test initialization with custom cache."""
        cached = CachedEmbeddingService(
            delegate=mock_service,
            cache_service=cache_service,
            model="custom-model",
        )
        assert cached._cache is cache_service
        assert cached._model == "custom-model"

    @pytest.mark.asyncio
    async def test_embed_cache_miss(self, cached_service, mock_service):
        """Test embed with cache miss calls delegate."""
        initial_count = mock_service.embed_count
        result = await cached_service.embed("test text")

        assert mock_service.embed_count == initial_count + 1
        assert len(result) == 1536

    @pytest.mark.asyncio
    async def test_embed_cache_hit(self, cached_service, mock_service):
        """Test embed with cache hit does not call delegate."""
        # First call - cache miss
        await cached_service.embed("test text")
        initial_count = mock_service.embed_count

        # Second call - cache hit
        result2 = await cached_service.embed("test text")

        assert mock_service.embed_count == initial_count  # No additional call
        assert len(result2) == 1536

    @pytest.mark.asyncio
    async def test_embed_empty_text_raises(self, cached_service):
        """Test that embedding empty text raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            await cached_service.embed("")

        with pytest.raises(ValueError, match="empty"):
            await cached_service.embed("   ")

    @pytest.mark.asyncio
    async def test_embed_delegate_failure_propagates(self):
        """Test that delegate failure propagates error."""
        failing_service = FailingEmbeddingService()
        cached = CachedEmbeddingService(failing_service)

        with pytest.raises(EmbeddingError, match="Service unavailable"):
            await cached.embed("test")

    @pytest.mark.asyncio
    async def test_embed_batch_all_cache_miss(self, cached_service, mock_service):
        """Test batch embed with all cache misses."""
        texts = ["text1", "text2", "text3"]
        initial_batch_count = mock_service.batch_count

        results = await cached_service.embed_batch(texts)

        # embed_batch should make one batch call
        assert mock_service.batch_count == initial_batch_count + 1
        assert len(results) == 3
        assert all(len(r) == 1536 for r in results)

    @pytest.mark.asyncio
    async def test_embed_batch_all_cache_hit(self, cached_service, mock_service):
        """Test batch embed with all cache hits."""
        texts = ["text1", "text2", "text3"]

        # First call - populate cache
        await cached_service.embed_batch(texts)
        initial_batch_count = mock_service.batch_count

        # Second call - all from cache
        results = await cached_service.embed_batch(texts)

        # No additional batch calls should be made
        assert mock_service.batch_count == initial_batch_count
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_embed_batch_partial_cache_hit(self, cached_service, mock_service):
        """Test batch embed with mixed cache hits and misses."""
        texts = ["text1", "text2", "text3"]

        # Populate cache for text1 and text3
        await cached_service.embed("text1")
        await cached_service.embed("text3")
        initial_embed_count = mock_service.embed_count
        initial_batch_count = mock_service.batch_count

        # Batch call - text2 should be cache miss, text1 and text3 are hits
        results = await cached_service.embed_batch(texts)

        # embed_batch processes all 3 texts, including the misses
        # It should make one batch call for the misses
        assert mock_service.batch_count == initial_batch_count + 1
        assert len(results) == 3

        # Verify results are in correct order
        result1 = await cached_service.embed("text1")
        result3 = await cached_service.embed("text3")
        assert results[0] == result1
        assert results[2] == result3

    @pytest.mark.asyncio
    async def test_embed_batch_empty_list(self, cached_service):
        """Test batch embed with empty list."""
        results = await cached_service.embed_batch([])
        assert results == []

    @pytest.mark.asyncio
    async def test_get_dimension(self, cached_service, mock_service):
        """Test get_dimension returns delegate's dimension."""
        assert cached_service.get_dimension() == mock_service.get_dimension()

    @pytest.mark.asyncio
    async def test_clear_cache(self, cached_service, mock_service):
        """Test clear_cache clears the cache but not delegate."""
        # Populate cache
        await cached_service.embed("test")

        # Clear cache
        cached_service.clear_cache()

        # Next call should hit delegate again
        initial_count = mock_service.call_count
        await cached_service.embed("test")
        assert mock_service.call_count == initial_count + 1

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, cached_service):
        """Test getting cache statistics."""
        stats = cached_service.get_cache_stats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.size == 0

        # Generate some activity
        await cached_service.embed("test")
        await cached_service.embed("test")  # Cache hit

        stats = cached_service.get_cache_stats()
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.size == 1

    @pytest.mark.asyncio
    async def test_invalidate_cache_by_model(self, cached_service):
        """Test invalidating cache entries."""
        await cached_service.embed("test")

        count = cached_service.invalidate_cache()
        assert count == 1

        # Should be cache miss now
        result = await cached_service.embed("test")
        assert len(result) == 1536

    @pytest.mark.asyncio
    async def test_different_models_separate_cache(self, mock_service):
        """Test that different models use separate cache entries."""
        cache = EmbeddingCacheService()
        cached_a = CachedEmbeddingService(
            delegate=mock_service,
            cache_service=cache,
            model="model-a",
        )
        cached_b = CachedEmbeddingService(
            delegate=mock_service,
            cache_service=cache,
            model="model-b",
        )

        # Same text, different models
        await cached_a.embed("test")
        await cached_b.embed("test")

        stats = cache.get_stats()
        assert stats.size == 2  # Two separate entries

    @pytest.mark.asyncio
    async def test_cache_stats_hit_rate(self, cached_service):
        """Test cache hit rate calculation."""
        await cached_service.embed("test")
        await cached_service.embed("test")  # Hit
        await cached_service.embed("other")  # Miss
        await cached_service.embed("test")  # Hit

        stats = cached_service.get_cache_stats()
        # 2 hits, 2 misses = 0.5 hit rate
        assert stats.hit_rate == 0.5
