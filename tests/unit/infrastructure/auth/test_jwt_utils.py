from __future__ import annotations

from datetime import datetime, timedelta

import jwt
import pytest

from src.shared.infrastructure.auth.jwt_utils import (
    InvalidTokenError,
    JWTManager,
    TokenExpiredError,
)

SECRET = "test-secret-key-with-enough-entropy-12345"


def test_jwt_manager_rejects_short_secret() -> None:
    with pytest.raises(ValueError, match="at least 32 characters"):
        JWTManager("short")


def test_access_and_refresh_tokens_round_trip() -> None:
    manager = JWTManager(SECRET)

    access_token = manager.create_access_token(
        user_id="user-1",
        username="operator",
        email="operator@novel.engine",
        roles=["author"],
        additional_claims={"tenant": "workspace-1"},
    )
    refresh_token = manager.create_refresh_token(
        user_id="user-1",
        additional_claims={"session": "session-1"},
    )

    access_payload = manager.verify_access_token(access_token)
    refresh_payload = manager.verify_refresh_token(refresh_token)

    assert access_payload["sub"] == "user-1"
    assert access_payload["username"] == "operator"
    assert access_payload["roles"] == ["author"]
    assert access_payload["tenant"] == "workspace-1"
    assert access_payload["type"] == "access"
    assert refresh_payload["sub"] == "user-1"
    assert refresh_payload["session"] == "session-1"
    assert refresh_payload["type"] == "refresh"


def test_token_type_specific_verifiers_reject_other_token_types() -> None:
    manager = JWTManager(SECRET)
    access_token = manager.create_access_token(
        user_id="user-1",
        username="operator",
        email="operator@novel.engine",
    )
    refresh_token = manager.create_refresh_token(user_id="user-1")

    with pytest.raises(InvalidTokenError, match="not a refresh token"):
        manager.verify_refresh_token(access_token)

    with pytest.raises(InvalidTokenError, match="not an access token"):
        manager.verify_access_token(refresh_token)


def test_expired_token_raises_token_expired_error() -> None:
    token = jwt.encode(
        {
            "sub": "user-1",
            "type": "access",
            "iat": datetime.utcnow() - timedelta(hours=2),
            "exp": datetime.utcnow() - timedelta(hours=1),
        },
        SECRET,
        algorithm="HS256",
    )
    manager = JWTManager(SECRET)

    with pytest.raises(TokenExpiredError, match="expired"):
        manager.verify_access_token(token)


def test_invalid_token_raises_invalid_token_error() -> None:
    manager = JWTManager(SECRET)

    with pytest.raises(InvalidTokenError, match="Invalid token"):
        manager.verify_token("not-a-jwt")


def test_get_token_expiry_decodes_without_signature_verification() -> None:
    manager = JWTManager(SECRET)
    token = manager.create_refresh_token("user-1")

    expiry = manager.get_token_expiry(token)

    assert expiry > datetime.utcnow()


def test_get_token_expiry_rejects_tokens_without_expiration() -> None:
    token = jwt.encode(
        {"sub": "user-1", "type": "access"},
        SECRET,
        algorithm="HS256",
    )
    manager = JWTManager(SECRET)

    with pytest.raises(InvalidTokenError, match="no expiration"):
        manager.get_token_expiry(token)


def test_refresh_access_token_uses_subject_from_refresh_token() -> None:
    manager = JWTManager(SECRET)
    refresh_token = manager.create_refresh_token("user-1")

    access_token = manager.refresh_access_token(
        refresh_token,
        username="operator",
        email="operator@novel.engine",
        roles=["author"],
    )

    payload = manager.verify_access_token(access_token)
    assert payload["sub"] == "user-1"
    assert payload["username"] == "operator"
    assert payload["roles"] == ["author"]
