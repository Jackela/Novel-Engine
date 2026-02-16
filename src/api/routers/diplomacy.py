"""Diplomacy API router for faction relationship operations.

This module provides API endpoints for managing diplomatic relations
between factions in a world, including retrieving the full diplomacy
matrix and individual faction relations.
"""

from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.contexts.world.domain.aggregates.diplomacy_matrix import DiplomacyMatrix
from src.contexts.world.domain.value_objects.diplomatic_status import DiplomaticStatus

router = APIRouter(tags=["diplomacy"])

# In-memory storage for diplomacy matrices (MVP implementation)
# In production, this would be replaced with a repository pattern
_diplomacy_matrices: Dict[str, DiplomacyMatrix] = {}


def get_diplomacy_storage() -> Dict[str, DiplomacyMatrix]:
    """Get the diplomacy storage dictionary."""
    return _diplomacy_matrices


def reset_diplomacy_storage() -> None:
    """Reset diplomacy storage (for testing)."""
    global _diplomacy_matrices
    _diplomacy_matrices = {}


# === Request/Response Models ===


class DiplomacyMatrixResponse(BaseModel):
    """Response model for full diplomacy matrix."""

    world_id: str = Field(description="World ID for this diplomacy matrix")
    matrix: Dict[str, Dict[str, str]] = Field(
        description="2D matrix of faction relationships"
    )
    factions: List[str] = Field(description="List of all faction IDs in the matrix")


class FactionDiplomacyResponse(BaseModel):
    """Response model for a single faction's diplomatic relations."""

    faction_id: str = Field(description="The faction's ID")
    allies: List[str] = Field(description="List of allied faction IDs")
    enemies: List[str] = Field(description="List of hostile/at war faction IDs")
    neutral: List[str] = Field(description="List of neutral faction IDs")


class SetRelationRequest(BaseModel):
    """Request model for setting a diplomatic relation."""

    status: str = Field(
        description="Diplomatic status to set (allied, friendly, neutral, cold, hostile, at_war)"
    )


# === Helper Functions ===


def _get_or_create_matrix(world_id: str) -> DiplomacyMatrix:
    """
    Get existing diplomacy matrix for world or create a new one.

    Args:
        world_id: Unique identifier for the world

    Returns:
        DiplomacyMatrix for the world (creates new if not exists)
    """
    if world_id not in _diplomacy_matrices:
        _diplomacy_matrices[world_id] = DiplomacyMatrix(world_id=world_id)
    return _diplomacy_matrices[world_id]


def _matrix_to_response(matrix: DiplomacyMatrix) -> DiplomacyMatrixResponse:
    """
    Convert DiplomacyMatrix domain object to API response model.

    Args:
        matrix: DiplomacyMatrix domain object

    Returns:
        DiplomacyMatrixResponse for the API
    """
    return DiplomacyMatrixResponse(
        world_id=matrix.world_id,
        matrix=matrix.to_matrix(),
        factions=sorted(list(matrix.faction_ids)),
    )


def _validate_status(status_str: str) -> DiplomaticStatus:
    """
    Validate and convert status string to DiplomaticStatus enum.

    Args:
        status_str: String representation of diplomatic status

    Returns:
        DiplomaticStatus enum value

    Raises:
        HTTPException: If status string is invalid
    """
    status_map = {
        "allied": DiplomaticStatus.ALLIED,
        "friendly": DiplomaticStatus.FRIENDLY,
        "neutral": DiplomaticStatus.NEUTRAL,
        "cold": DiplomaticStatus.COLD,
        "hostile": DiplomaticStatus.HOSTILE,
        "at_war": DiplomaticStatus.AT_WAR,
    }

    status_lower = status_str.lower().strip()
    if status_lower not in status_map:
        valid_values = ", ".join(status_map.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{status_str}'. Valid values: {valid_values}",
        )

    return status_map[status_lower]


# === Endpoints ===


@router.get(
    "/world/{world_id}/diplomacy", response_model=DiplomacyMatrixResponse
)
async def get_diplomacy_matrix(world_id: str) -> DiplomacyMatrixResponse:
    """
    Get the full diplomacy matrix for a world.

    Returns a 2D matrix showing diplomatic relations between all factions.
    Matrix entries are status strings (allied, friendly, neutral, cold, hostile, at_war).
    Self-relations are shown as '-'.

    Args:
        world_id: Unique identifier for the world

    Returns:
        DiplomacyMatrixResponse with full matrix and faction list
    """
    matrix = _get_or_create_matrix(world_id)
    return _matrix_to_response(matrix)


@router.get(
    "/world/{world_id}/diplomacy/faction/{faction_id}",
    response_model=FactionDiplomacyResponse,
)
async def get_faction_diplomacy(
    world_id: str, faction_id: str
) -> FactionDiplomacyResponse:
    """
    Get diplomatic relations for a single faction.

    Returns categorized lists of allies, enemies, and neutral factions.

    Args:
        world_id: Unique identifier for the world
        faction_id: ID of the faction to get relations for

    Returns:
        FactionDiplomacyResponse with categorized faction lists

    Raises:
        404: If faction not found in the diplomacy matrix
    """
    matrix = _get_or_create_matrix(world_id)

    # Check if faction exists
    if faction_id not in matrix.faction_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Faction '{faction_id}' not found in world '{world_id}'",
        )

    return FactionDiplomacyResponse(
        faction_id=faction_id,
        allies=matrix.get_allies(faction_id),
        enemies=matrix.get_enemies(faction_id),
        neutral=matrix.get_neutral(faction_id),
    )


@router.put(
    "/world/{world_id}/diplomacy/{faction_a}/{faction_b}",
    response_model=DiplomacyMatrixResponse,
)
async def set_relation(
    world_id: str, faction_a: str, faction_b: str, request: SetRelationRequest
) -> DiplomacyMatrixResponse:
    """
    Set the diplomatic relation between two factions.

    Updates the diplomatic status between two factions. The relation is
    symmetric - setting A's relation to B automatically sets B's relation to A.

    Args:
        world_id: Unique identifier for the world
        faction_a: First faction ID
        faction_b: Second faction ID
        request: SetRelationRequest with the new status

    Returns:
        DiplomacyMatrixResponse with updated matrix

    Raises:
        400: If status is invalid or operation fails
    """
    matrix = _get_or_create_matrix(world_id)

    # Validate and convert status
    status = _validate_status(request.status)

    # Set the relation
    result = matrix.set_status(faction_a, faction_b, status)

    if result.is_error:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to set relation: {str(result.error)}",
        )

    return _matrix_to_response(matrix)
