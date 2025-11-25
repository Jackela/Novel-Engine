#!/usr/bin/env python3
"""
Comprehensive Unit Tests for StoryPacing Value Objects

Test suite covering story pacing creation, validation, business logic,
enums, properties, score calculations, temporal methods, and factory methods
in the Narrative Context domain layer.
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest

from contexts.narratives.domain.value_objects.story_pacing import (
    PacingIntensity,
    PacingType,
    StoryPacing,
)


class TestPacingTypeEnum:
    """Test suite for PacingType enum."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_all_pacing_types_exist(self):
        """Test that all expected pacing types are defined."""
        expected_types = {
            "STEADY",
            "ACCELERATING",
            "DECELERATING",
            "EPISODIC",
            "CRESCENDO",
            "PLATEAU",
            "WAVE",
            "EXPLOSIVE_START",
            "SLOW_BURN",
            "STACCATO",
        }

        actual_types = {item.name for item in PacingType}
        assert actual_types == expected_types

    @pytest.mark.unit
    def test_pacing_type_string_values(self):
        """Test that pacing type enum values have correct string representations."""
        assert PacingType.STEADY.value == "steady"
        assert PacingType.ACCELERATING.value == "accelerating"
        assert PacingType.DECELERATING.value == "decelerating"
        assert PacingType.EPISODIC.value == "episodic"
        assert PacingType.CRESCENDO.value == "crescendo"
        assert PacingType.PLATEAU.value == "plateau"
        assert PacingType.WAVE.value == "wave"
        assert PacingType.EXPLOSIVE_START.value == "explosive_start"
        assert PacingType.SLOW_BURN.value == "slow_burn"
        assert PacingType.STACCATO.value == "staccato"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_pacing_type_uniqueness(self):
        """Test that all pacing type values are unique."""
        values = [item.value for item in PacingType]
        assert len(values) == len(set(values))

    @pytest.mark.unit
    @pytest.mark.fast
    def test_pacing_type_membership(self):
        """Test pacing type membership operations."""
        assert PacingType.STEADY in PacingType
        assert "steady" == PacingType.STEADY.value
        assert PacingType.STEADY == PacingType("steady")


