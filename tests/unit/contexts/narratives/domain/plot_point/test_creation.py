#!/usr/bin/env python3
"""
PlotPoint Creation Tests

Split from test_plot_point_value_object.py for maintainability.
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



class TestPlotPointCreation:
    """Test suite for PlotPoint creation and initialization."""

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


