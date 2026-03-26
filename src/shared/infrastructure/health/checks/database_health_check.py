"""
Database Health Check

Health check implementation for database connectivity using the unified HealthStatus model.
"""

from __future__ import annotations

from src.shared.infrastructure.health.health_checker import HealthStatus
from src.shared.infrastructure.persistence import DatabaseConnectionPool


class DatabaseHealthCheck:
    """Health check for database connectivity."""

    def __init__(self, connection_pool: DatabaseConnectionPool | None = None):
        self.connection_pool = connection_pool

    async def check(self) -> HealthStatus:
        """Check database health and return standardized HealthStatus.

        Returns:
            HealthStatus with status, message, and any error details.
        """
        try:
            if self.connection_pool:
                # Try to get a connection
                async with self.connection_pool.acquire() as conn:
                    # Execute simple query
                    result = await conn.fetchval("SELECT 1")
                    if result == 1:
                        return HealthStatus(
                            status="healthy",
                            message="Database connection successful",
                        )
                    else:
                        return HealthStatus(
                            status="unhealthy",
                            message="Database query returned unexpected result",
                            details={"expected": 1, "actual": result},
                        )
            else:
                return HealthStatus(
                    status="unknown",
                    message="Connection pool not configured",
                )
        except Exception as e:
            return HealthStatus(
                status="unhealthy",
                message=f"Database health check failed: {str(e)}",
                error=str(e),
                details={"error_type": type(e).__name__},
            )
