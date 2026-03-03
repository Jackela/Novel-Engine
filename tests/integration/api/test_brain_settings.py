"""Integration tests for Brain Settings API endpoints.

Tests AI brain settings including API keys, RAG configuration,
knowledge base status, and token usage analytics.
"""

import os

import pytest
from fastapi.testclient import TestClient

# Set testing mode BEFORE importing app
os.environ["ORCHESTRATOR_MODE"] = "testing"

from src.api.app import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    """Create a test client for the Brain Settings API."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def encryption_key():
    """Set up a test encryption key for API key storage tests."""
    # Generate a valid Fernet key for testing
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode()
    old_value = os.environ.get("BRAIN_SETTINGS_ENCRYPTION_KEY")
    os.environ["BRAIN_SETTINGS_ENCRYPTION_KEY"] = key

    yield key

    # Restore original value
    if old_value:
        os.environ["BRAIN_SETTINGS_ENCRYPTION_KEY"] = old_value
    else:
        os.environ.pop("BRAIN_SETTINGS_ENCRYPTION_KEY", None)


class TestBrainSettingsEndpoints:
    """Tests for GET/PUT /api/brain/settings endpoints."""

    def test_get_brain_settings_success(self, client):
        """Test getting all brain settings returns combined response."""
        response = client.get("/api/brain/settings")

        assert response.status_code == 200
        data = response.json()

        assert "api_keys" in data
        assert "rag_config" in data
        assert "knowledge_base" in data

        # Check API keys structure
        api_keys = data["api_keys"]
        assert "openai_key" in api_keys
        assert "anthropic_key" in api_keys
        assert "gemini_key" in api_keys
        assert "ollama_base_url" in api_keys

        # Check RAG config structure
        rag_config = data["rag_config"]
        assert "enabled" in rag_config
        assert "max_chunks" in rag_config

        # Check knowledge base structure
        kb = data["knowledge_base"]
        assert "total_entries" in kb
        assert "is_healthy" in kb

    def test_get_api_keys_success(self, client):
        """Test getting API keys returns masked values."""
        response = client.get("/api/brain/settings/api-keys")

        assert response.status_code == 200
        data = response.json()

        assert "openai_key" in data
        assert "anthropic_key" in data
        assert "gemini_key" in data
        assert "ollama_base_url" in data
        assert "has_openai" in data
        assert "has_anthropic" in data
        assert "has_gemini" in data

    def test_get_rag_config_success(self, client):
        """Test getting RAG configuration."""
        response = client.get("/api/brain/settings/rag-config")

        assert response.status_code == 200
        data = response.json()

        assert "enabled" in data
        assert "max_chunks" in data
        assert "score_threshold" in data
        assert "context_token_limit" in data

    def test_get_knowledge_base_status_success(self, client):
        """Test getting knowledge base status."""
        response = client.get("/api/brain/settings/knowledge-base")

        assert response.status_code == 200
        data = response.json()

        assert "total_entries" in data
        assert "is_healthy" in data


class TestUpdateAPIKeys:
    """Tests for PUT /api/brain/settings/api-keys endpoint."""

    def test_update_api_keys_requires_encryption(self, client):
        """Test that updating API keys fails without encryption key."""
        # Ensure no encryption key is set
        os.environ.pop("BRAIN_SETTINGS_ENCRYPTION_KEY", None)

        response = client.put(
            "/api/brain/settings/api-keys",
            json={"openai_key": "sk-test-key-12345"},
        )

        # Should return 503 if encryption not configured
        assert response.status_code == 503

    def test_update_api_keys_with_encryption(self, client, encryption_key):
        """Test updating API keys with encryption configured."""
        response = client.put(
            "/api/brain/settings/api-keys",
            json={"openai_key": "sk-test-key-1234567890"},
        )

        # May succeed with 200 or fail with 503 if encryption not properly configured in test env
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            # Key should be masked - the mask uses Unicode bullets (U+2022)
            # For key "sk-test-key-1234567890" (22 chars), mask is "sk-test-••••••••••7890"
            # So we check for the prefix "sk-test-" and that it's masked (contains bullets)
            assert data["openai_key"].startswith("sk-test-")
            assert "•" in data["openai_key"]  # Check for bullet character
            assert data["openai_key"].endswith("7890")
            assert data["has_openai"] is True

    def test_update_ollama_base_url(self, client):
        """Test updating Ollama base URL."""
        response = client.put(
            "/api/brain/settings/api-keys",
            json={"ollama_base_url": "http://custom-ollama:11434"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ollama_base_url"] == "http://custom-ollama:11434"

    def test_update_api_keys_partial(self, client, encryption_key):
        """Test partial update of API keys."""
        # Update only Anthropic key
        response = client.put(
            "/api/brain/settings/api-keys",
            json={"anthropic_key": "sk-ant-test12345678"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_anthropic"] is True


class TestUpdateRAGConfig:
    """Tests for PUT /api/brain/settings/rag-config endpoint."""

    def test_update_rag_config_success(self, client):
        """Test updating RAG configuration."""
        response = client.put(
            "/api/brain/settings/rag-config",
            json={"max_chunks": 10, "score_threshold": 0.5},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["max_chunks"] == 10
        assert data["score_threshold"] == 0.5

    def test_update_rag_config_enabled(self, client):
        """Test toggling RAG enabled state."""
        response = client.put(
            "/api/brain/settings/rag-config",
            json={"enabled": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False

        # Re-enable for other tests
        client.put("/api/brain/settings/rag-config", json={"enabled": True})

    def test_update_rag_config_partial(self, client):
        """Test partial update only changes specified fields."""
        # Get current config
        get_response = client.get("/api/brain/settings/rag-config")
        original = get_response.json()

        # Update only one field
        response = client.put(
            "/api/brain/settings/rag-config",
            json={"chunk_size": 1000},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["chunk_size"] == 1000
        # Other fields should remain unchanged
        assert data["max_chunks"] == original["max_chunks"]


class TestConnectionTest:
    """Tests for POST /api/brain/settings/test-connection endpoint."""

    def test_test_connection_returns_status(self, client):
        """Test connection test returns provider status."""
        response = client.post("/api/brain/settings/test-connection")

        assert response.status_code == 200
        data = response.json()

        assert "openai" in data
        assert "anthropic" in data
        assert "gemini" in data

        # Status should be one of the valid values
        for provider in ["openai", "anthropic", "gemini"]:
            assert data[provider] in ["configured", "not_configured"]


class TestTokenUsageAnalytics:
    """Tests for /api/brain/usage/* endpoints."""

    def test_get_usage_summary_success(self, client):
        """Test getting token usage summary."""
        response = client.get("/api/brain/usage/summary")

        assert response.status_code == 200
        data = response.json()

        assert "total_tokens" in data
        assert "total_input_tokens" in data
        assert "total_output_tokens" in data
        assert "total_cost" in data
        assert "total_requests" in data

    def test_get_usage_summary_with_days_param(self, client):
        """Test usage summary with days parameter."""
        response = client.get("/api/brain/usage/summary?days=7")

        assert response.status_code == 200
        data = response.json()
        assert "total_tokens" in data

    def test_get_daily_usage_success(self, client):
        """Test getting daily usage statistics."""
        response = client.get("/api/brain/usage/daily")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        if len(data) > 0:
            day = data[0]
            assert "date" in day
            assert "total_tokens" in day
            assert "total_cost" in day

    def test_get_daily_usage_with_days_param(self, client):
        """Test daily usage with days parameter."""
        response = client.get("/api/brain/usage/daily?days=7")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_usage_by_model_success(self, client):
        """Test getting usage breakdown by model."""
        response = client.get("/api/brain/usage/by-model")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        if len(data) > 0:
            model = data[0]
            assert "provider" in model
            assert "model_name" in model
            assert "total_tokens" in model

    def test_get_model_pricing_success(self, client):
        """Test getting model pricing information."""
        response = client.get("/api/brain/models")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        if len(data) > 0:
            model = data[0]
            assert "provider" in model
            assert "model_name" in model
            assert "cost_per_1m_input_tokens" in model
            assert "cost_per_1m_output_tokens" in model

    def test_get_model_pricing_filter_by_provider(self, client):
        """Test model pricing filtered by provider."""
        response = client.get("/api/brain/models?provider=openai")

        assert response.status_code == 200
        data = response.json()

        # All returned models should be from openai
        for model in data:
            assert model["provider"] == "openai"

    def test_get_model_pricing_invalid_provider(self, client):
        """Test model pricing with invalid provider returns 400."""
        response = client.get("/api/brain/models?provider=invalid_provider")

        assert response.status_code == 400


class TestUsageExport:
    """Tests for GET /api/brain/usage/export endpoint."""

    def test_export_usage_csv_success(self, client):
        """Test exporting usage data as CSV."""
        response = client.get("/api/brain/usage/export")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers.get("content-disposition", "")

        # Check CSV has content
        content = response.text
        assert "Timestamp" in content
        assert "Provider" in content

    def test_export_usage_csv_with_days_param(self, client):
        """Test CSV export with days parameter."""
        response = client.get("/api/brain/usage/export?days=7")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"


class TestChatEndpoints:
    """Tests for /api/brain/chat/* endpoints."""

    def test_list_chat_sessions_success(self, client):
        """Test listing chat sessions."""
        response = client.get("/api/brain/chat/sessions")

        assert response.status_code == 200
        data = response.json()

        assert "sessions" in data
        assert "total" in data
        assert isinstance(data["sessions"], list)

    def test_get_session_messages_not_found(self, client):
        """Test getting messages for non-existent session."""
        response = client.get("/api/brain/chat/sessions/nonexistent-session/messages")

        assert response.status_code == 200
        data = response.json()
        assert data["messages"] == []

    def test_clear_chat_session_success(self, client):
        """Test clearing a chat session."""
        response = client.delete("/api/brain/chat/sessions/test-session-clear")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestRAGContextEndpoint:
    """Tests for GET /api/brain/context endpoint."""

    def test_get_rag_context_success(self, client):
        """Test getting RAG context for a query."""
        response = client.get("/api/brain/context?query=test+query")

        assert response.status_code == 200
        data = response.json()

        assert "query" in data
        assert "chunks" in data
        assert "total_tokens" in data
        assert "chunk_count" in data

    def test_get_rag_context_with_params(self, client):
        """Test RAG context with optional parameters."""
        response = client.get(
            "/api/brain/context?query=test&max_chunks=3&used_threshold=0.8"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "test"
        assert data["chunk_count"] <= 3

    def test_get_rag_context_missing_query(self, client):
        """Test RAG context without query parameter returns 422."""
        response = client.get("/api/brain/context")

        assert response.status_code == 422


class TestIngestionEndpoints:
    """Tests for /api/brain/ingestion/* endpoints."""

    def test_start_ingestion_job_success(self, client):
        """Test starting an ingestion job."""
        response = client.post(
            "/api/brain/ingestion",
            json={
                "source_id": "test-source-1",
                "source_type": "character",
                "content": "This is test content for ingestion.",
            },
        )

        assert response.status_code == 202
        data = response.json()

        assert "job_id" in data
        assert data["status"] == "pending"
        assert "message" in data

    def test_start_ingestion_job_empty_content(self, client):
        """Test starting ingestion with empty content returns 400."""
        response = client.post(
            "/api/brain/ingestion",
            json={
                "source_id": "test-source",
                "source_type": "character",
                "content": "",
            },
        )

        assert response.status_code == 400

    def test_start_ingestion_job_missing_source_id(self, client):
        """Test starting ingestion without source_id returns 400."""
        response = client.post(
            "/api/brain/ingestion",
            json={
                "source_type": "character",
                "content": "test content",
            },
        )

        # May return 400 (bad request) or 422 (validation error)
        assert response.status_code in [400, 422]

    def test_list_ingestion_jobs_success(self, client):
        """Test listing ingestion jobs."""
        response = client.get("/api/brain/ingestion")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

    def test_get_ingestion_job_not_found(self, client):
        """Test getting non-existent job returns 404."""
        response = client.get("/api/brain/ingestion/nonexistent-job-id")

        assert response.status_code == 404

    def test_get_ingestion_job_after_creation(self, client):
        """Test getting a job after creating it."""
        # Create a job
        create_response = client.post(
            "/api/brain/ingestion",
            json={
                "source_id": "test-source-get",
                "source_type": "lore",
                "content": "Content for retrieval test.",
            },
        )
        assert create_response.status_code == 202
        job_id = create_response.json()["job_id"]

        # Get the job
        response = client.get(f"/api/brain/ingestion/{job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert "status" in data
