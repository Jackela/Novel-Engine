"""Tests for Honcho memory adapter.

Tests the HonchoMemoryAdapter implementation.
"""

import pytest
from datetime import datetime
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from src.contexts.character.domain.ports.memory_port import (
    MemoryEntry,
    MemoryQueryResult,
    MemoryStorageError,
    MemoryQueryError,
)
from src.contexts.character.infrastructure.adapters.honcho_memory_adapter import (
    HonchoMemoryAdapter,
)
from src.shared.infrastructure.honcho import HonchoClient, HonchoClientError


@pytest.fixture
def mock_honcho_client():
    """Create a mock Honcho client."""
    client = MagicMock(spec=HonchoClient)
    client.settings = MagicMock()
    client.settings.max_memories_per_query = 10
    client.settings.workspace_strategy = "story"
    client.settings.default_workspace_name = "novel-engine"
    client.get_workspace_for_character = MagicMock(
        side_effect=lambda character_id, story_id=None: (
            f"novel-engine-{story_id}"
            if story_id
            else f"novel-engine-character-{character_id}"
        )
    )
    client.get_workspace_for_story = MagicMock(
        side_effect=lambda story_id: f"novel-engine-{story_id}"
    )
    return client


@pytest.fixture
def adapter(mock_honcho_client):
    """Create an adapter with mock client."""
    adapter = HonchoMemoryAdapter(honcho_client=mock_honcho_client)
    return adapter


class TestHonchoMemoryAdapterRemember:
    """Tests for the remember method."""

    @pytest.mark.asyncio
    async def test_remember_success(self, adapter, mock_honcho_client) -> None:
        """Test successful memory storage."""
        character_id = uuid4()
        content = "Character discovered a hidden treasure"

        # Setup mock
        mock_message = MagicMock()
        mock_message.id = "msg-123"
        mock_message.content = content
        mock_message.created_at = datetime.utcnow()
        mock_message.metadata = {"importance": "high"}

        mock_honcho_client.get_or_create_workspace = AsyncMock()
        mock_honcho_client.get_or_create_peer = AsyncMock()
        mock_honcho_client.create_session = AsyncMock()
        mock_honcho_client.add_message = AsyncMock(return_value=mock_message)

        # Execute
        entry = await adapter.remember(
            character_id=character_id,
            content=content,
            metadata={"importance": "high"},
        )

        # Assert - directly check the returned entry
        assert entry.content == content
        assert entry.character_id == character_id
        assert entry.metadata["importance"] == "high"
        assert entry.memory_id == "msg-123"

    @pytest.mark.asyncio
    async def test_remember_with_story_id(self, adapter, mock_honcho_client) -> None:
        """Test memory storage with specific story_id."""
        character_id = uuid4()
        content = "Character met the wizard"
        story_id = "story-123"

        mock_message = MagicMock()
        mock_message.id = "msg-456"
        mock_message.content = content
        mock_message.created_at = datetime.utcnow()
        mock_message.metadata = {}

        mock_honcho_client.get_or_create_workspace = AsyncMock()
        mock_honcho_client.get_or_create_peer = AsyncMock()
        mock_honcho_client.create_session = AsyncMock()
        mock_honcho_client.add_message = AsyncMock(return_value=mock_message)

        entry = await adapter.remember(
            character_id=character_id,
            content=content,
            story_id=story_id,
        )

        assert entry.content == content
        # Verify workspace was used
        mock_honcho_client.get_or_create_workspace.assert_called_once_with(
            workspace_id=f"novel-engine-{story_id}",
            name=f"Story: novel-engine-{story_id}",
        )

    @pytest.mark.asyncio
    async def test_remember_error(self, adapter, mock_honcho_client) -> None:
        """Test error handling in remember."""
        character_id = uuid4()

        mock_honcho_client.get_or_create_workspace = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        with pytest.raises(MemoryStorageError) as exc_info:
            await adapter.remember(
                character_id=character_id,
                content="Test content",
            )

        assert "Failed to store memory" in str(exc_info.value)


