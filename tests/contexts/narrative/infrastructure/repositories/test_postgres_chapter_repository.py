"""Tests for PostgreSQL Chapter Repository.

These tests use a real PostgreSQL database for integration testing.
Ensure DATABASE_URL environment variable is set or use pytest-postgresql.
"""

# mypy: disable-error-code=misc

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import asyncpg
import pytest
import pytest_asyncio
from asyncpg import Connection

from src.contexts.narrative.domain.entities.chapter import Chapter
from src.contexts.narrative.infrastructure.repositories.postgres_chapter_repository import (  # noqa: E501
    PostgresChapterRepository,
)

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
        CREATE TABLE IF NOT EXISTS stories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            title VARCHAR(200) NOT NULL,
            genre VARCHAR(50) NOT NULL,
            author_id VARCHAR(255) NOT NULL,
            status VARCHAR(20) DEFAULT 'draft',
            current_chapter_id VARCHAR(36),
            target_audience VARCHAR(100),
            themes TEXT[] DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            metadata JSONB DEFAULT '{}'
        )
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chapters (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
            chapter_number INTEGER NOT NULL,
            title VARCHAR(200) NOT NULL,
            summary TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            metadata JSONB DEFAULT '{}'
        )
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scenes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            chapter_id UUID REFERENCES chapters(id) ON DELETE CASCADE,
            scene_number INTEGER NOT NULL,
            title VARCHAR(200),
            content TEXT NOT NULL,
            scene_type VARCHAR(50) DEFAULT 'narrative',
            choices JSONB DEFAULT '[]',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            metadata JSONB DEFAULT '{}'
        )
        """
    )

    # Truncate tables
    await conn.execute("TRUNCATE TABLE scenes CASCADE")
    await conn.execute("TRUNCATE TABLE chapters CASCADE")
    await conn.execute("TRUNCATE TABLE stories CASCADE")

    yield conn

    await conn.close()


@pytest_asyncio.fixture
async def repository(db_connection: Connection) -> PostgresChapterRepository:
    """Create a repository instance with database connection."""
    return PostgresChapterRepository(db_connection)


@pytest_asyncio.fixture
async def test_story_id(db_connection: Connection) -> UUID:
    """Create a test story and return its ID."""
    story_id = uuid4()
    await db_connection.execute(
        """
        INSERT INTO stories (id, title, genre, author_id)
        VALUES ($1, $2, $3, $4)
        """,
        story_id,
        "Test Story",
        "fantasy",
        "author-123",
    )
    return story_id


@pytest.mark.asyncio
class TestPostgresChapterRepository:
    """Test suite for PostgreSQL chapter repository."""

    async def test_create_and_get_chapter(
        self,
        repository: PostgresChapterRepository,
        test_story_id: UUID,
    ) -> None:
        """Test creating and retrieving a chapter."""
        # Arrange
        chapter_id = uuid4()
        chapter = Chapter(
            id=chapter_id,
            story_id=str(test_story_id),
            chapter_number=1,
            title="Test Chapter",
            summary="A test chapter summary",
            metadata={"word_count": 1000},
        )

        # Act - Create
        await repository.save(chapter)

        # Act - Retrieve
        result = await repository.get_by_id(chapter_id)

        # Assert
        assert result is not None
        assert result.id == chapter_id
        assert result.title == "Test Chapter"
        assert result.story_id == str(test_story_id)
        assert result.chapter_number == 1
        assert result.summary == "A test chapter summary"
        assert result.metadata == {"word_count": 1000}

    async def test_get_by_story(
        self,
        repository: PostgresChapterRepository,
        test_story_id: UUID,
    ) -> None:
        """Test retrieving chapters by story ID."""
        # Arrange
        chapter1 = Chapter(
            id=uuid4(),
            story_id=str(test_story_id),
            chapter_number=1,
            title="Chapter 1",
        )
        chapter2 = Chapter(
            id=uuid4(),
            story_id=str(test_story_id),
            chapter_number=2,
            title="Chapter 2",
        )
        await repository.save(chapter1)
        await repository.save(chapter2)

        # Act
        results = await repository.get_by_story(test_story_id)

        # Assert
        assert len(results) == 2
        titles = {c.title for c in results}
        assert titles == {"Chapter 1", "Chapter 2"}
        # Check ordering
        assert results[0].chapter_number == 1
        assert results[1].chapter_number == 2

    async def test_get_by_story_empty(
        self,
        repository: PostgresChapterRepository,
        test_story_id: UUID,
    ) -> None:
        """Test retrieving chapters from empty story."""
        results = await repository.get_by_story(test_story_id)
        assert results == []

    async def test_get_by_id_not_found(
        self,
        repository: PostgresChapterRepository,
    ) -> None:
        """Test retrieving a non-existent chapter."""
        result = await repository.get_by_id(uuid4())
        assert result is None

    async def test_update_chapter(
        self,
        repository: PostgresChapterRepository,
        test_story_id: UUID,
    ) -> None:
        """Test updating an existing chapter."""
        # Arrange
        chapter_id = uuid4()
        chapter = Chapter(
            id=chapter_id,
            story_id=str(test_story_id),
            chapter_number=1,
            title="Original Title",
            summary="Original summary",
        )
        await repository.save(chapter)

        # Act - Update
        chapter.title = "Updated Title"
        chapter.summary = "Updated summary"
        chapter.metadata = {"updated": True}
        await repository.save(chapter)

        # Assert
        result = await repository.get_by_id(chapter_id)
        assert result is not None
        assert result.title == "Updated Title"
        assert result.summary == "Updated summary"
        assert result.metadata == {"updated": True}

    async def test_delete_chapter(
        self,
        repository: PostgresChapterRepository,
        test_story_id: UUID,
    ) -> None:
        """Test deleting a chapter."""
        # Arrange
        chapter_id = uuid4()
        chapter = Chapter(
            id=chapter_id,
            story_id=str(test_story_id),
            chapter_number=1,
            title="To Be Deleted",
        )
        await repository.save(chapter)

        # Act
        deleted = await repository.delete(chapter_id)

        # Assert
        assert deleted is True
        result = await repository.get_by_id(chapter_id)
        assert result is None

    async def test_delete_nonexistent_chapter(
        self,
        repository: PostgresChapterRepository,
    ) -> None:
        """Test deleting a non-existent chapter."""
        deleted = await repository.delete(uuid4())
        assert deleted is False

    async def test_reorder_chapters(
        self,
        repository: PostgresChapterRepository,
        test_story_id: UUID,
    ) -> None:
        """Test reordering chapters."""
        # Arrange - Create chapters in order 1, 2, 3
        chapter1 = Chapter(
            id=uuid4(),
            story_id=str(test_story_id),
            chapter_number=1,
            title="First Chapter",
        )
        chapter2 = Chapter(
            id=uuid4(),
            story_id=str(test_story_id),
            chapter_number=2,
            title="Second Chapter",
        )
        chapter3 = Chapter(
            id=uuid4(),
            story_id=str(test_story_id),
            chapter_number=3,
            title="Third Chapter",
        )

        await repository.save(chapter1)
        await repository.save(chapter2)
        await repository.save(chapter3)

        # Act - Reorder to 3, 1, 2
        await repository.reorder_chapters(
            test_story_id, [chapter3.id, chapter1.id, chapter2.id]
        )

        # Assert
        results = await repository.get_by_story(test_story_id)
        assert len(results) == 3
        assert results[0].id == chapter3.id
        assert results[0].chapter_number == 1
        assert results[1].id == chapter1.id
        assert results[1].chapter_number == 2
        assert results[2].id == chapter2.id
        assert results[2].chapter_number == 3

    async def test_reorder_chapters_empty_list_raises(
        self,
        repository: PostgresChapterRepository,
        test_story_id: UUID,
    ) -> None:
        """Test that empty chapter order raises ValueError."""
        with pytest.raises(ValueError, match="Chapter order cannot be empty"):
            await repository.reorder_chapters(test_story_id, [])

    async def test_reorder_chapters_invalid_id_raises(
        self,
        repository: PostgresChapterRepository,
        test_story_id: UUID,
    ) -> None:
        """Test that invalid chapter ID raises ValueError."""
        # Arrange
        chapter = Chapter(
            id=uuid4(),
            story_id=str(test_story_id),
            chapter_number=1,
            title="Chapter",
        )
        await repository.save(chapter)

        # Act & Assert
        with pytest.raises(ValueError, match="not found or does not belong to story"):
            await repository.reorder_chapters(test_story_id, [chapter.id, uuid4()])

    async def test_count_by_story(
        self,
        repository: PostgresChapterRepository,
        test_story_id: UUID,
    ) -> None:
        """Test counting chapters in a story."""
        # Initially empty
        count = await repository.count_by_story(test_story_id)
        assert count == 0

        # Create chapters
        for i in range(3):
            chapter = Chapter(
                id=uuid4(),
                story_id=str(test_story_id),
                chapter_number=i + 1,
                title=f"Chapter {i + 1}",
            )
            await repository.save(chapter)

        count = await repository.count_by_story(test_story_id)
        assert count == 3

    async def test_get_chapter_numbers(
        self,
        repository: PostgresChapterRepository,
        test_story_id: UUID,
    ) -> None:
        """Test getting chapter numbers for a story."""
        # Arrange
        for i in range(3):
            chapter = Chapter(
                id=uuid4(),
                story_id=str(test_story_id),
                chapter_number=i + 1,
                title=f"Chapter {i + 1}",
            )
            await repository.save(chapter)

        # Act
        numbers = await repository.get_chapter_numbers(test_story_id)

        # Assert
        assert numbers == [1, 2, 3]

    async def test_save_chapter_with_scenes(
        self,
        repository: PostgresChapterRepository,
        test_story_id: UUID,
    ) -> None:
        """Test saving a chapter with scenes."""
        # Arrange
        chapter_id = uuid4()
        chapter = Chapter(
            id=chapter_id,
            story_id=str(test_story_id),
            chapter_number=1,
            title="Chapter with Scenes",
        )

        # Add scenes
        chapter.add_scene(
            content="Scene 1 content",
            scene_type="opening",
            title="Scene 1",
        )
        chapter.add_scene(
            content="Scene 2 content",
            scene_type="narrative",
            title="Scene 2",
        )

        # Act
        await repository.save(chapter)

        # Assert
        result = await repository.get_by_id(chapter_id)
        assert result is not None
        assert len(result.scenes) == 2
        assert result.scenes[0].content == "Scene 1 content"
        assert result.scenes[1].content == "Scene 2 content"

    async def test_delete_chapter_cascades_to_scenes(
        self,
        repository: PostgresChapterRepository,
        test_story_id: UUID,
        db_connection: Connection,
    ) -> None:
        """Test that deleting a chapter also deletes scenes."""
        # Arrange
        chapter_id = uuid4()
        chapter = Chapter(
            id=chapter_id,
            story_id=str(test_story_id),
            chapter_number=1,
            title="Chapter to Delete",
        )
        chapter.add_scene(content="Scene content")
        await repository.save(chapter)

        # Act
        await repository.delete(chapter_id)

        # Assert - Check scenes are also deleted
        scene_count = await db_connection.fetchval(
            "SELECT COUNT(*) FROM scenes WHERE chapter_id = $1", chapter_id
        )
        assert scene_count == 0

    async def test_preserve_metadata(
        self,
        repository: PostgresChapterRepository,
        test_story_id: UUID,
    ) -> None:
        """Test that metadata is preserved correctly."""
        # Arrange
        metadata = {
            "notes": ["important note"],
            "revision": 2,
            "settings": {"tone": "dark"},
        }
        chapter = Chapter(
            id=uuid4(),
            story_id=str(test_story_id),
            chapter_number=1,
            title="Chapter with metadata",
            metadata=metadata,
        )
        await repository.save(chapter)

        # Act
        result = await repository.get_by_id(chapter.id)

        # Assert
        assert result is not None
        assert result.metadata == metadata
