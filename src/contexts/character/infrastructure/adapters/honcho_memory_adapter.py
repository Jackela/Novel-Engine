"""Honcho memory adapter implementation.

This module provides the concrete adapter that connects the character domain
to Honcho's semantic memory system.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from src.contexts.character.domain.ports.memory_port import (
    MemoryEntry,
    MemoryErrorDetails,
    MemoryQueryResult,
    MemoryStorageError,
)
from src.shared.infrastructure.honcho import HonchoClient, HonchoClientError

from .memory_query_handler import MemoryQueryHandler
from .memory_session_handler import MemorySessionHandler
from .memory_storage_handler import MemoryStorageHandler


class HonchoMemoryAdapter:
    """Honcho-based implementation of character memory operations.

    This adapter connects the character domain to Honcho's semantic memory
    system, providing automatic embedding, reasoning, and retrieval.

    Attributes:
        honcho_client: The Honcho client instance.
        _workspace_cache: Cache of workspace IDs to avoid repeated lookups.

    Example:
        >>> adapter = HonchoMemoryAdapter()
        >>> await adapter.initialize()
        >>> entry = await adapter.remember(
        ...     character_id=uuid,
        ...     content="Character discovered a hidden door",
        ...     story_id="story-123"
        ... )
    """

    def __init__(self, honcho_client: HonchoClient | None = None) -> None:
        """Initialize the adapter.

        Args:
            honcho_client: Optional HonchoClient instance. If None, creates default.
        """
        self._honcho = honcho_client
        self._workspace_cache: dict[str, str] = {}

        # Initialize handlers
        self._storage_handler = MemoryStorageHandler(honcho_client)
        self._query_handler = MemoryQueryHandler(honcho_client)
        self._session_handler = MemorySessionHandler(honcho_client)

    def _classify_error(self, error: Exception) -> str:
        """Classify an exception into a standardized error code.

        Args:
            error: The exception to classify.

        Returns:
            Standardized error code string.
        """
        if isinstance(error, ConnectionError):
            return "CONNECTION_ERROR"
        elif isinstance(error, TimeoutError):
            return "TIMEOUT_ERROR"
        elif isinstance(error, HonchoClientError):
            return "HONCHO_CLIENT_ERROR"
        else:
            return "UNKNOWN_ERROR"

    async def initialize(self) -> None:
        """Initialize the adapter by ensuring Honcho client is ready."""
        # Client is now injected via constructor, no need for singleton
        if self._honcho is None:
            raise MemoryStorageError(
                "Honcho client not provided",
                details=MemoryErrorDetails(
                    operation="initialize",
                    entity_id="adapter",
                    error_code="CLIENT_NOT_INITIALIZED",
                ),
            )

    async def close(self) -> None:
        """Clean up resources."""
        self._workspace_cache.clear()
        self._storage_handler.clear_cache()
        self._session_handler.clear_cache()

    def _get_workspace_id(
        self,
        story_id: str | None,
        character_id: UUID,
    ) -> str:
        """Resolve workspace ID using story-centric strategy.

        If story_id is provided, uses the story-centric workspace.
        Otherwise falls back to character-based workspace.
        """
        if self._honcho is None:
            # Return simple default if client not initialized
            if story_id:
                return f"novel-engine-{story_id}"
            return f"novel-engine-character-{character_id}"

        return self._honcho.get_workspace_for_character(
            character_id=str(character_id),
            story_id=story_id,
        )

    def _resolve_honcho_fields(
        self,
        character_id: UUID,
        story_id: str | None,
        session_id: str | None,
    ) -> tuple[str, str, str]:
        """Resolve Honcho workspace, peer, and session fields.

        Returns:
            Tuple of (workspace_id, peer_id, resolved_session_id)
        """
        workspace_id = self._get_workspace_id(story_id, character_id)
        peer_id = str(character_id)
        resolved_session_id = self._session_handler._get_or_create_session_id(
            character_id, workspace_id, session_id
        )
        return workspace_id, peer_id, resolved_session_id

    async def remember(
        self,
        character_id: UUID,
        content: str,
        story_id: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Store a new memory for a character.

        Creates the workspace, peer, and session if they don't exist.

        Raises:
            MemoryStorageError: If storage operation fails.
        """
        await self.initialize()

        # Resolve workspace from story_id
        workspace_id = self._get_workspace_id(story_id, character_id)

        return await self._storage_handler.store_memory(
            character_id=character_id,
            content=content,
            workspace_id=workspace_id,
            session_id=session_id,
            metadata=metadata,
        )

    async def recall(
        self,
        character_id: UUID,
        query: str,
        story_id: str | None = None,
        session_id: str | None = None,
        top_k: int = 5,
    ) -> MemoryQueryResult:
        """Retrieve relevant memories for a character.

        Raises:
            MemoryQueryError: If query operation fails.
        """
        await self.initialize()

        workspace_id = self._get_workspace_id(story_id, character_id)

        return await self._query_handler.recall(
            character_id=character_id,
            query=query,
            workspace_id=workspace_id,
            session_id=session_id,
            top_k=top_k,
        )

    async def forget(
        self,
        character_id: UUID,
        memory_id: str,
        story_id: str | None = None,
    ) -> bool:
        """Delete a specific memory.

        Note: Honcho doesn't support direct message deletion through the
        high-level SDK. Returns False to indicate this limitation.
        """
        # Honcho SDK doesn't expose message deletion
        # Return False to indicate the limitation
        return False

    async def get_character_memories(
        self,
        character_id: UUID,
        story_id: str | None = None,
        session_id: str | None = None,
        limit: int = 100,
    ) -> list[MemoryEntry]:
        """Get all memories for a character."""
        await self.initialize()

        workspace_id = self._get_workspace_id(story_id, character_id)

        return await self._query_handler.get_character_memories(
            character_id=character_id,
            workspace_id=workspace_id,
            session_id=session_id,
            limit=limit,
        )

    async def create_session(
        self,
        character_id: UUID,
        story_id: str,
        session_name: str | None = None,
    ) -> str:
        """Create a new memory session for a character."""
        await self.initialize()

        workspace_id = self._get_workspace_id(story_id, character_id)

        return await self._session_handler.create_session(
            character_id=character_id,
            story_id=story_id,
            workspace_id=workspace_id,
            session_name=session_name,
        )

    async def get_character_summary(
        self,
        character_id: UUID,
        story_id: str | None = None,
        session_id: str | None = None,
    ) -> str:
        """Get a summary of character's experiences."""
        await self.initialize()

        workspace_id = self._get_workspace_id(story_id, character_id)

        return await self._query_handler.get_character_summary(
            character_id=character_id,
            workspace_id=workspace_id,
            session_id=session_id,
        )

    async def query_character(
        self,
        character_id: UUID,
        question: str,
        story_id: str | None = None,
        session_id: str | None = None,
    ) -> str:
        """Ask a natural language question about character's memories."""
        await self.initialize()

        workspace_id = self._get_workspace_id(story_id, character_id)

        return await self._query_handler.query_character(
            character_id=character_id,
            question=question,
            workspace_id=workspace_id,
            session_id=session_id,
        )

    async def get_session_context(
        self,
        character_id: UUID,
        session_id: str,
        story_id: str | None = None,
        tokens: int = 4000,
    ) -> list[dict[str, Any]]:
        """Get session context formatted for LLM consumption."""
        await self.initialize()

        workspace_id = self._get_workspace_id(story_id, character_id)

        return await self._session_handler.get_session_context(
            character_id=character_id,
            session_id=session_id,
            workspace_id=workspace_id,
            tokens=tokens,
        )
