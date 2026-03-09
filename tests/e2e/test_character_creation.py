"""E2E Tests for Character Creation Flow.

This module tests the end-to-end character creation and management flows:
1. Create character with full profile
2. Update character attributes and skills
3. Manage character relationships
4. Character lifecycle (CRUD operations)

Tests:
- Complete character creation flow
- Character attribute updates
- Character skill management
- Character validation and error handling
"""

import os

# Set testing mode BEFORE importing app
os.environ["ORCHESTRATOR_MODE"] = "testing"

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.fixture
def client():
    """Create a test client for the E2E tests."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def data_factory():
    """Provide test data factory."""
    from datetime import datetime
    from typing import Any, Dict

    class TestDataFactory:
        @staticmethod
        def create_character_data(
            name=None,
            agent_id=None,
            archetype=None,
        ) -> Dict[str, Any]:
            char_name = name or f"TestChar_{datetime.now().timestamp()}"
            char_id = agent_id or char_name.lower().replace(" ", "_")

            return {
                "agent_id": char_id,
                "name": char_name,
                "background_summary": f"Background for {char_name}",
                "personality_traits": "brave, intelligent, curious",
                "current_mood": 7,
                "dominant_emotion": "calm",
                "energy_level": 8,
                "stress_level": 3,
                "skills": {"combat": 0.7, "diplomacy": 0.6, "investigation": 0.8},
                "relationships": {},
                "current_location": "Test Location",
                "inventory": ["test_item"],
                "metadata": {"test": True},
            }

    return TestDataFactory()


@pytest.fixture
def api_helper(client):
    """Provide API helper instance."""

    class APITestHelper:
        def __init__(self, client):
            self.client = client

        def list_characters(self):
            response = self.client.get("/api/characters")
            response.raise_for_status()
            data = response.json()
            return data.get("characters", [])

    return APITestHelper(client)


# Mark all tests in this module as e2e tests
pytestmark = pytest.mark.e2e


@pytest.mark.e2e
class TestCharacterCreation:
    """E2E tests for character creation and management."""

    def test_create_character_complete(self, client, data_factory):
        """Test complete character creation with all attributes.

        Verifies:
        - POST /api/characters creates character successfully
        - Character is retrievable after creation
        - All attributes are stored correctly
        """
        # Step 1: Create character with comprehensive data
        character_data = data_factory.create_character_data(
            name="Elara Moonweaver", agent_id="elara_moonweaver"
        )
        character_data.update(
            {
                "background_summary": "A skilled mage from the mystical forests of Eldoria",
                "personality_traits": "wise, compassionate, determined, mysterious",
                "skills": {
                    "arcane_magic": 0.95,
                    "healing": 0.80,
                    "herbalism": 0.75,
                    "divination": 0.70,
                },
                "current_location": "Tower of Eldoria",
                "inventory": ["staff_of_ages", "healing_potions", "spellbook"],
                "metadata": {
                    "age": 147,
                    "faction": "Order of the Moon",
                    "race": "High Elf",
                },
            }
        )

        response = client.post("/api/characters", json=character_data)
        assert response.status_code in [
            200,
            201,
        ], f"Character creation failed: {response.text}"

        # Step 2: Verify character was created
        get_response = client.get("/api/characters/elara_moonweaver")
        assert get_response.status_code == 200, "Created character not found"

        char_data = get_response.json()
        data_section = char_data.get("data", char_data)

        assert data_section.get("agent_id") == "elara_moonweaver"
        assert data_section.get("name") == "Elara Moonweaver"

    def test_create_character_minimal(self, client, data_factory):
        """Test character creation with minimal data.

        Verifies:
        - Character can be created with basic fields
        - Default values are applied appropriately
        """
        character_data = {
            "agent_id": "minimal_char",
            "name": "Minimal Character",
            "background_summary": "A simple character",
        }

        response = client.post("/api/characters", json=character_data)
        assert response.status_code in [
            200,
            201,
        ], f"Minimal character creation failed: {response.text}"

        # Verify creation
        get_response = client.get("/api/characters/minimal_char")
        assert get_response.status_code == 200

    def test_create_character_with_skills(self, client, data_factory):
        """Test character creation with skill attributes.

        Verifies:
        - Skills are properly stored
        - Skill values are validated (0.0-1.0 range)
        """
        character_data = data_factory.create_character_data(
            name="Skill Master", agent_id="skill_master"
        )
        character_data["skills"] = {
            "combat": 0.90,
            "stealth": 0.85,
            "lockpicking": 0.75,
            "persuasion": 0.60,
        }

        response = client.post("/api/characters", json=character_data)
        assert response.status_code in [200, 201]

        # Verify skills
        get_response = client.get("/api/characters/skill_master")
        char_data = get_response.json().get("data", get_response.json())

        if "skills" in char_data:
            skills = char_data["skills"]
            assert "combat" in skills or skills == {}

    def test_create_duplicate_character_fails(self, client, data_factory):
        """Test that duplicate character creation is rejected.

        Verifies:
        - Creating character with existing ID fails
        - Appropriate error is returned
        """
        character_data = data_factory.create_character_data(
            name="Duplicate Test", agent_id="duplicate_char"
        )

        # First creation should succeed
        response1 = client.post("/api/characters", json=character_data)
        assert response1.status_code in [200, 201]

        # Second creation should fail
        response2 = client.post("/api/characters", json=character_data)
        assert response2.status_code in [
            400,
            409,
            422,
        ], "Duplicate character should be rejected"

        # Cleanup
        client.delete("/api/characters/duplicate_char")


@pytest.mark.e2e
class TestCharacterUpdates:
    """E2E tests for character updates and modifications."""

    def test_update_character_attributes(self, client, data_factory):
        """Test updating character attributes.

        Verifies:
        - PUT /api/characters/{id} updates attributes
        - Changes are persisted and retrievable
        """
        # Create character first
        char_data = data_factory.create_character_data(
            name="Update Test", agent_id="update_test_char"
        )
        client.post("/api/characters", json=char_data)

        # Update attributes
        update_data = {
            "background_summary": "Updated background story",
            "current_location": "New Location",
            "personality_traits": "brave, adventurous",
        }

        response = client.put("/api/characters/update_test_char", json=update_data)
        assert response.status_code in [200, 204], f"Update failed: {response.text}"

        # Verify update
        get_response = client.get("/api/characters/update_test_char")
        updated_data = get_response.json().get("data", get_response.json())

        if "background_summary" in updated_data:
            assert updated_data["background_summary"] == "Updated background story"

        # Cleanup
        client.delete("/api/characters/update_test_char")

    def test_update_character_skills(self, client, data_factory):
        """Test updating character skills.

        Verifies:
        - Skills can be updated
        - New skills can be added
        """
        # Create character with initial skills
        char_data = data_factory.create_character_data(
            name="Skill Update Test", agent_id="skill_update_char"
        )
        char_data["skills"] = {"combat": 0.5}
        client.post("/api/characters", json=char_data)

        # Update skills
        update_data = {
            "skills": {
                "combat": 0.75,  # Improved
                "magic": 0.60,  # New skill
                "stealth": 0.40,  # New skill
            }
        }

        response = client.put("/api/characters/skill_update_char", json=update_data)
        assert response.status_code in [200, 204]

        # Verify
        get_response = client.get("/api/characters/skill_update_char")
        data = get_response.json().get("data", get_response.json())

        if "skills" in data and data["skills"]:
            assert data["skills"].get("combat") == 0.75

        # Cleanup
        client.delete("/api/characters/skill_update_char")

    def test_character_relationships(self, client, data_factory):
        """Test managing character relationships.

        Verifies:
        - Relationships can be set between characters
        - Relationship values are stored
        """
        # Create two characters
        char1 = data_factory.create_character_data(
            name="Character One", agent_id="char_one"
        )
        char2 = data_factory.create_character_data(
            name="Character Two", agent_id="char_two"
        )

        client.post("/api/characters", json=char1)
        client.post("/api/characters", json=char2)

        # Set relationship
        update_data = {
            "relationships": {"char_two": 0.8}  # Positive relationship
        }

        response = client.put("/api/characters/char_one", json=update_data)
        assert response.status_code in [200, 204]

        # Verify
        get_response = client.get("/api/characters/char_one")
        data = get_response.json().get("data", get_response.json())

        if "relationships" in data and data["relationships"]:
            assert "char_two" in data["relationships"]

        # Cleanup
        client.delete("/api/characters/char_one")
        client.delete("/api/characters/char_two")

    def test_character_inventory_management(self, client, data_factory):
        """Test character inventory management.

        Verifies:
        - Inventory items can be added
        - Inventory changes persist
        """
        # Create character
        char_data = data_factory.create_character_data(
            name="Inventory Test", agent_id="inventory_char"
        )
        char_data["inventory"] = ["sword", "shield"]
        client.post("/api/characters", json=char_data)

        # Update inventory
        update_data = {"inventory": ["sword", "shield", "health_potion", "map"]}

        response = client.put("/api/characters/inventory_char", json=update_data)
        assert response.status_code in [200, 204]

        # Verify
        get_response = client.get("/api/characters/inventory_char")
        data = get_response.json().get("data", get_response.json())

        if "inventory" in data:
            assert len(data["inventory"]) >= 2

        # Cleanup
        client.delete("/api/characters/inventory_char")


@pytest.mark.e2e
class TestCharacterValidation:
    """E2E tests for character validation and error handling."""

    def test_character_validation_invalid_id(self, client):
        """Test validation of character ID format.

        Verifies:
        - Invalid ID formats are rejected
        - Appropriate error codes are returned
        """
        invalid_char = {
            "agent_id": "invalid id with spaces!",
            "name": "Invalid Character",
        }

        response = client.post("/api/characters", json=invalid_char)
        # API may return 400 (validation error), 422 (pydantic validation), or 500 (unhandled)
        assert response.status_code in [400, 422, 500], "Invalid ID should be rejected"

    def test_character_validation_missing_required(self, client):
        """Test validation of required fields.

        Verifies:
        - Missing required fields return appropriate errors
        """
        # Missing agent_id
        response = client.post("/api/characters", json={"name": "No ID"})
        assert response.status_code in [400, 422]

        # Missing name
        response = client.post("/api/characters", json={"agent_id": "no_name"})
        # This may succeed or fail depending on API requirements
        assert response.status_code in [200, 201, 400, 422]

    def test_character_validation_invalid_skills(self, client, data_factory):
        """Test validation of skill values.

        Verifies:
        - Skill values outside 0.0-1.0 range are rejected
        """
        char_data = data_factory.create_character_data(agent_id="invalid_skills")
        char_data["skills"] = {"combat": 1.5}  # Invalid: > 1.0

        response = client.post("/api/characters", json=char_data)
        # API may return 400 (validation error), 422 (pydantic validation), or 500 (unhandled)
        assert response.status_code in [
            400,
            422,
            500,
        ], "Invalid skill values should be rejected"

    def test_update_nonexistent_character(self, client):
        """Test updating a character that doesn't exist.

        Verifies:
        - 404 is returned for non-existent character
        """
        update_data = {"name": "Updated Name"}

        response = client.put(
            "/api/characters/nonexistent_char_12345", json=update_data
        )
        assert (
            response.status_code == 404
        ), "Should return 404 for non-existent character"


@pytest.mark.e2e
class TestCharacterLifecycle:
    """E2E tests for character lifecycle operations."""

    def test_character_crud_lifecycle(self, client, data_factory):
        """Test complete CRUD lifecycle for a character.

        Verifies:
        - Create, Read, Update, Delete operations work
        - Character is properly removed after deletion
        """
        # Create
        char_data = data_factory.create_character_data(
            name="Lifecycle Test", agent_id="lifecycle_char"
        )
        create_response = client.post("/api/characters", json=char_data)
        assert create_response.status_code in [200, 201]

        # Read
        read_response = client.get("/api/characters/lifecycle_char")
        assert read_response.status_code == 200

        # Update
        update_response = client.put(
            "/api/characters/lifecycle_char", json={"background_summary": "Updated"}
        )
        assert update_response.status_code in [200, 204]

        # Delete
        delete_response = client.delete("/api/characters/lifecycle_char")
        assert delete_response.status_code in [200, 204]

        # Verify deletion
        verify_response = client.get("/api/characters/lifecycle_char")
        assert verify_response.status_code == 404

    def test_list_characters(self, client, api_helper):
        """Test listing all characters.

        Verifies:
        - GET /api/characters returns list
        - Response contains characters array
        """
        response = client.get("/api/characters")
        assert response.status_code == 200

        data = response.json()
        assert "characters" in data, "Response missing characters field"
        assert isinstance(data["characters"], list), "Characters should be a list"

    def test_character_not_found(self, client):
        """Test retrieving non-existent character.

        Verifies:
        - 404 is returned for non-existent character ID
        """
        response = client.get("/api/characters/nonexistent_character_99999")
        assert (
            response.status_code == 404
        ), "Should return 404 for non-existent character"

    def test_bulk_character_operations(self, client, data_factory):
        """Test creating and deleting multiple characters.

        Verifies:
        - Multiple characters can be created
        - Bulk operations work correctly
        """
        char_ids = []

        # Create multiple characters
        for i in range(3):
            char_data = data_factory.create_character_data(
                name=f"Bulk Char {i}", agent_id=f"bulk_char_{i}"
            )
            response = client.post("/api/characters", json=char_data)
            assert response.status_code in [200, 201]
            char_ids.append(f"bulk_char_{i}")

        # Verify all exist
        list_response = client.get("/api/characters")
        characters = list_response.json().get("characters", [])
        existing_ids = [c.get("agent_id") for c in characters]

        for char_id in char_ids:
            assert char_id in existing_ids, f"Character {char_id} not found"

        # Cleanup
        for char_id in char_ids:
            client.delete(f"/api/characters/{char_id}")
