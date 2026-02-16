#!/usr/bin/env python3
"""
Tests for Diplomacy API Router

Tests for the diplomacy endpoints including matrix retrieval,
faction relations, and status updates.
"""

import sys
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

# Mock problematic dependencies
sys.modules["aioredis"] = MagicMock()


@pytest.fixture(autouse=True)
def reset_storage():
    """Reset diplomacy storage before each test."""
    from src.api.routers.diplomacy import reset_diplomacy_storage

    reset_diplomacy_storage()
    yield
    reset_diplomacy_storage()


@pytest.fixture
def client():
    """Create a test client with the diplomacy router."""
    from fastapi import FastAPI

    from src.api.routers.diplomacy import router

    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


class TestGetDiplomacyMatrix:
    """Tests for GET /world/{world_id}/diplomacy endpoint."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_empty_matrix(self, client):
        """Test getting an empty diplomacy matrix for a new world."""
        response = client.get("/api/world/test-world/diplomacy")

        assert response.status_code == 200
        data = response.json()
        assert data["world_id"] == "test-world"
        assert data["matrix"] == {}
        assert data["factions"] == []

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_matrix_with_factions(self, client):
        """Test getting a matrix after setting relations."""
        # First set a relation
        client.put(
            "/api/world/test-world/diplomacy/faction-a/faction-b",
            json={"status": "allied"},
        )

        # Then get the matrix
        response = client.get("/api/world/test-world/diplomacy")

        assert response.status_code == 200
        data = response.json()
        assert data["world_id"] == "test-world"
        assert "faction-a" in data["factions"]
        assert "faction-b" in data["factions"]
        assert data["matrix"]["faction-a"]["faction-b"] == "allied"
        assert data["matrix"]["faction-b"]["faction-a"] == "allied"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_matrix_self_relation_is_dash(self, client):
        """Test that self-relations in matrix are '-'."""
        client.put(
            "/api/world/test-world/diplomacy/faction-a/faction-b",
            json={"status": "allied"},
        )

        response = client.get("/api/world/test-world/diplomacy")
        data = response.json()

        assert data["matrix"]["faction-a"]["faction-a"] == "-"
        assert data["matrix"]["faction-b"]["faction-b"] == "-"


class TestGetFactionDiplomacy:
    """Tests for GET /world/{world_id}/diplomacy/faction/{faction_id} endpoint."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_faction_not_found(self, client):
        """Test getting diplomacy for nonexistent faction."""
        response = client.get("/api/world/test-world/diplomacy/faction/unknown")

        assert response.status_code == 404

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_faction_allies(self, client):
        """Test getting allies for a faction."""
        # Set up relations
        client.put(
            "/api/world/test-world/diplomacy/faction-a/faction-b",
            json={"status": "allied"},
        )
        client.put(
            "/api/world/test-world/diplomacy/faction-a/faction-c",
            json={"status": "allied"},
        )
        client.put(
            "/api/world/test-world/diplomacy/faction-a/faction-d",
            json={"status": "hostile"},
        )

        response = client.get("/api/world/test-world/diplomacy/faction/faction-a")

        assert response.status_code == 200
        data = response.json()
        assert data["faction_id"] == "faction-a"
        assert set(data["allies"]) == {"faction-b", "faction-c"}
        assert data["enemies"] == ["faction-d"]
        assert data["neutral"] == []

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_faction_enemies(self, client):
        """Test getting enemies for a faction."""
        client.put(
            "/api/world/test-world/diplomacy/faction-a/faction-b",
            json={"status": "at_war"},
        )
        client.put(
            "/api/world/test-world/diplomacy/faction-a/faction-c",
            json={"status": "hostile"},
        )

        response = client.get("/api/world/test-world/diplomacy/faction/faction-a")

        assert response.status_code == 200
        data = response.json()
        assert set(data["enemies"]) == {"faction-b", "faction-c"}
        assert data["allies"] == []

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_faction_neutral(self, client):
        """Test getting neutral relations for a faction."""
        client.put(
            "/api/world/test-world/diplomacy/faction-a/faction-b",
            json={"status": "neutral"},
        )
        client.put(
            "/api/world/test-world/diplomacy/faction-a/faction-c",
            json={"status": "neutral"},
        )

        response = client.get("/api/world/test-world/diplomacy/faction/faction-a")

        assert response.status_code == 200
        data = response.json()
        assert set(data["neutral"]) == {"faction-b", "faction-c"}


