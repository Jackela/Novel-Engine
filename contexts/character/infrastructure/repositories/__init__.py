#!/usr/bin/env python3
"""
Character Repository Implementations

This package contains concrete implementations of repository interfaces
defined in the domain layer. The repositories handle data persistence
and retrieval using SQLAlchemy ORM models.

Components:
- character_repository: Concrete implementation of ICharacterRepository
- mappers: Domain object to ORM model mapping utilities
- exceptions: Infrastructure-specific exception types

The repository implementations bridge the domain and infrastructure layers,
providing concrete persistence capabilities for domain aggregates.
"""

# Conditional import to handle platform naming conflict
from typing import Any, Optional, Type

try:
    from .character_repository import SQLAlchemyCharacterRepository

    _REPOSITORY_AVAILABLE = True
except ImportError:
    # Handle platform naming conflict gracefully
    SQLAlchemyCharacterRepository: Optional[Type[Any]] = None  # type: ignore
    _REPOSITORY_AVAILABLE = False

__all__ = ["SQLAlchemyCharacterRepository"]
