"""Plotline endpoints for structure router."""

from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException

from src.api.schemas import (
    PlotlineCreateRequest,
    PlotlineListResponse,
    PlotlineResponse,
    PlotlineUpdateRequest,
)
from src.contexts.narrative.domain.entities.plotline import Plotline, PlotlineStatus

from .common import (
    _count_scenes_for_plotline,
    _delete_plotline,
    _get_plotline,
    _list_plotlines,
    _list_scenes,
    _parse_uuid,
    _plotline_to_response,
    _store_plotline,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/plotlines")


@router.post("", response_model=PlotlineResponse, status_code=201)
async def create_plotline(
    request: PlotlineCreateRequest,
) -> PlotlineResponse:
    """Create a new plotline."""
    try:
        valid_statuses = [s.value for s in PlotlineStatus]
        if request.status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {request.status}. Must be one of {valid_statuses}",
            )

        plotline = Plotline(
            name=request.name,
            color=request.color,
            description=request.description,
            status=PlotlineStatus(request.status),
        )

        _store_plotline(plotline)
        logger.info("Created plotline: %s (%s)", plotline.id, plotline.name)

        return _plotline_to_response(plotline, scene_count=0)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to create plotline: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to create plotline: {str(e)}"
        )


@router.get("", response_model=PlotlineListResponse)
async def list_plotlines() -> PlotlineListResponse:
    """List all plotlines with scene counts."""
    plotlines = _list_plotlines()
    scenes = _list_scenes()

    scene_counts: dict[UUID, int] = {}
    for scene in scenes:
        for plotline_id in scene.plotline_ids:
            scene_counts[plotline_id] = scene_counts.get(plotline_id, 0) + 1

    return PlotlineListResponse(
        plotlines=[
            _plotline_to_response(p, scene_count=scene_counts.get(p.id, 0))
            for p in plotlines
        ],
    )


@router.get("/{plotline_id}", response_model=PlotlineResponse)
async def get_plotline(
    plotline_id: str,
) -> PlotlineResponse:
    """Get a plotline by ID."""
    plotline_uuid = _parse_uuid(plotline_id, "plotline_id")

    plotline = _get_plotline(plotline_uuid)
    if plotline is None:
        raise HTTPException(
            status_code=404, detail=f"Plotline not found: {plotline_id}"
        )

    scene_count = _count_scenes_for_plotline(plotline_uuid)
    return _plotline_to_response(plotline, scene_count=scene_count)


@router.patch("/{plotline_id}", response_model=PlotlineResponse)
async def update_plotline(
    plotline_id: str,
    request: PlotlineUpdateRequest,
) -> PlotlineResponse:
    """Update a plotline's properties."""
    plotline_uuid = _parse_uuid(plotline_id, "plotline_id")

    plotline = _get_plotline(plotline_uuid)
    if plotline is None:
        raise HTTPException(
            status_code=404, detail=f"Plotline not found: {plotline_id}"
        )

    try:
        if request.name is not None:
            plotline.update_name(request.name)

        if request.color is not None:
            plotline.update_color(request.color)

        if request.description is not None:
            plotline.update_description(request.description)

        if request.status is not None:
            valid_statuses = [s.value for s in PlotlineStatus]
            if request.status not in valid_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {request.status}. Must be one of {valid_statuses}",
                )

            if request.status == "resolved":
                plotline.resolve()
            elif request.status == "abandoned":
                plotline.abandon()
            elif request.status == "active":
                plotline.reactivate()

        _store_plotline(plotline)
        logger.info("Updated plotline: %s", plotline_uuid)

        scene_count = _count_scenes_for_plotline(plotline_uuid)
        return _plotline_to_response(plotline, scene_count=scene_count)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update plotline: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to update plotline: {str(e)}"
        )


@router.delete("/{plotline_id}", status_code=204)
async def delete_plotline(
    plotline_id: str,
) -> None:
    """Delete a plotline."""
    plotline_uuid = _parse_uuid(plotline_id, "plotline_id")

    if not _delete_plotline(plotline_uuid):
        raise HTTPException(
            status_code=404, detail=f"Plotline not found: {plotline_id}"
        )

    logger.info("Deleted plotline: %s", plotline_uuid)
