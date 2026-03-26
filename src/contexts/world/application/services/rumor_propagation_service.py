"""RumorPropagationService - Rumor Spreading and Creation (Refactored).

Orchestrates rumor propagation using specialized components:
- AdjacencyCache: Manages caching of location adjacency lookups
- RumorPropagator: Handles core propagation algorithm
- RumorContentGenerator: Generates rumor content from events
- RumorStatisticsService: Calculates and tracks rumor statistics
"""

from typing import Dict, List, Optional

import structlog

from src.contexts.world.application.services.adjacency_cache import (
    AdjacencyCache,
    ILocationRepository,
)
from src.contexts.world.application.services.rumor_content_generator import (
    RumorContentGenerator,
)
from src.contexts.world.application.services.rumor_propagator import (
    IRumorRepository,
    RumorPropagator,
)
from src.contexts.world.application.services.rumor_statistics_service import (
    RumorStatistics,
    RumorStatisticsService,
)
from src.contexts.world.domain.aggregates.world_state import WorldState
from src.contexts.world.domain.entities.history_event import (
    HistoryEvent,
    ImpactScope,
)
from src.contexts.world.domain.entities.rumor import Rumor, RumorOrigin
from src.shared.application.result import Failure, Result, Success

logger = structlog.get_logger()


class RumorPropagationService:
    """Service for propagating rumors and creating rumors from events."""

    TRUTH_BY_IMPACT: Dict[ImpactScope, int] = {
        ImpactScope.GLOBAL: 90,
        ImpactScope.REGIONAL: 70,
        ImpactScope.LOCAL: 50,
    }

    DEFAULT_BATCH_SIZE: int = 500

    def __init__(
        self,
        location_repo: ILocationRepository,
        rumor_repo: IRumorRepository,
    ) -> None:
        self._location_repo = location_repo
        self._rumor_repo = rumor_repo

        # Initialize specialized components
        self._cache = AdjacencyCache(location_repo)
        self._propagator = RumorPropagator(self._cache)
        self._content_generator = RumorContentGenerator()
        self._stats_service = RumorStatisticsService()

    async def propagate_rumors(self, world: WorldState) -> Result[List[Rumor]]:
        """Propagate all active rumors to adjacent locations."""
        try:
            active_rumors = await self._rumor_repo.get_active_rumors(world.id)

            if not active_rumors:
                logger.debug("rumor_propagation_no_active_rumors", world_id=world.id)
                return Success([])

            logger.info(
                "rumor_propagation_started",
                world_id=world.id,
                rumor_count=len(active_rumors),
            )

            updated_rumors, rumors_to_delete = await self._propagator.propagate(
                active_rumors
            )

            if updated_rumors:
                await self._rumor_repo.save_all(updated_rumors)

            if rumors_to_delete:
                await self._propagator.delete_rumors_batch(
                    self._rumor_repo, rumors_to_delete
                )

            logger.info(
                "rumor_propagation_complete",
                world_id=world.id,
                updated_count=len(updated_rumors),
                deleted_count=len(rumors_to_delete),
                cache_size=self._cache.size,
            )

            return Success(updated_rumors)

        except Exception as e:
            logger.error("rumor_propagation_error", world_id=world.id, error=str(e))
            return Failure.from_message(
                f"Failed to propagate rumors: {e}",
                code="RUMOR_PROPAGATION_ERROR",
                world_id=world.id,
            )

    async def propagate_rumors_batch(
        self,
        world: WorldState,
        batch_size: int = 500,
    ) -> Result[List[Rumor]]:
        """Propagate rumors in batches for memory-constrained environments."""
        try:
            active_rumors = await self._rumor_repo.get_active_rumors(world.id)

            if not active_rumors:
                return Success([])

            all_updated: List[Rumor] = []
            all_to_delete: List[str] = []

            logger.info(
                "rumor_propagation_batch_started",
                world_id=world.id,
                total_rumors=len(active_rumors),
                batch_size=batch_size,
            )

            for i in range(0, len(active_rumors), batch_size):
                batch = active_rumors[i : i + batch_size]
                updated, to_delete = await self._propagator.propagate(batch)
                all_updated.extend(updated)
                all_to_delete.extend(to_delete)

            if all_updated:
                await self._rumor_repo.save_all(all_updated)

            if all_to_delete:
                await self._propagator.delete_rumors_batch(
                    self._rumor_repo, all_to_delete
                )

            logger.info(
                "rumor_propagation_batch_complete",
                world_id=world.id,
                total_updated=len(all_updated),
                total_deleted=len(all_to_delete),
            )

            return Success(all_updated)

        except Exception as e:
            logger.error(
                "rumor_propagation_batch_error", world_id=world.id, error=str(e)
            )
            return Failure.from_message(
                f"Failed to propagate rumors in batches: {e}",
                code="RUMOR_PROPAGATION_ERROR",
                world_id=world.id,
                batch_size=batch_size,
            )

    def create_rumor_from_event(
        self,
        event: HistoryEvent,
        world: WorldState,
    ) -> Result[Rumor]:
        """Create a new rumor from a historical event."""
        try:
            if not event.location_ids and not event.affected_location_ids:
                return Failure.from_message(
                    "Cannot create rumor from event without location information",
                    code="RUMOR_CREATION_ERROR",
                    event_id=event.id,
                    event_name=event.name,
                )

            origin_location = self._get_origin_location(event)
            content = self._content_generator.generate_content(event)
            impact_scope = event.impact_scope or ImpactScope.LOCAL
            initial_truth = self.TRUTH_BY_IMPACT.get(impact_scope, 50)

            rumor = Rumor(
                content=content,
                truth_value=initial_truth,
                origin_type=RumorOrigin.EVENT,
                source_event_id=event.id,
                origin_location_id=origin_location,
                current_locations={origin_location},
                created_date=world.calendar,
                spread_count=0,
            )

            logger.info(
                "rumor_created_from_event",
                event_id=event.id,
                event_type=event.event_type.value,
                rumor_id=rumor.rumor_id,
                initial_truth=initial_truth,
            )

            return Success(rumor)

        except Exception as e:
            return Failure.from_message(
                f"Failed to create rumor from event: {e}",
                code="RUMOR_CREATION_ERROR",
                event_id=event.id,
            )

    def _get_origin_location(self, event: HistoryEvent) -> str:
        """Determine the origin location for an event's rumor."""
        if event.affected_location_ids and len(event.affected_location_ids) > 0:
            return event.affected_location_ids[0]
        if event.location_ids and len(event.location_ids) > 0:
            return event.location_ids[0]
        return "unknown"

    def get_statistics(self, rumors: List[Rumor]) -> Result[RumorStatistics]:
        """Calculate statistics about a list of rumors."""
        return self._stats_service.calculate_statistics(rumors)

    def clear_adjacency_cache(self) -> Result[None]:
        """Clear the adjacency cache."""
        try:
            self._cache.invalidate()
            return Success(None)
        except Exception as e:
            return Failure.from_message(
                f"Failed to clear adjacency cache: {e}",
                code="CACHE_CLEAR_ERROR",
            )

    def get_cache_stats(self) -> Result[Dict[str, int]]:
        """Get statistics about the adjacency cache."""
        try:
            return Success(self._cache.get_stats())
        except Exception as e:
            return Failure.from_message(
                f"Failed to get cache stats: {e}",
                code="CACHE_STATS_ERROR",
            )

    @property
    def total_rumors(self) -> int:
        """Get total number of rumors (placeholder)."""
        return 0

    @property
    def avg_truth(self) -> float:
        """Get average truth value (placeholder)."""
        return 0.0

    @property
    def most_spread(self) -> Optional[Rumor]:
        """Get most spread rumor (placeholder)."""
        return None
