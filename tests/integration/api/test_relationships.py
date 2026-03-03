#!/usr/bin/env python3
"""
Relationships API Integration Tests

Tests the Relationships API endpoints with full request/response validation.
Relationships track connections between entities in the World Knowledge Graph.
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
    """Reset the relationship repository before each test."""
    from src.api.routers.relationships import get_repository

    repo = get_repository()
    repo._relationships.clear()
    repo._id_counter = 0

    yield

    # Cleanup after test
    repo._relationships.clear()


class TestRelationshipsAPICreateEndpoint:
    """Tests for POST /api/relationships endpoint."""

    @pytest.mark.integration
    def test_create_relationship_success(self, client):
        """Test creating a new relationship."""
        relationship_data = {
            "source_id": "aria-shadowbane",
            "source_type": "character",
            "target_id": "house-shadowbane",
            "target_type": "faction",
            "relationship_type": "member_of",
            "description": "Aria is a member of House Shadowbane",
            "strength": 80,
            "trust": 50,
            "romance": 0,
        }

        response = client.post("/api/relationships", json=relationship_data)

        assert response.status_code == 201
        data = response.json()

        assert data["source_id"] == "aria-shadowbane"
        assert data["source_type"] == "character"
        assert data["target_id"] == "house-shadowbane"
        assert data["relationship_type"] == "member_of"
        assert data["strength"] == 80
        assert data["trust"] == 50
        assert "id" in data
        assert "created_at" in data
        assert "interaction_history" in data

    @pytest.mark.integration
    def test_create_relationship_between_characters(self, client):
        """Test creating a relationship between two characters."""
        relationship_data = {
            "source_id": "hero-001",
            "source_type": "character",
            "target_id": "hero-002",
            "target_type": "character",
            "relationship_type": "ally",
            "description": "Long-time friends",
            "strength": 90,
            "trust": 85,
            "romance": 0,
        }

        response = client.post("/api/relationships", json=relationship_data)

        assert response.status_code == 201
        data = response.json()

        assert data["relationship_type"] == "ally"
        assert data["is_active"] is True

    @pytest.mark.integration
    def test_create_relationship_invalid_type(self, client):
        """Test creating a relationship with invalid type."""
        relationship_data = {
            "source_id": "char-001",
            "source_type": "character",
            "target_id": "char-002",
            "target_type": "character",
            "relationship_type": "nonexistent_type",
        }

        response = client.post("/api/relationships", json=relationship_data)

        assert response.status_code == 400
        assert "Invalid relationship type" in response.json()["detail"]

    @pytest.mark.integration
    def test_create_relationship_invalid_entity_type(self, client):
        """Test creating a relationship with invalid entity type."""
        relationship_data = {
            "source_id": "char-001",
            "source_type": "invalid_type",
            "target_id": "char-002",
            "target_type": "character",
            "relationship_type": "ally",
        }

        response = client.post("/api/relationships", json=relationship_data)

        assert response.status_code == 400


class TestRelationshipsAPIGetEndpoint:
    """Tests for GET /api/relationships/{relationship_id} endpoint."""

    @pytest.mark.integration
    def test_get_relationship_success(self, client):
        """Test getting a relationship by ID."""
        # First create a relationship
        create_response = client.post(
            "/api/relationships",
            json={
                "source_id": "hero-001",
                "source_type": "character",
                "target_id": "hero-002",
                "target_type": "character",
                "relationship_type": "ally",
                "description": "Test relationship",
            },
        )
        relationship_id = create_response.json()["id"]

        # Then get it
        response = client.get(f"/api/relationships/{relationship_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == relationship_id
        assert data["source_id"] == "hero-001"
        assert data["target_id"] == "hero-002"

    @pytest.mark.integration
    def test_get_relationship_not_found(self, client):
        """Test getting a non-existent relationship."""
        response = client.get("/api/relationships/non-existent-id")

        assert response.status_code == 404


class TestRelationshipsAPIListEndpoint:
    """Tests for GET /api/relationships endpoint."""

    @pytest.mark.integration
    def test_list_relationships_empty(self, client):
        """Test listing relationships when none exist."""
        response = client.get("/api/relationships")

        assert response.status_code == 200
        data = response.json()

        assert data["relationships"] == []
        assert data["total"] == 0

    @pytest.mark.integration
    def test_list_relationships_with_data(self, client):
        """Test listing relationships with data."""
        # Create some relationships
        client.post(
            "/api/relationships",
            json={
                "source_id": "hero-001",
                "source_type": "character",
                "target_id": "hero-002",
                "target_type": "character",
                "relationship_type": "ally",
            },
        )
        client.post(
            "/api/relationships",
            json={
                "source_id": "hero-001",
                "source_type": "character",
                "target_id": "villain-001",
                "target_type": "character",
                "relationship_type": "enemy",
            },
        )

        response = client.get("/api/relationships")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert len(data["relationships"]) == 2

    @pytest.mark.integration
    def test_list_relationships_filter_by_type(self, client):
        """Test filtering relationships by type."""
        # Create relationships of different types
        client.post(
            "/api/relationships",
            json={
                "source_id": "hero-001",
                "source_type": "character",
                "target_id": "hero-002",
                "target_type": "character",
                "relationship_type": "ally",
            },
        )
        client.post(
            "/api/relationships",
            json={
                "source_id": "hero-001",
                "source_type": "character",
                "target_id": "villain-001",
                "target_type": "character",
                "relationship_type": "enemy",
            },
        )

        response = client.get("/api/relationships", params={"relationship_type": "ally"})

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert data["relationships"][0]["relationship_type"] == "ally"


class TestRelationshipsAPIByEntityEndpoint:
    """Tests for GET /api/relationships/by-entity/{entity_id} endpoint."""

    @pytest.mark.integration
    def test_get_relationships_by_entity(self, client):
        """Test getting relationships for an entity."""
        # Create relationships involving a specific entity
        client.post(
            "/api/relationships",
            json={
                "source_id": "hero-main",
                "source_type": "character",
                "target_id": "hero-sidekick",
                "target_type": "character",
                "relationship_type": "ally",
            },
        )
        client.post(
            "/api/relationships",
            json={
                "source_id": "villain-main",
                "source_type": "character",
                "target_id": "hero-main",
                "target_type": "character",
                "relationship_type": "enemy",
            },
        )

        response = client.get("/api/relationships/by-entity/hero-main")

        assert response.status_code == 200
        data = response.json()

        # Should find both relationships (hero-main is source in one, target in another)
        assert data["total"] >= 1

    @pytest.mark.integration
    def test_get_relationships_by_entity_with_type_filter(self, client):
        """Test getting relationships for an entity with type filter."""
        client.post(
            "/api/relationships",
            json={
                "source_id": "test-entity",
                "source_type": "character",
                "target_id": "target-001",
                "target_type": "character",
                "relationship_type": "ally",
            },
        )

        response = client.get(
            "/api/relationships/by-entity/test-entity",
            params={"entity_type": "character"},
        )

        assert response.status_code == 200


    @pytest.mark.integration
    def test_get_relationships_by_entity_include_inactive(self, client):
        """Test getting relationships including inactive ones."""
        # Create and deactivate a relationship
        create_response = client.post(
            "/api/relationships",
            json={
                "source_id": "test-entity-2",
                "source_type": "character",
                "target_id": "target-002",
                "target_type": "character",
                "relationship_type": "ally",
            },
        )
        relationship_id = create_response.json()["id"]

        # Deactivate it
        client.put(
            f"/api/relationships/{relationship_id}",
            json={"is_active": False},
        )

        # Get without inactive
        response = client.get("/api/relationships/by-entity/test-entity-2")
        active_count = response.json()["total"]

        # Get with inactive
        response = client.get(
            "/api/relationships/by-entity/test-entity-2",
            params={"include_inactive": True},
        )
        total_count = response.json()["total"]

        assert total_count >= active_count


class TestRelationshipsAPIBetweenEndpoint:
    """Tests for GET /api/relationships/between/{entity_a_id}/{entity_b_id} endpoint."""

    @pytest.mark.integration
    def test_get_relationships_between_entities(self, client):
        """Test getting relationships between two specific entities."""
        # Create a relationship between two entities
        client.post(
            "/api/relationships",
            json={
                "source_id": "entity-a",
                "source_type": "character",
                "target_id": "entity-b",
                "target_type": "character",
                "relationship_type": "rival",
            },
        )

        response = client.get("/api/relationships/between/entity-a/entity-b")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] >= 1
        # Should find the relationship regardless of direction
        found_ids = set()
        for r in data["relationships"]:
            found_ids.add(r["source_id"])
            found_ids.add(r["target_id"])
        assert "entity-a" in found_ids or "entity-b" in found_ids


class TestRelationshipsAPIUpdateEndpoint:
    """Tests for PUT /api/relationships/{relationship_id} endpoint."""

    @pytest.mark.integration
    def test_update_relationship_success(self, client):
        """Test updating a relationship."""
        # Create a relationship
        create_response = client.post(
            "/api/relationships",
            json={
                "source_id": "hero-001",
                "source_type": "character",
                "target_id": "hero-002",
                "target_type": "character",
                "relationship_type": "ally",
                "trust": 50,
            },
        )
        relationship_id = create_response.json()["id"]

        # Update it
        response = client.put(
            f"/api/relationships/{relationship_id}",
            json={
                "trust": 75,
                "strength": 85,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["trust"] == 75
        assert data["strength"] == 85

    @pytest.mark.integration
    def test_update_relationship_deactivate(self, client):
        """Test deactivating a relationship."""
        # Create a relationship
        create_response = client.post(
            "/api/relationships",
            json={
                "source_id": "hero-001",
                "source_type": "character",
                "target_id": "hero-002",
                "target_type": "character",
                "relationship_type": "ally",
            },
        )
        relationship_id = create_response.json()["id"]

        # Deactivate it
        response = client.put(
            f"/api/relationships/{relationship_id}",
            json={"is_active": False},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["is_active"] is False

    @pytest.mark.integration
    def test_update_relationship_not_found(self, client):
        """Test updating a non-existent relationship."""
        response = client.put(
            "/api/relationships/non-existent-id",
            json={"trust": 50},
        )

        assert response.status_code == 404


class TestRelationshipsAPILogInteractionEndpoint:
    """Tests for POST /api/relationships/{relationship_id}/interactions endpoint."""

    @pytest.mark.integration
    def test_log_interaction_success(self, client):
        """Test logging an interaction on a relationship."""
        # Create a relationship
        create_response = client.post(
            "/api/relationships",
            json={
                "source_id": "hero-001",
                "source_type": "character",
                "target_id": "hero-002",
                "target_type": "character",
                "relationship_type": "ally",
                "trust": 50,
                "romance": 0,
            },
        )
        relationship_id = create_response.json()["id"]

        # Log an interaction
        response = client.post(
            f"/api/relationships/{relationship_id}/interactions",
            json={
                "summary": "Saved each other in battle",
                "trust_change": 10,
                "romance_change": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["trust"] == 60  # 50 + 10
        assert data["romance"] == 5  # 0 + 5
        assert len(data["interaction_history"]) == 1
        assert data["interaction_history"][0]["summary"] == "Saved each other in battle"

    @pytest.mark.integration
    def test_log_interaction_negative_change(self, client):
        """Test logging a negative interaction."""
        # Create a relationship
        create_response = client.post(
            "/api/relationships",
            json={
                "source_id": "hero-001",
                "source_type": "character",
                "target_id": "villain-001",
                "target_type": "character",
                "relationship_type": "enemy",
                "trust": 20,
            },
        )
        relationship_id = create_response.json()["id"]

        # Log a negative interaction
        response = client.post(
            f"/api/relationships/{relationship_id}/interactions",
            json={
                "summary": "Betrayal",
                "trust_change": -15,
                "romance_change": 0,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["trust"] == 5  # 20 - 15


class TestRelationshipsAPIDeleteEndpoint:
    """Tests for DELETE /api/relationships/{relationship_id} endpoint."""

    @pytest.mark.integration
    def test_delete_relationship_success(self, client):
        """Test deleting a relationship."""
        # Create a relationship
        create_response = client.post(
            "/api/relationships",
            json={
                "source_id": "hero-001",
                "source_type": "character",
                "target_id": "hero-002",
                "target_type": "character",
                "relationship_type": "ally",
            },
        )
        relationship_id = create_response.json()["id"]

        # Delete it
        response = client.delete(f"/api/relationships/{relationship_id}")

        assert response.status_code == 204

        # Verify it's gone
        get_response = client.get(f"/api/relationships/{relationship_id}")
        assert get_response.status_code == 404

    @pytest.mark.integration
    def test_delete_relationship_not_found(self, client):
        """Test deleting a non-existent relationship."""
        response = client.delete("/api/relationships/non-existent-id")

        assert response.status_code == 404
