"""Tests for the Chapter entity.

This module contains comprehensive tests for the Chapter domain entity,
covering scene management, reordering, and metadata operations.
"""

from __future__ import annotations

from uuid import UUID

import pytest

from src.contexts.narrative.domain.entities.chapter import Chapter


@pytest.fixture
def valid_chapter() -> Chapter:
    """Create a valid chapter for testing."""
    return Chapter(
        story_id="story-123",
        chapter_number=1,
        title="Test Chapter",
        summary="A test chapter",
    )


class TestChapter:
    """Test cases for Chapter entity."""

    def test_create_chapter_with_valid_data(self) -> None:
        """Test chapter creation with valid data."""
        chapter = Chapter(
            story_id="story-456",
            chapter_number=2,
            title="Chapter Two",
            summary="The second chapter",
            metadata={"word_count": 5000},
        )

        assert chapter.story_id == "story-456"
        assert chapter.chapter_number == 2
        assert chapter.title == "Chapter Two"
        assert chapter.summary == "The second chapter"
        assert chapter.metadata == {"word_count": 5000}
        assert chapter.scene_count == 0
        assert isinstance(chapter.id, UUID)

    def test_create_chapter_with_minimal_data(self) -> None:
        """Test chapter creation with minimal data."""
        chapter = Chapter(
            story_id="story-123",
            chapter_number=1,
            title="Simple Chapter",
        )

        assert chapter.summary is None
        assert chapter.metadata == {}
        assert len(chapter.scenes) == 0

    def test_create_with_empty_story_id_raises_error(self) -> None:
        """Test that empty story_id raises ValueError."""
        with pytest.raises(ValueError, match="must belong to a story"):
            Chapter(story_id="", chapter_number=1, title="Test")

    def test_create_with_invalid_chapter_number_raises_error(self) -> None:
        """Test that invalid chapter number raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            Chapter(story_id="story-123", chapter_number=0, title="Test")

        with pytest.raises(ValueError, match="must be positive"):
            Chapter(story_id="story-123", chapter_number=-1, title="Test")

    def test_create_with_empty_title_raises_error(self) -> None:
        """Test that empty title raises ValueError."""
        with pytest.raises(ValueError, match="title cannot be empty"):
            Chapter(story_id="story-123", chapter_number=1, title="")

    def test_create_with_whitespace_title_raises_error(self) -> None:
        """Test that whitespace-only title raises ValueError."""
        with pytest.raises(ValueError, match="title cannot be empty"):
            Chapter(story_id="story-123", chapter_number=1, title="   ")

    def test_create_with_too_long_title_raises_error(self) -> None:
        """Test that title exceeding 200 characters raises ValueError."""
        with pytest.raises(ValueError, match="cannot exceed 200 characters"):
            Chapter(story_id="story-123", chapter_number=1, title="x" * 201)


class TestChapterScenes:
    """Test cases for scene management."""

    def test_add_scene(self, valid_chapter: Chapter) -> None:
        """Test adding a scene."""
        scene = valid_chapter.add_scene(
            content="It was a dark and stormy night...",
            scene_type="narrative",
            title="Opening Scene",
        )

        assert scene.content == "It was a dark and stormy night..."
        assert scene.scene_type == "narrative"
        assert scene.title == "Opening Scene"
        assert scene.scene_number == 1
        assert valid_chapter.scene_count == 1

    def test_add_scene_with_minimal_data(self, valid_chapter: Chapter) -> None:
        """Test adding scene with minimal data."""
        scene = valid_chapter.add_scene("Simple content")

        assert scene.content == "Simple content"
        assert scene.scene_type == "narrative"  # Default
        assert scene.title is None
        assert scene.scene_number == 1

    def test_add_multiple_scenes(self, valid_chapter: Chapter) -> None:
        """Test adding multiple scenes."""
        scene1 = valid_chapter.add_scene("Content 1", scene_type="narrative")
        scene2 = valid_chapter.add_scene("Content 2", scene_type="dialogue")
        scene3 = valid_chapter.add_scene("Content 3", scene_type="action")

        assert valid_chapter.scene_count == 3
        assert scene1.scene_number == 1
        assert scene2.scene_number == 2
        assert scene3.scene_number == 3

    def test_add_scene_beyond_maximum_raises_error(
        self, valid_chapter: Chapter
    ) -> None:
        """Test that adding more than 20 scenes raises ValueError."""
        # Add 20 scenes
        for i in range(20):
            valid_chapter.add_scene(f"Scene {i + 1} content")

        assert valid_chapter.scene_count == 20

        # 21st scene should fail
        with pytest.raises(ValueError, match="cannot have more than 20 scenes"):
            valid_chapter.add_scene("Extra scene content")

    def test_get_scene(self, valid_chapter: Chapter) -> None:
        """Test getting scene by number."""
        scene1 = valid_chapter.add_scene("Content 1")
        scene2 = valid_chapter.add_scene("Content 2")

        retrieved = valid_chapter.get_scene(1)
        assert retrieved == scene1

        retrieved = valid_chapter.get_scene(2)
        assert retrieved == scene2

    def test_get_nonexistent_scene_returns_none(self, valid_chapter: Chapter) -> None:
        """Test getting non-existent scene returns None."""
        result = valid_chapter.get_scene(999)
        assert result is None

    def test_remove_scene(self, valid_chapter: Chapter) -> None:
        """Test removing a scene."""
        valid_chapter.add_scene("Scene 1")
        valid_chapter.add_scene("Scene 2")
        valid_chapter.add_scene("Scene 3")

        valid_chapter.remove_scene(2)

        assert valid_chapter.scene_count == 2
        assert valid_chapter.get_scene(1) is not None
        assert valid_chapter.get_scene(2) is not None  # Renumbered
        assert valid_chapter.get_scene(3) is None

    def test_remove_scene_renumbers_remaining(self, valid_chapter: Chapter) -> None:
        """Test that removing scene renumbers remaining scenes."""
        valid_chapter.add_scene("Scene 1")
        valid_chapter.add_scene("Scene 2")
        valid_chapter.add_scene("Scene 3")

        valid_chapter.remove_scene(2)

        # Scenes should be renumbered 1, 2
        scenes = valid_chapter.scenes
        assert scenes[0].scene_number == 1
        assert scenes[1].scene_number == 2

    def test_remove_nonexistent_scene_does_nothing(
        self, valid_chapter: Chapter
    ) -> None:
        """Test removing non-existent scene does nothing."""
        valid_chapter.add_scene("Scene 1")

        valid_chapter.remove_scene(999)  # Should not raise

        assert valid_chapter.scene_count == 1


class TestChapterSceneReordering:
    """Test cases for scene reordering."""

    def test_reorder_scenes(self, valid_chapter: Chapter) -> None:
        """Test reordering scenes."""
        scene1 = valid_chapter.add_scene("Content 1")
        scene2 = valid_chapter.add_scene("Content 2")
        scene3 = valid_chapter.add_scene("Content 3")

        # Reorder: 3, 1, 2
        valid_chapter.reorder_scenes([3, 1, 2])

        assert valid_chapter.scenes[0] == scene3
        assert valid_chapter.scenes[1] == scene1
        assert valid_chapter.scenes[2] == scene2

    def test_reorder_scenes_renumbers(self, valid_chapter: Chapter) -> None:
        """Test that reordering renumbers scenes."""
        valid_chapter.add_scene("Content 1")
        valid_chapter.add_scene("Content 2")
        valid_chapter.add_scene("Content 3")

        valid_chapter.reorder_scenes([3, 1, 2])

        # After reorder, scene numbers should be 1, 2, 3
        for i, scene in enumerate(valid_chapter.scenes, 1):
            assert scene.scene_number == i

    def test_reorder_with_wrong_count_raises_error(
        self, valid_chapter: Chapter
    ) -> None:
        """Test reordering with wrong number of scenes raises ValueError."""
        valid_chapter.add_scene("Scene 1")
        valid_chapter.add_scene("Scene 2")

        with pytest.raises(ValueError, match="must include all scenes"):
            valid_chapter.reorder_scenes([1])  # Only 1, but 2 scenes exist

        with pytest.raises(ValueError, match="must include all scenes"):
            valid_chapter.reorder_scenes([1, 2, 3])  # 3 items, but 2 scenes exist

    def test_reorder_with_invalid_numbers_raises_error(
        self, valid_chapter: Chapter
    ) -> None:
        """Test reordering with invalid scene numbers raises ValueError."""
        valid_chapter.add_scene("Scene 1")
        valid_chapter.add_scene("Scene 2")

        with pytest.raises(ValueError, match="invalid scene numbers"):
            valid_chapter.reorder_scenes([1, 999])

        with pytest.raises(ValueError, match="invalid scene numbers"):
            valid_chapter.reorder_scenes([0, 1])


class TestChapterProperties:
    """Test cases for chapter properties."""

    def test_is_first_chapter_property(self) -> None:
        """Test is_first_chapter property."""
        chapter1 = Chapter(story_id="story-123", chapter_number=1, title="First")
        chapter2 = Chapter(story_id="story-123", chapter_number=2, title="Second")

        assert chapter1.is_first_chapter is True
        assert chapter2.is_first_chapter is False

    def test_current_scene_property(self, valid_chapter: Chapter) -> None:
        """Test current_scene property."""
        assert valid_chapter.current_scene is None

        scene1 = valid_chapter.add_scene("Scene 1")
        assert valid_chapter.current_scene == scene1

        scene2 = valid_chapter.add_scene("Scene 2")
        assert valid_chapter.current_scene == scene2

    def test_scene_count_property(self, valid_chapter: Chapter) -> None:
        """Test scene_count property."""
        assert valid_chapter.scene_count == 0

        valid_chapter.add_scene("Scene 1")
        assert valid_chapter.scene_count == 1

        valid_chapter.add_scene("Scene 2")
        assert valid_chapter.scene_count == 2


class TestChapterUpdates:
    """Test cases for chapter updates."""

    def test_update_title(self, valid_chapter: Chapter) -> None:
        """Test updating chapter title."""
        valid_chapter.update_title("New Title")

        assert valid_chapter.title == "New Title"

    def test_update_title_with_empty_raises_error(self, valid_chapter: Chapter) -> None:
        """Test that updating to empty title raises ValueError."""
        with pytest.raises(ValueError, match="Title cannot be empty"):
            valid_chapter.update_title("")

    def test_update_title_with_whitespace_raises_error(
        self, valid_chapter: Chapter
    ) -> None:
        """Test that updating to whitespace title raises ValueError."""
        with pytest.raises(ValueError, match="Title cannot be empty"):
            valid_chapter.update_title("   ")

    def test_update_title_too_long_raises_error(self, valid_chapter: Chapter) -> None:
        """Test that updating to long title raises ValueError."""
        with pytest.raises(ValueError, match="Title too long"):
            valid_chapter.update_title("x" * 201)


class TestChapterSerialization:
    """Test cases for serialization."""

    def test_to_dict(self, valid_chapter: Chapter) -> None:
        """Test converting to dictionary."""
        valid_chapter.add_scene("Scene content", scene_type="narrative")
        valid_chapter.metadata["word_count"] = 1000

        chapter_dict = valid_chapter.to_dict()

        assert chapter_dict["story_id"] == "story-123"
        assert chapter_dict["chapter_number"] == 1
        assert chapter_dict["title"] == "Test Chapter"
        assert chapter_dict["summary"] == "A test chapter"
        assert chapter_dict["metadata"] == {"word_count": 1000}
        assert "scenes" in chapter_dict
        assert len(chapter_dict["scenes"]) == 1
        assert "id" in chapter_dict
        assert "created_at" in chapter_dict
        assert "updated_at" in chapter_dict


class TestChapterInvariants:
    """Test cases for invariant validation."""

    def test_scene_count_matches_scenes_list(self, valid_chapter: Chapter) -> None:
        """Test that scene_count matches scenes list length."""
        assert valid_chapter.scene_count == len(valid_chapter.scenes)

        valid_chapter.add_scene("Scene 1")
        assert valid_chapter.scene_count == len(valid_chapter.scenes)

        valid_chapter.add_scene("Scene 2")
        assert valid_chapter.scene_count == len(valid_chapter.scenes)

    def test_chapter_belongs_to_story(self) -> None:
        """Test that chapter always belongs to a story."""
        chapter = Chapter(
            story_id="story-123",
            chapter_number=1,
            title="Test",
        )

        assert chapter.story_id == "story-123"

    def test_chapter_number_positive(self) -> None:
        """Test that chapter_number is always positive."""
        chapter = Chapter(
            story_id="story-123",
            chapter_number=5,
            title="Test",
        )

        assert chapter.chapter_number > 0

    def test_chapter_equality(self) -> None:
        """Test chapter equality based on ID."""
        chapter1 = Chapter(story_id="story-1", chapter_number=1, title="Chapter 1")
        chapter2 = Chapter(story_id="story-2", chapter_number=2, title="Chapter 2")

        assert chapter1 != chapter2

    def test_chapter_hash(self) -> None:
        """Test chapter hash based on ID."""
        chapter1 = Chapter(story_id="story-1", chapter_number=1, title="Chapter")
        chapter2 = Chapter(story_id="story-1", chapter_number=1, title="Chapter")

        assert hash(chapter1) != hash(chapter2)
