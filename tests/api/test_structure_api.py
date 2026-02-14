"""Tests for the Structure API (Narrative Outline CRUD).

Verifies the endpoints for managing Story, Chapter, and Scene entities,
ensuring proper CRUD operations and move functionality work as expected.
"""

import api_server
import pytest
from fastapi.testclient import TestClient

from src.api.routers.structure import get_repository, reset_scene_storage

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def reset_storage():
    """Reset in-memory storage before each test.

    Why this fixture:
        Ensures test isolation by clearing repository state between tests,
        preventing data pollution across test cases.
    """
    repo = get_repository()
    # Clear stories from repository
    for story in list(repo.list_all()):
        repo.delete(story.id)
    reset_scene_storage()
    yield


@pytest.fixture
def client():
    """Create a test client for the API."""
    return TestClient(api_server.app)


# ============ Story Endpoint Tests ============


@pytest.mark.unit
class TestStoryEndpoints:
    """Tests for story CRUD operations."""

    def test_create_story_success(self, client):
        """Creating a story returns 201 with proper response structure."""
        response = client.post(
            "/api/structure/stories",
            json={"title": "The Hero's Journey", "summary": "An epic adventure."},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "The Hero's Journey"
        assert data["summary"] == "An epic adventure."
        assert data["status"] == "draft"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_story_empty_title_fails(self, client):
        """Creating a story with empty title returns 422."""
        response = client.post(
            "/api/structure/stories",
            json={"title": "", "summary": "No title story."},
        )
        assert response.status_code == 422

    def test_list_stories_empty(self, client):
        """Listing stories when none exist returns empty list."""
        response = client.get("/api/structure/stories")
        assert response.status_code == 200
        assert response.json()["stories"] == []

    def test_list_stories_returns_all(self, client):
        """Listing stories returns all created stories."""
        client.post("/api/structure/stories", json={"title": "Story 1"})
        client.post("/api/structure/stories", json={"title": "Story 2"})

        response = client.get("/api/structure/stories")
        assert response.status_code == 200
        stories = response.json()["stories"]
        assert len(stories) == 2

    def test_get_story_by_id(self, client):
        """Getting a story by ID returns the correct story."""
        create_resp = client.post(
            "/api/structure/stories",
            json={"title": "Fetchable Story"},
        )
        story_id = create_resp.json()["id"]

        response = client.get(f"/api/structure/stories/{story_id}")
        assert response.status_code == 200
        assert response.json()["title"] == "Fetchable Story"

    def test_get_story_not_found(self, client):
        """Getting a non-existent story returns 404."""
        response = client.get(
            "/api/structure/stories/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    def test_update_story(self, client):
        """Updating a story modifies the specified fields."""
        create_resp = client.post(
            "/api/structure/stories",
            json={"title": "Original Title"},
        )
        story_id = create_resp.json()["id"]

        response = client.patch(
            f"/api/structure/stories/{story_id}",
            json={"title": "Updated Title", "summary": "New summary"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["summary"] == "New summary"

    def test_update_story_publish(self, client):
        """Updating story status to published works."""
        create_resp = client.post(
            "/api/structure/stories",
            json={"title": "Draft Story"},
        )
        story_id = create_resp.json()["id"]

        response = client.patch(
            f"/api/structure/stories/{story_id}",
            json={"status": "published"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "published"

    def test_delete_story(self, client):
        """Deleting a story removes it from the repository."""
        create_resp = client.post(
            "/api/structure/stories",
            json={"title": "To Delete"},
        )
        story_id = create_resp.json()["id"]

        delete_resp = client.delete(f"/api/structure/stories/{story_id}")
        assert delete_resp.status_code == 204

        get_resp = client.get(f"/api/structure/stories/{story_id}")
        assert get_resp.status_code == 404


# ============ Chapter Endpoint Tests ============


@pytest.mark.unit
class TestChapterEndpoints:
    """Tests for chapter CRUD operations."""

    @pytest.fixture
    def story_id(self, client):
        """Create a story and return its ID."""
        response = client.post(
            "/api/structure/stories",
            json={"title": "Test Story"},
        )
        return response.json()["id"]

    def test_create_chapter(self, client, story_id):
        """Creating a chapter returns 201 with proper structure."""
        response = client.post(
            f"/api/structure/stories/{story_id}/chapters",
            json={"title": "Chapter One", "summary": "The beginning."},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Chapter One"
        assert data["story_id"] == story_id
        assert data["order_index"] == 0

    def test_create_chapter_with_order_index(self, client, story_id):
        """Creating a chapter with explicit order_index uses it."""
        response = client.post(
            f"/api/structure/stories/{story_id}/chapters",
            json={"title": "Chapter Five", "order_index": 4},
        )
        assert response.status_code == 201
        assert response.json()["order_index"] == 4

    def test_list_chapters(self, client, story_id):
        """Listing chapters returns all chapters for a story."""
        client.post(
            f"/api/structure/stories/{story_id}/chapters",
            json={"title": "Chapter 1"},
        )
        client.post(
            f"/api/structure/stories/{story_id}/chapters",
            json={"title": "Chapter 2"},
        )

        response = client.get(f"/api/structure/stories/{story_id}/chapters")
        assert response.status_code == 200
        data = response.json()
        assert data["story_id"] == story_id
        assert len(data["chapters"]) == 2

    def test_get_chapter(self, client, story_id):
        """Getting a chapter by ID returns the correct chapter."""
        create_resp = client.post(
            f"/api/structure/stories/{story_id}/chapters",
            json={"title": "Fetch Me"},
        )
        chapter_id = create_resp.json()["id"]

        response = client.get(
            f"/api/structure/stories/{story_id}/chapters/{chapter_id}"
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Fetch Me"

    def test_update_chapter(self, client, story_id):
        """Updating a chapter modifies the specified fields."""
        create_resp = client.post(
            f"/api/structure/stories/{story_id}/chapters",
            json={"title": "Original"},
        )
        chapter_id = create_resp.json()["id"]

        response = client.patch(
            f"/api/structure/stories/{story_id}/chapters/{chapter_id}",
            json={"title": "Modified", "summary": "New synopsis"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Modified"
        assert data["summary"] == "New synopsis"

    def test_delete_chapter(self, client, story_id):
        """Deleting a chapter removes it from the story."""
        create_resp = client.post(
            f"/api/structure/stories/{story_id}/chapters",
            json={"title": "To Remove"},
        )
        chapter_id = create_resp.json()["id"]

        delete_resp = client.delete(
            f"/api/structure/stories/{story_id}/chapters/{chapter_id}"
        )
        assert delete_resp.status_code == 204

        get_resp = client.get(
            f"/api/structure/stories/{story_id}/chapters/{chapter_id}"
        )
        assert get_resp.status_code == 404

    def test_move_chapter(self, client, story_id):
        """Moving a chapter updates its order_index."""
        create_resp = client.post(
            f"/api/structure/stories/{story_id}/chapters",
            json={"title": "Movable", "order_index": 0},
        )
        chapter_id = create_resp.json()["id"]

        response = client.post(
            f"/api/structure/stories/{story_id}/chapters/{chapter_id}/move",
            json={"new_order_index": 5},
        )
        assert response.status_code == 200
        assert response.json()["order_index"] == 5


# ============ Scene Endpoint Tests ============


@pytest.mark.unit
class TestSceneEndpoints:
    """Tests for scene CRUD operations."""

    @pytest.fixture
    def chapter_context(self, client):
        """Create a story and chapter, return their IDs."""
        story_resp = client.post(
            "/api/structure/stories",
            json={"title": "Scene Test Story"},
        )
        story_id = story_resp.json()["id"]

        chapter_resp = client.post(
            f"/api/structure/stories/{story_id}/chapters",
            json={"title": "Scene Test Chapter"},
        )
        chapter_id = chapter_resp.json()["id"]

        return {"story_id": story_id, "chapter_id": chapter_id}

    def test_create_scene(self, client, chapter_context):
        """Creating a scene returns 201 with proper structure."""
        story_id = chapter_context["story_id"]
        chapter_id = chapter_context["chapter_id"]

        response = client.post(
            f"/api/structure/stories/{story_id}/chapters/{chapter_id}/scenes",
            json={
                "title": "Opening Scene",
                "summary": "The story begins.",
                "location": "A dark forest",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Opening Scene"
        assert data["chapter_id"] == chapter_id
        assert data["location"] == "A dark forest"
        assert data["status"] == "draft"

    def test_list_scenes(self, client, chapter_context):
        """Listing scenes returns all scenes for a chapter."""
        story_id = chapter_context["story_id"]
        chapter_id = chapter_context["chapter_id"]

        client.post(
            f"/api/structure/stories/{story_id}/chapters/{chapter_id}/scenes",
            json={"title": "Scene 1"},
        )
        client.post(
            f"/api/structure/stories/{story_id}/chapters/{chapter_id}/scenes",
            json={"title": "Scene 2"},
        )

        response = client.get(
            f"/api/structure/stories/{story_id}/chapters/{chapter_id}/scenes"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["chapter_id"] == chapter_id
        assert len(data["scenes"]) == 2

    def test_get_scene(self, client, chapter_context):
        """Getting a scene by ID returns the correct scene."""
        story_id = chapter_context["story_id"]
        chapter_id = chapter_context["chapter_id"]

        create_resp = client.post(
            f"/api/structure/stories/{story_id}/chapters/{chapter_id}/scenes",
            json={"title": "Fetchable Scene"},
        )
        scene_id = create_resp.json()["id"]

        response = client.get(
            f"/api/structure/stories/{story_id}/chapters/{chapter_id}/scenes/{scene_id}"
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Fetchable Scene"

    def test_update_scene(self, client, chapter_context):
        """Updating a scene modifies the specified fields."""
        story_id = chapter_context["story_id"]
        chapter_id = chapter_context["chapter_id"]

        create_resp = client.post(
            f"/api/structure/stories/{story_id}/chapters/{chapter_id}/scenes",
            json={"title": "Original Scene"},
        )
        scene_id = create_resp.json()["id"]

        response = client.patch(
            f"/api/structure/stories/{story_id}/chapters/{chapter_id}/scenes/{scene_id}",
            json={
                "title": "Updated Scene",
                "location": "Mountain peak",
                "status": "review",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Scene"
        assert data["location"] == "Mountain peak"
        assert data["status"] == "review"

    def test_delete_scene(self, client, chapter_context):
        """Deleting a scene removes it from storage."""
        story_id = chapter_context["story_id"]
        chapter_id = chapter_context["chapter_id"]

        create_resp = client.post(
            f"/api/structure/stories/{story_id}/chapters/{chapter_id}/scenes",
            json={"title": "To Delete"},
        )
        scene_id = create_resp.json()["id"]

        delete_resp = client.delete(
            f"/api/structure/stories/{story_id}/chapters/{chapter_id}/scenes/{scene_id}"
        )
        assert delete_resp.status_code == 204

        get_resp = client.get(
            f"/api/structure/stories/{story_id}/chapters/{chapter_id}/scenes/{scene_id}"
        )
        assert get_resp.status_code == 404

    def test_move_scene_within_chapter(self, client, chapter_context):
        """Moving a scene updates its order_index."""
        story_id = chapter_context["story_id"]
        chapter_id = chapter_context["chapter_id"]

        create_resp = client.post(
            f"/api/structure/stories/{story_id}/chapters/{chapter_id}/scenes",
            json={"title": "Movable Scene", "order_index": 0},
        )
        scene_id = create_resp.json()["id"]

        response = client.post(
            f"/api/structure/stories/{story_id}/chapters/{chapter_id}/scenes/{scene_id}/move",
            json={"new_order_index": 3},
        )
        assert response.status_code == 200
        assert response.json()["order_index"] == 3

    def test_move_scene_to_different_chapter(self, client, chapter_context):
        """Moving a scene to a different chapter updates chapter_id."""
        story_id = chapter_context["story_id"]
        source_chapter_id = chapter_context["chapter_id"]

        # Create target chapter
        target_resp = client.post(
            f"/api/structure/stories/{story_id}/chapters",
            json={"title": "Target Chapter"},
        )
        target_chapter_id = target_resp.json()["id"]

        # Create scene in source chapter
        create_resp = client.post(
            f"/api/structure/stories/{story_id}/chapters/{source_chapter_id}/scenes",
            json={"title": "Cross-chapter Scene"},
        )
        scene_id = create_resp.json()["id"]

        # Move to target chapter
        response = client.post(
            f"/api/structure/stories/{story_id}/chapters/{source_chapter_id}/scenes/{scene_id}/move",
            json={"target_chapter_id": target_chapter_id, "new_order_index": 0},
        )
        assert response.status_code == 200
        assert response.json()["chapter_id"] == target_chapter_id
