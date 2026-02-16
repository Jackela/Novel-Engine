#!/usr/bin/env python3
"""
Unit Tests for NarrativeTheme String Representation

Test suite covering __str__ and __repr__ methods
for NarrativeTheme in the Narrative Context domain layer.
"""

import pytest

from src.contexts.narratives.domain.value_objects.narrative_theme import (
    NarrativeTheme,
    ThemeIntensity,
    ThemeType,
)

pytestmark = pytest.mark.unit


class TestNarrativeThemeStringRepresentation:
    """Test suite for NarrativeTheme string representation methods."""

    @pytest.mark.unit
    def test_str_representation(self):
        """Test human-readable string representation."""
        theme = NarrativeTheme(
            theme_id="str-test",
            theme_type=ThemeType.COMING_OF_AGE,
            intensity=ThemeIntensity.CENTRAL,
            name="Growing Up",
            description="The journey from childhood to adulthood",
        )

        str_repr = str(theme)
        expected = "NarrativeTheme('Growing Up', coming_of_age, central)"
        assert str_repr == expected

    @pytest.mark.unit
    def test_repr_representation(self):
        """Test developer representation for debugging."""
        theme = NarrativeTheme(
            theme_id="repr-test-id",
            theme_type=ThemeType.TECHNOLOGICAL,
            intensity=ThemeIntensity.OVERWHELMING,
            name="AI Singularity",
            description="The moment AI surpasses human intelligence",
        )

        repr_str = repr(theme)
        expected = (
            "NarrativeTheme(id='repr-test-id', "
            "type=technological, "
            "intensity=overwhelming, "
            "name='AI Singularity')"
        )
        assert repr_str == expected

    @pytest.mark.unit
    def test_string_representations_different(self):
        """Test that str and repr provide different information."""
        theme = NarrativeTheme(
            theme_id="different-repr-test",
            theme_type=ThemeType.SPIRITUAL,
            intensity=ThemeIntensity.PROMINENT,
            name="Divine Purpose",
            description="Finding one's calling in life",
        )

        str_repr = str(theme)
        repr_str = repr(theme)

        # They should be different
        assert str_repr != repr_str
        # str should be more human-readable
        assert "Divine Purpose" in str_repr
        # repr should include more technical details
        assert "different-repr-test" in repr_str
        assert "spiritual" in repr_str
