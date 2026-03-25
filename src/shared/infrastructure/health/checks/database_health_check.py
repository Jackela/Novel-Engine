"""
Database Health Check

Health check implementation for database connectivity.
"""

from __future__ import annotations

from typing import Any

from src.shared.infrastructure.persistence import DatabaseConnectionPool


class DatabaseHealthCheck:
    """Health check for database connectivity."""

    def __init__(self, connection_pool: DatabaseConnectionPool | None = None):
        self.connection_pool = connection_pool

    async def check(self) -> dict[str, Any]:
        """Check database health."""
        try:
            if self.connection_pool:
                # Try to get a connection
                async with self.connection_pool.acquire() as conn:
                    # Execute simple query
                    result = await conn.fetchval("SELECT 1")
                    if result == 1:
                        return {
                            "status": "healthy",
                            "message": "Database connection successful",
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "message": "Database query returned unexpected result",
                        }
            else:
                return {
                    "status": "unknown",
                    "message": "Connection pool not configured",
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Database health check failed: {str(e)}",
            }
