from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from src.apps.api.middleware import error_handler as error_handler_module
from src.apps.api.middleware.error_handler import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationAPIError,
    format_validation_errors,
    setup_exception_handlers,
)


class Payload(BaseModel):
    count: int


class SensitivePayload(BaseModel):
    token: int


def make_app() -> FastAPI:
    app = FastAPI()
    setup_exception_handlers(app)

    @app.get("/api-error")
    async def api_error() -> None:
        raise APIError(
            "custom failure",
            status_code=418,
            error_code="CUSTOM",
            details={"hint": "retry"},
        )

    @app.get("/http-error")
    async def http_error() -> None:
        raise HTTPException(status_code=404, detail="missing")

    @app.post("/request-validation")
    async def request_validation(payload: Payload) -> Payload:
        return payload

    @app.post("/sensitive-validation")
    async def sensitive_validation(payload: SensitivePayload) -> SensitivePayload:
        return payload

    @app.get("/pydantic-validation")
    async def pydantic_validation() -> None:
        Payload(count="bad")

    @app.get("/unhandled")
    async def unhandled() -> None:
        raise RuntimeError("boom")

    return app


def test_api_error_subclasses_set_expected_codes() -> None:
    assert NotFoundError("Story", "story-1").error_code == "NOT_FOUND"
    assert ConflictError("conflict").status_code == 409
    assert ValidationAPIError("bad input").status_code == 422
    assert AuthenticationError().status_code == 401
    assert AuthorizationError().status_code == 403


def test_format_validation_errors_flattens_locations() -> None:
    try:
        Payload(count="bad")
    except ValidationError as exc:
        formatted = format_validation_errors(exc.errors())

    assert formatted == [
        {
            "field": ".count",
            "message": "Input should be a valid integer, unable to parse string as an integer",
            "type": "int_parsing",
        }
    ]


def test_api_error_handler_response_shape() -> None:
    response = TestClient(make_app()).get("/api-error")

    assert response.status_code == 418
    assert response.json() == {
        "error": {
            "code": "CUSTOM",
            "message": "custom failure",
            "details": {"hint": "retry"},
        }
    }


def test_http_exception_handler_response_shape() -> None:
    response = TestClient(make_app()).get("/http-error")

    assert response.status_code == 404
    assert response.json() == {"detail": "missing"}


def test_request_validation_handler_response_shape() -> None:
    response = TestClient(make_app()).post(
        "/request-validation",
        json={"count": "bad"},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["message"] == "Request validation failed"
    assert payload["error"]["details"]["errors"][0]["field"] == ".body.count"


def test_request_validation_log_uses_safe_whitelist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    warning = AsyncMock()
    monkeypatch.setattr(
        error_handler_module, "logger", SimpleNamespace(awarning=warning)
    )

    response = TestClient(make_app()).post(
        "/sensitive-validation",
        json={"token": "super-secret-token"},
    )

    assert response.status_code == 422
    warning.assert_awaited_once()
    call = warning.await_args
    assert call is not None
    _, kwargs = call
    assert kwargs["path"] == "/sensitive-validation"
    assert kwargs["method"] == "POST"
    assert kwargs["errors"][0].keys() == {"field", "message", "type"}
    serialized = repr(kwargs)
    assert "input" not in serialized
    assert "super-secret-token" not in serialized


def test_pydantic_validation_handler_response_shape() -> None:
    response = TestClient(make_app()).get("/pydantic-validation")

    assert response.status_code == 422
    assert response.json()["error"]["message"] == "Data validation failed"


def test_pydantic_validation_log_uses_safe_whitelist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    warning = AsyncMock()
    monkeypatch.setattr(
        error_handler_module, "logger", SimpleNamespace(awarning=warning)
    )

    response = TestClient(make_app()).get("/pydantic-validation")

    assert response.status_code == 422
    warning.assert_awaited_once()
    call = warning.await_args
    assert call is not None
    _, kwargs = call
    assert kwargs["path"] == "/pydantic-validation"
    assert kwargs["method"] == "GET"
    assert kwargs["errors"][0].keys() == {"field", "message", "type"}
    assert "input" not in repr(kwargs)


def test_general_exception_handler_hides_internal_message() -> None:
    response = TestClient(make_app(), raise_server_exceptions=False).get("/unhandled")

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["code"] == "INTERNAL_ERROR"
    assert payload["error"]["message"] == "An unexpected error occurred"
    assert payload["error"]["error_id"]
