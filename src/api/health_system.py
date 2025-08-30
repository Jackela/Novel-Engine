#!/usr/bin/env python3
"""
Comprehensive Health Check System.

Provides multi-layer health monitoring, dependency checks, and system metrics
for production readiness and operational monitoring.
"""

import asyncio
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

import psutil

from .response_models import HealthCheckData

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health check status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentType(str, Enum):
    """System component types."""

    DATABASE = "database"
    ORCHESTRATOR = "orchestrator"
    CACHE = "cache"
    FILESYSTEM = "filesystem"
    MEMORY = "memory"
    CPU = "cpu"
    NETWORK = "network"
    EXTERNAL_SERVICE = "external_service"


@dataclass
class HealthCheckResult:
    """Individual health check result."""

    component: str
    component_type: ComponentType
    status: HealthStatus
    response_time_ms: float
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None


@dataclass
class SystemHealth:
    """Overall system health status."""

    status: HealthStatus
    checks: List[HealthCheckResult]
    uptime_seconds: float
    timestamp: datetime
    version: str
    environment: str
    total_checks: int
    passed_checks: int
    failed_checks: int
    response_time_ms: float


class HealthChecker:
    """Individual health check implementation."""

    def __init__(
        self,
        name: str,
        component_type: ComponentType,
        check_func: Callable[[], Awaitable[Dict[str, Any]]],
        timeout_seconds: float = 5.0,
        critical: bool = True,
    ):
        self.name = name
        self.component_type = component_type
        self.check_func = check_func
        self.timeout_seconds = timeout_seconds
        self.critical = critical

    async def execute(self) -> HealthCheckResult:
        """Execute the health check with timeout and error handling."""
        start_time = time.time()

        try:
            # Execute check with timeout
            result = await asyncio.wait_for(
                self.check_func(), timeout=self.timeout_seconds
            )

            response_time = (time.time() - start_time) * 1000

            return HealthCheckResult(
                component=self.name,
                component_type=self.component_type,
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                message=result.get("message", "Component is healthy"),
                details=result.get("details"),
                timestamp=datetime.now(),
            )

        except asyncio.TimeoutError:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component=self.name,
                component_type=self.component_type,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message=f"Health check timed out after {self.timeout_seconds}s",
                error="timeout",
                timestamp=datetime.now(),
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component=self.name,
                component_type=self.component_type,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message=f"Health check failed: {str(e)}",
                error=str(e),
                timestamp=datetime.now(),
            )


