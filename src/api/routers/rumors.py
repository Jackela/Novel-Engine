"""Rumors API router for world rumor operations.

This module provides API endpoints for managing world rumors,
including listing, filtering, and retrieving rumor details.

Endpoints:
    GET /world/{world_id}/rumors - List rumors with optional filters
    GET /world/{world_id}/rumors/{rumor_id} - Get single rumor details
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query

from src.api.schemas import (
    CalendarData,
    ErrorDetail,
    RumorListResponse,
    RumorResponse,
    SortByEnum,
)

router = APIRouter(tags=["rumors"])

# === In-memory Storage (MVP Implementation) ===

# Rumors storage: world_id -> list of rumors
_rumors_storage: Dict[str, List[Dict[str, Any]]] = {}


def reset_rumors_storage() -> None:
    """Reset rumors storage (for testing)."""
    global _rumors_storage
    _rumors_storage = {}


def _get_mock_rumors(
    world_id: str, location_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get mock rumors for development.

    In production, this would fetch from a repository.
    """
    if world_id not in _rumors_storage:
        # Generate mock rumors for development
        _rumors_storage[world_id] = [
            {
                "rumor_id": str(uuid4()),
                "content": "Word spreads of a great battle in the northern mountains between the Iron Legion and the Silver Alliance.",
                "truth_value": 85,
                "origin_type": "event",
                "source_event_id": "evt-battle-001",
                "origin_location_id": "loc-north-pass",
                "current_locations": ["loc-north-pass", "loc-capital", "loc-port-city"],
                "created_date": {
                    "year": 1042,
                    "month": 3,
                    "day": 15,
                    "era_name": "Third Age",
                    "formatted": "Year 1042, Month 3, Day 15 - Third Age",
                },
                "spread_count": 3,
                "veracity_label": "Confirmed",
            },
            {
                "rumor_id": str(uuid4()),
                "content": "Merchants whisper about new trade routes opening between the eastern kingdoms.",
                "truth_value": 65,
                "origin_type": "npc",
                "source_event_id": None,
                "origin_location_id": "loc-market-district",
                "current_locations": ["loc-market-district", "loc-port-city"],
                "created_date": {
                    "year": 1042,
                    "month": 3,
                    "day": 10,
                    "era_name": "Third Age",
                    "formatted": "Year 1042, Month 3, Day 10 - Third Age",
                },
                "spread_count": 2,
                "veracity_label": "Likely True",
            },
            {
                "rumor_id": str(uuid4()),
                "content": "Rumors circulate that the king's advisor may be secretly working for a foreign power, though evidence remains scarce.",
                "truth_value": 35,
                "origin_type": "unknown",
                "source_event_id": None,
                "origin_location_id": "loc-castle",
                "current_locations": ["loc-castle", "loc-tavern"],
                "created_date": {
                    "year": 1042,
                    "month": 3,
                    "day": 12,
                    "era_name": "Third Age",
                    "formatted": "Year 1042, Month 3, Day 12 - Third Age",
                },
                "spread_count": 5,
                "veracity_label": "Likely False",
            },
            {
                "rumor_id": str(uuid4()),
                "content": "The ancient dragon of the southern peaks has awakened after centuries of slumber.",
                "truth_value": 92,
                "origin_type": "event",
                "source_event_id": "evt-dragon-001",
                "origin_location_id": "loc-southern-peaks",
                "current_locations": ["loc-southern-peaks"],
                "created_date": {
                    "year": 1042,
                    "month": 3,
                    "day": 14,
                    "era_name": "Third Age",
                    "formatted": "Year 1042, Month 3, Day 14 - Third Age",
                },
                "spread_count": 1,
                "veracity_label": "Confirmed",
            },
            {
                "rumor_id": str(uuid4()),
                "content": "They say a hidden treasure lies beneath the old lighthouse, but many have searched in vain.",
                "truth_value": 15,
                "origin_type": "player",
                "source_event_id": None,
                "origin_location_id": "loc-lighthouse",
                "current_locations": [
                    "loc-lighthouse",
                    "loc-fishing-village",
                    "loc-tavern",
                ],
                "created_date": {
                    "year": 1042,
                    "month": 3,
                    "day": 5,
                    "era_name": "Third Age",
                    "formatted": "Year 1042, Month 3, Day 5 - Third Age",
                },
                "spread_count": 8,
                "veracity_label": "False",
            },
        ]

    rumors = _rumors_storage[world_id]

    if location_id:
        rumors = [r for r in rumors if location_id in r.get("current_locations", [])]

    return rumors


