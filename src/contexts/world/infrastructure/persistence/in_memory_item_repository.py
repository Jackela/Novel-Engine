#!/usr/bin/env python3
"""In-Memory Item Repository Implementation.

This module provides an in-memory implementation of IItemRepository
suitable for testing, development, and lightweight deployments.

Why in-memory first: Enables rapid iteration and testing without database
setup. The repository interface ensures we can swap to PostgreSQL later
without changing domain or application code.
"""

from typing import Dict, List, Optional

from src.contexts.world.domain.entities.item import Item, ItemRarity, ItemType
from src.contexts.world.domain.repositories.item_repository import IItemRepository


class InMemoryItemRepository(IItemRepository):
    """In-memory implementation of IItemRepository.

    Stores items in a dictionary indexed by ID, with additional
    indexes for efficient type and rarity-based lookups.

    Thread Safety:
        This implementation is NOT thread-safe. For concurrent access,
        use locking or switch to a thread-safe implementation.
    """

    def __init__(self) -> None:
        """Initialize the repository with empty storage."""
        self._items: Dict[str, Item] = {}
        # Index: item_type -> set of item_ids
        self._type_index: Dict[ItemType, set] = {}
        # Index: rarity -> set of item_ids
        self._rarity_index: Dict[ItemRarity, set] = {}

    def _index_item(self, item: Item) -> None:
        """Add item to type and rarity indexes.

        Args:
            item: The item to index.
        """
        # Type index
        if item.item_type not in self._type_index:
            self._type_index[item.item_type] = set()
        self._type_index[item.item_type].add(item.id)

        # Rarity index
        if item.rarity not in self._rarity_index:
            self._rarity_index[item.rarity] = set()
        self._rarity_index[item.rarity].add(item.id)

    def _unindex_item(self, item: Item) -> None:
        """Remove item from type and rarity indexes.

        Args:
            item: The item to unindex.
        """
        # Type index
        if item.item_type in self._type_index:
            self._type_index[item.item_type].discard(item.id)
            if not self._type_index[item.item_type]:
                del self._type_index[item.item_type]

        # Rarity index
        if item.rarity in self._rarity_index:
            self._rarity_index[item.rarity].discard(item.id)
            if not self._rarity_index[item.rarity]:
                del self._rarity_index[item.rarity]

    async def save(self, item: Item) -> Item:
        """Save an Item to storage.

        Args:
            item: The Item to save.

        Returns:
            The saved Item.
        """
        existing = self._items.get(item.id)
        if existing:
            # Update: unindex old, index new
            self._unindex_item(existing)

        self._items[item.id] = item
        self._index_item(item)
        return item

    async def get_by_id(self, item_id: str) -> Optional[Item]:
        """Retrieve an Item by ID.

        Args:
            item_id: Unique identifier.

        Returns:
            Item if found, None otherwise.
        """
        return self._items.get(item_id)

    async def delete(self, item_id: str) -> bool:
        """Delete an Item.

        Args:
            item_id: Unique identifier.

        Returns:
            True if deleted, False if not found.
        """
        item = self._items.get(item_id)
        if item:
            self._unindex_item(item)
            del self._items[item_id]
            return True
        return False

    async def exists(self, item_id: str) -> bool:
        """Check if an Item exists.

        Args:
            item_id: Unique identifier.

        Returns:
            True if exists.
        """
        return item_id in self._items

    async def get_by_ids(self, item_ids: List[str]) -> List[Item]:
        """Retrieve multiple items by their IDs.

        Args:
            item_ids: List of item IDs.

        Returns:
            List of found Items.
        """
        results = []
        for item_id in item_ids:
            item = self._items.get(item_id)
            if item:
                results.append(item)
        return results

    async def find_by_type(
        self,
        item_type: ItemType,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Item]:
        """Find items by type.

        Args:
            item_type: Type to filter by.
            limit: Maximum results.
            offset: Results to skip.

        Returns:
            List of matching Items.
        """
        item_ids = self._type_index.get(item_type, set())
        items = [self._items[item_id] for item_id in item_ids if item_id in self._items]
        return items[offset : offset + limit]

    async def find_by_rarity(
        self,
        rarity: ItemRarity,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Item]:
        """Find items by rarity.

        Args:
            rarity: Rarity to filter by.
            limit: Maximum results.
            offset: Results to skip.

        Returns:
            List of matching Items.
        """
        item_ids = self._rarity_index.get(rarity, set())
        items = [self._items[item_id] for item_id in item_ids if item_id in self._items]
        return items[offset : offset + limit]

    async def search_by_name(
        self,
        query: str,
        limit: int = 50,
    ) -> List[Item]:
        """Search items by name.

        Args:
            query: Search query string.
            limit: Maximum results.

        Returns:
            List of matching Items.
        """
        query_lower = query.lower()
        results = []
        for item in self._items.values():
            if query_lower in item.name.lower():
                results.append(item)
                if len(results) >= limit:
                    break
        return results

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Item]:
        """Get all items with pagination.

        Args:
            limit: Maximum results.
            offset: Results to skip.

        Returns:
            List of Items.
        """
        all_items = list(self._items.values())
        return all_items[offset : offset + limit]

    async def count_all(self) -> int:
        """Get total count of items."""
        return len(self._items)

    # Utility methods for testing

    def clear(self) -> None:
        """Clear all data from the repository."""
        self._items.clear()
        self._type_index.clear()
        self._rarity_index.clear()
