#!/usr/bin/env python3
"""
ENTERPRISE SECURITY MODULE - ZERO TRUST ARCHITECTURE
====================================================

Complete enterprise-grade security framework providing:
- JWT Authentication & Role-Based Access Control (RBAC)
- Real-time Threat Detection & Response
- Behavioral Analytics & Anomaly Detection
- Advanced Rate Limiting & DDoS Protection
- Input Validation & Attack Prevention
- Security Monitoring & Compliance Dashboard
- HTTP Security Headers & OWASP Protection
- Zero Trust Architecture Implementation
- GDPR/SOC2/HIPAA Compliance Support

THROUGH ADVANCED PROTECTION, WE ACHIEVE ENHANCED SECURITY 🛡️

Architecture: Zero Trust + Defense in Depth + AI-Powered Detection
Security Level: Enterprise Grade with Military Standards
Author: Enterprise Security Team
System protects all operations from advanced threats
"""

# Core Authentication & Authorization
from .auth_system import (
    ROLE_PERMISSIONS,
    AuthenticationError,
    AuthorizationError,
    Permission,
    SecurityEvent,
    SecurityService,
    TokenPair,
    User,
    UserLogin,
    UserRegistration,
    UserRole,
    get_security_service,
    initialize_security_service,
)

# Enterprise Security Management
from .enterprise_security_manager import (
    BehavioralProfile,
    ComplianceFramework,
    EnterpriseSecurityManager,
    SecurityAction,
    SecurityMetrics,
    ThreatIntelligence,
    ThreatLevel,
    get_enterprise_security_manager,
    initialize_enterprise_security_manager,
)

# Security Monitoring & Dashboard
from .security_dashboard import (
    AlertSeverity,
    ComplianceReport,
    IncidentStatus,
    SecurityAlert,
    SecurityDashboard,
    SecurityIncident,
)
from .security_dashboard import SecurityMetrics as DashboardMetrics
from .security_dashboard import (
    get_security_dashboard,
    initialize_security_dashboard,
)

# Complete Security Integration
from .security_integration import (
    EnterpriseSecuritySuite,
    create_secure_app,
    get_security_suite,
    initialize_security_suite,
)

# Security Middleware & Input Protection
from .security_middleware import (
    DEFAULT_CSP_POLICY,
    SECURITY_HEADERS,
    VALIDATION_PATTERNS,
    CSRFProtectionError,
    InputValidationError,
    InputValidator,
    SecurityConfig,
    SecurityHeadersMiddleware,
    SecurityMiddleware,
    create_security_middleware,
    validate_request_data,
)

__all__ = [
    # Core Authentication & Authorization
    "UserRole",
    "Permission",
    "User",
    "TokenPair",
    "UserRegistration",
    "UserLogin",
    "SecurityEvent",
    "AuthenticationError",
    "AuthorizationError",
    "SecurityService",
    "get_security_service",
    "initialize_security_service",
    "ROLE_PERMISSIONS",
    # Enterprise Security Management
    "EnterpriseSecurityManager",
    "ThreatLevel",
    "SecurityAction",
    "ComplianceFramework",
    "ThreatIntelligence",
    "BehavioralProfile",
    "SecurityMetrics",
    "get_enterprise_security_manager",
    "initialize_enterprise_security_manager",
    # Security Middleware & Protection
    "SecurityMiddleware",
    "SecurityHeadersMiddleware",
    "SecurityConfig",
    "InputValidator",
    "InputValidationError",
    "CSRFProtectionError",
    "create_security_middleware",
    "validate_request_data",
    "SECURITY_HEADERS",
    "DEFAULT_CSP_POLICY",
    "VALIDATION_PATTERNS",
    # Security Monitoring & Dashboard
    "SecurityDashboard",
    "SecurityAlert",
    "SecurityIncident",
    "ComplianceReport",
    "AlertSeverity",
    "IncidentStatus",
    "DashboardMetrics",
    "get_security_dashboard",
    "initialize_security_dashboard",
    # Complete Integration Suite
    "EnterpriseSecuritySuite",
    "get_security_suite",
    "initialize_security_suite",
    "create_secure_app",
]
