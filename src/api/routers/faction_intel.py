"""Faction Intel API router for faction decision-making and intent management.

This module provides API endpoints for triggering faction decision-making
and retrieving intent history, following the OpenSpec specification for
the W5 Faction AI Intents feature.

Endpoints:
    POST /api/world/factions/{faction_id}/decide - Trigger decision generation
    GET /api/world/factions/{faction_id}/intents - Get intent history
    POST /api/world/factions/{faction_id}/intents/{intent_id}/select - Select intent
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Dict
from uuid import uuid4

import structlog
from fastapi import APIRouter, HTTPException, Query, Request

from src.api.schemas.system_schemas import ErrorDetail
from src.api.schemas.world_schemas import (
    FactionIntentResponse,
    GenerateIntentsRequest,
    GenerateIntentsResponse,
    IntentListResponse,
    IntentStatusEnum,
    SelectIntentResponse,
)
from src.contexts.world.domain.entities.faction_intent import (
    ActionType,
    FactionIntent,
    IntentStatus,
)
from src.contexts.world.infrastructure.persistence.in_memory_faction_intent_repository import (
    InMemoryFactionIntentRepository,
)

logger = structlog.get_logger()

router = APIRouter(tags=["faction-intel"])

# Singleton repository for MVP
# In a multi-world scenario, this would be dependency-injected
_repository = InMemoryFactionIntentRepository()

# Rate limiting storage: faction_id -> last_generation_timestamp
# REQ-API-004: Maximum 1 generation request per faction per 60 seconds
_rate_limit_store: Dict[str, float] = {}
RATE_LIMIT_SECONDS = 60


def _check_rate_limit(faction_id: str) -> tuple[bool, int]:
    """Check if faction is rate-limited for decision generation.

    Args:
        faction_id: ID of the faction to check

    Returns:
        Tuple of (is_allowed, retry_after_seconds)
        - is_allowed: True if request is allowed, False if rate-limited
        - retry_after_seconds: Seconds until rate limit expires (0 if allowed)
    """
    current_time = time.time()
    last_generation = _rate_limit_store.get(faction_id, 0)
    elapsed = current_time - last_generation

    if elapsed < RATE_LIMIT_SECONDS:
        return False, int(RATE_LIMIT_SECONDS - elapsed)

    return True, 0


def _update_rate_limit(faction_id: str) -> None:
    """Update rate limit timestamp for a faction.

    Args:
        faction_id: ID of the faction
    """
    _rate_limit_store[faction_id] = time.time()


def _intent_to_response(intent: FactionIntent) -> FactionIntentResponse:
    """Convert FactionIntent domain entity to API response model.

    Args:
        intent: FactionIntent domain object

    Returns:
        FactionIntentResponse for the API
    """
    return FactionIntentResponse(
        id=intent.id,
        faction_id=intent.faction_id,
        action_type=intent.action_type.value,
        target_id=intent.target_id,
        rationale=intent.rationale,
        priority=intent.priority,
        status=intent.status.value,
        created_at=intent.created_at.isoformat(),
    )


def _generate_mock_intents(faction_id: str) -> list[FactionIntent]:
    """Generate mock intents for a faction.

    This is a placeholder implementation that generates rule-based intents
    without requiring full world state. In production, this would use
    FactionDecisionService with LLM integration.

    Args:
        faction_id: ID of the faction

    Returns:
        List of generated FactionIntent objects
    """
    intents = []
    now = datetime.now()

    # Generate 2-3 varied intents for demonstration
    intent_configs = [
        (ActionType.STABILIZE, None, "Consolidate resources and strengthen borders", 1),
        (ActionType.EXPAND, "unclaimed-territory-1", "Expand influence into neighboring regions", 2),
        (ActionType.TRADE, "neutral-faction-1", "Establish trade routes for economic growth", 3),
    ]

    for action_type, target_id, rationale, priority in intent_configs:
        intent = FactionIntent(
            faction_id=faction_id,
            action_type=action_type,
            target_id=target_id,
            rationale=rationale,
            priority=priority,
            status=IntentStatus.PROPOSED,
            created_at=now,
        )
        intents.append(intent)

    return intents


@router.post(
    "/world/factions/{faction_id}/decide",
    response_model=GenerateIntentsResponse,
    responses={
        200: {"description": "Intents generated successfully"},
        404: {"description": "Faction not found"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def generate_faction_intents(
    faction_id: str,
    request: GenerateIntentsRequest,
    http_request: Request,
) -> GenerateIntentsResponse:
    """Trigger decision generation for a faction.

    Generates strategic intents for the faction based on world state,
    diplomatic relations, and optional context hints.

    REQ-API-001: Trigger Decision Endpoint
    - Rate-limited to 1 request per 60 seconds per faction
    - Returns generated intents with unique generation_id

    Args:
        faction_id: Unique identifier for the faction
        request: Optional context hints for generation
        http_request: FastAPI request object

    Returns:
        GenerateIntentsResponse with generated intents and generation_id

    Raises:
        404: Faction not found
        429: Rate limit exceeded (with Retry-After header)
    """
    logger.info(
        "generate_intents_request",
        faction_id=faction_id,
        context_hints=request.context_hints,
    )

    # Check rate limit (REQ-API-004)
    is_allowed, retry_after = _check_rate_limit(faction_id)
    if not is_allowed:
        logger.warning(
            "generate_intents_rate_limited",
            faction_id=faction_id,
            retry_after=retry_after,
        )
        raise HTTPException(
            status_code=429,
            detail=ErrorDetail(
                code="RATE_LIMITED",
                message=f"Please wait {retry_after} seconds before generating again",
                details={"retry_after_seconds": retry_after},
            ).model_dump(),
            headers={"Retry-After": str(retry_after)},
        )

    # Generate intents (mock implementation for MVP)
    # TODO: Replace with FactionDecisionService when available
    intents = _generate_mock_intents(faction_id)

    # Save intents to repository
    for intent in intents:
        _repository.save(intent)

    # Update rate limit
    _update_rate_limit(faction_id)

    # Generate unique batch ID
    generation_id = str(uuid4())

    logger.info(
        "generate_intents_success",
        faction_id=faction_id,
        generation_id=generation_id,
        intents_count=len(intents),
    )

    return GenerateIntentsResponse(
        intents=[_intent_to_response(i) for i in intents],
        generation_id=generation_id,
    )


@router.get(
    "/world/factions/{faction_id}/intents",
    response_model=IntentListResponse,
    responses={
        200: {"description": "Intent history retrieved successfully"},
        404: {"description": "Faction not found"},
    },
)
async def get_faction_intents(
    faction_id: str,
    status: IntentStatusEnum | None = Query(
        None, description="Filter by intent status"
    ),
    limit: int = Query(
        20, ge=1, le=100, description="Maximum number of intents to return"
    ),
    offset: int = Query(0, ge=0, description="Number of intents to skip"),
) -> IntentListResponse:
    """Get intent history for a faction.

    Retrieves paginated list of intents for the faction, optionally
    filtered by status.

    REQ-API-002: Get Intents Endpoint
    - Default limit: 20, max limit: 100
    - Returns total count and has_more flag for pagination

    Args:
        faction_id: Unique identifier for the faction
        status: Optional filter by intent status
        limit: Maximum number of intents to return (1-100, default 20)
        offset: Number of intents to skip for pagination

    Returns:
        IntentListResponse with intents, total count, and has_more flag

    Raises:
        404: Faction not found
    """
    logger.debug(
        "get_intents_request",
        faction_id=faction_id,
        status=status,
        limit=limit,
        offset=offset,
    )

    # Get paginated intents from repository
    # Convert string status to IntentStatus enum for repository
    status_enum: IntentStatus | None = None
    if status:
        status_enum = IntentStatus(status.value)

    intents, total, has_more = _repository.find_by_faction_paginated(
        faction_id=faction_id,
        status=status_enum,
        limit=limit,
        offset=offset,
    )

    logger.debug(
        "get_intents_response",
        faction_id=faction_id,
        count=len(intents),
        total=total,
        has_more=has_more,
    )

    return IntentListResponse(
        intents=[_intent_to_response(i) for i in intents],
        total=total,
        has_more=has_more,
    )


@router.post(
    "/world/factions/{faction_id}/intents/{intent_id}/select",
    response_model=SelectIntentResponse,
    responses={
        200: {"description": "Intent selected successfully"},
        404: {"description": "Intent not found"},
        409: {"description": "Intent already selected or in terminal state"},
    },
)
async def select_faction_intent(
    faction_id: str,
    intent_id: str,
) -> SelectIntentResponse:
    """Select an intent for execution.

    Marks the specified intent as SELECTED, indicating it has been
    chosen for execution during the next simulation tick.

    REQ-API-003: Select Intent Endpoint
    - Only PROPOSED intents can be selected
    - Returns 409 if intent is already selected or in terminal state

    Args:
        faction_id: Unique identifier for the faction
        intent_id: Unique identifier for the intent

    Returns:
        SelectIntentResponse with the selected intent

    Raises:
        404: Intent not found
        409: Intent already selected or in terminal state
    """
    logger.info(
        "select_intent_request",
        faction_id=faction_id,
        intent_id=intent_id,
    )

    # Find the intent
    intent = _repository.find_by_id(intent_id)

    if intent is None:
        logger.warning(
            "select_intent_not_found",
            faction_id=faction_id,
            intent_id=intent_id,
        )
        raise HTTPException(
            status_code=404,
            detail=ErrorDetail(
                code="INTENT_NOT_FOUND",
                message=f"Intent {intent_id} not found",
            ).model_dump(),
        )

    # Verify faction ownership
    if intent.faction_id != faction_id:
        logger.warning(
            "select_intent_faction_mismatch",
            faction_id=faction_id,
            intent_id=intent_id,
            actual_faction_id=intent.faction_id,
        )
        raise HTTPException(
            status_code=404,
            detail=ErrorDetail(
                code="INTENT_NOT_FOUND",
                message=f"Intent {intent_id} not found for faction {faction_id}",
            ).model_dump(),
        )

    # Check if already selected or in terminal state
    if intent.status == IntentStatus.SELECTED:
        raise HTTPException(
            status_code=409,
            detail=ErrorDetail(
                code="ALREADY_SELECTED",
                message="Intent has already been selected",
                details={"current_status": intent.status.value},
            ).model_dump(),
        )

    if intent.is_terminal:
        raise HTTPException(
            status_code=409,
            detail=ErrorDetail(
                code="INTENT_TERMINAL",
                message=f"Intent is in terminal state: {intent.status.value}",
                details={"current_status": intent.status.value},
            ).model_dump(),
        )

    # Mark as selected
    success = _repository.mark_selected(intent_id)

    if not success:
        # This shouldn't happen if we got here, but handle defensively
        raise HTTPException(
            status_code=500,
            detail=ErrorDetail(
                code="SELECTION_FAILED",
                message="Failed to select intent",
            ).model_dump(),
        )

    # Re-fetch to get updated state
    updated_intent = _repository.find_by_id(intent_id)

    logger.info(
        "select_intent_success",
        faction_id=faction_id,
        intent_id=intent_id,
    )

    return SelectIntentResponse(
        intent=_intent_to_response(updated_intent),
        status="SELECTED",
    )
