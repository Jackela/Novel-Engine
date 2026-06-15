from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _guest_client(app: FastAPI) -> TestClient:
    client = TestClient(app, raise_server_exceptions=False)
    session = client.post("/api/session/guest")
    assert session.status_code == 201
    return client


def _csrf_cookie(client: TestClient) -> str:
    value = client.cookies.get("novel_studio_csrf")
    assert value is not None
    return value


def test_login_and_guest_set_csrf_cookie(canonical_app: FastAPI) -> None:
    client = TestClient(canonical_app, raise_server_exceptions=False)

    guest = client.post("/api/session/guest")
    assert guest.status_code == 201
    assert "novel_studio_csrf" in guest.cookies

    setup = client.post(
        "/api/setup",
        json={"username": "owner", "password": "owner-password-123"},
    )
    assert setup.status_code == 201
    login = client.post(
        "/api/session/login",
        json={"username": "owner", "password": "owner-password-123"},
    )
    assert login.status_code == 200
    assert "novel_studio_csrf" in login.cookies


def test_write_without_csrf_header_is_forbidden(canonical_app: FastAPI) -> None:
    client = _guest_client(canonical_app)
    response = client.post(
        "/api/projects",
        json={"title": "No CSRF"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF token missing."


def test_write_with_wrong_csrf_header_is_forbidden(canonical_app: FastAPI) -> None:
    client = _guest_client(canonical_app)
    response = client.post(
        "/api/projects",
        json={"title": "Bad CSRF"},
        headers={"X-CSRF-Token": "not-the-cookie-value"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF token invalid."


def test_write_with_correct_csrf_header_succeeds(canonical_app: FastAPI) -> None:
    client = _guest_client(canonical_app)
    token = _csrf_cookie(client)
    response = client.post(
        "/api/projects",
        json={"title": "Valid CSRF"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 201
    assert response.json()["title"] == "Valid CSRF"


def test_get_session_does_not_require_csrf_header(canonical_app: FastAPI) -> None:
    client = _guest_client(canonical_app)
    response = client.get("/api/session")
    assert response.status_code == 200


def test_logout_without_csrf_header_is_forbidden(canonical_app: FastAPI) -> None:
    client = _guest_client(canonical_app)
    response = client.delete("/api/session")
    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF token missing."


def test_logout_with_correct_csrf_header_succeeds(canonical_app: FastAPI) -> None:
    client = _guest_client(canonical_app)
    token = _csrf_cookie(client)
    response = client.delete(
        "/api/session",
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 204
