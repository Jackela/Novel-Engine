"""Orchestration Router - Thin HTTP layer with Pydantic models."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.schemas import (
    NarrativeResponse,
    OrchestrationStartRequest,
    OrchestrationStartResponse,
    OrchestrationStatusResponse,
    OrchestrationStopResponse,
)
from src.api.services.orchestration_service import OrchestrationService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Orchestration"])


def get_orchestration_service(request: Request) -> OrchestrationService:
    """Dependency injection for orchestration service."""
    api_service = getattr(request.app.state, "api_service", None)
    return OrchestrationService(api_service)


@router.get("/api/orchestration/status", response_model=OrchestrationStatusResponse)
async def get_orchestration_status(
    service: OrchestrationService = Depends(get_orchestration_service),
) -> OrchestrationStatusResponse:
    """Get current orchestration status."""
    return await service.get_status()


@router.post("/api/orchestration/start", response_model=OrchestrationStartResponse)
async def start_orchestration(
    payload: Optional[OrchestrationStartRequest] = None,
    service: OrchestrationService = Depends(get_orchestration_service),
) -> OrchestrationStartResponse:
    """Start orchestration with optional parameters."""
    try:
        return await service.start(payload)
    except Exception:
        logger.exception("Failed to start orchestration.")
        raise HTTPException(status_code=500, detail="Failed to start orchestration.")


@router.post("/api/orchestration/stop", response_model=OrchestrationStopResponse)
async def stop_orchestration(
    service: OrchestrationService = Depends(get_orchestration_service),
) -> OrchestrationStopResponse:
    """Stop the current orchestration."""
    return await service.stop()


@router.post("/api/orchestration/pause", response_model=OrchestrationStopResponse)
async def pause_orchestration(
    service: OrchestrationService = Depends(get_orchestration_service),
) -> OrchestrationStopResponse:
    """Pause the current orchestration."""
    return await service.pause()


@router.get("/api/orchestration/narrative", response_model=NarrativeResponse)
async def get_narrative(
    service: OrchestrationService = Depends(get_orchestration_service),
) -> NarrativeResponse:
    """Get current narrative content."""
    return await service.get_narrative()
