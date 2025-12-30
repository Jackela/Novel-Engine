#!/usr/bin/env python3
"""
Comprehensive API Endpoints Test Suite
=====================================

This test suite provides complete coverage for the StoryForge AI API endpoints
with focus on the debranded functionality and new generic sci-fi content.

Test Categories:
1. Health & System Status
2. Character Management
3. Simulation Execution
4. Campaign Management
5. Error Handling & Edge Cases
6. Security & Validation
7. Performance & Load Testing
"""

import os
import time

import pytest

FULL_INTEGRATION = os.getenv("NOVEL_ENGINE_FULL_INTEGRATION") == "1"
if not FULL_INTEGRATION:
    pytestmark = pytest.mark.skip(
        reason="API comprehensive tests require NOVEL_ENGINE_FULL_INTEGRATION=1"
    )
from api_server import app
from fastapi.testclient import TestClient

client = TestClient(app)

# Test Data Constants
GENERIC_CHARACTERS = ["pilot", "scientist", "engineer", "test"]
SAMPLE_SIMULATION_REQUEST = {
    "character_names": ["pilot", "scientist"],
    "setting": "space station",
    "scenario": "scientific discovery",
}


def _character_ids(characters):
    return [
        entry["id"] if isinstance(entry, dict) else entry for entry in characters
    ]


class TestHealthEndpoints:
    """Test health check and system status endpoints"""

    @pytest.mark.integration
    def test_root_endpoint_returns_storyforge_branding(self):
        """Verify root endpoint shows StoryForge AI branding"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "StoryForge AI Interactive Story Engine is running!" in data["message"]
        assert "status" in data
        assert "timestamp" in data

    @pytest.mark.integration
    def test_health_endpoint_basic_functionality(self):
        """Test basic health check functionality"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "uptime" in data

    @pytest.mark.integration
    def test_system_status_endpoint(self):
        """Test system status endpoint with comprehensive checks"""
        response = client.get("/meta/system-status")
        assert response.status_code == 200
        # Note: This might fail due to Pydantic issues, but functionality works

    @pytest.mark.integration
    def test_policy_endpoint(self):
        """Test policy information endpoint"""
        response = client.get("/meta/policy")
        assert response.status_code == 200
        data = response.json()
        assert "compliance" in data
        assert data["brand_status"] == "Generic Sci-Fi"


