"""Recall character memories use case.

This use case handles retrieving relevant memories for characters
based on semantic search queries.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.contexts.character.domain.ports.memory_port import (
    CharacterMemoryPort,
    MemoryEntry,
    MemoryQueryError,
    MemoryQueryResult,
)


@dataclass(frozen=True)
class RecallCharacterMemoriesRequest:
    """Request to recall character memories.

    Attributes:
        character_id: The character whose memories to search.
        query: Search query (natural language).
        story_id: Optional story/workspace filter.
        session_id: Optional specific session to search.
        honcho_session_id: Optional Honcho session ID (overrides session_id).
        top_k: Maximum number of memories to return.
        min_relevance: Minimum relevance score threshold (0.0-1.0).
    """

    character_id: UUID
    query: str
    story_id: str | None = None
    session_id: str | None = None
    honcho_session_id: str | None = None
    top_k: int = 5
    min_relevance: float = 0.0

    def __post_init__(self) -> None:
        if not self.query or len(self.query.strip()) == 0:
            raise ValueError("Query cannot be empty")
        if self.top_k < 1 or self.top_k > 100:
            raise ValueError("top_k must be between 1 and 100")
        if self.min_relevance < 0.0 or self.min_relevance > 1.0:
            raise ValueError("min_relevance must be between 0.0 and 1.0")


@dataclass(frozen=True)
class MemoryRecallDTO:
    """Data transfer object for a recalled memory.

    Attributes:
        memory_id: Unique identifier.
        content: Memory content.
        relevance_score: Similarity score (0.0-1.0).
        chapter: Optional chapter reference.
        importance: Memory importance level.
        tags: Associated tags.
        created_at: Creation timestamp.
    """

    memory_id: str
    content: str
    relevance_score: float | None
    chapter: int | None
    importance: str
    tags: list[str]
    created_at: str

    @classmethod
    def from_memory_entry(cls, entry: MemoryEntry) -> "MemoryRecallDTO":
        """Create DTO from MemoryEntry."""
        metadata = entry.metadata or {}
        return cls(
            memory_id=entry.memory_id,
            content=entry.content,
            relevance_score=metadata.get("relevance_score"),
            chapter=metadata.get("chapter"),
            importance=metadata.get("importance", "medium"),
            tags=metadata.get("tags", []),
            created_at=entry.created_at.isoformat(),
        )


@dataclass(frozen=True)
class RecallCharacterMemoriesResponse:
    """Response from recalling character memories.

    Attributes:
        memories: List of recalled memories sorted by relevance.
        total_found: Total number of memories found.
        query: The original search query.
        character_id: The character ID searched.
    """

    memories: list[MemoryRecallDTO]
    total_found: int
    query: str
    character_id: UUID

    def to_prompt_context(self, max_memories: int | None = None) -> str:
        """Convert memories to a formatted string for LLM prompts.

        Args:
            max_memories: Limit number of memories included.

        Returns:
            Formatted context string.
        """
        memories = self.memories[:max_memories] if max_memories else self.memories

        if not memories:
            return "No relevant memories found."

        lines = ["## Character Memories", ""]

        for i, memory in enumerate(memories, 1):
            relevance = (
                f" ({memory.relevance_score:.2f})" if memory.relevance_score else ""
            )
            lines.append(f"{i}. {memory.content}{relevance}")

            # Add metadata if available
            meta_parts = []
            if memory.chapter:
                meta_parts.append(f"Chapter {memory.chapter}")
            if memory.importance != "medium":
                meta_parts.append(memory.importance)
            if memory.tags:
                meta_parts.append(", ".join(memory.tags))

            if meta_parts:
                lines.append(f"   [{' | '.join(meta_parts)}]")
            lines.append("")

        return "\n".join(lines)


class RecallCharacterMemoriesUseCase:
    """Use case for recalling character memories.

    Performs semantic search over a character's memories to find
    the most relevant entries for a given query.

    Example:
        >>> use_case = RecallCharacterMemoriesUseCase(memory_port)
        >>> request = RecallCharacterMemoriesRequest(
        ...     character_id=character_id,
        ...     query="What does the character know about the prophecy?",
        ...     top_k=3,
        ... )
        >>> response = await use_case.execute(request)
        >>> context = response.to_prompt_context()
    """

    def __init__(self, memory_port: CharacterMemoryPort) -> None:
        """Initialize the use case.

        Args:
            memory_port: The memory storage port implementation.
        """
        self._memory_port = memory_port

    async def execute(
        self,
        request: RecallCharacterMemoriesRequest,
    ) -> RecallCharacterMemoriesResponse:
        """Execute the use case.

        Args:
            request: The memory recall request.

        Returns:
            RecallCharacterMemoriesResponse with memories.

        Raises:
            MemoryQueryError: If query operation fails.
        """
        try:
            # Use honcho_session_id if provided, otherwise use session_id
            effective_session_id = request.honcho_session_id or request.session_id

            # Perform recall
            result: MemoryQueryResult = await self._memory_port.recall(
                character_id=request.character_id,
                query=request.query,
                story_id=request.story_id,
                session_id=effective_session_id,
                top_k=request.top_k,
            )

            entries = result.memories

            # Filter by relevance threshold
            if request.min_relevance > 0:
                entries = [
                    e
                    for e in entries
                    if e.metadata.get("relevance_score") is None
                    or e.metadata.get("relevance_score", 0) >= request.min_relevance
                ]

            # Convert to DTOs
            memory_dtos = [MemoryRecallDTO.from_memory_entry(e) for e in entries]

            return RecallCharacterMemoriesResponse(
                memories=memory_dtos,
                total_found=len(memory_dtos),
                query=request.query,
                character_id=request.character_id,
            )

        except MemoryQueryError:
            raise
        except Exception as e:
            raise MemoryQueryError(f"Failed to recall memories: {e}")
