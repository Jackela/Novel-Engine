"""Health check implementation for the optional Honcho runtime."""

from __future__ import annotations

from src.shared.infrastructure.health.health_checker import HealthStatus
from src.shared.infrastructure.honcho.client import HonchoClient


class HonchoHealthCheck:
    """Probe the optional Honcho client without making startup depend on it."""

    def __init__(self, client: HonchoClient | None = None) -> None:
        self.client = client

    async def check(self) -> HealthStatus:
        """Return a health status for the configured Honcho client."""
        if self.client is None:
            return HealthStatus(
                status="unknown",
                message="Honcho client not configured",
            )

        try:
            health_check = getattr(self.client, "health_check", None)
            if callable(health_check):
                is_healthy = await health_check()
                return HealthStatus(
                    status="healthy" if is_healthy else "unhealthy",
                    message=(
                        "Honcho service connection successful"
                        if is_healthy
                        else "Honcho service health check failed"
                    ),
                )

            get_client = getattr(self.client, "_get_client", None)
            if callable(get_client):
                await get_client()
                return HealthStatus(
                    status="healthy",
                    message="Honcho client initialized successfully",
                )

            return HealthStatus(
                status="unknown",
                message="Honcho client does not expose a health probe",
            )
        except Exception as exc:
            return HealthStatus(
                status="unhealthy",
                message=f"Honcho health check failed: {exc}",
                error=str(exc),
                details={"error_type": type(exc).__name__},
            )
