#!/usr/bin/env python3
"""
Unit Tests for NarrativeTheme Score Calculations

Test suite covering thematic complexity score and narrative impact score
calculations for NarrativeTheme in the Narrative Context domain layer.
"""

from decimal import Decimal

import pytest

from src.contexts.narratives.domain.value_objects.narrative_theme import (
    NarrativeTheme,
    ThemeIntensity,
    ThemeType,
)

pytestmark = pytest.mark.unit


class TestThematicComplexityScore:
    """Test suite for thematic complexity score calculation."""

    @pytest.mark.unit
    def test_base_complexity_only(self):
        """Test complexity score with only moral complexity (no bonuses)."""
        theme = NarrativeTheme(
            theme_id="base-complexity-test",
            theme_type=ThemeType.UNIVERSAL,
            intensity=ThemeIntensity.MODERATE,
            name="Love",
            description="Simple love story",
            moral_complexity=Decimal("3.0"),
            # All expression methods false except defaults
            expressed_through_dialogue=False,
            expressed_through_action=False,
            expressed_through_symbolism=False,
            expressed_through_setting=False,
            expressed_through_character_arc=False,
        )

        # Expected: 3.0 + 0.0 + 0.0 = 3.0
        assert theme.thematic_complexity_score == Decimal("3.0")

    @pytest.mark.unit
    def test_complexity_with_expression_methods(self):
        """Test complexity score with multiple expression methods."""
        theme = NarrativeTheme(
            theme_id="expression-complexity-test",
            theme_type=ThemeType.MORAL,
            intensity=ThemeIntensity.PROMINENT,
            name="Justice",
            description="Complex moral questions",
            moral_complexity=Decimal("6.0"),
            expressed_through_dialogue=True,
            expressed_through_action=True,
            expressed_through_symbolism=True,
            expressed_through_setting=False,
            expressed_through_character_arc=True,
        )

        # Expected: 6.0 + (4 * 0.5) + 0.0 = 8.0
        assert theme.thematic_complexity_score == Decimal("8.0")

    @pytest.mark.unit
    def test_complexity_with_theme_relationships(self):
        """Test complexity score with thematic relationships."""
        theme = NarrativeTheme(
            theme_id="relationship-complexity-test",
            theme_type=ThemeType.PHILOSOPHICAL,
            intensity=ThemeIntensity.CENTRAL,
            name="Truth vs Illusion",
            description="Questions about reality and perception",
            moral_complexity=Decimal("7.0"),
            conflicts_with_themes={"comfort", "ignorance"},
            reinforces_themes={"wisdom", "growth", "awakening"},
            expressed_through_dialogue=False,
            expressed_through_action=False,
            expressed_through_symbolism=False,
            expressed_through_setting=False,
            expressed_through_character_arc=False,
        )

        # Expected: 7.0 + 0.0 + ((2 + 3) * 0.3) = 7.0 + 1.5 = 8.5
        assert theme.thematic_complexity_score == Decimal("8.5")

    @pytest.mark.unit
    def test_complexity_with_all_bonuses(self):
        """Test complexity score with all bonuses."""
        theme = NarrativeTheme(
            theme_id="max-complexity-test",
            theme_type=ThemeType.PSYCHOLOGICAL,
            intensity=ThemeIntensity.OVERWHELMING,
            name="Human Nature",
            description="Deep exploration of human psychology",
            moral_complexity=Decimal("8.0"),
            expressed_through_dialogue=True,
            expressed_through_action=True,
            expressed_through_symbolism=True,
            expressed_through_setting=True,
            expressed_through_character_arc=True,
            conflicts_with_themes={"simplicity", "naivety"},
            reinforces_themes={"depth", "nuance", "understanding"},
        )

        # Expected: 8.0 + (5 * 0.5) + ((2 + 3) * 0.3) = 8.0 + 2.5 + 1.5 = 12.0
        # But capped at 10.0
        assert theme.thematic_complexity_score == Decimal("10.0")

    @pytest.mark.unit
    def test_complexity_capping_at_ten(self):
        """Test that complexity score is capped at 10."""
        theme = NarrativeTheme(
            theme_id="capped-complexity-test",
            theme_type=ThemeType.SPIRITUAL,
            intensity=ThemeIntensity.CENTRAL,
            name="Divine Mystery",
            description="Unfathomable spiritual depths",
            moral_complexity=Decimal("9.0"),
            expressed_through_dialogue=True,
            expressed_through_action=True,
            expressed_through_symbolism=True,
            expressed_through_setting=True,
            expressed_through_character_arc=True,
            conflicts_with_themes={"materialism", "atheism", "cynicism"},
            reinforces_themes={"faith", "hope", "transcendence", "mystery", "awe"},
        )

        # Would be: 9.0 + (5 * 0.5) + ((3 + 5) * 0.3) = 9.0 + 2.5 + 2.4 = 13.9
        # But capped at 10.0
        assert theme.thematic_complexity_score == Decimal("10.0")


