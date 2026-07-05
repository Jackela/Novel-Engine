"""In-memory fake implementation of the StudioRepository port."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

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
from src.contexts.studio.domain.utils import _word_count, dump_json, new_id, utcnow
from tests.fakes.fake_studio_repository_jobs import (
    FakeStudioRepositoryJobsMixin,
    UsageEvent,
)


@dataclass
class _FakeSearchIndex:
    """In-memory search index entry for a document revision."""

    document_id: str
    project_id: str
    title: str
    content: str


class FakeStudioRepository(FakeStudioRepositoryJobsMixin):
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
        self._search_index: list[_FakeSearchIndex] = []

    # ------------------------------------------------------------------
    # Health and auth
    # ------------------------------------------------------------------
    def health_check(self) -> bool:
        return True

    def owner_exists(self) -> bool:
        return bool(self._owners)

    def get_owner_by_username(self, username: str) -> OwnerDto | None:
        for owner in self._owners.values():
            if owner.username == username:
                return owner
        return None

    def get_first_owner(self) -> OwnerDto | None:
        if not self._owners:
            return None
        return min(self._owners.values(), key=lambda owner: owner.created_at)

    def create_owner(self, username: str, password_hash: str) -> OwnerDto:
        owner = OwnerDto(
            id=new_id(),
            username=username,
            password_hash=password_hash,
            created_at=utcnow(),
        )
        self._owners[owner.id] = owner
        return owner

    def create_session(
        self,
        *,
        kind: str,
        owner_id: str | None,
        token_hash: str,
        csrf_token: str,
        expires_at: datetime | None,
        created_at: datetime,
        last_seen_at: datetime,
    ) -> SessionDto:
        session = SessionDto(
            id=new_id(),
            kind=kind,
            owner_id=owner_id,
            token_hash=token_hash,
            csrf_token=csrf_token,
            created_at=created_at,
            expires_at=expires_at,
            last_seen_at=last_seen_at,
        )
        self._sessions[session.id] = session
        return session

    def get_session_by_token_hash(self, token_hash: str) -> SessionDto | None:
        for session in self._sessions.values():
            if session.token_hash == token_hash:
                return session
        return None

    def delete_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def delete_expired_guest_sessions(self, now: datetime) -> int:
        expired = [
            session_id
            for session_id, session in self._sessions.items()
            if session.kind == "guest"
            and session.expires_at is not None
            and session.expires_at <= now
        ]
        for session_id in expired:
            self._delete_session_cascade(session_id)
        return len(expired)

    def update_session_last_seen(
        self,
        session_id: str,
        last_seen_at: datetime,
    ) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        self._sessions[session_id] = SessionDto(
            id=session.id,
            kind=session.kind,
            owner_id=session.owner_id,
            token_hash=session.token_hash,
            csrf_token=session.csrf_token,
            created_at=session.created_at,
            expires_at=session.expires_at,
            last_seen_at=last_seen_at,
        )

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------
    def create_project(
        self,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
        title: str,
        description: str,
        settings_json: str,
        now: datetime,
        create_seed: bool = True,
    ) -> ProjectDto:
        project = ProjectDto(
            id=new_id(),
            owner_id=owner_id,
            guest_session_id=guest_session_id,
            title=title,
            description=description,
            settings_json=settings_json,
            import_hash=None,
            created_at=now,
            updated_at=now,
            documents=[],
        )
        self._projects[project.id] = project
        if create_seed:
            self._create_seed_document(project.id, now)
        return self._project_with_documents(project.id)

    def list_projects(
        self,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[ProjectDto]:
        projects = self._visible_projects(owner_id, guest_session_id)
        projects.sort(key=lambda project: project.updated_at, reverse=True)
        return [self._project_without_documents(project) for project in projects]

    def get_project(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> ProjectDto:
        self._get_visible_project(project_id, owner_id, guest_session_id)
        return self._project_with_documents(project_id)

    def update_project(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
        title: str | None,
        description: str | None,
        settings_json: str | None,
        now: datetime,
    ) -> ProjectDto:
        project = self._get_visible_project(project_id, owner_id, guest_session_id)
        self._projects[project_id] = self._replace_project(
            project,
            title=title if title is not None else project.title,
            description=description if description is not None else project.description,
            settings_json=settings_json
            if settings_json is not None
            else project.settings_json,
            updated_at=now,
        )
        return self._project_with_documents(project_id)

    def delete_project(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> None:
        project = self._get_visible_project(project_id, owner_id, guest_session_id)
        document_ids = {
            document.id
            for document in self._documents.values()
            if document.project_id == project.id
        }
        self._delete_project_records(project.id, document_ids)
        del self._projects[project_id]

    def find_project_by_import_hash(
        self,
        import_hash: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> ProjectDto | None:
        for project in self._projects.values():
            if project.import_hash == import_hash and self._scope_filter(
                project, owner_id, guest_session_id
            ):
                return self._project_without_documents(project)
        return None

    def set_project_import_hash(
        self,
        project_id: str,
        import_hash: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> None:
        project = self._get_visible_project(project_id, owner_id, guest_session_id)
        self._projects[project_id] = self._replace_project(
            project, import_hash=import_hash
        )

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------
    def create_document(
        self,
        *,
        project_id: str,
        owner_id: str | None,
        guest_session_id: str | None,
        kind: str,
        title: str,
        content_markdown: str,
        position: int,
        metadata_json: str,
        source: str,
        now: datetime,
    ) -> DocumentDto:
        self._get_visible_project(project_id, owner_id, guest_session_id)
        document, revision = self._make_document(
            project_id,
            kind,
            title,
            content_markdown,
            position,
            metadata_json,
            source,
            now,
        )
        self._revisions[revision.id] = revision
        self._documents[document.id] = document
        self._index_document(document, revision)
        self._update_project_timestamp(project_id, now)
        return document

    def list_documents(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[DocumentDto]:
        self._get_visible_project(project_id, owner_id, guest_session_id)
        return self._project_documents(project_id)

    def get_document(
        self,
        project_id: str,
        document_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> DocumentDto:
        self._get_visible_project(project_id, owner_id, guest_session_id)
        return self._get_project_document(project_id, document_id)

    def delete_document(
        self,
        project_id: str,
        document_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> None:
        self._get_visible_project(project_id, owner_id, guest_session_id)
        document = self._documents.get(document_id)
        if document is None or document.project_id != project_id:
            raise NotFound("Document not found.")
        self._delete_document_records(document_id)
        for items in self._snapshot_documents.values():
            items[:] = [item for item in items if item.document_id != document_id]
        self._update_project_timestamp(project_id, utcnow())

    def next_document_position(self, project_id: str, kind: str) -> int:
        positions = [
            document.position
            for document in self._documents.values()
            if document.project_id == project_id and document.kind == kind
        ]
        return max(positions, default=0) + 1

    def save_document(
        self,
        project_id: str,
        document_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
        content_markdown: str,
        base_revision_id: str | None,
        title: str | None,
        metadata_json: str,
        source: str,
        now: datetime,
    ) -> DocumentDto:
        self._get_visible_project(project_id, owner_id, guest_session_id)
        document = self._get_project_document(project_id, document_id)
        if document.current_revision_id != base_revision_id:
            raise InvalidOperation(
                "Document changed since the requested base revision."
            )
        current_revision = self._current_revision(document)
        new_revision = RevisionDto(
            id=new_id(),
            document_id=document_id,
            parent_revision_id=document.current_revision_id,
            revision_number=current_revision.revision_number + 1,
            content_markdown=content_markdown,
            metadata_json=metadata_json,
            source=source,
            created_at=now,
        )
        updated_document = DocumentDto(
            id=document.id,
            project_id=document.project_id,
            kind=document.kind,
            title=title if title is not None else document.title,
            position=document.position,
            current_revision_id=new_revision.id,
            created_at=document.created_at,
            updated_at=now,
            current_revision=new_revision,
        )
        self._revisions[new_revision.id] = new_revision
        self._documents[document_id] = updated_document
        self._index_document(updated_document, new_revision)
        self._update_project_timestamp(project_id, now)
        return updated_document

    def get_revision(
        self,
        project_id: str,
        document_id: str,
        revision_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> RevisionDto:
        self._get_visible_project(project_id, owner_id, guest_session_id)
        revision = self._revisions.get(revision_id)
        if revision is None or revision.document_id != document_id:
            raise NotFound("Revision not found.")
        return revision

    def list_revisions(
        self,
        project_id: str,
        document_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[RevisionDto]:
        self._get_visible_project(project_id, owner_id, guest_session_id)
        revisions = [
            revision
            for revision in self._revisions.values()
            if revision.document_id == document_id
        ]
        revisions.sort(key=lambda revision: revision.revision_number, reverse=True)
        return revisions

    def reorder_documents(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
        document_ids: list[str],
        now: datetime,
    ) -> list[DocumentDto]:
        self._get_visible_project(project_id, owner_id, guest_session_id)
        existing = {
            document.id
            for document in self._documents.values()
            if document.project_id == project_id
        }
        if set(document_ids) != existing:
            raise InvalidOperation("Reorder must include every project document once.")
        for position, doc_id in enumerate(document_ids, start=1):
            document = self._documents[doc_id]
            self._documents[doc_id] = DocumentDto(
                id=document.id,
                project_id=document.project_id,
                kind=document.kind,
                title=document.title,
                position=position,
                current_revision_id=document.current_revision_id,
                created_at=document.created_at,
                updated_at=now,
                current_revision=document.current_revision,
            )
        self._update_project_timestamp(project_id, now)
        return [self._documents[doc_id] for doc_id in document_ids]

    def search_documents(
        self,
        project_id: str,
        query: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[dict[str, Any]]:
        self._get_visible_project(project_id, owner_id, guest_session_id)
        tokens = [token.strip('"') for token in query.split('" "') if token.strip('"')]
        return [
            self._match_entry(entry, tokens)
            for entry in self._search_index
            if self._entry_matches(entry, project_id, tokens)
        ]

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------
    def create_snapshot(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
        reason: str,
        now: datetime,
    ) -> SnapshotDto:
        self._get_visible_project(project_id, owner_id, guest_session_id)
        snapshot_id = new_id()
        items = self._snapshot_items(project_id)
        snapshot = SnapshotDto(
            id=snapshot_id,
            project_id=project_id,
            reason=reason,
            created_at=now,
            documents=items,
        )
        self._snapshots[snapshot_id] = snapshot
        self._snapshot_documents[snapshot_id] = items
        return snapshot

    def list_snapshots(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[SnapshotDto]:
        self._get_visible_project(project_id, owner_id, guest_session_id)
        snapshots = [
            snapshot
            for snapshot in self._snapshots.values()
            if snapshot.project_id == project_id
        ]
        snapshots.sort(key=lambda snapshot: snapshot.created_at, reverse=True)
        return snapshots

    def get_latest_export_snapshot(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> SnapshotDto | None:
        self._get_visible_project(project_id, owner_id, guest_session_id)
        snapshots = [
            snapshot
            for snapshot in self._snapshots.values()
            if snapshot.project_id == project_id and snapshot.reason == "export"
        ]
        if not snapshots:
            return None
        snapshots.sort(key=lambda snapshot: snapshot.created_at, reverse=True)
        return snapshots[0]

    def snapshot_content(
        self,
        snapshot_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[tuple[DocumentDto, RevisionDto]]:
        snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            raise NotFound("Snapshot not found.")
        self._get_visible_project(snapshot.project_id, owner_id, guest_session_id)
        return self._snapshot_content_pairs(snapshot_id)

    def snapshot_revision_map(
        self,
        snapshot_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> dict[str, str]:
        snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            raise NotFound("Snapshot not found.")
        self._get_visible_project(snapshot.project_id, owner_id, guest_session_id)
        return {
            item.document_id: item.revision_id
            for item in self._snapshot_documents.get(snapshot_id, [])
        }

    # ------------------------------------------------------------------
    # Reviews
    # ------------------------------------------------------------------
    def create_review(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
        provider: str,
        model: str,
        now: datetime,
    ) -> ReviewDto:
        self._get_visible_project(project_id, owner_id, guest_session_id)
        snapshot = self.create_snapshot(
            project_id,
            owner_id=owner_id,
            guest_session_id=guest_session_id,
            reason="review",
            now=now,
        )
        issues = self._build_review_issues(project_id, now)
        review = ReviewDto(
            id=new_id(),
            project_id=project_id,
            snapshot_id=snapshot.id,
            provider=provider,
            model=model,
            summary="Editorial checks completed without modifying the manuscript.",
            created_at=now,
            issues=issues,
        )
        self._reviews[review.id] = review
        self._review_issues[review.id] = issues
        return review

    def list_reviews(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[ReviewDto]:
        self._get_visible_project(project_id, owner_id, guest_session_id)
        reviews = [
            review
            for review in self._reviews.values()
            if review.project_id == project_id
        ]
        reviews.sort(key=lambda review: review.created_at, reverse=True)
        return reviews

    # ------------------------------------------------------------------
    # Exports
    # ------------------------------------------------------------------
    def create_export(
        self,
        *,
        export_id: str,
        project_id: str,
        snapshot_id: str,
        export_format: str,
        relative_path: str,
        size_bytes: int,
        checksum_sha256: str,
        now: datetime,
    ) -> ExportDto:
        export = ExportDto(
            id=export_id,
            project_id=project_id,
            snapshot_id=snapshot_id,
            format=export_format,
            relative_path=relative_path,
            size_bytes=size_bytes,
            checksum_sha256=checksum_sha256,
            created_at=now,
        )
        self._exports[export.id] = export
        return export

    def list_exports(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[ExportDto]:
        self._get_visible_project(project_id, owner_id, guest_session_id)
        exports = [
            export
            for export in self._exports.values()
            if export.project_id == project_id
        ]
        exports.sort(key=lambda export: export.created_at, reverse=True)
        return exports

    def get_export(
        self,
        project_id: str,
        export_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> ExportDto:
        self._get_visible_project(project_id, owner_id, guest_session_id)
        export = self._exports.get(export_id)
        if export is None or export.project_id != project_id:
            raise NotFound("Export not found.")
        return export

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _scope_filter(
        self,
        project: ProjectDto,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> bool:
        if owner_id is not None:
            return project.owner_id == owner_id
        return project.guest_session_id == guest_session_id

    def _visible_projects(
        self,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[ProjectDto]:
        return [
            project
            for project in self._projects.values()
            if self._scope_filter(project, owner_id, guest_session_id)
        ]

    def _get_visible_project(
        self,
        project_id: str,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> ProjectDto:
        project = self._projects.get(project_id)
        if project is None or not self._scope_filter(
            project, owner_id, guest_session_id
        ):
            raise NotFound("Project not found.")
        return project

    def _replace_project(
        self,
        project: ProjectDto,
        *,
        title: str | None = None,
        description: str | None = None,
        settings_json: str | None = None,
        import_hash: str | None = None,
        updated_at: datetime | None = None,
    ) -> ProjectDto:
        return ProjectDto(
            id=project.id,
            owner_id=project.owner_id,
            guest_session_id=project.guest_session_id,
            title=title if title is not None else project.title,
            description=description if description is not None else project.description,
            settings_json=settings_json
            if settings_json is not None
            else project.settings_json,
            import_hash=import_hash if import_hash is not None else project.import_hash,
            created_at=project.created_at,
            updated_at=updated_at if updated_at is not None else project.updated_at,
            documents=None,
        )

    def _project_without_documents(self, project: ProjectDto) -> ProjectDto:
        return ProjectDto(
            id=project.id,
            owner_id=project.owner_id,
            guest_session_id=project.guest_session_id,
            title=project.title,
            description=project.description,
            settings_json=project.settings_json,
            import_hash=project.import_hash,
            created_at=project.created_at,
            updated_at=project.updated_at,
            documents=None,
        )

    def _project_with_documents(self, project_id: str) -> ProjectDto:
        project = self._projects[project_id]
        return ProjectDto(
            id=project.id,
            owner_id=project.owner_id,
            guest_session_id=project.guest_session_id,
            title=project.title,
            description=project.description,
            settings_json=project.settings_json,
            import_hash=project.import_hash,
            created_at=project.created_at,
            updated_at=project.updated_at,
            documents=self._project_documents(project_id),
        )

    def _update_project_timestamp(self, project_id: str, now: datetime) -> None:
        project = self._projects[project_id]
        self._projects[project_id] = self._replace_project(project, updated_at=now)

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

    def _index_document(self, document: DocumentDto, revision: RevisionDto) -> None:
        self._search_index = [
            entry for entry in self._search_index if entry.document_id != document.id
        ]
        self._search_index.append(
            _FakeSearchIndex(
                document_id=document.id,
                project_id=document.project_id,
                title=document.title,
                content=revision.content_markdown,
            )
        )

    def _delete_document_records(self, document_id: str) -> None:
        self._documents.pop(document_id, None)
        for revision_id, revision in list(self._revisions.items()):
            if revision.document_id == document_id:
                del self._revisions[revision_id]
        self._search_index = [
            entry for entry in self._search_index if entry.document_id != document_id
        ]

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

    def _entry_matches(
        self,
        entry: _FakeSearchIndex,
        project_id: str,
        tokens: list[str],
    ) -> bool:
        if entry.project_id != project_id or not tokens:
            return False
        title_lower = entry.title.casefold()
        content_lower = entry.content.casefold()
        return all(
            token.casefold() in title_lower or token.casefold() in content_lower
            for token in tokens
        )

    def _match_entry(
        self,
        entry: _FakeSearchIndex,
        _tokens: list[str],
    ) -> dict[str, Any]:
        excerpt = entry.content[:100]
        return {
            "document_id": entry.document_id,
            "title": entry.title,
            "excerpt": excerpt,
        }

    def _snapshot_items(self, project_id: str) -> list[SnapshotDocumentDto]:
        documents = [
            document
            for document in self._documents.values()
            if document.project_id == project_id
            and document.current_revision_id is not None
        ]
        documents.sort(key=lambda document: (document.position, document.created_at))
        return [
            SnapshotDocumentDto(
                document_id=document.id,
                revision_id=cast(str, document.current_revision_id),
                position=document.position,
            )
            for document in documents
        ]

    def _snapshot_content_pairs(
        self, snapshot_id: str
    ) -> list[tuple[DocumentDto, RevisionDto]]:
        pairs = []
        for item in self._snapshot_documents.get(snapshot_id, []):
            document = self._documents.get(item.document_id)
            revision = self._revisions.get(item.revision_id)
            if document is not None and revision is not None:
                pairs.append((document, revision))
        return pairs

    def _build_review_issues(
        self,
        project_id: str,
        _now: datetime,
    ) -> list[ReviewIssueDto]:
        issues: list[ReviewIssueDto] = []
        for document in self._documents.values():
            if document.project_id != project_id or document.kind != "chapter":
                continue
            revision = self._current_revision(document)
            words = _word_count(revision.content_markdown)
            if words < 250:
                issues.append(
                    ReviewIssueDto(
                        id=new_id(),
                        document_id=document.id,
                        severity="warning",
                        code="thin_chapter",
                        message=f"{document.title} contains only {words} words.",
                        suggestion="Develop the scene turn, consequence, and sensory detail.",
                        evidence_json=dump_json({"word_count": words}),
                    )
                )
            if not revision.content_markdown.strip():
                issues.append(
                    ReviewIssueDto(
                        id=new_id(),
                        document_id=document.id,
                        severity="blocker",
                        code="empty_chapter",
                        message=f"{document.title} has no manuscript content.",
                        suggestion="Draft the chapter before exporting.",
                        evidence_json="{}",
                    )
                )
        return issues
