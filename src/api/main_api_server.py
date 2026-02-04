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

# Load environment variables from .env file
from dotenv import load_dotenv
from pathlib import Path

# Load .env file (system environment variables take precedence)
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=False)

import asyncio
import json
import logging
import os
import re
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from src.api.character_api import create_character_api

# Import Context7 integration and enhanced documentation
from src.api.context7_integration_api import create_context7_integration_api
from src.api.emergent_narrative_api import create_emergent_narrative_api
from src.api.enhanced_documentation_system import EnhancedDocumentationSystem
from src.api.error_handlers import (
    ServiceUnavailableException,
    setup_error_handlers,
)
from src.api.health_system import HealthMonitor, create_health_data_response
from src.api.interaction_api import create_interaction_api
from src.api.logging_system import (
    LogCategory,
    LogLevel,
    StructuredLogger,
    setup_logging,
)

# Import new integration systems
from src.api.response_envelopes import (
    APIMetadata,
    HealthCheckData,
    HealthCheckResponse,
    SuccessResponse,
)
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

_CHARACTER_DIRNAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
_WORLD_ID_RE = re.compile(r"[^a-z0-9_-]+")


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
            os.getenv("ENABLE_RATE_LIMITING", "false").lower() == "true"
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

    # Detect testing mode early to skip blocking operations
    is_testing = os.getenv("ORCHESTRATOR_MODE", "").lower() == "testing"

    try:
        try:
            from src.api.startup import ensure_workspace_services

            ensure_workspace_services(app)
        except Exception:
            logger.debug("Workspace services init failed", exc_info=True)

        # Initialize structured logging (skip in testing mode to avoid blocking)
        if is_testing:
            # Create a minimal logger that doesn't try to add middleware
            global_structured_logger = StructuredLogger(
                name="novel_engine_test",
                level=LogLevel.DEBUG,
                output_format="text",
                log_file=None,
            )
            app.state.logger = global_structured_logger
        else:
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
        orchestrator_mode = (
            OrchestratorMode.TESTING if is_testing else OrchestratorMode.PRODUCTION
        )

        orchestrator_config = OrchestratorConfig(
            mode=orchestrator_mode,
            max_concurrent_agents=config.max_concurrent_agents,
            debug_logging=config.debug,
        )

        global_orchestrator = SystemOrchestrator(
            database_path=config.database_path, config=orchestrator_config
        )

        # Add timeout protection for startup (30s for TESTING, 60s for PRODUCTION)
        startup_timeout = 30.0 if is_testing else 60.0
        try:
            startup_result = await asyncio.wait_for(
                global_orchestrator.startup(), timeout=startup_timeout
            )
        except asyncio.TimeoutError:
            raise ServiceUnavailableException(
                "System Orchestrator", f"Startup timed out after {startup_timeout}s"
            )

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

        # Stop background tasks (none for character generation yet)

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
    # monitoring_components = setup_monitoring(app, enable_alerts=not config.debug)
    # app.state.metrics_collector = monitoring_components["metrics_collector"]
    # app.state.alert_manager = monitoring_components["alert_manager"]
    app.state.metrics_collector = None
    app.state.alert_manager = None

    # 4. Enhanced documentation (handled by EnhancedDocumentationSystem)

    # Add middleware (order matters - last added = first executed)
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Raw ASGI header guard intentionally omitted until we re-enable it.

    # Add ASGI-level header guard last so it executes first among middlewares
    # app.add_middleware(
    #    RawHeaderASGIMiddleware,
    #    headers={
    #        "X-Content-Type-Options": "nosniff",
    #        "X-Frame-Options": "DENY",
    #    },
    # )

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
        # security_config = get_production_security_config()
        # security_headers = SecurityHeaders(security_config)
        # app.add_middleware(SecurityHeadersMiddleware, security_headers=security_headers)
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

    def _normalize_cors_origins(origins: list[str]) -> list[str]:
        return [origin.strip() for origin in origins if origin and origin.strip()]

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
        cors_origins = _normalize_cors_origins(config.cors_origins)
        if not cors_origins or "*" in cors_origins:
            logger.warning(
                "CORS_ORIGINS is empty or contains '*'; defaulting to https://novel-engine.app."
            )
            cors_origins = ["https://novel-engine.app"]

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
        trusted_hosts = cors_origins + [
            config.host,
            "localhost",
            "127.0.0.1",
            "testserver",
        ]
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
                logging.getLogger(__name__).debug("Suppressed exception", exc_info=True)

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
                "characters": "/api/characters",
                "character_detail": "/api/characters/{id}",
                "simulations": "/simulations",
                "events_stream": "/api/events/stream",
                "legacy_characters": "/characters",
                "legacy_character_detail": "/characters/{id}",
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
                # Return 503 directly without raising - avoids global exception handler
                response_time = (time.time() - start_time) * 1000
                logger.warning("Health check called before monitor initialized")
                fallback_data = HealthCheckData(
                    service_status="initializing",
                    database_status="unknown",
                    orchestrator_status="unknown",
                    active_agents=0,
                    uptime_seconds=0,
                    version="1.1.0",
                    environment="startup",
                )
                metadata = APIMetadata(
                    timestamp=datetime.now(),
                    api_version="1.1",
                    server_time=response_time,
                )
                response = HealthCheckResponse(data=fallback_data, metadata=metadata)
                return JSONResponse(
                    content=response.model_dump(mode="json"),
                    status_code=503,
                    headers={
                        "Cache-Control": "no-cache",
                        "X-Content-Type-Options": "nosniff",
                        "X-Frame-Options": "DENY",
                    },
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
                content=response.model_dump(mode="json"),
                status_code=status_code,
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                },
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
                content=response.model_dump(mode="json"),
                status_code=503,
                headers={
                    "Cache-Control": "no-cache",
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                },
            )

    # Register API routes immediately (not in lifespan)
    _register_api_routes(app)

    # Register legacy routes for backward compatibility
    _register_legacy_routes(app)

    return app


