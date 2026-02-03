"""Orchestration Router - Thin HTTP layer with Pydantic models."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.api.schemas import (
    NarrativeData,
    NarrativeResponse,
    OrchestrationStartRequest,
    OrchestrationStartResponse,
    OrchestrationStatusData,
    OrchestrationStatusResponse,
    OrchestrationStopResponse,
)
from src.api.services.orchestration_service import OrchestrationService
from src.core.result import Error, Result

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
    """
    Get current orchestration status.

    Unwraps Result from service layer and converts to HTTP response.
    """
    result: Result = await service.get_status()

    if result.is_error:
        error: Error = result.error
        if error.code == "SERVICE_UNAVAILABLE":
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.message},
        )

    return OrchestrationStatusResponse(success=True, data=result.value)


@router.post("/api/orchestration/start", response_model=OrchestrationStartResponse)
async def start_orchestration(
    payload: Optional[OrchestrationStartRequest] = None,
    service: OrchestrationService = Depends(get_orchestration_service),
) -> OrchestrationStartResponse:
    """
    Start orchestration with optional parameters.

    Unwraps Result from service layer and converts to HTTP response.
    """
    result: Result = await service.start(payload)

    if result.is_error:
        error: Error = result.error
        if error.code == "SERVICE_UNAVAILABLE":
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif error.code == "INVALID_REQUEST":
            status_code = status.HTTP_400_BAD_REQUEST
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.message},
        )

    return OrchestrationStartResponse(**result.value)


@router.post("/api/orchestration/stop", response_model=OrchestrationStopResponse)
async def stop_orchestration(
    service: OrchestrationService = Depends(get_orchestration_service),
) -> OrchestrationStopResponse:
    """
    Stop the current orchestration.

    Unwraps Result from service layer and converts to HTTP response.
    """
    result: Result = await service.stop()

    if result.is_error:
        error: Error = result.error
        if error.code == "SERVICE_UNAVAILABLE":
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.message},
        )

    return OrchestrationStopResponse(**result.value)


@router.post("/api/orchestration/pause", response_model=OrchestrationStopResponse)
async def pause_orchestration(
    service: OrchestrationService = Depends(get_orchestration_service),
) -> OrchestrationStopResponse:
    """
    Pause the current orchestration.

    Unwraps Result from service layer and converts to HTTP response.
    """
    result: Result = await service.pause()

    if result.is_error:
        error: Error = result.error
        if error.code == "SERVICE_UNAVAILABLE":
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.message},
        )

    return OrchestrationStopResponse(**result.value)


@router.get("/api/orchestration/narrative", response_model=NarrativeResponse)
async def get_narrative(
    service: OrchestrationService = Depends(get_orchestration_service),
) -> NarrativeResponse:
    """
    Get current narrative content.

    Unwraps Result from service layer and converts to HTTP response.
    """
    result: Result = await service.get_narrative()

    if result.is_error:
        error: Error = result.error
        if error.code == "SERVICE_UNAVAILABLE":
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.message},
        )

    return NarrativeResponse(success=True, data=result.value)
