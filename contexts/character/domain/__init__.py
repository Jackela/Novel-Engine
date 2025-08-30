#!/usr/bin/env python3
"""
Character Domain Layer

This package contains the core domain logic for the Character bounded context,
including aggregates, value objects, domain events, and repository interfaces.

Following DDD principles, this layer:
- Contains business rules and invariants
- Defines domain entities and value objects
- Raises domain events for important state changes
- Declares repository contracts (interfaces)
- Is independent of infrastructure concerns
"""

from .aggregates.character import Character
from .events.character_events import (
    CharacterCreated,
    CharacterDeleted,
    CharacterEvent,
    CharacterLeveledUp,
    CharacterStatsChanged,
    CharacterUpdated,
)
from .repositories.character_repository import (
    ConcurrencyException,
    ICharacterRepository,
    NotSupportedException,
    RepositoryException,
)
from .value_objects.character_id import CharacterID
from .value_objects.character_profile import (
    Background,
    CharacterClass,
    CharacterProfile,
    CharacterRace,
    Gender,
    PersonalityTraits,
    PhysicalTraits,
)
from .value_objects.character_stats import (
    AbilityScore,
    CharacterStats,
    CombatStats,
    CoreAbilities,
    VitalStats,
)
from .value_objects.skills import (
    ProficiencyLevel,
    Skill,
    SkillCategory,
    SkillGroup,
    Skills,
)

__all__ = [
    # Aggregates
    "Character",
    # Value Objects
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
    # Domain Events
    "CharacterEvent",
    "CharacterCreated",
    "CharacterUpdated",
    "CharacterStatsChanged",
    "CharacterLeveledUp",
    "CharacterDeleted",
    # Repository Interface
    "ICharacterRepository",
    "RepositoryException",
    "ConcurrencyException",
    "NotSupportedException",
]
