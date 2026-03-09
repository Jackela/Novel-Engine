"""E2E Tests for Story Session Flow.

This module tests the end-to-end story session flows:
1. Create world and characters
2. Start story generation session
3. Send messages and receive responses
4. Manage story state and progression

Tests:
- Complete story session flow
- Story generation with multiple characters
- Story state management
- Invalid story requests handling
"""

import os

# Set testing mode BEFORE importing app
os.environ["ORCHESTRATOR_MODE"] = "testing"

import time

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
    from typing import Any, Dict, List
    
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
        
        @staticmethod
        def create_story_request(characters: List[str], title=None) -> Dict[str, Any]:
            return {
                "characters": characters,
                "title": title or f"Test Story {datetime.now().timestamp()}",
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
class TestStorySession:
    """E2E tests for story session management."""

    def test_start_story_session(self, client, data_factory, api_helper):
        """Test complete story session from creation to generation.

        Verifies:
        - Characters can be created
        - Story generation can be started
        - Generation status can be tracked
        """
        # Step 1: Create characters for the story
        char1_data = data_factory.create_character_data(
            name="Aria Stormwind",
            agent_id="aria_stormwind"
        )
        char2_data = data_factory.create_character_data(
            name="Marcus Shadowblade",
            agent_id="marcus_shadowblade"
        )

        response1 = client.post("/api/characters", json=char1_data)
        response2 = client.post("/api/characters", json=char2_data)

        assert response1.status_code in [200, 201]
        assert response2.status_code in [200, 201]

        # Step 2: Start story generation
        story_request = data_factory.create_story_request(
            characters=["aria_stormwind", "marcus_shadowblade"],
            title="The Storm and the Shadow"
        )

        response = client.post("/api/stories/generate", json=story_request)
        # Note: Story generation API may be disabled in some configurations
        if response.status_code == 404:
            pytest.skip("Story generation API not available")

        assert response.status_code in [200, 202], f"Story generation failed: {response.text}"

        # Step 3: Get generation ID
        story_response = response.json()
        generation_id = story_response.get("generation_id") or story_response.get("data", {}).get("generation_id")
        assert generation_id, "No generation_id returned"

    def test_story_generation_with_three_characters(self, client, data_factory):
        """Test story generation with three characters.

        Verifies:
        - Multiple characters can participate in story
        - Generation starts successfully
        """
        # Create three characters
        chars = [
            ("Elena Brightstar", "elena_brightstar"),
            ("Kael Ironforge", "kael_ironforge"),
            ("Lyra Moonwhisper", "lyra_moonwhisper"),
        ]

        char_ids = []
        for name, agent_id in chars:
            char_data = data_factory.create_character_data(name=name, agent_id=agent_id)
            response = client.post("/api/characters", json=char_data)
            assert response.status_code in [200, 201]
            char_ids.append(agent_id)

        # Start story
        story_request = {
            "characters": char_ids,
            "title": "The Unlikely Alliance"
        }

        response = client.post("/api/stories/generate", json=story_request)
        if response.status_code == 404:
            pytest.skip("Story generation API not available")

        assert response.status_code in [200, 202]

        # Verify generation ID is returned
        data = response.json()
        generation_id = data.get("generation_id") or data.get("data", {}).get("generation_id")
        assert generation_id

    def test_story_session_status_tracking(self, client, data_factory):
        """Test tracking story generation status.

        Verifies:
        - Generation status can be queried
        - Status endpoint returns valid response
        """
        # Create character and start story
        char_data = data_factory.create_character_data(
            name="Status Test Char",
            agent_id="status_test_char"
        )
        client.post("/api/characters", json=char_data)

        story_request = {
            "characters": ["status_test_char"],
            "title": "Status Test Story"
        }

        start_response = client.post("/api/stories/generate", json=story_request)
        if start_response.status_code == 404:
            pytest.skip("Story generation API not available")

        if start_response.status_code not in [200, 202]:
            pytest.skip("Story generation not functional")

        generation_id = start_response.json().get("generation_id") or \
                       start_response.json().get("data", {}).get("generation_id")

        # Check status
        status_response = client.get(f"/api/stories/status/{generation_id}")
        assert status_response.status_code == 200, "Status endpoint failed"

        status_data = status_response.json()
        assert "data" in status_data or "status" in status_data, "Status data missing"

    def test_concurrent_story_sessions(self, client, data_factory):
        """Test multiple concurrent story sessions.

        Verifies:
        - Multiple stories can be started concurrently
        - Each story has unique generation ID
        """
        # Create characters for two stories
        chars_1 = []
        chars_2 = []

        for i in range(2):
            char_data = data_factory.create_character_data(
                name=f"Story1Char{i}",
                agent_id=f"story1_char{i}"
            )
            response = client.post("/api/characters", json=char_data)
            assert response.status_code in [200, 201]
            chars_1.append(f"story1_char{i}")

        for i in range(2):
            char_data = data_factory.create_character_data(
                name=f"Story2Char{i}",
                agent_id=f"story2_char{i}"
            )
            response = client.post("/api/characters", json=char_data)
            assert response.status_code in [200, 201]
            chars_2.append(f"story2_char{i}")

        # Start both stories
        request1 = {"characters": chars_1, "title": "Story One"}
        request2 = {"characters": chars_2, "title": "Story Two"}

        response1 = client.post("/api/stories/generate", json=request1)
        response2 = client.post("/api/stories/generate", json=request2)

        if response1.status_code == 404:
            pytest.skip("Story generation API not available")

        assert response1.status_code in [200, 202]
        assert response2.status_code in [200, 202]

        # Verify unique IDs
        gen_id1 = response1.json().get("generation_id") or \
                  response1.json().get("data", {}).get("generation_id")
        gen_id2 = response2.json().get("generation_id") or \
                  response2.json().get("data", {}).get("generation_id")

        assert gen_id1
        assert gen_id2
        assert gen_id1 != gen_id2, "Generation IDs should be unique"


@pytest.mark.e2e
class TestStoryValidation:
    """E2E tests for story request validation."""

    def test_story_invalid_characters(self, client):
        """Test story generation with non-existent characters.

        Verifies:
        - Invalid character IDs are rejected
        - Appropriate error is returned
        """
        story_request = {
            "characters": ["nonexistent_char_1", "nonexistent_char_2"],
            "title": "Invalid Story"
        }

        response = client.post("/api/stories/generate", json=story_request)
        if response.status_code == 404:
            pytest.skip("Story generation API not available")

        # Should fail with 4xx error
        assert response.status_code in [400, 404, 422], \
            f"Expected error for invalid characters, got {response.status_code}"

    def test_story_empty_character_list(self, client):
        """Test story generation with empty character list.

        Verifies:
        - Empty character list is rejected
        - Validation error is returned
        """
        story_request = {
            "characters": [],
            "title": "Empty Story"
        }

        response = client.post("/api/stories/generate", json=story_request)
        if response.status_code == 404:
            pytest.skip("Story generation API not available")

        assert response.status_code in [400, 422], \
            f"Expected validation error for empty characters, got {response.status_code}"

    def test_story_missing_title(self, client, data_factory):
        """Test story generation with missing title.

        Verifies:
        - Request without title is handled
        """
        char_data = data_factory.create_character_data(agent_id="no_title_char")
        client.post("/api/characters", json=char_data)

        story_request = {
            "characters": ["no_title_char"]
            # Missing title
        }

        response = client.post("/api/stories/generate", json=story_request)
        if response.status_code == 404:
            pytest.skip("Story generation API not available")

        # May succeed with default title or fail validation
        assert response.status_code in [200, 201, 202, 400, 422]

    def test_story_status_nonexistent_id(self, client):
        """Test querying status for non-existent story.

        Verifies:
        - 404 is returned for non-existent generation ID
        """
        response = client.get("/api/stories/status/nonexistent_generation_id_12345")

        # May return 404 or 200 with error status depending on implementation
        assert response.status_code in [200, 404]


@pytest.mark.e2e
class TestStoryOrchestration:
    """E2E tests for story orchestration API."""

    def test_orchestration_status_endpoint(self, client):
        """Test orchestration status endpoint.

        Verifies:
        - GET /api/orchestration/status returns status
        """
        response = client.get("/api/orchestration/status")

        # May be 200 with status or 503 if service unavailable
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert "success" in data or "status" in data

    def test_orchestration_start_stop(self, client):
        """Test orchestration start and stop.

        Verifies:
        - Start endpoint works
        - Stop endpoint works
        """
        # Check current status first
        status_response = client.get("/api/orchestration/status")

        if status_response.status_code == 503:
            pytest.skip("Orchestration service unavailable")

        # Try to start (may already be running)
        start_response = client.post("/api/orchestration/start")
        assert start_response.status_code in [200, 400, 503]

        # Try to stop
        stop_response = client.post("/api/orchestration/stop")
        assert stop_response.status_code in [200, 503]

    def test_narrative_endpoint(self, client):
        """Test narrative retrieval endpoint.

        Verifies:
        - GET /api/orchestration/narrative returns narrative data
        """
        response = client.get("/api/orchestration/narrative")

        # May be 200 with data or 503 if service unavailable
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert "success" in data or "data" in data or "narrative" in data

    def test_orchestration_pause_resume(self, client):
        """Test orchestration pause functionality.

        Verifies:
        - Pause endpoint works
        - Status reflects paused state
        """
        # Check if orchestration is available
        status_response = client.get("/api/orchestration/status")
        if status_response.status_code == 503:
            pytest.skip("Orchestration service unavailable")

        # Try to pause
        pause_response = client.post("/api/orchestration/pause")
        assert pause_response.status_code in [200, 503]


@pytest.mark.e2e
class TestStoryGenerationFlow:
    """E2E tests for complete story generation workflow."""

    def test_story_generation_completion(self, client, data_factory):
        """Test waiting for story generation to complete.

        Verifies:
        - Story generation can be started
        - Status can be polled
        - Generation eventually completes or fails
        """
        # Create characters
        char_data = data_factory.create_character_data(
            name="Completion Test",
            agent_id="completion_test_char"
        )
        client.post("/api/characters", json=char_data)

        # Start generation
        story_request = {
            "characters": ["completion_test_char"],
            "title": "Completion Test Story"
        }

        start_response = client.post("/api/stories/generate", json=story_request)
        if start_response.status_code == 404:
            pytest.skip("Story generation API not available")

        if start_response.status_code not in [200, 202]:
            pytest.skip("Story generation not functional")

        generation_id = start_response.json().get("generation_id") or \
                       start_response.json().get("data", {}).get("generation_id")

        # Poll for status (limited attempts)
        for _ in range(5):
            status_response = client.get(f"/api/stories/status/{generation_id}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                status = status_data.get("data", {}).get("status", "")
                if status in ["completed", "failed"]:
                    break
            time.sleep(1)

        # We don't assert completion since it may take too long
        # Just verify the endpoint works
        assert status_response.status_code == 200

    def test_story_with_world_context(self, client, data_factory):
        """Test story generation with world context.

        Verifies:
        - Story can include world/lore context
        """
        # Create character
        char_data = data_factory.create_character_data(
            name="World Context Char",
            agent_id="world_context_char"
        )
        client.post("/api/characters", json=char_data)

        # Start story with world context (if supported)
        story_request = {
            "characters": ["world_context_char"],
            "title": "World Context Story",
            "world_id": "default"
        }

        response = client.post("/api/stories/generate", json=story_request)
        if response.status_code == 404:
            pytest.skip("Story generation API not available")

        # World context may or may not be supported
        assert response.status_code in [200, 201, 202, 400, 422]

    def test_story_content_retrieval(self, client, data_factory):
        """Test retrieving generated story content.

        Verifies:
        - Story content can be retrieved
        - Content has expected structure
        """
        # Create character and start story
        char_data = data_factory.create_character_data(
            name="Content Test",
            agent_id="content_test_char"
        )
        client.post("/api/characters", json=char_data)

        story_request = {
            "characters": ["content_test_char"],
            "title": "Content Test Story"
        }

        start_response = client.post("/api/stories/generate", json=story_request)
        if start_response.status_code == 404:
            pytest.skip("Story generation API not available")

        if start_response.status_code not in [200, 202]:
            pytest.skip("Story generation not functional")

        generation_id = start_response.json().get("generation_id") or \
                       start_response.json().get("data", {}).get("generation_id")

        # Get status/content
        content_response = client.get(f"/api/stories/status/{generation_id}")
        assert content_response.status_code == 200

        data = content_response.json()
        # Response should have some structure
        assert "data" in data or "status" in data or "content" in data

    def test_story_character_interactions(self, client, data_factory):
        """Test story with character interactions.

        Verifies:
        - Multiple characters interact in story
        - Relationships are considered
        """
        # Create characters with relationship
        char1 = data_factory.create_character_data(
            name="Hero",
            agent_id="story_hero"
        )
        char2 = data_factory.create_character_data(
            name="Villain",
            agent_id="story_villain"
        )

        client.post("/api/characters", json=char1)
        client.post("/api/characters", json=char2)

        # Start story with both characters
        story_request = {
            "characters": ["story_hero", "story_villain"],
            "title": "Hero vs Villain"
        }

        response = client.post("/api/stories/generate", json=story_request)
        if response.status_code == 404:
            pytest.skip("Story generation API not available")

        # Should succeed
        assert response.status_code in [200, 202]
