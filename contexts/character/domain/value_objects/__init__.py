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
    CharacterProfile, Gender, CharacterRace, CharacterClass,
    PhysicalTraits, PersonalityTraits, Background
)
from .character_stats import (
    CharacterStats, CoreAbilities, VitalStats, CombatStats,
    AbilityScore
)
from .skills import (
    Skills, Skill, SkillGroup, SkillCategory, ProficiencyLevel
)

__all__ = [
    "CharacterID",
    "CharacterProfile", "Gender", "CharacterRace", "CharacterClass",
    "PhysicalTraits", "PersonalityTraits", "Background",
    "CharacterStats", "CoreAbilities", "VitalStats", "CombatStats", "AbilityScore",
    "Skills", "Skill", "SkillGroup", "SkillCategory", "ProficiencyLevel",
]