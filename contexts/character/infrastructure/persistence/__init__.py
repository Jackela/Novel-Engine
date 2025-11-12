#!/usr/bin/env python3
"""
Character Persistence Layer

This package contains SQLAlchemy ORM models and database configurations
for the Character bounded context. It provides the data persistence
infrastructure for Character aggregates and related entities.

Components:
- models: SQLAlchemy ORM model definitions
- mappers: Domain object to ORM model mapping utilities
- migrations: Database schema migrations (future)

The persistence layer bridges the domain model and the database,
providing object-relational mapping and data access capabilities.
"""

# Conditional import to handle platform naming conflict
try:
    from .character_models import (
        CharacterORM,
        CharacterProfileORM,
        CharacterSkillsORM,
        CharacterStatsORM,
    )

    _MODELS_AVAILABLE = True
except ImportError:
    # Handle platform naming conflict gracefully
    CharacterORM = None
    CharacterProfileORM = None
    CharacterStatsORM = None
    CharacterSkillsORM = None
    _MODELS_AVAILABLE = False

__all__ = [
    "CharacterORM",
    "CharacterProfileORM",
    "CharacterStatsORM",
    "CharacterSkillsORM",
]
