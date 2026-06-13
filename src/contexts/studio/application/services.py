"""Transactional application services for Novel Studio."""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, cast
from uuid import uuid4

import bcrypt
import yaml
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from src.contexts.studio.domain.types import DOCUMENT_KINDS, DocumentKind, ExportFormat
from src.contexts.studio.infrastructure.database import StudioDatabase, studio_database
from src.contexts.studio.infrastructure.models import (
    Document,
    DocumentRevision,
    Export,
    Job,
    JobEvent,
    Owner,
    Project,
    ProjectSnapshot,
    Review,
    ReviewIssue,
    SessionRecord,
    SnapshotDocument,
    UsageEvent,
)
from src.shared.infrastructure.config.settings import get_settings

GUEST_TTL = timedelta(hours=24)
SESSION_COOKIE = "novel_studio_session"


def utcnow() -> datetime:
    return datetime.now(UTC)


def iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z") if value else None


def dump_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def load_json(value: str | None) -> Any:
    if not value:
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}


def new_id() -> str:
    return str(uuid4())


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _word_count(markdown: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", markdown, flags=re.UNICODE))


def _plain_text(markdown: str) -> str:
    text_value = re.sub(r"```.*?```", "", markdown, flags=re.DOTALL)
    text_value = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text_value)
    text_value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text_value)
    text_value = re.sub(r"^[#>*+-]+\s*", "", text_value, flags=re.MULTILINE)
    text_value = re.sub(r"[*_`~]", "", text_value)
    return text_value.strip()


class RevisionConflict(RuntimeError):
    """Raised when a client saves against a stale revision."""

    def __init__(self, current_revision_id: str | None) -> None:
        super().__init__("Document changed since the requested base revision.")
        self.current_revision_id = current_revision_id


class NotFound(RuntimeError):
    """Raised when a resource is not visible to the active principal."""


class InvalidOperation(RuntimeError):
    """Raised when a valid resource cannot perform an operation."""


@dataclass(frozen=True, slots=True)
class Principal:
    session_id: str
    kind: str
    owner_id: str | None
    expires_at: datetime | None


