"""Shared fixtures for Studio application service unit tests."""

from __future__ import annotations

import pytest

from src.contexts.studio.application.service_common import Principal
from tests.fakes.fake_studio_repository import FakeStudioRepository


@pytest.fixture
def fake_repository() -> FakeStudioRepository:
    return FakeStudioRepository()


@pytest.fixture
def guest_principal() -> Principal:
    return Principal(
        session_id="guest-session-1",
        kind="guest",
        owner_id=None,
        expires_at=None,
    )
