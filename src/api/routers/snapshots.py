"""Snapshots API router for world snapshot operations.

This module provides API endpoints for managing world state snapshots,
including creating, listing, restoring, and deleting snapshots.

Endpoints:
    POST /world/{world_id}/snapshots - Create a new snapshot
    GET /world/{world_id}/snapshots - List snapshots
    GET /world/{world_id}/snapshots/{snapshot_id} - Get snapshot details
    POST /world/{world_id}/snapshots/{snapshot_id}/restore - Restore snapshot
    DELETE /world/{world_id}/snapshots/{snapshot_id} - Delete snapshot
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.contexts.world.application.services.snapshot_service import (
    SnapshotService,
)
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar

router = APIRouter(tags=["snapshots"])

# === Singleton Service Instance ===
# In production, this would be injected via dependency injection
_snapshot_service = SnapshotService()


def get_snapshot_service() -> SnapshotService:
    """Get the snapshot service instance."""
    return _snapshot_service


def reset_snapshot_service() -> None:
    """Reset the snapshot service (for testing)."""
    global _snapshot_service
    _snapshot_service = SnapshotService()


# === Calendar Storage (MVP - shared with simulation router) ===
_world_calendars: dict[str, WorldCalendar] = {}


def _get_or_create_calendar(world_id: str) -> WorldCalendar:
    """Get existing calendar for world or create a default one."""
    if world_id not in _world_calendars:
        _world_calendars[world_id] = WorldCalendar(
            year=1, month=1, day=1, era_name="First Age"
        )
    return _world_calendars[world_id]


# === Request/Response Models ===


class CalendarData(BaseModel):
    """Calendar data in snapshot response."""

    year: int
    month: int
    day: int
    era_name: str
    formatted: str


class CreateSnapshotRequest(BaseModel):
    """Request model for creating a snapshot."""

    description: Optional[str] = Field(
        None, max_length=200, description="Optional description for the snapshot"
    )
    tick_number: int = Field(
        default=0, ge=0, description="Sequential tick number for the snapshot"
    )
    state_json: str = Field(
        default="{}", description="JSON-serialized world state data"
    )


class SnapshotResponse(BaseModel):
    """Response model for a snapshot."""

    snapshot_id: str
    world_id: str
    calendar: Optional[CalendarData]
    tick_number: int
    description: str
    created_at: str
    size_bytes: int


class SnapshotSummary(BaseModel):
    """Summary model for snapshot list."""

    snapshot_id: str
    tick_number: int
    description: str
    created_at: str


class SnapshotListResponse(BaseModel):
    """Response model for list of snapshots."""

    snapshots: List[SnapshotSummary]
    total: int


class RestoreSnapshotResponse(BaseModel):
    """Response model for snapshot restoration."""

    snapshot_id: str
    world_id: str
    restored: bool
    message: str


# === Helper Functions ===


def _calendar_to_data(calendar: Optional[WorldCalendar]) -> Optional[CalendarData]:
    """Convert WorldCalendar to response model."""
    if calendar is None:
        return None
    return CalendarData(
        year=calendar.year,
        month=calendar.month,
        day=calendar.day,
        era_name=calendar.era_name,
        formatted=calendar.format(),
    )


def _snapshot_to_response(snapshot) -> SnapshotResponse:
    """Convert WorldSnapshot to response model."""
    return SnapshotResponse(
        snapshot_id=snapshot.snapshot_id,
        world_id=snapshot.world_id,
        calendar=_calendar_to_data(snapshot.calendar),
        tick_number=snapshot.tick_number,
        description=snapshot.description,
        created_at=snapshot.created_at.isoformat(),
        size_bytes=snapshot.size_bytes,
    )


def _snapshot_to_summary(snapshot) -> SnapshotSummary:
    """Convert WorldSnapshot to summary model."""
    return SnapshotSummary(
        snapshot_id=snapshot.snapshot_id,
        tick_number=snapshot.tick_number,
        description=snapshot.description,
        created_at=snapshot.created_at.isoformat(),
    )


# === Endpoints ===


@router.post(
    "/world/{world_id}/snapshots",
    response_model=SnapshotResponse,
    summary="Create snapshot",
    description="Create a new snapshot of the world state.",
)
async def create_snapshot(
    world_id: str,
    request: CreateSnapshotRequest,
) -> SnapshotResponse:
    """Create a new snapshot for a world.

    Args:
        world_id: Unique identifier for the world
        request: CreateSnapshotRequest with optional description and tick_number

    Returns:
        SnapshotResponse with created snapshot details

    Raises:
        400: Invalid request (e.g., invalid state_json)
    """
    service = get_snapshot_service()
    calendar = _get_or_create_calendar(world_id)

    try:
        snapshot = service.create_snapshot(
            world_id=world_id,
            calendar=calendar,
            state_json=request.state_json,
            tick_number=request.tick_number,
            description=request.description or "",
        )
        return _snapshot_to_response(snapshot)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_REQUEST",
                "message": str(e),
            },
        )


@router.get(
    "/world/{world_id}/snapshots",
    response_model=SnapshotListResponse,
    summary="List snapshots",
    description="Get a list of snapshots for a world.",
)
async def list_snapshots(
    world_id: str,
    limit: int = 10,
) -> SnapshotListResponse:
    """List snapshots for a world.

    Args:
        world_id: Unique identifier for the world
        limit: Maximum number of snapshots to return (default 10)

    Returns:
        SnapshotListResponse with list of snapshot summaries
    """
    service = get_snapshot_service()
    snapshots = service.list_snapshots(world_id, limit)

    return SnapshotListResponse(
        snapshots=[_snapshot_to_summary(s) for s in snapshots],
        total=len(snapshots),
    )


@router.get(
    "/world/{world_id}/snapshots/{snapshot_id}",
    response_model=SnapshotResponse,
    summary="Get snapshot details",
    description="Get detailed information about a specific snapshot.",
)
async def get_snapshot(
    world_id: str,
    snapshot_id: str,
) -> SnapshotResponse:
    """Get details for a specific snapshot.

    Args:
        world_id: Unique identifier for the world
        snapshot_id: Unique identifier for the snapshot

    Returns:
        SnapshotResponse with full snapshot details

    Raises:
        404: Snapshot not found
    """
    service = get_snapshot_service()

    # Get latest to check if service has any snapshots for this world
    latest = service.get_latest_snapshot(world_id)
    if latest is None:
        # Check if snapshot exists in any world (cross-world access)
        result = service.restore_snapshot(snapshot_id)
        if result.is_error:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "SNAPSHOT_NOT_FOUND",
                    "message": f"Snapshot '{snapshot_id}' not found",
                },
            )
        snapshot = result.value
    else:
        # Find the specific snapshot
        snapshots = service.list_snapshots(world_id, limit=100)
        snapshot = next((s for s in snapshots if s.snapshot_id == snapshot_id), None)

        if snapshot is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "SNAPSHOT_NOT_FOUND",
                    "message": f"Snapshot '{snapshot_id}' not found in world '{world_id}'",
                },
            )

    return _snapshot_to_response(snapshot)


@router.post(
    "/world/{world_id}/snapshots/{snapshot_id}/restore",
    response_model=RestoreSnapshotResponse,
    summary="Restore snapshot",
    description="Restore world state from a snapshot.",
)
async def restore_snapshot(
    world_id: str,
    snapshot_id: str,
) -> RestoreSnapshotResponse:
    """Restore world state from a snapshot.

    Args:
        world_id: Unique identifier for the world
        snapshot_id: Unique identifier for the snapshot to restore

    Returns:
        RestoreSnapshotResponse confirming the restore

    Raises:
        404: Snapshot not found
        500: Restore failed
    """
    service = get_snapshot_service()
    result = service.restore_snapshot(snapshot_id)

    if result.is_error:
        error = result.error
        if error.value == "not_found":
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "SNAPSHOT_NOT_FOUND",
                    "message": f"Snapshot '{snapshot_id}' not found",
                },
            )
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "RESTORE_FAILED",
                    "message": f"Failed to restore snapshot: {error.value}",
                },
            )

    snapshot = result.value
    return RestoreSnapshotResponse(
        snapshot_id=snapshot.snapshot_id,
        world_id=snapshot.world_id,
        restored=True,
        message=f"Snapshot {snapshot.snapshot_id} restored successfully",
    )


@router.delete(
    "/world/{world_id}/snapshots/{snapshot_id}",
    summary="Delete snapshot",
    description="Delete a snapshot.",
)
async def delete_snapshot(
    world_id: str,
    snapshot_id: str,
) -> dict:
    """Delete a snapshot.

    Args:
        world_id: Unique identifier for the world
        snapshot_id: Unique identifier for the snapshot to delete

    Returns:
        Dict with deleted status

    Raises:
        404: Snapshot not found
    """
    service = get_snapshot_service()
    deleted = service.delete_snapshot(snapshot_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "SNAPSHOT_NOT_FOUND",
                "message": f"Snapshot '{snapshot_id}' not found",
            },
        )

    return {"deleted": True, "snapshot_id": snapshot_id}
