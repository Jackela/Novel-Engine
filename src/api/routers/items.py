"""Items API router.

This module provides CRUD endpoints for the Item entity and inventory
management operations for characters.

Endpoints:
    POST /api/items - Create a new item
    GET /api/items - List all items with filtering
    GET /api/items/{item_id} - Get a specific item
    PUT /api/items/{item_id} - Update an item
    DELETE /api/items/{item_id} - Delete an item
"""

from __future__ import annotations

from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Query, status

from src.api.schemas import (
    GiveItemRequest,
    ItemCreateRequest,
    ItemListResponse,
    ItemResponse,
    ItemUpdateRequest,
    RemoveItemResponse,
)
from src.contexts.world.domain.entities.item import Item, ItemRarity, ItemType
from src.contexts.world.infrastructure.persistence.in_memory_item_repository import (
    InMemoryItemRepository,
)

router = APIRouter(prefix="/items", tags=["items"])

# Separate router for character inventory endpoints
# These need to be registered with /characters prefix
character_inventory_router = APIRouter(tags=["characters", "items"])

# Global repository instance (would be injected via DI in production)
_repository: Optional[InMemoryItemRepository] = None


def get_repository() -> InMemoryItemRepository:
    """Get or create the repository singleton.

    Why singleton pattern here: Enables shared state during development
    and testing without a database. In production, this would be replaced
    with dependency injection of a PostgreSQL-backed repository.
    """
    global _repository
    if _repository is None:
        _repository = InMemoryItemRepository()
    return _repository


def _parse_item_type(value: str) -> ItemType:
    """Parse string to ItemType enum.

    Args:
        value: Item type string (case-insensitive).

    Returns:
        Parsed ItemType.

    Raises:
        HTTPException: If value is not a valid item type.
    """
    try:
        return ItemType(value.lower())
    except ValueError:
        valid_types = [t.value for t in ItemType]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid item type: {value}. Valid types: {valid_types}",
        )


def _parse_rarity(value: str) -> ItemRarity:
    """Parse string to ItemRarity enum.

    Args:
        value: Rarity string (case-insensitive).

    Returns:
        Parsed ItemRarity.

    Raises:
        HTTPException: If value is not a valid rarity.
    """
    try:
        return ItemRarity(value.lower())
    except ValueError:
        valid_rarities = [r.value for r in ItemRarity]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid rarity: {value}. Valid rarities: {valid_rarities}",
        )


def _item_to_response(item: Item) -> ItemResponse:
    """Convert domain Item to API response model."""
    return ItemResponse(
        id=item.id,
        name=item.name,
        item_type=item.item_type.value,
        description=item.description,
        rarity=item.rarity.value,
        weight=item.weight,
        value=item.value,
        is_equippable=item.is_equippable,
        is_consumable=item.is_consumable,
        effects=item.effects.copy(),
        lore=item.lore,
        created_at=item.created_at.isoformat(),
        updated_at=item.updated_at.isoformat(),
    )


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(request: ItemCreateRequest) -> ItemResponse:
    """Create a new item.

    Args:
        request: Item creation request.

    Returns:
        The created item.

    Raises:
        HTTPException: If validation fails.
    """
    repo = get_repository()

    item_type = _parse_item_type(request.item_type)
    rarity = _parse_rarity(request.rarity)

    try:
        item = Item(
            name=request.name,
            item_type=item_type,
            description=request.description,
            rarity=rarity,
            weight=request.weight,
            value=request.value,
            is_equippable=request.is_equippable,
            is_consumable=request.is_consumable,
            effects=request.effects.copy(),
            lore=request.lore,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    saved = await repo.save(item)
    return _item_to_response(saved)


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(item_id: str) -> ItemResponse:
    """Get a specific item by ID.

    Args:
        item_id: Unique identifier for the item.

    Returns:
        The item details.

    Raises:
        HTTPException: If item not found.
    """
    repo = get_repository()
    item = await repo.get_by_id(item_id)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item not found: {item_id}",
        )

    return _item_to_response(item)


