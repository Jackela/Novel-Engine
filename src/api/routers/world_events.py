"""World Events API router for history event operations.

This module provides API endpoints for managing world historical events,
following the OpenSpec specification for the W5 Events System.

Following Hexagonal Architecture:
- Router layer: Input validation, dependency injection, response formatting
- Service layer: Business logic (EventService)
- Repository layer: Data persistence (via DI)

Endpoints:
    GET /api/world/events - List events with pagination and filtering
    POST /api/world/events - Create manual event
    GET /api/world/events/{event_id} - Get single event
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from src.api.schemas.system_schemas import ErrorDetail
from src.api.schemas.world_schemas import (
    CreateEventRequest,
    EventListResponse,
    HistoryEventResponse,
)
from src.contexts.world.application.services.event_service import EventService
from src.contexts.world.domain.entities import HistoryEvent
from src.contexts.world.domain.ports.event_repository import EventRepository
from src.contexts.world.domain.ports.rumor_repository import RumorRepository

logger = structlog.get_logger()

router = APIRouter(tags=["world-events"])

# Default world ID for single-world MVP
DEFAULT_WORLD_ID = "default"


def get_event_repository(request: Request) -> EventRepository:
    """Get the EventRepository from DI container.

    Uses app.state.event_repository registered during startup.
    Falls back to creating a new repository if not configured.

    Args:
        request: FastAPI request object

    Returns:
        EventRepository instance

    Raises:
        RuntimeError: If repository not configured
    """
    repo = getattr(request.app.state, "event_repository", None)
    if repo is None:
        # Fallback: create in-memory repository for testing
        # Use a module-level singleton to ensure consistency across requests
        from src.contexts.world.infrastructure.persistence.in_memory_event_repository import (
            InMemoryEventRepository,
        )

        # Check if we already have a shared instance
        if not hasattr(get_event_repository, "_shared_repo"):
            get_event_repository._shared_repo = InMemoryEventRepository()
            logger.warning("event_repository_fallback_created_shared")

        repo = get_event_repository._shared_repo
        request.app.state.event_repository = repo
    return repo


def get_rumor_repository(request: Request) -> RumorRepository:
    """Get the RumorRepository from DI container.

    Uses app.state.rumor_repository registered during startup.
    Falls back to creating a new repository if not configured.

    Args:
        request: FastAPI request object

    Returns:
        RumorRepository instance

    Raises:
        RuntimeError: If repository not configured
    """
    repo = getattr(request.app.state, "rumor_repository", None)
    if repo is None:
        # Fallback: create in-memory repository for testing
        # Use a module-level singleton to ensure consistency across requests
        from src.contexts.world.infrastructure.persistence.in_memory_rumor_repository import (
            InMemoryRumorRepository,
        )

        # Check if we already have a shared instance
        if not hasattr(get_rumor_repository, "_shared_repo"):
            get_rumor_repository._shared_repo = InMemoryRumorRepository()
            logger.warning("rumor_repository_fallback_created_shared")

        repo = get_rumor_repository._shared_repo
        request.app.state.rumor_repository = repo
    return repo


def get_event_service(
    event_repo: EventRepository = Depends(get_event_repository),
    rumor_repo: RumorRepository = Depends(get_rumor_repository),
) -> EventService:
    """Get the EventService with injected repositories.

    Creates an EventService instance using repositories from the DI container.
    This follows the dependency injection pattern for proper hexagonal architecture.

    Args:
        event_repo: EventRepository from DI container
        rumor_repo: RumorRepository from DI container

    Returns:
        EventService instance with injected repositories
    """
    return EventService(event_repo, rumor_repo)


def _event_to_response(event: HistoryEvent) -> HistoryEventResponse:
    """Convert HistoryEvent domain entity to API response model.

    This function transforms the internal domain representation to the
    external API format, handling optional fields and type conversions.

    Args:
        event: HistoryEvent domain entity

    Returns:
        HistoryEventResponse for the API
    """
    # Convert structured_date to dict if present
    structured_date: Optional[Dict[str, Any]] = None
    if event.structured_date:
        structured_date = event.structured_date.to_dict()

    # Convert timestamps to ISO format strings
    created_at: Optional[str] = None
    if event.created_at:
        created_at = event.created_at.isoformat()

    updated_at: Optional[str] = None
    if event.updated_at:
        updated_at = event.updated_at.isoformat()

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
        structured_date=structured_date,
        created_at=created_at,
        updated_at=updated_at,
    )


@router.get("/world/events", response_model=EventListResponse)
async def list_events(
    world_id: str = Query(default=DEFAULT_WORLD_ID, description="World ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    impact_scope: Optional[str] = Query(None, description="Filter by impact scope"),
    faction_id: Optional[str] = Query(None, description="Filter by faction ID"),
    location_id: Optional[str] = Query(None, description="Filter by location ID"),
    is_secret: Optional[bool] = Query(None, description="Filter by secret status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=20, ge=1, le=100, description="Items per page"),
    service: EventService = Depends(get_event_service),
) -> EventListResponse:
    """List historical events with pagination and filtering.

    Returns a paginated list of historical events sorted by date (newest first).
    Supports filtering by event type, impact scope, faction, location, and secret status.

    Args:
        world_id: World ID to filter events
        event_type: Optional filter by event type (e.g., 'war', 'treaty')
        impact_scope: Optional filter by scope ('local', 'regional', 'global')
        faction_id: Optional filter by faction ID involved
        location_id: Optional filter by location ID
        is_secret: Optional filter by secret status
        page: Page number (1-indexed)
        per_page: Number of items per page (1-100)
        service: Injected EventService

    Returns:
        EventListResponse with paginated events

    Example:
        GET /api/world/events?world_id=default&event_type=war&page=1
    """
    logger.debug(
        "list_events_request",
        world_id=world_id,
        page=page,
        per_page=per_page,
        filters={
            "event_type": event_type,
            "impact_scope": impact_scope,
            "faction_id": faction_id,
            "location_id": location_id,
            "is_secret": is_secret,
        },
    )

    # Delegate to service layer
    result = await service.list_events(
        world_id=world_id,
        event_type=event_type,
        impact_scope=impact_scope,
        faction_id=faction_id,
        location_id=location_id,
        is_secret=is_secret,
        page=page,
        page_size=per_page,
    )

    logger.debug(
        "list_events_response",
        world_id=world_id,
        total_count=result.total_count,
        page=result.page,
        page_size=result.page_size,
        returned_count=len(result.events),
    )

    return EventListResponse(
        events=[_event_to_response(e) for e in result.events],
        total_count=result.total_count,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
    )


@router.post("/world/events", response_model=HistoryEventResponse, status_code=201)
async def create_event(
    request_body: CreateEventRequest,
    world_id: str = Query(default=DEFAULT_WORLD_ID, description="World ID"),
    service: EventService = Depends(get_event_service),
) -> HistoryEventResponse:
    """Create a new historical event.

    Creates a manual event with the provided details. Optionally generates
    a rumor if `generate_rumor` is set to true in the request.

    Args:
        request_body: CreateEventRequest with event details
        world_id: World ID
        service: Injected EventService

    Returns:
        HistoryEventResponse with the created event

    Raises:
        400: If event creation fails validation

    Example:
        POST /api/world/events
        {
            "name": "The Great War",
            "description": "A devastating conflict...",
            "event_type": "war",
            "generate_rumor": true
        }
    """
    logger.info(
        "create_event_request",
        world_id=world_id,
        event_name=request_body.name,
        event_type=request_body.event_type,
        generate_rumor=request_body.generate_rumor,
    )

    # Delegate to service layer
    result = await service.create_event(world_id=world_id, data=request_body)

    if result.is_error:
        logger.warning(
            "create_event_failed",
            world_id=world_id,
            error=result.error,
        )
        raise HTTPException(
            status_code=400,
            detail=ErrorDetail(
                code="EVENT_CREATION_FAILED",
                message=result.error,
            ).model_dump(),
        )

    event, rumor = result.value

    # Log rumor generation result
    if request_body.generate_rumor:
        if rumor:
            logger.info(
                "rumor_generated_from_event",
                world_id=world_id,
                event_id=event.id,
                rumor_id=rumor.rumor_id,
            )
        else:
            logger.warning(
                "rumor_generation_failed",
                world_id=world_id,
                event_id=event.id,
                reason="no_locations",
            )

    logger.info(
        "event_created",
        world_id=world_id,
        event_id=event.id,
        event_name=event.name,
    )

    return _event_to_response(event)


@router.get("/world/events/{event_id}", response_model=HistoryEventResponse)
async def get_event(
    event_id: str,
    world_id: str = Query(default=DEFAULT_WORLD_ID, description="World ID"),
    service: EventService = Depends(get_event_service),
) -> HistoryEventResponse:
    """Get a single historical event.

    Retrieves detailed information about a specific event.

    Args:
        event_id: Unique identifier for the event
        world_id: World ID
        service: Injected EventService

    Returns:
        HistoryEventResponse with full event details

    Raises:
        404: Event not found

    Example:
        GET /api/world/events/evt-123
    """
    logger.debug(
        "get_event_request",
        world_id=world_id,
        event_id=event_id,
    )

    # Delegate to service layer
    event = await service.get_event(event_id=event_id, world_id=world_id)

    if event is None:
        logger.warning(
            "get_event_not_found",
            world_id=world_id,
            event_id=event_id,
        )
        raise HTTPException(
            status_code=404,
            detail=ErrorDetail(
                code="EVENT_NOT_FOUND",
                message=f"Event '{event_id}' not found in world '{world_id}'",
            ).model_dump(),
        )

    logger.debug(
        "get_event_found",
        world_id=world_id,
        event_id=event_id,
    )

    return _event_to_response(event)
