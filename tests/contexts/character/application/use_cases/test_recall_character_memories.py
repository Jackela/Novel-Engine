"""Tests for recall character memories use case.

Tests the RecallCharacterMemories use case.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.contexts.character.application.use_cases.recall_character_memories import (
    MemoryRecallDTO,
    RecallCharacterMemoriesRequest,
    RecallCharacterMemoriesResponse,
    RecallCharacterMemoriesUseCase,
)
from src.contexts.character.domain.ports.memory_port import (
    CharacterMemoryPort,
    MemoryEntry,
    MemoryQueryError,
    MemoryQueryResult,
)


@pytest.fixture
def mock_memory_port():
    """Create a mock memory port."""
    port = MagicMock(spec=CharacterMemoryPort)
    return port


@pytest.fixture
def use_case(mock_memory_port):
    """Create use case with mock port."""
    return RecallCharacterMemoriesUseCase(memory_port=mock_memory_port)


class TestRecallCharacterMemoriesRequest:
    """Tests for the request DTO."""

    def test_valid_request(self) -> None:
        """Test creating a valid request."""
        request = RecallCharacterMemoriesRequest(
            character_id=uuid4(),
            query="What does the character know?",
            top_k=5,
            min_relevance=0.7,
        )

        assert request.query == "What does the character know?"
        assert request.top_k == 5
        assert request.min_relevance == 0.7

    def test_empty_query_raises_error(self) -> None:
        """Test that empty query raises error."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            RecallCharacterMemoriesRequest(
                character_id=uuid4(),
                query="",
            )

    def test_invalid_top_k(self) -> None:
        """Test that invalid top_k raises error."""
        with pytest.raises(ValueError, match="top_k must be between"):
            RecallCharacterMemoriesRequest(
                character_id=uuid4(),
                query="Test",
                top_k=0,
            )

        with pytest.raises(ValueError, match="top_k must be between"):
            RecallCharacterMemoriesRequest(
                character_id=uuid4(),
                query="Test",
                top_k=101,
            )

    def test_invalid_min_relevance(self) -> None:
        """Test that invalid min_relevance raises error."""
        with pytest.raises(ValueError, match="min_relevance must be between"):
            RecallCharacterMemoriesRequest(
                character_id=uuid4(),
                query="Test",
                min_relevance=-0.1,
            )

        with pytest.raises(ValueError, match="min_relevance must be between"):
            RecallCharacterMemoriesRequest(
                character_id=uuid4(),
                query="Test",
                min_relevance=1.1,
            )


class TestMemoryRecallDTO:
    """Tests for the memory DTO."""

    def test_from_memory_entry(self) -> None:
        """Test conversion from MemoryEntry."""
        entry = MemoryEntry(
            memory_id="mem-123",
            content="Character found a sword",
            character_id=uuid4(),
            scope_id="session-1",
            created_at=datetime.utcnow(),
            metadata={
                "chapter": 2,
                "importance": "high",
                "tags": ["item", "weapon"],
                "relevance_score": 0.95,
            },
        )

        dto = MemoryRecallDTO.from_memory_entry(entry)

        assert dto.memory_id == "mem-123"
        assert dto.content == "Character found a sword"
        assert dto.relevance_score == 0.95
        assert dto.chapter == 2
        assert dto.importance == "high"
        assert dto.tags == ["item", "weapon"]


class TestRecallCharacterMemoriesResponse:
    """Tests for the response DTO."""

    def test_to_prompt_context_with_memories(self) -> None:
        """Test context formatting with memories."""
        character_id = uuid4()

        memories = [
            MemoryRecallDTO(
                memory_id="m1",
                content="Found golden key",
                relevance_score=0.95,
                chapter=3,
                importance="high",
                tags=["item"],
                created_at="2024-01-01T00:00:00",
            ),
            MemoryRecallDTO(
                memory_id="m2",
                content="Opened the door",
                relevance_score=0.87,
                chapter=3,
                importance="medium",
                tags=[],
                created_at="2024-01-01T00:01:00",
            ),
        ]

        response = RecallCharacterMemoriesResponse(
            memories=memories,
            total_found=2,
            query="What did the character find?",
            character_id=character_id,
        )

        context = response.to_prompt_context()

        assert "## Character Memories" in context
        assert "Found golden key" in context
        assert "Opened the door" in context
        assert "(0.95)" in context  # Relevance score
        assert "Chapter 3" in context
        assert "high" in context

    def test_to_prompt_context_empty(self) -> None:
        """Test context formatting with no memories."""
        character_id = uuid4()

        response = RecallCharacterMemoriesResponse(
            memories=[],
            total_found=0,
            query="Unknown query",
            character_id=character_id,
        )

        context = response.to_prompt_context()

        assert "No relevant memories found" in context

    def test_to_prompt_context_with_limit(self) -> None:
        """Test context formatting with memory limit."""
        character_id = uuid4()

        memories = [
            MemoryRecallDTO(
                memory_id=f"m{i}",
                content=f"Memory {i}",
                relevance_score=0.9 - (i * 0.1),
                chapter=1,
                importance="medium",
                tags=[],
                created_at="2024-01-01T00:00:00",
            )
            for i in range(10)
        ]

        response = RecallCharacterMemoriesResponse(
            memories=memories,
            total_found=10,
            query="Test",
            character_id=character_id,
        )

        context = response.to_prompt_context(max_memories=3)

        # Should only include 3 memories
        assert context.count("Memory ") == 3


