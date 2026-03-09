"""
Tests for Knowledge Ingestion Service Module

Coverage targets:
- Document parsing (PDF, HTML, etc.)
- Text chunking
- Embedding generation
- Error handling for malformed documents
"""

from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio

from src.contexts.knowledge.application.services.knowledge_ingestion_service import (
    DEFAULT_COLLECTION,
    BatchIngestionResult,
    IngestionProgress,
    IngestionResult,
    KnowledgeIngestionService,
    RetrievedChunk,
)
from src.contexts.knowledge.domain.models.source_type import SourceType

pytestmark = pytest.mark.unit


class TestIngestionProgress:
    """Tests for IngestionProgress dataclass."""

    def test_progress_creation(self):
        """Test progress creation."""
        progress = IngestionProgress(
            current=5,
            total=10,
            source_id="source_001",
            success=True,
        )

        assert progress.current == 5
        assert progress.total == 10
        assert progress.source_id == "source_001"
        assert progress.success is True
        assert progress.error is None

    def test_progress_percentage(self):
        """Test progress percentage calculation."""
        progress = IngestionProgress(current=5, total=10, source_id="source_001")
        assert progress.percentage == 50.0

        # Edge case: total is 0
        progress_zero = IngestionProgress(current=0, total=0, source_id="source_001")
        assert progress_zero.percentage == 100.0

    def test_progress_percentage_error(self):
        """Test progress with error."""
        progress = IngestionProgress(
            current=5,
            total=10,
            source_id="source_001",
            success=False,
            error="Something went wrong",
        )

        assert progress.success is False
        assert progress.error == "Something went wrong"


class TestIngestionResult:
    """Tests for IngestionResult dataclass."""

    def test_success_result(self):
        """Test successful ingestion result."""
        result = IngestionResult(
            success=True,
            source_id="source_001",
            chunk_count=5,
            entries_created=5,
        )

        assert result.success is True
        assert result.source_id == "source_001"
        assert result.chunk_count == 5
        assert result.entries_created == 5
        assert result.error is None

    def test_error_result(self):
        """Test failed ingestion result."""
        result = IngestionResult(
            success=False,
            source_id="source_001",
            chunk_count=0,
            error="Failed to process",
        )

        assert result.success is False
        assert result.error == "Failed to process"


class TestBatchIngestionResult:
    """Tests for BatchIngestionResult dataclass."""

    def test_batch_result_success(self):
        """Test successful batch result."""
        result = BatchIngestionResult(
            success=True,
            total_entries=10,
            successful=10,
            failed=0,
        )

        assert result.success is True
        assert result.total_entries == 10
        assert result.successful == 10
        assert result.failed == 0

    def test_batch_result_partial(self):
        """Test partial batch result."""
        result = BatchIngestionResult(
            success=False,
            total_entries=10,
            successful=7,
            failed=3,
            errors={"source_1": "Error 1", "source_2": "Error 2"},
        )

        assert result.success is False
        assert result.successful == 7
        assert result.failed == 3
        assert len(result.errors) == 2


class TestRetrievedChunk:
    """Tests for RetrievedChunk dataclass."""

    def test_chunk_creation(self):
        """Test chunk creation."""
        chunk = RetrievedChunk(
            chunk_id="chunk_001",
            source_id="source_001",
            source_type=SourceType.LORE,
            content="Test content",
            score=0.95,
            metadata={"key": "value"},
        )

        assert chunk.chunk_id == "chunk_001"
        assert chunk.source_id == "source_001"
        assert chunk.source_type == SourceType.LORE
        assert chunk.content == "Test content"
        assert chunk.score == 0.95


