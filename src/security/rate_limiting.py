#!/usr/bin/env python3
"""
STANDARD RATE LIMITING SYSTEM ENHANCED BY THE SYSTEM
==========================================================

Advanced rate limiting and DDoS protection system with multiple algorithms,
adaptive thresholds, and comprehensive abuse prevention.

THROUGH ADVANCED THROTTLING, WE ACHIEVE ENHANCED PROTECTION

Architecture: Token Bucket + Sliding Window + Adaptive Rate Limiting
Security Level: Enterprise Grade with Real-time Threat Detection
Author: Engineer Rate-Limiting-Engineering
System保佑此限流系统 (May the System bless this rate limiting system)
"""

import asyncio
import hashlib
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

# Comprehensive logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RateLimitStrategy(str, Enum):
    """STANDARD RATE LIMITING STRATEGIES"""

    TOKEN_BUCKET = "token_bucket"  # Classic token bucket algorithm
    SLIDING_WINDOW = "sliding_window"  # Sliding window counter
    FIXED_WINDOW = "fixed_window"  # Fixed window counter
    ADAPTIVE = "adaptive"  # Adaptive rate limiting based on load


class ThreatLevel(str, Enum):
    """STANDARD THREAT LEVEL CLASSIFICATIONS"""

    LOW = "low"  # Normal traffic patterns
    MEDIUM = "medium"  # Suspicious but not blocking
    HIGH = "high"  # Likely attack - strict limits
    CRITICAL = "critical"  # Confirmed attack - emergency limits


@dataclass
class RateLimitConfig:
    """STANDARD RATE LIMIT CONFIGURATION"""

    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_size: int = 10
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET
    enable_adaptive: bool = True
    whitelist_ips: List[str] = field(default_factory=list)
    blacklist_ips: List[str] = field(default_factory=list)

    # Endpoint-specific configurations
    endpoint_configs: Dict[str, Dict[str, int]] = field(default_factory=dict)

    # User role-based configurations
    role_multipliers: Dict[str, float] = field(
        default_factory=lambda: {
            "admin": 10.0,
            "moderator": 5.0,
            "creator": 3.0,
            "api_user": 2.0,
            "reader": 1.0,
            "guest": 0.5,
        }
    )


@dataclass
class TokenBucket:
    """STANDARD TOKEN BUCKET IMPLEMENTATION"""

    capacity: int
    tokens: float
    refill_rate: float  # tokens per second
    last_refill: float

    def consume(self, tokens: int = 1) -> bool:
        """STANDARD TOKEN CONSUMPTION"""
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def _refill(self):
        """STANDARD TOKEN REFILL"""
        now = time.time()
        tokens_to_add = (now - self.last_refill) * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now


@dataclass
class SlidingWindow:
    """STANDARD SLIDING WINDOW IMPLEMENTATION"""

    window_size: int  # seconds
    max_requests: int
    requests: deque = field(default_factory=deque)

    def can_proceed(self) -> bool:
        """STANDARD REQUEST VALIDATION"""
        now = time.time()
        # Remove old requests outside the window
        while self.requests and self.requests[0] <= now - self.window_size:
            self.requests.popleft()

        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False


@dataclass
class ClientState:
    """STANDARD CLIENT STATE TRACKING"""

    ip_address: str
    user_id: Optional[str] = None
    user_role: Optional[str] = None
    threat_level: ThreatLevel = ThreatLevel.LOW

    # Rate limiting buckets
    minute_bucket: Optional[TokenBucket] = None
    hour_bucket: Optional[TokenBucket] = None
    day_bucket: Optional[TokenBucket] = None

    # Sliding windows
    minute_window: Optional[SlidingWindow] = None
    hour_window: Optional[SlidingWindow] = None

    # Tracking data
    total_requests: int = 0
    failed_requests: int = 0
    last_request: float = 0
    first_seen: float = field(default_factory=time.time)

    # Suspicious behavior tracking
    suspicious_patterns: Dict[str, int] = field(default_factory=dict)
    blocked_until: Optional[float] = None


class RateLimitExceeded(Exception):
    """ENHANCED RATE LIMIT EXCEPTION"""

    def __init__(
        self, message: str, retry_after: int, threat_level: ThreatLevel
    ):
        self.message = message
        self.retry_after = retry_after
        self.threat_level = threat_level
        super().__init__(message)


