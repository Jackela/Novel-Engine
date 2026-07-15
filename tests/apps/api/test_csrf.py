from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from src.contexts.studio.infrastructure.models import Owner
from src.shared.infrastructure.config.settings import Environment


def _guest_client(app: FastAPI) -> TestClient:
    client = TestClient(app, raise_server_exceptions=False)
    session = client.post("/api/session/guest")
    assert session.status_code == 201
    return client


def _csrf_cookie(client: TestClient) -> str:
    value = client.cookies.get("novel_studio_csrf")
    assert isinstance(value, str)
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


def test_session_cookie_api_and_csrf_contract_shape_is_stable(
    canonical_app: FastAPI,
) -> None:
    client = TestClient(canonical_app, raise_server_exceptions=False)

    response = client.post("/api/session/guest")

    assert response.status_code == 201
    assert set(response.json()) == {
        "session_id",
        "kind",
        "owner_id",
        "expires_at",
    }
    assert response.json()["kind"] == "guest"
    assert response.cookies.get("novel_studio_session")
    assert response.cookies.get("novel_studio_csrf")

    current = client.get("/api/session")
    assert current.status_code == 200
    assert set(current.json()) == set(response.json())

    csrf_token = _csrf_cookie(client)
    project = client.post(
        "/api/projects",
        json={"title": "Contract shape"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert project.status_code == 201


def test_setup_rejects_cross_site_origin_without_csrf_cookie(
    canonical_app: FastAPI,
) -> None:
    client = TestClient(canonical_app, raise_server_exceptions=False)
    response = client.post(
        "/api/setup",
        json={"username": "owner", "password": "owner-password-123"},
        headers={"Origin": "https://evil.example"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Setup requests must be same-origin."
    assert not canonical_app.state.studio_store.owner_exists()


def test_setup_accepts_configured_vite_origin(canonical_app: FastAPI) -> None:
    client = TestClient(canonical_app, raise_server_exceptions=False)
    response = client.post(
        "/api/setup",
        json={"username": "owner", "password": "owner-password-123"},
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 201


def test_concurrent_setup_creates_only_one_owner(canonical_app: FastAPI) -> None:
    def setup_owner() -> int:
        client = TestClient(canonical_app, raise_server_exceptions=False)
        response = client.post(
            "/api/setup",
            json={"username": "owner", "password": "owner-password-123"},
        )
        return int(response.status_code)

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(lambda _: setup_owner(), range(2)))

    assert sorted(statuses) == [201, 422]
    database = canonical_app.state.studio_runtime.database
    with database.session() as session:
        assert session.scalar(select(func.count()).select_from(Owner)) == 1


def test_staging_session_cookies_are_secure(canonical_app: FastAPI) -> None:
    canonical_app.state.settings.environment = Environment.STAGING
    client = TestClient(canonical_app, raise_server_exceptions=False)

    response = client.post("/api/session/guest")

    assert response.status_code == 201
    assert "Secure" in response.headers["set-cookie"]


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


def test_canonical_client_injects_csrf_header_for_writes(
    canonical_client: TestClient,
) -> None:
    guest = canonical_client.post("/api/session/guest")
    assert guest.status_code == 201

    response = canonical_client.post(
        "/api/projects",
        json={"title": "Fixture CSRF"},
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Fixture CSRF"


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
