"""Memory session handler for Honcho adapter."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from src.contexts.character.domain.ports.memory_port import (
    MemoryErrorDetails,
    MemoryStorageError,
)
from src.shared.infrastructure.honcho import HonchoClientError

if TYPE_CHECKING:
    from src.shared.infrastructure.honcho import HonchoClient


class MemorySessionHandler:
    """Handles session management for character memories."""

    def __init__(self, honcho_client: HonchoClient | None = None) -> None:
        """Initialize the session handler.

        Args:
            honcho_client: Optional HonchoClient instance.
        """
        self._honcho = honcho_client
        self._session_cache: dict[
            tuple[str, str], str
        ] = {}  # (char_id, workspace) -> session_id

    def _get_or_create_session_id(
        self,
        character_id: UUID,
        workspace_id: str,
        session_id: str | None,
    ) -> str:
        """Get cached session ID or use provided one."""
        if session_id:
            return session_id

        cache_key = (str(character_id), workspace_id)
        if cache_key in self._session_cache:
            return self._session_cache[cache_key]

        # Generate default session ID
        default_session = f"default-{character_id}"
        self._session_cache[cache_key] = default_session
        return default_session

    def cache_session(
        self, character_id: UUID, workspace_id: str, session_id: str
    ) -> None:
        """Cache a session ID."""
        cache_key = (str(character_id), workspace_id)
        self._session_cache[cache_key] = session_id

    def clear_cache(self) -> None:
        """Clear the session cache."""
        self._session_cache.clear()

    async def create_session(
        self,
        character_id: UUID,
        story_id: str,
        workspace_id: str,
        session_name: str | None = None,
    ) -> str:
        """Create a new memory session for a character.

        Args:
            character_id: The character UUID.
            story_id: The story ID.
            workspace_id: The workspace ID.
            session_name: Optional session name.

        Returns:
            The session ID.

        Raises:
            MemoryStorageError: If session creation fails.
        """
        if self._honcho is None:
            raise MemoryStorageError(
                "Honcho client not provided",
                details=MemoryErrorDetails(
                    operation="create_scope",
                    entity_id=str(character_id),
                    error_code="CLIENT_NOT_INITIALIZED",
                ),
            )

        try:
            peer_id = str(character_id)

            # Ensure workspace and peer exist
            await self._honcho.get_or_create_workspace(workspace_id)
            await self._honcho.get_or_create_peer(workspace_id, peer_id)

            # Generate session ID
            session_id = (
                session_name
                or f"session-{character_id}-{datetime.utcnow().timestamp()}"
            )

            session = await self._honcho.create_session(
                workspace_id=workspace_id,
                peer_id=peer_id,
                session_id=session_id,
                metadata={},
            )

            # Cache the session
            self.cache_session(character_id, workspace_id, session.id)

            return session.id

        except (HonchoClientError, ConnectionError, TimeoutError) as e:
            error_code = self._classify_error(e)
            raise MemoryStorageError(
                f"Failed to create session for character {character_id}",
                details=MemoryErrorDetails(
                    operation="create_scope",
                    entity_id=str(character_id),
                    error_code=error_code,
                    original_exception=e,
                    context={
                        "story_id": story_id,
                        "session_name": session_name,
                    },
                ),
            ) from e

    async def get_session_context(
        self,
        character_id: UUID,
        session_id: str,
        workspace_id: str,
        tokens: int = 4000,
    ) -> list[dict[str, Any]]:
        """Get session context formatted for LLM consumption.

        Args:
            character_id: The character UUID.
            session_id: The session ID.
            workspace_id: The workspace ID.
            tokens: Maximum tokens to return.

        Returns:
            List of context dictionaries.

        Raises:
            MemoryQueryError: If getting context fails.
        """
        from src.contexts.character.domain.ports.memory_port import (
            MemoryErrorDetails,
            MemoryQueryError,
        )

        if self._honcho is None:
            raise MemoryQueryError(
                "Honcho client not provided",
                details=MemoryErrorDetails(
                    operation="get_context_for_llm",
                    entity_id=str(character_id),
                    error_code="CLIENT_NOT_INITIALIZED",
                ),
            )

        try:
            context = await self._honcho.get_session_context(
                workspace_id=workspace_id,
                session_id=session_id,
                tokens=tokens,
                summarize=True,
            )

            return context

        except (HonchoClientError, ConnectionError, TimeoutError) as e:
            error_code = self._classify_error(e)
            raise MemoryQueryError(
                f"Failed to get session context for character {character_id}",
                details=MemoryErrorDetails(
                    operation="get_context_for_llm",
                    entity_id=str(character_id),
                    error_code=error_code,
                    original_exception=e,
                    context={
                        "workspace_id": workspace_id,
                        "session_id": session_id,
                        "tokens": tokens,
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
