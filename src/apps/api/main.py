"""Canonical FastAPI application for Novel Engine."""

# mypy: disable-error-code=misc

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse

from src.api.versioning import setup_versioning
from src.apps.api.dependencies import close_connection_pool
from src.apps.api.health import health_router, reset_health_state, set_honcho_client
from src.apps.api.middleware.cors import get_cors_config
from src.apps.api.middleware.error_handler import setup_exception_handlers
from src.apps.api.router import api_router
from src.apps.api.runtime import runtime_store
from src.shared.infrastructure.config.settings import (
    DEFAULT_SECRET_KEY,
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
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    openapi_schema["servers"] = [
        {"url": "/api/v1", "description": "Canonical API"},
        {"url": "http://localhost:8000/api/v1", "description": "Local development"},
    ]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def _configure_optional_honcho() -> None:
    """Attempt to attach the optional Honcho runtime without blocking startup."""
    logger = get_logger(__name__)
    try:
        from src.shared.infrastructure.honcho import create_honcho_client
    except Exception as exc:  # pragma: no cover - depends on optional dependency
        logger.info("honcho_unavailable", reason=str(exc))
        return

    try:
        set_honcho_client(create_honcho_client())
        logger.info("honcho_enabled", message="Optional Honcho client configured")
    except Exception as exc:  # pragma: no cover - runtime/network dependent
        logger.warning("honcho_disabled", reason=str(exc))


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

    reset_health_state()
    _configure_optional_honcho()

    yield

    await runtime_store.shutdown()
    await close_connection_pool()
    logger.info("api_shutdown", message="Shutting down Novel Engine API")


def create_application(
    settings: NovelEngineSettings | None = None,
) -> FastAPI:
    """Create and configure the canonical FastAPI application."""
    provided_settings = settings is not None
    resolved_settings = settings or get_settings()
    security_secret = os.getenv("SECURITY_SECRET_KEY")

    if (
        not provided_settings
        and (resolved_settings.is_staging or resolved_settings.is_production)
        and (not security_secret or security_secret == DEFAULT_SECRET_KEY)
    ):
        raise RuntimeError(
            "SECURITY_SECRET_KEY must be set for staging and production"
        )

    runtime_store.reset()

    app = FastAPI(
        title=resolved_settings.project_name,
        description=(
            "Canonical Novel Engine API with source-backed auth, story workflow, "
            "knowledge, guest, health, and versioning routes."
        ),
        version=resolved_settings.project_version,
        docs_url=None,
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        openapi_tags=[
            {"name": "health", "description": "Health and readiness endpoints"},
            {"name": "authentication", "description": "Authentication operations"},
            {"name": "knowledge", "description": "Knowledge management"},
            {"name": "guest", "description": "Guest session management"},
            {"name": "story", "description": "Long-form story generation workflow"},
        ],
    )
    app.state.settings = resolved_settings

    def _openapi() -> dict[str, Any]:
        return custom_openapi(app)

    cast(Any, app).openapi = _openapi

    app.add_middleware(GZipMiddleware, minimum_size=1000)

    cors_config = get_cors_config()
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

    setup_exception_handlers(app)
    setup_versioning(app)

    app.include_router(health_router, tags=["health"])
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html() -> HTMLResponse:
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url="/docs/oauth2-redirect",
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        )

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "name": resolved_settings.project_name,
            "version": resolved_settings.project_version,
            "documentation": "/docs",
            "health": "/health",
            "api_base": "/api/v1",
            "guest_session": "/api/v1/guest/session",
            "story": "/api/v1/story",
            "story_pipeline": "/api/v1/story/pipeline",
            "versioning": "/api/versions",
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
