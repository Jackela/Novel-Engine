"""Conflict endpoints for structure router."""

from __future__ import annotations

import structlog

from fastapi import APIRouter, HTTPException

from src.api.schemas import (
    ConflictCreateRequest,
    ConflictListResponse,
    ConflictResponse,
    ConflictUpdateRequest,
)
from src.contexts.narrative.domain.entities.conflict import (
    Conflict,
    ConflictStakes,
    ConflictType,
    ResolutionStatus,
)

from .common import (
    _conflict_to_response,
    _delete_conflict,
    _get_conflict,
    _get_conflicts_by_scene,
    _get_scene,
    _parse_uuid,
    _store_conflict,
)

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post(
    "/scenes/{scene_id}/conflicts", response_model=ConflictResponse, status_code=201
)
async def create_conflict(
    scene_id: str,
    request: ConflictCreateRequest,
) -> ConflictResponse:
    """Create a new conflict in a scene."""
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    scene = _get_scene(scene_uuid)
    if scene is None:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    try:
        valid_types = [t.value for t in ConflictType]
        if request.conflict_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid conflict_type: {request.conflict_type}. Must be one of {valid_types}",
            )

        valid_stakes = [s.value for s in ConflictStakes]
        if request.stakes not in valid_stakes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid stakes: {request.stakes}. Must be one of {valid_stakes}",
            )

        valid_statuses = [s.value for s in ResolutionStatus]
        if request.resolution_status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid resolution_status: {request.resolution_status}. Must be one of {valid_statuses}",
            )

        conflict = Conflict(
            scene_id=scene_uuid,
            conflict_type=ConflictType(request.conflict_type),
            stakes=ConflictStakes(request.stakes),
            description=request.description,
            resolution_status=ResolutionStatus(request.resolution_status),
        )
        _store_conflict(conflict)

        logger.info("Created conflict: %s in scene: %s", conflict.id, scene_uuid)
        return _conflict_to_response(conflict)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/scenes/{scene_id}/conflicts", response_model=ConflictListResponse)
async def list_conflicts(
    scene_id: str,
) -> ConflictListResponse:
    """List all conflicts in a scene."""
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    scene = _get_scene(scene_uuid)
    if scene is None:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    conflicts = _get_conflicts_by_scene(scene_uuid)

    return ConflictListResponse(
        scene_id=scene_id,
        conflicts=[_conflict_to_response(c) for c in conflicts],
    )


@router.get(
    "/scenes/{scene_id}/conflicts/{conflict_id}", response_model=ConflictResponse
)
async def get_conflict(
    scene_id: str,
    conflict_id: str,
) -> ConflictResponse:
    """Get a conflict by ID."""
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    conflict_uuid = _parse_uuid(conflict_id, "conflict_id")

    scene = _get_scene(scene_uuid)
    if scene is None:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    conflict = _get_conflict(conflict_uuid)
    if conflict is None or conflict.scene_id != scene_uuid:
        raise HTTPException(
            status_code=404, detail=f"Conflict not found: {conflict_id}"
        )

    return _conflict_to_response(conflict)


@router.patch(
    "/scenes/{scene_id}/conflicts/{conflict_id}", response_model=ConflictResponse
)
async def update_conflict(
    scene_id: str,
    conflict_id: str,
    request: ConflictUpdateRequest,
) -> ConflictResponse:
    """Update a conflict's properties."""
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    conflict_uuid = _parse_uuid(conflict_id, "conflict_id")

    scene = _get_scene(scene_uuid)
    if scene is None:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    conflict = _get_conflict(conflict_uuid)
    if conflict is None or conflict.scene_id != scene_uuid:
        raise HTTPException(
            status_code=404, detail=f"Conflict not found: {conflict_id}"
        )

    try:
        if request.description is not None:
            conflict.update_description(request.description)

        if request.conflict_type is not None:
            valid_types = [t.value for t in ConflictType]
            if request.conflict_type not in valid_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid conflict_type: {request.conflict_type}. Must be one of {valid_types}",
                )
            conflict.update_conflict_type(ConflictType(request.conflict_type))

        if request.stakes is not None:
            valid_stakes = [s.value for s in ConflictStakes]
            if request.stakes not in valid_stakes:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid stakes: {request.stakes}. Must be one of {valid_stakes}",
                )
            conflict.update_stakes(ConflictStakes(request.stakes))

        if request.resolution_status is not None:
            valid_statuses = [s.value for s in ResolutionStatus]
            if request.resolution_status not in valid_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid resolution_status: {request.resolution_status}. Must be one of {valid_statuses}",
                )
            if request.resolution_status == "escalating":
                conflict.escalate()
            elif request.resolution_status == "resolved":
                conflict.resolve()
            elif request.resolution_status == "unresolved":
                conflict.reopen()

        _store_conflict(conflict)
        logger.info("Updated conflict: %s", conflict_uuid)
        return _conflict_to_response(conflict)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/scenes/{scene_id}/conflicts/{conflict_id}", status_code=204)
async def delete_conflict(
    scene_id: str,
    conflict_id: str,
) -> None:
    """Delete a conflict from a scene."""
    scene_uuid = _parse_uuid(scene_id, "scene_id")
    conflict_uuid = _parse_uuid(conflict_id, "conflict_id")

    scene = _get_scene(scene_uuid)
    if scene is None:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    conflict = _get_conflict(conflict_uuid)
    if conflict is None or conflict.scene_id != scene_uuid:
        raise HTTPException(
            status_code=404, detail=f"Conflict not found: {conflict_id}"
        )

    _delete_conflict(conflict_uuid)
    logger.info("Deleted conflict: %s", conflict_uuid)
