#!/usr/bin/env python3
"""
Secure FastAPI Server for Novel Engine
======================================

Enterprise-grade secure FastAPI server with comprehensive security framework,
authentication, authorization, input validation, and performance optimization.

Architecture: Zero Trust API with Defense in Depth Security
Security Level: Enterprise Grade (OWASP Top 10 Compliant)
Performance: High-throughput with async operations and caching
Author: Novel Engine Development Team
"""

import json
import logging
import os
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import Body, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.api.character_api import create_character_api
from src.api.interaction_api import create_interaction_api
from src.api.story_generation_api import (
    StoryGenerationRequest,
    create_story_generation_api,
)
from src.core.system_orchestrator import (
    OrchestratorConfig,
    OrchestratorMode,
    SystemOrchestrator,
)

# Import our secure components
from src.security import (
    Permission,
    RateLimitConfig,
    SecurityService,
    TokenPair,
    User,
    UserLogin,
    UserRegistration,
    UserRole,
    create_rate_limit_middleware,
    create_security_headers_middleware,
    create_validation_middleware,
    get_development_security_config,
    get_production_security_config,
    get_rate_limiter,
    get_security_service,
    initialize_security_service,
)

# Comprehensive logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
)
logger = logging.getLogger(__name__)


class SecureAPIConfig:
    """Secure API Configuration Manager"""

    def __init__(self):
        # Basic server configuration
        self.host = os.getenv("API_HOST", "127.0.0.1")
        self.port = int(os.getenv("API_PORT", "8000"))
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.environment = os.getenv("ENVIRONMENT", "development")

        # Database and storage
        self.database_path = os.getenv("DATABASE_PATH", "data/secure_api.db")
        self.security_database_path = os.getenv(
            "SECURITY_DATABASE_PATH", "data/security.db"
        )

        # Security configuration
        self.secret_key = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
        self.enable_docs = (
            os.getenv("ENABLE_DOCS", "true" if self.debug else "false").lower()
            == "true"
        )

        # CORS configuration
        cors_origins = os.getenv(
            "CORS_ORIGINS", "http://localhost:3000" if self.debug else ""
        )
        self.cors_origins = [
            origin.strip() for origin in cors_origins.split(",") if origin.strip()
        ]

        # Performance configuration
        self.max_concurrent_agents = int(os.getenv("MAX_CONCURRENT_AGENTS", "20"))
        self.enable_metrics = os.getenv("ENABLE_METRICS", "true").lower() == "true"

        # Rate limiting configuration
        self.rate_limit_requests_per_minute = int(os.getenv("RATE_LIMIT_RPM", "60"))
        self.rate_limit_requests_per_hour = int(os.getenv("RATE_LIMIT_RPH", "1000"))

        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)


class OptimizedSecureJSONResponse(JSONResponse):
    """Optimized JSON Response with Security Headers"""

    def __init__(
        self,
        content: Any = None,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        cache_control: Optional[str] = None,
        max_age: Optional[int] = None,
    ):

        if headers is None:
            headers = {}

        # Performance headers
        if cache_control:
            headers["Cache-Control"] = cache_control
        elif max_age is not None:
            headers["Cache-Control"] = f"public, max-age={max_age}"
        else:
            headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

        # Security headers (additional to middleware)
        headers["X-Content-Type-Options"] = "nosniff"
        headers["X-API-Version"] = "2.0.0-secure"
        headers["X-Security-Framework"] = "Enterprise-Grade"

        # Add timing information for performance monitoring
        headers["Server-Timing"] = "api;dur=0"

        super().__init__(content=content, status_code=status_code, headers=headers)


# REQUEST/RESPONSE MODELS
class UserRegistrationRequest(BaseModel):
    """User Registration Request Model"""

    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole = UserRole.READER


class UserLoginRequest(BaseModel):
    """User Login Request Model"""

    username: str
    password: str


class ApiKeyResponse(BaseModel):
    """API Key Response Model"""

    api_key: str
    message: str


class SystemHealthResponse(BaseModel):
    """System Health Response Model"""

    status: str
    timestamp: datetime
    version: str
    environment: str
    security_level: str
    system_health: Optional[Dict[str, Any]] = None
    rate_limit_stats: Optional[Dict[str, Any]] = None


class SecureSimulationRequest(BaseModel):
    """Secure Simulation Request Model"""

    character_names: List[str] = Field(min_length=1, max_length=6)
    turns: Optional[int] = Field(default=3, ge=1, le=10)
    style: Optional[str] = Field(default="narrative", max_length=50)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "character_names": ["Alice", "Bob"],
                "turns": 3,
                "style": "narrative",
            }
        }
    )


