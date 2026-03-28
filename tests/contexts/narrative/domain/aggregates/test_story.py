# mypy: disable-error-code="misc, unreachable"
"""Tests for the Story aggregate root.

This module contains comprehensive tests for the Story domain aggregate,
covering chapter management, status transitions, and publishing workflow.
"""

from __future__ import annotations

from uuid import UUID

import pytest

from src.contexts.narrative.domain.aggregates.story import Story
from src.contexts.narrative.domain.events.story_events import (
    ChapterAdded,
    StoryCompleted,
    StoryCreated,
    StoryPublished,
)


@pytest.fixture
def valid_story() -> Story:
    """Create a valid story for testing."""
    return Story(
        title="Test Story",
        genre="fantasy",
        author_id="author-123",
        target_audience="young adult",
        themes=["adventure", "friendship"],
    )


class TestStory:
    """Test cases for Story aggregate root."""

    def test_create_story_with_valid_data(self) -> None:
        """Test story creation with valid data."""
        story = Story(
            title="My Story",
            genre="sci-fi",
            author_id="author-456",
            status="draft",
            target_audience="adult",
            themes=["space", "exploration"],
            metadata={"word_count": 5000},
        )

        assert story.title == "My Story"
        assert story.genre == "sci-fi"
        assert story.author_id == "author-456"
        assert story.status == "draft"
        assert story.target_audience == "adult"
        assert story.themes == ["space", "exploration"]
        assert story.metadata == {"word_count": 5000}
        assert story.chapter_count == 0
        assert story.current_chapter_id is None
        assert story.current_chapter is None
        assert isinstance(story.id, UUID)
        assert story.version == 0

    def test_create_story_generates_events(self) -> None:
        """Test that story creation generates domain events."""
        story = Story(
            title="Eventful Story",
            genre="mystery",
            author_id="author-789",
        )

        events = story.get_events()
        assert len(events) >= 1

        # Should have StoryCreated event
        created_events = [e for e in events if isinstance(e, StoryCreated)]
        assert len(created_events) == 1
        assert created_events[0].title == "Eventful Story"
        assert created_events[0].genre == "mystery"
        assert created_events[0].author_id == "author-789"

    def test_create_with_empty_title_raises_error(self) -> None:
        """Test that empty title raises ValueError."""
        with pytest.raises(ValueError, match="title cannot be empty"):
            Story(title="", genre="fantasy", author_id="author-123")

    def test_create_with_whitespace_title_raises_error(self) -> None:
        """Test that whitespace-only title raises ValueError."""
        with pytest.raises(ValueError, match="title cannot be empty"):
            Story(title="   ", genre="fantasy", author_id="author-123")

    def test_create_with_too_long_title_raises_error(self) -> None:
        """Test that title exceeding 200 characters raises ValueError."""
        with pytest.raises(ValueError, match="cannot exceed 200 characters"):
            Story(title="x" * 201, genre="fantasy", author_id="author-123")

    def test_create_with_empty_author_id_raises_error(self) -> None:
        """Test that empty author_id raises ValueError."""
        with pytest.raises(ValueError, match="must have an author"):
            Story(title="Test", genre="fantasy", author_id="")

    def test_create_with_invalid_genre_raises_error(self) -> None:
        """Test that invalid genre raises ValueError."""
        with pytest.raises(ValueError, match="Invalid genre"):
            Story(title="Test", genre="invalid-genre", author_id="author-123")

    def test_create_with_valid_genres(self) -> None:
        """Test creating stories with all valid genres."""
        valid_genres = [
            "fantasy",
            "sci-fi",
            "mystery",
            "romance",
            "horror",
            "adventure",
            "historical",
            "thriller",
            "comedy",
            "drama",
        ]

        for genre in valid_genres:
            story = Story(
                title=f"{genre.capitalize()} Story",
                genre=genre,
                author_id="author-123",
            )
            assert story.genre == genre


