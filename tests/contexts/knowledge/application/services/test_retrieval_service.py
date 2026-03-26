"""Tests for RetrievalService."""

from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.contexts.knowledge.application.ports.i_embedding_service import (
    EmbeddingError,
    IEmbeddingService,
)
from src.contexts.knowledge.application.ports.i_vector_store import (
    IVectorStore,
    QueryResult,
)
from src.contexts.knowledge.application.services.knowledge_ingestion_service import (
    RetrievedChunk,
    SourceType,
)
from src.contexts.knowledge.application.services.rerank_service import RerankService
from src.contexts.knowledge.application.services.retrieval_service import (
    RetrievalOptions,
    RetrievalResult,
    RetrievalService,
)


class MockEmbeddingService(IEmbeddingService):
    """Mock embedding service for testing."""

    def __init__(self):
        self.embed = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4, 0.5])
        self.embed_batch = AsyncMock(return_value=[[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]])
        self._dimension = 5

    async def embed(self, text: str) -> list[float]:
        return await self.embed(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return await self.embed_batch(texts)

    def get_dimension(self) -> int:
        return self._dimension


class MockVectorStore(IVectorStore):
    """Mock vector store for testing."""

    def __init__(self):
        self.upsert = AsyncMock()
        self.query = AsyncMock()
        self.delete = AsyncMock()
        self.clear = AsyncMock()
        self.count = AsyncMock(return_value=10)
        self.health_check = AsyncMock(return_value=True)

    async def upsert(
        self,
        collection: str,
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        ids: list[str],
    ) -> None:
        await self.upsert(collection, documents, embeddings, metadatas, ids)

    async def query(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        where: dict[str, Any] | None = None,
        collection: str = "knowledge",
    ) -> list[QueryResult]:
        return await self.query(query_embedding, n_results, where, collection)

    async def delete(self, collection: str, ids: list[str]) -> None:
        await self.delete(collection, ids)

    async def clear(self, collection: str) -> None:
        await self.clear(collection)

    async def count(self, collection: str) -> int:
        return await self.count(collection)

    async def health_check(self) -> bool:
        return await self.health_check()


class MockRerankService(RerankService):
    """Mock rerank service for testing."""

    def __init__(self):
        self.rerank = AsyncMock()

    async def rerank(
        self, query: str, documents: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return await self.rerank(query, documents)


@pytest.fixture
def mock_embedding_service():
    """Create mock embedding service."""
    service = MockEmbeddingService()
    service.embed = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4, 0.5])
    service.embed_batch = AsyncMock(return_value=[[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]])
    return service


@pytest.fixture
def mock_vector_store():
    """Create mock vector store."""
    store = MockVectorStore()
    store.query = AsyncMock(
        return_value=[
            QueryResult(
                id="doc-1",
                text="First document content",
                score=0.95,
                metadata={"source_type": "document", "title": "Doc 1"},
            ),
            QueryResult(
                id="doc-2",
                text="Second document content",
                score=0.85,
                metadata={"source_type": "url", "title": "Doc 2"},
            ),
        ]
    )
    return store


@pytest.fixture
def mock_rerank_service():
    """Create mock rerank service."""
    from dataclasses import dataclass

    @dataclass
    class RerankResult:
        id: str
        score: float

    service = MockRerankService()
    service.rerank = AsyncMock(
        return_value=[
            RerankResult(id="0", score=0.98),
            RerankResult(id="1", score=0.75),
        ]
    )
    return service


@pytest.fixture
def retrieval_service(mock_embedding_service, mock_vector_store):
    """Create RetrievalService without reranking."""
    return RetrievalService(
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,
        rerank_service=None,
    )


@pytest.fixture
def retrieval_service_with_rerank(
    mock_embedding_service, mock_vector_store, mock_rerank_service
):
    """Create RetrievalService with reranking."""
    return RetrievalService(
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,
        rerank_service=mock_rerank_service,
    )


