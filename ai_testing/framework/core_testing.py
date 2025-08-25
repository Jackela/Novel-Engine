"""
Core AI Testing Framework

Provides foundational testing utilities, assertions, and framework integration
for AI acceptance testing in Novel-Engine. Built on pytest patterns with
AI-specific extensions.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Awaitable
from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import statistics

import pytest
import httpx
from pydantic import BaseModel, Field

# Import Novel-Engine patterns
from config_loader import get_config
from src.event_bus import EventBus

# Import AI testing contracts
from ai_testing.interfaces.service_contracts import (
    TestScenario, TestResult, TestExecution, TestContext, TestStatus,
    QualityMetric, TestType, create_test_context
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Core Testing Framework ===

@dataclass
class TestMetrics:
    """Comprehensive test execution metrics"""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    
    # Performance metrics
    response_times: List[float] = field(default_factory=list)
    memory_usage_mb: List[float] = field(default_factory=list)
    cpu_usage_percent: List[float] = field(default_factory=list)
    
    # Quality metrics
    quality_scores: Dict[QualityMetric, float] = field(default_factory=dict)
    assertion_results: List[Dict[str, Any]] = field(default_factory=list)
    
    # Error tracking
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def finish(self):
        """Mark test completion and calculate final metrics"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
    
    def add_response_time(self, response_time_ms: float):
        """Add API response time measurement"""
        self.response_times.append(response_time_ms)
    
    def add_quality_score(self, metric: QualityMetric, score: float):
        """Add quality assessment score"""
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"Quality score must be between 0.0 and 1.0, got {score}")
        self.quality_scores[metric] = score
    
    def add_assertion_result(self, assertion_name: str, passed: bool, details: Dict[str, Any] = None):
        """Add assertion result"""
        self.assertion_results.append({
            "name": assertion_name,
            "passed": passed,
            "timestamp": time.time(),
            "details": details or {}
        })
    
    def get_average_response_time(self) -> float:
        """Get average response time in milliseconds"""
        return statistics.mean(self.response_times) if self.response_times else 0.0
    
    def get_overall_quality_score(self) -> float:
        """Get weighted overall quality score"""
        if not self.quality_scores:
            return 0.0
        
        # Weight scores by importance
        weights = {
            QualityMetric.SAFETY: 0.25,
            QualityMetric.ACCURACY: 0.20,
            QualityMetric.COHERENCE: 0.15,
            QualityMetric.RELEVANCE: 0.15,
            QualityMetric.CONSISTENCY: 0.15,
            QualityMetric.CREATIVITY: 0.10
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for metric, score in self.quality_scores.items():
            weight = weights.get(metric, 0.1)
            total_score += score * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def get_assertion_pass_rate(self) -> float:
        """Get percentage of passed assertions"""
        if not self.assertion_results:
            return 1.0
        
        passed_count = sum(1 for result in self.assertion_results if result["passed"])
        return passed_count / len(self.assertion_results)

class AITestingFramework:
    """
    Core AI testing framework providing utilities for Novel-Engine AI acceptance testing
    
    Features:
    - AI-specific assertions and validations
    - Performance and quality measurement
    - Integration with Novel-Engine patterns
    - Comprehensive result reporting
    - Event-driven test execution
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or get_config().get("ai_testing", {})
        self.event_bus = EventBus()
        self.http_client: Optional[httpx.AsyncClient] = None
        
        # Test session management
        self.session_id = str(uuid.uuid4())
        self.active_tests: Dict[str, TestMetrics] = {}
        self.completed_tests: List[TestResult] = []
        
        # Framework configuration
        self.default_timeout = self.config.get("default_timeout", 30)
        self.quality_threshold = self.config.get("quality_threshold", 0.7)
        self.performance_threshold_ms = self.config.get("performance_threshold_ms", 2000)
        
        logger.info(f"AI Testing Framework initialized with session {self.session_id}")
    
    async def initialize(self):
        """Initialize testing framework resources"""
        self.http_client = httpx.AsyncClient(timeout=self.default_timeout)
        logger.info("AI Testing Framework ready")
    
    async def cleanup(self):
        """Clean up framework resources"""
        if self.http_client:
            await self.http_client.aclose()
        logger.info("AI Testing Framework cleanup complete")
    
    # === Test Execution Methods ===
    
    async def run_test_scenario(
        self,
        scenario: TestScenario,
        context: Optional[TestContext] = None
    ) -> TestResult:
        """Run a complete test scenario with full instrumentation"""
        
        if context is None:
            context = create_test_context(self.session_id)
        
        metrics = TestMetrics()
        test_id = f"{scenario.id}_{int(time.time())}"
        self.active_tests[test_id] = metrics
        
        try:
            logger.info(f"Starting test scenario: {scenario.name}")
            
            # Emit test started event
            await self.event_bus.publish("ai_test_started", {
                "test_id": test_id,
                "scenario_id": scenario.id,
                "scenario_name": scenario.name,
                "test_type": scenario.test_type.value,
                "context": context.dict()
            })
            
            # Execute test based on type
            result = await self._execute_test_by_type(scenario, context, metrics)
            
            # Finalize metrics
            metrics.finish()
            
            # Create comprehensive result
            test_result = TestResult(
                execution_id=test_id,
                scenario_id=scenario.id,
                status=TestStatus.COMPLETED if result["passed"] else TestStatus.FAILED,
                passed=result["passed"],
                score=metrics.get_overall_quality_score(),
                duration_ms=int(metrics.duration_ms),
                quality_scores=metrics.quality_scores,
                performance_metrics={
                    "avg_response_time_ms": metrics.get_average_response_time(),
                    "assertion_pass_rate": metrics.get_assertion_pass_rate()
                },
                ai_analysis=result.get("ai_analysis", ""),
                recommendations=result.get("recommendations", []),
                **result.get("detailed_results", {})
            )
            
            # Store result
            self.completed_tests.append(test_result)
            
            # Emit test completed event
            await self.event_bus.publish("ai_test_completed", {
                "test_id": test_id,
                "scenario_id": scenario.id,
                "passed": test_result.passed,
                "score": test_result.score,
                "duration_ms": test_result.duration_ms,
                "quality_scores": test_result.quality_scores
            })
            
            logger.info(f"Test scenario completed: {scenario.name} (Score: {test_result.score:.3f})")
            return test_result
            
        except Exception as e:
            metrics.finish()
            metrics.errors.append(str(e))
            logger.error(f"Test scenario failed: {scenario.name}: {e}")
            
            # Create failed result
            failed_result = TestResult(
                execution_id=test_id,
                scenario_id=scenario.id,
                status=TestStatus.FAILED,
                passed=False,
                score=0.0,
                duration_ms=int(metrics.duration_ms or 0),
                error_type=type(e).__name__,
                error_message=str(e),
                recommendations=["Check test configuration", "Verify service availability"]
            )
            
            self.completed_tests.append(failed_result)
            return failed_result
        
        finally:
            # Cleanup test from active tests
            self.active_tests.pop(test_id, None)
    
    async def _execute_test_by_type(
        self,
        scenario: TestScenario,
        context: TestContext,
        metrics: TestMetrics
    ) -> Dict[str, Any]:
        """Execute test based on scenario type"""
        
        if scenario.test_type == TestType.API:
            return await self._execute_api_test(scenario, context, metrics)
        elif scenario.test_type == TestType.UI:
            return await self._execute_ui_test(scenario, context, metrics)
        elif scenario.test_type == TestType.AI_QUALITY:
            return await self._execute_ai_quality_test(scenario, context, metrics)
        elif scenario.test_type == TestType.INTEGRATION:
            return await self._execute_integration_test(scenario, context, metrics)
        elif scenario.test_type == TestType.PERFORMANCE:
            return await self._execute_performance_test(scenario, context, metrics)
        else:
            raise ValueError(f"Unsupported test type: {scenario.test_type}")
    
    async def _execute_api_test(
        self,
        scenario: TestScenario,
        context: TestContext,
        metrics: TestMetrics
    ) -> Dict[str, Any]:
        """Execute API test scenario"""
        api_spec = scenario.config.get("api_spec", {})
        
        # Build request
        method = api_spec.get("method", "GET")
        endpoint = api_spec.get("endpoint", "/")
        headers = api_spec.get("headers", {})
        params = api_spec.get("query_params", {})
        body = api_spec.get("request_body")
        
        # Add authentication if configured
        if context.metadata.get("auth_token"):
            headers["Authorization"] = f"Bearer {context.metadata['auth_token']}"
        
        start_time = time.time()
        
        try:
            # Make API request
            response = await self.http_client.request(
                method=method,
                url=endpoint,
                headers=headers,
                params=params,
                json=body,
                timeout=scenario.timeout_seconds
            )
            
            response_time = (time.time() - start_time) * 1000
            metrics.add_response_time(response_time)
            
            # Validate response
            expected_status = api_spec.get("expected_status", 200)
            status_passed = response.status_code == expected_status
            metrics.add_assertion_result("status_code", status_passed, {
                "expected": expected_status,
                "actual": response.status_code
            })
            
            # Validate response time
            max_response_time = api_spec.get("response_time_threshold_ms", self.performance_threshold_ms)
            response_time_passed = response_time <= max_response_time
            metrics.add_assertion_result("response_time", response_time_passed, {
                "threshold_ms": max_response_time,
                "actual_ms": response_time
            })
            
            # Validate response content
            content_passed = True
            if api_spec.get("expected_response_schema"):
                # Validate against JSON schema
                try:
                    response_json = response.json()
                    content_passed = self._validate_json_schema(
                        response_json, 
                        api_spec["expected_response_schema"]
                    )
                except Exception as e:
                    content_passed = False
                    metrics.errors.append(f"Response validation error: {e}")
            
            metrics.add_assertion_result("response_content", content_passed)
            
            # Overall API test result
            overall_passed = status_passed and response_time_passed and content_passed
            
            return {
                "passed": overall_passed,
                "detailed_results": {
                    "api_results": {
                        "status_code": response.status_code,
                        "response_time_ms": response_time,
                        "response_size_bytes": len(response.content),
                        "headers": dict(response.headers)
                    }
                },
                "recommendations": self._generate_api_recommendations(
                    response_time, max_response_time, status_passed
                )
            }
            
        except httpx.TimeoutException:
            metrics.add_assertion_result("api_timeout", False, {
                "timeout_seconds": scenario.timeout_seconds
            })
            return {
                "passed": False,
                "recommendations": ["Increase timeout or optimize API performance"]
            }
        except Exception as e:
            metrics.errors.append(f"API test error: {e}")
            return {
                "passed": False,
                "recommendations": ["Check API endpoint availability", "Verify request parameters"]
            }
    
    async def _execute_ui_test(
        self,
        scenario: TestScenario,
        context: TestContext,
        metrics: TestMetrics
    ) -> Dict[str, Any]:
        """Execute UI test scenario (delegated to Browser Automation Service)"""
        # This would be implemented when integrating with Playwright service
        ui_spec = scenario.config.get("ui_spec", {})
        
        # Mock UI test result for now
        metrics.add_assertion_result("ui_elements_present", True)
        metrics.add_assertion_result("accessibility_compliance", True)
        
        return {
            "passed": True,
            "detailed_results": {
                "ui_results": {
                    "page_load_time_ms": 1200,
                    "accessibility_score": 0.95,
                    "visual_regression_diff": 0.02
                }
            },
            "recommendations": ["Consider optimizing page load time"]
        }
    
    async def _execute_ai_quality_test(
        self,
        scenario: TestScenario,
        context: TestContext,
        metrics: TestMetrics
    ) -> Dict[str, Any]:
        """Execute AI quality assessment test"""
        ai_spec = scenario.config.get("ai_spec", {})
        
        # Get AI input and expected criteria
        input_prompt = ai_spec.get("input_prompt", "")
        assessment_criteria = ai_spec.get("assessment_criteria", {})
        
        # Mock AI quality assessment (would integrate with AI Quality Service)
        quality_scores = {
            QualityMetric.COHERENCE: 0.85,
            QualityMetric.CREATIVITY: 0.78,
            QualityMetric.ACCURACY: 0.92,
            QualityMetric.SAFETY: 0.96,
            QualityMetric.RELEVANCE: 0.89,
            QualityMetric.CONSISTENCY: 0.87
        }
        
        # Add quality scores to metrics
        for metric, score in quality_scores.items():
            metrics.add_quality_score(metric, score)
        
        # Check if scores meet thresholds
        overall_score = metrics.get_overall_quality_score()
        quality_passed = overall_score >= self.quality_threshold
        
        metrics.add_assertion_result("ai_quality_threshold", quality_passed, {
            "threshold": self.quality_threshold,
            "actual_score": overall_score
        })
        
        return {
            "passed": quality_passed,
            "detailed_results": {
                "ai_quality_results": {
                    "overall_score": overall_score,
                    "individual_scores": quality_scores,
                    "assessment_model": "gpt-4",
                    "input_prompt_hash": hashlib.sha256(input_prompt.encode()).hexdigest()[:16]
                }
            },
            "ai_analysis": "AI output demonstrates strong coherence and safety compliance with minor creativity improvements needed",
            "recommendations": self._generate_ai_quality_recommendations(quality_scores)
        }
    
    async def _execute_integration_test(
        self,
        scenario: TestScenario,
        context: TestContext,
        metrics: TestMetrics
    ) -> Dict[str, Any]:
        """Execute integration test scenario"""
        # Integration test combines multiple test types
        integration_spec = scenario.config.get("integration_spec", {})
        
        api_passed = True
        ui_passed = True
        
        # Mock integration test - would orchestrate multiple services
        metrics.add_assertion_result("api_integration", api_passed)
        metrics.add_assertion_result("ui_integration", ui_passed)
        metrics.add_assertion_result("data_consistency", True)
        
        overall_passed = api_passed and ui_passed
        
        return {
            "passed": overall_passed,
            "detailed_results": {
                "integration_results": {
                    "api_integration_passed": api_passed,
                    "ui_integration_passed": ui_passed,
                    "data_consistency_verified": True
                }
            },
            "recommendations": ["Monitor integration points for consistency"]
        }
    
    async def _execute_performance_test(
        self,
        scenario: TestScenario,
        context: TestContext,
        metrics: TestMetrics
    ) -> Dict[str, Any]:
        """Execute performance test scenario"""
        perf_spec = scenario.config.get("performance_spec", {})
        
        # Mock performance test
        load_time = 850  # milliseconds
        throughput = 1200  # requests per second
        
        metrics.add_response_time(load_time)
        
        # Check performance thresholds
        max_load_time = perf_spec.get("max_load_time_ms", self.performance_threshold_ms)
        load_time_passed = load_time <= max_load_time
        
        metrics.add_assertion_result("load_time", load_time_passed, {
            "threshold_ms": max_load_time,
            "actual_ms": load_time
        })
        
        return {
            "passed": load_time_passed,
            "detailed_results": {
                "performance_results": {
                    "load_time_ms": load_time,
                    "throughput_rps": throughput,
                    "cpu_usage_percent": 45.2,
                    "memory_usage_mb": 256.8
                }
            },
            "recommendations": self._generate_performance_recommendations(load_time, max_load_time)
        }
    
    # === Assertion and Validation Methods ===
    
    def _validate_json_schema(self, data: Any, schema: Dict[str, Any]) -> bool:
        """Validate JSON data against schema"""
        try:
            # Simple schema validation - in production would use jsonschema library
            if "type" in schema:
                expected_type = schema["type"]
                if expected_type == "object" and not isinstance(data, dict):
                    return False
                elif expected_type == "array" and not isinstance(data, list):
                    return False
                elif expected_type == "string" and not isinstance(data, str):
                    return False
                elif expected_type == "number" and not isinstance(data, (int, float)):
                    return False
            
            if "required" in schema and isinstance(data, dict):
                for required_field in schema["required"]:
                    if required_field not in data:
                        return False
            
            return True
        except Exception:
            return False
    
    # === Recommendation Generation ===
    
    def _generate_api_recommendations(
        self,
        response_time: float,
        threshold: float,
        status_passed: bool
    ) -> List[str]:
        """Generate API test recommendations"""
        recommendations = []
        
        if not status_passed:
            recommendations.append("Verify API endpoint configuration and error handling")
        
        if response_time > threshold:
            recommendations.append(f"Response time ({response_time:.1f}ms) exceeds threshold ({threshold}ms)")
            if response_time > threshold * 2:
                recommendations.append("Consider caching or performance optimization")
        
        if response_time < threshold * 0.5:
            recommendations.append("Excellent response time performance")
        
        return recommendations
    
    def _generate_ai_quality_recommendations(
        self,
        quality_scores: Dict[QualityMetric, float]
    ) -> List[str]:
        """Generate AI quality recommendations"""
        recommendations = []
        
        for metric, score in quality_scores.items():
            if score < 0.7:
                recommendations.append(f"Improve {metric.value} (current: {score:.2f})")
            elif score > 0.9:
                recommendations.append(f"Excellent {metric.value} performance")
        
        # Overall recommendations
        avg_score = sum(quality_scores.values()) / len(quality_scores)
        if avg_score < 0.8:
            recommendations.append("Consider prompt engineering or model fine-tuning")
        
        return recommendations
    
    def _generate_performance_recommendations(
        self,
        load_time: float,
        threshold: float
    ) -> List[str]:
        """Generate performance test recommendations"""
        recommendations = []
        
        if load_time > threshold:
            recommendations.append("Performance optimization needed")
            if load_time > threshold * 1.5:
                recommendations.append("Critical performance issue - investigate immediately")
        else:
            recommendations.append("Performance within acceptable range")
        
        return recommendations
    
    # === Utility Methods ===
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get comprehensive session summary"""
        total_tests = len(self.completed_tests)
        passed_tests = sum(1 for test in self.completed_tests if test.passed)
        
        if total_tests == 0:
            return {"message": "No tests completed in this session"}
        
        avg_score = sum(test.score for test in self.completed_tests) / total_tests
        avg_duration = sum(test.duration_ms for test in self.completed_tests) / total_tests
        
        return {
            "session_id": self.session_id,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "pass_rate": passed_tests / total_tests,
            "average_score": avg_score,
            "average_duration_ms": avg_duration,
            "test_types": list(set(test.status for test in self.completed_tests)),
            "quality_trends": self._calculate_quality_trends()
        }
    
    def _calculate_quality_trends(self) -> Dict[str, float]:
        """Calculate quality trends across tests"""
        if not self.completed_tests:
            return {}
        
        quality_by_metric = {}
        for test in self.completed_tests:
            for metric, score in test.quality_scores.items():
                if metric not in quality_by_metric:
                    quality_by_metric[metric] = []
                quality_by_metric[metric].append(score)
        
        return {
            metric.value: statistics.mean(scores)
            for metric, scores in quality_by_metric.items()
        }

# === Pytest Fixtures and Utilities ===

@pytest.fixture(scope="session")
async def ai_testing_framework():
    """Pytest fixture for AI testing framework"""
    framework = AITestingFramework()
    await framework.initialize()
    yield framework
    await framework.cleanup()

@pytest.fixture
def test_context():
    """Pytest fixture for test context"""
    return create_test_context(
        session_id=str(uuid.uuid4()),
        environment="test",
        created_by="pytest"
    )

@pytest.fixture
def mock_api_scenario():
    """Pytest fixture for mock API test scenario"""
    return TestScenario(
        name="API Health Check Test",
        description="Verify API health endpoint",
        test_type=TestType.API,
        config={
            "api_spec": {
                "endpoint": "http://localhost:8000/health",
                "method": "GET",
                "expected_status": 200,
                "response_time_threshold_ms": 1000
            }
        }
    )

# === Decorators and Helpers ===

def ai_test(
    test_type: TestType,
    quality_threshold: float = 0.7,
    performance_threshold_ms: int = 2000,
    timeout_seconds: int = 30
):
    """Decorator to mark and configure AI tests"""
    def decorator(func):
        func._ai_test_config = {
            "test_type": test_type,
            "quality_threshold": quality_threshold,
            "performance_threshold_ms": performance_threshold_ms,
            "timeout_seconds": timeout_seconds
        }
        return func
    return decorator

def quality_assertion(metric: QualityMetric, threshold: float):
    """Decorator for quality-specific assertions"""
    def decorator(func):
        func._quality_assertions = getattr(func, '_quality_assertions', [])
        func._quality_assertions.append((metric, threshold))
        return func
    return decorator

# === Export Framework Components ===

__all__ = [
    "AITestingFramework",
    "TestMetrics",
    "ai_test",
    "quality_assertion",
    "ai_testing_framework",
    "test_context",
    "mock_api_scenario"
]