"""
Health Checker

Centralized health checking coordinator with comprehensive error handling,
concurrent execution, and structured logging.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class HealthStatus:
    """Health status result with structured data.

    Attributes:
        status: Health status string (healthy, unhealthy, timeout, error, unknown)
        message: Human-readable status message
        error: Error message if status is error or timeout
        details: Additional details about the health check
        response_time_ms: Response time in milliseconds
    """

    status: str = "unknown"
    message: str = ""
    error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    response_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert HealthStatus to dictionary for serialization."""
        result = {
            "status": self.status,
            "message": self.message,
            "response_time_ms": self.response_time_ms,
        }
        if self.error:
            result["error"] = self.error
        if self.details:
            result["details"] = self.details
        return result


class HealthChecker:
    """Centralized health check coordinator with concurrency support.

    This class manages multiple health checks and runs them concurrently
    with timeout protection and comprehensive error handling.

    Example:
        >>> checker = HealthChecker()
        >>> checker.register("database", database_health_check)
        >>> checker.register("cache", cache_health_check)
        >>> results = await checker.check_all()
    """

    def __init__(self, default_timeout: float = 5.0):
        """Initialize the health checker.

        Args:
            default_timeout: Default timeout in seconds for each health check.
        """
        self._checks: dict[str, Callable[[], Awaitable[HealthStatus]]] = {}
        self._default_timeout = default_timeout
        self._logger = structlog.get_logger(__name__)

    def register(self, name: str, check: Callable[[], Awaitable[HealthStatus]]) -> None:
        """Register a health check.

        Args:
            name: Unique name for the health check.
            check: Async callable that returns a HealthStatus.

        Example:
            >>> async def db_check() -> HealthStatus:
            ...     return HealthStatus(status="healthy", message="DB OK")
            >>> checker.register("database", db_check)
        """
        self._checks[name] = check
        self._logger.debug("Health check registered", check_name=name)

    def unregister(self, name: str) -> None:
        """Unregister a health check.

        Args:
            name: Name of the health check to remove.
        """
        if name in self._checks:
            del self._checks[name]
            self._logger.debug("Health check unregistered", check_name=name)

    @property
    def checks(self) -> dict[str, Callable[[], Awaitable[HealthStatus]]]:
        """Get registered health checks."""
        return self._checks.copy()

    async def check_all(self) -> dict[str, Any]:
        """Run all health checks concurrently.

        Returns:
            Dictionary with overall status, timestamp, and component results.

        Example:
            >>> results = await checker.check_all()
            >>> print(results["overall_status"])  # "healthy" or "degraded" or "unhealthy"
        """
        import time
        from datetime import datetime

        if not self._checks:
            return {
                "overall_status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "components": {},
            }

        start_time = time.time()

        # Run all checks concurrently with gather
        check_items = list(self._checks.items())
        results = await asyncio.gather(
            *[self._run_check(name, check) for name, check in check_items],
            return_exceptions=True,
        )

        # Process results
        components = {}
        overall_status = "healthy"

        for (name, _), result in zip(check_items, results):
            if isinstance(result, Exception):
                # Handle exceptions that weren't caught in _run_check
                components[name] = HealthStatus(
                    status="error",
                    message="Health check failed with exception",
                    error=str(result),
                ).to_dict()
                overall_status = "unhealthy"
                self._logger.error(
                    "Health check raised unhandled exception",
                    check_name=name,
                    error=str(result),
                    error_type=type(result).__name__,
                )
            else:
                components[name] = result.to_dict()
                # Determine overall status based on individual status
                if result.status in ("unhealthy", "error"):
                    overall_status = "unhealthy"
                elif (
                    result.status in ("timeout", "degraded")
                    and overall_status == "healthy"
                ):
                    overall_status = "degraded"

        total_time_ms = (time.time() - start_time) * 1000

        self._logger.debug(
            "Health checks completed",
            overall_status=overall_status,
            check_count=len(self._checks),
            total_time_ms=total_time_ms,
        )

        return {
            "overall_status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "components": components,
        }

    async def _run_check(
        self, name: str, check: Callable[[], Awaitable[HealthStatus]]
    ) -> HealthStatus:
        """Run single check with timeout and error handling.

        Args:
            name: Name of the health check.
            check: Async callable that returns a HealthStatus.

        Returns:
            HealthStatus result (never raises).
        """
        import time

        start_time = time.time()

        try:
            # Run check with timeout
            result = await asyncio.wait_for(check(), timeout=self._default_timeout)
            result.response_time_ms = (time.time() - start_time) * 1000

            self._logger.debug(
                "Health check completed",
                check_name=name,
                status=result.status,
                response_time_ms=result.response_time_ms,
            )

            return result

        except asyncio.TimeoutError:
            response_time_ms = (time.time() - start_time) * 1000
            self._logger.warning(
                "Health check timed out",
                check_name=name,
                timeout_seconds=self._default_timeout,
                response_time_ms=response_time_ms,
            )
            return HealthStatus(
                status="timeout",
                message=f"Health check '{name}' timed out after {self._default_timeout}s",
                error=f"Check {name} timed out",
                response_time_ms=response_time_ms,
            )

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            self._logger.error(
                "Health check failed",
                check_name=name,
                error=str(e),
                error_type=type(e).__name__,
                response_time_ms=response_time_ms,
            )
            return HealthStatus(
                status="error",
                message=f"Health check '{name}' failed",
                error=str(e),
                response_time_ms=response_time_ms,
            )

    async def check_single(self, name: str) -> HealthStatus | None:
        """Run a single health check by name.

        Args:
            name: Name of the registered health check.

        Returns:
            HealthStatus if check exists, None otherwise.
        """
        if name not in self._checks:
            self._logger.warning("Health check not found", check_name=name)
            return None

        return await self._run_check(name, self._checks[name])

    def is_healthy(self, results: dict[str, Any]) -> bool:
        """Determine if all checks are healthy.

        Args:
            results: Results dictionary from check_all().

        Returns:
            True if overall status is healthy, False otherwise.
        """
        return results.get("overall_status") == "healthy"

    def clear(self) -> None:
        """Clear all registered health checks."""
        self._checks.clear()
        self._logger.debug("All health checks cleared")
