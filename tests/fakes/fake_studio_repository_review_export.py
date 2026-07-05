from __future__ import annotations

from datetime import datetime

from src.contexts.studio.application.ports.studio_repository import (
    DocumentDto,
    ExportDto,
    ProjectDto,
    ReviewDto,
    ReviewIssueDto,
    RevisionDto,
    SnapshotDto,
)
from src.contexts.studio.domain.exceptions import NotFound
from src.contexts.studio.domain.utils import _word_count, dump_json, new_id


class FakeStudioRepositoryReviewExportMixin:
    _reviews: dict[str, ReviewDto]
    _review_issues: dict[str, list[ReviewIssueDto]]
    _exports: dict[str, ExportDto]
    _documents: dict[str, DocumentDto]

    def _get_visible_project(
        self,
        project_id: str,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> ProjectDto:
        raise NotImplementedError

    def create_snapshot(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
        reason: str,
        now: datetime,
    ) -> SnapshotDto:
        raise NotImplementedError

    def _current_revision(self, document: DocumentDto) -> RevisionDto:
        raise NotImplementedError

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
