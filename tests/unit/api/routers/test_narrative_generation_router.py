"""Unit tests for the narrative generation streaming router.

Tests the SSE streaming endpoint for narrative generation,
including mock mode and error handling.
"""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.routers.narrative_generation import (
    GenerateStreamRequest,
    StreamChunk,
    is_mock_mode,
    router,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def client():
    """Create a test client for the narrative generation router."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


class TestIsMockMode:
    """Tests for the is_mock_mode function."""

    def test_mock_mode_true_when_env_true(self):
        """MOCK_LLM=true should enable mock mode."""
        with patch.dict(os.environ, {"MOCK_LLM": "true"}):
            assert is_mock_mode() is True

    def test_mock_mode_true_when_env_yes(self):
        """MOCK_LLM=yes should enable mock mode."""
        with patch.dict(os.environ, {"MOCK_LLM": "yes"}):
            assert is_mock_mode() is True

    def test_mock_mode_true_when_env_one(self):
        """MOCK_LLM=1 should enable mock mode."""
        with patch.dict(os.environ, {"MOCK_LLM": "1"}):
            assert is_mock_mode() is True

    def test_mock_mode_false_when_env_false(self):
        """MOCK_LLM=false should disable mock mode."""
        with patch.dict(os.environ, {"MOCK_LLM": "false"}):
            assert is_mock_mode() is False

    def test_mock_mode_false_when_env_empty(self):
        """MOCK_LLM='' should disable mock mode."""
        with patch.dict(os.environ, {"MOCK_LLM": ""}):
            assert is_mock_mode() is False

    def test_mock_mode_false_when_env_not_set(self):
        """Missing MOCK_LLM should disable mock mode."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear specific key if it exists
            os.environ.pop("MOCK_LLM", None)
            assert is_mock_mode() is False

    def test_mock_mode_case_insensitive(self):
        """MOCK_LLM check should be case insensitive."""
        with patch.dict(os.environ, {"MOCK_LLM": "TRUE"}):
            assert is_mock_mode() is True
        with patch.dict(os.environ, {"MOCK_LLM": "True"}):
            assert is_mock_mode() is True


class TestGenerateStreamRequestModel:
    """Tests for the GenerateStreamRequest Pydantic model."""

    def test_default_values(self):
        """Request should have sensible defaults."""
        request = GenerateStreamRequest()
        assert request.scene_id is None
        assert request.prompt is None
        assert request.context is None
        assert request.max_tokens == 500

    def test_custom_values(self):
        """Request should accept custom values."""
        request = GenerateStreamRequest(
            scene_id="test-scene-id",
            prompt="Write a dramatic scene",
            context="Fantasy setting",
            max_tokens=1000,
        )
        assert request.scene_id == "test-scene-id"
        assert request.prompt == "Write a dramatic scene"
        assert request.context == "Fantasy setting"
        assert request.max_tokens == 1000

    def test_max_tokens_minimum(self):
        """max_tokens should have a minimum of 50."""
        with pytest.raises(ValueError):
            GenerateStreamRequest(max_tokens=49)

    def test_max_tokens_maximum(self):
        """max_tokens should have a maximum of 4000."""
        with pytest.raises(ValueError):
            GenerateStreamRequest(max_tokens=4001)


class TestStreamChunkModel:
    """Tests for the StreamChunk Pydantic model."""

    def test_create_chunk_event(self):
        """Chunk events should have proper structure."""
        chunk = StreamChunk(type="chunk", content="Some text", sequence=0)
        assert chunk.type == "chunk"
        assert chunk.content == "Some text"
        assert chunk.sequence == 0

    def test_create_done_event(self):
        """Done events should have proper structure."""
        chunk = StreamChunk(type="done", content="", sequence=10)
        assert chunk.type == "done"
        assert chunk.content == ""
        assert chunk.sequence == 10

    def test_create_error_event(self):
        """Error events should have proper structure."""
        chunk = StreamChunk(type="error", content="Error message", sequence=-1)
        assert chunk.type == "error"
        assert chunk.content == "Error message"
        assert chunk.sequence == -1


class TestStreamEndpoint:
    """Tests for the /api/narrative/generate/stream endpoint."""

    def test_stream_returns_event_stream(self, client: TestClient):
        """Endpoint should return text/event-stream content type."""
        with patch.dict(os.environ, {"MOCK_LLM": "true"}):
            response = client.post(
                "/api/narrative/generate/stream",
                json={"max_tokens": 100},
            )
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

    def test_stream_returns_sse_format(self, client: TestClient):
        """Response should be in SSE format (data: ...\\n\\n)."""
        with patch.dict(os.environ, {"MOCK_LLM": "true"}):
            response = client.post(
                "/api/narrative/generate/stream",
                json={"max_tokens": 100},
            )
            content = response.text
            # SSE format has lines starting with "data: "
            assert "data: " in content

    def test_stream_contains_chunks(self, client: TestClient):
        """Stream should contain chunk events."""
        with patch.dict(os.environ, {"MOCK_LLM": "true"}):
            response = client.post(
                "/api/narrative/generate/stream",
                json={"max_tokens": 200},
            )
            content = response.text

            # Parse SSE events
            events = []
            for line in content.split("\n"):
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    events.append(data)

            # Should have at least one chunk and one done event
            chunk_events = [e for e in events if e.get("type") == "chunk"]
            done_events = [e for e in events if e.get("type") == "done"]

            assert len(chunk_events) > 0, "Should have at least one chunk event"
            assert len(done_events) == 1, "Should have exactly one done event"

    def test_stream_done_event_has_metadata(self, client: TestClient):
        """Done event should include generation metadata."""
        with patch.dict(os.environ, {"MOCK_LLM": "true"}):
            response = client.post(
                "/api/narrative/generate/stream",
                json={"max_tokens": 100},
            )
            content = response.text

            # Find the done event
            for line in content.split("\n"):
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if data.get("type") == "done":
                        assert "metadata" in data
                        metadata = data["metadata"]
                        assert "total_chunks" in metadata
                        assert "total_characters" in metadata
                        assert "generation_time_ms" in metadata
                        assert "mock_mode" in metadata
                        break

    def test_stream_chunks_have_sequence_numbers(self, client: TestClient):
        """Each chunk should have an incrementing sequence number."""
        with patch.dict(os.environ, {"MOCK_LLM": "true"}):
            response = client.post(
                "/api/narrative/generate/stream",
                json={"max_tokens": 300},
            )
            content = response.text

            # Parse and check sequence numbers
            sequences = []
            for line in content.split("\n"):
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if data.get("type") == "chunk":
                        sequences.append(data["sequence"])

            # Sequences should be increasing
            for i in range(1, len(sequences)):
                assert sequences[i] > sequences[i - 1], "Sequences should increase"

    def test_stream_accepts_empty_request(self, client: TestClient):
        """Endpoint should accept empty request body with defaults."""
        with patch.dict(os.environ, {"MOCK_LLM": "true"}):
            response = client.post(
                "/api/narrative/generate/stream",
                json={},
            )
            assert response.status_code == 200

    def test_stream_with_scene_id(self, client: TestClient):
        """Endpoint should accept scene_id parameter."""
        with patch.dict(os.environ, {"MOCK_LLM": "true"}):
            response = client.post(
                "/api/narrative/generate/stream",
                json={"scene_id": "test-scene-uuid", "max_tokens": 100},
            )
            assert response.status_code == 200

    def test_stream_with_prompt(self, client: TestClient):
        """Endpoint should accept custom prompt parameter."""
        with patch.dict(os.environ, {"MOCK_LLM": "true"}):
            response = client.post(
                "/api/narrative/generate/stream",
                json={"prompt": "Write a mystery scene", "max_tokens": 100},
            )
            assert response.status_code == 200

    def test_stream_has_correct_headers(self, client: TestClient):
        """Response should have proper SSE headers."""
        with patch.dict(os.environ, {"MOCK_LLM": "true"}):
            response = client.post(
                "/api/narrative/generate/stream",
                json={"max_tokens": 100},
            )
            assert response.headers.get("cache-control") == "no-cache"
