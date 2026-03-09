#!/usr/bin/env python3
"""
Goal API Integration Tests

Tests the Goal API endpoints with full request/response validation.
Goals are character objectives that drive narrative arcs.
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    """Create a test client for the API with mock character store."""
    from src.api import deps
    from src.api.app import create_app

    app = create_app(debug=True)

    # Mock the workspace character store
    mock_store = MagicMock()

    # Create a mock character with goals - store at module level for access in closures
    mock_character = {
        "id": "test-char-001",
        "name": "Test Hero",
        "structured_data": {
            "goals": [
                {
                    "goal_id": "existing-goal-001",
                    "description": "Save the kingdom",
                    "status": "ACTIVE",
                    "urgency": "HIGH",
                    "created_at": "2024-01-01T00:00:00",
                    "completed_at": None,
                },
                {
                    "goal_id": "completed-goal-001",
                    "description": "Find the sword",
                    "status": "COMPLETED",
                    "urgency": "MEDIUM",
                    "created_at": "2024-01-01T00:00:00",
                    "completed_at": "2024-01-02T00:00:00",
                },
            ]
        },
    }

    # Use a list to hold the reference so we can update it
    character_state = [mock_character]

    def mock_get(workspace_id, character_id):
        if character_id == "test-char-001":
            return character_state[0]
        elif character_id == "not-found":
            return None
        return character_state[0]

    def mock_update(workspace_id, character_id, updates):
        if updates.get("structured_data"):
            character_state[0]["structured_data"] = updates["structured_data"]
        return True

    mock_store.get = mock_get
    mock_store.update = mock_update

    # Set the mock store on app state
    app.state.workspace_character_store = mock_store

    # Set a default workspace ID
    app.state.default_workspace_id = "test-workspace"

    # Override dependencies using FastAPI's dependency_overrides
    def override_get_optional_workspace_id():
        return "test-workspace"

    def override_require_workspace_id():
        return "test-workspace"

    app.dependency_overrides[deps.get_optional_workspace_id] = (
        override_get_optional_workspace_id
    )
    app.dependency_overrides[deps.require_workspace_id] = override_require_workspace_id

    with TestClient(app) as test_client:
        yield test_client

    # Clean up overrides
    app.dependency_overrides.clear()


class TestGoalAPIListEndpoints:
    """Tests for GET /api/characters/{character_id}/goals endpoints."""

    @pytest.mark.integration
    def test_get_character_goals_success(self, client):
        """Test getting all goals for a character."""
        response = client.get(
            "/api/characters/test-char-001/goals",
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["character_id"] == "test-char-001"
        assert data["total_count"] == 2
        assert data["active_count"] == 1
        assert data["completed_count"] == 1
        assert len(data["goals"]) == 2

    @pytest.mark.integration
    def test_get_character_goals_filter_by_status(self, client):
        """Test filtering goals by status."""
        response = client.get(
            "/api/characters/test-char-001/goals",
            params={"status": "ACTIVE"},
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 1
        assert data["goals"][0]["status"] == "ACTIVE"

    @pytest.mark.integration
    def test_get_character_goals_character_not_found(self, client):
        """Test getting goals for non-existent character."""
        response = client.get(
            "/api/characters/not-found/goals",
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 404


class TestGoalAPICreateEndpoints:
    """Tests for POST /api/characters/{character_id}/goals endpoint."""

    @pytest.mark.integration
    def test_create_goal_success(self, client):
        """Test creating a new goal for a character."""
        goal_data = {
            "description": "Defeat the dragon",
            "urgency": "HIGH",
        }

        response = client.post(
            "/api/characters/test-char-001/goals",
            json=goal_data,
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 201
        data = response.json()

        assert data["description"] == "Defeat the dragon"
        assert data["status"] == "ACTIVE"
        assert data["urgency"] == "HIGH"
        assert data["is_active"] is True
        assert data["is_urgent"] is True
        assert "goal_id" in data
        assert "created_at" in data

    @pytest.mark.integration
    def test_create_goal_low_urgency(self, client):
        """Test creating a goal with low urgency."""
        goal_data = {
            "description": "Learn to cook",
            "urgency": "LOW",
        }

        response = client.post(
            "/api/characters/test-char-001/goals",
            json=goal_data,
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 201
        data = response.json()

        assert data["urgency"] == "LOW"
        assert data["is_urgent"] is False


class TestGoalAPIGetEndpoint:
    """Tests for GET /api/characters/{character_id}/goals/{goal_id} endpoint."""

    @pytest.mark.integration
    def test_get_single_goal_success(self, client):
        """Test getting a specific goal by ID."""
        response = client.get(
            "/api/characters/test-char-001/goals/existing-goal-001",
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["goal_id"] == "existing-goal-001"
        assert data["description"] == "Save the kingdom"
        assert data["status"] == "ACTIVE"

    @pytest.mark.integration
    def test_get_single_goal_not_found(self, client):
        """Test getting a non-existent goal."""
        response = client.get(
            "/api/characters/test-char-001/goals/non-existent-goal",
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 404


class TestGoalAPIUpdateEndpoint:
    """Tests for PATCH /api/characters/{character_id}/goals/{goal_id} endpoint."""

    @pytest.mark.integration
    def test_update_goal_status(self, client):
        """Test updating goal status to completed."""
        update_data = {
            "status": "COMPLETED",
        }

        response = client.patch(
            "/api/characters/test-char-001/goals/existing-goal-001",
            json=update_data,
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "COMPLETED"
        assert data["is_active"] is False
        assert data["completed_at"] is not None

    @pytest.mark.integration
    def test_update_goal_urgency(self, client):
        """Test updating goal urgency."""
        update_data = {
            "urgency": "CRITICAL",
        }

        response = client.patch(
            "/api/characters/test-char-001/goals/existing-goal-001",
            json=update_data,
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["urgency"] == "CRITICAL"
        assert data["is_urgent"] is True

    @pytest.mark.integration
    def test_update_completed_goal_fails(self, client):
        """Test that updating a completed goal's status fails."""
        update_data = {
            "status": "ACTIVE",
        }

        response = client.patch(
            "/api/characters/test-char-001/goals/completed-goal-001",
            json=update_data,
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 400


class TestGoalAPIDeleteEndpoint:
    """Tests for DELETE /api/characters/{character_id}/goals/{goal_id} endpoint."""

    @pytest.mark.integration
    def test_delete_goal_success(self, client):
        """Test deleting a goal."""
        response = client.delete(
            "/api/characters/test-char-001/goals/existing-goal-001",
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 204

    @pytest.mark.integration
    def test_delete_goal_not_found(self, client):
        """Test deleting a non-existent goal."""
        response = client.delete(
            "/api/characters/test-char-001/goals/non-existent-goal",
            headers={"X-Workspace-Id": "test-workspace"},
        )

        assert response.status_code == 404
