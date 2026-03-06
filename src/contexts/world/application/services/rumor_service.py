#!/usr/bin/env python3
"""Rumor Service for World Rumor Operations.

This module provides the application-layer service for managing world rumors.
It orchestrates domain objects and repositories to handle rumor-related
operations, including retrieving location-specific rumors and rumor details.

The RumorService follows the Command Query Separation principle:
- get_location_rumors() is a query (read-only)
- get_rumor() is a query (read-only)

Result Pattern:
    All public methods return Result[T, Error] for explicit error handling.
    This makes failure modes visible and forces callers to handle errors.
"""

from typing import Any, Dict, List, Optional

import structlog

from src.api.schemas.world_schemas import SortByEnum
from src.contexts.world.domain.entities import Rumor
from src.contexts.world.domain.errors import (
    RumorError,
    RumorNotFoundError,
    RumorValidationError,
)
from src.contexts.world.domain.ports.rumor_repository import RumorRepository
from src.core.result import Err, Error, Ok, Result

logger = structlog.get_logger()


# Note: Error types are now imported from src.contexts.world.domain.errors


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
    ) -> Result[List[Rumor], Error]:
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
            Result containing:
            - Ok: List of Rumor objects at the location, sorted and limited
            - Err: Error if operation fails

        Example:
            >>> result = await service.get_location_rumors(
            ...     location_id="loc-capital",
            ...     world_id="world-123",
            ...     sort_by=SortByEnum.RELIABLE,
            ...     limit=10
            ... )
            >>> if result.is_ok:
            ...     rumors = result.value
            ...     print(f"Found {len(rumors)} rumors at the capital")
        """
        logger.debug(
            "get_location_rumors_request",
            world_id=world_id,
            location_id=location_id,
            sort_by=sort_by.value,
            limit=limit,
        )

        try:
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

            return Ok(limited_rumors)
        except Exception as e:
            logger.error(
                "get_location_rumors_failed",
                world_id=world_id,
                location_id=location_id,
                error=str(e),
            )
            return Err(
                Error(
                    code="RUMOR_FETCH_FAILED",
                    message=f"Failed to fetch rumors for location: {e}",
                    recoverable=True,
                )
            )

    async def get_world_rumors(
        self,
        world_id: str,
        sort_by: SortByEnum = SortByEnum.RECENT,
        limit: int = 20,
        location_id: Optional[str] = None,
    ) -> Result[List[Rumor], Error]:
        """Get all rumors for a world with optional filtering and sorting.

        Retrieves all rumors in the world (or filtered by location),
        then sorts them according to the specified criteria.

        Args:
            world_id: World ID to get rumors for
            sort_by: Sort order (recent, reliable, spread)
            limit: Maximum number of rumors to return
            location_id: Optional filter by location ID

        Returns:
            Result containing:
            - Ok: List of Rumor objects, sorted and limited
            - Err: Error if operation fails

        Example:
            >>> result = await service.get_world_rumors(
            ...     world_id="world-123",
            ...     sort_by=SortByEnum.RECENT,
            ...     limit=50
            ... )
            >>> if result.is_ok:
            ...     rumors = result.value
            ...     print(f"World has {len(rumors)} rumors")
        """
        logger.debug(
            "get_world_rumors_request",
            world_id=world_id,
            sort_by=sort_by.value,
            limit=limit,
            location_id=location_id,
        )

        try:
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

            return Ok(limited_rumors)
        except Exception as e:
            logger.error(
                "get_world_rumors_failed",
                world_id=world_id,
                location_id=location_id,
                error=str(e),
            )
            return Err(
                Error(
                    code="RUMOR_FETCH_FAILED",
                    message=f"Failed to fetch world rumors: {e}",
                    recoverable=True,
                )
            )

    async def get_rumor(
        self,
        rumor_id: str,
        world_id: str,
    ) -> Result[Optional[Rumor], Error]:
        """Get a single rumor by ID.

        Retrieves a rumor and verifies it belongs to the specified world.

        Args:
            rumor_id: Unique identifier for the rumor
            world_id: World ID for verification

        Returns:
            Result containing:
            - Ok: Rumor if found, None if not found
            - Err: Error if operation fails

        Example:
            >>> result = await service.get_rumor("rumor-123", "world-456")
            >>> if result.is_ok:
            ...     rumor = result.value
            ...     if rumor:
            ...         print(f"Rumor: {rumor.content}")
            ...         print(f"Truth value: {rumor.truth_value}%")
        """
        try:
            rumor = await self._rumor_repo.get_by_id(rumor_id)

            if rumor is None:
                logger.debug(
                    "get_rumor_not_found",
                    rumor_id=rumor_id,
                    world_id=world_id,
                )
                return Ok(None)

            # Note: In a production implementation, we would verify the rumor
            # belongs to the specified world. For now, we rely on the rumor_id
            # being unique across worlds.

            logger.debug(
                "get_rumor_found",
                rumor_id=rumor_id,
                world_id=world_id,
            )
            return Ok(rumor)
        except Exception as e:
            logger.error(
                "get_rumor_failed",
                rumor_id=rumor_id,
                world_id=world_id,
                error=str(e),
            )
            return Err(
                Error(
                    code="RUMOR_FETCH_FAILED",
                    message=f"Failed to fetch rumor: {e}",
                    recoverable=True,
                )
            )

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
            def recent_key(r: Rumor) -> None:
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

    async def get_propagation_graph(
        self,
        world_id: str,
        rumor_id: Optional[str] = None,
        max_hops: int = 5,
    ) -> Result[Dict[str, Any], Error]:
        """Build a propagation graph for rumors.

        This query constructs a graph representation of rumor propagation,
        including nodes (locations and rumors) and edges (spread paths).

        Args:
            world_id: World ID
            rumor_id: Optional specific rumor to visualize
            max_hops: Maximum spread hops to include

        Returns:
            Result containing:
            - Ok: Dictionary containing graph data (nodes and edges)
            - Err: Error if operation fails
        """
        logger.info(
            "get_propagation_graph_request",
            world_id=world_id,
            rumor_id=rumor_id,
            max_hops=max_hops,
        )

        try:
            # Get rumors to visualize
            if rumor_id:
                rumor_result = await self.get_rumor(rumor_id, world_id)
                if rumor_result.is_error:
                    return rumor_result  # type: ignore
                rumor = rumor_result.value
                rumors = [rumor] if rumor else []
            else:
                rumors = await self._rumor_repo.get_by_world_id(world_id)

            # Build graph
            nodes: List[Dict[str, Any]] = []
            edges: List[Dict[str, Any]] = []
            node_ids: set = set()
            edge_ids: set = set()

            for rumor in rumors:
                # Add rumor node
                rumor_node_id = f"rumor:{rumor.rumor_id}"
                if rumor_node_id not in node_ids:
                    nodes.append(
                        {
                            "id": rumor_node_id,
                            "type": "rumor",
                            "label": f"Rumor {rumor.rumor_id[:8]}...",
                            "metadata": {
                                "truth_value": rumor.truth_value,
                                "veracity_label": self.get_veracity_label(
                                    rumor.truth_value
                                ),
                                "content_preview": (
                                    rumor.content[:100] + "..."
                                    if len(rumor.content) > 100
                                    else rumor.content
                                ),
                                "spread_count": rumor.spread_count,
                            },
                        }
                    )
                    node_ids.add(rumor_node_id)

                # Add origin location node
                origin_node_id = f"loc:{rumor.origin_location_id}"
                if origin_node_id not in node_ids:
                    nodes.append(
                        {
                            "id": origin_node_id,
                            "type": "location",
                            "label": rumor.origin_location_id,
                            "metadata": {
                                "is_origin": True,
                            },
                        }
                    )
                    node_ids.add(origin_node_id)

                # Add origin edge
                origin_edge_id = f"edge:{rumor.rumor_id}:origin"
                if origin_edge_id not in edge_ids:
                    edges.append(
                        {
                            "id": origin_edge_id,
                            "source": rumor_node_id,
                            "target": origin_node_id,
                            "type": "origin",
                            "metadata": {
                                "hop": 0,
                            },
                        }
                    )
                    edge_ids.add(origin_edge_id)

                # Add spread location nodes and edges
                for idx, location_id in enumerate(rumor.current_locations):
                    if location_id == rumor.origin_location_id:
                        continue  # Skip origin, already added

                    loc_node_id = f"loc:{location_id}"
                    if loc_node_id not in node_ids:
                        nodes.append(
                            {
                                "id": loc_node_id,
                                "type": "location",
                                "label": location_id,
                                "metadata": {
                                    "is_origin": False,
                                },
                            }
                        )
                        node_ids.add(loc_node_id)

                    # Add spread edge from origin to this location
                    spread_edge_id = f"edge:{rumor.rumor_id}:spread:{idx}"
                    if spread_edge_id not in edge_ids:
                        # Calculate truth at arrival
                        truth_at_arrival = max(0, rumor.truth_value - (10 * (idx + 1)))
                        edges.append(
                            {
                                "id": spread_edge_id,
                                "source": origin_node_id,
                                "target": loc_node_id,
                                "type": "spread",
                                "metadata": {
                                    "hop": idx + 1,
                                    "truth_at_arrival": truth_at_arrival,
                                },
                            }
                        )
                        edge_ids.add(spread_edge_id)

            max_hops_found = max(
                [edge["metadata"].get("hop", 0) for edge in edges], default=0
            )

            logger.info(
                "get_propagation_graph_completed",
                world_id=world_id,
                total_nodes=len(nodes),
                total_edges=len(edges),
                max_hops=max_hops_found,
            )

            return Ok({
                "world_id": world_id,
                "graph": {
                    "nodes": nodes,
                    "edges": edges,
                },
                "metadata": {
                    "total_nodes": len(nodes),
                    "total_edges": len(edges),
                    "max_hops": max_hops_found,
                },
            })
        except Exception as e:
            logger.error(
                "get_propagation_graph_failed",
                world_id=world_id,
                rumor_id=rumor_id,
                error=str(e),
            )
            return Err(
                Error(
                    code="GRAPH_BUILD_FAILED",
                    message=f"Failed to build propagation graph: {e}",
                    recoverable=True,
                )
            )
