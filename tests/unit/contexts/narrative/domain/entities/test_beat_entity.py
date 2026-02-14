"""Unit Tests for Beat Entity.

This test suite covers the Beat entity which represents the atomic unit
of narrative within a Scene in the Narrative bounded context.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from src.contexts.narrative.domain.entities.beat import Beat, BeatType

pytestmark = pytest.mark.unit


class TestBeatCreation:
    """Test suite for Beat instantiation and basic functionality."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_beat_with_required_fields(self):
        """Test creating a Beat with required fields."""
        scene_id = uuid4()
        beat = Beat(scene_id=scene_id)

        assert beat.scene_id == scene_id
        assert isinstance(beat.id, UUID)
        assert beat.content == ""
        assert beat.order_index == 0
        assert beat.beat_type == BeatType.ACTION
        assert beat.notes == ""
        assert isinstance(beat.created_at, datetime)
        assert isinstance(beat.updated_at, datetime)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_beat_with_all_attributes(self):
        """Test creating a Beat with all optional attributes."""
        beat_id = uuid4()
        scene_id = uuid4()
        created = datetime(2024, 1, 1, tzinfo=timezone.utc)

        beat = Beat(
            scene_id=scene_id,
            id=beat_id,
            content="The hero drew his sword.",
            order_index=5,
            beat_type=BeatType.ACTION,
            notes="Key moment",
            created_at=created,
            updated_at=created,
        )

        assert beat.scene_id == scene_id
        assert beat.id == beat_id
        assert beat.content == "The hero drew his sword."
        assert beat.order_index == 5
        assert beat.beat_type == BeatType.ACTION
        assert beat.notes == "Key moment"
        assert beat.created_at == created

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_beat_generates_unique_ids(self):
        """Test that each Beat gets a unique ID."""
        scene_id = uuid4()
        beat1 = Beat(scene_id=scene_id)
        beat2 = Beat(scene_id=scene_id)
        beat3 = Beat(scene_id=scene_id)

        ids = {beat1.id, beat2.id, beat3.id}
        assert len(ids) == 3

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_beat_with_empty_content_allowed(self):
        """Test that empty content is allowed for beats."""
        beat = Beat(scene_id=uuid4(), content="")
        assert beat.content == ""

    @pytest.mark.unit
    def test_create_beat_with_negative_order_index_raises_error(self):
        """Test that negative order_index raises ValueError."""
        with pytest.raises(ValueError, match="order_index cannot be negative"):
            Beat(scene_id=uuid4(), order_index=-1)


class TestBeatTypeEnum:
    """Test suite for BeatType enum."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_beat_type_values(self):
        """Test that BeatType has expected values."""
        assert BeatType.ACTION.value == "action"
        assert BeatType.DIALOGUE.value == "dialogue"
        assert BeatType.REACTION.value == "reaction"
        assert BeatType.REVELATION.value == "revelation"
        assert BeatType.TRANSITION.value == "transition"
        assert BeatType.DESCRIPTION.value == "description"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_beat_type_is_string_enum(self):
        """Test that BeatType values are strings."""
        assert isinstance(BeatType.ACTION, str)
        assert BeatType.ACTION == "action"


class TestBeatContentOperations:
    """Test suite for Beat content operations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_content(self):
        """Test updating the beat content."""
        beat = Beat(scene_id=uuid4(), content="Old content")
        original_updated_at = beat.updated_at

        beat.update_content("New content")

        assert beat.content == "New content"
        assert beat.updated_at >= original_updated_at

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_content_allows_empty(self):
        """Test that empty content is allowed."""
        beat = Beat(scene_id=uuid4(), content="Has content")
        beat.update_content("")

        assert beat.content == ""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_append_content(self):
        """Test appending content to a beat."""
        beat = Beat(scene_id=uuid4(), content="Start.")
        original_updated_at = beat.updated_at

        beat.append_content(" Middle.")

        assert beat.content == "Start. Middle."
        assert beat.updated_at >= original_updated_at

    @pytest.mark.unit
    @pytest.mark.fast
    def test_append_content_to_empty(self):
        """Test appending content to empty beat."""
        beat = Beat(scene_id=uuid4(), content="")

        beat.append_content("First content")

        assert beat.content == "First content"


class TestBeatTypeOperations:
    """Test suite for Beat type operations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_change_type(self):
        """Test changing the beat type."""
        beat = Beat(scene_id=uuid4(), beat_type=BeatType.ACTION)

        beat.change_type(BeatType.DIALOGUE)

        assert beat.beat_type == BeatType.DIALOGUE

    @pytest.mark.unit
    @pytest.mark.fast
    def test_change_type_updates_timestamp(self):
        """Test that changing type updates timestamp."""
        beat = Beat(scene_id=uuid4())
        original_timestamp = beat.updated_at

        beat.change_type(BeatType.REVELATION)

        assert beat.updated_at >= original_timestamp


class TestBeatNotesOperations:
    """Test suite for Beat notes operations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_notes(self):
        """Test updating the beat notes."""
        beat = Beat(scene_id=uuid4())

        beat.update_notes("Author note: important foreshadowing")

        assert beat.notes == "Author note: important foreshadowing"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_notes_allows_empty(self):
        """Test that empty notes is allowed."""
        beat = Beat(scene_id=uuid4(), notes="Has notes")
        beat.update_notes("")

        assert beat.notes == ""


