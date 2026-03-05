"""Foreshadowing endpoints for structure router."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from src.api.schemas import (
    ForeshadowingCreateRequest,
    ForeshadowingListResponse,
    ForeshadowingResponse,
    ForeshadowingUpdateRequest,
    LinkPayoffRequest,
)
from src.contexts.narrative.domain.entities.foreshadowing import (
    Foreshadowing,
    ForeshadowingStatus,
)

from .common import (
    _delete_foreshadowing,
    _foreshadowing_to_response,
    _get_foreshadowing,
    _get_scene,
    _list_foreshadowings,
    _parse_uuid,
    _store_foreshadowing,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/foreshadowings")


@router.post("", response_model=ForeshadowingResponse, status_code=201)
async def create_foreshadowing(
    request: ForeshadowingCreateRequest,
) -> ForeshadowingResponse:
    """Create a new foreshadowing."""
    setup_scene_uuid = _parse_uuid(request.setup_scene_id, "setup_scene_id")

    setup_scene = _get_scene(setup_scene_uuid)
    if setup_scene is None:
        raise HTTPException(
            status_code=404, detail=f"Setup scene not found: {request.setup_scene_id}"
        )

    try:
        valid_statuses = [s.value for s in ForeshadowingStatus]
        if request.status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {request.status}. Must be one of: {valid_statuses}",
            )

        foreshadowing = Foreshadowing(
            setup_scene_id=setup_scene_uuid,
            description=request.description,
            status=ForeshadowingStatus(request.status),
        )

        _store_foreshadowing(foreshadowing)
        logger.info(
            "Created foreshadowing %s for setup scene %s",
            foreshadowing.id,
            setup_scene_uuid,
        )

        return _foreshadowing_to_response(foreshadowing)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to create foreshadowing: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to create foreshadowing: {str(e)}"
        )


@router.get("", response_model=ForeshadowingListResponse)
async def list_foreshadowings() -> ForeshadowingListResponse:
    """List all foreshadowings."""
    foreshadowings = _list_foreshadowings()

    return ForeshadowingListResponse(
        foreshadowings=[_foreshadowing_to_response(f) for f in foreshadowings],
    )


@router.get("/{foreshadowing_id}", response_model=ForeshadowingResponse)
async def get_foreshadowing(
    foreshadowing_id: str,
) -> ForeshadowingResponse:
    """Get a foreshadowing by ID."""
    foreshadowing_uuid = _parse_uuid(foreshadowing_id, "foreshadowing_id")

    foreshadowing = _get_foreshadowing(foreshadowing_uuid)
    if foreshadowing is None:
        raise HTTPException(
            status_code=404, detail=f"Foreshadowing not found: {foreshadowing_id}"
        )

    return _foreshadowing_to_response(foreshadowing)


@router.put("/{foreshadowing_id}", response_model=ForeshadowingResponse)
async def update_foreshadowing(
    foreshadowing_id: str,
    request: ForeshadowingUpdateRequest,
) -> ForeshadowingResponse:
    """Update a foreshadowing."""
    foreshadowing_uuid = _parse_uuid(foreshadowing_id, "foreshadowing_id")

    foreshadowing = _get_foreshadowing(foreshadowing_uuid)
    if foreshadowing is None:
        raise HTTPException(
            status_code=404, detail=f"Foreshadowing not found: {foreshadowing_id}"
        )

    try:
        if request.description:
            foreshadowing.update_description(request.description)

        if request.status:
            valid_statuses = [s.value for s in ForeshadowingStatus]
            if request.status not in valid_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {request.status}. Must be one of: {valid_statuses}",
                )

            if request.status == ForeshadowingStatus.ABANDONED.value:
                foreshadowing.abandon()
            elif request.status == ForeshadowingStatus.PLANTED.value:
                foreshadowing.replant()

        if request.payoff_scene_id:
            payoff_uuid = _parse_uuid(request.payoff_scene_id, "payoff_scene_id")

            payoff_scene = _get_scene(payoff_uuid)
            if payoff_scene is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Payoff scene not found: {request.payoff_scene_id}",
                )

            foreshadowing.link_payoff(payoff_uuid, _get_scene)

        _store_foreshadowing(foreshadowing)
        logger.info("Updated foreshadowing %s", foreshadowing_uuid)

        return _foreshadowing_to_response(foreshadowing)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to update foreshadowing %s: %s", foreshadowing_uuid, e)
        raise HTTPException(
            status_code=500, detail=f"Failed to update foreshadowing: {str(e)}"
        )


@router.post("/{foreshadowing_id}/link-payoff", response_model=ForeshadowingResponse)
async def link_payoff_to_foreshadowing(
    foreshadowing_id: str,
    request: LinkPayoffRequest,
) -> ForeshadowingResponse:
    """Link a payoff scene to a foreshadowing."""
    foreshadowing_uuid = _parse_uuid(foreshadowing_id, "foreshadowing_id")

    foreshadowing = _get_foreshadowing(foreshadowing_uuid)
    if foreshadowing is None:
        raise HTTPException(
            status_code=404, detail=f"Foreshadowing not found: {foreshadowing_id}"
        )

    payoff_uuid = _parse_uuid(request.payoff_scene_id, "payoff_scene_id")

    payoff_scene = _get_scene(payoff_uuid)
    if payoff_scene is None:
        raise HTTPException(
            status_code=404, detail=f"Payoff scene not found: {request.payoff_scene_id}"
        )

    try:
        foreshadowing.link_payoff(payoff_uuid, _get_scene)

        _store_foreshadowing(foreshadowing)
        logger.info(
            "Linked payoff scene %s to foreshadowing %s",
            payoff_uuid,
            foreshadowing_uuid,
        )

        return _foreshadowing_to_response(foreshadowing)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "Failed to link payoff to foreshadowing %s: %s", foreshadowing_uuid, e
        )
        raise HTTPException(status_code=500, detail=f"Failed to link payoff: {str(e)}")


@router.delete("/{foreshadowing_id}", status_code=204)
async def delete_foreshadowing(
    foreshadowing_id: str,
) -> None:
    """Delete a foreshadowing."""
    foreshadowing_uuid = _parse_uuid(foreshadowing_id, "foreshadowing_id")

    deleted = _delete_foreshadowing(foreshadowing_uuid)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"Foreshadowing not found: {foreshadowing_id}"
        )

    logger.info("Deleted foreshadowing %s", foreshadowing_uuid)
