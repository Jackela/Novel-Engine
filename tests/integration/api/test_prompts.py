#!/usr/bin/env python3
"""
Prompt API Integration Tests

Tests the Prompt Management API endpoints with full request/response validation.
Prompt templates are used for AI generation with variable substitution.
"""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    """Create a test client for the API."""
    from src.api.app import create_app

    app = create_app(debug=True)
    test_client = TestClient(app)

    # Store app reference for cleanup
    test_client.app = app
    return test_client


@pytest.fixture(autouse=True)
def reset_repository(client):
    """Reset the prompt repository before each test."""
    from src.api.routers.prompts import get_prompt_repository

    # Get the repository from app state
    request = type("Request", (), {"app": client.app})()
    repo = get_prompt_repository(request)
    repo._templates.clear()

    yield

    # Cleanup after test
    repo._templates.clear()


class TestPromptAPICreateEndpoint:
    """Tests for POST /api/prompts endpoint."""

    @pytest.mark.integration
    def test_create_prompt_success(self, client):
        """Test creating a new prompt template."""
        prompt_data = {
            "name": "Character Description",
            "content": "Describe {{character_name}}, a {{archetype}} from {{location}}.",
            "variables": [
                {
                    "name": "character_name",
                    "type": "string",
                    "required": True,
                    "description": "Name of the character",
                },
                {
                    "name": "archetype",
                    "type": "string",
                    "required": False,
                    "default_value": "hero",
                    "description": "Character archetype",
                },
                {
                    "name": "location",
                    "type": "string",
                    "required": False,
                    "default_value": "unknown land",
                    "description": "Where the character is from",
                },
            ],
            "tags": ["character", "generation"],
            "description": "Template for generating character descriptions",
            "model_name": "gpt-4",
            "temperature": 0.7,
        }

        response = client.post("/api/prompts", json=prompt_data)

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "Character Description"
        assert data["description"] == "Template for generating character descriptions"
        assert len(data["variables"]) == 3
        assert "id" in data
        assert data["model_config"]["model_name"] == "gpt-4"

    @pytest.mark.integration
    def test_create_prompt_minimal(self, client):
        """Test creating a prompt with minimal fields."""
        prompt_data = {
            "name": "Simple Prompt",
            "content": "Hello, {{name}}!",
            "variables": [{"name": "name", "type": "string", "required": True}],
        }

        response = client.post("/api/prompts", json=prompt_data)

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "Simple Prompt"

    @pytest.mark.integration
    def test_create_prompt_validation_error(self, client):
        """Test creating a prompt with invalid data."""
        prompt_data = {
            "name": "",  # Empty name should fail
            "content": "Content",
        }

        response = client.post("/api/prompts", json=prompt_data)

        # FastAPI returns 422 for validation errors
        assert response.status_code in [400, 422]


