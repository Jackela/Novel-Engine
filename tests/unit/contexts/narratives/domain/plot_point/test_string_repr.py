#!/usr/bin/env python3
"""
PlotPoint String Representation Tests

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



class TestPlotPointStringRepresentation:
    """Test suite for PlotPoint string representation methods."""

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


