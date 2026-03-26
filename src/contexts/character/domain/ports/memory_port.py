"""Character memory port (interface).

This module defines the abstract interface for character memory operations,
following the Ports and Adapters pattern (Hexagonal Architecture).

The domain layer depends on these ports, while infrastructure provides
concrete implementations (e.g., HonchoMemoryAdapter).
"""

from __future__ import annotations

from abc import abstractmethod
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
    scope_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert memory entry to dictionary."""
        return {
            "memory_id": self.memory_id,
            "character_id": str(self.character_id),
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "scope_id": self.scope_id,
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


class MemoryStoragePort(Protocol):
    """Port interface for memory storage operations.

    This protocol defines the contract for storing and deleting memories.
    It abstracts away the underlying storage mechanism from the domain layer.

    Implementations:
        - HonchoMemoryAdapter: Uses Honcho for semantic memory storage
        - InMemoryMemoryAdapter: In-memory implementation for testing
    """

    @abstractmethod
    async def store(
        self,
        character_id: UUID,
        content: str,
        story_id: str | None = None,
        scope_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Store a new memory for a character.

        This creates a persistent memory entry that can be retrieved
        later via semantic search.

        Args:
            character_id: The character's unique identifier.
            content: The memory content to store.
            story_id: Optional story/workspace context.
            scope_id: Optional specific scope to store in.
            metadata: Optional metadata (chapter, importance, etc.).

        Returns:
            The created MemoryEntry with assigned ID.

        Raises:
            MemoryStorageError: If storage operation fails.
        """
        ...

    @abstractmethod
    async def delete(
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


class MemoryQueryPort(Protocol):
    """Port interface for memory query operations.

    This protocol defines the contract for searching and retrieving memories.
    It abstracts away the underlying search mechanism from the domain layer.
    """

    @abstractmethod
    async def search(
        self,
        character_id: UUID,
        query: str,
        story_id: str | None = None,
        scope_id: str | None = None,
        top_k: int = 5,
    ) -> MemoryQueryResult:
        """Retrieve relevant memories based on semantic query.

        Performs semantic search to find memories most relevant to the query.

        Args:
            character_id: The character's unique identifier.
            query: Natural language query describing what to recall.
            story_id: Optional story/workspace context.
            scope_id: Optional specific scope to search within.
            top_k: Maximum number of memories to retrieve.

        Returns:
            MemoryQueryResult containing matching memories.

        Raises:
            MemoryQueryError: If query operation fails.
        """
        ...

    @abstractmethod
    async def get_all(
        self,
        character_id: UUID,
        story_id: str | None = None,
        scope_id: str | None = None,
        limit: int = 100,
    ) -> list[MemoryEntry]:
        """Get all memories for a character.

        Args:
            character_id: The character's unique identifier.
            story_id: Optional story/workspace context.
            scope_id: Optional specific scope to retrieve from.
            limit: Maximum number of memories to return.

        Returns:
            List of memory entries, ordered by recency.
        """
        ...


class MemoryReasoningPort(Protocol):
    """Port interface for memory reasoning operations.

    This protocol defines the contract for AI-powered reasoning over memories,
    including summarization and question answering capabilities.
    """

    @abstractmethod
    async def summarize(
        self,
        character_id: UUID,
        story_id: str | None = None,
        scope_id: str | None = None,
    ) -> str:
        """Get a summarized representation of a character.

        This leverages AI reasoning capabilities to generate
        a coherent summary of the character based on all memories.

        Args:
            character_id: The character's unique identifier.
            story_id: Optional story/workspace context.
            scope_id: Optional specific scope context.

        Returns:
            Textual summary/representation of the character.
        """
        ...

    @abstractmethod
    async def query(
        self,
        character_id: UUID,
        question: str,
        story_id: str | None = None,
        scope_id: str | None = None,
    ) -> str:
        """Ask a natural language question about a character.

        Uses dialectic/reasoning to answer questions based on memories.

        Args:
            character_id: The character's unique identifier.
            question: Natural language question about the character.
            story_id: Optional story/workspace context.
            scope_id: Optional specific scope context.

        Returns:
            Reasoned answer based on character memories.
        """
        ...


class ScopeManagementPort(Protocol):
    """Port interface for memory scope management operations.

    This protocol defines the contract for organizing memories into logical
    scopes (e.g., different story arcs, time periods, or contexts).
    """

    @abstractmethod
    async def create_scope(
        self,
        character_id: UUID,
        story_id: str,
        scope_name: str | None = None,
    ) -> str:
        """Create a new memory scope for a character.

        Scopes allow organizing memories into logical groups
        (e.g., different story arcs, time periods).

        Args:
            character_id: The character's unique identifier.
            story_id: The story/workspace context.
            scope_name: Optional human-readable scope name.

        Returns:
            The created scope ID.
        """
        ...

    @abstractmethod
    async def get_context_for_llm(
        self,
        character_id: UUID,
        scope_id: str,
        story_id: str | None = None,
        tokens: int = 4000,
    ) -> list[dict[str, Any]]:
        """Get scope context formatted for LLM consumption.

        Retrieves relevant memories up to a token limit, formatted
        for direct use in LLM prompts.

        Args:
            character_id: The character's unique identifier.
            scope_id: The scope to get context from.
            story_id: Optional story/workspace context.
            tokens: Maximum tokens to return.

        Returns:
            List of context items suitable for LLM prompt.
        """
        ...


class CharacterMemoryPort(
    MemoryStoragePort,
    MemoryQueryPort,
    MemoryReasoningPort,
    ScopeManagementPort,
    Protocol,
):
    """Complete port interface for character memory operations.

    This protocol combines all memory-related operations into a single
    interface for backward compatibility. New code should prefer using
    the specialized ports (MemoryStoragePort, MemoryQueryPort, etc.)
    to adhere to the Interface Segregation Principle.

    Implementations:
        - HonchoMemoryAdapter: Uses Honcho for semantic memory storage
        - InMemoryMemoryAdapter: In-memory implementation for testing

    Example:
        >>> adapter: CharacterMemoryPort = HonchoMemoryAdapter()
        >>> await adapter.store(
        ...     character_id=uuid,
        ...     content="The character learned about the ancient prophecy",
        ...     metadata={"chapter": 3, "importance": "high"},
        ... )
    """

    pass


@dataclass
class MemoryErrorDetails:
    """Structured error details for memory operations.

    Attributes:
        operation: The operation being performed (e.g., "store", "retrieve").
        entity_id: The ID of the entity being operated on.
        error_code: Standardized error code (e.g., "CONNECTION_ERROR").
        original_exception: The original exception that was raised.
        context: Additional context information.
    """

    operation: str
    entity_id: str
    error_code: str
    original_exception: Exception | None = None
    context: dict[str, Any] | None = None


class MemoryStorageError(Exception):
    """Exception raised when memory storage operations fail.

    Attributes:
        message: Human-readable error message.
        details: Structured error details.
        error_code: Standardized error code.
    """

    def __init__(
        self,
        message: str,
        details: MemoryErrorDetails | None = None,
    ) -> None:
        super().__init__(message)
        self.details = details
        self.error_code = details.error_code if details else "UNKNOWN_ERROR"


class MemoryQueryError(Exception):
    """Exception raised when memory query operations fail.

    Attributes:
        message: Human-readable error message.
        details: Structured error details.
        error_code: Standardized error code.
    """

    def __init__(
        self,
        message: str,
        details: MemoryErrorDetails | None = None,
    ) -> None:
        super().__init__(message)
        self.details = details
        self.error_code = details.error_code if details else "UNKNOWN_ERROR"
