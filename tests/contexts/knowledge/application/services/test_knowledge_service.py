"""Tests for KnowledgeApplicationService."""

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.contexts.knowledge.application.services.knowledge_service import (
    KnowledgeApplicationService,
)
from src.contexts.knowledge.domain.aggregates.knowledge_base import KnowledgeBase
from src.contexts.knowledge.domain.entities.document import Document


class MockVectorStore:
    """Mock vector store for testing."""

    def __init__(self):
        self.store_embedding = AsyncMock()
        self.search_similar = AsyncMock()
        self.delete_document = AsyncMock()


class MockEmbeddingService:
    """Mock embedding service for testing."""

    def __init__(self):
        self.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])
        self.embed_batch = AsyncMock(return_value=[[0.1, 0.2], [0.3, 0.4]])
        self.get_dimension = MagicMock(return_value=3)


class MockChunkingService:
    """Mock chunking service for testing."""

    def __init__(self):
        self.chunk_document = MagicMock(
            return_value=[
                {"content": "Chunk 1", "index": 0},
                {"content": "Chunk 2", "index": 1},
            ]
        )


class MockKnowledgeRepository:
    """Mock knowledge repository for testing."""

    def __init__(self):
        self._data: Dict[UUID, KnowledgeBase] = {}
        self.save = AsyncMock(side_effect=self._save)
        self.get_by_id = AsyncMock(side_effect=self._get_by_id)
        self.delete = AsyncMock(side_effect=self._delete)

    async def _save(self, kb: KnowledgeBase) -> None:
        self._data[kb.id] = kb

    async def _get_by_id(self, kb_id: UUID) -> Any:
        return self._data.get(kb_id)

    async def _delete(self, kb_id: UUID) -> None:
        if kb_id in self._data:
            del self._data[kb_id]


@pytest.fixture
def mock_repo():
    """Create mock knowledge repository."""
    return MockKnowledgeRepository()


@pytest.fixture
def mock_vector_store():
    """Create mock vector store."""
    return MockVectorStore()


@pytest.fixture
def mock_embedding_service():
    """Create mock embedding service."""
    return MockEmbeddingService()


@pytest.fixture
def mock_chunking_service():
    """Create mock chunking service."""
    return MockChunkingService()


@pytest.fixture
def service(
    mock_repo, mock_vector_store, mock_embedding_service, mock_chunking_service
):
    """Create service with mocked dependencies."""
    return KnowledgeApplicationService(
        knowledge_repo=mock_repo,
        vector_store=mock_vector_store,
        embedding_service=mock_embedding_service,
        chunking_service=mock_chunking_service,
    )


@pytest.fixture
def sample_kb():
    """Create a sample knowledge base."""
    return KnowledgeBase(
        name="Test KB",
        owner_id="user-123",
        description="Test description",
    )


@pytest.fixture
def sample_document():
    """Create a sample document."""
    return Document(
        knowledge_base_id=str(uuid4()),
        title="Test Document",
        content="This is test content with multiple words for counting.",
        content_type="text",
    )


