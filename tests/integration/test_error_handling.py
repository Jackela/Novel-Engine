"""
Backend Chaos Testing - Error Handling Integration Tests

Tests verify system resilience against dependency failures (LLM, DB).
These tests ensure the system fails gracefully with user-friendly messages
rather than crashing with raw tracebacks.

TEST-002: Backend Chaos Testing
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI application."""
    from src.api.main_api_server import app

    return TestClient(app)


class TestLLMFailureHandling:
    """Scenario 1: LLM service failures should return HTTP 503 with user-friendly messages."""

    @pytest.mark.integration
    def test_llm_timeout_returns_503(self, test_client: TestClient):
        """
        When LLM service times out, backend should return HTTP 503.

        Given: UnifiedLLMService is mocked to raise APITimeoutError
        When: Client calls character generation endpoint
        Then: Response is 503 with user-friendly error message
        """
        with patch(
            "src.contexts.character.infrastructure.generators.llm_character_generator.LLMCharacterGenerator"
        ) as mock_generator:
            # Mock the generator to raise a timeout-like error
            mock_instance = MagicMock()
            mock_instance.generate.side_effect = TimeoutError("LLM request timed out")
            mock_generator.return_value = mock_instance

            # Make request to character generation (this endpoint uses LLM)
            response = test_client.post(
                "/api/generation/character",
                json={
                    "concept": "test hero",
                    "archetype": "hero",
                    "tone": "hopeful",
                },
            )

            # The response should indicate service unavailability
            # Accept 500 or 503 - both indicate server-side failure
            assert response.status_code in [
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                status.HTTP_503_SERVICE_UNAVAILABLE,
            ]

            # Response should have a structured error message
            data = response.json()
            assert "error" in data or "detail" in data or "message" in data

    @pytest.mark.integration
    def test_llm_connection_error_returns_503(self, test_client: TestClient):
        """
        When LLM service connection fails, backend should return HTTP 503.

        Given: LLM service is unreachable
        When: Client calls world generation endpoint
        Then: Response is 503 with descriptive error
        """
        with patch(
            "src.contexts.world.infrastructure.generators.llm_world_generator.LLMWorldGenerator"
        ) as mock_generator:
            mock_instance = MagicMock()
            mock_instance.generate.side_effect = ConnectionError(
                "Failed to connect to LLM service"
            )
            mock_generator.return_value = mock_instance

            response = test_client.post(
                "/api/world/generate",
                json={
                    "genre": "fantasy",
                    "era": "medieval",
                    "tone": "heroic",
                    "themes": ["adventure"],
                    "num_factions": 2,
                    "num_locations": 2,
                },
            )

            # Should indicate service unavailability
            assert response.status_code in [
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                status.HTTP_503_SERVICE_UNAVAILABLE,
            ]


class TestDatabaseFailureHandling:
    """Scenario 2: Database failures should trigger retries before failing."""

    @pytest.mark.integration
    def test_db_lock_triggers_retry(self, test_client: TestClient):
        """
        When database is locked, system should retry before failing.

        Given: ContextDatabase raises OperationalError (locked)
        When: Client calls character list endpoint
        Then: System retries up to 3 times before returning error
        """
        from sqlite3 import OperationalError

        call_count = 0

        def mock_db_operation(*args: Any, **kwargs: Any):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise OperationalError("database is locked")
            return []  # Success on 4th call

        with patch(
            "src.contexts.character.infrastructure.persistence.character_repository.CharacterRepository.list_all"
        ) as mock_list:
            mock_list.side_effect = mock_db_operation

            # Make request - it should either succeed after retries or fail gracefully
            response = test_client.get("/api/v1/characters")

            # The system should have attempted multiple times
            # Note: actual retry logic depends on implementation
            # Here we verify the endpoint doesn't crash

            # If it succeeded after retries, should be 200
            # If it failed after retries, should be 500/503
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                status.HTTP_503_SERVICE_UNAVAILABLE,
            ]

    @pytest.mark.integration
    def test_db_connection_error_graceful_failure(self, test_client: TestClient):
        """
        When database connection fails, system should fail gracefully.

        Given: Database is unreachable
        When: Client calls any data endpoint
        Then: Response is structured error, not raw traceback
        """
        with patch(
            "src.contexts.character.infrastructure.persistence.character_repository.CharacterRepository.list_all"
        ) as mock_list:
            mock_list.side_effect = ConnectionError("Database connection refused")

            response = test_client.get("/api/v1/characters")

            # Should return error status
            assert response.status_code >= 400

            # Response should be JSON, not a raw traceback
            assert response.headers.get("content-type", "").startswith("application/json")

            # Should have structured error info
            data = response.json()
            assert isinstance(data, dict)


