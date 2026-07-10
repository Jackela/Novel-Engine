from __future__ import annotations

from collections.abc import Sequence

from src.contexts.studio.infrastructure.repository.common import (
    Document,
    DocumentDto,
    Project,
    ProjectDto,
    _document_dto,
)


def project_dto(
    project: Project,
    *,
    documents: Sequence[Document] | Sequence[DocumentDto] | None,
) -> ProjectDto:
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
        documents=_document_payloads(documents),
    )


def _document_payloads(
    documents: Sequence[Document] | Sequence[DocumentDto] | None,
) -> list[DocumentDto] | None:
    if documents is None:
        return None
    return [
        document if isinstance(document, DocumentDto) else _document_dto(document)
        for document in documents
    ]