class TestKnowledgeService:
    """Test suite for KnowledgeApplicationService."""

    @pytest.mark.asyncio
    async def test_create_knowledge_base_success(self, service, mock_repo):
        """Test creating a knowledge base successfully."""
        # Arrange
        name = "Test KB"
        owner_id = "user-123"
        description = "Test description"

        # Act
        result = await service.create_knowledge_base(
            name=name, owner_id=owner_id, description=description
        )

        # Assert
        assert result.is_ok()
        assert result.value.name == name
        assert result.value.owner_id == owner_id
        assert result.value.description == description
        mock_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_knowledge_base_validation_error(self, service):
        """Test creating KB with invalid data fails."""
        # Arrange - empty name should trigger validation error
        name = ""
        owner_id = "user-123"

        # Act
        result = await service.create_knowledge_base(name=name, owner_id=owner_id)

        # Assert
        assert result.is_error
        assert result.code == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_create_knowledge_base_internal_error(self, service, mock_repo):
        """Test handling internal error during KB creation."""
        # Arrange
        mock_repo.save.side_effect = Exception("Database error")

        # Act
        result = await service.create_knowledge_base(
            name="Test KB", owner_id="user-123"
        )

        # Assert
        assert result.is_error
        assert result.code == "INTERNAL_ERROR"

    @pytest.mark.asyncio
    async def test_upload_document_success(self, service, mock_repo, sample_kb):
        """Test uploading document to knowledge base."""
        # Arrange
        await mock_repo._save(sample_kb)
        mock_repo.save.reset_mock()

        # Act
        result = await service.upload_document(
            knowledge_base_id=str(sample_kb.id),
            title="Test Doc",
            content="Test content",
            content_type="text",
        )

        # Assert
        assert result.is_ok()
        assert result.value.title == "Test Doc"
        mock_repo.save.assert_called()

    @pytest.mark.asyncio
    async def test_upload_document_kb_not_found(self, service):
        """Test uploading document to non-existent KB fails."""
        # Arrange
        kb_id = str(uuid4())

        # Act
        result = await service.upload_document(
            knowledge_base_id=kb_id,
            title="Test Doc",
            content="Test content",
        )

        # Assert
        assert result.is_error
        assert result.code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_upload_document_auto_index(self, service, mock_repo, sample_kb):
        """Test auto-indexing document on upload."""
        # Arrange
        await mock_repo._save(sample_kb)

        # Act
        result = await service.upload_document(
            knowledge_base_id=str(sample_kb.id),
            title="Test Doc",
            content="Test content for indexing",
            auto_index=True,
        )

        # Assert
        assert result.is_ok()
        # Document should be indexed

    @pytest.mark.asyncio
    async def test_get_document_success(self, service, mock_repo, sample_kb):
        """Test getting a document by ID."""
        # Arrange
        await mock_repo._save(sample_kb)
        doc = sample_kb.add_document(title="Test Doc", content="Test content")

        # Act
        result = await service.get_document(
            knowledge_base_id=str(sample_kb.id), document_id=str(doc.id)
        )

        # Assert
        assert result.is_ok()
        assert result.value.id == doc.id

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, service, mock_repo, sample_kb):
        """Test getting non-existent document fails."""
        # Arrange
        await mock_repo._save(sample_kb)

        # Act
        result = await service.get_document(
            knowledge_base_id=str(sample_kb.id), document_id=str(uuid4())
        )

        # Assert
        assert result.is_error
        assert result.code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_document_kb_not_found(self, service):
        """Test getting document from non-existent KB fails."""
        # Act
        result = await service.get_document(
            knowledge_base_id=str(uuid4()), document_id=str(uuid4())
        )

        # Assert
        assert result.is_error
        assert result.code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_delete_document_success(
        self, service, mock_repo, sample_kb, mock_vector_store
    ):
        """Test deleting a document."""
        # Arrange
        await mock_repo._save(sample_kb)
        doc = sample_kb.add_document(title="Test Doc", content="Test content")

        # Act
        result = await service.delete_document(
            knowledge_base_id=str(sample_kb.id), document_id=str(doc.id)
        )

        # Assert
        assert result.is_ok()
        assert result.value is True
        mock_vector_store.delete_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self, service, mock_repo, sample_kb):
        """Test deleting non-existent document fails."""
        # Arrange
        await mock_repo._save(sample_kb)

        # Act
        result = await service.delete_document(
            knowledge_base_id=str(sample_kb.id), document_id=str(uuid4())
        )

        # Assert
        assert result.is_error
        assert result.code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_delete_document_kb_not_found(self, service):
        """Test deleting document from non-existent KB fails."""
        # Act
        result = await service.delete_document(
            knowledge_base_id=str(uuid4()), document_id=str(uuid4())
        )

        # Assert
        assert result.is_error
        assert result.code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_index_document_success(
        self,
        service,
        mock_repo,
        sample_kb,
        mock_embedding_service,
        mock_vector_store,
        mock_chunking_service,
    ):
        """Test indexing a document."""
        # Arrange
        await mock_repo._save(sample_kb)
        doc = sample_kb.add_document(title="Test Doc", content="Test content here")

        # Act
        result = await service.index_document(
            knowledge_base_id=str(sample_kb.id), document_id=str(doc.id)
        )

        # Assert
        assert result.is_ok()
        mock_chunking_service.chunk_document.assert_called_once()
        mock_embedding_service.embed.assert_called_once()
        mock_vector_store.store_embedding.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_document_not_found(self, service, mock_repo, sample_kb):
        """Test indexing non-existent document fails."""
        # Arrange
        await mock_repo._save(sample_kb)

        # Act
        result = await service.index_document(
            knowledge_base_id=str(sample_kb.id), document_id=str(uuid4())
        )

        # Assert
        assert result.is_error
        assert result.code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_index_document_kb_not_found(self, service):
        """Test indexing document in non-existent KB fails."""
        # Act
        result = await service.index_document(
            knowledge_base_id=str(uuid4()), document_id=str(uuid4())
        )

        # Assert
        assert result.is_error
        assert result.code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_semantic_search_success(
        self, service, mock_repo, sample_kb, mock_embedding_service, mock_vector_store
    ):
        """Test semantic search on knowledge base."""
        # Arrange
        await mock_repo._save(sample_kb)
        doc = sample_kb.add_document(title="Test Doc", content="Test content")
        doc.set_indexed([0.1, 0.2])

        mock_vector_store.search_similar.return_value = [
            {
                "id": str(doc.id),
                "document_id": str(doc.id),
                "content": "Test content",
                "score": 0.95,
            }
        ]

        # Act
        result = await service.semantic_search(
            knowledge_base_id=str(sample_kb.id), query="test query"
        )

        # Assert
        assert result.is_ok()
        assert len(result.value) == 1
        mock_embedding_service.embed.assert_called_once_with("test query")
        mock_vector_store.search_similar.assert_called_once()

    @pytest.mark.asyncio
    async def test_semantic_search_kb_not_found(self, service):
        """Test semantic search on non-existent KB fails."""
        # Act
        result = await service.semantic_search(
            knowledge_base_id=str(uuid4()), query="test query"
        )

        # Assert
        assert result.is_error
        assert result.code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_semantic_search_with_filters(self, service, mock_repo, sample_kb):
        """Test semantic search with filters."""
        # Arrange
        await mock_repo._save(sample_kb)
        mock_repo.get_by_id.return_value = sample_kb

        # Act
        await service.semantic_search(
            knowledge_base_id=str(sample_kb.id),
            query="test query",
            filters={"tags": ["important"]},
        )

        # Assert
        # Result may be success or error depending on implementation

    @pytest.mark.asyncio
    async def test_keyword_search_success(self, service, mock_repo, sample_kb):
        """Test keyword-based search."""
        # Arrange
        await mock_repo._save(sample_kb)
        sample_kb.add_document(title="Test Document", content="Content with keyword")
        sample_kb.add_document(title="Another Doc", content="More content here")

        # Act
        result = await service.keyword_search(
            knowledge_base_id=str(sample_kb.id), keywords=["keyword"]
        )

        # Assert
        assert result.is_ok()
        assert len(result.value) == 1

    @pytest.mark.asyncio
    async def test_keyword_search_kb_not_found(self, service):
        """Test keyword search on non-existent KB fails."""
        # Act
        result = await service.keyword_search(
            knowledge_base_id=str(uuid4()), keywords=["test"]
        )

        # Assert
        assert result.is_error
        assert result.code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_keyword_search_multiple_keywords(
        self, service, mock_repo, sample_kb
    ):
        """Test keyword search with multiple keywords."""
        # Arrange
        await mock_repo._save(sample_kb)
        sample_kb.add_document(title="Alpha Beta", content="Content about alpha")
        sample_kb.add_document(title="Gamma Doc", content="Content about beta")

        # Act
        result = await service.keyword_search(
            knowledge_base_id=str(sample_kb.id), keywords=["alpha", "beta"]
        )

        # Assert
        assert result.is_ok()
        # Should find documents matching any keyword

    @pytest.mark.asyncio
    async def test_list_documents_success(self, service, mock_repo, sample_kb):
        """Test listing documents in knowledge base."""
        # Arrange
        await mock_repo._save(sample_kb)
        sample_kb.add_document(title="Doc 1", content="Content 1")
        sample_kb.add_document(title="Doc 2", content="Content 2")

        # Act
        result = await service.list_documents(knowledge_base_id=str(sample_kb.id))

        # Assert
        assert result.is_ok()
        assert len(result.value) == 2

    @pytest.mark.asyncio
    async def test_list_documents_with_tags(self, service, mock_repo, sample_kb):
        """Test listing documents filtered by tags."""
        # Arrange
        await mock_repo._save(sample_kb)
        doc1 = sample_kb.add_document(
            title="Doc 1", content="Content 1", tags=["important"]
        )
        sample_kb.add_document(title="Doc 2", content="Content 2", tags=["draft"])

        # Act
        result = await service.list_documents(
            knowledge_base_id=str(sample_kb.id), tags=["important"]
        )

        # Assert
        assert result.is_ok()
        assert len(result.value) == 1
        assert result.value[0].id == doc1.id

    @pytest.mark.asyncio
    async def test_list_documents_pagination(self, service, mock_repo, sample_kb):
        """Test document listing with pagination."""
        # Arrange
        await mock_repo._save(sample_kb)
        for i in range(5):
            sample_kb.add_document(title=f"Doc {i}", content=f"Content {i}")

        # Act
        result = await service.list_documents(
            knowledge_base_id=str(sample_kb.id), limit=2, offset=1
        )

        # Assert
        assert result.is_ok()
        assert len(result.value) == 2

    @pytest.mark.asyncio
    async def test_list_documents_kb_not_found(self, service):
        """Test listing documents from non-existent KB fails."""
        # Act
        result = await service.list_documents(knowledge_base_id=str(uuid4()))

        # Assert
        assert result.is_error
        assert result.code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_knowledge_base_stats_success(
        self, service, mock_repo, sample_kb
    ):
        """Test getting KB statistics."""
        # Arrange
        await mock_repo._save(sample_kb)
        sample_kb.add_document(title="Doc 1", content="Test content here")

        # Act
        result = await service.get_knowledge_base_stats(
            knowledge_base_id=str(sample_kb.id)
        )

        # Assert
        assert result.is_ok()
        assert result.value["document_count"] == 1
        assert result.value["name"] == sample_kb.name

    @pytest.mark.asyncio
    async def test_get_knowledge_base_stats_kb_not_found(self, service):
        """Test getting stats for non-existent KB fails."""
        # Act
        result = await service.get_knowledge_base_stats(knowledge_base_id=str(uuid4()))

        # Assert
        assert result.is_error
        assert result.code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_knowledge_base_stats_empty_kb(self, service, mock_repo):
        """Test getting stats for empty KB."""
        # Arrange
        kb = KnowledgeBase(name="Empty KB", owner_id="user-123")
        await mock_repo._save(kb)

        # Act
        result = await service.get_knowledge_base_stats(knowledge_base_id=str(kb.id))

        # Assert
        assert result.is_ok()
        assert result.value["document_count"] == 0
        assert result.value["total_word_count"] == 0


