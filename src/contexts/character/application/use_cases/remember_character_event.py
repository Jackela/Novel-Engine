"""Store a character memory event.

This use case handles storing new memories for characters,
including creating necessary sessions and handling workspace logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.contexts.character.domain.ports.memory_port import (
    CharacterMemoryPort,
    MemoryEntry,
    MemoryStorageError,
)


@dataclass(frozen=True)
class RememberCharacterEventRequest:
    """Request to store a character memory.

    Attributes:
        character_id: The character's unique identifier.
        content: The memory content to store.
        story_id: Optional story identifier for workspace isolation.
        session_id: Optional specific session for organization.
        honcho_session_id: Optional Honcho session ID (overrides session_id).
        importance: Memory importance level (low, medium, high, critical).
        chapter: Optional chapter/story point reference.
        tags: Optional list of tags for categorization.
        metadata: Additional arbitrary metadata.
    """

    character_id: UUID
    content: str
    story_id: str | None = None
    session_id: str | None = None
    honcho_session_id: str | None = None
    importance: str = "medium"  # low, medium, high, critical
    chapter: int | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.content or len(self.content.strip()) == 0:
            raise ValueError("Memory content cannot be empty")
        if len(self.content) > 10000:
            raise ValueError("Memory content too long (max 10000 characters)")
        if self.importance not in ("low", "medium", "high", "critical"):
            raise ValueError(f"Invalid importance: {self.importance}")


@dataclass(frozen=True)
class RememberCharacterEventResponse:
    """Response from storing a character memory.

    Attributes:
        memory_id: The unique identifier of the stored memory.
        content: The stored content.
        session_id: The session ID where the memory was stored.
        workspace_id: The workspace ID used.
        created_at: Timestamp when the memory was created.
    """

    memory_id: str
    content: str
    session_id: str
    workspace_id: str
    created_at: str

    @classmethod
    def from_memory_entry(
        cls,
        entry: MemoryEntry,
        workspace_id: str,
    ) -> "RememberCharacterEventResponse":
        """Create response from a MemoryEntry."""
        return cls(
            memory_id=entry.memory_id,
            content=entry.content,
            session_id=entry.session_id or "default",
            workspace_id=workspace_id,
            created_at=entry.created_at.isoformat(),
        )


class RememberCharacterEventUseCase:
    """Use case for storing character memories.

    This use case orchestrates the storage of character memories,
    handling workspace/session management automatically.

    Example:
        >>> use_case = RememberCharacterEventUseCase(memory_port)
        >>> request = RememberCharacterEventRequest(
        ...     character_id=character_id,
        ...     content="Character discovered the ancient artifact",
        ...     importance="high",
        ...     chapter=5,
        ... )
        >>> result = await use_case.execute(request)
    """

    def __init__(self, memory_port: CharacterMemoryPort) -> None:
        """Initialize the use case.

        Args:
            memory_port: The memory storage port implementation.
        """
        self._memory_port = memory_port

    async def execute(
        self,
        request: RememberCharacterEventRequest,
    ) -> RememberCharacterEventResponse:
        """Execute the use case.

        Args:
            request: The memory storage request.

        Returns:
            RememberCharacterEventResponse containing the stored memory details.

        Raises:
            MemoryStorageError: If storage operation fails.
        """
        try:
            # Build metadata
            metadata: dict[str, Any] = {
                "importance": request.importance,
            }
            if request.chapter is not None:
                metadata["chapter"] = request.chapter
            if request.tags:
                metadata["tags"] = request.tags
            if request.metadata:
                metadata.update(request.metadata)

            # Use honcho_session_id if provided, otherwise use session_id
            effective_session_id = request.honcho_session_id or request.session_id

            # Store the memory
            entry = await self._memory_port.remember(
                character_id=request.character_id,
                content=request.content,
                story_id=request.story_id,
                session_id=effective_session_id,
                metadata=metadata,
            )

            workspace_id = (
                f"novel-engine-{request.story_id}"
                if request.story_id
                else f"novel-engine-character-{request.character_id}"
            )
            response = RememberCharacterEventResponse.from_memory_entry(
                entry=entry,
                workspace_id=workspace_id,
            )

            return response

        except MemoryStorageError:
            raise
        except Exception as e:
            raise MemoryStorageError(f"INTERNAL_ERROR: {e}") from e
