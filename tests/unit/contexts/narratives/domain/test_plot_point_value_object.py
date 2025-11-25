#!/usr/bin/env python3
"""
Comprehensive Unit Tests for PlotPoint Value Objects

Test suite covering plot point creation, validation, business logic,
enums, properties, and factory methods in the Narrative Context domain layer.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from contexts.narratives.domain.value_objects.plot_point import (
    PlotPoint,
    PlotPointImportance,
    PlotPointType,
)


class TestPlotPointTypeEnum:
    """Test suite for PlotPointType enum."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_all_enum_values_exist(self):
        """Test that all expected enum values are defined."""
        expected_types = {
            "INCITING_INCIDENT",
            "RISING_ACTION",
            "CLIMAX",
            "FALLING_ACTION",
            "RESOLUTION",
            "TURNING_POINT",
            "REVELATION",
            "CRISIS",
            "SETBACK",
            "TRIUMPH",
            "COMPLICATION",
            "DISCOVERY",
            "CONFRONTATION",
            "RECONCILIATION",
            "SACRIFICE",
            "TRANSFORMATION",
        }

        actual_types = {item.name for item in PlotPointType}
        assert actual_types == expected_types

    @pytest.mark.unit
    def test_enum_string_values(self):
        """Test that enum values have correct string representations."""
        assert PlotPointType.INCITING_INCIDENT.value == "inciting_incident"
        assert PlotPointType.RISING_ACTION.value == "rising_action"
        assert PlotPointType.CLIMAX.value == "climax"
        assert PlotPointType.FALLING_ACTION.value == "falling_action"
        assert PlotPointType.RESOLUTION.value == "resolution"
        assert PlotPointType.TURNING_POINT.value == "turning_point"
        assert PlotPointType.REVELATION.value == "revelation"
        assert PlotPointType.CRISIS.value == "crisis"
        assert PlotPointType.SETBACK.value == "setback"
        assert PlotPointType.TRIUMPH.value == "triumph"
        assert PlotPointType.COMPLICATION.value == "complication"
        assert PlotPointType.DISCOVERY.value == "discovery"
        assert PlotPointType.CONFRONTATION.value == "confrontation"
        assert PlotPointType.RECONCILIATION.value == "reconciliation"
        assert PlotPointType.SACRIFICE.value == "sacrifice"
        assert PlotPointType.TRANSFORMATION.value == "transformation"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_enum_uniqueness(self):
        """Test that all enum values are unique."""
        values = [item.value for item in PlotPointType]
        assert len(values) == len(set(values))

    @pytest.mark.unit
    @pytest.mark.fast
    def test_enum_membership(self):
        """Test enum membership operations."""
        assert PlotPointType.CLIMAX in PlotPointType
        assert "climax" == PlotPointType.CLIMAX.value
        assert PlotPointType.CLIMAX == PlotPointType("climax")


class TestPlotPointImportanceEnum:
    """Test suite for PlotPointImportance enum."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_all_importance_levels_exist(self):
        """Test that all expected importance levels are defined."""
        expected_levels = {"CRITICAL", "MAJOR", "MODERATE", "MINOR", "SUPPLEMENTAL"}
        actual_levels = {item.name for item in PlotPointImportance}
        assert actual_levels == expected_levels

    @pytest.mark.unit
    @pytest.mark.fast
    def test_importance_string_values(self):
        """Test that importance enum values have correct string representations."""
        assert PlotPointImportance.CRITICAL.value == "critical"
        assert PlotPointImportance.MAJOR.value == "major"
        assert PlotPointImportance.MODERATE.value == "moderate"
        assert PlotPointImportance.MINOR.value == "minor"
        assert PlotPointImportance.SUPPLEMENTAL.value == "supplemental"

    @pytest.mark.unit
    def test_importance_ordering_concept(self):
        """Test that importance levels represent logical ordering."""
        # Test that we can create a mapping for ordering
        importance_order = {
            PlotPointImportance.CRITICAL: 5,
            PlotPointImportance.MAJOR: 4,
            PlotPointImportance.MODERATE: 3,
            PlotPointImportance.MINOR: 2,
            PlotPointImportance.SUPPLEMENTAL: 1,
        }

        assert (
            importance_order[PlotPointImportance.CRITICAL]
            > importance_order[PlotPointImportance.MAJOR]
        )
        assert (
            importance_order[PlotPointImportance.MAJOR]
            > importance_order[PlotPointImportance.MODERATE]
        )
        assert (
            importance_order[PlotPointImportance.MODERATE]
            > importance_order[PlotPointImportance.MINOR]
        )
        assert (
            importance_order[PlotPointImportance.MINOR]
            > importance_order[PlotPointImportance.SUPPLEMENTAL]
        )


class TestPlotPointCreation:
    """Test suite for PlotPoint creation and initialization."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_create_minimal_plot_point(self):
        """Test creating plot point with minimal required fields."""
        plot_point = PlotPoint(
            plot_point_id="test-plot-point-1",
            plot_point_type=PlotPointType.RISING_ACTION,
            importance=PlotPointImportance.MODERATE,
            title="Test Plot Point",
            description="A test plot point for validation",
            sequence_order=10,
        )

        assert plot_point.plot_point_id == "test-plot-point-1"
        assert plot_point.plot_point_type == PlotPointType.RISING_ACTION
        assert plot_point.importance == PlotPointImportance.MODERATE
        assert plot_point.title == "Test Plot Point"
        assert plot_point.description == "A test plot point for validation"
        assert plot_point.sequence_order == 10

    @pytest.mark.unit
    def test_create_plot_point_with_all_fields(self):
        """Test creating plot point with all fields specified."""
        char_id1 = uuid4()
        char_id2 = uuid4()
        creation_time = datetime.now(timezone.utc)

        plot_point = PlotPoint(
            plot_point_id="comprehensive-plot-point",
            plot_point_type=PlotPointType.CLIMAX,
            importance=PlotPointImportance.CRITICAL,
            title="Major Climax",
            description="The main climactic moment of the story",
            sequence_order=50,
            estimated_duration=120,
            involved_characters={char_id1, char_id2},
            affected_themes={"redemption", "sacrifice"},
            location_context="Ancient temple",
            emotional_intensity=Decimal("9.5"),
            dramatic_tension=Decimal("10.0"),
            story_significance=Decimal("9.8"),
            prerequisite_events=["hero_training", "villain_revealed"],
            triggered_consequences=["world_saved", "hero_transformed"],
            reveals_information=True,
            changes_character_relationships=True,
            advances_main_plot=True,
            advances_subplot=False,
            tags={"climax", "action", "resolution"},
            narrative_notes="This is the pivotal moment",
            creation_timestamp=creation_time,
            metadata={"author": "test", "version": 1},
        )

        assert plot_point.plot_point_id == "comprehensive-plot-point"
        assert plot_point.plot_point_type == PlotPointType.CLIMAX
        assert plot_point.importance == PlotPointImportance.CRITICAL
        assert plot_point.estimated_duration == 120
        assert plot_point.involved_characters == {char_id1, char_id2}
        assert plot_point.affected_themes == {"redemption", "sacrifice"}
        assert plot_point.location_context == "Ancient temple"
        assert plot_point.emotional_intensity == Decimal("9.5")
        assert plot_point.dramatic_tension == Decimal("10.0")
        assert plot_point.story_significance == Decimal("9.8")
        assert plot_point.prerequisite_events == ["hero_training", "villain_revealed"]
        assert plot_point.triggered_consequences == ["world_saved", "hero_transformed"]
        assert plot_point.reveals_information is True
        assert plot_point.changes_character_relationships is True
        assert plot_point.advances_main_plot is True
        assert plot_point.advances_subplot is False
        assert plot_point.tags == {"climax", "action", "resolution"}
        assert plot_point.narrative_notes == "This is the pivotal moment"
        assert plot_point.creation_timestamp == creation_time
        assert plot_point.metadata == {"author": "test", "version": 1}

    @pytest.mark.unit
    def test_default_values_initialization(self):
        """Test that default values are properly initialized."""
        plot_point = PlotPoint(
            plot_point_id="default-test",
            plot_point_type=PlotPointType.DISCOVERY,
            importance=PlotPointImportance.MINOR,
            title="Default Test",
            description="Testing default values",
            sequence_order=5,
        )

        # Test default collections are empty sets/lists
        assert plot_point.involved_characters == set()
        assert plot_point.affected_themes == set()
        assert plot_point.prerequisite_events == []
        assert plot_point.triggered_consequences == []
        assert plot_point.tags == set()
        assert plot_point.metadata == {}

        # Test default values
        assert plot_point.estimated_duration is None
        assert plot_point.location_context is None
        assert plot_point.emotional_intensity == Decimal("5.0")
        assert plot_point.dramatic_tension == Decimal("5.0")
        assert plot_point.story_significance == Decimal("5.0")
        assert plot_point.reveals_information is False
        assert plot_point.changes_character_relationships is False
        assert plot_point.advances_main_plot is True
        assert plot_point.advances_subplot is False
        assert plot_point.narrative_notes == ""

        # Test that creation timestamp was set
        assert plot_point.creation_timestamp is not None
        assert isinstance(plot_point.creation_timestamp, datetime)

    @pytest.mark.unit
    def test_frozen_dataclass_immutability(self):
        """Test that PlotPoint is immutable (frozen dataclass)."""
        plot_point = PlotPoint(
            plot_point_id="immutable-test",
            plot_point_type=PlotPointType.REVELATION,
            importance=PlotPointImportance.MAJOR,
            title="Immutable Test",
            description="Testing immutability",
            sequence_order=15,
        )

        # Should not be able to modify fields
        with pytest.raises(AttributeError):
            plot_point.title = "Modified Title"

        with pytest.raises(AttributeError):
            plot_point.sequence_order = 20

        with pytest.raises(AttributeError):
            plot_point.emotional_intensity = Decimal("8.0")


