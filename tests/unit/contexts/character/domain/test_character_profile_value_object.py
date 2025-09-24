#!/usr/bin/env python3
"""
Unit tests for CharacterProfile Value Object

Comprehensive test suite for the CharacterProfile value object covering
profile validation, trait management, background checks, and character identity.
"""

import sys
from unittest.mock import MagicMock

import pytest

# Mock problematic dependencies
sys.modules["aioredis"] = MagicMock()

# Import the value objects we're testing
from contexts.character.domain.value_objects.character_profile import (
    Background,
    CharacterClass,
    CharacterProfile,
    CharacterRace,
    Gender,
    PersonalityTraits,
    PhysicalTraits,
)


class TestPhysicalTraits:
    """Test suite for PhysicalTraits value object."""

    # ==================== Creation Tests ====================

    def test_physical_traits_creation_success(self):
        """Test successful physical traits creation."""
        traits = PhysicalTraits(
            height_cm=180,
            weight_kg=75,
            hair_color="brown",
            eye_color="blue",
            skin_tone="fair",
            distinguishing_marks=["scar on left cheek"],
            physical_description="Tall and athletic",
        )

        assert traits.height_cm == 180
        assert traits.weight_kg == 75
        assert traits.hair_color == "brown"
        assert traits.eye_color == "blue"
        assert traits.skin_tone == "fair"
        assert traits.distinguishing_marks == ["scar on left cheek"]
        assert traits.physical_description == "Tall and athletic"

    def test_physical_traits_creation_minimal(self):
        """Test physical traits creation with minimal data."""
        traits = PhysicalTraits()

        assert traits.height_cm is None
        assert traits.weight_kg is None
        assert traits.hair_color is None
        assert traits.eye_color is None
        assert traits.skin_tone is None
        assert traits.distinguishing_marks is None
        assert traits.physical_description is None

    # ==================== Validation Tests ====================

    def test_physical_traits_height_validation_too_short(self):
        """Test height validation fails for unreasonably short height."""
        with pytest.raises(ValueError) as exc_info:
            PhysicalTraits(height_cm=20)
        assert "Height must be between 30-300 cm" in str(exc_info.value)

    def test_physical_traits_height_validation_too_tall(self):
        """Test height validation fails for unreasonably tall height."""
        with pytest.raises(ValueError) as exc_info:
            PhysicalTraits(height_cm=350)
        assert "Height must be between 30-300 cm" in str(exc_info.value)

    def test_physical_traits_height_validation_boundary_values(self):
        """Test height validation at boundary values."""
        # Should work at boundaries
        traits_min = PhysicalTraits(height_cm=30)
        assert traits_min.height_cm == 30

        traits_max = PhysicalTraits(height_cm=300)
        assert traits_max.height_cm == 300

    def test_physical_traits_weight_validation_too_light(self):
        """Test weight validation fails for unreasonably light weight."""
        with pytest.raises(ValueError) as exc_info:
            PhysicalTraits(weight_kg=3)
        assert "Weight must be between 5-500 kg" in str(exc_info.value)

    def test_physical_traits_weight_validation_too_heavy(self):
        """Test weight validation fails for unreasonably heavy weight."""
        with pytest.raises(ValueError) as exc_info:
            PhysicalTraits(weight_kg=600)
        assert "Weight must be between 5-500 kg" in str(exc_info.value)

    def test_physical_traits_weight_validation_boundary_values(self):
        """Test weight validation at boundary values."""
        # Should work at boundaries
        traits_min = PhysicalTraits(weight_kg=5)
        assert traits_min.weight_kg == 5

        traits_max = PhysicalTraits(weight_kg=500)
        assert traits_max.weight_kg == 500


