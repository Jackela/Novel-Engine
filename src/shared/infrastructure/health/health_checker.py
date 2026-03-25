"""
Health Checker

Centralized health checking coordinator.
"""

from __future__ import annotations

from typing import Any


class HealthChecker:
    """Coordinates health checks for all services."""

    def __init__(self) -> None:
        self.checks: dict[str, Any] = {}

    def register(self, check: Any, name: str | None = None) -> None:
        """Register a health check."""
        check_name = name or check.__class__.__name__.lower().replace("healthcheck", "")
        self.checks[check_name] = check

    def register_check(self, name: str, check: Any) -> None:
        """Register a health check with explicit name."""
        self.checks[name] = check

    async def check_all(self) -> dict[str, Any]:
        """Run all health checks."""
        from datetime import datetime

        results = {}
        overall_status = "healthy"

        for name, check in self.checks.items():
            if hasattr(check, "check"):
                check_result = await check.check()
                results[name] = check_result
                if (
                    isinstance(check_result, dict)
                    and check_result.get("status") != "healthy"
                ):
                    overall_status = (
                        "degraded" if overall_status == "healthy" else "unhealthy"
                    )
            else:
                results[name] = {
                    "status": "unknown",
                    "message": f"Check {name} has no check method",
                }
                overall_status = "degraded"

        return {
            "overall_status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "components": results,
        }

    def is_healthy(self, results: dict[str, Any]) -> bool:
        """Determine if all checks are healthy."""
        for result in results.values():
            if isinstance(result, dict) and result.get("status") != "healthy":
                return False
        return True