class SecureSimulationResponse(BaseModel):
    """Secure Simulation Response Model"""

    simulation_id: str
    story: str
    participants: List[str]
    turns_executed: int
    duration_seconds: float
    timestamp: datetime
    user_id: str


class CharacterCreateRequest(BaseModel):
    """User character creation request"""

    name: str = Field(min_length=2, max_length=100)
    background_summary: str = Field("", max_length=1000)
    personality_traits: str = Field("", max_length=500)
    skills: Dict[str, float] = Field(default_factory=dict)
    relationships: Dict[str, float] = Field(default_factory=dict)
    current_location: str | None = Field(default=None, max_length=200)


class CharacterRecord(BaseModel):
    """Stored character record"""

    id: str
    user_id: str
    name: str
    background_summary: str
    personality_traits: str
    skills: Dict[str, float]
    relationships: Dict[str, float]
    current_location: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# GLOBAL STATE
global_orchestrator: Optional[SystemOrchestrator] = None
security_service: Optional[SecurityService] = None
user_character_store: Dict[str, List[CharacterRecord]] = {}
USER_CHARACTER_STORE_PATH = Path("data/user_characters.json")
AUTH_BYPASS_FLAG = "DISABLE_CHAR_AUTH"


def _persist_user_characters():
    try:
        serializable = {
            user_id: [
                {
                    **record.model_dump(),
                    "created_at": record.created_at.isoformat(),
                    "updated_at": record.updated_at.isoformat(),
                }
                for record in records
            ]
            for user_id, records in user_character_store.items()
        }
        USER_CHARACTER_STORE_PATH.write_text(json.dumps(serializable, indent=2))
    except Exception as err:
        logging.getLogger(__name__).error(f"Failed to persist user characters: {err}")


def _load_user_characters():
    if USER_CHARACTER_STORE_PATH.exists():
        try:
            data = json.loads(USER_CHARACTER_STORE_PATH.read_text())
            for user_id, records in data.items():
                user_character_store[user_id] = [
                    CharacterRecord(
                        **record,
                        created_at=datetime.fromisoformat(record["created_at"]),
                        updated_at=datetime.fromisoformat(record["updated_at"]),
                    )
                    for record in records
                ]
        except Exception as load_err:
            logging.getLogger(__name__).warning(
                f"Failed to load user characters: {load_err}"
            )


def _get_default_characters() -> List[str]:
    try:
        base_path = Path(__file__).resolve().parent.parent / "characters"
        if base_path.exists() and base_path.is_dir():
            return sorted({p.name for p in base_path.iterdir() if p.is_dir()})
    except Exception:
        pass
    return ["aria", "engineer", "pilot", "scientist", "test"]


def _get_user_characters(user_id: str) -> List[CharacterRecord]:
    return list(user_character_store.get(user_id, []))


def _upsert_user_character(
    user_id: str, payload: CharacterCreateRequest
) -> CharacterRecord:
    now = datetime.now(timezone.utc)
    existing = user_character_store.setdefault(user_id, [])
    record = CharacterRecord(
        id=secrets.token_urlsafe(8),
        user_id=user_id,
        name=payload.name.strip(),
        background_summary=payload.background_summary.strip(),
        personality_traits=payload.personality_traits.strip(),
        skills=payload.skills,
        relationships=payload.relationships,
        current_location=payload.current_location,
        created_at=now,
        updated_at=now,
    )
    existing.append(record)
    _persist_user_characters()
    return record


def _resolve_available_characters(user_id: str) -> List[str]:
    defaults = _get_default_characters()
    user_chars = [c.name for c in _get_user_characters(user_id)]
    return sorted({*defaults, *user_chars})


