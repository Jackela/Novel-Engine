"""Tests for refresh-session storage."""

from datetime import timedelta

from src.shared.infrastructure.auth import refresh_sessions
from src.shared.infrastructure.auth.refresh_sessions import (
    InMemoryRefreshSessionStore,
    get_refresh_session_store,
    reset_refresh_session_store,
)


def test_create_and_verify_refresh_session() -> None:
    store = InMemoryRefreshSessionStore()

    issue = store.create(
        user_id="user-1",
        expires_in_days=7,
        user_snapshot={"email": "author@example.com"},
    )

    assert issue.raw_token.startswith(f"{issue.session.session_id}.")
    assert issue.session.user_id == "user-1"
    assert issue.session.user_snapshot == {"email": "author@example.com"}
    assert issue.session.is_active
    assert store.verify(issue.raw_token) is issue.session
    assert store.verify("not-a-token") is None


def test_expired_session_is_not_verified() -> None:
    store = InMemoryRefreshSessionStore()
    issue = store.create(user_id="user-1", expires_in_days=7)
    issue.session.expires_at = refresh_sessions._now() - timedelta(seconds=1)

    assert not issue.session.is_active
    assert store.verify(issue.raw_token) is None


def test_rotate_revokes_old_session_and_preserves_user_snapshot() -> None:
    store = InMemoryRefreshSessionStore()
    issue = store.create(
        user_id="user-1",
        expires_in_days=7,
        user_snapshot={"name": "Author"},
    )

    rotated = store.rotate(raw_token=issue.raw_token, expires_in_days=7)

    assert rotated is not None
    assert rotated.raw_token != issue.raw_token
    assert rotated.session.user_id == "user-1"
    assert rotated.session.user_snapshot == {"name": "Author"}
    assert issue.session.revoked_at is not None
    assert issue.session.rotated_at == issue.session.revoked_at
    assert issue.session.rotated_to == rotated.session.session_id
    assert store.verify(issue.raw_token) is None
    assert store.verify(rotated.raw_token) is rotated.session
    assert store.rotate(raw_token=issue.raw_token, expires_in_days=7) is None


def test_revoke_invalid_empty_and_existing_tokens() -> None:
    store = InMemoryRefreshSessionStore()
    issue = store.create(user_id="user-1", expires_in_days=7)

    store.revoke(None)
    store.revoke("")
    store.revoke("missing-token")
    assert store.verify(issue.raw_token) is issue.session

    store.revoke(issue.raw_token)

    assert issue.session.revoked_at is not None
    assert issue.session.updated_at == issue.session.revoked_at
    assert store.verify(issue.raw_token) is None


def test_reset_clears_refresh_sessions() -> None:
    store = InMemoryRefreshSessionStore()
    issue = store.create(user_id="user-1", expires_in_days=7)

    store.reset()

    assert store.verify(issue.raw_token) is None


def test_global_refresh_session_store_can_be_reset() -> None:
    reset_refresh_session_store()
    store = get_refresh_session_store()
    issue = store.create(user_id="user-1", expires_in_days=7)

    reset_refresh_session_store()

    assert get_refresh_session_store() is store
    assert store.verify(issue.raw_token) is None
