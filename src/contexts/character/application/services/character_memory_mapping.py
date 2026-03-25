"""Character memory mapping service.

This module provides functionality for mapping character contexts
to memory systems and managing memory mappings.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol
from uuid import UUID, uuid4


@dataclass(frozen=True)
class CharacterMemoryMapping:
    """Value object representing a character to memory mapping.

    This maps a character to a specific memory scope or context,
    allowing characters to maintain different memory contexts
    across different stories or scenarios.

    Attributes:
        mapping_id: Unique identifier for this mapping
        character_id: The character UUID
        story_id: The story/workspace context
        scope_id: The memory scope identifier
        metadata: Optional metadata for the mapping
        created_at: When the mapping was created
    """

    character_id: UUID
    story_id: str
    scope_id: str
    mapping_id: UUID = field(default_factory=uuid4)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert mapping to dictionary representation."""
        return {
            "mapping_id": str(self.mapping_id),
            "character_id": str(self.character_id),
            "story_id": self.story_id,
            "scope_id": self.scope_id,
            "metadata": self.metadata,
        }


class CharacterMemoryMappingRepository(ABC):
    """Abstract repository for character memory mappings.

    This repository manages the persistence of character to memory
    scope mappings. Implementations handle the actual storage
    mechanism (in-memory, database, etc.).

    AI注意:
    - This is a port in hexagonal architecture
    - All methods are async
    - Returns Optional for queries that may not find results
    """

    @abstractmethod
    async def get_by_id(self, mapping_id: UUID) -> Optional[CharacterMemoryMapping]:
        """Get a mapping by its ID."""
        pass

    @abstractmethod
    async def get_by_character(
        self,
        character_id: UUID,
        story_id: Optional[str] = None,
    ) -> List[CharacterMemoryMapping]:
        """Get all mappings for a character, optionally filtered by story."""
        pass

    @abstractmethod
    async def get_by_scope(
        self,
        scope_id: str,
        story_id: Optional[str] = None,
    ) -> List[CharacterMemoryMapping]:
        """Get all mappings for a scope, optionally filtered by story."""
        pass

    @abstractmethod
    async def save(self, mapping: CharacterMemoryMapping) -> None:
        """Save a mapping (create or update)."""
        pass

    @abstractmethod
    async def delete(self, mapping_id: UUID) -> bool:
        """Delete a mapping. Returns True if deleted, False if not found."""
        pass

    @abstractmethod
    async def exists(
        self,
        character_id: UUID,
        story_id: str,
        scope_id: str,
    ) -> bool:
        """Check if a mapping exists for the given character, story, and scope."""
        pass

    @abstractmethod
    async def delete_by_character(
        self,
        character_id: UUID,
        story_id: Optional[str] = None,
    ) -> int:
        """Delete all mappings for a character. Returns count deleted."""
        pass


class InMemoryCharacterMemoryMappingRepository(CharacterMemoryMappingRepository):
    """In-memory implementation of CharacterMemoryMappingRepository.

    This implementation stores mappings in memory and is suitable
    for testing and development. Data is lost when the process exits.

    AI注意:
    - Not suitable for production use
    - Thread-safe for async operations within same process
    - Data is lost on process restart
    """

    def __init__(self) -> None:
        """Initialize the in-memory repository."""
        self._mappings: Dict[UUID, CharacterMemoryMapping] = {}

    async def get_by_id(self, mapping_id: UUID) -> Optional[CharacterMemoryMapping]:
        """Get a mapping by its ID."""
        return self._mappings.get(mapping_id)

    async def get_by_character(
        self,
        character_id: UUID,
        story_id: Optional[str] = None,
    ) -> List[CharacterMemoryMapping]:
        """Get all mappings for a character, optionally filtered by story."""
        mappings = [
            m for m in self._mappings.values() if m.character_id == character_id
        ]
        if story_id is not None:
            mappings = [m for m in mappings if m.story_id == story_id]
        return mappings

    async def get_by_scope(
        self,
        scope_id: str,
        story_id: Optional[str] = None,
    ) -> List[CharacterMemoryMapping]:
        """Get all mappings for a scope, optionally filtered by story."""
        mappings = [m for m in self._mappings.values() if m.scope_id == scope_id]
        if story_id is not None:
            mappings = [m for m in mappings if m.story_id == story_id]
        return mappings

    async def save(self, mapping: CharacterMemoryMapping) -> None:
        """Save a mapping (create or update)."""
        self._mappings[mapping.mapping_id] = mapping

    async def delete(self, mapping_id: UUID) -> bool:
        """Delete a mapping. Returns True if deleted, False if not found."""
        if mapping_id in self._mappings:
            del self._mappings[mapping_id]
            return True
        return False

    async def exists(
        self,
        character_id: UUID,
        story_id: str,
        scope_id: str,
    ) -> bool:
        """Check if a mapping exists for the given character, story, and scope."""
        for mapping in self._mappings.values():
            if (
                mapping.character_id == character_id
                and mapping.story_id == story_id
                and mapping.scope_id == scope_id
            ):
                return True
        return False

    async def delete_by_character(
        self,
        character_id: UUID,
        story_id: Optional[str] = None,
    ) -> int:
        """Delete all mappings for a character. Returns count deleted."""
        to_delete = []
        for mapping_id, mapping in self._mappings.items():
            if mapping.character_id == character_id:
                if story_id is None or mapping.story_id == story_id:
                    to_delete.append(mapping_id)

        for mapping_id in to_delete:
            del self._mappings[mapping_id]

        return len(to_delete)

    def clear(self) -> None:
        """Clear all mappings. Useful for testing."""
        self._mappings.clear()


