"""Tests for memory adapter components.

Tests the modular memory adapter implementation.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.contexts.character.domain.ports.memory_port import (
    MemoryQueryResult,
)
from src.contexts.character.infrastructure.adapters.memory_query_handler import (
    MemoryQueryHandler,
)
from src.contexts.character.infrastructure.adapters.memory_session_handler import (
    MemorySessionHandler,
)
from src.contexts.character.infrastructure.adapters.memory_storage_handler import (
    MemoryStorageHandler,
)


class TestMemoryStorageHandler:
    """Test MemoryStorageHandler."""

    @pytest.fixture
    def mock_honcho(self):
        """Create mock Honcho client."""
        honcho = AsyncMock()
        return honcho

    @pytest.fixture
    def handler(self, mock_honcho):
        """Create storage handler."""
        return MemoryStorageHandler(mock_honcho)

    @pytest.mark.asyncio
    async def test_get_or_create_session_id_provided(self, handler):
        """Test when session_id is provided."""
        char_id = uuid4()
        result = handler._get_or_create_session_id(char_id, "ws-123", "session-456")
        assert result == "session-456"

    @pytest.mark.asyncio
    async def test_get_or_create_session_id_cached(self, handler):
        """Test when session_id is cached."""
        char_id = uuid4()
        handler._session_cache[(str(char_id), "ws-123")] = "cached-session"
        result = handler._get_or_create_session_id(char_id, "ws-123", None)
        assert result == "cached-session"

    @pytest.mark.asyncio
    async def test_get_or_create_session_id_new(self, handler):
        """Test creating new session_id."""
        char_id = uuid4()
        result = handler._get_or_create_session_id(char_id, "ws-123", None)
        assert result == f"default-{char_id}"
        assert (str(char_id), "ws-123") in handler._session_cache

    @pytest.mark.asyncio
    async def test_clear_cache(self, handler):
        """Test clearing cache."""
        char_id = uuid4()
        handler._session_cache[(str(char_id), "ws-123")] = "session"
        handler.clear_cache()
        assert len(handler._session_cache) == 0


class TestMemoryQueryHandler:
    """Test MemoryQueryHandler."""

    @pytest.fixture
    def mock_honcho(self):
        """Create mock Honcho client."""
        honcho = AsyncMock()
        return honcho

    @pytest.fixture
    def handler(self, mock_honcho):
        """Create query handler."""
        return MemoryQueryHandler(mock_honcho)

    @pytest.mark.asyncio
    async def test_recall_success(self, handler, mock_honcho):
        """Test successful recall."""
        char_id = uuid4()
        mock_message = MagicMock()
        mock_message.id = "msg-123"
        mock_message.content = "Test memory"
        mock_message.created_at = datetime.utcnow()
        mock_message.metadata = {}

        mock_honcho.search_memories.return_value = [mock_message]

        result = await handler.recall(
            character_id=char_id,
            query="test",
            workspace_id="ws-123",
        )

        assert isinstance(result, MemoryQueryResult)
        assert len(result.memories) == 1
        assert result.memories[0].memory_id == "msg-123"
        assert result.query == "test"

    @pytest.mark.asyncio
    async def test_get_character_memories(self, handler, mock_honcho):
        """Test getting all character memories."""
        char_id = uuid4()
        mock_message = MagicMock()
        mock_message.id = "msg-123"
        mock_message.content = "Test memory"
        mock_message.created_at = datetime.utcnow()
        mock_message.metadata = {"key": "value"}

        mock_honcho.search_memories.return_value = [mock_message]

        result = await handler.get_character_memories(
            character_id=char_id,
            workspace_id="ws-123",
            limit=10,
        )

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].memory_id == "msg-123"
        assert result[0].metadata == {"key": "value"}


class TestMemorySessionHandler:
    """Test MemorySessionHandler."""

    @pytest.fixture
    def mock_honcho(self):
        """Create mock Honcho client."""
        honcho = AsyncMock()
        return honcho

    @pytest.fixture
    def handler(self, mock_honcho):
        """Create session handler."""
        return MemorySessionHandler(mock_honcho)

    @pytest.mark.asyncio
    async def test_create_session(self, handler, mock_honcho):
        """Test creating session."""
        char_id = uuid4()
        mock_session = MagicMock()
        mock_session.id = "session-123"
        mock_honcho.create_session.return_value = mock_session

        result = await handler.create_session(
            character_id=char_id,
            story_id="story-456",
            workspace_id="ws-123",
            session_name="Test Session",
        )

        assert result == "session-123"
        assert handler._session_cache[(str(char_id), "ws-123")] == "session-123"

    @pytest.mark.asyncio
    async def test_get_session_context(self, handler, mock_honcho):
        """Test getting session context."""
        char_id = uuid4()
        mock_context = [{"role": "user", "content": "Hello"}]
        mock_honcho.get_session_context.return_value = mock_context

        result = await handler.get_session_context(
            character_id=char_id,
            session_id="session-123",
            workspace_id="ws-123",
            tokens=1000,
        )

        assert result == mock_context
        mock_honcho.get_session_context.assert_called_once()

    def test_cache_session(self, handler):
        """Test caching session."""
        char_id = uuid4()
        handler.cache_session(char_id, "ws-123", "session-456")
        assert handler._session_cache[(str(char_id), "ws-123")] == "session-456"
