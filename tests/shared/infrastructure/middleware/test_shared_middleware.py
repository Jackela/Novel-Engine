from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.shared.infrastructure.middleware import (
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
    CorrelationIdMiddleware,
    LoggingMiddleware,
    MetricsMiddleware,
    get_correlation_id,
    get_correlation_id_from_context,
    get_request_id,
    http_requests_in_progress,
    http_requests_total,
)


def test_correlation_middleware_preserves_inbound_id_and_adds_request_id() -> None:
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/probe")
    async def probe(request: Request) -> dict[str, str]:
        return {
            "correlation_id": get_correlation_id(request),
            "request_id": get_request_id(request),
            "context_correlation_id": get_correlation_id_from_context() or "",
        }

    response = TestClient(app).get(
        "/probe",
        headers={CORRELATION_ID_HEADER: "corr-123"},
    )

    assert response.status_code == 200
    assert response.headers[CORRELATION_ID_HEADER] == "corr-123"
    assert response.headers[REQUEST_ID_HEADER]
    assert response.json()["correlation_id"] == "corr-123"
    assert response.json()["context_correlation_id"] == "corr-123"


def test_correlation_helpers_generate_fallback_ids_without_state() -> None:
    app = FastAPI()

    @app.get("/probe")
    async def probe(request: Request) -> dict[str, int]:
        return {
            "correlation_length": len(get_correlation_id(request)),
            "request_length": len(get_request_id(request)),
        }

    payload = TestClient(app).get("/probe").json()

    assert payload["correlation_length"] == 36
    assert payload["request_length"] == 8


def test_logging_middleware_adds_no_contract_headers_but_passes_response() -> None:
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)

    @app.get("/logged")
    async def logged() -> dict[str, str]:
        return {"status": "ok"}

    response = TestClient(app).get("/logged?debug=true")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_logging_middleware_reraises_handler_errors() -> None:
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    response = TestClient(app, raise_server_exceptions=False).get("/boom")

    assert response.status_code == 500


def test_metrics_middleware_records_success_and_decrements_in_progress() -> None:
    app = FastAPI()
    app.add_middleware(MetricsMiddleware)

    @app.get("/metrics-success-unique")
    async def success() -> dict[str, str]:
        return {"status": "ok"}

    response = TestClient(app).get("/metrics-success-unique")

    assert response.status_code == 200
    assert (
        http_requests_in_progress.labels(
            method="GET",
            endpoint="/metrics-success-unique",
        )._value.get()
        == 0
    )
    assert (
        http_requests_total.labels(
            method="GET",
            endpoint="/metrics-success-unique",
            status_code="200",
        )._value.get()
        >= 1
    )


def test_metrics_middleware_records_exceptions_and_decrements_in_progress() -> None:
    app = FastAPI()
    app.add_middleware(MetricsMiddleware)

    @app.get("/metrics-failure-unique")
    async def failure() -> None:
        raise RuntimeError("boom")

    response = TestClient(app, raise_server_exceptions=False).get(
        "/metrics-failure-unique"
    )

    assert response.status_code == 500
    assert (
        http_requests_in_progress.labels(
            method="GET",
            endpoint="/metrics-failure-unique",
        )._value.get()
        == 0
    )
    assert (
        http_requests_total.labels(
            method="GET",
            endpoint="/metrics-failure-unique",
            status_code="500",
        )._value.get()
        >= 1
    )