class TestPacingIntensityEnum:
    """Test suite for PacingIntensity enum."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_all_intensity_levels_exist(self):
        """Test that all expected intensity levels are defined."""
        expected_levels = {"GLACIAL", "SLOW", "MODERATE", "BRISK", "FAST", "BREAKNECK"}
        actual_levels = {item.name for item in PacingIntensity}
        assert actual_levels == expected_levels

    @pytest.mark.unit
    @pytest.mark.fast
    def test_intensity_string_values(self):
        """Test that intensity enum values have correct string representations."""
        assert PacingIntensity.GLACIAL.value == "glacial"
        assert PacingIntensity.SLOW.value == "slow"
        assert PacingIntensity.MODERATE.value == "moderate"
        assert PacingIntensity.BRISK.value == "brisk"
        assert PacingIntensity.FAST.value == "fast"
        assert PacingIntensity.BREAKNECK.value == "breakneck"

    @pytest.mark.unit
    def test_intensity_logical_ordering(self):
        """Test that intensity levels represent logical progression."""
        intensity_order = {
            PacingIntensity.GLACIAL: 1,
            PacingIntensity.SLOW: 2,
            PacingIntensity.MODERATE: 3,
            PacingIntensity.BRISK: 4,
            PacingIntensity.FAST: 5,
            PacingIntensity.BREAKNECK: 6,
        }

        assert (
            intensity_order[PacingIntensity.BREAKNECK]
            > intensity_order[PacingIntensity.FAST]
        )
        assert (
            intensity_order[PacingIntensity.FAST]
            > intensity_order[PacingIntensity.BRISK]
        )
        assert (
            intensity_order[PacingIntensity.BRISK]
            > intensity_order[PacingIntensity.MODERATE]
        )
        assert (
            intensity_order[PacingIntensity.MODERATE]
            > intensity_order[PacingIntensity.SLOW]
        )
        assert (
            intensity_order[PacingIntensity.SLOW]
            > intensity_order[PacingIntensity.GLACIAL]
        )

    @pytest.mark.unit
    @pytest.mark.fast
    def test_intensity_uniqueness(self):
        """Test that all intensity values are unique."""
        values = [item.value for item in PacingIntensity]
        assert len(values) == len(set(values))

    @pytest.mark.unit
    @pytest.mark.fast
    def test_intensity_membership(self):
        """Test intensity membership operations."""
        assert PacingIntensity.MODERATE in PacingIntensity
        assert "moderate" == PacingIntensity.MODERATE.value
        assert PacingIntensity.MODERATE == PacingIntensity("moderate")


class TestStoryPacingCreation:
    """Test suite for StoryPacing creation and initialization."""

    @pytest.mark.unit
    def test_create_minimal_story_pacing(self):
        """Test creating story pacing with minimal required fields."""
        pacing = StoryPacing(
            pacing_id="minimal-pacing-1",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=1,
            end_sequence=10,
        )

        assert pacing.pacing_id == "minimal-pacing-1"
        assert pacing.pacing_type == PacingType.STEADY
        assert pacing.base_intensity == PacingIntensity.MODERATE
        assert pacing.start_sequence == 1
        assert pacing.end_sequence == 10

        # Test default values
        assert pacing.segment_name == ""
        assert pacing.segment_description == ""
        assert pacing.event_density == Decimal("5.0")
        assert pacing.dialogue_ratio == Decimal("0.3")
        assert pacing.action_ratio == Decimal("0.4")
        assert pacing.reflection_ratio == Decimal("0.3")
        assert pacing.scene_transitions == 0
        assert pacing.time_jumps == 0
        assert pacing.average_scene_length is None
        assert pacing.tension_curve == ()
        assert pacing.emotional_peaks == ()
        assert pacing.rest_periods == ()
        assert pacing.revelation_frequency == Decimal("0.1")
        assert pacing.cliffhanger_intensity == Decimal("0.0")
        assert pacing.curiosity_hooks == 0
        assert pacing.sentence_complexity == Decimal("5.0")
        assert pacing.paragraph_length == Decimal("5.0")
        assert pacing.vocabulary_density == Decimal("5.0")
        assert pacing.target_reading_time is None
        assert pacing.emotional_target == ""
        assert pacing.pacing_notes == ""
        assert isinstance(pacing.creation_timestamp, datetime)
        assert pacing.metadata == {}

    @pytest.mark.unit
    def test_create_full_story_pacing(self):
        """Test creating story pacing with all fields specified."""
        tension_curve = (Decimal("2.0"), Decimal("5.0"), Decimal("8.0"), Decimal("3.0"))
        emotional_peaks = (3, 7)
        rest_periods = (1, 9)
        metadata = {"author": "test", "version": "1.0"}
        timestamp = datetime.now(timezone.utc)

        pacing = StoryPacing(
            pacing_id="full-pacing-1",
            pacing_type=PacingType.CRESCENDO,
            base_intensity=PacingIntensity.BRISK,
            start_sequence=1,
            end_sequence=10,
            segment_name="Climactic Battle",
            segment_description="The final confrontation builds to crescendo",
            event_density=Decimal("8.0"),
            dialogue_ratio=Decimal("0.2"),
            action_ratio=Decimal("0.6"),
            reflection_ratio=Decimal("0.2"),
            scene_transitions=3,
            time_jumps=1,
            average_scene_length=15,
            tension_curve=tension_curve,
            emotional_peaks=emotional_peaks,
            rest_periods=rest_periods,
            revelation_frequency=Decimal("0.3"),
            cliffhanger_intensity=Decimal("8.5"),
            curiosity_hooks=5,
            sentence_complexity=Decimal("7.0"),
            paragraph_length=Decimal("6.0"),
            vocabulary_density=Decimal("8.0"),
            target_reading_time=45,
            emotional_target="Excitement and tension",
            pacing_notes="High-intensity action sequence",
            creation_timestamp=timestamp,
            metadata=metadata,
        )

        assert pacing.pacing_id == "full-pacing-1"
        assert pacing.pacing_type == PacingType.CRESCENDO
        assert pacing.base_intensity == PacingIntensity.BRISK
        assert pacing.start_sequence == 1
        assert pacing.end_sequence == 10
        assert pacing.segment_name == "Climactic Battle"
        assert (
            pacing.segment_description == "The final confrontation builds to crescendo"
        )
        assert pacing.event_density == Decimal("8.0")
        assert pacing.dialogue_ratio == Decimal("0.2")
        assert pacing.action_ratio == Decimal("0.6")
        assert pacing.reflection_ratio == Decimal("0.2")
        assert pacing.scene_transitions == 3
        assert pacing.time_jumps == 1
        assert pacing.average_scene_length == 15
        assert pacing.tension_curve == tension_curve
        assert pacing.emotional_peaks == emotional_peaks
        assert pacing.rest_periods == rest_periods
        assert pacing.revelation_frequency == Decimal("0.3")
        assert pacing.cliffhanger_intensity == Decimal("8.5")
        assert pacing.curiosity_hooks == 5
        assert pacing.sentence_complexity == Decimal("7.0")
        assert pacing.paragraph_length == Decimal("6.0")
        assert pacing.vocabulary_density == Decimal("8.0")
        assert pacing.target_reading_time == 45
        assert pacing.emotional_target == "Excitement and tension"
        assert pacing.pacing_notes == "High-intensity action sequence"
        assert pacing.creation_timestamp == timestamp
        assert pacing.metadata == metadata

    @patch("contexts.narratives.domain.value_objects.story_pacing.datetime")
    @pytest.mark.unit
    def test_automatic_timestamp_generation(self, mock_datetime):
        """Test that creation_timestamp is auto-generated when not provided."""
        expected_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = expected_time

        pacing = StoryPacing(
            pacing_id="timestamp-test",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=1,
            end_sequence=5,
        )

        assert pacing.creation_timestamp == expected_time
        mock_datetime.now.assert_called_once_with(timezone.utc)

    @pytest.mark.unit
    def test_frozen_dataclass_immutability(self):
        """Test that StoryPacing instances are immutable."""
        pacing = StoryPacing(
            pacing_id="immutable-test",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=1,
            end_sequence=5,
        )

        with pytest.raises(AttributeError):
            pacing.pacing_id = "new-id"

        with pytest.raises(AttributeError):
            pacing.event_density = Decimal("7.0")


class TestStoryPacingValidation:
    """Test suite for StoryPacing validation and constraints."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_empty_pacing_id_raises_error(self):
        """Test that empty pacing ID raises validation error."""
        with pytest.raises(ValueError, match="Pacing ID cannot be empty"):
            StoryPacing(
                pacing_id="",
                pacing_type=PacingType.STEADY,
                base_intensity=PacingIntensity.MODERATE,
                start_sequence=1,
                end_sequence=5,
            )

        with pytest.raises(ValueError, match="Pacing ID cannot be empty"):
            StoryPacing(
                pacing_id="   ",
                pacing_type=PacingType.STEADY,
                base_intensity=PacingIntensity.MODERATE,
                start_sequence=1,
                end_sequence=5,
            )

    @pytest.mark.unit
    def test_invalid_sequence_numbers_raise_errors(self):
        """Test that invalid sequence numbers raise validation errors."""
        # Negative start sequence
        with pytest.raises(ValueError, match="Sequence numbers must be non-negative"):
            StoryPacing(
                pacing_id="test",
                pacing_type=PacingType.STEADY,
                base_intensity=PacingIntensity.MODERATE,
                start_sequence=-1,
                end_sequence=5,
            )

        # Negative end sequence
        with pytest.raises(ValueError, match="Sequence numbers must be non-negative"):
            StoryPacing(
                pacing_id="test",
                pacing_type=PacingType.STEADY,
                base_intensity=PacingIntensity.MODERATE,
                start_sequence=1,
                end_sequence=-1,
            )

        # Start sequence after end sequence
        with pytest.raises(
            ValueError, match="Start sequence must be before end sequence"
        ):
            StoryPacing(
                pacing_id="test",
                pacing_type=PacingType.STEADY,
                base_intensity=PacingIntensity.MODERATE,
                start_sequence=10,
                end_sequence=5,
            )

        # Start sequence equal to end sequence
        with pytest.raises(
            ValueError, match="Start sequence must be before end sequence"
        ):
            StoryPacing(
                pacing_id="test",
                pacing_type=PacingType.STEADY,
                base_intensity=PacingIntensity.MODERATE,
                start_sequence=5,
                end_sequence=5,
            )

    @pytest.mark.unit
    def test_invalid_ratios_raise_errors(self):
        """Test that invalid ratio values raise validation errors."""
        # Dialogue ratio out of range
        with pytest.raises(ValueError, match="dialogue_ratio must be between 0 and 1"):
            StoryPacing(
                pacing_id="test",
                pacing_type=PacingType.STEADY,
                base_intensity=PacingIntensity.MODERATE,
                start_sequence=1,
                end_sequence=5,
                dialogue_ratio=Decimal("1.5"),
            )

        # Action ratio negative
        with pytest.raises(ValueError, match="action_ratio must be between 0 and 1"):
            StoryPacing(
                pacing_id="test",
                pacing_type=PacingType.STEADY,
                base_intensity=PacingIntensity.MODERATE,
                start_sequence=1,
                end_sequence=5,
                action_ratio=Decimal("-0.1"),
            )

        # Ratios don't sum to ~1.0
        with pytest.raises(ValueError, match="should sum to approximately 1.0"):
            StoryPacing(
                pacing_id="test",
                pacing_type=PacingType.STEADY,
                base_intensity=PacingIntensity.MODERATE,
                start_sequence=1,
                end_sequence=5,
                dialogue_ratio=Decimal("0.1"),
                action_ratio=Decimal("0.1"),
                reflection_ratio=Decimal("0.1"),
            )

    @pytest.mark.unit
    def test_valid_ratio_sum_tolerance(self):
        """Test that slight deviations in ratio sum are tolerated."""
        # Should pass with ratios summing to 0.95
        pacing = StoryPacing(
            pacing_id="test",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=1,
            end_sequence=5,
            dialogue_ratio=Decimal("0.3"),
            action_ratio=Decimal("0.3"),
            reflection_ratio=Decimal("0.35"),  # Sum = 0.95
        )
        assert pacing.dialogue_ratio == Decimal("0.3")

        # Should pass with ratios summing to 1.05
        pacing2 = StoryPacing(
            pacing_id="test2",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=1,
            end_sequence=5,
            dialogue_ratio=Decimal("0.35"),
            action_ratio=Decimal("0.35"),
            reflection_ratio=Decimal("0.35"),  # Sum = 1.05
        )
        assert pacing2.dialogue_ratio == Decimal("0.35")

    @pytest.mark.unit
    def test_invalid_scale_values_raise_errors(self):
        """Test that invalid scale values (1-10) raise validation errors."""
        # Event density too low
        with pytest.raises(ValueError, match="event_density must be between 1 and 10"):
            StoryPacing(
                pacing_id="test",
                pacing_type=PacingType.STEADY,
                base_intensity=PacingIntensity.MODERATE,
                start_sequence=1,
                end_sequence=5,
                event_density=Decimal("0.5"),
            )

        # Sentence complexity too high
        with pytest.raises(
            ValueError, match="sentence_complexity must be between 1 and 10"
        ):
            StoryPacing(
                pacing_id="test",
                pacing_type=PacingType.STEADY,
                base_intensity=PacingIntensity.MODERATE,
                start_sequence=1,
                end_sequence=5,
                sentence_complexity=Decimal("15.0"),
            )

    @pytest.mark.unit
    def test_invalid_frequency_and_intensity_values_raise_errors(self):
        """Test that invalid frequency and intensity values raise validation errors."""
        # Revelation frequency out of range
        with pytest.raises(
            ValueError, match="Revelation frequency must be between 0 and 1"
        ):
            StoryPacing(
                pacing_id="test",
                pacing_type=PacingType.STEADY,
                base_intensity=PacingIntensity.MODERATE,
                start_sequence=1,
                end_sequence=5,
                revelation_frequency=Decimal("2.0"),
            )

        # Cliffhanger intensity too high
        with pytest.raises(
            ValueError, match="Cliffhanger intensity must be between 0 and 10"
        ):
            StoryPacing(
                pacing_id="test",
                pacing_type=PacingType.STEADY,
                base_intensity=PacingIntensity.MODERATE,
                start_sequence=1,
                end_sequence=5,
                cliffhanger_intensity=Decimal("15.0"),
            )

    @pytest.mark.unit
    def test_negative_count_values_raise_errors(self):
        """Test that negative count values raise validation errors."""
        with pytest.raises(ValueError, match="must be non-negative"):
            StoryPacing(
                pacing_id="test",
                pacing_type=PacingType.STEADY,
                base_intensity=PacingIntensity.MODERATE,
                start_sequence=1,
                end_sequence=5,
                scene_transitions=-1,
            )

        with pytest.raises(ValueError, match="must be non-negative"):
            StoryPacing(
                pacing_id="test",
                pacing_type=PacingType.STEADY,
                base_intensity=PacingIntensity.MODERATE,
                start_sequence=1,
                end_sequence=5,
                curiosity_hooks=-5,
            )

    @pytest.mark.unit
    def test_invalid_tension_curve_values_raise_errors(self):
        """Test that invalid tension curve values raise validation errors."""
        with pytest.raises(
            ValueError, match="Tension curve values must be between 0 and 10"
        ):
            StoryPacing(
                pacing_id="test",
                pacing_type=PacingType.STEADY,
                base_intensity=PacingIntensity.MODERATE,
                start_sequence=1,
                end_sequence=5,
                tension_curve=[Decimal("5.0"), Decimal("12.0"), Decimal("3.0")],
            )

    @pytest.mark.unit
    def test_invalid_peak_positions_raise_errors(self):
        """Test that invalid peak positions raise validation errors."""
        with pytest.raises(ValueError, match="outside segment range"):
            StoryPacing(
                pacing_id="test",
                pacing_type=PacingType.STEADY,
                base_intensity=PacingIntensity.MODERATE,
                start_sequence=5,
                end_sequence=10,
                emotional_peaks=[3, 7, 12],  # 3 and 12 are outside range
            )

    @pytest.mark.unit
    def test_invalid_rest_positions_raise_errors(self):
        """Test that invalid rest positions raise validation errors."""
        with pytest.raises(ValueError, match="outside segment range"):
            StoryPacing(
                pacing_id="test",
                pacing_type=PacingType.STEADY,
                base_intensity=PacingIntensity.MODERATE,
                start_sequence=5,
                end_sequence=10,
                rest_periods=[4, 8, 11],  # 4 and 11 are outside range
            )

    @pytest.mark.unit
    def test_string_length_constraints(self):
        """Test string length validation constraints."""
        long_id = "a" * 101
        with pytest.raises(ValueError, match="Pacing ID too long"):
            StoryPacing(
                pacing_id=long_id,
                pacing_type=PacingType.STEADY,
                base_intensity=PacingIntensity.MODERATE,
                start_sequence=1,
                end_sequence=5,
            )

        long_name = "b" * 201
        with pytest.raises(ValueError, match="Segment name too long"):
            StoryPacing(
                pacing_id="test",
                pacing_type=PacingType.STEADY,
                base_intensity=PacingIntensity.MODERATE,
                start_sequence=1,
                end_sequence=5,
                segment_name=long_name,
            )


