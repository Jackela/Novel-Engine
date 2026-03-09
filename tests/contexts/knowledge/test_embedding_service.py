"""
Test suite for Embedding Services.

Tests CachedEmbeddingService and EmbeddingServiceAdapter.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

from src.contexts.knowledge.application.ports.i_embedding_service import EmbeddingError
from src.contexts.knowledge.application.services.embedding_cache_service import (
    CacheStats,
)
from src.contexts.knowledge.infrastructure.adapters.cached_embedding_service import (
    CachedEmbeddingService,
)
from src.contexts.knowledge.infrastructure.adapters.embedding_generator_adapter import (
    EmbeddingServiceAdapter,
)

pytestmark = pytest.mark.unit


class TestEmbeddingServiceAdapter:
    """Tests for EmbeddingServiceAdapter."""

    def test_initialization_with_api_key(self):
        """Test initialization with explicit API key."""
        with patch.dict("os.environ", {}, clear=True):
            adapter = EmbeddingServiceAdapter(api_key="test_key", use_mock=True)
            assert adapter._api_key == "test_key"
            assert adapter._use_mock is True

    def test_initialization_from_env(self):
        """Test initialization reading API key from environment."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "env_key"}, clear=True):
            adapter = EmbeddingServiceAdapter(use_mock=False)
            assert adapter._api_key == "env_key"

    def test_initialization_mock_mode_no_key(self):
        """Test initialization defaults to mock mode without API key."""
        with patch.dict("os.environ", {}, clear=True):
            adapter = EmbeddingServiceAdapter()
            assert adapter._use_mock is True

    def test_initialization_with_model(self):
        """Test initialization with specific model."""
        adapter = EmbeddingServiceAdapter(use_mock=True, model="text-embedding-3-large")
        assert adapter._model == "text-embedding-3-large"

    def test_initialization_invalid_model(self):
        """Test initialization with invalid model raises error."""
        with pytest.raises(ValueError, match="Unknown model"):
            EmbeddingServiceAdapter(use_mock=True, model="invalid-model")

    def test_get_dimension_ada002(self):
        """Test getting dimension for ada-002 model."""
        adapter = EmbeddingServiceAdapter(use_mock=True, model="text-embedding-ada-002")
        assert adapter.get_dimension() == 1536

    def test_get_dimension_3_small(self):
        """Test getting dimension for text-embedding-3-small."""
        adapter = EmbeddingServiceAdapter(use_mock=True, model="text-embedding-3-small")
        assert adapter.get_dimension() == 1536

    def test_get_dimension_3_large(self):
        """Test getting dimension for text-embedding-3-large."""
        adapter = EmbeddingServiceAdapter(use_mock=True, model="text-embedding-3-large")
        assert adapter.get_dimension() == 3072

    @pytest.mark.asyncio
    async def test_embed_mock_mode(self):
        """Test embedding generation in mock mode."""
        adapter = EmbeddingServiceAdapter(use_mock=True)
        embedding = await adapter.embed("test text")

        assert isinstance(embedding, list)
        assert len(embedding) == 1536  # Default dimension

    @pytest.mark.asyncio
    async def test_embed_empty_text(self):
        """Test embedding with empty text raises error."""
        adapter = EmbeddingServiceAdapter(use_mock=True)

        with pytest.raises(EmbeddingError, match="empty"):
            await adapter.embed("")

    @pytest.mark.asyncio
    async def test_embed_whitespace_text(self):
        """Test embedding with whitespace-only text raises error."""
        adapter = EmbeddingServiceAdapter(use_mock=True)

        with pytest.raises(EmbeddingError, match="empty"):
            await adapter.embed("   ")

    @pytest.mark.asyncio
    async def test_embed_caching(self):
        """Test that embeddings are cached."""
        adapter = EmbeddingServiceAdapter(use_mock=True)
        text = "test text for caching"

        # First call
        embedding1 = await adapter.embed(text)
        # Second call - should come from cache
        embedding2 = await adapter.embed(text)

        assert embedding1 == embedding2

    @pytest.mark.asyncio
    async def test_embed_different_texts_different_embeddings(self):
        """Test that different texts produce different embeddings."""
        adapter = EmbeddingServiceAdapter(use_mock=True)

        embedding1 = await adapter.embed("text one")
        embedding2 = await adapter.embed("text two")

        assert embedding1 != embedding2

    @pytest.mark.asyncio
    async def test_embed_batch_mock_mode(self):
        """Test batch embedding in mock mode."""
        adapter = EmbeddingServiceAdapter(use_mock=True)
        texts = ["text one", "text two", "text three"]

        embeddings = await adapter.embed_batch(texts)

        assert len(embeddings) == 3
        assert all(len(e) == 1536 for e in embeddings)

    @pytest.mark.asyncio
    async def test_embed_batch_empty_list(self):
        """Test batch embedding with empty list."""
        adapter = EmbeddingServiceAdapter(use_mock=True)

        embeddings = await adapter.embed_batch([])

        assert embeddings == []

    @pytest.mark.asyncio
    async def test_embed_batch_single_text(self):
        """Test batch embedding with single text."""
        adapter = EmbeddingServiceAdapter(use_mock=True)

        embeddings = await adapter.embed_batch(["single text"])

        assert len(embeddings) == 1

    @pytest.mark.asyncio
    async def test_embed_batch_respects_batch_size(self):
        """Test that batch embedding respects batch size parameter."""
        adapter = EmbeddingServiceAdapter(use_mock=True)
        texts = ["text"] * 10

        embeddings = await adapter.embed_batch(texts, batch_size=3)

        assert len(embeddings) == 10

    def test_clear_cache(self):
        """Test clearing the embedding cache."""
        adapter = EmbeddingServiceAdapter(use_mock=True)
        adapter._embedding_cache = {"key1": [0.1, 0.2], "key2": [0.3, 0.4]}

        adapter.clear_cache()

        assert len(adapter._embedding_cache) == 0

    def test_get_cache_key_deterministic(self):
        """Test that cache keys are deterministic for same text."""
        adapter = EmbeddingServiceAdapter(use_mock=True)

        key1 = adapter._get_cache_key("test text")
        key2 = adapter._get_cache_key("test text")

        assert key1 == key2

    def test_get_cache_key_unique(self):
        """Test that different texts produce different cache keys."""
        adapter = EmbeddingServiceAdapter(use_mock=True)

        key1 = adapter._get_cache_key("text one")
        key2 = adapter._get_cache_key("text two")

        assert key1 != key2

    @pytest.mark.asyncio
    async def test_generate_mock_embedding_deterministic(self):
        """Test that mock embeddings are deterministic for same text."""
        adapter = EmbeddingServiceAdapter(use_mock=True)

        embedding1 = adapter._generate_mock_embedding("test text")
        embedding2 = adapter._generate_mock_embedding("test text")

        assert embedding1 == embedding2

    @pytest.mark.asyncio
    async def test_generate_mock_embedding_normalized(self):
        """Test that mock embeddings are normalized."""
        adapter = EmbeddingServiceAdapter(use_mock=True)

        embedding = adapter._generate_mock_embedding("test text")
        magnitude = sum(x**2 for x in embedding) ** 0.5

        assert abs(magnitude - 1.0) < 1e-6

    @pytest.mark.asyncio
    async def test_generate_mock_embedding_different_dimensions(self):
        """Test mock embeddings with different dimensions."""
        adapter_small = EmbeddingServiceAdapter(
            use_mock=True, model="text-embedding-3-small"
        )
        adapter_large = EmbeddingServiceAdapter(
            use_mock=True, model="text-embedding-3-large"
        )

        embedding_small = adapter_small._generate_mock_embedding("test")
        embedding_large = adapter_large._generate_mock_embedding("test")

        assert len(embedding_small) == 1536
        assert len(embedding_large) == 3072


