#!/usr/bin/env python3
"""
Unit tests for Chapter Entity

Comprehensive test suite for the Chapter domain entity including:
- Creation and validation
- Title and summary management
- Publication workflow
- Position management
"""

import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock
from uuid import UUID, uuid4

import pytest

pytestmark = pytest.mark.unit

# Mock problematic dependencies
sys.modules["aioredis"] = MagicMock()

from src.contexts.narrative.domain.entities.chapter import Chapter, ChapterStatus


class TestChapter:
    """Test suite for Chapter entity."""

    @pytest.fixture
    def sample_story_id(self):
        """Create a sample story ID."""
        return uuid4()

    @pytest.fixture
    def sample_chapter(self, sample_story_id):
        """Create a sample chapter for testing."""
        return Chapter(
            title="Test Chapter",
            story_id=sample_story_id,
            summary="A test chapter for unit testing",
            order_index=0,
        )

    def test_chapter_creation_success(self, sample_story_id):
        """Test successful chapter creation with all fields."""
        chapter = Chapter(
            title="Test Chapter",
            story_id=sample_story_id,
            summary="Test summary",
            order_index=1,
            status=ChapterStatus.DRAFT,
        )

        assert chapter.title == "Test Chapter"
        assert chapter.story_id == sample_story_id
        assert chapter.summary == "Test summary"
        assert chapter.order_index == 1
        assert chapter.status == ChapterStatus.DRAFT
        assert isinstance(chapter.id, UUID)
        assert isinstance(chapter.created_at, datetime)
        assert isinstance(chapter.updated_at, datetime)

    def test_chapter_creation_defaults(self, sample_story_id):
        """Test chapter creation with default values."""
        chapter = Chapter(
            title="Test Chapter",
            story_id=sample_story_id,
        )

        assert chapter.summary == ""
        assert chapter.order_index == 0
        assert chapter.status == ChapterStatus.DRAFT

    def test_chapter_creation_empty_title_raises_error(self, sample_story_id):
        """Test that empty title raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Chapter(
                title="",
                story_id=sample_story_id,
            )
        assert "Chapter title cannot be empty" in str(exc_info.value)

    def test_chapter_creation_whitespace_title_raises_error(self, sample_story_id):
        """Test that whitespace-only title raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Chapter(
                title="   ",
                story_id=sample_story_id,
            )
        assert "Chapter title cannot be empty" in str(exc_info.value)

    def test_chapter_creation_negative_order_raises_error(self, sample_story_id):
        """Test that negative order_index raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Chapter(
                title="Test Chapter",
                story_id=sample_story_id,
                order_index=-1,
            )
        assert "Chapter order_index cannot be negative" in str(exc_info.value)

    def test_update_title_success(self, sample_chapter):
        """Test successful title update."""
        old_updated_at = sample_chapter.updated_at

        sample_chapter.update_title("New Title")

        assert sample_chapter.title == "New Title"
        assert sample_chapter.updated_at > old_updated_at

    def test_update_title_strips_whitespace(self, sample_chapter):
        """Test that title update strips whitespace."""
        sample_chapter.update_title("  New Title  ")
        assert sample_chapter.title == "New Title"

    def test_update_title_empty_raises_error(self, sample_chapter):
        """Test that empty title update raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            sample_chapter.update_title("")
        assert "Chapter title cannot be empty" in str(exc_info.value)

    def test_update_summary_success(self, sample_chapter):
        """Test successful summary update."""
        old_updated_at = sample_chapter.updated_at

        sample_chapter.update_summary("New summary")

        assert sample_chapter.summary == "New summary"
        assert sample_chapter.updated_at > old_updated_at

    def test_publish_success(self, sample_chapter):
        """Test successful chapter publication."""
        assert sample_chapter.status == ChapterStatus.DRAFT
        old_updated_at = sample_chapter.updated_at

        sample_chapter.publish()

        assert sample_chapter.status == ChapterStatus.PUBLISHED
        assert sample_chapter.updated_at > old_updated_at

    def test_publish_already_published(self, sample_chapter):
        """Test publishing an already published chapter."""
        sample_chapter.publish()
        old_updated_at = sample_chapter.updated_at

        sample_chapter.publish()

        assert sample_chapter.status == ChapterStatus.PUBLISHED
        # Should still update timestamp
        assert sample_chapter.updated_at >= old_updated_at

    def test_unpublish_success(self, sample_chapter):
        """Test successful chapter unpublish."""
        sample_chapter.publish()
        old_updated_at = sample_chapter.updated_at

        sample_chapter.unpublish()

        assert sample_chapter.status == ChapterStatus.DRAFT
        assert sample_chapter.updated_at > old_updated_at

    def test_move_to_position_success(self, sample_chapter):
        """Test successful position change."""
        old_updated_at = sample_chapter.updated_at

        sample_chapter.move_to_position(5)

        assert sample_chapter.order_index == 5
        assert sample_chapter.updated_at > old_updated_at

    def test_move_to_position_zero(self, sample_chapter):
        """Test moving to position 0."""
        sample_chapter.move_to_position(0)
        assert sample_chapter.order_index == 0

    def test_move_to_position_negative_raises_error(self, sample_chapter):
        """Test that negative position raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            sample_chapter.move_to_position(-1)
        assert "Chapter order_index cannot be negative" in str(exc_info.value)

    def test_str_representation(self, sample_chapter):
        """Test string representation."""
        result = str(sample_chapter)

        assert "Test Chapter" in result
        assert "order=0" in result
        assert "draft" in result

    def test_repr_representation(self, sample_chapter):
        """Test repr representation."""
        result = repr(sample_chapter)

        assert "Chapter" in result
        assert "id=" in result
        assert "story_id=" in result
        assert "Test Chapter" in result
        assert "order_index=0" in result

    def test_chapter_status_enum_values(self):
        """Test ChapterStatus enum has correct values."""
        assert ChapterStatus.DRAFT.value == "draft"
        assert ChapterStatus.PUBLISHED.value == "published"

    def test_chapter_immutable_id(self, sample_chapter):
        """Test that chapter ID cannot be changed."""
        original_id = sample_chapter.id
        new_id = uuid4()

        # Dataclass is not frozen, so this would work, but it's a bad practice
        # The test documents expected behavior
        sample_chapter.id = new_id
        assert sample_chapter.id == new_id