class TestSetRelation:
    """Tests for PUT /world/{world_id}/diplomacy/{faction_a}/{faction_b} endpoint."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_set_allied_status(self, client):
        """Test setting ALLIED status between factions."""
        response = client.put(
            "/api/world/test-world/diplomacy/faction-a/faction-b",
            json={"status": "allied"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["matrix"]["faction-a"]["faction-b"] == "allied"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_set_at_war_status(self, client):
        """Test setting AT_WAR status between factions."""
        response = client.put(
            "/api/world/test-world/diplomacy/faction-a/faction-b",
            json={"status": "at_war"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["matrix"]["faction-a"]["faction-b"] == "at_war"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_set_all_status_types(self, client):
        """Test setting all valid status types."""
        statuses = ["allied", "friendly", "neutral", "cold", "hostile", "at_war"]

        for i, status in enumerate(statuses):
            response = client.put(
                f"/api/world/test-world/diplomacy/faction-{i}/faction-{i + 10}",
                json={"status": status},
            )
            assert response.status_code == 200

    @pytest.mark.unit
    @pytest.mark.fast
    def test_set_invalid_status(self, client):
        """Test setting an invalid status returns 400."""
        response = client.put(
            "/api/world/test-world/diplomacy/faction-a/faction-b",
            json={"status": "unknown"},
        )

        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]

    @pytest.mark.unit
    @pytest.mark.fast
    def test_set_relation_is_symmetric(self, client):
        """Test that setting relation is symmetric (A->B same as B->A)."""
        # Set A -> B
        client.put(
            "/api/world/test-world/diplomacy/faction-a/faction-b",
            json={"status": "allied"},
        )

        # Get faction B's relations
        response = client.get("/api/world/test-world/diplomacy/faction/faction-b")

        assert response.status_code == 200
        data = response.json()
        assert "faction-a" in data["allies"]

    @pytest.mark.unit
    @pytest.mark.fast
    def test_set_self_relation_fails(self, client):
        """Test that setting self-relation fails."""
        response = client.put(
            "/api/world/test-world/diplomacy/faction-a/faction-a",
            json={"status": "allied"},
        )

        assert response.status_code == 400
        assert "itself" in response.json()["detail"].lower()

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_existing_relation(self, client):
        """Test updating an existing relation."""
        # Set initial status
        client.put(
            "/api/world/test-world/diplomacy/faction-a/faction-b",
            json={"status": "allied"},
        )

        # Update to new status
        response = client.put(
            "/api/world/test-world/diplomacy/faction-a/faction-b",
            json={"status": "at_war"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["matrix"]["faction-a"]["faction-b"] == "at_war"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_status_case_insensitive(self, client):
        """Test that status values are case-insensitive."""
        response = client.put(
            "/api/world/test-world/diplomacy/faction-a/faction-b",
            json={"status": "ALLIED"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["matrix"]["faction-a"]["faction-b"] == "allied"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_status_with_whitespace(self, client):
        """Test that status values with whitespace are handled."""
        response = client.put(
            "/api/world/test-world/diplomacy/faction-a/faction-b",
            json={"status": "  allied  "},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["matrix"]["faction-a"]["faction-b"] == "allied"


class TestWorldsAreIsolated:
    """Tests for world isolation."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_different_worlds_isolated(self, client):
        """Test that different worlds have isolated diplomacy matrices."""
        # Set relation in world-1
        client.put(
            "/api/world/world-1/diplomacy/faction-a/faction-b",
            json={"status": "allied"},
        )

        # Set different relation in world-2
        client.put(
            "/api/world/world-2/diplomacy/faction-a/faction-b",
            json={"status": "at_war"},
        )

        # Verify isolation
        response1 = client.get("/api/world/world-1/diplomacy")
        response2 = client.get("/api/world/world-2/diplomacy")

        data1 = response1.json()
        data2 = response2.json()

        assert data1["matrix"]["faction-a"]["faction-b"] == "allied"
        assert data2["matrix"]["faction-a"]["faction-b"] == "at_war"
