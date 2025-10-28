"""
Comprehensive Integration Tests

End-to-end integration testing for the AI Testing Framework.
Validates complete system integration and orchestration.

NOTE: All tests in this module require external services to be running.
      Run services before executing these tests or use: pytest -m "not requires_services"
"""

import asyncio

import httpx
import pytest

# Mark all tests in this module as requiring services
pytestmark = pytest.mark.requires_services

# Test configuration
TEST_BASE_URL = "http://localhost:8000"
SERVICE_URLS = {
    "orchestrator": "http://localhost:8000",
    "browser-automation": "http://localhost:8001",
    "api-testing": "http://localhost:8002",
    "ai-quality": "http://localhost:8003",
    "results-aggregation": "http://localhost:8004",
    "notification": "http://localhost:8005"
}

@pytest.fixture
async def http_client():
    """HTTP client for testing"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        yield client

@pytest.fixture
async def wait_for_services():
    """Wait for all services to be ready"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        max_retries = 30
        retry_delay = 2
        
        for service_name, url in SERVICE_URLS.items():
            for attempt in range(max_retries):
                try:
                    response = await client.get(f"{url}/health")
                    if response.status_code == 200:
                        health_data = response.json()
                        if health_data.get("status") in ["healthy", "ready"]:
                            print(f"✓ {service_name} is ready")
                            break
                except Exception as e:
                    if attempt == max_retries - 1:
                        pytest.fail(f"Service {service_name} not ready after {max_retries} attempts: {e}")
                    await asyncio.sleep(retry_delay)

