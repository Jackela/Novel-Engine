from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import partial

import anyio
from fastapi import FastAPI

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProvider,
    TextGenerationProviderName,
)
from src.contexts.ai.infrastructure.providers.provider_factory import (
    create_text_generation_provider,
)
from src.contexts.studio.application.services import StudioStore
from src.contexts.studio.infrastructure.database import (
    StudioDatabase,
    create_studio_database,
)
from src.contexts.studio.infrastructure.exporters import DEFAULT_EXPORT_WRITERS
from src.contexts.studio.infrastructure.repository import SqlAlchemyStudioRepository
from src.shared.infrastructure.config.settings import NovelEngineSettings
from src.shared.infrastructure.logging.config import configure_logging, get_logger
from src.shared.infrastructure.middleware import start_prometheus_server


@dataclass(frozen=True, slots=True)
class StudioRuntime:
    store: StudioStore
    database: StudioDatabase


class StudioRuntimeNotConfiguredError(RuntimeError):
    pass


def create_runtime(settings: NovelEngineSettings) -> StudioRuntime:
    database = create_studio_database(settings)

    def ai_provider_factory(
        provider_name: TextGenerationProviderName,
        model_name: str,
    ) -> TextGenerationProvider:
        return create_text_generation_provider(settings, provider_name, model_name)

    return StudioRuntime(
        store=StudioStore(
            repository=SqlAlchemyStudioRepository(database),
            data_dir=settings.data_dir,
            ai_provider_factory=ai_provider_factory,
            session_secret=settings.security.secret_key,
            export_writers=DEFAULT_EXPORT_WRITERS,
        ),
        database=database,
    )


def attach_runtime(app: FastAPI, runtime: StudioRuntime) -> None:
    app.state.studio_runtime = runtime


def get_app_runtime(app: FastAPI) -> StudioRuntime:
    runtime = getattr(app.state, "studio_runtime", None)
    if not isinstance(runtime, StudioRuntime):
        raise StudioRuntimeNotConfiguredError(
            "FastAPI application has no configured StudioRuntime."
        )
    return runtime


async def _cleanup_expired_guests(store: StudioStore) -> None:
    while True:
        await anyio.sleep(60 * 60)
        await anyio.to_thread.run_sync(store.cleanup_expired_guests)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings: NovelEngineSettings = app.state.settings
    runtime = get_app_runtime(app)
    store = runtime.store
    configure_logging(
        log_level=settings.logging.level.value,
        json_format=settings.logging.json_format,
        service_name=settings.monitoring.service_name,
        service_version=settings.monitoring.service_version,
    )
    logger = get_logger(__name__)
    logger.info(
        "api_startup",
        version=settings.project_version,
        environment=settings.environment.value,
    )

    if settings.monitoring.metrics_enabled:
        try:
            start_prometheus_server(port=settings.monitoring.metrics_port)
            logger.info(
                "prometheus_started",
                port=settings.monitoring.metrics_port,
                path=settings.monitoring.metrics_path,
            )
        except OSError as exc:
            logger.warning("prometheus_start_failed", reason=str(exc))

    initialize = partial(
        runtime.database.initialize,
        create_backup=False,
        create_schema=False,
    )
    await anyio.to_thread.run_sync(initialize)
    await anyio.to_thread.run_sync(store.cleanup_expired_guests)

    try:
        async with anyio.create_task_group() as tasks:
            tasks.start_soon(_cleanup_expired_guests, store)
            try:
                yield
            finally:
                tasks.cancel_scope.cancel()
    finally:
        await anyio.to_thread.run_sync(runtime.database.dispose)
        logger.info("api_shutdown", message="Shutting down Novel Studio API")
