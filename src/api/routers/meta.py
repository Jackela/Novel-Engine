"""Meta Router - System status and policy information."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Request

from src.api.schemas import PolicyInfoResponse, SystemStatusResponse

router = APIRouter(tags=["Meta"])


def _uptime_seconds(request: Request) -> float:
    started_at = getattr(request.app.state, "api_start_time", None)
    if not started_at:
        return 0.0
    return (datetime.now(UTC) - started_at).total_seconds()


@router.get("/meta/system-status", response_model=SystemStatusResponse)
async def system_status(request: Request) -> SystemStatusResponse:
    """Get system status information."""
    return SystemStatusResponse(
        status="operational",
        uptime=_uptime_seconds(request),
        version="1.0.0",
        components={
            "api": "online",
            "simulation": "idle",
            "cache": "available",
        },
    )


@router.get("/meta/policy", response_model=PolicyInfoResponse)
async def policy_info() -> PolicyInfoResponse:
    """Get policy and compliance information."""
    return PolicyInfoResponse(
        brand_status="Generic Sci-Fi",
        compliance={
            "intellectual_property": "debranded",
            "content_filters": "enabled",
        },
        last_reviewed=datetime.now(UTC).isoformat(),
    )
