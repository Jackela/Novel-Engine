"""
API tests for World State endpoints.

Tests cover:
- GET /world/{world_id}/territories
- GET /world/{world_id}/diplomacy
- GET /world/{world_id}/resources
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers.world_state import router as world_state_router

pytestmark = pytest.mark.integration


@pytest.fixture
def app():
    """Create a test FastAPI app with world_state router."""
    app = FastAPI()
    app.include_router(world_state_router, prefix="/api")
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def world_store(app):
    """Create a world store with test data."""
    store = {
        "test-world": {
            "id": "test-world",
            "name": "Test World",
            "locations": [
                {
                    "id": "loc-1",
                    "name": "Capital City",
                    "location_type": "city",
                    "controlling_faction_id": "faction-1",
                    "contested_by": [],
                    "territory_value": 80,
                    "infrastructure_level": 75,
                    "population": 50000,
                    "resource_yields": [
                        {"resource_type": "gold", "current_stock": 1000},
                        {"resource_type": "food", "current_stock": 500},
                    ],
                },
                {
                    "id": "loc-2",
                    "name": "Border Fortress",
                    "location_type": "fortress",
                    "controlling_faction_id": "faction-1",
                    "contested_by": ["faction-2"],
                    "territory_value": 90,
                    "infrastructure_level": 60,
                    "population": 5000,
                    "resource_yields": [
                        {"resource_type": "iron", "current_stock": 200},
                    ],
                },
                {
                    "id": "loc-3",
                    "name": "Rebel Village",
                    "location_type": "village",
                    "controlling_faction_id": None,
                    "contested_by": [],
                    "territory_value": 20,
                    "infrastructure_level": 30,
                    "population": 1000,
                    "resource_yields": [],
                },
            ],
            "factions": [
                {
                    "id": "faction-1",
                    "name": "Kingdom of Light",
                    "resources": {"gold": 5000, "military": 1000},
                },
                {
                    "id": "faction-2",
                    "name": "Dark Empire",
                    "resources": {"gold": 3000, "military": 2000},
                },
            ],
            "diplomacy_matrix": {
                "matrix": {
                    "faction-1": {"faction-1": "-", "faction-2": "hostile"},
                    "faction-2": {"faction-1": "hostile", "faction-2": "-"},
                },
                "factions": ["faction-1", "faction-2"],
                "active_pacts": [
                    {
                        "id": "pact-1",
                        "faction_a_id": "faction-1",
                        "faction_b_id": "faction-2",
                        "pact_type": "ceasefire",
                        "signed_date": "2024-01-01",
                        "expires_date": "2024-12-31",
                        "is_active": True,
                    }
                ],
            },
        }
    }
    app.state.world_store = store
    return store


class TestTerritoriesEndpoint:
    """Tests for GET /world/{world_id}/territories."""

    def test_get_territories_success(self, client, world_store):
        """Test getting territories for a valid world."""
        response = client.get("/api/world/test-world/territories")

        assert response.status_code == 200
        data = response.json()

        assert data["world_id"] == "test-world"
        assert data["total_count"] == 3
        assert data["controlled_count"] == 2  # loc-1 and loc-2
        assert data["contested_count"] == 1  # loc-2
        assert len(data["territories"]) == 3

    def test_get_territories_world_not_found(self, client, world_store):
        """Test getting territories for non-existent world."""
        response = client.get("/api/world/nonexistent/territories")

        assert response.status_code == 404

    def test_territory_has_correct_fields(self, client, world_store):
        """Test that territory has all expected fields."""
        response = client.get("/api/world/test-world/territories")

        data = response.json()
        territory = data["territories"][0]  # Capital City

        assert "location_id" in territory
        assert "name" in territory
        assert "location_type" in territory
        assert "controlling_faction_id" in territory
        assert "contested_by" in territory
        assert "territory_value" in territory
        assert "infrastructure_level" in territory
        assert "population" in territory
        assert "resource_types" in territory

    def test_contested_territory_has_contenders(self, client, world_store):
        """Test that contested territory shows contenders."""
        response = client.get("/api/world/test-world/territories")

        data = response.json()
        fortress = [t for t in data["territories"] if t["name"] == "Border Fortress"][0]

        assert fortress["contested_by"] == ["faction-2"]


class TestDiplomacyEndpoint:
    """Tests for GET /world/{world_id}/diplomacy."""

    def test_get_diplomacy_success(self, client, world_store):
        """Test getting diplomacy matrix for a valid world."""
        response = client.get("/api/world/test-world/diplomacy")

        assert response.status_code == 200
        data = response.json()

        assert data["world_id"] == "test-world"
        assert "matrix" in data
        assert "factions" in data
        assert "active_pacts" in data

    def test_diplomacy_matrix_values(self, client, world_store):
        """Test diplomacy matrix has correct values."""
        response = client.get("/api/world/test-world/diplomacy")

        data = response.json()
        matrix = data["matrix"]

        # Self-relation should be "-"
        assert matrix["faction-1"]["faction-1"] == "-"
        # Hostile relation
        assert matrix["faction-1"]["faction-2"] == "hostile"

    def test_diplomacy_includes_pacts(self, client, world_store):
        """Test that diplomacy includes active pacts."""
        response = client.get("/api/world/test-world/diplomacy")

        data = response.json()
        pacts = data["active_pacts"]

        assert len(pacts) == 1
        assert pacts[0]["pact_type"] == "ceasefire"
        assert pacts[0]["is_active"] is True

    def test_diplomacy_world_not_found(self, client, world_store):
        """Test getting diplomacy for non-existent world."""
        response = client.get("/api/world/nonexistent/diplomacy")

        assert response.status_code == 404


class TestResourcesEndpoint:
    """Tests for GET /world/{world_id}/resources."""

    def test_get_resources_success(self, client, world_store):
        """Test getting resources for a valid world."""
        response = client.get("/api/world/test-world/resources")

        assert response.status_code == 200
        data = response.json()

        assert data["world_id"] == "test-world"
        assert "factions" in data
        assert "total_resources" in data
        assert "timestamp" in data

    def test_faction_resource_summary(self, client, world_store):
        """Test faction resource summary has correct fields."""
        response = client.get("/api/world/test-world/resources")

        data = response.json()
        faction = data["factions"][0]

        assert "faction_id" in faction
        assert "faction_name" in faction
        assert "resources" in faction
        assert "total_territories" in faction
        assert "total_population" in faction

    def test_resources_world_not_found(self, client, world_store):
        """Test getting resources for non-existent world."""
        response = client.get("/api/world/nonexistent/resources")

        assert response.status_code == 404

    def test_resources_include_territory_resources(self, client, world_store):
        """Test that resources include territory yields."""
        response = client.get("/api/world/test-world/resources")

        data = response.json()
        kingdom = [f for f in data["factions"] if f["faction_id"] == "faction-1"][0]

        # Kingdom controls loc-1 (50000 pop) and loc-2 (5000 pop)
        assert kingdom["total_territories"] == 2
        assert kingdom["total_population"] == 55000
