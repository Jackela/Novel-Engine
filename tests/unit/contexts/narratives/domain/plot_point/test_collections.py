#!/usr/bin/env python3
"""
PlotPoint Collections Tests

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
