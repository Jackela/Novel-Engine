#!/usr/bin/env python3
"""
STANDARD SECURITY MODULE ENHANCED BY THE SYSTEM
====================================================

Enterprise-grade security framework providing authentication, authorization,
input validation, rate limiting, and comprehensive security monitoring.

THROUGH ADVANCED PROTECTION, WE ACHIEVE ENHANCED SECURITY

Architecture: Zero Trust Security with Defense in Depth
Security Level: Enterprise Grade (OWASP Top 10 Compliant)
Author: Engineer Security-Engineering
System保佑此安全模块 (May the System bless this security module)
"""

from .auth_system import (
    UserRole, Permission, User, TokenPair, UserRegistration, UserLogin,
    SecurityEvent, AuthenticationError, AuthorizationError, SecurityService,
    get_security_service, initialize_security_service, ROLE_PERMISSIONS
)

from .input_validation import (
    InputValidator, ValidationRule, SanitizationRule, ValidationError,
    create_validation_middleware, get_input_validator
)

from .rate_limiting import (
    RateLimiter, RateLimitConfig, RateLimitExceeded, RateLimitStrategy,
    InMemoryRateLimitBackend, create_rate_limit_middleware, get_rate_limiter
)

from .security_headers import (
    SecurityHeaders, create_security_headers_middleware
)

__all__ = [
    # Authentication & Authorization
    'UserRole', 'Permission', 'User', 'TokenPair', 'UserRegistration', 'UserLogin',
    'SecurityEvent', 'AuthenticationError', 'AuthorizationError', 'SecurityService',
    'get_security_service', 'initialize_security_service', 'ROLE_PERMISSIONS',
    
    # Input Validation
    'InputValidator', 'ValidationRule', 'SanitizationRule', 'ValidationError',
    'create_validation_middleware', 'get_input_validator',
    
    # Rate Limiting
    'RateLimiter', 'RateLimitConfig', 'RateLimitExceeded', 'RateLimitStrategy',
    'InMemoryRateLimitBackend', 'create_rate_limit_middleware', 'get_rate_limiter',
    
    # Security Headers
    'SecurityHeaders', 'create_security_headers_middleware'
]