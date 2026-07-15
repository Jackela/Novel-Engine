from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from inspect import signature
from typing import NoReturn, ParamSpec, TypeVar

from fastapi import HTTPException, status

from src.contexts.studio.domain.exceptions import (
    InvalidOperation,
    NotFound,
    RevisionConflict,
    SnapshotConflict,
)

P = ParamSpec("P")
T = TypeVar("T")


def _raise_http(
    exc: NotFound | RevisionConflict | SnapshotConflict | InvalidOperation,
) -> NoReturn:
    if isinstance(exc, NotFound):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    if isinstance(exc, RevisionConflict):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(exc),
                "current_revision_id": exc.current_revision_id,
            },
        ) from exc
    if isinstance(exc, SnapshotConflict):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=str(exc),
    ) from exc


def _handle_domain_exceptions(
    handler: Callable[P, Awaitable[T]],
) -> Callable[P, Awaitable[T]]:
    resolved_signature = signature(handler, eval_str=True)

    @wraps(handler)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return await handler(*args, **kwargs)
        except (NotFound, RevisionConflict, SnapshotConflict, InvalidOperation) as exc:
            _raise_http(exc)

    wrapper.__dict__["__signature__"] = resolved_signature
    return wrapper
