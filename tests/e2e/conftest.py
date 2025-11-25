#!/usr/bin/env python3
"""
E2E Test Fixtures and Configuration
====================================

Shared fixtures for end-to-end testing of the Novel Engine API.
Provides test client setup, data factories, and cleanup utilities.
"""

import asyncio
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.api.main_api_server import create_app


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def api_app():
    """Create FastAPI application instance for testing."""
    # Set test environment variables
    os.environ["DEBUG"] = "true"
    os.environ["ENABLE_RATE_LIMITING"] = "false"
    os.environ["ENABLE_AUTH"] = "false"
    os.environ["DATABASE_PATH"] = "data/test_e2e.db"
    # Use TESTING mode for fast startup (skips background tasks and narrative engines)
    os.environ["ORCHESTRATOR_MODE"] = "testing"

    app = create_app()
    yield app

    # Cleanup test database
    db_path = Path("data/test_e2e.db")
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass


@pytest.fixture(scope="module")
def client(api_app):
    """Create synchronous test client."""
    with TestClient(api_app, raise_server_exceptions=False) as test_client:
        # Wait for API to become fully healthy before yielding client
        import time

        max_wait = 30
        start = time.time()
        last_status = None
        last_service_status = None

        while time.time() - start < max_wait:
            try:
                response = test_client.get("/health")
                last_status = response.status_code

                if response.status_code == 200:
                    data = response.json()
                    last_service_status = data.get("data", {}).get("service_status")
                    # Only accept truly healthy status
                    if last_service_status == "healthy":
                        break
            except Exception as e:
                last_status = f"exception: {e}"
            time.sleep(0.5)
        else:
            # Timeout reached - fail with clear message
            raise RuntimeError(
                f"API failed to become healthy within {max_wait}s. "
                f"Last status code: {last_status}, "
                f"Last service_status: {last_service_status}"
            )

        yield test_client


@pytest.fixture(scope="module")
async def async_client(api_app):
    """Create async test client for async operations."""
    async with AsyncClient(
        app=api_app, base_url="http://testserver", timeout=30.0
    ) as ac:
        yield ac


@pytest.fixture
def temp_artifacts_dir():
    """Create temporary directory for test artifacts (screenshots, logs, etc)."""
    artifacts_dir = Path(tempfile.mkdtemp(prefix="e2e_artifacts_"))
    yield artifacts_dir

    # Cleanup artifacts after test
    if artifacts_dir.exists():
        shutil.rmtree(artifacts_dir, ignore_errors=True)


@pytest.fixture
def capture_failure_artifacts(request, temp_artifacts_dir):
    """Capture artifacts on test failure."""
    yield

    if request.node.rep_call.failed:
        # Save failure information
        failure_log = temp_artifacts_dir / f"{request.node.name}_failure.json"
        failure_info = {
            "test_name": request.node.name,
            "timestamp": datetime.now().isoformat(),
            "failure": str(request.node.rep_call.longrepr),
        }
        failure_log.write_text(json.dumps(failure_info, indent=2))


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook to make test result available to fixtures."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


class TestDataFactory:
    """Factory for creating test data."""

    @staticmethod
    def create_character_data(
        name: Optional[str] = None,
        agent_id: Optional[str] = None,
        archetype: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create character data for testing."""
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
    def create_world_data(
        name: Optional[str] = None, description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create world data for testing."""
        world_name = name or f"TestWorld_{datetime.now().timestamp()}"

        return {
            "name": world_name,
            "description": description or f"Description for {world_name}",
            "settings": {"genre": "fantasy", "theme": "adventure", "tone": "epic"},
            "locations": [
                {
                    "name": "Starting Village",
                    "description": "A peaceful village",
                    "type": "settlement",
                }
            ],
            "rules": ["Magic exists but is rare", "Technology is medieval"],
            "metadata": {"test": True},
        }

    @staticmethod
    def create_story_request(
        characters: List[str], title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create story generation request."""
        return {
            "characters": characters,
            "title": title or f"Test Story {datetime.now().timestamp()}",
        }


@pytest.fixture
def data_factory():
    """Provide test data factory."""
    return TestDataFactory()


@pytest.fixture
async def cleanup_test_data(async_client):
    """Cleanup test data after test completion."""
    created_resources = {"characters": [], "worlds": [], "stories": []}

    yield created_resources

    # Cleanup created resources
    # Note: Implement cleanup based on actual API endpoints
    # For now, relying on test database cleanup


class APITestHelper:
    """Helper class for common API operations."""

    def __init__(self, client: TestClient):
        self.client = client

    def wait_for_health(self, timeout: int = 30) -> bool:
        """Wait for API to become healthy."""
        import time

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = self.client.get("/health")
                if response.status_code == 200:
                    data = response.json()
                    if data.get("data", {}).get("service_status") in [
                        "healthy",
                        "degraded",
                    ]:
                        return True
            except Exception:
                pass

            time.sleep(1)

        return False

    def create_character(self, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a character and return the response."""
        response = self.client.post("/api/characters", json=character_data)
        response.raise_for_status()
        return response.json()

    def get_character(self, agent_id: str) -> Dict[str, Any]:
        """Get character by ID."""
        response = self.client.get(f"/api/characters/{agent_id}")
        response.raise_for_status()
        return response.json()

    def list_characters(self) -> List[Dict[str, Any]]:
        """List all characters."""
        response = self.client.get("/api/characters")
        response.raise_for_status()
        data = response.json()
        # API returns {"characters": [...]} directly, not wrapped in data
        return data.get("characters", [])

    def delete_character(self, agent_id: str) -> bool:
        """Delete a character."""
        response = self.client.delete(f"/api/characters/{agent_id}")
        return response.status_code in [200, 204]

    def start_story_generation(self, story_request: Dict[str, Any]) -> str:
        """Start story generation and return generation_id."""
        response = self.client.post("/api/stories/generate", json=story_request)
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("generation_id")

    def get_story_status(self, generation_id: str) -> Dict[str, Any]:
        """Get story generation status."""
        response = self.client.get(f"/api/stories/status/{generation_id}")
        response.raise_for_status()
        return response.json()

    def wait_for_story_completion(
        self, generation_id: str, timeout: int = 60
    ) -> Dict[str, Any]:
        """Wait for story generation to complete."""
        import time

        start_time = time.time()

        while time.time() - start_time < timeout:
            status = self.get_story_status(generation_id)
            state = status.get("data", {}).get("status", "")

            if state in ["completed", "failed"]:
                return status

            time.sleep(2)

        raise TimeoutError(
            f"Story generation {generation_id} did not complete in {timeout}s"
        )


@pytest.fixture
def api_helper(client):
    """Provide API helper instance."""
    return APITestHelper(client)


@pytest.fixture(autouse=True)
def e2e_test_environment():
    """Setup E2E test environment."""
    # Ensure test directories exist
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    yield

    # Cleanup is handled by other fixtures


# Performance tracking
class PerformanceTracker:
    """Track performance metrics during E2E tests."""

    def __init__(self):
        self.metrics = []

    def record(self, operation: str, duration: float, metadata: Optional[Dict] = None):
        """Record a performance metric."""
        self.metrics.append(
            {
                "operation": operation,
                "duration": duration,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {},
            }
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        if not self.metrics:
            return {"total_operations": 0}

        durations = [m["duration"] for m in self.metrics]
        return {
            "total_operations": len(self.metrics),
            "total_duration": sum(durations),
            "avg_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "operations": self.metrics,
        }


@pytest.fixture
def performance_tracker():
    """Provide performance tracker."""
    return PerformanceTracker()