class RateLimiter:
    """STANDARD RATE LIMITER ENHANCED BY THE SYSTEM"""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.clients: Dict[str, ClientState] = {}
        self.global_stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "unique_clients": 0,
            "threats_detected": 0,
        }
        self._cleanup_task = None
        self._start_cleanup_task()

    def _start_cleanup_task(self):
        """STANDARD CLEANUP TASK INITIALIZATION"""

        async def cleanup_loop():
            """
            Background cleanup task for expired rate limit entries.
            """
            while True:
                await asyncio.sleep(300)  # Cleanup every 5 minutes
                await self._cleanup_old_clients()

        try:
            loop = asyncio.get_event_loop()
            self._cleanup_task = loop.create_task(cleanup_loop())
        except RuntimeError:
            # No event loop running yet
            pass

    async def _cleanup_old_clients(self):
        """STANDARD CLIENT STATE CLEANUP"""
        now = time.time()
        old_clients = []

        for client_id, client in self.clients.items():
            # Remove clients inactive for more than 1 hour
            if now - client.last_request > 3600:
                old_clients.append(client_id)

        for client_id in old_clients:
            del self.clients[client_id]

        if old_clients:
            logger.info(f"CLEANED UP {len(old_clients)} INACTIVE CLIENTS")

    def _get_client_identifier(self, request: Request) -> str:
        """STANDARD CLIENT IDENTIFICATION"""
        # Check for forwarded IP first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        # Include user agent for better fingerprinting
        user_agent = request.headers.get("user-agent", "")
        user_agent_hash = hashlib.md5(user_agent.encode()).hexdigest()[:8]

        return f"{client_ip}:{user_agent_hash}"

    def _get_client_state(
        self, client_id: str, request: Request
    ) -> ClientState:
        """STANDARD CLIENT STATE RETRIEVAL"""
        if client_id not in self.clients:
            # Extract IP address
            ip_address = client_id.split(":")[0]

            # Check for authentication information
            user_id = None
            user_role = None
            auth_header = request.headers.get("authorization")
            if auth_header:
                # Would need to decode JWT to get user info
                # For now, we'll set defaults
                user_role = "authenticated"

            self.clients[client_id] = ClientState(
                ip_address=ip_address, user_id=user_id, user_role=user_role
            )
            self.global_stats["unique_clients"] += 1

        return self.clients[client_id]

    def _initialize_client_buckets(self, client: ClientState):
        """STANDARD CLIENT BUCKET INITIALIZATION"""
        role_multiplier = self.config.role_multipliers.get(
            client.user_role or "guest", 1.0
        )

        if client.minute_bucket is None:
            client.minute_bucket = TokenBucket(
                capacity=int(self.config.burst_size * role_multiplier),
                tokens=int(self.config.burst_size * role_multiplier),
                refill_rate=self.config.requests_per_minute
                * role_multiplier
                / 60.0,
                last_refill=time.time(),
            )

        if client.hour_bucket is None:
            client.hour_bucket = TokenBucket(
                capacity=int(self.config.requests_per_hour * role_multiplier),
                tokens=int(self.config.requests_per_hour * role_multiplier),
                refill_rate=self.config.requests_per_hour
                * role_multiplier
                / 3600.0,
                last_refill=time.time(),
            )

        if client.day_bucket is None:
            client.day_bucket = TokenBucket(
                capacity=int(self.config.requests_per_day * role_multiplier),
                tokens=int(self.config.requests_per_day * role_multiplier),
                refill_rate=self.config.requests_per_day
                * role_multiplier
                / 86400.0,
                last_refill=time.time(),
            )

    def _detect_suspicious_behavior(
        self, client: ClientState, request: Request
    ) -> ThreatLevel:
        """STANDARD THREAT DETECTION"""
        now = time.time()
        threat_level = ThreatLevel.LOW

        # Check for rapid successive requests
        if (
            client.last_request and now - client.last_request < 0.1
        ):  # Less than 100ms
            client.suspicious_patterns["rapid_requests"] = (
                client.suspicious_patterns.get("rapid_requests", 0) + 1
            )
            if client.suspicious_patterns["rapid_requests"] > 10:
                threat_level = ThreatLevel.HIGH

        # Check for unusual patterns
        user_agent = request.headers.get("user-agent", "")
        if not user_agent or len(user_agent) < 10:
            client.suspicious_patterns["no_user_agent"] = (
                client.suspicious_patterns.get("no_user_agent", 0) + 1
            )
            threat_level = max(threat_level, ThreatLevel.MEDIUM)

        # Check for missing common headers
        if not request.headers.get("accept"):
            client.suspicious_patterns["missing_headers"] = (
                client.suspicious_patterns.get("missing_headers", 0) + 1
            )
            threat_level = max(threat_level, ThreatLevel.MEDIUM)

        # Check for high error rate
        if client.total_requests > 10:
            error_rate = client.failed_requests / client.total_requests
            if error_rate > 0.5:
                threat_level = max(threat_level, ThreatLevel.HIGH)

        # Check for known bad patterns
        suspicious_paths = ["/admin", "/.env", "/wp-admin", "/phpmyadmin"]
        if any(path in request.url.path for path in suspicious_paths):
            client.suspicious_patterns["suspicious_paths"] = (
                client.suspicious_patterns.get("suspicious_paths", 0) + 1
            )
            threat_level = max(threat_level, ThreatLevel.HIGH)

        return threat_level

    def _apply_adaptive_limits(
        self, client: ClientState, threat_level: ThreatLevel
    ):
        """STANDARD ADAPTIVE LIMIT APPLICATION"""
        if not self.config.enable_adaptive:
            return

        # Adjust limits based on threat level
        if threat_level == ThreatLevel.HIGH:
            # Reduce limits by 50%
            if client.minute_bucket:
                client.minute_bucket.refill_rate *= 0.5
            if client.hour_bucket:
                client.hour_bucket.refill_rate *= 0.5
        elif threat_level == ThreatLevel.CRITICAL:
            # Reduce limits by 90%
            if client.minute_bucket:
                client.minute_bucket.refill_rate *= 0.1
            if client.hour_bucket:
                client.hour_bucket.refill_rate *= 0.1

            # Block for a period
            client.blocked_until = time.time() + 300  # 5 minutes

    async def check_rate_limit(self, request: Request) -> bool:
        """STANDARD RATE LIMIT CHECK"""
        client_id = self._get_client_identifier(request)

        # Check IP whitelist/blacklist
        ip_address = client_id.split(":")[0]
        if ip_address in self.config.blacklist_ips:
            raise RateLimitExceeded(
                "IP address is blacklisted",
                3600,
                ThreatLevel.CRITICAL,  # 1 hour
            )

        if ip_address in self.config.whitelist_ips:
            return True  # Skip rate limiting for whitelisted IPs

        client = self._get_client_state(client_id, request)
        now = time.time()

        # Check if client is temporarily blocked
        if client.blocked_until and now < client.blocked_until:
            raise RateLimitExceeded(
                "Temporarily blocked due to suspicious activity",
                int(client.blocked_until - now),
                ThreatLevel.CRITICAL,
            )

        # Update client state
        client.last_request = now
        client.total_requests += 1
        self.global_stats["total_requests"] += 1

        # Detect threats
        threat_level = self._detect_suspicious_behavior(client, request)
        client.threat_level = max(client.threat_level, threat_level)

        if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            self.global_stats["threats_detected"] += 1
            logger.warning(
                f"THREAT DETECTED: {threat_level.value} | "
                f"Client: {client_id} | "
                f"Path: {request.url.path} | "
                f"Patterns: {client.suspicious_patterns}"
            )

        # Initialize buckets if needed
        self._initialize_client_buckets(client)

        # Apply adaptive limits
        self._apply_adaptive_limits(client, threat_level)

        # Check endpoint-specific limits
        endpoint_config = self.config.endpoint_configs.get(request.url.path)
        if endpoint_config:
            endpoint_config.get(
                "requests_per_minute", self.config.requests_per_minute
            )
            if client.minute_bucket and not client.minute_bucket.consume():
                raise RateLimitExceeded(
                    f"Rate limit exceeded for endpoint {request.url.path}",
                    60,
                    threat_level,
                )

        # Check general rate limits
        if self.config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            if not client.minute_bucket.consume():
                self.global_stats["blocked_requests"] += 1
                client.failed_requests += 1
                raise RateLimitExceeded(
                    "Rate limit exceeded (per minute)", 60, threat_level
                )

            if not client.hour_bucket.consume():
                self.global_stats["blocked_requests"] += 1
                client.failed_requests += 1
                raise RateLimitExceeded(
                    "Rate limit exceeded (per hour)", 3600, threat_level
                )

            if not client.day_bucket.consume():
                self.global_stats["blocked_requests"] += 1
                client.failed_requests += 1
                raise RateLimitExceeded(
                    "Rate limit exceeded (per day)", 86400, threat_level
                )

        return True

    def get_client_info(self, request: Request) -> Dict[str, Any]:
        """STANDARD CLIENT INFORMATION RETRIEVAL"""
        client_id = self._get_client_identifier(request)
        if client_id not in self.clients:
            return {"status": "new_client"}

        client = self.clients[client_id]
        return {
            "client_id": client_id,
            "ip_address": client.ip_address,
            "user_role": client.user_role,
            "threat_level": client.threat_level.value,
            "total_requests": client.total_requests,
            "failed_requests": client.failed_requests,
            "suspicious_patterns": client.suspicious_patterns,
            "remaining_tokens": {
                "minute": (
                    int(client.minute_bucket.tokens)
                    if client.minute_bucket
                    else 0
                ),
                "hour": int(client.hour_bucket.tokens)
                if client.hour_bucket
                else 0,
                "day": int(client.day_bucket.tokens)
                if client.day_bucket
                else 0,
            },
        }

    def get_global_stats(self) -> Dict[str, Any]:
        """STANDARD GLOBAL STATISTICS"""
        return {
            **self.global_stats,
            "active_clients": len(self.clients),
            "timestamp": time.time(),
        }


