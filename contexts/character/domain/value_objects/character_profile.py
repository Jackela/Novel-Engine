#!/usr/bin/env python3
"""
Character Profile Value Object

This module implements the CharacterProfile value object, representing the core
immutable characteristics of a character including identity, physical traits,
and personality attributes.

Follows P3 Sprint 3 patterns for type safety and validation.
"""

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

if TYPE_CHECKING:
    from ...infrastructure.character_domain_types import (
        CharacterTypeGuards,
        ensure_float,
        ensure_int,
    )


class Gender(Enum):
    """Character gender options."""

    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"
    OTHER = "other"
    UNSPECIFIED = "unspecified"


class CharacterRace(Enum):
    """Character race/species options."""

    HUMAN = "human"
    ELF = "elf"
    DWARF = "dwarf"
    HALFLING = "halfling"
    GNOME = "gnome"
    DRAGONBORN = "dragonborn"
    TIEFLING = "tiefling"
    HALF_ELF = "half_elf"
    HALF_ORC = "half_orc"
    OTHER = "other"


class CharacterClass(Enum):
    """Character class/profession options."""

    FIGHTER = "fighter"
    WIZARD = "wizard"
    ROGUE = "rogue"
    CLERIC = "cleric"
    RANGER = "ranger"
    PALADIN = "paladin"
    BARBARIAN = "barbarian"
    BARD = "bard"
    DRUID = "druid"
    MONK = "monk"
    SORCERER = "sorcerer"
    WARLOCK = "warlock"
    ARTIFICER = "artificer"
    PILOT = "pilot"
    SCIENTIST = "scientist"
    ENGINEER = "engineer"
    SOLDIER = "soldier"
    MEDIC = "medic"
    MERCHANT = "merchant"
    SCHOLAR = "scholar"
    NOBLE = "noble"
    CRIMINAL = "criminal"
    PERFORMER = "performer"
    CRAFTSPERSON = "craftsperson"
    OTHER = "other"


@dataclass(frozen=True)
class PhysicalTraits:
    """Value object representing physical characteristics."""

    height_cm: Optional[int] = None
    weight_kg: Optional[int] = None
    hair_color: Optional[str] = None
    eye_color: Optional[str] = None
    skin_tone: Optional[str] = None
    distinguishing_marks: Optional[List[str]] = None
    physical_description: Optional[str] = None

    def __post_init__(self):
        """Validate physical traits."""
        if self.height_cm is not None and (
            self.height_cm < 30 or self.height_cm > 300
        ):
            raise ValueError("Height must be between 30-300 cm")

        if self.weight_kg is not None and (
            self.weight_kg < 5 or self.weight_kg > 500
        ):
            raise ValueError("Weight must be between 5-500 kg")


@dataclass(frozen=True)
class PersonalityTraits:
    """Value object representing character personality."""

    traits: Dict[str, float]  # Trait name -> score (0.0-1.0)
    alignment: Optional[str] = None
    motivations: Optional[List[str]] = None
    fears: Optional[List[str]] = None
    quirks: Optional[List[str]] = None
    ideals: Optional[List[str]] = None
    bonds: Optional[List[str]] = None
    flaws: Optional[List[str]] = None

    def __post_init__(self):
        """Validate personality traits with type safety."""
        if not self.traits:
            raise ValueError("Personality traits cannot be empty")

        for trait, score in self.traits.items():
            # Use type guard to ensure score is a valid float
            try:
                from ...infrastructure.character_domain_types import (
                    ensure_float,
                )

                safe_score = ensure_float(score)
                if not 0.0 <= safe_score <= 1.0:
                    raise ValueError(
                        f"Trait score for '{trait}' must be between 0.0 and 1.0, got {safe_score}"
                    )
            except (TypeError, ValueError) as e:
                raise ValueError(
                    f"Invalid trait score for '{trait}': {score}"
                ) from e

        # Ensure trait names are not empty
        for trait in self.traits.keys():
            if not trait or not trait.strip():
                raise ValueError("Trait names cannot be empty")

    def get_trait_score(self, trait_name: str) -> float:
        """Get the score for a specific trait, returning 0.5 if not found."""
        return self.traits.get(trait_name.lower(), 0.5)

    def has_trait(self, trait_name: str) -> bool:
        """Check if character has a specific trait defined."""
        return trait_name.lower() in self.traits


@dataclass(frozen=True)
class Background:
    """Value object representing character background."""

    backstory: Optional[str] = None
    homeland: Optional[str] = None
    family: Optional[Dict[str, Any]] = None
    education: Optional[str] = None
    previous_occupations: Optional[List[str]] = None
    significant_events: Optional[List[Dict[str, Any]]] = None
    reputation: Optional[str] = None

    def has_education(self) -> bool:
        """Check if character has educational background."""
        return self.education is not None and len(self.education.strip()) > 0

    def has_family_connections(self) -> bool:
        """Check if character has family connections."""
        return self.family is not None and len(self.family) > 0


