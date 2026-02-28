"""
Geopolitics API Router

Unified API endpoints for geopolitical operations including
diplomacy, territory control, and resources.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.api.schemas.world_schemas import (
    DiplomacyMatrixDetailResponse,
    FactionResourceSummary,
    PactSummary,
    TerritoriesResponse,
    TerritorySummary,
    WorldResourcesResponse,
)
from src.contexts.world.application.services.geopolitics_service import GeopoliticsService
from src.contexts.world.domain.aggregates.diplomacy_matrix import DiplomacyMatrix

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/geopolitics", tags=["geopolitics"])


# === Request Schemas ===

class DeclareWarRequest(BaseModel):
    """Request body for declaring war."""
    aggressor_id: str
    defender_id: str
    reason: str


class FormAllianceRequest(BaseModel):
    """Request body for forming alliance."""
    faction_a_id: str
    faction_b_id: str
    pact_type: str = "defensive_alliance"


class TransferTerritoryRequest(BaseModel):
    """Request body for transferring territory."""
    location_id: str
    new_controller_id: Optional[str]
    reason: str = ""


# === Storage Helpers ===

def _get_world_store(request: Request) -> Dict[str, Dict[str, Any]]:
    """Get the world store from app state."""
    store = getattr(request.app.state, "world_store", None)
    if store is None:
        store = {}
        request.app.state.world_store = store
    return store


def _get_or_create_diplomacy_matrix(
    world_store: Dict[str, Dict[str, Any]],
    world_id: str,
) -> DiplomacyMatrix:
    """Get or create a diplomacy matrix for a world."""
    world_data = world_store.get(world_id, {})

    if "diplomacy_matrix" in world_data:
        matrix_data = world_data["diplomacy_matrix"]
        return DiplomacyMatrix.from_dict(matrix_data)

    matrix = DiplomacyMatrix(world_id=world_id)

    # Register factions from world data
    factions = world_data.get("factions", [])
    for faction in factions:
        if isinstance(faction, dict) and "id" in faction:
            matrix.register_faction(faction["id"])

    return matrix


def _save_diplomacy_matrix(
    world_store: Dict[str, Dict[str, Any]],
    world_id: str,
    matrix: DiplomacyMatrix,
) -> None:
    """Save diplomacy matrix back to world store."""
    if world_id not in world_store:
        world_store[world_id] = {}

    world_store[world_id]["diplomacy_matrix"] = matrix.to_dict()


# === Service Instance ===

def _get_geopolitics_service() -> GeopoliticsService:
    """Get a GeopoliticsService instance."""
    return GeopoliticsService()


# === Endpoints ===

@router.get(
    "/world/{world_id}/diplomacy",
    response_model=DiplomacyMatrixDetailResponse,
    summary="Get diplomacy matrix",
)
async def get_diplomacy(
    world_id: str,
    request: Request,
) -> DiplomacyMatrixDetailResponse:
    """Get the full diplomacy matrix with active pacts."""
    world_store = _get_world_store(request)
    matrix = _get_or_create_diplomacy_matrix(world_store, world_id)

    # Build active pacts list
    active_pacts = [
        PactSummary(
            pact_id=pact.id,
            faction_a_id=pact.faction_a_id,
            faction_b_id=pact.faction_b_id,
            pact_type=pact.pact_type.value if hasattr(pact.pact_type, 'value') else str(pact.pact_type),
            signed_date=str(pact.signed_date) if hasattr(pact, 'signed_date') else None,
            expires_date=str(pact.expires_date) if hasattr(pact, 'expires_date') else None,
            is_active=pact.is_active() if hasattr(pact, 'is_active') else True,
        )
        for pact in matrix.active_pacts
    ]

    return DiplomacyMatrixDetailResponse(
        world_id=world_id,
        matrix=matrix.to_matrix(),
        factions=sorted(list(matrix.faction_ids)),
        active_pacts=active_pacts,
    )


@router.get(
    "/world/{world_id}/territories",
    response_model=TerritoriesResponse,
    summary="Get world territories",
)
async def get_territories(
    world_id: str,
    request: Request,
) -> TerritoriesResponse:
    """Get territories with control information."""
    world_store = _get_world_store(request)
    world_data = world_store.get(world_id)

    if world_data is None:
        raise HTTPException(status_code=404, detail=f"World {world_id} not found")

    locations = world_data.get("locations", [])
    territories = []
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
    "/world/{world_id}/resources",
    response_model=WorldResourcesResponse,
    summary="Get world resources",
)
async def get_resources(
    world_id: str,
    request: Request,
) -> WorldResourcesResponse:
    """Get faction resource summary."""
    world_store = _get_world_store(request)
    world_data = world_store.get(world_id)

    if world_data is None:
        raise HTTPException(status_code=404, detail=f"World {world_id} not found")

    factions_data = world_data.get("factions", [])
    locations = world_data.get("locations", [])

    faction_summaries = []
    total_resources: Dict[str, int] = {}

    for faction in factions_data:
        if not isinstance(faction, dict):
            continue

        faction_id = faction.get("id", "")
        faction_name = faction.get("name", "Unknown")

        controlled_locations = [
            loc for loc in locations
            if isinstance(loc, dict) and loc.get("controlling_faction_id") == faction_id
        ]

        resources: Dict[str, int] = {}
        total_population = 0

        for loc in controlled_locations:
            total_population += loc.get("population", 0)
            for ry in loc.get("resource_yields", []):
                if isinstance(ry, dict):
                    resource_type = ry.get("resource_type", "")
                    if resource_type:
                        amount = ry.get("current_stock", 0)
                        resources[resource_type] = resources.get(resource_type, 0) + amount

        faction_resources = faction.get("resources", {})
        if isinstance(faction_resources, dict):
            for res_type, amount in faction_resources.items():
                resources[res_type] = resources.get(res_type, 0) + amount

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


@router.post(
    "/world/{world_id}/war",
    summary="Declare war",
)
async def declare_war(
    world_id: str,
    request_body: DeclareWarRequest,
    request: Request,
) -> Dict[str, Any]:
    """Declare war between two factions."""
    world_store = _get_world_store(request)
    matrix = _get_or_create_diplomacy_matrix(world_store, world_id)
    service = _get_geopolitics_service()

    result = service.declare_war(
        matrix=matrix,
        aggressor_id=request_body.aggressor_id,
        defender_id=request_body.defender_id,
        reason=request_body.reason,
        world_id=world_id,
    )

    if result.is_error:
        raise HTTPException(
            status_code=400,
            detail=str(result.error),
        )

    _save_diplomacy_matrix(world_store, world_id, matrix)

    return {
        "status": "war_declared",
        "aggressor_id": request_body.aggressor_id,
        "defender_id": request_body.defender_id,
    }


@router.post(
    "/world/{world_id}/alliance",
    summary="Form alliance",
)
async def form_alliance(
    world_id: str,
    request_body: FormAllianceRequest,
    request: Request,
) -> Dict[str, Any]:
    """Form an alliance between two factions."""
    from src.contexts.world.domain.events.geopolitics_events import PactType

    world_store = _get_world_store(request)
    matrix = _get_or_create_diplomacy_matrix(world_store, world_id)
    service = _get_geopolitics_service()

    pact_type = PactType.DEFENSIVE_ALLIANCE
    try:
        pact_type = PactType(request_body.pact_type)
    except ValueError:
        pass

    result = service.form_alliance(
        matrix=matrix,
        faction_a_id=request_body.faction_a_id,
        faction_b_id=request_body.faction_b_id,
        pact_type=pact_type,
        world_id=world_id,
    )

    if result.is_error:
        raise HTTPException(
            status_code=400,
            detail=str(result.error),
        )

    _save_diplomacy_matrix(world_store, world_id, matrix)

    return {
        "status": "alliance_formed",
        "faction_a_id": request_body.faction_a_id,
        "faction_b_id": request_body.faction_b_id,
    }


@router.post(
    "/world/{world_id}/transfer-territory",
    summary="Transfer territory",
)
async def transfer_territory(
    world_id: str,
    request_body: TransferTerritoryRequest,
    request: Request,
) -> Dict[str, Any]:
    """Transfer territory control to another faction."""
    world_store = _get_world_store(request)
    world_data = world_store.get(world_id)

    if world_data is None:
        raise HTTPException(status_code=404, detail=f"World {world_id} not found")

    locations = world_data.get("locations", [])
    location = None
    location_idx = None

    for idx, loc in enumerate(locations):
        if isinstance(loc, dict) and loc.get("id") == request_body.location_id:
            location = loc
            location_idx = idx
            break

    if location is None:
        raise HTTPException(
            status_code=404,
            detail=f"Location {request_body.location_id} not found",
        )

    previous_controller = location.get("controlling_faction_id")
    location["controlling_faction_id"] = request_body.new_controller_id
    locations[location_idx] = location

    # Emit event via service
    service = _get_geopolitics_service()
    from src.contexts.world.domain.events.geopolitics_events import TerritoryChangedEvent
    event = TerritoryChangedEvent.create(
        location_id=request_body.location_id,
        previous_controller_id=previous_controller,
        new_controller_id=request_body.new_controller_id,
        world_id=world_id,
        reason=request_body.reason,
    )
    service._emit_event(event)

    return {
        "status": "territory_transferred",
        "location_id": request_body.location_id,
        "previous_controller_id": previous_controller,
        "new_controller_id": request_body.new_controller_id,
    }
