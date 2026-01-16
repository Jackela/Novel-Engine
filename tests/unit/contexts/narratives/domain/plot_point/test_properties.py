#!/usr/bin/env python3
"""
PlotPoint Properties Tests

Split from test_plot_point_value_object.py for maintainability.
"""

from uuid import uuid4

import pytest

from src.contexts.narratives.domain.value_objects.plot_point import (
    PlotPoint,
    PlotPointImportance,
    PlotPointType,
)


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
