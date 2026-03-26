"""Tests for PostgreSQL Knowledge Repository.

These tests use a real PostgreSQL database for integration testing.
Ensure DATABASE_URL environment variable is set or use pytest-postgresql.
"""

from collections.abc import AsyncIterator
from uuid import uuid4

import asyncpg
import pytest
import pytest_asyncio

from src.contexts.knowledge.domain.aggregates.knowledge_base import KnowledgeBase
from src.contexts.knowledge.infrastructure.repositories.postgres_knowledge_repository import (
    PostgresKnowledgeRepository,
)

pytestmark = pytest.mark.postgres_integration

# Database configuration for tests
TEST_DB_URL = "postgresql://postgres:postgres@localhost:5432/test_novel_engine"


@pytest_asyncio.fixture
async def db_pool() -> AsyncIterator[asyncpg.Pool]:
    """Create a database connection pool for testing.

    Yields a pool that can be used for repository tests.
    """
    pool = await asyncpg.create_pool(TEST_DB_URL, min_size=1, max_size=5)
    assert pool is not None

    # Ensure tables exist
    async with pool.acquire() as conn:
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

        await conn.execute("TRUNCATE TABLE knowledge_bases CASCADE")

    yield pool

    await pool.close()


@pytest_asyncio.fixture
async def repository(db_pool: asyncpg.Pool) -> PostgresKnowledgeRepository:
    """Create a repository instance with database connection pool."""
    return PostgresKnowledgeRepository(db_pool)


