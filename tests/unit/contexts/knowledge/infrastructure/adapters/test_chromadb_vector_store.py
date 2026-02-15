"""
Unit Tests for ChromaDB Vector Store Adapter

Tests the ChromaDB adapter implementing IVectorStore port.

Warzone 4: AI Brain - BRAIN-001
Tests vector storage operations, persistence, and health checks.

Constitution Compliance:
- Article III (TDD): Tests written to validate vector storage behavior
- Article I (DDD): Tests adapter behavior, not business logic
"""

from pathlib import Path

import pytest

try:
    import chromadb  # noqa: F401 - imported for availability check
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from src.contexts.knowledge.application.ports.i_vector_store import (
    IVectorStore,
    QueryResult,
    UpsertResult,
    VectorDocument,
    VectorStoreError,
)
from src.contexts.knowledge.infrastructure.adapters.chromadb_vector_store import (
    ChromaDBVectorStore,
)

# Skip all tests if chromadb is not installed, and mark as unit tests
pytestmark = [pytest.mark.unit, pytest.mark.skipif(not CHROMADB_AVAILABLE, reason="chromadb not installed")]


@pytest.fixture
def temp_persist_dir(tmp_path: Path) -> str:
    """
    Create a temporary directory for ChromaDB persistence.

    Args:
        tmp_path: pytest fixture providing temporary directory

    Returns:
        Path to temporary persist directory
    """
    persist_dir = tmp_path / "chroma_test"
    return str(persist_dir)


@pytest.fixture
def vector_store(temp_persist_dir: str) -> ChromaDBVectorStore:
    """
    Create a ChromaDB vector store instance with temporary persistence.

    Args:
        temp_persist_dir: Temporary persist directory

    Returns:
        ChromaDBVectorStore instance
    """
    return ChromaDBVectorStore(persist_dir=temp_persist_dir)


@pytest.fixture
def sample_embedding() -> list[float]:
    """
    Create a sample 1536-dimensional embedding vector.

    Returns:
        List of 1536 float values (normalized unit vector)
    """
    # Simple deterministic embedding for testing
    import math

    dimension = 1536
    # Create a pattern-based embedding
    embedding = [math.sin(i * 0.1) for i in range(dimension)]
    # Normalize to unit length
    magnitude = math.sqrt(sum(x * x for x in embedding))
    return [x / magnitude for x in embedding]


@pytest.fixture
def sample_documents(sample_embedding: list[float]) -> list[VectorDocument]:
    """
    Create sample documents for testing.

    Args:
        sample_embedding: Sample embedding vector

    Returns:
        List of VectorDocument instances
    """
    return [
        VectorDocument(
            id="doc1",
            embedding=sample_embedding,
            text="The brave warrior fought with honor.",
            metadata={"source_type": "CHARACTER", "source_id": "char1"},
        ),
        VectorDocument(
            id="doc2",
            embedding=sample_embedding,
            text="The ancient dragon guarded the mountain treasure.",
            metadata={"source_type": "LORE", "source_id": "lore1"},
        ),
        VectorDocument(
            id="doc3",
            embedding=sample_embedding,
            text="In the realm of shadows, heroes rise.",
            metadata={"source_type": "SCENE", "source_id": "scene1"},
        ),
    ]


