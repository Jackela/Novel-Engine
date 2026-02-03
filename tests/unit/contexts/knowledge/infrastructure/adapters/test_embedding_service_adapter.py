"""
Unit Tests for Embedding Service Adapter

Tests the embedding service adapter implementing IEmbeddingService port.

Warzone 4: AI Brain - BRAIN-002
Tests embedding generation, batch processing, caching, and fallback behavior.

Constitution Compliance:
- Article III (TDD): Tests written to validate embedding service behavior
- Article I (DDD): Tests adapter behavior, not business logic
"""

from typing import List

import pytest

from src.contexts.knowledge.application.ports.i_embedding_service import (
    EmbeddingError,
    IEmbeddingService,
)
from src.contexts.knowledge.infrastructure.adapters.embedding_generator_adapter import (
    EmbeddingServiceAdapter,
)


@pytest.fixture
def mock_embedding_service() -> EmbeddingServiceAdapter:
    """
    Create an embedding service in mock mode.

    Mock mode uses deterministic hash-based embeddings for testing
    without requiring API keys.

    Returns:
        EmbeddingServiceAdapter instance with use_mock=True
    """
    return EmbeddingServiceAdapter(use_mock=True)


@pytest.fixture
def sample_texts() -> List[str]:
    """
    Create sample texts for embedding tests.

    Returns:
        List of sample text strings
    """
    return [
        "The brave warrior fought with honor.",
        "The ancient dragon guarded the mountain treasure.",
        "In the realm of shadows, heroes rise.",
        "Alice discovered the quantum portal.",
        "The starship traveled through hyperspace.",
    ]


class TestEmbeddingServiceAdapter:
    """Unit tests for EmbeddingServiceAdapter."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_init_creates_service_with_defaults(self):
        """Test that initialization creates service with default settings."""
        service = EmbeddingServiceAdapter(use_mock=True)

        assert service._model == "text-embedding-3-small"
        assert service._use_mock is True
        assert service.get_dimension() == 1536

    @pytest.mark.unit
    @pytest.mark.fast
    def test_init_with_custom_model(self):
        """Test that initialization accepts custom model."""
        service = EmbeddingServiceAdapter(model="text-embedding-3-large", use_mock=True)

        assert service._model == "text-embedding-3-large"
        assert service.get_dimension() == 3072

    @pytest.mark.unit
    @pytest.mark.fast
    def test_init_with_invalid_model_raises_error(self):
        """Test that invalid model name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            EmbeddingServiceAdapter(model="invalid-model", use_mock=True)

        assert "Unknown model" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_init_with_api_key_sets_key(self):
        """Test that API key is set when provided."""
        service = EmbeddingServiceAdapter(api_key="test-key", use_mock=True)

        assert service._api_key == "test-key"
        # use_mock=True takes precedence
        assert service._use_mock is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_service_implements_interface(self):
        """Test that EmbeddingServiceAdapter implements IEmbeddingService."""
        assert issubclass(EmbeddingServiceAdapter, IEmbeddingService)

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_embed_generates_vector_of_correct_dimension(
        self, mock_embedding_service: EmbeddingServiceAdapter
    ):
        """Test that embed generates vector with correct dimensions."""
        text = "The brave warrior fought with honor."
        embedding = await mock_embedding_service.embed(text)

        assert isinstance(embedding, list)
        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_embed_normalizes_vector_to_unit_length(
        self, mock_embedding_service: EmbeddingServiceAdapter
    ):
        """Test that generated embeddings are normalized to unit length."""
        text = "The brave warrior fought with honor."
        embedding = await mock_embedding_service.embed(text)

        # Calculate magnitude
        magnitude = sum(x**2 for x in embedding) ** 0.5

        # Should be approximately 1.0 (unit vector)
        assert abs(magnitude - 1.0) < 0.001

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_embed_returns_deterministic_results_for_same_input(
        self, mock_embedding_service: EmbeddingServiceAdapter
    ):
        """Test that same input produces same embedding (deterministic)."""
        text = "The brave warrior fought with honor."

        embedding1 = await mock_embedding_service.embed(text)
        embedding2 = await mock_embedding_service.embed(text)

        # Mock embeddings should be deterministic
        assert embedding1 == embedding2

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_embed_caches_results(
        self, mock_embedding_service: EmbeddingServiceAdapter
    ):
        """Test that embeddings are cached for repeated calls."""
        text = "The brave warrior fought with honor."

        # First call
        await mock_embedding_service.embed(text)
        cache_key = mock_embedding_service._get_cache_key(text)

        # Verify cache has the entry
        assert cache_key in mock_embedding_service._embedding_cache

        # Second call should use cache
        embedding = await mock_embedding_service.embed(text)
        cached = mock_embedding_service._embedding_cache[cache_key]

        assert embedding == cached

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_embed_with_empty_text_raises_error(
        self, mock_embedding_service: EmbeddingServiceAdapter
    ):
        """Test that empty text raises EmbeddingError."""
        with pytest.raises(EmbeddingError) as exc_info:
            await mock_embedding_service.embed("")

        assert exc_info.value.code == "EMPTY_TEXT"

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_embed_with_whitespace_only_raises_error(
        self, mock_embedding_service: EmbeddingServiceAdapter
    ):
        """Test that whitespace-only text raises EmbeddingError."""
        with pytest.raises(EmbeddingError) as exc_info:
            await mock_embedding_service.embed("   ")

        assert exc_info.value.code == "EMPTY_TEXT"

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_embed_different_texts_produce_different_embeddings(
        self, mock_embedding_service: EmbeddingServiceAdapter
    ):
        """Test that different texts produce different embeddings."""
        text1 = "The brave warrior fought with honor."
        text2 = "The ancient dragon guarded the mountain."

        embedding1 = await mock_embedding_service.embed(text1)
        embedding2 = await mock_embedding_service.embed(text2)

        # Different texts should produce different embeddings
        assert embedding1 != embedding2

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_embed_large_model_dimension(
        self, mock_embedding_service: EmbeddingServiceAdapter
    ):
        """Test that large model produces 3072-dimensional embeddings."""
        service = EmbeddingServiceAdapter(
            model="text-embedding-3-large", use_mock=True
        )
        text = "The brave warrior fought with honor."

        embedding = await service.embed(text)

        assert len(embedding) == 3072
        assert service.get_dimension() == 3072


