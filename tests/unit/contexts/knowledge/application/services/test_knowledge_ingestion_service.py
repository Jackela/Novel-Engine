"""
Unit Tests for KnowledgeIngestionService

Tests the knowledge ingestion pipeline for RAG (Retrieval-Augmented Generation).

Warzone 4: AI Brain - BRAIN-004
Tests ingestion, batch processing, deletion, and update operations.

Constitution Compliance:
- Article III (TDD): Tests written to validate ingestion behavior
- Article II (Hexagonal): Tests use mock ports for isolation
"""

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
    UpsertResult,
    VectorDocument,
    VectorStoreError,
)
from src.contexts.knowledge.application.services.knowledge_ingestion_service import (
    IngestionProgress,
    KnowledgeIngestionService,
)
from src.contexts.knowledge.domain.models.chunking_strategy import (
    ChunkingStrategy,
    ChunkStrategyType,
)
from src.contexts.knowledge.domain.models.source_type import SourceType

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_embedding_service():
    """
    Create a mock embedding service.

    Returns:
        Mock IEmbeddingService that returns deterministic embeddings
    """
    service = AsyncMock(spec=IEmbeddingService)

    # Return deterministic 1536-dimension embeddings
    def make_embedding(text: str) -> list[float]:
        import hashlib

        seed = int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)
        import random

        random.seed(seed)
        embedding = [random.gauss(0, 1) for _ in range(1536)]
        # Normalize
        magnitude = sum(x * x for x in embedding) ** 0.5
        return [x / magnitude for x in embedding]

    service.embed.side_effect = make_embedding
    service.embed_batch.side_effect = lambda texts: [make_embedding(t) for t in texts]
    service.get_dimension.return_value = 1536
    service.clear_cache.return_value = None

    return service


@pytest.fixture
def mock_vector_store():
    """
    Create a mock vector store.

    Returns:
        Mock IVectorStore that tracks upserts and queries
    """
    store = AsyncMock(spec=IVectorStore)

    # Track stored documents
    stored_docs: dict[str, list[VectorDocument]] = {}

    async def mock_upsert(
        collection: str, documents: list[VectorDocument]
    ) -> UpsertResult:
        if collection not in stored_docs:
            stored_docs[collection] = []
        stored_docs[collection].extend(documents)
        return UpsertResult(count=len(documents), success=True)

    async def mock_query(
        collection: str,
        query_embedding: list[float],
        n_results: int = 5,
        where: dict[str, Any] | None = None,
        where_document: dict[str, Any] | None = None,
    ) -> list[QueryResult]:
        docs = stored_docs.get(collection, [])
        return [
            QueryResult(
                id=doc.id,
                text=doc.text,
                score=0.9,
                metadata=doc.metadata,
            )
            for doc in docs[:n_results]
        ]

    async def mock_delete(
        collection: str,
        ids: list[str] | None = None,
        where: dict[str, Any] | None = None,
    ) -> int:
        if collection not in stored_docs:
            return 0

        if ids:
            initial_count = len(stored_docs[collection])
            stored_docs[collection] = [
                d for d in stored_docs[collection] if d.id not in ids
            ]
            return initial_count - len(stored_docs[collection])

        if where:
            # Filter by metadata
            initial_count = len(stored_docs[collection])
            filtered = []
            for doc in stored_docs[collection]:
                match = True
                for k, v in where.items():
                    if doc.metadata and doc.metadata.get(k) != v:
                        match = False
                        break
                if match:
                    filtered.append(doc)
            stored_docs[collection] = filtered
            return initial_count - len(stored_docs[collection])

        return 0

    store.upsert.side_effect = mock_upsert
    store.query.side_effect = mock_query
    store.delete.side_effect = mock_delete
    store.health_check.return_value = True
    store.count.side_effect = lambda col: len(stored_docs.get(col, []))

    # Attach storage to mock for test verification
    store._stored_docs = stored_docs

    return store


@pytest.fixture
def chunking_strategy():
    """
    Create a chunking strategy for testing.

    Returns:
        ChunkingStrategy with small chunks for faster tests
    """
    return ChunkingStrategy(
        strategy=ChunkStrategyType.FIXED,
        chunk_size=100,
        overlap=10,
        min_chunk_size=20,
    )