@dataclass(frozen=True)
class CharacterProfile:
    """
    Value object representing the core immutable profile of a character.

    This encapsulates all the fundamental characteristics that define who
    a character is, separate from their current state or equipment.
    Following DDD principles, this is immutable and self-validating.
    """

    name: str
    gender: Gender
    race: CharacterRace
    character_class: CharacterClass
    age: int
    level: int
    physical_traits: PhysicalTraits
    personality_traits: PersonalityTraits
    background: Background
    title: Optional[str] = None
    affiliation: Optional[str] = None
    languages: Optional[List[str]] = None

    def __post_init__(self):
        """Validate character profile data with type safety."""
        from ...infrastructure.character_domain_types import (
            CharacterTypeGuards,
        )

        # Validate required fields with type guards
        if not CharacterTypeGuards.is_valid_character_name(self.name):
            raise ValueError(
                "Character name must be a non-empty string between 1-100 characters"
            )

        if not CharacterTypeGuards.is_valid_age(self.age):
            raise ValueError("Age must be between 0 and 10000")

        if not CharacterTypeGuards.is_valid_level(self.level):
            raise ValueError("Level must be between 1 and 100")

        # Validate enum types
        if not isinstance(self.gender, Gender):
            raise TypeError("gender must be a Gender enum value")

        if not isinstance(self.race, CharacterRace):
            raise TypeError("race must be a CharacterRace enum value")

        if not isinstance(self.character_class, CharacterClass):
            raise TypeError(
                "character_class must be a CharacterClass enum value"
            )

        # Validate nested value objects
        if not isinstance(self.physical_traits, PhysicalTraits):
            raise TypeError(
                "physical_traits must be a PhysicalTraits instance"
            )

        if not isinstance(self.personality_traits, PersonalityTraits):
            raise TypeError(
                "personality_traits must be a PersonalityTraits instance"
            )

        if not isinstance(self.background, Background):
            raise TypeError("background must be a Background instance")

        # Validate languages
        if self.languages:
            if len(self.languages) > 20:
                raise ValueError("Cannot speak more than 20 languages")

            for lang in self.languages:
                if not lang or not lang.strip():
                    raise ValueError("Language names cannot be empty")

    def is_adult(self) -> bool:
        """Check if character is considered an adult for their race."""
        # Basic adult age determination (can be race-specific)
        adult_ages = {
            CharacterRace.HUMAN: 18,
            CharacterRace.HALFLING: 20,
            CharacterRace.DWARF: 50,
            CharacterRace.ELF: 100,
            CharacterRace.GNOME: 40,
            CharacterRace.HALF_ELF: 20,
            CharacterRace.HALF_ORC: 14,
            CharacterRace.DRAGONBORN: 15,
            CharacterRace.TIEFLING: 18,
            CharacterRace.OTHER: 18,
        }

        return self.age >= adult_ages.get(self.race, 18)

    def get_full_title(self) -> str:
        """Get the character's full title and name."""
        if self.title:
            return f"{self.title} {self.name}"
        return self.name

    def get_character_summary(self) -> str:
        """Get a brief summary of the character."""
        summary_parts = [
            f"Level {self.level}",
            self.race.value.title(),
            self.character_class.value.title(),
        ]

        if self.affiliation:
            summary_parts.append(f"of {self.affiliation}")

        return f"{self.get_full_title()}, {' '.join(summary_parts)}"

    def speaks_language(self, language: str) -> bool:
        """Check if character speaks a specific language."""
        if not self.languages:
            return (
                language.lower() == "common"
            )  # Assume common language by default

        return any(lang.lower() == language.lower() for lang in self.languages)

    def has_trait_above(self, trait_name: str, threshold: float) -> bool:
        """Check if character has a personality trait above a threshold."""
        return self.personality_traits.get_trait_score(trait_name) > threshold

    def get_personality_summary(self) -> List[str]:
        """Get a summary of the character's dominant personality traits."""
        if not self.personality_traits.traits:
            return []

        # Get traits above 0.7 (strong traits)
        strong_traits = [
            trait
            for trait, score in self.personality_traits.traits.items()
            if score > 0.7
        ]

        # If no strong traits, get top 3 traits
        if not strong_traits:
            sorted_traits = sorted(
                self.personality_traits.traits.items(),
                key=lambda x: x[1],
                reverse=True,
            )
            strong_traits = [trait for trait, _ in sorted_traits[:3]]

        return strong_traits

    @classmethod
    def create_with_validation(
        cls,
        name: str,
        gender: Union[Gender, str],
        race: Union[CharacterRace, str],
        character_class: Union[CharacterClass, str],
        age: Union[int, str],
        level: Union[int, str],
        **kwargs: Any,
    ) -> "CharacterProfile":
        """Factory method to create CharacterProfile with type validation."""
        from ...infrastructure.character_domain_types import ValueObjectFactory

        return ValueObjectFactory.create_character_profile_with_validation(
            name=name,
            gender=gender.value if hasattr(gender, "value") else str(gender),
            race=race.value if hasattr(race, "value") else str(race),
            character_class=character_class.value
            if hasattr(character_class, "value")
            else str(character_class),
            age=age,
            level=level,
            **kwargs,
        )
