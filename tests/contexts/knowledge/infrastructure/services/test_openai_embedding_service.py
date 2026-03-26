"""Tests for OpenAIEmbeddingService.

This module provides tests for the OpenAI embedding service implementation.
Note: Tests requiring actual OpenAI API are marked with 'requires_openai'
marker and skipped by default.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.contexts.knowledge.application.ports.i_embedding_service import EmbeddingError
from src.contexts.knowledge.infrastructure.services.openai_embedding_service import (
    OpenAIEmbeddingService,
)

if TYPE_CHECKING:
    from collections.abc import Generator


class TestOpenAIEmbeddingService:
    """Test suite for OpenAIEmbeddingService."""

    def test_init_with_default_model(self) -> None:
        """Test initialization with default model."""
        service = OpenAIEmbeddingService(api_key="test-key")
        assert service._api_key == "test-key"
        assert service._model == "text-embedding-3-small"
        assert service._client is None

    def test_init_with_custom_model(self) -> None:
        """Test initialization with custom model."""
        service = OpenAIEmbeddingService(
            api_key="test-key", model="text-embedding-3-large"
        )
        assert service._model == "text-embedding-3-large"

    def test_init_empty_api_key(self) -> None:
        """Test initialization with empty API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            OpenAIEmbeddingService(api_key="")


class TestOpenAIEmbeddingServiceWithMock:
    """Test suite for OpenAIEmbeddingService with mocked openai."""

    @pytest.fixture(autouse=True)
    def setup_mock(self) -> "Generator[None, None, None]":
        """Setup mock openai module for all tests in this class."""
        mock_openai = MagicMock()
        mock_client = MagicMock()
        mock_openai.AsyncOpenAI.return_value = mock_client

        with patch.dict(sys.modules, {"openai": mock_openai}):
            with patch(
                "src.contexts.knowledge.infrastructure.services.openai_embedding_service.openai",
                mock_openai,
                create=True,
            ):
                yield

    def test_get_client_creates_client(self, setup_mock: None) -> None:
        """Test that _get_client creates a new client."""
        import sys

        mock_openai = sys.modules["openai"]

        service = OpenAIEmbeddingService(api_key="test-key")
        client = service._get_client()

        assert client is not None
        assert service._client is not None
        mock_openai.AsyncOpenAI.assert_called_once_with(api_key="test-key")

    def test_get_client_reuses_client(self, setup_mock: None) -> None:
        """Test that _get_client reuses existing client."""
        import sys

        mock_openai = sys.modules["openai"]

        service = OpenAIEmbeddingService(api_key="test-key")

        # First call
        client1 = service._get_client()
        # Second call should return same client
        client2 = service._get_client()

        assert client1 is client2
        mock_openai.AsyncOpenAI.assert_called_once()

    def test_get_client_import_error(self) -> None:
        """Test that ImportError is raised when openai is not installed."""
        with patch.dict(sys.modules, {"openai": None}):
            service = OpenAIEmbeddingService(api_key="test-key")
            with pytest.raises(ImportError) as exc_info:
                service._get_client()
            assert "openai is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_embed_success(self, setup_mock: None) -> None:
        """Test successful embedding generation."""
        import sys

        mock_openai = sys.modules["openai"]
        service = OpenAIEmbeddingService(api_key="test-key")
        mock_client = MagicMock()
        mock_openai.AsyncOpenAI.return_value = mock_client

        # Mock the embeddings.create response
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)

        result = await service.embed("Hello world")

        assert result == [0.1, 0.2, 0.3]
        mock_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small",
            input="Hello world",
        )

    @pytest.mark.asyncio
    async def test_embed_empty_text(self, setup_mock: None) -> None:
        """Test embedding with empty text."""
        service = OpenAIEmbeddingService(api_key="test-key")

        with pytest.raises(ValueError, match="Text cannot be empty"):
            await service.embed("")

    @pytest.mark.asyncio
    async def test_embed_api_error(self, setup_mock: None) -> None:
        """Test embedding handles API error."""
        import sys

        mock_openai = sys.modules["openai"]
        service = OpenAIEmbeddingService(api_key="test-key")
        mock_client = MagicMock()
        mock_openai.AsyncOpenAI.return_value = mock_client
        mock_client.embeddings.create = AsyncMock(side_effect=Exception("API Error"))

        with pytest.raises(EmbeddingError) as exc_info:
            await service.embed("Hello world")
        assert "Failed to generate embedding" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_embed_batch_success(self, setup_mock: None) -> None:
        """Test successful batch embedding generation."""
        import sys

        mock_openai = sys.modules["openai"]
        service = OpenAIEmbeddingService(api_key="test-key")
        mock_client = MagicMock()
        mock_openai.AsyncOpenAI.return_value = mock_client

        # Mock the embeddings.create response
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1, 0.2]),
            MagicMock(embedding=[0.3, 0.4]),
            MagicMock(embedding=[0.5, 0.6]),
        ]
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)

        texts = ["text1", "text2", "text3"]
        result = await service.embed_batch(texts)

        assert len(result) == 3
        assert result[0] == [0.1, 0.2]
        assert result[1] == [0.3, 0.4]
        assert result[2] == [0.5, 0.6]
        mock_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small",
            input=texts,
        )

    @pytest.mark.asyncio
    async def test_embed_batch_empty_list(self, setup_mock: None) -> None:
        """Test batch embedding with empty list."""
        service = OpenAIEmbeddingService(api_key="test-key")

        with pytest.raises(ValueError, match="Texts list cannot be empty"):
            await service.embed_batch([])

    @pytest.mark.asyncio
    async def test_embed_batch_all_empty_strings(self, setup_mock: None) -> None:
        """Test batch embedding with all empty strings."""
        service = OpenAIEmbeddingService(api_key="test-key")

        with pytest.raises(ValueError, match="All texts are empty"):
            await service.embed_batch(["", "", ""])

    @pytest.mark.asyncio
    async def test_embed_batch_with_empty_strings(self, setup_mock: None) -> None:
        """Test batch embedding filters out empty strings."""
        import sys

        mock_openai = sys.modules["openai"]
        service = OpenAIEmbeddingService(api_key="test-key")
        mock_client = MagicMock()
        mock_openai.AsyncOpenAI.return_value = mock_client

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2])]
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)

        texts = ["valid text", "", "another valid"]
        await service.embed_batch(texts)

        # Only valid texts should be sent to API
        mock_client.embeddings.create.assert_called_once()
        call_args = mock_client.embeddings.create.call_args[1]
        assert len(call_args["input"]) == 2
        assert "" not in call_args["input"]

    @pytest.mark.asyncio
    async def test_embed_batch_api_error(self, setup_mock: None) -> None:
        """Test batch embedding handles API error."""
        import sys

        mock_openai = sys.modules["openai"]
        service = OpenAIEmbeddingService(api_key="test-key")
        mock_client = MagicMock()
        mock_openai.AsyncOpenAI.return_value = mock_client
        mock_client.embeddings.create = AsyncMock(side_effect=Exception("API Error"))

        with pytest.raises(EmbeddingError) as exc_info:
            await service.embed_batch(["text1", "text2"])
        assert "Failed to generate batch embeddings" in str(exc_info.value)

    def test_get_dimension_text_embedding_3_small(self) -> None:
        """Test dimension for text-embedding-3-small."""
        service = OpenAIEmbeddingService(
            api_key="test-key", model="text-embedding-3-small"
        )
        assert service.get_dimension() == 1536

    def test_get_dimension_text_embedding_3_large(self) -> None:
        """Test dimension for text-embedding-3-large."""
        service = OpenAIEmbeddingService(
            api_key="test-key", model="text-embedding-3-large"
        )
        assert service.get_dimension() == 3072

    def test_get_dimension_text_embedding_ada_002(self) -> None:
        """Test dimension for text-embedding-ada-002."""
        service = OpenAIEmbeddingService(
            api_key="test-key", model="text-embedding-ada-002"
        )
        assert service.get_dimension() == 1536

    def test_get_dimension_caching(self) -> None:
        """Test that dimension is cached."""
        service = OpenAIEmbeddingService(api_key="test-key")

        # First call should set cache
        dim1 = service.get_dimension()
        # Second call should return cached value
        dim2 = service.get_dimension()

        assert dim1 == dim2
        assert service._dimension is not None

    def test_get_dimension_unknown_model(self) -> None:
        """Test dimension for unknown model returns default."""
        service = OpenAIEmbeddingService(api_key="test-key", model="unknown-model")
        # Should return default dimension of 1536
        assert service.get_dimension() == 1536


