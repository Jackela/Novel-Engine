"""
Factions API Router (CHAR-035)

This module provides API endpoints for faction membership management.
Characters can join factions, leave factions, and factions can designate leaders.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.deps import get_optional_workspace_id, require_workspace_id
from src.api.schemas import (
    FactionDetailResponse,
    FactionJoinRequest,
    FactionJoinResponse,
    FactionLeaveRequest,
    FactionLeaveResponse,
    FactionMemberSchema,
    FactionSetLeaderRequest,
    FactionSetLeaderResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["factions"])


def _get_faction_store(request: Request) -> Dict[str, Dict[str, Any]]:
    """Get the world store which contains factions."""
    store = getattr(request.app.state, "world_store", None)
    if store is None:
        store = {}
        request.app.state.world_store = store
    return store


def _get_faction_by_id(request: Request, faction_id: str) -> Optional[Dict[str, Any]]:
    """Look up a faction by ID from the world store."""
    world_store = _get_faction_store(request)

    # Search through all worlds for the faction
    for world in world_store.values():
        factions = world.get("factions", [])
        for faction in factions:
            if isinstance(faction, dict) and faction.get("id") == faction_id:
                return faction

    return None


def _update_faction_in_store(request: Request, faction_id: str, faction_data: Dict[str, Any]) -> bool:
    """Update a faction in the world store."""
    world_store = _get_faction_store(request)

    for world in world_store.values():
        factions = world.get("factions", [])
        for i, faction in enumerate(factions):
            if isinstance(faction, dict) and faction.get("id") == faction_id:
                factions[i] = faction_data
                return True

    return False


def _get_character_name(
    request: Request, workspace_id: str, character_id: str
) -> str:
    """Get character display name from workspace store."""
    store = getattr(request.app.state, "workspace_character_store", None)
    if not store:
        return character_id

    try:
        record = store.get(workspace_id, character_id)
        if record:
            return record.get("name") or record.get("character_name") or character_id
    except (ValueError, FileNotFoundError):
        # Character not found - return the ID as the name
        pass

    return character_id


def _get_characters_in_faction(
    request: Request, workspace_id: str, faction_id: str
) -> List[Dict[str, Any]]:
    """Get all characters that belong to a faction."""
    store = getattr(request.app.state, "workspace_character_store", None)
    if not store or not workspace_id:
        return []

    members = []
    try:
        char_ids = store.list_ids(workspace_id)
        for char_id in char_ids:
            record = store.get(workspace_id, char_id)
            if record:
                structured_data = record.get("structured_data", {}) or {}
                char_faction_id = structured_data.get("faction_id")
                if char_faction_id == faction_id:
                    members.append({
                        "character_id": char_id,
                        "name": record.get("name") or record.get("character_name") or char_id,
                    })
    except (ValueError, FileNotFoundError):
        # Workspace or character lookup failed - return empty or partial list
        pass

    return members


@router.get(
    "/factions/{faction_id}",
    response_model=FactionDetailResponse,
)
async def get_faction_detail(
    faction_id: str,
    request: Request,
    workspace_id: Optional[str] = Depends(get_optional_workspace_id),
) -> FactionDetailResponse:
    """Get faction details including member list.

    Returns faction metadata and all characters that belong to this faction.
    """
    faction = _get_faction_by_id(request, faction_id)

    if not faction:
        raise HTTPException(
            status_code=404,
            detail=f"Faction '{faction_id}' not found",
        )

    # Get members from character store
    members_data = []
    leader_id = faction.get("leader_id")

    if workspace_id:
        members_data = _get_characters_in_faction(request, workspace_id, faction_id)

    # Convert to schema with leader flag
    members = [
        FactionMemberSchema(
            character_id=m["character_id"],
            name=m["name"],
            is_leader=(m["character_id"] == leader_id) if leader_id else False,
        )
        for m in members_data
    ]

    return FactionDetailResponse(
        id=faction_id,
        name=faction.get("name", ""),
        description=faction.get("description", ""),
        faction_type=faction.get("faction_type", "GUILD"),
        alignment=faction.get("alignment", "true_neutral"),
        status=faction.get("status", "active"),
        leader_id=leader_id,
        leader_name=faction.get("leader_name"),
        influence=faction.get("influence", 50),
        member_count=len(members),
        members=members,
    )


@router.post(
    "/factions/{faction_id}/join",
    response_model=FactionJoinResponse,
)
async def join_faction(
    faction_id: str,
    request: Request,
    payload: FactionJoinRequest,
    workspace_id: str = Depends(require_workspace_id),
) -> FactionJoinResponse:
    """Add a character to a faction.

    A character can only be in one faction at a time. If already in a faction,
    use the leave endpoint first, or the character will automatically leave
    their current faction when joining a new one.
    """
    store = getattr(request.app.state, "workspace_character_store", None)

    if not store:
        raise HTTPException(status_code=503, detail="Workspace service unavailable")

    # Validate faction exists
    faction = _get_faction_by_id(request, faction_id)
    if not faction:
        raise HTTPException(
            status_code=404,
            detail=f"Faction '{faction_id}' not found",
        )

    # Get character
    try:
        record = store.get(workspace_id, payload.character_id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Character '{payload.character_id}' not found",
        )

    # Update character's faction_id in structured_data
    structured_data = record.get("structured_data", {}) or {}
    current_faction = structured_data.get("faction_id")

    if current_faction == faction_id:
        raise HTTPException(
            status_code=400,
            detail=f"Character is already a member of faction '{faction_id}'",
        )

    structured_data["faction_id"] = faction_id

    try:
        store.update(workspace_id, payload.character_id, {"structured_data": structured_data})
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    faction_name = faction.get("name", faction_id)

    logger.info(
        "Character joined faction",
        extra={
            "character_id": payload.character_id[:64] if payload.character_id else "unknown",
            "faction_id": faction_id[:64] if faction_id else "unknown",
            "faction_name": faction_name[:64] if faction_name else "unknown",
        },
    )

    return FactionJoinResponse(
        faction_id=faction_id,
        character_id=payload.character_id,
        faction_name=faction_name,
        message=f"Successfully joined faction '{faction_name}'",
    )


@router.post(
    "/factions/{faction_id}/leave",
    response_model=FactionLeaveResponse,
)
async def leave_faction(
    faction_id: str,
    request: Request,
    payload: FactionLeaveRequest,
    workspace_id: str = Depends(require_workspace_id),
) -> FactionLeaveResponse:
    """Remove a character from a faction.

    If the character is the faction leader, they will be removed from
    leadership as well.
    """
    store = getattr(request.app.state, "workspace_character_store", None)

    if not store:
        raise HTTPException(status_code=503, detail="Workspace service unavailable")

    # Get character
    try:
        record = store.get(workspace_id, payload.character_id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Character '{payload.character_id}' not found",
        )

    # Check character is in this faction
    structured_data = record.get("structured_data", {}) or {}
    current_faction = structured_data.get("faction_id")

    if current_faction != faction_id:
        raise HTTPException(
            status_code=400,
            detail=f"Character is not a member of faction '{faction_id}'",
        )

    # Remove faction membership
    structured_data["faction_id"] = None

    try:
        store.update(workspace_id, payload.character_id, {"structured_data": structured_data})
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    # If character was the leader, remove them
    faction = _get_faction_by_id(request, faction_id)
    if faction and faction.get("leader_id") == payload.character_id:
        faction["leader_id"] = None
        faction["leader_name"] = None
        _update_faction_in_store(request, faction_id, faction)
        logger.info(
            "Removed leader from faction",
            extra={
                "character_id": payload.character_id[:64] if payload.character_id else "unknown",
                "faction_id": faction_id[:64] if faction_id else "unknown",
            },
        )

    logger.info(
        "Character left faction",
        extra={
            "character_id": payload.character_id[:64] if payload.character_id else "unknown",
            "faction_id": faction_id[:64] if faction_id else "unknown",
        },
    )

    return FactionLeaveResponse(
        faction_id=faction_id,
        character_id=payload.character_id,
        message="Successfully left faction",
    )


@router.post(
    "/factions/{faction_id}/leader",
    response_model=FactionSetLeaderResponse,
)
async def set_faction_leader(
    faction_id: str,
    request: Request,
    payload: FactionSetLeaderRequest,
    workspace_id: str = Depends(require_workspace_id),
) -> FactionSetLeaderResponse:
    """Set a character as the faction leader.

    The character must already be a member of the faction.
    Setting a new leader will replace any existing leader.
    """
    store = getattr(request.app.state, "workspace_character_store", None)

    if not store:
        raise HTTPException(status_code=503, detail="Workspace service unavailable")

    # Validate faction exists
    faction = _get_faction_by_id(request, faction_id)
    if not faction:
        raise HTTPException(
            status_code=404,
            detail=f"Faction '{faction_id}' not found",
        )

    # Get character
    try:
        record = store.get(workspace_id, payload.character_id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Character '{payload.character_id}' not found",
        )

    # Check character is in this faction
    structured_data = record.get("structured_data", {}) or {}
    current_faction = structured_data.get("faction_id")

    if current_faction != faction_id:
        raise HTTPException(
            status_code=400,
            detail=f"Character must be a member of faction '{faction_id}' to become leader",
        )

    # Get leader name from character or payload
    leader_name = payload.leader_name
    if not leader_name:
        leader_name = record.get("name") or record.get("character_name")

    # Update faction leader
    faction["leader_id"] = payload.character_id
    faction["leader_name"] = leader_name

    if not _update_faction_in_store(request, faction_id, faction):
        raise HTTPException(
            status_code=500,
            detail="Failed to update faction leader",
        )

    logger.info(
        "Set leader of faction",
        extra={
            "faction_id": faction_id[:64] if faction_id else "unknown",
            "character_id": payload.character_id[:64] if payload.character_id else "unknown",
            "leader_name": (leader_name[:64] if leader_name else None),
        },
    )

    return FactionSetLeaderResponse(
        faction_id=faction_id,
        leader_id=payload.character_id,
        leader_name=leader_name,
        message=f"Successfully set {leader_name or payload.character_id} as faction leader",
    )
