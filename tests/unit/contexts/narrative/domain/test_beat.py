#!/usr/bin/env python3
"""
Unit tests for Beat Entity

Comprehensive test suite for the Beat domain entity including:
- Creation and validation
- Content management
- Beat type changes
- Mood shift management
- Position management
- Utility methods (word count, is_empty)
"""

import sys
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

pytestmark = pytest.mark.unit

# Mock problematic dependencies
sys.modules["aioredis"] = MagicMock()

from src.contexts.narrative.domain.entities.beat import Beat, BeatType


class TestBeat:
    """Test suite for Beat entity."""

    @pytest.fixture
    def sample_scene_id(self):
        """Create a sample scene ID."""
        return uuid4()

    @pytest.fixture
    def sample_beat(self, sample_scene_id):
        """Create a sample beat for testing."""
        return Beat(
            scene_id=sample_scene_id,
            content="This is test content for a beat.",
            order_index=0,
            beat_type=BeatType.ACTION,
            mood_shift=0,
        )

    def test_beat_creation_success(self, sample_scene_id):
        """Test successful beat creation with all fields."""
        beat = Beat(
            scene_id=sample_scene_id,
            content="Test content",
            order_index=1,
            beat_type=BeatType.DIALOGUE,
            mood_shift=2,
            notes="Test notes",
        )

        assert beat.scene_id == sample_scene_id
        assert beat.content == "Test content"
        assert beat.order_index == 1
        assert beat.beat_type == BeatType.DIALOGUE
        assert beat.mood_shift == 2
        assert beat.notes == "Test notes"
        assert isinstance(beat.id, UUID)

    def test_beat_creation_defaults(self, sample_scene_id):
        """Test beat creation with default values."""
        beat = Beat(
            scene_id=sample_scene_id,
        )

        assert beat.content == ""
        assert beat.order_index == 0
        assert beat.beat_type == BeatType.ACTION
        assert beat.mood_shift == 0
        assert beat.notes == ""

    def test_beat_creation_negative_order_raises_error(self, sample_scene_id):
        """Test that negative order_index raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Beat(
                scene_id=sample_scene_id,
                order_index=-1,
            )
        assert "Beat order_index cannot be negative" in str(exc_info.value)

    def test_beat_creation_mood_shift_too_low_raises_error(self, sample_scene_id):
        """Test that mood_shift < -5 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Beat(
                scene_id=sample_scene_id,
                mood_shift=-6,
            )
        assert "Beat mood_shift must be between -5 and +5" in str(exc_info.value)

    def test_beat_creation_mood_shift_too_high_raises_error(self, sample_scene_id):
        """Test that mood_shift > 5 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Beat(
                scene_id=sample_scene_id,
                mood_shift=6,
            )
        assert "Beat mood_shift must be between -5 and +5" in str(exc_info.value)

    def test_update_content_success(self, sample_beat):
        """Test successful content update."""
        old_updated_at = sample_beat.updated_at

        sample_beat.update_content("New content")

        assert sample_beat.content == "New content"
        assert sample_beat.updated_at > old_updated_at

    def test_update_content_allows_empty(self, sample_beat):
        """Test that empty content is allowed."""
        sample_beat.update_content("")
        assert sample_beat.content == ""

    def test_append_content_success(self, sample_beat):
        """Test successful content append."""
        original_content = sample_beat.content
        sample_beat.append_content(" Additional text.")

        assert sample_beat.content == original_content + " Additional text."

    def test_append_content_to_empty(self, sample_scene_id):
        """Test appending to empty content."""
        beat = Beat(scene_id=sample_scene_id, content="")
        beat.append_content("New content")
        assert beat.content == "New content"

    def test_change_type_success(self, sample_beat):
        """Test successful beat type change."""
        old_updated_at = sample_beat.updated_at

        sample_beat.change_type(BeatType.REVELATION)

        assert sample_beat.beat_type == BeatType.REVELATION
        assert sample_beat.updated_at > old_updated_at

    def test_update_notes_success(self, sample_beat):
        """Test successful notes update."""
        sample_beat.update_notes("New notes")
        assert sample_beat.notes == "New notes"

    def test_update_mood_shift_success(self, sample_beat):
        """Test successful mood shift update."""
        sample_beat.update_mood_shift(3)
        assert sample_beat.mood_shift == 3

    def test_update_mood_shift_boundary_values(self, sample_beat):
        """Test mood shift at boundary values."""
        sample_beat.update_mood_shift(-5)
        assert sample_beat.mood_shift == -5

        sample_beat.update_mood_shift(5)
        assert sample_beat.mood_shift == 5

    def test_update_mood_shift_too_low_raises_error(self, sample_beat):
        """Test that mood_shift < -5 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            sample_beat.update_mood_shift(-6)
        assert "Beat mood_shift must be between -5 and +5" in str(exc_info.value)

    def test_update_mood_shift_too_high_raises_error(self, sample_beat):
        """Test that mood_shift > 5 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            sample_beat.update_mood_shift(6)
        assert "Beat mood_shift must be between -5 and +5" in str(exc_info.value)

    def test_move_to_position_success(self, sample_beat):
        """Test successful position change."""
        sample_beat.move_to_position(5)
        assert sample_beat.order_index == 5

    def test_move_to_position_zero(self, sample_beat):
        """Test moving to position 0."""
        sample_beat.move_to_position(0)
        assert sample_beat.order_index == 0

    def test_move_to_position_negative_raises_error(self, sample_beat):
        """Test that negative position raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            sample_beat.move_to_position(-1)
        assert "Beat order_index cannot be negative" in str(exc_info.value)

    def test_is_empty_with_content(self, sample_beat):
        """Test is_empty returns False when content exists."""
        assert sample_beat.is_empty() is False

    def test_is_empty_with_empty_string(self, sample_scene_id):
        """Test is_empty returns True when content is empty."""
        beat = Beat(scene_id=sample_scene_id, content="")
        assert beat.is_empty() is True

    def test_is_empty_with_whitespace_only(self, sample_scene_id):
        """Test is_empty returns True for whitespace-only content."""
        beat = Beat(scene_id=sample_scene_id, content="   ")
        assert beat.is_empty() is True

    def test_word_count_with_content(self, sample_beat):
        """Test word count with content."""
        # "This is test content for a beat." = 7 words
        assert sample_beat.word_count() == 7

    def test_word_count_empty(self, sample_scene_id):
        """Test word count with empty content."""
        beat = Beat(scene_id=sample_scene_id, content="")
        assert beat.word_count() == 0

    def test_word_count_multiple_spaces(self, sample_scene_id):
        """Test word count handles multiple spaces."""
        beat = Beat(scene_id=sample_scene_id, content="Word1   Word2    Word3")
        assert beat.word_count() == 3

    def test_word_count_newlines(self, sample_scene_id):
        """Test word count handles newlines."""
        beat = Beat(scene_id=sample_scene_id, content="Word1\nWord2\nWord3")
        assert beat.word_count() == 3

    def test_str_representation(self, sample_beat):
        """Test string representation."""
        result = str(sample_beat)
        assert "action" in result
        assert "order=0" in result

    def test_str_representation_long_content(self, sample_scene_id):
        """Test string representation truncates long content."""
        long_content = "A" * 100
        beat = Beat(scene_id=sample_scene_id, content=long_content)
        result = str(beat)
        assert "..." in result

    def test_repr_representation(self, sample_beat):
        """Test repr representation."""
        result = repr(sample_beat)
        assert "Beat" in result
        assert "id=" in result
        assert "scene_id=" in result
        assert "content_len=" in result


class TestBeatType:
    """Test BeatType enum."""

    def test_beat_type_values(self):
        """Test that enum has correct values."""
        assert BeatType.ACTION.value == "action"
        assert BeatType.DIALOGUE.value == "dialogue"
        assert BeatType.REACTION.value == "reaction"
        assert BeatType.REVELATION.value == "revelation"
        assert BeatType.TRANSITION.value == "transition"
        assert BeatType.DESCRIPTION.value == "description"

    def test_beat_type_comparison(self):
        """Test beat type comparison."""
        assert BeatType.ACTION == BeatType.ACTION
        assert BeatType.ACTION != BeatType.DIALOGUE
