"""Honcho client singleton.

Provides a singleton Honcho client instance for the entire application,
supporting both cloud and self-hosted deployments.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from honcho import Honcho

from .config import HonchoSettings

if TYPE_CHECKING:
    from honcho.types import (
        Message,
        Peer,
        Session,
        Workspace,
    )


class HonchoClientError(Exception):
    """Exception raised by HonchoClient operations."""

    pass


class HonchoClient:
    """Singleton Honcho client wrapper.

    This class provides a unified interface for interacting with Honcho,
    abstracting away cloud vs self-hosted differences.

    Attributes:
        settings: Honcho configuration settings.
        client: The underlying Honcho client instance.

    Example:
        >>> from src.shared.infrastructure.honcho import HonchoClient
        >>> client = HonchoClient()
        >>> workspace = await client.get_or_create_workspace("my-story")
    """

    _instance: HonchoClient | None = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __new__(cls, *args: Any, **kwargs: Any) -> HonchoClient:
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, settings: HonchoSettings | None = None) -> None:
        """Initialize the Honcho client.

        Args:
            settings: Honcho settings. If None, creates default settings.
        """
        if getattr(self, "_initialized", False):
            return

        self._settings = settings or HonchoSettings()

        # Initialize Honcho client
        client_kwargs: dict[str, Any] = {
            "base_url": self._settings.base_url,
            "timeout": self._settings.timeout,
        }

        if self._settings.api_key:
            client_kwargs["api_key"] = self._settings.api_key

        self._client = Honcho(**client_kwargs)
        self._initialized = True

    @property
    def client(self) -> Honcho:
        """Get the underlying Honcho client."""
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
        try:
            # Try to get existing workspace
            workspace = await self._client.workspaces.get(workspace_id)
            if workspace:
                return workspace
        except Exception:
            pass

        # Create new workspace
        try:
            workspace = await self._client.workspaces.create(
                workspace_id=workspace_id,
                name=name or workspace_id,
            )
            return workspace
        except Exception as e:
            raise HonchoClientError(f"Failed to create workspace {workspace_id}: {e}")

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
        try:
            peer = await self._client.peers.get(workspace_id, peer_id)
            if peer:
                return peer
        except Exception:
            pass

        try:
            peer = await self._client.peers.create(
                workspace_id=workspace_id,
                peer_id=peer_id,
                name=name or peer_id,
            )
            return peer
        except Exception as e:
            raise HonchoClientError(f"Failed to create peer {peer_id}: {e}")

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
        """
        try:
            session = await self._client.sessions.create(
                workspace_id=workspace_id,
                peer_id=peer_id,
                session_id=session_id,
                metadata=metadata or {},
            )
            return session
        except Exception as e:
            raise HonchoClientError(f"Failed to create session: {e}")

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
        """
        try:
            message = await self._client.messages.create(
                workspace_id=workspace_id,
                session_id=session_id,
                content=content,
                is_user=is_user,
                metadata=metadata or {},
            )
            return message
        except Exception as e:
            raise HonchoClientError(f"Failed to add message: {e}")

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
        """
        top_k = top_k or self._settings.max_memories_per_query

        try:
            if session_id:
                # Search within specific session
                results = await self._client.sessions.search(
                    workspace_id=workspace_id,
                    session_id=session_id,
                    query=query,
                    top_k=top_k,
                )
            else:
                # Search across all sessions for this peer
                results = await self._client.peers.search(
                    workspace_id=workspace_id,
                    peer_id=peer_id,
                    query=query,
                    top_k=top_k,
                )
            return results
        except Exception as e:
            raise HonchoClientError(f"Failed to search memories: {e}")

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
        """
        try:
            if session_id:
                representation = await self._client.sessions.representation(
                    workspace_id=workspace_id,
                    session_id=session_id,
                    peer_id=peer_id,
                )
            else:
                representation = await self._client.peers.representation(
                    workspace_id=workspace_id,
                    peer_id=peer_id,
                )
            return representation.content if representation else ""
        except Exception as e:
            raise HonchoClientError(f"Failed to get representation: {e}")

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
        """
        try:
            if session_id:
                response = await self._client.sessions.chat(
                    workspace_id=workspace_id,
                    session_id=session_id,
                    peer_id=peer_id,
                    query=query,
                )
            else:
                response = await self._client.peers.chat(
                    workspace_id=workspace_id,
                    peer_id=peer_id,
                    query=query,
                )
            return response.content if response else ""
        except Exception as e:
            raise HonchoClientError(f"Failed to chat with peer: {e}")

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
        """
        try:
            context = await self._client.sessions.context(
                workspace_id=workspace_id,
                session_id=session_id,
                tokens=tokens,
                summarize=summarize,
            )
            return context.to_openai() if hasattr(context, "to_openai") else []
        except Exception as e:
            raise HonchoClientError(f"Failed to get session context: {e}")

    @classmethod
    async def get_instance(
        cls,
        settings: HonchoSettings | None = None,
    ) -> HonchoClient:
        """Get or create the singleton instance asynchronously.

        Args:
            settings: Optional settings to use.

        Returns:
            HonchoClient singleton instance.
        """
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(settings)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None


# Convenience function
async def get_honcho_client(
    settings: HonchoSettings | None = None,
) -> HonchoClient:
    """Get the global Honcho client instance.

    Args:
        settings: Optional settings to override defaults.

    Returns:
        HonchoClient instance.
    """
    return await HonchoClient.get_instance(settings)
