"""Shared in-memory storage for world-related routers.

This module provides shared in-memory storage for world events and rumors.
Used by world_events.py and world_rumors.py routers (MVP implementation).
"""

from typing import Any, Dict, List

# Events storage: world_id -> list of events
_events_storage: Dict[str, List[Dict[str, Any]]] = {}

# Rumors storage: world_id -> list of rumors
_rumors_storage: Dict[str, List[Dict[str, Any]]] = {}


def get_events_storage(world_id: str) -> List[Dict[str, Any]]:
    """Get or create events storage for a world.

    Args:
        world_id: Unique identifier for the world

    Returns:
        List of events for the world
    """
    if world_id not in _events_storage:
        _events_storage[world_id] = []
    return _events_storage[world_id]


def get_rumors_storage(world_id: str) -> List[Dict[str, Any]]:
    """Get or create rumors storage for a world.

    Args:
        world_id: Unique identifier for the world

    Returns:
        List of rumors for the world
    """
    if world_id not in _rumors_storage:
        _rumors_storage[world_id] = []
    return _rumors_storage[world_id]


def reset_events_storage() -> None:
    """Reset events storage (for testing)."""
    global _events_storage
    _events_storage = {}
def reset_rumors_storage() -> None:
    """Reset rumors storage (for testing)."""
    global _rumors_storage
    _rumors_storage = {}
def reset_all_storage() -> None:
    """Reset all world storage (for testing)."""
    reset_events_storage()
    reset_rumors_storage()
