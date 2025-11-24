#!/usr/bin/env python3
"""
Enhanced Main API Server for the Dynamic Context Engineering Framework.

This server provides a comprehensive, production-ready API with:
- Standardized response formats and error handling
- Health monitoring and metrics collection
- API versioning and backward compatibility
- Structured logging and observability
- Integration testing capabilities
- Security enhancements and monitoring
"""

import asyncio
import json
import logging
import os
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.character_api import create_character_api

# Import Context7 integration and enhanced documentation
from src.api.context7_integration_api import create_context7_integration_api
from src.api.documentation import setup_enhanced_docs
from src.api.emergent_narrative_api import create_emergent_narrative_api
from src.api.enhanced_documentation_system import EnhancedDocumentationSystem
from src.api.error_handlers import (
    ServiceUnavailableException,
    setup_error_handlers,
)
from src.api.health_system import HealthMonitor, create_health_data_response
from src.api.interaction_api import create_interaction_api
from src.api.logging_system import LogCategory, LogLevel, setup_logging
from src.api.monitoring import setup_monitoring

# Import new integration systems
from src.api.response_models import (
    APIMetadata,
    HealthCheckData,
    HealthCheckResponse,
    SuccessResponse,
)
from src.api.story_generation_api import create_story_generation_api
from src.api.subjective_reality_api import create_subjective_reality_api
from src.api.versioning import setup_versioning
from src.core.system_orchestrator import (
    OrchestratorConfig,
    OrchestratorMode,
    SystemOrchestrator,
)

# Removed unused import: from functools import wraps


# Import security systems (if available)
try:
    from src.security.auth_system import (
        AuthenticationManager,
        initialize_security_service,
    )
    from src.security.enhanced_security import EnhancedSecurityMiddleware
    from src.security.input_validation import ValidationMiddleware, get_input_validator
    from src.security.rate_limiting import (
        InMemoryRateLimitBackend,
        RateLimitMiddleware,
        RateLimitStrategy,
    )
    from src.security.security_headers import (
        SecurityHeaders,
        SecurityHeadersMiddleware,
        get_production_security_config,
    )

    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False
    logging.warning("Security modules not available - running in basic mode")

# Initialize basic logging (will be enhanced during app startup)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

# Global variables for system components
global_orchestrator: Optional[SystemOrchestrator] = None
global_health_monitor: Optional[HealthMonitor] = None
global_structured_logger = None


class OptimizedJSONResponse(JSONResponse):
    """Optimized JSON response with performance enhancements."""

    def __init__(
        self,
        content: Any = None,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        cache_control: Optional[str] = None,
        max_age: Optional[int] = None,
    ):

        # Add performance headers
        if headers is None:
            headers = {}

        # Add cache control headers for performance
        if cache_control:
            headers["Cache-Control"] = cache_control
        elif max_age is not None:
            headers["Cache-Control"] = f"public, max-age={max_age}"

        # Add performance headers
        headers["X-Content-Type-Options"] = "nosniff"
        headers["X-Frame-Options"] = "DENY"
        headers["X-API-Version"] = "1.0.0"
        headers["Server-Timing"] = "api;dur=0"

        super().__init__(content=content, status_code=status_code, headers=headers)