# === Helper Functions ===


def _sort_rumors(
    rumors: List[Dict[str, Any]], sort_by: SortByEnum
) -> List[Dict[str, Any]]:
    """Sort rumors by the specified criteria."""
    if sort_by == SortByEnum.RECENT:
        # Sort by day descending (most recent first)
        return sorted(
            rumors,
            key=lambda r: r.get("created_date", {}).get("day", 0),
            reverse=True,
        )
    elif sort_by == SortByEnum.RELIABLE:
        # Sort by truth_value descending (most reliable first)
        return sorted(rumors, key=lambda r: r.get("truth_value", 0), reverse=True)
    elif sort_by == SortByEnum.SPREAD:
        # Sort by spread_count descending (most spread first)
        return sorted(rumors, key=lambda r: r.get("spread_count", 0), reverse=True)
    return rumors


def _dict_to_response(rumor: Dict[str, Any]) -> RumorResponse:
    """Convert a rumor dict to response model."""
    created_date = None
    if rumor.get("created_date"):
        cd = rumor["created_date"]
        created_date = CalendarData(
            year=cd.get("year", 1),
            month=cd.get("month", 1),
            day=cd.get("day", 1),
            era_name=cd.get("era_name", "First Age"),
            formatted=cd.get("formatted", ""),
        )

    return RumorResponse(
        rumor_id=rumor.get("rumor_id", ""),
        content=rumor.get("content", ""),
        truth_value=rumor.get("truth_value", 50),
        origin_type=rumor.get("origin_type", "unknown"),
        source_event_id=rumor.get("source_event_id"),
        origin_location_id=rumor.get("origin_location_id", ""),
        current_locations=rumor.get("current_locations", []),
        created_date=created_date,
        spread_count=rumor.get("spread_count", 0),
        veracity_label=rumor.get("veracity_label", "Uncertain"),
    )


# === Endpoints ===


@router.get(
    "/world/{world_id}/rumors",
    response_model=RumorListResponse,
    summary="List rumors",
    description="Get a list of rumors with optional location filter and sorting.",
)
async def list_rumors(
    world_id: str,
    location_id: Optional[str] = Query(
        None, description="Filter by location ID (rumors at this location)"
    ),
    sort_by: SortByEnum = Query(
        SortByEnum.RECENT, description="Sort order: recent, reliable, or spread"
    ),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
) -> RumorListResponse:
    """List rumors for a world with optional filtering and sorting.

    Args:
        world_id: Unique identifier for the world
        location_id: Optional filter for rumors at a specific location
        sort_by: Sort order (recent, reliable, spread)
        limit: Maximum number of results to return

    Returns:
        RumorListResponse with filtered and sorted rumors
    """
    rumors = _get_mock_rumors(world_id, location_id)
    sorted_rumors = _sort_rumors(rumors, sort_by)
    limited_rumors = sorted_rumors[:limit]

    return RumorListResponse(
        rumors=[_dict_to_response(r) for r in limited_rumors],
        total=len(limited_rumors),
    )


@router.get(
    "/world/{world_id}/rumors/{rumor_id}",
    response_model=RumorResponse,
    summary="Get rumor details",
    description="Get detailed information about a specific rumor.",
)
async def get_rumor(
    world_id: str,
    rumor_id: str,
) -> RumorResponse:
    """Get details for a specific rumor.

    Args:
        world_id: Unique identifier for the world
        rumor_id: Unique identifier for the rumor

    Returns:
        RumorResponse with full rumor details

    Raises:
        404: Rumor not found
    """
    rumors = _get_mock_rumors(world_id)

    for rumor in rumors:
        if rumor.get("rumor_id") == rumor_id:
            return _dict_to_response(rumor)

    raise HTTPException(
        status_code=404,
        detail=ErrorDetail(
            code="RUMOR_NOT_FOUND",
            message=f"Rumor '{rumor_id}' not found in world '{world_id}'",
        ).model_dump(),
    )
