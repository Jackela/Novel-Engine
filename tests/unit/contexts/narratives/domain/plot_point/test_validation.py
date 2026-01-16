#!/usr/bin/env python3
"""
PlotPoint Validation Tests

Split from test_plot_point_value_object.py for maintainability.
"""

from decimal import Decimal

import pytest

from src.contexts.narratives.domain.value_objects.plot_point import (
    PlotPoint,
    PlotPointImportance,
    PlotPointType,
)


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
