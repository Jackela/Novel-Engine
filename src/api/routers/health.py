from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Dict

from config_loader import get_config
from fastapi import APIRouter, HTTPException, Request

from src.api.schemas import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


def _uptime_seconds(request: Request) -> float:
    started_at = getattr(request.app.state, "api_start_time", None)
    if not started_at:
        return 0.0
    return (datetime.now(UTC) - started_at).total_seconds()


@router.get("/", response_model=HealthResponse)
async def root() -> Dict[str, Any]:
    logger.info("Root endpoint accessed for health check")
    response_data = {
        "message": "StoryForge AI Interactive Story Engine is running!",
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat(),
    }
    logger.debug("Root endpoint response: %s", response_data)
    return response_data


@router.get("/health")
async def health_check(request: Request) -> Dict[str, Any]:
    import datetime as datetime_mod

    try:
        import logging as logging_mod

        logging_mod.Formatter("%(name)s - %(levelname)s - %(message)s")
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

    health_data = {
        "status": status,
        "api": "running",
        "timestamp": datetime_mod.datetime.now().isoformat(),
        "version": "1.0.0",
        "config": config_status,
        "uptime": _uptime_seconds(request),
    }

    logger.debug("Health check response: %s", health_data)
    return health_data
