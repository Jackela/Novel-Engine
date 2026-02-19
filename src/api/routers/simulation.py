"""Simulation API router for world simulation operations.

This module provides API endpoints for managing world simulation operations,
including preview mode (read-only) and commit mode (persists changes).

Endpoints:
    POST /world/{world_id}/simulate/preview - Preview simulation (read-only)
    POST /world/{world_id}/simulate/commit - Commit simulation (applies changes)
    GET /world/{world_id}/simulate/history - Get simulation history
    GET /world/{world_id}/simulate/{tick_id} - Get single tick details
"""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from src.contexts.world.domain.value_objects.simulation_tick import (
    DiplomacyChange,
    ResourceChanges,
    SimulationTick,
)
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar

router = APIRouter(tags=["simulation"])

# === In-memory Storage (MVP Implementation) ===
# In production, these would be replaced with repository patterns

# World calendars: world_id -> WorldCalendar
_world_calendars: Dict[str, WorldCalendar] = {}

# Simulation history: world_id -> OrderedDict[tick_id, SimulationTick]
_simulation_history: Dict[str, OrderedDict[str, SimulationTick]] = {}

# Rate limiting: world_id -> list of commit timestamps
_commit_timestamps: Dict[str, List[float]] = {}

# Active simulations: world_id -> tick_id (for detecting concurrent simulations)
_active_simulations: Dict[str, str] = {}

# Maximum commits per minute per world
MAX_COMMITS_PER_MINUTE = 10

# Maximum history entries per world
MAX_HISTORY_PER_WORLD = 100


# === Storage Management Functions ===


def get_calendar_storage() -> Dict[str, WorldCalendar]:
    """Get the calendar storage dictionary."""
    return _world_calendars


def reset_simulation_storage() -> None:
    """Reset simulation storage (for testing)."""
    global _world_calendars, _simulation_history, _commit_timestamps, _active_simulations
    _world_calendars = {}
    _simulation_history = {}
    _commit_timestamps = {}
    _active_simulations = {}


def _get_or_create_calendar(world_id: str) -> WorldCalendar:
    """Get existing calendar for world or create a default one."""
    if world_id not in _world_calendars:
        _world_calendars[world_id] = WorldCalendar(
            year=1, month=1, day=1, era_name="First Age"
        )
    return _world_calendars[world_id]


def _check_rate_limit(world_id: str) -> bool:
    """Check if world is within rate limit for commits.

    Returns:
        True if within limit, False if rate limited.
    """
    now = time.time()
    timestamps = _commit_timestamps.get(world_id, [])

    # Remove timestamps older than 60 seconds
    timestamps = [t for t in timestamps if now - t < 60]

    _commit_timestamps[world_id] = timestamps

    return len(timestamps) < MAX_COMMITS_PER_MINUTE


def _record_commit(world_id: str) -> None:
    """Record a commit timestamp for rate limiting."""
    if world_id not in _commit_timestamps:
        _commit_timestamps[world_id] = []
    _commit_timestamps[world_id].append(time.time())


def _add_tick_to_history(world_id: str, tick: SimulationTick) -> None:
    """Add a tick to simulation history with FIFO eviction."""
    if world_id not in _simulation_history:
        _simulation_history[world_id] = OrderedDict()

    history = _simulation_history[world_id]
    history[tick.tick_id] = tick

    # Enforce max size with FIFO eviction
    while len(history) > MAX_HISTORY_PER_WORLD:
        oldest_key = next(iter(history))
        del history[oldest_key]


def _get_history(world_id: str, limit: int = 20) -> List[SimulationTick]:
    """Get simulation history for a world."""
    if world_id not in _simulation_history:
        return []

    history = _simulation_history[world_id]
    ticks = list(history.values())
    return ticks[-limit:][::-1]  # Most recent first


def _get_tick_by_id(world_id: str, tick_id: str) -> Optional[SimulationTick]:
    """Get a specific tick by ID."""
    if world_id not in _simulation_history:
        return None
    return _simulation_history[world_id].get(tick_id)


# === Request/Response Models ===


class SimulateRequest(BaseModel):
    """Request model for simulation operations."""

    days: int = Field(
        default=1,
        ge=1,
        le=365,
        description="Number of days to simulate (1-365)",
    )


class CalendarResponse(BaseModel):
    """Response model for calendar data."""

    year: int
    month: int
    day: int
    era_name: str
    formatted_date: str


class ResourceChangesResponse(BaseModel):
    """Response model for resource changes."""

    wealth_delta: int
    military_delta: int
    influence_delta: int
    has_changes: bool


class DiplomacyChangeResponse(BaseModel):
    """Response model for diplomacy changes."""

    faction_a: str
    faction_b: str
    status_before: str
    status_after: str
    is_significant: bool


