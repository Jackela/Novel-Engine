"""Tests for character memory use cases.

Tests the RememberCharacterEvent use case.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.contexts.character.application.use_cases.remember_character_event import (
    RememberCharacterEventRequest,
    RememberCharacterEventUseCase,
)
from src.contexts.character.domain.ports.memory_port import (
    CharacterMemoryPort,
    MemoryEntry,
    MemoryStorageError,
)


@pytest.fixture
def mock_memory_port():
    """Create a mock memory port."""
    port = MagicMock(spec=CharacterMemoryPort)
    return port


@pytest.fixture
def use_case(mock_memory_port):
    """Create use case with mock port."""
    return RememberCharacterEventUseCase(memory_port=mock_memory_port)


class TestRememberCharacterEventRequest:
    """Tests for the request DTO."""

    def test_valid_request(self) -> None:
        """Test creating a valid request."""
        request = RememberCharacterEventRequest(
            character_id=uuid4(),
            content="Character discovered a secret passage",
            importance="high",
            chapter=3,
            tags=["discovery", "important"],
        )

        assert request.content == "Character discovered a secret passage"
        assert request.importance == "high"
        assert request.chapter == 3
        assert request.tags == ["discovery", "important"]

    def test_empty_content_raises_error(self) -> None:
        """Test that empty content raises error."""
        with pytest.raises(ValueError, match="Memory content cannot be empty"):
            RememberCharacterEventRequest(
                character_id=uuid4(),
                content="",
            )

    def test_whitespace_content_raises_error(self) -> None:
        """Test that whitespace-only content raises error."""
        with pytest.raises(ValueError, match="Memory content cannot be empty"):
            RememberCharacterEventRequest(
                character_id=uuid4(),
                content="   ",
            )

    def test_content_too_long(self) -> None:
        """Test that content over 10000 chars raises error."""
        with pytest.raises(ValueError, match="Memory content too long"):
            RememberCharacterEventRequest(
                character_id=uuid4(),
                content="x" * 10001,
            )

    def test_invalid_importance(self) -> None:
        """Test that invalid importance raises error."""
        with pytest.raises(ValueError, match="Invalid importance"):
            RememberCharacterEventRequest(
                character_id=uuid4(),
                content="Test content",
                importance="invalid",
            )


class TestRememberCharacterEventUseCase:
    """Tests for the use case."""

    @pytest.mark.asyncio
    async def test_execute_success(self, use_case, mock_memory_port) -> None:
        """Test successful execution."""
        character_id = uuid4()

        mock_entry = MagicMock(spec=MemoryEntry)
        mock_entry.memory_id = "mem-123"
        mock_entry.content = "Character fought the dragon"
        mock_entry.session_id = "session-456"
        mock_entry.created_at = datetime.utcnow()

        mock_memory_port.remember = AsyncMock(return_value=mock_entry)

        request = RememberCharacterEventRequest(
            character_id=character_id,
            content="Character fought the dragon",
            story_id="story-123",
            scope_id="session-456",
            importance="critical",
            chapter=5,
            tags=["combat", "boss"],
        )

        response = await use_case.execute(request)

        assert response.memory_id == "mem-123"
        assert response.content == "Character fought the dragon"
        assert response.workspace_id == "novel-engine-story-123"

        # Verify the port was called correctly
        call_args = mock_memory_port.remember.call_args
        assert call_args.kwargs["character_id"] == character_id
        assert call_args.kwargs["content"] == "Character fought the dragon"
        assert call_args.kwargs["story_id"] == "story-123"
        assert call_args.kwargs["metadata"]["importance"] == "critical"
        assert call_args.kwargs["metadata"]["chapter"] == 5
        assert call_args.kwargs["metadata"]["tags"] == ["combat", "boss"]

    @pytest.mark.asyncio
    async def test_execute_without_story_id(self, use_case, mock_memory_port) -> None:
        """Test execution without story ID."""
        character_id = uuid4()

        mock_entry = MagicMock(spec=MemoryEntry)
        mock_entry.memory_id = "mem-789"
        mock_entry.content = "Simple memory"
        mock_entry.session_id = "session-abc"
        mock_entry.created_at = datetime.utcnow()

        mock_memory_port.remember = AsyncMock(return_value=mock_entry)

        request = RememberCharacterEventRequest(
            character_id=character_id,
            content="Simple memory",
        )

        response = await use_case.execute(request)

        # Workspace ID should be auto-generated
        assert f"novel-engine-character-{character_id}" in response.workspace_id

    @pytest.mark.asyncio
    async def test_execute_propagates_storage_error(
        self, use_case, mock_memory_port
    ) -> None:
        """Test that MemoryStorageError is raised when storage fails."""
        character_id = uuid4()

        mock_memory_port.remember = AsyncMock(
            side_effect=MemoryStorageError("Storage failed")
        )

        request = RememberCharacterEventRequest(
            character_id=character_id,
            content="Test content",
        )

        # Should raise the exception directly (no Result wrapper)
        with pytest.raises(MemoryStorageError) as exc_info:
            await use_case.execute(request)

        assert "Storage failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_handles_generic_exception(
        self, use_case, mock_memory_port
    ) -> None:
        """Test that generic exceptions are wrapped in MemoryStorageError."""
        character_id = uuid4()

        mock_memory_port.remember = AsyncMock(side_effect=Exception("Unexpected error"))

        request = RememberCharacterEventRequest(
            character_id=character_id,
            content="Test content",
        )

        # Should raise MemoryStorageError wrapping the original exception
        with pytest.raises(MemoryStorageError) as exc_info:
            await use_case.execute(request)

        assert "INTERNAL_ERROR" in str(exc_info.value)
