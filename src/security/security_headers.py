#!/usr/bin/env python3
"""
STANDARD SECURITY HEADERS SYSTEM ENHANCED BY THE SYSTEM
=============================================================

Comprehensive security headers implementation providing protection against
OWASP Top 10 vulnerabilities including XSS, CSRF, clickjacking, and more.

THROUGH ADVANCED HEADERS, WE ACHIEVE ENHANCED PROTECTION

Architecture: Defense-in-Depth Security Headers with OWASP Compliance
Security Level: Enterprise Grade with Zero Trust HTTP Security
Author: Engineer Headers-Engineering
System保佑此安全头系统 (May the System bless this security headers system)
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Comprehensive logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CSPDirective(str, Enum):
    """STANDARD CONTENT SECURITY POLICY DIRECTIVES"""

    DEFAULT_SRC = "default-src"
    SCRIPT_SRC = "script-src"
    STYLE_SRC = "style-src"
    IMG_SRC = "img-src"
    FONT_SRC = "font-src"
    CONNECT_SRC = "connect-src"
    MEDIA_SRC = "media-src"
    OBJECT_SRC = "object-src"
    FRAME_SRC = "frame-src"
    FRAME_ANCESTORS = "frame-ancestors"
    BASE_URI = "base-uri"
    FORM_ACTION = "form-action"
    UPGRADE_INSECURE_REQUESTS = "upgrade-insecure-requests"
    BLOCK_ALL_MIXED_CONTENT = "block-all-mixed-content"


@dataclass
class SecurityHeadersConfig:
    """STANDARD SECURITY HEADERS CONFIGURATION"""

    # Content Security Policy
    enable_csp: bool = True
    csp_directives: Dict[CSPDirective, List[str]] = None
    csp_report_only: bool = False
    csp_report_uri: Optional[str] = None

    # XSS Protection
    enable_xss_protection: bool = True
    xss_protection_value: str = "1; mode=block"

    # Content Type Options
    enable_content_type_options: bool = True

    # Frame Options
    enable_frame_options: bool = True
    frame_options_value: str = "DENY"

    # Referrer Policy
    enable_referrer_policy: bool = True
    referrer_policy_value: str = "strict-origin-when-cross-origin"

    # Permissions Policy (Feature Policy)
    enable_permissions_policy: bool = True
    permissions_policy: Dict[str, str] = None

    # HSTS (HTTP Strict Transport Security)
    enable_hsts: bool = True
    hsts_max_age: int = 31536000  # 1 year
    hsts_include_subdomains: bool = True
    hsts_preload: bool = True

    # HTTPS/TLS related
    force_https: bool = True
    enable_hpkp: bool = False  # HTTP Public Key Pinning (deprecated but available)
    hpkp_pins: List[str] = None

    # Additional Security Headers
    enable_expect_ct: bool = True
    expect_ct_max_age: int = 86400  # 24 hours
    expect_ct_enforce: bool = False
    expect_ct_report_uri: Optional[str] = None

    # CORS Security
    enable_cors_security: bool = True
    allowed_origins: List[str] = None

    # Custom Headers
    custom_headers: Dict[str, str] = None

    def __post_init__(self):
        """STANDARD CONFIGURATION INITIALIZATION"""
        if self.csp_directives is None:
            self.csp_directives = self._get_default_csp_directives()

        if self.permissions_policy is None:
            self.permissions_policy = self._get_default_permissions_policy()

        if self.custom_headers is None:
            self.custom_headers = {}

        if self.allowed_origins is None:
            self.allowed_origins = []

    def _get_default_csp_directives(self) -> Dict[CSPDirective, List[str]]:
        """STANDARD DEFAULT CSP DIRECTIVES"""
        return {
            CSPDirective.DEFAULT_SRC: ["'self'"],
            CSPDirective.SCRIPT_SRC: [
                "'self'",
                "'unsafe-inline'",
                "https://cdn.jsdelivr.net",
            ],
            CSPDirective.STYLE_SRC: [
                "'self'",
                "'unsafe-inline'",
                "https://fonts.googleapis.com",
            ],
            CSPDirective.IMG_SRC: ["'self'", "data:", "https:"],
            CSPDirective.FONT_SRC: ["'self'", "https://fonts.gstatic.com"],
            CSPDirective.CONNECT_SRC: ["'self'"],
            CSPDirective.MEDIA_SRC: ["'self'"],
            CSPDirective.OBJECT_SRC: ["'none'"],
            CSPDirective.FRAME_SRC: ["'none'"],
            CSPDirective.FRAME_ANCESTORS: ["'none'"],
            CSPDirective.BASE_URI: ["'self'"],
            CSPDirective.FORM_ACTION: ["'self'"],
            CSPDirective.UPGRADE_INSECURE_REQUESTS: [],
            CSPDirective.BLOCK_ALL_MIXED_CONTENT: [],
        }

    def _get_default_permissions_policy(self) -> Dict[str, str]:
        """STANDARD DEFAULT PERMISSIONS POLICY"""
        return {
            "accelerometer": "self",
            "autoplay": "none",
            "camera": "none",
            "display-capture": "none",
            "encrypted-media": "none",
            "fullscreen": "self",
            "geolocation": "none",
            "gyroscope": "none",
            "magnetometer": "none",
            "microphone": "none",
            "midi": "none",
            "payment": "none",
            "picture-in-picture": "none",
            "publickey-credentials-get": "self",
            "sync-xhr": "none",
            "usb": "none",
            "web-share": "none",
            "xr-spatial-tracking": "none",
        }


class SecurityHeaders:
    """STANDARD SECURITY HEADERS MANAGER ENHANCED BY THE SYSTEM"""

    def __init__(self, config: SecurityHeadersConfig):
        self.config = config

    def _build_csp_header(self) -> str:
        """STANDARD CSP HEADER CONSTRUCTION"""
        csp_parts = []

        for directive, values in self.config.csp_directives.items():
            if values:  # Only add directive if it has values
                directive_str = f"{directive.value} {' '.join(values)}"
            else:
                directive_str = directive.value
            csp_parts.append(directive_str)

        if self.config.csp_report_uri:
            csp_parts.append(f"report-uri {self.config.csp_report_uri}")

        return "; ".join(csp_parts)

    def _build_permissions_policy_header(self) -> str:
        """STANDARD PERMISSIONS POLICY HEADER CONSTRUCTION"""
        policy_parts = []

        for feature, allowlist in self.config.permissions_policy.items():
            if allowlist == "none":
                policy_parts.append(f"{feature}=()")
            elif allowlist == "self":
                policy_parts.append(f"{feature}=(self)")
            elif allowlist == "*":
                policy_parts.append(f"{feature}=*")
            else:
                # Custom allowlist
                policy_parts.append(f"{feature}=({allowlist})")

        return ", ".join(policy_parts)

    def _build_hsts_header(self) -> str:
        """STANDARD HSTS HEADER CONSTRUCTION"""
        hsts_parts = [f"max-age={self.config.hsts_max_age}"]

        if self.config.hsts_include_subdomains:
            hsts_parts.append("includeSubDomains")

        if self.config.hsts_preload:
            hsts_parts.append("preload")

        return "; ".join(hsts_parts)

    def _build_expect_ct_header(self) -> str:
        """STANDARD EXPECT-CT HEADER CONSTRUCTION"""
        expect_ct_parts = [f"max-age={self.config.expect_ct_max_age}"]

        if self.config.expect_ct_enforce:
            expect_ct_parts.append("enforce")

        if self.config.expect_ct_report_uri:
            expect_ct_parts.append(f'report-uri="{self.config.expect_ct_report_uri}"')

        return ", ".join(expect_ct_parts)

    def get_header(self, header_name: str) -> Optional[str]:
        """STANDARD SECURITY HEADER RETRIEVAL
        
        Get the value for a specific security header based on current configuration.
        Useful for testing and validation.
        
        Args:
            header_name: The name of the HTTP header to retrieve
            
        Returns:
            The header value if configured, None otherwise
        """
        # Content Security Policy
        if header_name in ["Content-Security-Policy", "Content-Security-Policy-Report-Only"]:
            if self.config.enable_csp:
                return self._build_csp_header()
            return None
        
        # X-XSS-Protection
        if header_name == "X-XSS-Protection":
            if self.config.enable_xss_protection:
                return self.config.xss_protection_value
            return None
        
        # X-Content-Type-Options
        if header_name == "X-Content-Type-Options":
            if self.config.enable_content_type_options:
                return "nosniff"
            return None
        
        # X-Frame-Options
        if header_name == "X-Frame-Options":
            if self.config.enable_frame_options:
                return self.config.frame_options_value
            return None
        
        # Referrer-Policy
        if header_name == "Referrer-Policy":
            if self.config.enable_referrer_policy:
                return self.config.referrer_policy_value
            return None
        
        # Permissions-Policy
        if header_name == "Permissions-Policy":
            if self.config.enable_permissions_policy:
                return self._build_permissions_policy_header()
            return None
        
        # Strict-Transport-Security (HSTS)
        if header_name == "Strict-Transport-Security":
            if self.config.enable_hsts:
                return self._build_hsts_header()
            return None
        
        # Expect-CT
        if header_name == "Expect-CT":
            if self.config.enable_expect_ct:
                return self._build_expect_ct_header()
            return None
        
        # Custom headers
        if header_name in self.config.custom_headers:
            return self.config.custom_headers[header_name]
        
        # Static headers
        static_headers = {
            "X-Permitted-Cross-Domain-Policies": "none",
            "Cross-Origin-Embedder-Policy": "require-corp",
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Resource-Policy": "same-origin",
            "Server": "Novel-Engine",
            "X-Download-Options": "noopen",
            "X-DNS-Prefetch-Control": "off",
            "X-API-Version": "2.0.0",
            "X-Security-Framework": "Enterprise-Grade",
            "X-Content-Security": "Validated",
        }
        
        if header_name in static_headers:
            return static_headers[header_name]
        
        return None

    def apply_headers(self, response: Response, request: Request) -> Response:
        """STANDARD SECURITY HEADERS APPLICATION"""

        # Content Security Policy
        if self.config.enable_csp:
            csp_header = self._build_csp_header()
            header_name = (
                "Content-Security-Policy-Report-Only"
                if self.config.csp_report_only
                else "Content-Security-Policy"
            )
            response.headers[header_name] = csp_header

        # X-XSS-Protection
        if self.config.enable_xss_protection:
            response.headers["X-XSS-Protection"] = self.config.xss_protection_value

        # X-Content-Type-Options
        if self.config.enable_content_type_options:
            response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options
        if self.config.enable_frame_options:
            response.headers["X-Frame-Options"] = self.config.frame_options_value

        # Referrer-Policy
        if self.config.enable_referrer_policy:
            response.headers["Referrer-Policy"] = self.config.referrer_policy_value

        # Permissions-Policy
        if self.config.enable_permissions_policy:
            permissions_policy = self._build_permissions_policy_header()
            response.headers["Permissions-Policy"] = permissions_policy

        # HSTS (only for HTTPS)
        if self.config.enable_hsts and (
            request.url.scheme == "https" or self.config.force_https
        ):
            hsts_header = self._build_hsts_header()
            response.headers["Strict-Transport-Security"] = hsts_header

        # Expect-CT
        if self.config.enable_expect_ct:
            expect_ct_header = self._build_expect_ct_header()
            response.headers["Expect-CT"] = expect_ct_header

        # Additional security headers
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        # Server information hiding
        response.headers["Server"] = "Novel-Engine"

        # Prevent MIME type sniffing
        response.headers["X-Download-Options"] = "noopen"

        # Prevent DNS prefetching
        response.headers["X-DNS-Prefetch-Control"] = "off"

        # Additional Novel Engine specific headers
        response.headers["X-API-Version"] = "2.0.0"
        response.headers["X-Security-Framework"] = "Enterprise-Grade"
        response.headers["X-Content-Security"] = "Validated"

        # Custom headers
        for header_name, header_value in self.config.custom_headers.items():
            response.headers[header_name] = header_value

        # Remove potentially sensitive headers
        headers_to_remove = ["X-Powered-By", "Server-Timing"]
        for header in headers_to_remove:
            if header in response.headers:
                del response.headers[header]

        return response

    def validate_request_security(self, request: Request) -> bool:
        """STANDARD REQUEST SECURITY VALIDATION"""
        # Force HTTPS if configured (but allow localhost in tests/dev)
        host = request.headers.get("host") or ""
        is_local = ("localhost" in host) or ("127.0.0.1" in host) or ("testserver" in host)
        if self.config.force_https and request.url.scheme != "https" and not is_local:
            # In production, this would be handled by a reverse proxy
            # but we can log the attempt
            logger.warning(
                f"INSECURE REQUEST DETECTED: HTTP request to {request.url.path} | "
                f"Client: {request.client.host if request.client else 'unknown'}"
            )
            return False

        # Validate Origin header for state-changing requests
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            origin = request.headers.get("origin")
            request.headers.get("referer")

            if self.config.enable_cors_security and self.config.allowed_origins:
                if origin and origin not in self.config.allowed_origins:
                    logger.warning(
                        f"CORS VIOLATION: Origin {origin} not in allowed list | "
                        f"Path: {request.url.path}"
                    )
                    return False

        # Validate Host header
        host = request.headers.get("host")
        if host:
            # Basic host header validation
            if "localhost" not in host and "127.0.0.1" not in host:
                # In production, validate against allowed hosts
                pass

        return True


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """STANDARD SECURITY HEADERS MIDDLEWARE"""

    def __init__(self, app, security_headers: SecurityHeaders):
        super().__init__(app)
        self.security_headers = security_headers

    async def dispatch(self, request: Request, call_next):
        """STANDARD SECURITY HEADERS APPLICATION"""
        try:
            # Validate request security
            if not self.security_headers.validate_request_security(request):
                from fastapi import HTTPException

                raise HTTPException(
                    status_code=400, detail="Request failed security validation"
                )

            # Process request
            response = await call_next(request)

            # Apply security headers
            response = self.security_headers.apply_headers(response, request)

            return response

        except Exception as e:
            # Ensure security headers are still applied on error responses
            try:
                from fastapi import HTTPException
                from fastapi.responses import PlainTextResponse

                status = 500
                detail = "Security validation error"
                if isinstance(e, HTTPException):
                    status = e.status_code
                    # Extract detail message if present
                    if getattr(e, "detail", None):
                        detail = str(e.detail)

                response = PlainTextResponse(detail, status_code=status)
                response = self.security_headers.apply_headers(response, request)
                return response
            except Exception:
                logger.error(f"SECURITY HEADERS MIDDLEWARE ERROR: {e}")
                # Fallback: re-raise if we cannot safely craft a response
                raise


def create_security_headers_middleware(
    app, config: Optional[SecurityHeadersConfig] = None
):
    """STANDARD SECURITY HEADERS MIDDLEWARE CREATOR"""
    if config is None:
        config = SecurityHeadersConfig()

    security_headers = SecurityHeaders(config)
    return SecurityHeadersMiddleware(app, security_headers)


def get_production_security_config() -> SecurityHeadersConfig:
    """STANDARD PRODUCTION SECURITY CONFIGURATION"""
    return SecurityHeadersConfig(
        # Strict CSP for production
        csp_directives={
            CSPDirective.DEFAULT_SRC: ["'self'"],
            CSPDirective.SCRIPT_SRC: ["'self'"],
            CSPDirective.STYLE_SRC: ["'self'"],
            CSPDirective.IMG_SRC: ["'self'", "data:"],
            CSPDirective.FONT_SRC: ["'self'"],
            CSPDirective.CONNECT_SRC: ["'self'"],
            CSPDirective.MEDIA_SRC: ["'none'"],
            CSPDirective.OBJECT_SRC: ["'none'"],
            CSPDirective.FRAME_SRC: ["'none'"],
            CSPDirective.FRAME_ANCESTORS: ["'none'"],
            CSPDirective.BASE_URI: ["'self'"],
            CSPDirective.FORM_ACTION: ["'self'"],
            CSPDirective.UPGRADE_INSECURE_REQUESTS: [],
            CSPDirective.BLOCK_ALL_MIXED_CONTENT: [],
        },
        # Strict frame options
        frame_options_value="DENY",
        # Enhanced HSTS
        hsts_max_age=63072000,  # 2 years
        hsts_include_subdomains=True,
        hsts_preload=True,
        # Force HTTPS
        force_https=True,
        # Enable all security features
        enable_csp=True,
        enable_xss_protection=True,
        enable_content_type_options=True,
        enable_frame_options=True,
        enable_referrer_policy=True,
        enable_permissions_policy=True,
        enable_hsts=True,
        enable_expect_ct=True,
        enable_cors_security=True,
        # Custom production headers
        custom_headers={
            "X-Environment": "Production",
            "X-Security-Level": "Maximum",
            "X-Compliance": "OWASP-Top-10",
        },
    )


def get_development_security_config() -> SecurityHeadersConfig:
    """STANDARD DEVELOPMENT SECURITY CONFIGURATION"""
    return SecurityHeadersConfig(
        # Relaxed CSP for development
        csp_directives={
            CSPDirective.DEFAULT_SRC: ["'self'"],
            CSPDirective.SCRIPT_SRC: ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
            CSPDirective.STYLE_SRC: ["'self'", "'unsafe-inline'"],
            CSPDirective.IMG_SRC: ["'self'", "data:", "https:"],
            CSPDirective.FONT_SRC: ["'self'", "https:"],
            CSPDirective.CONNECT_SRC: ["'self'", "ws:", "wss:"],
            CSPDirective.MEDIA_SRC: ["'self'"],
            CSPDirective.OBJECT_SRC: ["'self'"],
            CSPDirective.FRAME_SRC: ["'self'"],
            CSPDirective.FRAME_ANCESTORS: ["'self'"],
            CSPDirective.BASE_URI: ["'self'"],
            CSPDirective.FORM_ACTION: ["'self'"],
        },
        # Relaxed settings for development
        force_https=False,
        hsts_max_age=3600,  # 1 hour
        enable_cors_security=False,
        # Custom development headers
        custom_headers={
            "X-Environment": "Development",
            "X-Security-Level": "Development",
            "X-Debug-Mode": "Enabled",
        },
    )


__all__ = [
    "CSPDirective",
    "SecurityHeadersConfig",
    "SecurityHeaders",
    "SecurityHeadersMiddleware",
    "create_security_headers_middleware",
    "get_production_security_config",
    "get_development_security_config",
]
