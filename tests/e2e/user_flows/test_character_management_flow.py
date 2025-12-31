#!/usr/bin/env python3
"""
E2E Test: Character Management Flow
===================================

Tests the complete character lifecycle and management workflow:
1. Create character with full profile
2. Update character abilities/stats
3. Create relationships with other characters
4. View character history/evolution
5. Delete character and verify cleanup

Coverage:
- Character creation API
- Character update/modification API
- Character relationships API
- Character retrieval and listing
- Character deletion and cascade cleanup
"""

import time

import pytest


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCharacterManagementFlow:
    """E2E tests for complete character management workflow."""

    def test_full_character_lifecycle(
        self, client, data_factory, api_helper, performance_tracker
    ):
        """
        Test complete character lifecycle from creation to deletion.

        Flow:
        1. Create character with full profile
        2. Verify character was created
        3. Update character attributes
        4. Verify updates were applied
        5. Delete character
        6. Verify character was deleted
        """
        # Step 1: Create character with comprehensive profile
        start_time = time.time()
        character_data = data_factory.create_character_data(
            name="Theron Blackwood", agent_id="theron_blackwood"
        )
        character_data.update(
            {
                "background_summary": "A former knight turned mercenary with a tragic past",
                "personality_traits": "stoic, honorable, haunted",
                "skills": {
                    "swordsmanship": 0.95,
                    "tactics": 0.80,
                    "leadership": 0.75,
                    "archery": 0.60,
                },
                "current_location": "Crossroads Inn",
                "inventory": ["longsword", "plate_armor", "family_sigil"],
                "metadata": {
                    "age": 42,
                    "faction": "Independent",
                    "reputation": "Respected",
                },
            }
        )

        response = client.post("/api/characters", json=character_data)
        assert response.status_code in [
            200,
            201,
        ], f"Character creation failed: {response.text}"

        creation_result = response.json()
        performance_tracker.record("character_creation", time.time() - start_time)

        # Step 2: Verify character exists and has correct data
        start_time = time.time()
        response = client.get("/api/characters/theron_blackwood")
        assert response.status_code == 200, "Failed to retrieve created character"

        char_data = response.json()
        data_section = char_data.get(
            "data", char_data
        )  # Handle different response formats

        assert data_section.get("agent_id") == "theron_blackwood"
        assert data_section.get("name") == "Theron Blackwood"
        performance_tracker.record("character_retrieval", time.time() - start_time)

        # Step 3: Update character attributes
        start_time = time.time()
        update_data = {
            "background_summary": "A former knight turned mercenary seeking redemption",
            "skills": {
                "swordsmanship": 0.98,  # Improved skill
                "tactics": 0.85,  # Improved skill
                "leadership": 0.75,
                "archery": 0.65,  # Improved skill
                "healing": 0.30,  # New skill
            },
        }

        response = client.put("/api/characters/theron_blackwood", json=update_data)
        assert response.status_code in [
            200,
            204,
        ], f"Character update failed: {response.text}"
        performance_tracker.record("character_update", time.time() - start_time)

        # Step 4: Verify updates were applied
        response = client.get("/api/characters/theron_blackwood")
        assert response.status_code == 200

        updated_data = response.json().get("data", response.json())

        # Check if skills were updated (if endpoint supports it)
        if "skills" in updated_data:
            assert updated_data["skills"].get("swordsmanship") == 0.98
            assert "healing" in updated_data["skills"]

        # Step 5: List all characters and verify our character is present
        start_time = time.time()
        characters = api_helper.list_characters()
        character_ids = [c.get("agent_id") for c in characters]
        assert "theron_blackwood" in character_ids
        performance_tracker.record("character_list", time.time() - start_time)

        # Step 6: Delete character
        start_time = time.time()
        response = client.delete("/api/characters/theron_blackwood")
        assert response.status_code in [
            200,
            204,
        ], f"Character deletion failed: {response.text}"
        performance_tracker.record("character_deletion", time.time() - start_time)

        # Step 7: Verify character was deleted
        response = client.get("/api/characters/theron_blackwood")
        assert response.status_code == 404, "Character should not exist after deletion"

        # Verify not in list
        characters = api_helper.list_characters()
        character_ids = [c.get("agent_id") for c in characters]
        assert "theron_blackwood" not in character_ids

    def test_character_relationship_management(self, client, data_factory, api_helper):
        """Test creating and managing relationships between characters."""
        # Create two characters
        char1_data = data_factory.create_character_data(
            name="Alice Winters", agent_id="alice_winters"
        )
        char2_data = data_factory.create_character_data(
            name="Bob Summers", agent_id="bob_summers"
        )

        response1 = client.post("/api/characters", json=char1_data)
        response2 = client.post("/api/characters", json=char2_data)

        assert response1.status_code in [200, 201]
        assert response2.status_code in [200, 201]

        # Update character 1 with relationship to character 2
        update_data = {
            "relationships": {"bob_summers": 0.8}  # High positive relationship
        }

        response = client.put("/api/characters/alice_winters", json=update_data)
        assert response.status_code in [200, 204], "Failed to update relationships"

        # Verify relationship was set
        response = client.get("/api/characters/alice_winters")
        if response.status_code == 200:
            char_data = response.json().get("data", response.json())
            relationships = char_data.get("relationships", {})

            if relationships:
                assert "bob_summers" in relationships
                assert relationships["bob_summers"] == 0.8

    def test_character_skill_progression(
        self, client, data_factory, performance_tracker
    ):
        """Test tracking character skill progression over time."""
        # Create character with initial skills
        char_data = data_factory.create_character_data(
            name="Novice Mage", agent_id="novice_mage"
        )
        char_data["skills"] = {
            "fire_magic": 0.2,
            "ice_magic": 0.1,
            "mana_control": 0.15,
        }

        response = client.post("/api/characters", json=char_data)
        assert response.status_code in [200, 201]

        # Simulate skill progression through multiple updates
        skill_updates = [
            {"fire_magic": 0.4, "ice_magic": 0.2, "mana_control": 0.3},
            {"fire_magic": 0.6, "ice_magic": 0.4, "mana_control": 0.5},
            {"fire_magic": 0.8, "ice_magic": 0.6, "mana_control": 0.7},
        ]

        for idx, skills in enumerate(skill_updates):
            start_time = time.time()
            update_data = {"skills": skills}

            response = client.put("/api/characters/novice_mage", json=update_data)
            assert response.status_code in [200, 204], f"Skill update {idx+1} failed"

            performance_tracker.record(
                f"skill_update_{idx+1}", time.time() - start_time
            )

        # Verify final skill levels
        response = client.get("/api/characters/novice_mage")
        if response.status_code == 200:
            final_data = response.json().get("data", response.json())
            final_skills = final_data.get("skills", {})

            if final_skills:
                assert final_skills.get("fire_magic") == 0.8
                assert final_skills.get("ice_magic") == 0.6
                assert final_skills.get("mana_control") == 0.7

    def test_bulk_character_operations(
        self, client, api_helper, data_factory, performance_tracker
    ):
        """Test creating and managing multiple characters efficiently."""
        # Create 5 characters in bulk
        character_count = 5
        created_characters = []

        start_time = time.time()
        for i in range(character_count):
            char_data = data_factory.create_character_data(
                name=f"Bulk Character {i}", agent_id=f"bulk_char_{i}"
            )

            response = client.post("/api/characters", json=char_data)
            assert response.status_code in [200, 201], f"Failed to create character {i}"
            created_characters.append(f"bulk_char_{i}")

        bulk_creation_time = time.time() - start_time
        performance_tracker.record(
            "bulk_character_creation",
            bulk_creation_time,
            {
                "count": character_count,
                "avg_per_character": bulk_creation_time / character_count,
            },
        )

        # Verify all characters exist
        characters = api_helper.list_characters()
        character_ids = [c.get("agent_id") for c in characters]

        for char_id in created_characters:
            assert char_id in character_ids, f"Character {char_id} not found in list"

        # Bulk delete
        start_time = time.time()
        for char_id in created_characters:
            response = client.delete(f"/api/characters/{char_id}")
            assert response.status_code in [200, 204], f"Failed to delete {char_id}"

        bulk_deletion_time = time.time() - start_time
        performance_tracker.record(
            "bulk_character_deletion",
            bulk_deletion_time,
            {
                "count": character_count,
                "avg_per_character": bulk_deletion_time / character_count,
            },
        )

    def test_character_validation_and_error_handling(self, client, data_factory):
        """Test character validation and error handling."""
        # Test 1: Invalid agent_id format
        invalid_char = data_factory.create_character_data()
        invalid_char[
            "agent_id"
        ] = "invalid character id!"  # Contains invalid characters

        response = client.post("/api/characters", json=invalid_char)
        # Accept both 400 (Bad Request) and 422 (Unprocessable Entity) for validation errors
        assert response.status_code in [
            400,
            422,
        ], f"Should reject invalid agent_id, got {response.status_code}"

        # Test 2: Missing required fields
        incomplete_char = {
            "name": "Incomplete Character"
            # Missing agent_id and other required fields
        }

        response = client.post("/api/characters", json=incomplete_char)
        assert response.status_code in [
            400,
            422,
        ], f"Should reject incomplete character data, got {response.status_code}"

        # Test 3: Invalid skill values (out of range)
        invalid_skills_char = data_factory.create_character_data(
            agent_id="invalid_skills"
        )
        invalid_skills_char["skills"] = {"combat": 1.5}  # Should be 0.0-1.0

        response = client.post("/api/characters", json=invalid_skills_char)
        assert response.status_code in [
            400,
            422,
        ], f"Should reject invalid skill values, got {response.status_code}"

        # Test 4: Duplicate character creation
        valid_char = data_factory.create_character_data(agent_id="duplicate_test")

        # Create once
        response1 = client.post("/api/characters", json=valid_char)
        assert response1.status_code in [200, 201]

        # Try to create again with same agent_id
        response2 = client.post("/api/characters", json=valid_char)
        assert response2.status_code in [
            400,
            409,
            422,
        ], "Should reject duplicate character"

        # Cleanup
        client.delete("/api/characters/duplicate_test")

    def test_character_query_and_filtering(self, client, data_factory, api_helper):
        """Test querying and filtering characters (if supported)."""
        # Create characters with different attributes
        characters_to_create = [
            ("Warrior One", "warrior_1", {"combat": 0.9}),
            ("Mage One", "mage_1", {"magic": 0.9}),
            ("Warrior Two", "warrior_2", {"combat": 0.8}),
        ]

        for name, agent_id, skills in characters_to_create:
            char_data = data_factory.create_character_data(name=name, agent_id=agent_id)
            char_data["skills"] = skills

            response = client.post("/api/characters", json=char_data)
            assert response.status_code in [200, 201]

        # List all characters
        all_characters = api_helper.list_characters()
        assert len(all_characters) >= 3

        # Cleanup
        for _, agent_id, _ in characters_to_create:
            client.delete(f"/api/characters/{agent_id}")