def _auth_dependency(permission: Permission):
    async def _dep():
        # Test-mode bypass for local/dev automation
        if os.getenv(AUTH_BYPASS_FLAG, "0") == "1":
            return User(
                id="bypass-user",
                username="bypass-user",
                email="bypass@example.com",
                password_hash="",
                role=UserRole.READER,
                is_active=True,
                is_verified=True,
                api_key=None,
            )
        return await get_security_service().require_permission(permission)()

    return _dep


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application Lifecycle Management"""
    global global_orchestrator, security_service

    config = SecureAPIConfig()
    logger.info("Starting secure API server")

    try:
        # Initialize security service
        security_service = initialize_security_service(
            config.security_database_path, config.secret_key
        )
        await security_service.initialize_database()
        logger.info("Security service initialized")

        # Initialize user character store
        USER_CHARACTER_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _load_user_characters()

        # Initialize system orchestrator
        orchestrator_config = OrchestratorConfig(
            mode=(
                OrchestratorMode.PRODUCTION
                if not config.debug
                else OrchestratorMode.DEVELOPMENT
            ),
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
            logger.error(f"System orchestrator startup failed: {error_msg}")
            raise Exception(f"System Orchestrator startup failed: {error_msg}")

        app.state.orchestrator = global_orchestrator
        app.state.security_service = security_service
        app.state.config = config

        # Initialize API components
        if getattr(app.state, "character_api", None):
            app.state.character_api.set_orchestrator(global_orchestrator)
        if getattr(app.state, "story_api", None):
            app.state.story_api.set_orchestrator(global_orchestrator)
            await app.state.story_api.start_background_tasks()
        if getattr(app.state, "interaction_api", None):
            app.state.interaction_api.set_orchestrator(global_orchestrator)

        logger.info("Secure API server started successfully")
        yield

    finally:
        logger.info("Shutting down secure API server")

        # Stop background tasks
        if hasattr(app.state, "story_api"):
            await app.state.story_api.stop_background_tasks()

        # Shutdown orchestrator
        if global_orchestrator:
            await global_orchestrator.shutdown()

        logger.info("Secure API server shutdown complete")


def create_secure_app() -> FastAPI:
    """Create Secure FastAPI Application"""
    config = SecureAPIConfig()

    # Initialize global security service so dependency wiring does not fail at import time
    initialize_security_service(config.security_database_path, config.secret_key)

    # Create FastAPI app with security-focused configuration
    app = FastAPI(
        title="Novel Engine - Secure API",
        description="Enterprise-grade secure API for the Novel Engine with comprehensive security framework",
        version="2.0.0-secure",
        lifespan=lifespan,
        docs_url="/docs" if config.enable_docs else None,
        redoc_url="/redoc" if config.enable_docs else None,
        openapi_url="/openapi.json" if config.enable_docs else None,
    )

    # MIDDLEWARE CONFIGURATION (Order matters - last added = first executed)

    # Security headers (first layer of protection)
    if config.environment == "production":
        security_config = get_production_security_config()
    else:
        security_config = get_development_security_config()

    security_config.allowed_origins = config.cors_origins
    app.add_middleware(create_security_headers_middleware, config=security_config)

    # Rate limiting (second layer)
    rate_limit_config = RateLimitConfig(
        requests_per_minute=config.rate_limit_requests_per_minute,
        requests_per_hour=config.rate_limit_requests_per_hour,
        whitelist_ips=["127.0.0.1", "::1"] if config.debug else [],
        endpoint_configs={
            "/auth/login": {"requests_per_minute": 10},  # Stricter for auth
            "/auth/register": {"requests_per_minute": 5},
            "/simulations": {"requests_per_minute": 30},
        },
    )
    app.add_middleware(create_rate_limit_middleware, config=rate_limit_config)

    # Input validation (third layer) - allow opt-out for local debugging
    if os.getenv("SKIP_INPUT_VALIDATION", "0") != "1":
        app.add_middleware(create_validation_middleware)

    # Compression (performance)
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # CORS (controlled access)
    if config.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["*"],
        )

    # Trusted host middleware (production security)
    if config.environment == "production" and config.cors_origins:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=config.cors_origins)

    # EXCEPTION HANDLERS
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """General Exception Handler"""
        logger.error(
            f"Unhandled exception: {exc} | Path: {request.url.path}", exc_info=True
        )
        return OptimizedSecureJSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "type": "internal_error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": secrets.token_urlsafe(8),
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """HTTP Exception Handler"""
        return OptimizedSecureJSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "type": "http_error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    # AUTHENTICATION ROUTES
    @app.post("/auth/register", response_model=TokenPair, tags=["Authentication"])
    async def register_user(registration: UserRegistrationRequest, request: Request):
        """User Registration Endpoint"""
        try:
            security_service = get_security_service()

            # Get client info for security logging
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")

            # Register user
            user_reg = UserRegistration(
                username=registration.username,
                email=registration.email,
                password=registration.password,
                role=registration.role,
            )

            user = await security_service.register_user(user_reg, client_ip, user_agent)

            # Create token pair
            token_pair = await security_service.create_token_pair(user)

            logger.info(
                f"User registered successfully: {user.username} ({user.role.value})"
            )
            return token_pair

        except Exception as e:
            logger.error(f"User registration failed: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/auth/login", response_model=TokenPair, tags=["Authentication"])
    async def login_user(login: UserLoginRequest, request: Request):
        """User Login Endpoint"""
        try:
            security_service = get_security_service()

            # Get client info for security logging
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")

            # Authenticate user
            user_login = UserLogin(username=login.username, password=login.password)
            user = await security_service.authenticate_user(
                user_login, client_ip, user_agent
            )

            if not user:
                raise HTTPException(
                    status_code=401, detail="Invalid username or password"
                )

            # Create token pair
            token_pair = await security_service.create_token_pair(user)

            logger.info(f"User login successful: {user.username}")
            return token_pair

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"User login failed: {e}")
            raise HTTPException(status_code=500, detail="Login failed")

    @app.post("/auth/refresh", response_model=TokenPair, tags=["Authentication"])
    async def refresh_token(
        refresh_token: str = Body(..., embed=True, description="Refresh token")
    ):
        """Token Refresh Endpoint"""
        try:
            security_service = get_security_service()
            token_pair = await security_service.refresh_access_token(refresh_token)
            return token_pair
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise HTTPException(status_code=401, detail="Invalid refresh token")

    @app.post("/auth/logout", tags=["Authentication"])
    async def logout_user(
        current_user: User = Depends(get_security_service().get_current_user),
    ):
        """User Logout Endpoint"""
        # In a production system, you would revoke the token here
        logger.info(f"User logout: {current_user.username}")
        return OptimizedSecureJSONResponse(
            content={"message": "Logged out successfully"}
        )

    @app.post("/auth/api-key", response_model=ApiKeyResponse, tags=["Authentication"])
    async def generate_api_key(
        current_user: User = Depends(
            get_security_service().require_permission(Permission.API_ACCESS)
        ),
    ):
        """API Key Generation Endpoint"""
        try:
            security_service = get_security_service()
            api_key = await security_service.generate_api_key(current_user.id)

            logger.info(f"API key generated: {current_user.username}")
            return ApiKeyResponse(
                api_key=api_key, message="API key generated successfully"
            )
        except Exception as e:
            logger.error(f"API key generation failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate API key")

    # SYSTEM ROUTES
    @app.get("/", tags=["System"])
    async def root():
        """Root API Endpoint"""
        config = SecureAPIConfig()
        return OptimizedSecureJSONResponse(
            content={
                "name": "Novel Engine - Secure API",
                "version": "2.0.0-secure",
                "status": "operational",
                "security_level": "enterprise-grade",
                "environment": config.environment,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "features": {
                    "authentication": "JWT with refresh tokens",
                    "authorization": "Role-based access control (RBAC)",
                    "security": "OWASP Top 10 compliant",
                    "performance": "Async with caching",
                    "monitoring": "Comprehensive logging and metrics",
                },
                "endpoints": {
                    "health": "/health",
                    "authentication": "/auth/*",
                    "characters": "/api/characters",
                    "stories": "/api/stories",
                    "simulations": "/simulations",
                    "interactions": "/api/interactions",
                },
            },
            max_age=300,  # Cache for 5 minutes
        )

    @app.get("/health", response_model=SystemHealthResponse, tags=["System"])
    async def health_check(request: Request):
        """System Health Check Endpoint"""
        try:
            orchestrator = getattr(app.state, "orchestrator", None)
            rate_limiter = get_rate_limiter()
            config = SecureAPIConfig()

            health_data = None
            if orchestrator:
                health_result = await orchestrator.get_system_health()
                health_data = health_result.data if health_result.success else None

            # Get rate limiting stats
            rate_limit_stats = rate_limiter.get_global_stats()

            return SystemHealthResponse(
                status="healthy" if orchestrator else "starting",
                timestamp=datetime.now(timezone.utc),
                version="2.0.0-secure",
                environment=config.environment,
                security_level="enterprise-grade",
                system_health=health_data,
                rate_limit_stats=rate_limit_stats,
            )

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return OptimizedSecureJSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": "Health check failed",
                },
            )

    # SECURE SIMULATION ENDPOINT
    @app.post(
        "/simulations", response_model=SecureSimulationResponse, tags=["Simulations"]
    )
    async def run_secure_simulation(
        request: SecureSimulationRequest,
        current_user: User = Depends(_auth_dependency(Permission.SIMULATION_CREATE)),
    ):
        """Secure Simulation Execution Endpoint"""
        start_time = datetime.now(timezone.utc)
        simulation_id = secrets.token_urlsafe(16)

        logger.info(
            f"Simulation requested: {request.character_names} | User: {current_user.username}"
        )

        try:
            orchestrator = getattr(app.state, "orchestrator", None)
            story_api = getattr(app.state, "story_api", None)

            if not orchestrator or not story_api:
                raise HTTPException(
                    status_code=503, detail="System not ready. Please try again."
                )

            if len(set(request.character_names)) != len(request.character_names):
                raise HTTPException(
                    status_code=400, detail="Duplicate character names are not allowed"
                )

            available_characters = set(_resolve_available_characters(current_user.id))
            missing = [
                name
                for name in request.character_names
                if name not in available_characters
            ]
            if missing:
                raise HTTPException(
                    status_code=422,
                    detail=f"Characters unavailable for simulation: {', '.join(missing)}",
                )

            active_agents = getattr(orchestrator, "active_agents", {})
            for name in request.character_names:
                if name not in active_agents:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Character not registered in orchestrator: {name}",
                    )

            generation_id = f"secure_{uuid.uuid4().hex[:8]}"
            story_request = StoryGenerationRequest(
                characters=request.character_names,
                title=request.style or "Simulation Story",
            )

            story_api.active_generations[generation_id] = {
                "status": "initiated",
                "request": story_request,
                "progress": 0,
                "stage": "initializing",
                "start_time": datetime.now(),
            }

            await story_api._generate_story_async(generation_id)

            generation_state = story_api.active_generations.get(generation_id, {})
            story_content = generation_state.get("story_content", "")
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            response = SecureSimulationResponse(
                simulation_id=generation_id,
                story=story_content or "Story generation completed.",
                participants=request.character_names,
                turns_executed=request.turns,
                duration_seconds=duration,
                timestamp=start_time,
                user_id=current_user.id,
            )

            logger.info(
                f"Simulation completed: {generation_id} | Duration: {duration:.2f}s"
            )
            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            raise HTTPException(status_code=500, detail="Simulation execution failed")

    # REGISTER API ROUTES
    _register_secure_api_routes(app)

    logger.info("Secure API routes registered successfully")
    return app


def _register_secure_api_routes(app: FastAPI):
    """Secure API Routes Registration"""
    # Create secure API instances
    character_api = (
        None  # Legacy character API endpoints not used for user-created characters
    )
    story_generation_api = create_story_generation_api(None)
    interaction_api = create_interaction_api(None)

    # Store API instances in app state
    app.state.character_api = character_api
    app.state.story_api = story_generation_api
    app.state.interaction_api = interaction_api

    # Setup routes with security decorators
    story_generation_api.setup_routes(app)
    interaction_api.setup_routes(app)

    # --- User Character Routes ---

    @app.post(
        "/api/characters",
        response_model=CharacterRecord,
        status_code=201,
        tags=["Characters"],
    )
    async def create_user_character(
        request: CharacterCreateRequest,
        current_user: User = Depends(_auth_dependency(Permission.CHARACTER_CREATE)),
    ):
        """Create a user-owned character"""
        # Basic business validation
        if any(len(name.strip()) == 0 for name in [request.name]):
            raise HTTPException(status_code=400, detail="Character name is required")
        record = _upsert_user_character(current_user.id, request)
        return record

    @app.get(
        "/api/characters",
        response_model=Dict[str, List[str]],
        tags=["Characters"],
    )
    async def list_user_characters(
        current_user: User = Depends(_auth_dependency(Permission.CHARACTER_READ)),
    ):
        """List user-owned characters merged with defaults"""
        defaults = _get_default_characters()
        user_chars = [c.name for c in _get_user_characters(current_user.id)]
        merged = sorted({*defaults, *user_chars})
        return {"characters": merged}


def main():
    """Main Application Entry Point"""
    config = SecureAPIConfig()

    # Configure logging level
    log_level = "DEBUG" if config.debug else "INFO"
    logging.getLogger().setLevel(log_level)

    # Create secure app
    app = create_secure_app()

    logger.info(
        f"Starting secure API server: {config.host}:{config.port} | Environment: {config.environment}"
    )

    # Start server
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level=log_level.lower(),
        reload=config.debug,
        access_log=config.debug,
        # Production security settings
        server_header=False,
        date_header=False,
    )


if __name__ == "__main__":
    main()

__all__ = ["create_secure_app", "main", "SecureAPIConfig"]
