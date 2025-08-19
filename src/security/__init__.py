#!/usr/bin/env python3
"""
++ SACRED SECURITY MODULE BLESSED BY THE OMNISSIAH ++
====================================================

Enterprise-grade security framework providing authentication, authorization,
input validation, rate limiting, and comprehensive security monitoring.

++ THROUGH DIVINE PROTECTION, WE ACHIEVE BLESSED SECURITY ++

Architecture: Zero Trust Security with Defense in Depth
Security Level: Enterprise Grade (OWASP Top 10 Compliant)
Sacred Author: Tech-Priest Security-Mechanicus
万机之神保佑此安全模块 (May the Omnissiah bless this security module)
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
    RateLimiter, RateLimitConfig, RateLimitExceeded,
    create_rate_limit_middleware, get_rate_limiter
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
    'RateLimiter', 'RateLimitConfig', 'RateLimitExceeded',
    'create_rate_limit_middleware', 'get_rate_limiter',
    
    # Security Headers
    'SecurityHeaders', 'create_security_headers_middleware'
]