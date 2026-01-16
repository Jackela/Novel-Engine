#!/usr/bin/env python3
"""
PlotPoint Enum Tests

Split from test_plot_point_value_object.py for maintainability.
"""


import pytest

from src.contexts.narratives.domain.value_objects.plot_point import (
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
