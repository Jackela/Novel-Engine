"""World Rules API router.

This module provides CRUD endpoints for the WorldRule entity,
enabling management of world laws, magic systems, and physics constraints.

Endpoints:
    POST /api/world-rules - Create a new world rule
    GET /api/world-rules - List all world rules with filtering
    GET /api/world-rules/search - Search rules by name/category
    GET /api/world-rules/{rule_id} - Get a specific rule
    PUT /api/world-rules/{rule_id} - Update a rule
    DELETE /api/world-rules/{rule_id} - Delete a rule
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from src.api.schemas import (
    WorldRuleCreateRequest,
    WorldRuleListResponse,
    WorldRuleResponse,
    WorldRuleUpdateRequest,
)
from src.contexts.world.domain.entities.world_rule import WorldRule
from src.contexts.world.infrastructure.persistence.in_memory_world_rule_repository import (
    InMemoryWorldRuleRepository,
)

router = APIRouter(prefix="/world-rules", tags=["world-rules"])

# Global repository instance (would be injected via DI in production)
_repository: Optional[InMemoryWorldRuleRepository] = None


def get_repository() -> InMemoryWorldRuleRepository:
    """Get or create the repository singleton.

    Why singleton pattern here: Enables shared state during development
    and testing without a database. In production, this would be replaced
    with dependency injection of a PostgreSQL-backed repository.
    """
    global _repository
    if _repository is None:
        _repository = InMemoryWorldRuleRepository()
    return _repository


def _rule_to_response(rule: WorldRule) -> WorldRuleResponse:
    """Convert domain WorldRule to API response model."""
    return WorldRuleResponse(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        consequence=rule.consequence,
        exceptions=rule.exceptions.copy(),
        category=rule.category,
        severity=rule.severity,
        related_rule_ids=rule.related_rule_ids.copy(),
        created_at=rule.created_at.isoformat(),
        updated_at=rule.updated_at.isoformat(),
    )


# === Static Routes (must be defined before parameterized routes) ===


@router.post("", response_model=WorldRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_world_rule(request: WorldRuleCreateRequest) -> WorldRuleResponse:
    """Create a new world rule.

    Args:
        request: World rule creation request.

    Returns:
        The created world rule.

    Raises:
        HTTPException: If validation fails.
    """
    repo = get_repository()

    try:
        rule = WorldRule(
            name=request.name,
            description=request.description,
            consequence=request.consequence,
            exceptions=request.exceptions.copy(),
            category=request.category,
            severity=request.severity,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    saved = await repo.save(rule)
    return _rule_to_response(saved)


@router.get("", response_model=WorldRuleListResponse)
async def list_world_rules(
    category: Optional[str] = Query(None, description="Filter by category"),
    min_severity: Optional[int] = Query(None, ge=0, le=100, description="Minimum severity"),
    max_severity: Optional[int] = Query(None, ge=0, le=100, description="Maximum severity"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> WorldRuleListResponse:
    """List all world rules with optional filtering.

    Args:
        category: Optional filter by category.
        min_severity: Optional minimum severity filter.
        max_severity: Optional maximum severity filter.
        limit: Maximum number of results.
        offset: Number of results to skip.

    Returns:
        Paginated list of world rules.
    """
    repo = get_repository()

    if category:
        rules = await repo.find_by_category(category, limit=limit, offset=offset)
    elif min_severity is not None or max_severity is not None:
        rules = await repo.find_by_severity_range(
            min_severity=min_severity or 0,
            max_severity=max_severity or 100,
            limit=limit,
        )
        rules = rules[offset:] if offset > 0 else rules
    else:
        rules = await repo.get_all(limit=limit, offset=offset)

    return WorldRuleListResponse(
        rules=[_rule_to_response(rule) for rule in rules],
        total=len(rules),
    )


@router.get("/search", response_model=WorldRuleListResponse)
async def search_world_rules(
    q: str = Query("", description="Search query (matches name)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=200),
) -> WorldRuleListResponse:
    """Search world rules by name and optionally filter by category.

    This is the primary search endpoint combining text search with filtering.

    Args:
        q: Search query string (case-insensitive name match).
        category: Optional category filter.
        limit: Maximum number of results.

    Returns:
        List of matching world rules.
    """
    repo = get_repository()

    rules = await repo.search(
        query=q,
        category=category,
        limit=limit,
    )

    return WorldRuleListResponse(
        rules=[_rule_to_response(rule) for rule in rules],
        total=len(rules),
    )


@router.get("/absolute", response_model=WorldRuleListResponse)
async def list_absolute_rules(
    limit: int = Query(100, ge=1, le=500),
) -> WorldRuleListResponse:
    """List all absolute rules (severity >= 90).

    These are the unbreakable laws of the world.

    Args:
        limit: Maximum number of results.

    Returns:
        List of absolute world rules.
    """
    repo = get_repository()
    rules = await repo.find_absolute_rules(limit=limit)

    return WorldRuleListResponse(
        rules=[_rule_to_response(rule) for rule in rules],
        total=len(rules),
    )


# === Parameterized Routes (must be defined after static routes) ===


@router.get("/{rule_id}", response_model=WorldRuleResponse)
async def get_world_rule(rule_id: str) -> WorldRuleResponse:
    """Get a specific world rule by ID.

    Args:
        rule_id: Unique identifier for the rule.

    Returns:
        The world rule details.

    Raises:
        HTTPException: If rule not found.
    """
    repo = get_repository()
    rule = await repo.get_by_id(rule_id)

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"World rule not found: {rule_id}",
        )

    return _rule_to_response(rule)


@router.put("/{rule_id}", response_model=WorldRuleResponse)
async def update_world_rule(
    rule_id: str,
    request: WorldRuleUpdateRequest,
) -> WorldRuleResponse:
    """Update an existing world rule.

    Args:
        rule_id: Unique identifier for the rule.
        request: Fields to update.

    Returns:
        The updated world rule.

    Raises:
        HTTPException: If rule not found or update fails.
    """
    repo = get_repository()
    rule = await repo.get_by_id(rule_id)

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"World rule not found: {rule_id}",
        )

    try:
        if request.name is not None:
            rule.update_name(request.name)

        if request.description is not None:
            rule.update_description(request.description)

        if request.consequence is not None:
            rule.update_consequence(request.consequence)

        if request.category is not None:
            rule.set_category(request.category)

        if request.severity is not None:
            rule.set_severity(request.severity)

        if request.exceptions is not None:
            # Replace all exceptions
            rule.exceptions = [e.strip() for e in request.exceptions if e.strip()]
            rule.touch()

        saved = await repo.save(rule)
        return _rule_to_response(saved)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_world_rule(rule_id: str) -> None:
    """Delete a world rule.

    Args:
        rule_id: Unique identifier for the rule.

    Raises:
        HTTPException: If rule not found.
    """
    repo = get_repository()
    deleted = await repo.delete(rule_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"World rule not found: {rule_id}",
        )
