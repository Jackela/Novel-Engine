#!/usr/bin/env python3
"""
Unit tests for Story Entity

Comprehensive test suite for the Story domain entity including:
- Creation and validation
- Title and summary management
- Chapter management (add, remove, get, reorder)
- Publication workflow
"""

import sys
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

pytestmark = pytest.mark.unit

# Mock problematic dependencies
sys.modules["aioredis"] = MagicMock()

from src.contexts.narrative.domain.entities.chapter import Chapter
from src.contexts.narrative.domain.entities.story import Story, StoryStatus


class TestStory:
    """Test suite for Story entity."""

    @pytest.fixture
    def sample_story(self):
        """Create a sample story for testing."""
        return Story(
            title="Test Story",
            summary="A test story for unit testing",
        )

    @pytest.fixture
    def sample_chapter(self):
        """Create a sample chapter."""
        return Chapter(
            title="Test Chapter",
            story_id=uuid4(),
            order_index=0,
        )

    def test_story_creation_success(self):
        """Test successful story creation with all fields."""
        story = Story(
            title="Test Story",
            summary="Test summary",
            status=StoryStatus.DRAFT,
        )

        assert story.title == "Test Story"
        assert story.summary == "Test summary"
        assert story.status == StoryStatus.DRAFT
        assert isinstance(story.id, UUID)
        assert story.chapter_count == 0

    def test_story_creation_defaults(self):
        """Test story creation with default values."""
        story = Story(title="Test Story")

        assert story.summary == ""
        assert story.status == StoryStatus.DRAFT
        assert story.chapter_count == 0

    def test_story_creation_empty_title_raises_error(self):
        """Test that empty title raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Story(title="")
        assert "Story title cannot be empty" in str(exc_info.value)

    def test_story_creation_whitespace_title_raises_error(self):
        """Test that whitespace-only title raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Story(title="   ")
        assert "Story title cannot be empty" in str(exc_info.value)

    def test_update_title_success(self, sample_story):
        """Test successful title update."""
        old_updated_at = sample_story.updated_at

        sample_story.update_title("New Title")

        assert sample_story.title == "New Title"
        assert sample_story.updated_at > old_updated_at

    def test_update_title_strips_whitespace(self, sample_story):
        """Test that title update strips whitespace."""
        sample_story.update_title("  New Title  ")
        assert sample_story.title == "New Title"

    def test_update_title_empty_raises_error(self, sample_story):
        """Test that empty title update raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            sample_story.update_title("")
        assert "Story title cannot be empty" in str(exc_info.value)

    def test_update_summary_success(self, sample_story):
        """Test successful summary update."""
        old_updated_at = sample_story.updated_at

        sample_story.update_summary("New summary")

        assert sample_story.summary == "New summary"
        assert sample_story.updated_at > old_updated_at

    def test_publish_success(self, sample_story):
        """Test successful story publication."""
        assert sample_story.status == StoryStatus.DRAFT

        sample_story.publish()

        assert sample_story.status == StoryStatus.PUBLISHED

    def test_unpublish_success(self, sample_story):
        """Test successful story unpublish."""
        sample_story.publish()
        sample_story.unpublish()
        assert sample_story.status == StoryStatus.DRAFT

    def test_add_chapter_success(self, sample_story, sample_chapter):
        """Test successful chapter addition."""
        # Update chapter's story_id to match
        sample_chapter.story_id = sample_story.id

        sample_story.add_chapter(sample_chapter)

        assert sample_story.chapter_count == 1
        assert sample_chapter in sample_story._chapters

    def test_add_chapter_duplicate_raises_error(self, sample_story, sample_chapter):
        """Test that adding duplicate chapter raises ValueError."""
        sample_chapter.story_id = sample_story.id
        sample_story.add_chapter(sample_chapter)

        with pytest.raises(ValueError) as exc_info:
            sample_story.add_chapter(sample_chapter)
        assert "already exists" in str(exc_info.value)

    def test_add_chapter_updates_timestamp(self, sample_story, sample_chapter):
        """Test that adding chapter updates story timestamp."""
        old_updated_at = sample_story.updated_at
        sample_chapter.story_id = sample_story.id

        sample_story.add_chapter(sample_chapter)

        assert sample_story.updated_at > old_updated_at

    def test_remove_chapter_success(self, sample_story, sample_chapter):
        """Test successful chapter removal."""
        sample_chapter.story_id = sample_story.id
        sample_story.add_chapter(sample_chapter)

        removed = sample_story.remove_chapter(sample_chapter.id)

        assert removed == sample_chapter
        assert sample_story.chapter_count == 0

    def test_remove_chapter_not_found(self, sample_story):
        """Test removing non-existent chapter returns None."""
        result = sample_story.remove_chapter(uuid4())
        assert result is None

    def test_remove_chapter_updates_timestamp(self, sample_story, sample_chapter):
        """Test that removing chapter updates story timestamp."""
        sample_chapter.story_id = sample_story.id
        sample_story.add_chapter(sample_chapter)
        old_updated_at = sample_story.updated_at

        sample_story.remove_chapter(sample_chapter.id)

        assert sample_story.updated_at > old_updated_at

    def test_get_chapter_success(self, sample_story, sample_chapter):
        """Test successful chapter retrieval."""
        sample_chapter.story_id = sample_story.id
        sample_story.add_chapter(sample_chapter)

        result = sample_story.get_chapter(sample_chapter.id)

        assert result == sample_chapter

    def test_get_chapter_not_found(self, sample_story):
        """Test getting non-existent chapter returns None."""
        result = sample_story.get_chapter(uuid4())
        assert result is None

    def test_chapters_property_returns_sorted(self, sample_story):
        """Test that chapters property returns sorted list."""
        # Create chapters with different order indices
        chapter1 = Chapter(
            title="Chapter 1",
            story_id=sample_story.id,
            order_index=2,
        )
        chapter2 = Chapter(
            title="Chapter 2",
            story_id=sample_story.id,
            order_index=0,
        )
        chapter3 = Chapter(
            title="Chapter 3",
            story_id=sample_story.id,
            order_index=1,
        )

        sample_story.add_chapter(chapter1)
        sample_story.add_chapter(chapter2)
        sample_story.add_chapter(chapter3)

        chapters = sample_story.chapters

        # Should be sorted by order_index
        assert chapters[0] == chapter2  # order_index=0
        assert chapters[1] == chapter3  # order_index=1
        assert chapters[2] == chapter1  # order_index=2

    def test_chapters_property_returns_copy(self, sample_story, sample_chapter):
        """Test that chapters property returns a copy, not the original."""
        sample_chapter.story_id = sample_story.id
        sample_story.add_chapter(sample_chapter)

        chapters = sample_story.chapters
        chapters.clear()

        # Original should not be affected
        assert sample_story.chapter_count == 1

    def test_reorder_chapters_success(self, sample_story):
        """Test successful chapter reordering."""
        chapter1 = Chapter(
            title="Chapter 1",
            story_id=sample_story.id,
            order_index=0,
        )
        chapter2 = Chapter(
            title="Chapter 2",
            story_id=sample_story.id,
            order_index=1,
        )

        sample_story.add_chapter(chapter1)
        sample_story.add_chapter(chapter2)

        # Reorder: chapter2 first, then chapter1
        sample_story.reorder_chapters([chapter2.id, chapter1.id])

        assert chapter2.order_index == 0
        assert chapter1.order_index == 1

    def test_reorder_chapters_mismatch_raises_error(self, sample_story):
        """Test reordering with mismatched IDs raises ValueError."""
        chapter = Chapter(
            title="Chapter 1",
            story_id=sample_story.id,
            order_index=0,
        )
        sample_story.add_chapter(chapter)

        with pytest.raises(ValueError) as exc_info:
            sample_story.reorder_chapters([chapter.id, uuid4()])
        assert "must match existing chapters exactly" in str(exc_info.value)

    def test_reorder_chapters_missing_id_raises_error(self, sample_story):
        """Test reordering with missing ID raises ValueError."""
        chapter1 = Chapter(
            title="Chapter 1",
            story_id=sample_story.id,
            order_index=0,
        )
        chapter2 = Chapter(
            title="Chapter 2",
            story_id=sample_story.id,
            order_index=1,
        )
        sample_story.add_chapter(chapter1)
        sample_story.add_chapter(chapter2)

        with pytest.raises(ValueError) as exc_info:
            # Only provide one ID when there are two chapters
            sample_story.reorder_chapters([chapter1.id])
        assert "must match existing chapters exactly" in str(exc_info.value)

    def test_reorder_chapters_updates_timestamp(self, sample_story):
        """Test that reordering updates story timestamp."""
        chapter1 = Chapter(
            title="Chapter 1",
            story_id=sample_story.id,
            order_index=0,
        )
        chapter2 = Chapter(
            title="Chapter 2",
            story_id=sample_story.id,
            order_index=1,
        )
        sample_story.add_chapter(chapter1)
        sample_story.add_chapter(chapter2)
        old_updated_at = sample_story.updated_at

        sample_story.reorder_chapters([chapter2.id, chapter1.id])

        assert sample_story.updated_at > old_updated_at

    def test_chapter_count_property(self, sample_story, sample_chapter):
        """Test chapter_count property."""
        assert sample_story.chapter_count == 0

        sample_chapter.story_id = sample_story.id
        sample_story.add_chapter(sample_chapter)
        assert sample_story.chapter_count == 1

    def test_str_representation(self, sample_story):
        """Test string representation."""
        result = str(sample_story)
        assert "Test Story" in result
        assert "draft" in result
        assert "0 chapters" in result

    def test_repr_representation(self, sample_story):
        """Test repr representation."""
        result = repr(sample_story)
        assert "Story" in result
        assert "id=" in result
        assert "Test Story" in result
        assert "chapters=0" in result


class TestStoryStatus:
    """Test StoryStatus enum."""

    def test_status_values(self):
        """Test that enum has correct values."""
        assert StoryStatus.DRAFT.value == "draft"
        assert StoryStatus.PUBLISHED.value == "published"