class TestBeatOrderOperations:
    """Test suite for Beat order/position operations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_move_to_position(self):
        """Test moving beat to a new position."""
        beat = Beat(scene_id=uuid4(), order_index=0)

        beat.move_to_position(5)

        assert beat.order_index == 5

    @pytest.mark.unit
    def test_move_to_negative_position_raises_error(self):
        """Test that moving to negative position raises ValueError."""
        beat = Beat(scene_id=uuid4(), order_index=3)

        with pytest.raises(ValueError, match="order_index cannot be negative"):
            beat.move_to_position(-1)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_move_to_zero_position(self):
        """Test moving beat to position zero."""
        beat = Beat(scene_id=uuid4(), order_index=5)

        beat.move_to_position(0)

        assert beat.order_index == 0


class TestBeatUtilityMethods:
    """Test suite for Beat utility methods."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_is_empty_true(self):
        """Test is_empty returns True for empty content."""
        beat = Beat(scene_id=uuid4(), content="")
        assert beat.is_empty() is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_is_empty_true_for_whitespace(self):
        """Test is_empty returns True for whitespace-only content."""
        beat = Beat(scene_id=uuid4(), content="   \n\t  ")
        assert beat.is_empty() is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_is_empty_false(self):
        """Test is_empty returns False for content with text."""
        beat = Beat(scene_id=uuid4(), content="Some content")
        assert beat.is_empty() is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_word_count_empty(self):
        """Test word count of empty content."""
        beat = Beat(scene_id=uuid4(), content="")
        assert beat.word_count() == 0

    @pytest.mark.unit
    @pytest.mark.fast
    def test_word_count_single_word(self):
        """Test word count of single word."""
        beat = Beat(scene_id=uuid4(), content="Hello")
        assert beat.word_count() == 1

    @pytest.mark.unit
    @pytest.mark.fast
    def test_word_count_multiple_words(self):
        """Test word count of multiple words."""
        beat = Beat(scene_id=uuid4(), content="The quick brown fox jumps.")
        assert beat.word_count() == 5

    @pytest.mark.unit
    @pytest.mark.fast
    def test_word_count_with_extra_whitespace(self):
        """Test word count handles extra whitespace."""
        beat = Beat(scene_id=uuid4(), content="  Word   count   test  ")
        assert beat.word_count() == 3


class TestBeatStringRepresentation:
    """Test suite for Beat string representations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_str_representation_short_content(self):
        """Test string representation of Beat with short content."""
        beat = Beat(scene_id=uuid4(), content="Short content", order_index=0)

        str_repr = str(beat)

        assert "action" in str_repr
        assert "order=0" in str_repr
        assert "Short content" in str_repr

    @pytest.mark.unit
    @pytest.mark.fast
    def test_str_representation_long_content_truncated(self):
        """Test string representation truncates long content."""
        long_content = "A" * 100
        beat = Beat(scene_id=uuid4(), content=long_content, order_index=0)

        str_repr = str(beat)

        assert "..." in str_repr
        assert len(str_repr) < 100

    @pytest.mark.unit
    @pytest.mark.fast
    def test_repr_representation(self):
        """Test repr representation of Beat."""
        scene_id = uuid4()
        beat = Beat(scene_id=scene_id, content="Test content", order_index=3)

        repr_str = repr(beat)

        assert "Beat" in repr_str
        assert str(beat.id) in repr_str
        assert str(scene_id) in repr_str
        assert "action" in repr_str
        assert "order_index=3" in repr_str


class TestBeatTimestamps:
    """Test suite for Beat timestamp behavior."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_operations_touch_timestamp(self):
        """Test that update operations update the timestamp."""
        beat = Beat(scene_id=uuid4())
        original_timestamp = beat.updated_at

        beat.update_content("Content")
        assert beat.updated_at >= original_timestamp

        timestamp_after_content = beat.updated_at
        beat.append_content(" more")
        assert beat.updated_at >= timestamp_after_content

        timestamp_after_append = beat.updated_at
        beat.change_type(BeatType.DIALOGUE)
        assert beat.updated_at >= timestamp_after_append

        timestamp_after_type = beat.updated_at
        beat.update_notes("Notes")
        assert beat.updated_at >= timestamp_after_type

        timestamp_after_notes = beat.updated_at
        beat.move_to_position(5)
        assert beat.updated_at >= timestamp_after_notes


class TestBeatAllTypes:
    """Test suite verifying all beat types can be used."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_action_beat(self):
        """Test creating an action beat."""
        beat = Beat(
            scene_id=uuid4(),
            content="The hero swung his sword.",
            beat_type=BeatType.ACTION,
        )
        assert beat.beat_type == BeatType.ACTION

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_dialogue_beat(self):
        """Test creating a dialogue beat."""
        beat = Beat(
            scene_id=uuid4(),
            content='"I will defeat you!" he shouted.',
            beat_type=BeatType.DIALOGUE,
        )
        assert beat.beat_type == BeatType.DIALOGUE

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_reaction_beat(self):
        """Test creating a reaction beat."""
        beat = Beat(
            scene_id=uuid4(),
            content="Fear gripped her heart.",
            beat_type=BeatType.REACTION,
        )
        assert beat.beat_type == BeatType.REACTION

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_revelation_beat(self):
        """Test creating a revelation beat."""
        beat = Beat(
            scene_id=uuid4(),
            content="He realized the truth: she was his sister.",
            beat_type=BeatType.REVELATION,
        )
        assert beat.beat_type == BeatType.REVELATION

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_transition_beat(self):
        """Test creating a transition beat."""
        beat = Beat(
            scene_id=uuid4(),
            content="Three days later, they arrived at the castle.",
            beat_type=BeatType.TRANSITION,
        )
        assert beat.beat_type == BeatType.TRANSITION

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_description_beat(self):
        """Test creating a description beat."""
        beat = Beat(
            scene_id=uuid4(),
            content="The forest loomed dark and foreboding.",
            beat_type=BeatType.DESCRIPTION,
        )
        assert beat.beat_type == BeatType.DESCRIPTION
