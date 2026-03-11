# mypy: ignore-errors

"""Rumor Propagation Event Handler.

This handler subscribes to world.time_advanced events and triggers
rumor propagation through the world's location network.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Set

import structlog

from src.events.event_bus import Event, EventHandler

if TYPE_CHECKING:
    from src.contexts.world.application.services.rumor_propagation_service import (
        ILocationRepository,
        IRumorRepository,
        RumorPropagationService,
    )
    from src.contexts.world.domain.aggregates.world_state import WorldState

logger = structlog.get_logger()


class RumorPropagationHandler(EventHandler):
    """Handler for propagating rumors when world time advances.

    This handler is called when world time advances. It triggers
    the RumorPropagationService to spread rumors through adjacent locations,
    simulating information flow through the world.

    Why this handler exists:
        Rumors represent information flow in the world. When time advances,
        rumors should naturally spread to nearby locations, decaying in truth
        value as they travel. This creates emergent narrative possibilities
        where characters may have partial or outdated information.

    Event Flow:
        1. User calls POST /api/world/time/advance
        2. World time advances and TimeAdvancedEvent is published
        3. This handler receives the world.time_advanced event
        4. RumorPropagationService.propagate_rumors() is called
        5. Active rumors spread to adjacent locations with truth decay
        6. Dead rumors (truth_value == 0) are cleaned up

    Error Handling:
        This handler is designed to fail gracefully. If rumor propagation
        fails (e.g., repositories unavailable, database errors), the handler
        returns False but does not raise exceptions. This ensures that
        rumor propagation failures do not break the time advancement flow
        or affect other event handlers.
    """

    def __init__(
        self,
        propagation_service: RumorPropagationService | None = None,
        location_repo: ILocationRepository | None = None,
        rumor_repo: IRumorRepository | None = None,
    ) -> None:
        """Initialize the handler.

        Args:
            propagation_service: Optional RumorPropagationService instance.
                If not provided, the handler will attempt to create one
                from the provided repositories.
            location_repo: Optional location repository for creating the service.
                Only used if propagation_service is None.
            rumor_repo: Optional rumor repository for creating the service.
                Only used if propagation_service is None.

        Note:
            If no service or repositories are provided, the handler will
            log a warning and return False on handle() calls. This allows
            the application to start even if rumor infrastructure is not
            fully configured.
        """
        self._propagation_service = propagation_service
        self._location_repo = location_repo
        self._rumor_repo = rumor_repo

        # Attempt to create service from repositories if not provided
        if self._propagation_service is None:
            if self._location_repo is not None and self._rumor_repo is not None:
                from src.contexts.world.application.services.rumor_propagation_service import (
                    RumorPropagationService,
                )

                self._propagation_service = RumorPropagationService(
                    location_repo=self._location_repo,
                    rumor_repo=self._rumor_repo,
                )

        if self._propagation_service is None:
            logger.warning(
                "rumor_propagation_handler_initialized_without_service",
                message="RumorPropagationHandler created without a service. "
                "Rumor propagation will be skipped until service is available.",
            )
        else:
            logger.debug("rumor_propagation_handler_initialized")

    @property
    def handled_event_types(self) -> Set[str]:
        """Set of event types this handler can process.

        Returns:
            Set containing "world.time_advanced" event type.
        """
        return {"world.time_advanced"}

    async def handle(self, event: Event) -> bool:
        """Handle a world.time_advanced event by propagating rumors.

        Implements EventHandler interface. This method spreads active rumors
        to adjacent locations and cleans up dead rumors.

        Args:
            event: The Event to process (must be world.time_advanced type)

        Returns:
            True if rumors were propagated successfully, False otherwise.
            Returns False if no propagation service is available or if
            an error occurs during propagation.

        Note:
            This method never raises exceptions. All errors are caught and
            logged, with False returned to indicate failure. This isolation
            ensures rumor propagation failures do not affect other handlers.
        """
        # Extract world_id from event payload
        world_id = event.payload.get("world_id", "default")
        days_advanced = event.payload.get("days_advanced", 0)

        logger.info(
            "rumor_propagation_event_received",
            event_id=event.event_id,
            world_id=world_id,
            days_advanced=days_advanced,
        )

        # Check if service is available
        if self._propagation_service is None:
            logger.warning(
                "rumor_propagation_skipped_no_service",
                event_id=event.event_id,
                world_id=world_id,
                message="Cannot propagate rumors: RumorPropagationService not available",
            )
            return False

        try:
            # Build a minimal WorldState for the propagation service
            # The service only needs world.id for repository lookups
            world = self._create_world_state(world_id, event)

            # Propagate rumors through the location network
            updated_rumors = await self._propagation_service.propagate_rumors(world)

            logger.info(
                "rumor_propagation_complete",
                event_id=event.event_id,
                world_id=world_id,
                rumors_updated=len(updated_rumors),
            )

            return True

        except Exception as e:
            # Graceful error handling - don't crash if propagation fails
            logger.error(
                "rumor_propagation_failed",
                event_id=event.event_id,
                world_id=world_id,
                error=str(e),
                exc_info=True,
            )
            return False

    def _create_world_state(self, world_id: str, event: Event) -> "WorldState":
        """Create a minimal WorldState from event data.

        The RumorPropagationService only needs the world ID to fetch
        rumors and locations from repositories. We construct a minimal
        WorldState with just the ID and calendar information.

        Why not fetch the full WorldState from a repository?
            To keep the handler simple and avoid additional dependencies.
            The propagation service performs repository lookups itself,
            so we only provide the world identifier.

        Args:
            world_id: The unique identifier for the world.
            event: The time advanced event containing date information.

        Returns:
            A minimal WorldState aggregate with ID and calendar.
        """
        from src.contexts.world.domain.aggregates.world_state import WorldState
        from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar

        # Extract date information from event if available
        new_date = event.payload.get("new_date", {})

        calendar = WorldCalendar(
            year=new_date.get("year", 1),
            month=new_date.get("month", 1),
            day=new_date.get("day", 1),
            era_name=new_date.get("era_name", "First Age"),
        )

        # Create minimal world state
        world = WorldState(
            id=world_id,
            name=f"World_{world_id[:8]}",
            calendar=calendar,
        )

        return world

    @classmethod
    def create_for_event_bus(
        cls,
        location_repo: ILocationRepository | None = None,
        rumor_repo: IRumorRepository | None = None,
    ) -> "RumorPropagationHandler":
        """Factory method to create a handler for EventBus registration.

        This factory method allows the handler to be created with or without
        repository dependencies. If repositories are not available, the
        handler will log warnings and skip propagation until they are.

        Args:
            location_repo: Optional location repository.
            rumor_repo: Optional rumor repository.

        Returns:
            RumorPropagationHandler instance ready for event subscription.

        Example:
            >>> handler = RumorPropagationHandler.create_for_event_bus(
            ...     location_repo=location_repository,
            ...     rumor_repo=rumor_repository,
            ... )
            >>> event_bus.register_handler(handler)
        """
        return cls(location_repo=location_repo, rumor_repo=rumor_repo)
