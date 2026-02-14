#!/usr/bin/env python3
"""
E2E Test: World Building and Configuration Flow
===============================================

Tests the world creation and configuration workflow:
1. Create world with settings
2. Add locations/regions
3. Configure world rules
4. Run validation
5. View world history

Coverage:
- World creation API
- World configuration/settings
- Location management
- Rule definition
- World validation
- World state persistence
"""

import time

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.e2e
class TestWorldBuildingFlow:
    """E2E tests for world building and configuration."""

    def test_world_configuration_complete(
        self, client, data_factory, performance_tracker
    ):
        """
        Test complete world building workflow.

        Flow:
        1. Create world with initial settings
        2. Verify world was created
        3. Add locations to the world
        4. Configure world rules
        5. Validate world configuration
        """
        # Step 1: Create world with comprehensive settings
        start_time = time.time()
        world_data = data_factory.create_world_data(
            name="Aetheria", description="A realm where magic and technology coexist"
        )

        # Enhance world with detailed settings
        world_data.update(
            {
                "settings": {
                    "genre": "science-fantasy",
                    "theme": "exploration",
                    "tone": "hopeful",
                    "tech_level": "advanced",
                    "magic_level": "moderate",
                    "danger_level": "medium",
                },
                "locations": [
                    {
                        "name": "Crystal Spire",
                        "description": "A towering structure of crystallized energy",
                        "type": "landmark",
                        "accessibility": "public",
                    },
                    {
                        "name": "Shadowfen Marshes",
                        "description": "Dark wetlands shrouded in mystery",
                        "type": "wilderness",
                        "accessibility": "dangerous",
                    },
                    {
                        "name": "Haven City",
                        "description": "The central hub of civilization",
                        "type": "settlement",
                        "accessibility": "public",
                    },
                ],
                "rules": [
                    "Magic requires catalysts from natural sources",
                    "Technology is powered by crystalline energy",
                    "Different regions have varying magic density",
                    "Time flows normally across all locations",
                ],
                "factions": [
                    {
                        "name": "The Crystalline Order",
                        "description": "Mages who study energy manipulation",
                        "alignment": "neutral",
                    },
                    {
                        "name": "Tech Consortium",
                        "description": "Engineers and inventors",
                        "alignment": "progressive",
                    },
                ],
            }
        )

        # Note: Actual API endpoints may vary - adapting to what's available
        # If /api/worlds doesn't exist, this test documents the desired API
        response = client.post("/api/worlds", json=world_data)

        assert response.status_code in [
            200,
            201,
        ], f"World creation failed: {response.text}"

        world_result = response.json()
        performance_tracker.record("world_creation", time.time() - start_time)

        # Step 2: Verify world was created and retrieve it
        start_time = time.time()
        world_id = world_result.get("data", {}).get("id") or "aetheria"

        response = client.get(f"/api/worlds/{world_id}")
        assert response.status_code == 200, "Failed to retrieve created world"

        retrieved_world = response.json()
        data_section = retrieved_world.get("data", retrieved_world)

        assert data_section.get("name") == "Aetheria"
        performance_tracker.record("world_retrieval", time.time() - start_time)

        # Step 3: Update world with additional locations
        start_time = time.time()
        update_data = {
            "locations": [
                {
                    "name": "Ancient Library",
                    "description": "Repository of forgotten knowledge",
                    "type": "landmark",
                    "accessibility": "restricted",
                }
            ]
        }

        response = client.put(f"/api/worlds/{world_id}", json=update_data)
        assert response.status_code in [200, 204], "Failed to update world"
        performance_tracker.record("world_update", time.time() - start_time)

        # Step 4: List all worlds
        start_time = time.time()
        response = client.get("/api/worlds")

        assert response.status_code == 200, "Failed to list worlds"
        worlds_data = response.json()
        worlds_list = worlds_data.get("data", {}).get("worlds", [])

        # Verify our world is in the list
        world_names = [w.get("name") for w in worlds_list]
        assert "Aetheria" in world_names
        performance_tracker.record("world_list", time.time() - start_time)

    def test_world_validation(self, client, data_factory):
        """Test world configuration validation."""
        # Test 1: Create world with minimal valid data
        minimal_world = {"name": "Minimal World", "description": "A simple world"}

        response = client.post("/api/worlds", json=minimal_world)

        assert response.status_code in [200, 201], "Minimal world should be valid"

        # Test 2: Invalid world data
        invalid_world = {
            "description": "Missing name"
            # name is required
        }

        response = client.post("/api/worlds", json=invalid_world)
        assert response.status_code == 422, "Should reject world without name"

        # Test 3: World with empty name
        empty_name_world = {"name": "", "description": "Empty name world"}

        response = client.post("/api/worlds", json=empty_name_world)
        assert response.status_code == 422, "Should reject world with empty name"

    def test_world_location_management(self, client, data_factory):
        """Test managing locations within a world."""
        # Create world
        world_data = data_factory.create_world_data(name="Location Test World")
        response = client.post("/api/worlds", json=world_data)

        assert response.status_code in [200, 201]

        world_id = response.json().get("data", {}).get("id") or "location_test_world"

        # Add locations one by one
        locations_to_add = [
            {
                "name": "Northern Peaks",
                "description": "Mountain range",
                "type": "terrain",
            },
            {"name": "Southern Seas", "description": "Ocean waters", "type": "terrain"},
        ]

        for location in locations_to_add:
            update_data = {"locations": [location]}
            response = client.put(f"/api/worlds/{world_id}", json=update_data)

            assert response.status_code in [200, 204]

        # Retrieve world and verify locations
        response = client.get(f"/api/worlds/{world_id}")
        assert response.status_code == 200

        world_data = response.json().get("data", response.json())
        locations = world_data.get("locations", [])

        # Should have at least some locations (may include initial ones)
        assert len(locations) >= len(locations_to_add)

    def test_world_rules_configuration(self, client, data_factory):
        """Test configuring world rules and constraints."""
        # Create world
        world_data = data_factory.create_world_data(name="Rules World")
        world_data["rules"] = [
            "Magic is forbidden",
            "Technology is limited to medieval level",
            "Resurrection is impossible",
        ]

        response = client.post("/api/worlds", json=world_data)

        assert response.status_code in [200, 201]

        world_id = response.json().get("data", {}).get("id") or "rules_world"

        # Retrieve and verify rules
        response = client.get(f"/api/worlds/{world_id}")
        assert response.status_code == 200

        world_data = response.json().get("data", response.json())
        rules = world_data.get("rules", [])

        assert len(rules) >= 3
        assert "Magic is forbidden" in rules

    def test_world_with_characters(self, client, data_factory, api_helper):
        """Test creating characters within a specific world context."""
        # Create world
        world_data = data_factory.create_world_data(name="Character World")
        response = client.post("/api/worlds", json=world_data)

        assert response.status_code in [200, 201]

        world_id = response.json().get("data", {}).get("id") or "character_world"

        # Create characters associated with this world
        char_data = data_factory.create_character_data(
            name="World Native", agent_id="world_native"
        )

        # Add world reference if supported
        char_data["metadata"] = {"world_id": world_id, "origin": "Character World"}

        response = client.post("/api/characters", json=char_data)
        assert response.status_code in [200, 201]

        # Verify character exists
        characters = api_helper.list_characters()
        char_ids = [c.get("agent_id") for c in characters]
        assert "world_native" in char_ids

    def test_world_state_persistence(self, client, data_factory, performance_tracker):
        """Test that world state persists across operations."""
        # Create world
        world_data = data_factory.create_world_data(name="Persistent World")
        world_data["settings"] = {
            "time_of_day": "dawn",
            "season": "spring",
            "year": 1205,
        }

        response = client.post("/api/worlds", json=world_data)

        assert response.status_code in [200, 201]

        world_id = response.json().get("data", {}).get("id") or "persistent_world"

        # Retrieve multiple times
        for i in range(3):
            start_time = time.time()
            response = client.get(f"/api/worlds/{world_id}")
            assert response.status_code == 200

            world_data = response.json().get("data", response.json())
            assert world_data.get("name") == "Persistent World"

            performance_tracker.record(
                f"world_retrieval_{i+1}", time.time() - start_time
            )

            time.sleep(0.5)  # Small delay between retrievals

        # Verify consistency
        perf_summary = performance_tracker.get_summary()
        retrieval_times = [
            m["duration"]
            for m in perf_summary["operations"]
            if "world_retrieval_" in m["operation"]
        ]

        # All retrievals should be relatively fast and consistent
        assert len(retrieval_times) == 3
        assert all(t < 2.0 for t in retrieval_times), "Retrievals should be fast"

    def test_world_deletion_and_cleanup(self, client, data_factory):
        """Test world deletion and associated cleanup."""
        # Create world
        world_data = data_factory.create_world_data(name="Delete Test World")
        response = client.post("/api/worlds", json=world_data)

        assert response.status_code in [200, 201]

        world_id = response.json().get("data", {}).get("id") or "delete_test_world"

        # Delete world
        response = client.delete(f"/api/worlds/{world_id}")

        assert response.status_code in [200, 204], "Failed to delete world"

        # Verify world no longer exists
        response = client.get(f"/api/worlds/{world_id}")
        assert response.status_code == 404, "Deleted world should not be retrievable"

    def test_multiple_worlds_coexistence(
        self, client, data_factory, performance_tracker
    ):
        """Test that multiple worlds can coexist independently."""
        # Create multiple worlds
        world_names = ["World Alpha", "World Beta", "World Gamma"]
        created_worlds = []

        start_time = time.time()
        for name in world_names:
            world_data = data_factory.create_world_data(name=name)
            response = client.post("/api/worlds", json=world_data)

            assert response.status_code in [200, 201]

            world_id = response.json().get("data", {}).get(
                "id"
            ) or name.lower().replace(" ", "_")
            created_worlds.append((name, world_id))

        creation_time = time.time() - start_time
        performance_tracker.record(
            "multiple_worlds_creation", creation_time, {"count": len(world_names)}
        )

        # Verify all worlds exist
        response = client.get("/api/worlds")

        assert response.status_code == 200

        worlds_data = response.json().get("data", {}).get("worlds", [])
        retrieved_names = [w.get("name") for w in worlds_data]

        for name in world_names:
            assert name in retrieved_names, f"World '{name}' not found in list"

        # Each world should be independently retrievable
        for name, world_id in created_worlds:
            response = client.get(f"/api/worlds/{world_id}")
            assert response.status_code == 200

            world_data = response.json().get("data", response.json())
            assert world_data.get("name") == name
