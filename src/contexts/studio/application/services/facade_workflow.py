from __future__ import annotations

from src.contexts.studio.application.service_common import (
    Any,
    ExportFormat,
    Path,
    Principal,
)
from src.contexts.studio.application.services.facade_base import StudioServiceRegistry


class WorkflowFacade(StudioServiceRegistry):
    def review_project(
        self,
        principal: Principal,
        project_id: str,
        *,
        provider: str = "deterministic",
        model: str = "studio-review-v1",
    ) -> dict[str, Any]:
        return self.review_service.review_project(
            principal, project_id, provider=provider, model=model
        )

    def list_reviews(
        self,
        principal: Principal,
        project_id: str,
    ) -> list[dict[str, Any]]:
        return self.review_service.list_reviews(principal, project_id)

    def export_project(
        self,
        principal: Principal,
        project_id: str,
        *,
        export_format: ExportFormat,
    ) -> dict[str, Any]:
        return self.export_service.export_project(
            principal, project_id, export_format=export_format
        )

    def list_exports(
        self,
        principal: Principal,
        project_id: str,
    ) -> list[dict[str, Any]]:
        return self.export_service.list_exports(principal, project_id)

    def export_path(
        self,
        principal: Principal,
        project_id: str,
        export_id: str,
    ) -> Path:
        return self.export_service.export_path(principal, project_id, export_id)

    async def create_ai_proposal(
        self,
        principal: Principal,
        project_id: str,
        document_id: str,
        *,
        operation: str,
        instruction: str,
        provider: str = "mock",
        model: str = "studio-copilot-v1",
    ) -> dict[str, Any]:
        return await self.ai_service.create_ai_proposal(
            principal,
            project_id,
            document_id,
            operation=operation,
            instruction=instruction,
            provider=provider,
            model=model,
        )

    def accept_ai_proposal(
        self,
        principal: Principal,
        project_id: str,
        job_id: str,
    ) -> dict[str, Any]:
        return self.ai_service.accept_ai_proposal(principal, project_id, job_id)

    def list_jobs(self, principal: Principal, project_id: str) -> list[dict[str, Any]]:
        return self.job_service.list_jobs(principal, project_id)

    async def retry_job(
        self,
        principal: Principal,
        project_id: str,
        job_id: str,
    ) -> dict[str, Any]:
        return await self.job_service.retry_job(principal, project_id, job_id)

    def preview_legacy_workspace(self, source: Path) -> dict[str, Any]:
        return self.import_service.preview_legacy_workspace(source)

    def import_legacy_workspace(
        self,
        principal: Principal,
        source: Path,
    ) -> dict[str, Any]:
        return self.import_service.import_legacy_workspace(principal, source)
