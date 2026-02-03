#!/usr/bin/env python3
"""Lore Entry Repository Interface.

This module defines the abstract repository interface for LoreEntry entities.
Following DDD principles, the domain layer defines the contract while the
infrastructure layer provides concrete implementations.

Why a separate LoreEntry repository: Lore entries are frequently searched
by tags and content. A dedicated repository enables efficient full-text
search and tag-based filtering without coupling to other aggregates.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.lore_entry import LoreCategory, LoreEntry


class ILoreEntryRepository(ABC):
    """Abstract repository interface for LoreEntry entities.

    This interface defines the contract for persisting and querying
    LoreEntry entities. The design optimizes for wiki-style knowledge
    lookup and discovery operations.

    Thread Safety:
        Implementations should be thread-safe for concurrent access.
    """

    # Basic CRUD Operations

    @abstractmethod
    async def save(self, entry: LoreEntry) -> LoreEntry:
        """Save a LoreEntry to persistent storage.

        Handles both create and update operations based on whether
        the entry already exists.

        Args:
            entry: The LoreEntry to save.

        Returns:
            The saved LoreEntry (may include generated IDs).

        Raises:
            RepositoryException: If save operation fails.
        """

    @abstractmethod
    async def get_by_id(self, entry_id: str) -> Optional[LoreEntry]:
        """Retrieve a LoreEntry by its unique identifier.

        Args:
            entry_id: Unique identifier for the entry.

        Returns:
            LoreEntry if found, None otherwise.
        """

    @abstractmethod
    async def delete(self, entry_id: str) -> bool:
        """Delete a LoreEntry from persistent storage.

        Args:
            entry_id: Unique identifier for the entry.

        Returns:
            True if deletion was successful, False if not found.
        """

    @abstractmethod
    async def exists(self, entry_id: str) -> bool:
        """Check if a LoreEntry exists in storage.

        Args:
            entry_id: Unique identifier for the entry.

        Returns:
            True if entry exists, False otherwise.
        """

    # Category-based Queries

    @abstractmethod
    async def find_by_category(
        self,
        category: LoreCategory,
        limit: int = 100,
        offset: int = 0,
    ) -> List[LoreEntry]:
        """Find entries by category.

        Args:
            category: Category to filter by.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of LoreEntry instances matching the category.
        """

    # Tag-based Queries

    @abstractmethod
    async def find_by_tag(
        self,
        tag: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[LoreEntry]:
        """Find entries containing a specific tag.

        Args:
            tag: Tag to search for (case-insensitive).
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of LoreEntry instances with the tag.
        """

    @abstractmethod
    async def find_by_tags(
        self,
        tags: List[str],
        match_all: bool = False,
        limit: int = 100,
    ) -> List[LoreEntry]:
        """Find entries matching multiple tags.

        Args:
            tags: Tags to search for.
            match_all: If True, entry must have ALL tags. If False, ANY tag.
            limit: Maximum number of results.

        Returns:
            List of matching LoreEntry instances.
        """

    # Search Queries

    @abstractmethod
    async def search(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        category: Optional[LoreCategory] = None,
        limit: int = 50,
    ) -> List[LoreEntry]:
        """Search entries by title and optionally filter by tags/category.

        This is the primary search endpoint that combines text search
        with tag and category filtering.

        Args:
            query: Search query string (matches title, case-insensitive).
            tags: Optional tags to filter results.
            category: Optional category to filter results.
            limit: Maximum number of results.

        Returns:
            List of matching LoreEntry instances.
        """

    # Utility Methods

    @abstractmethod
    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[LoreEntry]:
        """Get all entries with pagination.

        Args:
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of LoreEntry instances.
        """

    @abstractmethod
    async def count_all(self) -> int:
        """Get total count of lore entries.

        Returns:
            Total number of entries in storage.
        """

    @abstractmethod
    async def get_all_tags(self) -> List[str]:
        """Get all unique tags across all entries.

        Useful for building tag clouds and autocomplete.

        Returns:
            Sorted list of unique tags.
        """


class LoreEntryRepositoryException(Exception):
    """Base exception for lore entry repository operations."""


class LoreEntryNotFoundException(LoreEntryRepositoryException):
    """Raised when a requested lore entry is not found."""

    def __init__(self, entry_id: str):
        super().__init__(f"Lore entry not found: {entry_id}")
        self.entry_id = entry_id


class DuplicateLoreEntryException(LoreEntryRepositoryException):
    """Raised when attempting to create a duplicate lore entry."""

    def __init__(self, entry_id: str, title: str):
        super().__init__(f"Lore entry already exists: {entry_id} ({title})")
        self.entry_id = entry_id
        self.title = title
