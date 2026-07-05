from __future__ import annotations

from datetime import datetime

from src.contexts.studio.application.ports.studio_repository import (
    DocumentDto,
    ProjectDto,
    RevisionDto,
    SnapshotDocumentDto,
)
from src.contexts.studio.domain.exceptions import InvalidOperation, NotFound
from src.contexts.studio.domain.utils import new_id, utcnow


class FakeStudioRepositoryDocumentsMixin:
    _documents: dict[str, DocumentDto]
    _revisions: dict[str, RevisionDto]
    _snapshot_documents: dict[str, list[SnapshotDocumentDto]]

    def _get_visible_project(
        self,
        project_id: str,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> ProjectDto:
        raise NotImplementedError

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
        raise NotImplementedError

    def _index_document(self, document: DocumentDto, revision: RevisionDto) -> None:
        raise NotImplementedError

    def _update_project_timestamp(self, project_id: str, now: datetime) -> None:
        raise NotImplementedError

    def _project_documents(self, project_id: str) -> list[DocumentDto]:
        raise NotImplementedError

    def _get_project_document(self, project_id: str, document_id: str) -> DocumentDto:
        raise NotImplementedError

    def _current_revision(self, document: DocumentDto) -> RevisionDto:
        raise NotImplementedError

    def _delete_document_records(self, document_id: str) -> None:
        raise NotImplementedError

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
