"""
Character Goals API Router

This module provides CRUD endpoints for character goals.
Goals represent what characters want to achieve, driving their
motivation and narrative arcs.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.deps import get_optional_workspace_id, require_workspace_id
from src.api.schemas import (
    CharacterGoalCreateRequest,
    CharacterGoalSchema,
    CharacterGoalsResponse,
    CharacterGoalUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["goals"])


def _sanitize_for_log(value: Optional[str]) -> Optional[str]:
    """Normalize user-controlled values before logging.

    Why: Prevent log forging by stripping CR/LF characters from strings.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    return value.replace("\r", "").replace("\n", "")


def _parse_uuid_safe(value: str) -> UUID | None:
    """Parse a string as UUID, returning None if invalid.

    This provides a safe way to validate and sanitize user input for logging.
    The returned UUID string representation is guaranteed safe for logs.
    """
    try:
        return UUID(value)
    except (ValueError, TypeError):
        return None


def _goal_to_schema(goal_data: dict) -> CharacterGoalSchema:
    """Convert a goal dict to the API schema."""
    status = goal_data.get("status", "ACTIVE")
    urgency = goal_data.get("urgency", "MEDIUM")
    is_active = status == "ACTIVE"
    is_urgent = urgency in ("HIGH", "CRITICAL")

    return CharacterGoalSchema(
        goal_id=goal_data.get("goal_id", str(uuid4())),
        description=goal_data.get("description", ""),
        status=status,
        urgency=urgency,
        created_at=goal_data.get("created_at", datetime.now().isoformat()),
        completed_at=goal_data.get("completed_at"),
        is_active=is_active,
        is_urgent=is_urgent,
    )


@router.get(
    "/characters/{character_id}/goals",
    response_model=CharacterGoalsResponse,
)
async def get_character_goals(
    character_id: str,
    request: Request,
    status: Optional[str] = None,
    workspace_id: Optional[str] = Depends(get_optional_workspace_id),
) -> CharacterGoalsResponse:
    """Get all goals for a character.

    Optionally filter by status (ACTIVE, COMPLETED, FAILED).
    """
    store = getattr(request.app.state, "workspace_character_store", None)

    if not workspace_id or not store:
        return CharacterGoalsResponse(
            character_id=character_id,
            goals=[],
            total_count=0,
            active_count=0,
            completed_count=0,
            failed_count=0,
        )

    try:
        record = store.get(workspace_id, character_id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Character '{character_id}' not found",
        )

    # Get goals from structured_data
    structured_data = record.get("structured_data", {}) or {}
    goals_data: List[dict] = structured_data.get("goals", [])

    # Apply status filter
    if status:
        status_upper = status.upper()
        goals_data = [
            g for g in goals_data
            if g.get("status", "ACTIVE").upper() == status_upper
        ]

    # Convert to schema
    goals = [_goal_to_schema(g) for g in goals_data]

    # Count by status (from original unfiltered data)
    all_goals = structured_data.get("goals", [])
    active_count = sum(1 for g in all_goals if g.get("status", "ACTIVE") == "ACTIVE")
    completed_count = sum(1 for g in all_goals if g.get("status") == "COMPLETED")
    failed_count = sum(1 for g in all_goals if g.get("status") == "FAILED")

    return CharacterGoalsResponse(
        character_id=character_id,
        goals=goals,
        total_count=len(goals),
        active_count=active_count,
        completed_count=completed_count,
        failed_count=failed_count,
    )


@router.post(
    "/characters/{character_id}/goals",
    response_model=CharacterGoalSchema,
    status_code=201,
)
async def create_character_goal(
    character_id: str,
    request: Request,
    payload: CharacterGoalCreateRequest,
    workspace_id: str = Depends(require_workspace_id),
) -> CharacterGoalSchema:
    """Add a new goal to a character."""
    store = getattr(request.app.state, "workspace_character_store", None)

    if not store:
        raise HTTPException(status_code=503, detail="Workspace service unavailable")

    try:
        record = store.get(workspace_id, character_id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Character '{character_id}' not found",
        )

    # Create goal data
    goal_id = str(uuid4())
    created_at = datetime.now().isoformat()
    goal_data = {
        "goal_id": goal_id,
        "description": payload.description,
        "status": "ACTIVE",
        "urgency": payload.urgency.upper(),
        "created_at": created_at,
        "completed_at": None,
    }

    # Get or create structured_data.goals
    structured_data = record.get("structured_data", {}) or {}
    goals_list = structured_data.get("goals", [])
    if not isinstance(goals_list, list):
        goals_list = []

    # Append new goal
    goals_list.append(goal_data)
    structured_data["goals"] = goals_list

    # Update the character record
    try:
        store.update(workspace_id, character_id, {"structured_data": structured_data})
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    # Parse UUID to ensure safe logging
    char_uuid = _parse_uuid_safe(character_id)
    logger.info(
        "Created goal for character",
        extra={
            "character_id": str(char_uuid) if char_uuid else "invalid",
            "goal_id": goal_id,
            "urgency": goal_data["urgency"],
        },
    )

    return _goal_to_schema(goal_data)