class TestStoryPacingProperties:
    """Test suite for StoryPacing computed properties."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_segment_length_property(self):
        """Test segment_length property calculation."""
        pacing = StoryPacing(
            pacing_id="test",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=5,
            end_sequence=15,
        )

        assert pacing.segment_length == 11

        # Single sequence segment
        single_pacing = StoryPacing(
            pacing_id="single",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=10,
            end_sequence=11,
        )

        assert single_pacing.segment_length == 2

    @pytest.mark.unit
    def test_boolean_properties(self):
        """Test boolean properties."""
        # Test with empty lists
        empty_pacing = StoryPacing(
            pacing_id="empty",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=1,
            end_sequence=5,
        )

        assert empty_pacing.has_peaks is False
        assert empty_pacing.has_rest_periods is False
        assert empty_pacing.has_tension_curve is False

        # Test with populated lists
        full_pacing = StoryPacing(
            pacing_id="full",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=1,
            end_sequence=5,
            emotional_peaks=[2, 4],
            rest_periods=[1, 5],
            tension_curve=[Decimal("3.0"), Decimal("7.0")],
        )

        assert full_pacing.has_peaks is True
        assert full_pacing.has_rest_periods is True
        assert full_pacing.has_tension_curve is True

    @pytest.mark.unit
    def test_intensity_classification_properties(self):
        """Test intensity classification properties."""
        # High intensity
        high_fast = StoryPacing(
            pacing_id="high-fast",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.FAST,
            start_sequence=1,
            end_sequence=5,
        )
        assert high_fast.is_high_intensity is True
        assert high_fast.is_low_intensity is False

        high_breakneck = StoryPacing(
            pacing_id="high-breakneck",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.BREAKNECK,
            start_sequence=1,
            end_sequence=5,
        )
        assert high_breakneck.is_high_intensity is True
        assert high_breakneck.is_low_intensity is False

        # Low intensity
        low_glacial = StoryPacing(
            pacing_id="low-glacial",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.GLACIAL,
            start_sequence=1,
            end_sequence=5,
        )
        assert low_glacial.is_high_intensity is False
        assert low_glacial.is_low_intensity is True

        low_slow = StoryPacing(
            pacing_id="low-slow",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.SLOW,
            start_sequence=1,
            end_sequence=5,
        )
        assert low_slow.is_high_intensity is False
        assert low_slow.is_low_intensity is True

        # Medium intensity
        medium = StoryPacing(
            pacing_id="medium",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=1,
            end_sequence=5,
        )
        assert medium.is_high_intensity is False
        assert medium.is_low_intensity is False

    @pytest.mark.unit
    def test_tension_properties_with_empty_curve(self):
        """Test tension properties with empty tension curve."""
        pacing = StoryPacing(
            pacing_id="no-tension",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=1,
            end_sequence=5,
        )

        assert pacing.average_tension == Decimal("5.0")
        assert pacing.peak_tension == Decimal("5.0")
        assert pacing.tension_variance == Decimal("0")

    @pytest.mark.unit
    def test_tension_properties_with_curve(self):
        """Test tension properties with defined tension curve."""
        tension_values = [
            Decimal("2.0"),
            Decimal("5.0"),
            Decimal("8.0"),
            Decimal("4.0"),
        ]
        pacing = StoryPacing(
            pacing_id="with-tension",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=1,
            end_sequence=5,
            tension_curve=tension_values,
        )

        expected_average = sum(tension_values) / Decimal("4")
        assert pacing.average_tension == expected_average
        assert pacing.peak_tension == Decimal("8.0")

        # Test variance calculation
        avg = expected_average
        expected_variance = sum((t - avg) ** 2 for t in tension_values) / Decimal("4")
        assert pacing.tension_variance == expected_variance

    @pytest.mark.unit
    def test_tension_properties_single_value(self):
        """Test tension properties with single tension value."""
        pacing = StoryPacing(
            pacing_id="single-tension",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=1,
            end_sequence=5,
            tension_curve=[Decimal("7.0")],
        )

        assert pacing.average_tension == Decimal("7.0")
        assert pacing.peak_tension == Decimal("7.0")
        assert pacing.tension_variance == Decimal("0")

    @pytest.mark.unit
    def test_pacing_complexity_score(self):
        """Test pacing complexity score calculation."""
        # Simple pacing
        simple = StoryPacing(
            pacing_id="simple",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=1,
            end_sequence=5,
        )

        simple_score = simple.pacing_complexity_score
        assert simple_score >= Decimal("0")

        # Complex pacing
        complex_pacing = StoryPacing(
            pacing_id="complex",
            pacing_type=PacingType.WAVE,
            base_intensity=PacingIntensity.FAST,
            start_sequence=1,
            end_sequence=20,
            scene_transitions=8,
            time_jumps=3,
            emotional_peaks=[5, 10, 15],
            rest_periods=[2, 12],
            tension_curve=[
                Decimal("1.0"),
                Decimal("8.0"),
                Decimal("3.0"),
                Decimal("9.0"),
            ],
            sentence_complexity=Decimal("9.0"),
            paragraph_length=Decimal("2.0"),
            vocabulary_density=Decimal("8.0"),
        )

        complex_score = complex_pacing.pacing_complexity_score
        assert complex_score > simple_score
        assert complex_score <= Decimal("10")  # Capped at 10

    @pytest.mark.unit
    def test_engagement_score(self):
        """Test engagement score calculation."""
        # Low engagement pacing
        low_engagement = StoryPacing(
            pacing_id="low",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.GLACIAL,
            start_sequence=1,
            end_sequence=5,
            revelation_frequency=Decimal("0.0"),
            cliffhanger_intensity=Decimal("0.0"),
            curiosity_hooks=0,
            action_ratio=Decimal("0.1"),
            dialogue_ratio=Decimal("0.1"),
            reflection_ratio=Decimal("0.8"),
        )

        low_score = low_engagement.engagement_score

        # High engagement pacing
        high_engagement = StoryPacing(
            pacing_id="high",
            pacing_type=PacingType.CRESCENDO,
            base_intensity=PacingIntensity.FAST,
            start_sequence=1,
            end_sequence=5,
            revelation_frequency=Decimal("0.5"),
            cliffhanger_intensity=Decimal("8.0"),
            curiosity_hooks=10,
            action_ratio=Decimal("0.4"),
            dialogue_ratio=Decimal("0.3"),
            reflection_ratio=Decimal("0.3"),
        )

        high_score = high_engagement.engagement_score
        assert high_score > low_score
        assert high_score <= Decimal("10")  # Capped at 10


class TestStoryPacingMethods:
    """Test suite for StoryPacing methods."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_contains_sequence(self):
        """Test contains_sequence method."""
        pacing = StoryPacing(
            pacing_id="test",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=5,
            end_sequence=15,
        )

        # Within range
        assert pacing.contains_sequence(5) is True
        assert pacing.contains_sequence(10) is True
        assert pacing.contains_sequence(15) is True

        # Outside range
        assert pacing.contains_sequence(4) is False
        assert pacing.contains_sequence(16) is False
        assert pacing.contains_sequence(0) is False
        assert pacing.contains_sequence(100) is False

    @pytest.mark.unit
    def test_get_tension_at_sequence_no_curve(self):
        """Test get_tension_at_sequence with no tension curve."""
        pacing = StoryPacing(
            pacing_id="test",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=5,
            end_sequence=15,
        )

        # Should return None for any sequence
        assert pacing.get_tension_at_sequence(10) is None
        assert pacing.get_tension_at_sequence(5) is None
        assert pacing.get_tension_at_sequence(15) is None

    @pytest.mark.unit
    def test_get_tension_at_sequence_outside_range(self):
        """Test get_tension_at_sequence outside segment range."""
        pacing = StoryPacing(
            pacing_id="test",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=5,
            end_sequence=15,
            tension_curve=[Decimal("3.0"), Decimal("7.0")],
        )

        assert pacing.get_tension_at_sequence(4) is None
        assert pacing.get_tension_at_sequence(16) is None

    @pytest.mark.unit
    def test_get_tension_at_sequence_single_value(self):
        """Test get_tension_at_sequence with single tension value."""
        pacing = StoryPacing(
            pacing_id="test",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=5,
            end_sequence=15,
            tension_curve=[Decimal("6.0")],
        )

        # Should return the single value for all sequences in range
        assert pacing.get_tension_at_sequence(5) == Decimal("6.0")
        assert pacing.get_tension_at_sequence(10) == Decimal("6.0")
        assert pacing.get_tension_at_sequence(15) == Decimal("6.0")

    @pytest.mark.unit
    def test_get_tension_at_sequence_interpolation(self):
        """Test get_tension_at_sequence with interpolation."""
        tension_curve = [Decimal("2.0"), Decimal("8.0"), Decimal("4.0")]
        pacing = StoryPacing(
            pacing_id="test",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=10,
            end_sequence=20,  # 11 sequences total
            tension_curve=tension_curve,
        )

        # First value
        assert pacing.get_tension_at_sequence(10) == Decimal("2.0")

        # Last value
        assert pacing.get_tension_at_sequence(20) == Decimal("4.0")

        # Interpolated values - sequence 13 should interpolate between curve[0] and curve[1]
        # relative_pos=3, curve_pos=(3/10)*2=0.6, index=0, weight=0.6
        # result = 2.0*(1-0.6) + 8.0*0.6 = 0.8 + 4.8 = 5.6
        tension_13 = pacing.get_tension_at_sequence(13)
        assert tension_13 is not None
        assert Decimal("2.0") < tension_13 < Decimal("8.0")

        # Sequence 17 should interpolate between curve[1] and curve[2]
        # relative_pos=7, curve_pos=(7/10)*2=1.4, index=1, weight=0.4
        # result = 8.0*(1-0.4) + 4.0*0.4 = 4.8 + 1.6 = 6.4
        tension_17 = pacing.get_tension_at_sequence(17)
        assert tension_17 is not None
        assert Decimal("4.0") < tension_17 < Decimal("8.0")

    @pytest.mark.unit
    def test_is_emotional_peak(self):
        """Test is_emotional_peak method."""
        pacing = StoryPacing(
            pacing_id="test",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=1,
            end_sequence=10,
            emotional_peaks=[3, 7, 9],
        )

        assert pacing.is_emotional_peak(3) is True
        assert pacing.is_emotional_peak(7) is True
        assert pacing.is_emotional_peak(9) is True

        assert pacing.is_emotional_peak(1) is False
        assert pacing.is_emotional_peak(5) is False
        assert pacing.is_emotional_peak(10) is False

    @pytest.mark.unit
    def test_is_rest_period(self):
        """Test is_rest_period method."""
        pacing = StoryPacing(
            pacing_id="test",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=1,
            end_sequence=10,
            rest_periods=[2, 5, 8],
        )

        assert pacing.is_rest_period(2) is True
        assert pacing.is_rest_period(5) is True
        assert pacing.is_rest_period(8) is True

        assert pacing.is_rest_period(1) is False
        assert pacing.is_rest_period(3) is False
        assert pacing.is_rest_period(10) is False

    @pytest.mark.unit
    def test_get_pacing_context(self):
        """Test get_pacing_context method."""
        tension_curve = [Decimal("3.0"), Decimal("7.0"), Decimal("5.0")]
        pacing = StoryPacing(
            pacing_id="context-test",
            pacing_type=PacingType.CRESCENDO,
            base_intensity=PacingIntensity.BRISK,
            start_sequence=5,
            end_sequence=15,
            scene_transitions=2,
            time_jumps=1,
            emotional_peaks=[7, 12],
            rest_periods=[10],
            curiosity_hooks=3,
            tension_curve=tension_curve,
            dialogue_ratio=Decimal("0.2"),
            action_ratio=Decimal("0.5"),
            reflection_ratio=Decimal("0.3"),
        )

        context = pacing.get_pacing_context()

        assert context["pacing_id"] == "context-test"
        assert context["pacing_type"] == "crescendo"
        assert context["base_intensity"] == "brisk"
        assert context["segment_length"] == 11
        assert context["segment_range"] == [5, 15]
        assert context["is_high_intensity"] is False
        assert context["is_low_intensity"] is False
        assert isinstance(context["complexity_score"], float)
        assert isinstance(context["engagement_score"], float)
        assert isinstance(context["average_tension"], float)
        assert isinstance(context["peak_tension"], float)
        assert isinstance(context["tension_variance"], float)

        assert context["content_distribution"]["dialogue"] == 0.2
        assert context["content_distribution"]["action"] == 0.5
        assert context["content_distribution"]["reflection"] == 0.3

        assert context["structural_elements"]["scene_transitions"] == 2
        assert context["structural_elements"]["time_jumps"] == 1
        assert context["structural_elements"]["emotional_peaks"] == 2
        assert context["structural_elements"]["rest_periods"] == 1
        assert context["structural_elements"]["curiosity_hooks"] == 3