class TestPersonalityTraits:
    """Test suite for PersonalityTraits value object."""

    # ==================== Creation Tests ====================

    def test_personality_traits_creation_success(self):
        """Test successful personality traits creation."""
        traits = PersonalityTraits(
            traits={
                "courage": 0.8,
                "intelligence": 0.6,
                "charisma": 0.5,
                "loyalty": 0.9,
            },
            alignment="lawful good",
            motivations=["protect the innocent", "seek justice"],
            fears=["losing loved ones"],
            quirks=["always polishes sword"],
            ideals=["honor above all"],
            bonds=["sworn to protect the village"],
            flaws=["too trusting"],
        )

        assert traits.traits["courage"] == 0.8
        assert traits.alignment == "lawful good"
        assert "protect the innocent" in traits.motivations
        assert "losing loved ones" in traits.fears

    def test_personality_traits_creation_minimal(self):
        """Test personality traits creation with minimal data."""
        traits = PersonalityTraits(traits={"courage": 0.5})

        assert traits.traits["courage"] == 0.5
        assert traits.alignment is None
        assert traits.motivations is None
        assert traits.fears is None

    # ==================== Validation Tests ====================

    def test_personality_traits_empty_traits_fails(self):
        """Test personality traits validation fails with empty traits."""
        with pytest.raises(ValueError) as exc_info:
            PersonalityTraits(traits={})
        assert "Personality traits cannot be empty" in str(exc_info.value)

    def test_personality_traits_invalid_score_too_low(self):
        """Test validation fails for trait scores below 0.0."""
        with pytest.raises(ValueError) as exc_info:
            PersonalityTraits(traits={"courage": -0.1})
        assert "Trait score for 'courage' must be between 0.0 and 1.0" in str(
            exc_info.value
        )

    def test_personality_traits_invalid_score_too_high(self):
        """Test validation fails for trait scores above 1.0."""
        with pytest.raises(ValueError) as exc_info:
            PersonalityTraits(traits={"courage": 1.5})
        assert "Trait score for 'courage' must be between 0.0 and 1.0" in str(
            exc_info.value
        )

    def test_personality_traits_boundary_scores(self):
        """Test trait scores at boundary values."""
        traits = PersonalityTraits(traits={"minimum": 0.0, "maximum": 1.0})

        assert traits.traits["minimum"] == 0.0
        assert traits.traits["maximum"] == 1.0

    def test_personality_traits_empty_trait_name_fails(self):
        """Test validation fails for empty trait names."""
        with pytest.raises(ValueError) as exc_info:
            PersonalityTraits(traits={"": 0.5})
        assert "Trait names cannot be empty" in str(exc_info.value)

    def test_personality_traits_whitespace_trait_name_fails(self):
        """Test validation fails for whitespace-only trait names."""
        with pytest.raises(ValueError) as exc_info:
            PersonalityTraits(traits={"   ": 0.5})
        assert "Trait names cannot be empty" in str(exc_info.value)

    # ==================== Method Tests ====================

    def test_get_trait_score_existing_trait(self):
        """Test getting trait score for existing trait."""
        traits = PersonalityTraits(traits={"courage": 0.8})

        assert traits.get_trait_score("courage") == 0.8

    def test_get_trait_score_missing_trait_returns_default(self):
        """Test getting trait score for missing trait returns 0.5."""
        traits = PersonalityTraits(traits={"courage": 0.8})

        assert traits.get_trait_score("missing") == 0.5

    def test_get_trait_score_case_insensitive(self):
        """Test trait score lookup is case insensitive."""
        traits = PersonalityTraits(traits={"courage": 0.8})

        assert traits.get_trait_score("courage") == 0.8
        assert traits.get_trait_score("COURAGE") == 0.8

    def test_has_trait_existing(self):
        """Test has_trait returns True for existing traits."""
        traits = PersonalityTraits(traits={"courage": 0.8})

        assert traits.has_trait("courage") is True

    def test_has_trait_missing(self):
        """Test has_trait returns False for missing traits."""
        traits = PersonalityTraits(traits={"courage": 0.8})

        assert traits.has_trait("missing") is False

    def test_has_trait_case_insensitive(self):
        """Test has_trait is case insensitive."""
        traits = PersonalityTraits(traits={"courage": 0.8})

        assert traits.has_trait("courage") is True
        assert traits.has_trait("COURAGE") is True


