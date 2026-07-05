"""In-memory fake implementation of the StudioRepository port."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.contexts.studio.application.ports.studio_repository import (
    DocumentDto,
    ExportDto,
    JobDto,
    JobEventDto,
    OwnerDto,
    ProjectDto,
    ReviewDto,
    ReviewIssueDto,
    RevisionDto,
    SessionDto,
    SnapshotDocumentDto,
    SnapshotDto,
)
from src.contexts.studio.domain.exceptions import InvalidOperation, NotFound
from src.contexts.studio.domain.utils import new_id
from tests.fakes.fake_studio_repository_auth import FakeStudioRepositoryAuthMixin
from tests.fakes.fake_studio_repository_documents import (
    FakeStudioRepositoryDocumentsMixin,
)
from tests.fakes.fake_studio_repository_jobs import (
    FakeStudioRepositoryJobsMixin,
    UsageEvent,
)
from tests.fakes.fake_studio_repository_projects import (
    FakeStudioRepositoryProjectsMixin,
)
from tests.fakes.fake_studio_repository_review_export import (
    FakeStudioRepositoryReviewExportMixin,
)
from tests.fakes.fake_studio_repository_search import (
    FakeSearchIndexEntry,
    FakeStudioRepositorySearchMixin,
)
from tests.fakes.fake_studio_repository_snapshots import (
    FakeStudioRepositorySnapshotsMixin,
)


class FakeStudioRepository(
    FakeStudioRepositoryAuthMixin,
    FakeStudioRepositoryProjectsMixin,
    FakeStudioRepositorySearchMixin,
    FakeStudioRepositoryDocumentsMixin,
    FakeStudioRepositoryJobsMixin,
    FakeStudioRepositoryReviewExportMixin,
    FakeStudioRepositorySnapshotsMixin,
):
    """In-memory StudioRepository for fast, deterministic unit tests."""

    def __init__(self, database: Any | None = None) -> None:
        self.database = database
        self._owners: dict[str, OwnerDto] = {}
        self._sessions: dict[str, SessionDto] = {}
        self._projects: dict[str, ProjectDto] = {}
        self._documents: dict[str, DocumentDto] = {}
        self._revisions: dict[str, RevisionDto] = {}
        self._snapshots: dict[str, SnapshotDto] = {}
        self._snapshot_documents: dict[str, list[SnapshotDocumentDto]] = {}
        self._reviews: dict[str, ReviewDto] = {}
        self._review_issues: dict[str, list[ReviewIssueDto]] = {}
        self._exports: dict[str, ExportDto] = {}
        self._jobs: dict[str, JobDto] = {}
        self._job_events: dict[str, list[JobEventDto]] = {}
        self._usage_events: list[UsageEvent] = []
        self._search_index: list[FakeSearchIndexEntry] = []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _project_documents(self, project_id: str) -> list[DocumentDto]:
        documents = [
            document
            for document in self._documents.values()
            if document.project_id == project_id
        ]
        documents.sort(
            key=lambda document: (document.kind, document.position, document.created_at)
        )
        return documents

    def _get_project_document(self, project_id: str, document_id: str) -> DocumentDto:
        document = self._documents.get(document_id)
        if document is None or document.project_id != project_id:
            raise NotFound("Document not found.")
        return document

    def _current_revision(self, document: DocumentDto) -> RevisionDto:
        if document.current_revision_id is None:
            raise InvalidOperation("Document has no current revision.")
        revision = self._revisions.get(document.current_revision_id)
        if revision is None:
            raise InvalidOperation("Document revision chain is invalid.")
        return revision

    def _create_seed_document(self, project_id: str, now: datetime) -> None:
        document, revision = self._make_document(
            project_id,
            "chapter",
            "Chapter 1",
            "# Chapter 1\n\n",
            1,
            "{}",
            "author",
            now,
        )
        self._revisions[revision.id] = revision
        self._documents[document.id] = document
        self._index_document(document, revision)

    def _make_document(
        self,
        project_id: str,
        kind: str,
        title: str,
        content_markdown: str,
        position: int,
        metadata_json: str,
        source: str,
        now: datetime,
    ) -> tuple[DocumentDto, RevisionDto]:
        document_id = new_id()
        revision_id = new_id()
        revision = RevisionDto(
            id=revision_id,
            document_id=document_id,
            parent_revision_id=None,
            revision_number=1,
            content_markdown=content_markdown,
            metadata_json=metadata_json,
            source=source,
            created_at=now,
        )
        document = DocumentDto(
            id=document_id,
            project_id=project_id,
            kind=kind,
            title=title,
            position=position,
            current_revision_id=revision_id,
            created_at=now,
            updated_at=now,
            current_revision=revision,
        )
        return document, revision

    def _delete_document_records(self, document_id: str) -> None:
        self._documents.pop(document_id, None)
        for revision_id, revision in list(self._revisions.items()):
            if revision.document_id == document_id:
                del self._revisions[revision_id]
        self._delete_search_document_records(document_id)

    def _delete_project_records(
        self,
        project_id: str,
        document_ids: set[str],
    ) -> None:
        for document_id in document_ids:
            self._delete_document_records(document_id)
        snapshot_ids = [
            snapshot_id
            for snapshot_id, snapshot in self._snapshots.items()
            if snapshot.project_id == project_id
        ]
        for snapshot_id in snapshot_ids:
            self._snapshot_documents.pop(snapshot_id, None)
            for review_id, review in list(self._reviews.items()):
                if review.snapshot_id == snapshot_id:
                    self._review_issues.pop(review_id, None)
                    del self._reviews[review_id]
            del self._snapshots[snapshot_id]
        for export_id, export in list(self._exports.items()):
            if export.project_id == project_id:
                del self._exports[export_id]
        for job_id, job in list(self._jobs.items()):
            if job.project_id == project_id:
                self._job_events.pop(job_id, None)
                del self._jobs[job_id]
        self._usage_events = [
            event for event in self._usage_events if event["project_id"] != project_id
        ]

    def _delete_session_cascade(self, session_id: str) -> None:
        project_ids = [
            project_id
            for project_id, project in self._projects.items()
            if project.guest_session_id == session_id
        ]
        for project_id in project_ids:
            document_ids = {
                document.id
                for document in self._documents.values()
                if document.project_id == project_id
            }
            self._delete_project_records(project_id, document_ids)
            del self._projects[project_id]
        self._sessions.pop(session_id, None)
