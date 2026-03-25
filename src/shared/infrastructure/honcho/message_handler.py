"""Honcho message handler."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from .errors import HonchoClientError, HonchoErrorDetails

if TYPE_CHECKING:
    from honcho import Honcho
    from honcho.types import Message


class HonchoMessageHandler:
    """Handles message operations."""

    def __init__(
        self,
        get_client: Callable[..., Any],
        classify_error: Callable[..., Any],
        settings: Any,
    ) -> None:
        """Initialize the message handler.

        Args:
            get_client: Function to get the Honcho client.
            classify_error: Function to classify errors.
            settings: Honcho settings for configuration.
        """
        self._get_client = get_client
        self._classify_error = classify_error
        self._settings = settings

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
        client: Honcho = await self._get_client()

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
        client: Honcho = await self._get_client()
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
            return results if isinstance(results, list) else []
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
        client: Honcho = await self._get_client()

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
        client: Honcho = await self._get_client()

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
