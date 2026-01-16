#!/usr/bin/env python3
"""
PlotPoint Instance Method Tests

Split from test_plot_point_value_object.py for maintainability.
"""

from uuid import uuid4

import pytest

from src.contexts.narratives.domain.value_objects.plot_point import (
    PlotPoint,
    PlotPointImportance,
    PlotPointType,
)


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