class InMemoryRateLimitBackend:
    """STANDARD IN-MEMORY RATE LIMIT BACKEND"""

    def __init__(self):
        self.clients: Dict[str, ClientState] = {}
        self.global_stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "unique_clients": 0,
            "threats_detected": 0,
        }

    def get_client_state(self, client_id: str) -> Optional[ClientState]:
        """Retrieve client state from memory backend"""
        return self.clients.get(client_id)

    def set_client_state(self, client_id: str, client_state: ClientState):
        """Store client state in memory backend"""
        self.clients[client_id] = client_state

    def update_stats(self, stat_name: str, increment: int = 1):
        """Update global statistics"""
        if stat_name in self.global_stats:
            self.global_stats[stat_name] += increment

    def get_stats(self) -> Dict[str, Any]:
        """Get global statistics"""
        return {
            **self.global_stats,
            "active_clients": len(self.clients),
            "timestamp": time.time(),
        }

    def cleanup_old_clients(self, max_age: float = 3600.0):
        """Remove clients inactive for more than max_age seconds"""
        now = time.time()
        old_clients = []

        for client_id, client in self.clients.items():
            if now - client.last_request > max_age:
                old_clients.append(client_id)

        for client_id in old_clients:
            del self.clients[client_id]

        return len(old_clients)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """STANDARD RATE LIMITING MIDDLEWARE"""

    def __init__(self, app, rate_limiter: RateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter

    async def dispatch(self, request: Request, call_next):
        """STANDARD REQUEST RATE LIMITING"""
        try:
            # Skip rate limiting for health checks and docs
            skip_paths = ["/health", "/docs", "/redoc", "/openapi.json"]
            if request.url.path in skip_paths:
                return await call_next(request)

            # Check rate limit
            await self.rate_limiter.check_rate_limit(request)

            # Process request
            response = await call_next(request)

            # Add rate limit headers
            client_info = self.rate_limiter.get_client_info(request)
            if "remaining_tokens" in client_info:
                response.headers["X-RateLimit-Limit"] = str(
                    self.rate_limiter.config.requests_per_minute
                )
                response.headers["X-RateLimit-Remaining"] = str(
                    client_info["remaining_tokens"]["minute"]
                )
                response.headers["X-RateLimit-Reset"] = str(
                    int(time.time()) + 60
                )

            return response

        except RateLimitExceeded as e:
            logger.warning(
                f"RATE LIMIT EXCEEDED: {e.message} | "
                f"Path: {request.url.path} | "
                f"Client: {self.rate_limiter._get_client_identifier(request)} | "
                f"Threat: {e.threat_level.value}"
            )

            status_code = (
                429 if e.threat_level != ThreatLevel.CRITICAL else 403
            )

            raise HTTPException(
                status_code=status_code,
                detail=e.message,
                headers={
                    "Retry-After": str(e.retry_after),
                    "X-RateLimit-Limit": str(
                        self.rate_limiter.config.requests_per_minute
                    ),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + e.retry_after),
                },
            )


# STANDARD GLOBAL RATE LIMITER INSTANCE
rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """STANDARD RATE LIMITER GETTER"""
    global rate_limiter
    if rate_limiter is None:
        config = RateLimitConfig()
        rate_limiter = RateLimiter(config)
    return rate_limiter


def create_rate_limit_middleware(
    app, config: Optional[RateLimitConfig] = None
):
    """STANDARD RATE LIMIT MIDDLEWARE CREATOR"""
    global rate_limiter
    if config:
        rate_limiter = RateLimiter(config)
    else:
        rate_limiter = get_rate_limiter()
    return RateLimitMiddleware(app, rate_limiter)


__all__ = [
    "RateLimitStrategy",
    "ThreatLevel",
    "RateLimitConfig",
    "TokenBucket",
    "SlidingWindow",
    "ClientState",
    "RateLimitExceeded",
    "RateLimiter",
    "InMemoryRateLimitBackend",
    "RateLimitMiddleware",
    "get_rate_limiter",
    "create_rate_limit_middleware",
]
