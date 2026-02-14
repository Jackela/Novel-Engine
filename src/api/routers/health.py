"""Health Router - Application health and status endpoints."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from src.api.schemas import HealthCheckResponse, HealthResponse
from src.core.config.config_loader import get_config

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


def _uptime_seconds(request: Request) -> float:
    started_at = getattr(request.app.state, "api_start_time", None)
    if not started_at:
        return 0.0
    return (datetime.now(UTC) - started_at).total_seconds()


@router.get("/", response_model=HealthResponse)
async def root() -> HealthResponse:
    """Root endpoint for basic health check."""
    logger.info("Root endpoint accessed for health check")
    return HealthResponse(
        message="StoryForge AI Interactive Story Engine is running!",
        status="ok",
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(request: Request) -> HealthCheckResponse:
    """Detailed health check endpoint."""
    try:
        get_config()
        config_status = "loaded"
        status = "healthy"
        logger.info("Health check endpoint accessed")
    except Exception as exc:
        logger.error("Health check configuration error: %s", exc)
        if "Severe system error" in str(exc):
            raise HTTPException(status_code=500, detail=str(exc))
        config_status = "error"
        status = "degraded"

    return HealthCheckResponse(
        status=status,
        api="running",
        timestamp=datetime.now(UTC).isoformat(),
        version="1.0.0",
        config=config_status,
        uptime=_uptime_seconds(request),
    )


@router.get("/health/chromadb")
async def chromadb_health_check() -> dict[str, Any]:
    """
    ChromaDB vector store health check endpoint.

    Warzone 4: AI Brain - BRAIN-001
    Returns the status of the ChromaDB vector database connection.
    """
    try:
        from src.contexts.knowledge.infrastructure.adapters.chromadb_vector_store import (
            ChromaDBVectorStore,
        )

        store = ChromaDBVectorStore()
        is_healthy = await store.health_check()

        from pathlib import Path

        persist_dir = Path(store._persist_dir)
        collection_count = 0
        if persist_dir.exists():
            collection_count = len([p for p in persist_dir.iterdir() if p.is_dir()])

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "message": (
                "ChromaDB vector store is operational"
                if is_healthy
                else "ChromaDB connection failed"
            ),
            "details": {
                "persist_dir": str(persist_dir.absolute()),
                "collection_count": collection_count,
                "embedding_dimension": store._embedding_dimension,
            },
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except ImportError:
        return {
            "status": "not_installed",
            "message": "ChromaDB is not installed. Vector features are disabled.",
            "details": {
                "install_command": "pip install chromadb>=0.5.0",
            },
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception:
        logger.exception("ChromaDB health check error")
        return {
            "status": "error",
            "message": "ChromaDB health check failed",
            "timestamp": datetime.now(UTC).isoformat(),
        }
