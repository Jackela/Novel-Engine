from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from src.contexts.studio.application.ports import (
    DocumentDto,
    ExportDto,
    JobDto,
    ProjectDto,
    ReviewDto,
    RevisionDto,
    SnapshotDto,
)
from src.contexts.studio.domain.exceptions import InvalidOperation
from src.contexts.studio.domain.utils import _word_count, load_json

logger = logging.getLogger(__name__)


def iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z") if value else None


def _safe_load_json(value: str | None) -> Any:
    try:
        return load_json(value)
    except ValueError as exc:
        logger.warning("json_decode_failed value=%s error=%s", value, str(exc))
        return {}


def _project_payload(
    project: ProjectDto,
    *,
    include_documents: bool = True,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": project.id,
        "title": project.title,
        "description": project.description,
        "settings": _safe_load_json(project.settings_json),
        "import_hash": project.import_hash,
        "created_at": iso(project.created_at),
        "updated_at": iso(project.updated_at),
    }
    if include_documents:
        documents = project.documents or []
        payload["documents"] = [_document_payload(document) for document in documents]
    return payload


def _document_payload(document: DocumentDto) -> dict[str, Any]:
    revision = document.current_revision
    if revision is None:
        raise InvalidOperation("Document has no current revision.")
    return {
        "id": document.id,
        "project_id": document.project_id,
        "kind": document.kind,
        "title": document.title,
        "position": document.position,
        "current_revision_id": revision.id,
        "content_markdown": revision.content_markdown,
        "metadata": _safe_load_json(revision.metadata_json),
        "revision_source": revision.source,
        "word_count": _word_count(revision.content_markdown),
        "created_at": iso(document.created_at),
        "updated_at": iso(document.updated_at),
    }


def _revision_payload(revision: RevisionDto) -> dict[str, Any]:
    return {
        "id": revision.id,
        "document_id": revision.document_id,
        "parent_revision_id": revision.parent_revision_id,
        "revision_number": revision.revision_number,
        "content_markdown": revision.content_markdown,
        "metadata": _safe_load_json(revision.metadata_json),
        "source": revision.source,
        "word_count": _word_count(revision.content_markdown),
        "created_at": iso(revision.created_at),
    }


def _snapshot_payload(snapshot: SnapshotDto) -> dict[str, Any]:
    return {
        "id": snapshot.id,
        "project_id": snapshot.project_id,
        "reason": snapshot.reason,
        "created_at": iso(snapshot.created_at),
        "documents": [
            {
                "document_id": item.document_id,
                "revision_id": item.revision_id,
                "position": item.position,
            }
            for item in snapshot.documents
        ],
    }


def _review_payload(review: ReviewDto) -> dict[str, Any]:
    return {
        "id": review.id,
        "project_id": review.project_id,
        "snapshot_id": review.snapshot_id,
        "provider": review.provider,
        "model": review.model,
        "summary": review.summary,
        "created_at": iso(review.created_at),
        "issues": [
            {
                "id": issue.id,
                "document_id": issue.document_id,
                "severity": issue.severity,
                "code": issue.code,
                "message": issue.message,
                "suggestion": issue.suggestion,
                "evidence": _safe_load_json(issue.evidence_json),
            }
            for issue in review.issues
        ],
    }


def _job_payload(job: JobDto) -> dict[str, Any]:
    return {
        "id": job.id,
        "project_id": job.project_id,
        "document_id": job.document_id,
        "kind": job.kind,
        "operation": job.operation,
        "status": job.status,
        "provider": job.provider,
        "model": job.model,
        "request": _safe_load_json(job.request_json),
        "result": _safe_load_json(job.result_json),
        "error": job.error,
        "retry_of_job_id": job.retry_of_job_id,
        "created_at": iso(job.created_at),
        "updated_at": iso(job.updated_at),
        "events": [
            {
                "id": event.id,
                "status": event.status,
                "details": _safe_load_json(event.details_json),
                "created_at": iso(event.created_at),
            }
            for event in job.events
        ],
    }


def _export_payload(item: ExportDto) -> dict[str, Any]:
    return {
        "id": item.id,
        "project_id": item.project_id,
        "snapshot_id": item.snapshot_id,
        "format": item.format,
        "size_bytes": item.size_bytes,
        "checksum_sha256": item.checksum_sha256,
        "created_at": iso(item.created_at),
        "download_url": f"/api/projects/{item.project_id}/exports/{item.id}/download",
    }
