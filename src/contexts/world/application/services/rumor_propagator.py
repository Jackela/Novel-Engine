"""Core rumor propagation logic.

This module provides the core algorithm for propagating rumors through
location networks with truth decay and batch processing optimizations.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Protocol, Set, Tuple, runtime_checkable

import structlog

from src.contexts.world.domain.entities.rumor import TRUTH_DECAY_PER_HOP, Rumor

if TYPE_CHECKING:
    from src.contexts.world.application.services.adjacency_cache import (
        AdjacencyCache,
    )

logger = structlog.get_logger()


@runtime_checkable
class IRumorRepository(Protocol):
    """Protocol for rumor repository."""

    async def save_all(self, rumors: List[Rumor]) -> List[Rumor]:
        """Save multiple rumors.

        Args:
            rumors: List of Rumor entities to save

        Returns:
            List of saved Rumor entities
        """
        ...

    async def delete(self, rumor_id: str) -> bool:
        """Delete a rumor by ID.

        Args:
            rumor_id: ID of the rumor to delete

        Returns:
            True if deleted, False if not found
        """
        ...


@dataclass
class SpreadOperation:
    """Represents a single spread operation.

    Used to batch spread operations for efficiency.

    Attributes:
        rumor_id: ID of the rumor to spread
        new_location_id: Location to spread to
        current_truth: Current truth value before spread
        current_count: Current spread count
        current_locations: Current set of locations
    """

    rumor_id: str
    new_location_id: str
    current_truth: int
    current_count: int
    current_locations: frozenset = field(hash=False)


class RumorPropagator:
    """Handles the core algorithm for rumor propagation.

    This class implements optimized rumor spreading through location networks
    with support for batch processing and adjacency caching.
    """

    def __init__(
        self,
        adjacency_cache: "AdjacencyCache",  # type: ignore  # Forward reference
    ) -> None:
        """Initialize the propagator.

        Args:
            adjacency_cache: Cache for location adjacency lookups
        """
        self._adjacency_cache = adjacency_cache

    async def propagate(
        self,
        rumors: List[Rumor],
    ) -> Tuple[List[Rumor], List[str]]:
        """Execute propagation algorithm on a batch of rumors.

        This method processes all rumors with optimized spread logic:
        1. Pre-fetches all adjacency data
        2. Collects all spread operations
        3. Applies spreads in batch to minimize object creation

        Args:
            rumors: List of rumors to propagate

        Returns:
            Tuple of (updated_rumors, rumors_to_delete)
        """
        if not rumors:
            return [], []

        # Collect all location IDs that need adjacency lookup
        all_location_ids: Set[str] = set()
        for rumor in rumors:
            all_location_ids.update(rumor.current_locations)

        # Pre-fetch adjacency for all locations
        await self._adjacency_cache.get_neighbors_batch(all_location_ids)

        updated_rumors: List[Rumor] = []
        rumors_to_delete: List[str] = []

        # Process each rumor
        for rumor in rumors:
            updated_rumor = self._propagate_single_rumor(rumor)

            if updated_rumor.is_dead:
                rumors_to_delete.append(updated_rumor.rumor_id)
                logger.debug(
                    "rumor_died",
                    rumor_id=updated_rumor.rumor_id,
                    spread_count=updated_rumor.spread_count,
                )
            else:
                updated_rumors.append(updated_rumor)

        return updated_rumors, rumors_to_delete

    def _propagate_single_rumor(self, rumor: Rumor) -> Rumor:
        """Propagate a single rumor using optimized spread logic.

        Args:
            rumor: Rumor to propagate

        Returns:
            Updated rumor after propagation
        """
        # Collect all new locations to spread to
        new_locations: Set[str] = set()
        current_locations = rumor.current_locations

        # Find adjacent locations for each current location using cache
        for location_id in current_locations:
            adjacent_ids = self._adjacency_cache._cache.get(location_id, [])

            # Add adjacent locations that haven't been reached yet
            for adj_id in adjacent_ids:
                if adj_id not in current_locations:
                    new_locations.add(adj_id)

        # If no new locations, return rumor unchanged
        if not new_locations:
            return rumor

        # Optimized spread: calculate final state directly
        # This reduces object creation from O(spreads) to O(1)
        final_truth = max(
            0, rumor.truth_value - (TRUTH_DECAY_PER_HOP * len(new_locations))
        )
        final_locations = current_locations | new_locations
        final_spread_count = rumor.spread_count + len(new_locations)

        # Create updated rumor directly with final state
        updated_rumor = Rumor(
            rumor_id=rumor.rumor_id,
            content=rumor.content,
            truth_value=final_truth,
            origin_type=rumor.origin_type,
            source_event_id=rumor.source_event_id,
            origin_location_id=rumor.origin_location_id,
            current_locations=final_locations,
            created_date=rumor.created_date,
            spread_count=final_spread_count,
        )

        return updated_rumor

    async def delete_rumors_batch(
        self,
        rumor_repo: IRumorRepository,
        rumor_ids: List[str],
    ) -> int:
        """Delete multiple rumors efficiently.

        Args:
            rumor_repo: Repository for deleting rumors
            rumor_ids: List of rumor IDs to delete

        Returns:
            Number of rumors successfully deleted
        """
        deleted_count = 0
        for rumor_id in rumor_ids:
            try:
                if await rumor_repo.delete(rumor_id):
                    deleted_count += 1
            except Exception as e:
                logger.warning(
                    "rumor_delete_failed",
                    rumor_id=rumor_id,
                    error=str(e),
                )

        logger.debug(
            "rumors_batch_deleted",
            requested=len(rumor_ids),
            deleted=deleted_count,
        )

        return deleted_count

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        return self._adjacency_cache.get_stats()
