#!/usr/bin/env python3
"""In-Memory Location Repository Implementation.

This module provides an in-memory implementation of LocationRepository
suitable for testing, development, and lightweight deployments.

Why in-memory first: Enables rapid iteration and testing without database
setup. The repository interface ensures we can swap to PostgreSQL later
without changing domain or application code.
"""

import threading
from typing import Dict, List, Optional, Set

import structlog

from src.contexts.world.domain.entities.location import Location
from src.contexts.world.domain.ports.location_repository import LocationRepository

logger = structlog.get_logger()


class InMemoryLocationRepository(LocationRepository):
    """In-memory implementation of LocationRepository.

    Stores locations in dictionaries indexed by location_id with additional
    indexes for efficient lookups by world_id and parent_id.

    Thread Safety:
        This implementation IS thread-safe. All operations are protected
        by a reentrant lock (RLock) to ensure safe concurrent access.

    Attributes:
        _locations: Dictionary mapping location_id to Location
        _world_locations: Dictionary mapping world_id to set of location_ids
        _parent_children: Dictionary mapping parent_id to set of child location_ids
        _lock: Reentrant lock for thread-safe access
    """

    def __init__(self) -> None:
        """Initialize the repository with empty storage and thread lock."""
        self._locations: Dict[str, Location] = {}
        self._world_locations: Dict[str, Set[str]] = {}
        self._parent_children: Dict[str, Set[str]] = {}
        self._lock = threading.RLock()
        logger.debug("in_memory_location_repository_initialized")

    async def get_by_id(self, location_id: str) -> Optional[Location]:
        """Retrieve a specific location by its ID.

        Args:
            location_id: Unique identifier for the location

        Returns:
            Location if found, None otherwise
        """
        with self._lock:
            return self._locations.get(location_id)

    async def get_by_world_id(self, world_id: str) -> List[Location]:
        """Retrieve all locations for a specific world.

        Args:
            world_id: ID of the world

        Returns:
            List of Location objects in the world
        """
        with self._lock:
            location_ids = self._world_locations.get(world_id, set())
            locations = [
                self._locations[loc_id]
                for loc_id in location_ids
                if loc_id in self._locations
            ]
            # Sort by name
            locations.sort(key=lambda loc: loc.name)
            return locations

    async def save(self, location: Location) -> Location:
        """Persist a location.

        Args:
            location: The Location to persist

        Returns:
            The saved Location
        """
        with self._lock:
            is_new = location.id not in self._locations
            old_location = self._locations.get(location.id)

            self._locations[location.id] = location

            # Update parent-child index
            # Remove from old parent's children if parent changed
            if old_location and old_location.parent_location_id:
                old_parent_id = old_location.parent_location_id
                if old_parent_id in self._parent_children:
                    self._parent_children[old_parent_id].discard(location.id)

            # Add to new parent's children
            if location.parent_location_id:
                parent_id = location.parent_location_id
                if parent_id not in self._parent_children:
                    self._parent_children[parent_id] = set()
                self._parent_children[parent_id].add(location.id)

            logger.debug(
                "location_saved",
                location_id=location.id,
                location_name=location.name,
                is_new=is_new,
            )
            return location

    async def delete(self, location_id: str) -> bool:
        """Remove a location from the repository.

        Args:
            location_id: Unique identifier for the location

        Returns:
            True if location was deleted, False if it didn't exist
        """
        with self._lock:
            location = self._locations.get(location_id)
            if location is None:
                return False

            del self._locations[location_id]

            # Remove from world index
            for world_id in list(self._world_locations.keys()):
                self._world_locations[world_id].discard(location_id)

            # Remove from parent index
            if (
                location.parent_location_id
                and location.parent_location_id in self._parent_children
            ):
                self._parent_children[location.parent_location_id].discard(location_id)

            # Remove this location as parent from other locations
            if location_id in self._parent_children:
                del self._parent_children[location_id]

            logger.debug("location_deleted", location_id=location_id)
            return True

    async def find_adjacent(self, location_id: str) -> List[str]:
        """Find all locations adjacent to the given location.

        Adjacent locations are those that:
        1. Share the same parent_id (siblings)
        2. Have a parent-child relationship
        3. Are explicitly connected via the connections list

        Args:
            location_id: ID of the location to find adjacents for

        Returns:
            List of adjacent location IDs
        """
        with self._lock:
            location = self._locations.get(location_id)
            if location is None:
                return []

            adjacent: Set[str] = set()

            # 1. Add siblings (same parent)
            if location.parent_location_id:
                parent_id = location.parent_location_id
                siblings = self._parent_children.get(parent_id, set())
                adjacent.update(siblings)

            # 2. Add parent (if exists)
            if location.parent_location_id:
                adjacent.add(location.parent_location_id)

            # 3. Add children (locations that have this as parent)
            children = self._parent_children.get(location_id, set())
            adjacent.update(children)

            # 4. Add explicitly connected locations
            adjacent.update(location.connections)

            # Remove self from adjacent set
            adjacent.discard(location_id)

            # Verify all adjacent locations exist
            valid_adjacent = [
                loc_id for loc_id in adjacent if loc_id in self._locations
            ]

            return valid_adjacent

    async def get_children(self, parent_id: str) -> List[Location]:
        """Retrieve all child locations of a parent location.

        Args:
            parent_id: ID of the parent location

        Returns:
            List of Location objects that have this location as parent
        """
        with self._lock:
            child_ids = self._parent_children.get(parent_id, set())
            children = [
                self._locations[loc_id]
                for loc_id in child_ids
                if loc_id in self._locations
            ]
            # Sort by name
            children.sort(key=lambda loc: loc.name)
            return children

    async def get_by_type(self, world_id: str, location_type: str) -> List[Location]:
        """Retrieve all locations of a specific type in a world.

        Args:
            world_id: ID of the world
            location_type: Type of location (e.g., "city", "dungeon")

        Returns:
            List of Location objects of the specified type
        """
        with self._lock:
            location_ids = self._world_locations.get(world_id, set())
            locations = [
                self._locations[loc_id]
                for loc_id in location_ids
                if loc_id in self._locations
                and self._locations[loc_id].location_type.value == location_type
            ]
            # Sort by name
            locations.sort(key=lambda loc: loc.name)
            return locations

    async def clear(self) -> None:
        """Clear all locations from the repository."""
        with self._lock:
            self._locations.clear()
            self._world_locations.clear()
            self._parent_children.clear()
            logger.debug("all_locations_cleared")

    def register_location_world(self, location_id: str, world_id: str) -> None:
        """Explicitly register a location as belonging to a world.

        Since Location entity doesn't have a world_id field, use this
        method to associate locations with worlds for get_by_world_id queries.

        Args:
            location_id: ID of the location
            world_id: ID of the world
        """
        with self._lock:
            if world_id not in self._world_locations:
                self._world_locations[world_id] = set()
            self._world_locations[world_id].add(location_id)
            logger.debug(
                "location_registered_to_world",
                world_id=world_id,
                location_id=location_id,
            )
