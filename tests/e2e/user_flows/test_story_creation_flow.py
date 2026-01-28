#!/usr/bin/env python3
"""
E2E Test: Complete Story Creation Workflow
==========================================

Tests the end-to-end flow of creating a complete story in the Novel Engine:
1. Create a new world/setting
2. Add 2-3 characters to the world
3. Start orchestration/narrative generation
4. Wait for generation to complete
5. Verify story output and quality

Coverage:
- World creation API
- Character creation API
- Story generation orchestration
- Real-time progress monitoring
- Story output validation
"""

import time

import pytest


@pytest.mark.e2e
class TestStoryCreationFlow:
    """E2E tests for complete story creation workflow."""

    @pytest.fixture(autouse=True)
    def _require_story_generation_api(self, client):
        response = client.get("/api/stories/generate")
        if response.status_code == 404:
            pytest.skip("Story generation API removed in M2 purge.")

    def test_complete_story_creation_flow(
        self, client, data_factory, api_helper, performance_tracker
    ):
        """
        Test complete story creation from world setup to narrative output.

        Flow:
        1. Verify API health
        2. Create 2 characters
        3. Start story generation with those characters
        4. Monitor generation progress
        5. Verify completed story output
        """
        # Step 1: Verify API is healthy
        start_time = time.time()
        assert api_helper.wait_for_health(timeout=30), "API failed to become healthy"
        performance_tracker.record("api_health_check", time.time() - start_time)

        # Step 2: Create first character
        start_time = time.time()
        character1_data = data_factory.create_character_data(
            name="Aria Stormwind", agent_id="aria_stormwind"
        )
        character1_data["background_summary"] = "A skilled warrior seeking redemption"
        character1_data["personality_traits"] = "brave, determined, honorable"

        response = client.post("/api/characters", json=character1_data)
        assert response.status_code in [
            200,
            201,
        ], f"Failed to create character: {response.text}"
        performance_tracker.record("create_character_1", time.time() - start_time)

        # Step 3: Create second character
        start_time = time.time()
        character2_data = data_factory.create_character_data(
            name="Marcus Shadowblade", agent_id="marcus_shadowblade"
        )
        character2_data["background_summary"] = "A mysterious rogue with a hidden past"
        character2_data["personality_traits"] = "cunning, secretive, loyal"

        response = client.post("/api/characters", json=character2_data)
        assert response.status_code in [
            200,
            201,
        ], f"Failed to create character: {response.text}"
        performance_tracker.record("create_character_2", time.time() - start_time)

        # Step 4: Verify characters were created
        characters = api_helper.list_characters()
        character_ids = [c.get("agent_id") for c in characters]
        assert "aria_stormwind" in character_ids, "Character 1 not found in list"
        assert "marcus_shadowblade" in character_ids, "Character 2 not found in list"

        # Step 5: Start story generation
        start_time = time.time()
        story_request = data_factory.create_story_request(
            characters=["aria_stormwind", "marcus_shadowblade"],
            title="The Shadow and the Storm",
        )

        response = client.post("/api/stories/generate", json=story_request)
        assert response.status_code in [
            200,
            202,
        ], f"Failed to start story generation: {response.text}"

        story_response = response.json()
        # API returns generation_id directly (not wrapped in "data")
        generation_id = story_response.get("generation_id") or story_response.get(
            "data", {}
        ).get("generation_id")
        assert generation_id, "No generation_id returned"
        performance_tracker.record("start_story_generation", time.time() - start_time)

        # Step 6: Monitor story generation progress
        start_time = time.time()
        max_wait = 60  # 60 seconds timeout
        poll_interval = 2  # Poll every 2 seconds

        story_completed = False
        final_status = None

        while time.time() - start_time < max_wait:
            response = client.get(f"/api/stories/status/{generation_id}")

            if response.status_code == 200:
                status_data = response.json()
                status = status_data.get("data", {}).get("status", "")

                if status in ["completed", "failed"]:
                    final_status = status_data
                    story_completed = status == "completed"
                    break

            time.sleep(poll_interval)

        generation_duration = time.time() - start_time
        performance_tracker.record("story_generation_wait", generation_duration)

        # Step 7: Verify story was generated successfully
        assert (
            story_completed
        ), f"Story generation did not complete. Final status: {final_status}"
        assert final_status, "No final status received"

        story_data = final_status.get("data", {})
        assert story_data.get("status") == "completed", "Story status not completed"

        # Step 8: Verify story content
        story_content = story_data.get("story_content")
        if story_content:
            assert len(story_content) > 0, "Story content is empty"
            assert isinstance(story_content, str), "Story content is not a string"

        # Step 9: Verify performance metrics
        perf_summary = performance_tracker.get_summary()
        assert perf_summary["total_operations"] >= 5, "Not enough operations tracked"

        # Total flow should complete in reasonable time (< 90 seconds)
        assert (
            perf_summary["total_duration"] < 90
        ), f"Story creation flow took too long: {perf_summary['total_duration']}s"

    def test_story_creation_with_three_characters(
        self, client, data_factory, api_helper, performance_tracker
    ):
        """Test story creation with 3 characters for more complex interactions."""
        # Ensure API is ready
        assert api_helper.wait_for_health()

        # Create 3 characters
        characters_data = [
            ("Elena Brightstar", "elena_brightstar", "wise, compassionate, mentor"),
            ("Kael Ironforge", "kael_ironforge", "strong, stubborn, protective"),
            ("Lyra Moonwhisper", "lyra_moonwhisper", "mystical, enigmatic, powerful"),
        ]

        created_chars = []
        for name, agent_id, traits in characters_data:
            char_data = data_factory.create_character_data(name=name, agent_id=agent_id)
            char_data["personality_traits"] = traits

            response = client.post("/api/characters", json=char_data)
            assert response.status_code in [200, 201], f"Failed to create {name}"
            created_chars.append(agent_id)

        # Start story generation with all 3 characters
        story_request = data_factory.create_story_request(
            characters=created_chars, title="The Unlikely Alliance"
        )

        response = client.post("/api/stories/generate", json=story_request)
        assert response.status_code in [200, 202]

        # API returns generation_id directly (not wrapped in "data")
        resp_data = response.json()
        generation_id = resp_data.get("generation_id") or resp_data.get("data", {}).get(
            "generation_id"
        )
        assert generation_id

        # Wait for completion (may take longer with 3 characters)
        start_time = time.time()
        completed = False

        while time.time() - start_time < 90:  # 90 second timeout for 3 characters
            response = client.get(f"/api/stories/status/{generation_id}")

            if response.status_code == 200:
                status = response.json().get("data", {}).get("status")
                if status in ["completed", "failed"]:
                    completed = status == "completed"
                    break

            time.sleep(2)

        assert completed, "3-character story generation failed or timed out"

    def test_story_creation_invalid_characters(self, client, data_factory):
        """Test that story generation fails gracefully with invalid characters."""
        # Attempt to create story with non-existent characters
        story_request = data_factory.create_story_request(
            characters=["nonexistent_char_1", "nonexistent_char_2"],
            title="Invalid Story",
        )

        response = client.post("/api/stories/generate", json=story_request)

        # Should fail with 4xx error (either 400, 404, or 422)
        assert response.status_code in [
            400,
            404,
            422,
        ], f"Expected error for invalid characters, got {response.status_code}"

    def test_story_creation_empty_character_list(self, client, data_factory):
        """Test that story generation requires at least one character."""
        story_request = {"characters": [], "title": "Empty Story"}

        response = client.post("/api/stories/generate", json=story_request)

        # Should fail validation (400 Bad Request or 422 Unprocessable Entity)
        assert response.status_code in [
            400,
            422,
        ], f"Expected validation error for empty characters, got {response.status_code}"

    def test_concurrent_story_generation(self, client, data_factory, api_helper):
        """Test that multiple stories can be generated concurrently."""
        # Create characters for two separate stories
        chars_story1 = []
        chars_story2 = []

        for i in range(2):
            char_data = data_factory.create_character_data(
                name=f"Story1Char{i}", agent_id=f"story1_char{i}"
            )
            response = client.post("/api/characters", json=char_data)
            assert response.status_code in [200, 201]
            chars_story1.append(f"story1_char{i}")

        for i in range(2):
            char_data = data_factory.create_character_data(
                name=f"Story2Char{i}", agent_id=f"story2_char{i}"
            )
            response = client.post("/api/characters", json=char_data)
            assert response.status_code in [200, 201]
            chars_story2.append(f"story2_char{i}")

        # Start both story generations
        request1 = data_factory.create_story_request(
            characters=chars_story1, title="Story One"
        )
        request2 = data_factory.create_story_request(
            characters=chars_story2, title="Story Two"
        )

        response1 = client.post("/api/stories/generate", json=request1)
        response2 = client.post("/api/stories/generate", json=request2)

        assert response1.status_code in [200, 202]
        assert response2.status_code in [200, 202]

        # API returns generation_id directly (not wrapped in "data")
        resp1 = response1.json()
        resp2 = response2.json()
        gen_id1 = resp1.get("generation_id") or resp1.get("data", {}).get(
            "generation_id"
        )
        gen_id2 = resp2.get("generation_id") or resp2.get("data", {}).get(
            "generation_id"
        )

        assert gen_id1
        assert gen_id2
        assert gen_id1 != gen_id2, "Generation IDs should be unique"

        # Both should eventually complete (or at least be tracked)
        # Note: This test verifies concurrent tracking, not necessarily concurrent completion
        time.sleep(3)  # Give both some time to start

        response1 = client.get(f"/api/stories/status/{gen_id1}")
        response2 = client.get(f"/api/stories/status/{gen_id2}")

        assert response1.status_code == 200, "Story 1 status should be trackable"
        assert response2.status_code == 200, "Story 2 status should be trackable"
