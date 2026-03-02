"""Integration tests for Structure API endpoints.

Tests the narrative outline management endpoints for stories, chapters,
and related entities.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    app = create_app()
    return TestClient(app)


@pytest.mark.integration
class TestStoryEndpoints:
    """Tests for story management endpoints."""

    def test_list_stories(self, client: TestClient) -> None:
        """Test GET /api/structure/stories endpoint."""
        response = client.get("/api/structure/stories")

        assert response.status_code == 200
        data = response.json()
        assert "stories" in data
        assert isinstance(data["stories"], list)

    def test_create_story(self, client: TestClient) -> None:
        """Test POST /api/structure/stories endpoint."""
        response = client.post(
            "/api/structure/stories",
            json={
                "title": "Test Story",
                "summary": "A test story for integration testing",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Story"
        assert "id" in data
        assert "created_at" in data

    def test_get_story_by_id(self, client: TestClient) -> None:
        """Test GET /api/structure/stories/{story_id} endpoint."""
        # First create a story
        create_response = client.post(
            "/api/structure/stories",
            json={"title": "Story to Get", "summary": "Test summary"},
        )
        story_id = create_response.json()["id"]

        # Then get it
        response = client.get(f"/api/structure/stories/{story_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == story_id

    def test_get_nonexistent_story(self, client: TestClient) -> None:
        """Test GET /api/structure/stories/{story_id} with invalid ID."""
        response = client.get("/api/structure/stories/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404

    def test_update_story(self, client: TestClient) -> None:
        """Test PATCH /api/structure/stories/{story_id} endpoint."""
        # Create a story first
        create_response = client.post(
            "/api/structure/stories",
            json={"title": "Original Title", "summary": "Original summary"},
        )
        story_id = create_response.json()["id"]

        # Update it
        response = client.patch(
            f"/api/structure/stories/{story_id}",
            json={"title": "Updated Title"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"


@pytest.mark.integration
class TestChapterEndpoints:
    """Tests for chapter management endpoints."""

    def test_list_chapters(self, client: TestClient) -> None:
        """Test GET /api/structure/stories/{story_id}/chapters endpoint."""
        # Create a story first
        create_response = client.post(
            "/api/structure/stories",
            json={"title": "Story for Chapters", "summary": "Test"},
        )
        story_id = create_response.json()["id"]

        response = client.get(f"/api/structure/stories/{story_id}/chapters")

        assert response.status_code == 200
        data = response.json()
        assert "chapters" in data

    def test_create_chapter(self, client: TestClient) -> None:
        """Test POST /api/structure/stories/{story_id}/chapters endpoint."""
        # Create a story first
        create_response = client.post(
            "/api/structure/stories",
            json={"title": "Story for Chapter Creation", "summary": "Test"},
        )
        story_id = create_response.json()["id"]

        response = client.post(
            f"/api/structure/stories/{story_id}/chapters",
            json={
                "title": "Chapter One",
                "summary": "The beginning",
                "order_index": 1,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Chapter One"
        assert data["story_id"] == story_id


@pytest.mark.integration
class TestPlotlineEndpoints:
    """Tests for plotline management endpoints."""

    def test_list_plotlines(self, client: TestClient) -> None:
        """Test GET /api/structure/stories/{story_id}/plotlines endpoint."""
        # Create a story first
        create_response = client.post(
            "/api/structure/stories",
            json={"title": "Story for Plotlines", "summary": "Test"},
        )
        story_id = create_response.json()["id"]

        response = client.get(f"/api/structure/stories/{story_id}/plotlines")

        assert response.status_code == 200
        data = response.json()
        assert "plotlines" in data


@pytest.mark.integration
class TestStructureResponseFormat:
    """Tests for structure API response format validation."""

    def test_story_response_format(self, client: TestClient) -> None:
        """Test that story response has correct format."""
        response = client.post(
            "/api/structure/stories",
            json={"title": "Format Test Story", "summary": "Test"},
        )

        assert response.status_code == 201
        data = response.json()

        # Required fields
        assert "id" in data
        assert "title" in data
        assert "status" in data
        assert "created_at" in data
        assert "updated_at" in data

        # Types
        assert isinstance(data["title"], str)
        assert isinstance(data["status"], str)

    def test_chapter_response_format(self, client: TestClient) -> None:
        """Test that chapter response has correct format."""
        story_response = client.post(
            "/api/structure/stories",
            json={"title": "Story", "summary": "Test"},
        )
        story_id = story_response.json()["id"]

        response = client.post(
            f"/api/structure/stories/{story_id}/chapters",
            json={"title": "Format Test Chapter", "summary": "Test", "order_index": 1},
        )

        assert response.status_code == 201
        data = response.json()

        assert "id" in data
        assert "story_id" in data
        assert "title" in data
        assert "order_index" in data
        assert "status" in data
