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

import base64
import time
from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from src.api.schemas.system_schemas import ErrorDetail
from src.api.schemas.world_schemas import (
    BulkImportFormat,
    BulkImportRequest,
    BulkImportResponse,
    CreateEventRequest,
    EventListResponse,
    HistoryEventResponse,
    ImportError,
    ImportOptions,
)
from src.contexts.world.application.services.event_service import EventService
from src.contexts.world.domain.entities import HistoryEvent
from src.contexts.world.domain.ports.event_repository import EventRepository
from src.contexts.world.domain.ports.rumor_repository import RumorRepository
from src.contexts.world.infrastructure.parsers import CSVEventParser, JSONEventParser

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


@router.post("/world/{world_id}/events/bulk-import", response_model=BulkImportResponse)
async def bulk_import_events(
    world_id: str,
    request: BulkImportRequest,
    service: EventService = Depends(get_event_service),
) -> BulkImportResponse:
    """Bulk import historical events from CSV or JSON.

    Imports multiple events from a file, with optional rumor generation.
    Returns detailed import statistics and any errors encountered.

    Args:
        world_id: World ID to import events into
        request: BulkImportRequest with format, data, and options
        service: Injected EventService

    Returns:
        BulkImportResponse with import statistics

    Raises:
        400: If import fails validation

    Example:
        POST /api/world/default/events/bulk-import
        {
            "format": "csv",
            "data": "base64_encoded_csv_content",
            "options": {
                "atomic": true,
                "generate_rumors": false
            }
        }
    """
    start_time = time.time()

    logger.info(
        "bulk_import_events_request",
        world_id=world_id,
        format=request.format,
        data_length=len(request.data),
    )

    # Decode base64 data
    try:
        decoded_bytes = base64.b64decode(request.data)
        decoded_content = decoded_bytes.decode("utf-8")
    except Exception as e:
        logger.error("bulk_import_decode_error", error=str(e))
        raise HTTPException(
            status_code=400,
            detail=ErrorDetail(
                code="IMPORT_DECODE_ERROR",
                message=f"Failed to decode import data: {e}",
            ).model_dump(),
        )

    # Parse based on format
    if request.format == BulkImportFormat.CSV:
        parser = CSVEventParser()
        parse_result = parser.parse(decoded_content)
        events_data = parse_result.events
        parse_errors = parse_result.errors
    elif request.format == BulkImportFormat.JSON:
        parser = JSONEventParser()
        parse_result = parser.parse(decoded_content)
        events_data = parse_result.events
        parse_errors = parse_result.errors
    else:
        raise HTTPException(
            status_code=400,
            detail=ErrorDetail(
                code="INVALID_FORMAT",
                message=f"Unsupported format: {request.format}",
            ).model_dump(),
        )

    # If there are parse errors and we're not skipping validation, return them
    if parse_errors and not (request.options and request.options.skip_validation):
        logger.warning(
            "bulk_import_parse_errors",
            world_id=world_id,
            error_count=len(parse_errors),
        )
        return BulkImportResponse(
            success=False,
            total=(
                parse_result.total_rows
                if hasattr(parse_result, "total_rows")
                else len(events_data) + len(parse_errors)
            ),
            imported=0,
            failed=len(parse_errors),
            imported_ids=[],
            errors=[ImportError(**e) for e in parse_errors[:100]],  # Limit errors
            generated_rumors=0,
            processing_time_ms=int((time.time() - start_time) * 1000),
        )

    # Import events
    options = request.options or ImportOptions()
    result = await service.bulk_import_events(
        world_id=world_id,
        events_data=events_data,
        generate_rumors=options.generate_rumors,
        atomic=options.atomic,
    )

    processing_time_ms = int((time.time() - start_time) * 1000)

    if result.is_error:
        logger.error(
            "bulk_import_failed",
            world_id=world_id,
            error=result.error,
        )
        raise HTTPException(
            status_code=400,
            detail=ErrorDetail(
                code="BULK_IMPORT_FAILED",
                message=result.error,
            ).model_dump(),
        )

    import_result = result.value

    logger.info(
        "bulk_import_completed",
        world_id=world_id,
        total=import_result["imported_count"] + import_result["failed_count"],
        imported=import_result["imported_count"],
        failed=import_result["failed_count"],
        processing_time_ms=processing_time_ms,
    )

    return BulkImportResponse(
        success=import_result["failed_count"] == 0,
        total=import_result["imported_count"] + import_result["failed_count"],
        imported=import_result["imported_count"],
        failed=import_result["failed_count"],
        imported_ids=import_result["imported_ids"],
        errors=[ImportError(**e) for e in import_result["errors"][:100]],
        generated_rumors=import_result["generated_rumors"],
        processing_time_ms=processing_time_ms,
    )


@router.get("/world/{world_id}/events/export")
async def export_events(
    world_id: str,
    format: str = Query(default="json", description="Export format: json"),
    from_date: Optional[str] = Query(None, description="Filter from date"),
    to_date: Optional[str] = Query(None, description="Filter to date"),
    event_types: Optional[str] = Query(None, description="Comma-separated event types"),
    service: EventService = Depends(get_event_service),
):
    """Export events as a timeline.

    Exports events in various formats (JSON, PDF, PNG) for external analysis.

    Args:
        world_id: World ID to export events from
        format: Export format (currently supports: json)
        from_date: Optional filter for events from this date
        to_date: Optional filter for events to this date
        event_types: Optional comma-separated list of event types
        service: Injected EventService

    Returns:
        EventTimelineExport for JSON format, or binary data for PDF/PNG

    Example:
        GET /api/world/default/events/export?format=json&event_types=war,battle
    """
    logger.info(
        "export_events_request",
        world_id=world_id,
        format=format,
        from_date=from_date,
        to_date=to_date,
        event_types=event_types,
    )

    # Parse event types
    type_list = None
    if event_types:
        type_list = [t.strip() for t in event_types.split(",") if t.strip()]

    # Export timeline
    timeline_data = await service.export_timeline(
        world_id=world_id,
        from_date=from_date,
        to_date=to_date,
        event_types=type_list,
    )

    # Format-specific handling
    if format.lower() == "json":
        from datetime import datetime

        timeline_data["metadata"]["generated_at"] = datetime.utcnow().isoformat()
        return timeline_data
    elif format.lower() in ("pdf", "png"):
        # TODO: Implement PDF/PNG export
        raise HTTPException(
            status_code=501,
            detail=ErrorDetail(
                code="NOT_IMPLEMENTED",
                message=f"Export format '{format}' is not yet implemented",
            ).model_dump(),
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=ErrorDetail(
                code="INVALID_FORMAT",
                message=f"Unsupported export format: {format}",
            ).model_dump(),
        )
