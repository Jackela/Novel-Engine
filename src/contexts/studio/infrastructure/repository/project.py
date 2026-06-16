from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete
from sqlalchemy.orm import selectinload

from src.contexts.studio.infrastructure.models import ProjectSnapshot, SnapshotDocument
from src.contexts.studio.infrastructure.repository.common import (
    Any,
    Document,
    DocumentDto,
    DocumentRevision,
    NotFound,
    Project,
    ProjectDto,
    Session,
    StudioDatabase,
    _document_dto,
    _session,
    cast,
    datetime,
    dump_json,
    new_id,
    select,
    text,
)

__all__ = ["ProjectRepositoryMixin"]


class ProjectRepositoryMixin:
    database: StudioDatabase

    if TYPE_CHECKING:

        def _refresh_search(
            self,
            session: Session,
            document: Document,
            revision: DocumentRevision,
        ) -> None: ...

    def _project(
        self,
        session: Session,
        project_id: str,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> Project:
        statement = select(Project).where(Project.id == project_id)
        statement = self._scope_projects(statement, owner_id, guest_session_id)
        project = session.scalar(statement)
        if project is None:
            raise NotFound("Project not found.")
        return cast(Project, project)

    @staticmethod
    def _scope_projects(
        statement: Any,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> Any:
        if owner_id:
            return statement.where(Project.owner_id == owner_id)
        return statement.where(Project.guest_session_id == guest_session_id)

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
        session: Session | None = None,
    ) -> ProjectDto:
        with _session(self.database, session) as db_session:
            project = Project(
                id=new_id(),
                owner_id=owner_id,
                guest_session_id=guest_session_id,
                title=title,
                description=description,
                settings_json=settings_json,
                created_at=now,
                updated_at=now,
            )
            db_session.add(project)
            db_session.flush()
            documents: list[DocumentDto] = []
            if create_seed:
                document = Document(
                    id=new_id(),
                    project_id=project.id,
                    kind="chapter",
                    title="Chapter 1",
                    position=1,
                    created_at=now,
                    updated_at=now,
                )
                db_session.add(document)
                db_session.flush()
                revision = DocumentRevision(
                    id=new_id(),
                    document_id=document.id,
                    parent_revision_id=None,
                    revision_number=1,
                    content_markdown="# Chapter 1\n\n",
                    metadata_json=dump_json({}),
                    source="author",
                    created_at=now,
                )
                db_session.add(revision)
                db_session.flush()
                document.current_revision_id = revision.id
                self._refresh_search(db_session, document, revision)
                documents.append(_document_dto(document))
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
                documents=documents,
            )

    def list_projects(
        self,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
        session: Session | None = None,
    ) -> list[ProjectDto]:
        with _session(self.database, session) as db_session:
            statement = (
                select(Project)
                .order_by(Project.updated_at.desc())
                .options(selectinload(Project.documents).selectinload(Document.revisions))
            )
            statement = self._scope_projects(statement, owner_id, guest_session_id)
            projects = db_session.scalars(statement).all()
            return [
                ProjectDto(
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
                for project in projects
            ]

    def get_project(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
        session: Session | None = None,
    ) -> ProjectDto:
        with _session(self.database, session) as db_session:
            project = self._project(db_session, project_id, owner_id, guest_session_id)
            documents = db_session.scalars(
                select(Document)
                .where(Document.project_id == project.id)
                .order_by(Document.kind, Document.position, Document.created_at)
                .options(selectinload(Document.revisions))
            ).all()
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
                documents=[_document_dto(document) for document in documents],
            )

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
        session: Session | None = None,
    ) -> ProjectDto:
        with _session(self.database, session) as db_session:
            project = self._project(db_session, project_id, owner_id, guest_session_id)
            if title is not None:
                project.title = title
            if description is not None:
                project.description = description
            if settings_json is not None:
                project.settings_json = settings_json
            project.updated_at = now
            documents = db_session.scalars(
                select(Document)
                .where(Document.project_id == project.id)
                .order_by(Document.kind, Document.position, Document.created_at)
            ).all()
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
                documents=[_document_dto(document) for document in documents],
            )

    def delete_project(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
        session: Session | None = None,
    ) -> None:
        with _session(self.database, session) as db_session:
            project = self._project(db_session, project_id, owner_id, guest_session_id)
            db_session.execute(
                text("DELETE FROM document_search WHERE project_id = :project_id"),
                {"project_id": project.id},
            )
            snapshot_ids = db_session.scalars(
                select(ProjectSnapshot.id).where(ProjectSnapshot.project_id == project.id)
            ).all()
            if snapshot_ids:
                db_session.execute(
                    delete(SnapshotDocument).where(
                        SnapshotDocument.snapshot_id.in_(snapshot_ids)
                    )
                )
                db_session.execute(
                    delete(ProjectSnapshot).where(ProjectSnapshot.id.in_(snapshot_ids))
                )
            db_session.delete(project)

    def find_project_by_import_hash(
        self,
        import_hash: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
        session: Session | None = None,
    ) -> ProjectDto | None:
        with _session(self.database, session) as db_session:
            statement = select(Project).where(Project.import_hash == import_hash)
            statement = self._scope_projects(statement, owner_id, guest_session_id)
            project = db_session.scalar(statement)
            if project is None:
                return None
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

    def set_project_import_hash(
        self,
        project_id: str,
        import_hash: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
        session: Session | None = None,
    ) -> None:
        with _session(self.database, session) as db_session:
            project = self._project(db_session, project_id, owner_id, guest_session_id)
            project.import_hash = import_hash
