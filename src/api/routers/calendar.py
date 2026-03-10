"""Calendar API router for world time operations.

This module provides API endpoints for managing world calendar operations,
including retrieving the current calendar state and advancing time.
"""

from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, HTTPException

from src.api.schemas import AdvanceCalendarRequest, CalendarResponse, ErrorDetail
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar

router = APIRouter(tags=["calendar"])

# In-memory storage for world calendars (MVP implementation)
# In production, this would be replaced with a repository pattern
_world_calendars: Dict[str, WorldCalendar] = {}


def get_calendar_storage() -> Dict[str, WorldCalendar]:
    """Get the calendar storage dictionary."""
    return _world_calendars


def reset_calendar_storage() -> None:
    """Reset calendar storage (for testing)."""
    global _world_calendars
    _world_calendars = {}


# === Helper Functions ===


def _get_or_create_calendar(world_id: str) -> WorldCalendar:
    """
    Get existing calendar for world or create a default one.

    Args:
        world_id: Unique identifier for the world

    Returns:
        WorldCalendar for the world (creates default if not exists)
    """
    if world_id not in _world_calendars:
        # Create a default calendar for new worlds
        _world_calendars[world_id] = WorldCalendar(
            year=1, month=1, day=1, era_name="First Age"
        )
    return _world_calendars[world_id]


def _calendar_to_response(calendar: WorldCalendar) -> CalendarResponse:
    """
    Convert WorldCalendar domain object to API response model.

    Args:
        calendar: WorldCalendar domain object

    Returns:
        CalendarResponse for the API
    """
    return CalendarResponse(
        year=calendar.year,
        month=calendar.month,
        day=calendar.day,
        era_name=calendar.era_name,
        formatted_date=calendar.format(),
        days_per_month=calendar.days_per_month,
        months_per_year=calendar.months_per_year,
    )


# === Endpoints ===


@router.get("/calendar/{world_id}", response_model=CalendarResponse)
async def get_calendar(world_id: str) -> CalendarResponse:
    """
    Get the current calendar state for a world.

    Args:
        world_id: Unique identifier for the world

    Returns:
        CalendarResponse with current calendar state

    Raises:
        404: If world not found (no calendar exists)
    """
    if world_id not in _world_calendars:
        raise HTTPException(
            status_code=404,
            detail=ErrorDetail(
                code="WORLD_NOT_FOUND",
                message=f"World '{world_id}' not found",
            ).model_dump(),
        )

    calendar = _world_calendars[world_id]
    return _calendar_to_response(calendar)


@router.post("/calendar/{world_id}/advance", response_model=CalendarResponse)
async def advance_calendar(
    world_id: str, request: AdvanceCalendarRequest
) -> CalendarResponse:
    """
    Advance the calendar for a world by a specified number of days.

    Args:
        world_id: Unique identifier for the world
        request: AdvanceCalendarRequest with days to advance

    Returns:
        CalendarResponse with updated calendar state

    Raises:
        404: If world not found (no calendar exists)
        400: If advance operation fails (e.g., invalid days value)
    """
    if world_id not in _world_calendars:
        raise HTTPException(
            status_code=404,
            detail=ErrorDetail(
                code="WORLD_NOT_FOUND",
                message=f"World '{world_id}' not found",
            ).model_dump(),
        )

    calendar = _world_calendars[world_id]
    result = calendar.advance(request.days)

    if result.is_error:
        raise HTTPException(
            status_code=400,
            detail=ErrorDetail(
                code="CALENDAR_ADVANCE_FAILED",
                message=f"Failed to advance calendar: {str(result.error)}",
            ).model_dump(),
        )

    # Update stored calendar - unwrap() is safe here since we checked is_error
    updated_calendar = result.unwrap()
    if updated_calendar is None:
        raise HTTPException(
            status_code=400,
            detail=ErrorDetail(
                code="CALENDAR_ADVANCE_FAILED",
                message="Failed to advance calendar: result was None",
            ).model_dump(),
        )
    _world_calendars[world_id] = updated_calendar
    return _calendar_to_response(updated_calendar)
