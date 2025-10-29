#!/usr/bin/env python3
"""
Comprehensive Unit Tests for NarrativeTheme Value Objects

Test suite covering narrative theme creation, validation, business logic,
enums, properties, score calculations, and factory methods in the Narrative Context domain layer.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from contexts.narratives.domain.value_objects.narrative_theme import (
    NarrativeTheme,
    ThemeIntensity,
    ThemeType,
)


class TestThemeTypeEnum:
    """Test suite for ThemeType enum."""

    def test_all_theme_types_exist(self):
        """Test that all expected theme types are defined."""
        expected_types = {
            "UNIVERSAL",
            "SOCIAL",
            "PHILOSOPHICAL",
            "PSYCHOLOGICAL",
            "CULTURAL",
            "MORAL",
            "POLITICAL",
            "SPIRITUAL",
            "ENVIRONMENTAL",
            "TECHNOLOGICAL",
            "FAMILY",
            "COMING_OF_AGE",
        }

        actual_types = {item.name for item in ThemeType}
        assert actual_types == expected_types

    def test_theme_type_string_values(self):
        """Test that theme type enum values have correct string representations."""
        assert ThemeType.UNIVERSAL.value == "universal"
        assert ThemeType.SOCIAL.value == "social"
        assert ThemeType.PHILOSOPHICAL.value == "philosophical"
        assert ThemeType.PSYCHOLOGICAL.value == "psychological"
        assert ThemeType.CULTURAL.value == "cultural"
        assert ThemeType.MORAL.value == "moral"
        assert ThemeType.POLITICAL.value == "political"
        assert ThemeType.SPIRITUAL.value == "spiritual"
        assert ThemeType.ENVIRONMENTAL.value == "environmental"
        assert ThemeType.TECHNOLOGICAL.value == "technological"
        assert ThemeType.FAMILY.value == "family"
        assert ThemeType.COMING_OF_AGE.value == "coming_of_age"

    def test_theme_type_uniqueness(self):
        """Test that all theme type values are unique."""
        values = [item.value for item in ThemeType]
        assert len(values) == len(set(values))

    def test_theme_type_membership(self):
        """Test theme type membership operations."""
        assert ThemeType.MORAL in ThemeType
        assert "moral" == ThemeType.MORAL.value
        assert ThemeType.MORAL == ThemeType("moral")


class TestThemeIntensityEnum:
    """Test suite for ThemeIntensity enum."""

    def test_all_intensity_levels_exist(self):
        """Test that all expected intensity levels are defined."""
        expected_levels = {"SUBTLE", "MODERATE", "PROMINENT", "CENTRAL", "OVERWHELMING"}
        actual_levels = {item.name for item in ThemeIntensity}
        assert actual_levels == expected_levels

    def test_intensity_string_values(self):
        """Test that intensity enum values have correct string representations."""
        assert ThemeIntensity.SUBTLE.value == "subtle"
        assert ThemeIntensity.MODERATE.value == "moderate"
        assert ThemeIntensity.PROMINENT.value == "prominent"
        assert ThemeIntensity.CENTRAL.value == "central"
        assert ThemeIntensity.OVERWHELMING.value == "overwhelming"

    def test_intensity_logical_ordering(self):
        """Test that intensity levels represent logical progression."""
        intensity_order = {
            ThemeIntensity.SUBTLE: 1,
            ThemeIntensity.MODERATE: 2,
            ThemeIntensity.PROMINENT: 3,
            ThemeIntensity.CENTRAL: 4,
            ThemeIntensity.OVERWHELMING: 5,
        }

        assert (
            intensity_order[ThemeIntensity.OVERWHELMING]
            > intensity_order[ThemeIntensity.CENTRAL]
        )
        assert (
            intensity_order[ThemeIntensity.CENTRAL]
            > intensity_order[ThemeIntensity.PROMINENT]
        )
        assert (
            intensity_order[ThemeIntensity.PROMINENT]
            > intensity_order[ThemeIntensity.MODERATE]
        )
        assert (
            intensity_order[ThemeIntensity.MODERATE]
            > intensity_order[ThemeIntensity.SUBTLE]
        )


class TestNarrativeThemeCreation:
    """Test suite for NarrativeTheme creation and initialization."""

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


class TestNarrativeThemeValidation:
    """Test suite for NarrativeTheme validation logic."""

    def test_empty_name_validation(self):
        """Test validation fails with empty name."""
        with pytest.raises(ValueError, match="Theme name cannot be empty"):
            NarrativeTheme(
                theme_id="empty-name-test",
                theme_type=ThemeType.FAMILY,
                intensity=ThemeIntensity.MODERATE,
                name="",
                description="Valid description",
            )

    def test_whitespace_only_name_validation(self):
        """Test validation fails with whitespace-only name."""
        with pytest.raises(ValueError, match="Theme name cannot be empty"):
            NarrativeTheme(
                theme_id="whitespace-name-test",
                theme_type=ThemeType.FAMILY,
                intensity=ThemeIntensity.MODERATE,
                name="   ",
                description="Valid description",
            )

    def test_empty_description_validation(self):
        """Test validation fails with empty description."""
        with pytest.raises(ValueError, match="Theme description cannot be empty"):
            NarrativeTheme(
                theme_id="empty-desc-test",
                theme_type=ThemeType.ENVIRONMENTAL,
                intensity=ThemeIntensity.SUBTLE,
                name="Valid Name",
                description="",
            )

    def test_whitespace_only_description_validation(self):
        """Test validation fails with whitespace-only description."""
        with pytest.raises(ValueError, match="Theme description cannot be empty"):
            NarrativeTheme(
                theme_id="whitespace-desc-test",
                theme_type=ThemeType.ENVIRONMENTAL,
                intensity=ThemeIntensity.SUBTLE,
                name="Valid Name",
                description="   \t\n  ",
            )

    def test_negative_sequence_validation(self):
        """Test validation fails with negative sequence numbers."""
        with pytest.raises(
            ValueError, match="introduction_sequence must be non-negative"
        ):
            NarrativeTheme(
                theme_id="negative-intro-test",
                theme_type=ThemeType.COMING_OF_AGE,
                intensity=ThemeIntensity.CENTRAL,
                name="Growing Up",
                description="The journey to maturity",
                introduction_sequence=-1,
            )

        with pytest.raises(
            ValueError, match="resolution_sequence must be non-negative"
        ):
            NarrativeTheme(
                theme_id="negative-resolution-test",
                theme_type=ThemeType.COMING_OF_AGE,
                intensity=ThemeIntensity.CENTRAL,
                name="Growing Up",
                description="The journey to maturity",
                resolution_sequence=-5,
            )

        with pytest.raises(
            ValueError, match="peak_intensity_sequence must be non-negative"
        ):
            NarrativeTheme(
                theme_id="negative-peak-test",
                theme_type=ThemeType.COMING_OF_AGE,
                intensity=ThemeIntensity.CENTRAL,
                name="Growing Up",
                description="The journey to maturity",
                peak_intensity_sequence=-10,
            )

    def test_zero_sequence_allowed(self):
        """Test that zero sequence numbers are allowed."""
        theme = NarrativeTheme(
            theme_id="zero-seq-test",
            theme_type=ThemeType.TECHNOLOGICAL,
            intensity=ThemeIntensity.OVERWHELMING,
            name="AI Dominance",
            description="Technology overtaking humanity",
            introduction_sequence=0,
            resolution_sequence=0,
            peak_intensity_sequence=0,
        )

        assert theme.introduction_sequence == 0
        assert theme.resolution_sequence == 0
        assert theme.peak_intensity_sequence == 0

    def test_moral_complexity_below_minimum_validation(self):
        """Test validation fails with moral complexity below 1."""
        with pytest.raises(
            ValueError, match="moral_complexity must be between 1 and 10"
        ):
            NarrativeTheme(
                theme_id="low-complexity-test",
                theme_type=ThemeType.SPIRITUAL,
                intensity=ThemeIntensity.MODERATE,
                name="Faith",
                description="Spiritual journey",
                moral_complexity=Decimal("0.5"),
            )

    def test_moral_complexity_above_maximum_validation(self):
        """Test validation fails with moral complexity above 10."""
        with pytest.raises(
            ValueError, match="moral_complexity must be between 1 and 10"
        ):
            NarrativeTheme(
                theme_id="high-complexity-test",
                theme_type=ThemeType.SPIRITUAL,
                intensity=ThemeIntensity.MODERATE,
                name="Faith",
                description="Spiritual journey",
                moral_complexity=Decimal("11.0"),
            )

    def test_emotional_resonance_boundary_validation(self):
        """Test emotional resonance boundary validation."""
        with pytest.raises(
            ValueError, match="emotional_resonance must be between 1 and 10"
        ):
            NarrativeTheme(
                theme_id="low-resonance-test",
                theme_type=ThemeType.POLITICAL,
                intensity=ThemeIntensity.PROMINENT,
                name="Revolution",
                description="Fight for freedom",
                emotional_resonance=Decimal("0.9"),
            )

        with pytest.raises(
            ValueError, match="emotional_resonance must be between 1 and 10"
        ):
            NarrativeTheme(
                theme_id="high-resonance-test",
                theme_type=ThemeType.POLITICAL,
                intensity=ThemeIntensity.PROMINENT,
                name="Revolution",
                description="Fight for freedom",
                emotional_resonance=Decimal("10.1"),
            )

    def test_universal_appeal_boundary_validation(self):
        """Test universal appeal boundary validation."""
        with pytest.raises(
            ValueError, match="universal_appeal must be between 1 and 10"
        ):
            NarrativeTheme(
                theme_id="low-appeal-test",
                theme_type=ThemeType.CULTURAL,
                intensity=ThemeIntensity.SUBTLE,
                name="Heritage",
                description="Cultural traditions",
                universal_appeal=Decimal("0.5"),
            )

        with pytest.raises(
            ValueError, match="universal_appeal must be between 1 and 10"
        ):
            NarrativeTheme(
                theme_id="high-appeal-test",
                theme_type=ThemeType.CULTURAL,
                intensity=ThemeIntensity.SUBTLE,
                name="Heritage",
                description="Cultural traditions",
                universal_appeal=Decimal("15.0"),
            )

    def test_valid_decimal_boundary_values(self):
        """Test that boundary decimal values (1 and 10) are valid."""
        theme = NarrativeTheme(
            theme_id="boundary-test",
            theme_type=ThemeType.PHILOSOPHICAL,
            intensity=ThemeIntensity.CENTRAL,
            name="Existential Crisis",
            description="Questions about meaning and existence",
            moral_complexity=Decimal("1.0"),
            emotional_resonance=Decimal("10.0"),
            universal_appeal=Decimal("5.5"),
        )

        assert theme.moral_complexity == Decimal("1.0")
        assert theme.emotional_resonance == Decimal("10.0")
        assert theme.universal_appeal == Decimal("5.5")

    def test_audience_relevance_boundary_validation(self):
        """Test audience relevance value validation."""
        with pytest.raises(
            ValueError, match="Audience relevance for 'teens' must be between 0 and 10"
        ):
            NarrativeTheme(
                theme_id="invalid-audience-test",
                theme_type=ThemeType.COMING_OF_AGE,
                intensity=ThemeIntensity.PROMINENT,
                name="Growing Up",
                description="Teenage struggles",
                target_audience_relevance={"teens": Decimal("-1.0")},
            )

        with pytest.raises(
            ValueError, match="Audience relevance for 'adults' must be between 0 and 10"
        ):
            NarrativeTheme(
                theme_id="invalid-audience-high-test",
                theme_type=ThemeType.COMING_OF_AGE,
                intensity=ThemeIntensity.PROMINENT,
                name="Growing Up",
                description="Teenage struggles",
                target_audience_relevance={"adults": Decimal("11.5")},
            )

    def test_valid_audience_relevance_boundaries(self):
        """Test that audience relevance boundaries (0 and 10) are valid."""
        theme = NarrativeTheme(
            theme_id="valid-audience-test",
            theme_type=ThemeType.TECHNOLOGICAL,
            intensity=ThemeIntensity.OVERWHELMING,
            name="Digital Dystopia",
            description="Technology controlling society",
            target_audience_relevance={
                "children": Decimal("0.0"),
                "tech_workers": Decimal("10.0"),
                "elderly": Decimal("3.5"),
            },
        )

        assert theme.target_audience_relevance["children"] == Decimal("0.0")
        assert theme.target_audience_relevance["tech_workers"] == Decimal("10.0")
        assert theme.target_audience_relevance["elderly"] == Decimal("3.5")

    def test_string_length_validations(self):
        """Test string length constraint validations."""
        # Theme ID too long
        with pytest.raises(
            ValueError, match="Theme ID too long \\(max 100 characters\\)"
        ):
            NarrativeTheme(
                theme_id="x" * 101,
                theme_type=ThemeType.UNIVERSAL,
                intensity=ThemeIntensity.MODERATE,
                name="Valid Name",
                description="Valid description",
            )

        # Name too long
        with pytest.raises(
            ValueError, match="Theme name too long \\(max 200 characters\\)"
        ):
            NarrativeTheme(
                theme_id="valid-id",
                theme_type=ThemeType.UNIVERSAL,
                intensity=ThemeIntensity.MODERATE,
                name="x" * 201,
                description="Valid description",
            )

        # Description too long
        with pytest.raises(
            ValueError, match="Theme description too long \\(max 1000 characters\\)"
        ):
            NarrativeTheme(
                theme_id="valid-id",
                theme_type=ThemeType.UNIVERSAL,
                intensity=ThemeIntensity.MODERATE,
                name="Valid Name",
                description="x" * 1001,
            )

    def test_valid_string_length_boundaries(self):
        """Test that maximum string length boundaries are valid."""
        theme = NarrativeTheme(
            theme_id="x" * 100,
            theme_type=ThemeType.MORAL,
            intensity=ThemeIntensity.CENTRAL,
            name="x" * 200,
            description="x" * 1000,
        )

        assert len(theme.theme_id) == 100
        assert len(theme.name) == 200
        assert len(theme.description) == 1000


class TestNarrativeThemeProperties:
    """Test suite for NarrativeTheme property methods."""

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


class TestThematicComplexityScore:
    """Test suite for thematic complexity score calculation."""

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


class TestNarrativeThemeInstanceMethods:
    """Test suite for NarrativeTheme instance methods."""

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


class TestNarrativeThemeFactoryMethods:
    """Test suite for NarrativeTheme factory methods."""

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


class TestNarrativeThemeStringRepresentation:
    """Test suite for NarrativeTheme string representation methods."""

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


class TestNarrativeThemeEdgeCasesAndBoundaryConditions:
    """Test suite for edge cases and boundary conditions."""

    def test_creation_with_fixed_timestamp(self):
        """Test creation with explicitly set timestamp."""
        fixed_time = datetime(2024, 6, 15, 14, 30, 45, tzinfo=timezone.utc)

        theme = NarrativeTheme(
            theme_id="timestamp-test",
            theme_type=ThemeType.UNIVERSAL,
            intensity=ThemeIntensity.CENTRAL,
            name="Eternal Love",
            description="Love that transcends time",
            creation_timestamp=fixed_time,
        )

        assert theme.creation_timestamp == fixed_time

    def test_large_collections_handling(self):
        """Test handling of large collections."""
        many_symbols = {f"symbol_{i}" for i in range(100)}
        many_motifs = {f"motif_{i}" for i in range(75)}
        many_archetypes = {f"archetype_{i}" for i in range(50)}
        many_conflicts = {f"conflict_theme_{i}" for i in range(25)}
        many_reinforces = {f"reinforce_theme_{i}" for i in range(30)}
        many_tags = {f"tag_{i}" for i in range(40)}
        large_audience_mapping = {
            f"audience_{i}": Decimal(str(i % 10 + 1)) for i in range(20)
        }

        theme = NarrativeTheme(
            theme_id="large-collections-test",
            theme_type=ThemeType.PHILOSOPHICAL,
            intensity=ThemeIntensity.OVERWHELMING,
            name="Complexity of Existence",
            description="A theme with many interconnected elements",
            symbolic_elements=many_symbols,
            related_motifs=many_motifs,
            character_archetypes=many_archetypes,
            conflicts_with_themes=many_conflicts,
            reinforces_themes=many_reinforces,
            target_audience_relevance=large_audience_mapping,
            tags=many_tags,
        )

        assert len(theme.symbolic_elements) == 100
        assert len(theme.related_motifs) == 75
        assert len(theme.character_archetypes) == 50
        assert len(theme.conflicts_with_themes) == 25
        assert len(theme.reinforces_themes) == 30
        assert len(theme.target_audience_relevance) == 20
        assert len(theme.tags) == 40
        assert theme.has_symbolic_representation is True
        assert theme.has_character_expression is True

    def test_decimal_precision_handling(self):
        """Test handling of decimal precision for score values."""
        theme = NarrativeTheme(
            theme_id="precision-test",
            theme_type=ThemeType.MORAL,
            intensity=ThemeIntensity.CENTRAL,
            name="Ethical Dilemma",
            description="Complex moral choices",
            moral_complexity=Decimal("7.123456789"),
            emotional_resonance=Decimal("8.987654321"),
            universal_appeal=Decimal("9.555555555"),
        )

        # Values should maintain precision
        assert theme.moral_complexity == Decimal("7.123456789")
        assert theme.emotional_resonance == Decimal("8.987654321")
        assert theme.universal_appeal == Decimal("9.555555555")

        # Scores should use precise calculation
        complexity_score = theme.thematic_complexity_score
        impact_score = theme.narrative_impact_score
        assert isinstance(complexity_score, Decimal)
        assert isinstance(impact_score, Decimal)

    def test_unicode_text_handling(self):
        """Test handling of unicode characters in text fields."""
        theme = NarrativeTheme(
            theme_id="unicode-test-🎭",
            theme_type=ThemeType.CULTURAL,
            intensity=ThemeIntensity.PROMINENT,
            name="文化传承 Cultural Heritage 🏛️",
            description="Preserving traditions across generations: αβγ 中文 русский العربية 🌍",
            cultural_context="多元文化环境 Multicultural environment",
            development_trajectory="从传统到现代 From tradition to modernity ⚡",
        )

        assert "🎭" in theme.theme_id
        assert "文化传承" in theme.name
        assert "🏛️" in theme.name
        assert "中文" in theme.description
        assert "العربية" in theme.description
        assert "🌍" in theme.description
        assert "多元文化环境" in theme.cultural_context
        assert "⚡" in theme.development_trajectory

    def test_complex_metadata_handling(self):
        """Test handling of complex metadata structures."""
        complex_metadata = {
            "research_data": {
                "sources": ["Jung", "Campbell", "Vogler"],
                "analysis_depth": {
                    "psychological": 8.5,
                    "mythological": 9.0,
                    "cultural": 7.5,
                },
            },
            "adaptation_notes": [
                {"medium": "film", "effectiveness": 9.0},
                {"medium": "novel", "effectiveness": 8.5},
                {"medium": "theatre", "effectiveness": 7.0},
            ],
            "unicode_metadata_🔍": {
                "global_appeal": "универсальный",
                "cultural_variants": ["Western", "Eastern", "中式", "العربي"],
            },
        }

        theme = NarrativeTheme(
            theme_id="complex-metadata-test",
            theme_type=ThemeType.UNIVERSAL,
            intensity=ThemeIntensity.CENTRAL,
            name="Hero's Journey",
            description="Universal pattern of adventure and transformation",
            metadata=complex_metadata,
        )

        # Should store complex metadata as-is
        assert theme.metadata == complex_metadata
        assert theme.metadata["research_data"]["sources"] == [
            "Jung",
            "Campbell",
            "Vogler",
        ]
        assert theme.metadata["unicode_metadata_🔍"]["global_appeal"] == "универсальный"
        assert "中式" in theme.metadata["unicode_metadata_🔍"]["cultural_variants"]


class TestNarrativeThemeCollectionsAndComparison:
    """Test suite for NarrativeTheme behavior in collections and comparisons."""

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
        assert not (theme1 == theme2)

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
