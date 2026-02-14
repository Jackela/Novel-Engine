#!/usr/bin/env python3
"""
Unit Tests for NarrativeTheme Properties

Test suite covering computed properties and state checks
for NarrativeTheme in the Narrative Context domain layer.
"""

import pytest

from src.contexts.narratives.domain.value_objects.narrative_theme import (
    NarrativeTheme,
    ThemeIntensity,
    ThemeType,
)

pytestmark = pytest.mark.unit


class TestNarrativeThemeProperties:
    """Test suite for NarrativeTheme property methods."""

    @pytest.mark.unit
    def test_is_major_theme_for_major_intensities(self):
        """Test is_major_theme returns True for major intensity levels."""
        major_intensities = [
            ThemeIntensity.PROMINENT,
            ThemeIntensity.CENTRAL,
            ThemeIntensity.OVERWHELMING,
        ]

        for intensity in major_intensities:
            theme = NarrativeTheme(
                theme_id=f"major-{intensity.value}",
                theme_type=ThemeType.UNIVERSAL,
                intensity=intensity,
                name=f"Major {intensity.value} Theme",
                description=f"Testing {intensity.value} intensity",
            )

            assert theme.is_major_theme is True

    @pytest.mark.unit
    def test_is_major_theme_false_for_minor_intensities(self):
        """Test is_major_theme returns False for minor intensity levels."""
        minor_intensities = [ThemeIntensity.SUBTLE, ThemeIntensity.MODERATE]

        for intensity in minor_intensities:
            theme = NarrativeTheme(
                theme_id=f"minor-{intensity.value}",
                theme_type=ThemeType.SOCIAL,
                intensity=intensity,
                name=f"Minor {intensity.value} Theme",
                description=f"Testing {intensity.value} intensity",
            )

            assert theme.is_major_theme is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_is_central_theme_true_for_central(self):
        """Test is_central_theme returns True only for CENTRAL intensity."""
        theme = NarrativeTheme(
            theme_id="central-test",
            theme_type=ThemeType.PHILOSOPHICAL,
            intensity=ThemeIntensity.CENTRAL,
            name="Central Theme",
            description="The core theme of the story",
        )

        assert theme.is_central_theme is True

    @pytest.mark.unit
    def test_is_central_theme_false_for_non_central(self):
        """Test is_central_theme returns False for non-CENTRAL intensities."""
        non_central_intensities = [
            ThemeIntensity.SUBTLE,
            ThemeIntensity.MODERATE,
            ThemeIntensity.PROMINENT,
            ThemeIntensity.OVERWHELMING,
        ]

        for intensity in non_central_intensities:
            theme = NarrativeTheme(
                theme_id=f"non-central-{intensity.value}",
                theme_type=ThemeType.PSYCHOLOGICAL,
                intensity=intensity,
                name=f"Non-central {intensity.value}",
                description=f"Testing {intensity.value}",
            )

            assert theme.is_central_theme is False

    @pytest.mark.unit
    def test_has_symbolic_representation_with_elements(self):
        """Test has_symbolic_representation with symbolic elements."""
        theme = NarrativeTheme(
            theme_id="symbolic-elements-test",
            theme_type=ThemeType.SPIRITUAL,
            intensity=ThemeIntensity.PROMINENT,
            name="Divine Light",
            description="Spiritual illumination",
            symbolic_elements={"light", "dove", "cross"},
            expressed_through_symbolism=False,
        )

        assert theme.has_symbolic_representation is True

    @pytest.mark.unit
    def test_has_symbolic_representation_with_flag(self):
        """Test has_symbolic_representation with expressed_through_symbolism flag."""
        theme = NarrativeTheme(
            theme_id="symbolic-flag-test",
            theme_type=ThemeType.MORAL,
            intensity=ThemeIntensity.CENTRAL,
            name="Good vs Evil",
            description="Moral conflict",
            symbolic_elements=set(),
            expressed_through_symbolism=True,
        )

        assert theme.has_symbolic_representation is True

    @pytest.mark.unit
    def test_has_symbolic_representation_false(self):
        """Test has_symbolic_representation returns False when neither condition met."""
        theme = NarrativeTheme(
            theme_id="no-symbolic-test",
            theme_type=ThemeType.TECHNOLOGICAL,
            intensity=ThemeIntensity.MODERATE,
            name="Progress",
            description="Technological advancement",
            symbolic_elements=set(),
            expressed_through_symbolism=False,
        )

        assert theme.has_symbolic_representation is False

    @pytest.mark.unit
    def test_has_character_expression_with_arc_flag(self):
        """Test has_character_expression with character arc expression."""
        theme = NarrativeTheme(
            theme_id="char-arc-test",
            theme_type=ThemeType.COMING_OF_AGE,
            intensity=ThemeIntensity.CENTRAL,
            name="Maturity",
            description="Growing up and taking responsibility",
            character_archetypes=set(),
            expressed_through_character_arc=True,
        )

        assert theme.has_character_expression is True

    @pytest.mark.unit
    def test_has_character_expression_with_archetypes(self):
        """Test has_character_expression with character archetypes."""
        theme = NarrativeTheme(
            theme_id="archetypes-test",
            theme_type=ThemeType.UNIVERSAL,
            intensity=ThemeIntensity.PROMINENT,
            name="Hero's Journey",
            description="Classic hero narrative",
            character_archetypes={"hero", "mentor", "shadow"},
            expressed_through_character_arc=False,
        )

        assert theme.has_character_expression is True

    @pytest.mark.unit
    def test_has_character_expression_false(self):
        """Test has_character_expression returns False when neither condition met."""
        theme = NarrativeTheme(
            theme_id="no-char-expression-test",
            theme_type=ThemeType.ENVIRONMENTAL,
            intensity=ThemeIntensity.SUBTLE,
            name="Nature",
            description="Environmental themes",
            character_archetypes=set(),
            expressed_through_character_arc=False,
        )

        assert theme.has_character_expression is False

    @pytest.mark.unit
    def test_spans_full_narrative_true(self):
        """Test spans_full_narrative returns True when both sequences are set."""
        theme = NarrativeTheme(
            theme_id="full-span-test",
            theme_type=ThemeType.FAMILY,
            intensity=ThemeIntensity.CENTRAL,
            name="Legacy",
            description="Family heritage through generations",
            introduction_sequence=1,
            resolution_sequence=100,
        )

        assert theme.spans_full_narrative is True

    @pytest.mark.unit
    def test_spans_full_narrative_false_missing_intro(self):
        """Test spans_full_narrative returns False when introduction sequence is None."""
        theme = NarrativeTheme(
            theme_id="no-intro-test",
            theme_type=ThemeType.POLITICAL,
            intensity=ThemeIntensity.PROMINENT,
            name="Revolution",
            description="Political uprising",
            introduction_sequence=None,
            resolution_sequence=90,
        )

        assert theme.spans_full_narrative is False

    @pytest.mark.unit
    def test_spans_full_narrative_false_missing_resolution(self):
        """Test spans_full_narrative returns False when resolution sequence is None."""
        theme = NarrativeTheme(
            theme_id="no-resolution-test",
            theme_type=ThemeType.PSYCHOLOGICAL,
            intensity=ThemeIntensity.MODERATE,
            name="Identity",
            description="Self-discovery journey",
            introduction_sequence=10,
            resolution_sequence=None,
        )

        assert theme.spans_full_narrative is False

    @pytest.mark.unit
    def test_spans_full_narrative_false_both_none(self):
        """Test spans_full_narrative returns False when both sequences are None."""
        theme = NarrativeTheme(
            theme_id="no-sequences-test",
            theme_type=ThemeType.CULTURAL,
            intensity=ThemeIntensity.SUBTLE,
            name="Tradition",
            description="Cultural values",
            introduction_sequence=None,
            resolution_sequence=None,
        )

        assert theme.spans_full_narrative is False
