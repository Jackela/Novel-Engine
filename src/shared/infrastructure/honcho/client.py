"""Honcho client wrapper.

Provides a Honcho client instance for the application,
supporting both cloud and self-hosted deployments.

This module uses dependency injection pattern instead of singleton
to avoid concurrency issues and enable better testability.
"""

from __future__ import annotations

import asyncio
import inspect
from typing import TYPE_CHECKING, Any

try:  # pragma: no cover - optional dependency
    from honcho import Honcho as _Honcho
except ImportError:  # pragma: no cover - optional dependency
    _Honcho = None

from .config import HonchoSettings
from .errors import HonchoClientError, HonchoErrorDetails
from .message_handler import HonchoMessageHandler
from .session_manager import HonchoSessionManager
from .workspace_manager import HonchoWorkspaceManager

if TYPE_CHECKING:
    from honcho.types import Message, Peer, Session, Workspace


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
        self._client: Any | None = None
        self._lock = asyncio.Lock()  # Instance-level lock for lazy initialization

        # Initialize managers
        self._workspace_manager = HonchoWorkspaceManager(
            self._get_client, self._classify_error
        )
        self._session_manager = HonchoSessionManager(
            self._get_client, self._classify_error
        )
        self._message_handler = HonchoMessageHandler(
            self._get_client, self._classify_error, self._settings
        )

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

    async def _get_client(self) -> Any:
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
                    if _Honcho is None:
                        raise HonchoClientError(
                            "Honcho package is not installed",
                            details=HonchoErrorDetails(
                                operation="initialize",
                                entity_id="honcho_client",
                                error_code="HONCHO_CLIENT_ERROR",
                                original_exception=ImportError(
                                    "honcho package is not installed"
                                ),
                            ),
                        )

                    try:
                        client_kwargs: dict[str, Any] = {
                            "base_url": self._settings.base_url,
                            "timeout": self._settings.timeout,
                        }

                        if self._settings.api_key:
                            client_kwargs["api_key"] = self._settings.api_key

                        self._client = _Honcho(**client_kwargs)
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

    # Workspace operations (delegate to workspace manager)
    async def get_or_create_workspace(
        self,
        workspace_id: str,
        name: str | None = None,
    ) -> "Workspace":
        """Get or create a workspace."""
        return await self._workspace_manager.get_or_create_workspace(workspace_id, name)

    async def get_or_create_peer(
        self,
        workspace_id: str,
        peer_id: str,
        name: str | None = None,
    ) -> "Peer":
        """Get or create a peer within a workspace."""
        return await self._workspace_manager.get_or_create_peer(
            workspace_id, peer_id, name
        )

    # Session operations (delegate to session manager)
    async def create_session(
        self,
        workspace_id: str,
        peer_id: str,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Session":
        """Create a new session for a peer."""
        return await self._session_manager.create_session(
            workspace_id, peer_id, session_id, metadata
        )

    async def get_session_context(
        self,
        workspace_id: str,
        session_id: str,
        tokens: int = 4000,
        summarize: bool = False,
    ) -> list[dict[str, Any]]:
        """Get session context for LLM consumption."""
        return await self._session_manager.get_session_context(
            workspace_id, session_id, tokens, summarize
        )

    # Message operations (delegate to message handler)
    async def add_message(
        self,
        workspace_id: str,
        session_id: str,
        content: str,
        is_user: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> "Message":
        """Add a message to a session."""
        return await self._message_handler.add_message(
            workspace_id, session_id, content, is_user, metadata
        )

    async def search_memories(
        self,
        workspace_id: str,
        peer_id: str,
        query: str,
        top_k: int | None = None,
        session_id: str | None = None,
    ) -> list["Message"]:
        """Search for similar memories."""
        return await self._message_handler.search_memories(
            workspace_id, peer_id, query, top_k, session_id
        )

    async def get_peer_representation(
        self,
        workspace_id: str,
        peer_id: str,
        session_id: str | None = None,
    ) -> str:
        """Get a peer's representation (insight summary)."""
        return await self._message_handler.get_peer_representation(
            workspace_id, peer_id, session_id
        )

    async def chat_with_peer(
        self,
        workspace_id: str,
        peer_id: str,
        query: str,
        session_id: str | None = None,
    ) -> str:
        """Chat with a peer's memory (dialectic API)."""
        return await self._message_handler.chat_with_peer(
            workspace_id, peer_id, query, session_id
        )

    async def health_check(self) -> bool:
        """Check whether the Honcho client can be initialized and probed."""
        try:
            client = await self._get_client()
        except HonchoClientError:
            return False

        for probe_name in ("health", "ping", "status"):
            probe = getattr(client, probe_name, None)
            if not callable(probe):
                continue

            try:
                result = probe()
                if inspect.isawaitable(result):
                    result = await result
                if isinstance(result, bool):
                    return result
                if hasattr(result, "ok"):
                    return bool(getattr(result, "ok"))
                return True
            except Exception:
                continue

        return True


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
