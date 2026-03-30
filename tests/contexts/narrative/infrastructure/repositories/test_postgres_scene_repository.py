"""Tests for PostgreSQL Scene Repository.

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

from src.contexts.narrative.domain.entities.choice import Choice
from src.contexts.narrative.domain.entities.scene import Scene
from src.contexts.narrative.infrastructure.repositories.postgres_scene_repository import (  # noqa: E501
    PostgresSceneRepository,
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
async def repository(db_connection: Connection) -> PostgresSceneRepository:
    """Create a repository instance with database connection."""
    return PostgresSceneRepository(db_connection)


@pytest_asyncio.fixture
async def test_chapter_id(db_connection: Connection) -> UUID:
    """Create a test chapter and return its ID."""
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

    chapter_id = uuid4()
    await db_connection.execute(
        """
        INSERT INTO chapters (id, story_id, chapter_number, title)
        VALUES ($1, $2, $3, $4)
        """,
        chapter_id,
        story_id,
        1,
        "Test Chapter",
    )
    return chapter_id


@pytest.mark.asyncio
class TestPostgresSceneRepository:
    """Test suite for PostgreSQL scene repository."""

    async def test_create_and_get_scene(
        self,
        repository: PostgresSceneRepository,
        test_chapter_id: UUID,
    ) -> None:
        """Test creating and retrieving a scene."""
        # Arrange
        scene_id = uuid4()
        scene = Scene(
            id=scene_id,
            chapter_id=str(test_chapter_id),
            scene_number=1,
            title="Test Scene",
            content="This is the scene content.",
            scene_type="narrative",
            metadata={"word_count": 50},
        )

        # Act - Create
        await repository.save(scene)

        # Act - Retrieve
        result = await repository.get_by_id(scene_id)

        # Assert
        assert result is not None
        assert result.id == scene_id
        assert result.title == "Test Scene"
        assert result.chapter_id == str(test_chapter_id)
        assert result.scene_number == 1
        assert result.content == "This is the scene content."
        assert result.scene_type == "narrative"
        assert result.metadata == {"word_count": 50}

    async def test_get_by_chapter(
        self,
        repository: PostgresSceneRepository,
        test_chapter_id: UUID,
    ) -> None:
        """Test retrieving scenes by chapter ID."""
        # Arrange
        scene1 = Scene(
            id=uuid4(),
            chapter_id=str(test_chapter_id),
            scene_number=1,
            title="Scene 1",
            content="Content 1",
        )
        scene2 = Scene(
            id=uuid4(),
            chapter_id=str(test_chapter_id),
            scene_number=2,
            title="Scene 2",
            content="Content 2",
        )
        await repository.save(scene1)
        await repository.save(scene2)

        # Act
        results = await repository.get_by_chapter(test_chapter_id)

        # Assert
        assert len(results) == 2
        titles = {s.title for s in results}
        assert titles == {"Scene 1", "Scene 2"}
        # Check ordering
        assert results[0].scene_number == 1
        assert results[1].scene_number == 2

    async def test_get_by_chapter_empty(
        self,
        repository: PostgresSceneRepository,
        test_chapter_id: UUID,
    ) -> None:
        """Test retrieving scenes from empty chapter."""
        results = await repository.get_by_chapter(test_chapter_id)
        assert results == []

    async def test_get_by_id_not_found(
        self,
        repository: PostgresSceneRepository,
    ) -> None:
        """Test retrieving a non-existent scene."""
        result = await repository.get_by_id(uuid4())
        assert result is None

    async def test_update_scene(
        self,
        repository: PostgresSceneRepository,
        test_chapter_id: UUID,
    ) -> None:
        """Test updating an existing scene."""
        # Arrange
        scene_id = uuid4()
        scene = Scene(
            id=scene_id,
            chapter_id=str(test_chapter_id),
            scene_number=1,
            title="Original Title",
            content="Original content",
            scene_type="narrative",
        )
        await repository.save(scene)

        # Act - Update
        scene.title = "Updated Title"
        scene.content = "Updated content"
        scene.scene_type = "dialogue"
        scene.metadata = {"updated": True}
        await repository.save(scene)

        # Assert
        result = await repository.get_by_id(scene_id)
        assert result is not None
        assert result.title == "Updated Title"
        assert result.content == "Updated content"
        assert result.scene_type == "dialogue"
        assert result.metadata == {"updated": True}

    async def test_delete_scene(
        self,
        repository: PostgresSceneRepository,
        test_chapter_id: UUID,
    ) -> None:
        """Test deleting a scene."""
        # Arrange
        scene_id = uuid4()
        scene = Scene(
            id=scene_id,
            chapter_id=str(test_chapter_id),
            scene_number=1,
            title="To Be Deleted",
            content="Delete me",
        )
        await repository.save(scene)

        # Act
        deleted = await repository.delete(scene_id)

        # Assert
        assert deleted is True
        result = await repository.get_by_id(scene_id)
        assert result is None

    async def test_delete_nonexistent_scene(
        self,
        repository: PostgresSceneRepository,
    ) -> None:
        """Test deleting a non-existent scene."""
        deleted = await repository.delete(uuid4())
        assert deleted is False

    async def test_count_by_chapter(
        self,
        repository: PostgresSceneRepository,
        test_chapter_id: UUID,
    ) -> None:
        """Test counting scenes in a chapter."""
        # Initially empty
        count = await repository.count_by_chapter(test_chapter_id)
        assert count == 0

        # Create scenes
        for i in range(3):
            scene = Scene(
                id=uuid4(),
                chapter_id=str(test_chapter_id),
                scene_number=i + 1,
                title=f"Scene {i + 1}",
                content=f"Content {i + 1}",
            )
            await repository.save(scene)

        count = await repository.count_by_chapter(test_chapter_id)
        assert count == 3

    async def test_get_max_scene_number(
        self,
        repository: PostgresSceneRepository,
        test_chapter_id: UUID,
    ) -> None:
        """Test getting maximum scene number in a chapter."""
        # Initially empty
        max_num = await repository.get_max_scene_number(test_chapter_id)
        assert max_num == 0

        # Create scenes
        scene1 = Scene(
            id=uuid4(),
            chapter_id=str(test_chapter_id),
            scene_number=5,
            title="Scene 5",
            content="Content",
        )
        scene2 = Scene(
            id=uuid4(),
            chapter_id=str(test_chapter_id),
            scene_number=10,
            title="Scene 10",
            content="Content",
        )
        await repository.save(scene1)
        await repository.save(scene2)

        max_num = await repository.get_max_scene_number(test_chapter_id)
        assert max_num == 10

    async def test_reorder_scenes(
        self,
        repository: PostgresSceneRepository,
        test_chapter_id: UUID,
    ) -> None:
        """Test reordering scenes within a chapter."""
        # Arrange - Create scenes in order 1, 2, 3
        scene1 = Scene(
            id=uuid4(),
            chapter_id=str(test_chapter_id),
            scene_number=1,
            title="First Scene",
            content="Content 1",
        )
        scene2 = Scene(
            id=uuid4(),
            chapter_id=str(test_chapter_id),
            scene_number=2,
            title="Second Scene",
            content="Content 2",
        )
        scene3 = Scene(
            id=uuid4(),
            chapter_id=str(test_chapter_id),
            scene_number=3,
            title="Third Scene",
            content="Content 3",
        )

        await repository.save(scene1)
        await repository.save(scene2)
        await repository.save(scene3)

        # Act - Reorder to 3, 1, 2
        await repository.reorder_scenes(
            test_chapter_id, [scene3.id, scene1.id, scene2.id]
        )

        # Assert
        results = await repository.get_by_chapter(test_chapter_id)
        assert len(results) == 3
        assert results[0].id == scene3.id
        assert results[0].scene_number == 1
        assert results[1].id == scene1.id
        assert results[1].scene_number == 2
        assert results[2].id == scene2.id
        assert results[2].scene_number == 3

    async def test_reorder_scenes_empty_list_raises(
        self,
        repository: PostgresSceneRepository,
        test_chapter_id: UUID,
    ) -> None:
        """Test that empty scene order raises ValueError."""
        with pytest.raises(ValueError, match="Scene order cannot be empty"):
            await repository.reorder_scenes(test_chapter_id, [])

    async def test_reorder_scenes_invalid_id_raises(
        self,
        repository: PostgresSceneRepository,
        test_chapter_id: UUID,
    ) -> None:
        """Test that invalid scene ID raises ValueError."""
        # Arrange
        scene = Scene(
            id=uuid4(),
            chapter_id=str(test_chapter_id),
            scene_number=1,
            title="Scene",
            content="Content",
        )
        await repository.save(scene)

        # Act & Assert
        with pytest.raises(ValueError, match="not found or does not belong to chapter"):
            await repository.reorder_scenes(test_chapter_id, [scene.id, uuid4()])

    async def test_search_by_content(
        self,
        repository: PostgresSceneRepository,
        test_chapter_id: UUID,
    ) -> None:
        """Test searching scenes by content."""
        # Arrange
        scene1 = Scene(
            id=uuid4(),
            chapter_id=str(test_chapter_id),
            scene_number=1,
            title="Scene 1",
            content="The dragon breathes fire.",
        )
        scene2 = Scene(
            id=uuid4(),
            chapter_id=str(test_chapter_id),
            scene_number=2,
            title="Scene 2",
            content="The wizard casts a spell.",
        )
        scene3 = Scene(
            id=uuid4(),
            chapter_id=str(test_chapter_id),
            scene_number=3,
            title="Scene 3",
            content="The hero fights the dragon.",
        )

        await repository.save(scene1)
        await repository.save(scene2)
        await repository.save(scene3)

        # Act - Search for "dragon"
        results = await repository.search_by_content(test_chapter_id, "dragon")

        # Assert
        assert len(results) == 2
        contents = {s.content for s in results}
        assert "The dragon breathes fire." in contents
        assert "The hero fights the dragon." in contents

    async def test_search_by_content_not_found(
        self,
        repository: PostgresSceneRepository,
        test_chapter_id: UUID,
    ) -> None:
        """Test searching for non-existent content."""
        scene = Scene(
            id=uuid4(),
            chapter_id=str(test_chapter_id),
            scene_number=1,
            title="Scene",
            content="Some content",
        )
        await repository.save(scene)

        results = await repository.search_by_content(test_chapter_id, "nonexistent")
        assert results == []

    async def test_search_by_content_negative_limit_raises(
        self,
        repository: PostgresSceneRepository,
        test_chapter_id: UUID,
    ) -> None:
        """Test that negative limit raises ValueError."""
        with pytest.raises(ValueError, match="Limit must be non-negative"):
            await repository.search_by_content(test_chapter_id, "query", limit=-1)

    async def test_save_scene_with_choices(
        self,
        repository: PostgresSceneRepository,
        test_chapter_id: UUID,
    ) -> None:
        """Test saving a scene with choices."""
        # Arrange
        scene_id = uuid4()
        scene = Scene(
            id=scene_id,
            chapter_id=str(test_chapter_id),
            scene_number=1,
            title="Decision Scene",
            content="What do you do?",
            scene_type="decision",
        )

        # Add choices
        choice1 = Choice(
            scene_id=str(scene_id),
            text="Fight the monster",
            next_scene_id=str(uuid4()),
            consequences={"courage": 1},
        )
        choice2 = Choice(
            scene_id=str(scene_id),
            text="Run away",
            next_scene_id=str(uuid4()),
            consequences={"cowardice": 1},
        )
        scene.add_choice(choice1)
        scene.add_choice(choice2)

        # Act
        await repository.save(scene)

        # Assert
        result = await repository.get_by_id(scene_id)
        assert result is not None
        assert len(result.choices) == 2
        assert result.choices[0].text == "Fight the monster"
        assert result.choices[1].text == "Run away"

    async def test_preserve_choices(
        self,
        repository: PostgresSceneRepository,
        test_chapter_id: UUID,
    ) -> None:
        """Test that choices are preserved correctly."""
        # Arrange
        scene_id = uuid4()
        scene = Scene(
            id=scene_id,
            chapter_id=str(test_chapter_id),
            scene_number=1,
            title="Scene with Choices",
            content="Make a choice.",
        )

        choice = Choice(
            scene_id=str(scene_id),
            text="Option A",
            next_scene_id=str(uuid4()),
            conditions={"level": 5},
            consequences={"experience": 10},
            order=1,
            is_hidden=False,
            metadata={"weight": 1.0},
        )
        scene.add_choice(choice)

        await repository.save(scene)

        # Act
        result = await repository.get_by_id(scene_id)

        # Assert
        assert result is not None
        assert len(result.choices) == 1
        restored_choice = result.choices[0]
        assert restored_choice.text == "Option A"
        assert restored_choice.next_scene_id == choice.next_scene_id
        assert restored_choice.conditions == {"level": 5}
        assert restored_choice.consequences == {"experience": 10}
        assert restored_choice.order == 1
        assert restored_choice.is_hidden is False
        assert restored_choice.metadata == {"weight": 1.0}

    async def test_preserve_metadata(
        self,
        repository: PostgresSceneRepository,
        test_chapter_id: UUID,
    ) -> None:
        """Test that metadata is preserved correctly."""
        # Arrange
        metadata = {
            "mood": "tense",
            "characters_present": ["hero", "villain"],
            "location": "castle",
        }
        scene = Scene(
            id=uuid4(),
            chapter_id=str(test_chapter_id),
            scene_number=1,
            title="Scene with metadata",
            content="Content",
            metadata=metadata,
        )
        await repository.save(scene)

        # Act
        result = await repository.get_by_id(scene.id)

        # Assert
        assert result is not None
        assert result.metadata == metadata
