"""
Honcho Health Check

Health check implementation for Honcho service connectivity using the unified HealthStatus model.
"""

from __future__ import annotations

from src.shared.infrastructure.health.health_checker import HealthStatus
from src.shared.infrastructure.honcho.client import HonchoClient


class HonchoHealthCheck:
    """Health check for Honcho service connectivity."""

    def __init__(self, client: HonchoClient | None = None):
        self.client = client

    async def check(self) -> HealthStatus:
        """Check Honcho service health and return standardized HealthStatus.

        Returns:
            HealthStatus with status, message, and any error details.
        """
        try:
            if self.client:
                # Try to check if client is healthy
                is_healthy = await self.client.health_check()
                if is_healthy:
                    return HealthStatus(
                        status="healthy",
                        message="Honcho service connection successful",
                    )
                else:
                    return HealthStatus(
                        status="unhealthy",
                        message="Honcho service health check failed",
                    )
            else:
                return HealthStatus(
                    status="unknown",
                    message="Honcho client not configured",
                )
        except Exception as e:
            return HealthStatus(
                status="unhealthy",
                message=f"Honcho health check failed: {str(e)}",
                error=str(e),
                details={"error_type": type(e).__name__},
            )
