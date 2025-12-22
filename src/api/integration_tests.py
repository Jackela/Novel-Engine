#!/usr/bin/env python3
"""
Comprehensive Integration Testing Framework.

Provides end-to-end testing capabilities for API endpoints, WebSocket connections,
and system integration scenarios with performance and reliability validation.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import httpx
import pytest
import websockets

logger = logging.getLogger(__name__)


@dataclass
class TestScenario:
    """Test scenario configuration."""

    name: str
    description: str
    setup_func: Optional[Callable] = None
    cleanup_func: Optional[Callable] = None
    timeout_seconds: int = 30
    retry_count: int = 3


@dataclass
class PerformanceExpectation:
    """Performance expectations for tests."""

    max_response_time_ms: float = 2000
    max_memory_usage_mb: float = 500
    min_success_rate: float = 0.95
    max_error_rate: float = 0.05


@dataclass
class TestResult:
    """Test execution result."""

    scenario_name: str
    success: bool
    duration_ms: float
    response_time_ms: Optional[float] = None
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class IntegrationTestFramework:
    """Comprehensive integration testing framework."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results: List[TestResult] = []
        self.test_data: Dict[str, Any] = {}

    async def run_test_suite(self) -> Dict[str, Any]:
        """Run complete integration test suite."""

        logger.info("🚀 Starting Novel Engine API Integration Tests")
        logger.info("=" * 60)

        suite_start_time = time.time()

        # Test scenarios
        scenarios = [
            TestScenario("health_check", "System health and readiness"),
            TestScenario("api_versioning", "API versioning and compatibility"),
            TestScenario("character_crud", "Character CRUD operations"),
            TestScenario("story_generation", "Story generation workflow"),
            TestScenario("websocket_connectivity", "WebSocket connections"),
            TestScenario("error_handling", "Error response handling"),
            TestScenario("performance_baseline", "Performance baseline tests"),
            TestScenario("concurrent_requests", "Concurrent request handling"),
            TestScenario("security_validation", "Security validation tests"),
        ]

        # Execute test scenarios
        for scenario in scenarios:
            logger.info(f"\n📋 Running: {scenario.name}")
            logger.info(f"   Description: {scenario.description}")

            try:
                result = await self._execute_scenario(scenario)
                self.test_results.append(result)

                if result.success:
                    logger.info(f"   ✅ PASSED ({result.duration_ms:.1f}ms)")
                else:
                    logger.error(f"   ❌ FAILED: {result.error_message}")

            except Exception as e:
                error_result = TestResult(
                    scenario_name=scenario.name,
                    success=False,
                    duration_ms=0,
                    error_message=str(e),
                )
                self.test_results.append(error_result)
                logger.error(f"   ❌ ERROR: {str(e)}")

        # Generate test report
        suite_duration = time.time() - suite_start_time
        report = self._generate_test_report(suite_duration)

        logger.info("\n" + "=" * 60)
        logger.info("📊 Test Suite Summary")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {report['total_tests']}")
        logger.info(f"Passed: {report['passed_tests']} ✅")
        logger.error(f"Failed: {report['failed_tests']} ❌")
        logger.info(f"Success Rate: {report['success_rate']:.1f}%")
        logger.info(f"Total Duration: {suite_duration:.1f}s")

        if report["failed_tests"] > 0:
            logger.error("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result.success:
                    logger.error(f"   - {result.scenario_name}: {result.error_message}")

        return report

    async def _execute_scenario(self, scenario: TestScenario) -> TestResult:
        """Execute a single test scenario."""

        start_time = time.time()

        try:
            # Setup
            if scenario.setup_func:
                await scenario.setup_func()

            # Execute test based on scenario name
            if scenario.name == "health_check":
                result = await self._test_health_check()
            elif scenario.name == "api_versioning":
                result = await self._test_api_versioning()
            elif scenario.name == "character_crud":
                result = await self._test_character_crud()
            elif scenario.name == "story_generation":
                result = await self._test_story_generation()
            elif scenario.name == "websocket_connectivity":
                result = await self._test_websocket_connectivity()
            elif scenario.name == "error_handling":
                result = await self._test_error_handling()
            elif scenario.name == "performance_baseline":
                result = await self._test_performance_baseline()
            elif scenario.name == "concurrent_requests":
                result = await self._test_concurrent_requests()
            elif scenario.name == "security_validation":
                result = await self._test_security_validation()
            else:
                raise ValueError(f"Unknown test scenario: {scenario.name}")

            # Cleanup
            if scenario.cleanup_func:
                await scenario.cleanup_func()

            # Update result with timing
            duration_ms = (time.time() - start_time) * 1000
            result.duration_ms = duration_ms

            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return TestResult(
                scenario_name=scenario.name,
                success=False,
                duration_ms=duration_ms,
                error_message=str(e),
            )

    async def _test_health_check(self) -> TestResult:
        """Test system health check endpoints."""

        async with httpx.AsyncClient() as client:
            # Test basic health endpoint
            response = await client.get(f"{self.base_url}/health")

            if response.status_code != 200:
                return TestResult(
                    scenario_name="health_check",
                    success=False,
                    status_code=response.status_code,
                    error_message="Health check endpoint failed",
                )

            health_data = response.json()

            # Validate health response structure
            required_fields = ["status", "timestamp"]
            for field in required_fields:
                if field not in health_data:
                    return TestResult(
                        scenario_name="health_check",
                        success=False,
                        error_message=f"Missing required field: {field}",
                    )

            # Test detailed health endpoint if available
            await client.get(f"{self.base_url}/api/health/detailed")

            return TestResult(
                scenario_name="health_check",
                success=True,
                status_code=response.status_code,
                response_time_ms=response.elapsed.total_seconds() * 1000,
            )

    async def _test_api_versioning(self) -> TestResult:
        """Test API versioning and compatibility."""

        async with httpx.AsyncClient() as client:
            # Test version info endpoint
            response = await client.get(f"{self.base_url}/api/versions")

            if response.status_code != 200:
                return TestResult(
                    scenario_name="api_versioning",
                    success=False,
                    status_code=response.status_code,
                    error_message="Version info endpoint failed",
                )

            version_data = response.json()

            # Validate version response
            required_fields = ["current_version", "supported_versions"]
            for field in required_fields:
                if field not in version_data:
                    return TestResult(
                        scenario_name="api_versioning",
                        success=False,
                        error_message=f"Missing version field: {field}",
                    )

            # Test version header handling
            headers = {"X-API-Version": "1.0"}
            versioned_response = await client.get(f"{self.base_url}/", headers=headers)

            if "X-API-Version" not in versioned_response.headers:
                return TestResult(
                    scenario_name="api_versioning",
                    success=False,
                    error_message="API version header not returned",
                )

            return TestResult(
                scenario_name="api_versioning",
                success=True,
                status_code=response.status_code,
                response_time_ms=response.elapsed.total_seconds() * 1000,
            )

    async def _test_character_crud(self) -> TestResult:
        """Test character CRUD operations."""

        async with httpx.AsyncClient() as client:
            # Create character
            character_data = {
                "agent_id": f"test_character_{uuid.uuid4().hex[:8]}",
                "name": "Test Character",
                "background_summary": "A test character for integration testing",
                "personality_traits": "Reliable, consistent, testable",
                "skills": {"testing": 0.9, "reliability": 0.8},
            }

            create_response = await client.post(
                f"{self.base_url}/api/characters", json=character_data
            )

            if create_response.status_code not in [200, 201]:
                return TestResult(
                    scenario_name="character_crud",
                    success=False,
                    status_code=create_response.status_code,
                    error_message="Character creation failed",
                )

            character_id = character_data["agent_id"]
            self.test_data["test_character_id"] = character_id

            # Read character
            read_response = await client.get(
                f"{self.base_url}/api/characters/{character_id}"
            )

            if read_response.status_code != 200:
                return TestResult(
                    scenario_name="character_crud",
                    success=False,
                    status_code=read_response.status_code,
                    error_message="Character read failed",
                )

            # List characters
            list_response = await client.get(f"{self.base_url}/api/characters")

            if list_response.status_code != 200:
                return TestResult(
                    scenario_name="character_crud",
                    success=False,
                    status_code=list_response.status_code,
                    error_message="Character list failed",
                )

            # Update character
            update_data = {"name": "Updated Test Character"}
            update_response = await client.put(
                f"{self.base_url}/api/characters/{character_id}", json=update_data
            )

            if update_response.status_code != 200:
                return TestResult(
                    scenario_name="character_crud",
                    success=False,
                    status_code=update_response.status_code,
                    error_message="Character update failed",
                )

            return TestResult(
                scenario_name="character_crud",
                success=True,
                status_code=200,
                response_time_ms=create_response.elapsed.total_seconds() * 1000,
            )

    async def _test_story_generation(self) -> TestResult:
        """Test story generation workflow."""

        # Ensure we have a test character
        if "test_character_id" not in self.test_data:
            return TestResult(
                scenario_name="story_generation",
                success=False,
                error_message="No test character available for story generation",
            )

        async with httpx.AsyncClient() as client:
            # Start story generation
            story_data = {
                "characters": [self.test_data["test_character_id"]],
                "title": "Integration Test Story",
            }

            generation_response = await client.post(
                f"{self.base_url}/api/stories/generate", json=story_data
            )

            if generation_response.status_code not in [200, 202]:
                return TestResult(
                    scenario_name="story_generation",
                    success=False,
                    status_code=generation_response.status_code,
                    error_message="Story generation initiation failed",
                )

            generation_data = generation_response.json()

            # Validate response structure
            if "data" not in generation_data:
                return TestResult(
                    scenario_name="story_generation",
                    success=False,
                    error_message="Invalid story generation response format",
                )

            generation_id = generation_data["data"].get("generation_id")
            if not generation_id:
                return TestResult(
                    scenario_name="story_generation",
                    success=False,
                    error_message="Missing generation_id in response",
                )

            # Check generation status
            status_response = await client.get(
                f"{self.base_url}/api/stories/status/{generation_id}"
            )

            if status_response.status_code != 200:
                return TestResult(
                    scenario_name="story_generation",
                    success=False,
                    status_code=status_response.status_code,
                    error_message="Story status check failed",
                )

            return TestResult(
                scenario_name="story_generation",
                success=True,
                status_code=generation_response.status_code,
                response_time_ms=generation_response.elapsed.total_seconds() * 1000,
            )

    async def _test_websocket_connectivity(self) -> TestResult:
        """Test WebSocket connectivity and basic communication."""

        try:
            # Test with a mock generation ID
            test_generation_id = f"test_{uuid.uuid4().hex[:8]}"
            ws_url = f"ws://localhost:8000/api/stories/progress/{test_generation_id}"

            # Attempt WebSocket connection with timeout
            async with asyncio.timeout(5):
                async with websockets.connect(ws_url) as websocket:
                    # Send ping
                    await websocket.send("ping")

                    # Wait for pong or timeout
                    response = await websocket.recv()

                    if response != "pong":
                        return TestResult(
                            scenario_name="websocket_connectivity",
                            success=False,
                            error_message=f"Unexpected WebSocket response: {response}",
                        )

            return TestResult(
                scenario_name="websocket_connectivity",
                success=True,
                response_time_ms=50,  # Approximate WebSocket setup time
            )

        except asyncio.TimeoutError:
            return TestResult(
                scenario_name="websocket_connectivity",
                success=False,
                error_message="WebSocket connection timeout",
            )
        except Exception as e:
            return TestResult(
                scenario_name="websocket_connectivity",
                success=False,
                error_message=f"WebSocket connection failed: {str(e)}",
            )

    async def _test_error_handling(self) -> TestResult:
        """Test error handling and response formats."""

        async with httpx.AsyncClient() as client:
            # Test 404 error
            response_404 = await client.get(
                f"{self.base_url}/api/characters/nonexistent"
            )

            if response_404.status_code != 404:
                return TestResult(
                    scenario_name="error_handling",
                    success=False,
                    error_message=f"Expected 404, got {response_404.status_code}",
                )

            # Validate error response format
            error_data = response_404.json()
            if "status" not in error_data or error_data["status"] != "error":
                return TestResult(
                    scenario_name="error_handling",
                    success=False,
                    error_message="Invalid error response format",
                )

            # Test validation error
            invalid_character = {"name": ""}  # Missing required fields
            validation_response = await client.post(
                f"{self.base_url}/api/characters", json=invalid_character
            )

            if validation_response.status_code != 422:
                return TestResult(
                    scenario_name="error_handling",
                    success=False,
                    error_message=f"Expected 422 validation error, got {validation_response.status_code}",
                )

            return TestResult(
                scenario_name="error_handling",
                success=True,
                status_code=200,
                response_time_ms=response_404.elapsed.total_seconds() * 1000,
            )

    async def _test_performance_baseline(self) -> TestResult:
        """Test basic performance expectations."""

        expectations = PerformanceExpectation()

        async with httpx.AsyncClient() as client:
            # Test multiple rapid requests
            start_time = time.time()

            tasks = []
            for _ in range(10):
                task = client.get(f"{self.base_url}/health")
                tasks.append(task)

            responses = await asyncio.gather(*tasks)

            total_time = time.time() - start_time
            avg_response_time = (total_time / len(responses)) * 1000

            # Check if any requests failed
            failed_requests = [r for r in responses if r.status_code != 200]
            success_rate = (len(responses) - len(failed_requests)) / len(responses)

            if success_rate < expectations.min_success_rate:
                return TestResult(
                    scenario_name="performance_baseline",
                    success=False,
                    error_message=f"Success rate {success_rate:.2f} below threshold {expectations.min_success_rate}",
                )

            if avg_response_time > expectations.max_response_time_ms:
                return TestResult(
                    scenario_name="performance_baseline",
                    success=False,
                    error_message=f"Average response time {avg_response_time:.1f}ms exceeds {expectations.max_response_time_ms}ms",
                )

            return TestResult(
                scenario_name="performance_baseline",
                success=True,
                response_time_ms=avg_response_time,
                performance_metrics={
                    "avg_response_time_ms": avg_response_time,
                    "success_rate": success_rate,
                    "total_requests": len(responses),
                },
            )

    async def _test_concurrent_requests(self) -> TestResult:
        """Test concurrent request handling."""

        async with httpx.AsyncClient() as client:
            # Test concurrent character creation
            tasks = []

            for i in range(5):
                character_data = {
                    "agent_id": f"concurrent_test_{i}_{uuid.uuid4().hex[:8]}",
                    "name": f"Concurrent Test Character {i}",
                    "background_summary": f"Test character {i} for concurrent testing",
                }

                task = client.post(
                    f"{self.base_url}/api/characters", json=character_data
                )
                tasks.append(task)

            start_time = time.time()
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            duration = time.time() - start_time

            # Check for exceptions
            exceptions = [r for r in responses if isinstance(r, Exception)]
            if exceptions:
                return TestResult(
                    scenario_name="concurrent_requests",
                    success=False,
                    error_message=f"Concurrent requests failed with exceptions: {len(exceptions)}",
                )

            # Check response codes
            successful_responses = [
                r
                for r in responses
                if hasattr(r, "status_code") and r.status_code in [200, 201]
            ]
            success_rate = len(successful_responses) / len(responses)

            if success_rate < 0.8:  # Allow for some failures under load
                return TestResult(
                    scenario_name="concurrent_requests",
                    success=False,
                    error_message=f"Concurrent request success rate too low: {success_rate:.2f}",
                )

            return TestResult(
                scenario_name="concurrent_requests",
                success=True,
                response_time_ms=duration * 1000,
                performance_metrics={
                    "concurrent_requests": len(tasks),
                    "success_rate": success_rate,
                    "total_duration_ms": duration * 1000,
                },
            )

    async def _test_security_validation(self) -> TestResult:
        """Test basic security validations."""

        async with httpx.AsyncClient() as client:
            # Test SQL injection attempt
            malicious_id = "'; DROP TABLE characters; --"
            response = await client.get(
                f"{self.base_url}/api/characters/{malicious_id}"
            )

            # Should return 404 or 400, not 500 (which might indicate SQL injection vulnerability)
            if response.status_code == 500:
                return TestResult(
                    scenario_name="security_validation",
                    success=False,
                    error_message="Potential SQL injection vulnerability detected",
                )

            # Test oversized payload
            oversized_data = {
                "agent_id": "test_oversized",
                "name": "A" * 10000,  # Very long name
                "background_summary": "B" * 50000,  # Very long background
            }

            oversized_response = await client.post(
                f"{self.base_url}/api/characters", json=oversized_data
            )

            # Should reject oversized payload
            if oversized_response.status_code not in [400, 413, 422]:
                return TestResult(
                    scenario_name="security_validation",
                    success=False,
                    error_message="Oversized payload not properly rejected",
                )

            return TestResult(
                scenario_name="security_validation",
                success=True,
                status_code=200,
                response_time_ms=response.elapsed.total_seconds() * 1000,
            )

    def _generate_test_report(self, suite_duration: float) -> Dict[str, Any]:
        """Generate comprehensive test report."""

        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r.success])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        avg_response_time = 0
        if self.test_results:
            response_times = [
                r.response_time_ms for r in self.test_results if r.response_time_ms
            ]
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)

        return {
            "timestamp": datetime.now().isoformat(),
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": success_rate,
            "suite_duration_seconds": suite_duration,
            "average_response_time_ms": avg_response_time,
            "test_results": [
                {
                    "scenario": r.scenario_name,
                    "success": r.success,
                    "duration_ms": r.duration_ms,
                    "response_time_ms": r.response_time_ms,
                    "status_code": r.status_code,
                    "error_message": r.error_message,
                    "performance_metrics": r.performance_metrics,
                }
                for r in self.test_results
            ],
        }


# Pytest integration for running tests
@pytest.mark.asyncio
async def test_integration_suite():
    """Run the complete integration test suite."""
    framework = IntegrationTestFramework()
    report = await framework.run_test_suite()

    # Assert overall test success
    assert (
        report["failed_tests"] == 0
    ), f"Integration tests failed: {report['failed_tests']} failures"
    assert (
        report["success_rate"] >= 90
    ), f"Success rate too low: {report['success_rate']}%"


if __name__ == "__main__":
    # Run tests directly
    async def main():
        """
        Run the complete integration test suite.
        """
        framework = IntegrationTestFramework()
        await framework.run_test_suite()

    asyncio.run(main())

__all__ = [
    "TestScenario",
    "PerformanceExpectation",
    "TestResult",
    "IntegrationTestFramework",
    "test_integration_suite",
]
