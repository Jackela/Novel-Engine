#!/usr/bin/env python3
"""
Items API Integration Tests

Tests the Items API endpoints with full request/response validation.
Items are game objects that can be collected, equipped, and used.
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
    """Reset the item repository before each test."""
    from src.api.routers.items import get_repository, _character_inventories

    repo = get_repository()
    # Clear the repository
    repo._items.clear()
    repo._id_counter = 0
    # Clear inventories
    _character_inventories.clear()

    yield

    # Cleanup after test
    repo._items.clear()
    _character_inventories.clear()


class TestItemsAPICreateEndpoint:
    """Tests for POST /api/items endpoint."""

    @pytest.mark.integration
    def test_create_item_success(self, client):
        """Test creating a new item."""
        item_data = {
            "name": "Sword of Valor",
            "item_type": "weapon",
            "description": "A legendary blade",
            "rarity": "legendary",
            "weight": 5.0,
            "value": 1000,
            "is_equippable": True,
            "is_consumable": False,
            "effects": {"damage": 50, "speed": -5},
            "lore": "Forged in dragon fire",
        }

        response = client.post("/api/items", json=item_data)

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "Sword of Valor"
        assert data["item_type"] == "weapon"
        assert data["rarity"] == "legendary"
        assert data["is_equippable"] is True
        assert data["effects"]["damage"] == 50
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.integration
    def test_create_item_minimal(self, client):
        """Test creating an item with minimal fields."""
        item_data = {
            "name": "Simple Rock",
            "item_type": "misc",
            "rarity": "common",
        }

        response = client.post("/api/items", json=item_data)

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "Simple Rock"
        assert data["item_type"] == "misc"
        assert data["rarity"] == "common"

    @pytest.mark.integration
    def test_create_item_invalid_type(self, client):
        """Test creating an item with invalid type."""
        item_data = {
            "name": "Invalid Item",
            "item_type": "nonexistent_type",
            "rarity": "common",
        }

        response = client.post("/api/items", json=item_data)

        assert response.status_code == 400
        assert "Invalid item type" in response.json()["detail"]

    @pytest.mark.integration
    def test_create_item_invalid_rarity(self, client):
        """Test creating an item with invalid rarity."""
        item_data = {
            "name": "Invalid Item",
            "item_type": "weapon",
            "rarity": "nonexistent_rarity",
        }

        response = client.post("/api/items", json=item_data)

        assert response.status_code == 400
        assert "Invalid rarity" in response.json()["detail"]


class TestItemsAPIGetEndpoint:
    """Tests for GET /api/items/{item_id} endpoint."""

    @pytest.mark.integration
    def test_get_item_success(self, client):
        """Test getting an item by ID."""
        # First create an item
        create_response = client.post(
            "/api/items",
            json={
                "name": "Test Sword",
                "item_type": "weapon",
                "rarity": "rare",
            },
        )
        item_id = create_response.json()["id"]

        # Then get it
        response = client.get(f"/api/items/{item_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == item_id
        assert data["name"] == "Test Sword"

    @pytest.mark.integration
    def test_get_item_not_found(self, client):
        """Test getting a non-existent item."""
        response = client.get("/api/items/non-existent-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestItemsAPIListEndpoint:
    """Tests for GET /api/items endpoint."""

    @pytest.mark.integration
    def test_list_items_empty(self, client):
        """Test listing items when none exist."""
        response = client.get("/api/items")

        assert response.status_code == 200
        data = response.json()

        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.integration
    def test_list_items_with_data(self, client):
        """Test listing items with data."""
        # Create some items
        client.post(
            "/api/items",
            json={"name": "Sword", "item_type": "weapon", "rarity": "common"},
        )
        client.post(
            "/api/items",
            json={"name": "Potion", "item_type": "consumable", "rarity": "common"},
        )

        response = client.get("/api/items")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert len(data["items"]) == 2

    @pytest.mark.integration
    def test_list_items_filter_by_type(self, client):
        """Test filtering items by type."""
        # Create items of different types
        client.post(
            "/api/items",
            json={"name": "Sword", "item_type": "weapon", "rarity": "common"},
        )
        client.post(
            "/api/items",
            json={"name": "Potion", "item_type": "consumable", "rarity": "common"},
        )

        response = client.get("/api/items", params={"item_type": "weapon"})

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert data["items"][0]["item_type"] == "weapon"

    @pytest.mark.integration
    def test_list_items_search_by_name(self, client):
        """Test searching items by name."""
        client.post(
            "/api/items",
            json={"name": "Dragon Sword", "item_type": "weapon", "rarity": "rare"},
        )
        client.post(
            "/api/items",
            json={"name": "Health Potion", "item_type": "consumable", "rarity": "common"},
        )

        response = client.get("/api/items", params={"search": "Dragon"})

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert "Dragon" in data["items"][0]["name"]


class TestItemsAPIUpdateEndpoint:
    """Tests for PUT /api/items/{item_id} endpoint."""

    @pytest.mark.integration
    def test_update_item_success(self, client):
        """Test updating an item."""
        # Create an item
        create_response = client.post(
            "/api/items",
            json={"name": "Basic Sword", "item_type": "weapon", "rarity": "common"},
        )
        item_id = create_response.json()["id"]

        # Update it
        update_data = {
            "name": "Enhanced Sword",
            "rarity": "rare",
            "effects": {"damage": 25},
        }

        response = client.put(f"/api/items/{item_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Enhanced Sword"
        assert data["rarity"] == "rare"
        assert data["effects"]["damage"] == 25

    @pytest.mark.integration
    def test_update_item_not_found(self, client):
        """Test updating a non-existent item."""
        response = client.put(
            "/api/items/non-existent-id",
            json={"name": "Updated Name"},
        )

        assert response.status_code == 404


class TestItemsAPIDeleteEndpoint:
    """Tests for DELETE /api/items/{item_id} endpoint."""

    @pytest.mark.integration
    def test_delete_item_success(self, client):
        """Test deleting an item."""
        # Create an item
        create_response = client.post(
            "/api/items",
            json={"name": "Disposable Item", "item_type": "misc", "rarity": "common"},
        )
        item_id = create_response.json()["id"]

        # Delete it
        response = client.delete(f"/api/items/{item_id}")

        assert response.status_code == 204

        # Verify it's gone
        get_response = client.get(f"/api/items/{item_id}")
        assert get_response.status_code == 404

    @pytest.mark.integration
    def test_delete_item_not_found(self, client):
        """Test deleting a non-existent item."""
        response = client.delete("/api/items/non-existent-id")

        assert response.status_code == 404


class TestCharacterInventoryEndpoints:
    """Tests for character inventory operations."""

    @pytest.mark.integration
    def test_give_item_to_character(self, client):
        """Test giving an item to a character."""
        # Create an item
        create_response = client.post(
            "/api/items",
            json={"name": "Gift Sword", "item_type": "weapon", "rarity": "common"},
        )
        item_id = create_response.json()["id"]

        # Give it to a character
        response = client.post(
            f"/api/characters/hero-001/give-item",
            json={"item_id": item_id},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "added to character" in data["message"].lower()

    @pytest.mark.integration
    def test_give_item_not_found(self, client):
        """Test giving a non-existent item to a character."""
        response = client.post(
            "/api/characters/hero-001/give-item",
            json={"item_id": "non-existent-item"},
        )

        assert response.status_code == 404

    @pytest.mark.integration
    def test_give_duplicate_item(self, client):
        """Test giving an item that character already has."""
        # Create an item
        create_response = client.post(
            "/api/items",
            json={"name": "Duplicate Sword", "item_type": "weapon", "rarity": "common"},
        )
        item_id = create_response.json()["id"]

        # Give it once
        client.post(
            f"/api/characters/hero-001/give-item",
            json={"item_id": item_id},
        )

        # Try to give again
        response = client.post(
            f"/api/characters/hero-001/give-item",
            json={"item_id": item_id},
        )

        assert response.status_code == 409

    @pytest.mark.integration
    def test_get_character_inventory(self, client):
        """Test getting a character's inventory."""
        # Create items
        item1_response = client.post(
            "/api/items",
            json={"name": "Sword", "item_type": "weapon", "rarity": "common"},
        )
        item2_response = client.post(
            "/api/items",
            json={"name": "Potion", "item_type": "consumable", "rarity": "common"},
        )

        item1_id = item1_response.json()["id"]
        item2_id = item2_response.json()["id"]

        # Give items to character
        client.post(
            f"/api/characters/inventory-hero/give-item",
            json={"item_id": item1_id},
        )
        client.post(
            f"/api/characters/inventory-hero/give-item",
            json={"item_id": item2_id},
        )

        # Get inventory
        response = client.get("/api/characters/inventory-hero/inventory")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        item_names = [item["name"] for item in data["items"]]
        assert "Sword" in item_names
        assert "Potion" in item_names

    @pytest.mark.integration
    def test_get_empty_inventory(self, client):
        """Test getting inventory for character with no items."""
        response = client.get("/api/characters/empty-hero/inventory")

        assert response.status_code == 200
        data = response.json()

        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.integration
    def test_remove_item_from_character(self, client):
        """Test removing an item from character's inventory."""
        # Create and give item
        create_response = client.post(
            "/api/items",
            json={"name": "Removable Sword", "item_type": "weapon", "rarity": "common"},
        )
        item_id = create_response.json()["id"]

        client.post(
            f"/api/characters/remove-hero/give-item",
            json={"item_id": item_id},
        )

        # Remove it
        response = client.delete(f"/api/characters/remove-hero/remove-item/{item_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "removed" in data["message"].lower()
