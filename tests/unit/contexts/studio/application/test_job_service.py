from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProvider,
    TextGenerationProviderName,
    TextGenerationResult,
    TextGenerationTask,
)
from src.contexts.studio.application.service_common import (
    Principal,
    dump_json,
    utcnow,
)
from src.contexts.studio.application.services.ai_service import AIService
from src.contexts.studio.application.services.export_service import ExportService
from src.contexts.studio.application.services.job_service import JobService
from src.contexts.studio.application.services.project_service import ProjectService
from src.contexts.studio.application.services.review_service import ReviewService
from tests.fakes.fake_studio_repository import FakeStudioRepository


class UnusedProvider:
    async def generate_structured(
        self,
        task: TextGenerationTask,
    ) -> TextGenerationResult:
        del task
        raise AssertionError("JobService unit tests should not call the AI provider.")


def unused_provider_factory(
    provider_name: TextGenerationProviderName,
    model_name: str,
) -> TextGenerationProvider:
    del provider_name, model_name
    return UnusedProvider()


def job_service(
    repository: FakeStudioRepository,
    *,
    data_dir: Path,
) -> JobService:
    return JobService(
        repository,
        AIService(repository, unused_provider_factory),
        ReviewService(repository),
        ExportService(repository, data_dir=data_dir),
    )


def project_id(
    repository: FakeStudioRepository,
    principal: Principal,
    title: str,
) -> str:
    project = ProjectService(repository).create_project(principal, title=title)
    return str(project["id"])


def test_list_jobs_returns_newest_visible_payload(
    fake_repository: FakeStudioRepository,
    guest_principal: Principal,
    tmp_path: Path,
) -> None:
    project = project_id(fake_repository, guest_principal, "Job list")
    first_created_at = utcnow()
    second_created_at = first_created_at + timedelta(seconds=1)
    first = fake_repository.create_job(
        project_id=project,
        document_id=None,
        kind="review",
        operation="review",
        status="failed",
        provider="mock",
        model="review-v1",
        request_json=dump_json({"reason": "first"}),
        result_json="{}",
        error="first failure",
        retry_of_job_id=None,
        now=first_created_at,
    )
    second = fake_repository.create_job(
        project_id=project,
        document_id=None,
        kind="export",
        operation="markdown",
        status="interrupted",
        provider="mock",
        model="export-v1",
        request_json=dump_json({"reason": "second"}),
        result_json="{}",
        error="second failure",
        retry_of_job_id=None,
        now=second_created_at,
    )

    jobs = job_service(fake_repository, data_dir=tmp_path).list_jobs(
        guest_principal,
        project,
    )

    assert [item["id"] for item in jobs] == [second.id, first.id]
    assert jobs[0]["request"] == {"reason": "second"}
    assert jobs[0]["status"] == "interrupted"


async def test_retry_review_job_completes_with_review_result(
    fake_repository: FakeStudioRepository,
    guest_principal: Principal,
    tmp_path: Path,
) -> None:
    project = project_id(fake_repository, guest_principal, "Review retry")
    original = fake_repository.create_job(
        project_id=project,
        document_id=None,
        kind="review",
        operation="review",
        status="failed",
        provider="mock",
        model="review-v1",
        request_json=dump_json({"review": True}),
        result_json="{}",
        error="previous review failure",
        retry_of_job_id=None,
        now=utcnow(),
    )

    retry = await job_service(fake_repository, data_dir=tmp_path).retry_job(
        guest_principal,
        project,
        original.id,
    )

    assert retry["status"] == "completed"
    assert retry["kind"] == "review"
    assert retry["retry_of_job_id"] == original.id
    assert retry["result"]["review_id"]
    assert retry["result"]["snapshot_id"]
    assert retry["events"][-1]["status"] == "completed"


async def test_retry_export_job_completes_with_download_result(
    fake_repository: FakeStudioRepository,
    guest_principal: Principal,
    tmp_path: Path,
) -> None:
    project = project_id(fake_repository, guest_principal, "Export retry")
    original = fake_repository.create_job(
        project_id=project,
        document_id=None,
        kind="export",
        operation="markdown",
        status="interrupted",
        provider="mock",
        model="export-v1",
        request_json=dump_json({"format": "markdown"}),
        result_json="{}",
        error="previous export interruption",
        retry_of_job_id=None,
        now=utcnow(),
    )

    retry = await job_service(fake_repository, data_dir=tmp_path).retry_job(
        guest_principal,
        project,
        original.id,
    )

    assert retry["status"] == "completed"
    assert retry["kind"] == "export"
    assert retry["retry_of_job_id"] == original.id
    assert retry["result"]["format"] == "markdown"
    assert retry["result"]["download_url"].startswith("/api/projects/")
    assert retry["events"][-1]["status"] == "completed"


async def test_retry_malformed_proposal_records_failed_retry(
    fake_repository: FakeStudioRepository,
    guest_principal: Principal,
    tmp_path: Path,
) -> None:
    project = project_id(fake_repository, guest_principal, "Malformed proposal")
    original = fake_repository.create_job(
        project_id=project,
        document_id=None,
        kind="proposal",
        operation="continue",
        status="failed",
        provider="mock",
        model="proposal-v1",
        request_json="{}",
        result_json="{}",
        error="previous proposal failure",
        retry_of_job_id=None,
        now=utcnow(),
    )

    retry = await job_service(fake_repository, data_dir=tmp_path).retry_job(
        guest_principal,
        project,
        original.id,
    )

    assert retry["status"] == "failed"
    assert retry["retry_of_job_id"] == original.id
    assert retry["error"] == "Original AI job is missing base_revision_id."
    assert retry["events"][-1]["status"] == "failed"