class TestBackground:
    """Test suite for Background value object."""

    # ==================== Creation Tests ====================

    def test_background_creation_success(self):
        """Test successful background creation."""
        background = Background(
            backstory="Born in a small village",
            homeland="Westlands",
            family={"father": "blacksmith", "mother": "healer"},
            education="village school",
            previous_occupations=["farmer", "guard"],
            significant_events=[
                {"event": "saved village from bandits", "age": 20}
            ],
            reputation="local hero",
        )

        assert background.backstory == "Born in a small village"
        assert background.homeland == "Westlands"
        assert background.family["father"] == "blacksmith"
        assert background.education == "village school"
        assert "farmer" in background.previous_occupations

    def test_background_creation_minimal(self):
        """Test background creation with minimal data."""
        background = Background()

        assert background.backstory is None
        assert background.homeland is None
        assert background.family is None
        assert background.education is None
        assert background.previous_occupations is None
        assert background.significant_events is None
        assert background.reputation is None

    # ==================== Method Tests ====================

    def test_has_education_with_education(self):
        """Test has_education returns True when education exists."""
        background = Background(education="university")

        assert background.has_education() is True

    def test_has_education_without_education(self):
        """Test has_education returns False when education is None."""
        background = Background()

        assert background.has_education() is False

    def test_has_education_with_empty_education(self):
        """Test has_education returns False when education is empty."""
        background = Background(education="   ")

        assert background.has_education() is False

    def test_has_family_connections_with_family(self):
        """Test has_family_connections returns True when family exists."""
        background = Background(family={"father": "merchant"})

        assert background.has_family_connections() is True

    def test_has_family_connections_without_family(self):
        """Test has_family_connections returns False when family is None."""
        background = Background()

        assert background.has_family_connections() is False

    def test_has_family_connections_with_empty_family(self):
        """Test has_family_connections returns False when family is empty."""
        background = Background(family={})

        assert background.has_family_connections() is False