class TestHonchoMemoryAdapterRecall:
    """Tests for the recall method."""

    @pytest.mark.asyncio
    async def test_recall_success(self, adapter, mock_honcho_client) -> None:
        """Test successful memory retrieval."""
        character_id = uuid4()
        query = "What did the character find?"

        # Setup mock
        mock_msg1 = MagicMock()
        mock_msg1.id = "msg-1"
        mock_msg1.content = "Found a golden key"
        mock_msg1.created_at = datetime.utcnow()
        mock_msg1.metadata = {}

        mock_msg2 = MagicMock()
        mock_msg2.id = "msg-2"
        mock_msg2.content = "Opened the chest"
        mock_msg2.created_at = datetime.utcnow()
        mock_msg2.metadata = {}

        mock_honcho_client.search_memories = AsyncMock(
            return_value=[mock_msg1, mock_msg2]
        )

        # Execute
        result = await adapter.recall(
            character_id=character_id,
            query=query,
            top_k=5,
        )

        # Assert - directly check the returned result
        assert isinstance(result, MemoryQueryResult)
        assert result.total_found == 2
        assert result.query == query
        assert len(result.memories) == 2
        assert result.memories[0].content == "Found a golden key"
        assert result.memories[1].content == "Opened the chest"

    @pytest.mark.asyncio
    async def test_recall_error(self, adapter, mock_honcho_client) -> None:
        """Test error handling in recall."""
        character_id = uuid4()

        mock_honcho_client.search_memories = AsyncMock(
            side_effect=Exception("Search failed")
        )

        with pytest.raises(MemoryQueryError) as exc_info:
            await adapter.recall(
                character_id=character_id,
                query="Test query",
            )

        assert "Failed to recall memories" in str(exc_info.value)


class TestHonchoMemoryAdapterGetCharacterMemories:
    """Tests for get_character_memories method."""

    @pytest.mark.asyncio
    async def test_get_all_memories(self, adapter, mock_honcho_client) -> None:
        """Test retrieving all character memories."""
        character_id = uuid4()

        mock_msg = MagicMock()
        mock_msg.id = "msg-test"
        mock_msg.content = "Test memory"
        mock_msg.created_at = datetime.utcnow()
        mock_msg.metadata = {"chapter": 1}

        mock_honcho_client.search_memories = AsyncMock(return_value=[mock_msg])

        entries = await adapter.get_character_memories(
            character_id=character_id,
            limit=50,
        )

        assert len(entries) == 1
        assert entries[0].content == "Test memory"
        assert entries[0].memory_id == "msg-test"


class TestHonchoMemoryAdapterCreateSession:
    """Tests for create_session method."""

    @pytest.mark.asyncio
    async def test_create_session_success(self, adapter, mock_honcho_client) -> None:
        """Test successful session creation."""
        character_id = uuid4()
        story_id = "test-story"

        mock_session = MagicMock()
        mock_session.id = "session-123"

        mock_honcho_client.get_or_create_workspace = AsyncMock()
        mock_honcho_client.get_or_create_peer = AsyncMock()
        mock_honcho_client.create_session = AsyncMock(return_value=mock_session)

        session_id = await adapter.create_session(
            character_id=character_id,
            story_id=story_id,
            session_name="chapter-1",
        )

        assert session_id == "session-123"


class TestHonchoMemoryAdapterGetCharacterSummary:
    """Tests for get_character_summary method."""

    @pytest.mark.asyncio
    async def test_get_summary_success(self, adapter, mock_honcho_client) -> None:
        """Test successful summary retrieval."""
        character_id = uuid4()

        mock_honcho_client.get_peer_representation = AsyncMock(
            return_value="A brave adventurer"
        )

        summary = await adapter.get_character_summary(
            character_id=character_id,
        )

        assert summary == "A brave adventurer"


class TestHonchoMemoryAdapterQueryCharacter:
    """Tests for query_character method."""

    @pytest.mark.asyncio
    async def test_query_success(self, adapter, mock_honcho_client) -> None:
        """Test successful memory query."""
        character_id = uuid4()
        question = "What is the character afraid of?"

        mock_honcho_client.chat_with_peer = AsyncMock(
            return_value="The character is afraid of heights"
        )

        answer = await adapter.query_character(
            character_id=character_id,
            question=question,
        )

        assert answer == "The character is afraid of heights"


class TestHonchoMemoryAdapterWorkspaceResolution:
    """Tests for workspace ID resolution."""

    def test_default_workspace_generation(self, adapter) -> None:
        """Test default workspace ID is generated from character ID."""
        character_id = uuid4()

        workspace_id = adapter._get_workspace_id(None, character_id)

        assert workspace_id == f"novel-engine-character-{character_id}"


