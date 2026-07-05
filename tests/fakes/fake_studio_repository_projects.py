from __future__ import annotations

from datetime import datetime

from src.contexts.studio.application.ports.studio_repository import (
    DocumentDto,
    ProjectDto,
)
from src.contexts.studio.domain.exceptions import NotFound
from src.contexts.studio.domain.utils import new_id


class FakeStudioRepositoryProjectsMixin:
    _documents: dict[str, DocumentDto]
    _projects: dict[str, ProjectDto]

    def _create_seed_document(self, project_id: str, now: datetime) -> None:
        raise NotImplementedError

    def _delete_project_records(
        self,
        project_id: str,
        document_ids: set[str],
    ) -> None:
        raise NotImplementedError

    def _project_documents(self, project_id: str) -> list[DocumentDto]:
        raise NotImplementedError

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
