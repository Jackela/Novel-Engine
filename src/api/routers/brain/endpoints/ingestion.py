"""
Async Ingestion Job Endpoints

OPT-005: Async Ingestion Job API
"""

from __future__ import annotations

import structlog
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from src.api.routers.brain.dependencies import (
    get_ingestion_job_store,
    get_ingestion_service,
)
from src.api.routers.brain.repositories.ingestion import IngestionJobStore
from src.api.routers.brain.services.ingestion_worker import run_ingestion_job
from src.api.schemas import (
    IngestionJobResponse,
    IngestionJobStatus,
    StartIngestionJobRequest,
    StartIngestionJobResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["brain-settings"])


@router.post(
    "/ingestion",
    status_code=202,
    response_model=StartIngestionJobResponse,
)
async def start_ingestion_job(
    request: Request,
    payload: StartIngestionJobRequest,
    background_tasks: BackgroundTasks,
    store: IngestionJobStore = Depends(get_ingestion_job_store),
    service=Depends(get_ingestion_service),
) -> StartIngestionJobResponse:
    """
    Start an async ingestion job.

    OPT-005: Async Ingestion Job API

    Args:
        payload: Ingestion job request

    Returns:
        202 Accepted with job_id for tracking

    Raises:
        400: If validation fails
        500: If job creation fails
    """
    try:
        # Validate input
        if not payload.content or not payload.content.strip():
            raise HTTPException(status_code=400, detail="content cannot be empty")

        if not payload.source_id or not payload.source_id.strip():
            raise HTTPException(status_code=400, detail="source_id cannot be empty")

        # Create job
        job = await store.create_job(
            source_id=payload.source_id,
            source_type=payload.source_type,
            content=payload.content,
            tags=payload.tags,
            extra_metadata=payload.extra_metadata,
        )

        # Queue background work
        background_tasks.add_task(run_ingestion_job, job.job_id, store, service)

        return StartIngestionJobResponse(
            job_id=job.job_id,
            status=job.status,
            message="Ingestion job started. Poll /api/brain/ingestion/{job_id} for status.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start ingestion job: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/ingestion/{job_id}",
    response_model=IngestionJobResponse,
)
async def get_ingestion_job_status(
    job_id: str,
    store: IngestionJobStore = Depends(get_ingestion_job_store),
) -> IngestionJobResponse:
    """
    Get the status of an async ingestion job.

    OPT-005: Async Ingestion Job API

    Args:
        job_id: ID of the job to query

    Returns:
        Current job status with progress and results

    Raises:
        404: If job not found
        500: If retrieval fails
    """
    try:
        job = await store.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        return job.to_response()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get ingestion job status: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/ingestion",
    response_model=List[IngestionJobResponse],
)
async def list_ingestion_jobs(
    request: Request,
    limit: int = 100,
) -> List[IngestionJobResponse]:
    """
    List all ingestion jobs, most recent first.

    OPT-005: Async Ingestion Job API

    Args:
        limit: Maximum number of jobs to return (default: 100)

    Returns:
        List of job status responses
    """
    try:
        store = get_ingestion_job_store(request)
        jobs = await store.list_jobs(limit)
        return [job.to_response() for job in jobs]

    except Exception as e:
        logger.error(f"Failed to list ingestion jobs: {e}")
        return []
