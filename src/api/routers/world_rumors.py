"""World Rumors API router for rumor operations.

This module provides API endpoints for managing world rumors,
following the OpenSpec specification for the W5 Rumors System.

Following Hexagonal Architecture:
- Router layer: Input validation, dependency injection, response formatting
- Service layer: Business logic (RumorService)
- Repository layer: Data persistence (via DI)

Endpoints:
    GET /api/world/locations/{location_id}/rumors - Get rumors for a location
    GET /api/world/rumors/{rumor_id} - Get single rumor
    GET /api/world/{world_id}/rumors - Get all rumors for a world
"""

from __future__ import annotations

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from src.api.schemas.system_schemas import ErrorDetail
from src.api.schemas.world_schemas import (
    CalendarData,
    GraphData,
    GraphEdge,
    GraphNode,
    RumorListResponse,
    RumorResponse,
    RumorVisualizationResponse,
    SortByEnum,
    VisualizationMetadata,
)
from src.contexts.world.application.services.rumor_service import RumorService
from src.contexts.world.domain.entities import Rumor
from src.contexts.world.domain.ports.rumor_repository import RumorRepository

logger = structlog.get_logger()

router = APIRouter(tags=["world-rumors"])

# Default world ID for single-world MVP
DEFAULT_WORLD_ID = "default"