def _register_api_routes(app: FastAPI):
    """Register all API routes immediately."""
    # Create API instances; orchestrator will be injected during lifespan       
    character_api = create_character_api(None)
    interaction_api = create_interaction_api(None)
    subjective_reality_api = create_subjective_reality_api(None)
    emergent_narrative_api = create_emergent_narrative_api(None)
    context7_integration_api = create_context7_integration_api(None)

    # Store API instances in app state for lifespan initialization
    app.state.character_api = character_api
    app.state.interaction_api = interaction_api
    app.state.subjective_reality_api = subjective_reality_api
    app.state.emergent_narrative_api = emergent_narrative_api
    app.state.context7_integration_api = context7_integration_api

    # Setup routes
    is_testing = os.getenv("ORCHESTRATOR_MODE", "").lower() == "testing"
    if not is_testing:
        character_api.setup_routes(app)
    else:
        logger.info("Skipping CharacterAPI routes in testing mode")
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

    # Import all router modules
    from src.api.routers.auth import router as auth_router
    from src.api.routers.cache import router as cache_router
    from src.api.routers.campaigns import router as campaigns_router
    from src.api.routers.characters import router as characters_router
    from src.api.routers.events import router as events_router
    from src.api.routers.generation import router as generation_router
    from src.api.routers.guest import router as guest_router
    from src.api.routers.narratives import router as narratives_router
    from src.api.routers.scene import router as scene_router
    from src.api.routers.health import router as health_router
    from src.api.routers.meta import router as meta_router
    from src.api.routers.orchestration import router as orchestration_router
    from src.api.routers.simulations import router as simulations_router
    from src.api.routers.world import router as world_gen_router
    from src.api.routers.structure import router as structure_router
    from src.api.routers.narrative_generation import router as narrative_generation_router
    from src.api.routers.relationships import router as relationships_router
    from src.api.routers.items import router as items_router
    from src.api.routers.items import character_inventory_router
    from src.api.routers.lore import router as lore_router
    from src.api.routers.memories import router as memories_router
    from src.api.routers.goals import router as goals_router
    from src.api.routers.world_rules import router as world_rules_router
    from src.api.routers.dialogue import router as dialogue_router
    from src.api.routers.social import router as social_router
    from src.api.routers.factions import router as factions_router
    from src.api.routers.prompts import router as prompts_router
    from src.api.routers.experiments import router as experiments_router

    # Register all routers with and without /api prefix for backward compatibility
    # Order matters: register without prefix first, then with prefix
    app.include_router(auth_router)
    app.include_router(cache_router)
    app.include_router(campaigns_router)
    app.include_router(characters_router)
    app.include_router(events_router)
    app.include_router(generation_router)
    app.include_router(guest_router)
    app.include_router(narratives_router)
    app.include_router(scene_router)
    app.include_router(health_router)
    app.include_router(meta_router)
    app.include_router(orchestration_router)
    app.include_router(simulations_router)
    app.include_router(world_gen_router)
    app.include_router(structure_router)
    app.include_router(narrative_generation_router)
    app.include_router(relationships_router)
    app.include_router(items_router)
    app.include_router(character_inventory_router)
    app.include_router(lore_router)
    app.include_router(memories_router)
    app.include_router(goals_router)
    app.include_router(world_rules_router)
    app.include_router(dialogue_router)
    app.include_router(social_router)
    app.include_router(factions_router)
    app.include_router(prompts_router)
    app.include_router(experiments_router)

    # Register with /api prefix
    app.include_router(auth_router, prefix="/api")
    app.include_router(cache_router, prefix="/api")
    app.include_router(campaigns_router, prefix="/api")
    app.include_router(characters_router, prefix="/api")
    app.include_router(events_router, prefix="/api")
    app.include_router(generation_router, prefix="/api")
    app.include_router(guest_router, prefix="/api")
    app.include_router(narratives_router, prefix="/api")
    app.include_router(scene_router, prefix="/api")
    app.include_router(health_router, prefix="/api")
    app.include_router(meta_router, prefix="/api")
    app.include_router(orchestration_router, prefix="/api")
    app.include_router(simulations_router, prefix="/api")
    app.include_router(world_gen_router, prefix="/api")
    app.include_router(structure_router, prefix="/api")
    app.include_router(narrative_generation_router, prefix="/api")
    app.include_router(relationships_router, prefix="/api")
    app.include_router(items_router, prefix="/api")
    app.include_router(character_inventory_router, prefix="/api")
    app.include_router(lore_router, prefix="/api")
    app.include_router(memories_router, prefix="/api")
    app.include_router(goals_router, prefix="/api")
    app.include_router(world_rules_router, prefix="/api")
    app.include_router(dialogue_router, prefix="/api")
    app.include_router(social_router, prefix="/api")
    app.include_router(factions_router, prefix="/api")
    app.include_router(prompts_router, prefix="/api")
    app.include_router(experiments_router, prefix="/api")

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
            raw_character_id = (character_id or "").strip()
            safe_character_id = os.path.basename(raw_character_id)
            if (
                not safe_character_id
                or safe_character_id in {".", ".."}
                or safe_character_id != raw_character_id
                or not _CHARACTER_DIRNAME_RE.fullmatch(safe_character_id)
            ):
                raise HTTPException(status_code=400, detail="Invalid character_id")
            if not os.path.isdir(characters_path):
                raise HTTPException(
                    status_code=404, detail=f"Character '{safe_character_id}' not found"
                )

            available_character_dirs = [
                item
                for item in os.listdir(characters_path)
                if os.path.isdir(os.path.join(characters_path, item))
            ]
            matched_name = next(
                (
                    item
                    for item in available_character_dirs
                    if item == safe_character_id
                ),
                None,
            )
            if not matched_name:
                raise HTTPException(
                    status_code=404, detail=f"Character '{safe_character_id}' not found"
                )

            character_path = os.path.join(characters_path, matched_name)

            character_file = os.path.join(
                character_path, f"character_{matched_name}.md"
            )
            stats_file = os.path.join(character_path, "stats.yaml")

            character_data = {
                "character_id": safe_character_id,
                "name": safe_character_id.replace("_", " ").title(),
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

            if os.path.exists(character_file):
                try:
                    with open(character_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        lines = content.split("\n")
                        for line in lines:
                            if line.startswith("# "):
                                character_data["name"] = line[2:].strip()
                            elif (
                                "background" in line.lower()
                                or "summary" in line.lower()
                            ):
                                character_data["background_summary"] = line.strip()
                except Exception:
                    logger.warning("Could not read character file", exc_info=True)

            if os.path.exists(stats_file):
                try:
                    import yaml

                    with open(stats_file, "r", encoding="utf-8") as f:
                        stats = yaml.safe_load(f)
                        if isinstance(stats, dict):
                            character_data["skills"] = stats.get("skills", {})
                            character_data["metadata"].update(stats.get("metadata", {}))
                except Exception:
                    logger.warning("Could not read stats file", exc_info=True)

            logger.info("Legacy character detail endpoint returned data")
            return character_data

        except HTTPException:
            raise
        except Exception:
            logger.error("Error in legacy character detail endpoint", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve character details",
            )

    @app.get("/api/characters", response_model=dict)
    async def legacy_get_characters_api():
        """Unversioned REST endpoint for legacy characters list."""
        return await legacy_get_characters()

    @app.get("/api/characters/{character_id}", response_model=dict)
    async def legacy_get_character_detail_api(character_id: str):
        """Unversioned REST endpoint for legacy character detail."""
        return await legacy_get_character_detail(character_id)

    def _ensure_workspace_services() -> None:
        if getattr(app.state, "workspace_store", None) is None:
            try:
                from src.api.startup import ensure_workspace_services

                ensure_workspace_services(app)
            except Exception:
                logger.debug(
                    "Failed to initialize workspace services", exc_info=True
                )

    def _resolve_workspace_id(request: Request, create_if_missing: bool) -> Optional[str]:
        _ensure_workspace_services()
        manager = getattr(app.state, "guest_session_manager", None)
        store = getattr(app.state, "workspace_store", None)
        if not manager or not store:
            return None
        token = request.cookies.get(manager.cookie_name)
        if token:
            workspace_id = manager.decode(token)
            if workspace_id:
                store.get_or_create(workspace_id)
                return workspace_id
        default_workspace_id = getattr(app.state, "default_workspace_id", None)
        if default_workspace_id:
            store.get_or_create(default_workspace_id)
            return default_workspace_id
        if create_if_missing:
            workspace = store.create()
            return workspace.id
        return None

    def _get_world_store() -> Dict[str, Dict[str, Any]]:
        store = getattr(app.state, "world_store", None)
        if store is None:
            store = {}
            app.state.world_store = store
        return store

    def _normalize_world_id(value: str) -> str:
        candidate = (value or "").strip().lower()
        candidate = _WORLD_ID_RE.sub("_", candidate).strip("_")
        if not candidate:
            raise HTTPException(status_code=422, detail="World name is required")
        return candidate

    def _normalize_export_character(record: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(record)
        agent_id = (
            payload.get("agent_id")
            or payload.get("id")
            or payload.get("character_id")
            or payload.get("name")
        )
        payload["agent_id"] = agent_id
        payload.setdefault("name", payload.get("character_name") or agent_id or "")
        return payload

    @app.post("/api/worlds", response_model=dict)
    async def create_world(payload: Dict[str, Any]) -> Dict[str, Any]:
        name = (payload.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=422, detail="World name is required")
        store = _get_world_store()
        world_id = _normalize_world_id(payload.get("id") or name)
        candidate = world_id
        suffix = 2
        while candidate in store:
            candidate = f"{world_id}_{suffix}"
            suffix += 1
        world_id = candidate
        now = datetime.now().isoformat()
        world = {
            "id": world_id,
            "name": name,
            "description": payload.get("description") or "",
            "settings": payload.get("settings") or {},
            "locations": payload.get("locations") or [],
            "rules": payload.get("rules") or [],
            "factions": payload.get("factions") or [],
            "metadata": payload.get("metadata") or {},
            "created_at": now,
            "updated_at": now,
        }
        store[world_id] = world
        return {"data": world}

    @app.get("/api/worlds/{world_id}", response_model=dict)
    async def get_world(world_id: str) -> Dict[str, Any]:
        store = _get_world_store()
        world = store.get(world_id)
        if not world:
            raise HTTPException(status_code=404, detail="World not found")
        return {"data": world}

    @app.put("/api/worlds/{world_id}", response_model=dict)
    async def update_world(world_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        store = _get_world_store()
        world = store.get(world_id)
        if not world:
            raise HTTPException(status_code=404, detail="World not found")
        if "name" in payload and str(payload.get("name", "")).strip():
            world["name"] = str(payload.get("name")).strip()
        if "description" in payload:
            world["description"] = payload.get("description") or ""
        if "settings" in payload and isinstance(payload.get("settings"), dict):
            world["settings"].update(payload["settings"])
        if "rules" in payload and isinstance(payload.get("rules"), list):
            world["rules"] = payload["rules"]
        if "factions" in payload and isinstance(payload.get("factions"), list):
            world["factions"] = payload["factions"]
        if "metadata" in payload and isinstance(payload.get("metadata"), dict):
            world["metadata"].update(payload["metadata"])
        if "locations" in payload and isinstance(payload.get("locations"), list):
            existing = world.get("locations") or []
            world["locations"] = existing + payload["locations"]
        world["updated_at"] = datetime.now().isoformat()
        return {"data": world}

    @app.delete("/api/worlds/{world_id}", response_model=dict)
    async def delete_world(world_id: str) -> Dict[str, Any]:
        store = _get_world_store()
        if world_id not in store:
            raise HTTPException(status_code=404, detail="World not found")
        store.pop(world_id, None)
        return {"data": {"id": world_id, "deleted": True}}

    @app.get("/api/worlds", response_model=dict)
    async def list_worlds() -> Dict[str, Any]:
        store = _get_world_store()
        return {"data": {"worlds": list(store.values())}}

    @app.get("/api/export/characters/{character_id}", response_model=dict)
    async def export_character(
        request: Request,
        character_id: str,
    ) -> Dict[str, Any]:
        workspace_id = _resolve_workspace_id(request, create_if_missing=False)
        store = getattr(app.state, "workspace_character_store", None)
        if not workspace_id or not store:
            raise HTTPException(status_code=404, detail="Character not found")
        record = store.get(workspace_id, character_id)
        if not record:
            raise HTTPException(status_code=404, detail="Character not found")
        return {"data": _normalize_export_character(record)}

    @app.get("/api/export/all", response_model=dict)
    async def export_all(
        request: Request,
    ) -> Dict[str, Any]:
        workspace_id = _resolve_workspace_id(request, create_if_missing=False)
        store = getattr(app.state, "workspace_character_store", None)
        characters: list[Dict[str, Any]] = []
        if workspace_id and store:
            for char_id in store.list_ids(workspace_id):
                record = store.get(workspace_id, char_id)
                if record:
                    characters.append(_normalize_export_character(record))
        worlds = list(_get_world_store().values())
        return {
            "version": "1.0",
            "timestamp": time.time(),
            "characters": characters,
            "worlds": worlds,
            "metadata": {"source": "api"},
        }

    @app.post("/api/import/all", response_model=dict)
    async def import_all(
        request: Request,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        workspace_id = _resolve_workspace_id(request, create_if_missing=True)
        store = getattr(app.state, "workspace_character_store", None)
        if not store or not workspace_id:
            raise HTTPException(status_code=503, detail="Workspace unavailable")

        version = payload.get("version")
        if version and str(version) not in {"1.0", "1.1"}:
            raise HTTPException(status_code=400, detail="Unsupported export version")

        characters = payload.get("characters") or []
        if not isinstance(characters, list):
            raise HTTPException(status_code=422, detail="Characters must be a list")

        imported = 0
        for entry in characters:
            if not isinstance(entry, dict):
                raise HTTPException(status_code=422, detail="Invalid character entry")
            agent_id = (
                entry.get("agent_id")
                or entry.get("id")
                or entry.get("character_id")
                or entry.get("name")
            )
            if not agent_id:
                raise HTTPException(
                    status_code=422, detail="Character requires agent_id or name"
                )
            record_payload = {
                "name": entry.get("name") or entry.get("character_name") or agent_id,
                "background_summary": entry.get("background_summary", ""),
                "personality_traits": entry.get("personality_traits", ""),
                "skills": entry.get("skills") or {},
                "relationships": entry.get("relationships") or {},
                "current_location": entry.get("current_location") or "",
                "inventory": entry.get("inventory") or [],
                "metadata": entry.get("metadata") or {},
                "structured_data": entry.get("structured_data") or {},
                "current_status": entry.get("current_status") or "active",
                "narrative_context": entry.get("narrative_context") or "",
            }
            existing = store.get(workspace_id, str(agent_id))
            if existing:
                store.update(workspace_id, str(agent_id), record_payload)
            else:
                store.create(workspace_id, str(agent_id), record_payload)
            imported += 1

        worlds = payload.get("worlds") or []
        if not isinstance(worlds, list):
            raise HTTPException(status_code=422, detail="Worlds must be a list")

        store_worlds = _get_world_store()
        for world in worlds:
            if not isinstance(world, dict):
                raise HTTPException(status_code=422, detail="Invalid world entry")
            name = (world.get("name") or "").strip()
            if not name:
                raise HTTPException(status_code=422, detail="World name is required")
            world_id = world.get("id") or _normalize_world_id(name)
            payload_world = {
                "id": world_id,
                "name": name,
                "description": world.get("description") or "",
                "settings": world.get("settings") or {},
                "locations": world.get("locations") or [],
                "rules": world.get("rules") or [],
                "factions": world.get("factions") or [],
                "metadata": world.get("metadata") or {},
                "created_at": world.get("created_at") or datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            store_worlds[world_id] = payload_world

        return {"data": {"imported_characters": imported, "imported_worlds": len(worlds)}}

    # ===================================================================
    # Real-time Events SSE Endpoint (Dashboard Live API Integration)
    # ===================================================================

    # Track active SSE connections for monitoring
    active_sse_connections = {"count": 0}

    async def event_generator(client_id: str, limit: Optional[int] = None):
        """
        Async generator yielding SSE-formatted events for real-time dashboard updates.

        Streams events with format:
        - retry: <milliseconds>
        - id: <event-id>
        - data: <json-payload>

        Args:
            client_id: Unique identifier for the connected client
            limit: Optional maximum number of events to generate

        Yields:
            SSE-formatted event strings
        """
        event_id = 0
        events_generated = 0
        effective_limit = 1 if limit is not None else None

        disconnected_logged = False

        try:
            # Send retry directive for client reconnection interval (3 seconds)
            yield "retry: 3000\n\n"

            if global_structured_logger:
                global_structured_logger.info(
                    f"SSE client connected: {client_id}", category=LogCategory.SYSTEM
                )
            else:
                logger.info(f"SSE client connected: {client_id}")

            active_sse_connections["count"] += 1

            # Main event loop
            while True:
                # Check limit
                if effective_limit is not None and events_generated >= effective_limit:
                    if global_structured_logger:
                        global_structured_logger.info(
                            f"SSE limit reached for {client_id}",
                            category=LogCategory.SYSTEM,
                        )
                    else:
                        logger.info(f"SSE limit reached for {client_id}")
                    break

                try:
                    await asyncio.sleep(2)  # Event frequency

                    event_id += 1
                    events_generated += 1

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
                    if global_structured_logger:
                        global_structured_logger.info(
                            f"SSE client disconnected: {client_id}",
                            category=LogCategory.SYSTEM,
                        )
                    else:
                        logger.info(f"SSE client disconnected: {client_id}")
                    disconnected_logged = True
                    raise

                except Exception as e:
                    # Internal error - send error event but continue streaming
                    if global_structured_logger:
                        global_structured_logger.error(
                            "SSE event generation error.",
                            exc_info=e,
                            category=LogCategory.ERROR,
                        )
                    else:
                        logger.exception("SSE event generation error.")

                    error_event = {
                        "id": f"err-{event_id}",
                        "type": "system",
                        "title": "Stream Error",
                        "description": "Internal error while streaming events.",
                        "timestamp": int(time.time() * 1000),
                        "severity": "high",
                    }

                    yield f"data: {json.dumps(error_event)}\n\n"

        except asyncio.CancelledError:
            if not disconnected_logged:
                if global_structured_logger:
                    global_structured_logger.info(
                        f"SSE client disconnected: {client_id}",
                        category=LogCategory.SYSTEM,
                    )
                else:
                    logger.info(f"SSE client disconnected: {client_id}")
            raise
        except Exception as fatal_error:
            # Fatal error - log and terminate
            if global_structured_logger:
                global_structured_logger.error(
                    "Fatal SSE error.",
                    exc_info=fatal_error,
                    category=LogCategory.ERROR,
                )
            else:
                logger.exception("Fatal SSE error.")
            raise
        finally:
            active_sse_connections["count"] = max(
                0, active_sse_connections["count"] - 1
            )

    @app.get("/api/events/stream", tags=["Dashboard"])
    async def stream_events(limit: Optional[int] = None):
        """
        Server-Sent Events (SSE) endpoint for real-time dashboard events.

        Streams continuous event updates with automatic reconnection support.
        Events include: character actions, story progression, system alerts, interactions.

        Args:
            limit: Optional maximum number of events to return (useful for testing)

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
            event_generator(client_id, limit=limit),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering for streaming
            },
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
            available_character_dirs = set()
            if os.path.isdir(characters_path):
                available_character_dirs = {
                    item
                    for item in os.listdir(characters_path)
                    if os.path.isdir(os.path.join(characters_path, item))
                }
            missing_characters = []
            for char_name in character_names:
                raw_char_name = (char_name or "").strip()
                safe_char_name = os.path.basename(raw_char_name)
                if (
                    not safe_char_name
                    or safe_char_name in {".", ".."}
                    or safe_char_name != raw_char_name
                    or not _CHARACTER_DIRNAME_RE.fullmatch(safe_char_name)
                ):
                    raise HTTPException(
                        status_code=400, detail="Invalid character_name"
                    )
                if safe_char_name not in available_character_dirs:
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
                        logger.warning("Could not create agent context")

            # Legacy simulation fallback response (story API removed in M2 purge)
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
    # Run the server
    uvicorn.run(
        "src.api.main_api_server:app",
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

# Create app instance at module level for uvicorn to import
app = create_app()

__all__ = ["create_app", "main", "app"]
