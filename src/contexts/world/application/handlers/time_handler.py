"""Time Advanced Event Handler.

This handler subscribes to world.time_advanced events and triggers
faction simulation updates via FactionTickService.
"""

from __future__ import annotations

from typing import Set

import structlog

from src.contexts.world.application.services.faction_tick_service import (
    FactionTickService,
)
from src.events.event_bus import Event, EventHandler

logger = structlog.get_logger()


class TimeAdvancedHandler(EventHandler):
    """Handler for TimeAdvancedEvent.

    This handler is called when world time advances. It triggers
    the FactionTickService to process resource yields and diplomatic changes.

    Event Flow:
        1. User calls POST /api/world/time/advance
        2. world_time router advances calendar
        3. TimeAdvancedEvent is published to EventBus
        4. This handler receives the event
        5. FactionTickService.process_tick() is called
        6. Faction resources and diplomacy are updated
    """

    def __init__(self, tick_service: FactionTickService | None = None) -> None:
        """Initialize the handler.

        Args:
            tick_service: Optional FactionTickService instance (for dependency injection)
        """
        self._tick_service = tick_service or FactionTickService()
        logger.debug("time_advanced_handler_initialized")

    @property
    def handled_event_types(self) -> Set[str]:
        """Set of event types this handler can process."""
        return {"world.time_advanced"}

    async def handle(self, event: Event) -> bool:
        """Handle a TimeAdvancedEvent.

        Implements EventHandler interface.

        Args:
            event: The Event to process (must be TimeAdvancedEvent)

        Returns:
            True if handled successfully, False otherwise
        """
        logger.info(
            "time_advanced_event_received",
            event_id=event.event_id,
            world_id=event.payload.get("world_id"),
            days_advanced=event.days_advanced,
        )

        world_id = event.payload.get("world_id", "default")

        try:
            result = self._tick_service.process_tick(
                world_id=world_id,
                days_advanced=event.days_advanced,
            )

            if result.is_ok:
                tick_result = result.unwrap()
                logger.info(
                    "time_advanced_event_processed",
                    event_id=event.event_id,
                    world_id=world_id,
                    success=tick_result.success,
                    resources_updated=tick_result.resources_updated,
                    diplomatic_changes=tick_result.diplomatic_changes,
                )
                return tick_result.success
            else:
                error = result.unwrap_err()
                logger.error(
                    "time_advanced_event_failed",
                    event_id=event.event_id,
                    world_id=world_id,
                    error=error.message,
                )
                return False

        except Exception as e:
            logger.error(
                "time_advanced_event_failed",
                event_id=event.event_id,
                world_id=world_id,
                error=str(e),
                exc_info=True,
            )

            return False  # EventHandler contract: return False on failure

    @classmethod
    def create_for_event_bus(cls) -> "TimeAdvancedHandler":
        """Factory method to create a handler for EventBus registration.

        Returns:
            TimeAdvancedHandler instance ready for event subscription
        """
        return cls()