class TestStoryPacingStringRepresentation:
    """Test suite for StoryPacing string representations."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_str_representation_with_segment_name(self):
        """Test __str__ method with segment name."""
        pacing = StoryPacing(
            pacing_id="test-pacing",
            pacing_type=PacingType.CRESCENDO,
            base_intensity=PacingIntensity.FAST,
            start_sequence=1,
            end_sequence=10,
            segment_name="Climax Battle",
        )

        expected = "StoryPacing('Climax Battle', crescendo, fast)"
        assert str(pacing) == expected

    @pytest.mark.unit
    @pytest.mark.fast
    def test_str_representation_without_segment_name(self):
        """Test __str__ method without segment name."""
        pacing = StoryPacing(
            pacing_id="test-pacing",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=1,
            end_sequence=10,
        )

        expected = "StoryPacing('test-pacing', steady, moderate)"
        assert str(pacing) == expected

    @pytest.mark.unit
    def test_repr_representation(self):
        """Test __repr__ method."""
        pacing = StoryPacing(
            pacing_id="test-pacing",
            pacing_type=PacingType.WAVE,
            base_intensity=PacingIntensity.BRISK,
            start_sequence=5,
            end_sequence=15,
        )

        expected = (
            "StoryPacing(id='test-pacing', type=wave, intensity=brisk, range=[5, 15])"
        )
        assert repr(pacing) == expected


class TestStoryPacingEquality:
    """Test suite for StoryPacing equality and hashing."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_equality_same_values(self):
        """Test equality with same values."""
        pacing1 = StoryPacing(
            pacing_id="test",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=1,
            end_sequence=5,
            segment_name="Test Segment",
        )

        pacing2 = StoryPacing(
            pacing_id="test",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=1,
            end_sequence=5,
            segment_name="Test Segment",
        )

        assert pacing1 == pacing2
        assert hash(pacing1) == hash(pacing2)

    @pytest.mark.unit
    def test_inequality_different_values(self):
        """Test inequality with different values."""
        pacing1 = StoryPacing(
            pacing_id="test1",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=1,
            end_sequence=5,
        )

        pacing2 = StoryPacing(
            pacing_id="test2",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=1,
            end_sequence=5,
        )

        assert pacing1 != pacing2
        assert hash(pacing1) != hash(pacing2)

    @pytest.mark.unit
    def test_equality_in_collections(self):
        """Test that equality works correctly in collections."""
        pacing1 = StoryPacing(
            pacing_id="test",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=1,
            end_sequence=5,
        )

        pacing2 = StoryPacing(
            pacing_id="test",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=1,
            end_sequence=5,
        )

        pacing_set = {pacing1}
        assert pacing2 in pacing_set

        pacing_list = [pacing1]
        assert pacing2 in pacing_list


