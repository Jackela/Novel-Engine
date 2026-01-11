from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict

from fastapi import APIRouter, Request

router = APIRouter(tags=["Meta"])


def _uptime_seconds(request: Request) -> float:
    started_at = getattr(request.app.state, "api_start_time", None)
    if not started_at:
        return 0.0
    return (datetime.now(UTC) - started_at).total_seconds()


@router.get("/meta/system-status")
async def system_status(request: Request) -> Dict[str, Any]:
    return {
        "status": "operational",
        "uptime": _uptime_seconds(request),
        "version": "1.0.0",
        "components": {
            "api": "online",
            "simulation": "idle",
            "cache": "available",
        },
    }


@router.get("/meta/policy")
async def policy_info() -> Dict[str, Any]:
    return {
        "brand_status": "Generic Sci-Fi",
        "compliance": {
            "intellectual_property": "debranded",
            "content_filters": "enabled",
        },
        "last_reviewed": datetime.now(UTC).isoformat(),
    }