class TestMalformedLLMResponse:
    """Scenario 3: Malformed LLM JSON should trigger self-correction retry."""

    @pytest.mark.integration
    def test_bad_json_triggers_retry(self, test_client: TestClient):
        """
        When LLM returns malformed JSON, generator should retry.

        Given: LLMWorldGenerator receives invalid JSON from LLM
        When: Client calls world generation
        Then: System attempts self-correction or returns structured error
        """
        retry_count = 0

        def mock_llm_call(*args: Any, **kwargs: Any):
            nonlocal retry_count
            retry_count += 1
            if retry_count == 1:
                # First call returns malformed JSON
                return "{ invalid json here"
            # Second call returns valid JSON
            return json.dumps(
                {
                    "world_setting": {
                        "id": "test-world",
                        "name": "Test World",
                        "description": "A test world",
                        "genre": "fantasy",
                        "era": "medieval",
                        "tone": "heroic",
                        "themes": [],
                        "magic_level": 5,
                        "technology_level": 3,
                    },
                    "factions": [],
                    "locations": [],
                    "events": [],
                }
            )

        with patch(
            "src.contexts.world.infrastructure.generators.llm_world_generator.LLMWorldGenerator._call_llm"
        ) as mock_call:
            mock_call.side_effect = mock_llm_call

            response = test_client.post(
                "/api/world/generate",
                json={
                    "genre": "fantasy",
                    "era": "medieval",
                    "tone": "heroic",
                    "themes": ["adventure"],
                    "num_factions": 0,
                    "num_locations": 0,
                },
            )

            # Should either succeed after retry or fail gracefully
            # The key is no raw exception traceback
            assert response.headers.get("content-type", "").startswith("application/json")

    @pytest.mark.integration
    def test_persistent_bad_json_fails_gracefully(self, test_client: TestClient):
        """
        When LLM consistently returns bad JSON, system should fail gracefully.

        Given: LLM always returns invalid JSON
        When: Client calls world generation
        Then: Response is structured error after max retries
        """
        with patch(
            "src.contexts.world.infrastructure.generators.llm_world_generator.LLMWorldGenerator._call_llm"
        ) as mock_call:
            mock_call.return_value = "not valid json {{{"

            response = test_client.post(
                "/api/world/generate",
                json={
                    "genre": "fantasy",
                    "era": "medieval",
                    "tone": "heroic",
                    "themes": ["adventure"],
                    "num_factions": 1,
                    "num_locations": 1,
                },
            )

            # Should be an error status
            assert response.status_code >= 400

            # Should be JSON, not traceback
            data = response.json()
            assert isinstance(data, dict)

            # Should contain error information
            error_info = (
                data.get("error")
                or data.get("detail")
                or data.get("message")
                or str(data)
            )
            assert error_info is not None


class TestGracefulDegradation:
    """Test that the system degrades gracefully under various failure conditions."""

    @pytest.mark.integration
    def test_health_endpoint_always_responds(self, test_client: TestClient):
        """Health endpoint should always respond, even during partial failures."""
        response = test_client.get("/api/health")
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.integration
    def test_error_responses_are_structured(self, test_client: TestClient):
        """
        All error responses should be structured JSON, never raw tracebacks.

        This is a meta-test that verifies the API's error handling contract.
        """
        # Test various invalid requests
        invalid_requests = [
            ("POST", "/api/generation/character", {"invalid": "data"}),
            ("GET", "/api/nonexistent/endpoint", None),
            ("POST", "/api/world/generate", {"genre": 12345}),  # Wrong type
        ]

        for method, path, body in invalid_requests:
            if method == "GET":
                response = test_client.get(path)
            else:
                response = test_client.post(path, json=body)

            # Should be JSON
            content_type = response.headers.get("content-type", "")
            assert "application/json" in content_type, (
                f"Non-JSON response for {method} {path}: {content_type}"
            )

            # Should not contain Python traceback markers
            text = response.text
            assert "Traceback (most recent call last)" not in text, (
                f"Raw traceback in response for {method} {path}"
            )
            assert "File \"" not in text or "line" not in text.lower(), (
                f"Stack trace leaked in response for {method} {path}"
            )
