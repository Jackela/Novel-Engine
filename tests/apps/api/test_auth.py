"""Tests for canonical authentication flows."""

from __future__ import annotations


def test_login_accepts_email_and_returns_workspace_profile(canonical_client) -> None:
    response = canonical_client.post(
        "/api/v1/auth/login",
        json={
            "email": "operator@novel.engine",
            "password": "demo-password",
        },
    )

    assert response.status_code == 200
    assert "set-cookie" in response.headers

    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["workspace_id"] == "user-operator"
    assert payload["user"]["id"]
    assert payload["user"]["name"] == "operator"
    assert payload["user"]["email"] == "operator@novel.engine"
    assert payload["user"]["roles"] == ["author"]

    dashboard_response = canonical_client.get("/api/v1/dashboard/status")
    assert dashboard_response.status_code == 200
    assert dashboard_response.json()["workspaceId"] == payload["workspace_id"]


def test_login_reuses_existing_guest_workspace_cookie(canonical_client) -> None:
    guest_response = canonical_client.post("/api/v1/guest/session")
    assert guest_response.status_code == 200

    guest_workspace_id = guest_response.json()["workspace_id"]

    response = canonical_client.post(
        "/api/v1/auth/login",
        json={
            "username": "operator",
            "password": "demo-password",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_id"] == guest_workspace_id
    assert payload["user"]["name"] == "operator"
    assert payload["user"]["email"] == "operator@novel.engine"
