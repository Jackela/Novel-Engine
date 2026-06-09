"""Tests for canonical authentication flows."""

from __future__ import annotations

from typing import Any


def test_login_accepts_email_and_returns_workspace_profile(
    canonical_client: Any,
) -> None:
    response = canonical_client.post(
        "/api/auth/login",
        json={
            "email": "operator@novel.engine",
            "password": "demo-password",
        },
    )

    assert response.status_code == 200
    assert "set-cookie" in response.headers

    payload = response.json()
    assert "access_token" not in payload
    assert "refresh_token" not in payload
    assert "novel_engine_access=" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert payload["workspace_id"].startswith("user-")
    assert payload["workspace_id"] != "user-operator"
    assert payload["active_workspace"]["workspace_id"] == payload["workspace_id"]
    assert payload["user"]["id"]
    assert payload["user"]["name"] == "operator"
    assert payload["user"]["email"] == "operator@novel.engine"
    assert payload["user"]["roles"] == ["author"]

    workspace_response = canonical_client.post(
        "/api/workspaces",
        json={
            "workspace_id": "logged-in-workspace",
            "title": "Logged-In Workspace",
            "genre": "fantasy",
            "premise": "A stolen crown reveals the hidden architecture of the empire.",
            "target_chapters": 3,
        },
    )
    assert workspace_response.status_code == 201
    assert workspace_response.json()["workspace_id"] == "logged-in-workspace"

    current_response = canonical_client.get("/api/auth/me")
    assert current_response.status_code == 200
    current = current_response.json()
    assert current["workspace_id"] == payload["workspace_id"]
    assert current["active_workspace"]["workspace_id"] == payload["workspace_id"]
    assert current["username"] == "operator"


def test_login_promotes_guest_cookie_to_user_workspace(
    canonical_client: Any,
) -> None:
    guest_response = canonical_client.post("/api/guest/session")
    assert guest_response.status_code == 200

    guest_workspace_id = guest_response.json()["workspace_id"]

    response = canonical_client.post(
        "/api/auth/login",
        json={
            "username": "operator",
            "password": "demo-password",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_id"].startswith("user-")
    assert payload["workspace_id"] != guest_workspace_id
    assert payload["user"]["name"] == "operator"
    assert payload["user"]["email"] == "operator@novel.engine"


def test_registered_username_with_punctuation_gets_safe_workspace(
    canonical_client: Any,
) -> None:
    register_response = canonical_client.post(
        "/api/auth/register",
        json={
            "email": "writer-dot@example.test",
            "username": "writer.name",
            "password": "supersecret",
        },
    )
    assert register_response.status_code == 201

    login_response = canonical_client.post(
        "/api/auth/login",
        json={"username": "writer.name", "password": "supersecret"},
    )
    assert login_response.status_code == 200
    workspace_id = login_response.json()["workspace_id"]
    assert workspace_id.startswith("user-")
    assert "." not in workspace_id
    current_response = canonical_client.get("/api/auth/me")
    assert current_response.status_code == 200
    assert current_response.json()["workspace_id"] == workspace_id

    workspace_response = canonical_client.post(
        "/api/workspaces",
        json={
            "workspace_id": "safe-user-story",
            "title": "Safe User Story",
            "genre": "mystery",
            "premise": "A writer proves punctuation cannot escape the workspace root.",
            "target_chapters": 1,
        },
    )
    assert workspace_response.status_code == 201


def test_guest_launch_does_not_reuse_user_workspace_cookie(
    canonical_client: Any,
) -> None:
    login_response = canonical_client.post(
        "/api/auth/login",
        json={
            "email": "operator@novel.engine",
            "password": "demo-password",
        },
    )

    assert login_response.status_code == 200
    user_workspace_id = login_response.json()["workspace_id"]
    assert user_workspace_id.startswith("user-")
    assert user_workspace_id != "user-operator"

    guest_response = canonical_client.post("/api/guest/session")

    assert guest_response.status_code == 200
    payload = guest_response.json()
    assert payload["workspace_id"].startswith("guest-")
    assert payload["workspace_id"] != user_workspace_id


def test_guest_workspace_cookie_selects_guest_then_me_restores_user_workspace(
    canonical_client: Any,
) -> None:
    login_response = canonical_client.post(
        "/api/auth/login",
        json={
            "email": "operator@novel.engine",
            "password": "demo-password",
        },
    )
    assert login_response.status_code == 200
    user_workspace_id = login_response.json()["workspace_id"]

    user_workspace_response = canonical_client.post(
        "/api/workspaces",
        json={
            "workspace_id": "user-cookie-story",
            "title": "User Cookie Story",
            "genre": "fantasy",
            "premise": "A signed-in author keeps one manuscript in the persistent library.",
            "target_chapters": 1,
        },
    )
    assert user_workspace_response.status_code == 201

    guest_response = canonical_client.post("/api/guest/session")
    assert guest_response.status_code == 200
    guest_workspace_id = guest_response.json()["workspace_id"]
    assert guest_workspace_id.startswith("guest-")
    assert guest_workspace_id != user_workspace_id

    guest_workspace_response = canonical_client.post(
        "/api/workspaces",
        json={
            "workspace_id": "guest-cookie-story",
            "title": "Guest Cookie Story",
            "genre": "mystery",
            "premise": "A guest author keeps a separate disposable manuscript.",
            "target_chapters": 1,
        },
    )
    assert guest_workspace_response.status_code == 201

    guest_list_response = canonical_client.get("/api/workspaces")
    assert guest_list_response.status_code == 200
    assert [
        workspace["workspace_id"]
        for workspace in guest_list_response.json()["workspaces"]
    ] == ["guest-cookie-story"]

    current_response = canonical_client.get("/api/auth/me")
    assert current_response.status_code == 200
    assert current_response.json()["workspace_id"] == user_workspace_id
    assert f"novel_engine_workspace={user_workspace_id}" in current_response.headers["set-cookie"]

    user_list_response = canonical_client.get("/api/workspaces")
    assert user_list_response.status_code == 200
    assert [
        workspace["workspace_id"]
        for workspace in user_list_response.json()["workspaces"]
    ] == ["user-cookie-story"]


def test_login_with_invalid_credentials_returns_401(
    canonical_client: Any,
) -> None:
    response = canonical_client.post(
        "/api/auth/login",
        json={
            "email": "operator@novel.engine",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "HTTP_ERROR",
            "message": "Invalid credentials",
        }
    }
