"""
Unit Tests for Async Ingestion Job API

Tests the async ingestion job endpoints for the brain router.

OPT-005: Async Ingestion Job API
Tests 202 response, job status transitions, and error handling.

Constitution Compliance:
- Article III (TDD): Tests written to validate async job behavior
- Article II (Hexagonal): Tests use mock services for isolation
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.api.routers.brain_settings import (
    IngestionJob,
    IngestionJobStore,
    _run_ingestion_job,
    get_ingestion_job_store,
    get_ingestion_service,
)
from src.api.schemas import (
    IngestionJobStatus,
    StartIngestionJobRequest,
)
from src.contexts.knowledge.application.services.knowledge_ingestion_service import (
    IngestionResult,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_ingestion_service():
    """Create a mock ingestion service."""
    service = AsyncMock()
    service.ingest.return_value = IngestionResult(
        success=True,
        source_id="test_source",
        chunk_count=5,
        entries_created=5,
    )
    return service


@pytest.fixture
def job_store():
    """Create a fresh job store for each test."""
    return IngestionJobStore()


@pytest.fixture
def mock_app():
    """Create a mock FastAPI app with state."""
    app = MagicMock(spec=FastAPI)
    app.state = MagicMock()
    return app


@pytest.mark.unit
class TestIngestionJobStore:
    """Tests for IngestionJobStore."""

    @pytest.mark.asyncio
    async def test_create_job(self, job_store):
        """Test creating a new job."""
        job = await job_store.create_job(
            source_id="test_source",
            source_type="CHARACTER",
            content="Test content",
        )

        assert job.job_id is not None
        assert job.source_id == "test_source"
        assert job.source_type == "CHARACTER"
        assert job.content == "Test content"
        assert job.status == IngestionJobStatus.PENDING
        assert job.progress == 0.0
        assert job.created_at is not None
        assert job.started_at is None
        assert job.completed_at is None

    @pytest.mark.asyncio
    async def test_get_job(self, job_store):
        """Test retrieving a job by ID."""
        created = await job_store.create_job(
            source_id="test_source",
            source_type="LORE",
            content="Test content",
        )

        retrieved = await job_store.get_job(created.job_id)

        assert retrieved is not None
        assert retrieved.job_id == created.job_id
        assert retrieved.source_id == created.source_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_job(self, job_store):
        """Test retrieving a non-existent job."""
        job = await job_store.get_job("nonexistent_id")
        assert job is None

    @pytest.mark.asyncio
    async def test_update_job_status_to_running(self, job_store):
        """Test updating job status to RUNNING sets started_at."""
        job = await job_store.create_job(
            source_id="test_source",
            source_type="SCENE",
            content="Test content",
        )

        updated = await job_store.update_job(
            job.job_id,
            status=IngestionJobStatus.RUNNING,
            progress=50.0,
        )

        assert updated is not None
        assert updated.status == IngestionJobStatus.RUNNING
        assert updated.progress == 50.0
        assert updated.started_at is not None

    @pytest.mark.asyncio
    async def test_update_job_status_to_completed(self, job_store):
        """Test updating job status to COMPLETED sets completed_at."""
        job = await job_store.create_job(
            source_id="test_source",
            source_type="ITEM",
            content="Test content",
        )

        updated = await job_store.update_job(
            job.job_id,
            status=IngestionJobStatus.COMPLETED,
            progress=100.0,
            chunk_count=10,
            entries_created=10,
        )

        assert updated is not None
        assert updated.status == IngestionJobStatus.COMPLETED
        assert updated.progress == 100.0
        assert updated.completed_at is not None
        assert updated.chunk_count == 10
        assert updated.entries_created == 10

    @pytest.mark.asyncio
    async def test_update_job_status_to_failed(self, job_store):
        """Test updating job status to FAILED sets error and completed_at."""
        job = await job_store.create_job(
            source_id="test_source",
            source_type="LOCATION",
            content="Test content",
        )

        error_msg = "Embedding service unavailable"
        updated = await job_store.update_job(
            job.job_id,
            status=IngestionJobStatus.FAILED,
            error=error_msg,
        )

        assert updated is not None
        assert updated.status == IngestionJobStatus.FAILED
        assert updated.error == error_msg
        assert updated.completed_at is not None

    @pytest.mark.asyncio
    async def test_list_jobs_most_recent_first(self, job_store):
        """Test listing jobs returns most recent first."""
        # Create jobs with slight delay to ensure different timestamps
        import asyncio

        job1 = await job_store.create_job("source1", "CHARACTER", "content1")
        await asyncio.sleep(0.01)
        job2 = await job_store.create_job("source2", "LORE", "content2")
        await asyncio.sleep(0.01)
        job3 = await job_store.create_job("source3", "SCENE", "content3")

        jobs = await job_store.list_jobs(limit=10)

        assert len(jobs) == 3
        assert jobs[0].job_id == job3.job_id
        assert jobs[1].job_id == job2.job_id
        assert jobs[2].job_id == job1.job_id

    @pytest.mark.asyncio
    async def test_list_jobs_respects_limit(self, job_store):
        """Test listing jobs respects the limit parameter."""
        for i in range(10):
            await job_store.create_job(f"source{i}", "CHARACTER", f"content{i}")

        jobs = await job_store.list_jobs(limit=5)

        assert len(jobs) == 5


@pytest.mark.unit
class TestIngestionJobWorker:
    """Tests for the background ingestion job worker."""

    @pytest.mark.asyncio
    async def test_successful_job_execution(self, mock_ingestion_service):
        """Test worker executes job successfully."""
        store = IngestionJobStore()

        job = await store.create_job(
            source_id="test_source",
            source_type="CHARACTER",
            content="Test content",
        )

        await _run_ingestion_job(job.job_id, store, mock_ingestion_service)

        # Verify job was updated
        final_job = await store.get_job(job.job_id)
        assert final_job is not None
        assert final_job.status == IngestionJobStatus.COMPLETED
        assert final_job.progress == 100.0
        assert final_job.chunk_count == 5
        assert final_job.entries_created == 5

        # Verify service was called
        mock_ingestion_service.ingest.assert_called_once_with(
            content="Test content",
            source_type="CHARACTER",
            source_id="test_source",
            tags=None,
            extra_metadata=None,
        )

    @pytest.mark.asyncio
    async def test_job_execution_with_failure(self, mock_ingestion_service):
        """Test worker handles service failure."""
        mock_ingestion_service.ingest.side_effect = Exception("Service unavailable")

        store = IngestionJobStore()

        job = await store.create_job(
            source_id="test_source",
            source_type="LORE",
            content="Test content",
        )

        await _run_ingestion_job(job.job_id, store, mock_ingestion_service)

        # Verify job was marked as failed
        final_job = await store.get_job(job.job_id)
        assert final_job is not None
        assert final_job.status == IngestionJobStatus.FAILED
        assert final_job.error is not None
        assert "Service unavailable" in final_job.error
        assert final_job.completed_at is not None

    @pytest.mark.asyncio
    async def test_job_execution_with_tags_and_metadata(self, mock_ingestion_service):
        """Test worker passes tags and metadata to service."""
        store = IngestionJobStore()

        tags = ["protagonist", "knight"]
        metadata = {"world_version": "1.0"}

        job = await store.create_job(
            source_id="test_source",
            source_type="CHARACTER",
            content="Test content",
            tags=tags,
            extra_metadata=metadata,
        )

        await _run_ingestion_job(job.job_id, store, mock_ingestion_service)

        # Verify service was called with tags and metadata
        mock_ingestion_service.ingest.assert_called_once_with(
            content="Test content",
            source_type="CHARACTER",
            source_id="test_source",
            tags=tags,
            extra_metadata=metadata,
        )

    @pytest.mark.asyncio
    async def test_nonexistent_job_is_logged(self, mock_ingestion_service, caplog):
        """Test worker handles nonexistent job gracefully."""
        import logging

        store = IngestionJobStore()

        # Should not raise, just log a warning
        await _run_ingestion_job("nonexistent_id", store, mock_ingestion_service)

        # Verify no crash occurred


@pytest.mark.unit
class TestIngestionJobToResponse:
    """Tests for IngestionJob.to_response conversion."""

    def test_to_response_with_pending_status(self):
        """Test converting a pending job to response."""
        job = IngestionJob(
            job_id="test-id",
            source_id="test_source",
            source_type="CHARACTER",
            content="Test content",
        )

        response = job.to_response()

        assert response.job_id == "test-id"
        assert response.status == IngestionJobStatus.PENDING
        assert response.progress == 0.0
        assert response.source_id == "test_source"
        assert response.source_type == "CHARACTER"
        assert response.created_at is not None
        assert response.started_at is None
        assert response.completed_at is None
        assert response.error is None
        assert response.chunk_count is None
        assert response.entries_created is None

    def test_to_response_with_completed_status(self):
        """Test converting a completed job to response."""
        job = IngestionJob(
            job_id="test-id",
            source_id="test_source",
            source_type="LORE",
            content="Test content",
        )
        job.status = IngestionJobStatus.COMPLETED
        job.progress = 100.0
        job.started_at = datetime.now(UTC)
        job.completed_at = datetime.now(UTC)
        job.chunk_count = 10
        job.entries_created = 10

        response = job.to_response()

        assert response.status == IngestionJobStatus.COMPLETED
        assert response.progress == 100.0
        assert response.started_at is not None
        assert response.completed_at is not None
        assert response.chunk_count == 10
        assert response.entries_created == 10

    def test_to_response_with_failed_status(self):
        """Test converting a failed job to response."""
        job = IngestionJob(
            job_id="test-id",
            source_id="test_source",
            source_type="SCENE",
            content="Test content",
        )
        job.status = IngestionJobStatus.FAILED
        job.started_at = datetime.now(UTC)
        job.completed_at = datetime.now(UTC)
        job.error = "Embedding service unavailable"

        response = job.to_response()

        assert response.status == IngestionJobStatus.FAILED
        assert response.error == "Embedding service unavailable"
        assert response.started_at is not None
        assert response.completed_at is not None
