# mypy: ignore-errors

#!/usr/bin/env python3
"""
World Context Persistence Infrastructure

This module contains persistence implementations for the World context,
including repository implementations and database models.

Note: Models import is lazy to avoid SQLAlchemy metadata conflicts
when importing in-memory repositories that don't need database models.
"""

from typing import TYPE_CHECKING

from .in_memory_calendar_repository import InMemoryCalendarRepository
from .in_memory_event_repository import InMemoryEventRepository
from .in_memory_faction_intent_repository import InMemoryFactionIntentRepository
from .in_memory_location_repository import InMemoryLocationRepository
from .in_memory_rumor_repository import InMemoryRumorRepository

# Lazy imports to avoid SQLAlchemy initialization issues
# when only in-memory repositories are needed
if TYPE_CHECKING:
    from .models import WorldStateModel
    from .postgres_event_repository import PostgreSQLEventRepository
    from .postgres_rumor_repository import PostgreSQLRumorRepository
    from .postgres_world_state_repo import PostgresWorldStateRepository

__all__ = [
    "InMemoryCalendarRepository",
    "InMemoryEventRepository",
    "InMemoryFactionIntentRepository",
    "InMemoryLocationRepository",
    "InMemoryRumorRepository",
    "PostgresWorldStateRepository",
    "PostgreSQLEventRepository",
    "PostgreSQLRumorRepository",
    "WorldStateModel",
]


def __getattr__(name: str) -> None:
    """Lazy load modules on first access to avoid import-time issues."""
    if name == "WorldStateModel":
        from .models import WorldStateModel

        return WorldStateModel
    if name == "PostgresWorldStateRepository":
        from .postgres_world_state_repo import PostgresWorldStateRepository

        return PostgresWorldStateRepository
    if name == "PostgreSQLEventRepository":
        from .postgres_event_repository import PostgreSQLEventRepository

        return PostgreSQLEventRepository
    if name == "PostgreSQLRumorRepository":
        from .postgres_rumor_repository import PostgreSQLRumorRepository

        return PostgreSQLRumorRepository
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
