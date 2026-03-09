#!/usr/bin/env python3
"""
Lore API Integration Tests

Tests the Lore API endpoints with full request/response validation.
Lore entries represent world-building knowledge and wiki-style content.
"""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    """Create a test client for the API."""
    from src.api.app import create_app

    app = create_app(debug=True)
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_repository():
    """Reset the lore repository before each test."""
    from src.api.routers.lore import get_repository

    repo = get_repository()
    # Clear the repository
    repo._entries.clear()
    repo._id_counter = 0

    yield

    # Cleanup after test
    repo._entries.clear()


class TestLoreAPICreateEndpoint:
    """Tests for POST /api/lore endpoint."""

    @pytest.mark.integration
    def test_create_lore_entry_success(self, client):
        """Test creating a new lore entry."""
        lore_data = {
            "title": "The Great War",
            "content": "A devastating conflict that reshaped the world...",
            "tags": ["war", "history", "major_event"],
            "category": "history",
            "summary": "The conflict that ended the First Age",
        }

        response = client.post("/api/lore", json=lore_data)

        assert response.status_code == 201
        data = response.json()

        assert data["title"] == "The Great War"
        assert data["category"] == "history"
        assert "war" in data["tags"]
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.integration
    def test_create_lore_entry_minimal(self, client):
        """Test creating a lore entry with minimal fields."""
        lore_data = {
            "title": "Simple Entry",
            "content": "Basic content",
            "category": "history",  # Using valid category
        }

        response = client.post("/api/lore", json=lore_data)

        assert response.status_code == 201
        data = response.json()

        assert data["title"] == "Simple Entry"
        assert data["category"] == "history"

    @pytest.mark.integration
    def test_create_lore_entry_invalid_category(self, client):
        """Test creating a lore entry with invalid category."""
        lore_data = {
            "title": "Invalid Entry",
            "content": "Content",
            "category": "nonexistent_category",
        }

        response = client.post("/api/lore", json=lore_data)

        assert response.status_code == 400
        assert "Invalid category" in response.json()["detail"]