class HealthMonitor:
    """Comprehensive health monitoring system."""

    def __init__(self, app_start_time: Optional[datetime] = None):
        self.app_start_time = app_start_time or datetime.now()
        self.health_checkers: List[HealthChecker] = []
        self.last_check_time: Optional[datetime] = None
        self.last_check_result: Optional[SystemHealth] = None
        self.check_history: List[SystemHealth] = []
        self.max_history_size = 100

    def register_checker(self, checker: HealthChecker):
        """Register a health checker."""
        self.health_checkers.append(checker)
        logger.info(f"Registered health checker: {checker.name}")

    def register_database_check(self, database_path: str):
        """Register database connectivity check."""

        async def check_database():
            """
            Check database connectivity and health.

            Returns:
                Database health status and metrics

            Raises:
                Exception: If database connectivity fails
            """
            try:
                # Test database connection
                conn = sqlite3.connect(database_path, timeout=2.0)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                conn.close()

                # Check database file size
                db_path = Path(database_path)
                if db_path.exists():
                    file_size = db_path.stat().st_size
                    return {
                        "message": "Database connection successful",
                        "details": {
                            "file_size_bytes": file_size,
                            "file_path": str(db_path.absolute()),
                        },
                    }
                else:
                    raise Exception(f"Database file not found: {database_path}")

            except Exception as e:
                raise Exception(f"Database check failed: {str(e)}")

        checker = HealthChecker(
            name="database",
            component_type=ComponentType.DATABASE,
            check_func=check_database,
            timeout_seconds=3.0,
            critical=True,
        )
        self.register_checker(checker)

    def register_orchestrator_check(self, orchestrator):
        """Register system orchestrator check."""

        async def check_orchestrator():
            """
            Check system orchestrator health and status.

            Returns:
                Orchestrator health status and metrics

            Raises:
                Exception: If orchestrator is not initialized or unhealthy
            """
            try:
                if not orchestrator:
                    raise Exception("Orchestrator not initialized")

                # Check if orchestrator is running
                health_result = await orchestrator.get_system_health()
                active_agents = getattr(orchestrator, "active_agents", {})

                return {
                    "message": "Orchestrator operational",
                    "details": {
                        "active_agents": len(active_agents),
                        "health_data": (
                            health_result.data if health_result.success else None
                        ),
                    },
                }

            except Exception as e:
                raise Exception(f"Orchestrator check failed: {str(e)}")

        checker = HealthChecker(
            name="orchestrator",
            component_type=ComponentType.ORCHESTRATOR,
            check_func=check_orchestrator,
            timeout_seconds=2.0,
            critical=True,
        )
        self.register_checker(checker)

    def register_system_resource_checks(self):
        """Register system resource health checks."""

        # Memory check
        async def check_memory():
            """
            Check system memory usage and availability.

            Returns:
                Memory health status and usage metrics
            """
            memory = psutil.virtual_memory()
            memory_usage_percent = memory.percent

            if memory_usage_percent > 90:
                raise Exception(f"High memory usage: {memory_usage_percent}%")

            return {
                "message": f"Memory usage: {memory_usage_percent}%",
                "details": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "usage_percent": memory_usage_percent,
                },
            }

        # CPU check
        async def check_cpu():
            """
            Check CPU usage and performance metrics.

            Returns:
                CPU health status and performance metrics
            """
            # Get CPU usage over 1 second
            cpu_percent = psutil.cpu_percent(interval=1)

            if cpu_percent > 95:
                raise Exception(f"High CPU usage: {cpu_percent}%")

            return {
                "message": f"CPU usage: {cpu_percent}%",
                "details": {
                    "usage_percent": cpu_percent,
                    "cpu_count": psutil.cpu_count(),
                    "load_average": (
                        psutil.getloadavg() if hasattr(psutil, "getloadavg") else None
                    ),
                },
            }

        # Disk check
        async def check_filesystem():
            """
            Check filesystem health and disk space availability.

            Returns:
                Filesystem health status and disk usage metrics
            """
            disk_usage = psutil.disk_usage(".")
            usage_percent = (disk_usage.used / disk_usage.total) * 100

            if usage_percent > 95:
                raise Exception(f"High disk usage: {usage_percent:.1f}%")

            return {
                "message": f"Disk usage: {usage_percent:.1f}%",
                "details": {
                    "total_gb": round(disk_usage.total / (1024**3), 2),
                    "used_gb": round(disk_usage.used / (1024**3), 2),
                    "free_gb": round(disk_usage.free / (1024**3), 2),
                    "usage_percent": round(usage_percent, 1),
                },
            }

        # Register resource checkers
        self.register_checker(
            HealthChecker(
                name="memory",
                component_type=ComponentType.MEMORY,
                check_func=check_memory,
                timeout_seconds=2.0,
                critical=False,
            )
        )

        self.register_checker(
            HealthChecker(
                name="cpu",
                component_type=ComponentType.CPU,
                check_func=check_cpu,
                timeout_seconds=3.0,
                critical=False,
            )
        )

        self.register_checker(
            HealthChecker(
                name="filesystem",
                component_type=ComponentType.FILESYSTEM,
                check_func=check_filesystem,
                timeout_seconds=2.0,
                critical=False,
            )
        )

    async def run_health_checks(
        self, include_non_critical: bool = True
    ) -> SystemHealth:
        """Run all health checks and return system health status."""
        start_time = time.time()

        # Select checkers to run
        checkers_to_run = self.health_checkers
        if not include_non_critical:
            checkers_to_run = [c for c in self.health_checkers if c.critical]

        # Run all checks concurrently
        check_tasks = [checker.execute() for checker in checkers_to_run]
        check_results = await asyncio.gather(*check_tasks)

        # Calculate overall status
        total_checks = len(check_results)
        failed_checks = len(
            [r for r in check_results if r.status == HealthStatus.UNHEALTHY]
        )
        passed_checks = total_checks - failed_checks

        # Determine overall system status
        critical_failures = [
            r
            for r in check_results
            if r.status == HealthStatus.UNHEALTHY
            and any(c.critical for c in checkers_to_run if c.name == r.component)
        ]

        if critical_failures:
            overall_status = HealthStatus.UNHEALTHY
        elif failed_checks > 0:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        # Calculate uptime
        uptime_seconds = (datetime.now() - self.app_start_time).total_seconds()

        # Create system health object
        system_health = SystemHealth(
            status=overall_status,
            checks=check_results,
            uptime_seconds=uptime_seconds,
            timestamp=datetime.now(),
            version="1.0.0",
            environment="production",  # Could be configured
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            response_time_ms=(time.time() - start_time) * 1000,
        )

        # Update cache
        self.last_check_time = datetime.now()
        self.last_check_result = system_health

        # Add to history
        self.check_history.append(system_health)
        if len(self.check_history) > self.max_history_size:
            self.check_history.pop(0)

        return system_health

    def get_cached_health(self, max_age_seconds: int = 30) -> Optional[SystemHealth]:
        """Get cached health check result if recent enough."""
        if (
            self.last_check_result
            and self.last_check_time
            and (datetime.now() - self.last_check_time).total_seconds()
            < max_age_seconds
        ):
            return self.last_check_result
        return None

    def get_health_summary(self) -> Dict[str, Any]:
        """Get summary of health check history."""
        if not self.check_history:
            return {"message": "No health check history available"}

        recent_checks = self.check_history[-10:]  # Last 10 checks
        healthy_count = len(
            [h for h in recent_checks if h.status == HealthStatus.HEALTHY]
        )

        return {
            "total_checks_run": len(self.check_history),
            "recent_healthy_percentage": (healthy_count / len(recent_checks)) * 100,
            "last_check": (
                self.last_check_time.isoformat() if self.last_check_time else None
            ),
            "uptime_hours": (datetime.now() - self.app_start_time).total_seconds()
            / 3600,
        }


def create_health_data_response(system_health: SystemHealth) -> HealthCheckData:
    """Convert SystemHealth to API response format."""
    return HealthCheckData(
        service_status=system_health.status.value,
        database_status=next(
            (c.status.value for c in system_health.checks if c.component == "database"),
            "unknown",
        ),
        orchestrator_status=next(
            (
                c.status.value
                for c in system_health.checks
                if c.component == "orchestrator"
            ),
            "unknown",
        ),
        active_agents=next(
            (
                c.details.get("active_agents", 0)
                for c in system_health.checks
                if c.component == "orchestrator" and c.details
            ),
            0,
        ),
        uptime_seconds=system_health.uptime_seconds,
        version=system_health.version,
        environment=system_health.environment,
    )


__all__ = [
    "HealthStatus",
    "ComponentType",
    "HealthCheckResult",
    "SystemHealth",
    "HealthChecker",
    "HealthMonitor",
    "create_health_data_response",
]
