#!/usr/bin/env python3
"""
Memory API Integration Tests

Tests the Memory API endpoints with full request/response validation.
Memories are immutable event logs representing character experiences.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from datetime import datetime

pytestmark = pytest.mark.integration


memory_now = datetime.now().isoformat()


@pytest.fixture
def client():
    """Create a test client for the API with mock character store."""
    from src.api.app import create_app

    app = create_app(debug=True)

    # Mock the workspace character store
    mock_store = MagicMock()

    # Create a mock character with memories
    mock_character = {
        "id": "test-char-001",
        "name": "Test Hero",
        "structured_data": {
            "memories": [
                {
                    "memory_id": "existing-memory-001",
                    "content": "I remember the great battle",
                    "importance": 9,
                    "tags": ["battle", "important"],
                    "timestamp": "2024-01-01T00:00:00",
                },
                {
                    "memory_id": "minor-memory-001",
                    "content": "I had breakfast",
                    "importance": 3,
                    "tags": ["daily"],
                    "timestamp": "2024-01-02T00:00:00",
                },
            ]
        },
    }

    def mock_get(workspace_id, character_id):
        if character_id == "test-char-001":
            return mock_character
        elif character_id == "not-found":
            return None
        return mock_character

    def mock_update(workspace_id, character_id, updates):
        if updates.get("structured_data"):
            mock_character["structured_data"] = updates["structured_data"]
        return True

    mock_store.get = mock_get
    mock_store.update = mock_update

    # Set the mock store on app state
    app.state.workspace_character_store = mock_store

    # Mock workspace_id dependency
    from src.api import deps

    original_get_optional = deps.get_optional_workspace_id
    original_require = deps.require_workspace_id

    async def mock_get_optional_workspace_id():
        return "test-workspace"

    async def mock_require_workspace_id():
        return "test-workspace"

    deps.get_optional_workspace_id = lambda: mock_get_optional_workspace_id()
    deps.require_workspace_id = lambda: mock_require_workspace_id()

    yield TestClient(app)

    # Restore original functions
    deps.get_optional_workspace_id = original_get_optional
    deps.require_workspace_id = original_require


class TestMemoryAPIListEndpoints:
    """Tests for GET /api/characters/{character_id}/memories endpoints."""

    @pytest.mark.integration
    def test_get_character_memories_success(self, client):
        """Test getting all memories for a character."""
        response = client.get(
            "/api/characters/test-char-001/memories",
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["character_id"] == "test-char-001"
        assert data["total_count"] == 2
        assert data["core_memory_count"] == 1  # importance > 8
        assert len(data["memories"]) == 2

    @pytest.mark.integration
    def test_get_character_memories_filter_by_tag(self, client):
        """Test filtering memories by tag."""
        response = client.get(
            "/api/characters/test-char-001/memories",
            params={"tag": "battle"},
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 1
        assert "battle" in data["memories"][0]["tags"]

    @pytest.mark.integration
    def test_get_character_memories_filter_by_importance(self, client):
        """Test filtering memories by minimum importance."""
        response = client.get(
            "/api/characters/test-char-001/memories",
            params={"min_importance": 5},
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 1  # Only the importance 9 memory
        assert data["memories"][0]["importance"] >= 5

    @pytest.mark.integration
    def test_get_character_memories_character_not_found(self, client):
        """Test getting memories for non-existent character."""
        response = client.get(
            "/api/characters/not-found/memories",
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 404

    @pytest.mark.integration
    def test_get_character_memories_importance_levels(self, client):
        """Test that importance_level field is calculated correctly."""
        response = client.get(
            "/api/characters/test-char-001/memories",
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check importance levels
        for memory in data["memories"]:
            if memory["importance"] <= 3:
                assert memory["importance_level"] == "minor"
            elif memory["importance"] <= 6:
                assert memory["importance_level"] == "moderate"
            elif memory["importance"] <= 8:
                assert memory["importance_level"] == "significant"
            else:
                assert memory["importance_level"] == "core"
                assert memory["is_core_memory"] is True


class TestMemoryAPICreateEndpoint:
    """Tests for POST /api/characters/{character_id}/memories endpoint."""

    @pytest.mark.integration
    def test_create_memory_success(self, client):
        """Test creating a new memory for a character."""
        memory_data = {
            "content": "I witnessed a magical event",
            "importance": 7,
            "tags": ["magic", "wonder"],
        }

        response = client.post(
            "/api/characters/test-char-001/memories",
            json=memory_data,
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 201
        data = response.json()

        assert data["content"] == "I witnessed a magical event"
        assert data["importance"] == 7
        assert "magic" in data["tags"]
        assert "wonder" in data["tags"]
        assert "memory_id" in data
        assert "timestamp" in data

    @pytest.mark.integration
    def test_create_memory_core_memory(self, client):
        """Test creating a core memory (importance > 8)."""
        memory_data = {
            "content": "A life-changing event",
            "importance": 10,
            "tags": ["core", "life"],
        }

        response = client.post(
            "/api/characters/test-char-001/memories",
            json=memory_data,
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 201
        data = response.json()

        assert data["importance"] == 10
        assert data["is_core_memory"] is True
        assert data["importance_level"] == "core"

    @pytest.mark.integration
    def test_create_memory_character_not_found(self, client):
        """Test creating a memory for non-existent character."""
        memory_data = {
            "content": "Test memory",
            "importance": 5,
            "tags": [],
        }

        response = client.post(
            "/api/characters/not-found/memories",
            json=memory_data,
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 404


class TestMemoryAPIGetEndpoint:
    """Tests for GET /api/characters/{character_id}/memories/{memory_id} endpoint."""

    @pytest.mark.integration
    def test_get_single_memory_success(self, client):
        """Test getting a specific memory by ID."""
        response = client.get(
            "/api/characters/test-char-001/memories/existing-memory-001",
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["memory_id"] == "existing-memory-001"
        assert data["content"] == "I remember the great battle"
        assert data["importance"] == 9

    @pytest.mark.integration
    def test_get_single_memory_not_found(self, client):
        """Test getting a non-existent memory."""
        response = client.get(
            "/api/characters/test-char-001/memories/non-existent-memory",
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 404


class TestMemoryAPIDeleteEndpoint:
    """Tests for DELETE /api/characters/{character_id}/memories/{memory_id} endpoint."""

    @pytest.mark.integration
    def test_delete_memory_success(self, client):
        """Test deleting a memory."""
        response = client.delete(
            "/api/characters/test-char-001/memories/existing-memory-001",
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 204

    @pytest.mark.integration
    def test_delete_memory_not_found(self, client):
        """Test deleting a non-existent memory."""
        response = client.delete(
            "/api/characters/test-char-001/memories/non-existent-memory",
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 404
