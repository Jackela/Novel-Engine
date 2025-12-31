from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


def _status_code_to_error(status_code: int) -> tuple[str, str]:
    mapping = {
        400: ("Bad Request", "bad_request"),
        401: ("Unauthorized", "unauthorized"),
        403: ("Forbidden", "forbidden"),
        404: ("Not Found", "not_found"),
        405: ("Method Not Allowed", "method_not_allowed"),
        409: ("Conflict", "conflict"),
        422: ("Validation Error", "validation_error"),
        429: ("Too Many Requests", "rate_limited"),
        500: ("Internal Server Error", "internal_error"),
        503: ("Service Unavailable", "service_unavailable"),
    }
    return mapping.get(status_code, ("Unknown Error", "unknown_error"))


def _envelope(
    *,
    status_code: int,
    detail: str,
    code: Optional[str] = None,
    error: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    title, default_code = _status_code_to_error(status_code)
    payload: Dict[str, Any] = {
        "error": error or title,
        "detail": detail,
        "code": code or default_code,
    }
    if extra:
        payload.update(extra)
    return payload


def install_error_handlers(app: FastAPI, *, debug: bool = False) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def _starlette_http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        if exc.status_code == 404:
            detail = "The requested endpoint does not exist."
        else:
            detail = str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(status_code=exc.status_code, detail=detail),
        )

    @app.exception_handler(HTTPException)
    async def _fastapi_http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(status_code=exc.status_code, detail=str(exc.detail)),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_envelope(
                status_code=422,
                detail="Request validation failed.",
                extra={"fields": exc.errors()},
            ),
        )

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(
            "Unhandled exception for %s: %s", request.url.path, exc, exc_info=True
        )
        detail = str(exc) if debug else "Internal server error."
        return JSONResponse(
            status_code=500,
            content=_envelope(status_code=500, detail=detail),
        )
