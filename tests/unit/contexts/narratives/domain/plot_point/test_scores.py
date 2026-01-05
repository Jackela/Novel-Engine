#!/usr/bin/env python3
"""
PlotPoint Score Tests

Split from test_plot_point_value_object.py for maintainability.
"""

from decimal import Decimal

import pytest

from contexts.narratives.domain.value_objects.plot_point import (
    PlotPoint,
    PlotPointImportance,
    PlotPointType,
)


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