class StudioStore:
    """High-level Studio persistence API."""

    def __init__(self, database: StudioDatabase = studio_database) -> None:
        self.database = database

    def owner_exists(self) -> bool:
        with self.database.session() as session:
            return session.scalar(select(func.count()).select_from(Owner)) > 0

    def owner_principal(self, username: str | None = None) -> Principal:
        """Return an operational principal for local CLI maintenance."""
        with self.database.session() as session:
            statement = select(Owner).order_by(Owner.created_at)
            if username:
                statement = statement.where(Owner.username == username)
            owner = session.scalar(statement)
            if owner is None:
                raise InvalidOperation("Configure the local owner before importing data.")
            return Principal(
                session_id=f"cli:{owner.id}",
                kind="owner",
                owner_id=owner.id,
                expires_at=None,
            )

    def setup_owner(self, username: str, password: str) -> dict[str, Any]:
        username = username.strip()
        password_bytes = password.encode("utf-8")
        if not username or len(password) < 10 or len(password_bytes) > 72:
            raise InvalidOperation(
                "Username is required and password must be 10-72 UTF-8 bytes."
            )
        with self.database.session() as session:
            if session.scalar(select(func.count()).select_from(Owner)):
                raise InvalidOperation("The local owner has already been configured.")
            owner = Owner(
                id=new_id(),
                username=username,
                password_hash=bcrypt.hashpw(
                    password_bytes,
                    bcrypt.gensalt(),
                ).decode("ascii"),
                created_at=utcnow(),
            )
            session.add(owner)
            return {"id": owner.id, "username": owner.username}

    def create_owner_session(self, username: str, password: str) -> tuple[str, Principal]:
        password_bytes = password.encode("utf-8")
        with self.database.session() as session:
            owner = session.scalar(select(Owner).where(Owner.username == username.strip()))
            if (
                owner is None
                or len(password_bytes) > 72
                or not bcrypt.checkpw(password_bytes, owner.password_hash.encode("ascii"))
            ):
                raise InvalidOperation("Invalid username or password.")
            return self._create_session(session, kind="owner", owner_id=owner.id)

    def create_guest_session(self) -> tuple[str, Principal]:
        with self.database.session() as session:
            return self._create_session(
                session,
                kind="guest",
                owner_id=None,
                expires_at=utcnow() + GUEST_TTL,
            )

    def _create_session(
        self,
        session: Session,
        *,
        kind: str,
        owner_id: str | None,
        expires_at: datetime | None = None,
    ) -> tuple[str, Principal]:
        token = secrets.token_urlsafe(36)
        now = utcnow()
        record = SessionRecord(
            id=new_id(),
            kind=kind,
            owner_id=owner_id,
            token_hash=_token_hash(token),
            created_at=now,
            expires_at=expires_at,
            last_seen_at=now,
        )
        session.add(record)
        return token, Principal(record.id, kind, owner_id, expires_at)

    def principal_from_token(self, token: str | None) -> Principal | None:
        if not token:
            return None
        with self.database.session() as session:
            record = session.scalar(
                select(SessionRecord).where(SessionRecord.token_hash == _token_hash(token))
            )
            if record is None:
                return None
            now = utcnow()
            expires_at = record.expires_at
            if expires_at is not None and _as_utc(expires_at) <= now:
                session.delete(record)
                return None
            record.last_seen_at = now
            return Principal(record.id, record.kind, record.owner_id, expires_at)

    def logout(self, token: str | None) -> None:
        if not token:
            return
        with self.database.session() as session:
            record = session.scalar(
                select(SessionRecord).where(SessionRecord.token_hash == _token_hash(token))
            )
            if record is not None:
                session.delete(record)

    def cleanup_expired_guests(self) -> int:
        with self.database.session() as session:
            expired = session.scalars(
                select(SessionRecord).where(
                    SessionRecord.kind == "guest",
                    SessionRecord.expires_at.is_not(None),
                    SessionRecord.expires_at <= utcnow(),
                )
            ).all()
            for record in expired:
                session.delete(record)
            return len(expired)

    def create_project(
        self,
        principal: Principal,
        *,
        title: str,
        description: str = "",
        create_seed: bool = True,
    ) -> dict[str, Any]:
        title = title.strip()
        if not title:
            raise InvalidOperation("Project title is required.")
        with self.database.session() as session:
            now = utcnow()
            project = Project(
                id=new_id(),
                owner_id=principal.owner_id,
                guest_session_id=principal.session_id if principal.kind == "guest" else None,
                title=title,
                description=description.strip(),
                settings_json=dump_json({"provider": "mock"}),
                created_at=now,
                updated_at=now,
            )
            session.add(project)
            session.flush()
            if create_seed:
                self._create_document(
                    session,
                    project,
                    kind="chapter",
                    title="Chapter 1",
                    content_markdown="# Chapter 1\n\n",
                    position=1,
                )
            return self._project_payload(session, project)

    def list_projects(self, principal: Principal) -> list[dict[str, Any]]:
        with self.database.session() as session:
            statement = select(Project).order_by(Project.updated_at.desc())
            statement = self._scope_projects(statement, principal)
            return [
                self._project_payload(session, project, include_documents=False)
                for project in session.scalars(statement).all()
            ]

    def get_project(self, principal: Principal, project_id: str) -> dict[str, Any]:
        with self.database.session() as session:
            project = self._project(session, principal, project_id)
            return self._project_payload(session, project)

    def update_project(
        self,
        principal: Principal,
        project_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self.database.session() as session:
            project = self._project(session, principal, project_id)
            if title is not None and title.strip():
                project.title = title.strip()
            if description is not None:
                project.description = description.strip()
            if settings is not None:
                project.settings_json = dump_json(settings)
            project.updated_at = utcnow()
            return self._project_payload(session, project)

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
        with self.database.session() as session:
            project = self._project(session, principal, project_id)
            resolved_position = position
            if resolved_position is None:
                resolved_position = (
                    session.scalar(
                        select(func.max(Document.position)).where(
                            Document.project_id == project.id,
                            Document.kind == kind,
                        )
                    )
                    or 0
                ) + 1
            document = self._create_document(
                session,
                project,
                kind=kind,
                title=title,
                content_markdown=content_markdown,
                position=resolved_position,
                metadata=metadata,
            )
            project.updated_at = utcnow()
            return self._document_payload(session, document)

    def _create_document(
        self,
        session: Session,
        project: Project,
        *,
        kind: DocumentKind,
        title: str,
        content_markdown: str,
        position: int,
        metadata: dict[str, Any] | None = None,
        source: str = "author",
    ) -> Document:
        now = utcnow()
        document = Document(
            id=new_id(),
            project_id=project.id,
            kind=kind,
            title=title.strip() or kind.title(),
            position=position,
            created_at=now,
            updated_at=now,
        )
        session.add(document)
        session.flush()
        revision = DocumentRevision(
            id=new_id(),
            document_id=document.id,
            parent_revision_id=None,
            revision_number=1,
            content_markdown=content_markdown,
            metadata_json=dump_json(metadata or {}),
            source=source,
            created_at=now,
        )
        session.add(revision)
        session.flush()
        document.current_revision_id = revision.id
        self._refresh_search(session, document, revision)
        return document

    def get_document(
        self,
        principal: Principal,
        project_id: str,
        document_id: str,
    ) -> dict[str, Any]:
        with self.database.session() as session:
            project = self._project(session, principal, project_id)
            document = self._document(session, project, document_id)
            return self._document_payload(session, document)

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
        with self.database.session() as session:
            project = self._project(session, principal, project_id)
            document = self._document(session, project, document_id)
            if document.current_revision_id != base_revision_id:
                raise RevisionConflict(document.current_revision_id)
            if title is not None and title.strip():
                document.title = title.strip()
            current_revision = self._current_revision(session, document)
            revision = DocumentRevision(
                id=new_id(),
                document_id=document.id,
                parent_revision_id=document.current_revision_id,
                revision_number=current_revision.revision_number + 1,
                content_markdown=content_markdown,
                metadata_json=dump_json(metadata or {}),
                source=source,
                created_at=utcnow(),
            )
            session.add(revision)
            session.flush()
            document.current_revision_id = revision.id
            document.updated_at = revision.created_at
            project.updated_at = revision.created_at
            self._refresh_search(session, document, revision)
            return self._document_payload(session, document)

    def list_revisions(
        self,
        principal: Principal,
        project_id: str,
        document_id: str,
    ) -> list[dict[str, Any]]:
        with self.database.session() as session:
            project = self._project(session, principal, project_id)
            document = self._document(session, project, document_id)
            revisions = session.scalars(
                select(DocumentRevision)
                .where(DocumentRevision.document_id == document.id)
                .order_by(DocumentRevision.revision_number.desc())
            ).all()
            return [self._revision_payload(revision) for revision in revisions]

    def restore_revision(
        self,
        principal: Principal,
        project_id: str,
        document_id: str,
        revision_id: str,
        *,
        base_revision_id: str | None,
    ) -> dict[str, Any]:
        with self.database.session() as session:
            project = self._project(session, principal, project_id)
            document = self._document(session, project, document_id)
            revision = session.scalar(
                select(DocumentRevision).where(
                    DocumentRevision.id == revision_id,
                    DocumentRevision.document_id == document.id,
                )
            )
            if revision is None:
                raise NotFound("Revision not found.")
            content = revision.content_markdown
            metadata = cast(dict[str, Any], load_json(revision.metadata_json))
        return self.save_document(
            principal,
            project_id,
            document_id,
            content_markdown=content,
            base_revision_id=base_revision_id,
            metadata={**metadata, "restored_from": revision_id},
            source="restore",
        )

    def reorder_documents(
        self,
        principal: Principal,
        project_id: str,
        document_ids: list[str],
    ) -> list[dict[str, Any]]:
        with self.database.session() as session:
            project = self._project(session, principal, project_id)
            documents = {
                document.id: document
                for document in session.scalars(
                    select(Document).where(Document.project_id == project.id)
                ).all()
            }
            if set(document_ids) != set(documents):
                raise InvalidOperation("Reorder must include every project document once.")
            now = utcnow()
            for position, document_id in enumerate(document_ids, start=1):
                documents[document_id].position = position
                documents[document_id].updated_at = now
            project.updated_at = now
            return [
                self._document_payload(session, documents[document_id])
                for document_id in document_ids
            ]

    def search(
        self,
        principal: Principal,
        project_id: str,
        query: str,
    ) -> list[dict[str, Any]]:
        query = query.strip()
        if not query:
            return []
        match_query = f'"{query.replace(chr(34), chr(34) * 2)}"'
        with self.database.session() as session:
            project = self._project(session, principal, project_id)
            rows = session.execute(
                text(
                    "SELECT document_id, title, snippet(document_search, 3, '', "
                    "'', ' … ', 16) AS excerpt "
                    "FROM document_search WHERE project_id = :project_id "
                    "AND document_search MATCH :query ORDER BY rank LIMIT 30"
                ),
                {"project_id": project.id, "query": match_query},
            ).mappings()
            return [dict(row) for row in rows]

    def create_snapshot(
        self,
        principal: Principal,
        project_id: str,
        *,
        reason: str,
    ) -> dict[str, Any]:
        with self.database.session() as session:
            project = self._project(session, principal, project_id)
            snapshot = self._create_snapshot(session, project, reason=reason)
            return self._snapshot_payload(session, snapshot)

    def list_snapshots(
        self,
        principal: Principal,
        project_id: str,
    ) -> list[dict[str, Any]]:
        with self.database.session() as session:
            project = self._project(session, principal, project_id)
            snapshots = session.scalars(
                select(ProjectSnapshot)
                .where(ProjectSnapshot.project_id == project.id)
                .order_by(ProjectSnapshot.created_at.desc())
            ).all()
            return [self._snapshot_payload(session, snapshot) for snapshot in snapshots]

    def _create_snapshot(
        self,
        session: Session,
        project: Project,
        *,
        reason: str,
    ) -> ProjectSnapshot:
        snapshot = ProjectSnapshot(
            id=new_id(),
            project_id=project.id,
            reason=reason,
            created_at=utcnow(),
        )
        session.add(snapshot)
        session.flush()
        documents = session.scalars(
            select(Document)
            .where(
                Document.project_id == project.id,
                Document.current_revision_id.is_not(None),
            )
            .order_by(Document.position, Document.created_at)
        ).all()
        for document in documents:
            session.add(
                SnapshotDocument(
                    id=new_id(),
                    snapshot_id=snapshot.id,
                    document_id=document.id,
                    revision_id=cast(str, document.current_revision_id),
                    position=document.position,
                )
            )
        session.flush()
        return snapshot

    def review_project(
        self,
        principal: Principal,
        project_id: str,
        *,
        provider: str = "deterministic",
        model: str = "studio-review-v1",
    ) -> dict[str, Any]:
        with self.database.session() as session:
            project = self._project(session, principal, project_id)
            snapshot = self._create_snapshot(session, project, reason="review")
            review = Review(
                id=new_id(),
                project_id=project.id,
                snapshot_id=snapshot.id,
                provider=provider,
                model=model,
                summary="Editorial checks completed without modifying the manuscript.",
                created_at=utcnow(),
            )
            session.add(review)
            session.flush()
            for document, revision in self._snapshot_content(session, snapshot.id):
                if document.kind != "chapter":
                    continue
                words = _word_count(revision.content_markdown)
                if words < 250:
                    session.add(
                        ReviewIssue(
                            id=new_id(),
                            review_id=review.id,
                            document_id=document.id,
                            severity="warning",
                            code="thin_chapter",
                            message=f"{document.title} contains only {words} words.",
                            suggestion="Develop the scene turn, consequence, and sensory detail.",
                            evidence_json=dump_json({"word_count": words}),
                        )
                    )
                if not revision.content_markdown.strip():
                    session.add(
                        ReviewIssue(
                            id=new_id(),
                            review_id=review.id,
                            document_id=document.id,
                            severity="blocker",
                            code="empty_chapter",
                            message=f"{document.title} has no manuscript content.",
                            suggestion="Draft the chapter before exporting.",
                            evidence_json="{}",
                        )
                    )
            session.flush()
            return self._review_payload(session, review)

    def list_reviews(self, principal: Principal, project_id: str) -> list[dict[str, Any]]:
        with self.database.session() as session:
            project = self._project(session, principal, project_id)
            reviews = session.scalars(
                select(Review)
                .where(Review.project_id == project.id)
                .order_by(Review.created_at.desc())
            ).all()
            return [self._review_payload(session, review) for review in reviews]

    def export_project(
        self,
        principal: Principal,
        project_id: str,
        *,
        export_format: ExportFormat,
    ) -> dict[str, Any]:
        if export_format not in {"markdown", "docx", "epub"}:
            raise InvalidOperation(f"Unsupported export format: {export_format}")
        with self.database.session() as session:
            project = self._project(session, principal, project_id)
            snapshot = session.scalar(
                select(ProjectSnapshot)
                .where(
                    ProjectSnapshot.project_id == project.id,
                    ProjectSnapshot.reason == "export",
                )
                .order_by(ProjectSnapshot.created_at.desc())
            )
            current_revisions = {
                document.id: document.current_revision_id
                for document in session.scalars(
                    select(Document).where(Document.project_id == project.id)
                ).all()
            }
            snapshot_revisions = (
                {
                    item.document_id: item.revision_id
                    for item in session.scalars(
                        select(SnapshotDocument).where(
                            SnapshotDocument.snapshot_id == snapshot.id
                        )
                    ).all()
                }
                if snapshot is not None
                else {}
            )
            if snapshot is None or snapshot_revisions != current_revisions:
                snapshot = self._create_snapshot(session, project, reason="export")
            content = [
                (document, revision)
                for document, revision in self._snapshot_content(session, snapshot.id)
                if document.kind == "chapter"
            ]
            if not content:
                raise InvalidOperation("Create at least one chapter before exporting.")
            export_id = new_id()
            output_dir = get_settings().data_dir / "exports" / project.id
            output_dir.mkdir(parents=True, exist_ok=True)
            suffix = "md" if export_format == "markdown" else export_format
            output_path = output_dir / f"{export_id}.{suffix}"
            if export_format == "markdown":
                self._write_markdown(output_path, project.title, content)
            elif export_format == "docx":
                self._write_docx(output_path, project.title, content)
            else:
                self._write_epub(output_path, project.title, content)
            checksum = hashlib.sha256(output_path.read_bytes()).hexdigest()
            relative_path = output_path.relative_to(get_settings().data_dir).as_posix()
            export = Export(
                id=export_id,
                project_id=project.id,
                snapshot_id=snapshot.id,
                format=export_format,
                relative_path=relative_path,
                size_bytes=output_path.stat().st_size,
                checksum_sha256=checksum,
                created_at=utcnow(),
            )
            session.add(export)
            session.flush()
            return self._export_payload(export)

    def list_exports(self, principal: Principal, project_id: str) -> list[dict[str, Any]]:
        with self.database.session() as session:
            project = self._project(session, principal, project_id)
            exports = session.scalars(
                select(Export)
                .where(Export.project_id == project.id)
                .order_by(Export.created_at.desc())
            ).all()
            return [self._export_payload(item) for item in exports]

    def export_path(
        self,
        principal: Principal,
        project_id: str,
        export_id: str,
    ) -> Path:
        with self.database.session() as session:
            project = self._project(session, principal, project_id)
            item = session.scalar(
                select(Export).where(
                    Export.id == export_id,
                    Export.project_id == project.id,
                )
            )
            if item is None:
                raise NotFound("Export not found.")
            root = get_settings().data_dir.resolve()
            path = (root / item.relative_path).resolve()
            if root not in {path, *path.parents} or not path.is_file():
                raise NotFound("Export file not found.")
            return path

    def create_ai_proposal(
        self,
        principal: Principal,
        project_id: str,
        document_id: str,
        *,
        operation: str,
        instruction: str,
        provider: str = "mock",
        model: str = "studio-copilot-v1",
    ) -> dict[str, Any]:
        with self.database.session() as session:
            project = self._project(session, principal, project_id)
            document = self._document(session, project, document_id)
            revision = self._current_revision(session, document)
            proposal = self._deterministic_proposal(
                revision.content_markdown,
                operation=operation,
                instruction=instruction,
            )
            now = utcnow()
            job = Job(
                id=new_id(),
                project_id=project.id,
                document_id=document.id,
                kind="ai",
                operation=operation,
                status="completed",
                provider=provider,
                model=model,
                request_json=dump_json(
                    {
                        "instruction": instruction,
                        "base_revision_id": revision.id,
                    }
                ),
                result_json=dump_json(
                    {
                        "proposal_markdown": proposal,
                        "base_revision_id": revision.id,
                        "accepted_revision_id": None,
                    }
                ),
                created_at=now,
                updated_at=now,
                started_at=now,
                finished_at=now,
            )
            session.add(job)
            session.add(
                JobEvent(
                    id=new_id(),
                    job_id=job.id,
                    status="completed",
                    details_json=dump_json({"proposal_only": True}),
                    created_at=now,
                )
            )
            session.add(
                UsageEvent(
                    id=new_id(),
                    project_id=project.id,
                    job_id=job.id,
                    provider=provider,
                    model=model,
                    prompt_tokens=_word_count(instruction),
                    completion_tokens=_word_count(proposal),
                    request_evidence_json=dump_json(
                        {"operation": operation, "base_revision_id": revision.id}
                    ),
                    estimated_cost=None,
                    created_at=now,
                )
            )
            session.flush()
            return self._job_payload(session, job)

    def accept_ai_proposal(
        self,
        principal: Principal,
        project_id: str,
        job_id: str,
    ) -> dict[str, Any]:
        with self.database.session() as session:
            project = self._project(session, principal, project_id)
            job = session.scalar(
                select(Job).where(
                    Job.id == job_id,
                    Job.project_id == project.id,
                    Job.kind == "ai",
                )
            )
            if job is None or job.document_id is None:
                raise NotFound("AI proposal not found.")
            result = cast(dict[str, Any], load_json(job.result_json))
            request = cast(dict[str, Any], load_json(job.request_json))
            if result.get("accepted_revision_id"):
                return self._job_payload(session, job)
            document_id = job.document_id
            proposal = str(result.get("proposal_markdown", ""))
            base_revision_id = cast(str | None, request.get("base_revision_id"))
        saved = self.save_document(
            principal,
            project_id,
            document_id,
            content_markdown=proposal,
            base_revision_id=base_revision_id,
            metadata={"ai_job_id": job_id},
            source="ai-accepted",
        )
        with self.database.session() as session:
            job = cast(Job, session.get(Job, job_id))
            result = cast(dict[str, Any], load_json(job.result_json))
            result["accepted_revision_id"] = saved["current_revision_id"]
            job.result_json = dump_json(result)
            job.updated_at = utcnow()
            return self._job_payload(session, job)

    def list_jobs(self, principal: Principal, project_id: str) -> list[dict[str, Any]]:
        with self.database.session() as session:
            project = self._project(session, principal, project_id)
            jobs = session.scalars(
                select(Job)
                .where(Job.project_id == project.id)
                .order_by(Job.created_at.desc())
            ).all()
            return [self._job_payload(session, job) for job in jobs]

    def retry_job(
        self,
        principal: Principal,
        project_id: str,
        job_id: str,
    ) -> dict[str, Any]:
        with self.database.session() as session:
            project = self._project(session, principal, project_id)
            original = session.scalar(
                select(Job).where(Job.id == job_id, Job.project_id == project.id)
            )
            if original is None:
                raise NotFound("Job not found.")
            if original.status not in {"failed", "interrupted"}:
                raise InvalidOperation("Only failed or interrupted jobs may be retried.")
            now = utcnow()
            retry = Job(
                id=new_id(),
                project_id=original.project_id,
                document_id=original.document_id,
                kind=original.kind,
                operation=original.operation,
                status="queued",
                provider=original.provider,
                model=original.model,
                request_json=original.request_json,
                result_json="{}",
                retry_of_job_id=original.id,
                created_at=now,
                updated_at=now,
            )
            session.add(retry)
            session.add(
                JobEvent(
                    id=new_id(),
                    job_id=retry.id,
                    status="queued",
                    details_json=dump_json({"retry_of": original.id}),
                    created_at=now,
                )
            )
            session.flush()
            return self._job_payload(session, retry)

    def preview_legacy_workspace(self, source: Path) -> dict[str, Any]:
        source = source.expanduser().resolve()
        story_path = source / "story.yaml"
        if not story_path.is_file():
            raise InvalidOperation("Legacy workspace must contain story.yaml.")
        story = yaml.safe_load(story_path.read_text(encoding="utf-8")) or {}
        chapter_dir = source / "manuscript" / "chapters"
        chapters = sorted(chapter_dir.glob("chapter-*.md")) if chapter_dir.exists() else []
        source_hash = self._legacy_hash(source, [story_path, *chapters])
        return {
            "source": str(source),
            "source_hash": source_hash,
            "title": str(story.get("title", source.name)),
            "description": str(story.get("premise", "")),
            "chapter_count": len(chapters),
            "chapters": [
                {"filename": chapter.name, "bytes": chapter.stat().st_size}
                for chapter in chapters
            ],
        }

    def import_legacy_workspace(
        self,
        principal: Principal,
        source: Path,
    ) -> dict[str, Any]:
        preview = self.preview_legacy_workspace(source)
        with self.database.session() as session:
            existing = session.scalar(
                select(Project).where(Project.import_hash == preview["source_hash"])
            )
            if existing is not None:
                scoped = self._project(session, principal, existing.id)
                return self._project_payload(session, scoped)
        project = self.create_project(
            principal,
            title=str(preview["title"]),
            description=str(preview["description"]),
            create_seed=False,
        )
        source_root = Path(str(preview["source"]))
        for position, chapter_path in enumerate(
            sorted((source_root / "manuscript" / "chapters").glob("chapter-*.md")),
            start=1,
        ):
            self.create_document(
                principal,
                project["id"],
                kind="chapter",
                title=f"Chapter {position}",
                content_markdown=chapter_path.read_text(encoding="utf-8"),
                position=position,
                metadata={"legacy_filename": chapter_path.name},
            )
        with self.database.session() as session:
            stored = self._project(session, principal, project["id"])
            stored.import_hash = str(preview["source_hash"])
            stored.settings_json = dump_json(
                {
                    **cast(dict[str, Any], load_json(stored.settings_json)),
                    "legacy_source": str(source_root),
                }
            )
            return self._project_payload(session, stored)

    def _project(self, session: Session, principal: Principal, project_id: str) -> Project:
        statement = select(Project).where(Project.id == project_id)
        statement = self._scope_projects(statement, principal)
        project = session.scalar(statement)
        if project is None:
            raise NotFound("Project not found.")
        return project

    @staticmethod
    def _scope_projects(statement: Any, principal: Principal) -> Any:
        if principal.kind == "owner" and principal.owner_id:
            return statement.where(Project.owner_id == principal.owner_id)
        return statement.where(Project.guest_session_id == principal.session_id)

    @staticmethod
    def _document(session: Session, project: Project, document_id: str) -> Document:
        document = session.scalar(
            select(Document).where(
                Document.id == document_id,
                Document.project_id == project.id,
            )
        )
        if document is None:
            raise NotFound("Document not found.")
        return document

    @staticmethod
    def _current_revision(session: Session, document: Document) -> DocumentRevision:
        if document.current_revision_id is None:
            raise InvalidOperation("Document has no current revision.")
        revision = session.get(DocumentRevision, document.current_revision_id)
        if revision is None:
            raise InvalidOperation("Document revision chain is invalid.")
        return revision

    @staticmethod
    def _refresh_search(
        session: Session,
        document: Document,
        revision: DocumentRevision,
    ) -> None:
        session.execute(
            text("DELETE FROM document_search WHERE document_id = :document_id"),
            {"document_id": document.id},
        )
        session.execute(
            text(
                "INSERT INTO document_search(document_id, project_id, title, content) "
                "VALUES (:document_id, :project_id, :title, :content)"
            ),
            {
                "document_id": document.id,
                "project_id": document.project_id,
                "title": document.title,
                "content": revision.content_markdown,
            },
        )

    def _project_payload(
        self,
        session: Session,
        project: Project,
        *,
        include_documents: bool = True,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": project.id,
            "title": project.title,
            "description": project.description,
            "settings": load_json(project.settings_json),
            "import_hash": project.import_hash,
            "created_at": iso(project.created_at),
            "updated_at": iso(project.updated_at),
        }
        if include_documents:
            documents = session.scalars(
                select(Document)
                .where(Document.project_id == project.id)
                .order_by(Document.kind, Document.position, Document.created_at)
            ).all()
            payload["documents"] = [
                self._document_payload(session, document) for document in documents
            ]
        return payload

    def _document_payload(self, session: Session, document: Document) -> dict[str, Any]:
        revision = self._current_revision(session, document)
        return {
            "id": document.id,
            "project_id": document.project_id,
            "kind": document.kind,
            "title": document.title,
            "position": document.position,
            "current_revision_id": revision.id,
            "content_markdown": revision.content_markdown,
            "metadata": load_json(revision.metadata_json),
            "revision_source": revision.source,
            "word_count": _word_count(revision.content_markdown),
            "created_at": iso(document.created_at),
            "updated_at": iso(document.updated_at),
        }

    @staticmethod
    def _revision_payload(revision: DocumentRevision) -> dict[str, Any]:
        return {
            "id": revision.id,
            "document_id": revision.document_id,
            "parent_revision_id": revision.parent_revision_id,
            "revision_number": revision.revision_number,
            "content_markdown": revision.content_markdown,
            "metadata": load_json(revision.metadata_json),
            "source": revision.source,
            "word_count": _word_count(revision.content_markdown),
            "created_at": iso(revision.created_at),
        }

    def _snapshot_payload(
        self,
        session: Session,
        snapshot: ProjectSnapshot,
    ) -> dict[str, Any]:
        documents = session.scalars(
            select(SnapshotDocument)
            .where(SnapshotDocument.snapshot_id == snapshot.id)
            .order_by(SnapshotDocument.position)
        ).all()
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
                for item in documents
            ],
        }

    @staticmethod
    def _snapshot_content(
        session: Session,
        snapshot_id: str,
    ) -> list[tuple[Document, DocumentRevision]]:
        rows = session.execute(
            select(Document, DocumentRevision)
            .join(SnapshotDocument, SnapshotDocument.document_id == Document.id)
            .join(
                DocumentRevision,
                DocumentRevision.id == SnapshotDocument.revision_id,
            )
            .where(SnapshotDocument.snapshot_id == snapshot_id)
            .order_by(SnapshotDocument.position, Document.created_at)
        ).all()
        return [(row[0], row[1]) for row in rows]

    def _review_payload(self, session: Session, review: Review) -> dict[str, Any]:
        issues = session.scalars(
            select(ReviewIssue)
            .where(ReviewIssue.review_id == review.id)
            .order_by(ReviewIssue.severity, ReviewIssue.code)
        ).all()
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
                    "evidence": load_json(issue.evidence_json),
                }
                for issue in issues
            ],
        }

    def _job_payload(self, session: Session, job: Job) -> dict[str, Any]:
        events = session.scalars(
            select(JobEvent)
            .where(JobEvent.job_id == job.id)
            .order_by(JobEvent.created_at)
        ).all()
        return {
            "id": job.id,
            "project_id": job.project_id,
            "document_id": job.document_id,
            "kind": job.kind,
            "operation": job.operation,
            "status": job.status,
            "provider": job.provider,
            "model": job.model,
            "request": load_json(job.request_json),
            "result": load_json(job.result_json),
            "error": job.error,
            "retry_of_job_id": job.retry_of_job_id,
            "created_at": iso(job.created_at),
            "updated_at": iso(job.updated_at),
            "events": [
                {
                    "id": event.id,
                    "status": event.status,
                    "details": load_json(event.details_json),
                    "created_at": iso(event.created_at),
                }
                for event in events
            ],
        }

    @staticmethod
    def _export_payload(item: Export) -> dict[str, Any]:
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

    @staticmethod
    def _deterministic_proposal(
        current: str,
        *,
        operation: str,
        instruction: str,
    ) -> str:
        instruction = instruction.strip()
        if operation == "rewrite":
            replacement = instruction or "Rewrite this passage with clearer action and stakes."
            return f"{current.rstrip()}\n\n<!-- Proposed rewrite: {replacement} -->\n"
        if operation == "continue":
            direction = instruction or "Continue from the current dramatic pressure."
            return (
                f"{current.rstrip()}\n\n"
                f"The next choice arrived before anyone was ready. {direction}\n"
            )
        return f"{current.rstrip()}\n\n{instruction}\n"

    @staticmethod
    def _write_markdown(
        path: Path,
        title: str,
        content: Iterable[tuple[Document, DocumentRevision]],
    ) -> None:
        parts = [f"# {title}"]
        parts.extend(revision.content_markdown.strip() for _, revision in content)
        path.write_text("\n\n".join(parts).strip() + "\n", encoding="utf-8")

    @staticmethod
    def _write_docx(
        path: Path,
        title: str,
        content: Iterable[tuple[Document, DocumentRevision]],
    ) -> None:
        from docx import Document as DocxDocument

        output = DocxDocument()
        output.add_heading(title, 0)
        for document, revision in content:
            output.add_heading(document.title, level=1)
            for paragraph in _plain_text(revision.content_markdown).split("\n\n"):
                if paragraph.strip():
                    output.add_paragraph(paragraph.strip())
        output.save(path)

    @staticmethod
    def _write_epub(
        path: Path,
        title: str,
        content: Iterable[tuple[Document, DocumentRevision]],
    ) -> None:
        from ebooklib import epub

        book = epub.EpubBook()
        book.set_identifier(new_id())
        book.set_title(title)
        book.set_language("en")
        chapters = []
        for index, (document, revision) in enumerate(content, start=1):
            chapter = epub.EpubHtml(
                title=document.title,
                file_name=f"chapter-{index:03d}.xhtml",
                lang="en",
            )
            paragraphs = "".join(
                f"<p>{_escape_html(paragraph)}</p>"
                for paragraph in _plain_text(revision.content_markdown).split("\n\n")
                if paragraph.strip()
            )
            chapter.content = f"<h1>{_escape_html(document.title)}</h1>{paragraphs}"
            book.add_item(chapter)
            chapters.append(chapter)
        book.toc = tuple(chapters)
        book.spine = ["nav", *chapters]
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        epub.write_epub(path, book)

    @staticmethod
    def _legacy_hash(root: Path, files: Iterable[Path]) -> str:
        digest = hashlib.sha256()
        digest.update(str(root).encode("utf-8"))
        for path in sorted(files):
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(path.read_bytes())
        return digest.hexdigest()


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


studio_store = StudioStore()
