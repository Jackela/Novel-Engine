#!/usr/bin/env python3
"""Location Repository Port

This module defines the repository port (interface) for Location persistence.
Following Hexagonal Architecture, this port defines the contract that
infrastructure implementations must fulfill, keeping the domain layer
pure and independent of persistence details.

The LocationRepository follows the Repository Pattern, providing an
abstraction for storing and retrieving Location entities.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.contexts.world.domain.entities.location import Location


class LocationRepository(ABC):
    """Abstract repository port for Location persistence.

    This interface defines the contract for location storage operations.
    Implementations can use different storage backends (in-memory, database, etc.)
    while the domain layer remains decoupled from infrastructure concerns.
    """

    @abstractmethod
    async def get_by_id(self, location_id: str) -> Optional[Location]:
        """Retrieve a specific location by its ID.

        Args:
            location_id: Unique identifier for the location

        Returns:
            Location if found, None otherwise

        Example:
            >>> location = await repository.get_by_id("loc-uuid")
            >>> if location:
            ...     print(location.name)
        """
        pass

    @abstractmethod
    async def get_by_world_id(self, world_id: str) -> List[Location]:
        """Retrieve all locations for a specific world.

        Args:
            world_id: ID of the world

        Returns:
            List of Location objects in the world

        Example:
            >>> locations = await repository.get_by_world_id("world-1")
            >>> print(f"World has {len(locations)} locations")
        """
        pass

    @abstractmethod
    async def save(self, location: Location) -> Location:
        """Persist a location.

        If a location with the same id exists, it will be updated.
        Otherwise, a new location is created.

        Args:
            location: The Location to persist

        Returns:
            The saved Location

        Example:
            >>> location = Location(name="Thornhaven", world_id="world-1")
            >>> saved = await repository.save(location)
        """
        pass

    @abstractmethod
    async def delete(self, location_id: str) -> bool:
        """Remove a location from the repository.

        Args:
            location_id: Unique identifier for the location

        Returns:
            True if location was deleted, False if it didn't exist

        Example:
            >>> deleted = await repository.delete("loc-uuid")
            >>> if deleted:
            ...     print("Location removed")
        """
        pass

    @abstractmethod
    async def find_adjacent(self, location_id: str) -> List[str]:
        """Find all locations adjacent to the given location.

        Adjacent locations are those that share the same parent_id,
        or have a parent-child relationship, or are explicitly connected
        via the connections list.

        This method is used primarily for rumor propagation and
        pathfinding algorithms.

        Args:
            location_id: ID of the location to find adjacents for

        Returns:
            List of adjacent location IDs

        Example:
            >>> adjacent = await repository.find_adjacent("city-1")
            >>> print(f"Adjacent locations: {adjacent}")
        """
        pass

    @abstractmethod
    async def get_children(self, parent_id: str) -> List[Location]:
        """Retrieve all child locations of a parent location.

        Args:
            parent_id: ID of the parent location

        Returns:
            List of Location objects that have this location as parent

        Example:
            >>> children = await repository.get_children("region-1")
            >>> print(f"Region contains {len(children)} sub-locations")
        """
        pass

    @abstractmethod
    async def get_by_type(
        self, world_id: str, location_type: str
    ) -> List[Location]:
        """Retrieve all locations of a specific type in a world.

        Args:
            world_id: ID of the world
            location_type: Type of location (e.g., "city", "dungeon")

        Returns:
            List of Location objects of the specified type

        Example:
            >>> cities = await repository.get_by_type("world-1", "city")
            >>> print(f"World has {len(cities)} cities")
        """
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all locations from the repository.

        This is a utility method primarily used for testing.
        """
        pass
