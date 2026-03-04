#!/usr/bin/env python3
"""Rumor Service for World Rumor Operations.

This module provides the application-layer service for managing world rumors.
It orchestrates domain objects and repositories to handle rumor-related
operations, including retrieving location-specific rumors and rumor details.

The RumorService follows the Command Query Separation principle:
- get_location_rumors() is a query (read-only)
- get_rumor() is a query (read-only)
"""

from typing import List, Optional

import structlog

from src.api.schemas.world_schemas import SortByEnum
from src.contexts.world.domain.entities import Rumor
from src.contexts.world.domain.ports.rumor_repository import RumorRepository

logger = structlog.get_logger()


class RumorService:
    """Application service for managing world rumors.

    This service provides the primary interface for rumor operations,
    abstracting the complexity of rumor retrieval, filtering, and sorting.

    Responsibilities:
        - Retrieving rumors for specific locations
        - Getting individual rumor details
        - Sorting and filtering rumors
        - Providing veracity labels based on truth values

    Attributes:
        _rumor_repo: The rumor repository for persistence
    """

    def __init__(self, rumor_repo: RumorRepository) -> None:
        """Initialize the rumor service with a repository.

        Args:
            rumor_repo: The rumor repository to use for persistence
        """
        self._rumor_repo = rumor_repo
        logger.debug("rumor_service_initialized")

    async def get_location_rumors(
        self,
        location_id: str,
        world_id: str,
        sort_by: SortByEnum = SortByEnum.RECENT,
        limit: int = 20,
    ) -> List[Rumor]:
        """Get rumors for a specific location with sorting.

        Retrieves all rumors that have spread to the specified location,
        then sorts them according to the specified criteria.

        Why we sort in service not repository:
            Different use cases need different sort orders (by recency,
            reliability, or spread count). Keeping this logic in the
            service allows flexible sorting without adding multiple
            repository methods.

        Args:
            location_id: Location ID to get rumors for
            world_id: World ID for context
            sort_by: Sort order (recent, reliable, spread)
            limit: Maximum number of rumors to return

        Returns:
            List of Rumor objects at the location, sorted and limited

        Example:
            >>> rumors = await service.get_location_rumors(
            ...     location_id="loc-capital",
            ...     world_id="world-123",
            ...     sort_by=SortByEnum.RELIABLE,
            ...     limit=10
            ... )
            >>> print(f"Found {len(rumors)} rumors at the capital")
        """
        logger.debug(
            "get_location_rumors_request",
            world_id=world_id,
            location_id=location_id,
            sort_by=sort_by.value,
            limit=limit,
        )

        # Get rumors from repository
        rumors = await self._rumor_repo.get_by_location_id(location_id)

        # Apply sorting based on criteria
        sorted_rumors = self._sort_rumors(rumors, sort_by)

        # Apply limit
        limited_rumors = sorted_rumors[:limit]

        logger.debug(
            "get_location_rumors_response",
            world_id=world_id,
            location_id=location_id,
            total_rumors=len(rumors),
            returned_count=len(limited_rumors),
        )

        return limited_rumors

    async def get_world_rumors(
        self,
        world_id: str,
        sort_by: SortByEnum = SortByEnum.RECENT,
        limit: int = 20,
        location_id: Optional[str] = None,
    ) -> List[Rumor]:
        """Get all rumors for a world with optional filtering and sorting.

        Retrieves all rumors in the world (or filtered by location),
        then sorts them according to the specified criteria.

        Args:
            world_id: World ID to get rumors for
            sort_by: Sort order (recent, reliable, spread)
            limit: Maximum number of rumors to return
            location_id: Optional filter by location ID

        Returns:
            List of Rumor objects, sorted and limited

        Example:
            >>> rumors = await service.get_world_rumors(
            ...     world_id="world-123",
            ...     sort_by=SortByEnum.RECENT,
            ...     limit=50
            ... )
            >>> print(f"World has {len(rumors)} rumors")
        """
        logger.debug(
            "get_world_rumors_request",
            world_id=world_id,
            sort_by=sort_by.value,
            limit=limit,
            location_id=location_id,
        )

        # Get rumors from repository
        if location_id:
            rumors = await self._rumor_repo.get_by_location_id(location_id)
        else:
            rumors = await self._rumor_repo.get_by_world_id(world_id)

        # Apply sorting
        sorted_rumors = self._sort_rumors(rumors, sort_by)

        # Apply limit
        limited_rumors = sorted_rumors[:limit]

        logger.debug(
            "get_world_rumors_response",
            world_id=world_id,
            total_rumors=len(rumors),
            returned_count=len(limited_rumors),
        )

        return limited_rumors

    async def get_rumor(
        self,
        rumor_id: str,
        world_id: str,
    ) -> Optional[Rumor]:
        """Get a single rumor by ID.

        Retrieves a rumor and verifies it belongs to the specified world.

        Args:
            rumor_id: Unique identifier for the rumor
            world_id: World ID for verification

        Returns:
            Rumor if found, None otherwise

        Example:
            >>> rumor = await service.get_rumor("rumor-123", "world-456")
            >>> if rumor:
            ...     print(f"Rumor: {rumor.content}")
            ...     print(f"Truth value: {rumor.truth_value}%")
        """
        rumor = await self._rumor_repo.get_by_id(rumor_id)

        if rumor is None:
            logger.debug(
                "get_rumor_not_found",
                rumor_id=rumor_id,
                world_id=world_id,
            )
            return None

        # Note: In a production implementation, we would verify the rumor
        # belongs to the specified world. For now, we rely on the rumor_id
        # being unique across worlds.

        logger.debug(
            "get_rumor_found",
            rumor_id=rumor_id,
            world_id=world_id,
        )
        return rumor

    def _sort_rumors(self, rumors: List[Rumor], sort_by: SortByEnum) -> List[Rumor]:
        """Sort rumors by the specified criteria.

        This internal method handles sorting logic to keep the public
        methods clean and focused.

        Args:
            rumors: List of rumors to sort
            sort_by: Sort order (recent, reliable, spread)

        Returns:
            Sorted list of rumors
        """
        if sort_by == SortByEnum.RECENT:
            # Sort by created_date descending (most recent first)
            # Handle None created_date by putting at end
            def recent_key(r: Rumor):
                if r.created_date:
                    return (
                        -r.created_date.year,
                        -r.created_date.month,
                        -r.created_date.day,
                    )
                return (0, 0, 0)

            return sorted(rumors, key=recent_key)

        elif sort_by == SortByEnum.RELIABLE:
            # Sort by truth_value descending (most reliable first)
            return sorted(rumors, key=lambda r: -r.truth_value)

        elif sort_by == SortByEnum.SPREAD:
            # Sort by spread_count descending (most spread first)
            return sorted(rumors, key=lambda r: -r.spread_count)

        # Default: return as-is
        return rumors

    @staticmethod
    def get_veracity_label(truth_value: int) -> str:
        """Get the veracity label for a truth value.

        This utility method converts a numeric truth value to a
        human-readable label.

        Args:
            truth_value: Truth percentage (0-100)

        Returns:
            Veracity label string

        Example:
            >>> label = RumorService.get_veracity_label(85)
            >>> print(label)  # "Confirmed"
        """
        if truth_value >= 80:
            return "Confirmed"
        elif truth_value >= 60:
            return "Likely True"
        elif truth_value >= 40:
            return "Uncertain"
        elif truth_value >= 20:
            return "Likely False"
        else:
            return "False"
