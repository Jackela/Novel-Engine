"""
Novel Engine API Application

FastAPI 0.116+ application with OpenAPI documentation,
comprehensive middleware, and Clean Architecture.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from src.apps.api.middleware.cors import get_cors_config
from src.apps.api.middleware.error_handler import setup_exception_handlers
from src.apps.api.router import api_router
from src.shared.infrastructure.config.settings import get_settings
from src.shared.infrastructure.logging.config import configure_logging, get_logger
from src.shared.infrastructure.middleware import (
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
    CorrelationIdMiddleware,
    LoggingMiddleware,
    MetricsMiddleware,
    start_prometheus_server,
)

# Configure logging at startup
settings = get_settings()
configure_logging(
    log_level=settings.logging.level.value,
    json_format=settings.logging.json_format,
    service_name=settings.monitoring.service_name,
    service_version=settings.monitoring.service_version,
)

logger = get_logger(__name__)


def custom_openapi(app: FastAPI) -> dict:
    """Generate custom OpenAPI schema with enhanced documentation."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )

    # Add security schemes
    openapi_schema["components"] = openapi_schema.get("components", {})
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token authentication",
        },
        "apiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key authentication",
        },
    }

    # Add server information
    openapi_schema["servers"] = [
        {"url": "/api/v1", "description": "API Version 1"},
        {"url": "http://localhost:8000/api/v1", "description": "Local development"},
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan events."""
    # Startup
    logger.info(
        "api_startup",
        message="Starting Novel Engine API",
        version=settings.project_version,
        environment=settings.environment.value,
    )

    # Start Prometheus metrics server if enabled
    if settings.monitoring.metrics_enabled:
        start_prometheus_server(port=settings.monitoring.metrics_port)
        logger.info(
            "prometheus_started",
            port=settings.monitoring.metrics_port,
            path=settings.monitoring.metrics_path,
        )

    yield

    # Shutdown
    logger.info("api_shutdown", message="Shutting down Novel Engine API")


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Novel Engine API",
        description="""
        AI-powered narrative engine with Clean Architecture.

        ## Features

        - **Character Management**: Create and manage story characters
        - **Narrative Generation**: AI-powered story generation
        - **Knowledge Management**: Context-aware knowledge system
        - **Real-time Updates**: WebSocket support for live interactions

        ## Authentication

        Most endpoints require authentication via JWT Bearer token or API key.

        ## Distributed Tracing

        All requests include correlation ID tracking via headers:
        - X-Correlation-ID: Tracks requests across services
        - X-Request-ID: Unique ID for each request
        """,
        version="2.0.0",
        docs_url=None,  # Custom docs endpoint
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        openapi_tags=[
            {"name": "health", "description": "Health check endpoints"},
            {"name": "auth", "description": "Authentication operations"},
            {"name": "characters", "description": "Character management"},
            {"name": "narrative", "description": "Narrative generation"},
            {"name": "knowledge", "description": "Knowledge management"},
        ],
    )

    # Override OpenAPI schema
    app.openapi = lambda: custom_openapi(app)

    # Add middleware (order matters - first added is outermost, last is innermost)
    # 1. GZip compression (innermost - processes response last)
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # 2. CORS
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

    # 3. Logging (captures request/response details)
    app.add_middleware(LoggingMiddleware)

    # 4. Metrics (collects Prometheus metrics)
    if settings.monitoring.metrics_enabled:
        app.add_middleware(MetricsMiddleware)

    # 5. Correlation ID (outermost - sets up tracing context first)
    app.add_middleware(CorrelationIdMiddleware)

    # Setup exception handlers
    setup_exception_handlers(app)

    # Include routers
    from src.apps.api.health import health_router

    app.include_router(health_router, tags=["health"])
    app.include_router(api_router, prefix="/api/v1")

    # Custom docs endpoint
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url="/docs/oauth2-redirect",
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        )

    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "name": "Novel Engine API",
            "version": "2.0.0",
            "documentation": "/docs",
            "health": "/health",
            "metrics": settings.monitoring.metrics_path,
        }

    return app


# Create application instance
app = create_application()
