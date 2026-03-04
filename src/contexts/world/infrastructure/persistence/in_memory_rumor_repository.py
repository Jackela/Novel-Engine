#!/usr/bin/env python3
"""In-Memory Rumor Repository Implementation.

This module provides an in-memory implementation of RumorRepository
suitable for testing, development, and lightweight deployments.

Why in-memory first: Enables rapid iteration and testing without database
setup. The repository interface ensures we can swap to PostgreSQL later
without changing domain or application code.
"""

import threading
from typing import Dict, List, Optional, Set

import structlog

from src.contexts.world.domain.entities.rumor import Rumor
from src.contexts.world.domain.ports.rumor_repository import RumorRepository

logger = structlog.get_logger()


class InMemoryRumorRepository(RumorRepository):
    """In-memory implementation of RumorRepository.

    Stores rumors in dictionaries indexed by rumor_id with additional
    indexes for efficient lookups by world_id, location_id, and event_id.

    Thread Safety:
        This implementation IS thread-safe. All operations are protected
        by a reentrant lock (RLock) to ensure safe concurrent access.

    Attributes:
        _rumors: Dictionary mapping rumor_id to Rumor
        _world_rumors: Dictionary mapping world_id to set of rumor_ids
        _location_rumors: Dictionary mapping location_id to set of rumor_ids
        _event_rumors: Dictionary mapping event_id to set of rumor_ids
        _lock: Reentrant lock for thread-safe access
    """

    def __init__(self) -> None:
        """Initialize the repository with empty storage and thread lock."""
        self._rumors: Dict[str, Rumor] = {}
        self._world_rumors: Dict[str, Set[str]] = {}
        self._location_rumors: Dict[str, Set[str]] = {}
        self._event_rumors: Dict[str, Set[str]] = {}
        # Map to track explicit world registration for rumors
        self._rumor_to_world: Dict[str, str] = {}
        self._lock = threading.RLock()
        logger.debug("in_memory_rumor_repository_initialized")

    async def get_by_id(self, rumor_id: str) -> Optional[Rumor]:
        """Retrieve a specific rumor by its ID.

        Args:
            rumor_id: Unique identifier for the rumor

        Returns:
            Rumor if found, None otherwise
        """
        with self._lock:
            return self._rumors.get(rumor_id)

    async def get_active_rumors(self, world_id: str) -> List[Rumor]:
        """Retrieve all active rumors for a world (truth_value > 0).

        Args:
            world_id: ID of the world

        Returns:
            List of active Rumor objects (truth_value > 0)
        """
        with self._lock:
            rumor_ids = self._world_rumors.get(world_id, set())
            rumors = [
                self._rumors[rid]
                for rid in rumor_ids
                if rid in self._rumors and self._rumors[rid].truth_value > 0
            ]
            # Sort by truth value (descending), then by spread count
            rumors.sort(key=lambda r: (-r.truth_value, -r.spread_count))
            return rumors

    async def get_by_world_id(self, world_id: str) -> List[Rumor]:
        """Retrieve all rumors for a specific world (including dead ones).

        Args:
            world_id: ID of the world

        Returns:
            List of all Rumor objects in the world
        """
        with self._lock:
            rumor_ids = self._world_rumors.get(world_id, set())
            rumors = [self._rumors[rid] for rid in rumor_ids if rid in self._rumors]
            # Sort by truth value (descending)
            rumors.sort(key=lambda r: -r.truth_value)
            return rumors

    async def save(self, rumor: Rumor) -> Rumor:
        """Persist a rumor.

        Args:
            rumor: The Rumor to persist

        Returns:
            The saved Rumor
        """
        with self._lock:
            is_new = rumor.rumor_id not in self._rumors
            self._rumors[rumor.rumor_id] = rumor

            # Update indexes
            self._update_indexes(rumor)

            logger.debug(
                "rumor_saved",
                rumor_id=rumor.rumor_id,
                truth_value=rumor.truth_value,
                spread_count=rumor.spread_count,
                is_new=is_new,
            )
            return rumor

    async def save_all(self, rumors: List[Rumor]) -> List[Rumor]:
        """Persist multiple rumors in a single operation.

        Optimized to minimize lock contention and index updates.

        Args:
            rumors: List of Rumor objects to persist

        Returns:
            List of saved Rumor objects
        """
        with self._lock:
            # Process all rumors in a single lock acquisition
            for rumor in rumors:
                # Store the rumor
                self._rumors[rumor.rumor_id] = rumor

                # Update indexes
                self._update_indexes(rumor)

            logger.info(
                "rumors_batch_saved",
                count=len(rumors),
            )
            return list(rumors)

    async def delete(self, rumor_id: str) -> bool:
        """Remove a rumor from the repository.

        Args:
            rumor_id: Unique identifier for the rumor

        Returns:
            True if rumor was deleted, False if it didn't exist
        """
        with self._lock:
            rumor = self._rumors.get(rumor_id)
            if rumor is None:
                return False

            del self._rumors[rumor_id]

            # Remove from all indexes
            self._remove_from_indexes(rumor_id, rumor)

            logger.debug("rumor_deleted", rumor_id=rumor_id)
            return True

    async def get_by_location_id(self, location_id: str) -> List[Rumor]:
        """Retrieve all rumors currently at a specific location.

        Args:
            location_id: ID of the location

        Returns:
            List of Rumor objects that have spread to this location
        """
        with self._lock:
            rumor_ids = self._location_rumors.get(location_id, set())
            rumors = [self._rumors[rid] for rid in rumor_ids if rid in self._rumors]
            # Sort by truth value (descending)
            rumors.sort(key=lambda r: -r.truth_value)
            return rumors

    async def get_by_event_id(self, event_id: str) -> List[Rumor]:
        """Retrieve all rumors originating from a specific event.

        Args:
            event_id: ID of the source event

        Returns:
            List of Rumor objects that originated from this event
        """
        with self._lock:
            rumor_ids = self._event_rumors.get(event_id, set())
            rumors = [self._rumors[rid] for rid in rumor_ids if rid in self._rumors]
            # Sort by truth value (descending)
            rumors.sort(key=lambda r: -r.truth_value)
            return rumors

    async def clear(self) -> None:
        """Clear all rumors from the repository."""
        with self._lock:
            self._rumors.clear()
            self._world_rumors.clear()
            self._location_rumors.clear()
            self._event_rumors.clear()
            logger.debug("all_rumors_cleared")

    def _update_indexes(self, rumor: Rumor) -> None:
        """Update all indexes for a rumor.

        Args:
            rumor: The Rumor to index
        """
        # Index by origin location (treat location as world proxy)
        world_id = self._derive_world_id(rumor)
        if world_id:
            if world_id not in self._world_rumors:
                self._world_rumors[world_id] = set()
            self._world_rumors[world_id].add(rumor.rumor_id)

        # Index by current locations
        for loc_id in rumor.current_locations:
            if loc_id not in self._location_rumors:
                self._location_rumors[loc_id] = set()
            self._location_rumors[loc_id].add(rumor.rumor_id)

        # Index by source event
        if rumor.source_event_id:
            if rumor.source_event_id not in self._event_rumors:
                self._event_rumors[rumor.source_event_id] = set()
            self._event_rumors[rumor.source_event_id].add(rumor.rumor_id)

    def _remove_from_indexes(self, rumor_id: str, rumor: Rumor) -> None:
        """Remove a rumor from all indexes.

        Args:
            rumor_id: ID of the rumor to remove
            rumor: The Rumor object (for index lookup)
        """
        # Remove from world index
        world_id = self._derive_world_id(rumor)
        if world_id and world_id in self._world_rumors:
            self._world_rumors[world_id].discard(rumor_id)

        # Remove from location indexes
        for loc_id in rumor.current_locations:
            if loc_id in self._location_rumors:
                self._location_rumors[loc_id].discard(rumor_id)

        # Remove from event index
        if rumor.source_event_id and rumor.source_event_id in self._event_rumors:
            self._event_rumors[rumor.source_event_id].discard(rumor_id)

    def _derive_world_id(self, rumor: Rumor) -> Optional[str]:
        """Derive a world_id from the rumor.

        First checks if the rumor has been explicitly registered to a world,
        then falls back to using origin_location_id as a proxy.

        Args:
            rumor: The Rumor to derive world_id from

        Returns:
            World ID string or None
        """
        # First check explicit registration
        if rumor.rumor_id in self._rumor_to_world:
            return self._rumor_to_world[rumor.rumor_id]
        # Fall back to origin_location_id as world proxy
        return rumor.origin_location_id or None

    def register_rumor_world(self, rumor_id: str, world_id: str) -> None:
        """Explicitly register a rumor as belonging to a world.

        This is a helper method since Rumor doesn't have a world_id field.
        Call this to explicitly associate a rumor with a world.

        Args:
            rumor_id: ID of the rumor
            world_id: ID of the world
        """
        with self._lock:
            if world_id not in self._world_rumors:
                self._world_rumors[world_id] = set()
            self._world_rumors[world_id].add(rumor_id)
            # Track the world mapping for consistent lookups
            self._rumor_to_world[rumor_id] = world_id
            logger.debug(
                "rumor_registered_to_world",
                world_id=world_id,
                rumor_id=rumor_id,
            )
