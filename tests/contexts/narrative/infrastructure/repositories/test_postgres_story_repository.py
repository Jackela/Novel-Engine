"""Tests for PostgreSQL Story Repository.

These tests use a real PostgreSQL database for integration testing.
Ensure DATABASE_URL environment variable is set or use pytest-postgresql.
"""

# mypy: disable-error-code=misc

from collections.abc import AsyncIterator
from uuid import uuid4

import asyncpg
import pytest
import pytest_asyncio
from asyncpg import Connection

from src.contexts.narrative.domain.aggregates.story import Story
from src.contexts.narrative.infrastructure.repositories.postgres_story_repository import (  # noqa: E501
    PostgresStoryRepository,
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
async def repository(db_connection: Connection) -> PostgresStoryRepository:
    """Create a repository instance with database connection."""
    return PostgresStoryRepository(db_connection)


@pytest.mark.asyncio
class TestPostgresStoryRepository:
    """Test suite for PostgreSQL story repository."""

    async def test_create_and_get_story(
        self,
        repository: PostgresStoryRepository,
    ) -> None:
        """Test creating and retrieving a story."""
        # Arrange
        story_id = uuid4()
        story = Story(
            id=story_id,
            title="Test Story",
            genre="fantasy",
            author_id="author-123",
            status="draft",
            themes=["magic", "adventure"],
            metadata={"target_word_count": 50000},
        )

        # Act - Create
        await repository.save(story)

        # Act - Retrieve
        result = await repository.get_by_id(story_id)

        # Assert
        assert result is not None
        assert result.id == story_id
        assert result.title == "Test Story"
        assert result.genre == "fantasy"
        assert result.author_id == "author-123"
        assert result.status == "draft"
        assert result.themes == ["magic", "adventure"]
        assert result.metadata == {"target_word_count": 50000}

    async def test_get_by_title(
        self,
        repository: PostgresStoryRepository,
    ) -> None:
        """Test retrieving a story by title."""
        # Arrange
        story = Story(
            id=uuid4(),
            title="Unique Story Title",
            genre="sci-fi",
            author_id="author-123",
        )
        await repository.save(story)

        # Act
        result = await repository.get_by_title("Unique Story Title")

        # Assert
        assert result is not None
        assert result.title == "Unique Story Title"
        assert result.genre == "sci-fi"

    async def test_get_by_title_not_found(
        self,
        repository: PostgresStoryRepository,
    ) -> None:
        """Test retrieving a non-existent story by title."""
        result = await repository.get_by_title("NonExistentTitle12345")
        assert result is None

    async def test_get_by_id_not_found(
        self,
        repository: PostgresStoryRepository,
    ) -> None:
        """Test retrieving a non-existent story by ID."""
        result = await repository.get_by_id(uuid4())
        assert result is None

    async def test_update_story(
        self,
        repository: PostgresStoryRepository,
    ) -> None:
        """Test updating an existing story."""
        # Arrange
        story_id = uuid4()
        story = Story(
            id=story_id,
            title="Original Title",
            genre="mystery",
            author_id="author-123",
            status="draft",
        )
        await repository.save(story)

        # Act - Update
        story.title = "Updated Title"
        story.status = "active"
        story.themes = ["suspense"]
        await repository.save(story)

        # Assert
        result = await repository.get_by_id(story_id)
        assert result is not None
        assert result.title == "Updated Title"
        assert result.status == "active"
        assert result.themes == ["suspense"]

    async def test_delete_story(
        self,
        repository: PostgresStoryRepository,
    ) -> None:
        """Test deleting a story."""
        # Arrange
        story_id = uuid4()
        story = Story(
            id=story_id,
            title="To Be Deleted",
            genre="horror",
            author_id="author-123",
        )
        await repository.save(story)

        # Act - Delete
        deleted = await repository.delete(story_id)

        # Assert
        assert deleted is True
        result = await repository.get_by_id(story_id)
        assert result is None

    async def test_delete_nonexistent_story(
        self,
        repository: PostgresStoryRepository,
    ) -> None:
        """Test deleting a non-existent story."""
        deleted = await repository.delete(uuid4())
        assert deleted is False

    async def test_list_all_with_pagination(
        self,
        repository: PostgresStoryRepository,
    ) -> None:
        """Test listing stories with pagination."""
        # Arrange - Create multiple stories
        for i in range(5):
            story = Story(
                id=uuid4(),
                title=f"Story {i}",
                genre="fantasy",
                author_id="author-123",
            )
            await repository.save(story)

        # Act - List all
        all_stories = await repository.list_all()

        # Assert
        assert len(all_stories) == 5

        # Act - List with limit
        limited_stories = await repository.list_all(limit=3)
        assert len(limited_stories) == 3

        # Act - List with offset
        offset_stories = await repository.list_all(limit=10, offset=2)
        assert len(offset_stories) == 3

    async def test_list_all_empty(self, repository: PostgresStoryRepository) -> None:
        """Test listing when no stories exist."""
        result = await repository.list_all()
        assert result == []

    async def test_list_all_negative_limit_raises(
        self,
        repository: PostgresStoryRepository,
    ) -> None:
        """Test that negative limit raises ValueError."""
        with pytest.raises(ValueError, match="Limit must be non-negative"):
            await repository.list_all(limit=-1)

    async def test_list_all_negative_offset_raises(
        self,
        repository: PostgresStoryRepository,
    ) -> None:
        """Test that negative offset raises ValueError."""
        with pytest.raises(ValueError, match="Offset must be non-negative"):
            await repository.list_all(offset=-1)

    async def test_list_by_author(
        self,
        repository: PostgresStoryRepository,
    ) -> None:
        """Test listing stories by author."""
        # Arrange - Create stories for different authors
        story1 = Story(
            id=uuid4(), title="Author1 Story 1", genre="fantasy", author_id="author-1"
        )
        story2 = Story(
            id=uuid4(), title="Author1 Story 2", genre="sci-fi", author_id="author-1"
        )
        story3 = Story(
            id=uuid4(), title="Author2 Story", genre="mystery", author_id="author-2"
        )

        await repository.save(story1)
        await repository.save(story2)
        await repository.save(story3)

        # Act
        author1_stories = await repository.list_by_author("author-1")

        # Assert
        assert len(author1_stories) == 2
        assert all(s.author_id == "author-1" for s in author1_stories)

    async def test_save_story_with_chapters(
        self,
        repository: PostgresStoryRepository,
    ) -> None:
        """Test saving a story with chapters and scenes."""
        # Arrange
        story_id = uuid4()
        story = Story(
            id=story_id,
            title="Story with Chapters",
            genre="adventure",
            author_id="author-123",
        )

        # Add chapter with scene
        chapter = story.add_chapter(title="Chapter 1", summary="The beginning")
        chapter.add_scene(
            content="Once upon a time...",
            scene_type="opening",
            title="The Beginning",
        )

        # Act
        await repository.save(story)

        # Assert
        result = await repository.get_by_id(story_id)
        assert result is not None
        assert len(result.chapters) == 1
        assert result.chapters[0].title == "Chapter 1"
        assert len(result.chapters[0].scenes) == 1
        assert result.chapters[0].scenes[0].content == "Once upon a time..."

    async def test_save_story_with_multiple_chapters(
        self,
        repository: PostgresStoryRepository,
    ) -> None:
        """Test saving a story with multiple chapters."""
        # Arrange
        story_id = uuid4()
        story = Story(
            id=story_id,
            title="Epic Tale",
            genre="fantasy",
            author_id="author-123",
        )

        # Add multiple chapters
        chapter1 = story.add_chapter(title="Chapter 1")
        chapter1.add_scene(content="Scene 1 in chapter 1")

        chapter2 = story.add_chapter(title="Chapter 2")
        chapter2.add_scene(content="Scene 1 in chapter 2")

        # Act
        await repository.save(story)

        # Assert
        result = await repository.get_by_id(story_id)
        assert result is not None
        assert len(result.chapters) == 2
        assert result.chapters[0].title == "Chapter 1"
        assert result.chapters[1].title == "Chapter 2"

    async def test_delete_story_cascades_to_chapters(
        self,
        repository: PostgresStoryRepository,
        db_connection: Connection,
    ) -> None:
        """Test that deleting a story also deletes chapters and scenes."""
        # Arrange
        story_id = uuid4()
        story = Story(
            id=story_id,
            title="Story to Delete",
            genre="drama",
            author_id="author-123",
        )
        chapter = story.add_chapter(title="Chapter 1")
        chapter.add_scene(content="Scene content")
        await repository.save(story)

        # Act
        await repository.delete(story_id)

        # Assert - Check chapters are also deleted
        chapter_count = await db_connection.fetchval(
            "SELECT COUNT(*) FROM chapters WHERE story_id = $1", story_id
        )
        assert chapter_count == 0

    async def test_preserve_metadata(self, repository: PostgresStoryRepository) -> None:
        """Test that metadata is preserved correctly."""
        # Arrange
        metadata = {
            "tags": ["fiction", "fantasy"],
            "version": 1,
            "settings": {"auto_save": True},
        }
        story = Story(
            id=uuid4(),
            title="Story with metadata",
            genre="fantasy",
            author_id="author-123",
            metadata=metadata,
        )
        await repository.save(story)

        # Act
        result = await repository.get_by_id(story.id)

        # Assert
        assert result is not None
        assert result.metadata == metadata
