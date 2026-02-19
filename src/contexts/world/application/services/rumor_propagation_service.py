#!/usr/bin/env python3
"""RumorPropagationService - Rumor Spreading and Creation.

This module provides the RumorPropagationService for propagating rumors
through the world's location network and creating new rumors from events.

Rumors spread to adjacent locations with truth decay, simulating the
distortion of information as it travels. Events automatically generate
rumors with truth values based on their impact scope.

Typical usage example:
    >>> from src.contexts.world.application.services import RumorPropagationService
    >>> service = RumorPropagationService(location_repo, rumor_repo)
    >>> updated_rumors = await service.propagate_rumors(world)
    >>> new_rumor = service.create_rumor_from_event(event, world)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Protocol, Set, runtime_checkable

import structlog

from src.contexts.world.domain.aggregates.world_state import WorldState
from src.contexts.world.domain.entities.history_event import (
    EventType,
    HistoryEvent,
    ImpactScope,
)
from src.contexts.world.domain.entities.location import Location
from src.contexts.world.domain.entities.rumor import Rumor, RumorOrigin

logger = structlog.get_logger()


@runtime_checkable
class ILocationRepository(Protocol):
    """Protocol for Location repository interface.

    Defines the minimal interface needed by RumorPropagationService.
    """

    async def get_by_id(self, location_id: str) -> Location | None:
        """Retrieve a Location by ID.

        Args:
            location_id: Unique identifier for the location

        Returns:
            Location if found, None otherwise
        """
        ...

    async def get_by_world_id(self, world_id: str) -> List[Location]:
        """Retrieve all locations for a world.

        Args:
            world_id: ID of the world to get locations for

        Returns:
            List of Location entities in the world
        """
        ...

    async def find_adjacent(self, location_id: str) -> List[str]:
        """Find all locations adjacent to the given location.

        Adjacent locations are those that share the same parent_id,
        or have a parent-child relationship, or are explicitly connected.

        Args:
            location_id: ID of the location to find adjacents for

        Returns:
            List of adjacent location IDs
        """
        ...


@runtime_checkable
class IRumorRepository(Protocol):
    """Protocol for Rumor repository interface.

    Defines the minimal interface needed by RumorPropagationService.
    """

    async def get_active_rumors(self, world_id: str) -> List[Rumor]:
        """Get all active rumors (truth_value > 0) for a world.

        Args:
            world_id: ID of the world

        Returns:
            List of active Rumor entities
        """
        ...

    async def save(self, rumor: Rumor) -> Rumor:
        """Save a rumor (create or update).

        Args:
            rumor: Rumor entity to save

        Returns:
            Saved Rumor entity
        """
        ...

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

    async def get_by_world_id(self, world_id: str) -> List[Rumor]:
        """Get all rumors for a world.

        Args:
            world_id: ID of the world

        Returns:
            List of all Rumor entities in the world
        """
        ...


@dataclass
class RumorStatistics:
    """Statistics about rumors in a world.

    Attributes:
        total_rumors: Total number of rumors (including dead).
        active_rumors: Number of active rumors (truth_value > 0).
        avg_truth: Average truth value of active rumors.
        most_spread: Rumor with highest spread_count (or None if no rumors).
        dead_rumors: Number of dead rumors (truth_value == 0).
    """

    total_rumors: int = 0
    active_rumors: int = 0
    avg_truth: float = 0.0
    most_spread: Optional[Rumor] = None
    dead_rumors: int = 0


class RumorPropagationService:
    """Service for propagating rumors and creating rumors from events.

    This service handles:
    - Spreading rumors to adjacent locations with truth decay
    - Creating new rumors from historical events
    - Cleaning up dead rumors (truth_value == 0)
    - Tracking rumor statistics

    Attributes:
        TRUTH_BY_IMPACT: Mapping from ImpactScope to initial truth value.

    Example:
        >>> service = RumorPropagationService(location_repo, rumor_repo)
        >>> updated_rumors = await service.propagate_rumors(world)
        >>> stats = service.get_statistics(updated_rumors)
        >>> print(f"Average truth: {stats.avg_truth}")
    """

    # Initial truth value by event impact scope
    TRUTH_BY_IMPACT: Dict[ImpactScope, int] = {
        ImpactScope.GLOBAL: 90,
        ImpactScope.REGIONAL: 70,
        ImpactScope.LOCAL: 50,
    }

    def __init__(
        self,
        location_repo: ILocationRepository,
        rumor_repo: IRumorRepository,
    ):
        """Initialize the rumor propagation service.

        Args:
            location_repo: Repository for Location entities.
            rumor_repo: Repository for Rumor entities.
        """
        self._location_repo = location_repo
        self._rumor_repo = rumor_repo

    async def propagate_rumors(self, world: WorldState) -> List[Rumor]:
        """Propagate all active rumors to adjacent locations.

        For each active rumor (truth_value > 0):
        1. Get all current locations where the rumor exists
        2. For each location, find adjacent locations
        3. Spread rumor to each adjacent location not already reached
        4. Update rumor with new locations and decayed truth
        5. Save updated rumors
        6. Delete dead rumors (truth_value == 0)

        Args:
            world: Current WorldState aggregate.

        Returns:
            List of updated Rumor entities after propagation.

        Example:
            >>> rumors = await service.propagate_rumors(world)
            >>> print(f"Propagated {len(rumors)} rumors")
        """
        try:
            # Get all active rumors
            active_rumors = await self._rumor_repo.get_active_rumors(world.id)

            if not active_rumors:
                logger.debug(
                    "rumor_propagation_no_active_rumors",
                    world_id=world.id,
                )
                return []

            updated_rumors: List[Rumor] = []
            rumors_to_delete: List[str] = []

            for rumor in active_rumors:
                # Track new locations to spread to
                new_locations: Set[str] = set()

                # Find adjacent locations for each current location
                for location_id in rumor.current_locations:
                    try:
                        adjacent_ids = await self._location_repo.find_adjacent(
                            location_id
                        )
                        for adj_id in adjacent_ids:
                            # Only spread to locations not already reached
                            if adj_id not in rumor.current_locations:
                                new_locations.add(adj_id)
                    except Exception as e:
                        logger.warning(
                            "rumor_propagation_adjacent_failed",
                            location_id=location_id,
                            error=str(e),
                        )
                        continue

                # Spread rumor to new locations
                updated_rumor = rumor
                for new_loc_id in new_locations:
                    updated_rumor = updated_rumor.spread_to(new_loc_id)

                # Check if rumor is dead after spreading
                if updated_rumor.is_dead:
                    rumors_to_delete.append(updated_rumor.rumor_id)
                    logger.info(
                        "rumor_died",
                        rumor_id=updated_rumor.rumor_id,
                        spread_count=updated_rumor.spread_count,
                    )
                else:
                    updated_rumors.append(updated_rumor)

            # Save updated rumors
            if updated_rumors:
                await self._rumor_repo.save_all(updated_rumors)

            # Delete dead rumors
            for rumor_id in rumors_to_delete:
                await self._rumor_repo.delete(rumor_id)

            logger.info(
                "rumor_propagation_complete",
                world_id=world.id,
                updated_count=len(updated_rumors),
                deleted_count=len(rumors_to_delete),
            )

            return updated_rumors

        except Exception as e:
            logger.error(
                "rumor_propagation_error",
                world_id=world.id,
                error=str(e),
            )
            # Return empty list on error - don't crash simulation
            return []

    def create_rumor_from_event(
        self,
        event: HistoryEvent,
        world: WorldState,
    ) -> Rumor:
        """Create a new rumor from a historical event.

        The rumor's initial truth value is based on the event's impact_scope:
        - GLOBAL: 90% truth
        - REGIONAL: 70% truth
        - LOCAL: 50% truth

        The content is generated from a template based on event type.

        Args:
            event: HistoryEvent to create rumor from.
            world: Current WorldState aggregate (for calendar).

        Returns:
            A new Rumor entity based on the event.

        Raises:
            ValueError: If event has no location_ids.

        Example:
            >>> rumor = service.create_rumor_from_event(war_event, world)
            >>> print(f"New rumor: {rumor.content[:50]}...")
        """
        # Determine origin location
        origin_location = self._get_origin_location(event)

        # Generate rumor content based on event type
        content = self._generate_rumor_content(event)

        # Determine initial truth value based on impact scope
        impact_scope = event.impact_scope or ImpactScope.LOCAL
        initial_truth = self.TRUTH_BY_IMPACT.get(impact_scope, 50)

        # Create the rumor
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

        return rumor

    def _get_origin_location(self, event: HistoryEvent) -> str:
        """Determine the origin location for an event's rumor.

        Priority:
        1. First affected_location_id
        2. First location_id (where event occurred)
        3. "unknown" fallback

        Args:
            event: HistoryEvent to get location from.

        Returns:
            Location ID string for rumor origin.
        """
        # Prefer affected locations
        if event.affected_location_ids and len(event.affected_location_ids) > 0:
            return event.affected_location_ids[0]

        # Fall back to event locations
        if event.location_ids and len(event.location_ids) > 0:
            return event.location_ids[0]

        # Fallback to unknown
        return "unknown"

    def _generate_rumor_content(self, event: HistoryEvent) -> str:
        """Generate rumor content based on event type.

        Uses templates specific to each event type to create
        engaging rumor text.

        Args:
            event: HistoryEvent to generate content for.

        Returns:
            Rumor content string.
        """
        event_type = event.event_type
        event_name = event.name

        if event_type == EventType.WAR:
            faction_names = self._format_faction_list(event)
            return f"Word spreads of conflict between {faction_names}. {event_name}..."

        elif event_type == EventType.BATTLE:
            location = self._format_location_list(event)
            return f"Tales of a great battle at {location} circulate. {event_name}..."

        elif event_type == EventType.TRADE:
            return f"Merchants whisper about new trade routes. {event_name}..."

        elif event_type == EventType.DEATH:
            figures = ", ".join(event.key_figures) if event.key_figures else "a notable figure"
            return f"Rumors of {figures}'s passing circulate through the realm..."

        elif event_type == EventType.BIRTH:
            figures = ", ".join(event.key_figures) if event.key_figures else "a notable figure"
            return f"News arrives of {figures}'s birth. A new chapter begins..."

        elif event_type == EventType.MARRIAGE:
            figures = " and ".join(event.key_figures) if len(event.key_figures) >= 2 else "two noble houses"
            return f"Word spreads of the union between {figures}..."

        elif event_type == EventType.ALLIANCE:
            faction_names = self._format_faction_list(event)
            return f"Diplomats speak of a new alliance between {faction_names}..."

        elif event_type == EventType.CORONATION:
            figures = event.key_figures[0] if event.key_figures else "a new ruler"
            return f"Proclamations announce the coronation of {figures}..."

        elif event_type == EventType.DISASTER:
            location = self._format_location_list(event)
            return f"Terrifying news of disaster at {location} spreads. {event_name}..."

        elif event_type == EventType.DISCOVERY:
            location = self._format_location_list(event)
            return f"Whispers of a discovery at {location} excite scholars. {event_name}..."

        elif event_type == EventType.REVOLUTION:
            location = self._format_location_list(event)
            return f"Reports of uprising in {location} spread rapidly. {event_name}..."

        elif event_type == EventType.MIRACLE:
            location = self._format_location_list(event)
            return f"Tales of a miracle at {location} inspire the faithful. {event_name}..."

        elif event_type == EventType.MAGICAL:
            location = self._format_location_list(event)
            return f"Strange tales of magical occurrence at {location} spread. {event_name}..."

        else:
            location = self._format_location_list(event)
            return f"Something happened at {location}. {event_name}..."

    def _format_faction_list(self, event: HistoryEvent) -> str:
        """Format faction IDs as a readable string.

        Args:
            event: HistoryEvent with faction_ids.

        Returns:
            Formatted string of faction names (or count if unavailable).
        """
        if not event.faction_ids:
            return "unknown parties"

        if len(event.faction_ids) == 1:
            return "an unknown faction"

        if len(event.faction_ids) == 2:
            return "two great powers"

        return f"{len(event.faction_ids)} factions"

    def _format_location_list(self, event: HistoryEvent) -> str:
        """Format location IDs as a readable string.

        Args:
            event: HistoryEvent with location_ids.

        Returns:
            Formatted string describing locations.
        """
        locations = event.location_ids or event.affected_location_ids or []

        if not locations:
            return "an unknown location"

        if len(locations) == 1:
            return "a distant land"

        return "several locations"

    def get_statistics(self, rumors: List[Rumor]) -> RumorStatistics:
        """Calculate statistics about a list of rumors.

        Args:
            rumors: List of Rumor entities to analyze.

        Returns:
            RumorStatistics with calculated values.

        Example:
            >>> stats = service.get_statistics(rumors)
            >>> print(f"Active: {stats.active_rumors}, Avg Truth: {stats.avg_truth}")
        """
        if not rumors:
            return RumorStatistics()

        active_rumors = [r for r in rumors if not r.is_dead]
        dead_rumors = [r for r in rumors if r.is_dead]

        avg_truth = 0.0
        if active_rumors:
            avg_truth = sum(r.truth_value for r in active_rumors) / len(active_rumors)

        most_spread: Rumor | None = None
        if rumors:
            most_spread = max(rumors, key=lambda r: r.spread_count)

        return RumorStatistics(
            total_rumors=len(rumors),
            active_rumors=len(active_rumors),
            avg_truth=round(avg_truth, 2),
            most_spread=most_spread,
            dead_rumors=len(dead_rumors),
        )

    @property
    def total_rumors(self) -> int:
        """Get total number of rumors (requires repo access).

        Note: This property is for convenience but requires synchronous
        repo access. For async usage, use get_statistics() with the
        result of get_by_world_id().

        Returns:
            0 (placeholder - use get_statistics for actual data).
        """
        return 0

    @property
    def avg_truth(self) -> float:
        """Get average truth value (requires repo access).

        Note: This property is for convenience but requires synchronous
        repo access. For async usage, use get_statistics() with the
        result of get_by_world_id().

        Returns:
            0.0 (placeholder - use get_statistics for actual data).
        """
        return 0.0

    @property
    def most_spread(self) -> Optional[Rumor]:
        """Get most spread rumor (requires repo access).

        Note: This property is for convenience but requires synchronous
        repo access. For async usage, use get_statistics() with the
        result of get_by_world_id().

        Returns:
            None (placeholder - use get_statistics for actual data).
        """
        return None