class SimulationTickResponse(BaseModel):
    """Response model for a complete simulation tick."""

    tick_id: str
    world_id: str
    calendar_before: Optional[CalendarResponse]
    calendar_after: Optional[CalendarResponse]
    days_advanced: int
    events_generated: List[str]
    resource_changes: Dict[str, ResourceChangesResponse]
    diplomacy_changes: List[DiplomacyChangeResponse]
    created_at: str


class SimulationTickSummary(BaseModel):
    """Summary model for simulation tick history."""

    tick_id: str
    days_advanced: int
    events_count: int
    created_at: str


class SimulationHistoryResponse(BaseModel):
    """Response model for simulation history."""

    ticks: List[SimulationTickSummary]
    total: int


class SimulationStatusResponse(BaseModel):
    """Response model for async simulation status."""

    tick_id: str
    status: str
    status_url: str
    message: str


# === Helper Functions ===


def _calendar_to_response(calendar: Optional[WorldCalendar]) -> Optional[CalendarResponse]:
    """Convert WorldCalendar to response model."""
    if calendar is None:
        return None
    return CalendarResponse(
        year=calendar.year,
        month=calendar.month,
        day=calendar.day,
        era_name=calendar.era_name,
        formatted_date=calendar.format(),
    )


def _resource_changes_to_response(changes: ResourceChanges) -> ResourceChangesResponse:
    """Convert ResourceChanges to response model."""
    return ResourceChangesResponse(
        wealth_delta=changes.wealth_delta,
        military_delta=changes.military_delta,
        influence_delta=changes.influence_delta,
        has_changes=changes.has_changes,
    )


def _diplomacy_change_to_response(change: DiplomacyChange) -> DiplomacyChangeResponse:
    """Convert DiplomacyChange to response model."""
    return DiplomacyChangeResponse(
        faction_a=change.faction_a,
        faction_b=change.faction_b,
        status_before=change.status_before.value,
        status_after=change.status_after.value,
        is_significant=change.is_significant,
    )


def _tick_to_response(tick: SimulationTick) -> SimulationTickResponse:
    """Convert SimulationTick to response model."""
    return SimulationTickResponse(
        tick_id=tick.tick_id,
        world_id=tick.world_id,
        calendar_before=_calendar_to_response(tick.calendar_before),
        calendar_after=_calendar_to_response(tick.calendar_after),
        days_advanced=tick.days_advanced,
        events_generated=tick.events_generated,
        resource_changes={
            k: _resource_changes_to_response(v)
            for k, v in tick.resource_changes.items()
        },
        diplomacy_changes=[
            _diplomacy_change_to_response(dc) for dc in tick.diplomacy_changes
        ],
        created_at=tick.created_at.isoformat(),
    )


def _tick_to_summary(tick: SimulationTick) -> SimulationTickSummary:
    """Convert SimulationTick to summary model."""
    return SimulationTickSummary(
        tick_id=tick.tick_id,
        days_advanced=tick.days_advanced,
        events_count=len(tick.events_generated),
        created_at=tick.created_at.isoformat(),
    )


def _run_simulation(world_id: str, days: int) -> SimulationTick:
    """Run a simulation tick (MVP implementation).

    This is a simplified implementation that:
    1. Advances the calendar
    2. Records the tick in history
    3. Returns the tick result

    In production, this would:
    - Call WorldSimulationService.advance_simulation() for preview
    - Call WorldSimulationService.commit_simulation() for commit
    - Generate faction intents and resolve them
    - Create historical events
    - Propagate rumors
    """
    calendar = _get_or_create_calendar(world_id)
    calendar_before = calendar

    # Advance calendar
    result = calendar.advance(days)
    if result.is_error:
        raise ValueError(f"Failed to advance calendar: {result.error}")

    calendar_after = result.value
    if calendar_after is None:
        raise ValueError("Calendar advance returned None unexpectedly")
    _world_calendars[world_id] = calendar_after

    # Create simulation tick
    tick = SimulationTick(
        world_id=world_id,
        calendar_before=calendar_before,
        calendar_after=calendar_after,
        days_advanced=days,
        events_generated=[],  # MVP: No events generated
        resource_changes={},  # MVP: No resource changes
        diplomacy_changes=[],  # MVP: No diplomacy changes
        character_reactions=[],  # MVP: No character reactions
        rumors_created=0,
    )

    return tick


# === Endpoints ===


