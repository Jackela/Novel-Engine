#!/usr/bin/env python3
"""
World Context Persistence Infrastructure

This module contains persistence implementations for the World context,
including repository implementations and database models.

Note: Models import is lazy to avoid SQLAlchemy metadata conflicts
when importing in-memory repositories that don't need database models.
"""

from typing import TYPE_CHECKING

# Lazy imports to avoid SQLAlchemy initialization issues
# when only in-memory repositories are needed
if TYPE_CHECKING:
    from .models import WorldStateModel
    from .postgres_world_state_repo import PostgresWorldStateRepository

__all__ = ["PostgresWorldStateRepository", "WorldStateModel"]


def __getattr__(name: str):
    """Lazy load modules on first access to avoid import-time issues."""
    if name == "WorldStateModel":
        from .models import WorldStateModel
        return WorldStateModel
    if name == "PostgresWorldStateRepository":
        from .postgres_world_state_repo import PostgresWorldStateRepository
        return PostgresWorldStateRepository
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
