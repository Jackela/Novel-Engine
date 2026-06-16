"""Unit tests for DocumentService using the fake repository."""

from __future__ import annotations

import pytest

from src.contexts.studio.application.service_common import (
    Principal,
    RevisionConflict,
)
from src.contexts.studio.application.services.document_service import DocumentService
from src.contexts.studio.application.services.project_service import ProjectService
from tests.fakes.fake_studio_repository import FakeStudioRepository


def _guest(session_id: str) -> Principal:
    return Principal(
        session_id=session_id,
        kind="guest",
        owner_id=None,
        expires_at=None,
    )


def test_save_document_creates_new_revision(
    fake_repository: FakeStudioRepository,
) -> None:
    principal = _guest("guest-session-1")
    project = ProjectService(fake_repository).create_project(
        principal, title="Document Test"
    )
    document = project["documents"][0]
    service = DocumentService(fake_repository)

    result = service.save_document(
        principal,
        project["id"],
        document["id"],
        content_markdown="# Chapter 1\n\nUpdated content.",
        base_revision_id=document["current_revision_id"],
    )

    assert result["content_markdown"] == "# Chapter 1\n\nUpdated content."
    assert result["current_revision_id"] != document["current_revision_id"]


def test_save_document_with_stale_base_raises_revision_conflict(
    fake_repository: FakeStudioRepository,
) -> None:
    principal = _guest("guest-session-1")
    project = ProjectService(fake_repository).create_project(
        principal, title="Conflict Test"
    )
    document = project["documents"][0]
    service = DocumentService(fake_repository)
    original_revision_id = document["current_revision_id"]
    service.save_document(
        principal,
        project["id"],
        document["id"],
        content_markdown="First update.",
        base_revision_id=original_revision_id,
    )

    with pytest.raises(RevisionConflict):
        service.save_document(
            principal,
            project["id"],
            document["id"],
            content_markdown="Stale update.",
            base_revision_id=original_revision_id,
        )


def test_save_document_can_update_title_and_metadata(
    fake_repository: FakeStudioRepository,
) -> None:
    principal = _guest("guest-session-1")
    project = ProjectService(fake_repository).create_project(
        principal, title="Metadata Test"
    )
    document = project["documents"][0]
    service = DocumentService(fake_repository)

    result = service.save_document(
        principal,
        project["id"],
        document["id"],
        content_markdown="Content.",
        base_revision_id=document["current_revision_id"],
        title="New Title",
        metadata={"source": "test"},
    )

    assert result["title"] == "New Title"
    assert result["metadata"] == {"source": "test"}


def test_search_ignores_malicious_operators(
    fake_repository: FakeStudioRepository,
) -> None:
    principal = _guest("guest-session-1")
    project = ProjectService(fake_repository).create_project(
        principal, title="Search Test"
    )
    document = project["documents"][0]
    DocumentService(fake_repository).save_document(
        principal,
        project["id"],
        document["id"],
        content_markdown="The lighthouse went dark.",
        base_revision_id=document["current_revision_id"],
    )

    results = DocumentService(fake_repository).search(
        principal, project["id"], 'lighthouse" OR title:Chapter*'
    )

    assert results == []
