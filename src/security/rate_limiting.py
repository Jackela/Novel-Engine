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
from enum import Enum, EnumMeta
from typing import Any, Dict, List, Optional, Set

from fastapi import Request

# Comprehensive logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class _RateLimitStrategyMeta(EnumMeta):
    """Enum meta class that provides a sensible default when instantiated without a value."""

    def __call__(cls, value=None, *args, **kwargs):
        if isinstance(value, cls):
            return value
        if value is None:
            # Default to the first declared enum member (TOKEN_BUCKET for this enum)
            return next(iter(cls))
        return super().__call__(value, *args, **kwargs)


class RateLimitStrategy(str, Enum, metaclass=_RateLimitStrategyMeta):
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


THREAT_PRECEDENCE = {
    ThreatLevel.LOW: 0,
    ThreatLevel.MEDIUM: 1,
    ThreatLevel.HIGH: 2,
    ThreatLevel.CRITICAL: 3,
}


def elevate_threat(current: ThreatLevel, candidate: ThreatLevel) -> ThreatLevel:
    """Return the higher-severity threat level based on predefined precedence."""
    if THREAT_PRECEDENCE[candidate] > THREAT_PRECEDENCE[current]:
        return candidate
    return current


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
            "guest": 1.0,
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
class RateLimit:
    """STANDARD RATE LIMIT SPECIFICATION

    Simple rate limit configuration for testing and basic use cases.
    For production use, consider RateLimitConfig with advanced features.
    """

    requests: int  # Maximum number of requests allowed
    window: int  # Time window in seconds


@dataclass
class RateLimitResult:
    """STANDARD RATE LIMIT CHECK RESULT

    Result of checking whether a request is allowed under rate limiting.
    """

    allowed: bool  # Whether the request is allowed
    remaining: int  # Number of requests remaining in the window
    retry_after: int = 0  # Seconds until the client can retry (if blocked)


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

    def __init__(self, message: str, retry_after: int, threat_level: ThreatLevel):
        self.message = message
        self.retry_after = retry_after
        self.threat_level = threat_level
        super().__init__(message)