class MemoryScopePort(Protocol):
    """Port for memory scope operations.

    This protocol abstracts the creation and management of
    memory scopes independent of the underlying implementation.
    """

    async def create_scope(
        self,
        character_id: UUID,
        story_id: str,
        scope_name: Optional[str] = None,
    ) -> str:
        """Create a new memory scope."""
        ...

    async def get_context_for_llm(
        self,
        character_id: UUID,
        scope_id: str,
        story_id: Optional[str] = None,
        tokens: int = 4000,
    ) -> List[Dict[str, Any]]:
        """Get context formatted for LLM consumption."""
        ...


class CharacterMemoryContextService:
    """Service for managing character memory contexts.

    This service coordinates character memory mappings and provides
    high-level operations for associating characters with memory scopes.

    AI注意:
    - Uses repository pattern for persistence
    - Uses port pattern for memory scope operations
    - All operations return Result type for error handling
    """

    def __init__(
        self,
        mapping_repo: CharacterMemoryMappingRepository,
        memory_scope_port: Optional[MemoryScopePort] = None,
    ):
        """Initialize the service.

        Args:
            mapping_repo: Repository for memory mappings
            memory_scope_port: Optional port for scope operations
        """
        self.mapping_repo = mapping_repo
        self.memory_scope = memory_scope_port

    async def create_mapping(
        self,
        character_id: UUID,
        story_id: str,
        scope_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CharacterMemoryMapping:
        """Create a new memory mapping for a character.

        Args:
            character_id: The character UUID
            story_id: The story/workspace context
            scope_id: Optional scope ID (will create new if not provided)
            metadata: Optional metadata for the mapping

        Returns:
            The created CharacterMemoryMapping

        Raises:
            ValueError: If scope creation fails and no scope_id provided
        """
        # Create a new scope if needed and port is available
        if scope_id is None and self.memory_scope is not None:
            scope_id = await self.memory_scope.create_scope(
                character_id=character_id,
                story_id=story_id,
                scope_name=f"scope-{character_id}-{story_id}",
            )
        elif scope_id is None:
            scope_id = f"default-{character_id}-{story_id}"

        mapping = CharacterMemoryMapping(
            character_id=character_id,
            story_id=story_id,
            scope_id=scope_id,
            metadata=metadata or {},
        )

        await self.mapping_repo.save(mapping)
        return mapping

    async def get_character_context(
        self,
        character_id: UUID,
        story_id: str,
        tokens: int = 4000,
    ) -> List[Dict[str, Any]]:
        """Get memory context for a character in a story.

        Args:
            character_id: The character UUID
            story_id: The story context
            tokens: Maximum tokens to return

        Returns:
            List of context items formatted for LLM

        Raises:
            ValueError: If no mapping exists and memory scope port not available
        """
        # Get mappings for this character in this story
        mappings = await self.mapping_repo.get_by_character(character_id, story_id)

        if not mappings:
            # No existing mapping, create default if we have the port
            if self.memory_scope is not None:
                mapping = await self.create_mapping(character_id, story_id)
                mappings = [mapping]
            else:
                return []

        # Use the first mapping's scope (could be extended for multiple scopes)
        primary_mapping = mappings[0]

        if self.memory_scope is not None:
            return await self.memory_scope.get_context_for_llm(
                character_id=character_id,
                scope_id=primary_mapping.scope_id,
                story_id=story_id,
                tokens=tokens,
            )

        return []

    async def remove_character_context(
        self,
        character_id: UUID,
        story_id: Optional[str] = None,
    ) -> int:
        """Remove memory context for a character.

        Args:
            character_id: The character UUID
            story_id: Optional story context (removes all if None)

        Returns:
            Number of mappings removed
        """
        return await self.mapping_repo.delete_by_character(character_id, story_id)

    async def has_memory_context(
        self,
        character_id: UUID,
        story_id: str,
    ) -> bool:
        """Check if a character has memory context in a story.

        Args:
            character_id: The character UUID
            story_id: The story context

        Returns:
            True if the character has at least one memory mapping
        """
        mappings = await self.mapping_repo.get_by_character(character_id, story_id)
        return len(mappings) > 0

    async def get_character_scopes(
        self,
        character_id: UUID,
        story_id: Optional[str] = None,
    ) -> List[str]:
        """Get all scope IDs for a character.

        Args:
            character_id: The character UUID
            story_id: Optional story context filter

        Returns:
            List of scope IDs
        """
        mappings = await self.mapping_repo.get_by_character(character_id, story_id)
        return [m.scope_id for m in mappings]