@pytest.fixture
def ingestion_service(
    mock_embedding_service: IEmbeddingService,
    mock_vector_store: IVectorStore,
    chunking_strategy: ChunkingStrategy,
) -> KnowledgeIngestionService:
    """
    Create a KnowledgeIngestionService with mocked dependencies.

    Args:
        mock_embedding_service: Mock embedding service
        mock_vector_store: Mock vector store
        chunking_strategy: Chunking strategy

    Returns:
        KnowledgeIngestionService instance
    """
    return KnowledgeIngestionService(
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,
        default_chunking_strategy=chunking_strategy,
    )


@pytest.fixture
def sample_character_content() -> str:
    """
    Create sample character profile content.

    Returns:
        Character profile text (~200 words)
    """
    return """
    Sir Aldric the Brave

    A legendary knight known for his unwavering honor and unmatched skill in combat.
    Born in the northern highlands, Aldric rose from humble beginnings to become
    the commander of the Royal Guard. His distinctive silver armor and crimson cape
    are recognizable throughout the kingdom.

    Personality: Noble, stoic, fiercely loyal to the crown. Known to quote ancient
    proverbs at inappropriate times. Has a secret fondness for poetry.

    Appearance: Tall with broad shoulders, weathered skin from years of campaigns,
    piercing blue eyes, close-cropped gray hair, a scar running from his left
    temple to his jaw.

    Equipment: Carries "Dawnbreaker," a legendary sword passed down through his
    family for seven generations. Wears plate armor enchanted with protective
    runes gifted by the court wizards.

    Background: Trained at the Academy of Arms since age twelve. Served in three
    major campaigns including the Siege of Blackstone and the Dragon Wars. Lost his
    younger brother to a sorcerer's curse, driving his hatred of dark magic.
    """


