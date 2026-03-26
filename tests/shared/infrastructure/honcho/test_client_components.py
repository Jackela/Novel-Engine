"""Tests for Honcho client components.

Tests the modular Honcho client implementation.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.shared.infrastructure.honcho.errors import (
    HonchoClientError,
    HonchoErrorDetails,
)
from src.shared.infrastructure.honcho.message_handler import (
    HonchoMessageHandler,
)
from src.shared.infrastructure.honcho.session_manager import (
    HonchoSessionManager,
)
from src.shared.infrastructure.honcho.workspace_manager import (
    HonchoWorkspaceManager,
)


class TestHonchoErrors:
    """Test error classes."""

    def test_error_details_creation(self):
        """Test HonchoErrorDetails creation."""
        details = HonchoErrorDetails(
            operation="create_workspace",
            entity_id="ws-123",
            error_code="CONNECTION_ERROR",
        )
        assert details.operation == "create_workspace"
        assert details.entity_id == "ws-123"
        assert details.error_code == "CONNECTION_ERROR"

    def test_client_error_creation(self):
        """Test HonchoClientError creation."""
        details = HonchoErrorDetails(
            operation="test_op",
            entity_id="test_id",
            error_code="TEST_ERROR",
        )
        error = HonchoClientError("Test message", details)
        assert str(error) == "Test message"
        assert error.error_code == "TEST_ERROR"
        assert error.details is details

    def test_client_error_without_details(self):
        """Test HonchoClientError without details."""
        error = HonchoClientError("Simple error")
        assert str(error) == "Simple error"
        assert error.error_code == "UNKNOWN_ERROR"
        assert error.details is None


class TestHonchoWorkspaceManager:
    """Test HonchoWorkspaceManager."""

    @pytest.fixture
    def mock_client(self):
        """Create mock Honcho client."""
        client = AsyncMock()
        return client

    @pytest.fixture
    def manager(self, mock_client):
        """Create workspace manager."""

        async def get_client():
            return mock_client

        def classify_error(e):
            return "TEST_ERROR"

        return HonchoWorkspaceManager(get_client, classify_error)

    @pytest.mark.asyncio
    async def test_get_or_create_workspace_existing(self, manager, mock_client):
        """Test getting existing workspace."""
        mock_workspace = MagicMock()
        mock_client.workspaces.get.return_value = mock_workspace

        result = await manager.get_or_create_workspace("test-ws")

        assert result is mock_workspace
        mock_client.workspaces.get.assert_called_once_with("test-ws")

    @pytest.mark.asyncio
    async def test_get_or_create_workspace_new(self, manager, mock_client):
        """Test creating new workspace."""
        mock_client.workspaces.get.return_value = None
        mock_workspace = MagicMock()
        mock_client.workspaces.create.return_value = mock_workspace

        result = await manager.get_or_create_workspace("test-ws", "Test Workspace")

        assert result is mock_workspace
        mock_client.workspaces.create.assert_called_once_with(
            workspace_id="test-ws",
            name="Test Workspace",
        )


class TestHonchoSessionManager:
    """Test HonchoSessionManager."""

    @pytest.fixture
    def mock_client(self):
        """Create mock Honcho client."""
        client = AsyncMock()
        return client

    @pytest.fixture
    def manager(self, mock_client):
        """Create session manager."""

        async def get_client():
            return mock_client

        def classify_error(e):
            return "TEST_ERROR"

        return HonchoSessionManager(get_client, classify_error)

    @pytest.mark.asyncio
    async def test_create_session(self, manager, mock_client):
        """Test creating session."""
        mock_session = MagicMock()
        mock_client.sessions.create.return_value = mock_session

        result = await manager.create_session(
            workspace_id="ws-123",
            peer_id="peer-456",
            session_id="session-789",
        )

        assert result is mock_session
        mock_client.sessions.create.assert_called_once()


class TestHonchoMessageHandler:
    """Test HonchoMessageHandler."""

    @pytest.fixture
    def mock_client(self):
        """Create mock Honcho client."""
        client = AsyncMock()
        return client

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.max_memories_per_query = 10
        return settings

    @pytest.fixture
    def handler(self, mock_client, mock_settings):
        """Create message handler."""

        async def get_client():
            return mock_client

        def classify_error(e):
            return "TEST_ERROR"

        return HonchoMessageHandler(get_client, classify_error, mock_settings)

    @pytest.mark.asyncio
    async def test_add_message(self, handler, mock_client):
        """Test adding message."""
        mock_message = MagicMock()
        mock_client.messages.create.return_value = mock_message

        result = await handler.add_message(
            workspace_id="ws-123",
            session_id="session-456",
            content="Test message",
        )

        assert result is mock_message
        mock_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_memories(self, handler, mock_client):
        """Test searching memories."""
        mock_results = [MagicMock(), MagicMock()]
        mock_client.peers.search.return_value = mock_results

        result = await handler.search_memories(
            workspace_id="ws-123",
            peer_id="peer-456",
            query="test query",
        )

        assert result is mock_results
        mock_client.peers.search.assert_called_once()