class TestRecallCharacterMemoriesUseCase:
    """Tests for the use case."""

    @pytest.mark.asyncio
    async def test_execute_success(self, use_case, mock_memory_port) -> None:
        """Test successful execution."""
        character_id = uuid4()

        mock_entries = [
            MemoryEntry(
                memory_id="m1",
                content="Memory 1",
                character_id=character_id,
                scope_id="session-1",
                created_at=datetime.utcnow(),
                metadata={"chapter": 1, "relevance_score": 0.95},
            ),
            MemoryEntry(
                memory_id="m2",
                content="Memory 2",
                character_id=character_id,
                scope_id="session-1",
                created_at=datetime.utcnow(),
                metadata={"relevance_score": 0.85},
            ),
        ]

        mock_result = MemoryQueryResult(
            memories=mock_entries,
            query="What happened?",
            total_found=2,
        )

        mock_memory_port.recall = AsyncMock(return_value=mock_result)

        request = RecallCharacterMemoriesRequest(
            character_id=character_id,
            query="What happened?",
            story_id="story-123",
            scope_id="session-1",
            top_k=5,
        )

        response = await use_case.execute(request)

        assert len(response.memories) == 2
        assert response.total_found == 2
        assert response.query == "What happened?"

        # Verify correct story_id was used
        call_kwargs = mock_memory_port.recall.call_args.kwargs
        assert call_kwargs["story_id"] == "story-123"

    @pytest.mark.asyncio
    async def test_execute_with_relevance_filter(
        self, use_case, mock_memory_port
    ) -> None:
        """Test that relevance filter is applied."""
        character_id = uuid4()

        mock_entries = [
            MemoryEntry(
                memory_id="m1",
                content="High relevance",
                character_id=character_id,
                scope_id="session-1",
                created_at=datetime.utcnow(),
                metadata={"relevance_score": 0.95},
            ),
            MemoryEntry(
                memory_id="m2",
                content="Low relevance",
                character_id=character_id,
                scope_id="session-1",
                created_at=datetime.utcnow(),
                metadata={"relevance_score": 0.30},
            ),
        ]

        mock_result = MemoryQueryResult(
            memories=mock_entries,
            query="Test",
            total_found=2,
        )

        mock_memory_port.recall = AsyncMock(return_value=mock_result)

        request = RecallCharacterMemoriesRequest(
            character_id=character_id,
            query="Test",
            min_relevance=0.50,
        )

        response = await use_case.execute(request)

        # Should only include memories above threshold
        assert len(response.memories) == 1
        assert response.memories[0].content == "High relevance"

    @pytest.mark.asyncio
    async def test_execute_propagates_query_error(
        self, use_case, mock_memory_port
    ) -> None:
        """Test that MemoryQueryError is propagated."""
        character_id = uuid4()

        mock_memory_port.recall = AsyncMock(
            side_effect=MemoryQueryError("Search failed")
        )

        request = RecallCharacterMemoriesRequest(
            character_id=character_id,
            query="Test query",
        )

        # Should raise the exception directly (no Result wrapper)
        with pytest.raises(MemoryQueryError) as exc_info:
            await use_case.execute(request)

        assert "Search failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_handles_generic_exception(
        self, use_case, mock_memory_port
    ) -> None:
        """Test that generic exceptions are wrapped in MemoryQueryError."""
        character_id = uuid4()

        mock_memory_port.recall = AsyncMock(side_effect=Exception("Unexpected error"))

        request = RecallCharacterMemoriesRequest(
            character_id=character_id,
            query="Test query",
        )

        # Should raise MemoryQueryError wrapping the original exception
        with pytest.raises(MemoryQueryError) as exc_info:
            await use_case.execute(request)

        assert "Failed to recall memories" in str(exc_info.value)