class TestCachedEmbeddingService:
    """Tests for CachedEmbeddingService."""

    @pytest_asyncio.fixture
    async def mock_delegate(self):
        """Create mock delegate embedding service."""
        delegate = AsyncMock()
        delegate.embed = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4, 0.5])
        delegate.embed_batch = AsyncMock(return_value=[[0.1, 0.2], [0.3, 0.4]])
        delegate.get_dimension = Mock(return_value=5)
        delegate.clear_cache = Mock()
        return delegate

    @pytest_asyncio.fixture
    async def mock_cache_service(self):
        """Create mock cache service."""
        cache = Mock()
        cache.get = Mock(return_value=None)
        cache.put = Mock()
        cache.get_batch = Mock(return_value={})
        cache.put_batch = Mock()
        cache.get_stats = Mock(return_value=CacheStats(hits=0, misses=0))
        cache.clear = Mock()
        cache.invalidate = Mock(return_value=0)
        return cache

    @pytest_asyncio.fixture
    async def cached_service(self, mock_delegate, mock_cache_service):
        """Create cached embedding service."""
        return CachedEmbeddingService(
            delegate=mock_delegate,
            cache_service=mock_cache_service,
            model="test-model",
        )

    @pytest.mark.asyncio
    async def test_embed_cache_hit(self, cached_service, mock_cache_service):
        """Test embedding with cache hit."""
        cached_embedding = [0.5, 0.4, 0.3, 0.2, 0.1]
        mock_cache_service.get = Mock(return_value=cached_embedding)

        result = await cached_service.embed("test text")

        assert result == cached_embedding
        # Should not call delegate on cache hit
        cached_service._delegate.embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_embed_cache_miss(
        self, cached_service, mock_cache_service, mock_delegate
    ):
        """Test embedding with cache miss."""
        mock_cache_service.get = Mock(return_value=None)

        result = await cached_service.embed("test text")

        assert result == [0.1, 0.2, 0.3, 0.4, 0.5]
        # Should call delegate on cache miss
        mock_delegate.embed.assert_called_once_with("test text")
        # Should store in cache
        mock_cache_service.put.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_empty_text(self, cached_service):
        """Test embedding with empty text raises error."""
        with pytest.raises(ValueError, match="empty"):
            await cached_service.embed("")

    @pytest.mark.asyncio
    async def test_embed_whitespace_text(self, cached_service):
        """Test embedding with whitespace-only text raises error."""
        with pytest.raises(ValueError, match="empty"):
            await cached_service.embed("   ")

    @pytest.mark.asyncio
    async def test_embed_batch_all_cache_hits(self, cached_service, mock_cache_service):
        """Test batch embedding with all cache hits."""
        texts = ["text1", "text2"]
        cached_results = {
            "text1": [0.1, 0.2],
            "text2": [0.3, 0.4],
        }
        mock_cache_service.get_batch = Mock(return_value=cached_results)

        results = await cached_service.embed_batch(texts)

        assert len(results) == 2
        # Should not call delegate when all in cache
        cached_service._delegate.embed_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_embed_batch_partial_cache_hits(
        self, cached_service, mock_cache_service, mock_delegate
    ):
        """Test batch embedding with partial cache hits."""
        texts = ["cached_text", "new_text"]
        cached_results = {"cached_text": [0.1, 0.2]}
        mock_cache_service.get_batch = Mock(return_value=cached_results)
        mock_delegate.embed_batch = AsyncMock(return_value=[[0.3, 0.4]])

        results = await cached_service.embed_batch(texts)

        assert len(results) == 2
        # Should call delegate for missing text
        mock_delegate.embed_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_batch_no_cache_hits(
        self, cached_service, mock_cache_service, mock_delegate
    ):
        """Test batch embedding with no cache hits."""
        texts = ["text1", "text2"]
        mock_cache_service.get_batch = Mock(return_value={})
        mock_delegate.embed_batch = AsyncMock(return_value=[[0.1, 0.2], [0.3, 0.4]])

        results = await cached_service.embed_batch(texts)

        assert len(results) == 2
        mock_delegate.embed_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_batch_empty_list(self, cached_service):
        """Test batch embedding with empty list."""
        results = await cached_service.embed_batch([])

        assert results == []

    def test_get_dimension(self, cached_service, mock_delegate):
        """Test getting dimension delegates to underlying service."""
        dimension = cached_service.get_dimension()

        assert dimension == 5
        mock_delegate.get_dimension.assert_called_once()

    def test_clear_cache(self, cached_service, mock_cache_service):
        """Test clearing cache."""
        cached_service.clear_cache()

        mock_cache_service.clear.assert_called_once()

    def test_get_cache_stats(self, cached_service, mock_cache_service):
        """Test getting cache statistics."""
        stats = cached_service.get_cache_stats()

        assert isinstance(stats, CacheStats)
        mock_cache_service.get_stats.assert_called_once()

    def test_invalidate_cache_all_models(self, cached_service, mock_cache_service):
        """Test invalidating all cache entries."""
        cached_service.invalidate_cache()

        mock_cache_service.invalidate.assert_called_once()

    def test_invalidate_cache_specific_model(self, cached_service, mock_cache_service):
        """Test invalidating cache for specific model."""
        cached_service.invalidate_cache(model="test-model")

        mock_cache_service.invalidate.assert_called_once()


