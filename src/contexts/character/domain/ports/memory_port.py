"""Character memory port (interface).

This module defines the abstract interface for character memory operations,
following the Ports and Adapters pattern (Hexagonal Architecture).

The domain layer depends on this port, while infrastructure provides
concrete implementations (e.g., HonchoMemoryAdapter).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID


@dataclass(frozen=True)
class MemoryEntry:
    """Value object representing a single memory entry.

    This is a domain concept representing a character's memory,
    independent of the underlying storage mechanism.
    """

    memory_id: str
    character_id: UUID
    content: str
    created_at: datetime
    metadata: dict[str, Any]
    session_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert memory entry to dictionary."""
        return {
            "memory_id": self.memory_id,
            "character_id": str(self.character_id),
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "session_id": self.session_id,
        }


@dataclass(frozen=True)
class MemoryQueryResult:
    """Result of a memory query operation.

    Contains the retrieved memories along with relevance scores.
    """

    memories: list[MemoryEntry]
    query: str
    total_found: int

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "memories": [m.to_dict() for m in self.memories],
            "query": self.query,
            "total_found": self.total_found,
        }


class CharacterMemoryPort(Protocol):
    """Port interface for character memory operations.

    This protocol defines the contract that any memory adapter must implement.
    It abstracts away the underlying storage mechanism (Honcho, ChromaDB, etc.)
    from the domain layer.

    Implementations:
        - HonchoMemoryAdapter: Uses Honcho for semantic memory storage
        - InMemoryMemoryAdapter: In-memory implementation for testing

    Example:
        >>> adapter: CharacterMemoryPort = HonchoMemoryAdapter()
        >>> await adapter.remember(
        ...     character_id=uuid,
        ...     content="The character learned about the ancient prophecy",
        ...     metadata={"chapter": 3, "importance": "high"},
        ... )
    """

    @abstractmethod
    async def remember(
        self,
        character_id: UUID,
        content: str,
        story_id: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Store a new memory for a character.

        This creates a persistent memory entry that can be retrieved
        later via semantic search.

        Args:
            character_id: The character's unique identifier.
            content: The memory content to store.
            story_id: Optional story/workspace context.
            session_id: Optional specific session to store in.
            metadata: Optional metadata (chapter, importance, etc.).

        Returns:
            The created MemoryEntry with assigned ID.

        Raises:
            MemoryStorageError: If storage operation fails.
        """
        ...

    @abstractmethod
    async def recall(
        self,
        character_id: UUID,
        query: str,
        story_id: str | None = None,
        session_id: str | None = None,
        top_k: int = 5,
    ) -> MemoryQueryResult:
        """Retrieve relevant memories based on semantic query.

        Performs semantic search to find memories most relevant to the query.

        Args:
            character_id: The character's unique identifier.
            query: Natural language query describing what to recall.
            story_id: Optional story/workspace context.
            session_id: Optional specific session to search within.
            top_k: Maximum number of memories to retrieve.

        Returns:
            MemoryQueryResult containing matching memories.

        Raises:
            MemoryQueryError: If query operation fails.
        """
        ...

    @abstractmethod
    async def forget(
        self,
        character_id: UUID,
        memory_id: str,
        story_id: str | None = None,
    ) -> bool:
        """Delete a specific memory.

        Args:
            character_id: The character's unique identifier.
            memory_id: The memory entry ID to delete.
            story_id: Optional story/workspace context.

        Returns:
            True if memory was deleted, False if not found.

        Raises:
            MemoryStorageError: If deletion operation fails.
        """
        ...

    @abstractmethod
    async def get_character_memories(
        self,
        character_id: UUID,
        story_id: str | None = None,
        session_id: str | None = None,
        limit: int = 100,
    ) -> list[MemoryEntry]:
        """Get all memories for a character.

        Args:
            character_id: The character's unique identifier.
            story_id: Optional story/workspace context.
            session_id: Optional specific session to retrieve from.
            limit: Maximum number of memories to return.

        Returns:
            List of memory entries, ordered by recency.
        """
        ...

    @abstractmethod
    async def get_character_summary(
        self,
        character_id: UUID,
        story_id: str | None = None,
        session_id: str | None = None,
    ) -> str:
        """Get a summarized representation of a character.

        This leverages Honcho's reasoning capabilities to generate
        a coherent summary of the character based on all memories.

        Args:
            character_id: The character's unique identifier.
            story_id: Optional story/workspace context.
            session_id: Optional specific session context.

        Returns:
            Textual summary/representation of the character.
        """
        ...

    @abstractmethod
    async def query_character(
        self,
        character_id: UUID,
        question: str,
        story_id: str | None = None,
        session_id: str | None = None,
    ) -> str:
        """Ask a natural language question about a character.

        Uses dialectic/reasoning to answer questions based on memories.

        Args:
            character_id: The character's unique identifier.
            question: Natural language question about the character.
            story_id: Optional story/workspace context.
            session_id: Optional specific session context.

        Returns:
            Reasoned answer based on character memories.
        """
        ...

    @abstractmethod
    async def create_session(
        self,
        character_id: UUID,
        story_id: str,
        session_name: str | None = None,
    ) -> str:
        """Create a new memory session for a character.

        Sessions allow organizing memories into logical groups
        (e.g., different story arcs, time periods).

        Args:
            character_id: The character's unique identifier.
            story_id: The story/workspace context.
            session_name: Optional human-readable session name.

        Returns:
            The created session ID.
        """
        ...

    @abstractmethod
    async def get_session_context(
        self,
        character_id: UUID,
        session_id: str,
        story_id: str | None = None,
        tokens: int = 4000,
    ) -> list[dict[str, Any]]:
        """Get session context formatted for LLM consumption.

        Retrieves relevant memories up to a token limit, formatted
        for direct use in LLM prompts.

        Args:
            character_id: The character's unique identifier.
            session_id: The session to get context from.
            story_id: Optional story/workspace context.
            tokens: Maximum tokens to return.

        Returns:
            List of context items suitable for LLM prompt.
        """
        ...


class MemoryStorageError(Exception):
    """Exception raised when memory storage operations fail."""

    pass


class MemoryQueryError(Exception):
    """Exception raised when memory query operations fail."""

    pass