@pytest.mark.asyncio
class TestKnowledgeIngestionService:
    """Tests for KnowledgeIngestionService class."""

    @pytest_asyncio.fixture
    async def mock_embedding_service(self):
        """Create a mock embedding service."""
        service = AsyncMock()

        # Dynamic mock: return same number of embeddings as input texts
        async def mock_embed_batch(texts):
            return [[0.1, 0.2, 0.3] for _ in texts]

        service.embed_batch = AsyncMock(side_effect=mock_embed_batch)
        service.get_dimension = Mock(return_value=3)
        return service

    @pytest_asyncio.fixture
    async def mock_vector_store(self):
        """Create a mock vector store."""
        store = AsyncMock()
        store.upsert = AsyncMock(return_value=Mock(success=True))
        store.delete = AsyncMock(return_value=5)
        store.query = AsyncMock(return_value=[])
        store.count = AsyncMock(return_value=100)
        store.health_check = AsyncMock(return_value=True)
        return store

    @pytest_asyncio.fixture
    async def ingestion_service(self, mock_embedding_service, mock_vector_store):
        """Create a KnowledgeIngestionService instance."""
        service = KnowledgeIngestionService(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
        )
        return service

    def test_initialization(self, mock_embedding_service, mock_vector_store):
        """Test service initialization."""
        service = KnowledgeIngestionService(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            default_collection="custom_collection",
        )

        assert service._embedding_service == mock_embedding_service
        assert service._vector_store == mock_vector_store
        assert service._default_collection == "custom_collection"

    def test_initialization_default_collection(
        self, mock_embedding_service, mock_vector_store
    ):
        """Test service initialization with default collection."""
        service = KnowledgeIngestionService(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
        )

        assert service._default_collection == DEFAULT_COLLECTION

    async def test_ingest_success(
        self, ingestion_service, mock_embedding_service, mock_vector_store
    ):
        """Test successful ingestion."""
        content = "This is a test content. It has multiple sentences for chunking."

        result = await ingestion_service.ingest(
            content=content,
            source_type=SourceType.LORE,
            source_id="lore_001",
            tags=["test", "lore"],
        )

        assert result.is_ok
        ingestion_result = result.unwrap()
        assert ingestion_result.success is True
        assert ingestion_result.source_id == "lore_001"
        assert ingestion_result.chunk_count > 0
        assert ingestion_result.entries_created > 0

        # Verify embedding service was called
        mock_embedding_service.embed_batch.assert_called_once()

        # Verify vector store was called
        mock_vector_store.upsert.assert_called_once()

    async def test_ingest_empty_content(self, ingestion_service):
        """Test ingestion with empty content returns error result."""
        result = await ingestion_service.ingest(
            content="",
            source_type=SourceType.LORE,
            source_id="lore_001",
        )
        assert result.is_error
        assert "content cannot be empty" in result.error.message

    async def test_ingest_empty_source_id(self, ingestion_service):
        """Test ingestion with empty source_id returns error result."""
        result = await ingestion_service.ingest(
            content="Some content",
            source_type=SourceType.LORE,
            source_id="",
        )
        assert result.is_error
        assert "source_id cannot be empty" in result.error.message

    async def test_ingest_with_string_source_type(
        self, ingestion_service, mock_embedding_service
    ):
        """Test ingestion with string source type."""
        result = await ingestion_service.ingest(
            content="Test content",
            source_type="LORE",
            source_id="lore_001",
        )

        assert result.is_ok
        ingestion_result = result.unwrap()
        assert ingestion_result.success is True

    async def test_ingest_embedding_error(
        self, ingestion_service, mock_embedding_service
    ):
        """Test ingestion with embedding error returns error result."""
        from src.contexts.knowledge.application.ports.i_embedding_service import (
            EmbeddingError,
        )

        mock_embedding_service.embed_batch = AsyncMock(
            side_effect=EmbeddingError("Embedding failed")
        )

        result = await ingestion_service.ingest(
            content="Test content",
            source_type=SourceType.LORE,
            source_id="lore_001",
        )
        assert result.is_error
        assert "Embedding failed" in result.error.message

    async def test_batch_ingest_success(self, ingestion_service):
        """Test successful batch ingestion."""
        entries = [
            {
                "content": "Entry 1",
                "source_type": SourceType.LORE,
                "source_id": "lore_001",
            },
            {
                "content": "Entry 2",
                "source_type": SourceType.CHARACTER,
                "source_id": "char_001",
            },
        ]

        result = await ingestion_service.batch_ingest(entries)

        assert result.is_ok
        batch_result = result.unwrap()
        assert batch_result.success is True
        assert batch_result.total_entries == 2
        assert batch_result.successful == 2
        assert batch_result.failed == 0

    async def test_batch_ingest_partial_failure(self, ingestion_service):
        """Test batch ingestion with partial failures."""
        entries = [
            {
                "content": "Entry 1",
                "source_type": SourceType.LORE,
                "source_id": "lore_001",
            },
            {
                "content": "",  # Empty content will fail
                "source_type": SourceType.LORE,
                "source_id": "lore_002",
            },
        ]

        result = await ingestion_service.batch_ingest(entries)

        assert result.is_ok
        batch_result = result.unwrap()
        assert batch_result.success is False
        assert batch_result.total_entries == 2
        assert batch_result.successful == 1
        assert batch_result.failed == 1
        assert "lore_002" in batch_result.errors

    async def test_batch_ingest_with_progress_callback(self, ingestion_service):
        """Test batch ingestion with progress callback."""
        progress_calls = []

        async def progress_callback(progress):
            progress_calls.append(progress)

        entries = [
            {
                "content": "Entry 1",
                "source_type": SourceType.LORE,
                "source_id": "lore_001",
            },
            {
                "content": "Entry 2",
                "source_type": SourceType.LORE,
                "source_id": "lore_002",
            },
        ]

        await ingestion_service.batch_ingest(entries, on_progress=progress_callback)

        assert len(progress_calls) == 2
        assert progress_calls[0].source_id == "lore_001"
        assert progress_calls[1].source_id == "lore_002"

    async def test_delete(self, ingestion_service, mock_vector_store):
        """Test deleting chunks by source."""
        result = await ingestion_service.delete(
            source_id="source_001",
            source_type=SourceType.LORE,
        )

        assert result.is_ok
        assert result.unwrap() == 5
        mock_vector_store.delete.assert_called_once()

    async def test_delete_without_source_type(
        self, ingestion_service, mock_vector_store
    ):
        """Test deleting chunks without specifying source type."""
        result = await ingestion_service.delete(source_id="source_001")

        assert result.is_ok
        assert result.unwrap() == 5
        # Should not include source_type in filter
        call_args = mock_vector_store.delete.call_args
        assert "source_type" not in call_args.kwargs.get("where", {})

    async def test_update(self, ingestion_service, mock_vector_store):
        """Test updating existing content."""
        result = await ingestion_service.update(
            source_id="source_001",
            new_content="Updated content",
            source_type=SourceType.LORE,
            tags=["updated"],
        )

        assert result.is_ok
        update_result = result.unwrap()
        assert update_result.success is True
        assert update_result.source_id == "source_001"
        assert update_result.entries_deleted > 0  # Old chunks deleted
        assert update_result.entries_created > 0  # New chunks created

    async def test_update_empty_content(self, ingestion_service):
        """Test update with empty content returns error result."""
        result = await ingestion_service.update(
            source_id="source_001",
            new_content="",
            source_type=SourceType.LORE,
        )
        assert result.is_error
        assert "new_content cannot be empty" in result.error.message

    async def test_query_by_source(self, ingestion_service, mock_vector_store):
        """Test querying chunks by source."""
        # Mock query results
        mock_result = Mock()
        mock_result.id = "chunk_001"
        mock_result.text = "Test content"
        mock_result.score = 0.95
        mock_result.metadata = {"source_id": "source_001", "source_type": "LORE"}
        mock_vector_store.query = AsyncMock(return_value=[mock_result])

        result = await ingestion_service.query_by_source(
            source_id="source_001",
            source_type=SourceType.LORE,
        )

        assert result.is_ok
        chunks = result.unwrap()
        assert len(chunks) == 1
        assert chunks[0].chunk_id == "chunk_001"
        assert chunks[0].source_id == "source_001"

    async def test_query_by_source_empty_result(
        self, ingestion_service, mock_vector_store
    ):
        """Test querying by source with no results."""
        mock_vector_store.query = AsyncMock(return_value=[])

        result = await ingestion_service.query_by_source(source_id="nonexistent")

        assert result.is_ok
        assert len(result.unwrap()) == 0

    async def test_health_check(self, ingestion_service, mock_vector_store):
        """Test health check."""
        result = await ingestion_service.health_check()

        assert result.is_ok
        assert result.unwrap() is True
        mock_vector_store.health_check.assert_called_once()

    async def test_get_count(self, ingestion_service, mock_vector_store):
        """Test getting chunk count."""
        result = await ingestion_service.get_count()

        assert result.is_ok
        assert result.unwrap() == 100
        mock_vector_store.count.assert_called_once_with(DEFAULT_COLLECTION)

    async def test_get_count_custom_collection(
        self, ingestion_service, mock_vector_store
    ):
        """Test getting chunk count for custom collection."""
        result = await ingestion_service.get_count(collection="custom")

        assert result.is_ok
        assert result.unwrap() == 100
        mock_vector_store.count.assert_called_once_with("custom")

    async def test_call_progress_callback_sync(self, ingestion_service):
        """Test calling synchronous progress callback."""
        calls = []

        def sync_callback(progress):
            calls.append(progress)

        progress = IngestionProgress(current=1, total=10, source_id="source_001")
        await ingestion_service._call_progress_callback(sync_callback, progress)

        assert len(calls) == 1
        assert calls[0].source_id == "source_001"

    async def test_call_progress_callback_async(self, ingestion_service):
        """Test calling asynchronous progress callback."""
        calls = []

        async def async_callback(progress):
            calls.append(progress)

        progress = IngestionProgress(current=1, total=10, source_id="source_001")
        await ingestion_service._call_progress_callback(async_callback, progress)

        assert len(calls) == 1

    async def test_call_progress_callback_error(self, ingestion_service):
        """Test progress callback with error."""

        def bad_callback(progress):
            raise Exception("Callback error")

        progress = IngestionProgress(current=1, total=10, source_id="source_001")

        # Should not raise, just log warning
        await ingestion_service._call_progress_callback(bad_callback, progress)
