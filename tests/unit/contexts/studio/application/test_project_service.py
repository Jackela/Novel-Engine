"""Unit tests for ProjectService using the fake repository."""

from __future__ import annotations

import pytest

from src.contexts.studio.application.service_common import InvalidOperation, Principal
from src.contexts.studio.application.services.project_service import ProjectService
from tests.fakes.fake_studio_repository import FakeStudioRepository


def test_create_project_returns_project_with_seed_document(
    fake_repository: FakeStudioRepository,
    guest_principal: Principal,
) -> None:
    service = ProjectService(fake_repository)

    result = service.create_project(
        guest_principal,
        title="Test Project",
        description="A unit test project.",
    )

    assert result["title"] == "Test Project"
    assert result["description"] == "A unit test project."
    assert result["settings"] == {"provider": "mock"}
    assert len(result["documents"]) == 1
    document = result["documents"][0]
    assert document["title"] == "Chapter 1"
    assert document["kind"] == "chapter"
    assert document["content_markdown"] == "# Chapter 1\n\n"


def test_create_project_without_seed_has_no_documents(
    fake_repository: FakeStudioRepository,
    guest_principal: Principal,
) -> None:
    service = ProjectService(fake_repository)

    result = service.create_project(
        guest_principal,
        title="Empty Project",
        create_seed=False,
    )

    assert result["documents"] == []


def test_create_project_rejects_blank_title(
    fake_repository: FakeStudioRepository,
    guest_principal: Principal,
) -> None:
    service = ProjectService(fake_repository)

    with pytest.raises(InvalidOperation, match="Project title is required"):
        service.create_project(guest_principal, title="   ")


def test_list_projects_is_scoped_to_principal(
    fake_repository: FakeStudioRepository,
) -> None:
    guest = Principal(
        session_id="guest-session-1",
        kind="guest",
        owner_id=None,
        expires_at=None,
    )
    other_guest = Principal(
        session_id="guest-session-2",
        kind="guest",
        owner_id=None,
        expires_at=None,
    )
    service = ProjectService(fake_repository)
    service.create_project(guest, title="Guest Project")

    guest_projects = service.list_projects(guest)
    other_projects = service.list_projects(other_guest)

    assert len(guest_projects) == 1
    assert len(other_projects) == 0
