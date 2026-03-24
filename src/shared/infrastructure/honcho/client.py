"""Honcho client wrapper.

Provides a Honcho client instance for the application,
supporting both cloud and self-hosted deployments.

This module uses dependency injection pattern instead of singleton
to avoid concurrency issues and enable better testability.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from honcho import Honcho

from .config import HonchoSettings

if TYPE_CHECKING:
    from honcho.types import (
        Message,
        Peer,
        Session,
        Workspace,
    )


@dataclass
class HonchoErrorDetails:
    """Structured error details for Honcho operations.

    Attributes:
        operation: The operation being performed (e.g., "create_workspace").
        entity_id: The ID of the entity being operated on.
        error_code: Standardized error code (e.g., "CONNECTION_ERROR").
        original_exception: The original exception that was raised.
        context: Additional context information.
    """

    operation: str
    entity_id: str
    error_code: str
    original_exception: Optional[Exception] = None
    context: Optional[dict[str, Any]] = None


class HonchoClientError(Exception):
    """Exception raised by HonchoClient operations.

    Attributes:
        message: Human-readable error message.
        details: Structured error details.
        error_code: Standardized error code.
    """

    def __init__(
        self,
        message: str,
        details: Optional[HonchoErrorDetails] = None,
    ) -> None:
        super().__init__(message)
        self.details = details
        self.error_code = details.error_code if details else "UNKNOWN_ERROR"


class HonchoClient:
    """Honcho client wrapper with dependency injection.

    This class provides a unified interface for interacting with Honcho,
    abstracting away cloud vs self-hosted differences.

    Uses instance-level locking for thread-safe lazy initialization.

    Attributes:
        settings: Honcho configuration settings.
        client: The underlying Honcho client instance (lazily initialized).

    Example:
        >>> from src.shared.infrastructure.honcho import HonchoClient
        >>> client = HonchoClient(settings)
        >>> workspace = await client.get_or_create_workspace("my-story")
    """

    def __init__(self, settings: HonchoSettings | None = None) -> None:
        """Initialize the Honcho client.

        Args:
            settings: Honcho settings. If None, creates default settings.
        """
        self._settings = settings or HonchoSettings()
        self._client: Honcho | None = None
        self._lock = asyncio.Lock()  # Instance-level lock for lazy initialization

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

    async def _get_client(self) -> Honcho:
        """Get or create the Honcho client instance (lazy initialization).

        This method is thread-safe and uses double-checked locking pattern.

        Returns:
            The initialized Honcho client.

        Raises:
            HonchoClientError: If client initialization fails.
        """
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    try:
                        client_kwargs: dict[str, Any] = {
                            "base_url": self._settings.base_url,
                            "timeout": self._settings.timeout,
                        }

                        if self._settings.api_key:
                            client_kwargs["api_key"] = self._settings.api_key

                        self._client = Honcho(**client_kwargs)
                    except (ConnectionError, TimeoutError) as e:
                        raise HonchoClientError(
                            f"Failed to initialize Honcho client: {e}",
                            details=HonchoErrorDetails(
                                operation="initialize",
                                entity_id="honcho_client",
                                error_code=self._classify_error(e),
                                original_exception=e,
                            ),
                        ) from e
        return self._client

    @property
    def settings(self) -> HonchoSettings:
        """Get Honcho settings."""
        return self._settings

    def get_workspace_for_story(self, story_id: str) -> str:
        """Get workspace ID for a story using story-centric strategy.

        Args:
            story_id: The story identifier.

        Returns:
            Workspace identifier.
        """
        return self._settings.get_workspace_for_story(story_id)

    def get_workspace_for_character(
        self,
        character_id: str,
        story_id: str | None = None,
    ) -> str:
        """Get workspace ID for a character.

        Args:
            character_id: The character identifier.
            story_id: Optional story identifier for story-centric mode.

        Returns:
            Workspace identifier.
        """
        return self._settings.get_workspace_for_character(character_id, story_id)

    async def get_or_create_workspace(
        self,
        workspace_id: str,
        name: str | None = None,
    ) -> "Workspace":
        """Get or create a workspace.

        Args:
            workspace_id: Unique workspace identifier.
            name: Optional human-readable name.

        Returns:
            Workspace instance.

        Raises:
            HonchoClientError: If workspace operations fail.
        """
        client = await self._get_client()

        try:
            # Try to get existing workspace
            workspace = await client.workspaces.get(workspace_id)
            if workspace:
                return workspace
        except (ConnectionError, TimeoutError, HonchoClientError):
            # Workspace doesn't exist or connection issue, continue to create
            pass

        # Create new workspace
        try:
            workspace = await client.workspaces.create(
                workspace_id=workspace_id,
                name=name or workspace_id,
            )
            return workspace
        except (ConnectionError, TimeoutError) as e:
            raise HonchoClientError(
                f"Failed to create workspace {workspace_id}: {e}",
                details=HonchoErrorDetails(
                    operation="create_workspace",
                    entity_id=workspace_id,
                    error_code=self._classify_error(e),
                    original_exception=e,
                ),
            ) from e

    async def get_or_create_peer(
        self,
        workspace_id: str,
        peer_id: str,
        name: str | None = None,
    ) -> "Peer":
        """Get or create a peer within a workspace.

        Args:
            workspace_id: Workspace identifier.
            peer_id: Unique peer identifier (e.g., character ID).
            name: Optional human-readable name.

        Returns:
            Peer instance.

        Raises:
            HonchoClientError: If peer operations fail.
        """
        client = await self._get_client()

        try:
            peer = await client.peers.get(workspace_id, peer_id)
            if peer:
                return peer
        except (ConnectionError, TimeoutError, HonchoClientError):
            # Peer doesn't exist or connection issue, continue to create
            pass

        try:
            peer = await client.peers.create(
                workspace_id=workspace_id,
                peer_id=peer_id,
                name=name or peer_id,
            )
            return peer
        except (ConnectionError, TimeoutError) as e:
            raise HonchoClientError(
                f"Failed to create peer {peer_id}: {e}",
                details=HonchoErrorDetails(
                    operation="create_peer",
                    entity_id=peer_id,
                    error_code=self._classify_error(e),
                    original_exception=e,
                ),
            ) from e

    async def create_session(
        self,
        workspace_id: str,
        peer_id: str,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Session":
        """Create a new session for a peer.

        Args:
            workspace_id: Workspace identifier.
            peer_id: Peer identifier (character).
            session_id: Optional custom session ID.
            metadata: Optional session metadata.

        Returns:
            Session instance.

        Raises:
            HonchoClientError: If session creation fails.
        """
        client = await self._get_client()

        try:
            session = await client.sessions.create(
                workspace_id=workspace_id,
                peer_id=peer_id,
                session_id=session_id,
                metadata=metadata or {},
            )
            return session
        except (ConnectionError, TimeoutError) as e:
            raise HonchoClientError(
                f"Failed to create session for peer {peer_id}: {e}",
                details=HonchoErrorDetails(
                    operation="create_session",
                    entity_id=session_id or "auto-generated",
                    error_code=self._classify_error(e),
                    original_exception=e,
                    context={"workspace_id": workspace_id, "peer_id": peer_id},
                ),
            ) from e

    async def add_message(
        self,
        workspace_id: str,
        session_id: str,
        content: str,
        is_user: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> "Message":
        """Add a message to a session.

        This creates a memory entry that Honcho will process for reasoning.

        Args:
            workspace_id: Workspace identifier.
            session_id: Session identifier.
            content: Message content (the memory).
            is_user: Whether this is a user message (vs agent).
            metadata: Optional message metadata.

        Returns:
            Message instance.

        Raises:
            HonchoClientError: If message creation fails.
        """
        client = await self._get_client()

        try:
            message = await client.messages.create(
                workspace_id=workspace_id,
                session_id=session_id,
                content=content,
                is_user=is_user,
                metadata=metadata or {},
            )
            return message
        except (ConnectionError, TimeoutError) as e:
            raise HonchoClientError(
                f"Failed to add message to session {session_id}: {e}",
                details=HonchoErrorDetails(
                    operation="add_message",
                    entity_id=session_id,
                    error_code=self._classify_error(e),
                    original_exception=e,
                    context={
                        "workspace_id": workspace_id,
                        "content_length": len(content),
                    },
                ),
            ) from e

    async def search_memories(
        self,
        workspace_id: str,
        peer_id: str,
        query: str,
        top_k: int | None = None,
        session_id: str | None = None,
    ) -> list["Message"]:
        """Search for similar memories.

        Performs semantic search over a peer's memories.

        Args:
            workspace_id: Workspace identifier.
            peer_id: Peer identifier (character).
            query: Search query.
            top_k: Maximum results to return (default: settings.max_memories_per_query).
            session_id: Optional specific session to search within.

        Returns:
            List of matching messages/memories.

        Raises:
            HonchoClientError: If search operation fails.
        """
        client = await self._get_client()
        top_k = top_k or self._settings.max_memories_per_query

        try:
            if session_id:
                # Search within specific session
                results = await client.sessions.search(
                    workspace_id=workspace_id,
                    session_id=session_id,
                    query=query,
                    top_k=top_k,
                )
            else:
                # Search across all sessions for this peer
                results = await client.peers.search(
                    workspace_id=workspace_id,
                    peer_id=peer_id,
                    query=query,
                    top_k=top_k,
                )
            return results
        except (ConnectionError, TimeoutError) as e:
            raise HonchoClientError(
                f"Failed to search memories for peer {peer_id}: {e}",
                details=HonchoErrorDetails(
                    operation="search_memories",
                    entity_id=peer_id,
                    error_code=self._classify_error(e),
                    original_exception=e,
                    context={
                        "workspace_id": workspace_id,
                        "query": query,
                        "top_k": top_k,
                        "session_id": session_id,
                    },
                ),
            ) from e

    async def get_peer_representation(
        self,
        workspace_id: str,
        peer_id: str,
        session_id: str | None = None,
    ) -> str:
        """Get a peer's representation (insight summary).

        This is Honcho's synthesized understanding of the peer based on
        all observed interactions.

        Args:
            workspace_id: Workspace identifier.
            peer_id: Peer identifier.
            session_id: Optional specific session context.

        Returns:
            Representation text.

        Raises:
            HonchoClientError: If getting representation fails.
        """
        client = await self._get_client()

        try:
            if session_id:
                representation = await client.sessions.representation(
                    workspace_id=workspace_id,
                    session_id=session_id,
                    peer_id=peer_id,
                )
            else:
                representation = await client.peers.representation(
                    workspace_id=workspace_id,
                    peer_id=peer_id,
                )
            return representation.content if representation else ""
        except (ConnectionError, TimeoutError) as e:
            raise HonchoClientError(
                f"Failed to get representation for peer {peer_id}: {e}",
                details=HonchoErrorDetails(
                    operation="get_peer_representation",
                    entity_id=peer_id,
                    error_code=self._classify_error(e),
                    original_exception=e,
                    context={"workspace_id": workspace_id, "session_id": session_id},
                ),
            ) from e

    async def chat_with_peer(
        self,
        workspace_id: str,
        peer_id: str,
        query: str,
        session_id: str | None = None,
    ) -> str:
        """Chat with a peer's memory (dialectic API).

        Ask natural language questions about the peer's memories and
        get reasoned responses.

        Args:
            workspace_id: Workspace identifier.
            peer_id: Peer identifier.
            query: Natural language question.
            session_id: Optional session context.

        Returns:
            Chat response.

        Raises:
            HonchoClientError: If chat operation fails.
        """
        client = await self._get_client()

        try:
            if session_id:
                response = await client.sessions.chat(
                    workspace_id=workspace_id,
                    session_id=session_id,
                    peer_id=peer_id,
                    query=query,
                )
            else:
                response = await client.peers.chat(
                    workspace_id=workspace_id,
                    peer_id=peer_id,
                    query=query,
                )
            return response.content if response else ""
        except (ConnectionError, TimeoutError) as e:
            raise HonchoClientError(
                f"Failed to chat with peer {peer_id}: {e}",
                details=HonchoErrorDetails(
                    operation="chat_with_peer",
                    entity_id=peer_id,
                    error_code=self._classify_error(e),
                    original_exception=e,
                    context={
                        "workspace_id": workspace_id,
                        "session_id": session_id,
                        "query": query,
                    },
                ),
            ) from e

    async def get_session_context(
        self,
        workspace_id: str,
        session_id: str,
        tokens: int = 4000,
        summarize: bool = False,
    ) -> list[dict[str, Any]]:
        """Get session context for LLM consumption.

        Retrieves relevant messages and summaries up to a token limit.

        Args:
            workspace_id: Workspace identifier.
            session_id: Session identifier.
            tokens: Maximum tokens to return.
            summarize: Whether to include session summary.

        Returns:
            List of context messages suitable for LLM prompt.

        Raises:
            HonchoClientError: If getting session context fails.
        """
        client = await self._get_client()

        try:
            context = await client.sessions.context(
                workspace_id=workspace_id,
                session_id=session_id,
                tokens=tokens,
                summarize=summarize,
            )
            return context.to_openai() if hasattr(context, "to_openai") else []
        except (ConnectionError, TimeoutError) as e:
            raise HonchoClientError(
                f"Failed to get session context for {session_id}: {e}",
                details=HonchoErrorDetails(
                    operation="get_session_context",
                    entity_id=session_id,
                    error_code=self._classify_error(e),
                    original_exception=e,
                    context={
                        "workspace_id": workspace_id,
                        "tokens": tokens,
                        "summarize": summarize,
                    },
                ),
            ) from e


# Convenience function for creating a new client instance
def create_honcho_client(
    settings: HonchoSettings | None = None,
) -> HonchoClient:
    """Create a new Honcho client instance.

    This function creates a new client instance with the provided settings.
    Use dependency injection to share client instances across the application.

    Args:
        settings: Optional settings to override defaults.

    Returns:
        New HonchoClient instance.
    """
    return HonchoClient(settings)
