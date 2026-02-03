#!/usr/bin/env python3
"""In-Memory Lore Entry Repository Implementation.

This module provides an in-memory implementation of ILoreEntryRepository
suitable for testing, development, and lightweight deployments.

Why in-memory first: Enables rapid iteration and testing without database
setup. The repository interface ensures we can swap to PostgreSQL later
without changing domain or application code.
"""

from typing import Dict, List, Optional, Set

from src.contexts.world.domain.entities.lore_entry import LoreCategory, LoreEntry
from src.contexts.world.domain.repositories.lore_entry_repository import (
    ILoreEntryRepository,
)


class InMemoryLoreEntryRepository(ILoreEntryRepository):
    """In-memory implementation of ILoreEntryRepository.

    Stores lore entries in a dictionary indexed by ID, with additional
    indexes for efficient category and tag-based lookups.

    Thread Safety:
        This implementation is NOT thread-safe. For concurrent access,
        use locking or switch to a thread-safe implementation.
    """

    def __init__(self) -> None:
        """Initialize the repository with empty storage."""
        self._entries: Dict[str, LoreEntry] = {}
        # Index: category -> set of entry_ids
        self._category_index: Dict[LoreCategory, Set[str]] = {}
        # Index: tag (lowercase) -> set of entry_ids
        self._tag_index: Dict[str, Set[str]] = {}

    def _index_entry(self, entry: LoreEntry) -> None:
        """Add entry to category and tag indexes.

        Args:
            entry: The entry to index.
        """
        # Category index
        if entry.category not in self._category_index:
            self._category_index[entry.category] = set()
        self._category_index[entry.category].add(entry.id)

        # Tag index
        for tag in entry.tags:
            tag_lower = tag.lower()
            if tag_lower not in self._tag_index:
                self._tag_index[tag_lower] = set()
            self._tag_index[tag_lower].add(entry.id)

    def _unindex_entry(self, entry: LoreEntry) -> None:
        """Remove entry from category and tag indexes.

        Args:
            entry: The entry to unindex.
        """
        # Category index
        if entry.category in self._category_index:
            self._category_index[entry.category].discard(entry.id)
            if not self._category_index[entry.category]:
                del self._category_index[entry.category]

        # Tag index
        for tag in entry.tags:
            tag_lower = tag.lower()
            if tag_lower in self._tag_index:
                self._tag_index[tag_lower].discard(entry.id)
                if not self._tag_index[tag_lower]:
                    del self._tag_index[tag_lower]

    async def save(self, entry: LoreEntry) -> LoreEntry:
        """Save a LoreEntry to storage.

        Args:
            entry: The LoreEntry to save.

        Returns:
            The saved LoreEntry.
        """
        existing = self._entries.get(entry.id)
        if existing:
            # Update: unindex old, index new
            self._unindex_entry(existing)

        self._entries[entry.id] = entry
        self._index_entry(entry)
        return entry

    async def get_by_id(self, entry_id: str) -> Optional[LoreEntry]:
        """Retrieve a LoreEntry by ID.

        Args:
            entry_id: Unique identifier.

        Returns:
            LoreEntry if found, None otherwise.
        """
        return self._entries.get(entry_id)

    async def delete(self, entry_id: str) -> bool:
        """Delete a LoreEntry.

        Args:
            entry_id: Unique identifier.

        Returns:
            True if deleted, False if not found.
        """
        entry = self._entries.get(entry_id)
        if entry:
            self._unindex_entry(entry)
            del self._entries[entry_id]
            return True
        return False

    async def exists(self, entry_id: str) -> bool:
        """Check if a LoreEntry exists.

        Args:
            entry_id: Unique identifier.

        Returns:
            True if exists.
        """
        return entry_id in self._entries

    async def find_by_category(
        self,
        category: LoreCategory,
        limit: int = 100,
        offset: int = 0,
    ) -> List[LoreEntry]:
        """Find entries by category.

        Args:
            category: Category to filter by.
            limit: Maximum results.
            offset: Results to skip.

        Returns:
            List of matching LoreEntry instances.
        """
        entry_ids = self._category_index.get(category, set())
        entries = [
            self._entries[entry_id]
            for entry_id in entry_ids
            if entry_id in self._entries
        ]
        # Sort by updated_at descending for consistent ordering
        entries.sort(key=lambda e: e.updated_at, reverse=True)
        return entries[offset : offset + limit]

    async def find_by_tag(
        self,
        tag: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[LoreEntry]:
        """Find entries containing a specific tag.

        Args:
            tag: Tag to search for (case-insensitive).
            limit: Maximum results.
            offset: Results to skip.

        Returns:
            List of matching LoreEntry instances.
        """
        tag_lower = tag.lower().strip()
        entry_ids = self._tag_index.get(tag_lower, set())
        entries = [
            self._entries[entry_id]
            for entry_id in entry_ids
            if entry_id in self._entries
        ]
        entries.sort(key=lambda e: e.updated_at, reverse=True)
        return entries[offset : offset + limit]

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
            limit: Maximum results.

        Returns:
            List of matching LoreEntry instances.
        """
        if not tags:
            return []

        tags_lower = [t.lower().strip() for t in tags]

        if match_all:
            # Intersection: entry must have ALL tags
            matching_ids: Optional[Set[str]] = None
            for tag in tags_lower:
                tag_entries = self._tag_index.get(tag, set())
                if matching_ids is None:
                    matching_ids = tag_entries.copy()
                else:
                    matching_ids &= tag_entries
        else:
            # Union: entry can have ANY tag
            matching_ids = set()
            for tag in tags_lower:
                matching_ids |= self._tag_index.get(tag, set())

        entries = [
            self._entries[entry_id]
            for entry_id in (matching_ids or set())
            if entry_id in self._entries
        ]
        entries.sort(key=lambda e: e.updated_at, reverse=True)
        return entries[:limit]

    async def search(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        category: Optional[LoreCategory] = None,
        limit: int = 50,
    ) -> List[LoreEntry]:
        """Search entries by title with optional tag/category filtering.

        Args:
            query: Search query string (matches title, case-insensitive).
            tags: Optional tags to filter results.
            category: Optional category to filter results.
            limit: Maximum results.

        Returns:
            List of matching LoreEntry instances.
        """
        query_lower = query.lower().strip()
        results: List[LoreEntry] = []

        for entry in self._entries.values():
            # Title match (case-insensitive partial match)
            if query_lower and query_lower not in entry.title.lower():
                continue

            # Category filter
            if category is not None and entry.category != category:
                continue

            # Tag filter (any match)
            if tags:
                tags_lower = {t.lower().strip() for t in tags}
                entry_tags_lower = {t.lower() for t in entry.tags}
                if not tags_lower & entry_tags_lower:
                    continue

            results.append(entry)
            if len(results) >= limit:
                break

        # Sort by title for consistent alphabetical results
        results.sort(key=lambda e: e.title.lower())
        return results

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[LoreEntry]:
        """Get all entries with pagination.

        Args:
            limit: Maximum results.
            offset: Results to skip.

        Returns:
            List of LoreEntry instances.
        """
        all_entries = list(self._entries.values())
        # Sort by updated_at descending
        all_entries.sort(key=lambda e: e.updated_at, reverse=True)
        return all_entries[offset : offset + limit]

    async def count_all(self) -> int:
        """Get total count of lore entries."""
        return len(self._entries)

    async def get_all_tags(self) -> List[str]:
        """Get all unique tags across all entries.

        Returns:
            Sorted list of unique tags.
        """
        return sorted(self._tag_index.keys())

    # Utility methods for testing

    def clear(self) -> None:
        """Clear all data from the repository."""
        self._entries.clear()
        self._category_index.clear()
        self._tag_index.clear()
