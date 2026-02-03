#!/usr/bin/env python3
"""
Unit Tests for NarrativeTheme Creation

Test suite covering NarrativeTheme object creation, initialization,
and default values in the Narrative Context domain layer.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.contexts.narratives.domain.value_objects.narrative_theme import (
    NarrativeTheme,
    ThemeIntensity,
    ThemeType,
)


class TestNarrativeThemeCreation:
    """Test suite for NarrativeTheme creation and initialization."""

    @pytest.mark.unit
    def test_create_minimal_narrative_theme(self):
        """Test creating narrative theme with minimal required fields."""
        theme = NarrativeTheme(
            theme_id="minimal-theme-1",
            theme_type=ThemeType.UNIVERSAL,
            intensity=ThemeIntensity.MODERATE,
            name="Love",
            description="The power of love to transform",
        )

        assert theme.theme_id == "minimal-theme-1"
        assert theme.theme_type == ThemeType.UNIVERSAL
        assert theme.intensity == ThemeIntensity.MODERATE
        assert theme.name == "Love"
        assert theme.description == "The power of love to transform"

    @pytest.mark.unit
    def test_create_comprehensive_narrative_theme(self):
        """Test creating narrative theme with all fields specified."""
        creation_time = datetime.now(timezone.utc)

        theme = NarrativeTheme(
            theme_id="comprehensive-theme",
            theme_type=ThemeType.MORAL,
            intensity=ThemeIntensity.CENTRAL,
            name="Redemption",
            description="The journey from darkness to light through sacrifice and growth",
            symbolic_elements={"light", "darkness", "phoenix"},
            related_motifs={"rebirth", "sacrifice", "transformation"},
            character_archetypes={"fallen_hero", "mentor", "sacrificial_lamb"},
            introduction_sequence=5,
            resolution_sequence=95,
            peak_intensity_sequence=75,
            development_trajectory="Gradual buildup to climactic realization",
            conflicts_with_themes={"vengeance", "nihilism"},
            reinforces_themes={"love", "forgiveness"},
            moral_complexity=Decimal("8.5"),
            emotional_resonance=Decimal("9.2"),
            universal_appeal=Decimal("9.8"),
            expressed_through_dialogue=True,
            expressed_through_action=True,
            expressed_through_symbolism=True,
            expressed_through_setting=False,
            expressed_through_character_arc=True,
            cultural_context="Western literary tradition",
            historical_context="Post-war redemption narratives",
            target_audience_relevance={
                "adults": Decimal("9.0"),
                "young_adults": Decimal("7.5"),
                "children": Decimal("4.0"),
            },
            tags={"classic", "universal", "christian_undertones"},
            creation_timestamp=creation_time,
            metadata={
                "author_intent": "explore human capacity for change",
                "influences": ["Dickens", "Hugo"],
            },
        )

        assert theme.theme_id == "comprehensive-theme"
        assert theme.theme_type == ThemeType.MORAL
        assert theme.intensity == ThemeIntensity.CENTRAL
        assert theme.symbolic_elements == {"light", "darkness", "phoenix"}
        assert theme.related_motifs == {"rebirth", "sacrifice", "transformation"}
        assert theme.character_archetypes == {
            "fallen_hero",
            "mentor",
            "sacrificial_lamb",
        }
        assert theme.introduction_sequence == 5
        assert theme.resolution_sequence == 95
        assert theme.peak_intensity_sequence == 75
        assert (
            theme.development_trajectory == "Gradual buildup to climactic realization"
        )
        assert theme.conflicts_with_themes == {"vengeance", "nihilism"}
        assert theme.reinforces_themes == {"love", "forgiveness"}
        assert theme.moral_complexity == Decimal("8.5")
        assert theme.emotional_resonance == Decimal("9.2")
        assert theme.universal_appeal == Decimal("9.8")
        assert theme.expressed_through_dialogue is True
        assert theme.expressed_through_symbolism is True
        assert theme.expressed_through_setting is False
        assert theme.cultural_context == "Western literary tradition"
        assert theme.target_audience_relevance["adults"] == Decimal("9.0")
        assert theme.tags == {"classic", "universal", "christian_undertones"}
        assert theme.creation_timestamp == creation_time
        assert theme.metadata["author_intent"] == "explore human capacity for change"

    @pytest.mark.unit
    def test_default_values_initialization(self):
        """Test that default values are properly initialized."""
        theme = NarrativeTheme(
            theme_id="default-test",
            theme_type=ThemeType.PSYCHOLOGICAL,
            intensity=ThemeIntensity.SUBTLE,
            name="Identity Crisis",
            description="Questions about self and purpose",
        )

        # Test default collections are empty
        assert theme.symbolic_elements == set()
        assert theme.related_motifs == set()
        assert theme.character_archetypes == set()
        assert theme.conflicts_with_themes == set()
        assert theme.reinforces_themes == set()
        assert theme.target_audience_relevance == {}
        assert theme.tags == set()
        assert theme.metadata == {}

        # Test default values
        assert theme.introduction_sequence is None
        assert theme.resolution_sequence is None
        assert theme.peak_intensity_sequence is None
        assert theme.development_trajectory == ""
        assert theme.moral_complexity == Decimal("5.0")
        assert theme.emotional_resonance == Decimal("5.0")
        assert theme.universal_appeal == Decimal("5.0")
        assert theme.expressed_through_dialogue is False
        assert theme.expressed_through_action is True
        assert theme.expressed_through_symbolism is False
        assert theme.expressed_through_setting is False
        assert theme.expressed_through_character_arc is True
        assert theme.cultural_context is None
        assert theme.historical_context is None

        # Test that creation timestamp was set
        assert theme.creation_timestamp is not None
        assert isinstance(theme.creation_timestamp, datetime)

    @pytest.mark.unit
    def test_frozen_dataclass_immutability(self):
        """Test that NarrativeTheme is immutable (frozen dataclass)."""
        theme = NarrativeTheme(
            theme_id="immutable-test",
            theme_type=ThemeType.SOCIAL,
            intensity=ThemeIntensity.PROMINENT,
            name="Justice",
            description="The struggle for fairness and equality",
        )

        # Should not be able to modify fields
        with pytest.raises(AttributeError):
            theme.name = "Modified Name"

        with pytest.raises(AttributeError):
            theme.intensity = ThemeIntensity.CENTRAL

        with pytest.raises(AttributeError):
            theme.moral_complexity = Decimal("8.0")
