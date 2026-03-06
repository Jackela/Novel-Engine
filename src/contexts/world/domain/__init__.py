"""World domain package.

This package contains domain models, entities, aggregates, value objects,
events, and errors for the world context.
"""

from src.contexts.world.domain.errors import (
    DiplomacyError,
    EventError,
    EventNotFoundError,
    EventValidationError,
    FactionError,
    FactionNotFoundError,
    FactionTickError,
    FactionValidationError,
    GeopoliticsError,
    IntentGenerationError,
    LocationError,
    LocationNotFoundError,
    LocationValidationError,
    RepositoryError,
    RumorCreationError,
    RumorError,
    RumorNotFoundError,
    RumorPropagationError,
    RumorValidationError,
    SanityCheckError,
    SimulationError,
    SimulationValidationError,
    SnapshotError,
    SnapshotNotFoundError,
    SocialGraphError,
    TimeError,
    TimeValidationError,
    ValidationError,
    WorldError,
    WorldNotFoundError,
    WorldValidationError,
)

__all__ = [
    # World Errors
    "WorldError",
    "WorldNotFoundError",
    "WorldValidationError",
    # Event Errors
    "EventError",
    "EventNotFoundError",
    "EventValidationError",
    # Location Errors
    "LocationError",
    "LocationNotFoundError",
    "LocationValidationError",
    # Faction Errors
    "FactionError",
    "FactionNotFoundError",
    "FactionValidationError",
    "FactionTickError",
    # Geopolitics Errors
    "GeopoliticsError",
    "DiplomacyError",
    # Simulation Errors
    "SimulationError",
    "SimulationValidationError",
    "SanityCheckError",
    # Snapshot Errors
    "SnapshotError",
    "SnapshotNotFoundError",
    # Rumor Errors
    "RumorError",
    "RumorNotFoundError",
    "RumorValidationError",
    "RumorPropagationError",
    "RumorCreationError",
    # Time Errors
    "TimeError",
    "TimeValidationError",
    # Intent Errors
    "IntentGenerationError",
    # Social Graph Errors
    "SocialGraphError",
    # Generic Errors
    "RepositoryError",
    "ValidationError",
]
