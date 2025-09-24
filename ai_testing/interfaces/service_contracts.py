"""
AI Testing Framework - Service Interface Contracts

This module defines the comprehensive interface contracts for all AI testing microservices,
ensuring consistent communication patterns and data models across the testing framework.

Compatible with Novel-Engine architecture patterns and extends existing shared_types.py
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# === Core Data Models ===


class TestStatus(str, Enum):
    """Test execution status enumeration"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TestType(str, Enum):
    """Test type classification"""

    API = "api"
    UI = "ui"
    AI_QUALITY = "ai_quality"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    SECURITY = "security"
    ACCESSIBILITY = "accessibility"


class QualityMetric(str, Enum):
    """AI quality assessment metrics"""

    COHERENCE = "coherence"
    CREATIVITY = "creativity"
    ACCURACY = "accuracy"
    SAFETY = "safety"
    RELEVANCE = "relevance"
    CONSISTENCY = "consistency"


# === Base Models ===


class BaseTestModel(BaseModel):
    """Base model for all test-related entities"""

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class TestContext(BaseModel):
    """Test execution context information"""

    session_id: str
    user_id: Optional[str] = None
    environment: str = "test"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


# === Test Definition Models ===


class TestScenario(BaseTestModel):
    """Comprehensive test scenario definition"""

    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=1000)
    test_type: TestType
    priority: int = Field(default=5, ge=1, le=10)
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    retry_count: int = Field(default=3, ge=0, le=10)

    # Test configuration
    config: Dict[str, Any] = Field(default_factory=dict)
    prerequisites: List[str] = Field(default_factory=list)
    cleanup_actions: List[str] = Field(default_factory=list)

    # Validation criteria
    expected_outcomes: List[str] = Field(default_factory=list)
    quality_thresholds: Dict[QualityMetric, float] = Field(
        default_factory=dict
    )
    performance_thresholds: Dict[str, float] = Field(default_factory=dict)


class APITestSpec(BaseModel):
    """API testing specification"""

    endpoint: str = Field(..., description="API endpoint to test")
    method: str = Field(..., pattern="^(GET|POST|PUT|DELETE|PATCH)$")
    headers: Dict[str, str] = Field(default_factory=dict)
    query_params: Dict[str, str] = Field(default_factory=dict)
    request_body: Optional[Dict[str, Any]] = None

    # Expected response
    expected_status: int = Field(default=200, ge=100, le=599)
    expected_response_schema: Optional[Dict[str, Any]] = None
    response_time_threshold_ms: int = Field(default=2000, ge=1)

    # Validation rules
    response_validators: List[str] = Field(default_factory=list)
    custom_assertions: List[str] = Field(default_factory=list)


class UITestSpec(BaseModel):
    """UI testing specification for Playwright"""

    page_url: str = Field(..., description="Page URL to test")
    viewport_size: Dict[str, int] = Field(
        default={"width": 1280, "height": 720}
    )
    device_type: Optional[str] = None  # mobile, tablet, desktop
    browser: str = Field(
        default="chromium", pattern="^(chromium|firefox|webkit)$"
    )

    # Test actions
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    assertions: List[Dict[str, Any]] = Field(default_factory=list)

    # Visual testing
    screenshot_comparison: bool = Field(default=False)
    visual_threshold: float = Field(default=0.1, ge=0.0, le=1.0)

    # Performance
    performance_metrics: List[str] = Field(
        default_factory=lambda: ["FCP", "LCP", "CLS"]
    )
    accessibility_standards: List[str] = Field(
        default_factory=lambda: ["WCAG2A"]
    )


class AIQualitySpec(BaseModel):
    """AI quality assessment specification"""

    input_prompt: str = Field(..., min_length=1)
    context_data: Dict[str, Any] = Field(default_factory=dict)

    # Quality assessment configuration
    assessment_models: List[str] = Field(
        default_factory=lambda: ["gpt-4", "claude-3"]
    )
    quality_metrics: List[QualityMetric] = Field(default_factory=list)

    # Comparison data
    reference_outputs: List[str] = Field(default_factory=list)
    baseline_scores: Dict[QualityMetric, float] = Field(default_factory=dict)

    # Assessment parameters
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1, le=4000)
    assessment_criteria: Dict[str, str] = Field(default_factory=dict)


# === Test Execution Models ===


class TestExecution(BaseTestModel):
    """Test execution instance"""

    scenario_id: str
    context: TestContext
    status: TestStatus = TestStatus.PENDING

    # Execution details
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    # Resource usage
    cpu_usage_percent: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    network_io_mb: Optional[float] = None

    # Execution metadata
    executor_service: str
    execution_node: Optional[str] = None
    retry_attempt: int = 0

    # Results preview
    passed: Optional[bool] = None
    score: Optional[float] = None
    error_message: Optional[str] = None


