"""Relationships API router.

This module provides CRUD endpoints for the Relationship entity,
enabling the World Knowledge Graph to track connections between
characters, factions, locations, and other world entities.

Endpoints:
    POST /api/relationships - Create a new relationship
    GET /api/relationships/by-entity/{entity_id} - Get relationships for an entity
    DELETE /api/relationships/{relationship_id} - Delete a relationship
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from src.api.schemas import (
    RelationshipCreateRequest,
    RelationshipListResponse,
    RelationshipResponse,
    RelationshipUpdateRequest,
)
from src.contexts.world.domain.entities.relationship import (
    EntityType,
    Relationship,
    RelationshipType,
)
from src.contexts.world.infrastructure.persistence.in_memory_relationship_repository import (
    InMemoryRelationshipRepository,
)

router = APIRouter(prefix="/relationships", tags=["relationships"])

# Global repository instance (would be injected via DI in production)
_repository: Optional[InMemoryRelationshipRepository] = None


def get_repository() -> InMemoryRelationshipRepository:
    """Get or create the repository singleton.

    Why singleton pattern here: Enables shared state during development
    and testing without a database. In production, this would be replaced
    with dependency injection of a PostgreSQL-backed repository.
    """
    global _repository
    if _repository is None:
        _repository = InMemoryRelationshipRepository()
    return _repository


def _parse_entity_type(value: str) -> EntityType:
    """Parse string to EntityType enum.

    Args:
        value: Entity type string (case-insensitive).

    Returns:
        Parsed EntityType.

    Raises:
        HTTPException: If value is not a valid entity type.
    """
    try:
        return EntityType(value.lower())
    except ValueError:
        valid_types = [t.value for t in EntityType]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entity type: {value}. Valid types: {valid_types}",
        )


def _parse_relationship_type(value: str) -> RelationshipType:
    """Parse string to RelationshipType enum.

    Args:
        value: Relationship type string (case-insensitive).

    Returns:
        Parsed RelationshipType.

    Raises:
        HTTPException: If value is not a valid relationship type.
    """
    try:
        return RelationshipType(value.lower())
    except ValueError:
        valid_types = [t.value for t in RelationshipType]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid relationship type: {value}. Valid types: {valid_types}",
        )


def _relationship_to_response(relationship: Relationship) -> RelationshipResponse:
    """Convert domain Relationship to API response model."""
    return RelationshipResponse(
        id=relationship.id,
        source_id=relationship.source_id,
        source_type=relationship.source_type.value,
        target_id=relationship.target_id,
        target_type=relationship.target_type.value,
        relationship_type=relationship.relationship_type.value,
        description=relationship.description,
        strength=relationship.strength,
        is_active=relationship.is_active,
        created_at=relationship.created_at.isoformat(),
        updated_at=relationship.updated_at.isoformat(),
    )


@router.post("", response_model=RelationshipResponse, status_code=status.HTTP_201_CREATED)
async def create_relationship(request: RelationshipCreateRequest) -> RelationshipResponse:
    """Create a new relationship between entities.

    Creates a directed relationship from source to target. For bidirectional
    relationships (like ALLY or ENEMY), consider creating both directions.

    Args:
        request: Relationship creation request.

    Returns:
        The created relationship.

    Raises:
        HTTPException: If validation fails or entities are invalid.
    """
    repo = get_repository()

    source_type = _parse_entity_type(request.source_type)
    target_type = _parse_entity_type(request.target_type)
    relationship_type = _parse_relationship_type(request.relationship_type)

    try:
        relationship = Relationship(
            source_id=request.source_id,
            source_type=source_type,
            target_id=request.target_id,
            target_type=target_type,
            relationship_type=relationship_type,
            description=request.description,
            strength=request.strength,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    saved = await repo.save(relationship)
    return _relationship_to_response(saved)


@router.get("/by-entity/{entity_id}", response_model=RelationshipListResponse)
async def get_relationships_by_entity(
    entity_id: str,
    entity_type: Optional[str] = Query(
        None, description="Filter by entity type (CHARACTER, FACTION, etc.)"
    ),
    include_inactive: bool = Query(False, description="Include inactive relationships"),
) -> RelationshipListResponse:
    """Get all relationships for a specific entity.

    Returns relationships where the entity is either source or target.
    This is the primary query for building relationship graphs in the UI.

    Args:
        entity_id: ID of the entity to query.
        entity_type: Optional filter by entity type.
        include_inactive: Whether to include historical relationships.

    Returns:
        List of relationships involving the entity.
    """
    repo = get_repository()

    parsed_entity_type = None
    if entity_type:
        parsed_entity_type = _parse_entity_type(entity_type)

    relationships = await repo.find_by_entity(
        entity_id=entity_id,
        entity_type=parsed_entity_type,
        include_inactive=include_inactive,
    )

    return RelationshipListResponse(
        relationships=[_relationship_to_response(r) for r in relationships],
        total=len(relationships),
    )


@router.get("/{relationship_id}", response_model=RelationshipResponse)
async def get_relationship(relationship_id: str) -> RelationshipResponse:
    """Get a specific relationship by ID.

    Args:
        relationship_id: Unique identifier for the relationship.

    Returns:
        The relationship details.

    Raises:
        HTTPException: If relationship not found.
    """
    repo = get_repository()
    relationship = await repo.get_by_id(relationship_id)

    if not relationship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship not found: {relationship_id}",
        )

    return _relationship_to_response(relationship)


@router.put("/{relationship_id}", response_model=RelationshipResponse)
async def update_relationship(
    relationship_id: str,
    request: RelationshipUpdateRequest,
) -> RelationshipResponse:
    """Update an existing relationship.

    Args:
        relationship_id: Unique identifier for the relationship.
        request: Fields to update.

    Returns:
        The updated relationship.

    Raises:
        HTTPException: If relationship not found or update fails.
    """
    repo = get_repository()
    relationship = await repo.get_by_id(relationship_id)

    if not relationship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship not found: {relationship_id}",
        )

    try:
        if request.relationship_type is not None:
            new_type = _parse_relationship_type(request.relationship_type)
            relationship.change_type(new_type)

        if request.description is not None:
            relationship.update_description(request.description)

        if request.strength is not None:
            relationship.update_strength(request.strength)

        if request.is_active is not None:
            if request.is_active:
                relationship.activate()
            else:
                relationship.deactivate()

        saved = await repo.save(relationship)
        return _relationship_to_response(saved)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{relationship_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_relationship(relationship_id: str) -> None:
    """Delete a relationship.

    Permanently removes the relationship from the knowledge graph.
    Consider using deactivation (via PUT with is_active=false) to
    preserve historical data.

    Args:
        relationship_id: Unique identifier for the relationship.

    Raises:
        HTTPException: If relationship not found.
    """
    repo = get_repository()
    deleted = await repo.delete(relationship_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship not found: {relationship_id}",
        )


@router.get("", response_model=RelationshipListResponse)
async def list_relationships(
    relationship_type: Optional[str] = Query(None, description="Filter by relationship type"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> RelationshipListResponse:
    """List all relationships with optional filtering.

    Args:
        relationship_type: Optional filter by relationship type.
        limit: Maximum number of results.
        offset: Number of results to skip.

    Returns:
        Paginated list of relationships.
    """
    repo = get_repository()

    if relationship_type:
        parsed_type = _parse_relationship_type(relationship_type)
        relationships = await repo.find_by_type(parsed_type, limit=limit, offset=offset)
    else:
        relationships = await repo.get_all(limit=limit, offset=offset)

    return RelationshipListResponse(
        relationships=[_relationship_to_response(r) for r in relationships],
        total=len(relationships),
    )


@router.get("/between/{entity_a_id}/{entity_b_id}", response_model=RelationshipListResponse)
async def get_relationships_between(
    entity_a_id: str,
    entity_b_id: str,
) -> RelationshipListResponse:
    """Get all relationships between two specific entities.

    Checks both directions (A->B and B->A).

    Args:
        entity_a_id: First entity ID.
        entity_b_id: Second entity ID.

    Returns:
        List of relationships connecting the two entities.
    """
    repo = get_repository()
    relationships = await repo.find_between(entity_a_id, entity_b_id)

    return RelationshipListResponse(
        relationships=[_relationship_to_response(r) for r in relationships],
        total=len(relationships),
    )
