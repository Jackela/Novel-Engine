"""
Prompt Experiment API Router

Warzone 4: AI Brain - BRAIN-018B
REST API for managing prompt A/B testing experiments.

Constitution Compliance:
- Article II (Hexagonal): Router handles HTTP, Service handles business logic
- Article I (DDD): No business logic in router layer
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from src.api.schemas import (
    ExperimentActionRequest,
    ExperimentCreateRequest,
    ExperimentListResponse,
    ExperimentRecordRequest,
    ExperimentResultsResponse,
    ExperimentSummaryResponse,
)
from src.api.services.experiment_router_service import ExperimentRouterService
from src.api.services.prompt_router_service import PromptRouterService
from src.contexts.knowledge.application.ports.i_experiment_repository import (
    ExperimentNotFoundError,
    ExperimentRepositoryError,
)
from src.contexts.knowledge.application.ports.i_prompt_repository import (
    PromptNotFoundError,
)
from src.contexts.knowledge.domain.models.prompt_experiment import (
    ExperimentMetric,
)
from src.contexts.knowledge.infrastructure.adapters.in_memory_experiment_repository import (
    InMemoryExperimentRepository,
)
from src.contexts.knowledge.infrastructure.adapters.in_memory_prompt_repository import (
    InMemoryPromptRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["experiments"])


def get_experiment_repository(request: Request) -> InMemoryExperimentRepository:
    """
    Get or create the experiment repository from app state.

    Why: Lazy initialization and singleton pattern for the repository.

    Args:
        request: FastAPI request object

    Returns:
        The experiment repository instance
    """
    repository = getattr(request.app.state, "experiment_repository", None)
    if repository is None:
        repository = InMemoryExperimentRepository()
        request.app.state.experiment_repository = repository
        logger.info("Initialized InMemoryExperimentRepository")
    return repository


def get_prompt_repository(request: Request) -> InMemoryPromptRepository:
    """
    Get or create the prompt repository from app state.

    Args:
        request: FastAPI request object

    Returns:
        The prompt repository instance
    """
    repository = getattr(request.app.state, "prompt_repository", None)
    if repository is None:
        repository = InMemoryPromptRepository()
        request.app.state.prompt_repository = repository
        logger.info("Initialized InMemoryPromptRepository")
    return repository


def get_prompt_service(
    repository: InMemoryPromptRepository = Depends(get_prompt_repository),
) -> PromptRouterService:
    """
    Get the prompt router service.

    Args:
        repository: The prompt repository

    Returns:
        PromptRouterService instance
    """
    return PromptRouterService(repository)


def get_experiment_service(
    experiment_repository: InMemoryExperimentRepository = Depends(get_experiment_repository),
    prompt_repository: InMemoryPromptRepository = Depends(get_prompt_repository),
) -> ExperimentRouterService:
    """
    Get the experiment router service.

    Args:
        experiment_repository: The experiment repository
        prompt_repository: The prompt repository

    Returns:
        ExperimentRouterService instance
    """
    return ExperimentRouterService(experiment_repository, prompt_repository)


# ==================== Query/List Endpoints ====================


@router.get("/experiments", response_model=ExperimentListResponse)
async def list_experiments(
    request: Request,
    response: Response,
    status: Optional[str] = None,
    prompt_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    service: ExperimentRouterService = Depends(get_experiment_service),
) -> ExperimentListResponse:
    """
    List all experiments with optional filtering.

    Why: Provides discovery and browsing of experiments.

    Args:
        request: FastAPI request
        response: FastAPI response (for cache headers)
        status: Optional filter by status
        prompt_id: Optional filter by prompt ID
        limit: Maximum number of results
        offset: Number of results to skip
        service: Experiment router service

    Returns:
        List of experiment summaries
    """
    try:
        experiments = await service.list_experiments(
            status=status,
            prompt_id=prompt_id,
            limit=limit,
            offset=offset,
        )

        total = await service.count_experiments()

        return ExperimentListResponse(
            experiments=[service.to_summary(e) for e in experiments],
            total=total,
            limit=limit,
            offset=offset,
        )

    except ExperimentRepositoryError as e:
        logger.error(f"Failed to list experiments: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/experiments/health", response_model=dict[str, Any])
async def experiments_health(
    service: ExperimentRouterService = Depends(get_experiment_service),
) -> dict[str, Any]:
    """
    Health check for the experiment system.

    Why: Verify repository is accessible and count experiments.

    NOTE: This route must be defined BEFORE /experiments/{experiment_id}
          to avoid 'health' being captured as an experiment_id.

    Args:
        service: Experiment router service

    Returns:
        Health status information
    """
    try:
        count = await service.count_experiments()
        return {
            "status": "healthy",
            "repository_type": "InMemoryExperimentRepository",
            "total_experiments": count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except ExperimentRepositoryError as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ==================== CRUD Endpoints ====================


@router.post("/experiments", response_model=ExperimentSummaryResponse, status_code=201)
async def create_experiment(
    payload: ExperimentCreateRequest,
    service: ExperimentRouterService = Depends(get_experiment_service),
) -> ExperimentSummaryResponse:
    """
    Create a new A/B testing experiment.

    Why: Allows users to compare prompt variants.

    Args:
        payload: Experiment creation request
        service: Experiment router service

    Returns:
        Created experiment summary
    """
    try:
        metric = ExperimentMetric(payload.metric)

        experiment = await service.create_experiment(
            name=payload.name,
            prompt_a_id=payload.prompt_a_id,
            prompt_b_id=payload.prompt_b_id,
            metric=metric,
            traffic_split=payload.traffic_split,
            description=payload.description,
            min_sample_size=payload.min_sample_size,
            confidence_threshold=payload.confidence_threshold,
        )

        return service.to_summary(experiment)

    except PromptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except (ValueError, ExperimentRepositoryError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/experiments/{experiment_id}", response_model=ExperimentSummaryResponse)
async def get_experiment(
    experiment_id: str,
    service: ExperimentRouterService = Depends(get_experiment_service),
) -> ExperimentSummaryResponse:
    """
    Get a specific experiment by ID.

    Why: Retrieve full experiment details for viewing.

    Args:
        experiment_id: Experiment ID
        service: Experiment router service

    Returns:
        Experiment summary response
    """
    try:
        experiment = await service.get_experiment(experiment_id)
        return service.to_summary(experiment)

    except ExperimentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ExperimentRepositoryError as e:
        logger.error(f"Failed to get experiment: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/experiments/{experiment_id}/results",
    response_model=ExperimentResultsResponse,
)
async def get_experiment_results(
    experiment_id: str,
    service: ExperimentRouterService = Depends(get_experiment_service),
) -> ExperimentResultsResponse:
    """
    Get experiment results with statistical analysis.

    Why: View detailed metrics and statistical significance.

    Args:
        experiment_id: Experiment ID
        service: Experiment router service

    Returns:
        Experiment results with metrics, comparison, and significance
    """
    try:
        results = await service.get_results(experiment_id)
        return ExperimentResultsResponse(**results)

    except ExperimentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ExperimentRepositoryError as e:
        logger.error(f"Failed to get experiment results: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/experiments/{experiment_id}", status_code=204, response_class=Response)
async def delete_experiment(
    experiment_id: str,
    service: ExperimentRouterService = Depends(get_experiment_service),
) -> Response:
    """
    Delete an experiment.

    Why: Remove experiments that are no longer needed.

    Args:
        experiment_id: ID of the experiment to delete
        service: Experiment router service

    Returns:
        204 No Content on success
    """
    try:
        deleted = await service.delete_experiment(experiment_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")

        return Response(status_code=204)

    except HTTPException:
        raise
    except ExperimentRepositoryError as e:
        logger.error(f"Failed to delete experiment: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== Action Endpoints ====================


@router.post("/experiments/{experiment_id}/start", response_model=ExperimentSummaryResponse)
async def start_experiment(
    experiment_id: str,
    service: ExperimentRouterService = Depends(get_experiment_service),
) -> ExperimentSummaryResponse:
    """
    Start an experiment.

    Why: Begin data collection for an A/B test.

    Args:
        experiment_id: ID of the experiment to start
        service: Experiment router service

    Returns:
        Updated experiment summary
    """
    try:
        experiment = await service.start_experiment(experiment_id)
        return service.to_summary(experiment)

    except ExperimentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ExperimentRepositoryError as e:
        logger.error(f"Failed to start experiment: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/experiments/{experiment_id}/pause", response_model=ExperimentSummaryResponse)
async def pause_experiment(
    experiment_id: str,
    service: ExperimentRouterService = Depends(get_experiment_service),
) -> ExperimentSummaryResponse:
    """
    Pause a running experiment.

    Why: Temporarily stop data collection.

    Args:
        experiment_id: ID of the experiment to pause
        service: Experiment router service

    Returns:
        Updated experiment summary
    """
    try:
        experiment = await service.pause_experiment(experiment_id)
        return service.to_summary(experiment)

    except ExperimentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ExperimentRepositoryError as e:
        logger.error(f"Failed to pause experiment: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/experiments/{experiment_id}/resume", response_model=ExperimentSummaryResponse)
async def resume_experiment(
    experiment_id: str,
    service: ExperimentRouterService = Depends(get_experiment_service),
) -> ExperimentSummaryResponse:
    """
    Resume a paused experiment.

    Why: Continue data collection.

    Args:
        experiment_id: ID of the experiment to resume
        service: Experiment router service

    Returns:
        Updated experiment summary
    """
    try:
        experiment = await service.resume_experiment(experiment_id)
        return service.to_summary(experiment)

    except ExperimentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ExperimentRepositoryError as e:
        logger.error(f"Failed to resume experiment: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/experiments/{experiment_id}/complete", response_model=ExperimentSummaryResponse)
async def complete_experiment(
    experiment_id: str,
    payload: ExperimentActionRequest = ExperimentActionRequest(),
    service: ExperimentRouterService = Depends(get_experiment_service),
) -> ExperimentSummaryResponse:
    """
    Complete an experiment and optionally declare a winner.

    Why: Finish data collection and finalize results.

    Args:
        experiment_id: ID of the experiment to complete
        payload: Optional winner specification
        service: Experiment router service

    Returns:
        Updated experiment summary
    """
    try:
        # Map "A" or "B" to actual prompt IDs
        winner_id = None
        if payload.winner:
            experiment = await service.get_experiment(experiment_id)
            if payload.winner == "A":
                winner_id = experiment.prompt_a_id
            elif payload.winner == "B":
                winner_id = experiment.prompt_b_id

        experiment = await service.complete_experiment(experiment_id, winner_id=winner_id)
        return service.to_summary(experiment)

    except ExperimentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ExperimentRepositoryError as e:
        logger.error(f"Failed to complete experiment: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/experiments/{experiment_id}/record", response_model=ExperimentSummaryResponse)
async def record_result(
    experiment_id: str,
    payload: ExperimentRecordRequest,
    service: ExperimentRouterService = Depends(get_experiment_service),
) -> ExperimentSummaryResponse:
    """
    Record a generation result for an experiment.

    Why: Track performance data for A/B testing.

    Args:
        experiment_id: ID of the experiment
        payload: Result recording request
        service: Experiment router service

    Returns:
        Updated experiment summary
    """
    try:
        experiment = await service.record_result(
            experiment_id=experiment_id,
            variant_id=payload.variant_id,
            success=payload.success,
            tokens=payload.tokens,
            latency_ms=payload.latency_ms,
            rating=payload.rating,
        )
        return service.to_summary(experiment)

    except ExperimentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ExperimentRepositoryError as e:
        logger.error(f"Failed to record result: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


__all__ = ["router"]
