#!/usr/bin/env python3
"""
Character Profile Value Object

This module implements the CharacterProfile value object, representing the core
immutable characteristics of a character including identity, physical traits,
and personality attributes.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


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
    WARRIOR = "warrior"
    WIZARD = "wizard"
    MAGE = "mage"
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
        if self.height_cm is not None and (self.height_cm < 30 or self.height_cm > 300):
            raise ValueError("Height must be between 30-300 cm")

        if self.weight_kg is not None and (self.weight_kg < 5 or self.weight_kg > 500):
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
        """Validate personality traits."""
        if not self.traits:
            raise ValueError("Personality traits cannot be empty")

        for trait, score in self.traits.items():
            if not 0.0 <= score <= 1.0:
                raise ValueError(
                    f"Trait score for '{trait}' must be between 0.0 and 1.0, got {score}"
                )

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
    # New fields for WORLD-001: Enhanced character profiles
    aliases: Optional[List[str]] = None
    archetype: Optional[str] = None
    traits: Optional[List[str]] = None
    appearance: Optional[str] = None

    def __post_init__(self):
        """Validate character profile data."""
        # Validate required fields
        if not self.name or not self.name.strip():
            raise ValueError("Character name cannot be empty")

        if self.age < 0 or self.age > 10000:
            raise ValueError("Age must be between 0 and 10000")

        if self.level < 1 or self.level > 100:
            raise ValueError("Level must be between 1 and 100")

        # Validate name length
        if len(self.name.strip()) > 100:
            raise ValueError("Character name cannot exceed 100 characters")

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
            return language.lower() == "common"  # Assume common language by default

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
                self.personality_traits.traits.items(), key=lambda x: x[1], reverse=True
            )
            strong_traits = [trait for trait, _ in sorted_traits[:3]]

        return strong_traits
