"""Tests for the Studio HTTP router helpers."""

from __future__ import annotations

from typing import Any, cast

import pytest
from fastapi import HTTPException

from src.contexts.studio.domain.exceptions import (
    InvalidOperation,
    NotFound,
    RevisionConflict,
)
from src.contexts.studio.interface.http.router import (
    _handle_domain_exceptions,
    _raise_http,
)


@pytest.mark.parametrize(
    ("exc", "expected_status", "expected_detail"),
    [
        (NotFound("missing"), 404, "missing"),
        (
            RevisionConflict("rev-1"),
            409,
            {"message": "Document changed since the requested base revision.", "current_revision_id": "rev-1"},
        ),
        (InvalidOperation("bad"), 422, "bad"),
    ],
)
def test_raise_http_maps_domain_exceptions(
    exc: NotFound | RevisionConflict | InvalidOperation,
    expected_status: int,
    expected_detail: Any,
) -> None:
    with pytest.raises(HTTPException) as ctx:
        _raise_http(exc)

    assert ctx.value.status_code == expected_status
    assert ctx.value.detail == expected_detail


async def test_handle_domain_exceptions_passes_through_result() -> None:
    @_handle_domain_exceptions
    async def handler(value: int) -> dict[str, int]:
        return {"value": value}

    assert await handler(42) == {"value": 42}


async def test_handle_domain_exceptions_converts_not_found() -> None:
    @_handle_domain_exceptions
    async def handler() -> dict[str, Any]:
        raise NotFound("gone")

    with pytest.raises(HTTPException) as ctx:
        await handler()

    assert ctx.value.status_code == 404
    assert ctx.value.detail == "gone"


async def test_handle_domain_exceptions_converts_revision_conflict() -> None:
    @_handle_domain_exceptions
    async def handler() -> dict[str, Any]:
        raise RevisionConflict("rev-2")

    with pytest.raises(HTTPException) as ctx:
        await handler()

    assert ctx.value.status_code == 409
    detail = cast(dict[str, str], ctx.value.detail)
    assert detail["current_revision_id"] == "rev-2"


async def test_handle_domain_exceptions_converts_invalid_operation() -> None:
    @_handle_domain_exceptions
    async def handler() -> dict[str, Any]:
        raise InvalidOperation("nope")

    with pytest.raises(HTTPException) as ctx:
        await handler()

    assert ctx.value.status_code == 422
    assert ctx.value.detail == "nope"


async def test_handle_domain_exceptions_does_not_catch_other_exceptions() -> None:
    @_handle_domain_exceptions
    async def handler() -> dict[str, Any]:
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        await handler()