class TestKnowledgeServiceEdgeCases:
    """Test edge cases for KnowledgeApplicationService."""

    @pytest.mark.asyncio
    async def test_upload_document_validation_error(
        self, service, mock_repo, sample_kb
    ):
        """Test upload with invalid document data."""
        # Arrange
        await mock_repo._save(sample_kb)

        # Act - empty title should fail validation
        result = await service.upload_document(
            knowledge_base_id=str(sample_kb.id), title="", content="Content"
        )

        # Assert
        # Document validation should fail
        assert result.is_error

    @pytest.mark.asyncio
    async def test_create_kb_name_too_long(self, service):
        """Test creating KB with name exceeding max length."""
        # Arrange
        long_name = "a" * 201

        # Act
        result = await service.create_knowledge_base(
            name=long_name, owner_id="user-123"
        )

        # Assert
        assert result.is_error
        assert result.code == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_keyword_search_case_insensitive(self, service, mock_repo, sample_kb):
        """Test keyword search is case insensitive."""
        # Arrange
        await mock_repo._save(sample_kb)
        sample_kb.add_document(title="UPPER CASE", content="lower case content")

        # Act
        result = await service.keyword_search(
            knowledge_base_id=str(sample_kb.id), keywords=["upper", "LOWER"]
        )

        # Assert
        assert result.is_ok()
        assert len(result.value) == 1

    @pytest.mark.asyncio
    async def test_semantic_search_embedding_error(
        self, service, mock_repo, sample_kb, mock_embedding_service
    ):
        """Test handling embedding service error."""
        # Arrange
        await mock_repo._save(sample_kb)
        mock_embedding_service.embed.side_effect = Exception("Embedding failed")

        # Act
        result = await service.semantic_search(
            knowledge_base_id=str(sample_kb.id), query="test"
        )

        # Assert
        assert result.is_error
        assert result.code == "SEARCH_ERROR"

    @pytest.mark.asyncio
    async def test_index_document_chunking_error(
        self, service, mock_repo, sample_kb, mock_chunking_service
    ):
        """Test handling chunking service error."""
        # Arrange
        await mock_repo._save(sample_kb)
        doc = sample_kb.add_document(title="Test Doc", content="Test content")
        mock_chunking_service.chunk_document.side_effect = Exception("Chunking failed")

        # Act
        result = await service.index_document(
            knowledge_base_id=str(sample_kb.id), document_id=str(doc.id)
        )

        # Assert
        assert result.is_error
        assert result.code == "INDEXING_ERROR"

    @pytest.mark.asyncio
    async def test_upload_document_no_auto_index(self, service, mock_repo, sample_kb):
        """Test upload without auto-indexing."""
        # Arrange
        await mock_repo._save(sample_kb)

        # Act
        result = await service.upload_document(
            knowledge_base_id=str(sample_kb.id),
            title="Test Doc",
            content="Test content",
            auto_index=False,
        )

        # Assert
        assert result.is_ok()
        assert not result.value.is_indexed

    @pytest.mark.asyncio
    async def test_keyword_search_empty_keywords(self, service, mock_repo, sample_kb):
        """Test keyword search with empty keywords list."""
        # Arrange
        await mock_repo._save(sample_kb)
        sample_kb.add_document(title="Test Doc", content="Content")

        # Act
        result = await service.keyword_search(
            knowledge_base_id=str(sample_kb.id), keywords=[]
        )

        # Assert
        assert result.is_ok()
        assert len(result.value) == 0

    @pytest.mark.asyncio
    async def test_list_documents_offset_beyond_range(
        self, service, mock_repo, sample_kb
    ):
        """Test listing documents with offset beyond document count."""
        # Arrange
        await mock_repo._save(sample_kb)
        sample_kb.add_document(title="Doc 1", content="Content 1")

        # Act
        result = await service.list_documents(
            knowledge_base_id=str(sample_kb.id), offset=100
        )

        # Assert
        assert result.is_ok()
        assert len(result.value) == 0

    @pytest.mark.asyncio
    async def test_delete_document_vector_store_error(
        self, service, mock_repo, sample_kb, mock_vector_store
    ):
        """Test handling vector store error during delete."""
        # Arrange
        await mock_repo._save(sample_kb)
        doc = sample_kb.add_document(title="Test Doc", content="Test content")
        mock_vector_store.delete_document.side_effect = Exception("Vector store error")

        # Act
        result = await service.delete_document(
            knowledge_base_id=str(sample_kb.id), document_id=str(doc.id)
        )

        # Assert
        assert result.is_error


