"""Unit Tests for Chapter Entity.

This test suite covers the Chapter entity which represents a container
for scenes within a Story in the Narrative bounded context.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from src.contexts.narrative.domain.entities.chapter import Chapter, ChapterStatus

pytestmark = pytest.mark.unit


class TestChapterCreation:
    """Test suite for Chapter instantiation and basic functionality."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_chapter_with_required_fields(self):
        """Test creating a Chapter with required fields."""
        story_id = uuid4()
        chapter = Chapter(title="Chapter One", story_id=story_id)

        assert chapter.title == "Chapter One"
        assert chapter.story_id == story_id
        assert isinstance(chapter.id, UUID)
        assert chapter.summary == ""
        assert chapter.order_index == 0
        assert chapter.status == ChapterStatus.DRAFT
        assert isinstance(chapter.created_at, datetime)
        assert isinstance(chapter.updated_at, datetime)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_chapter_with_all_attributes(self):
        """Test creating a Chapter with all optional attributes."""
        chapter_id = uuid4()
        story_id = uuid4()
        created = datetime(2024, 1, 1, tzinfo=timezone.utc)

        chapter = Chapter(
            title="The Beginning",
            story_id=story_id,
            id=chapter_id,
            summary="Where our story starts",
            order_index=5,
            status=ChapterStatus.PUBLISHED,
            created_at=created,
            updated_at=created,
        )

        assert chapter.title == "The Beginning"
        assert chapter.story_id == story_id
        assert chapter.id == chapter_id
        assert chapter.summary == "Where our story starts"
        assert chapter.order_index == 5
        assert chapter.status == ChapterStatus.PUBLISHED
        assert chapter.created_at == created

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_chapter_generates_unique_ids(self):
        """Test that each Chapter gets a unique ID."""
        story_id = uuid4()
        chapter1 = Chapter(title="Chapter 1", story_id=story_id)
        chapter2 = Chapter(title="Chapter 2", story_id=story_id)
        chapter3 = Chapter(title="Chapter 3", story_id=story_id)

        ids = {chapter1.id, chapter2.id, chapter3.id}
        assert len(ids) == 3

    @pytest.mark.unit
    def test_create_chapter_with_empty_title_raises_error(self):
        """Test that empty title raises ValueError."""
        with pytest.raises(ValueError, match="Chapter title cannot be empty"):
            Chapter(title="", story_id=uuid4())

    @pytest.mark.unit
    def test_create_chapter_with_whitespace_title_raises_error(self):
        """Test that whitespace-only title raises ValueError."""
        with pytest.raises(ValueError, match="Chapter title cannot be empty"):
            Chapter(title="   ", story_id=uuid4())

    @pytest.mark.unit
    def test_create_chapter_with_negative_order_index_raises_error(self):
        """Test that negative order_index raises ValueError."""
        with pytest.raises(ValueError, match="order_index cannot be negative"):
            Chapter(title="Invalid Chapter", story_id=uuid4(), order_index=-1)


class TestChapterStatusEnum:
    """Test suite for ChapterStatus enum."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_status_values(self):
        """Test that ChapterStatus has expected values."""
        assert ChapterStatus.DRAFT.value == "draft"
        assert ChapterStatus.PUBLISHED.value == "published"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_status_is_string_enum(self):
        """Test that ChapterStatus values are strings."""
        assert isinstance(ChapterStatus.DRAFT, str)
        assert ChapterStatus.DRAFT == "draft"


class TestChapterTitleOperations:
    """Test suite for Chapter title operations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_title(self):
        """Test updating the chapter title."""
        chapter = Chapter(title="Old Title", story_id=uuid4())
        original_updated_at = chapter.updated_at

        chapter.update_title("New Title")

        assert chapter.title == "New Title"
        assert chapter.updated_at >= original_updated_at

    @pytest.mark.unit
    def test_update_title_trims_whitespace(self):
        """Test that title update trims whitespace."""
        chapter = Chapter(title="Title", story_id=uuid4())
        chapter.update_title("  Trimmed Title  ")

        assert chapter.title == "Trimmed Title"

    @pytest.mark.unit
    def test_update_title_empty_raises_error(self):
        """Test that updating to empty title raises ValueError."""
        chapter = Chapter(title="Valid Title", story_id=uuid4())

        with pytest.raises(ValueError, match="Chapter title cannot be empty"):
            chapter.update_title("")