class TestPlotPointValidation:
    """Test suite for PlotPoint validation logic."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_empty_title_validation(self):
        """Test validation fails with empty title."""
        with pytest.raises(ValueError, match="Plot point title cannot be empty"):
            PlotPoint(
                plot_point_id="empty-title-test",
                plot_point_type=PlotPointType.COMPLICATION,
                importance=PlotPointImportance.MODERATE,
                title="",
                description="Valid description",
                sequence_order=10,
            )

    @pytest.mark.unit
    def test_whitespace_only_title_validation(self):
        """Test validation fails with whitespace-only title."""
        with pytest.raises(ValueError, match="Plot point title cannot be empty"):
            PlotPoint(
                plot_point_id="whitespace-title-test",
                plot_point_type=PlotPointType.COMPLICATION,
                importance=PlotPointImportance.MODERATE,
                title="   ",
                description="Valid description",
                sequence_order=10,
            )

    @pytest.mark.unit
    def test_empty_description_validation(self):
        """Test validation fails with empty description."""
        with pytest.raises(ValueError, match="Plot point description cannot be empty"):
            PlotPoint(
                plot_point_id="empty-desc-test",
                plot_point_type=PlotPointType.SETBACK,
                importance=PlotPointImportance.MINOR,
                title="Valid Title",
                description="",
                sequence_order=10,
            )

    @pytest.mark.unit
    def test_whitespace_only_description_validation(self):
        """Test validation fails with whitespace-only description."""
        with pytest.raises(ValueError, match="Plot point description cannot be empty"):
            PlotPoint(
                plot_point_id="whitespace-desc-test",
                plot_point_type=PlotPointType.SETBACK,
                importance=PlotPointImportance.MINOR,
                title="Valid Title",
                description="   \t\n  ",
                sequence_order=10,
            )

    @pytest.mark.unit
    def test_negative_sequence_order_validation(self):
        """Test validation fails with negative sequence order."""
        with pytest.raises(ValueError, match="Sequence order must be non-negative"):
            PlotPoint(
                plot_point_id="negative-seq-test",
                plot_point_type=PlotPointType.TRIUMPH,
                importance=PlotPointImportance.MAJOR,
                title="Valid Title",
                description="Valid description",
                sequence_order=-1,
            )

    @pytest.mark.unit
    @pytest.mark.fast
    def test_zero_sequence_order_allowed(self):
        """Test that zero sequence order is allowed."""
        plot_point = PlotPoint(
            plot_point_id="zero-seq-test",
            plot_point_type=PlotPointType.INCITING_INCIDENT,
            importance=PlotPointImportance.CRITICAL,
            title="Starting Point",
            description="The beginning",
            sequence_order=0,
        )

        assert plot_point.sequence_order == 0

    @pytest.mark.unit
    def test_negative_estimated_duration_validation(self):
        """Test validation fails with negative estimated duration."""
        with pytest.raises(
            ValueError, match="Estimated duration must be positive if specified"
        ):
            PlotPoint(
                plot_point_id="negative-duration-test",
                plot_point_type=PlotPointType.CRISIS,
                importance=PlotPointImportance.CRITICAL,
                title="Valid Title",
                description="Valid description",
                sequence_order=10,
                estimated_duration=-5,
            )

    @pytest.mark.unit
    def test_zero_estimated_duration_validation(self):
        """Test validation fails with zero estimated duration."""
        with pytest.raises(
            ValueError, match="Estimated duration must be positive if specified"
        ):
            PlotPoint(
                plot_point_id="zero-duration-test",
                plot_point_type=PlotPointType.CRISIS,
                importance=PlotPointImportance.CRITICAL,
                title="Valid Title",
                description="Valid description",
                sequence_order=10,
                estimated_duration=0,
            )

    @pytest.mark.unit
    def test_none_estimated_duration_allowed(self):
        """Test that None estimated duration is allowed."""
        plot_point = PlotPoint(
            plot_point_id="none-duration-test",
            plot_point_type=PlotPointType.CONFRONTATION,
            importance=PlotPointImportance.MAJOR,
            title="Valid Title",
            description="Valid description",
            sequence_order=10,
            estimated_duration=None,
        )

        assert plot_point.estimated_duration is None

    @pytest.mark.unit
    def test_emotional_intensity_below_minimum_validation(self):
        """Test validation fails with emotional intensity below 0."""
        with pytest.raises(
            ValueError, match="emotional_intensity must be between 0 and 10"
        ):
            PlotPoint(
                plot_point_id="low-emotion-test",
                plot_point_type=PlotPointType.RECONCILIATION,
                importance=PlotPointImportance.MODERATE,
                title="Valid Title",
                description="Valid description",
                sequence_order=10,
                emotional_intensity=Decimal("-1.0"),
            )

    @pytest.mark.unit
    def test_emotional_intensity_above_maximum_validation(self):
        """Test validation fails with emotional intensity above 10."""
        with pytest.raises(
            ValueError, match="emotional_intensity must be between 0 and 10"
        ):
            PlotPoint(
                plot_point_id="high-emotion-test",
                plot_point_type=PlotPointType.RECONCILIATION,
                importance=PlotPointImportance.MODERATE,
                title="Valid Title",
                description="Valid description",
                sequence_order=10,
                emotional_intensity=Decimal("11.0"),
            )

    @pytest.mark.unit
    def test_dramatic_tension_boundary_validation(self):
        """Test dramatic tension boundary validation."""
        with pytest.raises(
            ValueError, match="dramatic_tension must be between 0 and 10"
        ):
            PlotPoint(
                plot_point_id="high-tension-test",
                plot_point_type=PlotPointType.SACRIFICE,
                importance=PlotPointImportance.CRITICAL,
                title="Valid Title",
                description="Valid description",
                sequence_order=10,
                dramatic_tension=Decimal("15.5"),
            )

    @pytest.mark.unit
    def test_story_significance_boundary_validation(self):
        """Test story significance boundary validation."""
        with pytest.raises(
            ValueError, match="story_significance must be between 0 and 10"
        ):
            PlotPoint(
                plot_point_id="low-significance-test",
                plot_point_type=PlotPointType.TRANSFORMATION,
                importance=PlotPointImportance.MAJOR,
                title="Valid Title",
                description="Valid description",
                sequence_order=10,
                story_significance=Decimal("-0.5"),
            )

    @pytest.mark.unit
    def test_valid_intensity_boundary_values(self):
        """Test that boundary intensity values (0 and 10) are valid."""
        plot_point = PlotPoint(
            plot_point_id="boundary-test",
            plot_point_type=PlotPointType.CLIMAX,
            importance=PlotPointImportance.CRITICAL,
            title="Boundary Test",
            description="Testing boundary values",
            sequence_order=25,
            emotional_intensity=Decimal("0.0"),
            dramatic_tension=Decimal("10.0"),
            story_significance=Decimal("5.5"),
        )

        assert plot_point.emotional_intensity == Decimal("0.0")
        assert plot_point.dramatic_tension == Decimal("10.0")
        assert plot_point.story_significance == Decimal("5.5")

    @pytest.mark.unit
    def test_plot_point_id_max_length_validation(self):
        """Test validation fails with plot point ID too long."""
        long_id = "x" * 101  # 101 characters

        with pytest.raises(
            ValueError, match="Plot point ID too long \\(max 100 characters\\)"
        ):
            PlotPoint(
                plot_point_id=long_id,
                plot_point_type=PlotPointType.DISCOVERY,
                importance=PlotPointImportance.MINOR,
                title="Valid Title",
                description="Valid description",
                sequence_order=10,
            )

    @pytest.mark.unit
    def test_title_max_length_validation(self):
        """Test validation fails with title too long."""
        long_title = "x" * 201  # 201 characters

        with pytest.raises(
            ValueError, match="Plot point title too long \\(max 200 characters\\)"
        ):
            PlotPoint(
                plot_point_id="long-title-test",
                plot_point_type=PlotPointType.FALLING_ACTION,
                importance=PlotPointImportance.MODERATE,
                title=long_title,
                description="Valid description",
                sequence_order=10,
            )

    @pytest.mark.unit
    def test_description_max_length_validation(self):
        """Test validation fails with description too long."""
        long_description = "x" * 2001  # 2001 characters

        with pytest.raises(
            ValueError,
            match="Plot point description too long \\(max 2000 characters\\)",
        ):
            PlotPoint(
                plot_point_id="long-desc-test",
                plot_point_type=PlotPointType.RESOLUTION,
                importance=PlotPointImportance.MAJOR,
                title="Valid Title",
                description=long_description,
                sequence_order=10,
            )

    @pytest.mark.unit
    def test_valid_max_length_boundaries(self):
        """Test that maximum length boundaries are valid."""
        max_id = "x" * 100
        max_title = "x" * 200
        max_description = "x" * 2000

        plot_point = PlotPoint(
            plot_point_id=max_id,
            plot_point_type=PlotPointType.TURNING_POINT,
            importance=PlotPointImportance.MAJOR,
            title=max_title,
            description=max_description,
            sequence_order=30,
        )

        assert len(plot_point.plot_point_id) == 100
        assert len(plot_point.title) == 200
        assert len(plot_point.description) == 2000


class TestPlotPointProperties:
    """Test suite for PlotPoint property methods."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_is_major_plot_point_critical(self):
        """Test is_major_plot_point returns True for CRITICAL importance."""
        plot_point = PlotPoint(
            plot_point_id="critical-test",
            plot_point_type=PlotPointType.CLIMAX,
            importance=PlotPointImportance.CRITICAL,
            title="Critical Point",
            description="A critical plot point",
            sequence_order=50,
        )

        assert plot_point.is_major_plot_point is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_is_major_plot_point_major(self):
        """Test is_major_plot_point returns True for MAJOR importance."""
        plot_point = PlotPoint(
            plot_point_id="major-test",
            plot_point_type=PlotPointType.REVELATION,
            importance=PlotPointImportance.MAJOR,
            title="Major Point",
            description="A major plot point",
            sequence_order=30,
        )

        assert plot_point.is_major_plot_point is True

    @pytest.mark.unit
    def test_is_major_plot_point_false_for_lower_importance(self):
        """Test is_major_plot_point returns False for lower importance levels."""
        plot_points = [
            (PlotPointImportance.MODERATE, "moderate-test"),
            (PlotPointImportance.MINOR, "minor-test"),
            (PlotPointImportance.SUPPLEMENTAL, "supplemental-test"),
        ]

        for importance, test_id in plot_points:
            plot_point = PlotPoint(
                plot_point_id=test_id,
                plot_point_type=PlotPointType.COMPLICATION,
                importance=importance,
                title=f"Test {importance.value}",
                description=f"Testing {importance.value} importance",
                sequence_order=10,
            )

            assert plot_point.is_major_plot_point is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_is_climactic_true_for_climax(self):
        """Test is_climactic returns True for CLIMAX type."""
        plot_point = PlotPoint(
            plot_point_id="climax-test",
            plot_point_type=PlotPointType.CLIMAX,
            importance=PlotPointImportance.CRITICAL,
            title="The Climax",
            description="The story climax",
            sequence_order=75,
        )

        assert plot_point.is_climactic is True

    @pytest.mark.unit
    def test_is_climactic_false_for_non_climax(self):
        """Test is_climactic returns False for non-CLIMAX types."""
        non_climax_types = [
            PlotPointType.INCITING_INCIDENT,
            PlotPointType.RISING_ACTION,
            PlotPointType.FALLING_ACTION,
            PlotPointType.RESOLUTION,
            PlotPointType.REVELATION,
        ]

        for plot_type in non_climax_types:
            plot_point = PlotPoint(
                plot_point_id=f"non-climax-{plot_type.value}",
                plot_point_type=plot_type,
                importance=PlotPointImportance.MODERATE,
                title=f"Non-climax {plot_type.value}",
                description=f"Testing {plot_type.value}",
                sequence_order=20,
            )

            assert plot_point.is_climactic is False

    @pytest.mark.unit
    def test_is_turning_point_for_turning_point_types(self):
        """Test is_turning_point returns True for turning point types."""
        turning_point_types = [
            PlotPointType.CLIMAX,
            PlotPointType.TURNING_POINT,
            PlotPointType.REVELATION,
            PlotPointType.CRISIS,
            PlotPointType.TRANSFORMATION,
        ]

        for plot_type in turning_point_types:
            plot_point = PlotPoint(
                plot_point_id=f"turning-{plot_type.value}",
                plot_point_type=plot_type,
                importance=PlotPointImportance.MAJOR,
                title=f"Turning point {plot_type.value}",
                description=f"Testing turning point {plot_type.value}",
                sequence_order=40,
            )

            assert plot_point.is_turning_point is True

    @pytest.mark.unit
    def test_is_turning_point_false_for_non_turning_point_types(self):
        """Test is_turning_point returns False for non-turning point types."""
        non_turning_types = [
            PlotPointType.INCITING_INCIDENT,
            PlotPointType.RISING_ACTION,
            PlotPointType.FALLING_ACTION,
            PlotPointType.RESOLUTION,
            PlotPointType.SETBACK,
            PlotPointType.TRIUMPH,
            PlotPointType.COMPLICATION,
        ]

        for plot_type in non_turning_types:
            plot_point = PlotPoint(
                plot_point_id=f"non-turning-{plot_type.value}",
                plot_point_type=plot_type,
                importance=PlotPointImportance.MODERATE,
                title=f"Non-turning {plot_type.value}",
                description=f"Testing non-turning {plot_type.value}",
                sequence_order=25,
            )

            assert plot_point.is_turning_point is False

    @pytest.mark.unit
    def test_has_prerequisites_with_events(self):
        """Test has_prerequisites returns True when prerequisite events exist."""
        plot_point = PlotPoint(
            plot_point_id="prereq-test",
            plot_point_type=PlotPointType.CONFRONTATION,
            importance=PlotPointImportance.MAJOR,
            title="Confrontation Scene",
            description="Major confrontation",
            sequence_order=60,
            prerequisite_events=["character_development", "relationship_strain"],
        )

        assert plot_point.has_prerequisites is True

    @pytest.mark.unit
    def test_has_prerequisites_without_events(self):
        """Test has_prerequisites returns False when no prerequisite events."""
        plot_point = PlotPoint(
            plot_point_id="no-prereq-test",
            plot_point_type=PlotPointType.INCITING_INCIDENT,
            importance=PlotPointImportance.CRITICAL,
            title="Story Start",
            description="Beginning of story",
            sequence_order=1,
            prerequisite_events=[],
        )

        assert plot_point.has_prerequisites is False

    @pytest.mark.unit
    def test_has_consequences_with_events(self):
        """Test has_consequences returns True when consequence events exist."""
        plot_point = PlotPoint(
            plot_point_id="conseq-test",
            plot_point_type=PlotPointType.SACRIFICE,
            importance=PlotPointImportance.CRITICAL,
            title="Hero's Sacrifice",
            description="Ultimate sacrifice scene",
            sequence_order=85,
            triggered_consequences=[
                "villain_defeated",
                "world_saved",
                "hero_remembered",
            ],
        )

        assert plot_point.has_consequences is True

    @pytest.mark.unit
    def test_has_consequences_without_events(self):
        """Test has_consequences returns False when no consequence events."""
        plot_point = PlotPoint(
            plot_point_id="no-conseq-test",
            plot_point_type=PlotPointType.DISCOVERY,
            importance=PlotPointImportance.MINOR,
            title="Small Discovery",
            description="Minor revelation",
            sequence_order=15,
            triggered_consequences=[],
        )

        assert plot_point.has_consequences is False

    @pytest.mark.unit
    def test_affects_characters_with_characters(self):
        """Test affects_characters returns True when characters are involved."""
        char_id1 = uuid4()
        char_id2 = uuid4()

        plot_point = PlotPoint(
            plot_point_id="chars-test",
            plot_point_type=PlotPointType.RECONCILIATION,
            importance=PlotPointImportance.MAJOR,
            title="Character Reconciliation",
            description="Characters make peace",
            sequence_order=70,
            involved_characters={char_id1, char_id2},
        )

        assert plot_point.affects_characters is True

    @pytest.mark.unit
    def test_affects_characters_without_characters(self):
        """Test affects_characters returns False when no characters involved."""
        plot_point = PlotPoint(
            plot_point_id="no-chars-test",
            plot_point_type=PlotPointType.RISING_ACTION,
            importance=PlotPointImportance.MODERATE,
            title="Environmental Event",
            description="Natural disaster",
            sequence_order=35,
            involved_characters=set(),
        )

        assert plot_point.affects_characters is False


