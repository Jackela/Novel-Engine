#!/usr/bin/env python3
"""In-Memory Memory Store Implementation.

This module provides a simple in-memory store for character memories.
It supports storing, retrieving, and deleting memory entries with
associated metadata.

Why in-memory: Enables rapid testing and development without requiring
external storage. The interface allows swapping to persistent storage
later without changing calling code.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class MemoryEntry:
    """A single memory entry with content and metadata.

    Attributes:
        memory_id: Unique identifier for this memory.
        content: The memory content text.
        metadata: Optional metadata dict for additional context.
        created_at: Timestamp when the memory was stored.
        updated_at: Timestamp when the memory was last updated.
    """

    memory_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class MemoryStore:
    """In-memory implementation of a character memory store.

    Stores memory entries in a dictionary indexed by memory_id.
    Provides CRUD operations for memory management.

    Thread Safety:
        This implementation is NOT thread-safe. For concurrent access,
        use locking or switch to a thread-safe implementation.

    Example:
        >>> store = MemoryStore()
        >>> store.store("mem-001", "Character remembers the castle", {"importance": 5})
        >>> entry = store.retrieve("mem-001")
        >>> print(entry.content)
        'Character remembers the castle'
    """

    def __init__(self) -> None:
        """Initialize the store with empty storage."""
        self._store: Dict[str, MemoryEntry] = {}

    def store(
        self,
        memory_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store a memory entry.

        If an entry with the same memory_id exists, it will be updated
        with the new content and metadata. The created_at timestamp is
        preserved on updates, but updated_at is refreshed.

        Args:
            memory_id: Unique identifier for this memory.
            content: The memory content text.
            metadata: Optional metadata dict for additional context.
        """
        now = datetime.utcnow()

        # Preserve created_at if updating existing entry
        existing = self._store.get(memory_id)
        created_at = existing.created_at if existing else now

        self._store[memory_id] = MemoryEntry(
            memory_id=memory_id,
            content=content,
            metadata=metadata or {},
            created_at=created_at,
            updated_at=now,
        )

    def retrieve(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry by ID.

        Args:
            memory_id: Unique identifier for the memory.

        Returns:
            MemoryEntry if found, None otherwise.
        """
        return self._store.get(memory_id)

    def delete(self, memory_id: str) -> bool:
        """Delete a memory entry.

        Args:
            memory_id: Unique identifier for the memory.

        Returns:
            True if deleted, False if not found.
        """
        if memory_id in self._store:
            del self._store[memory_id]
            return True
        return False

    def clear(self) -> None:
        """Clear all memories from the store."""
        self._store.clear()

    def count(self) -> int:
        """Get the total number of stored memories."""
        return len(self._store)

    def list_all(self) -> list[MemoryEntry]:
        """List all stored memory entries.

        Returns:
            List of all MemoryEntry instances, sorted by created_at descending.
        """
        entries = list(self._store.values())
        entries.sort(key=lambda e: e.created_at, reverse=True)
        return entries