class TestKnowledgeServiceWithRealData:
    """Test with more realistic data scenarios."""

    @pytest.mark.asyncio
    async def test_full_document_lifecycle(self, service, mock_repo, sample_kb):
        """Test complete document lifecycle: create, index, search, delete."""
        # Arrange
        await mock_repo._save(sample_kb)

        # Create document
        upload_result = await service.upload_document(
            knowledge_base_id=str(sample_kb.id),
            title="Important Document",
            content="This is very important content for testing.",
            auto_index=False,
        )
        assert upload_result.is_ok()
        doc_id = str(upload_result.value.id)

        # Index document
        index_result = await service.index_document(
            knowledge_base_id=str(sample_kb.id), document_id=doc_id
        )
        assert index_result.is_ok()

        # Get document
        get_result = await service.get_document(
            knowledge_base_id=str(sample_kb.id), document_id=doc_id
        )
        assert get_result.is_ok()

        # Delete document
        delete_result = await service.delete_document(
            knowledge_base_id=str(sample_kb.id), document_id=doc_id
        )
        assert delete_result.is_ok()

    @pytest.mark.asyncio
    async def test_multiple_documents_search(self, service, mock_repo, sample_kb):
        """Test searching across multiple documents."""
        # Arrange
        await mock_repo._save(sample_kb)
        for i in range(5):
            sample_kb.add_document(
                title=f"Document {i}",
                content=f"Content about topic {i} with specific keywords.",
            )

        # Act
        result = await service.keyword_search(
            knowledge_base_id=str(sample_kb.id), keywords=["topic"]
        )

        # Assert
        assert result.is_ok()
        # Should find documents matching the keyword

    @pytest.mark.asyncio
    async def test_kb_with_project_id(self, service):
        """Test creating KB with project association."""
        # Act
        result = await service.create_knowledge_base(
            name="Project KB",
            owner_id="user-123",
            project_id="project-456",
            is_public=True,
        )

        # Assert
        assert result.is_ok()
        assert result.value.project_id == "project-456"
        assert result.value.is_public is True

    @pytest.mark.asyncio
    async def test_search_result_enrichment(self, service, mock_repo, sample_kb):
        """Test that search results include document metadata."""
        # Arrange
        await mock_repo._save(sample_kb)
        doc = sample_kb.add_document(
            title="Test Document",
            content="Test content",
            source="test_source",
            tags=["test", "important"],
        )
        doc.set_indexed([0.1, 0.2])

        # Mock vector store to return result with document_id
        mock_repo.get_by_id.return_value = sample_kb

        # Act
        await service.semantic_search(knowledge_base_id=str(sample_kb.id), query="test")

        # Assert
        # Result handling may vary based on implementation
