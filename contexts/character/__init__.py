#!/usr/bin/env python3
"""
Character Bounded Context

This package implements the Character bounded context following Domain-Driven
Design (DDD) principles. It provides a complete character management system
with proper separation of concerns between domain, application, and
infrastructure layers.

The Character context handles:
- Character creation and management
- Character statistics and progression
- Character skills and abilities
- Character profile and background information
- Character domain events and business rules

Architecture:
- Domain Layer: Aggregates, value objects, domain events, and repository interfaces
- Application Layer: Commands, queries, use cases, and application services
- Infrastructure Layer: Repository implementations and persistence models
"""

from .application.commands.character_commands import (
    CreateCharacterCommand,
    DamageCharacterCommand,
    DeleteCharacterCommand,
    HealCharacterCommand,
    LevelUpCharacterCommand,
    UpdateCharacterSkillCommand,
    UpdateCharacterStatsCommand,
)

# Application Layer Exports
from .application.services.character_application_service import (
    CharacterApplicationService,
)

# Domain Layer Exports
from .domain.aggregates.character import Character
from .domain.repositories.character_repository import ICharacterRepository
from .domain.value_objects.character_id import CharacterID
from .domain.value_objects.character_profile import (
    CharacterClass,
    CharacterProfile,
    CharacterRace,
    Gender,
)
from .domain.value_objects.character_stats import CharacterStats
from .domain.value_objects.skills import Skills

# Infrastructure Layer Exports (conditional import due to platform naming conflict)
try:
    from .infrastructure.persistence.character_models import (
        Base as CharacterBase,
    )
    from .infrastructure.repositories.character_repository import (
        SQLAlchemyCharacterRepository,
    )

    INFRASTRUCTURE_AVAILABLE = True
except ImportError as e:
    # Handle gracefully if SQLAlchemy imports fail due to platform naming conflict
    from typing import Any, Optional, Type

    SQLAlchemyCharacterRepository: Optional[Type[Any]] = None  # type: ignore
    CharacterBase: Optional[Type[Any]] = None  # type: ignore
    INFRASTRUCTURE_AVAILABLE = False
    import warnings

    warnings.warn(
        f"Character infrastructure layer not available due to import error: {e}"
    )

# Build __all__ list dynamically based on available imports
__all__ = [
    # Domain Layer
    "Character",
    "CharacterID",
    "CharacterProfile",
    "CharacterStats",
    "Skills",
    "Gender",
    "CharacterRace",
    "CharacterClass",
    "ICharacterRepository",
    # Application Layer
    "CharacterApplicationService",
    "CreateCharacterCommand",
    "UpdateCharacterStatsCommand",
    "UpdateCharacterSkillCommand",
    "LevelUpCharacterCommand",
    "DeleteCharacterCommand",
    "HealCharacterCommand",
    "DamageCharacterCommand",
    # Availability flag
    "INFRASTRUCTURE_AVAILABLE",
]

# Add infrastructure components if available
if INFRASTRUCTURE_AVAILABLE:
    __all__.extend(["SQLAlchemyCharacterRepository", "CharacterBase"])
