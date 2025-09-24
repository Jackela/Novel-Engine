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

# Conditional imports to handle platform naming conflict
from typing import Any, Optional, Type

try:
    from .persistence.character_models import (
        Base,
        CharacterEventORM,
        CharacterORM,
        CharacterProfileORM,
        CharacterSkillsORM,
        CharacterStatsORM,
    )
    from .repositories.character_repository import (
        SQLAlchemyCharacterRepository,
    )

    _IMPORTS_AVAILABLE = True
except ImportError:
    # Handle platform naming conflict gracefully
    SQLAlchemyCharacterRepository: Optional[Type[Any]] = None  # type: ignore
    CharacterORM: Optional[Type[Any]] = None  # type: ignore
    CharacterProfileORM: Optional[Type[Any]] = None  # type: ignore
    CharacterStatsORM: Optional[Type[Any]] = None  # type: ignore
    CharacterSkillsORM: Optional[Type[Any]] = None  # type: ignore
    CharacterEventORM: Optional[Type[Any]] = None  # type: ignore
    Base: Optional[Type[Any]] = None  # type: ignore
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
