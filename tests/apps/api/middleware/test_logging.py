from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.apps.api.middleware.logging import (
    LoggingMiddleware,
    RequestContext,
    logging_middleware,
)


def test_api_logging_middleware_compat_export_passes_response() -> None:
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)

    @app.get("/logged")
    async def logged() -> dict[str, str]:
        return {"status": "ok"}

    response = TestClient(app).get("/logged")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_logging_function_wrapper_adds_request_id_header() -> None:
    app = FastAPI()
    app.middleware("http")(logging_middleware)

    @app.get("/logged-function")
    async def logged_function(request: Request) -> dict[str, str]:
        return {"request_id": getattr(request.state, "request_id", "")}

    response = TestClient(app).get("/logged-function")

    assert response.status_code == 200
    assert response.json()["request_id"]


def test_request_context_binds_logger() -> None:
    with RequestContext(request_id="req-1") as logger:
        assert logger is not None
