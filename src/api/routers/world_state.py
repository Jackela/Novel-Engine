"""World State API Router (PREP-010)

DEPRECATED: This router is deprecated in favor of src.api.routers.geopolitics

The /world/{world_id}/* endpoints are now served by the unified
geopolitics router at /api/geopolitics/world/{world_id}/*

This file will be removed in a future version.

This module provides API endpoints for geopolitical state queries,
enabling the frontend to visualize territory control, diplomacy, and resources.

Endpoints:
- GET /world/{world_id}/territories - Get territories with control info
- GET /world/{world_id}/diplomacy - Get diplomacy matrix with pacts
- GET /world/{world_id}/resources - Get faction resource summary
"""

from __future__ import annotations

import warnings

warnings.warn(
    "world_state router is deprecated. Use geopolitics router instead.",
    DeprecationWarning,
    stacklevel=2,
)

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request

from src.api.schemas.world_schemas import (
    DiplomacyMatrixDetailResponse,
    FactionResourceSummary,
    PactSummary,
    TerritoriesResponse,
    TerritorySummary,
    WorldResourcesResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/world", tags=["world-state"])


def _get_world_store(request: Request) -> Dict[str, Dict[str, Any]]:
    """Get the world store from app state."""
    store = getattr(request.app.state, "world_store", None)
    if store is None:
        store: dict[Any, Any] = {}
        request.app.state.world_store = store
    return store


def _get_world_data(request: Request, world_id: str) -> Optional[Dict[str, Any]]:
    """Get world data by ID."""
    world_store = _get_world_store(request)
    return world_store.get(world_id)


@router.get(
    "/{world_id}/territories",
    response_model=TerritoriesResponse,
    summary="Get world territories",
    description="Retrieve all territories with control information for visualization.",
)
async def get_territories(
    world_id: str,
    request: Request,
) -> TerritoriesResponse:
    """Get territories with control information.

    Args:
        world_id: The world ID to query
        request: FastAPI request object

    Returns:
        TerritoriesResponse with territory summaries
    """
    world_data = _get_world_data(request, world_id)

    if world_data is None:
        raise HTTPException(status_code=404, detail=f"World {world_id} not found")

    # Extract locations from world data
    locations = world_data.get("locations", [])
    territories: list[Any] = []
    controlled_count = 0
    contested_count = 0

    for loc in locations:
        if not isinstance(loc, dict):
            continue

        controlling_faction = loc.get("controlling_faction_id")
        contested_by = loc.get("contested_by", [])
        resource_yields = loc.get("resource_yields", [])

        territory = TerritorySummary(
            location_id=loc.get("id", ""),
            name=loc.get("name", "Unknown"),
            location_type=loc.get("location_type", "unknown"),
            controlling_faction_id=controlling_faction,
            contested_by=contested_by if isinstance(contested_by, list) else [],
            territory_value=loc.get("territory_value", 0),
            infrastructure_level=loc.get("infrastructure_level", 0),
            population=loc.get("population", 0),
            resource_types=[
                ry.get("resource_type", "")
                for ry in resource_yields
                if isinstance(ry, dict) and ry.get("resource_type")
            ],
        )
        territories.append(territory)

        if controlling_faction:
            controlled_count += 1
        if contested_by and len(contested_by) > 0:
            contested_count += 1

    return TerritoriesResponse(
        world_id=world_id,
        territories=territories,
        total_count=len(territories),
        controlled_count=controlled_count,
        contested_count=contested_count,
    )


@router.get(
    "/{world_id}/diplomacy",
    response_model=DiplomacyMatrixDetailResponse,
    summary="Get diplomacy matrix",
    description="Retrieve the full diplomacy matrix with active pacts.",
)
async def get_diplomacy(
    world_id: str,
    request: Request,
) -> DiplomacyMatrixDetailResponse:
    """Get diplomacy matrix with pacts.

    Args:
        world_id: The world ID to query
        request: FastAPI request object

    Returns:
        DiplomacyMatrixDetailResponse with matrix and pacts
    """
    world_data = _get_world_data(request, world_id)

    if world_data is None:
        raise HTTPException(status_code=404, detail=f"World {world_id} not found")

    # Get diplomacy matrix
    diplomacy_data = world_data.get("diplomacy_matrix", {})
    matrix = diplomacy_data.get("matrix", {})
    factions = diplomacy_data.get("factions", [])

    # Get active pacts
    pacts_data = diplomacy_data.get("active_pacts", [])
    active_pacts: list[Any] = []
    for pact in pacts_data:
        if not isinstance(pact, dict):
            continue

        active_pacts.append(
            PactSummary(
                pact_id=pact.get("id", ""),
                faction_a_id=pact.get("faction_a_id", ""),
                faction_b_id=pact.get("faction_b_id", ""),
                pact_type=pact.get("pact_type", "unknown"),
                signed_date=pact.get("signed_date"),
                expires_date=pact.get("expires_date"),
                is_active=pact.get("is_active", True),
            )
        )

    return DiplomacyMatrixDetailResponse(
        world_id=world_id,
        matrix=matrix if isinstance(matrix, dict) else {},
        factions=factions if isinstance(factions, list) else [],
        active_pacts=active_pacts,
    )


@router.get(
    "/{world_id}/resources",
    response_model=WorldResourcesResponse,
    summary="Get world resources",
    description="Retrieve faction resource summary for the world.",
)
async def get_resources(
    world_id: str,
    request: Request,
) -> WorldResourcesResponse:
    """Get faction resource summary.

    Args:
        world_id: The world ID to query
        request: FastAPI request object

    Returns:
        WorldResourcesResponse with faction resource summaries
    """
    world_data = _get_world_data(request, world_id)

    if world_data is None:
        raise HTTPException(status_code=404, detail=f"World {world_id} not found")

    factions_data = world_data.get("factions", [])
    locations = world_data.get("locations", [])

    # Build faction resource summaries
    faction_summaries: list[Any] = []
    total_resources: Dict[str, int] = {}

    for faction in factions_data:
        if not isinstance(faction, dict):
            continue

        faction_id = faction.get("id", "")
        faction_name = faction.get("name", "Unknown")

        # Get territories controlled by this faction
        controlled_locations = [
            loc
            for loc in locations
            if isinstance(loc, dict) and loc.get("controlling_faction_id") == faction_id
        ]

        # Calculate resources from controlled territories
        resources: Dict[str, int] = {}
        total_population = 0

        for loc in controlled_locations:
            total_population += loc.get("population", 0)

            # Sum resource yields
            for ry in loc.get("resource_yields", []):
                if isinstance(ry, dict):
                    resource_type = ry.get("resource_type", "")
                    if resource_type:
                        amount = ry.get("current_stock", 0)
                        resources[resource_type] = (
                            resources.get(resource_type, 0) + amount
                        )

        # Add faction's own resources
        faction_resources = faction.get("resources", {})
        if isinstance(faction_resources, dict):
            for res_type, amount in faction_resources.items():
                resources[res_type] = resources.get(res_type, 0) + amount

        # Update totals
        for res_type, amount in resources.items():
            total_resources[res_type] = total_resources.get(res_type, 0) + amount

        faction_summaries.append(
            FactionResourceSummary(
                faction_id=faction_id,
                faction_name=faction_name,
                resources=resources,
                total_territories=len(controlled_locations),
                total_population=total_population,
            )
        )

    return WorldResourcesResponse(
        world_id=world_id,
        factions=faction_summaries,
        total_resources=total_resources,
        timestamp=datetime.utcnow().isoformat(),
    )