class TestStoryChapters:
    """Test cases for chapter management."""

    def test_add_chapter(self, valid_story: Story) -> None:
        """Test adding a chapter."""
        chapter = valid_story.add_chapter(
            title="Chapter 1",
            summary="The beginning",
        )

        assert chapter.title == "Chapter 1"
        assert chapter.summary == "The beginning"
        assert chapter.chapter_number == 1
        assert valid_story.chapter_count == 1
        assert valid_story.current_chapter_id == str(chapter.id)
        assert valid_story.current_chapter == chapter

    def test_add_chapter_generates_event(self, valid_story: Story) -> None:
        """Test that adding chapter generates event."""
        valid_story.clear_events()  # Clear creation events

        valid_story.add_chapter("New Chapter", "Summary")

        events = valid_story.get_events()
        chapter_events = [e for e in events if isinstance(e, ChapterAdded)]
        assert len(chapter_events) == 1
        assert chapter_events[0].title == "New Chapter"
        assert chapter_events[0].chapter_number == 1

    def test_add_multiple_chapters(self, valid_story: Story) -> None:
        """Test adding multiple chapters."""
        chapter1 = valid_story.add_chapter("Chapter 1", "First")
        chapter2 = valid_story.add_chapter("Chapter 2", "Second")

        assert valid_story.chapter_count == 2
        assert chapter1.chapter_number == 1
        assert chapter2.chapter_number == 2
        assert valid_story.current_chapter_id == str(chapter2.id)

    def test_add_chapter_beyond_maximum_raises_error(self, valid_story: Story) -> None:
        """Test that adding beyond the long-form chapter cap raises ValueError."""
        # Add up to the configured chapter cap.
        for i in range(Story.MAX_CHAPTERS):
            valid_story.add_chapter(f"Chapter {i + 1}", f"Summary {i + 1}")

        assert valid_story.chapter_count == Story.MAX_CHAPTERS

        # One more chapter should fail.
        with pytest.raises(
            ValueError,
            match=f"cannot have more than {Story.MAX_CHAPTERS} chapters",
        ):
            valid_story.add_chapter("Chapter 11", "Should fail")

    def test_add_chapter_to_completed_story_raises_error(
        self, valid_story: Story
    ) -> None:
        """Test that adding chapter to completed story raises ValueError."""
        # Set up: Add chapter with scene, publish, and complete
        chapter = valid_story.add_chapter("Chapter 1", "Summary")
        chapter.add_scene("Scene content", scene_type="narrative")
        valid_story.publish()
        valid_story.complete()

        with pytest.raises(ValueError, match="completed story"):
            valid_story.add_chapter("Chapter 2", "Should fail")

    def test_get_chapter(self, valid_story: Story) -> None:
        """Test getting chapter by number."""
        chapter1 = valid_story.add_chapter("Chapter 1", "First")
        chapter2 = valid_story.add_chapter("Chapter 2", "Second")

        retrieved = valid_story.get_chapter(1)
        assert retrieved == chapter1

        retrieved = valid_story.get_chapter(2)
        assert retrieved == chapter2

    def test_get_nonexistent_chapter_returns_none(self, valid_story: Story) -> None:
        """Test getting non-existent chapter returns None."""
        result = valid_story.get_chapter(999)
        assert result is None

    def test_switch_chapter(self, valid_story: Story) -> None:
        """Test switching to a different chapter."""
        chapter1 = valid_story.add_chapter("Chapter 1", "First")
        valid_story.add_chapter("Chapter 2", "Second")

        # Switch back to chapter 1
        switched = valid_story.switch_chapter(1)

        assert switched == chapter1
        assert valid_story.current_chapter_id == str(chapter1.id)

    def test_switch_to_nonexistent_chapter_raises_error(
        self, valid_story: Story
    ) -> None:
        """Test switching to non-existent chapter raises ValueError."""
        with pytest.raises(ValueError, match="Chapter 999 not found"):
            valid_story.switch_chapter(999)


class TestStoryPublishing:
    """Test cases for publishing workflow."""

    def test_publish_valid_story(self, valid_story: Story) -> None:
        """Test publishing a valid story."""
        # Add a chapter with a scene
        chapter = valid_story.add_chapter("Chapter 1", "Summary")
        chapter.add_scene("Scene content", scene_type="narrative")

        valid_story.publish()

        assert valid_story.status == "active"
        assert valid_story.is_published is True

    def test_publish_generates_event(self, valid_story: Story) -> None:
        """Test that publishing generates event."""
        chapter = valid_story.add_chapter("Chapter 1", "Summary")
        chapter.add_scene("Scene content")

        valid_story.clear_events()
        valid_story.publish()

        events = valid_story.get_events()
        published_events = [e for e in events if isinstance(e, StoryPublished)]
        assert len(published_events) == 1

    def test_publish_without_chapters_raises_error(self, valid_story: Story) -> None:
        """Test publishing without chapters raises ValueError."""
        with pytest.raises(ValueError, match="at least one chapter"):
            valid_story.publish()

    def test_publish_with_empty_first_chapter_raises_error(
        self, valid_story: Story
    ) -> None:
        """Test publishing when first chapter has no scenes raises ValueError."""
        valid_story.add_chapter("Chapter 1", "Summary")
        # No scenes added

        with pytest.raises(ValueError, match="at least one scene"):
            valid_story.publish()

    def test_publish_non_draft_story_raises_error(self, valid_story: Story) -> None:
        """Test publishing non-draft story raises ValueError."""
        chapter = valid_story.add_chapter("Chapter 1", "Summary")
        chapter.add_scene("Scene content")
        valid_story.publish()

        with pytest.raises(ValueError, match="Only draft stories can be published"):
            valid_story.publish()

    def test_complete_story(self, valid_story: Story) -> None:
        """Test completing an active story."""
        chapter = valid_story.add_chapter("Chapter 1", "Summary")
        chapter.add_scene("Scene content")
        valid_story.publish()

        valid_story.complete()

        assert valid_story.status == "completed"
        assert valid_story.is_completed is True

    def test_complete_generates_event(self, valid_story: Story) -> None:
        """Test that completing generates event."""
        chapter = valid_story.add_chapter("Chapter 1", "Summary")
        chapter.add_scene("Scene content")
        valid_story.publish()

        valid_story.clear_events()
        valid_story.complete()

        events = valid_story.get_events()
        completed_events = [e for e in events if isinstance(e, StoryCompleted)]
        assert len(completed_events) == 1

    def test_complete_non_active_story_raises_error(self, valid_story: Story) -> None:
        """Test completing non-active story raises ValueError."""
        with pytest.raises(ValueError, match="Only active stories can be completed"):
            valid_story.complete()


