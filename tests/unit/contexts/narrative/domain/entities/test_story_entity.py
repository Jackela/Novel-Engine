"""Unit Tests for Story Entity.

This test suite covers the Story entity which serves as the root aggregate
for managing novels within the Narrative bounded context.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from src.contexts.narrative.domain.entities.story import Story, StoryStatus
from src.contexts.narrative.domain.entities.chapter import Chapter


class TestStoryCreation:
    """Test suite for Story instantiation and basic functionality."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_story_with_title(self):
        """Test creating a Story with a valid title."""
        story = Story(title="My First Novel")

        assert story.title == "My First Novel"
        assert isinstance(story.id, UUID)
        assert story.summary == ""
        assert story.status == StoryStatus.DRAFT
        assert isinstance(story.created_at, datetime)
        assert isinstance(story.updated_at, datetime)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_story_with_all_attributes(self):
        """Test creating a Story with all optional attributes."""
        story_id = uuid4()
        created = datetime(2024, 1, 1, tzinfo=timezone.utc)

        story = Story(
            title="Epic Fantasy",
            id=story_id,
            summary="A tale of heroes and magic",
            status=StoryStatus.PUBLISHED,
            created_at=created,
            updated_at=created,
        )

        assert story.title == "Epic Fantasy"
        assert story.id == story_id
        assert story.summary == "A tale of heroes and magic"
        assert story.status == StoryStatus.PUBLISHED
        assert story.created_at == created

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_story_generates_unique_ids(self):
        """Test that each Story gets a unique ID."""
        story1 = Story(title="Story One")
        story2 = Story(title="Story Two")
        story3 = Story(title="Story Three")

        ids = {story1.id, story2.id, story3.id}
        assert len(ids) == 3

    @pytest.mark.unit
    def test_create_story_with_empty_title_raises_error(self):
        """Test that empty title raises ValueError."""
        with pytest.raises(ValueError, match="Story title cannot be empty"):
            Story(title="")

    @pytest.mark.unit
    def test_create_story_with_whitespace_title_raises_error(self):
        """Test that whitespace-only title raises ValueError."""
        with pytest.raises(ValueError, match="Story title cannot be empty"):
            Story(title="   ")


class TestStoryStatusEnum:
    """Test suite for StoryStatus enum."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_status_values(self):
        """Test that StoryStatus has expected values."""
        assert StoryStatus.DRAFT.value == "draft"
        assert StoryStatus.PUBLISHED.value == "published"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_status_is_string_enum(self):
        """Test that StoryStatus values are strings."""
        assert isinstance(StoryStatus.DRAFT, str)
        assert StoryStatus.DRAFT == "draft"


class TestStoryTitleOperations:
    """Test suite for Story title operations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_title(self):
        """Test updating the story title."""
        story = Story(title="Old Title")
        original_updated_at = story.updated_at

        # Small delay to ensure timestamp difference
        story.update_title("New Title")

        assert story.title == "New Title"
        assert story.updated_at >= original_updated_at

    @pytest.mark.unit
    def test_update_title_trims_whitespace(self):
        """Test that title update trims whitespace."""
        story = Story(title="Title")
        story.update_title("  Trimmed Title  ")

        assert story.title == "Trimmed Title"

    @pytest.mark.unit
    def test_update_title_empty_raises_error(self):
        """Test that updating to empty title raises ValueError."""
        story = Story(title="Valid Title")

        with pytest.raises(ValueError, match="Story title cannot be empty"):
            story.update_title("")


class TestStorySummaryOperations:
    """Test suite for Story summary operations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_summary(self):
        """Test updating the story summary."""
        story = Story(title="My Story")
        story.update_summary("A new summary")

        assert story.summary == "A new summary"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_summary_allows_empty(self):
        """Test that empty summary is allowed."""
        story = Story(title="My Story", summary="Has a summary")
        story.update_summary("")

        assert story.summary == ""


class TestStoryStatusOperations:
    """Test suite for Story status operations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_publish_story(self):
        """Test publishing a draft story."""
        story = Story(title="Draft Story")
        assert story.status == StoryStatus.DRAFT

        story.publish()

        assert story.status == StoryStatus.PUBLISHED

    @pytest.mark.unit
    @pytest.mark.fast
    def test_unpublish_story(self):
        """Test unpublishing a published story."""
        story = Story(title="Published Story", status=StoryStatus.PUBLISHED)
        assert story.status == StoryStatus.PUBLISHED

        story.unpublish()

        assert story.status == StoryStatus.DRAFT