@pytest.mark.requires_openai
class TestOpenAIEmbeddingServiceIntegration:
    """Integration tests requiring actual OpenAI API.

    These tests are skipped unless explicitly enabled.
    """

    @pytest.fixture
    def openai_service(self) -> OpenAIEmbeddingService:
        """Provide OpenAIEmbeddingService with real API key."""
        import os

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            pytest.skip("OPENAI_API_KEY environment variable not set")

        return OpenAIEmbeddingService(api_key=api_key)

    @pytest.mark.asyncio
    async def test_real_embed(self, openai_service: OpenAIEmbeddingService) -> None:
        """Test embedding with real OpenAI API."""
        result = await openai_service.embed("Hello world")

        assert isinstance(result, list)
        assert len(result) == 1536  # text-embedding-3-small dimension
        assert all(isinstance(x, float) for x in result)

    @pytest.mark.asyncio
    async def test_real_embed_batch(
        self, openai_service: OpenAIEmbeddingService
    ) -> None:
        """Test batch embedding with real OpenAI API."""
        texts = ["Hello world", "Test sentence", "Another example"]
        results = await openai_service.embed_batch(texts)

        assert len(results) == 3
        for embedding in results:
            assert isinstance(embedding, list)
            assert len(embedding) == 1536
            assert all(isinstance(x, float) for x in embedding)