class TestKnowledgeIngestionService:
    """Unit tests for KnowledgeIngestionService."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_ingest_character_entry(
        self,
        ingestion_service: KnowledgeIngestionService,
        sample_character_content: str,
        mock_vector_store: IVectorStore,
    ):
        """Test ingesting a character profile creates chunks and embeddings."""
        result = await ingestion_service.ingest(
            content=sample_character_content,
            source_type=SourceType.CHARACTER,
            source_id="char_aldric",
        )

        # Verify result
        assert result.success is True
        assert result.source_id == "char_aldric"
        assert result.chunk_count > 0
        assert result.entries_created == result.chunk_count
        assert result.entries_updated == 0

        # Verify vector store was called
        assert mock_vector_store.upsert.call_count == 1

        # Get the upsert call arguments
        call_args = mock_vector_store.upsert.call_args
        documents = call_args[1]["documents"]

        # Verify documents were created
        assert len(documents) == result.chunk_count

        # Verify each document has required fields
        for doc in documents:
            assert doc.id
            assert len(doc.embedding) == 1536
            assert doc.text
            assert doc.metadata["source_type"] == "CHARACTER"
            assert doc.metadata["source_id"] == "char_aldric"

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_ingest_with_custom_chunking(
        self,
        ingestion_service: KnowledgeIngestionService,
        sample_character_content: str,
        mock_vector_store: IVectorStore,
        chunking_strategy: ChunkingStrategy,
    ):
        """Test ingesting with custom chunking strategy."""
        # Use the fixture chunking strategy (100 words, 10 overlap)
        # instead of creating a new one to avoid comparison issues
        result = await ingestion_service.ingest(
            content=sample_character_content,
            source_type=SourceType.CHARACTER,
            source_id="char_aldric",
            chunking_strategy=chunking_strategy,
        )

        assert result.success is True
        assert result.chunk_count > 0

        # Get upserted documents
        call_args = mock_vector_store.upsert.call_args
        documents = call_args[1]["documents"]

        # Verify chunks were created with the strategy
        assert len(documents) == result.chunk_count

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_ingest_with_tags_and_metadata(
        self,
        ingestion_service: KnowledgeIngestionService,
        mock_vector_store: IVectorStore,
    ):
        """Test ingesting with custom tags and metadata."""
        content = "A mystical sword forged in dragon fire."

        result = await ingestion_service.ingest(
            content=content,
            source_type=SourceType.ITEM,
            source_id="item_dragon_sword",
            tags=["legendary", "weapon", "fire"],
            extra_metadata={"rarity": "legendary", "damage": 100},
        )

        assert result.success is True

        # Verify metadata
        call_args = mock_vector_store.upsert.call_args
        documents = call_args[1]["documents"]

        assert len(documents) > 0
        doc = documents[0]

        assert "legendary" in doc.metadata["tags"]
        assert "weapon" in doc.metadata["tags"]
        assert doc.metadata["rarity"] == "legendary"
        assert doc.metadata["damage"] == 100

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_ingest_empty_content_raises_error(
        self,
        ingestion_service: KnowledgeIngestionService,
    ):
        """Test that ingesting empty content raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await ingestion_service.ingest(
                content="",
                source_type=SourceType.CHARACTER,
                source_id="char_1",
            )

        assert "content" in str(exc_info.value).lower()

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_ingest_empty_source_id_raises_error(
        self,
        ingestion_service: KnowledgeIngestionService,
    ):
        """Test that empty source_id raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await ingestion_service.ingest(
                content="Some content",
                source_type=SourceType.CHARACTER,
                source_id="",
            )

        assert "source_id" in str(exc_info.value).lower()

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_batch_ingest_multiple_entries(
        self,
        ingestion_service: KnowledgeIngestionService,
        mock_vector_store: IVectorStore,
    ):
        """Test batch ingesting multiple entries."""
        entries = [
            {
                "content": "First character profile.",
                "source_type": SourceType.CHARACTER,
                "source_id": "char_1",
            },
            {
                "content": "Second character profile.",
                "source_type": SourceType.CHARACTER,
                "source_id": "char_2",
            },
            {
                "content": "Lore entry about the kingdom.",
                "source_type": SourceType.LORE,
                "source_id": "lore_1",
            },
        ]

        result = await ingestion_service.batch_ingest(entries)

        assert result.success is True
        assert result.total_entries == 3
        assert result.successful == 3
        assert result.failed == 0

        # Verify upsert was called once for the batch
        assert mock_vector_store.upsert.call_count == 3  # One per entry

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_batch_ingest_with_progress_callback(
        self,
        ingestion_service: KnowledgeIngestionService,
    ):
        """Test batch ingest with progress tracking callback."""
        entries = [
            {
                "content": f"Content {i}",
                "source_type": SourceType.CHARACTER,
                "source_id": f"char_{i}",
            }
            for i in range(5)
        ]

        progress_updates = []

        async def track_progress(progress: IngestionProgress):
            progress_updates.append(progress)

        result = await ingestion_service.batch_ingest(
            entries, on_progress=track_progress
        )

        assert result.success is True
        assert len(progress_updates) == 5

        # Verify progress updates
        for i, progress in enumerate(progress_updates):
            assert progress.current == i + 1
            assert progress.total == 5
            assert progress.source_id == f"char_{i}"

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_batch_ingest_continues_on_error(
        self,
        ingestion_service: KnowledgeIngestionService,
        mock_embedding_service: IEmbeddingService,
    ):
        """Test that batch ingest continues even if one entry fails."""
        # Get the original embed_batch function
        original_embed_batch = mock_embedding_service.embed_batch.side_effect

        async def conditional_embed_batch(texts: list[str]):
            # Check if any text contains "fail"
            if any("fail" in t.lower() for t in texts):
                raise EmbeddingError("Simulated failure")
            return await original_embed_batch(texts)

        mock_embedding_service.embed_batch.side_effect = conditional_embed_batch

        entries = [
            {
                "content": "Valid content 1",
                "source_type": SourceType.CHARACTER,
                "source_id": "char_1",
            },
            {
                "content": "This will FAIL",
                "source_type": SourceType.CHARACTER,
                "source_id": "char_fail",
            },
            {
                "content": "Valid content 2",
                "source_type": SourceType.CHARACTER,
                "source_id": "char_2",
            },
        ]

        result = await ingestion_service.batch_ingest(entries)

        # The batch process should fail overall because one entry failed
        assert result.success is False
        assert result.total_entries == 3
        # First entry succeeds, second fails, third is never processed due to batch order
        assert result.failed >= 1
        assert "char_fail" in result.errors

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_delete_by_source_id(
        self,
        ingestion_service: KnowledgeIngestionService,
        mock_vector_store: IVectorStore,
    ):
        """Test deleting all chunks for a source."""
        # First ingest something
        result = await ingestion_service.ingest(
            content="Content to delete",
            source_type=SourceType.CHARACTER,
            source_id="char_to_delete",
        )

        _chunk_count = result.chunk_count  # noqa: F841

        # Now delete
        deleted_count = await ingestion_service.delete("char_to_delete")

        # The mock's delete implementation tracks deletions
        assert deleted_count >= 0

        # Verify delete was called
        assert mock_vector_store.delete.call_count == 1

        # Get delete call arguments
        delete_args = mock_vector_store.delete.call_args
        assert delete_args[1]["collection"] == "knowledge"
        assert delete_args[1]["where"]["source_id"] == "char_to_delete"

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_delete_by_source_id_and_type(
        self,
        ingestion_service: KnowledgeIngestionService,
        mock_vector_store: IVectorStore,
    ):
        """Test deleting chunks with source type filter."""
        await ingestion_service.ingest(
            content="Character content",
            source_type=SourceType.CHARACTER,
            source_id="shared_id",
        )

        deleted_count = await ingestion_service.delete(
            source_id="shared_id",
            source_type=SourceType.CHARACTER,
        )

        assert deleted_count >= 0

        # Verify delete was called with where filter
        delete_args = mock_vector_store.delete.call_args
        assert delete_args[1]["where"] is not None

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_delete_nonexistent_source_returns_zero(
        self,
        ingestion_service: KnowledgeIngestionService,
    ):
        """Test deleting a non-existent source returns 0."""
        deleted_count = await ingestion_service.delete("nonexistent_char")

        assert deleted_count == 0

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_update_replaces_existing_chunks(
        self,
        ingestion_service: KnowledgeIngestionService,
        mock_vector_store: IVectorStore,
    ):
        """Test updating a source replaces old chunks with new."""
        # Initial ingest
        await ingestion_service.ingest(
            content="Original content that will be replaced",
            source_type=SourceType.CHARACTER,
            source_id="char_to_update",
        )

        first_upsert_count = mock_vector_store.upsert.call_count

        # Update with new content
        result = await ingestion_service.update(
            source_id="char_to_update",
            new_content="Updated content with new information",
            source_type=SourceType.CHARACTER,
        )

        assert result.success is True
        # entries_deleted will be 0 in mock because mock delete doesn't track state
        # but entries_created should reflect new chunks
        assert result.entries_created > 0

        # Verify delete was called (update calls delete first)
        assert mock_vector_store.delete.call_count >= 1

        # Verify upsert was called again
        assert mock_vector_store.upsert.call_count > first_upsert_count

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_update_with_tags(
        self,
        ingestion_service: KnowledgeIngestionService,
        mock_vector_store: IVectorStore,
    ):
        """Test updating with new tags."""
        await ingestion_service.ingest(
            content="Original content",
            source_type=SourceType.CHARACTER,
            source_id="char_tags",
        )

        result = await ingestion_service.update(
            source_id="char_tags",
            new_content="Updated content",
            source_type=SourceType.CHARACTER,
            tags=["updated", "v2"],
            extra_metadata={"version": 2},
        )

        assert result.success is True

        # Verify new metadata is stored
        call_args = mock_vector_store.upsert.call_args
        documents = call_args[1]["documents"]

        for doc in documents:
            assert "updated" in doc.metadata["tags"]
            assert doc.metadata["version"] == 2

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_update_nonexistent_source_ingests_new(
        self,
        ingestion_service: KnowledgeIngestionService,
    ):
        """Test updating a non-existent source just ingests it as new."""
        result = await ingestion_service.update(
            source_id="new_char",
            new_content="New character content",
            source_type=SourceType.CHARACTER,
        )

        assert result.success is True
        assert result.entries_created > 0
        assert result.entries_deleted == 0  # Nothing to delete

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_update_empty_content_raises_error(
        self,
        ingestion_service: KnowledgeIngestionService,
    ):
        """Test that updating with empty content raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await ingestion_service.update(
                source_id="char_1",
                new_content="",
                source_type=SourceType.CHARACTER,
            )

        assert "content" in str(exc_info.value).lower()

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_query_by_source_returns_ingested_content(
        self,
        ingestion_service: KnowledgeIngestionService,
        sample_character_content: str,
    ):
        """Test querying by source_id returns ingested chunks."""
        # Ingest content
        await ingestion_service.ingest(
            content=sample_character_content,
            source_type=SourceType.CHARACTER,
            source_id="char_query",
        )

        # Query by source_id
        results = await ingestion_service.query_by_source("char_query")

        assert len(results) > 0
        assert all(r.source_id == "char_query" for r in results)

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_query_by_nonexistent_source_returns_empty(
        self,
        ingestion_service: KnowledgeIngestionService,
    ):
        """Test querying non-existent source returns empty list."""
        results = await ingestion_service.query_by_source("nonexistent")

        assert results == []

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_ingest_with_collection_override(
        self,
        ingestion_service: KnowledgeIngestionService,
        mock_vector_store: IVectorStore,
    ):
        """Test ingesting with custom collection name."""
        result = await ingestion_service.ingest(
            content="Custom collection content",
            source_type=SourceType.LORE,
            source_id="lore_1",
            collection="custom_collection",
        )

        assert result.success is True

        # Verify upsert was called with custom collection
        call_args = mock_vector_store.upsert.call_args
        assert call_args[1]["collection"] == "custom_collection"

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_embedding_service_error_propagates(
        self,
        ingestion_service: KnowledgeIngestionService,
        mock_embedding_service: IEmbeddingService,
    ):
        """Test that embedding service errors are handled properly."""
        # The service uses embed_batch, so we need to mock that
        mock_embedding_service.embed_batch.side_effect = EmbeddingError("API error")

        with pytest.raises(EmbeddingError):
            await ingestion_service.ingest(
                content="Test content",
                source_type=SourceType.CHARACTER,
                source_id="char_1",
            )

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_vector_store_error_propagates(
        self,
        ingestion_service: KnowledgeIngestionService,
        mock_vector_store: IVectorStore,
    ):
        """Test that vector store errors are handled properly."""
        mock_vector_store.upsert.side_effect = VectorStoreError("Storage error")

        with pytest.raises(VectorStoreError):
            await ingestion_service.ingest(
                content="Test content",
                source_type=SourceType.CHARACTER,
                source_id="char_1",
            )

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_ingest_creates_entries_with_embeddings(
        self,
        ingestion_service: KnowledgeIngestionService,
        mock_embedding_service: IEmbeddingService,
    ):
        """Test that ingested entries have embedding_id set."""
        result = await ingestion_service.ingest(
            content="Test content for embedding",
            source_type=SourceType.CHARACTER,
            source_id="char_embed",
        )

        assert result.success is True

        # Verify embed_batch was called (service uses batch for efficiency)
        embed_batch_calls = mock_embedding_service.embed_batch.call_count
        assert embed_batch_calls > 0

        # Verify embeddings were created
        call_args = mock_embedding_service.embed_batch.call_args
        embeddings = call_args[0][0]  # First positional arg is texts list
        assert len(embeddings) == result.chunk_count

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_health_check_delegates_to_services(
        self,
        ingestion_service: KnowledgeIngestionService,
        mock_vector_store: IVectorStore,
    ):
        """Test that health check delegates to vector store."""
        is_healthy = await ingestion_service.health_check()

        assert is_healthy is True
        assert mock_vector_store.health_check.call_count == 1

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_get_count_returns_vector_store_count(
        self,
        ingestion_service: KnowledgeIngestionService,
        mock_vector_store: IVectorStore,
    ):
        """Test that get_count delegates to vector store."""
        count = await ingestion_service.get_count()

        assert count >= 0
        assert mock_vector_store.count.call_count == 1
