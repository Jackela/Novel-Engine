#!/usr/bin/env python3
"""Rumor Repository Port

This module defines the repository port (interface) for Rumor persistence.
Following Hexagonal Architecture, this port defines the contract that
infrastructure implementations must fulfill, keeping the domain layer
pure and independent of persistence details.

The RumorRepository follows the Repository Pattern, providing an
abstraction for storing and retrieving Rumor entities.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.contexts.world.domain.entities.rumor import Rumor


class RumorRepository(ABC):
    """Abstract repository port for Rumor persistence.

    This interface defines the contract for rumor storage operations.
    Implementations can use different storage backends (in-memory, database, etc.)
    while the domain layer remains decoupled from infrastructure concerns.

    Key constraints enforced by implementations:
        - Rumors have truth values that decay as they spread
        - Active rumors are those with truth_value > 0
        - Rumors are immutable; updates create new instances
    """

    @abstractmethod
    async def get_by_id(self, rumor_id: str) -> Optional[Rumor]:
        """Retrieve a specific rumor by its ID.

        Args:
            rumor_id: Unique identifier for the rumor

        Returns:
            Rumor if found, None otherwise

        Example:
            >>> rumor = await repository.get_by_id("rumor-uuid")
            >>> if rumor:
            ...     print(rumor.content)
        """
        pass

    @abstractmethod
    async def get_active_rumors(self, world_id: str) -> List[Rumor]:
        """Retrieve all active rumors for a world (truth_value > 0).

        Active rumors are those that still have some truth value
        and can continue spreading through the world.

        Args:
            world_id: ID of the world

        Returns:
            List of active Rumor objects (truth_value > 0)

        Example:
            >>> active = await repository.get_active_rumors("world-1")
            >>> print(f"{len(active)} rumors currently spreading")
        """
        pass

    @abstractmethod
    async def get_by_world_id(self, world_id: str) -> List[Rumor]:
        """Retrieve all rumors for a specific world (including dead ones).

        Args:
            world_id: ID of the world

        Returns:
            List of all Rumor objects in the world

        Example:
            >>> rumors = await repository.get_by_world_id("world-1")
            >>> print(f"World has {len(rumors)} total rumors")
        """
        pass

    @abstractmethod
    async def save(self, rumor: Rumor) -> Rumor:
        """Persist a rumor.

        If a rumor with the same rumor_id exists, it will be updated.
        Otherwise, a new rumor is created.

        Args:
            rumor: The Rumor to persist

        Returns:
            The saved Rumor

        Example:
            >>> rumor = Rumor(
            ...     content="A dragon has been sighted...",
            ...     truth_value=75,
            ...     origin_location_id="loc-1"
            ... )
            >>> saved = await repository.save(rumor)
        """
        pass

    @abstractmethod
    async def save_all(self, rumors: List[Rumor]) -> List[Rumor]:
        """Persist multiple rumors in a single operation.

        This is more efficient than calling save() multiple times,
        especially for database implementations that can batch inserts.

        Args:
            rumors: List of Rumor objects to persist

        Returns:
            List of saved Rumor objects

        Example:
            >>> rumors = [rumor1, rumor2, rumor3]
            >>> saved = await repository.save_all(rumors)
        """
        pass

    @abstractmethod
    async def delete(self, rumor_id: str) -> bool:
        """Remove a rumor from the repository.

        Args:
            rumor_id: Unique identifier for the rumor

        Returns:
            True if rumor was deleted, False if it didn't exist

        Example:
            >>> deleted = await repository.delete("rumor-uuid")
            >>> if deleted:
            ...     print("Rumor removed")
        """
        pass

    @abstractmethod
    async def get_by_location_id(self, location_id: str) -> List[Rumor]:
        """Retrieve all rumors currently at a specific location.

        Args:
            location_id: ID of the location

        Returns:
            List of Rumor objects that have spread to this location

        Example:
            >>> rumors = await repository.get_by_location_id("loc-1")
            >>> print(f"Location has {len(rumors)} circulating rumors")
        """
        pass

    @abstractmethod
    async def get_by_event_id(self, event_id: str) -> List[Rumor]:
        """Retrieve all rumors originating from a specific event.

        Args:
            event_id: ID of the source event

        Returns:
            List of Rumor objects that originated from this event

        Example:
            >>> rumors = await repository.get_by_event_id("event-1")
            >>> print(f"Event spawned {len(rumors)} rumors")
        """
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all rumors from the repository.

        This is a utility method primarily used for testing.
        """
        pass