class TestStoryPacingEdgeCases:
    """Test suite for StoryPacing edge cases and boundary conditions."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_minimum_valid_segment(self):
        """Test minimum valid segment with two sequences."""
        pacing = StoryPacing(
            pacing_id="min",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=0,
            end_sequence=1,
        )

        assert pacing.segment_length == 2
        assert pacing.contains_sequence(0) is True
        assert pacing.contains_sequence(1) is True
        assert pacing.contains_sequence(2) is False

    @pytest.mark.unit
    def test_large_segment(self):
        """Test large segment with many sequences."""
        pacing = StoryPacing(
            pacing_id="large",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=1,
            end_sequence=1000,
        )

        assert pacing.segment_length == 1000
        assert pacing.contains_sequence(1) is True
        assert pacing.contains_sequence(500) is True
        assert pacing.contains_sequence(1000) is True
        assert pacing.contains_sequence(1001) is False

    @pytest.mark.unit
    def test_extreme_ratio_values(self):
        """Test extreme but valid ratio values."""
        # All dialogue
        dialogue_heavy = StoryPacing(
            pacing_id="dialogue",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=1,
            end_sequence=5,
            dialogue_ratio=Decimal("1.0"),
            action_ratio=Decimal("0.0"),
            reflection_ratio=Decimal("0.0"),
        )
        assert dialogue_heavy.dialogue_ratio == Decimal("1.0")

        # All action
        action_heavy = StoryPacing(
            pacing_id="action",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=1,
            end_sequence=5,
            dialogue_ratio=Decimal("0.0"),
            action_ratio=Decimal("1.0"),
            reflection_ratio=Decimal("0.0"),
        )
        assert action_heavy.action_ratio == Decimal("1.0")

    @pytest.mark.unit
    def test_extreme_scale_values(self):
        """Test extreme but valid scale values."""
        extreme_pacing = StoryPacing(
            pacing_id="extreme",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=1,
            end_sequence=5,
            event_density=Decimal("10.0"),
            sentence_complexity=Decimal("1.0"),
            paragraph_length=Decimal("10.0"),
            vocabulary_density=Decimal("1.0"),
        )

        assert extreme_pacing.event_density == Decimal("10.0")
        assert extreme_pacing.sentence_complexity == Decimal("1.0")

    @pytest.mark.unit
    def test_complex_tension_curve_interpolation(self):
        """Test complex tension curve with many points."""
        complex_curve = [
            Decimal("1.0"),
            Decimal("3.0"),
            Decimal("7.0"),
            Decimal("9.0"),
            Decimal("5.0"),
            Decimal("2.0"),
            Decimal("8.0"),
            Decimal("4.0"),
        ]

        pacing = StoryPacing(
            pacing_id="complex",
            pacing_type=PacingType.WAVE,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=10,
            end_sequence=30,  # 21 sequences
            tension_curve=complex_curve,
        )

        # Test interpolation at various points
        tension_start = pacing.get_tension_at_sequence(10)
        tension_end = pacing.get_tension_at_sequence(30)
        tension_middle = pacing.get_tension_at_sequence(20)

        assert tension_start == Decimal("1.0")
        assert tension_end == Decimal("4.0")
        assert tension_middle is not None
        assert Decimal("1.0") <= tension_middle <= Decimal("9.0")