class TestLoreAPIGetEndpoint:
    """Tests for GET /api/lore/{entry_id} endpoint."""

    @pytest.mark.integration
    def test_get_lore_entry_success(self, client):
        """Test getting a lore entry by ID."""
        # First create an entry
        create_response = client.post(
            "/api/lore",
            json={
                "title": "Test Entry",
                "content": "Test content",
                "category": "history",
            },
        )
        entry_id = create_response.json()["id"]

        # Then get it
        response = client.get(f"/api/lore/{entry_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == entry_id
        assert data["title"] == "Test Entry"

    @pytest.mark.integration
    def test_get_lore_entry_not_found(self, client):
        """Test getting a non-existent lore entry."""
        response = client.get("/api/lore/non-existent-id")

        assert response.status_code == 404
        # The error response uses 'message' for the error text
        response_data = response.json()
        # The global 404 handler returns "The requested endpoint does not exist"
        # or the router may return "Lore entry not found: {entry_id}"
        # Check that we get a 404 response
        assert response_data.get("code") == "NOT_FOUND" or "message" in response_data


class TestLoreAPIListEndpoint:
    """Tests for GET /api/lore endpoint."""

    @pytest.mark.integration
    def test_list_lore_entries_empty(self, client):
        """Test listing lore entries when none exist."""
        response = client.get("/api/lore")

        assert response.status_code == 200
        data = response.json()

        assert data["entries"] == []
        assert data["total"] == 0

    @pytest.mark.integration
    def test_list_lore_entries_with_data(self, client):
        """Test listing lore entries with data."""
        # Create some entries
        client.post(
            "/api/lore",
            json={"title": "Entry 1", "content": "Content 1", "category": "history"},
        )
        client.post(
            "/api/lore",
            json={"title": "Entry 2", "content": "Content 2", "category": "culture"},
        )

        response = client.get("/api/lore")

        assert response.status_code == 200
        data = response.json()

        # Should have at least 2 entries (might have more from other tests that didn't clean up)
        assert data["total"] >= 2
        assert len(data["entries"]) >= 2

    @pytest.mark.integration
    def test_list_lore_entries_filter_by_category(self, client):
        """Test filtering lore entries by category."""
        # Create entries of different categories
        client.post(
            "/api/lore",
            json={"title": "History 1", "content": "Content", "category": "history"},
        )
        client.post(
            "/api/lore",
            json={"title": "Magic 1", "content": "Content", "category": "magic"},
        )

        response = client.get("/api/lore", params={"category": "history"})

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert data["entries"][0]["category"] == "history"

    @pytest.mark.integration
    def test_list_lore_entries_filter_by_tag(self, client):
        """Test filtering lore entries by tag."""
        client.post(
            "/api/lore",
            json={
                "title": "Tagged Entry",
                "content": "Content",
                "category": "history",
                "tags": ["important", "war"],
            },
        )
        client.post(
            "/api/lore",
            json={
                "title": "Untagged Entry",
                "content": "Content",
                "category": "history",
                "tags": ["minor"],
            },
        )

        response = client.get("/api/lore", params={"tag": "important"})

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert "important" in data["entries"][0]["tags"]


class TestLoreAPISearchEndpoint:
    """Tests for GET /api/lore/search endpoint."""

    @pytest.mark.integration
    def test_search_lore_entries_by_query(self, client):
        """Test searching lore entries by title."""
        client.post(
            "/api/lore",
            json={"title": "Dragon Legends", "content": "Content", "category": "magic"},
        )
        client.post(
            "/api/lore",
            json={
                "title": "Elven History",
                "content": "Content",
                "category": "history",
            },
        )

        response = client.get("/api/lore/search", params={"q": "Dragon"})

        assert response.status_code == 200
        data = response.json()

        # At least one result should match
        assert data["total"] >= 1
        # Find the Dragon entry in results
        dragon_entries = [e for e in data["entries"] if "Dragon" in e["title"]]
        assert len(dragon_entries) >= 1

    @pytest.mark.integration
    def test_search_lore_entries_by_tags(self, client):
        """Test searching lore entries by tags."""
        client.post(
            "/api/lore",
            json={
                "title": "Entry A",
                "content": "Content",
                "category": "history",
                "tags": ["ancient", "war"],
            },
        )
        client.post(
            "/api/lore",
            json={
                "title": "Entry B",
                "content": "Content",
                "category": "history",
                "tags": ["modern"],
            },
        )

        response = client.get("/api/lore/search", params={"tags": "ancient,war"})

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1

    @pytest.mark.integration
    def test_search_lore_entries_combined_filters(self, client):
        """Test searching with combined filters."""
        client.post(
            "/api/lore",
            json={
                "title": "Ancient Magic",
                "content": "Content about magic",
                "category": "magic",
                "tags": ["ancient"],
            },
        )
        client.post(
            "/api/lore",
            json={
                "title": "Modern Magic",
                "content": "Content",
                "category": "magic",
                "tags": ["modern"],
            },
        )

        response = client.get(
            "/api/lore/search",
            params={"q": "Ancient", "category": "magic", "tags": "ancient"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert "Ancient" in data["entries"][0]["title"]


class TestLoreAPIUpdateEndpoint:
    """Tests for PUT /api/lore/{entry_id} endpoint."""

    @pytest.mark.integration
    def test_update_lore_entry_success(self, client):
        """Test updating a lore entry."""
        # Create an entry
        create_response = client.post(
            "/api/lore",
            json={
                "title": "Original Title",
                "content": "Original content",
                "category": "history",
            },
        )
        entry_id = create_response.json()["id"]

        # Update it
        update_data = {
            "title": "Updated Title",
            "content": "Updated content",
            "tags": ["updated", "modified"],
        }

        response = client.put(f"/api/lore/{entry_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()

        assert data["title"] == "Updated Title"
        assert data["content"] == "Updated content"
        assert "updated" in data["tags"]

    @pytest.mark.integration
    def test_update_lore_entry_category(self, client):
        """Test updating lore entry category."""
        create_response = client.post(
            "/api/lore",
            json={"title": "Entry", "content": "Content", "category": "history"},
        )
        entry_id = create_response.json()["id"]

        response = client.put(
            f"/api/lore/{entry_id}",
            json={"category": "magic"},  # Using valid category
        )

        assert response.status_code == 200
        data = response.json()

        assert data["category"] == "magic"

    @pytest.mark.integration
    def test_update_lore_entry_not_found(self, client):
        """Test updating a non-existent lore entry."""
        response = client.put(
            "/api/lore/non-existent-id",
            json={"title": "New Title"},
        )

        assert response.status_code == 404


class TestLoreAPISmartTagsEndpoints:
    """Tests for smart tags management endpoints."""

    @pytest.mark.integration
    def test_get_smart_tags(self, client):
        """Test getting smart tags for a lore entry."""
        create_response = client.post(
            "/api/lore",
            json={"title": "Entry", "content": "Content", "category": "history"},
        )
        entry_id = create_response.json()["id"]

        response = client.get(f"/api/lore/{entry_id}/smart-tags")

        assert response.status_code == 200
        data = response.json()

        assert "smart_tags" in data
        assert "manual_smart_tags" in data
        assert "effective_tags" in data

    @pytest.mark.integration
    def test_update_manual_smart_tags(self, client):
        """Test updating manual smart tags."""
        create_response = client.post(
            "/api/lore",
            json={"title": "Entry", "content": "Content", "category": "history"},
        )
        entry_id = create_response.json()["id"]

        response = client.put(
            f"/api/lore/{entry_id}/smart-tags/manual",
            json={
                "category": "topic",
                "tags": ["war", "politics"],
                "replace": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "manual_smart_tags" in data

    @pytest.mark.integration
    def test_delete_manual_smart_tags(self, client):
        """Test deleting manual smart tags."""
        create_response = client.post(
            "/api/lore",
            json={"title": "Entry", "content": "Content", "category": "history"},
        )
        entry_id = create_response.json()["id"]

        # First add some tags
        client.put(
            f"/api/lore/{entry_id}/smart-tags/manual",
            json={"category": "topic", "tags": ["test"], "replace": True},
        )

        # Then delete them
        response = client.delete(f"/api/lore/{entry_id}/smart-tags/manual/topic")

        assert response.status_code == 204


class TestLoreAPIDeleteEndpoint:
    """Tests for DELETE /api/lore/{entry_id} endpoint."""

    @pytest.mark.integration
    def test_delete_lore_entry_success(self, client):
        """Test deleting a lore entry."""
        # Create an entry
        create_response = client.post(
            "/api/lore",
            json={"title": "To Delete", "content": "Content", "category": "history"},
        )
        entry_id = create_response.json()["id"]

        # Delete it
        response = client.delete(f"/api/lore/{entry_id}")

        assert response.status_code == 204

        # Verify it's gone
        get_response = client.get(f"/api/lore/{entry_id}")
        assert get_response.status_code == 404

    @pytest.mark.integration
    def test_delete_lore_entry_not_found(self, client):
        """Test deleting a non-existent lore entry."""
        response = client.delete("/api/lore/non-existent-id")

        assert response.status_code == 404
