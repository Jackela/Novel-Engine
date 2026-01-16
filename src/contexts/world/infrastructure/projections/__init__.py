#!/usr/bin/env python3
"""
World Context CQRS Projections Infrastructure

This package contains the CQRS read model and projection services
for the World context, providing optimized query performance through
denormalized data structures and event-driven consistency.
"""

from .world_projector import (
    WorldProjector,
    WorldProjectorException,
    get_world_projector,
    initialize_world_projector,
    shutdown_world_projector,
)
from .world_read_model import EntitySummary, WorldSliceReadModel

__all__ = [
    "WorldSliceReadModel",
    "EntitySummary",
    "WorldProjector",
    "WorldProjectorException",
    "get_world_projector",
    "initialize_world_projector",
    "shutdown_world_projector",
]
