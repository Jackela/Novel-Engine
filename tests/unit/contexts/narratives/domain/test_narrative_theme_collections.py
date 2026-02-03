#!/usr/bin/env python3
"""
Unit Tests for NarrativeTheme Collections and Comparison

Test suite covering NarrativeTheme behavior in collections,
sorting, equality, hashing, and comparison operations.
"""

from decimal import Decimal

import pytest

from src.contexts.narratives.domain.value_objects.narrative_theme import (
    NarrativeTheme,
    ThemeIntensity,
    ThemeType,
)


class TestNarrativeThemeCollectionsAndComparison:
    """Test suite for NarrativeTheme behavior in collections and comparisons."""

    @pytest.mark.unit
    def test_themes_in_list(self):
        """Test NarrativeTheme objects in list operations."""
        theme1 = NarrativeTheme(
            theme_id="list-test-1",
            theme_type=ThemeType.UNIVERSAL,
            intensity=ThemeIntensity.CENTRAL,
            name="Love",
            description="The power of love",
        )

        theme2 = NarrativeTheme(
            theme_id="list-test-2",
            theme_type=ThemeType.MORAL,
            intensity=ThemeIntensity.PROMINENT,
            name="Justice",
            description="The pursuit of justice",
        )

        theme_list = [theme1, theme2]

        assert len(theme_list) == 2
        assert theme1 in theme_list
        assert theme2 in theme_list

    @pytest.mark.unit
    def test_themes_sorting_by_impact_score(self):
        """Test sorting NarrativeTheme objects by narrative impact score."""
        themes = [
            NarrativeTheme(
                theme_id=f"sort-test-{i}",
                theme_type=ThemeType.PSYCHOLOGICAL,
                intensity=intensity,
                name=f"Theme {i}",
                description=f"Theme number {i}",
                moral_complexity=Decimal(str(complexity)),
                emotional_resonance=Decimal(str(resonance)),
                universal_appeal=Decimal(str(appeal)),
            )
            for i, (intensity, complexity, resonance, appeal) in enumerate(
                [
                    (ThemeIntensity.SUBTLE, 3.0, 4.0, 5.0),
                    (ThemeIntensity.OVERWHELMING, 9.0, 10.0, 9.5),
                    (ThemeIntensity.MODERATE, 5.0, 6.0, 7.0),
                    (ThemeIntensity.CENTRAL, 8.0, 9.0, 8.5),
                ]
            )
        ]

        sorted_themes = sorted(
            themes, key=lambda t: t.narrative_impact_score, reverse=True
        )

        # OVERWHELMING should be first (highest impact)
        assert sorted_themes[0].intensity == ThemeIntensity.OVERWHELMING
        # SUBTLE should be last (lowest impact)
        assert sorted_themes[-1].intensity == ThemeIntensity.SUBTLE

    @pytest.mark.unit
    def test_theme_equality_identity(self):
        """Test that identical NarrativeTheme objects are considered equal."""
        theme1 = NarrativeTheme(
            theme_id="equality-test",
            theme_type=ThemeType.FAMILY,
            intensity=ThemeIntensity.PROMINENT,
            name="Family Bonds",
            description="The strength of family connections",
        )

        theme2 = NarrativeTheme(
            theme_id="equality-test",
            theme_type=ThemeType.FAMILY,
            intensity=ThemeIntensity.PROMINENT,
            name="Family Bonds",
            description="The strength of family connections",
        )

        # Frozen dataclasses with same values should be equal
        assert theme1 == theme2
        # But they should be different objects
        assert theme1 is not theme2

    @pytest.mark.unit
    def test_theme_inequality(self):
        """Test that different NarrativeTheme objects are not equal."""
        theme1 = NarrativeTheme(
            theme_id="different-1",
            theme_type=ThemeType.SPIRITUAL,
            intensity=ThemeIntensity.CENTRAL,
            name="Faith",
            description="Religious faith and belief",
        )

        theme2 = NarrativeTheme(
            theme_id="different-2",
            theme_type=ThemeType.SPIRITUAL,
            intensity=ThemeIntensity.CENTRAL,
            name="Doubt",
            description="Questioning faith and belief",
        )

        assert theme1 != theme2

    @pytest.mark.unit
    def test_theme_hashing_consistency(self):
        """Test that equal NarrativeTheme objects have same hash."""
        theme1 = NarrativeTheme(
            theme_id="hash-test",
            theme_type=ThemeType.TECHNOLOGICAL,
            intensity=ThemeIntensity.OVERWHELMING,
            name="Digital Revolution",
            description="Technology transforming society",
        )

        theme2 = NarrativeTheme(
            theme_id="hash-test",
            theme_type=ThemeType.TECHNOLOGICAL,
            intensity=ThemeIntensity.OVERWHELMING,
            name="Digital Revolution",
            description="Technology transforming society",
        )

        # Equal objects should have equal hashes
        assert theme1 == theme2
        assert hash(theme1) == hash(theme2)

    @pytest.mark.unit
    def test_themes_in_set(self):
        """Test NarrativeTheme objects in set operations."""
        theme1 = NarrativeTheme(
            theme_id="set-test-1",
            theme_type=ThemeType.ENVIRONMENTAL,
            intensity=ThemeIntensity.CENTRAL,
            name="Nature's Balance",
            description="Harmony between humans and nature",
        )

        theme2 = NarrativeTheme(
            theme_id="set-test-2",
            theme_type=ThemeType.POLITICAL,
            intensity=ThemeIntensity.PROMINENT,
            name="Power Struggle",
            description="Competition for political control",
        )

        # Identical theme
        theme1_duplicate = NarrativeTheme(
            theme_id="set-test-1",
            theme_type=ThemeType.ENVIRONMENTAL,
            intensity=ThemeIntensity.CENTRAL,
            name="Nature's Balance",
            description="Harmony between humans and nature",
        )

        theme_set = {theme1, theme2, theme1_duplicate}

        # Set should deduplicate identical objects
        assert len(theme_set) == 2  # theme1 and theme1_duplicate are the same
        assert theme1 in theme_set
        assert theme2 in theme_set
        assert theme1_duplicate in theme_set  # Should find theme1

    @pytest.mark.unit
    def test_themes_as_dict_keys(self):
        """Test using NarrativeTheme objects as dictionary keys."""
        theme1 = NarrativeTheme(
            theme_id="dict-key-1",
            theme_type=ThemeType.COMING_OF_AGE,
            intensity=ThemeIntensity.CENTRAL,
            name="Loss of Innocence",
            description="The painful journey to maturity",
        )

        theme2 = NarrativeTheme(
            theme_id="dict-key-2",
            theme_type=ThemeType.UNIVERSAL,
            intensity=ThemeIntensity.PROMINENT,
            name="Redemption",
            description="Second chances and forgiveness",
        )

        theme_dict = {theme1: "coming_of_age_data", theme2: "redemption_data"}

        assert theme_dict[theme1] == "coming_of_age_data"
        assert theme_dict[theme2] == "redemption_data"

        # Test with equivalent theme
        equivalent_theme1 = NarrativeTheme(
            theme_id="dict-key-1",
            theme_type=ThemeType.COMING_OF_AGE,
            intensity=ThemeIntensity.CENTRAL,
            name="Loss of Innocence",
            description="The painful journey to maturity",
        )

        # Should find the same entry
        assert theme_dict[equivalent_theme1] == "coming_of_age_data"
