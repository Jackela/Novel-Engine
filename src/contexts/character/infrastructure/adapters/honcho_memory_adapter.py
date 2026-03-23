"""Honcho memory adapter implementation.

This module provides the concrete adapter that connects the character domain
to Honcho's semantic memory system.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from src.contexts.character.domain.ports.memory_port import (
    CharacterMemoryPort,
    MemoryEntry,
    MemoryQueryResult,
    MemoryStorageError,
    MemoryQueryError,
)
from src.shared.infrastructure.honcho import HonchoClient, HonchoClientError


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
        self._session_cache: dict[
            tuple[str, str], str
        ] = {}  # (char_id, workspace) -> session_id

    async def initialize(self) -> None:
        """Initialize the adapter by ensuring Honcho client is ready."""
        if self._honcho is None:
            self._honcho = await HonchoClient.get_instance()

    async def close(self) -> None:
        """Clean up resources."""
        self._workspace_cache.clear()
        self._session_cache.clear()

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
        resolved_session_id = self._get_or_create_session_id(
            character_id, workspace_id, session_id
        )
        return workspace_id, peer_id, resolved_session_id

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
        try:
            await self.initialize()
            assert self._honcho is not None

            # Resolve workspace from story_id
            workspace_id = self._get_workspace_id(story_id, character_id)

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
                session_id=resolved_session,
            )

            return entry

        except Exception as e:
            raise MemoryStorageError(f"Failed to store memory: {e}")

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
        try:
            await self.initialize()
            assert self._honcho is not None

            workspace_id = self._get_workspace_id(story_id, character_id)
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
                    session_id=session_id,
                )
                entries.append(entry)

            return MemoryQueryResult(
                memories=entries,
                query=query,
                total_found=len(entries),
            )

        except Exception as e:
            raise MemoryQueryError(f"Failed to recall memories: {e}")

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
        try:
            await self.initialize()
            assert self._honcho is not None

            workspace_id = self._get_workspace_id(story_id, character_id)
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
                    session_id=session_id,
                )
                entries.append(entry)

            return entries

        except Exception as e:
            raise MemoryQueryError(f"Failed to get character memories: {e}")

    async def create_session(
        self,
        character_id: UUID,
        story_id: str,
        session_name: str | None = None,
    ) -> str:
        """Create a new memory session for a character."""
        try:
            await self.initialize()
            assert self._honcho is not None

            workspace_id = self._get_workspace_id(story_id, character_id)
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
            cache_key = (str(character_id), workspace_id)
            self._session_cache[cache_key] = session.id

            return session.id

        except Exception as e:
            raise MemoryStorageError(f"Failed to create session: {e}")

    async def get_character_summary(
        self,
        character_id: UUID,
        story_id: str | None = None,
        session_id: str | None = None,
    ) -> str:
        """Get a summary of character's experiences."""
        try:
            await self.initialize()
            assert self._honcho is not None

            workspace_id = self._get_workspace_id(story_id, character_id)
            peer_id = str(character_id)

            # Get representation from Honcho
            representation = await self._honcho.get_peer_representation(
                workspace_id=workspace_id,
                peer_id=peer_id,
                session_id=session_id,
            )

            return representation

        except Exception as e:
            raise MemoryQueryError(f"Failed to get character summary: {e}")

    async def query_character(
        self,
        character_id: UUID,
        question: str,
        story_id: str | None = None,
        session_id: str | None = None,
    ) -> str:
        """Ask a natural language question about character's memories."""
        try:
            await self.initialize()
            assert self._honcho is not None

            workspace_id = self._get_workspace_id(story_id, character_id)
            peer_id = str(character_id)

            response = await self._honcho.chat_with_peer(
                workspace_id=workspace_id,
                peer_id=peer_id,
                query=question,
                session_id=session_id,
            )

            return response

        except Exception as e:
            raise MemoryQueryError(f"Failed to query character: {e}")

    async def get_session_context(
        self,
        character_id: UUID,
        session_id: str,
        story_id: str | None = None,
        tokens: int = 4000,
    ) -> list[dict[str, Any]]:
        """Get session context formatted for LLM consumption."""
        try:
            await self.initialize()
            assert self._honcho is not None

            workspace_id = self._get_workspace_id(story_id, character_id)

            context = await self._honcho.get_session_context(
                workspace_id=workspace_id,
                session_id=session_id,
                tokens=tokens,
                summarize=True,
            )

            return context

        except Exception as e:
            raise MemoryQueryError(f"Failed to get session context: {e}")
