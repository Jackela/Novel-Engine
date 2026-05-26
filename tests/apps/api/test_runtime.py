"""Tests for guest-session canonical runtime behavior."""

from __future__ import annotations

import pytest

from src.apps.api.services.runtime import CanonicalRuntimeService


@pytest.mark.asyncio
async def test_guest_session_is_created_when_missing() -> None:
    runtime = CanonicalRuntimeService()

    session = await runtime.create_or_resume_guest_session(None)

    assert session.is_new_session is True
    assert session.workspace_id.startswith("guest-")


@pytest.mark.asyncio
async def test_guest_session_resume_reuses_known_workspace_id() -> None:
    runtime = CanonicalRuntimeService()
    created = await runtime.create_or_resume_guest_session(None)

    resumed = await runtime.create_or_resume_guest_session(created.workspace_id)

    assert resumed.workspace_id == created.workspace_id
    assert resumed.is_new_session is False


@pytest.mark.asyncio
async def test_guest_session_reset_forgets_known_sessions() -> None:
    runtime = CanonicalRuntimeService()
    created = await runtime.create_or_resume_guest_session(None)

    runtime.reset()
    resumed = await runtime.create_or_resume_guest_session(created.workspace_id)

    assert resumed.workspace_id == created.workspace_id
    assert resumed.is_new_session is True
