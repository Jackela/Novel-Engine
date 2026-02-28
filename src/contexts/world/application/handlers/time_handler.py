"""Time Advanced Event Handler.

This handler subscribes to world.time_advanced events and triggers
faction simulation updates via FactionTickService.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from src.contexts.world.application.services.faction_tick_service import (
    FactionTickService,
    TickResult,
)

if TYPE_CHECKING:
    from src.contexts.world.domain.events.time_events import TimeAdvancedEvent

logger = structlog.get_logger()


class TimeAdvancedHandler:
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

    async def handle(self, event: "TimeAdvancedEvent") -> TickResult:
        """Handle a TimeAdvancedEvent.

        Args:
            event: The TimeAdvancedEvent to process

        Returns:
            TickResult with processing details

        Raises:
            No exceptions are raised - errors are logged and returned in TickResult
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

            logger.info(
                "time_advanced_event_processed",
                event_id=event.event_id,
                world_id=world_id,
                success=result.success,
                resources_updated=result.resources_updated,
                diplomatic_changes=result.diplomatic_changes,
            )

            return result

        except Exception as e:
            logger.error(
                "time_advanced_event_failed",
                event_id=event.event_id,
                world_id=world_id,
                error=str(e),
                exc_info=True,
            )

            return TickResult(
                world_id=world_id,
                days_advanced=event.days_advanced,
                success=False,
                errors=[str(e)],
            )

    @classmethod
    def create_for_event_bus(cls) -> "TimeAdvancedHandler":
        """Factory method to create a handler for EventBus registration.

        Returns:
            TimeAdvancedHandler instance ready for event subscription
        """
        return cls()


def handle_time_advanced(event: "TimeAdvancedEvent") -> None:
    """Sync wrapper for event bus compatibility.

    This function can be registered as a handler with the EventBus.

    Args:
        event: The TimeAdvancedEvent to process
    """
    import asyncio

    handler = TimeAdvancedHandler()

    # Run async handler in sync context
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(handler.handle(event))
    except RuntimeError:
        # No running loop, create new one
        asyncio.run(handler.handle(event))