@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: str,
    request: ItemUpdateRequest,
) -> ItemResponse:
    """Update an existing item.

    Args:
        item_id: Unique identifier for the item.
        request: Fields to update.

    Returns:
        The updated item.

    Raises:
        HTTPException: If item not found or update fails.
    """
    repo = get_repository()
    item = await repo.get_by_id(item_id)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item not found: {item_id}",
        )

    try:
        if request.name is not None:
            item.update_name(request.name)

        if request.description is not None:
            item.update_description(request.description)

        if request.rarity is not None:
            new_rarity = _parse_rarity(request.rarity)
            item.set_rarity(new_rarity)

        if request.weight is not None:
            item.weight = request.weight
            item.touch()

        if request.value is not None:
            item.value = request.value
            item.touch()

        if request.effects is not None:
            item.effects = request.effects.copy()
            item.touch()

        if request.lore is not None:
            item.update_lore(request.lore)

        saved = await repo.save(item)
        return _item_to_response(saved)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: str) -> None:
    """Delete an item.

    Args:
        item_id: Unique identifier for the item.

    Raises:
        HTTPException: If item not found.
    """
    repo = get_repository()
    deleted = await repo.delete(item_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item not found: {item_id}",
        )


@router.get("", response_model=ItemListResponse)
async def list_items(
    item_type: Optional[str] = Query(None, description="Filter by item type"),
    rarity: Optional[str] = Query(None, description="Filter by rarity"),
    search: Optional[str] = Query(None, description="Search by name"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> ItemListResponse:
    """List all items with optional filtering.

    Args:
        item_type: Optional filter by item type.
        rarity: Optional filter by rarity.
        search: Optional search query for name.
        limit: Maximum number of results.
        offset: Number of results to skip.

    Returns:
        Paginated list of items.
    """
    repo = get_repository()

    if search:
        items = await repo.search_by_name(search, limit=limit)
    elif item_type:
        parsed_type = _parse_item_type(item_type)
        items = await repo.find_by_type(parsed_type, limit=limit, offset=offset)
    elif rarity:
        parsed_rarity = _parse_rarity(rarity)
        items = await repo.find_by_rarity(parsed_rarity, limit=limit, offset=offset)
    else:
        items = await repo.get_all(limit=limit, offset=offset)

    return ItemListResponse(
        items=[_item_to_response(item) for item in items],
        total=len(items),
    )


# === Character Inventory Endpoints ===
# These track which items are assigned to characters using an in-memory store.
# In production, this would integrate with a character repository.

_character_inventories: Dict[str, list] = {}


@character_inventory_router.post(
    "/characters/{character_id}/give-item",
    response_model=RemoveItemResponse,
    status_code=status.HTTP_200_OK,
)
async def give_item_to_character(
    character_id: str,
    request: GiveItemRequest,
) -> RemoveItemResponse:
    """Give an item to a character.

    Adds the item to the character's inventory. The item must exist
    in the items repository.

    Args:
        character_id: ID of the character.
        request: Contains the item_id to give.

    Returns:
        Success status and message.

    Raises:
        HTTPException: If item not found or already in inventory.
    """
    repo = get_repository()

    # Verify item exists
    item = await repo.get_by_id(request.item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item not found: {request.item_id}",
        )

    # Get or create character inventory
    if character_id not in _character_inventories:
        _character_inventories[character_id] = []

    inventory = _character_inventories[character_id]

    # Check if already in inventory
    if request.item_id in inventory:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Item {request.item_id} is already in character's inventory",
        )

    inventory.append(request.item_id)

    return RemoveItemResponse(
        success=True,
        message=f"Item '{item.name}' added to character {character_id}'s inventory",
    )


@character_inventory_router.delete(
    "/characters/{character_id}/remove-item/{item_id}",
    response_model=RemoveItemResponse,
)
async def remove_item_from_character(
    character_id: str,
    item_id: str,
) -> RemoveItemResponse:
    """Remove an item from a character's inventory.

    Args:
        character_id: ID of the character.
        item_id: ID of the item to remove.

    Returns:
        Success status and message.
    """
    if character_id not in _character_inventories:
        return RemoveItemResponse(
            success=False,
            message=f"Character {character_id} has no inventory",
        )

    inventory = _character_inventories[character_id]

    if item_id not in inventory:
        return RemoveItemResponse(
            success=False,
            message=f"Item {item_id} not in character's inventory",
        )

    inventory.remove(item_id)

    return RemoveItemResponse(
        success=True,
        message=f"Item {item_id} removed from character {character_id}'s inventory",
    )


@character_inventory_router.get(
    "/characters/{character_id}/inventory",
    response_model=ItemListResponse,
)
async def get_character_inventory(
    character_id: str,
) -> ItemListResponse:
    """Get all items in a character's inventory.

    Args:
        character_id: ID of the character.

    Returns:
        List of items in the character's inventory.
    """
    repo = get_repository()

    if character_id not in _character_inventories:
        return ItemListResponse(items=[], total=0)

    inventory = _character_inventories[character_id]
    items = await repo.get_by_ids(inventory)

    return ItemListResponse(
        items=[_item_to_response(item) for item in items],
        total=len(items),
    )
