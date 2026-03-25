"""Tests for PostgreSQL Document Repository.

These tests use a real PostgreSQL database for integration testing.
Ensure DATABASE_URL environment variable is set or use pytest-postgresql.
"""

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import asyncpg
import pytest
import pytest_asyncio

from src.contexts.knowledge.domain.entities.document import Document
from src.contexts.knowledge.infrastructure.repositories.postgres_document_repository import (
    PostgresDocumentRepository,
)

if TYPE_CHECKING:
    from asyncpg import Connection


# Database configuration for tests
TEST_DB_URL = "postgresql://postgres:postgres@localhost:5432/test_novel_engine"


@pytest_asyncio.fixture
async def db_connection() -> AsyncIterator[Connection]:
    """Create a database connection for testing.

    Yields a connection that can be used for repository tests.
    """
    conn = await asyncpg.connect(TEST_DB_URL)

    # Ensure tables exist
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_bases (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            owner_id VARCHAR(255) NOT NULL,
            project_id VARCHAR(255),
            embedding_model VARCHAR(100) DEFAULT 'text-embedding-3-small',
            is_public BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            metadata JSONB DEFAULT '{}'
        )
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            knowledge_base_id UUID REFERENCES knowledge_bases(id) ON DELETE CASCADE,
            title VARCHAR(500) NOT NULL,
            content TEXT NOT NULL,
            content_type VARCHAR(50) DEFAULT 'text',
            source VARCHAR(1000),
            tags TEXT[] DEFAULT '{}',
            chunks JSONB DEFAULT '[]',
            embedding TEXT[],
            is_indexed BOOLEAN DEFAULT FALSE,
            indexed_at TIMESTAMP,
            chunk_count INTEGER DEFAULT 0,
            word_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            metadata JSONB DEFAULT '{}'
        )
        """
    )

    await conn.execute("TRUNCATE TABLE documents CASCADE")
    await conn.execute("TRUNCATE TABLE knowledge_bases CASCADE")

    yield conn

    await conn.close()


@pytest_asyncio.fixture
async def repository(db_connection: Connection) -> PostgresDocumentRepository:
    """Create a repository instance with database connection."""
    return PostgresDocumentRepository(db_connection)


@pytest_asyncio.fixture
async def test_kb_id(db_connection: Connection) -> UUID:
    """Create a test knowledge base and return its ID."""
    kb_id = uuid4()
    await db_connection.execute(
        """
        INSERT INTO knowledge_bases (id, name, owner_id)
        VALUES ($1, $2, $3)
        """,
        kb_id,
        "Test KB",
        "user-123",
    )
    return kb_id


@pytest.mark.asyncio
class TestPostgresDocumentRepository:
    """Test suite for PostgreSQL document repository."""

    async def test_create_and_get_document(
        self,
        repository: PostgresDocumentRepository,
        test_kb_id: UUID,
    ) -> None:
        """Test creating and retrieving a document."""
        # Arrange
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            knowledge_base_id=str(test_kb_id),
            title="Test Document",
            content="This is test content for the document.",
            content_type="text",
            source="test_source",
            tags=["tag1", "tag2"],
            chunks=[{"content": "chunk1", "metadata": {}}],
            chunk_count=1,
            word_count=7,
            metadata={"author": "test"},
        )

        # Act - Create
        await repository.save(doc)

        # Act - Retrieve
        result = await repository.get_by_id(doc_id)

        # Assert
        assert result is not None
        assert result.id == doc_id
        assert result.title == "Test Document"
        assert result.content == "This is test content for the document."
        assert result.knowledge_base_id == str(test_kb_id)
        assert result.content_type == "text"
        assert result.source == "test_source"
        assert result.tags == ["tag1", "tag2"]
        assert result.word_count == 7
        assert result.chunk_count == 1
        assert result.metadata == {"author": "test"}

    async def test_get_by_knowledge_base(
        self,
        repository: PostgresDocumentRepository,
        test_kb_id: UUID,
    ) -> None:
        """Test retrieving documents by knowledge base."""
        # Arrange
        doc1 = Document(
            id=uuid4(),
            knowledge_base_id=str(test_kb_id),
            title="Doc 1",
            content="Content 1",
        )
        doc2 = Document(
            id=uuid4(),
            knowledge_base_id=str(test_kb_id),
            title="Doc 2",
            content="Content 2",
        )
        await repository.save(doc1)
        await repository.save(doc2)

        # Act
        results = await repository.get_by_knowledge_base(test_kb_id)

        # Assert
        assert len(results) == 2
        titles = {doc.title for doc in results}
        assert titles == {"Doc 1", "Doc 2"}

    async def test_get_by_knowledge_base_empty(
        self,
        repository: PostgresDocumentRepository,
        test_kb_id: UUID,
    ) -> None:
        """Test retrieving documents from empty knowledge base."""
        results = await repository.get_by_knowledge_base(test_kb_id)
        assert results == []

    async def test_get_by_id_not_found(
        self,
        repository: PostgresDocumentRepository,
    ) -> None:
        """Test retrieving a non-existent document."""
        result = await repository.get_by_id(uuid4())
        assert result is None

    async def test_update_document(
        self,
        repository: PostgresDocumentRepository,
        test_kb_id: UUID,
    ) -> None:
        """Test updating an existing document."""
        # Arrange
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            knowledge_base_id=str(test_kb_id),
            title="Original Title",
            content="Original content",
        )
        await repository.save(doc)

        # Act - Update
        doc.title = "Updated Title"
        doc.content = "Updated content"
        doc.tags = ["new-tag"]
        await repository.save(doc)

        # Assert
        result = await repository.get_by_id(doc_id)
        assert result is not None
        assert result.title == "Updated Title"
        assert result.content == "Updated content"
        assert result.tags == ["new-tag"]

    async def test_delete_document(
        self,
        repository: PostgresDocumentRepository,
        test_kb_id: UUID,
    ) -> None:
        """Test deleting a document."""
        # Arrange
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            knowledge_base_id=str(test_kb_id),
            title="To Be Deleted",
            content="Delete me",
        )
        await repository.save(doc)

        # Act
        deleted = await repository.delete(doc_id)

        # Assert
        assert deleted is True
        result = await repository.get_by_id(doc_id)
        assert result is None

    async def test_delete_nonexistent_document(
        self,
        repository: PostgresDocumentRepository,
    ) -> None:
        """Test deleting a non-existent document."""
        deleted = await repository.delete(uuid4())
        assert deleted is False

    async def test_count_by_knowledge_base(
        self,
        repository: PostgresDocumentRepository,
        test_kb_id: UUID,
    ) -> None:
        """Test counting documents in a knowledge base."""
        # Initially empty
        count = await repository.count_by_knowledge_base(test_kb_id)
        assert count == 0

        # Create documents
        for i in range(3):
            doc = Document(
                id=uuid4(),
                knowledge_base_id=str(test_kb_id),
                title=f"Doc {i}",
                content=f"Content {i}",
            )
            await repository.save(doc)

        count = await repository.count_by_knowledge_base(test_kb_id)
        assert count == 3

    async def test_search_by_tags(
        self,
        repository: PostgresDocumentRepository,
        test_kb_id: UUID,
    ) -> None:
        """Test searching documents by tags."""
        # Arrange
        doc1 = Document(
            id=uuid4(),
            knowledge_base_id=str(test_kb_id),
            title="Doc with tag1",
            content="Content",
            tags=["tag1", "common"],
        )
        doc2 = Document(
            id=uuid4(),
            knowledge_base_id=str(test_kb_id),
            title="Doc with tag2",
            content="Content",
            tags=["tag2", "common"],
        )
        doc3 = Document(
            id=uuid4(),
            knowledge_base_id=str(test_kb_id),
            title="Doc no tags",
            content="Content",
            tags=[],
        )
        await repository.save(doc1)
        await repository.save(doc2)
        await repository.save(doc3)

        # Act - Search for tag1
        results = await repository.search_by_tags(test_kb_id, ["tag1"])
        assert len(results) == 1
        assert results[0].title == "Doc with tag1"

        # Act - Search for common
        results = await repository.search_by_tags(test_kb_id, ["common"])
        assert len(results) == 2

        # Act - Search for non-existent tag
        results = await repository.search_by_tags(test_kb_id, ["nonexistent"])
        assert len(results) == 0

    async def test_search_by_tags_empty_list(
        self,
        repository: PostgresDocumentRepository,
        test_kb_id: UUID,
    ) -> None:
        """Test searching with empty tag list returns empty."""
        results = await repository.search_by_tags(test_kb_id, [])
        assert results == []

    async def test_search_by_title(
        self,
        repository: PostgresDocumentRepository,
        test_kb_id: UUID,
    ) -> None:
        """Test searching documents by title."""
        # Arrange
        doc1 = Document(
            id=uuid4(),
            knowledge_base_id=str(test_kb_id),
            title="Python Programming Guide",
            content="Content",
        )
        doc2 = Document(
            id=uuid4(),
            knowledge_base_id=str(test_kb_id),
            title="JavaScript Basics",
            content="Content",
        )
        doc3 = Document(
            id=uuid4(),
            knowledge_base_id=str(test_kb_id),
            title="Python Advanced",
            content="Content",
        )
        await repository.save(doc1)
        await repository.save(doc2)
        await repository.save(doc3)

        # Act
        results = await repository.search_by_title(test_kb_id, "Python")

        # Assert
        assert len(results) == 2
        titles = {doc.title for doc in results}
        assert "Python Programming Guide" in titles
        assert "Python Advanced" in titles

    async def test_paginated_query(
        self,
        repository: PostgresDocumentRepository,
        test_kb_id: UUID,
    ) -> None:
        """Test paginated document query."""
        # Arrange
        for i in range(10):
            doc = Document(
                id=uuid4(),
                knowledge_base_id=str(test_kb_id),
                title=f"Doc {i}",
                content=f"Content {i}",
            )
            await repository.save(doc)

        # Act - Get first 5
        results = await repository.get_by_knowledge_base_paginated(
            test_kb_id, limit=5, offset=0
        )
        assert len(results) == 5

        # Act - Get next 5
        results = await repository.get_by_knowledge_base_paginated(
            test_kb_id, limit=5, offset=5
        )
        assert len(results) == 5

    async def test_paginated_negative_limit_raises(
        self,
        repository: PostgresDocumentRepository,
        test_kb_id: UUID,
    ) -> None:
        """Test that negative limit raises ValueError."""
        with pytest.raises(ValueError, match="Limit must be non-negative"):
            await repository.get_by_knowledge_base_paginated(test_kb_id, limit=-1)

    async def test_paginated_negative_offset_raises(
        self,
        repository: PostgresDocumentRepository,
        test_kb_id: UUID,
    ) -> None:
        """Test that negative offset raises ValueError."""
        with pytest.raises(ValueError, match="Offset must be non-negative"):
            await repository.get_by_knowledge_base_paginated(test_kb_id, offset=-1)

    async def test_delete_by_knowledge_base(
        self,
        repository: PostgresDocumentRepository,
        test_kb_id: UUID,
    ) -> None:
        """Test deleting all documents in a knowledge base."""
        # Arrange
        for i in range(5):
            doc = Document(
                id=uuid4(),
                knowledge_base_id=str(test_kb_id),
                title=f"Doc {i}",
                content=f"Content {i}",
            )
            await repository.save(doc)

        # Act
        deleted_count = await repository.delete_by_knowledge_base(test_kb_id)

        # Assert
        assert deleted_count == 5
        remaining = await repository.count_by_knowledge_base(test_kb_id)
        assert remaining == 0

    async def test_update_indexed_status(
        self,
        repository: PostgresDocumentRepository,
        test_kb_id: UUID,
    ) -> None:
        """Test updating document indexed status."""
        # Arrange
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            knowledge_base_id=str(test_kb_id),
            title="Test Doc",
            content="Content",
            is_indexed=False,
        )
        await repository.save(doc)

        # Act - Mark as indexed
        await repository.update_indexed_status(
            doc_id, is_indexed=True, embedding=[0.1, 0.2, 0.3]
        )

        # Assert
        result = await repository.get_by_id(doc_id)
        assert result is not None
        assert result.is_indexed is True
        assert result.indexed_at is not None

    async def test_preserve_chunks(
        self, repository: PostgresDocumentRepository, test_kb_id: UUID
    ) -> None:
        """Test that document chunks are preserved correctly."""
        # Arrange
        chunks = [
            {"content": "First chunk", "metadata": {"pos": 1}},
            {"content": "Second chunk", "metadata": {"pos": 2}},
        ]
        doc = Document(
            id=uuid4(),
            knowledge_base_id=str(test_kb_id),
            title="Chunked Doc",
            content="First chunk Second chunk",
            chunks=chunks,
            chunk_count=2,
        )
        await repository.save(doc)

        # Act
        result = await repository.get_by_id(doc.id)

        # Assert
        assert result is not None
        assert len(result.chunks) == 2
        assert result.chunks[0]["content"] == "First chunk"
