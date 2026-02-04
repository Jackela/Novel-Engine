"""
Tests for Prompt Router Endpoints

Warzone 4: AI Brain - BRAIN-015
Unit tests for the prompt management API endpoints.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers.prompts import router
from src.api.schemas import (
    PromptCreateRequest,
    PromptDetailResponse,
    PromptListResponse,
    PromptRenderRequest,
    PromptUpdateRequest,
)
from src.contexts.knowledge.domain.models.prompt_template import (
    ModelConfig,
    PromptTemplate,
    VariableDefinition,
    VariableType,
)
from src.contexts.knowledge.infrastructure.adapters.in_memory_prompt_repository import (
    InMemoryPromptRepository,
)


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
def mock_repository() -> InMemoryPromptRepository:
    """Create a mock repository with sample data."""
    repo = InMemoryPromptRepository()

    # Add sample prompts
    template1 = PromptTemplate(
        id="prompt-1",
        name="Test Prompt",
        content="Hello {{name}}!",
        description="A simple greeting prompt",
        tags=("test", "greeting"),
        variables=(
            VariableDefinition(
                name="name",
                type=VariableType.STRING,
                required=True,
                description="The name to greet",
            ),
        ),
        model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        version=1,
    )

    template2 = PromptTemplate(
        id="prompt-2",
        name="Story Generator",
        content="Write a {{genre}} story about {{topic}}.",
        description="Generate stories",
        tags=("creative", "story", "model:gpt-4"),
        variables=(
            VariableDefinition(
                name="genre",
                type=VariableType.STRING,
                required=True,
                description="Story genre",
            ),
            VariableDefinition(
                name="topic",
                type=VariableType.STRING,
                required=True,
                description="Story topic",
            ),
        ),
        model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        version=1,
    )

    # Save synchronously for test setup
    import asyncio

    async def setup() -> None:
        await repo.save(template1)
        await repo.save(template2)

    asyncio.run(setup())
    return repo


@pytest.fixture
def app_with_repo(mock_repository: InMemoryPromptRepository) -> FastAPI:
    """Create app with pre-populated repository."""
    app = FastAPI()

    # Mock the get_prompt_repository dependency
    async def get_repo_mock() -> InMemoryPromptRepository:
        return mock_repository

    from src.api.routers import prompts

    # Override the dependency
    app.dependency_overrides[prompts.get_prompt_repository] = get_repo_mock
    app.include_router(router, prefix="/api")

    return app


@pytest.fixture
def client_with_repo(app_with_repo: FastAPI) -> TestClient:
    """Create client with pre-populated repository."""
    return TestClient(app_with_repo)


class TestListPrompts:
    """Tests for GET /api/prompts"""

    def test_list_all_prompts(self, client_with_repo: TestClient) -> None:
        """Test listing all prompts."""
        response = client_with_repo.get("/api/prompts")
        assert response.status_code == 200

        data = response.json()
        assert "prompts" in data
        assert "total" in data
        assert data["total"] == 2
        assert len(data["prompts"]) == 2
        assert data["prompts"][0]["name"] == "Test Prompt"

    def test_list_prompts_with_tag_filter(self, client_with_repo: TestClient) -> None:
        """Test filtering prompts by tags."""
        response = client_with_repo.get("/api/prompts?tags=test")
        assert response.status_code == 200

        data = response.json()
        assert len(data["prompts"]) == 1
        assert data["prompts"][0]["name"] == "Test Prompt"

    def test_list_prompts_with_model_filter(self, client_with_repo: TestClient) -> None:
        """Test filtering prompts by model."""
        response = client_with_repo.get("/api/prompts?model=gpt-4")
        assert response.status_code == 200

        data = response.json()
        # Both prompts have model:gpt-4 tag
        assert data["total"] >= 1

    def test_list_prompts_with_limit(self, client_with_repo: TestClient) -> None:
        """Test pagination with limit."""
        response = client_with_repo.get("/api/prompts?limit=1")
        assert response.status_code == 200

        data = response.json()
        assert len(data["prompts"]) == 1
        assert data["limit"] == 1

    def test_list_prompts_with_offset(self, client_with_repo: TestClient) -> None:
        """Test pagination with offset."""
        response = client_with_repo.get("/api/prompts?offset=1")
        assert response.status_code == 200

        data = response.json()
        assert len(data["prompts"]) == 1
        assert data["offset"] == 1


class TestSearchPrompts:
    """Tests for GET /api/prompts/search"""

    def test_search_by_name(self, client_with_repo: TestClient) -> None:
        """Test searching prompts by name."""
        response = client_with_repo.get("/api/prompts/search?query=story")
        assert response.status_code == 200

        data = response.json()
        assert len(data["prompts"]) == 1
        assert data["prompts"][0]["name"] == "Story Generator"

    def test_search_by_description(self, client_with_repo: TestClient) -> None:
        """Test searching prompts by description."""
        response = client_with_repo.get("/api/prompts/search?query=greeting")
        assert response.status_code == 200

        data = response.json()
        assert len(data["prompts"]) == 1
        assert data["prompts"][0]["name"] == "Test Prompt"

    def test_search_empty_query(self, client_with_repo: TestClient) -> None:
        """Test search with empty query returns error."""
        response = client_with_repo.get("/api/prompts/search?query=")
        assert response.status_code == 400


class TestGetPromptTags:
    """Tests for GET /api/prompts/tags"""

    def test_get_all_tags(self, client_with_repo: TestClient) -> None:
        """Test getting all unique tags."""
        response = client_with_repo.get("/api/prompts/tags")
        assert response.status_code == 200

        data = response.json()
        assert "all" in data
        assert "model" in data
        assert "test" in data["all"]
        assert "greeting" in data["all"]
        assert "gpt-4" in data["model"]


class TestCreatePrompt:
    """Tests for POST /api/prompts"""

    def test_create_prompt(self, client_with_repo: TestClient) -> None:
        """Test creating a new prompt."""
        payload = {
            "name": "New Prompt",
            "content": "Write about {{topic}}.",
            "description": "A new test prompt",
            "tags": ["test", "new"],
            "variables": [
                {
                    "name": "topic",
                    "type": "string",
                    "required": True,
                    "description": "The topic to write about",
                }
            ],
        }
        response = client_with_repo.post("/api/prompts", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "New Prompt"
        assert data["content"] == "Write about {{topic}}."
        assert data["version"] == 1
        assert "id" in data

    def test_create_prompt_with_model_config(self, client_with_repo: TestClient) -> None:
        """Test creating a prompt with model configuration."""
        payload = {
            "name": "Configured Prompt",
            "content": "Generate {{type}} content.",
            "model_provider": "anthropic",
            "model_name": "claude-3-opus",
            "temperature": 0.5,
            "max_tokens": 2000,
            "variables": [
                {
                    "name": "type",
                    "type": "string",
                    "required": True,
                    "description": "Content type",
                }
            ],
        }
        response = client_with_repo.post("/api/prompts", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["model_config"]["provider"] == "anthropic"
        assert data["model_config"]["model_name"] == "claude-3-opus"
        assert data["model_config"]["temperature"] == 0.5
        assert data["model_config"]["max_tokens"] == 2000

    def test_create_prompt_invalid_variable_type(self, client_with_repo: TestClient) -> None:
        """Test creating prompt with invalid variable type."""
        payload = {
            "name": "Bad Prompt",
            "content": "Test {{var}}.",
            "variables": [
                {"name": "var", "type": "invalid_type", "required": True}
            ],
        }
        response = client_with_repo.post("/api/prompts", json=payload)
        assert response.status_code == 400


class TestGetPrompt:
    """Tests for GET /api/prompts/{id}"""

    def test_get_prompt_by_id(self, client_with_repo: TestClient) -> None:
        """Test getting a prompt by ID."""
        response = client_with_repo.get("/api/prompts/prompt-1")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == "prompt-1"
        assert data["name"] == "Test Prompt"
        assert data["content"] == "Hello {{name}}!"
        assert len(data["variables"]) == 1
        assert data["variables"][0]["name"] == "name"

    def test_get_prompt_not_found(self, client_with_repo: TestClient) -> None:
        """Test getting non-existent prompt returns 404."""
        response = client_with_repo.get("/api/prompts/nonexistent")
        assert response.status_code == 404


class TestUpdatePrompt:
    """Tests for PUT /api/prompts/{id}"""

    def test_update_prompt_creates_new_version(
        self, client_with_repo: TestClient
    ) -> None:
        """Test updating a prompt creates a new version."""
        payload = {
            "content": "Updated content for {{name}}!",
        }
        response = client_with_repo.put("/api/prompts/prompt-1", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["content"] == "Updated content for {{name}}!"
        assert data["version"] == 2  # New version
        assert data["parent_version_id"] == "prompt-1"

    def test_update_prompt_not_found(self, client_with_repo: TestClient) -> None:
        """Test updating non-existent prompt returns 404."""
        payload = {"content": "New content"}
        response = client_with_repo.put("/api/prompts/nonexistent", json=payload)
        assert response.status_code == 404

    def test_update_prompt_with_variables(self, client_with_repo: TestClient) -> None:
        """Test updating prompt variables."""
        payload = {
            "variables": [
                {
                    "name": "name",
                    "type": "string",
                    "required": True,
                    "description": "Updated description",
                },
                {
                    "name": "age",
                    "type": "integer",
                    "required": False,
                    "description": "Person's age",
                    "default_value": 25,  # Optional variables need a default value
                },
            ]
        }
        response = client_with_repo.put("/api/prompts/prompt-1", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert len(data["variables"]) == 2
        assert data["variables"][0]["description"] == "Updated description"


class TestDeletePrompt:
    """Tests for DELETE /api/prompts/{id}"""

    def test_delete_prompt(self, client_with_repo: TestClient) -> None:
        """Test soft deleting a prompt."""
        response = client_with_repo.delete("/api/prompts/prompt-1")
        assert response.status_code == 204

        # Verify it's deleted
        get_response = client_with_repo.get("/api/prompts/prompt-1")
        assert get_response.status_code == 404

    def test_delete_prompt_not_found(self, client_with_repo: TestClient) -> None:
        """Test deleting non-existent prompt returns 404."""
        response = client_with_repo.delete("/api/prompts/nonexistent")
        assert response.status_code == 404


class TestRenderPrompt:
    """Tests for POST /api/prompts/{id}/render"""

    def test_render_prompt(self, client_with_repo: TestClient) -> None:
        """Test rendering a prompt with variables."""
        payload = {
            "variables": [
                {"name": "name", "value": "Alice"}
            ]
        }
        response = client_with_repo.post("/api/prompts/prompt-1/render", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "Alice" in data["rendered"]
        assert data["template_name"] == "Test Prompt"
        assert "name" in data["variables_used"]
        assert data["token_count"] > 0

    def test_render_prompt_with_strict_mode(self, client_with_repo: TestClient) -> None:
        """Test rendering with strict mode raises error for missing variables."""
        payload = {
            "variables": [],
            "strict": True,
        }
        response = client_with_repo.post("/api/prompts/prompt-1/render", json=payload)
        assert response.status_code == 400  # Missing required 'name'

    def test_render_prompt_not_found(self, client_with_repo: TestClient) -> None:
        """Test rendering non-existent prompt returns 404."""
        payload = {"variables": []}
        response = client_with_repo.post("/api/prompts/nonexistent/render", json=payload)
        assert response.status_code == 404

    def test_render_prompt_multiple_variables(self, client_with_repo: TestClient) -> None:
        """Test rendering prompt with multiple variables."""
        payload = {
            "variables": [
                {"name": "genre", "value": "sci-fi"},
                {"name": "topic", "value": "space exploration"},
            ]
        }
        response = client_with_repo.post("/api/prompts/prompt-2/render", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "sci-fi" in data["rendered"]
        assert "space exploration" in data["rendered"]
        assert len(data["variables_used"]) == 2


class TestGetVersionHistory:
    """Tests for GET /api/prompts/{id}/versions"""

    def test_get_version_history(self, client_with_repo: TestClient) -> None:
        """Test getting version history."""
        response = client_with_repo.get("/api/prompts/prompt-1/versions")
        assert response.status_code == 200

        data = response.json()
        assert len(data["prompts"]) == 1
        assert data["prompts"][0]["version"] == 1

    def test_get_version_history_nonexistent(self, client_with_repo: TestClient) -> None:
        """Test version history for non-existent prompt returns 404."""
        response = client_with_repo.get("/api/prompts/nonexistent/versions")
        assert response.status_code == 404


class TestPromptsHealth:
    """Tests for GET /api/prompts/health"""

    def test_health_check(self, client_with_repo: TestClient) -> None:
        """Test health check endpoint."""
        response = client_with_repo.get("/api/prompts/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["repository_type"] == "InMemoryPromptRepository"
        assert data["total_prompts"] >= 0
        assert "timestamp" in data
