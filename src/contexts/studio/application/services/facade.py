from __future__ import annotations

from src.contexts.studio.application.service_common import (
    Any,
    DocumentDto,
    JobDto,
    ProjectDto,
    ReviewDto,
    RevisionDto,
    SnapshotDto,
    _document_payload,
    _job_payload,
    _project_payload,
    _review_payload,
    _revision_payload,
    _snapshot_payload,
)
from src.contexts.studio.application.services.facade_auth_project import (
    AuthProjectFacade,
)
from src.contexts.studio.application.services.facade_document import (
    DocumentRevisionFacade,
)
from src.contexts.studio.application.services.facade_workflow import WorkflowFacade

__all__ = ["StudioStore"]


class StudioStore(AuthProjectFacade, DocumentRevisionFacade, WorkflowFacade):
    def _project_payload(
        self,
        project: ProjectDto,
        *,
        include_documents: bool = True,
    ) -> dict[str, Any]:
        return _project_payload(project, include_documents=include_documents)

    def _document_payload(self, document: DocumentDto) -> dict[str, Any]:
        return _document_payload(document)

    def _revision_payload(self, revision: RevisionDto) -> dict[str, Any]:
        return _revision_payload(revision)

    def _snapshot_payload(self, snapshot: SnapshotDto) -> dict[str, Any]:
        return _snapshot_payload(snapshot)

    def _review_payload(self, review: ReviewDto) -> dict[str, Any]:
        return _review_payload(review)

    def _job_payload(self, job: JobDto) -> dict[str, Any]:
        return _job_payload(job)
