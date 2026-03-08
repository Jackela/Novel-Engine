"""World Time API router for calendar operations.

This module provides API endpoints for managing world time operations,
following the OpenSpec specification for the W5 Calendar System.

Endpoints:
    GET /api/world/time - Get current world time
    POST /api/world/time/advance - Advance world time by days
"""

from __future__ import annotations

import os

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.schemas.system_schemas import ErrorDetail
from src.api.schemas.world_schemas import (
    AdvanceTimeRequest,
    WorldTimeResponse,
)
from src.contexts.world.application.services.time_service import TimeService
from src.contexts.world.domain.ports.calendar_repository import CalendarRepository

logger = structlog.get_logger()

router = APIRouter(tags=["world-time"])

# Default world ID for single-world MVP
DEFAULT_WORLD_ID = "default"


def get_repository(request: Request) -> CalendarRepository:
    """Get the CalendarRepository from DI container.

    Uses app.state.calendar_repository registered during startup.
    In testing mode (ORCHESTRATOR_MODE=testing), falls back to in-memory repo.
    In production, raises RuntimeError if repository is not configured.

    Args:
        request: FastAPI request object

    Returns:
        CalendarRepository instance

    Raises:
        RuntimeError: If repository not configured in non-testing mode
    """
    repo = getattr(request.app.state, "calendar_repository", None)
    if repo is None:
        is_testing = os.getenv("ORCHESTRATOR_MODE", "").lower() == "testing"
        if is_testing:
            from src.contexts.world.infrastructure.persistence.in_memory_calendar_repository import (
                InMemoryCalendarRepository,
            )

            repo = InMemoryCalendarRepository()
            logger.warning("using_fallback_repository_test_mode")
        else:
            raise RuntimeError(
                "CalendarRepository not configured. Check startup initialization."
            )
    return repo


def get_time_service(request: Request) -> TimeService:
    """Get the TimeService with injected repository.

    Creates a TimeService instance using the CalendarRepository
    from the DI container.

    Args:
        request: FastAPI request object

    Returns:
        TimeService instance with injected repository
    """
    repo = get_repository(request)
    return TimeService(repo)


def _get_event_bus(request: Request) -> None:
    """Get the EventBus from app.state.

    Reads the EventBus from request.app.state.event_bus which is
    configured during startup. Returns None if not available.

    Args:
        request: FastAPI request object

    Returns:
        EventBus instance or None if not configured
    """
    return getattr(request.app.state, "event_bus", None)


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
async def get_world_time(
    request: Request,
    service: TimeService = Depends(get_time_service),
) -> WorldTimeResponse:
    """Get the current world time.

    Returns the current in-world date. If no calendar exists,
    a default calendar is created (year=1, month=1, day=1, era_name="First Age").

    Args:
        request: FastAPI request object for accessing app.state
        service: Injected TimeService

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
    result = service.get_time(DEFAULT_WORLD_ID)

    if result.is_error:
        raise HTTPException(
            status_code=404,
            detail=ErrorDetail(
                code="WORLD_NOT_FOUND",
                message=f"World time not found for '{DEFAULT_WORLD_ID}'",
            ).model_dump(),
        )

    calendar = result.unwrap()
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
async def advance_world_time(
    request_body: AdvanceTimeRequest,
    fastapi_request: Request,
    service: TimeService = Depends(get_time_service),
) -> WorldTimeResponse:
    """Advance the world time by a specified number of days.

    Advances the in-world calendar and emits a TimeAdvancedEvent.
    The days parameter must be >= 1.

    Args:
        request_body: AdvanceTimeRequest with days to advance
        fastapi_request: FastAPI request object for accessing app.state
        service: Injected TimeService

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
        days=request_body.days,
    )

    result = service.advance_time(DEFAULT_WORLD_ID, request_body.days)

    if result.is_error:
        logger.error(
            "advance_world_time_failed",
            world_id=DEFAULT_WORLD_ID,
            days=request_body.days,
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
    event_bus = _get_event_bus(fastapi_request)
    if event_bus is not None:
        try:
            await event_bus.publish(event)
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