class RateLimiter:
    """STANDARD RATE LIMITER ENHANCED BY THE SYSTEM"""

    def __init__(
        self,
        config: RateLimitConfig,
        backend: Optional["InMemoryRateLimitBackend"] = None,
    ):
        self.config = config
        self.clients: Dict[str, ClientState] = {}
        self.backend = backend or InMemoryRateLimitBackend()
        self.global_stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "unique_clients": 0,
            "threats_detected": 0,
        }
        self._cleanup_task = None
        self.ddos_detector = DDoSDetector()
        self.whitelist = IPWhitelist(config.whitelist_ips)
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
            loop = asyncio.get_running_loop()
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

    def _get_client_state(self, client_id: str, request: Request) -> ClientState:
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
                ip_address=ip_address,
                user_id=user_id,
                user_role=user_role or "guest",
            )
            self.global_stats["unique_clients"] += 1

        return self.clients[client_id]

    def _initialize_client_buckets(self, client: ClientState):
        """STANDARD CLIENT BUCKET INITIALIZATION"""
        role_multiplier = self.config.role_multipliers.get(
            client.user_role or "guest", 1.0
        )

        if client.minute_bucket is None:
            base_capacity = max(self.config.burst_size, self.config.requests_per_minute)
            client.minute_bucket = TokenBucket(
                capacity=int(base_capacity * role_multiplier),
                tokens=int(base_capacity * role_multiplier),
                refill_rate=self.config.requests_per_minute * role_multiplier / 60.0,
                last_refill=time.time(),
            )

        if client.hour_bucket is None:
            client.hour_bucket = TokenBucket(
                capacity=int(self.config.requests_per_hour * role_multiplier),
                tokens=int(self.config.requests_per_hour * role_multiplier),
                refill_rate=self.config.requests_per_hour * role_multiplier / 3600.0,
                last_refill=time.time(),
            )

        if client.day_bucket is None:
            client.day_bucket = TokenBucket(
                capacity=int(self.config.requests_per_day * role_multiplier),
                tokens=int(self.config.requests_per_day * role_multiplier),
                refill_rate=self.config.requests_per_day * role_multiplier / 86400.0,
                last_refill=time.time(),
            )

    def _detect_suspicious_behavior(
        self, client: ClientState, request: Request
    ) -> ThreatLevel:
        """STANDARD THREAT DETECTION"""
        now = time.time()
        threat_level = ThreatLevel.LOW

        # Check for rapid successive requests
        if client.last_request and now - client.last_request < 0.1:  # Less than 100ms
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
            threat_level = elevate_threat(threat_level, ThreatLevel.MEDIUM)

        # Check for missing common headers
        if not request.headers.get("accept"):
            client.suspicious_patterns["missing_headers"] = (
                client.suspicious_patterns.get("missing_headers", 0) + 1
            )
            threat_level = elevate_threat(threat_level, ThreatLevel.MEDIUM)

        # Check for high error rate
        if client.total_requests > 10:
            error_rate = client.failed_requests / client.total_requests
            if error_rate > 0.5:
                threat_level = elevate_threat(threat_level, ThreatLevel.HIGH)

        # Check for known bad patterns
        suspicious_paths = ["/admin", "/.env", "/wp-admin", "/phpmyadmin"]
        if any(path in request.url.path for path in suspicious_paths):
            client.suspicious_patterns["suspicious_paths"] = (
                client.suspicious_patterns.get("suspicious_paths", 0) + 1
            )
            threat_level = elevate_threat(threat_level, ThreatLevel.HIGH)

        return threat_level

    def _apply_adaptive_limits(self, client: ClientState, threat_level: ThreatLevel):
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
                "IP address is blacklisted", 3600, ThreatLevel.CRITICAL  # 1 hour
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

        # Update counters
        client.total_requests += 1
        self.global_stats["total_requests"] += 1

        # Detect threats before mutating last_request so we can compare to the previous value
        threat_level = self._detect_suspicious_behavior(client, request)
        client.threat_level = elevate_threat(client.threat_level, threat_level)

        # Track request timestamp after detection checks
        client.last_request = now

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
            endpoint_config.get("requests_per_minute", self.config.requests_per_minute)
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
                if (
                    client.suspicious_patterns.get("rapid_requests", 0) >= 3
                    or client.total_requests <= self.config.burst_size * 2
                ):
                    threat_level = elevate_threat(threat_level, ThreatLevel.HIGH)
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
                    int(client.minute_bucket.tokens) if client.minute_bucket else 0
                ),
                "hour": int(client.hour_bucket.tokens) if client.hour_bucket else 0,
                "day": int(client.day_bucket.tokens) if client.day_bucket else 0,
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

    async def check_rate_limit(
        self, client_id: str, rate_limit: RateLimit
    ) -> RateLimitResult:
        """STANDARD RATE LIMIT CHECK

        Check if a client has exceeded their rate limit and return the result.

        Args:
            client_id: Unique identifier for the client (IP, user ID, etc.)
            rate_limit: Rate limit specification to check against

        Returns:
            RateLimitResult indicating whether request is allowed
        """
        now = time.time()

        # Get or create client state
        if client_id not in self.clients:
            # Create new client state with sliding window
            window = SlidingWindow(
                window_size=rate_limit.window,
                max_requests=rate_limit.requests,
            )
            self.clients[client_id] = ClientState(
                ip_address=client_id,
                minute_window=window,
                first_seen=now,
                last_request=now,
            )

        client_state = self.clients[client_id]
        window = client_state.minute_window

        if window is None:
            # Initialize window if not present
            window = SlidingWindow(
                window_size=rate_limit.window,
                max_requests=rate_limit.requests,
            )
            client_state.minute_window = window

        # Remove old requests outside the window
        while window.requests and window.requests[0] <= now - rate_limit.window:
            window.requests.popleft()

        # Check if request is allowed
        current_count = len(window.requests)
        remaining = rate_limit.requests - current_count

        if current_count < rate_limit.requests:
            # Allow the request
            window.requests.append(now)
            client_state.total_requests += 1
            client_state.last_request = now
            self.update_stats("total_requests")

            return RateLimitResult(
                allowed=True,
                remaining=remaining - 1,  # -1 because we just consumed one
                retry_after=0,
            )
        else:
            # Block the request
            oldest_request = window.requests[0]
            retry_after = int(rate_limit.window - (now - oldest_request)) + 1

            client_state.failed_requests += 1
            self.update_stats("blocked_requests")

            return RateLimitResult(
                allowed=False,
                remaining=0,
                retry_after=retry_after,
            )

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


class DDoSDetector:
    """Lightweight async DDoS detector used in middleware tests."""

    def __init__(self, threshold: int = 500, interval_seconds: int = 60):
        self.threshold = threshold
        self.interval_seconds = interval_seconds
        self._request_windows: Dict[str, deque] = {}

    async def analyze_request(self, client_identifier: str) -> tuple[bool, str]:
        now = time.time()
        window = self._request_windows.setdefault(client_identifier, deque())

        while window and now - window[0] > self.interval_seconds:
            window.popleft()

        window.append(now)
        if len(window) > self.threshold:
            return (
                False,
                "Potential DDoS attack detected - request threshold exceeded",
            )
        return True, "Traffic within acceptable thresholds"


class IPWhitelist:
    """Simple IP whitelist with sensible defaults for local development."""

    def __init__(self, additional_ips: Optional[List[str]] = None):
        defaults: Set[str] = {
            "127.0.0.1",
            "::1",
            "192.168.1.100",
        }
        if additional_ips:
            defaults.update(additional_ips)
        self._whitelist = defaults

    def is_whitelisted(self, ip_address: str) -> bool:
        if ip_address in self._whitelist:
            return True
        if ip_address.startswith("192.168."):
            return True
        if ip_address.startswith("10.") or ip_address.startswith("172.16."):
            return True
        return False


