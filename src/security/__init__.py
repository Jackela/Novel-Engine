"""Security package exports for FastAPI apps."""

# Core auth system
from .auth_system import (
    Permission,
    SecurityService,
    TokenPair,
    User,
    UserLogin,
    UserRegistration,
    UserRole,
    get_security_service,
    initialize_security_service,
)

# Rate limiting
from .rate_limiting import RateLimitConfig, create_rate_limit_middleware, get_rate_limiter

# Security headers middleware
from .security_headers import (
    create_security_headers_middleware,
    get_development_security_config,
    get_production_security_config,
)

# Input validation middleware
from .input_validation import create_validation_middleware

__all__ = [
    # Auth
    "Permission",
    "RateLimitConfig",
    "SecurityService",
    "TokenPair",
    "User",
    "UserLogin",
    "UserRegistration",
    "UserRole",
    "get_security_service",
    "initialize_security_service",
    # Rate limiting
    "create_rate_limit_middleware",
    "get_rate_limiter",
    # Headers
    "create_security_headers_middleware",
    "get_development_security_config",
    "get_production_security_config",
    # Validation
    "create_validation_middleware",
]