class TestStoryChapterManagement:
    """Test suite for Story chapter management."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_story_starts_with_no_chapters(self):
        """Test that a new story has no chapters."""
        story = Story(title="Empty Story")

        assert story.chapter_count == 0
        assert story.chapters == []

    @pytest.mark.unit
    @pytest.mark.fast
    def test_add_chapter(self):
        """Test adding a chapter to a story."""
        story = Story(title="My Story")
        chapter = Chapter(title="Chapter One", story_id=story.id, order_index=0)

        story.add_chapter(chapter)

        assert story.chapter_count == 1
        assert chapter in story.chapters

    @pytest.mark.unit
    def test_add_duplicate_chapter_raises_error(self):
        """Test that adding duplicate chapter raises ValueError."""
        story = Story(title="My Story")
        chapter = Chapter(title="Chapter One", story_id=story.id)

        story.add_chapter(chapter)

        with pytest.raises(ValueError, match="already exists"):
            story.add_chapter(chapter)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_remove_chapter(self):
        """Test removing a chapter from a story."""
        story = Story(title="My Story")
        chapter = Chapter(title="Chapter One", story_id=story.id)

        story.add_chapter(chapter)
        removed = story.remove_chapter(chapter.id)

        assert removed == chapter
        assert story.chapter_count == 0

    @pytest.mark.unit
    @pytest.mark.fast
    def test_remove_nonexistent_chapter_returns_none(self):
        """Test that removing nonexistent chapter returns None."""
        story = Story(title="My Story")
        result = story.remove_chapter(uuid4())

        assert result is None

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_chapter(self):
        """Test getting a chapter by ID."""
        story = Story(title="My Story")
        chapter = Chapter(title="Chapter One", story_id=story.id)

        story.add_chapter(chapter)
        retrieved = story.get_chapter(chapter.id)

        assert retrieved == chapter

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_nonexistent_chapter_returns_none(self):
        """Test that getting nonexistent chapter returns None."""
        story = Story(title="My Story")
        result = story.get_chapter(uuid4())

        assert result is None

    @pytest.mark.unit
    @pytest.mark.fast
    def test_chapters_returns_sorted_by_order_index(self):
        """Test that chapters property returns sorted list."""
        story = Story(title="My Story")
        chapter3 = Chapter(title="Chapter Three", story_id=story.id, order_index=2)
        chapter1 = Chapter(title="Chapter One", story_id=story.id, order_index=0)
        chapter2 = Chapter(title="Chapter Two", story_id=story.id, order_index=1)

        story.add_chapter(chapter3)
        story.add_chapter(chapter1)
        story.add_chapter(chapter2)

        chapters = story.chapters
        assert chapters[0].title == "Chapter One"
        assert chapters[1].title == "Chapter Two"
        assert chapters[2].title == "Chapter Three"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_chapters_returns_copy(self):
        """Test that chapters property returns a copy, not the internal list."""
        story = Story(title="My Story")
        chapter = Chapter(title="Chapter One", story_id=story.id)
        story.add_chapter(chapter)

        chapters = story.chapters
        chapters.clear()

        assert story.chapter_count == 1


class TestStoryChapterReordering:
    """Test suite for chapter reordering operations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_reorder_chapters(self):
        """Test reordering chapters."""
        story = Story(title="My Story")
        chapter1 = Chapter(title="Chapter One", story_id=story.id, order_index=0)
        chapter2 = Chapter(title="Chapter Two", story_id=story.id, order_index=1)
        chapter3 = Chapter(title="Chapter Three", story_id=story.id, order_index=2)

        story.add_chapter(chapter1)
        story.add_chapter(chapter2)
        story.add_chapter(chapter3)

        # Reorder: 3, 1, 2
        story.reorder_chapters([chapter3.id, chapter1.id, chapter2.id])

        chapters = story.chapters
        assert chapters[0].id == chapter3.id
        assert chapters[1].id == chapter1.id
        assert chapters[2].id == chapter2.id

    @pytest.mark.unit
    def test_reorder_chapters_with_missing_id_raises_error(self):
        """Test that reordering with missing ID raises ValueError."""
        story = Story(title="My Story")
        chapter1 = Chapter(title="Chapter One", story_id=story.id)
        chapter2 = Chapter(title="Chapter Two", story_id=story.id)

        story.add_chapter(chapter1)
        story.add_chapter(chapter2)

        with pytest.raises(ValueError, match="must match existing chapters"):
            story.reorder_chapters([chapter1.id])  # Missing chapter2

    @pytest.mark.unit
    def test_reorder_chapters_with_extra_id_raises_error(self):
        """Test that reordering with extra ID raises ValueError."""
        story = Story(title="My Story")
        chapter1 = Chapter(title="Chapter One", story_id=story.id)

        story.add_chapter(chapter1)

        with pytest.raises(ValueError, match="must match existing chapters"):
            story.reorder_chapters([chapter1.id, uuid4()])  # Extra random ID


class TestStoryStringRepresentation:
    """Test suite for Story string representations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_str_representation(self):
        """Test string representation of Story."""
        story = Story(title="My Novel")

        str_repr = str(story)

        assert "My Novel" in str_repr
        assert "draft" in str_repr
        assert "0 chapters" in str_repr

    @pytest.mark.unit
    @pytest.mark.fast
    def test_repr_representation(self):
        """Test repr representation of Story."""
        story = Story(title="My Novel")

        repr_str = repr(story)

        assert "Story" in repr_str
        assert "My Novel" in repr_str
        assert str(story.id) in repr_str