class TestPlotPointOverallImpactScore:
    """Test suite for overall impact score calculation."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_critical_importance_impact_score(self):
        """Test impact score calculation for CRITICAL importance."""
        plot_point = PlotPoint(
            plot_point_id="critical-impact-test",
            plot_point_type=PlotPointType.CLIMAX,
            importance=PlotPointImportance.CRITICAL,
            title="Critical Climax",
            description="The most important moment",
            sequence_order=50,
            emotional_intensity=Decimal("8.0"),
            dramatic_tension=Decimal("9.0"),
            story_significance=Decimal("10.0"),
        )

        # Expected: (9.0 * 0.4 + 10.0 * 0.4 + 8.0 * 0.2) * 1.0 = 9.2
        expected_score = Decimal("9.2")
        assert plot_point.overall_impact_score == expected_score

    @pytest.mark.unit
    def test_major_importance_impact_score(self):
        """Test impact score calculation for MAJOR importance."""
        plot_point = PlotPoint(
            plot_point_id="major-impact-test",
            plot_point_type=PlotPointType.REVELATION,
            importance=PlotPointImportance.MAJOR,
            title="Major Revelation",
            description="Important discovery",
            sequence_order=40,
            emotional_intensity=Decimal("6.0"),
            dramatic_tension=Decimal("7.0"),
            story_significance=Decimal("8.0"),
        )

        # Expected: (7.0 * 0.4 + 8.0 * 0.4 + 6.0 * 0.2) * 0.8 = 5.76
        expected_score = Decimal("5.76")
        assert plot_point.overall_impact_score == expected_score

    @pytest.mark.unit
    def test_supplemental_importance_impact_score(self):
        """Test impact score calculation for SUPPLEMENTAL importance."""
        plot_point = PlotPoint(
            plot_point_id="supplemental-impact-test",
            plot_point_type=PlotPointType.COMPLICATION,
            importance=PlotPointImportance.SUPPLEMENTAL,
            title="Minor Complication",
            description="Small obstacle",
            sequence_order=20,
            emotional_intensity=Decimal("3.0"),
            dramatic_tension=Decimal("4.0"),
            story_significance=Decimal("2.0"),
        )

        # Expected: (4.0 * 0.4 + 2.0 * 0.4 + 3.0 * 0.2) * 0.2 = (1.6 + 0.8 + 0.6) * 0.2 = 0.6
        expected_score = Decimal("0.6")
        assert plot_point.overall_impact_score == expected_score

    @pytest.mark.unit
    def test_impact_score_boundary_values(self):
        """Test impact score with boundary intensity values."""
        # Maximum possible score
        max_plot_point = PlotPoint(
            plot_point_id="max-impact-test",
            plot_point_type=PlotPointType.CLIMAX,
            importance=PlotPointImportance.CRITICAL,
            title="Maximum Impact",
            description="Highest possible impact",
            sequence_order=100,
            emotional_intensity=Decimal("10.0"),
            dramatic_tension=Decimal("10.0"),
            story_significance=Decimal("10.0"),
        )

        # Expected: (10.0 * 0.4 + 10.0 * 0.4 + 10.0 * 0.2) * 1.0 = 10.0
        assert max_plot_point.overall_impact_score == Decimal("10.0")

        # Minimum possible score
        min_plot_point = PlotPoint(
            plot_point_id="min-impact-test",
            plot_point_type=PlotPointType.SETBACK,
            importance=PlotPointImportance.SUPPLEMENTAL,
            title="Minimum Impact",
            description="Lowest possible impact",
            sequence_order=5,
            emotional_intensity=Decimal("0.0"),
            dramatic_tension=Decimal("0.0"),
            story_significance=Decimal("0.0"),
        )

        # Expected: (0.0 * 0.4 + 0.0 * 0.4 + 0.0 * 0.2) * 0.2 = 0.0
        assert min_plot_point.overall_impact_score == Decimal("0.0")


class TestPlotPointInstanceMethods:
    """Test suite for PlotPoint instance methods."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_involves_character_true(self):
        """Test involves_character returns True for involved character."""
        char_id1 = uuid4()
        char_id2 = uuid4()
        char_id3 = uuid4()

        plot_point = PlotPoint(
            plot_point_id="char-involvement-test",
            plot_point_type=PlotPointType.CONFRONTATION,
            importance=PlotPointImportance.MAJOR,
            title="Character Scene",
            description="Scene with multiple characters",
            sequence_order=45,
            involved_characters={char_id1, char_id2},
        )

        assert plot_point.involves_character(char_id1) is True
        assert plot_point.involves_character(char_id2) is True
        assert plot_point.involves_character(char_id3) is False

    @pytest.mark.unit
    def test_affects_theme_true(self):
        """Test affects_theme returns True for affected theme."""
        plot_point = PlotPoint(
            plot_point_id="theme-test",
            plot_point_type=PlotPointType.TRANSFORMATION,
            importance=PlotPointImportance.CRITICAL,
            title="Character Growth",
            description="Major character development",
            sequence_order=80,
            affected_themes={"redemption", "courage", "sacrifice"},
        )

        assert plot_point.affects_theme("redemption") is True
        assert plot_point.affects_theme("courage") is True
        assert plot_point.affects_theme("love") is False

    @pytest.mark.unit
    def test_has_tag_true(self):
        """Test has_tag returns True for existing tag."""
        plot_point = PlotPoint(
            plot_point_id="tag-test",
            plot_point_type=PlotPointType.TRIUMPH,
            importance=PlotPointImportance.MAJOR,
            title="Victory Scene",
            description="Heroes achieve victory",
            sequence_order=90,
            tags={"victory", "celebration", "resolution"},
        )

        assert plot_point.has_tag("victory") is True
        assert plot_point.has_tag("celebration") is True
        assert plot_point.has_tag("defeat") is False

    @pytest.mark.unit
    def test_get_narrative_context(self):
        """Test get_narrative_context returns comprehensive context dict."""
        char_id = uuid4()

        plot_point = PlotPoint(
            plot_point_id="context-test",
            plot_point_type=PlotPointType.REVELATION,
            importance=PlotPointImportance.CRITICAL,
            title="Major Revelation",
            description="Truth is revealed",
            sequence_order=55,
            involved_characters={char_id},
            affected_themes={"truth", "deception"},
            prerequisite_events=["investigation"],
            triggered_consequences=["confrontation"],
            reveals_information=True,
            changes_character_relationships=True,
        )

        context = plot_point.get_narrative_context()

        assert context["plot_point_id"] == "context-test"
        assert context["type"] == "revelation"
        assert context["importance"] == "critical"
        assert context["sequence_order"] == 55
        assert context["is_major"] is True
        assert context["is_turning_point"] is True
        assert isinstance(context["overall_impact"], float)
        assert context["character_count"] == 1
        assert context["theme_count"] == 2
        assert context["has_prerequisites"] is True
        assert context["has_consequences"] is True
        assert context["reveals_information"] is True
        assert context["changes_relationships"] is True


