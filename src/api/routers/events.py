"""Events Router - SSE streaming, analytics, and historical events endpoints."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.api.schemas import (
    AnalyticsMetricsResponse,
    CreateEventRequest,
    EventListResponse,
    HistoryEventResponse,
    SSEStatsResponse,
)
from src.api.services.events_service import EventsService
from src.contexts.world.domain.entities.history_event import (
    EventOutcome,
    EventSignificance,
    EventType,
    HistoryEvent,
    ImpactScope,
)

router = APIRouter(tags=["Dashboard", "History Events"])


def get_events_service(request: Request) -> EventsService:
    """Dependency injection for events service."""
    return EventsService(request.app)


def _resolve_event_interval(interval_seconds: Optional[float]) -> float:
    """Resolve and clamp event interval."""
    default_interval = 2.0
    if interval_seconds is None:
        return default_interval
    try:
        interval_value = float(interval_seconds)
    except (TypeError, ValueError):
        return default_interval
    return max(0.01, min(interval_value, 10.0))


@router.get("/events/stream")
async def stream_events(
    request: Request,
    limit: Optional[int] = None,
    interval: Optional[float] = None,
    service: EventsService = Depends(get_events_service),
) -> StreamingResponse:
    """Stream SSE events to client."""
    client_id = secrets.token_hex(8)
    interval_seconds = _resolve_event_interval(interval)

    return StreamingResponse(
        service.generate_events(
            client_id,
            limit=limit,
            interval_seconds=interval_seconds,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


class EmitEventRequest(BaseModel):
    """Request to emit a dashboard event."""

    type: str = Field(
        default="system",
        description="Event type: character, story, system, interaction",
    )
    title: str = Field(description="Event title")
    description: str = Field(description="Event description")
    severity: str = Field(
        default="low", description="Event severity: low, medium, high"
    )
    character_name: Optional[str] = Field(
        default=None, description="Character name for character events"
    )


class EmitEventResponse(BaseModel):
    """Response after emitting event."""

    success: bool
    message: str
    event_id: str
    connected_clients: int


@router.post("/events/emit", response_model=EmitEventResponse)
async def emit_dashboard_event(
    payload: EmitEventRequest,
    service: EventsService = Depends(get_events_service),
) -> EmitEventResponse:
    """Emit event to all connected clients."""
    event_data = service.create_event(
        event_type=payload.type,
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        character_name=payload.character_name,
    )

    service.broadcast_event(event_data)
    stats = service.get_stats()

    return EmitEventResponse(
        success=True,
        message="Event broadcast to all connected clients",
        event_id=event_data.id,
        connected_clients=stats.connected_clients,
    )


@router.get("/events/stats", response_model=SSEStatsResponse)
async def get_sse_stats(
    service: EventsService = Depends(get_events_service),
) -> SSEStatsResponse:
    """Get SSE connection statistics."""
    return service.get_stats()


@router.get("/analytics/metrics", response_model=AnalyticsMetricsResponse)
async def get_analytics_metrics(
    request: Request,
    service: EventsService = Depends(get_events_service),
) -> AnalyticsMetricsResponse:
    """Get analytics metrics for dashboard."""
    api_service = getattr(request.app.state, "api_service", None)
    return await service.get_analytics_metrics(api_service)


# === Historical Events Storage (MVP in-memory implementation) ===
# In production, this would be replaced with a repository pattern

_world_events: Dict[str, Dict[str, HistoryEvent]] = {}


def _get_events_storage(world_id: str) -> Dict[str, HistoryEvent]:
    """Get or create events storage for a world."""
    if world_id not in _world_events:
        _world_events[world_id] = {}
    return _world_events[world_id]


def reset_events_storage() -> None:
    """Reset events storage (for testing)."""
    global _world_events
    _world_events = {}
# === Helper Functions ===


def _parse_event_type(value: str) -> EventType:
    """Parse event type string to EventType enum."""
    try:
        return EventType(value.lower())
    except ValueError:
        valid_types = [t.value for t in EventType]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event_type. Must be one of: {valid_types}",
        )


def _parse_event_significance(value: str) -> EventSignificance:
    """Parse significance string to EventSignificance enum."""
    try:
        return EventSignificance(value.lower())
    except ValueError:
        valid_levels = [s.value for s in EventSignificance]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid significance. Must be one of: {valid_levels}",
        )


def _parse_event_outcome(value: str) -> EventOutcome:
    """Parse outcome string to EventOutcome enum."""
    try:
        return EventOutcome(value.lower())
    except ValueError:
        valid_outcomes = [o.value for o in EventOutcome]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid outcome. Must be one of: {valid_outcomes}",
        )


def _parse_impact_scope(value: Optional[str]) -> Optional[ImpactScope]:
    """Parse impact scope string to ImpactScope enum."""
    if value is None:
        return None
    try:
        return ImpactScope(value.lower())
    except ValueError:
        valid_scopes = [s.value for s in ImpactScope]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid impact_scope. Must be one of: {valid_scopes}",
        )


def _event_to_response(event: HistoryEvent) -> HistoryEventResponse:
    """Convert HistoryEvent domain entity to API response model."""
    return HistoryEventResponse(
        id=event.id,
        name=event.name,
        description=event.description,
        event_type=event.event_type.value,
        significance=event.significance.value,
        outcome=event.outcome.value,
        date_description=event.date_description,
        duration_description=event.duration_description,
        location_ids=event.location_ids,
        faction_ids=event.faction_ids,
        key_figures=event.key_figures,
        causes=event.causes,
        consequences=event.consequences,
        preceding_event_ids=event.preceding_event_ids,
        following_event_ids=event.following_event_ids,
        related_event_ids=event.related_event_ids,
        is_secret=event.is_secret,
        sources=event.sources,
        narrative_importance=event.narrative_importance,
        impact_scope=event.impact_scope.value if event.impact_scope else None,
        affected_faction_ids=event.affected_faction_ids,
        affected_location_ids=event.affected_location_ids,
        structured_date=(
            event.structured_date.to_dict() if event.structured_date else None
        ),
        created_at=event.created_at.isoformat() if event.created_at else None,
        updated_at=event.updated_at.isoformat() if event.updated_at else None,
    )


# === Historical Events Endpoints ===


@router.get("/world/{world_id}/events", response_model=EventListResponse)
async def list_historical_events(
    world_id: str,
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    impact_scope: Optional[str] = Query(None, description="Filter by impact scope"),
    from_date: Optional[str] = Query(None, description="Filter events from this date"),
    to_date: Optional[str] = Query(None, description="Filter events to this date"),
    faction_id: Optional[str] = Query(None, description="Filter by faction ID"),
    location_id: Optional[str] = Query(None, description="Filter by location ID"),
    is_secret: Optional[bool] = Query(None, description="Filter by secret status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> EventListResponse:
    """
    List historical events for a world with pagination and filtering.

    Args:
        world_id: Unique identifier for the world
        event_type: Optional filter by event type (e.g., war, battle, treaty)
        impact_scope: Optional filter by impact scope (local, regional, global)
        from_date: Optional filter events from this date
        to_date: Optional filter events to this date
        faction_id: Optional filter by faction ID involved
        location_id: Optional filter by location ID
        is_secret: Optional filter by secret status
        page: Page number for pagination (starts at 1)
        page_size: Number of items per page (1-100)

    Returns:
        EventListResponse with paginated list of events
    """
    storage = _get_events_storage(world_id)
    events = list(storage.values())

    # Apply filters
    if event_type:
        try:
            et = EventType(event_type.lower())
            events = [e for e in events if e.event_type == et]
        except ValueError:
            pass  # Invalid filter, ignore

    if impact_scope:
        try:
            scope = ImpactScope(impact_scope.lower())
            events = [e for e in events if e.impact_scope == scope]
        except ValueError:
            pass  # Invalid filter, ignore

    if faction_id:
        events = [
            e
            for e in events
            if faction_id in e.faction_ids
            or (e.affected_faction_ids and faction_id in e.affected_faction_ids)
        ]

    if location_id:
        events = [
            e
            for e in events
            if location_id in e.location_ids
            or (e.affected_location_ids and location_id in e.affected_location_ids)
        ]

    if is_secret is not None:
        events = [e for e in events if e.is_secret == is_secret]

    # Date filtering (simplified - matches against date_description for MVP)
    # In production, this would use structured_date for proper date comparison
    if from_date:
        events = [e for e in events if from_date.lower() in e.date_description.lower()]
    if to_date:
        events = [e for e in events if to_date.lower() in e.date_description.lower()]

    # Sort by created_at descending (newest first)
    events.sort(key=lambda e: e.created_at or datetime.min, reverse=True)

    # Paginate
    total_count = len(events)
    total_pages = (total_count + page_size - 1) // page_size
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_events = events[start_idx:end_idx]

    return EventListResponse(
        events=[_event_to_response(e) for e in paginated_events],
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "/world/{world_id}/events", response_model=HistoryEventResponse, status_code=201
)
async def create_historical_event(
    world_id: str,
    request: CreateEventRequest,
) -> HistoryEventResponse:
    """
    Create a new historical event for a world.

    Args:
        world_id: Unique identifier for the world
        request: CreateEventRequest with event details

    Returns:
        HistoryEventResponse with the created event

    Raises:
        400: Invalid request data (e.g., invalid event_type)
    """
    storage = _get_events_storage(world_id)

    # Parse enums
    event_type = _parse_event_type(request.event_type)
    significance = _parse_event_significance(request.significance)
    outcome = _parse_event_outcome(request.outcome)
    impact_scope = _parse_impact_scope(request.impact_scope)

    # Create event
    event = HistoryEvent(
        id=str(uuid.uuid4()),
        name=request.name,
        description=request.description,
        event_type=event_type,
        significance=significance,
        outcome=outcome,
        date_description=request.date_description,
        duration_description=request.duration_description,
        location_ids=request.location_ids or [],
        faction_ids=request.faction_ids or [],
        key_figures=request.key_figures or [],
        causes=request.causes or [],
        consequences=request.consequences or [],
        preceding_event_ids=request.preceding_event_ids or [],
        following_event_ids=request.following_event_ids or [],
        related_event_ids=request.related_event_ids or [],
        is_secret=request.is_secret,
        sources=request.sources or [],
        narrative_importance=request.narrative_importance,
        impact_scope=impact_scope,
        affected_faction_ids=request.affected_faction_ids,
        affected_location_ids=request.affected_location_ids,
        structured_date=None,  # Will be set by simulation service
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Validate
    try:
        event.validate()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Store
    storage[event.id] = event

    return _event_to_response(event)


@router.get("/world/{world_id}/events/{event_id}", response_model=HistoryEventResponse)
async def get_historical_event(
    world_id: str,
    event_id: str,
) -> HistoryEventResponse:
    """
    Get details of a specific historical event.

    Args:
        world_id: Unique identifier for the world
        event_id: Unique identifier for the event

    Returns:
        HistoryEventResponse with the event details

    Raises:
        404: Event not found
    """
    storage = _get_events_storage(world_id)

    if event_id not in storage:
        raise HTTPException(
            status_code=404,
            detail=f"Event '{event_id}' not found in world '{world_id}'",
        )

    event = storage[event_id]
    return _event_to_response(event)