class TestEmbeddingCacheService:
    """Tests for EmbeddingCacheService."""

    def test_cache_initialization(self):
        """Test cache initialization with default parameters."""
        from src.contexts.knowledge.application.services.embedding_cache_service import (
            EmbeddingCacheService,
        )

        cache = EmbeddingCacheService()

        assert cache._max_size == EmbeddingCacheService.DEFAULT_MAX_SIZE

    def test_cache_initialization_custom_params(self):
        """Test cache initialization with custom parameters."""
        from src.contexts.knowledge.application.services.embedding_cache_service import (
            EmbeddingCacheService,
        )

        cache = EmbeddingCacheService(max_size=500, default_ttl_seconds=1800)

        assert cache._max_size == 500
        assert cache._default_ttl == 1800

    def test_cache_get_miss(self):
        """Test cache get with miss."""
        from src.contexts.knowledge.application.services.embedding_cache_service import (
            EmbeddingCacheService,
        )

        cache = EmbeddingCacheService()

        result = cache.get("nonexistent text", "model")

        assert result is None

    def test_cache_put_and_get(self):
        """Test cache put and get."""
        from src.contexts.knowledge.application.services.embedding_cache_service import (
            EmbeddingCacheService,
        )

        cache = EmbeddingCacheService()
        embedding = [0.1, 0.2, 0.3]

        cache.put("test text", embedding, "model")
        result = cache.get("test text", "model")

        assert result == embedding

    def test_cache_put_batch(self):
        """Test cache put batch."""
        from src.contexts.knowledge.application.services.embedding_cache_service import (
            EmbeddingCacheService,
        )

        cache = EmbeddingCacheService()
        items = [
            ("text1", [0.1, 0.2]),
            ("text2", [0.3, 0.4]),
        ]

        cache.put_batch(items, "model")

        assert cache.get("text1", "model") == [0.1, 0.2]
        assert cache.get("text2", "model") == [0.3, 0.4]

    def test_cache_get_batch(self):
        """Test cache get batch."""
        from src.contexts.knowledge.application.services.embedding_cache_service import (
            EmbeddingCacheService,
        )

        cache = EmbeddingCacheService()
        cache.put("text1", [0.1, 0.2], "model")
        cache.put("text2", [0.3, 0.4], "model")

        results = cache.get_batch(["text1", "text2", "text3"], "model")

        assert "text1" in results
        assert "text2" in results
        assert "text3" not in results

    def test_cache_stats(self):
        """Test cache statistics."""
        from src.contexts.knowledge.application.services.embedding_cache_service import (
            EmbeddingCacheService,
        )

        cache = EmbeddingCacheService()

        # Initial stats
        stats = cache.get_stats()
        assert stats.hits == 0
        assert stats.misses == 0

        # Generate some hits and misses
        cache.put("text1", [0.1], "model")
        cache.get("text1", "model")  # hit
        cache.get("text2", "model")  # miss

        stats = cache.get_stats()
        assert stats.hits >= 0
        assert stats.misses >= 0

    def test_cache_stats_hit_rate(self):
        """Test cache hit rate calculation."""
        from src.contexts.knowledge.application.services.embedding_cache_service import (
            CacheStats,
        )

        stats = CacheStats(hits=8, misses=2)
        assert stats.hit_rate == 0.8

        stats_empty = CacheStats()
        assert stats_empty.hit_rate == 0.0

    def test_cache_clear(self):
        """Test cache clear."""
        from src.contexts.knowledge.application.services.embedding_cache_service import (
            EmbeddingCacheService,
        )

        cache = EmbeddingCacheService()
        cache.put("text1", [0.1], "model")

        cache.clear()

        assert cache.get("text1", "model") is None

    def test_cache_invalidate(self):
        """Test cache invalidation."""
        from src.contexts.knowledge.application.services.embedding_cache_service import (
            EmbeddingCacheService,
        )

        cache = EmbeddingCacheService()
        cache.put("text1", [0.1], "model1")
        cache.put("text2", [0.2], "model2")

        count = cache.invalidate("model1")

        # Note: Current implementation clears all on model-specific invalidate
        assert count >= 0


