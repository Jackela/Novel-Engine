"""Tests for the Lore API (Knowledge Base CRUD).

Verifies the endpoints for managing LoreEntry entities,
ensuring proper CRUD operations and search functionality.
"""

import pytest
from fastapi.testclient import TestClient

import api_server
from src.api.routers.lore import get_repository

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def reset_storage():
    """Reset in-memory storage before each test.

    Why this fixture:
        Ensures test isolation by clearing repository state between tests,
        preventing data pollution across test cases.
    """
    repo = get_repository()
    repo.clear()
    yield


@pytest.fixture
def client():
    """Create a test client for the API."""
    return TestClient(api_server.app)


# ============ LoreEntry CRUD Endpoint Tests ============


@pytest.mark.unit
class TestLoreEntryCreate:
    """Tests for lore entry creation endpoint."""

    def test_create_entry_success(self, client):
        """Creating an entry returns 201 with proper response structure."""
        response = client.post(
            "/api/lore",
            json={
                "title": "The Binding Laws",
                "content": "All magic requires sacrifice...",
                "category": "magic",
                "tags": ["magic", "rules"],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "The Binding Laws"
        assert data["content"] == "All magic requires sacrifice..."
        assert data["category"] == "magic"
        assert data["tags"] == ["magic", "rules"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_entry_minimal(self, client):
        """Creating an entry with only required fields succeeds."""
        response = client.post(
            "/api/lore",
            json={"title": "Minimal Entry"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Minimal Entry"
        assert data["category"] == "history"  # Default
        assert data["content"] == ""
        assert data["tags"] == []

    def test_create_entry_empty_title_fails(self, client):
        """Creating an entry with empty title returns 422."""
        response = client.post(
            "/api/lore",
            json={"title": "", "content": "Some content"},
        )
        assert response.status_code == 422

    def test_create_entry_invalid_category(self, client):
        """Creating an entry with invalid category returns 400."""
        response = client.post(
            "/api/lore",
            json={"title": "Test", "category": "invalid"},
        )
        assert response.status_code == 400
        assert "Invalid category" in response.json()["detail"]


@pytest.mark.unit
class TestLoreEntryGet:
    """Tests for getting lore entries."""

    def test_get_entry_success(self, client):
        """Getting an existing entry returns 200 with full data."""
        # Create first
        create_response = client.post(
            "/api/lore",
            json={"title": "Test Entry", "content": "Content here"},
        )
        entry_id = create_response.json()["id"]

        # Get
        response = client.get(f"/api/lore/{entry_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Entry"
        assert data["content"] == "Content here"

    def test_get_entry_not_found(self, client):
        """Getting a non-existent entry returns 404."""
        response = client.get("/api/lore/nonexistent-id")
        assert response.status_code == 404
        payload = response.json()
        assert payload.get("code") == "NOT_FOUND"
        assert "message" in payload


@pytest.mark.unit
class TestLoreEntryUpdate:
    """Tests for updating lore entries."""

    def test_update_entry_success(self, client):
        """Updating an entry returns 200 with updated data."""
        # Create first
        create_response = client.post(
            "/api/lore",
            json={"title": "Original Title", "content": "Original content"},
        )
        entry_id = create_response.json()["id"]

        # Update
        response = client.put(
            f"/api/lore/{entry_id}",
            json={"title": "Updated Title", "content": "Updated content"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["content"] == "Updated content"

    def test_update_entry_partial(self, client):
        """Updating only some fields preserves other fields."""
        # Create first
        create_response = client.post(
            "/api/lore",
            json={
                "title": "Original",
                "content": "Content",
                "category": "magic",
                "tags": ["tag1", "tag2"],
            },
        )
        entry_id = create_response.json()["id"]

        # Update only title
        response = client.put(
            f"/api/lore/{entry_id}",
            json={"title": "New Title"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"
        assert data["content"] == "Content"  # Preserved
        assert data["category"] == "magic"  # Preserved
        assert data["tags"] == ["tag1", "tag2"]  # Preserved

    def test_update_entry_tags(self, client):
        """Updating tags replaces all tags."""
        # Create first
        create_response = client.post(
            "/api/lore",
            json={"title": "Test", "tags": ["old1", "old2"]},
        )
        entry_id = create_response.json()["id"]

        # Update tags
        response = client.put(
            f"/api/lore/{entry_id}",
            json={"tags": ["new1", "new2", "new3"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tags"] == ["new1", "new2", "new3"]

    def test_update_entry_not_found(self, client):
        """Updating a non-existent entry returns 404."""
        response = client.put(
            "/api/lore/nonexistent-id",
            json={"title": "Updated"},
        )
        assert response.status_code == 404


@pytest.mark.unit
class TestLoreEntryDelete:
    """Tests for deleting lore entries."""

    def test_delete_entry_success(self, client):
        """Deleting an entry returns 204 and removes it."""
        # Create first
        create_response = client.post(
            "/api/lore",
            json={"title": "To Delete"},
        )
        entry_id = create_response.json()["id"]

        # Delete
        response = client.delete(f"/api/lore/{entry_id}")
        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(f"/api/lore/{entry_id}")
        assert get_response.status_code == 404

    def test_delete_entry_not_found(self, client):
        """Deleting a non-existent entry returns 404."""
        response = client.delete("/api/lore/nonexistent-id")
        assert response.status_code == 404


@pytest.mark.unit
class TestLoreEntryList:
    """Tests for listing lore entries."""

    def test_list_entries_empty(self, client):
        """Listing entries when none exist returns empty list."""
        response = client.get("/api/lore")
        assert response.status_code == 200
        data = response.json()
        assert data["entries"] == []
        assert data["total"] == 0

    def test_list_entries_returns_all(self, client):
        """Listing entries returns all created entries."""
        client.post("/api/lore", json={"title": "Entry 1"})
        client.post("/api/lore", json={"title": "Entry 2"})

        response = client.get("/api/lore")
        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 2
        assert data["total"] == 2

    def test_list_entries_filter_by_category(self, client):
        """Listing entries can filter by category."""
        client.post("/api/lore", json={"title": "History 1", "category": "history"})
        client.post("/api/lore", json={"title": "Magic 1", "category": "magic"})
        client.post("/api/lore", json={"title": "Magic 2", "category": "magic"})

        response = client.get("/api/lore?category=magic")
        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 2
        assert all(e["category"] == "magic" for e in data["entries"])

    def test_list_entries_filter_by_tag(self, client):
        """Listing entries can filter by tag."""
        client.post("/api/lore", json={"title": "Entry 1", "tags": ["magic", "rules"]})
        client.post("/api/lore", json={"title": "Entry 2", "tags": ["history"]})
        client.post("/api/lore", json={"title": "Entry 3", "tags": ["magic"]})

        response = client.get("/api/lore?tag=magic")
        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 2


@pytest.mark.unit
class TestLoreEntrySearch:
    """Tests for searching lore entries."""

    def test_search_by_title(self, client):
        """Search finds entries by title match."""
        client.post("/api/lore", json={"title": "The Great War"})
        client.post("/api/lore", json={"title": "Festival of Lights"})
        client.post("/api/lore", json={"title": "The Great Flood"})

        response = client.get("/api/lore/search?q=Great")
        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 2
        titles = [e["title"] for e in data["entries"]]
        assert "The Great War" in titles
        assert "The Great Flood" in titles

    def test_search_case_insensitive(self, client):
        """Search is case-insensitive."""
        client.post("/api/lore", json={"title": "The MAGIC System"})

        response = client.get("/api/lore/search?q=magic")
        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 1

    def test_search_with_tag_filter(self, client):
        """Search can combine title search with tag filter."""
        client.post("/api/lore", json={"title": "Magic Laws", "tags": ["magic"]})
        client.post("/api/lore", json={"title": "Magic History", "tags": ["history"]})

        response = client.get("/api/lore/search?q=Magic&tags=magic")
        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 1
        assert data["entries"][0]["title"] == "Magic Laws"

    def test_search_with_category_filter(self, client):
        """Search can combine title search with category filter."""
        client.post(
            "/api/lore",
            json={"title": "The Binding", "category": "magic"},
        )
        client.post(
            "/api/lore",
            json={"title": "The Binding Treaty", "category": "history"},
        )

        response = client.get("/api/lore/search?q=Binding&category=magic")
        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 1
        assert data["entries"][0]["category"] == "magic"

    def test_search_empty_query_returns_all(self, client):
        """Search with empty query returns all entries (filtered by other params)."""
        client.post("/api/lore", json={"title": "Entry 1", "category": "magic"})
        client.post("/api/lore", json={"title": "Entry 2", "category": "magic"})
        client.post("/api/lore", json={"title": "Entry 3", "category": "history"})

        response = client.get("/api/lore/search?q=&category=magic")
        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 2

    def test_search_multiple_tags(self, client):
        """Search can filter by multiple comma-separated tags."""
        client.post(
            "/api/lore",
            json={"title": "Entry 1", "tags": ["magic", "rules"]},
        )
        client.post(
            "/api/lore",
            json={"title": "Entry 2", "tags": ["history"]},
        )
        client.post(
            "/api/lore",
            json={"title": "Entry 3", "tags": ["rules", "law"]},
        )

        response = client.get("/api/lore/search?q=&tags=magic,rules")
        assert response.status_code == 200
        data = response.json()
        # Should match entries with ANY of the tags
        assert len(data["entries"]) >= 2