class TestPlotPointFactoryMethods:
    """Test suite for PlotPoint factory methods."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_with_updated_intensity_single_value(self):
        """Test updating a single intensity value."""
        original = PlotPoint(
            plot_point_id="intensity-update-test",
            plot_point_type=PlotPointType.CRISIS,
            importance=PlotPointImportance.MAJOR,
            title="Crisis Point",
            description="Major crisis",
            sequence_order=60,
            emotional_intensity=Decimal("5.0"),
            dramatic_tension=Decimal("6.0"),
            story_significance=Decimal("7.0"),
        )

        updated = original.with_updated_intensity(emotional_intensity=Decimal("9.0"))

        # Updated value should change
        assert updated.emotional_intensity == Decimal("9.0")
        # Other values should remain the same
        assert updated.dramatic_tension == Decimal("6.0")
        assert updated.story_significance == Decimal("7.0")
        # All other fields should be identical
        assert updated.plot_point_id == original.plot_point_id
        assert updated.title == original.title
        assert updated.sequence_order == original.sequence_order

    @pytest.mark.unit
    def test_with_updated_intensity_multiple_values(self):
        """Test updating multiple intensity values."""
        original = PlotPoint(
            plot_point_id="multi-intensity-test",
            plot_point_type=PlotPointType.CLIMAX,
            importance=PlotPointImportance.CRITICAL,
            title="The Climax",
            description="Peak of the story",
            sequence_order=75,
            emotional_intensity=Decimal("7.0"),
            dramatic_tension=Decimal("8.0"),
            story_significance=Decimal("9.0"),
        )

        updated = original.with_updated_intensity(
            emotional_intensity=Decimal("10.0"), dramatic_tension=Decimal("10.0")
        )

        # Updated values should change
        assert updated.emotional_intensity == Decimal("10.0")
        assert updated.dramatic_tension == Decimal("10.0")
        # Non-updated value should remain the same
        assert updated.story_significance == Decimal("9.0")

    @pytest.mark.unit
    def test_with_updated_intensity_none_values(self):
        """Test that None values preserve original intensities."""
        original = PlotPoint(
            plot_point_id="none-intensity-test",
            plot_point_type=PlotPointType.RESOLUTION,
            importance=PlotPointImportance.MAJOR,
            title="Resolution",
            description="Story conclusion",
            sequence_order=95,
            emotional_intensity=Decimal("4.0"),
            dramatic_tension=Decimal("3.0"),
            story_significance=Decimal("8.0"),
        )

        updated = original.with_updated_intensity(
            emotional_intensity=None,
            dramatic_tension=Decimal("5.0"),
            story_significance=None,
        )

        # None values should preserve originals
        assert updated.emotional_intensity == Decimal("4.0")
        assert updated.story_significance == Decimal("8.0")
        # Non-None value should be updated
        assert updated.dramatic_tension == Decimal("5.0")

    @pytest.mark.unit
    def test_with_updated_intensity_immutability(self):
        """Test that original PlotPoint remains unchanged."""
        original = PlotPoint(
            plot_point_id="immutable-test",
            plot_point_type=PlotPointType.TURNING_POINT,
            importance=PlotPointImportance.CRITICAL,
            title="Original",
            description="Original description",
            sequence_order=50,
            emotional_intensity=Decimal("6.0"),
        )

        updated = original.with_updated_intensity(emotional_intensity=Decimal("9.0"))

        # Original should remain unchanged
        assert original.emotional_intensity == Decimal("6.0")
        # Updated should have new value
        assert updated.emotional_intensity == Decimal("9.0")
        # They should be different objects
        assert original is not updated

    @pytest.mark.unit
    def test_with_additional_characters_add_characters(self):
        """Test adding characters to a plot point."""
        char_id1 = uuid4()
        char_id2 = uuid4()
        char_id3 = uuid4()

        original = PlotPoint(
            plot_point_id="add-chars-test",
            plot_point_type=PlotPointType.CONFRONTATION,
            importance=PlotPointImportance.MAJOR,
            title="Initial Scene",
            description="Scene with some characters",
            sequence_order=40,
            involved_characters={char_id1},
        )

        updated = original.with_additional_characters({char_id2, char_id3})

        # Should have all characters
        assert updated.involved_characters == {char_id1, char_id2, char_id3}
        # Original should remain unchanged
        assert original.involved_characters == {char_id1}

    @pytest.mark.unit
    def test_with_additional_characters_duplicate_characters(self):
        """Test adding characters that already exist."""
        char_id1 = uuid4()
        char_id2 = uuid4()

        original = PlotPoint(
            plot_point_id="duplicate-chars-test",
            plot_point_type=PlotPointType.RECONCILIATION,
            importance=PlotPointImportance.MODERATE,
            title="Character Scene",
            description="Scene with characters",
            sequence_order=65,
            involved_characters={char_id1, char_id2},
        )

        updated = original.with_additional_characters({char_id1, char_id2})

        # Should still have the same characters (set union handles duplicates)
        assert updated.involved_characters == {char_id1, char_id2}
        assert len(updated.involved_characters) == 2

    @pytest.mark.unit
    def test_with_additional_characters_empty_set(self):
        """Test adding empty set of characters."""
        char_id = uuid4()

        original = PlotPoint(
            plot_point_id="empty-chars-test",
            plot_point_type=PlotPointType.DISCOVERY,
            importance=PlotPointImportance.MINOR,
            title="Solo Scene",
            description="Character alone",
            sequence_order=25,
            involved_characters={char_id},
        )

        updated = original.with_additional_characters(set())

        # Should have the same characters
        assert updated.involved_characters == {char_id}
        # Objects should be different
        assert original is not updated

    @pytest.mark.unit
    def test_with_additional_characters_immutability(self):
        """Test that original collections are not modified."""
        char_id1 = uuid4()
        char_id2 = uuid4()

        original = PlotPoint(
            plot_point_id="collection-immutable-test",
            plot_point_type=PlotPointType.SACRIFICE,
            importance=PlotPointImportance.CRITICAL,
            title="Sacrifice Scene",
            description="Character makes sacrifice",
            sequence_order=85,
            involved_characters={char_id1},
        )

        original_chars_before = original.involved_characters.copy()
        updated = original.with_additional_characters({char_id2})

        # Original should be unchanged
        assert original.involved_characters == original_chars_before
        assert char_id2 not in original.involved_characters
        # Updated should have new character
        assert char_id2 in updated.involved_characters


class TestPlotPointStringRepresentation:
    """Test suite for PlotPoint string representation methods."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_str_representation(self):
        """Test human-readable string representation."""
        plot_point = PlotPoint(
            plot_point_id="str-test",
            plot_point_type=PlotPointType.CLIMAX,
            importance=PlotPointImportance.CRITICAL,
            title="The Final Battle",
            description="Ultimate confrontation",
            sequence_order=90,
        )

        str_repr = str(plot_point)
        expected = "PlotPoint('The Final Battle', climax, seq=90)"
        assert str_repr == expected

    @pytest.mark.unit
    def test_repr_representation(self):
        """Test developer representation for debugging."""
        plot_point = PlotPoint(
            plot_point_id="repr-test-id",
            plot_point_type=PlotPointType.REVELATION,
            importance=PlotPointImportance.MAJOR,
            title="Truth Revealed",
            description="The truth comes out",
            sequence_order=65,
        )

        repr_str = repr(plot_point)
        expected = (
            "PlotPoint(id='repr-test-id', "
            "type=revelation, "
            "importance=major, "
            "title='Truth Revealed', "
            "sequence_order=65)"
        )
        assert repr_str == expected

    @pytest.mark.unit
    def test_string_representations_different(self):
        """Test that str and repr provide different information."""
        plot_point = PlotPoint(
            plot_point_id="different-repr-test",
            plot_point_type=PlotPointType.TRANSFORMATION,
            importance=PlotPointImportance.CRITICAL,
            title="Character Growth",
            description="Character learns and grows",
            sequence_order=80,
        )

        str_repr = str(plot_point)
        repr_str = repr(plot_point)

        # They should be different
        assert str_repr != repr_str
        # str should be more human-readable
        assert "Character Growth" in str_repr
        # repr should include more technical details
        assert "different-repr-test" in repr_str
        assert "critical" in repr_str