class TestServiceHealthChecks:
    """Test individual service health checks"""
    
    @pytest.mark.asyncio
    async def test_orchestrator_health(self, http_client, wait_for_services):
        """Test orchestrator service health"""
        response = await http_client.get(f"{SERVICE_URLS['orchestrator']}/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["service_name"] == "master-orchestrator"
        assert health_data["status"] in ["healthy", "ready", "degraded"]
        assert "version" in health_data
        assert "external_dependencies" in health_data
    
    @pytest.mark.asyncio
    async def test_all_services_health(self, http_client, wait_for_services):
        """Test all services health status"""
        response = await http_client.get(f"{SERVICE_URLS['orchestrator']}/services/health")
        assert response.status_code == 200
        
        health_results = response.json()
        
        for service_name in ["browser-automation", "api-testing", "ai-quality", "results-aggregation", "notification"]:
            assert service_name in health_results
            service_health = health_results[service_name]
            assert "status" in service_health
            # Allow for services that might be starting up
            assert service_health["status"] in ["healthy", "ready", "degraded", "starting"]

class TestAPITestingIntegration:
    """Test API testing service integration"""
    
    @pytest.mark.asyncio
    async def test_single_api_endpoint(self, http_client, wait_for_services):
        """Test single API endpoint testing"""
        test_data = {
            "endpoint_url": "https://httpbin.org/json",
            "method": "GET",
            "expected_status": 200
        }
        
        response = await http_client.post(
            f"{SERVICE_URLS['api-testing']}/test/single",
            params=test_data
        )
        assert response.status_code == 200
        
        result = response.json()
        assert "execution_id" in result
        assert "status" in result
        assert result["passed"] is True
        assert result["score"] > 0.0
    
    @pytest.mark.asyncio
    async def test_api_performance_testing(self, http_client, wait_for_services):
        """Test API performance testing"""
        test_data = {
            "endpoint_url": "https://httpbin.org/delay/1",
            "method": "GET",
            "concurrent_requests": 3,
            "duration_seconds": 10
        }
        
        response = await http_client.post(
            f"{SERVICE_URLS['api-testing']}/test/performance",
            params=test_data
        )
        assert response.status_code == 200
        
        result = response.json()
        assert "avg_response_time_ms" in result
        assert "success_rate" in result
        assert result["avg_response_time_ms"] > 0

class TestUITestingIntegration:
    """Test UI testing service integration"""
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires live website and browser setup")
    async def test_basic_ui_interaction(self, http_client, wait_for_services):
        """Test basic UI interaction"""
        test_spec = {
            "url": "https://example.com",
            "actions": [
                {
                    "type": "navigate",
                    "url": "https://example.com"
                },
                {
                    "type": "wait_for_element",
                    "selector": "h1",
                    "timeout": 5000
                }
            ],
            "assertions": [
                {
                    "type": "element_visible",
                    "selector": "h1"
                }
            ]
        }
        
        response = await http_client.post(
            f"{SERVICE_URLS['browser-automation']}/test/ui",
            json=test_spec
        )
        assert response.status_code == 200
        
        result = response.json()
        assert "execution_id" in result
        assert "status" in result

class TestAIQualityIntegration:
    """Test AI quality assessment service integration"""
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires API keys for AI services")
    async def test_ai_quality_assessment(self, http_client, wait_for_services):
        """Test AI quality assessment"""
        assessment_request = {
            "input_prompt": "Write a brief summary of climate change",
            "ai_output": "Climate change refers to long-term shifts in global temperatures and weather patterns. It is primarily caused by human activities such as burning fossil fuels.",
            "quality_dimensions": ["coherence", "accuracy", "relevance"],
            "assessment_strategy": "single_judge",
            "assessment_models": ["gpt-4"]
        }
        
        response = await http_client.post(
            f"{SERVICE_URLS['ai-quality']}/assess",
            json=assessment_request
        )
        assert response.status_code == 200
        
        result = response.json()
        assert "assessment_id" in result
        assert "overall_score" in result
        assert "quality_scores" in result

class TestComprehensiveOrchestration:
    """Test comprehensive end-to-end orchestration"""
    
    @pytest.mark.asyncio
    async def test_minimal_comprehensive_test(self, http_client, wait_for_services):
        """Test minimal comprehensive test execution"""
        test_request = {
            "test_name": "Integration Test - Minimal",
            "api_test_specs": [
                {
                    "endpoint": "https://httpbin.org/json",
                    "method": "GET",
                    "expected_status": 200,
                    "base_url": "https://httpbin.org",
                    "headers": {},
                    "query_params": {},
                    "request_body": None,
                    "auth_config": {},
                    "response_time_threshold_ms": 5000,
                    "expected_response_schema": None
                }
            ],
            "strategy": "sequential",
            "parallel_execution": False,
            "fail_fast": False,
            "quality_threshold": 0.7,
            "max_execution_time_minutes": 10
        }
        
        response = await http_client.post(
            f"{SERVICE_URLS['orchestrator']}/test/comprehensive",
            json=test_request
        )
        assert response.status_code == 200
        
        result = response.json()
        assert "test_session_id" in result
        assert "overall_status" in result
        assert "overall_score" in result
        assert "phase_results" in result
        
        # Verify at least API testing phase was executed
        phase_results = result["phase_results"]
        assert len(phase_results) > 0
        
        api_phases = [p for p in phase_results if p["phase"] == "api_testing"]
        assert len(api_phases) > 0
        
        api_phase = api_phases[0]
        assert api_phase["status"] == "COMPLETED"
        assert api_phase["passed"] is True
    
    @pytest.mark.asyncio
    async def test_comprehensive_test_status_tracking(self, http_client, wait_for_services):
        """Test comprehensive test status tracking"""
        # Start a test
        test_request = {
            "test_name": "Integration Test - Status Tracking",
            "api_test_specs": [
                {
                    "endpoint": "https://httpbin.org/delay/2",
                    "method": "GET",
                    "expected_status": 200,
                    "base_url": "https://httpbin.org",
                    "headers": {},
                    "query_params": {},
                    "request_body": None,
                    "auth_config": {},
                    "response_time_threshold_ms": 10000,
                    "expected_response_schema": None
                }
            ],
            "strategy": "sequential",
            "max_execution_time_minutes": 5
        }
        
        response = await http_client.post(
            f"{SERVICE_URLS['orchestrator']}/test/comprehensive",
            json=test_request
        )
        assert response.status_code == 200
        
        result = response.json()
        session_id = result["test_session_id"]
        
        # Check final status
        status_response = await http_client.get(
            f"{SERVICE_URLS['orchestrator']}/test/{session_id}/status"
        )
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        assert status_data["status"] == "completed"
        assert status_data["session_id"] == session_id
        
        # Get full result
        result_response = await http_client.get(
            f"{SERVICE_URLS['orchestrator']}/test/{session_id}"
        )
        assert result_response.status_code == 200
        
        full_result = result_response.json()
        assert full_result["test_session_id"] == session_id
        assert "total_duration_ms" in full_result
        assert full_result["total_duration_ms"] > 0

class TestResultsAggregation:
    """Test results aggregation and reporting"""
    
    @pytest.mark.asyncio
    async def test_health_aggregation(self, http_client, wait_for_services):
        """Test basic results aggregation service health"""
        response = await http_client.get(f"{SERVICE_URLS['results-aggregation']}/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["service_name"] == "results-aggregation"
        assert health_data["status"] in ["healthy", "ready"]

class TestNotificationIntegration:
    """Test notification service integration"""
    
    @pytest.mark.asyncio
    async def test_notification_health(self, http_client, wait_for_services):
        """Test notification service health"""
        response = await http_client.get(f"{SERVICE_URLS['notification']}/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["service_name"] == "notification"
        assert health_data["status"] in ["healthy", "ready"]

class TestSystemResilience:
    """Test system resilience and error handling"""
    
    @pytest.mark.asyncio
    async def test_invalid_api_endpoint(self, http_client, wait_for_services):
        """Test handling of invalid API endpoints"""
        test_request = {
            "test_name": "Integration Test - Invalid Endpoint",
            "api_test_specs": [
                {
                    "endpoint": "https://nonexistent-domain-12345.com/api",
                    "method": "GET",
                    "expected_status": 200,
                    "base_url": "https://nonexistent-domain-12345.com",
                    "headers": {},
                    "query_params": {},
                    "request_body": None,
                    "auth_config": {},
                    "response_time_threshold_ms": 5000,
                    "expected_response_schema": None
                }
            ],
            "strategy": "sequential",
            "fail_fast": True,
            "max_execution_time_minutes": 2
        }
        
        response = await http_client.post(
            f"{SERVICE_URLS['orchestrator']}/test/comprehensive",
            json=test_request
        )
        assert response.status_code == 200
        
        result = response.json()
        assert result["overall_passed"] is False
        assert result["overall_score"] == 0.0
        assert len(result["phase_results"]) > 0
        
        # Should have at least one failed phase
        failed_phases = [p for p in result["phase_results"] if not p["passed"]]
        assert len(failed_phases) > 0
    
    @pytest.mark.asyncio
    async def test_active_sessions_tracking(self, http_client, wait_for_services):
        """Test active sessions tracking"""
        # Check initial active sessions
        sessions_response = await http_client.get(
            f"{SERVICE_URLS['orchestrator']}/sessions/active"
        )
        assert sessions_response.status_code == 200
        
        initial_sessions = sessions_response.json()
        assert "active_sessions" in initial_sessions
        assert "count" in initial_sessions

class TestPerformanceAndScaling:
    """Test system performance and scaling characteristics"""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_test_execution(self, http_client, wait_for_services):
        """Test concurrent test execution"""
        # Create multiple test requests
        test_requests = []
        for i in range(3):
            test_request = {
                "test_name": f"Concurrent Test {i+1}",
                "api_test_specs": [
                    {
                        "endpoint": f"https://httpbin.org/delay/{i+1}",
                        "method": "GET",
                        "expected_status": 200,
                        "base_url": "https://httpbin.org",
                        "headers": {},
                        "query_params": {},
                        "request_body": None,
                        "auth_config": {},
                        "response_time_threshold_ms": 10000,
                        "expected_response_schema": None
                    }
                ],
                "strategy": "sequential",
                "max_execution_time_minutes": 5
            }
            test_requests.append(test_request)
        
        # Execute tests concurrently
        tasks = []
        for test_request in test_requests:
            task = http_client.post(
                f"{SERVICE_URLS['orchestrator']}/test/comprehensive",
                json=test_request
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        
        # Verify all tests completed successfully
        for response in responses:
            assert response.status_code == 200
            result = response.json()
            assert "test_session_id" in result
            assert result["overall_status"] in ["COMPLETED", "FAILED"]

@pytest.mark.asyncio
async def test_full_system_integration():
    """
    Comprehensive system integration test
    
    This test validates the complete AI testing framework by:
    1. Checking all services are healthy
    2. Executing a comprehensive test with multiple phases
    3. Validating results aggregation
    4. Ensuring proper cleanup
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. Verify all services are healthy
        health_response = await client.get(f"{SERVICE_URLS['orchestrator']}/services/health")
        assert health_response.status_code == 200
        
        # 2. Execute comprehensive test
        test_request = {
            "test_name": "Full System Integration Test",
            "api_test_specs": [
                {
                    "endpoint": "https://httpbin.org/get",
                    "method": "GET",
                    "expected_status": 200,
                    "base_url": "https://httpbin.org",
                    "headers": {"User-Agent": "AI-Testing-Framework/1.0"},
                    "query_params": {"test": "integration"},
                    "request_body": None,
                    "auth_config": {},
                    "response_time_threshold_ms": 5000,
                    "expected_response_schema": None
                },
                {
                    "endpoint": "https://httpbin.org/post",
                    "method": "POST",
                    "expected_status": 200,
                    "base_url": "https://httpbin.org",
                    "headers": {"Content-Type": "application/json"},
                    "query_params": {},
                    "request_body": {"message": "integration test"},
                    "auth_config": {},
                    "response_time_threshold_ms": 5000,
                    "expected_response_schema": None
                }
            ],
            "strategy": "adaptive",
            "parallel_execution": True,
            "fail_fast": False,
            "quality_threshold": 0.6,
            "test_environment": "integration",
            "max_execution_time_minutes": 10
        }
        
        test_response = await client.post(
            f"{SERVICE_URLS['orchestrator']}/test/comprehensive",
            json=test_request
        )
        assert test_response.status_code == 200
        
        result = test_response.json()
        
        # 3. Validate comprehensive results
        assert result["overall_status"] in ["COMPLETED", "FAILED"]
        assert "phase_results" in result
        assert len(result["phase_results"]) >= 2  # At least API testing and Integration phases
        assert result["total_tests_executed"] >= 2
        assert result["total_duration_ms"] > 0
        
        # 4. Verify specific phase execution
        phase_types = [phase["phase"] for phase in result["phase_results"]]
        assert "api_testing" in phase_types
        assert "integration_validation" in phase_types
        
        # 5. Check service health snapshot
        assert "service_health_snapshot" in result
        health_snapshot = result["service_health_snapshot"]
        assert len(health_snapshot) > 0
        
        print("✓ Full system integration test completed successfully")
        print(f"  - Test Session ID: {result['test_session_id']}")
        print(f"  - Overall Score: {result['overall_score']:.3f}")
        print(f"  - Total Duration: {result['total_duration_ms']}ms")
        print(f"  - Tests Executed: {result['total_tests_executed']}")
        print(f"  - Phases Completed: {len(result['phase_results'])}")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])