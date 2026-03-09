"""
Unit tests for Narratives Router API

Tests cover:
- POST /narratives/stream - Stream narrative generation via SSE
- SSE generator function
"""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers.narratives import _sse_generator, router
from src.api.schemas import NarrativeStreamRequest, WorldContext, WorldContextEntity

pytestmark = pytest.mark.unit


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app."""
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def valid_narrative_request() -> Dict[str, Any]:
    """Create a valid narrative stream request payload."""
    return {
        "prompt": "Write a scene where the hero enters the ancient temple.",
        "world_context": {
            "characters": [
                {
                    "id": "char_001",
                    "name": "Hero",
                    "type": "character",
                    "description": "A brave warrior",
                    "attributes": {"strength": "high"},
                }
            ],
            "locations": [
                {
                    "id": "loc_001",
                    "name": "Ancient Temple",
                    "type": "location",
                    "description": "A mysterious temple",
                    "attributes": {"atmosphere": "eerie"},
                }
            ],
            "entities": [],
            "current_scene": "The hero approaches the temple entrance",
            "narrative_style": "descriptive",
        },
        "chapter_title": "The Temple of Shadows",
        "tone": "mysterious",
        "max_tokens": 2000,
    }


class TestNarrativeStream:
    """Tests for POST /api/narratives/stream endpoint."""

    @patch("src.api.routers.narratives.generate_narrative_stream")
    def test_stream_narrative_success(
        self, mock_generate, client: TestClient, valid_narrative_request
    ) -> None:
        """Test successful narrative streaming."""
        # Setup mock to return chunks
        mock_chunk = MagicMock()
        mock_chunk.content = "The hero stepped forward."
        mock_chunk.sequence = 1
        mock_generate.return_value = [mock_chunk]

        response = client.post("/api/narratives/stream", json=valid_narrative_request)
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        assert response.headers["cache-control"] == "no-cache"
        assert response.headers["connection"] == "keep-alive"

    @patch("src.api.routers.narratives.generate_narrative_stream")
    def test_stream_narrative_multiple_chunks(
        self, mock_generate, client: TestClient, valid_narrative_request
    ) -> None:
        """Test streaming with multiple chunks."""
        chunks = []
        for i in range(3):
            chunk = MagicMock()
            chunk.content = f"Chunk {i + 1} content. "
            chunk.sequence = i + 1
            chunks.append(chunk)
        mock_generate.return_value = chunks

        response = client.post("/api/narratives/stream", json=valid_narrative_request)
        assert response.status_code == 200

        # Parse SSE events
        content = response.content.decode("utf-8")
        events = [line for line in content.split("\n\n") if line.startswith("data:")]

        # Should have chunk events + completion event
        assert len(events) >= 2  # At least one chunk + completion

    def test_stream_narrative_invalid_prompt(self, client: TestClient) -> None:
        """Test streaming with invalid prompt (too long)."""
        invalid_request = {
            "prompt": "x" * 5001,  # Exceeds max_length of 5000
            "world_context": {"characters": [], "locations": [], "entities": []},
        }

        response = client.post("/api/narratives/stream", json=invalid_request)
        assert response.status_code == 422

    def test_stream_narrative_invalid_max_tokens(self, client: TestClient) -> None:
        """Test streaming with invalid max_tokens."""
        invalid_request = {
            "prompt": "Test prompt",
            "world_context": {"characters": [], "locations": [], "entities": []},
            "max_tokens": 9000,  # Exceeds max of 8000
        }

        response = client.post("/api/narratives/stream", json=invalid_request)
        assert response.status_code == 422

    def test_stream_narrative_min_tokens(self, client: TestClient) -> None:
        """Test streaming with too few max_tokens."""
        invalid_request = {
            "prompt": "Test prompt",
            "world_context": {"characters": [], "locations": [], "entities": []},
            "max_tokens": 50,  # Below min of 100
        }

        response = client.post("/api/narratives/stream", json=invalid_request)
        assert response.status_code == 422

    def test_stream_narrative_missing_prompt(self, client: TestClient) -> None:
        """Test streaming without required prompt."""
        invalid_request = {
            "world_context": {"characters": [], "locations": [], "entities": []},
        }

        response = client.post("/api/narratives/stream", json=invalid_request)
        assert response.status_code == 422

    def test_stream_narrative_empty_prompt(self, client: TestClient) -> None:
        """Test streaming with empty prompt."""
        invalid_request = {
            "prompt": "",
            "world_context": {"characters": [], "locations": [], "entities": []},
        }

        response = client.post("/api/narratives/stream", json=invalid_request)
        assert response.status_code == 422

    @patch("src.api.routers.narratives.generate_narrative_stream")
    def test_stream_narrative_with_optional_fields(
        self, mock_generate, client: TestClient
    ) -> None:
        """Test streaming with all optional fields."""
        mock_chunk = MagicMock()
        mock_chunk.content = "Test content"
        mock_chunk.sequence = 1
        mock_generate.return_value = [mock_chunk]

        request = {
            "prompt": "Test prompt",
            "world_context": {
                "characters": [],
                "locations": [],
                "entities": [],
                "current_scene": "Test scene",
                "narrative_style": "dramatic",
            },
            "chapter_title": "Chapter 1",
            "tone": "dark",
            "max_tokens": 1500,
        }

        response = client.post("/api/narratives/stream", json=request)
        assert response.status_code == 200


class TestSSEGenerator:
    """Tests for the SSE generator function."""

    @pytest.mark.asyncio
    @patch("src.api.routers.narratives.generate_narrative_stream")
    async def test_sse_generator_basic(self, mock_generate) -> None:
        """Test basic SSE generation."""
        mock_chunk = MagicMock()
        mock_chunk.content = "Test content"
        mock_chunk.sequence = 1
        mock_generate.return_value = [mock_chunk]

        request = NarrativeStreamRequest(
            prompt="Test",
            world_context=WorldContext(),
        )

        events = []
        async for event in _sse_generator(request):
            events.append(event)

        # Should have chunk event and completion event
        assert len(events) == 2
        assert "chunk" in events[0]
        assert "done" in events[1]

    @pytest.mark.asyncio
    @patch("src.api.routers.narratives.generate_narrative_stream")
    async def test_sse_generator_multiple_chunks(self, mock_generate) -> None:
        """Test SSE generation with multiple chunks."""
        chunks = []
        for i in range(3):
            chunk = MagicMock()
            chunk.content = f"Content {i + 1} "
            chunk.sequence = i + 1
            chunks.append(chunk)
        mock_generate.return_value = chunks

        request = NarrativeStreamRequest(
            prompt="Test",
            world_context=WorldContext(),
        )

        events = []
        async for event in _sse_generator(request):
            events.append(event)

        # Should have 3 chunk events and 1 completion event
        assert len(events) == 4

    @pytest.mark.asyncio
    @patch("src.api.routers.narratives.generate_narrative_stream")
    async def test_sse_generator_error_handling(self, mock_generate) -> None:
        """Test SSE generator error handling."""
        mock_generate.side_effect = Exception("Generation failed")

        request = NarrativeStreamRequest(
            prompt="Test",
            world_context=WorldContext(),
        )

        events = []
        async for event in _sse_generator(request):
            events.append(event)

        # Should have error event
        assert len(events) == 1
        assert "error" in events[0]

    @pytest.mark.asyncio
    @patch("src.api.routers.narratives.generate_narrative_stream")
    async def test_sse_generator_metadata(self, mock_generate) -> None:
        """Test SSE generator includes metadata in completion."""
        mock_chunk = MagicMock()
        mock_chunk.content = "Test"
        mock_chunk.sequence = 1
        mock_generate.return_value = [mock_chunk]

        request = NarrativeStreamRequest(
            prompt="Test",
            world_context=WorldContext(),
        )

        events = []
        async for event in _sse_generator(request):
            events.append(event)

        # Parse the completion event
        completion_event = events[-1]
        data_str = completion_event.replace("data: ", "").strip()
        data = json.loads(data_str)

        assert data["type"] == "done"
        assert "metadata" in data
        assert "total_chunks" in data["metadata"]
        assert "total_characters" in data["metadata"]
        assert "generation_time_ms" in data["metadata"]
        assert "model_used" in data["metadata"]


class TestNarrativeSchemas:
    """Tests for narrative-related Pydantic schemas."""

    def test_world_context_entity(self) -> None:
        """Test WorldContextEntity schema."""
        entity = WorldContextEntity(
            id="char_001",
            name="Hero",
            type="character",
            description="A brave warrior",
            attributes={"strength": "high"},
        )

        assert entity.id == "char_001"
        assert entity.name == "Hero"
        assert entity.attributes == {"strength": "high"}

    def test_world_context_entity_defaults(self) -> None:
        """Test WorldContextEntity with default values."""
        entity = WorldContextEntity(
            id="loc_001",
            name="Town",
            type="location",
        )

        assert entity.description == ""
        assert entity.attributes == {}

    def test_world_context(self) -> None:
        """Test WorldContext schema."""
        char = WorldContextEntity(id="char_001", name="Hero", type="character")
        loc = WorldContextEntity(id="loc_001", name="Town", type="location")

        context = WorldContext(
            characters=[char],
            locations=[loc],
            entities=[],
            current_scene="Test scene",
            narrative_style="descriptive",
        )

        assert len(context.characters) == 1
        assert len(context.locations) == 1
        assert context.current_scene == "Test scene"

    def test_world_context_defaults(self) -> None:
        """Test WorldContext with default values."""
        context = WorldContext()

        assert context.characters == []
        assert context.locations == []
        assert context.entities == []
        assert context.current_scene is None
        assert context.narrative_style is None

    def test_narrative_stream_request(self) -> None:
        """Test NarrativeStreamRequest schema."""
        request = NarrativeStreamRequest(
            prompt="Write a scene",
            world_context=WorldContext(),
            chapter_title="Chapter 1",
            tone="dark",
            max_tokens=1500,
        )

        assert request.prompt == "Write a scene"
        assert request.chapter_title == "Chapter 1"
        assert request.tone == "dark"
        assert request.max_tokens == 1500

    def test_narrative_stream_request_defaults(self) -> None:
        """Test NarrativeStreamRequest default values."""
        request = NarrativeStreamRequest(
            prompt="Test",
            world_context=WorldContext(),
        )

        assert request.chapter_title is None
        assert request.tone is None
        assert request.max_tokens == 2000  # Default

    def test_narrative_stream_request_max_tokens_validation(self) -> None:
        """Test max_tokens validation."""
        # Valid values
        assert (
            NarrativeStreamRequest(
                prompt="Test", world_context=WorldContext(), max_tokens=100
            ).max_tokens
            == 100
        )
        assert (
            NarrativeStreamRequest(
                prompt="Test", world_context=WorldContext(), max_tokens=8000
            ).max_tokens
            == 8000
        )

    def test_narrative_stream_chunk(self) -> None:
        """Test NarrativeStreamChunk schema."""
        from src.api.schemas import NarrativeStreamChunk

        chunk = NarrativeStreamChunk(
            type="chunk",
            content="Test content",
            sequence=1,
        )

        assert chunk.type == "chunk"
        assert chunk.content == "Test content"
        assert chunk.sequence == 1

    def test_narrative_stream_chunk_defaults(self) -> None:
        """Test NarrativeStreamChunk default sequence."""
        from src.api.schemas import NarrativeStreamChunk

        chunk = NarrativeStreamChunk(type="chunk", content="Test")

        assert chunk.sequence == 0
