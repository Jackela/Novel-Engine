#!/usr/bin/env python3
"""
ENTERPRISE SECURITY MIDDLEWARE SUITE
====================================

Comprehensive security middleware for FastAPI applications including:
- HTTP Security Headers (OWASP recommendations)
- Input Validation & Sanitization
- Request/Response Security Processing
- CSRF Protection
- Content Security Policy (CSP)
- Security Headers Enforcement

Architecture: Defense in Depth Security Layers
Security Level: Enterprise Grade with OWASP Compliance
Author: Security Engineering Team
System protects all communications 🛡️
"""

import re
import html
import json
import asyncio
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable, Pattern, Union
from urllib.parse import urlparse, parse_qs
from contextlib import asynccontextmanager

from fastapi import Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp
from pydantic import BaseModel, Field, validator
import bleach
from markupsafe import Markup

# Enhanced logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security Constants
DEFAULT_CSP_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data: https:; "
    "connect-src 'self' ws: wss:; "
    "media-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none';"
)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=()",
    "Cross-Origin-Embedder-Policy": "require-corp",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin"
}

# Input validation patterns
VALIDATION_PATTERNS = {
    "username": re.compile(r"^[a-zA-Z0-9_\-\.]{3,50}$"),
    "email": re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"),
    "safe_string": re.compile(r"^[a-zA-Z0-9\s\-_.,!?()]{1,255}$"),
    "alphanumeric": re.compile(r"^[a-zA-Z0-9]+$"),
    "uuid": re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"),
    "token": re.compile(r"^[a-zA-Z0-9_\-]{10,255}$"),
    "session_id": re.compile(r"^session_[0-9]+_[a-zA-Z0-9]+$"),
    "narrative_content": re.compile(r"^[\w\s.,!?;:\-'\"()[\]{}@#$%^&*+=<>/\\|~`]{1,10000}$", re.MULTILINE),
}

# Dangerous patterns to detect
DANGEROUS_PATTERNS = {
    "sql_injection": [
        re.compile(r"(union|select|insert|delete|update|drop|create|alter|exec|execute)\s", re.IGNORECASE),
        re.compile(r"(or|and)\s+\d+\s*=\s*\d+", re.IGNORECASE),
        re.compile(r"['\"];?\s*(drop|delete|truncate)", re.IGNORECASE),
    ],
    "xss": [
        re.compile(r"<script[\s\S]*?>[\s\S]*?</script>", re.IGNORECASE),
        re.compile(r"javascript\s*:", re.IGNORECASE),
        re.compile(r"on\w+\s*=\s*['\"]?[^'\"]*['\"]?", re.IGNORECASE),
        re.compile(r"data\s*:\s*text/html", re.IGNORECASE),
    ],
    "command_injection": [
        re.compile(r"[;&|`$()\\]", re.IGNORECASE),
        re.compile(r"(cat|ls|rm|mv|cp|chmod|chown|ps|kill|wget|curl|nc|netcat)\s", re.IGNORECASE),
    ],
    "path_traversal": [
        re.compile(r"\.\./"),
        re.compile(r"\.\.\\"),
        re.compile(r"%2e%2e%2f", re.IGNORECASE),
        re.compile(r"%2e%2e%5c", re.IGNORECASE),
    ],
    "ldap_injection": [
        re.compile(r"[()&|!*\\]"),
        re.compile(r"\x00"),
    ]
}

class SecurityConfig(BaseModel):
    """Security middleware configuration"""
    enable_csp: bool = True
    csp_policy: str = DEFAULT_CSP_POLICY
    enable_security_headers: bool = True
    custom_headers: Dict[str, str] = Field(default_factory=dict)
    enable_csrf_protection: bool = True
    csrf_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    enable_input_validation: bool = True
    enable_output_sanitization: bool = True
    max_request_size: int = 1024 * 1024  # 1MB
    rate_limit_enabled: bool = True
    allowed_hosts: List[str] = Field(default_factory=list)
    blocked_user_agents: List[str] = Field(default_factory=list)

class InputValidationError(Exception):
    """Input validation exception"""
    pass

class CSRFProtectionError(Exception):
    """CSRF protection exception"""
    pass

