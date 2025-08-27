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
try:
    from .repositories.character_repository import SQLAlchemyCharacterRepository
    from .persistence.character_models import (
        CharacterORM, CharacterProfileORM, CharacterStatsORM, 
        CharacterSkillsORM, CharacterEventORM, Base
    )
    _IMPORTS_AVAILABLE = True
except ImportError as e:
    # Handle platform naming conflict gracefully
    SQLAlchemyCharacterRepository = None
    CharacterORM = None
    CharacterProfileORM = None
    CharacterStatsORM = None
    CharacterSkillsORM = None
    CharacterEventORM = None
    Base = None
    _IMPORTS_AVAILABLE = False

__all__ = [
    "SQLAlchemyCharacterRepository",
    "CharacterORM",
    "CharacterProfileORM", 
    "CharacterStatsORM",
    "CharacterSkillsORM",
    "CharacterEventORM",
    "Base",
    "_IMPORTS_AVAILABLE"
]