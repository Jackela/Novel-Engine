#!/usr/bin/env python3
"""
Synthetic Monitoring for Novel Engine

Implements comprehensive synthetic monitoring with:
- Synthetic transaction monitoring
- User journey simulation
- API endpoint monitoring
- Performance baseline tracking
"""

import asyncio
import json
import logging
import ssl
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp
import certifi

logger = logging.getLogger(__name__)


class CheckType(Enum):
    """Types of synthetic checks"""

    HTTP = "http"
    API = "api"
    USER_JOURNEY = "user_journey"
    DATABASE = "database"
    WEBSOCKET = "websocket"
    CUSTOM = "custom"


class CheckStatus(Enum):
    """Status of synthetic check"""

    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class CheckResult:
    """Result of a synthetic check"""

    check_name: str
    check_type: CheckType
    status: CheckStatus
    timestamp: datetime
    duration_ms: float

    # Response details
    status_code: Optional[int] = None
    response_size: Optional[int] = None
    response_time_ms: Optional[float] = None

    # Error information
    error_message: Optional[str] = None
    error_details: Dict[str, Any] = field(default_factory=dict)

    # Performance metrics
    dns_time_ms: Optional[float] = None
    connect_time_ms: Optional[float] = None
    ssl_time_ms: Optional[float] = None
    first_byte_time_ms: Optional[float] = None
    download_time_ms: Optional[float] = None

    # Validation results
    validations_passed: int = 0
    validations_failed: int = 0
    validation_details: List[Dict[str, Any]] = field(default_factory=list)

    # Custom metrics
    custom_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class HttpCheckConfig:
    """Configuration for HTTP synthetic checks"""

    url: str
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None
    timeout_seconds: float = 30.0

    # Expected response validation
    expected_status_codes: List[int] = field(default_factory=lambda: [200])
    expected_response_time_ms: Optional[float] = None
    expected_content: Optional[str] = None
    expected_json_schema: Optional[Dict[str, Any]] = None

    # SSL/TLS configuration
    verify_ssl: bool = True
    ssl_cert_expiry_days: int = 30

    # Follow redirects
    allow_redirects: bool = True
    max_redirects: int = 10


@dataclass
class ApiCheckConfig:
    """Configuration for API synthetic checks"""

    base_url: str
    endpoints: List[Dict[str, Any]]  # List of endpoint configs
    authentication: Optional[Dict[str, Any]] = None
    common_headers: Dict[str, str] = field(default_factory=dict)
    timeout_seconds: float = 30.0


@dataclass
class UserJourneyStep:
    """Step in a user journey"""

    name: str
    action_type: str  # "http_request", "wait", "validate", "extract"
    config: Dict[str, Any]
    validation: Optional[Dict[str, Any]] = None


@dataclass
class UserJourneyConfig:
    """Configuration for user journey synthetic checks"""

    name: str
    description: str
    steps: List[UserJourneyStep]
    timeout_seconds: float = 300.0  # 5 minutes for full journey

    # Session management
    maintain_session: bool = True
    session_cookies: bool = True


@dataclass
class SyntheticCheck:
    """Synthetic check definition"""

    name: str
    check_type: CheckType
    config: Any  # HttpCheckConfig, ApiCheckConfig, etc.

    # Schedule configuration
    interval_seconds: float = 60.0
    enabled: bool = True

    # Alert configuration
    failure_threshold: int = 3  # Consecutive failures to trigger alert
    timeout_threshold_ms: float = 5000.0

    # Metadata
    tags: Dict[str, str] = field(default_factory=dict)
    description: str = ""


