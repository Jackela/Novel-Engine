#!/usr/bin/env python3
"""
PlotPoint Factory Method Tests

Split from test_plot_point_value_object.py for maintainability.
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from contexts.narratives.domain.value_objects.plot_point import (
    PlotPoint,
    PlotPointImportance,
    PlotPointType,
)


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
