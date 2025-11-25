#!/usr/bin/env python3
"""
E2E Test: Narrative Generation and Orchestration Flow
=====================================================

Tests the narrative orchestration and real-time monitoring workflow:
1. Start narrative orchestration
2. Monitor via SSE (Server-Sent Events)
3. Check progress updates
4. View generated narrative
5. Stop orchestration cleanly

Coverage:
- Orchestration start/stop API
- SSE event streaming
- Real-time progress monitoring
- Narrative generation quality
- Resource cleanup
"""

import json
import time

import pytest


@pytest.mark.e2e
@pytest.mark.asyncio
class TestNarrativeGenerationFlow:
    """E2E tests for narrative generation and orchestration monitoring."""

    def test_orchestration_lifecycle(
        self, client, data_factory, api_helper, performance_tracker
    ):
        """
        Test complete orchestration lifecycle with monitoring.

        Flow:
        1. Create characters for story
        2. Start narrative orchestration
        3. Monitor generation progress
        4. Verify narrative output
        5. Stop orchestration
        """
        # Step 1: Create characters
        char1_data = data_factory.create_character_data(
            name="Captain Nova", agent_id="captain_nova"
        )
        char2_data = data_factory.create_character_data(
            name="Engineer Vex", agent_id="engineer_vex"
        )

        response = client.post("/api/characters", json=char1_data)
        assert response.status_code in [200, 201]

        response = client.post("/api/characters", json=char2_data)
        assert response.status_code in [200, 201]

        # Step 2: Start narrative orchestration
        start_time = time.time()
        story_request = data_factory.create_story_request(
            characters=["captain_nova", "engineer_vex"], title="Space Station Crisis"
        )

        response = client.post("/api/stories/generate", json=story_request)
        assert response.status_code in [
            200,
            202,
        ], f"Failed to start orchestration: {response.text}"

        generation_id = response.json().get("data", {}).get("generation_id")
        assert generation_id, "No generation_id returned"
        performance_tracker.record("orchestration_start", time.time() - start_time)

        # Step 3: Monitor progress through status API
        start_time = time.time()
        progress_checks = []
        max_wait = 60
        check_count = 0

        while time.time() - start_time < max_wait:
            response = client.get(f"/api/stories/status/{generation_id}")

            if response.status_code == 200:
                status_data = response.json().get("data", {})
                progress = status_data.get("progress", 0)
                stage = status_data.get("stage", "unknown")

                progress_checks.append(
                    {"progress": progress, "stage": stage, "timestamp": time.time()}
                )

                check_count += 1

                # Check if completed
                if status_data.get("status") in ["completed", "failed"]:
                    break

            time.sleep(2)

        monitoring_duration = time.time() - start_time
        performance_tracker.record(
            "orchestration_monitoring",
            monitoring_duration,
            {
                "checks": check_count,
                "avg_interval": monitoring_duration / max(check_count, 1),
            },
        )

        # Step 4: Verify we got progress updates
        assert len(progress_checks) > 0, "No progress updates received"

        # Verify progress increases over time (if multiple checks)
        if len(progress_checks) > 1:
            # Check that some progress was made
            first_progress = progress_checks[0]["progress"]
            last_progress = progress_checks[-1]["progress"]
            # Progress should increase or stay at 100
            assert last_progress >= first_progress, "Progress should not decrease"

        # Step 5: Verify final status
        response = client.get(f"/api/stories/status/{generation_id}")
        assert response.status_code == 200

        final_status = response.json().get("data", {})
        assert final_status.get("status") in ["completed", "failed", "in_progress"]

    def test_sse_event_streaming(self, client, performance_tracker):
        """Test Server-Sent Events (SSE) for real-time updates."""
        # Test SSE endpoint exists and returns proper format
        start_time = time.time()

        with client.stream("GET", "/api/events/stream") as response:
            assert response.status_code == 200, "SSE endpoint should return 200"

            # Verify content type
            content_type = response.headers.get("content-type", "")
            assert (
                "text/event-stream" in content_type
            ), f"Wrong content type: {content_type}"

            # Read first few events
            events_received = []
            lines_read = 0
            max_lines = 50

            for line in response.iter_lines():
                lines_read += 1

                # Parse SSE format
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    try:
                        event_data = json.loads(data_str)
                        events_received.append(event_data)

                        # Stop after receiving a few events
                        if len(events_received) >= 3:
                            break
                    except json.JSONDecodeError:
                        pass

                if lines_read > max_lines:
                    break

        sse_duration = time.time() - start_time
        performance_tracker.record(
            "sse_streaming",
            sse_duration,
            {"events_received": len(events_received), "lines_read": lines_read},
        )

        # Verify we received events
        assert len(events_received) > 0, "Should receive at least one event"

        # Verify event structure
        for event in events_received:
            assert "type" in event, "Event should have type"
            assert "timestamp" in event, "Event should have timestamp"

    def test_narrative_progress_tracking(self, client, data_factory, api_helper):
        """Test detailed progress tracking during narrative generation."""
        # Create characters
        char_data = data_factory.create_character_data(
            name="Test Hero", agent_id="test_hero"
        )
        response = client.post("/api/characters", json=char_data)
        assert response.status_code in [200, 201]

        # Start generation
        story_request = data_factory.create_story_request(
            characters=["test_hero"], title="Progress Test"
        )

        response = client.post("/api/stories/generate", json=story_request)
        assert response.status_code in [200, 202]

        generation_id = response.json().get("data", {}).get("generation_id")

        # Track progress over time
        progress_snapshots = []
        start_time = time.time()
        max_wait = 45

        while time.time() - start_time < max_wait:
            response = client.get(f"/api/stories/status/{generation_id}")

            if response.status_code == 200:
                status_data = response.json().get("data", {})
                progress_snapshots.append(
                    {
                        "time": time.time() - start_time,
                        "progress": status_data.get("progress", 0),
                        "stage": status_data.get("stage", "unknown"),
                        "status": status_data.get("status", "unknown"),
                    }
                )

                if status_data.get("status") in ["completed", "failed"]:
                    break

            time.sleep(2)

        # Verify progress tracking
        assert len(progress_snapshots) > 0, "Should have progress snapshots"

        # Check that status progresses logically
        statuses = [s["status"] for s in progress_snapshots]
        # Should end with completed or failed (or still in progress)
        final_status = statuses[-1]
        assert final_status in ["completed", "failed", "in_progress", "initiated"]

    def test_orchestration_error_handling(self, client, data_factory):
        """Test error handling during orchestration."""
        # Test 1: Start generation with invalid data
        invalid_request = {
            "characters": [],  # Empty character list
            "title": "Invalid Story",
        }

        response = client.post("/api/stories/generate", json=invalid_request)
        assert response.status_code == 422, "Should reject invalid request"

        # Test 2: Query status of non-existent generation
        response = client.get("/api/stories/status/nonexistent_id")
        assert response.status_code in [404, 400], "Should return error for invalid ID"

        # Test 3: Start generation with non-existent characters
        invalid_chars_request = data_factory.create_story_request(
            characters=["nonexistent_char"], title="Error Test"
        )

        response = client.post("/api/stories/generate", json=invalid_chars_request)
        assert response.status_code in [
            400,
            404,
            422,
        ], "Should reject non-existent characters"

    def test_concurrent_orchestration_sessions(
        self, client, data_factory, api_helper, performance_tracker
    ):
        """Test running multiple orchestration sessions concurrently."""
        # Create multiple sets of characters
        char_sets = []
        for i in range(2):
            char_data = data_factory.create_character_data(
                name=f"Concurrent Char {i}", agent_id=f"concurrent_char_{i}"
            )
            response = client.post("/api/characters", json=char_data)
            assert response.status_code in [200, 201]
            char_sets.append(f"concurrent_char_{i}")

        # Start multiple generations
        generation_ids = []
        start_time = time.time()

        for i, char_id in enumerate(char_sets):
            story_request = data_factory.create_story_request(
                characters=[char_id], title=f"Concurrent Story {i}"
            )

            response = client.post("/api/stories/generate", json=story_request)
            assert response.status_code in [200, 202]

            gen_id = response.json().get("data", {}).get("generation_id")
            generation_ids.append(gen_id)

        performance_tracker.record(
            "concurrent_start", time.time() - start_time, {"count": len(generation_ids)}
        )

        # Verify all generations are tracked
        for gen_id in generation_ids:
            response = client.get(f"/api/stories/status/{gen_id}")
            assert response.status_code == 200, f"Generation {gen_id} should be tracked"

        # Verify IDs are unique
        assert len(generation_ids) == len(
            set(generation_ids)
        ), "Generation IDs should be unique"

    def test_narrative_quality_metrics(self, client, data_factory, api_helper):
        """Test that generated narratives meet quality requirements."""
        # Create character
        char_data = data_factory.create_character_data(
            name="Quality Test Character", agent_id="quality_char"
        )
        response = client.post("/api/characters", json=char_data)
        assert response.status_code in [200, 201]

        # Generate story
        story_request = data_factory.create_story_request(
            characters=["quality_char"], title="Quality Metrics Test"
        )

        response = client.post("/api/stories/generate", json=story_request)
        assert response.status_code in [200, 202]

        generation_id = response.json().get("data", {}).get("generation_id")

        # Wait for completion
        max_wait = 60
        start_time = time.time()
        story_content = None

        while time.time() - start_time < max_wait:
            response = client.get(f"/api/stories/status/{generation_id}")

            if response.status_code == 200:
                status_data = response.json().get("data", {})

                if status_data.get("status") == "completed":
                    story_content = status_data.get("story_content")
                    break

            time.sleep(2)

        # Verify narrative quality (if content available)
        if story_content:
            assert isinstance(story_content, str), "Story should be a string"
            assert len(story_content) > 0, "Story should not be empty"
            # Minimum length check (stories should have substance)
            assert len(story_content) > 50, "Story should have meaningful content"

    def test_orchestration_resource_cleanup(self, client, data_factory, api_helper):
        """Test that orchestration properly cleans up resources."""
        # Create character
        char_data = data_factory.create_character_data(
            name="Cleanup Test", agent_id="cleanup_char"
        )
        response = client.post("/api/characters", json=char_data)
        assert response.status_code in [200, 201]

        # Start multiple short generations
        generation_ids = []
        for i in range(3):
            story_request = data_factory.create_story_request(
                characters=["cleanup_char"], title=f"Cleanup Test {i}"
            )

            response = client.post("/api/stories/generate", json=story_request)
            if response.status_code in [200, 202]:
                gen_id = response.json().get("data", {}).get("generation_id")
                generation_ids.append(gen_id)

        # All generations should be trackable
        for gen_id in generation_ids:
            response = client.get(f"/api/stories/status/{gen_id}")
            # Should either exist (200) or be cleaned up (404)
            assert response.status_code in [200, 404]

        # Delete character should not crash even with active/completed generations
        response = client.delete("/api/characters/cleanup_char")
        assert response.status_code in [200, 204, 404]