@pytest.mark.asyncio
class TestPostgresKnowledgeRepository:
    """Test suite for PostgreSQL knowledge repository."""

    async def test_create_and_get_knowledge_base(
        self,
        repository: PostgresKnowledgeRepository,
    ) -> None:
        """Test creating and retrieving a knowledge base."""
        # Arrange
        kb_id = uuid4()
        kb = KnowledgeBase(
            id=kb_id,
            name="Test Knowledge Base",
            description="A test knowledge base",
            owner_id="user-123",
            project_id="project-456",
            embedding_model="text-embedding-3-small",
            is_public=False,
            metadata={"category": "test"},
        )

        # Act - Create
        await repository.save(kb)

        # Act - Retrieve
        result = await repository.get_by_id(kb_id)

        # Assert
        assert result is not None
        assert result.id == kb_id
        assert result.name == "Test Knowledge Base"
        assert result.owner_id == "user-123"
        assert result.description == "A test knowledge base"
        assert result.project_id == "project-456"
        assert result.is_public is False
        assert result.metadata == {"category": "test"}

    async def test_get_by_name(
        self,
        repository: PostgresKnowledgeRepository,
    ) -> None:
        """Test retrieving a knowledge base by name."""
        # Arrange
        kb = KnowledgeBase(
            id=uuid4(),
            name="Unique KB Name",
            description="Test description",
            owner_id="user-123",
        )
        await repository.save(kb)

        # Act
        result = await repository.get_by_name("Unique KB Name")

        # Assert
        assert result is not None
        assert result.name == "Unique KB Name"

    async def test_get_by_name_not_found(
        self,
        repository: PostgresKnowledgeRepository,
    ) -> None:
        """Test retrieving a non-existent knowledge base by name."""
        result = await repository.get_by_name("NonExistentName12345")
        assert result is None

    async def test_get_by_id_not_found(
        self,
        repository: PostgresKnowledgeRepository,
    ) -> None:
        """Test retrieving a non-existent knowledge base by ID."""
        result = await repository.get_by_id(uuid4())
        assert result is None

    async def test_update_knowledge_base(
        self,
        repository: PostgresKnowledgeRepository,
    ) -> None:
        """Test updating an existing knowledge base."""
        # Arrange
        kb_id = uuid4()
        kb = KnowledgeBase(
            id=kb_id,
            name="Original Name",
            owner_id="user-123",
        )
        await repository.save(kb)

        # Act - Update
        kb.name = "Updated Name"
        kb.description = "Updated description"
        kb.is_public = True
        await repository.save(kb)

        # Assert
        result = await repository.get_by_id(kb_id)
        assert result is not None
        assert result.name == "Updated Name"
        assert result.description == "Updated description"
        assert result.is_public is True

    async def test_delete_knowledge_base(
        self,
        repository: PostgresKnowledgeRepository,
    ) -> None:
        """Test deleting a knowledge base."""
        # Arrange
        kb_id = uuid4()
        kb = KnowledgeBase(
            id=kb_id,
            name="To Be Deleted",
            owner_id="user-123",
        )
        await repository.save(kb)

        # Act - Delete
        deleted = await repository.delete(kb_id)

        # Assert
        assert deleted is True
        result = await repository.get_by_id(kb_id)
        assert result is None

    async def test_delete_nonexistent_knowledge_base(
        self,
        repository: PostgresKnowledgeRepository,
    ) -> None:
        """Test deleting a non-existent knowledge base."""
        deleted = await repository.delete(uuid4())
        assert deleted is False

    async def test_list_all_with_pagination(
        self,
        repository: PostgresKnowledgeRepository,
    ) -> None:
        """Test listing knowledge bases with pagination."""
        # Arrange - Create multiple KBs
        for i in range(5):
            kb = KnowledgeBase(
                id=uuid4(),
                name=f"KB {i}",
                owner_id="user-123",
            )
            await repository.save(kb)

        # Act - List all
        all_kbs = await repository.list_all()

        # Assert
        assert len(all_kbs) == 5

        # Act - List with limit
        limited_kbs = await repository.list_all(limit=3)
        assert len(limited_kbs) == 3

        # Act - List with offset
        offset_kbs = await repository.list_all(limit=10, offset=2)
        assert len(offset_kbs) == 3

    async def test_list_all_empty(
        self, repository: PostgresKnowledgeRepository
    ) -> None:
        """Test listing when no knowledge bases exist."""
        result = await repository.list_all()
        assert result == []

    async def test_list_all_negative_limit_raises(
        self,
        repository: PostgresKnowledgeRepository,
    ) -> None:
        """Test that negative limit raises ValueError."""
        with pytest.raises(ValueError, match="Limit must be non-negative"):
            await repository.list_all(limit=-1)

    async def test_list_all_negative_offset_raises(
        self,
        repository: PostgresKnowledgeRepository,
    ) -> None:
        """Test that negative offset raises ValueError."""
        with pytest.raises(ValueError, match="Offset must be non-negative"):
            await repository.list_all(offset=-1)

    async def test_count(self, repository: PostgresKnowledgeRepository) -> None:
        """Test counting knowledge bases."""
        # Initially empty
        count = await repository.count()
        assert count == 0

        # Create some KBs
        for i in range(3):
            kb = KnowledgeBase(
                id=uuid4(),
                name=f"KB {i}",
                owner_id="user-123",
            )
            await repository.save(kb)

        count = await repository.count()
        assert count == 3

    async def test_list_by_owner(
        self,
        repository: PostgresKnowledgeRepository,
    ) -> None:
        """Test listing knowledge bases by owner."""
        # Arrange - Create KBs for different owners
        kb1 = KnowledgeBase(id=uuid4(), name="Owner1 KB 1", owner_id="owner-1")
        kb2 = KnowledgeBase(id=uuid4(), name="Owner1 KB 2", owner_id="owner-1")
        kb3 = KnowledgeBase(id=uuid4(), name="Owner2 KB", owner_id="owner-2")

        await repository.save(kb1)
        await repository.save(kb2)
        await repository.save(kb3)

        # Act
        owner1_kbs = await repository.list_by_owner("owner-1")

        # Assert
        assert len(owner1_kbs) == 2
        assert all(kb.owner_id == "owner-1" for kb in owner1_kbs)

    async def test_list_by_project(
        self,
        repository: PostgresKnowledgeRepository,
    ) -> None:
        """Test listing knowledge bases by project."""
        # Arrange - Create KBs for different projects
        kb1 = KnowledgeBase(
            id=uuid4(),
            name="Project1 KB",
            owner_id="user-123",
            project_id="project-1",
        )
        kb2 = KnowledgeBase(
            id=uuid4(),
            name="Project2 KB",
            owner_id="user-123",
            project_id="project-2",
        )
        kb3 = KnowledgeBase(
            id=uuid4(),
            name="No Project KB",
            owner_id="user-123",
        )

        await repository.save(kb1)
        await repository.save(kb2)
        await repository.save(kb3)

        # Act
        project1_kbs = await repository.list_by_project("project-1")

        # Assert
        assert len(project1_kbs) == 1
        assert project1_kbs[0].project_id == "project-1"

    async def test_preserve_metadata(
        self, repository: PostgresKnowledgeRepository
    ) -> None:
        """Test that metadata is preserved correctly."""
        # Arrange
        metadata = {
            "tags": ["fiction", "scifi"],
            "version": 1,
            "settings": {"auto_index": True},
        }
        kb = KnowledgeBase(
            id=uuid4(),
            name="KB with metadata",
            owner_id="user-123",
            metadata=metadata,
        )
        await repository.save(kb)

        # Act
        result = await repository.get_by_id(kb.id)

        # Assert
        assert result is not None
        assert result.metadata == metadata
