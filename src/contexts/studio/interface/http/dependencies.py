from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, Request

from src.contexts.studio.application.services import StudioStore


class StudioStoreNotConfiguredError(RuntimeError):
    pass


def attach_studio_store(app: FastAPI, store: StudioStore) -> None:
    app.state.studio_store = store


def get_app_studio_store(app: FastAPI) -> StudioStore:
    store = getattr(app.state, "studio_store", None)
    if not isinstance(store, StudioStore):
        raise StudioStoreNotConfiguredError(
            "FastAPI application has no configured StudioStore."
        )
    return store


def get_studio_store(request: Request) -> StudioStore:
    return get_app_studio_store(request.app)


StudioStoreDependency = Annotated[StudioStore, Depends(get_studio_store)]
