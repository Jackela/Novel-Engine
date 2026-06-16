from __future__ import annotations

from src.contexts.studio.application.service_common import (
    Any,
    Principal,
    StudioRepository,
    _owner_scopes,
    _revision_payload,
    _safe_load_json,
    cast,
)

from .document_service import DocumentService

__all__ = ["RevisionService"]


class RevisionService:
    """Revision history and restore operations."""

    def __init__(
        self,
        repository: StudioRepository,
        document_service: DocumentService,
    ) -> None:
        self._repository = repository
        self._document_service = document_service

    def list_revisions(
        self,
        principal: Principal,
        project_id: str,
        document_id: str,
    ) -> list[dict[str, Any]]:
        owner_id, guest_session_id = _owner_scopes(principal)
        revisions = self._repository.list_revisions(
            project_id,
            document_id,
            owner_id=owner_id,
            guest_session_id=guest_session_id,
        )
        return [_revision_payload(revision) for revision in revisions]

    def restore_revision(
        self,
        principal: Principal,
        project_id: str,
        document_id: str,
        revision_id: str,
        *,
        base_revision_id: str | None,
    ) -> dict[str, Any]:
        owner_id, guest_session_id = _owner_scopes(principal)
        revision = self._repository.get_revision(
            project_id,
            document_id,
            revision_id,
            owner_id=owner_id,
            guest_session_id=guest_session_id,
        )
        metadata = cast(dict[str, Any], _safe_load_json(revision.metadata_json))
        return self._document_service.save_document(
            principal,
            project_id,
            document_id,
            content_markdown=revision.content_markdown,
            base_revision_id=base_revision_id,
            metadata={**metadata, "restored_from": revision_id},
            source="restore",
        )