class TestChapterSummaryOperations:
    """Test suite for Chapter summary operations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_summary(self):
        """Test updating the chapter summary."""
        chapter = Chapter(title="Chapter", story_id=uuid4())
        chapter.update_summary("A new summary")

        assert chapter.summary == "A new summary"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_summary_allows_empty(self):
        """Test that empty summary is allowed."""
        chapter = Chapter(title="Chapter", story_id=uuid4(), summary="Has a summary")
        chapter.update_summary("")

        assert chapter.summary == ""


class TestChapterStatusOperations:
    """Test suite for Chapter status operations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_publish_chapter(self):
        """Test publishing a draft chapter."""
        chapter = Chapter(title="Draft Chapter", story_id=uuid4())
        assert chapter.status == ChapterStatus.DRAFT

        chapter.publish()

        assert chapter.status == ChapterStatus.PUBLISHED

    @pytest.mark.unit
    @pytest.mark.fast
    def test_unpublish_chapter(self):
        """Test unpublishing a published chapter."""
        chapter = Chapter(
            title="Published Chapter", story_id=uuid4(), status=ChapterStatus.PUBLISHED
        )
        assert chapter.status == ChapterStatus.PUBLISHED

        chapter.unpublish()

        assert chapter.status == ChapterStatus.DRAFT


class TestChapterOrderOperations:
    """Test suite for Chapter order/position operations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_move_to_position(self):
        """Test moving chapter to a new position."""
        chapter = Chapter(title="Chapter", story_id=uuid4(), order_index=0)

        chapter.move_to_position(5)

        assert chapter.order_index == 5

    @pytest.mark.unit
    def test_move_to_negative_position_raises_error(self):
        """Test that moving to negative position raises ValueError."""
        chapter = Chapter(title="Chapter", story_id=uuid4(), order_index=3)

        with pytest.raises(ValueError, match="order_index cannot be negative"):
            chapter.move_to_position(-1)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_move_to_zero_position(self):
        """Test moving chapter to position zero."""
        chapter = Chapter(title="Chapter", story_id=uuid4(), order_index=5)

        chapter.move_to_position(0)

        assert chapter.order_index == 0


class TestChapterStringRepresentation:
    """Test suite for Chapter string representations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_str_representation(self):
        """Test string representation of Chapter."""
        chapter = Chapter(title="The Beginning", story_id=uuid4(), order_index=0)

        str_repr = str(chapter)

        assert "The Beginning" in str_repr
        assert "order=0" in str_repr
        assert "draft" in str_repr

    @pytest.mark.unit
    @pytest.mark.fast
    def test_repr_representation(self):
        """Test repr representation of Chapter."""
        story_id = uuid4()
        chapter = Chapter(title="The Beginning", story_id=story_id, order_index=0)

        repr_str = repr(chapter)

        assert "Chapter" in repr_str
        assert "The Beginning" in repr_str
        assert str(chapter.id) in repr_str
        assert str(story_id) in repr_str


class TestChapterTimestamps:
    """Test suite for Chapter timestamp behavior."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_operations_touch_timestamp(self):
        """Test that update operations update the timestamp."""
        chapter = Chapter(title="Chapter", story_id=uuid4())
        original_timestamp = chapter.updated_at

        # Each operation should update the timestamp
        chapter.update_title("New Title")
        assert chapter.updated_at >= original_timestamp

        timestamp_after_title = chapter.updated_at
        chapter.update_summary("Summary")
        assert chapter.updated_at >= timestamp_after_title

        timestamp_after_summary = chapter.updated_at
        chapter.publish()
        assert chapter.updated_at >= timestamp_after_summary

        timestamp_after_publish = chapter.updated_at
        chapter.move_to_position(3)
        assert chapter.updated_at >= timestamp_after_publish
