"""
Ingestion Worker Service

Background job processing for async ingestion.
OPT-005: Async Ingestion Job API
"""

from __future__ import annotations

import structlog
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.api.routers.brain.repositories.ingestion import IngestionJobStore
    from src.contexts.knowledge.application.services.knowledge_ingestion_service import (
        KnowledgeIngestionService,
    )

logger = structlog.get_logger(__name__)


async def run_ingestion_job(
    job_id: str,
    store: IngestionJobStore,
    service: KnowledgeIngestionService,
) -> None:
    """
    Background worker that executes an ingestion job.

    Args:
        job_id: ID of the job to execute
        store: Job store for updates
        service: Ingestion service for processing
    """
    from src.api.schemas import IngestionJobStatus

    job = await store.get_job(job_id)
    if job is None:
        logger.warning(f"ingestion_job_not_found: job_id={job_id}")
        return

    try:
        # Update to running
        await store.update_job(job_id, status=IngestionJobStatus.RUNNING, progress=10.0)

        # Execute ingestion
        result = await service.ingest(
            content=job.content,
            source_type=job.source_type,
            source_id=job.source_id,
            tags=job.tags,
            extra_metadata=job.extra_metadata,
        )

        # Update to completed
        await store.update_job(
            job_id,
            status=IngestionJobStatus.COMPLETED,
            progress=100.0,
            chunk_count=result.chunk_count,
            entries_created=result.entries_created,
        )

        logger.info(
            f"ingestion_job_completed: job_id={job_id}, source_id={job.source_id}, chunk_count={result.chunk_count}"
        )

    except Exception as e:
        # Update to failed
        error_msg = f"{type(e).__name__}: {e}"
        await store.update_job(
            job_id,
            status=IngestionJobStatus.FAILED,
            error=error_msg,
        )

        logger.error(
            f"ingestion_job_failed: job_id={job_id}, source_id={job.source_id}, error={error_msg}"
        )


__all__ = ["run_ingestion_job"]
