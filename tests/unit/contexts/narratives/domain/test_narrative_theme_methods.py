#!/usr/bin/env python3
"""
Unit Tests for NarrativeTheme Instance Methods

Test suite covering instance methods and behavioral logic
for NarrativeTheme in the Narrative Context domain layer.
"""

from decimal import Decimal

import pytest

from src.contexts.narratives.domain.value_objects.narrative_theme import (
    NarrativeTheme,
    ThemeIntensity,
    ThemeType,
)

pytestmark = pytest.mark.unit


class TestNarrativeThemeInstanceMethods:
    """Test suite for NarrativeTheme instance methods."""

    @pytest.mark.unit
    def test_conflicts_with_theme_true(self):
        """Test conflicts_with_theme returns True for conflicting theme."""
        theme = NarrativeTheme(
            theme_id="conflict-test",
            theme_type=ThemeType.MORAL,
            intensity=ThemeIntensity.CENTRAL,
            name="Hope",
            description="The power of hope in dark times",
            conflicts_with_themes={"despair", "nihilism", "cynicism"},
        )

        assert theme.conflicts_with_theme("despair") is True
        assert theme.conflicts_with_theme("nihilism") is True
        assert theme.conflicts_with_theme("optimism") is False

    @pytest.mark.unit
    def test_reinforces_theme_true(self):
        """Test reinforces_theme returns True for reinforcing theme."""
        theme = NarrativeTheme(
            theme_id="reinforce-test",
            theme_type=ThemeType.FAMILY,
            intensity=ThemeIntensity.PROMINENT,
            name="Family Bonds",
            description="The strength of family connections",
            reinforces_themes={"love", "loyalty", "sacrifice", "belonging"},
        )

        assert theme.reinforces_theme("love") is True
        assert theme.reinforces_theme("loyalty") is True
        assert theme.reinforces_theme("hatred") is False

    @pytest.mark.unit
    def test_has_symbolic_element_true(self):
        """Test has_symbolic_element returns True for existing symbol."""
        theme = NarrativeTheme(
            theme_id="symbol-test",
            theme_type=ThemeType.SPIRITUAL,
            intensity=ThemeIntensity.CENTRAL,
            name="Divine Grace",
            description="God's presence in human life",
            symbolic_elements={"light", "dove", "cross", "water"},
        )

        assert theme.has_symbolic_element("light") is True
        assert theme.has_symbolic_element("dove") is True
        assert theme.has_symbolic_element("darkness") is False

    @pytest.mark.unit
    def test_has_related_motif_true(self):
        """Test has_related_motif returns True for existing motif."""
        theme = NarrativeTheme(
            theme_id="motif-test",
            theme_type=ThemeType.COMING_OF_AGE,
            intensity=ThemeIntensity.PROMINENT,
            name="Loss of Innocence",
            description="The painful journey to maturity",
            related_motifs={"fallen_eden", "first_betrayal", "mentor_death"},
        )

        assert theme.has_related_motif("fallen_eden") is True
        assert theme.has_related_motif("mentor_death") is True
        assert theme.has_related_motif("happy_ending") is False

    @pytest.mark.unit
    def test_uses_archetype_true(self):
        """Test uses_archetype returns True for existing archetype."""
        theme = NarrativeTheme(
            theme_id="archetype-test",
            theme_type=ThemeType.UNIVERSAL,
            intensity=ThemeIntensity.CENTRAL,
            name="Hero's Journey",
            description="The classic monomyth structure",
            character_archetypes={
                "hero",
                "mentor",
                "shadow",
                "shapeshifter",
                "threshold_guardian",
            },
        )

        assert theme.uses_archetype("hero") is True
        assert theme.uses_archetype("shadow") is True
        assert theme.uses_archetype("villain") is False

    @pytest.mark.unit
    def test_get_audience_relevance_existing(self):
        """Test get_audience_relevance returns correct value for existing audience."""
        theme = NarrativeTheme(
            theme_id="audience-test",
            theme_type=ThemeType.TECHNOLOGICAL,
            intensity=ThemeIntensity.OVERWHELMING,
            name="AI Ethics",
            description="Moral implications of artificial intelligence",
            target_audience_relevance={
                "tech_workers": Decimal("9.5"),
                "philosophers": Decimal("8.0"),
                "general_public": Decimal("6.0"),
            },
        )

        assert theme.get_audience_relevance("tech_workers") == Decimal("9.5")
        assert theme.get_audience_relevance("philosophers") == Decimal("8.0")
        assert theme.get_audience_relevance("general_public") == Decimal("6.0")

    @pytest.mark.unit
    def test_get_audience_relevance_default(self):
        """Test get_audience_relevance returns default value for non-existing audience."""
        theme = NarrativeTheme(
            theme_id="default-audience-test",
            theme_type=ThemeType.CULTURAL,
            intensity=ThemeIntensity.MODERATE,
            name="Heritage",
            description="Cultural identity and traditions",
            target_audience_relevance={"local_community": Decimal("8.0")},
        )

        # Should return default 5.0 for non-existing audience
        assert theme.get_audience_relevance("international") == Decimal("5.0")
        assert theme.get_audience_relevance("local_community") == Decimal("8.0")

    @pytest.mark.unit
    def test_get_thematic_context(self):
        """Test get_thematic_context returns comprehensive context dict."""
        theme = NarrativeTheme(
            theme_id="context-test",
            theme_type=ThemeType.PHILOSOPHICAL,
            intensity=ThemeIntensity.CENTRAL,
            name="Truth and Lies",
            description="The nature of truth and deception",
            introduction_sequence=10,
            resolution_sequence=90,
            symbolic_elements={"mirror", "mask"},
            related_motifs={"hidden_truth", "false_appearance"},
            character_archetypes={"truth_seeker", "deceiver"},
            conflicts_with_themes={"ignorance"},
            reinforces_themes={"wisdom", "enlightenment"},
            expressed_through_dialogue=True,
            expressed_through_action=False,
            expressed_through_symbolism=True,
            expressed_through_setting=False,
            expressed_through_character_arc=True,
        )

        context = theme.get_thematic_context()

        assert context["theme_id"] == "context-test"
        assert context["type"] == "philosophical"
        assert context["intensity"] == "central"
        assert context["name"] == "Truth and Lies"
        assert context["is_major"] is True
        assert context["is_central"] is True
        assert isinstance(context["complexity_score"], float)
        assert isinstance(context["impact_score"], float)
        assert context["spans_full_narrative"] is True
        assert context["has_symbolic_representation"] is True

        # Check expression methods dict
        assert context["expression_methods"]["dialogue"] is True
        assert context["expression_methods"]["symbolism"] is True
        assert context["expression_methods"]["character_arc"] is True
        assert context["expression_methods"]["action"] is False
        assert context["expression_methods"]["setting"] is False

        # Check relationship counts
        assert context["relationship_counts"]["conflicts"] == 1
        assert context["relationship_counts"]["reinforces"] == 2
        assert context["relationship_counts"]["symbolic_elements"] == 2
        assert context["relationship_counts"]["motifs"] == 2
        assert context["relationship_counts"]["archetypes"] == 2
