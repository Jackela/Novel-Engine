"""Unit Tests for Beat Entity - Director Mode Features.

This test suite covers the Beat entity enhancements for Director Mode,
focusing on the ACTION/REACTION micro-units and mood_shift pacing features.

These tests complement the comprehensive entity tests in
tests/unit/contexts/narrative/domain/entities/test_beat_entity.py
"""

from uuid import uuid4

import pytest

from src.contexts.narrative.domain.entities.beat import Beat, BeatType


class TestBeatMoodShift:
    """Test suite for Beat mood_shift pacing feature."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_beat_with_default_mood_shift(self):
        """Test that beat defaults to neutral mood_shift (0)."""
        beat = Beat(scene_id=uuid4())
        assert beat.mood_shift == 0

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_beat_with_positive_mood_shift(self):
        """Test creating a beat with positive mood_shift (+5 max)."""
        beat = Beat(scene_id=uuid4(), mood_shift=5)
        assert beat.mood_shift == 5

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_beat_with_negative_mood_shift(self):
        """Test creating a beat with negative mood_shift (-5 min)."""
        beat = Beat(scene_id=uuid4(), mood_shift=-5)
        assert beat.mood_shift == -5

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_beat_with_mood_shift_in_range(self):
        """Test creating beats with various valid mood_shift values."""
        for shift in range(-5, 6):
            beat = Beat(scene_id=uuid4(), mood_shift=shift)
            assert beat.mood_shift == shift

    @pytest.mark.unit
    def test_create_beat_with_mood_shift_too_high_raises_error(self):
        """Test that mood_shift > 5 raises ValueError."""
        with pytest.raises(ValueError, match="mood_shift must be between -5 and \\+5"):
            Beat(scene_id=uuid4(), mood_shift=6)

    @pytest.mark.unit
    def test_create_beat_with_mood_shift_too_low_raises_error(self):
        """Test that mood_shift < -5 raises ValueError."""
        with pytest.raises(ValueError, match="mood_shift must be between -5 and \\+5"):
            Beat(scene_id=uuid4(), mood_shift=-6)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_mood_shift(self):
        """Test updating mood_shift on existing beat."""
        beat = Beat(scene_id=uuid4(), mood_shift=0)
        original_updated_at = beat.updated_at

        beat.update_mood_shift(3)

        assert beat.mood_shift == 3
        assert beat.updated_at >= original_updated_at

    @pytest.mark.unit
    def test_update_mood_shift_invalid_raises_error(self):
        """Test that updating to invalid mood_shift raises ValueError."""
        beat = Beat(scene_id=uuid4(), mood_shift=0)

        with pytest.raises(ValueError, match="mood_shift must be between -5 and \\+5"):
            beat.update_mood_shift(10)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_mood_shift_to_boundary_values(self):
        """Test updating mood_shift to boundary values."""
        beat = Beat(scene_id=uuid4(), mood_shift=0)

        beat.update_mood_shift(-5)
        assert beat.mood_shift == -5

        beat.update_mood_shift(5)
        assert beat.mood_shift == 5


class TestBeatActionReaction:
    """Test suite for ACTION/REACTION beat type micro-units.

    Why this focus:
        Director Mode uses ACTION/REACTION as the primary beat types
        for pacing analysis. These are the core micro-units that
        alternate to create narrative rhythm.
    """

    @pytest.mark.unit
    @pytest.mark.fast
    def test_action_beat_creation(self):
        """Test creating an ACTION beat for Director Mode."""
        beat = Beat(
            scene_id=uuid4(),
            content="The knight charged forward.",
            beat_type=BeatType.ACTION,
            mood_shift=2,
        )
        assert beat.beat_type == BeatType.ACTION
        assert beat.mood_shift == 2

    @pytest.mark.unit
    @pytest.mark.fast
    def test_reaction_beat_creation(self):
        """Test creating a REACTION beat for Director Mode."""
        beat = Beat(
            scene_id=uuid4(),
            content="Fear gripped her heart as she watched.",
            beat_type=BeatType.REACTION,
            mood_shift=-3,
        )
        assert beat.beat_type == BeatType.REACTION
        assert beat.mood_shift == -3

    @pytest.mark.unit
    @pytest.mark.fast
    def test_action_reaction_alternation_pattern(self):
        """Test creating alternating ACTION/REACTION beats.

        Why this test:
            Good narrative pacing often alternates between action
            and reaction. This tests the pattern Director Mode analyzes.
        """
        scene_id = uuid4()
        beats = [
            Beat(
                scene_id=scene_id,
                content="She drew her sword.",
                beat_type=BeatType.ACTION,
                mood_shift=1,
                order_index=0,
            ),
            Beat(
                scene_id=scene_id,
                content="Doubt crept into her mind.",
                beat_type=BeatType.REACTION,
                mood_shift=-2,
                order_index=1,
            ),
            Beat(
                scene_id=scene_id,
                content="She lunged at her opponent.",
                beat_type=BeatType.ACTION,
                mood_shift=3,
                order_index=2,
            ),
            Beat(
                scene_id=scene_id,
                content="Relief washed over her as he fell.",
                beat_type=BeatType.REACTION,
                mood_shift=4,
                order_index=3,
            ),
        ]

        # Verify alternating pattern
        expected_types = [
            BeatType.ACTION,
            BeatType.REACTION,
            BeatType.ACTION,
            BeatType.REACTION,
        ]
        actual_types = [b.beat_type for b in beats]
        assert actual_types == expected_types

        # Verify mood progression (tension -> release pattern)
        mood_shifts = [b.mood_shift for b in beats]
        assert mood_shifts == [1, -2, 3, 4]


class TestBeatDirectorModeIntegration:
    """Test suite for Beat features supporting Director Mode.

    These tests verify that Beat attributes support the pacing
    and rhythm analysis features in Director Mode.
    """

    @pytest.mark.unit
    @pytest.mark.fast
    def test_beat_provides_pacing_data(self):
        """Test that beat exposes all data needed for pacing analysis."""
        beat = Beat(
            scene_id=uuid4(),
            content="The storm broke overhead.",
            beat_type=BeatType.ACTION,
            mood_shift=-2,
            order_index=5,
        )

        # Director Mode needs: type, mood_shift, order for analysis
        assert hasattr(beat, "beat_type")
        assert hasattr(beat, "mood_shift")
        assert hasattr(beat, "order_index")
        assert beat.beat_type == BeatType.ACTION
        assert beat.mood_shift == -2
        assert beat.order_index == 5

    @pytest.mark.unit
    @pytest.mark.fast
    def test_beat_type_is_string_enum(self):
        """Test that BeatType works as string for serialization."""
        beat = Beat(scene_id=uuid4(), beat_type=BeatType.ACTION)

        # String enum allows direct comparison and JSON serialization
        assert beat.beat_type == "action"
        assert beat.beat_type.value == "action"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_beat_supports_all_types_with_mood_shift(self):
        """Test that all beat types work with mood_shift."""
        scene_id = uuid4()
        beats_with_mood = [
            Beat(scene_id=scene_id, beat_type=BeatType.ACTION, mood_shift=3),
            Beat(scene_id=scene_id, beat_type=BeatType.REACTION, mood_shift=-2),
            Beat(scene_id=scene_id, beat_type=BeatType.DIALOGUE, mood_shift=1),
            Beat(scene_id=scene_id, beat_type=BeatType.REVELATION, mood_shift=5),
            Beat(scene_id=scene_id, beat_type=BeatType.TRANSITION, mood_shift=0),
            Beat(scene_id=scene_id, beat_type=BeatType.DESCRIPTION, mood_shift=-1),
        ]

        for beat in beats_with_mood:
            assert -5 <= beat.mood_shift <= 5
