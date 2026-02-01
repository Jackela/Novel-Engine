"""Lore API router.

This module provides CRUD and search endpoints for the LoreEntry entity,
enabling wiki-style knowledge management for world-building.

Endpoints:
    POST /api/lore - Create a new lore entry
    GET /api/lore - List all lore entries with filtering
    GET /api/lore/search - Search entries by title/tags/category
    GET /api/lore/{entry_id} - Get a specific entry
    PUT /api/lore/{entry_id} - Update an entry
    DELETE /api/lore/{entry_id} - Delete an entry
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from src.api.schemas import (
    LoreEntryCreateRequest,
    LoreEntryListResponse,
    LoreEntryResponse,
    LoreEntryUpdateRequest,
)
from src.contexts.world.domain.entities.lore_entry import LoreCategory, LoreEntry
from src.contexts.world.infrastructure.persistence.in_memory_lore_entry_repository import (
    InMemoryLoreEntryRepository,
)

router = APIRouter(prefix="/lore", tags=["lore"])

# Global repository instance (would be injected via DI in production)
_repository: Optional[InMemoryLoreEntryRepository] = None


def get_repository() -> InMemoryLoreEntryRepository:
    """Get or create the repository singleton.

    Why singleton pattern here: Enables shared state during development
    and testing without a database. In production, this would be replaced
    with dependency injection of a PostgreSQL-backed repository.
    """
    global _repository
    if _repository is None:
        _repository = InMemoryLoreEntryRepository()
    return _repository


def _parse_category(value: str) -> LoreCategory:
    """Parse string to LoreCategory enum.

    Args:
        value: Category string (case-insensitive).

    Returns:
        Parsed LoreCategory.

    Raises:
        HTTPException: If value is not a valid category.
    """
    try:
        return LoreCategory(value.lower())
    except ValueError:
        valid_categories = [c.value for c in LoreCategory]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category: {value}. Valid categories: {valid_categories}",
        )


def _entry_to_response(entry: LoreEntry) -> LoreEntryResponse:
    """Convert domain LoreEntry to API response model."""
    return LoreEntryResponse(
        id=entry.id,
        title=entry.title,
        content=entry.content,
        tags=entry.tags.copy(),
        category=entry.category.value,
        summary=entry.summary,
        related_entry_ids=entry.related_entry_ids.copy(),
        created_at=entry.created_at.isoformat(),
        updated_at=entry.updated_at.isoformat(),
    )


# === Static Routes (must be defined before parameterized routes) ===


@router.post("", response_model=LoreEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_lore_entry(request: LoreEntryCreateRequest) -> LoreEntryResponse:
    """Create a new lore entry.

    Args:
        request: Lore entry creation request.

    Returns:
        The created lore entry.

    Raises:
        HTTPException: If validation fails.
    """
    repo = get_repository()

    category = _parse_category(request.category)

    try:
        entry = LoreEntry(
            title=request.title,
            content=request.content,
            tags=request.tags.copy(),
            category=category,
            summary=request.summary,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    saved = await repo.save(entry)
    return _entry_to_response(saved)


@router.get("", response_model=LoreEntryListResponse)
async def list_lore_entries(
    category: Optional[str] = Query(None, description="Filter by category"),
    tag: Optional[str] = Query(None, description="Filter by single tag"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> LoreEntryListResponse:
    """List all lore entries with optional filtering.

    Args:
        category: Optional filter by category.
        tag: Optional filter by a single tag.
        limit: Maximum number of results.
        offset: Number of results to skip.

    Returns:
        Paginated list of lore entries.
    """
    repo = get_repository()

    if tag:
        entries = await repo.find_by_tag(tag, limit=limit, offset=offset)
    elif category:
        parsed_category = _parse_category(category)
        entries = await repo.find_by_category(parsed_category, limit=limit, offset=offset)
    else:
        entries = await repo.get_all(limit=limit, offset=offset)

    return LoreEntryListResponse(
        entries=[_entry_to_response(entry) for entry in entries],
        total=len(entries),
    )


@router.get("/search", response_model=LoreEntryListResponse)
async def search_lore_entries(
    q: str = Query("", description="Search query (matches title)"),
    tags: Optional[str] = Query(None, description="Comma-separated tags to filter by"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=200),
) -> LoreEntryListResponse:
    """Search lore entries by title and optionally filter by tags/category.

    This is the primary search endpoint combining text search with filtering.

    Args:
        q: Search query string (case-insensitive title match).
        tags: Comma-separated list of tags to filter by (any match).
        category: Optional category filter.
        limit: Maximum number of results.

    Returns:
        List of matching lore entries.
    """
    repo = get_repository()

    # Parse tags from comma-separated string
    tag_list = None
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    # Parse category
    parsed_category = None
    if category:
        parsed_category = _parse_category(category)

    entries = await repo.search(
        query=q,
        tags=tag_list,
        category=parsed_category,
        limit=limit,
    )

    return LoreEntryListResponse(
        entries=[_entry_to_response(entry) for entry in entries],
        total=len(entries),
    )


# === Parameterized Routes (must be defined after static routes) ===


@router.get("/{entry_id}", response_model=LoreEntryResponse)
async def get_lore_entry(entry_id: str) -> LoreEntryResponse:
    """Get a specific lore entry by ID.

    Args:
        entry_id: Unique identifier for the entry.

    Returns:
        The lore entry details.

    Raises:
        HTTPException: If entry not found.
    """
    repo = get_repository()
    entry = await repo.get_by_id(entry_id)

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lore entry not found: {entry_id}",
        )

    return _entry_to_response(entry)


@router.put("/{entry_id}", response_model=LoreEntryResponse)
async def update_lore_entry(
    entry_id: str,
    request: LoreEntryUpdateRequest,
) -> LoreEntryResponse:
    """Update an existing lore entry.

    Args:
        entry_id: Unique identifier for the entry.
        request: Fields to update.

    Returns:
        The updated lore entry.

    Raises:
        HTTPException: If entry not found or update fails.
    """
    repo = get_repository()
    entry = await repo.get_by_id(entry_id)

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lore entry not found: {entry_id}",
        )

    try:
        if request.title is not None:
            entry.update_title(request.title)

        if request.content is not None:
            entry.update_content(request.content)

        if request.summary is not None:
            entry.update_summary(request.summary)

        if request.category is not None:
            new_category = _parse_category(request.category)
            entry.set_category(new_category)

        if request.tags is not None:
            # Replace all tags
            entry.tags = [t.strip().lower() for t in request.tags if t.strip()]
            entry.touch()

        saved = await repo.save(entry)
        return _entry_to_response(saved)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lore_entry(entry_id: str) -> None:
    """Delete a lore entry.

    Args:
        entry_id: Unique identifier for the entry.

    Raises:
        HTTPException: If entry not found.
    """
    repo = get_repository()
    deleted = await repo.delete(entry_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lore entry not found: {entry_id}",
        )
