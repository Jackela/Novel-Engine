"""Events Router - SSE streaming and analytics endpoints."""

from __future__ import annotations

import secrets
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.api.schemas import AnalyticsMetricsResponse, SSEStatsResponse
from src.api.services.events_service import EventsService

router = APIRouter(tags=["Dashboard"])


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
):
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