class RateLimitMiddleware:
    """STANDARD RATE LIMITING MIDDLEWARE (ASGI)"""

    def __init__(
        self,
        app,
        backend: Optional[InMemoryRateLimitBackend] = None,
        strategy: Optional[RateLimitStrategy] = None,
        config: Optional[RateLimitConfig] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        self.app = app
        self.strategy = strategy or RateLimitStrategy.TOKEN_BUCKET
        self.config = config or RateLimitConfig(strategy=self.strategy)
        self.backend = backend or InMemoryRateLimitBackend()
        self.rate_limiter = rate_limiter or RateLimiter(
            self.config, backend=self.backend
        )
        # Surface helper utilities commonly used by tests
        self.ddos_detector = self.rate_limiter.ddos_detector
        self.whitelist = self.rate_limiter.whitelist

    async def __call__(self, scope, receive, send):
        """STANDARD REQUEST RATE LIMITING"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from fastapi import Request

        request = Request(scope)

        try:
            # Skip rate limiting for health checks and docs
            skip_paths = ["/health", "/docs", "/redoc", "/openapi.json"]
            # To handle path correctly without consuming, we use request.url.path which is safe
            if request.url.path in skip_paths:
                await self.app(scope, receive, send)
                return

            client_id = self.rate_limiter._get_client_identifier(request)

            if self.whitelist and self.whitelist.is_whitelisted(client_id):
                await self.app(scope, receive, send)
                return

            if self.ddos_detector:
                allowed, reason = await self.ddos_detector.analyze_request(client_id)
                if not allowed:
                    raise RateLimitExceeded(
                        reason,
                        retry_after=60,
                        threat_level=ThreatLevel.CRITICAL,
                    )

            # Check rate limit
            rate_limit = RateLimit(
                requests=self.config.requests_per_minute,
                window=60,
            )
            limit_result = await self.backend.check_rate_limit(client_id, rate_limit)

            if not limit_result.allowed:
                raise RateLimitExceeded(
                    "Rate limit exceeded",
                    retry_after=limit_result.retry_after,
                    threat_level=ThreatLevel.HIGH,
                )

            # Wrapper to intercept response start and inject headers
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = message.setdefault("headers", [])
                    # Remove existing headers if any (to avoid dups, though unlikely for unique keys)
                    headers = [
                        h
                        for h in headers
                        if h[0].decode("latin-1").lower()
                        not in [
                            "x-ratelimit-limit",
                            "x-ratelimit-remaining",
                            "x-ratelimit-reset",
                        ]
                    ]

                    headers.append(
                        (
                            b"x-ratelimit-limit",
                            str(self.config.requests_per_minute).encode(),
                        )
                    )
                    headers.append(
                        (
                            b"x-ratelimit-remaining",
                            str(max(limit_result.remaining, 0)).encode(),
                        )
                    )
                    headers.append(
                        (b"x-ratelimit-reset", str(int(time.time()) + 60).encode())
                    )

                    message["headers"] = headers

                await send(message)

            await self.app(scope, receive, send_wrapper)

        except RateLimitExceeded as e:
            logger.warning(
                f"RATE LIMIT EXCEEDED: {e.message} | "
                f"Path: {request.url.path} | "
                f"Client: {self.rate_limiter._get_client_identifier(request)} | "
                f"Threat: {e.threat_level.value}"
            )

            status_code = 429 if e.threat_level != ThreatLevel.CRITICAL else 403

            from fastapi.responses import JSONResponse

            content = {"detail": e.message}
            headers = {
                "Retry-After": str(e.retry_after),
                "X-RateLimit-Limit": str(self.rate_limiter.config.requests_per_minute),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + e.retry_after),
            }

            response = JSONResponse(
                content=content, status_code=status_code, headers=headers
            )
            await response(scope, receive, send)

        except Exception:
            # Re-raise other exceptions to let downstream/upstream handle them
            raise


# STANDARD GLOBAL RATE LIMITER INSTANCE
rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """STANDARD RATE LIMITER GETTER"""
    global rate_limiter
    if rate_limiter is None:
        config = RateLimitConfig()
        backend = InMemoryRateLimitBackend()
        rate_limiter = RateLimiter(config, backend=backend)
    return rate_limiter


def create_rate_limit_middleware(app, config: Optional[RateLimitConfig] = None):
    """STANDARD RATE LIMIT MIDDLEWARE CREATOR"""
    global rate_limiter
    if config:
        backend = InMemoryRateLimitBackend()
        rate_limiter = RateLimiter(config, backend=backend)
        return RateLimitMiddleware(
            app,
            backend=backend,
            config=config,
            rate_limiter=rate_limiter,
        )
    else:
        rate_limiter = get_rate_limiter()
        return RateLimitMiddleware(
            app,
            backend=rate_limiter.backend,
            config=rate_limiter.config,
            rate_limiter=rate_limiter,
        )


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
    "DDoSDetector",
    "IPWhitelist",
    "get_rate_limiter",
    "create_rate_limit_middleware",
]
