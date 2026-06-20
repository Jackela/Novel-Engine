from __future__ import annotations

from src.contexts.studio.application.service_common import (
    Any,
    DocumentKind,
    Principal,
)
from src.contexts.studio.application.services.facade_base import StudioServiceRegistry


class DocumentRevisionFacade(StudioServiceRegistry):
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
        return self.document_service.create_document(
            principal,
            project_id,
            kind=kind,
            title=title,
            content_markdown=content_markdown,
            position=position,
            metadata=metadata,
        )

    def get_document(
        self,
        principal: Principal,
        project_id: str,
        document_id: str,
    ) -> dict[str, Any]:
        return self.document_service.get_document(principal, project_id, document_id)

    def delete_document(
        self,
        principal: Principal,
        project_id: str,
        document_id: str,
    ) -> None:
        return self.document_service.delete_document(principal, project_id, document_id)

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
        return self.document_service.save_document(
            principal,
            project_id,
            document_id,
            content_markdown=content_markdown,
            base_revision_id=base_revision_id,
            title=title,
            metadata=metadata,
            source=source,
        )

    def reorder_documents(
        self,
        principal: Principal,
        project_id: str,
        document_ids: list[str],
    ) -> list[dict[str, Any]]:
        return self.document_service.reorder_documents(
            principal, project_id, document_ids
        )

    def search(
        self,
        principal: Principal,
        project_id: str,
        query: str,
    ) -> list[dict[str, Any]]:
        return self.document_service.search(principal, project_id, query)

    def list_revisions(
        self,
        principal: Principal,
        project_id: str,
        document_id: str,
    ) -> list[dict[str, Any]]:
        return self.revision_service.list_revisions(principal, project_id, document_id)

    def restore_revision(
        self,
        principal: Principal,
        project_id: str,
        document_id: str,
        revision_id: str,
        *,
        base_revision_id: str | None,
    ) -> dict[str, Any]:
        return self.revision_service.restore_revision(
            principal,
            project_id,
            document_id,
            revision_id,
            base_revision_id=base_revision_id,
        )

    def create_snapshot(
        self,
        principal: Principal,
        project_id: str,
        *,
        reason: str,
    ) -> dict[str, Any]:
        return self.snapshot_service.create_snapshot(
            principal, project_id, reason=reason
        )

    def list_snapshots(
        self,
        principal: Principal,
        project_id: str,
    ) -> list[dict[str, Any]]:
        return self.snapshot_service.list_snapshots(principal, project_id)
