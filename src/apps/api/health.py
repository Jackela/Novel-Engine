"""
Health Check Endpoints

Application health monitoring and readiness probes.
"""

import time
import os
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, status
from pydantic import BaseModel

health_router = APIRouter()


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str
    version: str
    timestamp: str
    environment: str
    uptime_seconds: float


class ComponentStatus(BaseModel):
    """Individual component health status."""

    name: str
    status: str
    healthy: bool
    response_time_ms: float
    details: Dict[str, Any] = {}


class DetailedHealthStatus(BaseModel):
    """Detailed health check with component statuses."""

    status: str
    version: str
    timestamp: str
    environment: str
    uptime_seconds: float
    components: list[ComponentStatus]


# Track application start time
_START_TIME = time.time()


def _get_uptime() -> float:
    """Calculate application uptime in seconds."""
    return time.time() - _START_TIME


async def _check_database() -> ComponentStatus:
    """Check database connectivity."""
    start = time.perf_counter()

    try:
        # TODO: Implement actual database health check
        # from src.infrastructure.database import check_connection
        # await check_connection()

        return ComponentStatus(
            name="database",
            status="healthy",
            healthy=True,
            response_time_ms=(time.perf_counter() - start) * 1000,
            details={"type": "postgresql"},
        )
    except Exception as exc:
        return ComponentStatus(
            name="database",
            status="unhealthy",
            healthy=False,
            response_time_ms=(time.perf_counter() - start) * 1000,
            details={"error": str(exc)},
        )


async def _check_cache() -> ComponentStatus:
    """Check cache connectivity."""
    start = time.perf_counter()

    try:
        # TODO: Implement actual cache health check
        # from src.infrastructure.cache import check_connection
        # await check_connection()

        return ComponentStatus(
            name="cache",
            status="healthy",
            healthy=True,
            response_time_ms=(time.perf_counter() - start) * 1000,
            details={"type": "redis"},
        )
    except Exception as exc:
        return ComponentStatus(
            name="cache",
            status="unhealthy",
            healthy=False,
            response_time_ms=(time.perf_counter() - start) * 1000,
            details={"error": str(exc)},
        )


@health_router.get(
    "/health",
    response_model=HealthStatus,
    status_code=status.HTTP_200_OK,
    summary="Basic health check",
    description="Returns basic health status of the application. Suitable for load balancer health checks.",
    responses={
        200: {"description": "Application is healthy"},
        503: {"description": "Application is unhealthy"},
    },
)
async def health_check() -> HealthStatus:
    """
    Basic health check endpoint.

    Returns:
        HealthStatus: Basic health information including status and version.
    """
    return HealthStatus(
        status="healthy",
        version="2.0.0",
        timestamp=datetime.utcnow().isoformat(),
        environment=os.getenv("ENVIRONMENT", "development"),
        uptime_seconds=round(_get_uptime(), 2),
    )


@health_router.get(
    "/health/live",
    response_model=HealthStatus,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
    description="Kubernetes liveness probe - indicates if the application is running.",
)
async def liveness_probe() -> HealthStatus:
    """
    Liveness probe for Kubernetes.

    Returns:
        HealthStatus: Liveness status. Returns 200 if application is running.
    """
    return await health_check()


@health_router.get(
    "/health/ready",
    response_model=DetailedHealthStatus,
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
    description="Kubernetes readiness probe - indicates if the application is ready to serve requests.",
    responses={
        200: {"description": "Application is ready"},
        503: {"description": "Application is not ready"},
    },
)
async def readiness_probe() -> DetailedHealthStatus:
    """
    Readiness probe with component checks.

    Checks database, cache, and other dependencies.

    Returns:
        DetailedHealthStatus: Detailed health information with component statuses.
    """
    # Check all components
    components = [
        await _check_database(),
        await _check_cache(),
    ]

    # Overall status is healthy only if all components are healthy
    all_healthy = all(comp.healthy for comp in components)

    return DetailedHealthStatus(
        status="healthy" if all_healthy else "degraded",
        version="2.0.0",
        timestamp=datetime.utcnow().isoformat(),
        environment=os.getenv("ENVIRONMENT", "development"),
        uptime_seconds=round(_get_uptime(), 2),
        components=components,
    )


@health_router.get(
    "/health/detailed",
    response_model=DetailedHealthStatus,
    status_code=status.HTTP_200_OK,
    summary="Detailed health check",
    description="Returns detailed health information including all component statuses.",
)
async def detailed_health_check() -> DetailedHealthStatus:
    """
    Detailed health check with all components.

    Same as readiness probe, returns comprehensive health information.

    Returns:
        DetailedHealthStatus: Complete health status information.
    """
    return await readiness_probe()


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
    return {
        "version": "2.0.0",
        "name": "Novel Engine API",
        "python_version": os.sys.version.split()[0],
        "environment": os.getenv("ENVIRONMENT", "development"),
        "build": os.getenv("BUILD_SHA", "unknown"),
    }
