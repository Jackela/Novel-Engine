from __future__ import annotations

from src.contexts.studio.application.service_common import (
    DOCUMENT_KINDS,
    Any,
    DocumentKind,
    InvalidOperation,
    Principal,
    RevisionConflict,
    StudioRepository,
    _build_fts5_match_query,
    _document_payload,
    _owner_scopes,
    dump_json,
    utcnow,
)

__all__ = ["DocumentService"]


class DocumentService:
    """Document lifecycle within a project."""

    def __init__(self, repository: StudioRepository) -> None:
        self._repository = repository

    def create_document(
        self,
        principal: Principal,
        project_id: str,
        *,
        kind: DocumentKind,
        title: str,
        content_markdown: str = "",
        position: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if kind not in DOCUMENT_KINDS:
            raise InvalidOperation(f"Unsupported document kind: {kind}")
        owner_id, guest_session_id = _owner_scopes(principal)
        resolved_position = position
        if resolved_position is None:
            resolved_position = self._repository.next_document_position(project_id, kind)
        document = self._repository.create_document(
            project_id=project_id,
            owner_id=owner_id,
            guest_session_id=guest_session_id,
            kind=kind,
            title=title,
            content_markdown=content_markdown,
            position=resolved_position,
            metadata_json=dump_json(metadata or {}),
            source="author",
            now=utcnow(),
        )
        return _document_payload(document)

    def get_document(
        self,
        principal: Principal,
        project_id: str,
        document_id: str,
    ) -> dict[str, Any]:
        owner_id, guest_session_id = _owner_scopes(principal)
        document = self._repository.get_document(
            project_id,
            document_id,
            owner_id=owner_id,
            guest_session_id=guest_session_id,
        )
        return _document_payload(document)

    def delete_document(
        self,
        principal: Principal,
        project_id: str,
        document_id: str,
    ) -> None:
        owner_id, guest_session_id = _owner_scopes(principal)
        self._repository.delete_document(
            project_id,
            document_id,
            owner_id=owner_id,
            guest_session_id=guest_session_id,
        )

    def save_document(
        self,
        principal: Principal,
        project_id: str,
        document_id: str,
        *,
        content_markdown: str,
        base_revision_id: str | None,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
        source: str = "author",
    ) -> dict[str, Any]:
        owner_id, guest_session_id = _owner_scopes(principal)
        try:
            document = self._repository.save_document(
                project_id,
                document_id,
                owner_id=owner_id,
                guest_session_id=guest_session_id,
                content_markdown=content_markdown,
                base_revision_id=base_revision_id,
                title=title.strip() if title is not None and title.strip() else None,
                metadata_json=dump_json(metadata or {}),
                source=source,
                now=utcnow(),
            )
        except InvalidOperation as exc:
            if "changed since" in str(exc):
                current_document = self._repository.get_document(
                    project_id,
                    document_id,
                    owner_id=owner_id,
                    guest_session_id=guest_session_id,
                )
                raise RevisionConflict(current_document.current_revision_id) from exc
            raise
        return _document_payload(document)

    def reorder_documents(
        self,
        principal: Principal,
        project_id: str,
        document_ids: list[str],
    ) -> list[dict[str, Any]]:
        owner_id, guest_session_id = _owner_scopes(principal)
        documents = self._repository.reorder_documents(
            project_id,
            owner_id=owner_id,
            guest_session_id=guest_session_id,
            document_ids=document_ids,
            now=utcnow(),
        )
        return [_document_payload(document) for document in documents]

    def search(
        self,
        principal: Principal,
        project_id: str,
        query: str,
    ) -> list[dict[str, Any]]:
        match_query = _build_fts5_match_query(query)
        if match_query is None:
            return []
        owner_id, guest_session_id = _owner_scopes(principal)
        return self._repository.search_documents(
            project_id,
            match_query,
            owner_id=owner_id,
            guest_session_id=guest_session_id,
        )
