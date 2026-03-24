"""
Health Check Endpoints

Application health monitoring and readiness probes.
"""

import os
import time
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.shared.infrastructure.config.settings import get_settings
from src.shared.infrastructure.health.checks.database_health_check import (
    DatabaseHealthCheck,
)
from src.shared.infrastructure.health.checks.honcho_health_check import (
    HonchoHealthCheck,
)
from src.shared.infrastructure.health.health_checker import HealthChecker
from src.shared.infrastructure.honcho.client import HonchoClient
from src.shared.infrastructure.persistence import DatabaseConnectionPool

health_router = APIRouter()

# Track application start time
_START_TIME = time.time()

# Global health checker instance
_health_checker: HealthChecker | None = None
# Global connection pool reference
_connection_pool: DatabaseConnectionPool | None = None
# Global Honcho client reference
_honcho_client: HonchoClient | None = None


class HealthStatusResponse(BaseModel):
    """Basic health check response model."""

    status: str
    version: str
    timestamp: str
    environment: str
    uptime_seconds: float


class ComponentStatusResponse(BaseModel):
    """Individual component health status."""

    status: str
    response_time_ms: float
    message: str
    metadata: Dict[str, Any] = {}
    checked_at: str


class DetailedHealthResponse(BaseModel):
    """Detailed health check with component statuses."""

    overall_status: str
    timestamp: str
    components: Dict[str, ComponentStatusResponse]


class SimpleHealthResponse(BaseModel):
    """Simple health response for liveness/readiness."""

    status: str
    reason: str | None = None


def _get_uptime() -> float:
    """Calculate application uptime in seconds."""
    return time.time() - _START_TIME


async def _get_health_checker() -> HealthChecker:
    """Get or initialize the global health checker.

    Returns:
        HealthChecker: The global health checker instance.
    """
    global _health_checker, _connection_pool, _honcho_client

    if _health_checker is None:
        _health_checker = HealthChecker()

        # Register database health check if pool is available
        if _connection_pool is not None:
            _health_checker.register(DatabaseHealthCheck(_connection_pool))

        # Register Honcho health check if client is available
        if _honcho_client is not None:
            _health_checker.register(HonchoHealthCheck(_honcho_client))

    return _health_checker


def set_connection_pool(pool: DatabaseConnectionPool) -> None:
    """Set the database connection pool for health checks.

    Args:
        pool: The database connection pool.
    """
    global _connection_pool
    _connection_pool = pool


def set_honcho_client(client: HonchoClient) -> None:
    """Set the Honcho client for health checks.

    Args:
        client: The Honcho client.
    """
    global _honcho_client
    _honcho_client = client


@health_router.get(
    "/health",
    response_model=DetailedHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Comprehensive health check",
    description="Returns detailed health status including all component checks.",
    responses={
        200: {"description": "Application is healthy or degraded"},
        503: {"description": "Application is unhealthy"},
    },
)
async def health_check() -> JSONResponse:
    """
    Comprehensive health check endpoint.

    Checks all registered components (database, cache, external services)
    and returns detailed status information.

    Returns:
        JSONResponse: Detailed health status with appropriate HTTP status code.
    """
    try:
        checker = await _get_health_checker()
        result = await checker.check_all()

        # Determine HTTP status code based on overall status
        http_status = status.HTTP_200_OK
        if result["overall_status"] == "unhealthy":
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE

        return JSONResponse(content=result, status_code=http_status)
    except Exception as e:
        # If health checker itself fails, return unhealthy
        return JSONResponse(
            content={
                "overall_status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "components": {},
                "error": f"Health check failed: {str(e)}",
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@health_router.get(
    "/health/live",
    response_model=SimpleHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
    description="Kubernetes liveness probe - indicates if the application process is running.",
)
async def liveness_probe() -> SimpleHealthResponse:
    """
    Liveness probe for Kubernetes.

    This endpoint checks if the application process is running.
    It does not check dependencies and should always return 200
    as long as the application is alive.

    Returns:
        SimpleHealthResponse: Liveness status.
    """
    return {"status": "alive"}


@health_router.get(
    "/health/ready",
    response_model=SimpleHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
    description="Kubernetes readiness probe - indicates if the application is ready to serve requests.",
    responses={
        200: {"description": "Application is ready"},
        503: {"description": "Application is not ready"},
    },
)
async def readiness_probe() -> JSONResponse:
    """
    Readiness probe for Kubernetes.

    Checks if critical dependencies (database) are ready to serve requests.
    Returns 503 if critical components are not ready.

    Returns:
        JSONResponse: Readiness status with appropriate HTTP status code.
    """
    try:
        checker = await _get_health_checker()
        result = await checker.check_all()

        # Check critical components (database is always critical)
        critical_components = ["database"]
        missing_critical = []

        for comp_name in critical_components:
            if comp_name in result["components"]:
                comp_status = result["components"][comp_name]["status"]
                if comp_status != "healthy":
                    missing_critical.append(f"{comp_name} ({comp_status})")
            else:
                # Database not registered means not initialized yet
                if comp_name == "database":
                    return JSONResponse(
                        content={
                            "status": "not_ready",
                            "reason": "Database connection pool not initialized",
                        },
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    )

        if missing_critical:
            return JSONResponse(
                content={
                    "status": "not_ready",
                    "reason": f"Critical components not ready: {', '.join(missing_critical)}",
                },
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return {"status": "ready"}

    except Exception as e:
        return JSONResponse(
            content={"status": "not_ready", "reason": str(e)},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@health_router.get(
    "/health/detailed",
    response_model=DetailedHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Detailed health check",
    description="Alias for /health - returns comprehensive health information.",
    responses={
        200: {"description": "Application is healthy or degraded"},
        503: {"description": "Application is unhealthy"},
    },
)
async def detailed_health_check() -> JSONResponse:
    """
    Detailed health check endpoint.

    This is an alias for the /health endpoint that returns the same
    comprehensive health information.

    Returns:
        JSONResponse: Complete health status information.
    """
    return await health_check()


@health_router.get(
    "/version",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Version information",
    description="Returns application version and build information.",
)
async def version() -> Dict[str, str]:
    """
    Get application version information.

    Returns:
        Dictionary with version details.
    """
    settings = get_settings()
    return {
        "version": settings.project_version,
        "name": settings.project_name,
        "python_version": os.sys.version.split()[0],
        "environment": settings.environment.value,
        "build": os.getenv("BUILD_SHA", "unknown"),
    }