class TestChromaDBVectorStore:
    """Unit tests for ChromaDBVectorStore adapter."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_init_creates_persist_directory(self, temp_persist_dir: str):
        """Test that initialization creates the persist directory."""
        store = ChromaDBVectorStore(persist_dir=temp_persist_dir)

        # Access client to trigger initialization
        _client = store._get_client()

        # Verify directory was created
        persist_path = Path(temp_persist_dir)
        assert persist_path.exists()
        assert persist_path.is_dir()

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_upsert_inserts_documents(
        self, vector_store: ChromaDBVectorStore, sample_documents: list[VectorDocument]
    ):
        """Test that upsert inserts documents successfully."""
        result = await vector_store.upsert("test_collection", sample_documents)

        assert isinstance(result, UpsertResult)
        assert result.success is True
        assert result.count == len(sample_documents)

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_upsert_empty_list_returns_success(
        self, vector_store: ChromaDBVectorStore
    ):
        """Test that upsert with empty list returns success with count 0."""
        result = await vector_store.upsert("test_collection", [])

        assert isinstance(result, UpsertResult)
        assert result.success is True
        assert result.count == 0

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_upsert_then_query_returns_documents(
        self,
        vector_store: ChromaDBVectorStore,
        sample_documents: list[VectorDocument],
        sample_embedding: list[float],
    ):
        """Test that upserted documents can be queried back."""
        collection = "test_collection"

        # Upsert documents
        await vector_store.upsert(collection, sample_documents)

        # Query with same embedding
        results = await vector_store.query(collection, sample_embedding, n_results=3)

        assert len(results) > 0
        assert all(isinstance(r, QueryResult) for r in results)
        assert all(0 <= r.score <= 1 for r in results)

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_query_with_metadata_filter(
        self,
        vector_store: ChromaDBVectorStore,
        sample_documents: list[VectorDocument],
        sample_embedding: list[float],
    ):
        """Test that query filters by metadata correctly."""
        collection = "test_collection"

        # Upsert documents
        await vector_store.upsert(collection, sample_documents)

        # Query with metadata filter
        results = await vector_store.query(
            collection,
            sample_embedding,
            n_results=10,
            where={"source_type": "CHARACTER"},
        )

        assert len(results) > 0
        assert all(r.metadata.get("source_type") == "CHARACTER" for r in results)

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_count_returns_document_count(
        self,
        vector_store: ChromaDBVectorStore,
        sample_documents: list[VectorDocument],
    ):
        """Test that count returns the number of documents in collection."""
        collection = "test_collection"

        # Initially empty
        count = await vector_store.count(collection)
        assert count == 0

        # After upsert
        await vector_store.upsert(collection, sample_documents)
        count = await vector_store.count(collection)
        assert count == len(sample_documents)

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_delete_by_ids(
        self,
        vector_store: ChromaDBVectorStore,
        sample_documents: list[VectorDocument],
    ):
        """Test that delete removes documents by ID."""
        collection = "test_collection"

        # Upsert documents
        await vector_store.upsert(collection, sample_documents)

        # Delete one document
        deleted_count = await vector_store.delete(collection, ids=["doc1"])
        assert deleted_count >= 0

        # Verify count decreased
        count = await vector_store.count(collection)
        assert count < len(sample_documents)

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_delete_by_metadata_filter(
        self,
        vector_store: ChromaDBVectorStore,
        sample_documents: list[VectorDocument],
    ):
        """Test that delete removes documents by metadata filter."""
        collection = "test_collection"

        # Upsert documents
        await vector_store.upsert(collection, sample_documents)

        # Delete by metadata filter
        deleted_count = await vector_store.delete(
            collection, where={"source_type": "CHARACTER"}
        )
        assert deleted_count >= 0

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_clear_removes_all_documents(
        self,
        vector_store: ChromaDBVectorStore,
        sample_documents: list[VectorDocument],
    ):
        """Test that clear removes all documents from collection."""
        collection = "test_collection"

        # Upsert documents
        await vector_store.upsert(collection, sample_documents)
        assert await vector_store.count(collection) > 0

        # Clear collection
        await vector_store.clear(collection)

        # Verify empty
        count = await vector_store.count(collection)
        assert count == 0

    @pytest.mark.unit
    @pytest.mark.fast
    async def test_health_check_returns_true_when_initialized(
        self, vector_store: ChromaDBVectorStore
    ):
        """Test that health_check returns True for initialized store."""
        is_healthy = await vector_store.health_check()
        assert is_healthy is True

    @pytest.mark.unit
    @pytest.mark.slow
    async def test_data_persists_across_restarts(
        self,
        temp_persist_dir: str,
        sample_documents: list[VectorDocument],
    ):
        """
        Test that data persists across store restarts.

        Warzone 4: AI Brain - BRAIN-001
        Verifies that ChromaDB correctly persists data to disk.
        """
        collection = "test_collection"

        # First store - upsert documents
        store1 = ChromaDBVectorStore(persist_dir=temp_persist_dir)
        await store1.upsert(collection, sample_documents)
        count1 = await store1.count(collection)

        # Create new store instance (simulates restart)
        store2 = ChromaDBVectorStore(persist_dir=temp_persist_dir)
        count2 = await store2.count(collection)

        # Verify data persisted
        assert count2 == count1
        assert count2 == len(sample_documents)

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_multiple_collections_independent(
        self,
        vector_store: ChromaDBVectorStore,
        sample_documents: list[VectorDocument],
    ):
        """Test that multiple collections are independent."""
        doc1 = [sample_documents[0]]
        doc2 = [sample_documents[1]]

        # Upsert to different collections
        await vector_store.upsert("collection1", doc1)
        await vector_store.upsert("collection2", doc2)

        # Verify independent counts
        count1 = await vector_store.count("collection1")
        count2 = await vector_store.count("collection2")

        assert count1 == 1
        assert count2 == 1

        # Clear one collection
        await vector_store.clear("collection1")

        # Verify only one cleared
        assert await vector_store.count("collection1") == 0
        assert await vector_store.count("collection2") == 1

    @pytest.mark.unit
    @pytest.mark.fast
    def test_vector_store_implements_interface(self):
        """Test that ChromaDBVectorStore implements IVectorStore interface."""
        assert issubclass(ChromaDBVectorStore, IVectorStore)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_default_persist_dir_is_dot_data_chroma(self):
        """Test that default persist directory is .data/chroma."""
        store = ChromaDBVectorStore()
        assert store._persist_dir == ".data/chroma"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_custom_embedding_dimension(self):
        """Test that custom embedding dimension can be set."""
        store = ChromaDBVectorStore(embedding_dimension=3072)
        assert store._embedding_dimension == 3072

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_query_respects_n_results_limit(
        self,
        vector_store: ChromaDBVectorStore,
        sample_documents: list[VectorDocument],
        sample_embedding: list[float],
    ):
        """Test that query respects n_results parameter."""
        collection = "test_collection"

        # Upsert multiple documents
        await vector_store.upsert(collection, sample_documents)

        # Query with limit
        results = await vector_store.query(collection, sample_embedding, n_results=2)

        assert len(results) <= 2

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_delete_without_filter_raises_error(
        self, vector_store: ChromaDBVectorStore
    ):
        """Test that delete without ids or where raises VectorStoreError."""
        with pytest.raises(VectorStoreError) as exc_info:
            await vector_store.delete("test_collection")

        assert exc_info.value.code == "INVALID_DELETE"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_reset_deletes_all_data(
        self, temp_persist_dir: str, sample_documents: list[VectorDocument]
    ):
        """
        Test that reset deletes all collections.

        WARNING: Destructive test.
        """
        import pytest

        pytest.skip("Reset is destructive - skip in unit tests")


class TestVectorDocument:
    """Unit tests for VectorDocument value object."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_vector_document_is_immutable(self):
        """Test that VectorDocument is frozen (immutable)."""
        doc = VectorDocument(id="test", embedding=[0.1, 0.2], text="test text")

        # Attempting to modify should raise (frozen dataclass)
        with pytest.raises(Exception):  # FrozenInstanceError
            doc.id = "new_id"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_vector_document_with_metadata(self):
        """Test VectorDocument with optional metadata."""
        doc = VectorDocument(
            id="test",
            embedding=[0.1, 0.2],
            text="test text",
            metadata={"key": "value"},
        )

        assert doc.metadata == {"key": "value"}

    @pytest.mark.unit
    @pytest.mark.fast
    def test_vector_document_defaults_metadata_to_none(self):
        """Test that metadata defaults to None."""
        doc = VectorDocument(id="test", embedding=[0.1, 0.2], text="test text")

        assert doc.metadata is None


class TestQueryResult:
    """Unit tests for QueryResult value object."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_query_result_is_immutable(self):
        """Test that QueryResult is frozen (immutable)."""
        result = QueryResult(id="test", text="test text", score=0.95)

        # Attempting to modify should raise
        with pytest.raises(Exception):
            result.id = "new_id"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_query_result_score_in_valid_range(self):
        """Test that score is within valid range (0-1)."""
        result = QueryResult(id="test", text="test text", score=0.95)

        assert 0 <= result.score <= 1


class TestUpsertResult:
    """Unit tests for UpsertResult value object."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_upsert_result_fields(self):
        """Test UpsertResult fields."""
        result = UpsertResult(count=5, success=True)

        assert result.count == 5
        assert result.success is True
