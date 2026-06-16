from __future__ import annotations

from src.contexts.studio.application.service_common import (
    Any,
    InvalidOperation,
    Principal,
    StudioRepository,
    _owner_scopes,
    _project_payload,
    dump_json,
    utcnow,
)

__all__ = ["ProjectService"]


class ProjectService:
    """Project creation and mutation."""

    def __init__(self, repository: StudioRepository) -> None:
        self._repository = repository

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
        owner_id, guest_session_id = _owner_scopes(principal)
        project = self._repository.create_project(
            owner_id=owner_id,
            guest_session_id=guest_session_id,
            title=title,
            description=description.strip(),
            settings_json=dump_json({"provider": "mock"}),
            now=utcnow(),
            create_seed=create_seed,
        )
        return _project_payload(project)

    def list_projects(self, principal: Principal) -> list[dict[str, Any]]:
        owner_id, guest_session_id = _owner_scopes(principal)
        projects = self._repository.list_projects(
            owner_id=owner_id,
            guest_session_id=guest_session_id,
        )
        return [
            _project_payload(project, include_documents=False)
            for project in projects
        ]

    def get_project(self, principal: Principal, project_id: str) -> dict[str, Any]:
        owner_id, guest_session_id = _owner_scopes(principal)
        project = self._repository.get_project(
            project_id,
            owner_id=owner_id,
            guest_session_id=guest_session_id,
        )
        return _project_payload(project)

    def update_project(
        self,
        principal: Principal,
        project_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        owner_id, guest_session_id = _owner_scopes(principal)
        resolved_title = title.strip() if title is not None and title.strip() else None
        resolved_description = description.strip() if description is not None else None
        settings_json = dump_json(settings) if settings is not None else None
        project = self._repository.update_project(
            project_id,
            owner_id=owner_id,
            guest_session_id=guest_session_id,
            title=resolved_title,
            description=resolved_description,
            settings_json=settings_json,
            now=utcnow(),
        )
        return _project_payload(project)

    def delete_project(self, principal: Principal, project_id: str) -> None:
        owner_id, guest_session_id = _owner_scopes(principal)
        self._repository.delete_project(
            project_id,
            owner_id=owner_id,
            guest_session_id=guest_session_id,
        )