class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive Security Middleware Suite"""
    
    def __init__(self, app: ASGIApp, config: SecurityConfig = None):
        super().__init__(app)
        self.config = config or SecurityConfig()
        self.csrf_tokens: Dict[str, datetime] = {}
        self.request_stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "validation_errors": 0,
            "csrf_errors": 0
        }
        
        # Compile patterns for performance
        self._compile_security_patterns()
        
    def _compile_security_patterns(self):
        """Pre-compile regex patterns for better performance"""
        self.compiled_dangerous_patterns = {}
        for category, patterns in DANGEROUS_PATTERNS.items():
            self.compiled_dangerous_patterns[category] = [
                pattern if isinstance(pattern, Pattern) else re.compile(pattern, re.IGNORECASE)
                for pattern in patterns
            ]
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Main security middleware dispatch"""
        self.request_stats["total_requests"] += 1
        
        try:
            # Pre-request security checks
            await self._pre_request_security_checks(request)
            
            # Process request
            response = await call_next(request)
            
            # Post-response security processing
            response = await self._post_response_security_processing(request, response)
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            self.request_stats["blocked_requests"] += 1
            return JSONResponse(
                status_code=500,
                content={"error": "Internal security error"}
            )
    
    async def _pre_request_security_checks(self, request: Request):
        """Comprehensive pre-request security validation"""
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.config.max_request_size:
            raise HTTPException(status_code=413, detail="Request entity too large")
        
        # Host validation
        if self.config.allowed_hosts:
            host = request.headers.get("host", "")
            if host and host not in self.config.allowed_hosts:
                raise HTTPException(status_code=400, detail="Invalid host")
        
        # User agent validation
        user_agent = request.headers.get("user-agent", "")
        if any(blocked_ua in user_agent.lower() for blocked_ua in self.config.blocked_user_agents):
            raise HTTPException(status_code=403, detail="Blocked user agent")
        
        # CSRF protection for state-changing methods
        if self.config.enable_csrf_protection and request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            await self._validate_csrf_token(request)
        
        # Input validation
        if self.config.enable_input_validation:
            await self._validate_request_input(request)
    
    async def _validate_csrf_token(self, request: Request):
        """Validate CSRF token for state-changing requests"""
        csrf_token = None
        
        # Check header first
        csrf_token = request.headers.get("X-CSRF-Token")
        
        # Check form data if header not present
        if not csrf_token and request.method == "POST":
            try:
                form_data = await request.form()
                csrf_token = form_data.get("csrf_token")
            except:
                pass
        
        if not csrf_token:
            self.request_stats["csrf_errors"] += 1
            raise HTTPException(status_code=403, detail="CSRF token missing")
        
        # Validate token
        if not self._is_valid_csrf_token(csrf_token):
            self.request_stats["csrf_errors"] += 1
            raise HTTPException(status_code=403, detail="Invalid CSRF token")
        
        # Clean expired tokens
        self._cleanup_expired_csrf_tokens()
    
    def _is_valid_csrf_token(self, token: str) -> bool:
        """Validate CSRF token"""
        if token not in self.csrf_tokens:
            return False
        
        # Check if token is expired (valid for 1 hour)
        token_time = self.csrf_tokens[token]
        if datetime.now(timezone.utc) - token_time > timedelta(hours=1):
            del self.csrf_tokens[token]
            return False
        
        return True
    
    def _cleanup_expired_csrf_tokens(self):
        """Remove expired CSRF tokens"""
        current_time = datetime.now(timezone.utc)
        expired_tokens = [
            token for token, timestamp in self.csrf_tokens.items()
            if current_time - timestamp > timedelta(hours=1)
        ]
        
        for token in expired_tokens:
            del self.csrf_tokens[token]
    
    async def _validate_request_input(self, request: Request):
        """Comprehensive input validation and attack pattern detection"""
        # Validate URL path
        self._validate_input_string(str(request.url.path), "URL path")
        
        # Validate query parameters
        for param, value in request.query_params.items():
            self._validate_input_string(param, "Query parameter name")
            if isinstance(value, str):
                self._validate_input_string(value, "Query parameter value")
            elif isinstance(value, list):
                for v in value:
                    if isinstance(v, str):
                        self._validate_input_string(v, "Query parameter value")
        
        # Validate headers (selected ones)
        headers_to_validate = ["user-agent", "referer", "origin"]
        for header_name in headers_to_validate:
            header_value = request.headers.get(header_name)
            if header_value:
                self._validate_input_string(header_value, f"Header {header_name}")
        
        # Validate request body if present
        if request.method in ["POST", "PUT", "PATCH"]:
            await self._validate_request_body(request)
    
    async def _validate_request_body(self, request: Request):
        """Validate request body content"""
        content_type = request.headers.get("content-type", "").lower()
        
        if "application/json" in content_type:
            try:
                # Read and validate JSON body
                body = await request.body()
                if body:
                    json_data = json.loads(body.decode('utf-8'))
                    self._validate_json_data(json_data)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON format")
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="Invalid character encoding")
        
        elif "application/x-www-form-urlencoded" in content_type:
            try:
                form_data = await request.form()
                for field_name, field_value in form_data.items():
                    self._validate_input_string(field_name, "Form field name")
                    if isinstance(field_value, str):
                        self._validate_input_string(field_value, "Form field value")
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid form data")
    
    def _validate_json_data(self, data: Any, path: str = "root"):
        """Recursively validate JSON data"""
        if isinstance(data, dict):
            for key, value in data.items():
                self._validate_input_string(str(key), f"JSON key at {path}")
                self._validate_json_data(value, f"{path}.{key}")
        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self._validate_json_data(item, f"{path}[{i}]")
        
        elif isinstance(data, str):
            self._validate_input_string(data, f"JSON string at {path}")
    
    def _validate_input_string(self, input_str: str, context: str = "input"):
        """Validate individual input string for malicious patterns"""
        if not isinstance(input_str, str):
            return
        
        # Check for dangerous patterns
        for category, patterns in self.compiled_dangerous_patterns.items():
            for pattern in patterns:
                if pattern.search(input_str):
                    self.request_stats["validation_errors"] += 1
                    logger.warning(f"🚨 {category.upper()} DETECTED in {context}: {input_str[:100]}")
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Invalid input detected: {category}"
                    )
        
        # Check for null bytes
        if '\x00' in input_str:
            raise HTTPException(status_code=400, detail="Null byte detected")
        
        # Check for excessive length
        if len(input_str) > 10000:  # Configurable limit
            raise HTTPException(status_code=400, detail="Input too long")
    
    async def _post_response_security_processing(self, request: Request, response: Response) -> Response:
        """Apply security headers and output sanitization"""
        
        # Add security headers
        if self.config.enable_security_headers:
            for header, value in SECURITY_HEADERS.items():
                response.headers[header] = value
            
            # Add custom headers
            for header, value in self.config.custom_headers.items():
                response.headers[header] = value
        
        # Add CSP header
        if self.config.enable_csp:
            response.headers["Content-Security-Policy"] = self.config.csp_policy
        
        # Add CSRF token for GET requests to HTML pages
        if (request.method == "GET" and 
            response.headers.get("content-type", "").startswith("text/html")):
            csrf_token = self._generate_csrf_token()
            response.headers["X-CSRF-Token"] = csrf_token
        
        # Output sanitization for JSON responses
        if (self.config.enable_output_sanitization and 
            response.headers.get("content-type", "").startswith("application/json")):
            response = await self._sanitize_json_response(response)
        
        # Security logging
        self._log_request_response(request, response)
        
        return response
    
    def _generate_csrf_token(self) -> str:
        """Generate a new CSRF token"""
        token = secrets.token_urlsafe(32)
        self.csrf_tokens[token] = datetime.now(timezone.utc)
        return token
    
    async def _sanitize_json_response(self, response: Response) -> Response:
        """Sanitize JSON response content"""
        try:
            # Get response content
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            
            # Parse and sanitize JSON
            if response_body:
                json_data = json.loads(response_body.decode('utf-8'))
                sanitized_data = self._sanitize_json_data(json_data)
                
                # Create new response with sanitized content
                response_body = json.dumps(sanitized_data, ensure_ascii=True).encode('utf-8')
                response.headers["content-length"] = str(len(response_body))
            
            # Create new response
            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=response.headers,
                media_type=response.media_type
            )
            
        except Exception as e:
            logger.error(f"Error sanitizing JSON response: {e}")
            return response
    
    def _sanitize_json_data(self, data: Any) -> Any:
        """Recursively sanitize JSON data"""
        if isinstance(data, dict):
            return {
                self._sanitize_string(str(key)): self._sanitize_json_data(value)
                for key, value in data.items()
            }
        
        elif isinstance(data, list):
            return [self._sanitize_json_data(item) for item in data]
        
        elif isinstance(data, str):
            return self._sanitize_string(data)
        
        else:
            return data
    
    def _sanitize_string(self, input_str: str) -> str:
        """Sanitize string content"""
        if not isinstance(input_str, str):
            return input_str
        
        # HTML escape
        sanitized = html.escape(input_str, quote=True)
        
        # Additional cleaning using bleach for HTML content
        if any(char in sanitized for char in ['<', '>', '&']):
            sanitized = bleach.clean(
                sanitized,
                tags=[],  # No HTML tags allowed
                attributes={},
                strip=True
            )
        
        return sanitized
    
    def _log_request_response(self, request: Request, response: Response):
        """Log security-relevant request/response information"""
        if response.status_code >= 400:
            logger.warning(
                f"🔍 Security Event: {request.method} {request.url.path} "
                f"-> {response.status_code} from {request.client.host if request.client else 'unknown'}"
            )
    
    def get_csrf_token(self) -> str:
        """Public method to get CSRF token for forms"""
        return self._generate_csrf_token()
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get security middleware metrics"""
        return {
            "total_requests": self.request_stats["total_requests"],
            "blocked_requests": self.request_stats["blocked_requests"],
            "validation_errors": self.request_stats["validation_errors"],
            "csrf_errors": self.request_stats["csrf_errors"],
            "active_csrf_tokens": len(self.csrf_tokens),
            "block_rate": (
                self.request_stats["blocked_requests"] / max(self.request_stats["total_requests"], 1)
            ) * 100
        }

class InputValidator:
    """Standalone input validation utility"""
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username format"""
        return bool(VALIDATION_PATTERNS["username"].match(username)) if username else False
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        return bool(VALIDATION_PATTERNS["email"].match(email)) if email else False
    
    @staticmethod
    def validate_session_id(session_id: str) -> bool:
        """Validate session ID format"""
        return bool(VALIDATION_PATTERNS["session_id"].match(session_id)) if session_id else False
    
    @staticmethod
    def validate_narrative_content(content: str) -> bool:
        """Validate narrative content"""
        if not content:
            return False
        
        # Check pattern
        if not VALIDATION_PATTERNS["narrative_content"].match(content):
            return False
        
        # Check for dangerous patterns
        for category, patterns in DANGEROUS_PATTERNS.items():
            for pattern in patterns:
                if isinstance(pattern, str):
                    pattern = re.compile(pattern, re.IGNORECASE)
                if pattern.search(content):
                    return False
        
        return True
    
    @staticmethod
    def sanitize_input(input_str: str) -> str:
        """Sanitize input string"""
        if not isinstance(input_str, str):
            return ""
        
        # HTML escape
        sanitized = html.escape(input_str, quote=True)
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        # Limit length
        if len(sanitized) > 10000:
            sanitized = sanitized[:10000]
        
        return sanitized

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Lightweight security headers middleware"""
    
    def __init__(self, app: ASGIApp, custom_headers: Dict[str, str] = None):
        super().__init__(app)
        self.custom_headers = custom_headers or {}
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        
        # Apply security headers
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        
        # Apply custom headers
        for header, value in self.custom_headers.items():
            response.headers[header] = value
        
        # Add CSP
        response.headers["Content-Security-Policy"] = DEFAULT_CSP_POLICY
        
        return response

# Utility functions for direct use
def create_security_middleware(
    enable_full_security: bool = True,
    custom_config: SecurityConfig = None
) -> Union[SecurityMiddleware, SecurityHeadersMiddleware]:
    """Factory function to create appropriate security middleware"""
    if enable_full_security:
        return lambda app: SecurityMiddleware(app, custom_config)
    else:
        return lambda app: SecurityHeadersMiddleware(app)

def validate_request_data(data: Dict[str, Any], validation_rules: Dict[str, str] = None) -> Dict[str, Any]:
    """Validate and sanitize request data"""
    if not isinstance(data, dict):
        raise InputValidationError("Input must be a dictionary")
    
    sanitized_data = {}
    validator = InputValidator()
    
    for key, value in data.items():
        # Sanitize key
        clean_key = validator.sanitize_input(str(key))
        
        # Validate and sanitize value
        if isinstance(value, str):
            clean_value = validator.sanitize_input(value)
            
            # Apply specific validation rules if provided
            if validation_rules and key in validation_rules:
                rule = validation_rules[key]
                if rule == "username" and not validator.validate_username(clean_value):
                    raise InputValidationError(f"Invalid username: {key}")
                elif rule == "email" and not validator.validate_email(clean_value):
                    raise InputValidationError(f"Invalid email: {key}")
                elif rule == "narrative" and not validator.validate_narrative_content(clean_value):
                    raise InputValidationError(f"Invalid narrative content: {key}")
            
            sanitized_data[clean_key] = clean_value
        
        elif isinstance(value, (int, float, bool)):
            sanitized_data[clean_key] = value
        
        elif isinstance(value, (list, dict)):
            sanitized_data[clean_key] = validate_request_data(value, validation_rules) if isinstance(value, dict) else value
        
        else:
            sanitized_data[clean_key] = str(value)
    
    return sanitized_data

__all__ = [
    'SecurityMiddleware', 'SecurityHeadersMiddleware', 'SecurityConfig',
    'InputValidator', 'InputValidationError', 'CSRFProtectionError',
    'create_security_middleware', 'validate_request_data',
    'SECURITY_HEADERS', 'DEFAULT_CSP_POLICY', 'VALIDATION_PATTERNS'
]