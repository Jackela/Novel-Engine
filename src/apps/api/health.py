"""Health and readiness endpoints for the canonical API."""

# mypy: disable-error-code=misc

from __future__ import annotations

import logging
import os
import sys
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.shared.infrastructure.config.settings import get_settings
from src.shared.infrastructure.health.checks.database_health_check import (
    DatabaseHealthCheck,
)
from src.shared.infrastructure.health.health_checker import HealthChecker

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from src.shared.infrastructure.persistence import DatabaseConnectionPool
else:  # pragma: no cover - exercised when asyncpg is absent
    DatabaseConnectionPool = Any  # type: ignore[assignment]

honcho_health_check_module: Any | None = None
try:  # pragma: no cover - optional runtime integration
    from src.shared.infrastructure.health.checks import (
        honcho_health_check as _honcho_health_check_module,
    )

    HONCHO_RUNTIME_AVAILABLE = True
    honcho_health_check_module = _honcho_health_check_module
except Exception:  # pragma: no cover - depends on optional package availability
    HONCHO_RUNTIME_AVAILABLE = False

health_router = APIRouter()

_START_TIME = time.time()
_health_checker: HealthChecker | None = None
_connection_pool: DatabaseConnectionPool | None = None
_honcho_client: Any | None = None


class ComponentStatusResponse(BaseModel):
    """Serialized status of an individual runtime dependency."""

    status: str
    response_time_ms: float = 0.0
    message: str = ""
    error: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class DetailedHealthResponse(BaseModel):
    """Detailed health payload returned by `/health`."""

    overall_status: str
    timestamp: str
    components: dict[str, ComponentStatusResponse]


class SimpleHealthResponse(BaseModel):
    """Simple liveness and readiness response."""

    status: str
    reason: str | None = None


def _timestamp() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(UTC).isoformat()


async def _get_health_checker() -> HealthChecker:
    """Build or return the cached health checker."""
    global _health_checker

    if _health_checker is None:
        _health_checker = HealthChecker()
        if _connection_pool is not None:
            _health_checker.register(
                "database",
                DatabaseHealthCheck(_connection_pool).check,
            )
        if (
            _honcho_client is not None
            and HONCHO_RUNTIME_AVAILABLE
            and honcho_health_check_module is not None
        ):
            _health_checker.register(
                "honcho",
                honcho_health_check_module.HonchoHealthCheck(_honcho_client).check,
            )

    return _health_checker


def set_connection_pool(pool: DatabaseConnectionPool) -> None:
    """Expose the shared connection pool to health checks."""
    global _connection_pool, _health_checker
    _connection_pool = pool
    _health_checker = None


def set_honcho_client(client: Any) -> None:
    """Expose the optional Honcho client to health checks."""
    global _honcho_client, _health_checker
    _honcho_client = client
    _health_checker = None


def reset_health_state() -> None:
    """Reset cached health state for tests and reconfiguration."""
    global _health_checker, _connection_pool, _honcho_client
    _health_checker = None
    _connection_pool = None
    _honcho_client = None


@health_router.get("/health", response_model=DetailedHealthResponse)
async def health_check() -> JSONResponse:
    """Return the detailed runtime health of the application."""
    try:
        checker = await _get_health_checker()
        result = await checker.check_all()
        overall_status = result.get("overall_status", "healthy")
        return JSONResponse(
            content={
                "overall_status": overall_status,
                "timestamp": result.get("timestamp", _timestamp()),
                "components": result.get("components", {}),
            },
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
                if overall_status == "unhealthy"
                else status.HTTP_200_OK
            ),
        )
    except Exception:
        logger.exception("Health check failed")
        return JSONResponse(
            content={
                "overall_status": "unhealthy",
                "timestamp": _timestamp(),
                "components": {},
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@health_router.get("/health/live", response_model=SimpleHealthResponse)
async def liveness_probe() -> SimpleHealthResponse:
    """Liveness probe used by orchestrators such as Kubernetes."""
    return SimpleHealthResponse(status="alive")


@health_router.get("/health/ready", response_model=SimpleHealthResponse)
async def readiness_probe() -> JSONResponse:
    """Readiness probe that prefers database health when configured."""
    try:
        checker = await _get_health_checker()
        if "database" not in checker.checks:
            return JSONResponse(content={"status": "ready"}, status_code=status.HTTP_200_OK)

        result = await checker.check_single("database")
        if result is None or result.status != "healthy":
            reason = (
                "Database not initialized"
                if result is None
                else f"Database ({result.status})"
            )
            return JSONResponse(
                content={"status": "not_ready", "reason": reason},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return JSONResponse(content={"status": "ready"}, status_code=status.HTTP_200_OK)
    except Exception:
        logger.exception("Readiness probe failed")
        return JSONResponse(
            content={"status": "not_ready", "reason": "Readiness check failed"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@health_router.get("/version", response_model=dict[str, str])
async def version() -> dict[str, str]:
    """Return application version metadata."""
    settings = get_settings()
    return {
        "version": settings.project_version,
        "name": settings.project_name,
        "python_version": sys.version.split()[0],
        "environment": settings.environment.value,
        "build": os.getenv("BUILD_SHA", "unknown"),
    }


__all__ = [
    "HONCHO_RUNTIME_AVAILABLE",
    "health_router",
    "reset_health_state",
    "set_connection_pool",
    "set_honcho_client",
    "_get_health_checker",
]
