#!/usr/bin/env python3
"""
Unit Tests for NarrativeTheme Factory Methods

Test suite covering factory methods for creating modified copies
of NarrativeTheme in the Narrative Context domain layer.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.contexts.narratives.domain.value_objects.narrative_theme import (
    NarrativeTheme,
    ThemeIntensity,
    ThemeType,
)


class TestNarrativeThemeFactoryMethods:
    """Test suite for NarrativeTheme factory methods."""

    @pytest.mark.unit
    def test_with_updated_intensity_change_intensity(self):
        """Test updating theme intensity."""
        original = NarrativeTheme(
            theme_id="intensity-update-test",
            theme_type=ThemeType.SOCIAL,
            intensity=ThemeIntensity.MODERATE,
            name="Social Justice",
            description="Fighting for equality and fairness",
            symbolic_elements={"scales", "torch"},
            moral_complexity=Decimal("7.0"),
        )

        updated = original.with_updated_intensity(ThemeIntensity.CENTRAL)

        # Intensity should change
        assert updated.intensity == ThemeIntensity.CENTRAL
        # All other fields should remain the same
        assert updated.theme_id == original.theme_id
        assert updated.theme_type == original.theme_type
        assert updated.name == original.name
        assert updated.description == original.description
        assert updated.symbolic_elements == original.symbolic_elements
        assert updated.moral_complexity == original.moral_complexity

    @pytest.mark.unit
    def test_with_updated_intensity_immutability(self):
        """Test that original theme remains unchanged."""
        original = NarrativeTheme(
            theme_id="immutable-test",
            theme_type=ThemeType.UNIVERSAL,
            intensity=ThemeIntensity.SUBTLE,
            name="Love",
            description="Universal theme of love",
        )

        updated = original.with_updated_intensity(ThemeIntensity.OVERWHELMING)

        # Original should remain unchanged
        assert original.intensity == ThemeIntensity.SUBTLE
        # Updated should have new intensity
        assert updated.intensity == ThemeIntensity.OVERWHELMING
        # They should be different objects
        assert original is not updated

    @pytest.mark.unit
    def test_with_updated_intensity_collections_copied(self):
        """Test that collections are properly copied in new instance."""
        original = NarrativeTheme(
            theme_id="collection-copy-test",
            theme_type=ThemeType.MORAL,
            intensity=ThemeIntensity.PROMINENT,
            name="Redemption",
            description="Second chances and forgiveness",
            symbolic_elements={"phoenix", "dawn"},
            conflicts_with_themes={"vengeance"},
            reinforces_themes={"forgiveness", "love"},
            tags={"classic", "universal"},
        )

        updated = original.with_updated_intensity(ThemeIntensity.CENTRAL)

        # Verify collections have correct values (identity not checked for immutable frozensets)
        assert updated.symbolic_elements == original.symbolic_elements
        assert updated.conflicts_with_themes == original.conflicts_with_themes
        assert updated.reinforces_themes == original.reinforces_themes
        assert updated.tags == original.tags

    @pytest.mark.unit
    def test_with_updated_intensity_preserves_metadata(self):
        """Test that metadata and timestamps are preserved."""
        creation_time = datetime.now(timezone.utc)
        metadata = {"version": 2, "author": "test"}

        original = NarrativeTheme(
            theme_id="metadata-test",
            theme_type=ThemeType.PSYCHOLOGICAL,
            intensity=ThemeIntensity.MODERATE,
            name="Inner Conflict",
            description="Battle within the psyche",
            creation_timestamp=creation_time,
            metadata=metadata,
        )

        updated = original.with_updated_intensity(ThemeIntensity.PROMINENT)

        # Timestamp should be preserved
        assert updated.creation_timestamp == creation_time
        # Metadata should be copied
        assert updated.metadata == metadata
        assert updated.metadata is not original.metadata