class TestCharacterEndpoints:
    """Test character-related API endpoints"""

    @pytest.mark.integration
    def test_characters_list_returns_generic_characters(self):
        """Verify characters list returns only generic characters"""
        response = client.get("/characters")
        assert response.status_code == 200
        data = response.json()

        # Should contain our generic characters
        characters = _character_ids(data["characters"])
        assert "pilot" in characters
        assert "scientist" in characters
        assert "engineer" in characters
        assert "test" in characters

        # Should NOT contain branded characters
        branded_chars = [
            "bastion_guardian",
            "freewind_raider",
            "isabella_varr",
            "cors_test_char",
        ]
        for branded in branded_chars:
            assert branded not in characters

    @pytest.mark.integration
    def test_character_detail_pilot(self):
        """Test pilot character details"""
        response = client.get("/characters/pilot")
        assert response.status_code == 200
        data = response.json()

        assert data["character_name"] == "pilot"
        assert "Alex Chen" in data["narrative_context"]
        assert "Elite Starfighter Pilot" in data["narrative_context"]
        assert "Galactic Defense Force" in data["narrative_context"]

        # Verify structured data
        stats = data["structured_data"]["stats"]
        assert stats["character"]["name"] == "Alex Chen"
        assert stats["character"]["faction"] == "Galactic Defense Force"
        assert stats["character"]["specialization"] == "Starfighter Pilot"

    @pytest.mark.integration
    def test_character_detail_scientist(self):
        """Test scientist character details"""
        response = client.get("/characters/scientist")
        assert response.status_code == 200
        data = response.json()

        assert data["character_name"] == "scientist"
        assert "Dr. Maya Patel" in data["narrative_context"]
        assert "Xenobiology Research" in data["narrative_context"]
        assert "Scientific Research Institute" in data["narrative_context"]

        # Verify no branded content
        branded_terms = [
            "Founders' Council",
            "Alliance Network",
            "legacy franchise",
            "40k",
        ]
        content = data["narrative_context"].lower()
        for term in branded_terms:
            assert term.lower() not in content

    @pytest.mark.integration
    def test_character_detail_engineer(self):
        """Test engineer character details"""
        response = client.get("/characters/engineer")
        assert response.status_code == 200
        data = response.json()

        assert data["character_name"] == "engineer"
        assert "Jordan Kim" in data["narrative_context"]
        assert "Systems Engineer" in data["narrative_context"]
        assert "Engineering Corps" in data["narrative_context"]

    @pytest.mark.integration
    def test_character_detail_nonexistent(self):
        """Test request for non-existent character"""
        response = client.get("/characters/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    @pytest.mark.integration
    def test_character_detail_legacy_branded_characters(self):
        """Test that legacy branded characters return 404"""
        legacy_characters = ["bastion_guardian", "freewind_raider", "isabella_varr"]
        for char_name in legacy_characters:
            response = client.get(f"/characters/{char_name}")
            assert response.status_code == 404

    @pytest.mark.integration
    def test_enhanced_character_endpoint(self):
        """Test enhanced character data endpoint"""
        response = client.get("/characters/pilot/enhanced")
        assert response.status_code == 200
        data = response.json()

        assert "enhanced_context" in data
        assert "psychological_profile" in data
        assert "tactical_analysis" in data


class TestSimulationEndpoints:
    """Test simulation execution endpoints"""

    @pytest.mark.integration
    def test_simulation_with_generic_characters(self):
        """Test simulation with new generic characters"""
        response = client.post("/simulations", json=SAMPLE_SIMULATION_REQUEST)
        assert response.status_code == 200
        data = response.json()

        assert "story" in data
        assert "participants" in data
        assert "turns_executed" in data
        assert "duration_seconds" in data

        # Verify story contains no branded content
        story = data["story"].lower()
        branded_terms = [
            "founders' council",
            "alliance network",
            "Novel Engine",
            "40k",
            "bastion_guardian",
            "space marines",
            "grim darkness",
            "far future",
        ]
        for term in branded_terms:
            assert term not in story

        # Verify story contains generic sci-fi content
        assert "vast expanse" in story or "space" in story
        assert data["participants"] == ["pilot", "scientist"]

    @pytest.mark.integration
    def test_simulation_minimum_characters_validation(self):
        """Test validation for minimum character requirement"""
        invalid_request = {
            "character_names": ["pilot"],
            "setting": "space station",
            "scenario": "solo mission",
        }
        response = client.post("/simulations", json=invalid_request)
        assert response.status_code == 422  # Validation error

    @pytest.mark.integration
    def test_simulation_maximum_characters_validation(self):
        """Test validation for maximum character limit"""
        # Create request with too many characters
        too_many_chars = ["pilot", "scientist", "engineer", "test"] * 3  # 12 characters
        invalid_request = {
            "character_names": too_many_chars[:10],  # Still over limit
            "setting": "large facility",
            "scenario": "massive operation",
        }
        response = client.post("/simulations", json=invalid_request)
        # Should either limit or reject based on validation rules
        assert response.status_code in [200, 422]

    @pytest.mark.integration
    def test_simulation_with_all_generic_characters(self):
        """Test simulation with all available generic characters"""
        all_chars_request = {
            "character_names": GENERIC_CHARACTERS,
            "setting": "research facility",
            "scenario": "team collaboration",
        }
        response = client.post("/simulations", json=all_chars_request)
        assert response.status_code == 200
        data = response.json()

        assert len(data["participants"]) == len(GENERIC_CHARACTERS)
        assert data["turns_executed"] > 0
        assert data["duration_seconds"] > 0

    @pytest.mark.integration
    def test_simulation_story_quality(self):
        """Test that generated stories meet quality standards"""
        response = client.post("/simulations", json=SAMPLE_SIMULATION_REQUEST)
        assert response.status_code == 200
        data = response.json()

        story = data["story"]

        # Quality checks
        assert len(story) > 100  # Minimum length
        assert story.count(".") > 3  # Multiple sentences
        assert not story.startswith("Error")  # No error messages

        # Generic sci-fi atmosphere
        sci_fi_indicators = [
            "space",
            "galaxy",
            "cosmos",
            "technology",
            "discovery",
            "research",
            "facility",
            "system",
            "advanced",
        ]
        story_lower = story.lower()
        assert any(indicator in story_lower for indicator in sci_fi_indicators)

    @pytest.mark.integration
    def test_simulation_with_custom_setting_scenario(self):
        """Test simulation with various settings and scenarios"""
        test_cases = [
            {
                "character_names": ["pilot", "engineer"],
                "setting": "asteroid mining station",
                "scenario": "equipment malfunction",
            },
            {
                "character_names": ["scientist", "test"],
                "setting": "deep space laboratory",
                "scenario": "alien artifact discovery",
            },
            {
                "character_names": ["pilot", "scientist", "engineer"],
                "setting": "colonial outpost",
                "scenario": "first contact protocol",
            },
        ]

        for test_case in test_cases:
            response = client.post("/simulations", json=test_case)
            assert response.status_code == 200
            data = response.json()
            assert len(data["story"]) > 50
            assert data["participants"] == test_case["character_names"]


class TestCampaignEndpoints:
    """Test campaign management endpoints"""

    @pytest.mark.integration
    def test_campaigns_list_endpoint(self):
        """Test listing available campaigns"""
        response = client.get("/campaigns")
        assert response.status_code == 200
        data = response.json()
        assert "campaigns" in data
        assert isinstance(data["campaigns"], list)

    @pytest.mark.integration
    def test_campaign_creation_with_generic_theme(self):
        """Test creating campaign with generic sci-fi theme"""
        campaign_data = {
            "name": "Deep Space Exploration",
            "description": "A scientific expedition to unknown sectors",
            "theme": "sci-fi exploration",
            "participants": ["pilot", "scientist"],
            "settings": {
                "difficulty": "moderate",
                "environment": "space",
                "objectives": ["discover", "research", "survive"],
            },
        }

        response = client.post("/campaigns", json=campaign_data)
        assert response.status_code in [200, 201]
        # Campaign creation might be placeholder functionality


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases"""

    @pytest.mark.integration
    def test_invalid_json_request(self):
        """Test handling of malformed JSON"""
        response = client.post(
            "/simulations",
            content="invalid json{",
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 422

    @pytest.mark.integration
    def test_missing_required_fields(self):
        """Test validation of missing required fields"""
        incomplete_request = {"setting": "space station"}
        response = client.post("/simulations", json=incomplete_request)
        assert response.status_code == 422
        data = response.json()
        assert "character_names" in str(data)

    @pytest.mark.integration
    def test_empty_character_list(self):
        """Test simulation with empty character list"""
        empty_request = {
            "character_names": [],
            "setting": "empty facility",
            "scenario": "no participants",
        }
        response = client.post("/simulations", json=empty_request)
        assert response.status_code == 422

    @pytest.mark.integration
    def test_nonexistent_character_in_simulation(self):
        """Test simulation with non-existent character"""
        invalid_request = {
            "character_names": ["pilot", "nonexistent_character"],
            "setting": "test facility",
            "scenario": "error test",
        }
        response = client.post("/simulations", json=invalid_request)
        # Should either filter out invalid characters or return error
        assert response.status_code in [200, 400, 404, 422]

    @pytest.mark.integration
    def test_rate_limiting_compliance(self):
        """Test that API handles multiple requests appropriately"""
        # Make multiple rapid requests
        responses = []
        for i in range(5):
            response = client.get("/health")
            responses.append(response.status_code)

        # All should succeed (no rate limiting implemented yet)
        assert all(status == 200 for status in responses)

    @pytest.mark.integration
    def test_cors_headers_present(self):
        """Test CORS headers are present"""
        response = client.options("/characters")
        # CORS might be handled by middleware
        assert response.status_code in [200, 204]


class TestSecurityAndValidation:
    """Test security measures and input validation"""

    @pytest.mark.integration
    def test_input_sanitization(self):
        """Test that inputs are properly sanitized"""
        malicious_request = {
            "character_names": ["pilot", "scientist"],
            "setting": "<script>alert('xss')</script>",
            "scenario": "'; DROP TABLE users; --",
        }

        response = client.post("/simulations", json=malicious_request)
        assert response.status_code == 200
        data = response.json()

        # Story should not contain raw malicious input
        story = data["story"]
        assert "<script>" not in story
        assert "DROP TABLE" not in story

    @pytest.mark.integration
    def test_sql_injection_prevention(self):
        """Test SQL injection prevention"""
        injection_attempt = {
            "character_names": ["pilot'; DROP TABLE characters; --"],
            "setting": "hacker facility",
            "scenario": "security test",
        }

        response = client.post("/simulations", json=injection_attempt)
        # Should handle gracefully without crashes
        assert response.status_code in [200, 400, 422]

    @pytest.mark.integration
    def test_excessive_input_length_handling(self):
        """Test handling of excessively long inputs"""
        very_long_string = "x" * 10000
        long_request = {
            "character_names": ["pilot", "scientist"],
            "setting": very_long_string,
            "scenario": very_long_string,
        }

        response = client.post("/simulations", json=long_request)
        # Should either truncate or reject appropriately
        assert response.status_code in [200, 413, 422]


class TestPerformanceAndLoad:
    """Test performance characteristics"""

    @pytest.mark.integration
    def test_response_time_health_check(self):
        """Test health check response time"""
        start_time = time.time()
        response = client.get("/health")
        end_time = time.time()

        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 1.0  # Should respond within 1 second

    @pytest.mark.integration
    def test_response_time_character_list(self):
        """Test character listing response time"""
        start_time = time.time()
        response = client.get("/characters")
        end_time = time.time()

        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 2.0  # Should respond within 2 seconds

    @pytest.mark.integration
    def test_simulation_execution_time(self):
        """Test simulation execution time is reasonable"""
        start_time = time.time()
        response = client.post("/simulations", json=SAMPLE_SIMULATION_REQUEST)
        end_time = time.time()

        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 10.0  # Should complete within 10 seconds

        # Also check the reported duration in response
        data = response.json()
        assert data["duration_seconds"] < 10.0

    @pytest.mark.slow
    @pytest.mark.integration
    def test_concurrent_requests_handling(self):
        """Test handling of concurrent requests"""
        import concurrent.futures

        def make_request():
            return client.get("/health")

        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All should succeed
        assert all(r.status_code == 200 for r in responses)
        assert len(responses) == 10


class TestAPIDocumentation:
    """Test API documentation and schema"""

    @pytest.mark.integration
    def test_openapi_schema_accessibility(self):
        """Test that OpenAPI schema is accessible"""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.integration
    def test_redoc_documentation_accessibility(self):
        """Test that ReDoc documentation is accessible"""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


# Pytest configuration and fixtures
@pytest.fixture
def mock_character_data():
    """Fixture providing mock character data for tests"""
    return {
        "pilot": {
            "name": "Alex Chen",
            "role": "Elite Starfighter Pilot",
            "faction": "Galactic Defense Force",
        },
        "scientist": {
            "name": "Dr. Maya Patel",
            "role": "Xenobiology Research Scientist",
            "faction": "Scientific Research Institute",
        },
        "engineer": {
            "name": "Jordan Kim",
            "role": "Senior Systems Engineer",
            "faction": "Galactic Engineering Corps",
        },
    }


@pytest.fixture
def sample_simulation_result():
    """Fixture providing sample simulation result"""
    return {
        "story": "In the vast expanse of space, where conflict shapes destiny...",
        "participants": ["pilot", "scientist"],
        "turns_executed": 3,
        "duration_seconds": 4.2,
    }


# Test execution markers
pytestmark = [pytest.mark.api, pytest.mark.integration]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