class TestRetrievalService:
    """Test suite for RetrievalService."""

    @pytest.mark.asyncio
    async def test_retrieve_relevant_success(
        self, retrieval_service, mock_embedding_service, mock_vector_store
    ):
        """Test successful retrieval of relevant chunks."""
        # Arrange
        query = "test query"
        k = 5

        # Act
        result = await retrieval_service.retrieve_relevant(query, k=k)

        # Assert
        assert isinstance(result, RetrievalResult)
        assert result.total_found == 2
        assert len(result.chunks) == 2
        mock_embedding_service.embed.assert_called_once_with(query)
        mock_vector_store.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_relevant_default_options(
        self, retrieval_service, mock_vector_store
    ):
        """Test retrieval with default options."""
        # Arrange
        query = "test query"

        # Act
        result = await retrieval_service.retrieve_relevant(query)

        # Assert
        assert isinstance(result, RetrievalResult)
        assert len(result.chunks) > 0

    @pytest.mark.asyncio
    async def test_retrieve_relevant_with_custom_options(
        self, retrieval_service, mock_vector_store
    ):
        """Test retrieval with custom options."""
        # Arrange
        query = "test query"
        options = RetrievalOptions(min_score=0.9, max_results=3)

        # Act
        result = await retrieval_service.retrieve_relevant(query, options=options)

        # Assert
        assert isinstance(result, RetrievalResult)

    @pytest.mark.asyncio
    async def test_retrieve_relevant_filters_by_min_score(
        self, retrieval_service, mock_vector_store
    ):
        """Test that results are filtered by minimum score."""
        # Arrange
        query = "test query"
        options = RetrievalOptions(min_score=0.9)

        mock_vector_store.query.return_value = [
            QueryResult(
                id="high-score",
                text="High score content",
                score=0.95,
                metadata={"source_type": "document"},
            ),
            QueryResult(
                id="low-score",
                text="Low score content",
                score=0.5,
                metadata={"source_type": "document"},
            ),
        ]

        # Act
        result = await retrieval_service.retrieve_relevant(query, options=options)

        # Assert
        assert len(result.chunks) == 1
        assert result.chunks[0].score >= 0.9

    @pytest.mark.asyncio
    async def test_retrieve_relevant_source_type_conversion(
        self, retrieval_service, mock_vector_store
    ):
        """Test source type conversion from metadata."""
        # Arrange
        query = "test query"
        mock_vector_store.query.return_value = [
            QueryResult(
                id="doc-1",
                text="Content",
                score=0.9,
                metadata={"source_type": "url"},
            ),
            QueryResult(
                id="doc-2",
                text="Content",
                score=0.8,
                metadata={"source_type": "api"},
            ),
            QueryResult(
                id="doc-3",
                text="Content",
                score=0.7,
                metadata={"source_type": "manual"},
            ),
        ]

        # Act
        result = await retrieval_service.retrieve_relevant(query)

        # Assert
        assert len(result.chunks) == 3
        assert result.chunks[0].source_type == SourceType.URL
        assert result.chunks[1].source_type == SourceType.API
        assert result.chunks[2].source_type == SourceType.MANUAL

    @pytest.mark.asyncio
    async def test_retrieve_relevant_invalid_source_type_defaults_to_document(
        self, retrieval_service, mock_vector_store
    ):
        """Test invalid source type defaults to DOCUMENT."""
        # Arrange
        query = "test query"
        mock_vector_store.query.return_value = [
            QueryResult(
                id="doc-1",
                text="Content",
                score=0.9,
                metadata={"source_type": "invalid_type"},
            ),
        ]

        # Act
        result = await retrieval_service.retrieve_relevant(query)

        # Assert
        assert len(result.chunks) == 1
        assert result.chunks[0].source_type == SourceType.DOCUMENT

    @pytest.mark.asyncio
    async def test_retrieve_relevant_with_reranking(
        self,
        retrieval_service_with_rerank,
        mock_vector_store,
        mock_rerank_service,
    ):
        """Test retrieval with reranking enabled."""
        # Arrange
        query = "test query"
        options = RetrievalOptions(enable_rerank=True)

        # Act
        result = await retrieval_service_with_rerank.retrieve_relevant(
            query, options=options
        )

        # Assert
        mock_rerank_service.rerank.assert_called_once()
        assert isinstance(result, RetrievalResult)
        assert len(result.chunks) == 2

    @pytest.mark.asyncio
    async def test_retrieve_relevant_no_results(
        self, retrieval_service, mock_vector_store
    ):
        """Test retrieval when no results found."""
        # Arrange
        query = "test query"
        mock_vector_store.query.return_value = []

        # Act
        result = await retrieval_service.retrieve_relevant(query)

        # Assert
        assert isinstance(result, RetrievalResult)
        assert result.total_found == 0
        assert len(result.chunks) == 0

    @pytest.mark.asyncio
    async def test_retrieve_relevant_empty_query(self, retrieval_service):
        """Test retrieval with empty query."""
        # Arrange
        query = ""

        # Act
        result = await retrieval_service.retrieve_relevant(query)

        # Assert
        assert isinstance(result, RetrievalResult)

    @pytest.mark.asyncio
    async def test_retrieve_relevant_preserves_metadata(
        self, retrieval_service, mock_vector_store
    ):
        """Test that metadata is preserved in results."""
        # Arrange
        query = "test query"
        metadata = {"key1": "value1", "key2": "value2", "source_type": "document"}
        mock_vector_store.query.return_value = [
            QueryResult(
                id="doc-1",
                text="Content",
                score=0.9,
                metadata=metadata,
            ),
        ]

        # Act
        result = await retrieval_service.retrieve_relevant(query)

        # Assert
        assert len(result.chunks) == 1
        assert result.chunks[0].metadata == metadata


