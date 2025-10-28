#!/usr/bin/env python3
"""
World Context FastAPI Router

This module implements FastAPI endpoints for the World context, providing
RESTful access to both command (write) and query (read) operations following
CQRS principles.

Endpoints:
- POST /worlds/{world_id}/delta - Apply state changes (commands)
- GET /worlds/{world_id}/slice - Get spatial world data (queries)
- GET /worlds/{world_id}/summary - Get world summary statistics
- GET /worlds/{world_id}/entities - Get entities within area
- GET /worlds/{world_id}/entities/type/{entity_type} - Get entities by type
- GET /worlds/search - Search worlds by criteria

All endpoints follow RESTful principles with proper error handling,
validation, and performance optimization.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

# World Context CQRS Imports
from contexts.world.application.commands.world_commands import (
    ApplyWorldDelta,
    EntityOperation,
    EnvironmentOperation,
    ResetOperation,
    SnapshotOperation,
    TimeOperation,
    WorldOperationType,
)
from contexts.world.application.queries.world_queries import (
    GetEntitiesByType,
    GetEntitiesInArea,
    GetWorldSlice,
    GetWorldSummary,
    QueryExecutionException,
    QueryValidationException,
    SearchWorlds,
    execute_query,
)
from contexts.world.domain.aggregates.world_state import EntityType
from contexts.world.domain.value_objects.coordinates import Coordinates
from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

# Create FastAPI router for World context
router = APIRouter(prefix="/worlds", tags=["worlds"])

# ==================== REQUEST/RESPONSE MODELS ====================

# Command Request Models (Write Operations)


class CoordinatesRequest(BaseModel):
    """Request model for coordinate data."""

    x: float
    y: float
    z: Optional[float] = 0.0


class EntityOperationRequest(BaseModel):
    """Request model for entity operations."""

    operation_type: str = Field(..., description="Type of entity operation")
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    entity_name: Optional[str] = None
    coordinates: Optional[CoordinatesRequest] = None
    new_coordinates: Optional[CoordinatesRequest] = None
    properties: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None

    @field_validator("operation_type")
    @classmethod
    def validate_operation_type(cls, v):
        """Validate operation type against available options."""
        valid_types = [op.value for op in WorldOperationType]
        if v not in valid_types:
            raise ValueError(f"operation_type must be one of: {valid_types}")
        return v

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v):
        """Validate entity type against available options."""
        if v is not None:
            valid_types = [et.value for et in EntityType]
            if v not in valid_types:
                raise ValueError(f"entity_type must be one of: {valid_types}")
        return v


class EnvironmentOperationRequest(BaseModel):
    """Request model for environment operations."""

    environment_changes: Dict[str, Any] = Field(
        ..., description="Environment changes to apply"
    )
    affected_area: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None


class TimeOperationRequest(BaseModel):
    """Request model for time operations."""

    new_time: datetime = Field(..., description="New world time")
    reason: Optional[str] = None


class SnapshotOperationRequest(BaseModel):
    """Request model for snapshot operations."""

    reason: str = Field(..., description="Reason for creating snapshot")
    include_entities: bool = True
    include_environment: bool = True
    metadata: Optional[Dict[str, Any]] = None


class ResetOperationRequest(BaseModel):
    """Request model for reset operations."""

    reason: str = Field(..., description="Reason for resetting world")
    preserve_entities: bool = False
    preserve_environment: bool = False
    create_backup: bool = True


class ApplyWorldDeltaRequest(BaseModel):
    """Request model for applying world state changes."""

    world_state_id: str = Field(..., description="ID of the world state to modify")
    entity_operations: List[EntityOperationRequest] = Field(default_factory=list)
    environment_operation: Optional[EnvironmentOperationRequest] = None
    time_operation: Optional[TimeOperationRequest] = None
    snapshot_operation: Optional[SnapshotOperationRequest] = None
    reset_operation: Optional[ResetOperationRequest] = None
    batch_id: Optional[str] = None
    user_id: Optional[str] = None
    source: str = "world_api"
    correlation_id: Optional[str] = None
    reason: str = Field(..., description="Overall reason for applying this delta")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    priority: str = Field(default="normal", pattern="^(low|normal|high|critical)$")
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    idempotency_key: Optional[str] = None
    expected_world_version: Optional[int] = None


# Query Request Models (Read Operations)


class GetWorldSliceRequest(BaseModel):
    """Request model for world slice queries."""

    # Spatial parameters (either circular or rectangular)
    center_x: Optional[float] = None
    center_y: Optional[float] = None
    radius: Optional[float] = None
    min_x: Optional[float] = None
    max_x: Optional[float] = None
    min_y: Optional[float] = None
    max_y: Optional[float] = None
    min_z: Optional[float] = None
    max_z: Optional[float] = None

    # Filtering and options
    entity_types: Optional[List[str]] = None
    include_environment: bool = True
    include_metadata: bool = False
    include_world_summary: bool = True
    include_spatial_index: bool = False

    # Pagination
    limit: Optional[int] = Field(None, ge=1, le=1000)
    offset: int = Field(0, ge=0)


# Response Models


class WorldDeltaResponse(BaseModel):
    """Response model for world delta operations."""

    command_id: str
    world_state_id: str
    success: bool
    operations_applied: int
    operation_summary: str
    execution_time_ms: float
    world_version: Optional[int] = None
    correlation_id: str
    timestamp: datetime


class EntityResponse(BaseModel):
    """Response model for entity data."""

    id: str
    entity_type: str
    name: str
    coordinates: Dict[str, float]
    properties_summary: Optional[Dict[str, Any]] = None
    distance: Optional[float] = None  # For area queries


class WorldSliceResponse(BaseModel):
    """Response model for world slice queries."""

    world_id: str
    found: bool
    entities: List[EntityResponse] = Field(default_factory=list)
    entity_count: int
    total_entities: Optional[int] = None
    world_summary: Optional[Dict[str, Any]] = None
    environment: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    spatial_bounds: Optional[Dict[str, float]] = None
    query_time_ms: float
    query_metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class WorldSummaryResponse(BaseModel):
    """Response model for world summary queries."""

    world_id: str
    found: bool
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    total_entities: Optional[int] = None
    entity_types: Optional[Dict[str, int]] = None
    spatial_bounds: Optional[Dict[str, float]] = None
    world_time: Optional[datetime] = None
    entity_type_details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class EntitiesInAreaResponse(BaseModel):
    """Response model for entities in area queries."""

    world_id: str
    found: bool
    entities: List[EntityResponse] = Field(default_factory=list)
    entity_count: int
    total_entities: int
    search_area: Dict[str, float]
    error: Optional[str] = None


class EntitiesByTypeResponse(BaseModel):
    """Response model for entities by type queries."""

    world_id: str
    found: bool
    entity_type: str
    entities: List[EntityResponse] = Field(default_factory=list)
    entity_count: int
    total_entities: int
    error: Optional[str] = None


class WorldSearchResult(BaseModel):
    """Individual world search result."""

    world_id: str
    name: str
    description: Optional[str] = None
    status: str
    world_time: Optional[datetime] = None
    total_entities: Optional[int] = None
    entity_types: Optional[Dict[str, int]] = None


class SearchWorldsResponse(BaseModel):
    """Response model for world search queries."""

    search_term: str
    worlds: List[WorldSearchResult] = Field(default_factory=list)
    world_count: int
    total_worlds: int
    status_filter: Optional[str] = None


# ==================== COMMAND ENDPOINTS (Write Operations) ====================


@router.post("/{world_id}/delta", response_model=WorldDeltaResponse)
async def apply_world_delta(
    request: ApplyWorldDeltaRequest,
    world_id: str = Path(..., description="ID of the world to modify"),
) -> WorldDeltaResponse:
    """
    Apply a set of changes (delta) to a world state.

    This endpoint executes write operations on the world state through
    the command side of CQRS. All changes are applied atomically.
    """
    start_time = datetime.now()
    logger.info(f"Applying world delta to world {world_id}")

    try:
        # Validate world_id matches request
        if world_id != request.world_state_id:
            raise HTTPException(
                status_code=400, detail="URL world_id must match request world_state_id"
            )

        # Convert request to domain command
        command = _build_world_delta_command(request)

        # TODO: Execute command through command bus/handler
        # For now, simulate successful execution
        # In full implementation: await command_bus.execute(command)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(f"World delta applied successfully in {execution_time:.1f}ms")

        return WorldDeltaResponse(
            command_id=command.command_id,
            world_state_id=command.world_state_id,
            success=True,
            operations_applied=command.get_operation_count(),
            operation_summary=command.get_operation_summary(),
            execution_time_ms=execution_time,
            world_version=None,  # TODO: Get from aggregate
            correlation_id=command.correlation_id,
            timestamp=command.timestamp,
        )

    except ValueError as e:
        logger.error(f"Validation error in world delta: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error applying world delta: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to apply world delta: {str(e)}"
        )


# ==================== QUERY ENDPOINTS (Read Operations) ====================


@router.get("/{world_id}/slice", response_model=WorldSliceResponse)
async def get_world_slice(
    world_id: str = Path(..., description="ID of the world to query"),
    center_x: Optional[float] = Query(
        None, description="Center X coordinate for circular query"
    ),
    center_y: Optional[float] = Query(
        None, description="Center Y coordinate for circular query"
    ),
    radius: Optional[float] = Query(
        None, ge=0, description="Radius for circular query"
    ),
    min_x: Optional[float] = Query(
        None, description="Minimum X coordinate for rectangular query"
    ),
    max_x: Optional[float] = Query(
        None, description="Maximum X coordinate for rectangular query"
    ),
    min_y: Optional[float] = Query(
        None, description="Minimum Y coordinate for rectangular query"
    ),
    max_y: Optional[float] = Query(
        None, description="Maximum Y coordinate for rectangular query"
    ),
    min_z: Optional[float] = Query(None, description="Minimum Z coordinate"),
    max_z: Optional[float] = Query(None, description="Maximum Z coordinate"),
    entity_types: Optional[List[str]] = Query(
        None, description="Filter by entity types"
    ),
    include_environment: bool = Query(True, description="Include environment data"),
    include_metadata: bool = Query(False, description="Include metadata"),
    include_world_summary: bool = Query(True, description="Include world summary"),
    include_spatial_index: bool = Query(False, description="Include spatial bounds"),
    limit: Optional[int] = Query(
        None, ge=1, le=1000, description="Maximum entities to return"
    ),
    offset: int = Query(0, ge=0, description="Number of entities to skip"),
) -> WorldSliceResponse:
    """
    Retrieve a spatial slice of world data.

    This endpoint provides high-performance access to world entity data
    within specified geographic bounds using the optimized read model.
    """
    logger.info(f"Getting world slice for world {world_id}")

    try:
        # Build query object
        query = GetWorldSlice(
            world_id=world_id,
            center_x=center_x,
            center_y=center_y,
            radius=radius,
            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y,
            min_z=min_z,
            max_z=max_z,
            entity_types=entity_types,
            include_environment=include_environment,
            include_metadata=include_metadata,
            include_world_summary=include_world_summary,
            include_spatial_index=include_spatial_index,
            limit=limit,
            offset=offset,
        )

        # Execute query
        result = await execute_query(query)

        logger.info(
            f"World slice query completed in {result.get('query_time_ms', 0):.1f}ms"
        )

        return WorldSliceResponse(**result)

    except QueryValidationException as e:
        logger.error(f"Query validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except QueryExecutionException as e:
        logger.error(f"Query execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in world slice query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/{world_id}/summary", response_model=WorldSummaryResponse)
async def get_world_summary(
    world_id: str = Path(..., description="ID of the world to summarize"),
    include_entity_details: bool = Query(
        False, description="Include detailed entity type information"
    ),
    include_spatial_bounds: bool = Query(True, description="Include spatial bounds"),
) -> WorldSummaryResponse:
    """
    Retrieve summary statistics for a world.

    This endpoint provides aggregated world information optimized
    for dashboards and quick status checks.
    """
    logger.info(f"Getting world summary for world {world_id}")

    try:
        query = GetWorldSummary(
            world_id=world_id,
            include_entity_details=include_entity_details,
            include_spatial_bounds=include_spatial_bounds,
        )

        result = await execute_query(query)
        logger.info(f"World summary query completed for world {world_id}")

        return WorldSummaryResponse(**result)

    except QueryValidationException as e:
        logger.error(f"Query validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except QueryExecutionException as e:
        logger.error(f"Query execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in world summary query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/{world_id}/entities", response_model=EntitiesInAreaResponse)
async def get_entities_in_area(
    world_id: str = Path(..., description="ID of the world to query"),
    center_x: float = Query(..., description="Center X coordinate"),
    center_y: float = Query(..., description="Center Y coordinate"),
    radius: float = Query(..., ge=0, description="Search radius"),
    entity_types: Optional[List[str]] = Query(
        None, description="Filter by entity types"
    ),
    limit: Optional[int] = Query(
        None, ge=1, le=1000, description="Maximum entities to return"
    ),
    offset: int = Query(0, ge=0, description="Number of entities to skip"),
    include_distance: bool = Query(True, description="Include distance from center"),
) -> EntitiesInAreaResponse:
    """
    Retrieve entities within a specific geographic area.

    This endpoint provides efficient spatial queries for finding entities
    within a circular area around a center point.
    """
    logger.info(
        f"Getting entities in area for world {world_id} at ({center_x}, {center_y}) radius {radius}"
    )

    try:
        query = GetEntitiesInArea(
            world_id=world_id,
            center_x=center_x,
            center_y=center_y,
            radius=radius,
            entity_types=entity_types,
            limit=limit,
            offset=offset,
            include_distance=include_distance,
        )

        result = await execute_query(query)
        logger.info(f"Entities in area query completed for world {world_id}")

        return EntitiesInAreaResponse(**result)

    except QueryValidationException as e:
        logger.error(f"Query validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except QueryExecutionException as e:
        logger.error(f"Query execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in entities in area query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get(
    "/{world_id}/entities/type/{entity_type}", response_model=EntitiesByTypeResponse
)
async def get_entities_by_type(
    world_id: str = Path(..., description="ID of the world to query"),
    entity_type: str = Path(..., description="Type of entities to retrieve"),
    limit: Optional[int] = Query(
        None, ge=1, le=1000, description="Maximum entities to return"
    ),
    offset: int = Query(0, ge=0, description="Number of entities to skip"),
    include_coordinates: bool = Query(True, description="Include entity coordinates"),
) -> EntitiesByTypeResponse:
    """
    Retrieve entities filtered by type.

    This endpoint provides efficient queries for finding all entities
    of a specific type within a world.
    """
    logger.info(f"Getting entities by type '{entity_type}' for world {world_id}")

    try:
        query = GetEntitiesByType(
            world_id=world_id,
            entity_type=entity_type,
            limit=limit,
            offset=offset,
            include_coordinates=include_coordinates,
        )

        result = await execute_query(query)
        logger.info(f"Entities by type query completed for world {world_id}")

        return EntitiesByTypeResponse(**result)

    except QueryValidationException as e:
        logger.error(f"Query validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except QueryExecutionException as e:
        logger.error(f"Query execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in entities by type query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/search", response_model=SearchWorldsResponse)
async def search_worlds(
    search_term: str = Query(
        ..., min_length=1, description="Search term for world names/descriptions"
    ),
    limit: Optional[int] = Query(
        50, ge=1, le=200, description="Maximum worlds to return"
    ),
    offset: int = Query(0, ge=0, description="Number of worlds to skip"),
    include_entity_counts: bool = Query(
        True, description="Include entity count information"
    ),
    status_filter: Optional[str] = Query(None, description="Filter by world status"),
) -> SearchWorldsResponse:
    """
    Search worlds by name, description, or content.

    This endpoint provides full-text search capabilities across
    world metadata for discovery and navigation.
    """
    logger.info(f"Searching worlds with term '{search_term}'")

    try:
        query = SearchWorlds(
            search_term=search_term,
            limit=limit,
            offset=offset,
            include_entity_counts=include_entity_counts,
            status_filter=status_filter,
        )

        result = await execute_query(query)
        logger.info(
            f"World search completed with {result.get('world_count', 0)} results"
        )

        return SearchWorldsResponse(**result)

    except QueryValidationException as e:
        logger.error(f"Query validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except QueryExecutionException as e:
        logger.error(f"Query execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in world search query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


# ==================== HELPER FUNCTIONS ====================


def _build_world_delta_command(request: ApplyWorldDeltaRequest) -> ApplyWorldDelta:
    """
    Convert API request to domain command object.

    This function handles the translation between the API layer
    and the domain layer, ensuring proper validation and conversion.
    """
    try:
        # Convert entity operations
        entity_operations = []
        for op_request in request.entity_operations:
            # Convert coordinates
            coordinates = None
            if op_request.coordinates:
                coordinates = Coordinates(
                    x=op_request.coordinates.x,
                    y=op_request.coordinates.y,
                    z=op_request.coordinates.z or 0.0,
                )

            new_coordinates = None
            if op_request.new_coordinates:
                new_coordinates = Coordinates(
                    x=op_request.new_coordinates.x,
                    y=op_request.new_coordinates.y,
                    z=op_request.new_coordinates.z or 0.0,
                )

            # Convert entity type
            entity_type = None
            if op_request.entity_type:
                entity_type = EntityType(op_request.entity_type)

            # Create entity operation
            entity_op = EntityOperation(
                operation_type=WorldOperationType(op_request.operation_type),
                entity_id=op_request.entity_id,
                entity_type=entity_type,
                entity_name=op_request.entity_name,
                coordinates=coordinates,
                new_coordinates=new_coordinates,
                properties=op_request.properties,
                metadata=op_request.metadata,
                reason=op_request.reason,
            )
            entity_operations.append(entity_op)

        # Convert environment operation
        environment_operation = None
        if request.environment_operation:
            environment_operation = EnvironmentOperation(
                environment_changes=request.environment_operation.environment_changes,
                affected_area=request.environment_operation.affected_area,
                reason=request.environment_operation.reason,
            )

        # Convert time operation
        time_operation = None
        if request.time_operation:
            time_operation = TimeOperation(
                new_time=request.time_operation.new_time,
                reason=request.time_operation.reason,
            )

        # Convert snapshot operation
        snapshot_operation = None
        if request.snapshot_operation:
            snapshot_operation = SnapshotOperation(
                reason=request.snapshot_operation.reason,
                include_entities=request.snapshot_operation.include_entities,
                include_environment=request.snapshot_operation.include_environment,
                metadata=request.snapshot_operation.metadata,
            )

        # Convert reset operation
        reset_operation = None
        if request.reset_operation:
            reset_operation = ResetOperation(
                reason=request.reset_operation.reason,
                preserve_entities=request.reset_operation.preserve_entities,
                preserve_environment=request.reset_operation.preserve_environment,
                create_backup=request.reset_operation.create_backup,
            )

        # Create and return command
        return ApplyWorldDelta(
            world_state_id=request.world_state_id,
            entity_operations=entity_operations,
            environment_operation=environment_operation,
            time_operation=time_operation,
            snapshot_operation=snapshot_operation,
            reset_operation=reset_operation,
            batch_id=request.batch_id,
            user_id=request.user_id,
            source=request.source,
            correlation_id=request.correlation_id,
            reason=request.reason,
            metadata=request.metadata,
            priority=request.priority,
            timeout_seconds=request.timeout_seconds,
            idempotency_key=request.idempotency_key,
            expected_world_version=request.expected_world_version,
        )

    except Exception as e:
        logger.error(f"Error building world delta command: {e}")
        raise ValueError(f"Invalid request data: {e}")
