"""Health Router - Application health and status endpoints."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.api.schemas import HealthCheckResponse, HealthResponse
from src.core.config.config_loader import get_config

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


# ---------------------------------------------------------------------------
# Health Check Helper Functions
# ---------------------------------------------------------------------------


async def check_chroma() -> tuple[bool, str]:
    """Check ChromaDB vector store connectivity and health.

    Returns:
        Tuple of (is_healthy, status_message)
    """
    try:
        from src.contexts.knowledge.infrastructure.adapters.chromadb_vector_store import (
            ChromaDBVectorStore,
        )

        store = ChromaDBVectorStore()
        is_healthy = await store.health_check()

        if is_healthy:
            return (True, "ok")

        # Check if this is a "not installed" situation by looking at persist dir
        from pathlib import Path

        persist_dir = Path(store._persist_dir)
        if not persist_dir.exists():
            return (True, "not_configured")

        return (False, "unhealthy")
    except ImportError:
        # ChromaDB not installed - service can operate without it
        return (True, "not_configured")
    except Exception as exc:
        error_msg = str(exc)
        # Treat "not installed" errors as not configured rather than unhealthy
        if "not installed" in error_msg.lower() or "not found" in error_msg.lower():
            return (True, "not_configured")
        logger.warning("ChromaDB health check failed: %s", exc)
        return (False, error_msg)


async def check_postgres() -> tuple[bool, str]:
    """Check PostgreSQL connection pool health.

    Verifies that the PostgreSQL database is reachable and the connection
    pool is functioning correctly.

    Returns:
        Tuple of (is_healthy, status_message)
    """
    try:
        from src.infrastructure.postgresql_manager import (
            PostgreSQLManager,
            create_postgresql_config_from_env,
        )

        # Check if PostgreSQL is configured (has non-default host or password)
        config = create_postgresql_config_from_env()

        # Quick check: if using default localhost with no password, skip
        if config.host == "localhost" and not config.password:
            # Check if POSTGRES_HOST was explicitly set
            if not os.getenv("POSTGRES_HOST"):
                return (True, "not_configured")

        # Create a temporary manager for health check
        manager = PostgreSQLManager(config)
        await manager.initialize()

        try:
            result = await manager.health_check()
            if result.get("healthy", False):
                return (True, "ok")
            else:
                return (False, result.get("error", "unhealthy"))
        finally:
            await manager.close()

    except ImportError:
        return (True, "not_installed")
    except Exception as exc:
        logger.warning("PostgreSQL health check failed: %s", exc)
        return (False, str(exc))


async def check_redis() -> tuple[bool, str]:
    """Check Redis connectivity with ping.

    Verifies that the Redis server is reachable and responding to ping
    commands.

    Returns:
        Tuple of (is_healthy, status_message)
    """
    try:
        from src.infrastructure.redis_manager import (
            RedisManager,
            create_redis_config_from_env,
        )

        # Check if Redis is configured
        config = create_redis_config_from_env()

        # Quick check: if using default localhost, verify it was explicitly set
        if config.host == "localhost" and not os.getenv("REDIS_HOST"):
            return (True, "not_configured")

        # Create a temporary manager for health check
        manager = RedisManager(config)
        await manager.initialize()

        try:
            result = await manager.health_check()
            if result.get("healthy", False):
                return (True, "ok")
            else:
                return (False, result.get("error", "unhealthy"))
        finally:
            await manager.close()

    except ImportError:
        return (True, "not_installed")
    except Exception as exc:
        logger.warning("Redis health check failed: %s", exc)
        return (False, str(exc))


async def check_llm() -> tuple[bool, str]:
    """Check LLM API key validity and service reachability.

    Validates that an LLM API key is configured. Currently supports:
    - Google Gemini (GEMINI_API_KEY)
    - OpenAI (OPENAI_API_KEY)
    - Anthropic Claude (ANTHROPIC_API_KEY)

    Returns:
        Tuple of (is_healthy, status_message)
    """
    try:
        # Check for configured LLM API keys
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        openai_key = os.getenv("OPENAI_API_KEY", "")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

        configured_providers = []

        if gemini_key:
            configured_providers.append("gemini")
        if openai_key:
            configured_providers.append("openai")
        if anthropic_key:
            configured_providers.append("anthropic")

        if not configured_providers:
            return (True, "not_configured")

        # At least one LLM provider is configured
        providers_str = ", ".join(configured_providers)
        return (True, f"ok (providers: {providers_str})")

    except Exception as exc:
        logger.warning("LLM health check failed: %s", exc)
        return (False, str(exc))


class LivenessResponse(BaseModel):
    """Liveness probe response."""

    status: str


def _uptime_seconds(request: Request) -> float:
    started_at = getattr(request.app.state, "api_start_time", None)
    if not started_at:
        return 0.0
    return (datetime.now(UTC) - started_at).total_seconds()


@router.get("/health/live", response_model=LivenessResponse)
async def live() -> LivenessResponse:
    """Liveness probe endpoint for Kubernetes/container orchestration.

    Returns a simple status check to indicate the application is running.
    This endpoint should respond in < 10ms and have no external dependencies.
    """
    return LivenessResponse(status="ok")


class CheckDetail(BaseModel):
    """Individual health check result with status and message."""

    status: str
    message: str


class ReadinessResponseV2(BaseModel):
    """Enhanced readiness probe response with detailed check information."""

    status: str
    checks: dict[str, CheckDetail]


@router.get("/health/ready", response_model=ReadinessResponseV2)
async def ready() -> ReadinessResponseV2:
    """Readiness probe endpoint for Kubernetes/container orchestration.

    Checks if the application is ready to receive traffic by verifying
    critical dependencies: ChromaDB, PostgreSQL, Redis, and LLM services.

    Returns 503 Service Unavailable if any critical dependency is unhealthy.
    Services marked as "not_configured" or "not_installed" are treated as
    healthy since the application can operate without them.
    """
    checks: dict[str, CheckDetail] = {}
    all_healthy = True

    # Run all health checks
    health_checks = {
        "chromadb": await check_chroma(),
        "postgres": await check_postgres(),
        "redis": await check_redis(),
        "llm": await check_llm(),
    }

    for name, (is_healthy, message) in health_checks.items():
        checks[name] = CheckDetail(
            status="ok" if is_healthy else "error",
            message=message,
        )

        # Only treat actual errors as unhealthy, not missing/optional services
        if not is_healthy and message not in ("not_configured", "not_installed"):
            all_healthy = False

    if not all_healthy:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "checks": {
                    k: {"status": v.status, "message": v.message}
                    for k, v in checks.items()
                },
            },
        )

    return ReadinessResponseV2(
        status="healthy" if all_healthy else "unhealthy",
        checks=checks,
    )


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
