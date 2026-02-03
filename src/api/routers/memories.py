"""
Character Memories API Router

This module provides CRUD endpoints for character memories.
Memories are immutable event logs that accumulate over time,
representing experiences that shape character behavior and dialogue.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.deps import get_optional_workspace_id, require_workspace_id
from src.api.schemas import (
    CharacterMemoriesResponse,
    CharacterMemoryCreateRequest,
    CharacterMemorySchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["memories"])


def _parse_uuid_safe(value: str) -> UUID | None:
    """Parse a string as UUID, returning None if invalid.

    This provides a safe way to validate and sanitize user input for logging.
    The returned UUID string representation is guaranteed safe for logs.
    """
    try:
        return UUID(value)
    except (ValueError, TypeError):
        return None


def _memory_to_schema(memory_data: dict) -> CharacterMemorySchema:
    """Convert a memory dict to the API schema."""
    importance = memory_data.get("importance", 5)
    return CharacterMemorySchema(
        memory_id=memory_data.get("memory_id", str(uuid4())),
        content=memory_data.get("content", ""),
        importance=importance,
        tags=memory_data.get("tags", []),
        timestamp=memory_data.get("timestamp", datetime.now().isoformat()),
        is_core_memory=importance > 8,
        importance_level=_get_importance_level(importance),
    )


def _get_importance_level(importance: int) -> str:
    """Get qualitative importance level from numeric score."""
    if importance <= 3:
        return "minor"
    elif importance <= 6:
        return "moderate"
    elif importance <= 8:
        return "significant"
    else:
        return "core"


@router.get(
    "/characters/{character_id}/memories",
    response_model=CharacterMemoriesResponse,
)
async def get_character_memories(
    character_id: str,
    request: Request,
    tag: Optional[str] = None,
    min_importance: Optional[int] = None,
    workspace_id: Optional[str] = Depends(get_optional_workspace_id),
) -> CharacterMemoriesResponse:
    """Get all memories for a character.

    Optionally filter by tag or minimum importance level.
    """
    store = getattr(request.app.state, "workspace_character_store", None)

    if not workspace_id or not store:
        # For filesystem characters, memories would need to be stored separately
        # For now, return empty list
        return CharacterMemoriesResponse(
            character_id=character_id,
            memories=[],
            total_count=0,
            core_memory_count=0,
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

    # Get memories from structured_data
    structured_data = record.get("structured_data", {}) or {}
    memories_data: List[dict] = structured_data.get("memories", [])

    # Apply filters
    if tag:
        memories_data = [
            m for m in memories_data
            if tag.lower() in [t.lower() for t in m.get("tags", [])]
        ]

    if min_importance is not None:
        memories_data = [
            m for m in memories_data
            if m.get("importance", 0) >= min_importance
        ]

    # Convert to schema
    memories = [_memory_to_schema(m) for m in memories_data]

    # Count core memories (importance > 8)
    core_count = sum(1 for m in memories_data if m.get("importance", 0) > 8)

    return CharacterMemoriesResponse(
        character_id=character_id,
        memories=memories,
        total_count=len(memories),
        core_memory_count=core_count,
    )


@router.post(
    "/characters/{character_id}/memories",
    response_model=CharacterMemorySchema,
    status_code=201,
)
async def create_character_memory(
    character_id: str,
    request: Request,
    payload: CharacterMemoryCreateRequest,
    workspace_id: str = Depends(require_workspace_id),
) -> CharacterMemorySchema:
    """Add a new memory to a character.

    Memories are immutable once created - they represent historical events.
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

    # Create memory data
    memory_id = str(uuid4())
    timestamp = datetime.now().isoformat()
    memory_data = {
        "memory_id": memory_id,
        "content": payload.content,
        "importance": payload.importance,
        "tags": payload.tags,
        "timestamp": timestamp,
    }

    # Get or create structured_data.memories
    structured_data = record.get("structured_data", {}) or {}
    memories_list = structured_data.get("memories", [])
    if not isinstance(memories_list, list):
        memories_list = []

    # Append new memory
    memories_list.append(memory_data)
    structured_data["memories"] = memories_list

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
        "Created memory for character",
        extra={
            "character_id": str(char_uuid) if char_uuid else "invalid",
            "memory_id": memory_id,
            "importance": int(payload.importance),
        },
    )

    return _memory_to_schema(memory_data)


@router.get(
    "/characters/{character_id}/memories/{memory_id}",
    response_model=CharacterMemorySchema,
)
async def get_character_memory(
    character_id: str,
    memory_id: str,
    request: Request,
    workspace_id: Optional[str] = Depends(get_optional_workspace_id),
) -> CharacterMemorySchema:
    """Get a specific memory by ID."""
    store = getattr(request.app.state, "workspace_character_store", None)

    if not workspace_id or not store:
        raise HTTPException(
            status_code=404,
            detail=f"Memory '{memory_id}' not found",
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

    # Find memory in structured_data
    structured_data = record.get("structured_data", {}) or {}
    memories_data: List[dict] = structured_data.get("memories", [])

    memory = next(
        (m for m in memories_data if m.get("memory_id") == memory_id),
        None,
    )

    if not memory:
        raise HTTPException(
            status_code=404,
            detail=f"Memory '{memory_id}' not found",
        )

    return _memory_to_schema(memory)


@router.delete(
    "/characters/{character_id}/memories/{memory_id}",
    status_code=204,
)
async def delete_character_memory(
    character_id: str,
    memory_id: str,
    request: Request,
    workspace_id: str = Depends(require_workspace_id),
) -> None:
    """Delete a memory.

    Note: In most cases, memories should not be deleted as they represent
    historical events. This endpoint exists for data correction purposes.
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

    # Find and remove memory
    structured_data = record.get("structured_data", {}) or {}
    memories_data: List[dict] = structured_data.get("memories", [])

    original_count = len(memories_data)
    memories_data = [m for m in memories_data if m.get("memory_id") != memory_id]

    if len(memories_data) == original_count:
        raise HTTPException(
            status_code=404,
            detail=f"Memory '{memory_id}' not found",
        )

    structured_data["memories"] = memories_data

    # Update the character record
    try:
        store.update(workspace_id, character_id, {"structured_data": structured_data})
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    # Parse UUIDs to ensure safe logging
    char_uuid = _parse_uuid_safe(character_id)
    mem_uuid = _parse_uuid_safe(memory_id)
    logger.info(
        "Deleted memory from character",
        extra={
            "memory_id": str(mem_uuid) if mem_uuid else "invalid",
            "character_id": str(char_uuid) if char_uuid else "invalid",
        },
    )
