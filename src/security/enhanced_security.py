#!/usr/bin/env python3
"""
ENHANCED SECURITY MIDDLEWARE INTEGRATION
============================================

Enhanced security middleware for comprehensive protection.
Provides additional security layers beyond basic headers.
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


@dataclass
class SecurityEvent:
    """Security event for monitoring"""

    event_type: str
    source_ip: str
    user_agent: str
    endpoint: str
    timestamp: float
    severity: str
    details: Dict[str, Any]


class EnhancedSecurityMiddleware(BaseHTTPMiddleware):
    """Enhanced security middleware with threat detection"""

    def __init__(self, app, config: Optional[Dict] = None):
        super().__init__(app)
        self.config = config or {}
        self.security_events = []
        self.rate_limits = {}

    async def dispatch(self, request: Request, call_next):
        """Process request with enhanced security checks"""
        start_time = time.time()

        # Extract request info
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        endpoint = str(request.url.path)

        # Security checks
        security_result = await self._perform_security_checks(
            request, client_ip, user_agent, endpoint
        )

        if not security_result["allowed"]:
            return Response(
                content=json.dumps(
                    {"error": "Request blocked by security policy"}
                ),
                status_code=403,
                headers={"Content-Type": "application/json"},
            )

        # Process request
        response = await call_next(request)

        # Add security headers
        self._add_security_headers(response)

        # Log security event if needed
        processing_time = time.time() - start_time
        if processing_time > 1.0:  # Slow request - potential attack
            await self._log_security_event(
                "slow_request",
                client_ip,
                user_agent,
                endpoint,
                "medium",
                {"processing_time": processing_time},
            )

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP with proxy support"""
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fallback to direct connection
        if hasattr(request.client, "host"):
            return request.client.host

        return "unknown"

    async def _perform_security_checks(
        self, request: Request, client_ip: str, user_agent: str, endpoint: str
    ) -> Dict[str, Any]:
        """Perform comprehensive security checks"""
        checks = []

        # Rate limiting check
        rate_check = self._check_rate_limit(client_ip, endpoint)
        checks.append(rate_check)

        # Suspicious user agent check
        ua_check = self._check_user_agent(user_agent)
        checks.append(ua_check)

        # Request size check
        size_check = await self._check_request_size(request)
        checks.append(size_check)

        # SQL injection pattern check
        sql_check = await self._check_sql_injection(request)
        checks.append(sql_check)

        # All checks must pass
        allowed = all(check["allowed"] for check in checks)

        return {
            "allowed": allowed,
            "checks": checks,
            "risk_score": sum(check.get("risk_score", 0) for check in checks),
        }

    def _check_rate_limit(
        self, client_ip: str, endpoint: str
    ) -> Dict[str, Any]:
        """Simple rate limiting check"""
        current_time = time.time()
        window = 60  # 1 minute window
        limit = 100  # 100 requests per minute

        key = f"{client_ip}:{endpoint}"

        if key not in self.rate_limits:
            self.rate_limits[key] = []

        # Clean old entries
        self.rate_limits[key] = [
            timestamp
            for timestamp in self.rate_limits[key]
            if current_time - timestamp < window
        ]

        # Add current request
        self.rate_limits[key].append(current_time)

        request_count = len(self.rate_limits[key])
        allowed = request_count <= limit

        return {
            "check": "rate_limit",
            "allowed": allowed,
            "risk_score": 0 if allowed else 5,
            "details": {"requests": request_count, "limit": limit},
        }

    def _check_user_agent(self, user_agent: str) -> Dict[str, Any]:
        """Check for suspicious user agents"""
        suspicious_patterns = [
            "sqlmap",
            "nikto",
            "nmap",
            "masscan",
            "zap",
            "burp",
            "dirb",
            "gobuster",
            "wfuzz",
            "hydra",
            "medusa",
        ]

        user_agent_lower = user_agent.lower()
        suspicious = any(
            pattern in user_agent_lower for pattern in suspicious_patterns
        )

        return {
            "check": "user_agent",
            "allowed": not suspicious,
            "risk_score": 8 if suspicious else 0,
            "details": {"user_agent": user_agent, "suspicious": suspicious},
        }

    async def _check_request_size(self, request: Request) -> Dict[str, Any]:
        """Check request size limits"""
        max_size = 10 * 1024 * 1024  # 10MB limit

        content_length = request.headers.get("content-length")
        if content_length:
            size = int(content_length)
            allowed = size <= max_size
            risk_score = 3 if not allowed else 0
        else:
            allowed = True
            size = 0
            risk_score = 0

        return {
            "check": "request_size",
            "allowed": allowed,
            "risk_score": risk_score,
            "details": {"size": size, "max_size": max_size},
        }

    async def _check_sql_injection(self, request: Request) -> Dict[str, Any]:
        """Check for SQL injection patterns"""
        sql_patterns = [
            "union select",
            "drop table",
            "delete from",
            "insert into",
            "update set",
            "'or'1'='1",
            "';--",
            "/*",
            "*/",
        ]

        # Check query parameters
        query_string = str(request.url.query).lower()

        # Check for SQL injection patterns
        sql_detected = any(pattern in query_string for pattern in sql_patterns)

        return {
            "check": "sql_injection",
            "allowed": not sql_detected,
            "risk_score": 10 if sql_detected else 0,
            "details": {
                "sql_detected": sql_detected,
                "query": query_string[:100],
            },
        }

    def _add_security_headers(self, response: Response):
        """Add comprehensive security headers"""
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        }

        for header, value in security_headers.items():
            response.headers[header] = value

    async def _log_security_event(
        self,
        event_type: str,
        source_ip: str,
        user_agent: str,
        endpoint: str,
        severity: str,
        details: Dict[str, Any],
    ):
        """Log security event for monitoring"""
        event = SecurityEvent(
            event_type=event_type,
            source_ip=source_ip,
            user_agent=user_agent,
            endpoint=endpoint,
            timestamp=time.time(),
            severity=severity,
            details=details,
        )

        self.security_events.append(event)

        # Log to system logger
        logger.warning(
            f"Security event: {event_type} from {source_ip} at {endpoint}"
        )

        # Keep only recent events (last 1000)
        if len(self.security_events) > 1000:
            self.security_events = self.security_events[-1000:]

    def get_security_metrics(self) -> Dict[str, Any]:
        """Get security metrics for monitoring"""
        current_time = time.time()
        recent_events = [
            event
            for event in self.security_events
            if current_time - event.timestamp < 3600  # Last hour
        ]

        event_types = {}
        severity_counts = {}

        for event in recent_events:
            event_types[event.event_type] = (
                event_types.get(event.event_type, 0) + 1
            )
            severity_counts[event.severity] = (
                severity_counts.get(event.severity, 0) + 1
            )

        return {
            "total_events": len(recent_events),
            "event_types": event_types,
            "severity_distribution": severity_counts,
            "rate_limit_entries": len(self.rate_limits),
        }


# Factory function for easy integration
def create_enhanced_security_middleware(config: Optional[Dict] = None):
    """Create enhanced security middleware with configuration"""
    return EnhancedSecurityMiddleware, config or {}