class TestPlotPointEdgeCasesAndBoundaryConditions:
    """Test suite for edge cases and boundary conditions."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_creation_with_mock_timestamp(self):
        """Test creation with explicitly mocked timestamp."""
        fixed_time = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)

        plot_point = PlotPoint(
            plot_point_id="timestamp-test",
            plot_point_type=PlotPointType.INCITING_INCIDENT,
            importance=PlotPointImportance.CRITICAL,
            title="Story Begins",
            description="The story starts here",
            sequence_order=1,
            creation_timestamp=fixed_time,
        )

        assert plot_point.creation_timestamp == fixed_time

    @pytest.mark.unit
    def test_large_collections_handling(self):
        """Test handling of large collections."""
        many_characters = {uuid4() for _ in range(100)}
        many_themes = {f"theme_{i}" for i in range(50)}
        many_events = [f"event_{i}" for i in range(75)]
        many_consequences = [f"consequence_{i}" for i in range(60)]
        many_tags = {f"tag_{i}" for i in range(25)}

        plot_point = PlotPoint(
            plot_point_id="large-collections-test",
            plot_point_type=PlotPointType.CLIMAX,
            importance=PlotPointImportance.CRITICAL,
            title="Epic Climax",
            description="A climax involving many elements",
            sequence_order=100,
            involved_characters=many_characters,
            affected_themes=many_themes,
            prerequisite_events=many_events,
            triggered_consequences=many_consequences,
            tags=many_tags,
        )

        assert len(plot_point.involved_characters) == 100
        assert len(plot_point.affected_themes) == 50
        assert len(plot_point.prerequisite_events) == 75
        assert len(plot_point.triggered_consequences) == 60
        assert len(plot_point.tags) == 25
        assert plot_point.affects_characters is True
        assert plot_point.has_prerequisites is True
        assert plot_point.has_consequences is True

    @pytest.mark.unit
    def test_decimal_precision_handling(self):
        """Test handling of decimal precision for intensity values."""
        plot_point = PlotPoint(
            plot_point_id="precision-test",
            plot_point_type=PlotPointType.CRISIS,
            importance=PlotPointImportance.MAJOR,
            title="Precise Crisis",
            description="Testing decimal precision",
            sequence_order=45,
            emotional_intensity=Decimal("7.123456789"),
            dramatic_tension=Decimal("8.987654321"),
            story_significance=Decimal("9.555555555"),
        )

        # Values should maintain precision
        assert plot_point.emotional_intensity == Decimal("7.123456789")
        assert plot_point.dramatic_tension == Decimal("8.987654321")
        assert plot_point.story_significance == Decimal("9.555555555")

        # Impact score should use precise calculation
        impact_score = plot_point.overall_impact_score
        assert isinstance(impact_score, Decimal)
        # Should be calculated with precision
        expected = (
            (Decimal("8.987654321") * Decimal("0.4"))
            + (Decimal("9.555555555") * Decimal("0.4"))
            + (Decimal("7.123456789") * Decimal("0.2"))
        ) * Decimal(
            "0.8"
        )  # MAJOR importance weight
        assert impact_score == expected

    @pytest.mark.unit
    def test_unicode_text_handling(self):
        """Test handling of unicode characters in text fields."""
        plot_point = PlotPoint(
            plot_point_id="unicode-test-🎭",
            plot_point_type=PlotPointType.REVELATION,
            importance=PlotPointImportance.MAJOR,
            title="révélation épique 🎯",
            description="Une révélation importante avec des caractères unicode: αβγ 中文 🚀",
            sequence_order=50,
            location_context="café parisien ☕",
            narrative_notes="Notes avec émojis 📝✨",
        )

        assert "🎭" in plot_point.plot_point_id
        assert "révélation épique 🎯" in plot_point.title
        assert "中文" in plot_point.description
        assert "café parisien ☕" in plot_point.location_context
        assert "📝✨" in plot_point.narrative_notes

    @pytest.mark.unit
    def test_complex_metadata_handling(self):
        """Test handling of complex metadata structures."""
        complex_metadata = {
            "nested_dict": {"level1": {"level2": ["item1", "item2", "item3"]}},
            "list_of_dicts": [
                {"key1": "value1", "key2": 42},
                {"key3": "value3", "key4": 3.14},
            ],
            "unicode_key_🔑": "unicode_value_🌟",
            "numbers": {
                "integer": 123,
                "float": 45.67,
                "decimal": str(Decimal("89.012")),
            },
        }

        plot_point = PlotPoint(
            plot_point_id="complex-metadata-test",
            plot_point_type=PlotPointType.TRANSFORMATION,
            importance=PlotPointImportance.CRITICAL,
            title="Complex Metadata",
            description="Testing complex metadata handling",
            sequence_order=75,
            metadata=complex_metadata,
        )

        # Should store complex metadata as-is
        assert plot_point.metadata == complex_metadata
        assert plot_point.metadata["nested_dict"]["level1"]["level2"] == [
            "item1",
            "item2",
            "item3",
        ]
        assert plot_point.metadata["unicode_key_🔑"] == "unicode_value_🌟"


class TestPlotPointCollectionsAndComparison:
    """Test suite for PlotPoint behavior in collections and comparisons."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_plot_points_in_list(self):
        """Test PlotPoint objects in list operations."""
        plot1 = PlotPoint(
            plot_point_id="list-test-1",
            plot_point_type=PlotPointType.INCITING_INCIDENT,
            importance=PlotPointImportance.CRITICAL,
            title="Beginning",
            description="Story starts",
            sequence_order=1,
        )

        plot2 = PlotPoint(
            plot_point_id="list-test-2",
            plot_point_type=PlotPointType.CLIMAX,
            importance=PlotPointImportance.CRITICAL,
            title="Peak",
            description="Story peak",
            sequence_order=50,
        )

        plot_list = [plot1, plot2]

        assert len(plot_list) == 2
        assert plot1 in plot_list
        assert plot2 in plot_list

    @pytest.mark.unit
    def test_plot_points_sorting_by_sequence(self):
        """Test sorting PlotPoint objects by sequence order."""
        plots = [
            PlotPoint(
                plot_point_id=f"sort-test-{i}",
                plot_point_type=PlotPointType.RISING_ACTION,
                importance=PlotPointImportance.MODERATE,
                title=f"Plot Point {i}",
                description=f"Plot point number {i}",
                sequence_order=order,
            )
            for i, order in enumerate([30, 10, 50, 20, 40])
        ]

        sorted_plots = sorted(plots, key=lambda p: p.sequence_order)
        expected_orders = [10, 20, 30, 40, 50]
        actual_orders = [p.sequence_order for p in sorted_plots]

        assert actual_orders == expected_orders

    @pytest.mark.unit
    def test_plot_points_sorting_by_impact_score(self):
        """Test sorting PlotPoint objects by overall impact score."""
        plots = [
            PlotPoint(
                plot_point_id=f"impact-sort-{i}",
                plot_point_type=PlotPointType.CRISIS,
                importance=importance,
                title=f"Crisis {i}",
                description=f"Crisis point {i}",
                sequence_order=i * 10,
                emotional_intensity=Decimal(str(intensity)),
                dramatic_tension=Decimal(str(tension)),
                story_significance=Decimal(str(significance)),
            )
            for i, (importance, intensity, tension, significance) in enumerate(
                [
                    (PlotPointImportance.MINOR, 3.0, 4.0, 2.0),
                    (PlotPointImportance.CRITICAL, 9.0, 10.0, 9.5),
                    (PlotPointImportance.MODERATE, 6.0, 5.0, 7.0),
                    (PlotPointImportance.MAJOR, 8.0, 8.5, 8.0),
                ]
            )
        ]

        sorted_by_impact = sorted(
            plots, key=lambda p: p.overall_impact_score, reverse=True
        )

        # CRITICAL should be first (highest impact)
        assert sorted_by_impact[0].importance == PlotPointImportance.CRITICAL
        # MINOR should be last (lowest impact)
        assert sorted_by_impact[-1].importance == PlotPointImportance.MINOR

    @pytest.mark.unit
    def test_plot_point_equality_identity(self):
        """Test that identical PlotPoint objects are considered equal."""
        plot1 = PlotPoint(
            plot_point_id="equality-test",
            plot_point_type=PlotPointType.REVELATION,
            importance=PlotPointImportance.MAJOR,
            title="Same Plot Point",
            description="Identical plot point",
            sequence_order=25,
        )

        plot2 = PlotPoint(
            plot_point_id="equality-test",
            plot_point_type=PlotPointType.REVELATION,
            importance=PlotPointImportance.MAJOR,
            title="Same Plot Point",
            description="Identical plot point",
            sequence_order=25,
        )

        # Frozen dataclasses with same values should be equal
        assert plot1 == plot2
        # But they should be different objects
        assert plot1 is not plot2

    @pytest.mark.unit
    def test_plot_point_inequality(self):
        """Test that different PlotPoint objects are not equal."""
        plot1 = PlotPoint(
            plot_point_id="different-1",
            plot_point_type=PlotPointType.CRISIS,
            importance=PlotPointImportance.CRITICAL,
            title="Crisis One",
            description="First crisis",
            sequence_order=40,
        )

        plot2 = PlotPoint(
            plot_point_id="different-2",
            plot_point_type=PlotPointType.CRISIS,
            importance=PlotPointImportance.CRITICAL,
            title="Crisis Two",
            description="Second crisis",
            sequence_order=60,
        )

        assert plot1 != plot2
        assert not (plot1 == plot2)

    @pytest.mark.unit
    def test_plot_point_hashing_consistency(self):
        """Test that equal PlotPoint objects have same hash."""
        plot1 = PlotPoint(
            plot_point_id="hash-test",
            plot_point_type=PlotPointType.TURNING_POINT,
            importance=PlotPointImportance.MAJOR,
            title="Hash Test",
            description="Testing hash consistency",
            sequence_order=35,
        )

        plot2 = PlotPoint(
            plot_point_id="hash-test",
            plot_point_type=PlotPointType.TURNING_POINT,
            importance=PlotPointImportance.MAJOR,
            title="Hash Test",
            description="Testing hash consistency",
            sequence_order=35,
        )

        # Equal objects should have equal hashes
        assert plot1 == plot2
        assert hash(plot1) == hash(plot2)

    @pytest.mark.unit
    def test_plot_points_in_set(self):
        """Test PlotPoint objects in set operations."""
        plot1 = PlotPoint(
            plot_point_id="set-test-1",
            plot_point_type=PlotPointType.TRIUMPH,
            importance=PlotPointImportance.MAJOR,
            title="Victory",
            description="Hero wins",
            sequence_order=80,
        )

        plot2 = PlotPoint(
            plot_point_id="set-test-2",
            plot_point_type=PlotPointType.SETBACK,
            importance=PlotPointImportance.MODERATE,
            title="Defeat",
            description="Hero loses",
            sequence_order=30,
        )

        # Identical plot point
        plot1_duplicate = PlotPoint(
            plot_point_id="set-test-1",
            plot_point_type=PlotPointType.TRIUMPH,
            importance=PlotPointImportance.MAJOR,
            title="Victory",
            description="Hero wins",
            sequence_order=80,
        )

        plot_set = {plot1, plot2, plot1_duplicate}

        # Set should deduplicate identical objects
        assert len(plot_set) == 2  # plot1 and plot1_duplicate are the same
        assert plot1 in plot_set
        assert plot2 in plot_set
        assert plot1_duplicate in plot_set  # Should find plot1

    @pytest.mark.unit
    def test_plot_points_as_dict_keys(self):
        """Test using PlotPoint objects as dictionary keys."""
        plot1 = PlotPoint(
            plot_point_id="dict-key-1",
            plot_point_type=PlotPointType.CONFRONTATION,
            importance=PlotPointImportance.CRITICAL,
            title="Main Confrontation",
            description="Final showdown",
            sequence_order=85,
        )

        plot2 = PlotPoint(
            plot_point_id="dict-key-2",
            plot_point_type=PlotPointType.RECONCILIATION,
            importance=PlotPointImportance.MAJOR,
            title="Making Peace",
            description="Characters reconcile",
            sequence_order=95,
        )

        plot_dict = {plot1: "confrontation_data", plot2: "reconciliation_data"}

        assert plot_dict[plot1] == "confrontation_data"
        assert plot_dict[plot2] == "reconciliation_data"

        # Test with equivalent plot point
        equivalent_plot1 = PlotPoint(
            plot_point_id="dict-key-1",
            plot_point_type=PlotPointType.CONFRONTATION,
            importance=PlotPointImportance.CRITICAL,
            title="Main Confrontation",
            description="Final showdown",
            sequence_order=85,
        )

        # Should find the same entry
        assert plot_dict[equivalent_plot1] == "confrontation_data"
