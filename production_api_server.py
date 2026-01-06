#!/usr/bin/env python3
"""
Production-Hardened FastAPI Server for Novel Engine
==================================================

This module implements a security-hardened FastAPI server with comprehensive
security measures for production deployment.
"""

import asyncio
import logging
import os
import secrets
import ssl
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import jwt
import uvicorn
from src.config.character_factory import CharacterFactory
from src.agents.chronicler_agent import ChroniclerAgent

# Import existing modules
from config_loader import get_config
from src.agents.director_agent import DirectorAgent
from src.event_bus import EventBus
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    logger.error("JWT_SECRET_KEY environment variable is required")
    raise ValueError("JWT_SECRET_KEY environment variable must be set")

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Rate limiting
limiter = Limiter(key_func=get_remote_address)


class SecurityHeaders(BaseHTTPMiddleware):
    """Security headers middleware."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'"
        )

        # Remove server identification
        if "server" in response.headers:
            del response.headers["server"]

        return response


class InputValidator:
    """Enhanced input validation and sanitization."""

    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Sanitize string input."""
        if not isinstance(value, str):
            raise ValueError("Input must be a string")

        # Remove null bytes and control characters
        value = "".join(char for char in value if ord(char) >= 32 or char in "\t\n\r")

        # Truncate if too long
        if len(value) > max_length:
            value = value[:max_length]

        return value.strip()

    @staticmethod
    def validate_character_names(names: List[str]) -> List[str]:
        """Validate character names with strict rules."""
        validated_names = []

        for name in names:
            # Sanitize
            name = InputValidator.sanitize_string(name, 50)

            # Validate format (alphanumeric + spaces + hyphens)
            if not name or len(name) < 2:
                raise ValueError(f"Character name too short: {name}")

            if not all(c.isalnum() or c in " -_" for c in name):
                raise ValueError(f"Invalid characters in name: {name}")

            validated_names.append(name)

        return validated_names


class AuthenticationManager:
    """JWT-based authentication manager."""

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        """Create JWT access token."""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify JWT token."""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )


# Pydantic models with validation
class SimulationRequest(BaseModel):
    character_names: List[str] = Field(..., min_length=2, max_length=6)
    turns: Optional[int] = Field(None, ge=1, le=10)

    @field_validator("character_names")
    @classmethod
    def validate_names(cls, v):
        return InputValidator.validate_character_names(v)


class SimulationResponse(BaseModel):
    story: str
    participants: List[str]
    turns_executed: int
    duration_seconds: float
    request_id: str


class TokenRequest(BaseModel):
    username: str
    password: str


# Security dependency
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Dependency to get current authenticated user."""
    token = credentials.credentials
    payload = AuthenticationManager.verify_token(token)
    return payload.get("sub")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan event handler with security checks."""
    logger.info("Starting production-hardened Novel Engine API server...")

    # Validate environment
    required_env_vars = [
        "ENVIRONMENT",
        "SECRET_KEY",
        "JWT_SECRET_KEY",
        "ADMIN_PASSWORD",
    ]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        raise RuntimeError("Security configuration incomplete")

    # Validate configuration
    try:
        get_config()
        logger.info("Configuration loaded and validated successfully")
    except Exception as e:
        logger.error(f"Configuration error during startup: {e}")
        raise e

    yield
    logger.info("Shutting down production-hardened Novel Engine API server.")


# Create FastAPI app with security configuration
app = FastAPI(
    title="Novel Engine API (Production)",
    description="Production-hardened RESTful API for the Novel Engine Interactive Story System.",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None,
    lifespan=lifespan,
)

# Add security middleware
app.add_middleware(SecurityHeaders)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Trusted hosts (configure for your domain)
if os.getenv("ENVIRONMENT") == "production":
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["your-domain.com", "*.your-domain.com"]
    )

# CORS with restricted origins for production
def _parse_cors_origins(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _resolve_cors_origins() -> List[str]:
    environment = os.getenv("ENVIRONMENT", "development")
    if environment == "production":
        origins = _parse_cors_origins(os.getenv("CORS_ORIGINS"))
        if not origins:
            logger.warning(
                "CORS_ORIGINS is empty in production; defaulting to https://your-domain.com."
            )
            origins = ["https://your-domain.com"]
    else:
        origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]

    if "*" in origins:
        logger.warning("Removing wildcard CORS origin because credentials are enabled.")
        origins = [origin for origin in origins if origin != "*"]
        if not origins:
            origins = ["https://your-domain.com"]

    return origins


allowed_origins = _resolve_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Rate limit exceeded handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler."""
    # Log security-relevant errors
    if exc.status_code in [401, 403, 429]:
        logger.warning(f"Security event: {exc.status_code} from {request.client.host}")

    response = JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "Request failed",
            "detail": exc.detail,
            "request_id": secrets.token_hex(8),
        },
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Fallback exception handler with security headers."""
    logger.exception("Unhandled error", exc_info=exc)
    response = JSONResponse(
        status_code=500,
        content={
            "error": "Request failed",
            "detail": "Internal Server Error",
            "request_id": secrets.token_hex(8),
        },
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


def _reject_query_credentials(request: Request) -> None:
    query_params = request.query_params
    if any(key in query_params for key in ("username", "password", "email")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credentials must be sent in the request body.",
        )


@app.get("/")
@limiter.limit("10/minute")
async def root(request: Request) -> Dict[str, str]:
    """Health check endpoint with rate limiting."""
    return {"message": "Novel Engine API is running securely!"}


@app.get("/health")
@limiter.limit("30/minute")
async def health_check(request: Request) -> Dict[str, Any]:
    """Comprehensive health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0-production",
        "environment": os.getenv("ENVIRONMENT", "development"),
    }


