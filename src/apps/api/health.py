"""Health and readiness endpoints for Novel Studio."""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.contexts.studio.application.services import StudioStore
from src.contexts.studio.interface.http.dependencies import StudioStoreDependency

health_router = APIRouter()


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


def _database_component(store: StudioStore) -> ComponentStatusResponse:
    repository = store.repository
    try:
        healthy = repository.health_check()
    except RuntimeError as exc:
        return ComponentStatusResponse(status="unhealthy", error=str(exc))

    if healthy:
        return ComponentStatusResponse(status="healthy", message="SQLite ready")
    return ComponentStatusResponse(
        status="unhealthy", error="database health check failed"
    )


@health_router.get("/health", response_model=DetailedHealthResponse)
async def health_check(store: StudioStoreDependency) -> JSONResponse:
    """Return the detailed runtime health of the application."""
    database = _database_component(store)
    return JSONResponse(
        content={
            "overall_status": database.status,
            "timestamp": _timestamp(),
            "components": {"database": database.model_dump()},
        },
        status_code=status.HTTP_200_OK,
    )


@health_router.get("/health/live", response_model=SimpleHealthResponse)
async def liveness_probe() -> SimpleHealthResponse:
    """Liveness probe used by orchestrators such as Kubernetes."""
    return SimpleHealthResponse(status="alive")


@health_router.get("/health/ready", response_model=SimpleHealthResponse)
async def readiness_probe(store: StudioStoreDependency) -> JSONResponse:
    """Return whether the authoritative SQLite database is available."""
    component = _database_component(store)
    if component.status != "healthy":
        return JSONResponse(
            content={"status": "not_ready", "reason": component.error},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return JSONResponse(content={"status": "ready"}, status_code=status.HTTP_200_OK)


@health_router.get("/version", response_model=dict[str, str])
async def version(request: Request) -> dict[str, str]:
    """Return application version metadata."""
    settings = request.app.state.settings
    return {
        "version": settings.project_version,
        "name": settings.project_name,
        "python_version": sys.version.split()[0],
        "environment": settings.environment.value,
        "build": os.getenv("BUILD_SHA", "unknown"),
    }


__all__ = ["health_router"]
