#!/usr/bin/env python3
"""Item Repository Interface.

This module defines the abstract repository interface for Item entities.
Following DDD principles, the domain layer defines the contract while the
infrastructure layer provides concrete implementations.

Why a separate Item repository: Items are frequently queried entities that
benefit from optimized lookups by type, rarity, and owner. A dedicated
repository enables efficient queries without coupling to other aggregates.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.item import Item, ItemRarity, ItemType


class IItemRepository(ABC):
    """Abstract repository interface for Item entities.

    This interface defines the contract for persisting and querying
    Item entities. The design optimizes for inventory management
    and item discovery operations common in narrative applications.

    Thread Safety:
        Implementations should be thread-safe for concurrent access.
    """

    # Basic CRUD Operations

    @abstractmethod
    async def save(self, item: Item) -> Item:
        """Save an Item to persistent storage.

        Handles both create and update operations based on whether
        the item already exists.

        Args:
            item: The Item to save.

        Returns:
            The saved Item (may include generated IDs).

        Raises:
            RepositoryException: If save operation fails.
        """

    @abstractmethod
    async def get_by_id(self, item_id: str) -> Optional[Item]:
        """Retrieve an Item by its unique identifier.

        Args:
            item_id: Unique identifier for the item.

        Returns:
            Item if found, None otherwise.
        """

    @abstractmethod
    async def delete(self, item_id: str) -> bool:
        """Delete an Item from persistent storage.

        Args:
            item_id: Unique identifier for the item.

        Returns:
            True if deletion was successful, False if not found.
        """

    @abstractmethod
    async def exists(self, item_id: str) -> bool:
        """Check if an Item exists in storage.

        Args:
            item_id: Unique identifier for the item.

        Returns:
            True if item exists, False otherwise.
        """

    # Bulk Operations

    @abstractmethod
    async def get_by_ids(self, item_ids: List[str]) -> List[Item]:
        """Retrieve multiple items by their IDs.

        Useful for loading a character's entire inventory at once.

        Args:
            item_ids: List of item IDs to retrieve.

        Returns:
            List of found Items (missing IDs are silently skipped).
        """

    # Type-based Queries

    @abstractmethod
    async def find_by_type(
        self,
        item_type: ItemType,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Item]:
        """Find items by type.

        Args:
            item_type: Type of items to find.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of Items of the specified type.
        """

    @abstractmethod
    async def find_by_rarity(
        self,
        rarity: ItemRarity,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Item]:
        """Find items by rarity.

        Args:
            rarity: Rarity level to filter by.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of Items of the specified rarity.
        """

    # Search Queries

    @abstractmethod
    async def search_by_name(
        self,
        query: str,
        limit: int = 50,
    ) -> List[Item]:
        """Search items by name (case-insensitive partial match).

        Args:
            query: Search query string.
            limit: Maximum number of results.

        Returns:
            List of matching Items.
        """

    # Utility Methods

    @abstractmethod
    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Item]:
        """Get all items with pagination.

        Args:
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of Items.
        """

    @abstractmethod
    async def count_all(self) -> int:
        """Get total count of items.

        Returns:
            Total number of items in storage.
        """


class ItemRepositoryException(Exception):
    """Base exception for item repository operations."""


class ItemNotFoundException(ItemRepositoryException):
    """Raised when a requested item is not found."""

    def __init__(self, item_id: str):
        super().__init__(f"Item not found: {item_id}")
        self.item_id = item_id


class DuplicateItemException(ItemRepositoryException):
    """Raised when attempting to create a duplicate item."""

    def __init__(self, item_id: str, name: str):
        super().__init__(f"Item already exists: {item_id} ({name})")
        self.item_id = item_id
        self.name = name