class TestNarrativeImpactScore:
    """Test suite for narrative impact score calculation."""

    @pytest.mark.unit
    def test_impact_score_subtle_intensity(self):
        """Test impact score calculation for SUBTLE intensity."""
        theme = NarrativeTheme(
            theme_id="subtle-impact-test",
            theme_type=ThemeType.ENVIRONMENTAL,
            intensity=ThemeIntensity.SUBTLE,
            name="Nature Connection",
            description="Subtle environmental undertones",
            moral_complexity=Decimal("4.0"),
            emotional_resonance=Decimal("6.0"),
            universal_appeal=Decimal("8.0"),
        )

        # Base score: (6.0 * 0.4) + (8.0 * 0.3) + (complexity_score * 0.3)
        # Complexity score would be 4.0 (base only)
        # Base score: 2.4 + 2.4 + 1.2 = 6.0
        # Final: 6.0 * 0.2 = 1.2
        expected_score = Decimal("1.2")
        assert theme.narrative_impact_score == expected_score

    @pytest.mark.unit
    def test_impact_score_central_intensity(self):
        """Test impact score calculation for CENTRAL intensity."""
        theme = NarrativeTheme(
            theme_id="central-impact-test",
            theme_type=ThemeType.UNIVERSAL,
            intensity=ThemeIntensity.CENTRAL,
            name="Love Conquers All",
            description="Central theme of transformative love",
            moral_complexity=Decimal("7.0"),
            emotional_resonance=Decimal("9.0"),
            universal_appeal=Decimal("10.0"),
        )

        # Base score: (9.0 * 0.4) + (10.0 * 0.3) + (7.0 * 0.3) = 3.6 + 3.0 + 2.1 = 8.7
        # Final: 8.7 * 0.8 = 6.96
        expected_score = Decimal("6.96")
        assert theme.narrative_impact_score == expected_score

    @pytest.mark.unit
    def test_impact_score_overwhelming_intensity(self):
        """Test impact score calculation for OVERWHELMING intensity."""
        theme = NarrativeTheme(
            theme_id="overwhelming-impact-test",
            theme_type=ThemeType.MORAL,
            intensity=ThemeIntensity.OVERWHELMING,
            name="Ultimate Sacrifice",
            description="Overwhelming theme of self-sacrifice",
            moral_complexity=Decimal("10.0"),
            emotional_resonance=Decimal("10.0"),
            universal_appeal=Decimal("9.0"),
            # Add some complexity bonuses
            expressed_through_dialogue=True,
            expressed_through_action=True,
            expressed_through_character_arc=True,
        )

        # Complexity score: 10.0 + (3 * 0.5) + 0.0 = 11.5, capped at 10.0
        # Base score: (10.0 * 0.4) + (9.0 * 0.3) + (10.0 * 0.3) = 4.0 + 2.7 + 3.0 = 9.7
        # Final: 9.7 * 1.0 = 9.7
        expected_score = Decimal("9.7")
        assert theme.narrative_impact_score == expected_score

    @pytest.mark.unit
    def test_impact_score_all_intensities(self):
        """Test impact score progression across intensity levels."""
        base_scores = []

        for intensity in ThemeIntensity:
            theme = NarrativeTheme(
                theme_id=f"intensity-{intensity.value}-test",
                theme_type=ThemeType.PSYCHOLOGICAL,
                intensity=intensity,
                name=f"{intensity.value.title()} Theme",
                description=f"Theme with {intensity.value} intensity",
                moral_complexity=Decimal("5.0"),
                emotional_resonance=Decimal("5.0"),
                universal_appeal=Decimal("5.0"),
            )

            base_scores.append((intensity, theme.narrative_impact_score))

        # Scores should generally increase with intensity
        subtle_score = next(
            score
            for intensity, score in base_scores
            if intensity == ThemeIntensity.SUBTLE
        )
        overwhelming_score = next(
            score
            for intensity, score in base_scores
            if intensity == ThemeIntensity.OVERWHELMING
        )

        assert overwhelming_score > subtle_score