class TestHonchoMemoryAdapterForget:
    """Tests for the forget method."""

    @pytest.mark.asyncio
    async def test_forget_returns_false(self, adapter) -> None:
        """Test that forget returns False (not implemented)."""
        character_id = uuid4()

        result = await adapter.forget(
            character_id=character_id,
            memory_id="msg-123",
        )

        assert result is False


class TestHonchoMemoryAdapterGetSessionContext:
    """Tests for get_session_context method."""

    @pytest.mark.asyncio
    async def test_get_session_context_success(
        self, adapter, mock_honcho_client
    ) -> None:
        """Test successful session context retrieval."""
        character_id = uuid4()
        session_id = "session-123"

        mock_context = MagicMock()
        mock_context.to_openai.return_value = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        mock_honcho_client.get_session_context = AsyncMock(
            return_value=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ]
        )

        context = await adapter.get_session_context(
            character_id=character_id,
            session_id=session_id,
            tokens=2000,
        )

        assert len(context) == 2
        mock_honcho_client.get_session_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_context_error(self, adapter, mock_honcho_client) -> None:
        """Test error handling in get_session_context."""
        character_id = uuid4()
        session_id = "session-123"

        mock_honcho_client.get_session_context = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        with pytest.raises(MemoryQueryError) as exc_info:
            await adapter.get_session_context(
                character_id=character_id,
                session_id=session_id,
            )

        assert "Failed to get session context" in str(exc_info.value)


class TestHonchoMemoryAdapterResolveHonchoFields:
    """Tests for _resolve_honcho_fields helper method."""

    def test_resolve_honcho_fields_with_story_id(
        self, adapter, mock_honcho_client
    ) -> None:
        """Test resolving Honcho fields with story_id."""
        character_id = uuid4()
        story_id = "story-456"
        session_id = "session-789"

        workspace_id, peer_id, resolved_session_id = adapter._resolve_honcho_fields(
            character_id=character_id,
            story_id=story_id,
            session_id=session_id,
        )

        assert workspace_id == f"novel-engine-{story_id}"
        assert peer_id == str(character_id)
        assert resolved_session_id == session_id

    def test_resolve_honcho_fields_without_story_id(
        self, adapter, mock_honcho_client
    ) -> None:
        """Test resolving Honcho fields without story_id."""
        character_id = uuid4()

        workspace_id, peer_id, resolved_session_id = adapter._resolve_honcho_fields(
            character_id=character_id,
            story_id=None,
            session_id=None,
        )

        assert workspace_id == f"novel-engine-character-{character_id}"
        assert peer_id == str(character_id)
        assert resolved_session_id.startswith("default-")

    def test_resolve_honcho_fields_caches_session(
        self, adapter, mock_honcho_client
    ) -> None:
        """Test that session IDs are cached."""
        character_id = uuid4()
        story_id = "story-123"

        # First call
        _, _, session1 = adapter._resolve_honcho_fields(
            character_id=character_id,
            story_id=story_id,
            session_id=None,
        )

        # Second call with same parameters should return cached session
        _, _, session2 = adapter._resolve_honcho_fields(
            character_id=character_id,
            story_id=story_id,
            session_id=None,
        )

        assert session1 == session2


class TestHonchoMemoryAdapterInitialize:
    """Tests for adapter initialization."""

    @pytest.mark.asyncio
    async def test_initialize_creates_client(self) -> None:
        """Test that initialize creates Honcho client if not provided."""
        adapter = HonchoMemoryAdapter(honcho_client=None)

        # Mock the get_instance method
        mock_client = MagicMock(spec=HonchoClient)
        with patch.object(
            HonchoClient, "get_instance", AsyncMock(return_value=mock_client)
        ):
            await adapter.initialize()
            assert adapter._honcho == mock_client

    @pytest.mark.asyncio
    async def test_initialize_uses_existing_client(
        self, adapter, mock_honcho_client
    ) -> None:
        """Test that initialize uses existing client."""
        existing_client = adapter._honcho
        await adapter.initialize()
        assert adapter._honcho == existing_client


class TestHonchoMemoryAdapterClose:
    """Tests for adapter close."""

    @pytest.mark.asyncio
    async def test_close_clears_caches(self, adapter) -> None:
        """Test that close clears workspace and session caches."""
        # Add some items to caches
        adapter._workspace_cache["test"] = "workspace"
        adapter._session_cache[("char", "ws")] = "session"

        await adapter.close()

        assert len(adapter._workspace_cache) == 0
        assert len(adapter._session_cache) == 0
