"""
Honcho Health Check

Health check implementation for Honcho service connectivity.
"""

from __future__ import annotations

from typing import Any

from src.shared.infrastructure.honcho.client import HonchoClient


class HonchoHealthCheck:
    """Health check for Honcho service connectivity."""

    def __init__(self, client: HonchoClient | None = None):
        self.client = client

    async def check(self) -> dict[str, Any]:
        """Check Honcho service health."""
        try:
            if self.client:
                # Try to check if client is healthy
                is_healthy = await self.client.health_check()
                if is_healthy:
                    return {
                        "status": "healthy",
                        "message": "Honcho service connection successful",
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "message": "Honcho service health check failed",
                    }
            else:
                return {
                    "status": "unknown",
                    "message": "Honcho client not configured",
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Honcho health check failed: {str(e)}",
            }
