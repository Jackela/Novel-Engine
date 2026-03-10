#!/usr/bin/env python3
"""
Character Infrastructure Layer

This package contains infrastructure implementations for the Character
bounded context, including persistence models, repository implementations,
and external service integrations.

Components:
- Persistence: SQLAlchemy ORM models and database configurations
- Repositories: Concrete implementations of domain repository interfaces
- Services: External service integrations and adapters

The infrastructure layer implements the interfaces defined in the domain
layer and provides concrete implementations for data persistence,
external communications, and other infrastructure concerns.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .persistence.character_models import (
        Base,
        CharacterEventORM,
        CharacterORM,
        CharacterProfileORM,
        CharacterSkillsORM,
        CharacterStatsORM,
    )
    from .repositories.character_repository import SQLAlchemyCharacterRepository

# Conditional imports to handle platform naming conflict
try:
    from .persistence.character_models import (
        Base,
        CharacterEventORM,
        CharacterORM,
        CharacterProfileORM,
        CharacterSkillsORM,
        CharacterStatsORM,
    )
    from .repositories.character_repository import SQLAlchemyCharacterRepository

    _IMPORTS_AVAILABLE: bool = True
except ImportError:
    # Handle platform naming conflict gracefully
    SQLAlchemyCharacterRepository = None  # type: ignore[assignment,misc]
    CharacterORM = None  # type: ignore[assignment,misc]
    CharacterProfileORM = None  # type: ignore[assignment,misc]
    CharacterStatsORM = None  # type: ignore[assignment,misc]
    CharacterSkillsORM = None  # type: ignore[assignment,misc]
    CharacterEventORM = None  # type: ignore[assignment,misc]
    Base = None  # type: ignore[assignment,misc]
    _IMPORTS_AVAILABLE = False

__all__ = [
    "SQLAlchemyCharacterRepository",
    "CharacterORM",
    "CharacterProfileORM",
    "CharacterStatsORM",
    "CharacterSkillsORM",
    "CharacterEventORM",
    "Base",
    "_IMPORTS_AVAILABLE",
]