def get_rumor_repository(request: Request) -> RumorRepository:
    """Get the RumorRepository from DI container.

    Uses app.state.rumor_repository registered during startup.
    Falls back to creating a new repository if not configured.

    Args:
        request: FastAPI request object

    Returns:
        RumorRepository instance
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


def get_rumor_service(
    rumor_repo: RumorRepository = Depends(get_rumor_repository),
) -> RumorService:
    """Get the RumorService with injected repository.

    Creates a RumorService instance using the RumorRepository
    from the DI container.

    Args:
        rumor_repo: RumorRepository from DI container

    Returns:
        RumorService instance with injected repository
    """
    return RumorService(rumor_repo)


def _rumor_to_response(rumor: Rumor) -> RumorResponse:
    """Convert Rumor domain entity to API response model.

    This function transforms the internal domain representation to the
    external API format, handling optional fields and type conversions.

    Args:
        rumor: Rumor domain entity

    Returns:
        RumorResponse for the API
    """
    # Convert created_date to CalendarData if present
    created_date: Optional[CalendarData] = None
    if rumor.created_date:
        created_date = CalendarData(
            year=rumor.created_date.year,
            month=rumor.created_date.month,
            day=rumor.created_date.day,
            era_name=rumor.created_date.era_name,
            formatted=rumor.created_date.format(),
        )

    # Calculate veracity label based on truth value
    veracity_label = RumorService.get_veracity_label(rumor.truth_value)

    return RumorResponse(
        rumor_id=rumor.rumor_id,
        content=rumor.content,
        truth_value=rumor.truth_value,
        origin_type=rumor.origin_type.value,
        source_event_id=rumor.source_event_id,
        origin_location_id=rumor.origin_location_id,
        current_locations=list(rumor.current_locations),
        created_date=created_date,
        spread_count=rumor.spread_count,
        veracity_label=veracity_label,
    )


@router.get("/world/locations/{location_id}/rumors", response_model=RumorListResponse)
async def get_location_rumors(
    location_id: str,
    world_id: str = Query(default=DEFAULT_WORLD_ID, description="World ID"),
    service: RumorService = Depends(get_rumor_service),
) -> RumorListResponse:
    """Get rumors for a specific location.

    Returns all rumors that have spread to the specified location,
    sorted by creation date (most recent first).

    Args:
        location_id: Location ID to get rumors for
        world_id: World ID
        service: Injected RumorService

    Returns:
        RumorListResponse with rumors at the location

    Example:
        GET /api/world/locations/loc-capital/rumors
    """
    logger.debug(
        "get_location_rumors_request",
        world_id=world_id,
        location_id=location_id,
    )

    # Delegate to service layer
    rumors = await service.get_location_rumors(
        location_id=location_id,
        world_id=world_id,
        sort_by=SortByEnum.RECENT,
    )

    logger.debug(
        "get_location_rumors_response",
        world_id=world_id,
        location_id=location_id,
        matching_rumors=len(rumors),
    )

    return RumorListResponse(
        rumors=[_rumor_to_response(r) for r in rumors],
        total=len(rumors),
    )


@router.get(
    "/world/{world_id}/rumors/visualization", response_model=RumorVisualizationResponse
)
async def get_rumor_visualization(
    world_id: str,
    rumor_id: Optional[str] = Query(None, description="Filter by specific rumor ID"),
    from_date: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    to_date: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    max_hops: int = Query(default=5, ge=1, le=10, description="Maximum spread hops"),
    service: RumorService = Depends(get_rumor_service),
) -> RumorVisualizationResponse:
    """Get rumor propagation visualization data.

    Returns graph data (nodes and edges) representing rumor propagation
    across locations. Nodes include both rumors and locations; edges
    represent spread paths.

    Args:
        world_id: World ID to get rumors from
        rumor_id: Optional specific rumor to visualize
        from_date: Optional filter for rumors from this date
        to_date: Optional filter for rumors to this date
        max_hops: Maximum number of spread hops to include
        service: Injected RumorService

    Returns:
        RumorVisualizationResponse with graph data

    Example:
        GET /api/world/default/rumors/visualization?max_hops=3
    """
    logger.debug(
        "get_rumor_visualization_request",
        world_id=world_id,
        rumor_id=rumor_id,
        max_hops=max_hops,
    )

    # Get propagation graph
    graph_data = await service.get_propagation_graph(
        world_id=world_id,
        rumor_id=rumor_id,
        max_hops=max_hops,
    )

    # Convert to response model
    nodes = [
        GraphNode(
            id=node["id"],
            type=node["type"],
            label=node["label"],
            metadata=node.get("metadata", {}),
        )
        for node in graph_data["graph"]["nodes"]
    ]

    edges = [
        GraphEdge(
            id=edge["id"],
            source=edge["source"],
            target=edge["target"],
            type=edge["type"],
            metadata=edge.get("metadata", {}),
        )
        for edge in graph_data["graph"]["edges"]
    ]

    logger.debug(
        "get_rumor_visualization_response",
        world_id=world_id,
        total_nodes=len(nodes),
        total_edges=len(edges),
    )

    from datetime import datetime

    return RumorVisualizationResponse(
        world_id=world_id,
        graph=GraphData(nodes=nodes, edges=edges),
        metadata=VisualizationMetadata(
            total_nodes=graph_data["metadata"]["total_nodes"],
            total_edges=graph_data["metadata"]["total_edges"],
            max_hops=graph_data["metadata"]["max_hops"],
            generated_at=datetime.utcnow().isoformat(),
        ),
    )


@router.get("/world/rumors/{rumor_id}", response_model=RumorResponse)
async def get_rumor(
    rumor_id: str,
    world_id: str = Query(default=DEFAULT_WORLD_ID, description="World ID"),
    service: RumorService = Depends(get_rumor_service),
) -> RumorResponse:
    """Get a single rumor.

    Retrieves detailed information about a specific rumor.

    Args:
        rumor_id: Unique identifier for the rumor
        world_id: World ID
        service: Injected RumorService

    Returns:
        RumorResponse with full rumor details

    Raises:
        404: Rumor not found

    Example:
        GET /api/world/rumors/rumor-123
    """
    logger.debug(
        "get_rumor_request",
        world_id=world_id,
        rumor_id=rumor_id,
    )

    # Delegate to service layer
    rumor = await service.get_rumor(rumor_id=rumor_id, world_id=world_id)

    if rumor is None:
        logger.warning(
            "get_rumor_not_found",
            world_id=world_id,
            rumor_id=rumor_id,
        )
        raise HTTPException(
            status_code=404,
            detail=ErrorDetail(
                code="RUMOR_NOT_FOUND",
                message=f"Rumor '{rumor_id}' not found in world '{world_id}'",
            ).model_dump(),
        )

    logger.debug(
        "get_rumor_found",
        world_id=world_id,
        rumor_id=rumor_id,
    )

    return _rumor_to_response(rumor)


@router.get("/world/{world_id}/rumors", response_model=RumorListResponse)
async def list_world_rumors(
    world_id: str,
    location_id: Optional[str] = Query(
        None, description="Filter by location ID (rumors at this location)"
    ),
    sort_by: SortByEnum = Query(
        SortByEnum.RECENT, description="Sort order: recent, reliable, or spread"
    ),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    service: RumorService = Depends(get_rumor_service),
) -> RumorListResponse:
    """List rumors for a world with optional filtering and sorting.

    Returns all rumors in the world, optionally filtered by location,
    with flexible sorting options.

    Args:
        world_id: World ID to get rumors for
        location_id: Optional filter for rumors at a specific location
        sort_by: Sort order (recent, reliable, spread)
        limit: Maximum number of results to return
        service: Injected RumorService

    Returns:
        RumorListResponse with filtered and sorted rumors

    Example:
        GET /api/world/default/rumors?sort_by=reliable&limit=10
    """
    logger.debug(
        "list_world_rumors_request",
        world_id=world_id,
        location_id=location_id,
        sort_by=sort_by.value,
        limit=limit,
    )

    # Delegate to service layer
    rumors = await service.get_world_rumors(
        world_id=world_id,
        sort_by=sort_by,
        limit=limit,
        location_id=location_id,
    )

    logger.debug(
        "list_world_rumors_response",
        world_id=world_id,
        returned_count=len(rumors),
    )

    return RumorListResponse(
        rumors=[_rumor_to_response(r) for r in rumors],
        total=len(rumors),
    )