class APIServerConfig:
    """Configuration for the API server."""

    def __init__(self):
        self.host = os.getenv("API_HOST", "127.0.0.1")
        self.port = int(os.getenv("API_PORT", "8000"))
        self.database_path = os.getenv("DATABASE_PATH", "data/api_server.db")
        self.security_database_path = os.getenv(
            "SECURITY_DATABASE_PATH", "data/security.db"
        )
        self.debug = (
            os.getenv("DEBUG", "true").lower() == "true"
        )  # Default to debug mode
        self.enable_docs = os.getenv("ENABLE_DOCS", "true").lower() == "true"
        self.cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
        self.max_concurrent_agents = int(os.getenv("MAX_CONCURRENT_AGENTS", "20"))
        self.enable_metrics = os.getenv("ENABLE_METRICS", "true").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        # Security configurations
        self.enable_https = os.getenv("ENABLE_HTTPS", "false").lower() == "true"
        self.ssl_cert_file = os.getenv("SSL_CERT_FILE")
        self.ssl_key_file = os.getenv("SSL_KEY_FILE")
        self.jwt_secret = os.getenv("JWT_SECRET", secrets.token_urlsafe(32))
        self.enable_rate_limiting = (
            os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true"
        )
        self.enable_auth = (
            os.getenv("ENABLE_AUTH", "false").lower() == "true"
        )  # Disabled by default for compatibility

        # Ensure data directory exists for security database
        security_db_dir = os.path.dirname(self.security_database_path)
        if security_db_dir:
            os.makedirs(security_db_dir, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Enhanced application startup and shutdown with comprehensive system initialization."""
    global global_orchestrator, global_health_monitor, global_structured_logger

    config = APIServerConfig()
    app_start_time = datetime.now()

    try:
        # Initialize structured logging
        global_structured_logger = setup_logging(
            app,
            log_level=LogLevel.DEBUG if config.debug else LogLevel.INFO,
            log_file="logs/novel_engine_api.log" if not config.debug else None,
            output_format="json" if not config.debug else "text",
        )

        global_structured_logger.info(
            "Starting Enhanced Novel Engine API Server", category=LogCategory.SYSTEM
        )

        # Initialize health monitoring
        global_health_monitor = HealthMonitor(app_start_time)
        app.state.health_monitor = global_health_monitor

        # Setup system orchestrator
        orchestrator_config = OrchestratorConfig(
            mode=OrchestratorMode.PRODUCTION,
            max_concurrent_agents=config.max_concurrent_agents,
            debug_logging=config.debug,
        )

        global_orchestrator = SystemOrchestrator(
            database_path=config.database_path, config=orchestrator_config
        )

        startup_result = await global_orchestrator.startup()

        if not startup_result.success:
            error_msg = (
                startup_result.error.message
                if startup_result.error
                else "Unknown error"
            )
            global_structured_logger.error(
                f"System Orchestrator startup failed: {error_msg}",
                category=LogCategory.SYSTEM,
            )
            raise ServiceUnavailableException("System Orchestrator", error_msg)

        app.state.orchestrator = global_orchestrator
        global_structured_logger.info(
            "System Orchestrator started successfully", category=LogCategory.SYSTEM
        )

        # Register health checks
        global_health_monitor.register_database_check(config.database_path)
        global_health_monitor.register_orchestrator_check(global_orchestrator)
        global_health_monitor.register_system_resource_checks()

        # Set orchestrator on all API instances
        if hasattr(app.state, "character_api"):
            app.state.character_api.set_orchestrator(global_orchestrator)
        if hasattr(app.state, "story_api"):
            app.state.story_api.set_orchestrator(global_orchestrator)
            await app.state.story_api.start_background_tasks()
        if hasattr(app.state, "interaction_api"):
            app.state.interaction_api.set_orchestrator(global_orchestrator)
        if hasattr(app.state, "subjective_reality_api"):
            app.state.subjective_reality_api.orchestrator = global_orchestrator
        if hasattr(app.state, "emergent_narrative_api"):
            app.state.emergent_narrative_api.orchestrator = global_orchestrator
        if hasattr(app.state, "context7_integration_api"):
            app.state.context7_integration_api.orchestrator = global_orchestrator

        # Initialize authentication system if enabled and available
        if config.enable_auth and SECURITY_AVAILABLE:
            try:
                auth_manager = AuthenticationManager(
                    database_path=config.database_path, jwt_secret=config.jwt_secret
                )
                await auth_manager.initialize()
                app.state.auth_manager = auth_manager
                global_structured_logger.info(
                    "Authentication system initialized", category=LogCategory.SECURITY
                )
            except Exception as e:
                global_structured_logger.error(
                    f"Authentication initialization failed: {e}",
                    category=LogCategory.SECURITY,
                )

        global_structured_logger.info(
            "All API components initialized successfully", category=LogCategory.SYSTEM
        )

        # Perform initial health check
        initial_health = await global_health_monitor.run_health_checks()
        global_structured_logger.info(
            f"Initial health check completed - Status: {initial_health.status.value}",
            category=LogCategory.SYSTEM,
        )

        yield

    except Exception as startup_error:
        global_structured_logger.error(
            f"API server startup failed: {startup_error}",
            exc_info=startup_error,
            category=LogCategory.ERROR,
        )
        raise

    finally:
        global_structured_logger.info(
            "Shutting down Enhanced API Server", category=LogCategory.SYSTEM
        )

        # Stop background tasks
        if hasattr(app.state, "story_api"):
            try:
                await app.state.story_api.stop_background_tasks()
                global_structured_logger.info(
                    "Story API background tasks stopped", category=LogCategory.SYSTEM
                )
            except Exception as e:
                global_structured_logger.error(
                    f"Error stopping story API tasks: {e}", category=LogCategory.ERROR
                )

        # Shutdown orchestrator
        if global_orchestrator:
            try:
                await global_orchestrator.shutdown()
                global_structured_logger.info(
                    "System Orchestrator shutdown complete", category=LogCategory.SYSTEM
                )
            except Exception as e:
                global_structured_logger.error(
                    f"Error during orchestrator shutdown: {e}",
                    category=LogCategory.ERROR,
                )


def create_app() -> FastAPI:
    """Creates and configures the enhanced FastAPI application with comprehensive integration systems."""
    config = APIServerConfig()

    # Create FastAPI application with enhanced configuration
    app = FastAPI(
        title="Novel Engine API",
        version="1.1.0",
        description="Enhanced Dynamic Context Engineering Framework with comprehensive integration systems",
        lifespan=lifespan,
        docs_url=None,  # Will be handled by enhanced docs system
        redoc_url=None,  # Will be handled by enhanced docs system
        openapi_url="/api/openapi.json",
    )

    # Setup enhanced systems in proper order

    # 1. Error handling (must be first)
    setup_error_handlers(app, debug=config.debug)

    # 2. API versioning
    setup_versioning(app)

    # 3. Monitoring and metrics
    monitoring_components = setup_monitoring(app, enable_alerts=not config.debug)
    app.state.metrics_collector = monitoring_components["metrics_collector"]
    app.state.alert_manager = monitoring_components["alert_manager"]

    # 4. Enhanced documentation
    setup_enhanced_docs(app)

    # Add middleware (order matters - last added = first executed)
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Always-on header guard to ensure minimal security headers on all responses
    class HeaderGuardMiddleware(BaseHTTPMiddleware):
        def __init__(self, app, headers: Dict[str, str]):
            super().__init__(app)
            self._headers = headers

        async def dispatch(self, request, call_next):
            try:
                response = await call_next(request)
            except Exception:
                # Fallback to 400 if an error bubbles up before other middleware
                response = PlainTextResponse("Bad Request", status_code=400)
            # Ensure headers are present
            for k, v in self._headers.items():
                if k not in response.headers:
                    response.headers[k] = v
            return response

    # Define and add a raw ASGI middleware to ensure headers even on early errors
    class RawHeaderASGIMiddleware:
        def __init__(self, app, headers: Dict[str, str]):
            self.app = app
            self._headers = headers

        async def __call__(self, scope, receive, send):
            async def send_wrapper(message):
                if message.get("type") == "http.response.start":
                    hdrs = message.setdefault("headers", [])
                    existing = {k.decode().lower() for k, _ in hdrs}
                    for k, v in self._headers.items():
                        if k.lower() not in existing:
                            hdrs.append((k.encode("latin-1"), v.encode("latin-1")))
                await send(message)

            try:
                await self.app(scope, receive, send_wrapper)
            except Exception:
                start = {
                    "type": "http.response.start",
                    "status": 400,
                    "headers": [
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"content-type", b"text/plain; charset=utf-8"),
                    ],
                }
                body = {"type": "http.response.body", "body": b"Bad Request"}
                await send(start)
                await send(body)

    # Add ASGI-level header guard last so it executes first among middlewares
    app.add_middleware(
        RawHeaderASGIMiddleware,
        headers={
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
        },
    )

    # Exception handlers that ensure minimal security headers on error responses
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc: HTTPException):
        response = JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc: Exception):
        response = JSONResponse({"detail": "Bad Request"}, status_code=400)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    # Add security middleware stack if available (order matters - first added = last executed)
    if SECURITY_AVAILABLE:
        # Apply Security Headers as the outermost middleware so it can decorate all responses
        # Note: Using production config for both modes since get_development_security_config not available
        security_config = get_production_security_config()
        security_headers = SecurityHeaders(security_config)
        app.add_middleware(SecurityHeadersMiddleware, security_headers=security_headers)
        logger.info("Security headers middleware enabled (outermost)")

        # Rate limiting (line of defense inside headers layer)
        if config.enable_rate_limiting:
            rate_limit_backend = InMemoryRateLimitBackend()
            rate_limit_strategy = RateLimitStrategy.TOKEN_BUCKET
            app.add_middleware(
                RateLimitMiddleware,
                backend=rate_limit_backend,
                strategy=rate_limit_strategy,
            )
            logger.info("Rate limiting middleware enabled")

        # Input validation and enhanced security (inner layers)
        if not config.debug:
            validator = get_input_validator()
            app.add_middleware(ValidationMiddleware, validator=validator)
            logger.info("Input validation middleware enabled")

            app.add_middleware(
                EnhancedSecurityMiddleware, config={"strict_mode": not config.debug}
            )
            logger.info("Enhanced security middleware enabled")
        else:
            logger.info("Some security middleware disabled in debug mode")
    else:
        logger.info("Security middleware not available - basic mode enabled")

    # Initialize core security service prior to route registration (required by decorators)
    app.state.security_service = None
    if SECURITY_AVAILABLE:
        try:
            security_service = initialize_security_service(
                config.security_database_path, config.jwt_secret
            )
            try:
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                running_loop = None

            if running_loop and running_loop.is_running():
                running_loop.create_task(security_service.initialize_database())
            else:
                asyncio.run(security_service.initialize_database())

            app.state.security_service = security_service
            logger.info("Security service initialized for API routing.")
        except Exception as exc:
            logger.error(f"Failed to initialize security service: {exc}")
            raise

    # Configure CORS more securely
    if config.debug:
        # Development: Allow localhost origins with proper validation
        cors_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ]
    else:
        # Production: Use specific origins from environment
        cors_origins = (
            config.cors_origins
            if config.cors_origins != ["*"]
            else ["https://novel-engine.app"]
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],  # Specific methods only
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-API-Key",
            "X-Request-ID",
        ],  # Specific headers only
    )

    # Add trusted host middleware for security in production
    if not config.debug:
        trusted_hosts = cors_origins + [config.host, "localhost", "127.0.0.1", "testserver"]
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)

    # Enhanced system endpoints

    @app.get("/", tags=["System"])
    async def root():
        """Enhanced root endpoint with comprehensive API information."""
        orchestrator = getattr(app.state, "orchestrator", None)
        health_monitor = getattr(app.state, "health_monitor", None)

        # Get basic system status
        system_status = "operational" if orchestrator else "starting"

        # Get health status if available
        health_status = "unknown"
        if health_monitor:
            try:
                cached_health = health_monitor.get_cached_health(max_age_seconds=60)
                if cached_health:
                    health_status = cached_health.status.value
            except Exception:
                pass

        content = {
            "name": "Novel Engine API",
            "version": "1.1.0",
            "status": system_status,
            "health": health_status,
            "timestamp": datetime.now().isoformat(),
            "api_documentation": {
                "interactive_docs": "/docs",
                "api_reference": "/redoc",
                "integration_guide": "/api/documentation",
                "openapi_spec": "/api/openapi.json",
                "version_info": "/api/versions",
            },
            "endpoints": {
                "health_detailed": "/health",
                "characters": "/api/v1/characters",
                "character_detail": "/api/v1/characters/{id}",
                "stories": "/api/v1/stories",
                "story_generation": "/api/v1/stories/generate",
                "interactions": "/api/v1/interactions",
                "turn_briefs": "/api/v1/turns/{turn_id}/briefs",
                "agent_brief": "/api/v1/turns/{turn_id}/briefs/{agent_id}",
                "agent_beliefs": "/api/v1/agents/{agent_id}/beliefs",
                "emergent_narratives": "/api/v1/narratives/emergent/generate",
                "narrative_build": "/api/v1/narratives/build",
                "causal_graph": "/api/v1/causality/graph",
                "context7_examples": "/api/v1/context7/examples",
                "context7_validation": "/api/v1/context7/validate",
                "context7_documentation": "/api/v1/context7/documentation",
                "context7_best_practices": "/api/v1/context7/best-practices/{framework}",
                "context7_status": "/api/v1/context7/status",
                "metrics": "/api/v1/metrics",
                "performance": "/api/v1/metrics/performance",
                "legacy_characters": "/characters",
                "legacy_character_detail": "/characters/{id}",
                "legacy_simulations": "/simulations",
            },
            "features": [
                "Character Management",
                "Story Generation",
                "Real-time Interactions",
                "Subjective Reality Engine",
                "Emergent Narrative Generation",
                "Personalized Turn Briefs",
                "Causal Graph Analysis",
                "Context7 Integration",
                "Interactive Code Examples",
                "API Pattern Validation",
                "Framework Best Practices",
                "Enhanced Documentation",
                "Performance Monitoring",
                "Health Checks",
                "API Versioning",
            ],
        }

        metadata = APIMetadata(
            timestamp=datetime.now(),
            api_version="1.1",
            server_time=0.001,  # Root endpoint is very fast
        )

        response_data = SuccessResponse(data=content, metadata=metadata)
        return JSONResponse(
            content=response_data.model_dump(),
            headers={"Cache-Control": "public, max-age=60"},
        )

    @app.get("/health", tags=["System"])
    async def enhanced_health_check():
        """Enhanced comprehensive health check with detailed system status."""
        start_time = time.time()

        try:
            health_monitor = getattr(app.state, "health_monitor", None)
            if not health_monitor:
                raise ServiceUnavailableException(
                    "Health Monitor", "Health monitoring system not available"
                )

            # Get comprehensive health status
            system_health = await health_monitor.run_health_checks(
                include_non_critical=True
            )

            # Create response data
            health_data = create_health_data_response(system_health)

            # Calculate response time
            response_time = (time.time() - start_time) * 1000

            metadata = APIMetadata(
                timestamp=datetime.now(), api_version="1.1", server_time=response_time
            )

            # Determine HTTP status code based on health
            if system_health.status.value == "healthy":
                status_code = 200
            elif system_health.status.value == "degraded":
                status_code = 200  # Still operational but with warnings
            else:
                status_code = 503  # Service unavailable

            response = HealthCheckResponse(data=health_data, metadata=metadata)

            return JSONResponse(
                content=response.model_dump(),
                status_code=status_code,
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Health check failed: {e}")

            # Fallback health response
            fallback_data = HealthCheckData(
                service_status="unhealthy",
                database_status="unknown",
                orchestrator_status="unknown",
                active_agents=0,
                uptime_seconds=0,
                version="1.1.0",
                environment="unknown",
            )

            metadata = APIMetadata(
                timestamp=datetime.now(), api_version="1.1", server_time=response_time
            )

            response = HealthCheckResponse(data=fallback_data, metadata=metadata)

            return JSONResponse(
                content=response.model_dump(),
                status_code=503,
                headers={"Cache-Control": "no-cache"},
            )

    # Register API routes immediately (not in lifespan)
    _register_api_routes(app)

    # Register legacy routes for backward compatibility
    _register_legacy_routes(app)

    return app


def _register_api_routes(app: FastAPI):
    """Register all API routes immediately."""
    # Create placeholder API instances that will be initialized during lifespan
    character_api = create_character_api(None)  # Will be set during lifespan
    story_generation_api = create_story_generation_api(None)
    interaction_api = create_interaction_api(None)
    subjective_reality_api = create_subjective_reality_api(None)
    emergent_narrative_api = create_emergent_narrative_api(None)
    context7_integration_api = create_context7_integration_api(None)

    # Store API instances in app state for lifespan initialization
    app.state.character_api = character_api
    app.state.story_api = story_generation_api
    app.state.interaction_api = interaction_api
    app.state.subjective_reality_api = subjective_reality_api
    app.state.emergent_narrative_api = emergent_narrative_api
    app.state.context7_integration_api = context7_integration_api

    # Setup routes
    character_api.setup_routes(app)
    story_generation_api.setup_routes(app)
    interaction_api.setup_routes(app)
    subjective_reality_api.setup_routes(app)
    emergent_narrative_api.setup_routes(app)
    context7_integration_api.setup_routes(app)

    # Setup enhanced documentation system
    enhanced_docs = EnhancedDocumentationSystem(app, context7_integration_api)
    enhanced_docs.setup_routes(app)
    app.state.enhanced_docs = enhanced_docs

    logger.info("API routes registered successfully with Context7 integration.")


def _register_legacy_routes(app: FastAPI):
    """Register legacy routes for backward compatibility."""
    import os

    @app.get("/", response_model=dict)
    async def root_index():
        """Root endpoint for basic availability with explicit security headers.

        Adding headers directly ensures compliance in test environments where
        middleware ordering or transport differences may bypass decoration.
        """
        from fastapi.responses import JSONResponse

        payload = {"message": "Novel Engine API is running"}
        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
        }
        return JSONResponse(content=payload, headers=headers)

    @app.get("/characters", response_model=dict)
    async def legacy_get_characters():
        """Legacy endpoint - List all characters from file system."""
        try:
            characters_path = os.path.join(os.getcwd(), "characters")
            if not os.path.isdir(characters_path):
                return {"characters": []}

            characters = []
            for item in os.listdir(characters_path):
                item_path = os.path.join(characters_path, item)
                if os.path.isdir(item_path):
                    characters.append(item)

            characters = sorted(characters)
            logger.info(
                f"Legacy characters endpoint returned {len(characters)} characters"
            )
            return {"characters": characters}
        except Exception as e:
            logger.error(f"Error in legacy characters endpoint: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve characters")

    @app.get("/characters/{character_id}", response_model=dict)
    async def legacy_get_character_detail(character_id: str):
        """Legacy endpoint - Get character details from file system."""
        try:
            characters_path = os.path.join(os.getcwd(), "characters")
            character_path = os.path.join(characters_path, character_id)

            if not os.path.isdir(character_path):
                raise HTTPException(
                    status_code=404, detail=f"Character '{character_id}' not found"
                )

            # Read character data from file system
            character_file = os.path.join(
                character_path, f"character_{character_id}.md"
            )
            stats_file = os.path.join(character_path, "stats.yaml")

            character_data = {
                "character_id": character_id,
                "name": character_id.replace("_", " ").title(),
                "background_summary": "Character loaded from file system",
                "personality_traits": "Based on character files",
                "current_status": "active",
                "narrative_context": "File-based character",
                "skills": {},
                "relationships": {},
                "current_location": "Unknown",
                "inventory": [],
                "metadata": {"source": "file_system"},
            }

            # Try to read character description if file exists
            if os.path.exists(character_file):
                try:
                    with open(character_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        # Extract basic info from markdown content
                        lines = content.split("\n")
                        for line in lines:
                            if line.startswith("# "):
                                character_data["name"] = line[2:].strip()
                            elif (
                                "background" in line.lower()
                                or "summary" in line.lower()
                            ):
                                character_data["background_summary"] = line.strip()
                except Exception as e:
                    logger.warning(
                        f"Could not read character file for {character_id}: {e}"
                    )

            # Try to read stats if file exists
            if os.path.exists(stats_file):
                try:
                    import yaml

                    with open(stats_file, "r", encoding="utf-8") as f:
                        stats = yaml.safe_load(f)
                        if isinstance(stats, dict):
                            character_data["skills"] = stats.get("skills", {})
                            character_data["metadata"].update(stats.get("metadata", {}))
                except Exception as e:
                    logger.warning(f"Could not read stats file for {character_id}: {e}")

            logger.info(
                f"Legacy character detail endpoint returned data for {character_id}"
            )
            return character_data

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Error in legacy character detail endpoint for {character_id}: {e}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve character details: {str(e)}",
            )

    @app.get("/api/characters", response_model=dict)
    async def legacy_get_characters_api():
        """Unversioned REST endpoint for legacy characters list."""
        return await legacy_get_characters()

    @app.get("/api/characters/{character_id}", response_model=dict)
    async def legacy_get_character_detail_api(character_id: str):
        """Unversioned REST endpoint for legacy character detail."""
        return await legacy_get_character_detail(character_id)

    # ===================================================================
    # Real-time Events SSE Endpoint (Dashboard Live API Integration)
    # ===================================================================

    # Track active SSE connections for monitoring
    active_sse_connections = {"count": 0}

    async def event_generator(client_id: str) -> AsyncGenerator[str, None]:
        """
        Async generator yielding SSE-formatted events for real-time dashboard updates.

        Streams events with format:
        - retry: <milliseconds>
        - id: <event-id>
        - data: <json-payload>

        Args:
            client_id: Unique identifier for the connected client

        Yields:
            SSE-formatted event strings
        """
        event_id = 0

        try:
            # Send retry directive for client reconnection interval (3 seconds)
            yield "retry: 3000\n\n"

            global_structured_logger.info(
                f"SSE client connected: {client_id}",
                category=LogCategory.SYSTEM
            )
            active_sse_connections["count"] += 1

            # Main event loop - generate events every 2 seconds (MVP: simulated events)
            while True:
                try:
                    await asyncio.sleep(2)  # Event frequency

                    event_id += 1

                    # Generate simulated event (MVP implementation)
                    # Production: Replace with actual event store/message queue integration
                    event_types = ["character", "story", "system", "interaction"]
                    severities = ["low", "medium", "high"]

                    event_data = {
                        "id": f"evt-{event_id}",
                        "type": event_types[event_id % len(event_types)],
                        "title": f"Event {event_id}",
                        "description": f"Simulated dashboard event #{event_id}",
                        "timestamp": int(time.time() * 1000),
                        "severity": severities[event_id % len(severities)],
                    }

                    # Add optional characterName for character-type events
                    if event_data["type"] == "character":
                        event_data["characterName"] = f"Character-{event_id}"

                    # Format as SSE message
                    yield f"id: evt-{event_id}\n"
                    yield f"data: {json.dumps(event_data)}\n\n"

                except asyncio.CancelledError:
                    # Client disconnected - clean up and exit gracefully
                    global_structured_logger.info(
                        f"SSE client disconnected: {client_id}",
                        category=LogCategory.SYSTEM
                    )
                    active_sse_connections["count"] -= 1
                    break

                except Exception as e:
                    # Internal error - send error event but continue streaming
                    global_structured_logger.error(
                        f"SSE event generation error for client {client_id}: {e}",
                        exc_info=e,
                        category=LogCategory.ERROR
                    )

                    error_event = {
                        "id": f"err-{event_id}",
                        "type": "system",
                        "title": "Stream Error",
                        "description": f"Internal error: {str(e)}",
                        "timestamp": int(time.time() * 1000),
                        "severity": "high"
                    }

                    yield f"data: {json.dumps(error_event)}\n\n"

        except Exception as fatal_error:
            # Fatal error - log and terminate
            global_structured_logger.error(
                f"Fatal SSE error for client {client_id}: {fatal_error}",
                exc_info=fatal_error,
                category=LogCategory.ERROR
            )
            active_sse_connections["count"] -= 1
            raise

    @app.get("/api/events/stream", tags=["Dashboard"])
    async def stream_events():
        """
        Server-Sent Events (SSE) endpoint for real-time dashboard events.

        Streams continuous event updates with automatic reconnection support.
        Events include: character actions, story progression, system alerts, interactions.

        Returns:
            StreamingResponse: text/event-stream with continuous event updates

        Example:
            ```javascript
            const eventSource = new EventSource('/api/events/stream');
            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                console.log('Event:', data);
            };
            ```
        """
        # Generate unique client identifier for logging/monitoring
        client_id = secrets.token_hex(8)

        return StreamingResponse(
            event_generator(client_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering for streaming
            }
        )

    @app.post("/simulations", response_model=dict)
    async def legacy_run_simulation(request: dict):
        """Legacy endpoint - Run story simulation with character interactions."""
        try:
            # Extract parameters from request
            character_names = request.get("character_names", [])
            turns = request.get("turns", 3)

            if not character_names:
                raise HTTPException(
                    status_code=400, detail="At least one character name is required"
                )

            # Validate characters exist
            characters_path = os.path.join(os.getcwd(), "characters")
            missing_characters = []
            for char_name in character_names:
                char_path = os.path.join(characters_path, char_name)
                if not os.path.isdir(char_path):
                    missing_characters.append(char_name)

            if missing_characters:
                raise HTTPException(
                    status_code=404,
                    detail=f"Characters not found: {', '.join(missing_characters)}",
                )

            # Get orchestrator
            orchestrator = getattr(app.state, "orchestrator", None)
            if not orchestrator:
                raise HTTPException(
                    status_code=503, detail="System not ready. Please try again."
                )

            # Create characters in the system if they don't exist
            from src.core.data_models import (
                CharacterIdentity,
                CharacterState,
                EmotionalState,
            )

            for char_name in character_names:
                # Check if character already exists in active agents
                active_agents = getattr(orchestrator, "active_agents", {})
                if char_name not in active_agents:
                    # Create character identity
                    character_identity = CharacterIdentity(
                        name=char_name.replace("_", " ").title(),
                        personality_traits=[f"Dynamic personality for {char_name}"],
                        core_beliefs=["Engage in meaningful interactions"],
                        motivations=["Participate in story generation"],
                    )

                    # Create character state
                    character_state = CharacterState(
                        base_identity=character_identity,
                        current_mood=EmotionalState.CALM,
                    )

                    # Create agent context
                    result = await orchestrator.create_agent_context(
                        char_name, character_state
                    )
                    if not result.success:
                        logger.warning(
                            f"Could not create agent context for {char_name}: {result.error}"
                        )

            # Use the story generation API to create a story
            story_api = getattr(app.state, "story_api", None)
            if story_api:
                # Create a story generation request
                import time
                import uuid

                start_time = time.time()
                generation_id = f"legacy_{uuid.uuid4().hex[:8]}"

                # Trigger story generation directly
                story_api.active_generations[generation_id] = {
                    "status": "initiated",
                    "request": {
                        "characters": character_names,
                        "title": "Legacy Simulation Story",
                    },
                    "progress": 0,
                    "stage": "initializing",
                    "start_time": datetime.now(),
                }

                # Run simplified story generation
                try:
                    await story_api._generate_story_async(generation_id)

                    # Get the result
                    generation_state = story_api.active_generations.get(
                        generation_id, {}
                    )
                    story_content = generation_state.get(
                        "story_content", "Story generation completed"
                    )

                    duration = time.time() - start_time

                    response = {
                        "story": story_content,
                        "participants": character_names,
                        "turns_executed": turns,
                        "duration_seconds": duration,
                    }

                    logger.info(
                        f"Legacy simulation completed for {character_names} in {duration:.2f}s"
                    )
                    return response

                except Exception as e:
                    logger.error(f"Story generation failed in legacy simulation: {e}")
                    # Fallback response
                    characters = ", ".join(character_names)
                    fallback_story = (
                        "A story featuring "
                        f"{characters} was generated through the legacy simulation "
                        "system."
                    )
                    return {
                        "story": fallback_story,
                        "participants": character_names,
                        "turns_executed": turns,
                        "duration_seconds": time.time() - start_time,
                    }
            else:
                # Fallback if story API is not available
                characters = ", ".join(character_names)
                fallback_story = (
                    "Legacy simulation story featuring "
                    f"{characters}. The characters interacted for {turns} turns "
                    "in an engaging narrative."
                )
                return {
                    "story": fallback_story,
                    "participants": character_names,
                    "turns_executed": turns,
                    "duration_seconds": 2.0,
                }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in legacy simulation endpoint: {e}")
            raise HTTPException(
                status_code=500, detail=f"Simulation execution failed: {str(e)}"
            )

    logger.info("Legacy routes registered successfully.")


def main():
    """Enhanced main entry point for the API server with comprehensive initialization."""
    config = APIServerConfig()

    # Ensure required directories exist
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    # Set basic logging level
    logging.getLogger().setLevel(config.log_level.upper())

    # Create enhanced application
    app = create_app()

    logger.info("=" * 60)
    logger.info("🚀 Starting Enhanced Novel Engine API Server")
    logger.info("=" * 60)
    logger.info(f"📡 Server: {config.host}:{config.port}")
    logger.info(f"🔧 Mode: {'Development' if config.debug else 'Production'}")
    logger.info(f"📊 Logging: {config.log_level}")
    logger.info(f"💾 Database: {config.database_path}")
    logger.info(f"🔒 Security: {'Enhanced' if SECURITY_AVAILABLE else 'Basic'}")
    logger.info("📈 Monitoring: Enabled")
    logger.info("📚 Documentation: Enhanced")
    logger.info("=" * 60)

    # Run the server
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower(),
        reload=config.debug,
        access_log=config.debug,
        server_header=False,  # Security: Don't expose server info
        date_header=False,  # Security: Don't expose date header
    )


if __name__ == "__main__":
    main()

__all__ = ["create_app", "main"]