@router.get(
    "/characters/{character_id}/goals/{goal_id}",
    response_model=CharacterGoalSchema,
)
async def get_character_goal(
    character_id: str,
    goal_id: str,
    request: Request,
    workspace_id: Optional[str] = Depends(get_optional_workspace_id),
) -> CharacterGoalSchema:
    """Get a specific goal by ID."""
    store = getattr(request.app.state, "workspace_character_store", None)

    if not workspace_id or not store:
        raise HTTPException(
            status_code=404,
            detail=f"Goal '{goal_id}' not found",
        )

    try:
        record = store.get(workspace_id, character_id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Character '{character_id}' not found",
        )

    # Find goal in structured_data
    structured_data = record.get("structured_data", {}) or {}
    goals_data: List[dict] = structured_data.get("goals", [])

    goal = next(
        (g for g in goals_data if g.get("goal_id") == goal_id),
        None,
    )

    if not goal:
        raise HTTPException(
            status_code=404,
            detail=f"Goal '{goal_id}' not found",
        )

    return _goal_to_schema(goal)


@router.patch(
    "/characters/{character_id}/goals/{goal_id}",
    response_model=CharacterGoalSchema,
)
async def update_character_goal(
    character_id: str,
    goal_id: str,
    request: Request,
    payload: CharacterGoalUpdateRequest,
    workspace_id: str = Depends(require_workspace_id),
) -> CharacterGoalSchema:
    """Update a goal's status or urgency.

    Use this to mark goals as COMPLETED or FAILED, or to change urgency.
    """
    store = getattr(request.app.state, "workspace_character_store", None)

    if not store:
        raise HTTPException(status_code=503, detail="Workspace service unavailable")

    try:
        record = store.get(workspace_id, character_id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Character '{character_id}' not found",
        )

    # Find and update goal
    structured_data = record.get("structured_data", {}) or {}
    goals_data: List[dict] = structured_data.get("goals", [])

    goal_index = next(
        (i for i, g in enumerate(goals_data) if g.get("goal_id") == goal_id),
        None,
    )

    if goal_index is None:
        raise HTTPException(
            status_code=404,
            detail=f"Goal '{goal_id}' not found",
        )

    goal = goals_data[goal_index]

    # Validate status transition
    current_status = goal.get("status", "ACTIVE")
    if payload.status and current_status != "ACTIVE":
        # Cannot change status of already resolved goals
        raise HTTPException(
            status_code=400,
            detail=f"Cannot change status of a {current_status} goal",
        )

    # Apply updates
    if payload.status:
        goal["status"] = payload.status.upper()
        if payload.status.upper() in ("COMPLETED", "FAILED"):
            goal["completed_at"] = datetime.now().isoformat()

    if payload.urgency:
        if current_status != "ACTIVE" and not payload.status:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot change urgency of a {current_status} goal",
            )
        goal["urgency"] = payload.urgency.upper()

    goals_data[goal_index] = goal
    structured_data["goals"] = goals_data

    # Update the character record
    try:
        store.update(workspace_id, character_id, {"structured_data": structured_data})
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    # Parse UUIDs to ensure safe logging
    char_uuid = _parse_uuid_safe(character_id)
    goal_uuid = _parse_uuid_safe(goal_id)
    logger.info(
        "Updated goal for character",
        extra={
            "goal_id": _sanitize_for_log(str(goal_uuid) if goal_uuid else "invalid"),
            "character_id": _sanitize_for_log(
                str(char_uuid) if char_uuid else "invalid"
            ),
            "status": _sanitize_for_log(goal.get("status")),
            "urgency": _sanitize_for_log(goal.get("urgency")),
        },
    )

    return _goal_to_schema(goal)


@router.delete(
    "/characters/{character_id}/goals/{goal_id}",
    status_code=204,
)
async def delete_character_goal(
    character_id: str,
    goal_id: str,
    request: Request,
    workspace_id: str = Depends(require_workspace_id),
) -> None:
    """Delete a goal.

    Note: In most cases, goals should be marked as COMPLETED or FAILED
    rather than deleted. This endpoint exists for data correction.
    """
    store = getattr(request.app.state, "workspace_character_store", None)

    if not store:
        raise HTTPException(status_code=503, detail="Workspace service unavailable")

    try:
        record = store.get(workspace_id, character_id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Character '{character_id}' not found",
        )

    # Find and remove goal
    structured_data = record.get("structured_data", {}) or {}
    goals_data: List[dict] = structured_data.get("goals", [])

    original_count = len(goals_data)
    goals_data = [g for g in goals_data if g.get("goal_id") != goal_id]

    if len(goals_data) == original_count:
        raise HTTPException(
            status_code=404,
            detail=f"Goal '{goal_id}' not found",
        )

    structured_data["goals"] = goals_data

    # Update the character record
    try:
        store.update(workspace_id, character_id, {"structured_data": structured_data})
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    # Parse UUIDs to ensure safe logging
    char_uuid = _parse_uuid_safe(character_id)
    goal_uuid = _parse_uuid_safe(goal_id)
    logger.info(
        "Deleted goal from character",
        extra={
            "goal_id": str(goal_uuid) if goal_uuid else "invalid",
            "character_id": str(char_uuid) if char_uuid else "invalid",
        },
    )