class TestResult(BaseTestModel):
    """Comprehensive test result"""

    execution_id: str
    scenario_id: str
    status: TestStatus

    # Core results
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    duration_ms: int = Field(ge=0)

    # Detailed results
    api_results: Optional[Dict[str, Any]] = None
    ui_results: Optional[Dict[str, Any]] = None
    ai_quality_results: Optional[Dict[str, Any]] = None

    # Quality metrics
    quality_scores: Dict[QualityMetric, float] = Field(default_factory=dict)
    performance_metrics: Dict[str, float] = Field(default_factory=dict)

    # Evidence and artifacts
    screenshots: List[str] = Field(default_factory=list)
    logs: List[str] = Field(default_factory=list)
    traces: List[str] = Field(default_factory=list)
    artifacts: Dict[str, str] = Field(default_factory=dict)

    # Error details
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_stack: Optional[str] = None

    # Analysis
    ai_analysis: Optional[str] = None
    recommendations: List[str] = Field(default_factory=list)


# === Service Interface Contracts ===


class ITestOrchestrator(ABC):
    """AI Test Orchestrator Service Interface"""

    @abstractmethod
    async def create_test_plan(
        self, scenarios: List[TestScenario], context: TestContext
    ) -> str:
        """Create an intelligent test execution plan"""
        pass

    @abstractmethod
    async def execute_test_plan(self, plan_id: str) -> List[TestExecution]:
        """Execute a test plan with orchestration"""
        pass

    @abstractmethod
    async def get_execution_status(self, execution_id: str) -> TestExecution:
        """Get current execution status"""
        pass

    @abstractmethod
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running test execution"""
        pass


class IBrowserAutomation(ABC):
    """Browser Automation Service Interface"""

    @abstractmethod
    async def execute_ui_test(
        self, test_spec: UITestSpec, context: TestContext
    ) -> TestResult:
        """Execute UI test with browser automation"""
        pass

    @abstractmethod
    async def capture_screenshot(
        self, page_url: str, viewport: Dict[str, int]
    ) -> str:
        """Capture page screenshot"""
        pass

    @abstractmethod
    async def run_accessibility_audit(self, page_url: str) -> Dict[str, Any]:
        """Run accessibility compliance audit"""
        pass

    @abstractmethod
    async def measure_performance(self, page_url: str) -> Dict[str, float]:
        """Measure page performance metrics"""
        pass


class IAPITesting(ABC):
    """API Testing Service Interface"""

    @abstractmethod
    async def execute_api_test(
        self, test_spec: APITestSpec, context: TestContext
    ) -> TestResult:
        """Execute API endpoint test"""
        pass

    @abstractmethod
    async def validate_response_schema(
        self, response: Dict[str, Any], schema: Dict[str, Any]
    ) -> bool:
        """Validate API response against schema"""
        pass

    @abstractmethod
    async def run_load_test(
        self,
        test_spec: APITestSpec,
        concurrent_users: int,
        duration_seconds: int,
    ) -> Dict[str, Any]:
        """Run API load testing"""
        pass


class IAIQualityAssessment(ABC):
    """AI Quality Assessment Service Interface"""

    @abstractmethod
    async def assess_quality(
        self, test_spec: AIQualitySpec, context: TestContext
    ) -> TestResult:
        """Assess AI output quality using LLM-as-Judge"""
        pass

    @abstractmethod
    async def compare_outputs(
        self,
        current_output: str,
        reference_outputs: List[str],
        metrics: List[QualityMetric],
    ) -> Dict[QualityMetric, float]:
        """Compare AI outputs for consistency"""
        pass

    @abstractmethod
    async def generate_quality_report(
        self, results: List[TestResult]
    ) -> Dict[str, Any]:
        """Generate comprehensive quality assessment report"""
        pass


class IResultsAggregation(ABC):
    """Results Aggregation Service Interface"""

    @abstractmethod
    async def store_test_result(self, result: TestResult) -> str:
        """Store test result with indexing"""
        pass

    @abstractmethod
    async def get_test_results(
        self, filters: Dict[str, Any], limit: int = 100
    ) -> List[TestResult]:
        """Retrieve test results with filtering"""
        pass

    @abstractmethod
    async def generate_analytics(
        self, time_range: Dict[str, datetime], grouping: str = "daily"
    ) -> Dict[str, Any]:
        """Generate test analytics and trends"""
        pass

    @abstractmethod
    async def create_dashboard_data(
        self, dashboard_type: str
    ) -> Dict[str, Any]:
        """Create real-time dashboard data"""
        pass


class INotificationService(ABC):
    """Notification Service Interface"""

    @abstractmethod
    async def send_test_completion(
        self, execution_id: str, results_summary: Dict[str, Any]
    ) -> bool:
        """Send test completion notification"""
        pass

    @abstractmethod
    async def send_quality_alert(
        self, alert_type: str, details: Dict[str, Any]
    ) -> bool:
        """Send quality threshold alert"""
        pass

    @abstractmethod
    async def send_performance_alert(
        self, metric: str, threshold: float, actual_value: float
    ) -> bool:
        """Send performance threshold alert"""
        pass


# === Message/Event Models ===


class TestExecutionEvent(BaseModel):
    """Test execution event for event bus"""

    event_type: Literal["started", "completed", "failed", "cancelled"]
    execution_id: str
    scenario_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(default_factory=dict)


class QualityAssessmentEvent(BaseModel):
    """AI quality assessment event"""

    event_type: Literal[
        "assessment_completed", "threshold_breached", "pattern_detected"
    ]
    assessment_id: str
    quality_scores: Dict[QualityMetric, float]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(default_factory=dict)


class PerformanceMetricEvent(BaseModel):
    """Performance metric event"""

    event_type: Literal[
        "metric_recorded", "threshold_exceeded", "anomaly_detected"
    ]
    metric_name: str
    metric_value: float
    threshold: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(default_factory=dict)


# === Service Configuration Models ===


class ServiceConfig(BaseModel):
    """Base service configuration"""

    service_name: str
    version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int
    debug: bool = False

    # Resource limits
    max_concurrent_tests: int = 10
    timeout_seconds: int = 300
    retry_attempts: int = 3

    # Monitoring
    metrics_enabled: bool = True
    tracing_enabled: bool = True
    health_check_interval: int = 30


class DatabaseConfig(BaseModel):
    """Database connection configuration"""

    url: str
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600


class MessageQueueConfig(BaseModel):
    """Message queue configuration"""

    broker_url: str
    result_backend: str
    task_serializer: str = "json"
    accept_content: List[str] = Field(default_factory=lambda: ["json"])
    timezone: str = "UTC"


# === Response Models ===


class ServiceHealthResponse(BaseModel):
    """Service health check response"""

    service_name: str
    status: Literal["healthy", "degraded", "unhealthy"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str

    # Detailed health info
    database_status: str
    message_queue_status: str
    external_dependencies: Dict[str, str] = Field(default_factory=dict)

    # Performance metrics
    response_time_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float

    # Service-specific metrics
    active_tests: int = 0
    completed_tests_24h: int = 0
    error_rate_percent: float = 0.0


class BatchTestResponse(BaseModel):
    """Batch test execution response"""

    batch_id: str
    total_tests: int
    queued_tests: int
    estimated_completion_minutes: int
    execution_ids: List[str]

    # Progress tracking
    progress_url: str
    webhook_url: Optional[str] = None


# === Error Models ===


class TestingFrameworkError(BaseModel):
    """Standardized error response"""

    error_type: str
    error_code: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(default_factory=dict)

    # Request context
    request_id: Optional[str] = None
    service_name: Optional[str] = None

    # Troubleshooting
    suggested_actions: List[str] = Field(default_factory=list)
    documentation_url: Optional[str] = None


# === Validation Helpers ===


def validate_test_scenario(scenario: TestScenario) -> List[str]:
    """Validate test scenario configuration"""
    errors = []

    if scenario.test_type == TestType.API and not scenario.config.get(
        "api_spec"
    ):
        errors.append("API test requires api_spec in config")

    if scenario.test_type == TestType.UI and not scenario.config.get(
        "ui_spec"
    ):
        errors.append("UI test requires ui_spec in config")

    if scenario.test_type == TestType.AI_QUALITY and not scenario.config.get(
        "ai_spec"
    ):
        errors.append("AI quality test requires ai_spec in config")

    # Validate quality thresholds
    for metric, threshold in scenario.quality_thresholds.items():
        if not 0.0 <= threshold <= 1.0:
            errors.append(
                f"Quality threshold for {metric} must be between 0.0 and 1.0"
            )

    return errors


def create_test_context(
    session_id: str,
    user_id: Optional[str] = None,
    environment: str = "test",
    **metadata,
) -> TestContext:
    """Create a test context with standard metadata"""
    return TestContext(
        session_id=session_id,
        user_id=user_id,
        environment=environment,
        metadata={
            "created_by": "ai_testing_framework",
            "framework_version": "1.0.0",
            **metadata,
        },
    )


# === Export all interface contracts ===

__all__ = [
    # Enums
    "TestStatus",
    "TestType",
    "QualityMetric",
    # Base Models
    "BaseTestModel",
    "TestContext",
    # Test Definition Models
    "TestScenario",
    "APITestSpec",
    "UITestSpec",
    "AIQualitySpec",
    # Execution Models
    "TestExecution",
    "TestResult",
    # Service Interfaces
    "ITestOrchestrator",
    "IBrowserAutomation",
    "IAPITesting",
    "IAIQualityAssessment",
    "IResultsAggregation",
    "INotificationService",
    # Event Models
    "TestExecutionEvent",
    "QualityAssessmentEvent",
    "PerformanceMetricEvent",
    # Configuration Models
    "ServiceConfig",
    "DatabaseConfig",
    "MessageQueueConfig",
    # Response Models
    "ServiceHealthResponse",
    "BatchTestResponse",
    "TestingFrameworkError",
    # Utilities
    "validate_test_scenario",
    "create_test_context",
]