class TestEmbeddingServiceBatch:
    """Unit tests for batch embedding functionality."""

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_embed_batch_with_multiple_texts(
        self, mock_embedding_service: EmbeddingServiceAdapter, sample_texts: List[str]
    ):
        """Test that batch embedding processes multiple texts."""
        embeddings = await mock_embedding_service.embed_batch(sample_texts)

        assert len(embeddings) == len(sample_texts)
        assert all(isinstance(e, list) for e in embeddings)
        assert all(len(e) == 1536 for e in embeddings)

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_embed_batch_maintains_order(
        self, mock_embedding_service: EmbeddingServiceAdapter, sample_texts: List[str]
    ):
        """Test that batch embeddings maintain input order."""
        embeddings = await mock_embedding_service.embed_batch(sample_texts)

        # Generate individual embeddings for comparison
        individual_embeddings = [
            await mock_embedding_service.embed(text) for text in sample_texts
        ]

        # Order should match
        for i in range(len(sample_texts)):
            assert embeddings[i] == individual_embeddings[i]

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_embed_batch_with_empty_list(
        self, mock_embedding_service: EmbeddingServiceAdapter
    ):
        """Test that batch embedding with empty list returns empty list."""
        embeddings = await mock_embedding_service.embed_batch([])

        assert embeddings == []

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_embed_batch_with_single_text(
        self, mock_embedding_service: EmbeddingServiceAdapter
    ):
        """Test that batch embedding works with single text."""
        embeddings = await mock_embedding_service.embed_batch(["test text"])

        assert len(embeddings) == 1
        assert len(embeddings[0]) == 1536

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_embed_batch_respects_batch_size(
        self, mock_embedding_service: EmbeddingServiceAdapter
    ):
        """Test that batch processing respects batch_size parameter."""
        # Create 5 texts, batch size of 2
        texts = [f"text {i}" for i in range(5)]
        embeddings = await mock_embedding_service.embed_batch(texts, batch_size=2)

        assert len(embeddings) == 5

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_embed_batch_caches_results(
        self, mock_embedding_service: EmbeddingServiceAdapter, sample_texts: List[str]
    ):
        """Test that batch embeddings are cached."""
        await mock_embedding_service.embed_batch(sample_texts)

        # Verify cache has entries for all texts
        for text in sample_texts:
            cache_key = mock_embedding_service._get_cache_key(text)
            assert cache_key in mock_embedding_service._embedding_cache


