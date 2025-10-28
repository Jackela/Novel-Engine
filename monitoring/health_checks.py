#!/usr/bin/env python3
"""
Health Check Endpoints and Synthetic Monitoring for Novel Engine

Implements comprehensive health checks with:
- Comprehensive health check endpoints
- Synthetic transaction monitoring
- Uptime monitoring and SLA tracking
- Dependency health monitoring
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import aiohttp
import aiosqlite
import psutil
from fastapi import FastAPI
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status values"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check definition"""

    name: str
    check_function: Callable
    timeout_seconds: float = 5.0
    critical: bool = True
    enabled: bool = True
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    """Result of a health check"""

    name: str
    status: HealthStatus
    message: str
    duration_ms: float
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class SystemHealth:
    """Overall system health"""

    status: HealthStatus
    timestamp: datetime
    uptime_seconds: float
    checks: List[HealthCheckResult]
    summary: Dict[str, Any] = field(default_factory=dict)


class HealthCheckManager:
    """Manages health checks for the application"""

    def __init__(self):
        self.checks: Dict[str, HealthCheck] = {}
        self.start_time = time.time()
        self.last_check_results: Dict[str, HealthCheckResult] = {}

        # Register default health checks
        self._register_default_checks()

        logger.info("Health check manager initialized")

    def register_check(self, health_check: HealthCheck):
        """Register a health check"""
        self.checks[health_check.name] = health_check
        logger.info(f"Registered health check: {health_check.name}")

    def unregister_check(self, name: str):
        """Unregister a health check"""
        if name in self.checks:
            del self.checks[name]
            logger.info(f"Unregistered health check: {name}")

    async def run_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check"""
        if name not in self.checks:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Health check '{name}' not found",
                duration_ms=0,
                timestamp=datetime.utcnow(),
                error="Check not found",
            )

        check = self.checks[name]
        if not check.enabled:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message="Health check disabled",
                duration_ms=0,
                timestamp=datetime.utcnow(),
            )

        start_time = time.time()

        try:
            # Run the check with timeout
            result = await asyncio.wait_for(check.check_function(), timeout=check.timeout_seconds)

            duration_ms = (time.time() - start_time) * 1000

            if isinstance(result, dict):
                status = HealthStatus(result.get("status", "healthy"))
                message = result.get("message", "OK")
                details = result.get("details", {})
            elif isinstance(result, bool):
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                message = "OK" if result else "Check failed"
                details = {}
            else:
                status = HealthStatus.HEALTHY
                message = str(result) if result else "OK"
                details = {}

            health_result = HealthCheckResult(
                name=name,
                status=status,
                message=message,
                duration_ms=duration_ms,
                timestamp=datetime.utcnow(),
                details=details,
            )

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            health_result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {check.timeout_seconds}s",
                duration_ms=duration_ms,
                timestamp=datetime.utcnow(),
                error="Timeout",
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            health_result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                duration_ms=duration_ms,
                timestamp=datetime.utcnow(),
                error=str(e),
            )

        # Store result
        self.last_check_results[name] = health_result

        return health_result

    async def run_all_checks(self) -> SystemHealth:
        """Run all registered health checks"""
        results = []

        # Run all checks concurrently
        tasks = []
        for name in self.checks.keys():
            task = asyncio.create_task(self.run_check(name))
            tasks.append(task)

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # Filter out exceptions and convert to HealthCheckResult if needed
            filtered_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    check_name = list(self.checks.keys())[i]
                    filtered_results.append(
                        HealthCheckResult(
                            name=check_name,
                            status=HealthStatus.UNHEALTHY,
                            message=f"Health check error: {str(result)}",
                            duration_ms=0,
                            timestamp=datetime.utcnow(),
                            error=str(result),
                        )
                    )
                else:
                    filtered_results.append(result)
            results = filtered_results

        # Determine overall system status
        overall_status = self._calculate_overall_status(results)

        # Calculate uptime
        uptime_seconds = time.time() - self.start_time

        # Generate summary
        summary = self._generate_summary(results)

        return SystemHealth(
            status=overall_status,
            timestamp=datetime.utcnow(),
            uptime_seconds=uptime_seconds,
            checks=results,
            summary=summary,
        )

    def _calculate_overall_status(self, results: List[HealthCheckResult]) -> HealthStatus:
        """Calculate overall system status from individual check results"""
        if not results:
            return HealthStatus.UNKNOWN

        # Check for critical failures
        critical_checks = [
            result
            for result in results
            if self.checks.get(result.name, HealthCheck("", lambda: None)).critical
        ]

        critical_failures = [
            result for result in critical_checks if result.status == HealthStatus.UNHEALTHY
        ]

        if critical_failures:
            return HealthStatus.UNHEALTHY

        # Check for any degraded status
        degraded_checks = [result for result in results if result.status == HealthStatus.DEGRADED]

        if degraded_checks:
            return HealthStatus.DEGRADED

        # Check for non-critical failures
        failed_checks = [result for result in results if result.status == HealthStatus.UNHEALTHY]

        if failed_checks:
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    def _generate_summary(self, results: List[HealthCheckResult]) -> Dict[str, Any]:
        """Generate summary statistics from health check results"""
        if not results:
            return {}

        total_checks = len(results)
        healthy_count = sum(1 for r in results if r.status == HealthStatus.HEALTHY)
        degraded_count = sum(1 for r in results if r.status == HealthStatus.DEGRADED)
        unhealthy_count = sum(1 for r in results if r.status == HealthStatus.UNHEALTHY)
        unknown_count = sum(1 for r in results if r.status == HealthStatus.UNKNOWN)

        avg_duration = sum(r.duration_ms for r in results) / total_checks
        max_duration = max(r.duration_ms for r in results)

        return {
            "total_checks": total_checks,
            "healthy_count": healthy_count,
            "degraded_count": degraded_count,
            "unhealthy_count": unhealthy_count,
            "unknown_count": unknown_count,
            "health_percentage": (healthy_count / total_checks) * 100,
            "average_duration_ms": avg_duration,
            "max_duration_ms": max_duration,
        }

    def _register_default_checks(self):
        """Register default health checks"""

        # System resource checks
        self.register_check(
            HealthCheck(
                name="system_memory",
                check_function=self._check_system_memory,
                critical=True,
                tags={"category": "system"},
            )
        )

        self.register_check(
            HealthCheck(
                name="system_disk",
                check_function=self._check_system_disk,
                critical=True,
                tags={"category": "system"},
            )
        )

        self.register_check(
            HealthCheck(
                name="system_cpu",
                check_function=self._check_system_cpu,
                critical=False,
                tags={"category": "system"},
            )
        )

        # Database checks
        self.register_check(
            HealthCheck(
                name="database_connection",
                check_function=self._check_database,
                critical=True,
                tags={"category": "database"},
            )
        )

        # Application-specific checks
        self.register_check(
            HealthCheck(
                name="story_generation",
                check_function=self._check_story_generation,
                critical=True,
                tags={"category": "application"},
            )
        )

        self.register_check(
            HealthCheck(
                name="character_system",
                check_function=self._check_character_system,
                critical=True,
                tags={"category": "application"},
            )
        )

    async def _check_system_memory(self) -> Dict[str, Any]:
        """Check system memory usage"""
        memory = psutil.virtual_memory()
        usage_percent = memory.percent

        if usage_percent > 95:
            status = HealthStatus.UNHEALTHY
            message = f"Memory usage critical: {usage_percent:.1f}%"
        elif usage_percent > 85:
            status = HealthStatus.DEGRADED
            message = f"Memory usage high: {usage_percent:.1f}%"
        else:
            status = HealthStatus.HEALTHY
            message = f"Memory usage normal: {usage_percent:.1f}%"

        return {
            "status": status.value,
            "message": message,
            "details": {
                "total_gb": memory.total / (1024**3),
                "available_gb": memory.available / (1024**3),
                "used_percent": usage_percent,
            },
        }

    async def _check_system_disk(self) -> Dict[str, Any]:
        """Check system disk usage"""
        disk = psutil.disk_usage("/")
        usage_percent = (disk.used / disk.total) * 100

        if usage_percent > 95:
            status = HealthStatus.UNHEALTHY
            message = f"Disk usage critical: {usage_percent:.1f}%"
        elif usage_percent > 85:
            status = HealthStatus.DEGRADED
            message = f"Disk usage high: {usage_percent:.1f}%"
        else:
            status = HealthStatus.HEALTHY
            message = f"Disk usage normal: {usage_percent:.1f}%"

        return {
            "status": status.value,
            "message": message,
            "details": {
                "total_gb": disk.total / (1024**3),
                "free_gb": disk.free / (1024**3),
                "used_percent": usage_percent,
            },
        }

    async def _check_system_cpu(self) -> Dict[str, Any]:
        """Check system CPU usage"""
        # Get CPU usage over 1 second interval
        cpu_percent = psutil.cpu_percent(interval=1)

        if cpu_percent > 90:
            status = HealthStatus.DEGRADED
            message = f"CPU usage high: {cpu_percent:.1f}%"
        else:
            status = HealthStatus.HEALTHY
            message = f"CPU usage normal: {cpu_percent:.1f}%"

        return {
            "status": status.value,
            "message": message,
            "details": {"cpu_percent": cpu_percent, "cpu_count": psutil.cpu_count()},
        }

    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            # Try to connect to the database
            db_path = "data/api_server.db"
            if not os.path.exists(db_path):
                return {
                    "status": HealthStatus.UNHEALTHY.value,
                    "message": "Database file not found",
                    "details": {"db_path": db_path},
                }

            async with aiosqlite.connect(db_path) as db:
                await db.execute("SELECT 1")
                await db.commit()

            return {
                "status": HealthStatus.HEALTHY.value,
                "message": "Database connection successful",
                "details": {"db_path": db_path},
            }

        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Database connection failed: {str(e)}",
                "details": {"error": str(e)},
            }

    async def _check_story_generation(self) -> Dict[str, Any]:
        """Check story generation functionality"""
        try:
            # This is a simplified check - in production you might test
            # a simple story generation request

            # Check if the story generation module can be imported
            from src.ai_intelligence.story_quality_engine import StoryQualityEngine

            # Simple functionality test
            StoryQualityEngine()

            return {
                "status": HealthStatus.HEALTHY.value,
                "message": "Story generation system operational",
                "details": {"component": "story_quality_engine"},
            }

        except ImportError as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Story generation module not available: {str(e)}",
                "details": {"error": str(e)},
            }
        except Exception as e:
            return {
                "status": HealthStatus.DEGRADED.value,
                "message": f"Story generation system error: {str(e)}",
                "details": {"error": str(e)},
            }

    async def _check_character_system(self) -> Dict[str, Any]:
        """Check character system functionality"""
        try:
            # Check if character files exist
            character_dir = "characters"
            if not os.path.exists(character_dir):
                return {
                    "status": HealthStatus.DEGRADED.value,
                    "message": "Character directory not found",
                    "details": {"character_dir": character_dir},
                }

            # Count available characters
            character_count = 0
            for item in os.listdir(character_dir):
                if os.path.isdir(os.path.join(character_dir, item)):
                    character_count += 1

            if character_count == 0:
                return {
                    "status": HealthStatus.DEGRADED.value,
                    "message": "No character files found",
                    "details": {"character_count": character_count},
                }

            return {
                "status": HealthStatus.HEALTHY.value,
                "message": f"Character system operational with {character_count} characters",
                "details": {"character_count": character_count},
            }

        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Character system error: {str(e)}",
                "details": {"error": str(e)},
            }


# Global health check manager
health_manager = HealthCheckManager()


def create_health_endpoint(app: FastAPI):
    """Create health check endpoints for FastAPI app"""

    @app.get("/health")
    async def health_check():
        """Simple health check endpoint"""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    @app.get("/health/live")
    async def liveness_probe():
        """Kubernetes liveness probe endpoint"""
        return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}

    @app.get("/health/ready")
    async def readiness_probe():
        """Kubernetes readiness probe endpoint"""
        system_health = await health_manager.run_all_checks()

        if system_health.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "ready",
                    "system_status": system_health.status.value,
                    "timestamp": system_health.timestamp.isoformat(),
                },
            )
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "system_status": system_health.status.value,
                    "timestamp": system_health.timestamp.isoformat(),
                },
            )

    @app.get("/health/detailed")
    async def detailed_health_check():
        """Detailed health check with all components"""
        system_health = await health_manager.run_all_checks()

        response_data = {
            "status": system_health.status.value,
            "timestamp": system_health.timestamp.isoformat(),
            "uptime_seconds": system_health.uptime_seconds,
            "summary": system_health.summary,
            "checks": [],
        }

        for check_result in system_health.checks:
            response_data["checks"].append(
                {
                    "name": check_result.name,
                    "status": check_result.status.value,
                    "message": check_result.message,
                    "duration_ms": check_result.duration_ms,
                    "timestamp": check_result.timestamp.isoformat(),
                    "details": check_result.details,
                    "error": check_result.error,
                }
            )

        # Return appropriate HTTP status
        if system_health.status == HealthStatus.HEALTHY:
            status_code = 200
        elif system_health.status == HealthStatus.DEGRADED:
            status_code = 200  # Still serving traffic
        else:
            status_code = 503  # Service unavailable

        return JSONResponse(status_code=status_code, content=response_data)

    @app.get("/health/check/{check_name}")
    async def individual_health_check(check_name: str):
        """Run individual health check"""
        result = await health_manager.run_check(check_name)

        response_data = {
            "name": result.name,
            "status": result.status.value,
            "message": result.message,
            "duration_ms": result.duration_ms,
            "timestamp": result.timestamp.isoformat(),
            "details": result.details,
            "error": result.error,
        }

        if result.status == HealthStatus.HEALTHY:
            return JSONResponse(status_code=200, content=response_data)
        else:
            return JSONResponse(status_code=503, content=response_data)

    logger.info("Health check endpoints registered")


# Synthetic monitoring
class SyntheticMonitor:
    """Synthetic monitoring for external services and user journeys"""

    def __init__(self):
        self.checks: Dict[str, "SyntheticCheck"] = {}
        self.results: Dict[str, List["CheckResult"]] = {}
        self.running = False

    def register_check(self, check: "SyntheticCheck"):
        """Register a synthetic check"""
        self.checks[check.name] = check
        self.results[check.name] = []
        logger.info(f"Registered synthetic check: {check.name}")

    async def start_monitoring(self):
        """Start synthetic monitoring"""
        self.running = True

        # Start monitoring tasks for each check
        tasks = []
        for check in self.checks.values():
            task = asyncio.create_task(self._monitor_check(check))
            tasks.append(task)

        logger.info(f"Started synthetic monitoring for {len(tasks)} checks")

        # Wait for all tasks to complete (they run indefinitely)
        if tasks:
            await asyncio.gather(*tasks)

    async def stop_monitoring(self):
        """Stop synthetic monitoring"""
        self.running = False
        logger.info("Synthetic monitoring stopped")

    async def _monitor_check(self, check: "SyntheticCheck"):
        """Monitor a specific synthetic check"""
        while self.running:
            try:
                result = await check.run()

                # Store result
                self.results[check.name].append(result)

                # Keep only last 100 results
                if len(self.results[check.name]) > 100:
                    self.results[check.name] = self.results[check.name][-100:]

                # Log failures
                if not result.success:
                    logger.warning(f"Synthetic check failed: {check.name} - {result.message}")

                await asyncio.sleep(check.interval_seconds)

            except Exception as e:
                logger.error(f"Error in synthetic check {check.name}: {e}")
                await asyncio.sleep(check.interval_seconds)

    def get_results(self, check_name: str) -> List["CheckResult"]:
        """Get results for a specific check"""
        return self.results.get(check_name, [])

    def get_all_results(self) -> Dict[str, List["CheckResult"]]:
        """Get all check results"""
        return self.results.copy()


@dataclass
class CheckResult:
    """Result of a synthetic check"""

    timestamp: datetime
    success: bool
    duration_ms: float
    message: str
    status_code: Optional[int] = None
    response_size: Optional[int] = None
    error: Optional[str] = None


class SyntheticCheck:
    """Base class for synthetic checks"""

    def __init__(self, name: str, interval_seconds: float = 60.0):
        self.name = name
        self.interval_seconds = interval_seconds

    async def run(self) -> CheckResult:
        """Run the synthetic check"""
        raise NotImplementedError


class HttpSyntheticCheck(SyntheticCheck):
    """HTTP synthetic check"""

    def __init__(
        self,
        name: str,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
        interval_seconds: float = 60.0,
        expected_status: int = 200,
    ):
        super().__init__(name, interval_seconds)
        self.url = url
        self.method = method
        self.headers = headers or {}
        self.timeout = timeout
        self.expected_status = expected_status

    async def run(self) -> CheckResult:
        """Run HTTP check"""
        start_time = time.time()

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as session:
                async with session.request(self.method, self.url, headers=self.headers) as response:
                    duration_ms = (time.time() - start_time) * 1000
                    response_size = len(await response.read())

                    success = response.status == self.expected_status
                    message = f"HTTP {self.method} {self.url} returned {response.status}"

                    return CheckResult(
                        timestamp=datetime.utcnow(),
                        success=success,
                        duration_ms=duration_ms,
                        message=message,
                        status_code=response.status,
                        response_size=response_size,
                    )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return CheckResult(
                timestamp=datetime.utcnow(),
                success=False,
                duration_ms=duration_ms,
                message=f"HTTP check failed: {str(e)}",
                error=str(e),
            )


# Global synthetic monitor
synthetic_monitor = SyntheticMonitor()

__all__ = [
    "HealthStatus",
    "HealthCheck",
    "HealthCheckResult",
    "SystemHealth",
    "HealthCheckManager",
    "health_manager",
    "create_health_endpoint",
    "SyntheticMonitor",
    "SyntheticCheck",
    "CheckResult",
    "HttpSyntheticCheck",
    "synthetic_monitor",
]
