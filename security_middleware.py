#!/usr/bin/env python3
"""
Security Middleware for Novel Engine
===================================

This module provides comprehensive security middleware for the FastAPI application.
"""

import time
import logging
import hashlib
import ipaddress
from typing import Set, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from collections import defaultdict, deque
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SecurityEventLogger:
    """Log security events for monitoring and analysis."""
    
    def __init__(self):
        self.security_logger = logging.getLogger("security")
        handler = logging.FileHandler("logs/security.log")
        formatter = logging.Formatter(
            '%(asctime)s - SECURITY - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.security_logger.addHandler(handler)
        self.security_logger.setLevel(logging.WARNING)
    
    def log_event(self, event_type: str, client_ip: str, details: Dict[str, Any]):
        """Log a security event."""
        self.security_logger.warning(
            f"{event_type} from {client_ip}: {details}"
        )

class IPBlocklist:
    """Manage IP address blocklist."""
    
    def __init__(self):
        self.blocked_ips: Set[str] = set()
        self.temp_blocked: Dict[str, datetime] = {}
        self.block_duration = timedelta(minutes=15)
    
    def is_blocked(self, ip: str) -> bool:
        """Check if IP is blocked."""
        # Check permanent blocks
        if ip in self.blocked_ips:
            return True
        
        # Check temporary blocks
        if ip in self.temp_blocked:
            if datetime.utcnow() > self.temp_blocked[ip]:
                del self.temp_blocked[ip]
                return False
            return True
        
        return False
    
    def temp_block(self, ip: str):
        """Temporarily block an IP address."""
        self.temp_blocked[ip] = datetime.utcnow() + self.block_duration
        logger.warning(f"Temporarily blocked IP: {ip}")
    
    def permanent_block(self, ip: str):
        """Permanently block an IP address."""
        self.blocked_ips.add(ip)
        logger.warning(f"Permanently blocked IP: {ip}")

class RequestAnalyzer:
    """Analyze requests for suspicious patterns."""
    
    def __init__(self):
        self.request_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.failed_attempts: Dict[str, int] = defaultdict(int)
        self.security_logger = SecurityEventLogger()
    
    def analyze_request(self, request: Request) -> bool:
        """Analyze request for suspicious patterns."""
        client_ip = self.get_client_ip(request)
        
        # Track request history
        now = time.time()
        self.request_history[client_ip].append(now)
        
        # Check for rapid requests (potential DoS)
        recent_requests = [
            t for t in self.request_history[client_ip] 
            if now - t < 60  # Last minute
        ]
        
        if len(recent_requests) > 30:  # More than 30 requests per minute
            self.security_logger.log_event(
                "RAPID_REQUESTS",
                client_ip,
                {"requests_per_minute": len(recent_requests)}
            )
            return False
        
        # Check for suspicious paths
        suspicious_patterns = [
            '/admin', '/wp-admin', '/.env', '/config',
            '/etc/passwd', '/proc/', '/sys/',
            'script>', 'javascript:', 'vbscript:',
            'SELECT ', 'UNION ', 'DROP ',
            '../', '..\\', '%2e%2e',
        ]
        
        request_path = str(request.url.path).lower()
        request_query = str(request.url.query).lower()
        
        for pattern in suspicious_patterns:
            if pattern.lower() in request_path or pattern.lower() in request_query:
                self.security_logger.log_event(
                    "SUSPICIOUS_REQUEST",
                    client_ip,
                    {"pattern": pattern, "path": request_path, "query": request_query}
                )
                return False
        
        return True
    
    def get_client_ip(self, request: Request) -> str:
        """Get the real client IP address."""
        # Check X-Forwarded-For header (from reverse proxy)
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header
        x_real_ip = request.headers.get("X-Real-IP")
        if x_real_ip:
            return x_real_ip
        
        # Fall back to direct connection
        return request.client.host if request.client else "unknown"

class SecurityMiddleware:
    """Comprehensive security middleware."""
    
    def __init__(self):
        self.ip_blocklist = IPBlocklist()
        self.request_analyzer = RequestAnalyzer()
        self.security_logger = SecurityEventLogger()
    
    async def __call__(self, request: Request, call_next):
        """Process request through security filters."""
        client_ip = self.request_analyzer.get_client_ip(request)
        
        # Check IP blocklist
        if self.ip_blocklist.is_blocked(client_ip):
            self.security_logger.log_event(
                "BLOCKED_IP_ACCESS",
                client_ip,
                {"path": str(request.url.path)}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Analyze request for suspicious patterns
        if not self.request_analyzer.analyze_request(request):
            self.ip_blocklist.temp_block(client_ip)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Suspicious request detected"
            )
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log slow requests (potential attacks)
        if process_time > 5.0:
            self.security_logger.log_event(
                "SLOW_REQUEST",
                client_ip,
                {"path": str(request.url.path), "duration": process_time}
            )
        
        return response
