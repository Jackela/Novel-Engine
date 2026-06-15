"""Canonical FastAPI application for Novel Studio."""

# mypy: disable-error-code=misc

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.apps.api.middleware.cors import get_cors_config
from src.apps.api.middleware.error_handler import setup_exception_handlers
from src.contexts.studio.application.services import (
    StudioStore,
    configure_studio_store,
    is_studio_store_configured,
    studio_store,
)
from src.contexts.studio.infrastructure.ai_provider import (
    create_studio_text_generation_provider,
)
from src.contexts.studio.infrastructure.database import studio_database
from src.contexts.studio.infrastructure.repository import SqlAlchemyStudioRepository
from src.shared.infrastructure.config.settings import (
    NovelEngineSettings,
    get_settings,
)
from src.shared.infrastructure.logging.config import configure_logging, get_logger
from src.shared.infrastructure.middleware import (
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
    CorrelationIdMiddleware,
    LoggingMiddleware,
    MetricsMiddleware,
    RateLimitMiddleware,
    start_prometheus_server,
)


def custom_openapi(app: FastAPI) -> dict:
    """Generate the canonical OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )
    openapi_schema["components"] = openapi_schema.get("components", {})
    openapi_schema["components"]["securitySchemes"] = {
        "cookieAuth": {
            "type": "apiKey",
            "in": "cookie",
            "name": "novel_studio_session",
        },
    }
    _apply_openapi_security(openapi_schema)
    openapi_schema["servers"] = [
        {"url": "/", "description": "Same-origin Novel Studio service"},
        {"url": "http://localhost:8000", "description": "Local development"},
    ]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def _apply_openapi_security(openapi_schema: dict[str, Any]) -> None:
    """Normalize generated auth metadata to browser cookie session schemes."""
    cookie_auth: list[dict[str, list[Any]]] = [{"cookieAuth": []}]
    paths = openapi_schema.get("paths", {})
    if not isinstance(paths, dict):
        return

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            if not isinstance(operation, dict):
                continue

            if path in {
                "/api/setup",
                "/api/session/login",
                "/api/session/guest",
            }:
                operation["security"] = []
            elif path.startswith(
                (
                    "/api/projects",
                    "/api/providers",
                    "/api/imports",
                    "/api/session",
                )
            ):
                operation["security"] = cookie_auth


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Canonical startup/shutdown hooks."""
    settings: NovelEngineSettings = app.state.settings
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

    await asyncio.to_thread(
        studio_store.database.initialize,
        create_backup=False,
        create_schema=False,
    )
    await asyncio.to_thread(studio_store.cleanup_expired_guests)

    async def cleanup_expired_guests() -> None:
        while True:
            await asyncio.sleep(60 * 60)
            await asyncio.to_thread(studio_store.cleanup_expired_guests)

    cleanup_task = asyncio.create_task(cleanup_expired_guests())

    yield

    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    await asyncio.to_thread(studio_store.database.dispose)
    logger.info("api_shutdown", message="Shutting down Novel Studio API")


def create_application(
    settings: NovelEngineSettings | None = None,
) -> FastAPI:
    """Create and configure the canonical FastAPI application."""
    resolved_settings = settings or get_settings()

    if not is_studio_store_configured():
        configure_studio_store(
            StudioStore(
                repository=SqlAlchemyStudioRepository(studio_database),
                data_dir=resolved_settings.data_dir,
                ai_provider_factory=create_studio_text_generation_provider,
            )
        )

    from src.apps.api.health import health_router
    from src.apps.api.router import api_router

    app = FastAPI(
        title=resolved_settings.project_name,
        description=(
            "Novel Studio API for projects, Markdown revisions, AI proposals, "
            "reviews, snapshots, exports, sessions, and durable jobs."
        ),
        version=resolved_settings.project_version,
        docs_url=None,
        redoc_url=resolved_settings.api.redoc_url,
        openapi_url=resolved_settings.api.openapi_url,
        lifespan=lifespan,
        openapi_tags=[
            {"name": "health", "description": "Health and readiness endpoints"},
            {"name": "studio", "description": "Novel Studio product operations"},
        ],
    )
    app.state.settings = resolved_settings

    def _openapi() -> dict[str, Any]:
        return custom_openapi(app)

    cast(Any, app).openapi = _openapi

    app.add_middleware(GZipMiddleware, minimum_size=1000)

    cors_config = get_cors_config(resolved_settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config["allow_origins"],
        allow_credentials=cors_config["allow_credentials"],
        allow_methods=cors_config["allow_methods"],
        allow_headers=cors_config["allow_headers"],
        expose_headers=cors_config["expose_headers"]
        + [CORRELATION_ID_HEADER, REQUEST_ID_HEADER],
        max_age=cors_config["max_age"],
    )

    app.add_middleware(LoggingMiddleware)
    if resolved_settings.monitoring.metrics_enabled:
        app.add_middleware(MetricsMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(RateLimitMiddleware)

    setup_exception_handlers(app)

    app.include_router(health_router, tags=["health"])
    app.include_router(api_router, prefix="/api")

    if resolved_settings.api.docs_url and resolved_settings.api.openapi_url:
        @app.get(resolved_settings.api.docs_url, include_in_schema=False)
        async def custom_swagger_ui_html() -> HTMLResponse:
            return get_swagger_ui_html(
                openapi_url=resolved_settings.api.openapi_url or "",
                title=f"{app.title} - Swagger UI",
                oauth2_redirect_url=f"{resolved_settings.api.docs_url}/oauth2-redirect",
                swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
                swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
            )

    frontend_dist = resolved_settings.base_dir / "frontend" / "dist"
    assets_dir = frontend_dist / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="studio-assets")

    @app.get("/{full_path:path}", include_in_schema=False, response_model=None)
    async def studio_spa(full_path: str) -> Any:
        if full_path.startswith(("api/", "health", "metrics", "docs", "openapi")):
            return {
                "name": resolved_settings.project_name,
                "version": resolved_settings.project_version,
                "api_base": "/api",
            }
        candidate = (frontend_dist / full_path).resolve()
        if frontend_dist.resolve() in {candidate, *candidate.parents} and candidate.is_file():
            return FileResponse(candidate)
        index = frontend_dist / "index.html"
        if index.is_file():
            return FileResponse(index)
        return {
            "name": resolved_settings.project_name,
            "version": resolved_settings.project_version,
            "message": "Build frontend/ to enable the Studio UI.",
        }

    return app


def main() -> None:
    """Run the canonical FastAPI app with Uvicorn."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.apps.api.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
        log_level=settings.logging.level.value.lower(),
    )


app = create_application()

__all__ = ["app", "create_application", "main"]