class TestCharacterProfile:
    """Test suite for CharacterProfile value object."""

    @pytest.fixture
    def sample_physical_traits(self) -> PhysicalTraits:
        """Create sample physical traits for testing."""
        return PhysicalTraits(
            height_cm=180, weight_kg=75, hair_color="brown", eye_color="blue"
        )

    @pytest.fixture
    def sample_personality_traits(self) -> PersonalityTraits:
        """Create sample personality traits for testing."""
        return PersonalityTraits(
            traits={"courage": 0.8, "intelligence": 0.6, "loyalty": 0.9}
        )

    @pytest.fixture
    def sample_background(self) -> Background:
        """Create sample background for testing."""
        return Background(
            backstory="Noble warrior", homeland="Kingdom of Valor"
        )

    @pytest.fixture
    def sample_character_profile(
        self,
        sample_physical_traits,
        sample_personality_traits,
        sample_background,
    ) -> CharacterProfile:
        """Create a test CharacterProfile instance."""
        return CharacterProfile(
            name="Sir Galahad",
            gender=Gender.MALE,
            race=CharacterRace.HUMAN,
            character_class=CharacterClass.PALADIN,
            age=30,
            level=5,
            physical_traits=sample_physical_traits,
            personality_traits=sample_personality_traits,
            background=sample_background,
            title="Sir",
            affiliation="Knights of the Round Table",
            languages=["Common", "Celestial"],
        )

    # ==================== Creation Tests ====================

    def test_character_profile_creation_success(
        self,
        sample_physical_traits,
        sample_personality_traits,
        sample_background,
    ):
        """Test successful character profile creation."""
        profile = CharacterProfile(
            name="Test Hero",
            gender=Gender.FEMALE,
            race=CharacterRace.ELF,
            character_class=CharacterClass.RANGER,
            age=120,
            level=3,
            physical_traits=sample_physical_traits,
            personality_traits=sample_personality_traits,
            background=sample_background,
        )

        assert profile.name == "Test Hero"
        assert profile.gender == Gender.FEMALE
        assert profile.race == CharacterRace.ELF
        assert profile.character_class == CharacterClass.RANGER
        assert profile.age == 120
        assert profile.level == 3

    def test_character_profile_creation_minimal(
        self,
        sample_physical_traits,
        sample_personality_traits,
        sample_background,
    ):
        """Test character profile creation with minimal data."""
        profile = CharacterProfile(
            name="Minimal Hero",
            gender=Gender.UNSPECIFIED,
            race=CharacterRace.HUMAN,
            character_class=CharacterClass.FIGHTER,
            age=25,
            level=1,
            physical_traits=sample_physical_traits,
            personality_traits=sample_personality_traits,
            background=sample_background,
        )

        assert profile.name == "Minimal Hero"
        assert profile.title is None
        assert profile.affiliation is None
        assert profile.languages is None

    # ==================== Validation Tests ====================

    def test_character_profile_empty_name_fails(
        self,
        sample_physical_traits,
        sample_personality_traits,
        sample_background,
    ):
        """Test character profile validation fails with empty name."""
        with pytest.raises(ValueError) as exc_info:
            CharacterProfile(
                name="",
                gender=Gender.MALE,
                race=CharacterRace.HUMAN,
                character_class=CharacterClass.FIGHTER,
                age=25,
                level=1,
                physical_traits=sample_physical_traits,
                personality_traits=sample_personality_traits,
                background=sample_background,
            )
        assert "Character name cannot be empty" in str(exc_info.value)

    def test_character_profile_whitespace_name_fails(
        self,
        sample_physical_traits,
        sample_personality_traits,
        sample_background,
    ):
        """Test character profile validation fails with whitespace-only name."""
        with pytest.raises(ValueError) as exc_info:
            CharacterProfile(
                name="   ",
                gender=Gender.MALE,
                race=CharacterRace.HUMAN,
                character_class=CharacterClass.FIGHTER,
                age=25,
                level=1,
                physical_traits=sample_physical_traits,
                personality_traits=sample_personality_traits,
                background=sample_background,
            )
        assert "Character name cannot be empty" in str(exc_info.value)

    def test_character_profile_name_too_long_fails(
        self,
        sample_physical_traits,
        sample_personality_traits,
        sample_background,
    ):
        """Test character profile validation fails with name too long."""
        long_name = "A" * 101  # 101 characters
        with pytest.raises(ValueError) as exc_info:
            CharacterProfile(
                name=long_name,
                gender=Gender.MALE,
                race=CharacterRace.HUMAN,
                character_class=CharacterClass.FIGHTER,
                age=25,
                level=1,
                physical_traits=sample_physical_traits,
                personality_traits=sample_personality_traits,
                background=sample_background,
            )
        assert "Character name cannot exceed 100 characters" in str(
            exc_info.value
        )

    def test_character_profile_negative_age_fails(
        self,
        sample_physical_traits,
        sample_personality_traits,
        sample_background,
    ):
        """Test character profile validation fails with negative age."""
        with pytest.raises(ValueError) as exc_info:
            CharacterProfile(
                name="Test",
                gender=Gender.MALE,
                race=CharacterRace.HUMAN,
                character_class=CharacterClass.FIGHTER,
                age=-1,
                level=1,
                physical_traits=sample_physical_traits,
                personality_traits=sample_personality_traits,
                background=sample_background,
            )
        assert "Age must be between 0 and 10000" in str(exc_info.value)

    def test_character_profile_age_too_high_fails(
        self,
        sample_physical_traits,
        sample_personality_traits,
        sample_background,
    ):
        """Test character profile validation fails with age too high."""
        with pytest.raises(ValueError) as exc_info:
            CharacterProfile(
                name="Test",
                gender=Gender.MALE,
                race=CharacterRace.HUMAN,
                character_class=CharacterClass.FIGHTER,
                age=10001,
                level=1,
                physical_traits=sample_physical_traits,
                personality_traits=sample_personality_traits,
                background=sample_background,
            )
        assert "Age must be between 0 and 10000" in str(exc_info.value)

    def test_character_profile_level_too_low_fails(
        self,
        sample_physical_traits,
        sample_personality_traits,
        sample_background,
    ):
        """Test character profile validation fails with level too low."""
        with pytest.raises(ValueError) as exc_info:
            CharacterProfile(
                name="Test",
                gender=Gender.MALE,
                race=CharacterRace.HUMAN,
                character_class=CharacterClass.FIGHTER,
                age=25,
                level=0,
                physical_traits=sample_physical_traits,
                personality_traits=sample_personality_traits,
                background=sample_background,
            )
        assert "Level must be between 1 and 100" in str(exc_info.value)

    def test_character_profile_level_too_high_fails(
        self,
        sample_physical_traits,
        sample_personality_traits,
        sample_background,
    ):
        """Test character profile validation fails with level too high."""
        with pytest.raises(ValueError) as exc_info:
            CharacterProfile(
                name="Test",
                gender=Gender.MALE,
                race=CharacterRace.HUMAN,
                character_class=CharacterClass.FIGHTER,
                age=25,
                level=101,
                physical_traits=sample_physical_traits,
                personality_traits=sample_personality_traits,
                background=sample_background,
            )
        assert "Level must be between 1 and 100" in str(exc_info.value)

    def test_character_profile_too_many_languages_fails(
        self,
        sample_physical_traits,
        sample_personality_traits,
        sample_background,
    ):
        """Test character profile validation fails with too many languages."""
        too_many_languages = [
            f"Language{i}" for i in range(21)
        ]  # 21 languages
        with pytest.raises(ValueError) as exc_info:
            CharacterProfile(
                name="Test",
                gender=Gender.MALE,
                race=CharacterRace.HUMAN,
                character_class=CharacterClass.FIGHTER,
                age=25,
                level=1,
                physical_traits=sample_physical_traits,
                personality_traits=sample_personality_traits,
                background=sample_background,
                languages=too_many_languages,
            )
        assert "Cannot speak more than 20 languages" in str(exc_info.value)

    def test_character_profile_empty_language_fails(
        self,
        sample_physical_traits,
        sample_personality_traits,
        sample_background,
    ):
        """Test character profile validation fails with empty language name."""
        with pytest.raises(ValueError) as exc_info:
            CharacterProfile(
                name="Test",
                gender=Gender.MALE,
                race=CharacterRace.HUMAN,
                character_class=CharacterClass.FIGHTER,
                age=25,
                level=1,
                physical_traits=sample_physical_traits,
                personality_traits=sample_personality_traits,
                background=sample_background,
                languages=["Common", ""],
            )
        assert "Language names cannot be empty" in str(exc_info.value)

    # ==================== Age Methods Tests ====================

    def test_is_adult_human_adult(
        self,
        sample_physical_traits,
        sample_personality_traits,
        sample_background,
    ):
        """Test is_adult returns True for adult human."""
        profile = CharacterProfile(
            name="Adult Human",
            gender=Gender.MALE,
            race=CharacterRace.HUMAN,
            character_class=CharacterClass.FIGHTER,
            age=25,
            level=1,
            physical_traits=sample_physical_traits,
            personality_traits=sample_personality_traits,
            background=sample_background,
        )

        assert profile.is_adult() is True

    def test_is_adult_human_child(
        self,
        sample_physical_traits,
        sample_personality_traits,
        sample_background,
    ):
        """Test is_adult returns False for child human."""
        profile = CharacterProfile(
            name="Child Human",
            gender=Gender.MALE,
            race=CharacterRace.HUMAN,
            character_class=CharacterClass.FIGHTER,
            age=15,
            level=1,
            physical_traits=sample_physical_traits,
            personality_traits=sample_personality_traits,
            background=sample_background,
        )

        assert profile.is_adult() is False

    def test_is_adult_elf_adult(
        self,
        sample_physical_traits,
        sample_personality_traits,
        sample_background,
    ):
        """Test is_adult returns True for adult elf."""
        profile = CharacterProfile(
            name="Adult Elf",
            gender=Gender.FEMALE,
            race=CharacterRace.ELF,
            character_class=CharacterClass.WIZARD,
            age=120,
            level=1,
            physical_traits=sample_physical_traits,
            personality_traits=sample_personality_traits,
            background=sample_background,
        )

        assert profile.is_adult() is True

    def test_is_adult_elf_child(
        self,
        sample_physical_traits,
        sample_personality_traits,
        sample_background,
    ):
        """Test is_adult returns False for child elf."""
        profile = CharacterProfile(
            name="Child Elf",
            gender=Gender.FEMALE,
            race=CharacterRace.ELF,
            character_class=CharacterClass.WIZARD,
            age=80,
            level=1,
            physical_traits=sample_physical_traits,
            personality_traits=sample_personality_traits,
            background=sample_background,
        )

        assert profile.is_adult() is False

    def test_is_adult_dwarf_adult(
        self,
        sample_physical_traits,
        sample_personality_traits,
        sample_background,
    ):
        """Test is_adult returns True for adult dwarf."""
        profile = CharacterProfile(
            name="Adult Dwarf",
            gender=Gender.MALE,
            race=CharacterRace.DWARF,
            character_class=CharacterClass.FIGHTER,
            age=60,
            level=1,
            physical_traits=sample_physical_traits,
            personality_traits=sample_personality_traits,
            background=sample_background,
        )

        assert profile.is_adult() is True

    def test_is_adult_boundary_values(
        self,
        sample_physical_traits,
        sample_personality_traits,
        sample_background,
    ):
        """Test is_adult at exact boundary ages."""
        # Human at exactly 18
        profile = CharacterProfile(
            name="Boundary Human",
            gender=Gender.MALE,
            race=CharacterRace.HUMAN,
            character_class=CharacterClass.FIGHTER,
            age=18,
            level=1,
            physical_traits=sample_physical_traits,
            personality_traits=sample_personality_traits,
            background=sample_background,
        )

        assert profile.is_adult() is True

    # ==================== Title and Summary Methods Tests ====================

    def test_get_full_title_with_title(self, sample_character_profile):
        """Test get_full_title with title."""
        assert sample_character_profile.get_full_title() == "Sir Sir Galahad"

    def test_get_full_title_without_title(
        self,
        sample_physical_traits,
        sample_personality_traits,
        sample_background,
    ):
        """Test get_full_title without title."""
        profile = CharacterProfile(
            name="No Title",
            gender=Gender.MALE,
            race=CharacterRace.HUMAN,
            character_class=CharacterClass.FIGHTER,
            age=25,
            level=1,
            physical_traits=sample_physical_traits,
            personality_traits=sample_personality_traits,
            background=sample_background,
        )

        assert profile.get_full_title() == "No Title"

    def test_get_character_summary_with_affiliation(
        self, sample_character_profile
    ):
        """Test character summary with affiliation."""
        summary = sample_character_profile.get_character_summary()

        assert "Sir Sir Galahad" in summary
        assert "Level 5" in summary
        assert "Human" in summary
        assert "Paladin" in summary
        assert "Knights of the Round Table" in summary

    def test_get_character_summary_without_affiliation(
        self,
        sample_physical_traits,
        sample_personality_traits,
        sample_background,
    ):
        """Test character summary without affiliation."""
        profile = CharacterProfile(
            name="No Affiliation",
            gender=Gender.MALE,
            race=CharacterRace.HUMAN,
            character_class=CharacterClass.FIGHTER,
            age=25,
            level=1,
            physical_traits=sample_physical_traits,
            personality_traits=sample_personality_traits,
            background=sample_background,
        )

        summary = profile.get_character_summary()

        assert "No Affiliation" in summary
        assert "Level 1" in summary
        assert "Human" in summary
        assert "Fighter" in summary
        assert "of " not in summary  # No affiliation

    # ==================== Language Methods Tests ====================

    def test_speaks_language_with_languages_list(
        self, sample_character_profile
    ):
        """Test speaks_language with explicit languages list."""
        assert sample_character_profile.speaks_language("Common") is True
        assert sample_character_profile.speaks_language("Celestial") is True
        assert sample_character_profile.speaks_language("Orcish") is False

    def test_speaks_language_case_insensitive(self, sample_character_profile):
        """Test speaks_language is case insensitive."""
        assert sample_character_profile.speaks_language("common") is True
        assert sample_character_profile.speaks_language("CELESTIAL") is True

    def test_speaks_language_without_languages_list(
        self,
        sample_physical_traits,
        sample_personality_traits,
        sample_background,
    ):
        """Test speaks_language defaults to Common when no languages specified."""
        profile = CharacterProfile(
            name="Default Language",
            gender=Gender.MALE,
            race=CharacterRace.HUMAN,
            character_class=CharacterClass.FIGHTER,
            age=25,
            level=1,
            physical_traits=sample_physical_traits,
            personality_traits=sample_personality_traits,
            background=sample_background,
        )

        assert profile.speaks_language("Common") is True
        assert profile.speaks_language("Elvish") is False

    # ==================== Personality Trait Methods Tests ====================

    def test_has_trait_above_threshold_true(self, sample_character_profile):
        """Test has_trait_above returns True when trait is above threshold."""
        assert sample_character_profile.has_trait_above("courage", 0.7) is True
        assert sample_character_profile.has_trait_above("loyalty", 0.8) is True

    def test_has_trait_above_threshold_false(self, sample_character_profile):
        """Test has_trait_above returns False when trait is below threshold."""
        assert (
            sample_character_profile.has_trait_above("intelligence", 0.7)
            is False
        )
        assert (
            sample_character_profile.has_trait_above("courage", 0.9) is False
        )

    def test_has_trait_above_missing_trait(self, sample_character_profile):
        """Test has_trait_above with missing trait uses default 0.5."""
        assert sample_character_profile.has_trait_above("missing", 0.4) is True
        assert (
            sample_character_profile.has_trait_above("missing", 0.6) is False
        )

    def test_get_personality_summary_strong_traits(
        self, sample_physical_traits, sample_background
    ):
        """Test personality summary with strong traits (>0.7)."""
        strong_traits = PersonalityTraits(
            traits={
                "courage": 0.8,
                "loyalty": 0.9,
                "intelligence": 0.5,
                "charisma": 0.6,
            }
        )

        profile = CharacterProfile(
            name="Strong Traits",
            gender=Gender.MALE,
            race=CharacterRace.HUMAN,
            character_class=CharacterClass.FIGHTER,
            age=25,
            level=1,
            physical_traits=sample_physical_traits,
            personality_traits=strong_traits,
            background=sample_background,
        )

        summary = profile.get_personality_summary()

        assert "courage" in summary
        assert "loyalty" in summary
        assert "intelligence" not in summary
        assert "charisma" not in summary

    def test_get_personality_summary_no_strong_traits(
        self, sample_physical_traits, sample_background
    ):
        """Test personality summary without strong traits returns top 3."""
        weak_traits = PersonalityTraits(
            traits={
                "courage": 0.6,
                "loyalty": 0.5,
                "intelligence": 0.4,
                "charisma": 0.3,
                "wisdom": 0.2,
            }
        )

        profile = CharacterProfile(
            name="Weak Traits",
            gender=Gender.MALE,
            race=CharacterRace.HUMAN,
            character_class=CharacterClass.FIGHTER,
            age=25,
            level=1,
            physical_traits=sample_physical_traits,
            personality_traits=weak_traits,
            background=sample_background,
        )

        summary = profile.get_personality_summary()

        assert len(summary) == 3
        assert "courage" in summary
        assert "loyalty" in summary
        assert "intelligence" in summary

    def test_get_personality_summary_empty_traits(
        self, sample_physical_traits, sample_background
    ):
        """Test personality summary with single trait."""
        single_trait = PersonalityTraits(traits={"courage": 0.5})

        profile = CharacterProfile(
            name="Single Trait",
            gender=Gender.MALE,
            race=CharacterRace.HUMAN,
            character_class=CharacterClass.FIGHTER,
            age=25,
            level=1,
            physical_traits=sample_physical_traits,
            personality_traits=single_trait,
            background=sample_background,
        )

        summary = profile.get_personality_summary()

        assert summary == ["courage"]

    # ==================== Immutability Tests ====================

    def test_character_profile_immutability(self, sample_character_profile):
        """Test that character profile is immutable (frozen dataclass)."""
        with pytest.raises(AttributeError):
            sample_character_profile.name = "New Name"

    def test_physical_traits_immutability(self):
        """Test that physical traits is immutable."""
        traits = PhysicalTraits(height_cm=180)

        with pytest.raises(AttributeError):
            traits.height_cm = 190

    def test_personality_traits_immutability(self):
        """Test that personality traits is immutable."""
        traits = PersonalityTraits(traits={"courage": 0.8})

        with pytest.raises(AttributeError):
            traits.alignment = "chaotic good"

    def test_background_immutability(self):
        """Test that background is immutable."""
        background = Background(backstory="Test")

        with pytest.raises(AttributeError):
            background.backstory = "New story"

    # ==================== Edge Cases and Integration Tests ====================

    def test_character_profile_with_all_enum_values(
        self,
        sample_physical_traits,
        sample_personality_traits,
        sample_background,
    ):
        """Test character profile creation with various enum values."""
        # Test all genders
        for gender in Gender:
            profile = CharacterProfile(
                name=f"Test {gender.value}",
                gender=gender,
                race=CharacterRace.HUMAN,
                character_class=CharacterClass.FIGHTER,
                age=25,
                level=1,
                physical_traits=sample_physical_traits,
                personality_traits=sample_personality_traits,
                background=sample_background,
            )
            assert profile.gender == gender

    def test_character_profile_racial_age_combinations(
        self,
        sample_physical_traits,
        sample_personality_traits,
        sample_background,
    ):
        """Test character profiles with different racial age combinations."""
        racial_ages = [
            (CharacterRace.HUMAN, 25, True),
            (CharacterRace.ELF, 150, True),
            (CharacterRace.ELF, 50, False),
            (CharacterRace.DWARF, 80, True),
            (CharacterRace.DWARF, 30, False),
            (CharacterRace.HALFLING, 25, True),
            (CharacterRace.HALFLING, 15, False),
        ]

        for race, age, expected_adult in racial_ages:
            profile = CharacterProfile(
                name=f"Test {race.value}",
                gender=Gender.MALE,
                race=race,
                character_class=CharacterClass.FIGHTER,
                age=age,
                level=1,
                physical_traits=sample_physical_traits,
                personality_traits=sample_personality_traits,
                background=sample_background,
            )

            assert profile.is_adult() == expected_adult

    def test_character_profile_boundary_validations(
        self,
        sample_physical_traits,
        sample_personality_traits,
        sample_background,
    ):
        """Test character profile at all validation boundaries."""
        # Test boundary ages
        boundary_profile = CharacterProfile(
            name="Boundary Test",
            gender=Gender.MALE,
            race=CharacterRace.HUMAN,
            character_class=CharacterClass.FIGHTER,
            age=0,  # Minimum age
            level=1,  # Minimum level
            physical_traits=sample_physical_traits,
            personality_traits=sample_personality_traits,
            background=sample_background,
        )

        assert boundary_profile.age == 0
        assert boundary_profile.level == 1

        # Test maximum boundaries
        max_boundary_profile = CharacterProfile(
            name="Max Boundary",
            gender=Gender.MALE,
            race=CharacterRace.HUMAN,
            character_class=CharacterClass.FIGHTER,
            age=10000,  # Maximum age
            level=100,  # Maximum level
            physical_traits=sample_physical_traits,
            personality_traits=sample_personality_traits,
            background=sample_background,
            languages=[f"Language{i}" for i in range(20)],  # Maximum languages
        )

        assert max_boundary_profile.age == 10000
        assert max_boundary_profile.level == 100
        assert len(max_boundary_profile.languages) == 20