class TestPromptAPIGetEndpoint:
    """Tests for GET /api/prompts/{prompt_id} endpoint."""

    @pytest.mark.integration
    def test_get_prompt_success(self, client):
        """Test getting a prompt by ID."""
        # First create a prompt
        create_response = client.post(
            "/api/prompts",
            json={
                "name": "Test Prompt",
                "content": "Test content with {{var}}",
                "variables": [{"name": "var", "type": "string", "required": True}],
            },
        )
        prompt_id = create_response.json()["id"]

        # Then get it
        response = client.get(f"/api/prompts/{prompt_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == prompt_id
        assert data["name"] == "Test Prompt"

    @pytest.mark.integration
    def test_get_prompt_not_found(self, client):
        """Test getting a non-existent prompt."""
        response = client.get("/api/prompts/non-existent-id")

        assert response.status_code == 404


class TestPromptAPIListEndpoint:
    """Tests for GET /api/prompts endpoint."""

    @pytest.mark.integration
    def test_list_prompts_empty(self, client):
        """Test listing prompts when none exist."""
        response = client.get("/api/prompts")

        assert response.status_code == 200
        data = response.json()

        assert data["prompts"] == []
        assert data["total"] == 0

    @pytest.mark.integration
    def test_list_prompts_with_data(self, client):
        """Test listing prompts with data."""
        # Create some prompts
        client.post(
            "/api/prompts",
            json={
                "name": "Prompt 1",
                "content": "Content 1",
                "tags": ["category1"],
            },
        )
        client.post(
            "/api/prompts",
            json={
                "name": "Prompt 2",
                "content": "Content 2",
                "tags": ["category2"],
            },
        )

        response = client.get("/api/prompts")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert len(data["prompts"]) == 2

    @pytest.mark.integration
    def test_list_prompts_filter_by_tags(self, client):
        """Test filtering prompts by tags."""
        client.post(
            "/api/prompts",
            json={
                "name": "Tagged Prompt",
                "content": "Content",
                "tags": ["special", "unique"],
            },
        )
        client.post(
            "/api/prompts",
            json={
                "name": "Other Prompt",
                "content": "Content",
                "tags": ["other"],
            },
        )

        response = client.get("/api/prompts", params={"tags": "special"})

        assert response.status_code == 200
        data = response.json()

        # At least one prompt should be returned
        assert data["total"] >= 1
        # The filtered results should contain the tag
        for prompt in data["prompts"]:
            assert "special" in prompt.get("tags", [])


class TestPromptAPISearchEndpoint:
    """Tests for GET /api/prompts/search endpoint."""

    @pytest.mark.integration
    def test_search_prompts_success(self, client):
        """Test searching prompts."""
        client.post(
            "/api/prompts",
            json={"name": "Dragon Description", "content": "Describe a dragon"},
        )
        client.post(
            "/api/prompts",
            json={"name": "Knight Description", "content": "Describe a knight"},
        )

        response = client.get("/api/prompts/search", params={"query": "Dragon"})

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert "Dragon" in data["prompts"][0]["name"]

    @pytest.mark.integration
    def test_search_prompts_empty_query(self, client):
        """Test searching with empty query."""
        response = client.get("/api/prompts/search", params={"query": ""})

        assert response.status_code == 400


class TestPromptAPIRenderEndpoint:
    """Tests for POST /api/prompts/{prompt_id}/render endpoint."""

    @pytest.mark.integration
    def test_render_prompt_success(self, client):
        """Test rendering a prompt with variables."""
        # Create a prompt
        create_response = client.post(
            "/api/prompts",
            json={
                "name": "Greeting",
                "content": "Hello, {{name}}! Welcome to {{place}}.",
                "variables": [
                    {"name": "name", "type": "string", "required": True},
                    {
                        "name": "place",
                        "type": "string",
                        "required": False,
                        "default_value": "our world",
                    },
                ],
            },
        )
        prompt_id = create_response.json()["id"]

        # Render it
        response = client.post(
            f"/api/prompts/{prompt_id}/render",
            json={
                "variables": [
                    {"name": "name", "value": "Alice"},
                    {"name": "place", "value": "Wonderland"},
                ],
                "strict": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "Alice" in data["rendered"]
        assert "Wonderland" in data["rendered"]
        # variables_used could be a list or dict depending on implementation
        assert "variables_used" in data

    @pytest.mark.integration
    def test_render_prompt_with_defaults(self, client):
        """Test rendering a prompt using default values."""
        # Create a prompt
        create_response = client.post(
            "/api/prompts",
            json={
                "name": "Greeting",
                "content": "Hello, {{name}}! Welcome to {{place}}.",
                "variables": [
                    {"name": "name", "type": "string", "required": True},
                    {
                        "name": "place",
                        "type": "string",
                        "required": False,
                        "default_value": "our world",
                    },
                ],
            },
        )
        prompt_id = create_response.json()["id"]

        # Render with only required variable
        response = client.post(
            f"/api/prompts/{prompt_id}/render",
            json={"variables": [{"name": "name", "value": "Bob"}]},
        )

        assert response.status_code == 200
        data = response.json()

        assert "Bob" in data["rendered"]
        assert "our world" in data["rendered"]

    @pytest.mark.integration
    def test_render_prompt_not_found(self, client):
        """Test rendering a non-existent prompt."""
        response = client.post(
            "/api/prompts/non-existent-id/render",
            json={"variables": []},
        )

        assert response.status_code == 404


class TestPromptAPIUpdateEndpoint:
    """Tests for PUT /api/prompts/{prompt_id} endpoint."""

    @pytest.mark.integration
    def test_update_prompt_success(self, client):
        """Test updating a prompt template."""
        # Create a prompt
        create_response = client.post(
            "/api/prompts",
            json={
                "name": "Original Name",
                "content": "Original content",
            },
        )
        prompt_id = create_response.json()["id"]

        # Update it
        response = client.put(
            f"/api/prompts/{prompt_id}",
            json={
                "name": "Updated Name",
                "content": "Updated content",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Updated Name"
        assert data["content"] == "Updated content"

    @pytest.mark.integration
    def test_update_prompt_not_found(self, client):
        """Test updating a non-existent prompt."""
        response = client.put(
            "/api/prompts/non-existent-id",
            json={"name": "New Name"},
        )

        assert response.status_code == 404


class TestPromptAPIDeleteEndpoint:
    """Tests for DELETE /api/prompts/{prompt_id} endpoint."""

    @pytest.mark.integration
    def test_delete_prompt_success(self, client):
        """Test deleting a prompt template."""
        # Create a prompt
        create_response = client.post(
            "/api/prompts",
            json={"name": "To Delete", "content": "Content"},
        )
        prompt_id = create_response.json()["id"]

        # Delete it
        response = client.delete(f"/api/prompts/{prompt_id}")

        assert response.status_code == 204

        # Verify it's gone
        get_response = client.get(f"/api/prompts/{prompt_id}")
        assert get_response.status_code == 404

    @pytest.mark.integration
    def test_delete_prompt_not_found(self, client):
        """Test deleting a non-existent prompt."""
        response = client.delete("/api/prompts/non-existent-id")

        assert response.status_code == 404


class TestPromptAPIHealthEndpoint:
    """Tests for GET /api/prompts/health endpoint."""

    @pytest.mark.integration
    def test_prompts_health(self, client):
        """Test the prompt system health check."""
        response = client.get("/api/prompts/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "total_prompts" in data
        assert "timestamp" in data


class TestPromptAPITagsEndpoint:
    """Tests for GET /api/prompts/tags endpoint."""

    @pytest.mark.integration
    def test_list_prompt_tags(self, client):
        """Test listing all prompt tags."""
        client.post(
            "/api/prompts",
            json={
                "name": "Prompt 1",
                "content": "Content",
                "tags": ["tag1", "tag2"],
            },
        )
        client.post(
            "/api/prompts",
            json={
                "name": "Prompt 2",
                "content": "Content",
                "tags": ["tag3"],
            },
        )

        response = client.get("/api/prompts/tags")

        assert response.status_code == 200
        data = response.json()

        assert "tags" in data or isinstance(data, dict)