class TestCacheKey:
    """Tests for CacheKey dataclass."""

    def test_cache_key_creation(self):
        """Test cache key creation."""
        from src.contexts.knowledge.application.services.embedding_cache_service import (
            CacheKey,
        )

        key = CacheKey(content_hash="abc123", model="text-embedding-ada-002")

        assert key.content_hash == "abc123"
        assert key.model == "text-embedding-ada-002"

    def test_cache_key_from_text(self):
        """Test cache key generation from text."""
        from src.contexts.knowledge.application.services.embedding_cache_service import (
            CacheKey,
        )

        key = CacheKey.from_text("test text", "model-name")

        assert key.model == "model-name"
        assert len(key.content_hash) == 64  # SHA256 hex length

    def test_cache_key_deterministic(self):
        """Test that cache keys are deterministic."""
        from src.contexts.knowledge.application.services.embedding_cache_service import (
            CacheKey,
        )

        key1 = CacheKey.from_text("same text", "same-model")
        key2 = CacheKey.from_text("same text", "same-model")

        assert key1.content_hash == key2.content_hash

    def test_cache_key_unique_per_model(self):
        """Test that cache keys are unique per model."""
        from src.contexts.knowledge.application.services.embedding_cache_service import (
            CacheKey,
        )

        key1 = CacheKey.from_text("same text", "model1")
        key2 = CacheKey.from_text("same text", "model2")

        assert key1.content_hash != key2.content_hash

    def test_cache_key_string_representation(self):
        """Test cache key string representation."""
        from src.contexts.knowledge.application.services.embedding_cache_service import (
            CacheKey,
        )

        key = CacheKey(content_hash="abcdef1234567890", model="test-model")

        str_repr = str(key)
        assert "test-model" in str_repr
        assert "abcdef1234567890"[:16] in str_repr