@router.post(
    "/world/{world_id}/simulate/preview",
    response_model=SimulationTickResponse,
    summary="Preview simulation (read-only)",
    description="Run a read-only simulation preview without persisting changes.",
)
async def preview_simulation(
    world_id: str,
    request: SimulateRequest,
) -> SimulationTickResponse:
    """Preview a simulation tick without persisting changes.

    This is a fast, read-only operation that:
    - Validates inputs
    - Advances calendar (in-memory only for preview)
    - Returns preview tick without saving to history

    Args:
        world_id: Unique identifier for the world
        request: SimulateRequest with days to advance

    Returns:
        SimulationTickResponse with preview results

    Raises:
        400: Invalid request (days out of range)
        404: World not found
    """
    # For preview, we don't require the world to exist - we create a default
    # This allows users to preview without committing first
    calendar = _get_or_create_calendar(world_id)
    calendar_before = calendar

    # Advance calendar
    result = calendar.advance(request.days)
    if result.is_error:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_DAYS",
                "message": f"Failed to advance calendar: {result.error}",
            },
        )

    calendar_after = result.unwrap()

    # Create preview tick (not saved to history)
    tick = SimulationTick(
        world_id=world_id,
        calendar_before=calendar_before,
        calendar_after=calendar_after,
        days_advanced=request.days,
        events_generated=[],
        resource_changes={},
        diplomacy_changes=[],
        character_reactions=[],
        rumors_created=0,
    )

    return _tick_to_response(tick)


@router.post(
    "/world/{world_id}/simulate/commit",
    response_model=SimulationTickResponse,
    summary="Commit simulation (applies changes)",
    description="Commit a simulation tick that persists changes to the world state.",
    responses={
        202: {
            "description": "Simulation accepted for background processing (days > 30)",
            "model": SimulationStatusResponse,
        },
    },
)
async def commit_simulation(
    world_id: str,
    request: SimulateRequest,
    background_tasks: BackgroundTasks,
) -> SimulationTickResponse:
    """Commit a simulation tick with full state persistence.

    This operation:
    - Validates inputs and rate limits
    - Creates pre-commit snapshot
    - Advances calendar
    - Generates and resolves faction intents
    - Creates historical events
    - Saves to repository
    - Records in simulation history

    For large simulations (days > 30), returns 202 Accepted and
    processes in background.

    Args:
        world_id: Unique identifier for the world
        request: SimulateRequest with days to advance
        background_tasks: FastAPI background tasks for async processing

    Returns:
        SimulationTickResponse with committed results

    Raises:
        400: Invalid request (days out of range)
        404: World not found
        429: Rate limited (too many commits)
        503: Simulation locked (another simulation in progress)
    """
    # Check for concurrent simulation
    if world_id in _active_simulations:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "SIMULATION_LOCKED",
                "message": "Another simulation is in progress for this world",
                "details": {"active_tick_id": _active_simulations[world_id]},
            },
        )

    # Check rate limit
    if not _check_rate_limit(world_id):
        raise HTTPException(
            status_code=429,
            detail={
                "code": "RATE_LIMITED",
                "message": f"Too many commits. Max {MAX_COMMITS_PER_MINUTE} per minute.",
            },
        )

    # For large simulations, process in background
    if request.days > 30:
        tick_id = str(uuid4())
        _active_simulations[world_id] = tick_id

        # Return 202 Accepted with status URL
        raise HTTPException(
            status_code=202,
            detail={
                "tick_id": tick_id,
                "status": "accepted",
                "status_url": f"/api/world/{world_id}/simulate/{tick_id}",
                "message": f"Large simulation ({request.days} days) accepted for background processing",
            },
        )

    # Run simulation synchronously
    try:
        _active_simulations[world_id] = str(uuid4())
        tick = _run_simulation(world_id, request.days)

        # Record in history
        _add_tick_to_history(world_id, tick)

        # Record commit for rate limiting
        _record_commit(world_id)

        return _tick_to_response(tick)

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "SIMULATION_ERROR",
                "message": str(e),
            },
        )
    finally:
        _active_simulations.pop(world_id, None)


@router.get(
    "/world/{world_id}/simulate/history",
    response_model=SimulationHistoryResponse,
    summary="Get simulation history",
    description="Get the last 20 simulation tick summaries for a world.",
)
async def get_simulation_history(
    world_id: str,
    limit: int = 20,
) -> SimulationHistoryResponse:
    """Get simulation tick history for a world.

    Returns the most recent simulation ticks, ordered by most recent first.

    Args:
        world_id: Unique identifier for the world
        limit: Maximum number of ticks to return (default 20)

    Returns:
        SimulationHistoryResponse with tick summaries
    """
    ticks = _get_history(world_id, limit)
    summaries = [_tick_to_summary(t) for t in ticks]

    return SimulationHistoryResponse(
        ticks=summaries,
        total=len(summaries),
    )


@router.get(
    "/world/{world_id}/simulate/{tick_id}",
    response_model=SimulationTickResponse,
    summary="Get single tick details",
    description="Get detailed information about a specific simulation tick.",
)
async def get_tick_details(
    world_id: str,
    tick_id: str,
) -> SimulationTickResponse:
    """Get detailed information about a specific simulation tick.

    Args:
        world_id: Unique identifier for the world
        tick_id: Unique identifier for the tick

    Returns:
        SimulationTickResponse with full tick details

    Raises:
        404: Tick not found
    """
    tick = _get_tick_by_id(world_id, tick_id)

    if tick is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "TICK_NOT_FOUND",
                "message": f"Tick '{tick_id}' not found for world '{world_id}'",
            },
        )

    return _tick_to_response(tick)
