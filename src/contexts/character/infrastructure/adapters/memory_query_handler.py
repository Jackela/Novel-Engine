"""Memory query handler for Honcho adapter."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from src.contexts.character.domain.ports.memory_port import (
    MemoryEntry,
    MemoryErrorDetails,
    MemoryQueryError,
    MemoryQueryResult,
)
from src.shared.infrastructure.honcho import HonchoClientError

if TYPE_CHECKING:
    from src.shared.infrastructure.honcho import HonchoClient


class MemoryQueryHandler:
    """Handles search/retrieve operations for character memories."""

    def __init__(self, honcho_client: HonchoClient | None = None) -> None:
        """Initialize the query handler.

        Args:
            honcho_client: Optional HonchoClient instance.
        """
        self._honcho = honcho_client

    async def recall(
        self,
        character_id: UUID,
        query: str,
        workspace_id: str,
        session_id: str | None = None,
        top_k: int = 5,
    ) -> MemoryQueryResult:
        """Retrieve relevant memories for a character.

        Args:
            character_id: The character UUID.
            query: The search query.
            workspace_id: The workspace ID.
            session_id: Optional session ID to search within.
            top_k: Maximum number of results.

        Returns:
            MemoryQueryResult containing the retrieved memories.

        Raises:
            MemoryQueryError: If query operation fails.
        """
        if self._honcho is None:
            raise MemoryQueryError(
                "Honcho client not provided",
                details=MemoryErrorDetails(
                    operation="recall",
                    entity_id=str(character_id),
                    error_code="CLIENT_NOT_INITIALIZED",
                ),
            )

        try:
            peer_id = str(character_id)

            # Search for memories
            messages = await self._honcho.search_memories(
                workspace_id=workspace_id,
                peer_id=peer_id,
                query=query,
                top_k=top_k,
                session_id=session_id,
            )

            # Convert to MemoryEntry objects
            entries = []
            for msg in messages:
                entry = MemoryEntry(
                    memory_id=msg.id,
                    content=msg.content,
                    character_id=character_id,
                    created_at=msg.created_at or datetime.utcnow(),
                    metadata=msg.metadata or {},
                    scope_id=session_id,
                )
                entries.append(entry)

            return MemoryQueryResult(
                memories=entries,
                query=query,
                total_found=len(entries),
            )

        except (HonchoClientError, ConnectionError, TimeoutError) as e:
            error_code = self._classify_error(e)
            raise MemoryQueryError(
                f"Failed to recall memories for character {character_id}",
                details=MemoryErrorDetails(
                    operation="recall",
                    entity_id=str(character_id),
                    error_code=error_code,
                    original_exception=e,
                    context={
                        "workspace_id": workspace_id,
                        "session_id": session_id,
                        "query": query,
                        "top_k": top_k,
                    },
                ),
            ) from e

    async def get_character_memories(
        self,
        character_id: UUID,
        workspace_id: str,
        session_id: str | None = None,
        limit: int = 100,
    ) -> list[MemoryEntry]:
        """Get all memories for a character.

        Args:
            character_id: The character UUID.
            workspace_id: The workspace ID.
            session_id: Optional session ID.
            limit: Maximum number of memories to retrieve.

        Returns:
            List of MemoryEntry objects.

        Raises:
            MemoryQueryError: If query operation fails.
        """
        if self._honcho is None:
            raise MemoryQueryError(
                "Honcho client not provided",
                details=MemoryErrorDetails(
                    operation="get_all",
                    entity_id=str(character_id),
                    error_code="CLIENT_NOT_INITIALIZED",
                ),
            )

        try:
            peer_id = str(character_id)

            # Use a broad search query to get all memories
            messages = await self._honcho.search_memories(
                workspace_id=workspace_id,
                peer_id=peer_id,
                query="*",  # Broad search
                top_k=limit,
                session_id=session_id,
            )

            entries = []
            for msg in messages:
                entry = MemoryEntry(
                    memory_id=msg.id,
                    content=msg.content,
                    character_id=character_id,
                    created_at=msg.created_at or datetime.utcnow(),
                    metadata=msg.metadata or {},
                    scope_id=session_id,
                )
                entries.append(entry)

            return entries

        except (HonchoClientError, ConnectionError, TimeoutError) as e:
            error_code = self._classify_error(e)
            raise MemoryQueryError(
                f"Failed to get character memories for {character_id}",
                details=MemoryErrorDetails(
                    operation="get_all",
                    entity_id=str(character_id),
                    error_code=error_code,
                    original_exception=e,
                    context={
                        "workspace_id": workspace_id,
                        "session_id": session_id,
                        "limit": limit,
                    },
                ),
            ) from e

    async def get_character_summary(
        self,
        character_id: UUID,
        workspace_id: str,
        session_id: str | None = None,
    ) -> str:
        """Get a summary of character's experiences.

        Args:
            character_id: The character UUID.
            workspace_id: The workspace ID.
            session_id: Optional session ID.

        Returns:
            A summary string.

        Raises:
            MemoryQueryError: If query operation fails.
        """
        if self._honcho is None:
            raise MemoryQueryError(
                "Honcho client not provided",
                details=MemoryErrorDetails(
                    operation="summarize",
                    entity_id=str(character_id),
                    error_code="CLIENT_NOT_INITIALIZED",
                ),
            )

        try:
            peer_id = str(character_id)

            # Get representation from Honcho
            representation = await self._honcho.get_peer_representation(
                workspace_id=workspace_id,
                peer_id=peer_id,
                session_id=session_id,
            )

            return representation

        except (HonchoClientError, ConnectionError, TimeoutError) as e:
            error_code = self._classify_error(e)
            raise MemoryQueryError(
                f"Failed to get character summary for {character_id}",
                details=MemoryErrorDetails(
                    operation="summarize",
                    entity_id=str(character_id),
                    error_code=error_code,
                    original_exception=e,
                    context={
                        "workspace_id": workspace_id,
                        "session_id": session_id,
                    },
                ),
            ) from e

    async def query_character(
        self,
        character_id: UUID,
        question: str,
        workspace_id: str,
        session_id: str | None = None,
    ) -> str:
        """Ask a natural language question about character's memories.

        Args:
            character_id: The character UUID.
            question: The question to ask.
            workspace_id: The workspace ID.
            session_id: Optional session ID.

        Returns:
            The response string.

        Raises:
            MemoryQueryError: If query operation fails.
        """
        if self._honcho is None:
            raise MemoryQueryError(
                "Honcho client not provided",
                details=MemoryErrorDetails(
                    operation="query",
                    entity_id=str(character_id),
                    error_code="CLIENT_NOT_INITIALIZED",
                ),
            )

        try:
            peer_id = str(character_id)

            response = await self._honcho.chat_with_peer(
                workspace_id=workspace_id,
                peer_id=peer_id,
                query=question,
                session_id=session_id,
            )

            return response

        except (HonchoClientError, ConnectionError, TimeoutError) as e:
            error_code = self._classify_error(e)
            raise MemoryQueryError(
                f"Failed to query character {character_id}",
                details=MemoryErrorDetails(
                    operation="query",
                    entity_id=str(character_id),
                    error_code=error_code,
                    original_exception=e,
                    context={
                        "workspace_id": workspace_id,
                        "session_id": session_id,
                        "question": question,
                    },
                ),
            ) from e

    def _classify_error(self, error: Exception) -> str:
        """Classify an exception into a standardized error code."""
        if isinstance(error, ConnectionError):
            return "CONNECTION_ERROR"
        elif isinstance(error, TimeoutError):
            return "TIMEOUT_ERROR"
        elif isinstance(error, HonchoClientError):
            return "HONCHO_CLIENT_ERROR"
        else:
            return "UNKNOWN_ERROR"