class TestEmbeddingServiceCache:
    """Unit tests for caching functionality."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_clear_cache_removes_cached_embeddings(
        self, mock_embedding_service: EmbeddingServiceAdapter
    ):
        """Test that clear_cache removes all cached embeddings."""
        # Add some items to cache
        mock_embedding_service._embedding_cache["key1"] = [0.1, 0.2]
        mock_embedding_service._embedding_cache["key2"] = [0.3, 0.4]

        # Clear cache
        mock_embedding_service.clear_cache()

        assert len(mock_embedding_service._embedding_cache) == 0

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_cache_key_is_deterministic(
        self, mock_embedding_service: EmbeddingServiceAdapter
    ):
        """Test that cache key generation is deterministic."""
        text = "The brave warrior fought with honor."

        key1 = mock_embedding_service._get_cache_key(text)
        key2 = mock_embedding_service._get_cache_key(text)

        assert key1 == key2

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_cache_key_differs_for_different_texts(
        self, mock_embedding_service: EmbeddingServiceAdapter
    ):
        """Test that different texts produce different cache keys."""
        text1 = "The brave warrior fought with honor."
        text2 = "The ancient dragon guarded the mountain."

        key1 = mock_embedding_service._get_cache_key(text1)
        key2 = mock_embedding_service._get_cache_key(text2)

        assert key1 != key2


class TestEmbeddingServiceModels:
    """Unit tests for different embedding models."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_dimension_for_ada_002(self):
        """Test dimension for text-embedding-ada-002."""
        service = EmbeddingServiceAdapter(model="text-embedding-ada-002", use_mock=True)
        assert service.get_dimension() == 1536

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_dimension_for_3_small(self):
        """Test dimension for text-embedding-3-small."""
        service = EmbeddingServiceAdapter(model="text-embedding-3-small", use_mock=True)
        assert service.get_dimension() == 1536

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_dimension_for_3_large(self):
        """Test dimension for text-embedding-3-large."""
        service = EmbeddingServiceAdapter(model="text-embedding-3-large", use_mock=True)
        assert service.get_dimension() == 3072


class TestBackwardCompatibility:
    """Tests for backward compatibility aliases."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_embedding_generator_adapter_alias_exists(self):
        """Test that EmbeddingGeneratorAdapter alias exists."""
        from src.contexts.knowledge.infrastructure.adapters.embedding_generator_adapter import (
            EmbeddingGeneratorAdapter,
        )

        assert EmbeddingGeneratorAdapter is EmbeddingServiceAdapter

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_embedding_generator_adapter_works(self):
        """Test that old alias still works."""
        from src.contexts.knowledge.infrastructure.adapters.embedding_generator_adapter import (
            EmbeddingGeneratorAdapter,
        )

        service = EmbeddingGeneratorAdapter(use_mock=True)
        embedding = await service.embed("test text")

        assert len(embedding) == 1536


class TestEmbeddingServiceApiMode:
    """Tests for API mode (when OPENAI_API_KEY is available)."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_api_mode_false_when_no_key(self, monkeypatch):
        """Test that API mode is disabled when no key is available."""
        # Remove any existing API key
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        service = EmbeddingServiceAdapter()
        assert service._use_mock is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_api_mode_true_when_key_provided(self):
        """Test that API mode is enabled when key is provided."""
        service = EmbeddingServiceAdapter(api_key="test-key")
        assert service._use_mock is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_force_mock_overrides_api_key(self):
        """Test that use_mock=True overrides API key presence."""
        service = EmbeddingServiceAdapter(api_key="test-key", use_mock=True)
        assert service._use_mock is True


class TestEmbeddingError:
    """Tests for EmbeddingError exception."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_embedding_error_has_message_and_code(self):
        """Test that EmbeddingError has message and code."""
        error = EmbeddingError("Test error", "TEST_CODE")

        assert str(error) == "Test error"
        assert error.code == "TEST_CODE"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_embedding_error_default_code(self):
        """Test that EmbeddingError has default code."""
        error = EmbeddingError("Test error")

        assert error.code == "EMBEDDING_ERROR"