class TestRetrievalOptions:
    """Test suite for RetrievalOptions."""

    def test_retrieval_options_defaults(self):
        """Test default values for RetrievalOptions."""
        # Act
        options = RetrievalOptions()

        # Assert
        assert options.min_score == 0.0
        assert options.enable_rerank is True
        assert options.max_results == 10

    def test_retrieval_options_custom_values(self):
        """Test custom values for RetrievalOptions."""
        # Act
        options = RetrievalOptions(min_score=0.5, enable_rerank=False, max_results=5)

        # Assert
        assert options.min_score == 0.5
        assert options.enable_rerank is False
        assert options.max_results == 5


class TestRetrievalResult:
    """Test suite for RetrievalResult."""

    def test_retrieval_result_defaults(self):
        """Test default values for RetrievalResult."""
        # Act
        result = RetrievalResult()

        # Assert
        assert result.chunks == []
        assert result.total_found == 0

    def test_retrieval_result_with_chunks(self):
        """Test RetrievalResult with chunks."""
        # Arrange
        chunks = [
            RetrievedChunk(
                content="Chunk 1",
                score=0.9,
                source_type=SourceType.DOCUMENT,
                metadata={},
            ),
            RetrievedChunk(
                content="Chunk 2", score=0.8, source_type=SourceType.URL, metadata={}
            ),
        ]

        # Act
        result = RetrievalResult(chunks=chunks, total_found=2)

        # Assert
        assert result.chunks == chunks
        assert result.total_found == 2


class TestRetrievalServiceEdgeCases:
    """Test edge cases for RetrievalService."""

    @pytest.mark.asyncio
    async def test_retrieve_relevant_embedding_service_error(
        self, retrieval_service, mock_embedding_service
    ):
        """Test handling embedding service error."""
        # Arrange
        query = "test query"
        mock_embedding_service.embed.side_effect = EmbeddingError("Embedding failed")

        # Act & Assert
        with pytest.raises(EmbeddingError):
            await retrieval_service.retrieve_relevant(query)

    @pytest.mark.asyncio
    async def test_retrieve_relevant_vector_store_error(
        self, retrieval_service, mock_vector_store
    ):
        """Test handling vector store error."""
        # Arrange
        query = "test query"
        mock_vector_store.query.side_effect = Exception("Vector store error")

        # Act & Assert
        with pytest.raises(Exception):
            await retrieval_service.retrieve_relevant(query)

    @pytest.mark.asyncio
    async def test_retrieve_relevant_reranking_error(
        self,
        retrieval_service_with_rerank,
        mock_vector_store,
        mock_rerank_service,
    ):
        """Test handling reranking service error."""
        # Arrange
        query = "test query"
        options = RetrievalOptions(enable_rerank=True)
        mock_rerank_service.rerank.side_effect = Exception("Reranking failed")

        # Act & Assert
        with pytest.raises(Exception):
            await retrieval_service_with_rerank.retrieve_relevant(
                query, options=options
            )

    @pytest.mark.asyncio
    async def test_retrieve_relevant_all_results_filtered_by_score(
        self, retrieval_service, mock_vector_store
    ):
        """Test when all results are filtered out by min_score."""
        # Arrange
        query = "test query"
        options = RetrievalOptions(min_score=0.95)
        mock_vector_store.query.return_value = [
            QueryResult(
                id="low-1",
                text="Low score 1",
                score=0.5,
                metadata={"source_type": "document"},
            ),
            QueryResult(
                id="low-2",
                text="Low score 2",
                score=0.6,
                metadata={"source_type": "document"},
            ),
        ]

        # Act
        result = await retrieval_service.retrieve_relevant(query, options=options)

        # Assert
        assert len(result.chunks) == 0
        assert result.total_found == 0

    @pytest.mark.asyncio
    async def test_retrieve_relevant_no_rerank_service_with_enable_flag(
        self, retrieval_service
    ):
        """Test retrieval when rerank is enabled but no service provided."""
        # Arrange
        query = "test query"
        options = RetrievalOptions(enable_rerank=True)

        # Act
        result = await retrieval_service.retrieve_relevant(query, options=options)

        # Assert
        assert isinstance(result, RetrievalResult)
        # Should still work without rerank service

    @pytest.mark.asyncio
    async def test_retrieve_relevant_reranking_with_empty_results(
        self,
        retrieval_service_with_rerank,
        mock_vector_store,
        mock_rerank_service,
    ):
        """Test reranking when no results to rerank."""
        # Arrange
        query = "test query"
        options = RetrievalOptions(enable_rerank=True)
        mock_vector_store.query.return_value = []

        # Act
        result = await retrieval_service_with_rerank.retrieve_relevant(
            query, options=options
        )

        # Assert
        mock_rerank_service.rerank.assert_not_called()
        assert len(result.chunks) == 0

    @pytest.mark.asyncio
    async def test_retrieve_relevant_mixed_source_types(
        self, retrieval_service, mock_vector_store
    ):
        """Test retrieval with mixed source types."""
        # Arrange
        query = "test query"
        mock_vector_store.query.return_value = [
            QueryResult(
                id="doc-1",
                text="Document content",
                score=0.9,
                metadata={"source_type": "document"},
            ),
            QueryResult(
                id="url-1",
                text="URL content",
                score=0.85,
                metadata={"source_type": "url"},
            ),
            QueryResult(
                id="api-1",
                text="API content",
                score=0.8,
                metadata={"source_type": "api"},
            ),
            QueryResult(
                id="manual-1",
                text="Manual content",
                score=0.75,
                metadata={"source_type": "manual"},
            ),
        ]

        # Act
        result = await retrieval_service.retrieve_relevant(query)

        # Assert
        assert len(result.chunks) == 4
        source_types = {chunk.source_type for chunk in result.chunks}
        assert SourceType.DOCUMENT in source_types
        assert SourceType.URL in source_types
        assert SourceType.API in source_types
        assert SourceType.MANUAL in source_types

    @pytest.mark.asyncio
    async def test_retrieve_relevant_handles_none_metadata(
        self, retrieval_service, mock_vector_store
    ):
        """Test handling of None metadata values."""
        # Arrange
        query = "test query"
        mock_vector_store.query.return_value = [
            QueryResult(
                id="doc-1",
                text="Content",
                score=0.9,
                metadata={"source_type": None},  # None source_type
            ),
        ]

        # Act & Assert
        # Should handle None gracefully (may default to DOCUMENT)
        result = await retrieval_service.retrieve_relevant(query)
        assert isinstance(result, RetrievalResult)