class TestStoryProperties:
    """Test cases for story properties."""

    def test_is_published_property(self, valid_story: Story) -> None:
        """Test is_published property."""
        assert valid_story.is_published is False

        chapter = valid_story.add_chapter("Chapter 1", "Summary")
        chapter.add_scene("Scene content")
        valid_story.publish()

        assert valid_story.is_published is True

        valid_story.complete()
        assert valid_story.is_published is True

    def test_is_completed_property(self, valid_story: Story) -> None:
        """Test is_completed property."""
        assert valid_story.is_completed is False

        chapter = valid_story.add_chapter("Chapter 1", "Summary")
        chapter.add_scene("Scene content")
        valid_story.publish()

        assert valid_story.is_completed is False

        valid_story.complete()
        assert valid_story.is_completed is True

    def test_current_chapter_property(self, valid_story: Story) -> None:
        """Test current_chapter property."""
        assert valid_story.current_chapter is None

        chapter = valid_story.add_chapter("Chapter 1", "Summary")
        assert valid_story.current_chapter == chapter


class TestStoryMetadata:
    """Test cases for metadata operations."""

    def test_update_metadata(self, valid_story: Story) -> None:
        """Test updating metadata."""
        valid_story.update_metadata("word_count", 5000)
        valid_story.update_metadata("rating", 4.5)

        assert valid_story.metadata["word_count"] == 5000
        assert valid_story.metadata["rating"] == 4.5

    def test_update_metadata_overwrites_existing(self, valid_story: Story) -> None:
        """Test that update overwrites existing metadata."""
        valid_story.update_metadata("key", "old_value")
        valid_story.update_metadata("key", "new_value")

        assert valid_story.metadata["key"] == "new_value"


class TestStorySerialization:
    """Test cases for serialization."""

    def test_to_dict(self, valid_story: Story) -> None:
        """Test converting to dictionary."""
        chapter = valid_story.add_chapter("Chapter 1", "Summary")
        chapter.add_scene("Scene content")
        valid_story.update_metadata("word_count", 1000)

        story_dict = valid_story.to_dict()

        assert story_dict["title"] == "Test Story"
        assert story_dict["genre"] == "fantasy"
        assert story_dict["author_id"] == "author-123"
        assert story_dict["status"] == "draft"
        assert story_dict["target_audience"] == "young adult"
        assert story_dict["themes"] == ["adventure", "friendship"]
        assert story_dict["metadata"] == {"word_count": 1000}
        assert story_dict["chapter_count"] == 1
        assert "chapters" in story_dict
        assert len(story_dict["chapters"]) == 1
        assert "id" in story_dict
        assert "created_at" in story_dict
        assert "updated_at" in story_dict


class TestStoryInvariants:
    """Test cases for invariant validation."""

    def test_chapter_count_matches_chapters_list(self, valid_story: Story) -> None:
        """Test that chapter_count matches chapters list length."""
        assert valid_story.chapter_count == len(valid_story.chapters)

        valid_story.add_chapter("Chapter 1", "Summary")
        assert valid_story.chapter_count == len(valid_story.chapters)

        valid_story.add_chapter("Chapter 2", "Summary")
        assert valid_story.chapter_count == len(valid_story.chapters)

    def test_story_equality(self) -> None:
        """Test story equality based on ID."""
        story1 = Story(title="Story 1", genre="fantasy", author_id="author-1")
        story2 = Story(title="Story 2", genre="sci-fi", author_id="author-2")

        assert story1 != story2

    def test_story_hash(self) -> None:
        """Test story hash based on ID."""
        story1 = Story(title="Story 1", genre="fantasy", author_id="author-1")
        story2 = Story(title="Story 2", genre="fantasy", author_id="author-1")

        assert hash(story1) != hash(story2)
