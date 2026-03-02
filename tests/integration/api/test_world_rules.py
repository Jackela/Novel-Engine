"""Integration tests for World Rules API endpoints.

Tests the world rules CRUD endpoints for managing world laws,
magic systems, and physics constraints.
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
class TestWorldRulesEndpoints:
    """Tests for world rules management endpoints."""

    def test_list_world_rules(self, client: TestClient) -> None:
        """Test GET /api/world-rules endpoint."""
        response = client.get("/api/world-rules")

        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert "total" in data
        assert isinstance(data["rules"], list)

    def test_create_world_rule(self, client: TestClient) -> None:
        """Test POST /api/world-rules endpoint."""
        response = client.post(
            "/api/world-rules",
            json={
                "name": "Magic Requires Sacrifice",
                "description": "All magical acts require a sacrifice proportional to the power invoked",
                "consequence": "Attempting magic without sacrifice results in backlash damage",
                "exceptions": ["Divine intervention", "Artifact-based magic"],
                "category": "magic",
                "severity": 75,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Magic Requires Sacrifice"
        assert "id" in data
        assert data["category"] == "magic"

    def test_get_world_rule_by_id(self, client: TestClient) -> None:
        """Test GET /api/world-rules/{rule_id} endpoint."""
        # First create a rule
        create_response = client.post(
            "/api/world-rules",
            json={
                "name": "Gravity Works Normally",
                "description": "Standard gravity applies",
                "consequence": "Falling causes damage",
                "category": "physics",
                "severity": 100,
            },
        )
        rule_id = create_response.json()["id"]

        # Then get it
        response = client.get(f"/api/world-rules/{rule_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == rule_id

    def test_get_nonexistent_rule(self, client: TestClient) -> None:
        """Test GET /api/world-rules/{rule_id} with invalid ID."""
        response = client.get("/api/world-rules/nonexistent-rule-id")

        assert response.status_code == 404

    def test_update_world_rule(self, client: TestClient) -> None:
        """Test PUT /api/world-rules/{rule_id} endpoint."""
        # Create a rule first
        create_response = client.post(
            "/api/world-rules",
            json={
                "name": "Original Rule",
                "description": "Original description",
                "consequence": "Original consequence",
                "category": "custom",
                "severity": 50,
            },
        )
        rule_id = create_response.json()["id"]

        # Update it
        response = client.put(
            f"/api/world-rules/{rule_id}",
            json={
                "name": "Updated Rule",
                "severity": 80,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Rule"
        assert data["severity"] == 80

    def test_delete_world_rule(self, client: TestClient) -> None:
        """Test DELETE /api/world-rules/{rule_id} endpoint."""
        # Create a rule first
        create_response = client.post(
            "/api/world-rules",
            json={
                "name": "Rule to Delete",
                "description": "This will be deleted",
                "consequence": "None",
                "category": "test",
                "severity": 10,
            },
        )
        rule_id = create_response.json()["id"]

        # Delete it
        response = client.delete(f"/api/world-rules/{rule_id}")

        assert response.status_code == 204

        # Verify it's deleted
        get_response = client.get(f"/api/world-rules/{rule_id}")
        assert get_response.status_code == 404


@pytest.mark.integration
class TestWorldRulesFiltering:
    """Tests for world rules filtering and search endpoints."""

    def test_list_rules_by_category(self, client: TestClient) -> None:
        """Test GET /api/world-rules with category filter."""
        # Create rules in different categories
        client.post(
            "/api/world-rules",
            json={
                "name": "Magic Rule",
                "description": "A magic rule",
                "consequence": "Magic consequence",
                "category": "magic",
                "severity": 50,
            },
        )

        response = client.get("/api/world-rules?category=magic")

        assert response.status_code == 200
        data = response.json()
        # All returned rules should be in the magic category
        for rule in data["rules"]:
            assert rule["category"] == "magic"

    def test_list_rules_by_severity_range(self, client: TestClient) -> None:
        """Test GET /api/world-rules with severity filters."""
        response = client.get("/api/world-rules?min_severity=50&max_severity=100")

        assert response.status_code == 200
        data = response.json()
        for rule in data["rules"]:
            assert 50 <= rule["severity"] <= 100

    def test_search_rules(self, client: TestClient) -> None:
        """Test GET /api/world-rules/search endpoint."""
        # Create a rule with a unique name
        client.post(
            "/api/world-rules",
            json={
                "name": "Unique Searchable Rule Name",
                "description": "Test description",
                "consequence": "Test consequence",
                "category": "test",
                "severity": 25,
            },
        )

        response = client.get("/api/world-rules/search?q=Unique")

        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert "total" in data

    def test_list_absolute_rules(self, client: TestClient) -> None:
        """Test GET /api/world-rules/absolute endpoint."""
        # Create an absolute rule (severity >= 90)
        client.post(
            "/api/world-rules",
            json={
                "name": "Absolute Law",
                "description": "An unbreakable law",
                "consequence": "Reality collapse",
                "category": "fundamental",
                "severity": 100,
            },
        )

        response = client.get("/api/world-rules/absolute")

        assert response.status_code == 200
        data = response.json()
        for rule in data["rules"]:
            assert rule["severity"] >= 90


@pytest.mark.integration
class TestWorldRulesValidation:
    """Tests for world rules request validation."""

    def test_severity_bounds(self, client: TestClient) -> None:
        """Test that severity must be between 0 and 100."""
        # Test lower bound
        response = client.post(
            "/api/world-rules",
            json={
                "name": "Invalid Rule",
                "description": "Test",
                "consequence": "Test",
                "severity": -1,
            },
        )
        assert response.status_code == 422

        # Test upper bound
        response = client.post(
            "/api/world-rules",
            json={
                "name": "Invalid Rule",
                "description": "Test",
                "consequence": "Test",
                "severity": 101,
            },
        )
        assert response.status_code == 422

    def test_required_fields(self, client: TestClient) -> None:
        """Test that required fields are validated."""
        response = client.post(
            "/api/world-rules",
            json={},
        )
        assert response.status_code == 422


@pytest.mark.integration
class TestWorldRulesResponseFormat:
    """Tests for world rules response format validation."""

    def test_rule_response_format(self, client: TestClient) -> None:
        """Test that rule response has correct format."""
        response = client.post(
            "/api/world-rules",
            json={
                "name": "Format Test Rule",
                "description": "Testing response format",
                "consequence": "Test consequence",
                "exceptions": ["Exception 1", "Exception 2"],
                "category": "test",
                "severity": 50,
            },
        )

        assert response.status_code == 201
        data = response.json()

        # Required fields
        assert "id" in data
        assert "name" in data
        assert "description" in data
        assert "consequence" in data
        assert "exceptions" in data
        assert "category" in data
        assert "severity" in data
        assert "created_at" in data
        assert "updated_at" in data

        # Types
        assert isinstance(data["exceptions"], list)
        assert isinstance(data["severity"], int)

    def test_list_response_format(self, client: TestClient) -> None:
        """Test that list response has correct format."""
        response = client.get("/api/world-rules")

        assert response.status_code == 200
        data = response.json()

        assert "rules" in data
        assert "total" in data
        assert isinstance(data["rules"], list)
        assert isinstance(data["total"], int)
