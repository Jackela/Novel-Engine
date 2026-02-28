"""World Time API router for calendar operations.

This module provides API endpoints for managing world time operations,
following the OpenSpec specification for the W5 Calendar System.

Endpoints:
    GET /api/world/time - Get current world time
    POST /api/world/time/advance - Advance world time by days
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException

from src.api.schemas.system_schemas import ErrorDetail
from src.api.schemas.world_schemas import (
    AdvanceTimeRequest,
    WorldTimeResponse,
)
from src.contexts.world.application.services.time_service import TimeService
from src.contexts.world.infrastructure.persistence.in_memory_calendar_repository import (
    InMemoryCalendarRepository,
)
from src.events.event_bus import EventBus

logger = structlog.get_logger()

router = APIRouter(tags=["world-time"])

# Singleton repository and service for the default world
# In a multi-world scenario, this would be dependency-injected
_repository = InMemoryCalendarRepository()
_service = TimeService(_repository)
_event_bus: EventBus | None = None

# Default world ID for single-world MVP
DEFAULT_WORLD_ID = "default"


def set_event_bus(event_bus: EventBus) -> None:
    """Set the event bus for publishing time events.

    This should be called during application startup to enable
    event publishing from the router.

    Args:
        event_bus: The EventBus instance to use for publishing events
    """
    global _event_bus
    _event_bus = event_bus
    logger.info("world_time_router_event_bus_configured")


def _calendar_to_response(calendar) -> WorldTimeResponse:
    """Convert WorldCalendar domain object to API response model.

    Args:
        calendar: WorldCalendar domain object

    Returns:
        WorldTimeResponse for the API
    """
    return WorldTimeResponse(
        year=calendar.year,
        month=calendar.month,
        day=calendar.day,
        era_name=calendar.era_name,
        display_string=calendar.format(),
    )


@router.get("/world/time", response_model=WorldTimeResponse)
async def get_world_time() -> WorldTimeResponse:
    """Get the current world time.

    Returns the current in-world date. If no calendar exists,
    a default calendar is created (year=1, month=1, day=1, era_name="First Age").

    Returns:
        WorldTimeResponse with current calendar state

    Example:
        GET /api/world/time
        {
            "year": 1042,
            "month": 5,
            "day": 14,
            "era_name": "Third Age",
            "display_string": "Year 1042, Month 5, Day 14 - Third Age"
        }
    """
    logger.debug("get_world_time_request", world_id=DEFAULT_WORLD_ID)
    calendar = _service.get_time(DEFAULT_WORLD_ID)
    response = _calendar_to_response(calendar)
    logger.debug(
        "get_world_time_response",
        world_id=DEFAULT_WORLD_ID,
        year=response.year,
        month=response.month,
        day=response.day,
        era_name=response.era_name,
    )
    return response


@router.post("/world/time/advance", response_model=WorldTimeResponse)
async def advance_world_time(request: AdvanceTimeRequest) -> WorldTimeResponse:
    """Advance the world time by a specified number of days.

    Advances the in-world calendar and emits a TimeAdvancedEvent.
    The days parameter must be >= 1.

    Args:
        request: AdvanceTimeRequest with days to advance

    Returns:
        WorldTimeResponse with updated calendar state

    Raises:
        422: If days <= 0 (validation error)
        400: If advance operation fails

    Example:
        POST /api/world/time/advance
        {"days": 5}
        {
            "year": 1042,
            "month": 5,
            "day": 19,
            "era_name": "Third Age",
            "display_string": "Year 1042, Month 5, Day 19 - Third Age"
        }
    """
    logger.info(
        "advance_world_time_request",
        world_id=DEFAULT_WORLD_ID,
        days=request.days,
    )

    result = _service.advance_time(DEFAULT_WORLD_ID, request.days)

    if result.is_error:
        logger.error(
            "advance_world_time_failed",
            world_id=DEFAULT_WORLD_ID,
            days=request.days,
            error=result.error,
        )
        raise HTTPException(
            status_code=400,
            detail=ErrorDetail(
                code="TIME_ADVANCE_FAILED",
                message=result.error,
            ).model_dump(),
        )

    calendar, event = result.value

    # Publish the event to the event bus if available
    if _event_bus is not None:
        try:
            await _event_bus.publish(event)
            logger.info(
                "time_advanced_event_published",
                world_id=DEFAULT_WORLD_ID,
                event_id=event.event_id,
                days_advanced=event.days_advanced,
            )
        except Exception as e:
            # Log failure but don't fail the request - event is still stored in service
            logger.warning(
                "time_advanced_event_publish_failed",
                world_id=DEFAULT_WORLD_ID,
                event_id=event.event_id,
                error=str(e),
                message="Event stored in service but failed to publish to event bus",
            )
    else:
        # No event bus configured - log that event was created but not published
        logger.info(
            "time_advanced_event_created_no_bus",
            world_id=DEFAULT_WORLD_ID,
            event_id=event.event_id,
            days_advanced=event.days_advanced,
            message="Event created but no event bus configured for publishing",
        )

    response = _calendar_to_response(calendar)
    logger.info(
        "advance_world_time_response",
        world_id=DEFAULT_WORLD_ID,
        year=response.year,
        month=response.month,
        day=response.day,
        era_name=response.era_name,
    )
    return response