@app.post("/auth/token")
@limiter.limit("5/minute")
async def login(request: Request, credentials: TokenRequest) -> Dict[str, str]:
    """Authentication endpoint (implement your authentication logic)."""
    # TODO: Implement proper authentication against your user database
    # This is a placeholder implementation

    _reject_query_credentials(request)

    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if not admin_password:
        logger.error("ADMIN_PASSWORD environment variable is required")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service configuration error",
        )

    if (
        credentials.username == admin_username
        and credentials.password == admin_password
    ):
        access_token = AuthenticationManager.create_access_token(
            data={"sub": credentials.username}
        )
        return {"access_token": access_token, "token_type": "bearer"}

    # Rate limit failed attempts more aggressively
    await asyncio.sleep(1)  # Prevent timing attacks
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
    )


@app.get("/characters")
@limiter.limit("20/minute")
async def get_characters(
    request: Request, current_user: str = Depends(get_current_user)
):
    """Get characters list (protected endpoint)."""
    try:
        characters_path = "characters"
        if not os.path.isdir(characters_path):
            raise HTTPException(
                status_code=404, detail="Characters directory not found."
            )

        characters = sorted(
            [
                d
                for d in os.listdir(characters_path)
                if os.path.isdir(os.path.join(characters_path, d))
            ]
        )
        return {"characters": characters}

    except Exception as e:
        logger.error(f"Error retrieving characters: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve characters.")


@app.get("/api/characters")
@limiter.limit("20/minute")
async def get_characters_unversioned(
    request: Request, current_user: str = Depends(get_current_user)
):
    """Unversioned REST endpoint for characters."""
    return await get_characters(request, current_user)


@app.post("/simulations")
@limiter.limit("5/minute")
async def run_simulation(
    request: Request,
    simulation_request: SimulationRequest,
    current_user: str = Depends(get_current_user),
) -> SimulationResponse:
    """Execute a character simulation (protected endpoint)."""
    start_time = time.time()
    request_id = secrets.token_hex(8)

    logger.info("Simulation requested (ID: %s).", request_id)

    try:
        config = get_config()
        turns_to_execute = simulation_request.turns or config.simulation.turns

        # Input validation has already been performed by Pydantic
        character_names = simulation_request.character_names

        # Create simulation with security context
        event_bus = EventBus()
        character_factory = CharacterFactory(event_bus)
        agents = [character_factory.create_character(name) for name in character_names]

        log_path = f"simulation_{request_id}.md"
        director = DirectorAgent(event_bus, campaign_log_path=log_path)

        for agent in agents:
            director.register_agent(agent)

        for _ in range(turns_to_execute):
            director.run_turn()

        chronicler = ChroniclerAgent(character_names=character_names)
        story = chronicler.transcribe_log(log_path)

        # Clean up temporary files
        if os.path.exists(log_path):
            os.remove(log_path)

        return SimulationResponse(
            story=story,
            participants=character_names,
            turns_executed=turns_to_execute,
            duration_seconds=time.time() - start_time,
            request_id=request_id,
        )

    except Exception as e:
        logger.error(f"Simulation failed (ID: {request_id}): {e}")
        raise HTTPException(
            status_code=500, detail=f"Simulation execution failed: {request_id}"
        )


def run_production_server(host: str = "127.0.0.1", port: int = 8000):
    """Run the production-hardened FastAPI server."""
    # Production configuration
    ssl_context = None
    if os.getenv("ENVIRONMENT") == "production":
        # SSL configuration for production
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(
            os.getenv("SSL_CERT_PATH", "/path/to/cert.pem"),
            os.getenv("SSL_KEY_PATH", "/path/to/key.pem"),
        )

    uvicorn.run(
        "production_api_server:app",
        host=host,
        port=port,
        ssl_certfile=os.getenv("SSL_CERT_PATH") if ssl_context else None,
        ssl_keyfile=os.getenv("SSL_KEY_PATH") if ssl_context else None,
        log_level="info",
        access_log=True,
        use_colors=False,
        reload=False,  # Never reload in production
    )


if __name__ == "__main__":
    run_production_server()