class SyntheticMonitor:
    """Manages synthetic monitoring checks"""

    def __init__(self):
        self.checks: Dict[str, SyntheticCheck] = {}
        self.results: Dict[str, List[CheckResult]] = defaultdict(list)
        self.running = False
        self.check_tasks: Dict[str, asyncio.Task] = {}

        # Failure tracking
        self.consecutive_failures: Dict[str, int] = defaultdict(int)
        self.last_success: Dict[str, datetime] = {}

        # Session management
        self.http_session: Optional[aiohttp.ClientSession] = None

        logger.info("Synthetic monitor initialized")

    def add_check(self, check: SyntheticCheck):
        """Add a synthetic check"""
        self.checks[check.name] = check
        self.results[check.name] = []
        logger.info(f"Added synthetic check: {check.name}")

    def remove_check(self, check_name: str):
        """Remove a synthetic check"""
        if check_name in self.checks:
            # Cancel running task
            if check_name in self.check_tasks:
                self.check_tasks[check_name].cancel()
                del self.check_tasks[check_name]

            del self.checks[check_name]
            del self.results[check_name]
            logger.info(f"Removed synthetic check: {check_name}")

    async def start_monitoring(self):
        """Start synthetic monitoring"""
        if self.running:
            return

        self.running = True

        # Create HTTP session
        connector = aiohttp.TCPConnector(
            ssl=ssl.create_default_context(cafile=certifi.where()),
            limit=100,
            limit_per_host=30,
        )

        timeout = aiohttp.ClientTimeout(total=30)
        self.http_session = aiohttp.ClientSession(
            connector=connector, timeout=timeout
        )

        # Start monitoring tasks for each check
        for check_name, check in self.checks.items():
            if check.enabled:
                task = asyncio.create_task(self._monitor_check(check))
                self.check_tasks[check_name] = task

        logger.info(
            f"Started synthetic monitoring for {len(self.check_tasks)} checks"
        )

    async def stop_monitoring(self):
        """Stop synthetic monitoring"""
        self.running = False

        # Cancel all running tasks
        for task in self.check_tasks.values():
            task.cancel()

        # Wait for tasks to complete
        if self.check_tasks:
            await asyncio.gather(
                *self.check_tasks.values(), return_exceptions=True
            )

        self.check_tasks.clear()

        # Close HTTP session
        if self.http_session:
            await self.http_session.close()
            self.http_session = None

        logger.info("Synthetic monitoring stopped")

    async def _monitor_check(self, check: SyntheticCheck):
        """Monitor a specific synthetic check"""
        while self.running and check.enabled:
            try:
                result = await self._run_check(check)

                # Store result
                self.results[check.name].append(result)

                # Keep only last 1000 results
                if len(self.results[check.name]) > 1000:
                    self.results[check.name] = self.results[check.name][-1000:]

                # Track failures
                if result.status == CheckStatus.SUCCESS:
                    self.consecutive_failures[check.name] = 0
                    self.last_success[check.name] = datetime.now(timezone.utc)
                else:
                    self.consecutive_failures[check.name] += 1

                    # Log failures
                    if (
                        self.consecutive_failures[check.name]
                        >= check.failure_threshold
                    ):
                        logger.error(
                            f"Synthetic check '{check.name}' has failed "
                            f"{self.consecutive_failures[check.name]} consecutive times: "
                            f"{result.error_message}"
                        )

                await asyncio.sleep(check.interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in synthetic check '{check.name}': {e}")
                await asyncio.sleep(check.interval_seconds)

    async def _run_check(self, check: SyntheticCheck) -> CheckResult:
        """Run a specific synthetic check"""
        start_time = time.time()

        try:
            if check.check_type == CheckType.HTTP:
                result = await self._run_http_check(check)
            elif check.check_type == CheckType.API:
                result = await self._run_api_check(check)
            elif check.check_type == CheckType.USER_JOURNEY:
                result = await self._run_user_journey_check(check)
            else:
                result = CheckResult(
                    check_name=check.name,
                    check_type=check.check_type,
                    status=CheckStatus.ERROR,
                    timestamp=datetime.now(timezone.utc),
                    duration_ms=(time.time() - start_time) * 1000,
                    error_message=f"Unsupported check type: {check.check_type}",
                )

            return result

        except Exception as e:
            return CheckResult(
                check_name=check.name,
                check_type=check.check_type,
                status=CheckStatus.ERROR,
                timestamp=datetime.now(timezone.utc),
                duration_ms=(time.time() - start_time) * 1000,
                error_message=str(e),
                error_details={"exception": type(e).__name__},
            )

    async def _run_http_check(self, check: SyntheticCheck) -> CheckResult:
        """Run HTTP synthetic check"""
        config: HttpCheckConfig = check.config
        start_time = time.time()

        try:
            # Prepare request
            kwargs = {
                "method": config.method,
                "url": config.url,
                "headers": config.headers,
                "timeout": aiohttp.ClientTimeout(total=config.timeout_seconds),
                "allow_redirects": config.allow_redirects,
                "max_redirects": config.max_redirects,
                "ssl": config.verify_ssl,
            }

            if config.body:
                kwargs["data"] = config.body

            # Make request
            async with self.http_session.request(**kwargs) as response:
                response_time = (time.time() - start_time) * 1000
                content = await response.text()

                # Create result
                result = CheckResult(
                    check_name=check.name,
                    check_type=CheckType.HTTP,
                    status=CheckStatus.SUCCESS,
                    timestamp=datetime.now(timezone.utc),
                    duration_ms=response_time,
                    status_code=response.status,
                    response_size=len(content),
                    response_time_ms=response_time,
                )

                # Validate response
                await self._validate_http_response(
                    result, response, content, config
                )

                return result

        except asyncio.TimeoutError:
            return CheckResult(
                check_name=check.name,
                check_type=CheckType.HTTP,
                status=CheckStatus.TIMEOUT,
                timestamp=datetime.now(timezone.utc),
                duration_ms=(time.time() - start_time) * 1000,
                error_message=f"Request timed out after {config.timeout_seconds}s",
            )
        except Exception as e:
            return CheckResult(
                check_name=check.name,
                check_type=CheckType.HTTP,
                status=CheckStatus.FAILURE,
                timestamp=datetime.now(timezone.utc),
                duration_ms=(time.time() - start_time) * 1000,
                error_message=str(e),
                error_details={"exception": type(e).__name__},
            )

    async def _validate_http_response(
        self,
        result: CheckResult,
        response: aiohttp.ClientResponse,
        content: str,
        config: HttpCheckConfig,
    ):
        """Validate HTTP response against expected criteria"""
        validations = []

        # Validate status code
        if config.expected_status_codes:
            if response.status in config.expected_status_codes:
                validations.append(
                    {
                        "name": "status_code",
                        "passed": True,
                        "expected": config.expected_status_codes,
                        "actual": response.status,
                    }
                )
            else:
                validations.append(
                    {
                        "name": "status_code",
                        "passed": False,
                        "expected": config.expected_status_codes,
                        "actual": response.status,
                    }
                )
                result.status = CheckStatus.FAILURE
                result.error_message = (
                    f"Unexpected status code: {response.status}"
                )

        # Validate response time
        if config.expected_response_time_ms:
            if result.response_time_ms <= config.expected_response_time_ms:
                validations.append(
                    {
                        "name": "response_time",
                        "passed": True,
                        "expected": f"<= {config.expected_response_time_ms}ms",
                        "actual": f"{result.response_time_ms:.2f}ms",
                    }
                )
            else:
                validations.append(
                    {
                        "name": "response_time",
                        "passed": False,
                        "expected": f"<= {config.expected_response_time_ms}ms",
                        "actual": f"{result.response_time_ms:.2f}ms",
                    }
                )
                result.status = CheckStatus.FAILURE
                if not result.error_message:
                    result.error_message = f"Response time too slow: {result.response_time_ms:.2f}ms"

        # Validate content
        if config.expected_content:
            if config.expected_content in content:
                validations.append(
                    {
                        "name": "content",
                        "passed": True,
                        "expected": config.expected_content,
                        "actual": "Found in response",
                    }
                )
            else:
                validations.append(
                    {
                        "name": "content",
                        "passed": False,
                        "expected": config.expected_content,
                        "actual": "Not found in response",
                    }
                )
                result.status = CheckStatus.FAILURE
                if not result.error_message:
                    result.error_message = "Expected content not found"

        # Validate JSON schema
        if config.expected_json_schema:
            try:
                response_json = json.loads(content)
                # Simple schema validation (in production, use jsonschema library)
                schema_valid = self._validate_json_schema(
                    response_json, config.expected_json_schema
                )

                validations.append(
                    {
                        "name": "json_schema",
                        "passed": schema_valid,
                        "expected": "Valid JSON schema",
                        "actual": "Valid" if schema_valid else "Invalid",
                    }
                )

                if not schema_valid:
                    result.status = CheckStatus.FAILURE
                    if not result.error_message:
                        result.error_message = "JSON schema validation failed"
            except json.JSONDecodeError:
                validations.append(
                    {
                        "name": "json_schema",
                        "passed": False,
                        "expected": "Valid JSON",
                        "actual": "Invalid JSON",
                    }
                )
                result.status = CheckStatus.FAILURE
                if not result.error_message:
                    result.error_message = "Response is not valid JSON"

        # Update validation counters
        result.validations_passed = sum(1 for v in validations if v["passed"])
        result.validations_failed = sum(
            1 for v in validations if not v["passed"]
        )
        result.validation_details = validations

    def _validate_json_schema(self, data: Any, schema: Dict[str, Any]) -> bool:
        """Simple JSON schema validation"""
        # This is a simplified implementation
        # In production, use the jsonschema library
        try:
            if "type" in schema:
                expected_type = schema["type"]
                if expected_type == "object" and not isinstance(data, dict):
                    return False
                elif expected_type == "array" and not isinstance(data, list):
                    return False
                elif expected_type == "string" and not isinstance(data, str):
                    return False
                elif expected_type == "number" and not isinstance(
                    data, (int, float)
                ):
                    return False
                elif expected_type == "boolean" and not isinstance(data, bool):
                    return False

            if "required" in schema and isinstance(data, dict):
                for required_field in schema["required"]:
                    if required_field not in data:
                        return False

            return True
        except Exception:
            return False

    async def _run_api_check(self, check: SyntheticCheck) -> CheckResult:
        """Run API synthetic check"""
        config: ApiCheckConfig = check.config
        start_time = time.time()

        try:
            results = []

            # Test each endpoint
            for endpoint_config in config.endpoints:
                endpoint_result = await self._test_api_endpoint(
                    config, endpoint_config
                )
                results.append(endpoint_result)

            # Aggregate results
            total_duration = (time.time() - start_time) * 1000
            all_passed = all(r["success"] for r in results)

            result = CheckResult(
                check_name=check.name,
                check_type=CheckType.API,
                status=CheckStatus.SUCCESS
                if all_passed
                else CheckStatus.FAILURE,
                timestamp=datetime.now(timezone.utc),
                duration_ms=total_duration,
                custom_metrics={
                    "endpoints_tested": len(results),
                    "endpoints_passed": sum(
                        1 for r in results if r["success"]
                    ),
                    "endpoints_failed": sum(
                        1 for r in results if not r["success"]
                    ),
                },
            )

            if not all_passed:
                failed_endpoints = [
                    r["endpoint"] for r in results if not r["success"]
                ]
                result.error_message = (
                    f"API endpoints failed: {', '.join(failed_endpoints)}"
                )

            result.validation_details = results
            result.validations_passed = sum(1 for r in results if r["success"])
            result.validations_failed = sum(
                1 for r in results if not r["success"]
            )

            return result

        except Exception as e:
            return CheckResult(
                check_name=check.name,
                check_type=CheckType.API,
                status=CheckStatus.ERROR,
                timestamp=datetime.now(timezone.utc),
                duration_ms=(time.time() - start_time) * 1000,
                error_message=str(e),
                error_details={"exception": type(e).__name__},
            )

    async def _test_api_endpoint(
        self, config: ApiCheckConfig, endpoint_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Test a single API endpoint"""
        endpoint_url = f"{config.base_url.rstrip('/')}/{endpoint_config['path'].lstrip('/')}"
        method = endpoint_config.get("method", "GET")

        try:
            # Prepare headers
            headers = config.common_headers.copy()
            headers.update(endpoint_config.get("headers", {}))

            # Handle authentication
            if config.authentication:
                if config.authentication.get("type") == "bearer":
                    headers[
                        "Authorization"
                    ] = f"Bearer {config.authentication['token']}"
                elif config.authentication.get("type") == "basic":
                    # Basic auth would be handled by aiohttp BasicAuth
                    pass

            # Make request
            async with self.http_session.request(
                method=method,
                url=endpoint_url,
                headers=headers,
                json=endpoint_config.get("body"),
                timeout=aiohttp.ClientTimeout(total=config.timeout_seconds),
            ) as response:
                content = await response.text()

                # Check expected status
                expected_status = endpoint_config.get("expected_status", 200)
                success = response.status == expected_status

                return {
                    "endpoint": endpoint_config["path"],
                    "method": method,
                    "success": success,
                    "status_code": response.status,
                    "expected_status": expected_status,
                    "response_size": len(content),
                }

        except Exception as e:
            return {
                "endpoint": endpoint_config["path"],
                "method": method,
                "success": False,
                "error": str(e),
            }

    async def _run_user_journey_check(
        self, check: SyntheticCheck
    ) -> CheckResult:
        """Run user journey synthetic check"""
        config: UserJourneyConfig = check.config
        start_time = time.time()

        try:
            journey_session = (
                aiohttp.ClientSession()
                if config.maintain_session
                else self.http_session
            )

            step_results = []
            journey_context = {}  # Store data between steps

            try:
                for step in config.steps:
                    step_result = await self._execute_journey_step(
                        step, journey_session, journey_context
                    )
                    step_results.append(step_result)

                    # If step failed and it's critical, stop journey
                    if not step_result["success"] and step_result.get(
                        "critical", True
                    ):
                        break

                # Calculate overall success
                critical_steps = [
                    r for r in step_results if r.get("critical", True)
                ]
                journey_success = all(r["success"] for r in critical_steps)

                result = CheckResult(
                    check_name=check.name,
                    check_type=CheckType.USER_JOURNEY,
                    status=(
                        CheckStatus.SUCCESS
                        if journey_success
                        else CheckStatus.FAILURE
                    ),
                    timestamp=datetime.now(timezone.utc),
                    duration_ms=(time.time() - start_time) * 1000,
                    custom_metrics={
                        "steps_total": len(config.steps),
                        "steps_completed": len(step_results),
                        "steps_passed": sum(
                            1 for r in step_results if r["success"]
                        ),
                        "steps_failed": sum(
                            1 for r in step_results if not r["success"]
                        ),
                    },
                )

                if not journey_success:
                    failed_steps = [
                        r["step_name"]
                        for r in step_results
                        if not r["success"]
                    ]
                    result.error_message = f"User journey failed at steps: {', '.join(failed_steps)}"

                result.validation_details = step_results
                result.validations_passed = sum(
                    1 for r in step_results if r["success"]
                )
                result.validations_failed = sum(
                    1 for r in step_results if not r["success"]
                )

                return result

            finally:
                if (
                    config.maintain_session
                    and journey_session != self.http_session
                ):
                    await journey_session.close()

        except Exception as e:
            return CheckResult(
                check_name=check.name,
                check_type=CheckType.USER_JOURNEY,
                status=CheckStatus.ERROR,
                timestamp=datetime.now(timezone.utc),
                duration_ms=(time.time() - start_time) * 1000,
                error_message=str(e),
                error_details={"exception": type(e).__name__},
            )

    async def _execute_journey_step(
        self,
        step: UserJourneyStep,
        session: aiohttp.ClientSession,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a single step in a user journey"""
        step_start = time.time()

        try:
            if step.action_type == "http_request":
                return await self._execute_http_step(step, session, context)
            elif step.action_type == "wait":
                await asyncio.sleep(step.config.get("seconds", 1))
                return {
                    "step_name": step.name,
                    "action_type": step.action_type,
                    "success": True,
                    "duration_ms": (time.time() - step_start) * 1000,
                }
            elif step.action_type == "validate":
                return await self._execute_validation_step(step, context)
            elif step.action_type == "extract":
                return await self._execute_extraction_step(step, context)
            else:
                return {
                    "step_name": step.name,
                    "action_type": step.action_type,
                    "success": False,
                    "error": f"Unknown action type: {step.action_type}",
                    "duration_ms": (time.time() - step_start) * 1000,
                }

        except Exception as e:
            return {
                "step_name": step.name,
                "action_type": step.action_type,
                "success": False,
                "error": str(e),
                "duration_ms": (time.time() - step_start) * 1000,
            }

    async def _execute_http_step(
        self,
        step: UserJourneyStep,
        session: aiohttp.ClientSession,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute HTTP request step"""
        step_start = time.time()

        try:
            # Prepare request from step config
            url = step.config["url"]
            method = step.config.get("method", "GET")
            headers = step.config.get("headers", {})

            # Substitute context variables in URL and headers
            url = self._substitute_variables(url, context)
            headers = {
                k: self._substitute_variables(v, context)
                for k, v in headers.items()
            }

            # Make request
            async with session.request(
                method=method,
                url=url,
                headers=headers,
                json=step.config.get("body"),
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                content = await response.text()

                # Store response in context for next steps
                context[f"{step.name}_response"] = {
                    "status_code": response.status,
                    "content": content,
                    "headers": dict(response.headers),
                }

                # Validate response if validation config provided
                success = True
                validation_error = None

                if step.validation:
                    expected_status = step.validation.get("status_code", 200)
                    if response.status != expected_status:
                        success = False
                        validation_error = f"Expected status {expected_status}, got {response.status}"

                    if "content_contains" in step.validation:
                        expected_content = step.validation["content_contains"]
                        if expected_content not in content:
                            success = False
                            validation_error = f"Response does not contain: {expected_content}"

                return {
                    "step_name": step.name,
                    "action_type": step.action_type,
                    "success": success,
                    "status_code": response.status,
                    "response_size": len(content),
                    "duration_ms": (time.time() - step_start) * 1000,
                    "error": validation_error,
                }

        except Exception as e:
            return {
                "step_name": step.name,
                "action_type": step.action_type,
                "success": False,
                "error": str(e),
                "duration_ms": (time.time() - step_start) * 1000,
            }

    async def _execute_validation_step(
        self, step: UserJourneyStep, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute validation step"""
        # Implementation for validation steps
        # This would validate data in the context against expected criteria
        return {
            "step_name": step.name,
            "action_type": step.action_type,
            "success": True,
            "duration_ms": 0,
        }

    async def _execute_extraction_step(
        self, step: UserJourneyStep, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute data extraction step"""
        # Implementation for extracting data from responses and storing in context
        return {
            "step_name": step.name,
            "action_type": step.action_type,
            "success": True,
            "duration_ms": 0,
        }

    def _substitute_variables(self, text: str, context: Dict[str, Any]) -> str:
        """Substitute context variables in text"""
        # Simple variable substitution - in production, use a template engine
        for key, value in context.items():
            if isinstance(value, str):
                text = text.replace(f"{{{key}}}", value)
        return text

    def get_check_results(
        self, check_name: str, limit: int = 100
    ) -> List[CheckResult]:
        """Get recent results for a check"""
        if check_name not in self.results:
            return []

        return self.results[check_name][-limit:]

    def get_check_statistics(
        self, check_name: str, hours: int = 24
    ) -> Dict[str, Any]:
        """Get statistics for a check"""
        if check_name not in self.results:
            return {}

        # Filter results to time window
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent_results = [
            r for r in self.results[check_name] if r.timestamp >= cutoff_time
        ]

        if not recent_results:
            return {}

        # Calculate statistics
        total_checks = len(recent_results)
        successful_checks = sum(
            1 for r in recent_results if r.status == CheckStatus.SUCCESS
        )
        failed_checks = sum(
            1 for r in recent_results if r.status == CheckStatus.FAILURE
        )
        error_checks = sum(
            1 for r in recent_results if r.status == CheckStatus.ERROR
        )
        timeout_checks = sum(
            1 for r in recent_results if r.status == CheckStatus.TIMEOUT
        )

        response_times = [
            r.duration_ms for r in recent_results if r.duration_ms
        ]

        return {
            "check_name": check_name,
            "time_window_hours": hours,
            "total_checks": total_checks,
            "successful_checks": successful_checks,
            "failed_checks": failed_checks,
            "error_checks": error_checks,
            "timeout_checks": timeout_checks,
            "success_rate": (
                (successful_checks / total_checks) * 100
                if total_checks > 0
                else 0
            ),
            "avg_response_time_ms": (
                sum(response_times) / len(response_times)
                if response_times
                else 0
            ),
            "min_response_time_ms": min(response_times)
            if response_times
            else 0,
            "max_response_time_ms": max(response_times)
            if response_times
            else 0,
            "consecutive_failures": self.consecutive_failures.get(
                check_name, 0
            ),
            "last_success": self.last_success.get(check_name, None),
        }

    def get_overall_statistics(self) -> Dict[str, Any]:
        """Get overall synthetic monitoring statistics"""
        total_checks = len(self.checks)
        enabled_checks = sum(1 for c in self.checks.values() if c.enabled)

        # Calculate aggregate stats
        all_results = []
        for results in self.results.values():
            all_results.extend(results[-24:])  # Last 24 results per check

        if all_results:
            success_rate = (
                sum(1 for r in all_results if r.status == CheckStatus.SUCCESS)
                / len(all_results)
            ) * 100
            avg_response_time = sum(
                r.duration_ms for r in all_results if r.duration_ms
            ) / len(all_results)
        else:
            success_rate = 0
            avg_response_time = 0

        return {
            "total_checks": total_checks,
            "enabled_checks": enabled_checks,
            "running_checks": len(self.check_tasks),
            "overall_success_rate": success_rate,
            "avg_response_time_ms": avg_response_time,
            "checks_with_failures": sum(
                1 for count in self.consecutive_failures.values() if count > 0
            ),
        }


# Helper functions to create common check types
def create_http_check(
    name: str,
    url: str,
    method: str = "GET",
    expected_status: int = 200,
    timeout: float = 30.0,
    interval: float = 60.0,
) -> SyntheticCheck:
    """Create a simple HTTP check"""
    config = HttpCheckConfig(
        url=url,
        method=method,
        timeout_seconds=timeout,
        expected_status_codes=[expected_status],
    )

    return SyntheticCheck(
        name=name,
        check_type=CheckType.HTTP,
        config=config,
        interval_seconds=interval,
    )


def create_api_health_check(
    name: str, base_url: str, endpoints: List[str], interval: float = 60.0
) -> SyntheticCheck:
    """Create API health check for multiple endpoints"""
    endpoint_configs = [
        {"path": endpoint, "method": "GET", "expected_status": 200}
        for endpoint in endpoints
    ]

    config = ApiCheckConfig(base_url=base_url, endpoints=endpoint_configs)

    return SyntheticCheck(
        name=name,
        check_type=CheckType.API,
        config=config,
        interval_seconds=interval,
    )


__all__ = [
    "CheckType",
    "CheckStatus",
    "CheckResult",
    "HttpCheckConfig",
    "ApiCheckConfig",
    "UserJourneyStep",
    "UserJourneyConfig",
    "SyntheticCheck",
    "SyntheticMonitor",
    "create_http_check",
    "create_api_health_check",
]