class TestRetrievalServiceIntegration:
    """Integration-style tests for RetrievalService."""

    @pytest.mark.asyncio
    async def test_full_retrieval_workflow(self, retrieval_service_with_rerank):
        """Test complete retrieval workflow."""
        # Arrange
        query = "What is machine learning?"
        options = RetrievalOptions(min_score=0.5, enable_rerank=True, max_results=5)

        # Act
        result = await retrieval_service_with_rerank.retrieve_relevant(
            query, k=5, options=options
        )

        # Assert
        assert isinstance(result, RetrievalResult)
        # Result should have chunks with proper structure
        for chunk in result.chunks:
            assert hasattr(chunk, "content")
            assert hasattr(chunk, "score")
            assert hasattr(chunk, "source_type")
            assert hasattr(chunk, "metadata")

    @pytest.mark.asyncio
    async def test_retrieval_result_scores_ordered(
        self, retrieval_service, mock_vector_store
    ):
        """Test that results maintain proper score ordering."""
        # Arrange
        query = "test query"
        mock_vector_store.query.return_value = [
            QueryResult(
                id="doc-1",
                text="First",
                score=0.95,
                metadata={"source_type": "document"},
            ),
            QueryResult(
                id="doc-2",
                text="Second",
                score=0.85,
                metadata={"source_type": "document"},
            ),
            QueryResult(
                id="doc-3",
                text="Third",
                score=0.75,
                metadata={"source_type": "document"},
            ),
        ]

        # Act
        result = await retrieval_service.retrieve_relevant(query)

        # Assert
        scores = [chunk.score for chunk in result.chunks]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_retrieval_with_special_characters_in_query(self, retrieval_service):
        """Test retrieval with special characters in query."""
        # Arrange
        queries = [
            "test with 'quotes'",
            'test with "double quotes"',
            "test with <html>tags</html>",
            "test with unicode: 你好世界",
            "test with new\nlines",
        ]

        # Act & Assert
        for query in queries:
            result = await retrieval_service.retrieve_relevant(query)
            assert isinstance(result, RetrievalResult)

    @pytest.mark.asyncio
    async def test_retrieval_options_validation(self, retrieval_service):
        """Test that options are properly validated."""
        # Arrange & Act & Assert
        # Valid options
        valid_options = RetrievalOptions(min_score=0.5, max_results=100)
        result = await retrieval_service.retrieve_relevant(
            "test", options=valid_options
        )
        assert isinstance(result, RetrievalResult)

        # Edge case: negative min_score
        negative_options = RetrievalOptions(min_score=-0.1)
        result = await retrieval_service.retrieve_relevant(
            "test", options=negative_options
        )
        assert isinstance(result, RetrievalResult)

        # Edge case: zero max_results
        zero_options = RetrievalOptions(max_results=0)
        result = await retrieval_service.retrieve_relevant("test", options=zero_options)
        assert isinstance(result, RetrievalResult)
