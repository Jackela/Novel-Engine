"""Memory storage handler for Honcho adapter."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from src.contexts.character.domain.ports.memory_port import (
    MemoryEntry,
    MemoryErrorDetails,
    MemoryStorageError,
)
from src.shared.infrastructure.honcho import HonchoClientError

if TYPE_CHECKING:
    from src.shared.infrastructure.honcho import HonchoClient


class MemoryStorageHandler:
    """Handles store/delete operations for character memories."""

    def __init__(self, honcho_client: HonchoClient | None = None) -> None:
        """Initialize the storage handler.

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

    def clear_cache(self) -> None:
        """Clear the session cache."""
        self._session_cache.clear()

    async def store_memory(
        self,
        character_id: UUID,
        content: str,
        workspace_id: str,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Store a new memory for a character.

        Creates the workspace, peer, and session if they don't exist.

        Args:
            character_id: The character UUID.
            content: The memory content.
            workspace_id: The workspace ID.
            session_id: Optional session ID.
            metadata: Optional metadata.

        Returns:
            The created MemoryEntry.

        Raises:
            MemoryStorageError: If storage operation fails.
        """
        if self._honcho is None:
            raise MemoryStorageError(
                "Honcho client not provided",
                details=MemoryErrorDetails(
                    operation="store",
                    entity_id=str(character_id),
                    error_code="CLIENT_NOT_INITIALIZED",
                ),
            )

        try:
            # Ensure workspace exists
            await self._honcho.get_or_create_workspace(
                workspace_id=workspace_id,
                name=f"Story: {workspace_id}",
            )

            # Ensure peer exists (character as peer)
            peer_id = str(character_id)
            await self._honcho.get_or_create_peer(
                workspace_id=workspace_id,
                peer_id=peer_id,
                name=f"Character {character_id}",
            )

            # Resolve or create session
            resolved_session = self._get_or_create_session_id(
                character_id, workspace_id, session_id
            )

            # Ensure session exists (may fail if already exists, that's ok)
            try:
                await self._honcho.create_session(
                    workspace_id=workspace_id,
                    peer_id=peer_id,
                    session_id=resolved_session,
                    metadata={"character_id": str(character_id)},
                )
            except HonchoClientError:
                # Session might already exist, continue
                pass

            # Add memory as message
            message = await self._honcho.add_message(
                workspace_id=workspace_id,
                session_id=resolved_session,
                content=content,
                is_user=True,  # Character's experiences are "user" messages
                metadata=metadata or {},
            )

            # Create memory entry
            entry = MemoryEntry(
                memory_id=message.id,
                content=message.content,
                character_id=character_id,
                created_at=message.created_at or datetime.utcnow(),
                metadata=metadata or {},
                scope_id=resolved_session,
            )

            return entry

        except (HonchoClientError, ConnectionError, TimeoutError) as e:
            error_code = self._classify_error(e)
            raise MemoryStorageError(
                f"Failed to store memory for character {character_id}",
                details=MemoryErrorDetails(
                    operation="store",
                    entity_id=str(character_id),
                    error_code=error_code,
                    original_exception=e,
                    context={
                        "workspace_id": workspace_id,
                        "session_id": session_id,
                        "content_length": len(content),
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
