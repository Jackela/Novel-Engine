#!/usr/bin/env python3
"""
World Domain Aggregates

This module exports all aggregates from the world context domain layer.
"""

from src.contexts.world.domain.aggregates.diplomacy_matrix import DiplomacyMatrix
from src.contexts.world.domain.aggregates.world_state import (
    EntityType,
    WorldEntity,
    WorldState,
    WorldStatus,
)

__all__ = [
    "DiplomacyMatrix",
    "EntityType",
    "WorldEntity",
    "WorldState",
    "WorldStatus",
]
