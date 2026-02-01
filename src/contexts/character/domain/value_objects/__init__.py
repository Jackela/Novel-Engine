#!/usr/bin/env python3
"""
Character Domain Value Objects

This package contains immutable value objects that represent concepts
in the Character domain. Value objects are distinguished from entities
by having no identity and being immutable.

Value objects included:
- CharacterID: Unique identifier for characters
- CharacterProfile: Core character identity and traits
- CharacterStats: Abilities, health, mana, and combat statistics
- Skills: Character abilities and proficiencies
"""

from .character_id import CharacterID
from .character_profile import (
    Background,
    CharacterClass,
    CharacterProfile,
    CharacterRace,
    Gender,
    PersonalityTraits,
    PhysicalTraits,
)
from .character_stats import (
    AbilityScore,
    CharacterStats,
    CombatStats,
    CoreAbilities,
    VitalStats,
)
from .character_memory import CharacterMemory
from .character_psychology import CharacterPsychology
from .skills import ProficiencyLevel, Skill, SkillCategory, SkillGroup, Skills

__all__ = [
    "CharacterMemory",
    "CharacterPsychology",
    "CharacterID",
    "CharacterProfile",
    "Gender",
    "CharacterRace",
    "CharacterClass",
    "PhysicalTraits",
    "PersonalityTraits",
    "Background",
    "CharacterStats",
    "CoreAbilities",
    "VitalStats",
    "CombatStats",
    "AbilityScore",
    "Skills",
    "Skill",
    "SkillGroup",
    "SkillCategory",
    "ProficiencyLevel",
]
