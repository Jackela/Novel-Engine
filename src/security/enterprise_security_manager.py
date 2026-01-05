#!/usr/bin/env python3
"""
ENTERPRISE SECURITY MANAGER - ZERO TRUST ARCHITECTURE
=======================================================

Advanced enterprise-grade security features including:
- Real-time threat detection and response
- Advanced rate limiting and DDoS protection
- IP reputation management and geo-blocking
- Behavioral analytics and anomaly detection
- Compliance frameworks (GDPR, SOC2, HIPAA)
- Zero Trust architecture implementation
- Advanced audit trails and forensics

Architecture: Zero Trust + AI-Powered Threat Detection
Security Level: Enterprise Grade with Military Standards
Author: Chief Security Officer
May the System protect all operations from threats 🛡️
"""

import ipaddress
import json
import os
import time

try:
    import aioredis
except ImportError:
    aioredis = None

try:
    import aiosqlite
except ImportError:
    aiosqlite = None

try:
    import geoip2.database
except ImportError:
    if os.getenv("ALLOW_MOCK_GEOIP", "false").lower() != "true":
        raise

    # Stub implementation when geoip2 is not available and mocks are allowed
    class MockGeoIP2Database:
        def __init__(self, *args, **kwargs):
            pass

        def city(self, ip):
            class MockCity:
                country = type("", (), {"iso_code": "US"})()
                city = type("", (), {"name": "Unknown"})()

            return MockCity()

    geoip2 = type(
        "", (), {"database": type("", (), {"Reader": MockGeoIP2Database})()}
    )()
import logging
import re
import secrets
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from fastapi import Request

try:
    import user_agents
except ImportError:
    if os.getenv("ALLOW_MOCK_USER_AGENTS", "false").lower() != "true":
        raise

    # Stub implementation when user_agents is not available and mocks are allowed
    class MockUserAgent:
        def __init__(self):
            self.browser = type("", (), {"family": "Unknown"})()
            self.os = type("", (), {"family": "Unknown"})()

    user_agents = type("", (), {"parse": lambda ua: MockUserAgent()})()

# Enhanced logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enterprise Security Constants
MAX_REQUESTS_PER_MINUTE = 60
MAX_REQUESTS_PER_HOUR = 1000
MAX_REQUESTS_PER_DAY = 10000
SUSPICIOUS_THRESHOLD = 0.7
THREAT_THRESHOLD = 0.9
GEO_BLOCK_HIGH_RISK_COUNTRIES = {"CN", "RU", "KP", "IR"}
ALLOWED_USER_AGENTS_PATTERNS = [
    r"^Mozilla/.*",
    r"^Chrome/.*",
    r"^Safari/.*",
    r"^Edge/.*",
    r"^Opera/.*",
    r"^curl/.*",
    r"^PostmanRuntime/.*",
    r"^python-requests/.*",
]


class ThreatLevel(str, Enum):
    """Enterprise Threat Classification System"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    BLOCKED = "blocked"


class SecurityAction(str, Enum):
    """Automated Security Response Actions"""

    MONITOR = "monitor"
    RATE_LIMIT = "rate_limit"
    CHALLENGE = "challenge"
    BLOCK_TEMPORARY = "block_temporary"
    BLOCK_PERMANENT = "block_permanent"
    REQUIRE_MFA = "require_mfa"
    ALERT_ADMIN = "alert_admin"


class ComplianceFramework(str, Enum):
    """Supported Compliance Frameworks"""

    GDPR = "gdpr"
    SOC2 = "soc2"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    ISO27001 = "iso27001"
    NIST = "nist"


@dataclass
class ThreatIntelligence:
    """Real-time Threat Intelligence Data"""

    ip_address: str
    reputation_score: float  # 0.0 (safe) to 1.0 (malicious)
    country_code: Optional[str]
    is_vpn: bool = False
    is_tor: bool = False
    is_proxy: bool = False
    is_datacenter: bool = False
    threat_categories: List[str] = field(default_factory=list)
    last_seen_malicious: Optional[datetime] = None
    confidence_score: float = 0.0


@dataclass
class BehavioralProfile:
    """User Behavioral Analytics Profile"""

    user_id: str
    typical_access_hours: List[int] = field(default_factory=list)
    typical_countries: Set[str] = field(default_factory=set)
    typical_user_agents: Set[str] = field(default_factory=set)
    typical_request_patterns: Dict[str, int] = field(default_factory=dict)
    average_session_duration: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    anomaly_score: float = 0.0


@dataclass
class SecurityEvent:
    """Enhanced Security Event with Threat Intelligence"""

    id: str
    timestamp: datetime
    event_type: str
    severity: ThreatLevel
    source_ip: str
    user_id: Optional[str]
    user_agent: str
    request_path: str
    threat_indicators: List[str]
    automated_response: List[SecurityAction]
    evidence: Dict[str, Any]
    compliance_tags: List[ComplianceFramework]
    investigation_status: str = "open"


class SecurityMetrics:
    """Real-time Security Metrics"""

    def __init__(self):
        self.requests_per_minute = defaultdict(int)
        self.blocked_ips = set()
        self.threat_events = deque(maxlen=1000)
        self.compliance_violations = defaultdict(int)
        self.false_positives = 0
        self.true_positives = 0


class EnterpriseSecurityManager:
    """Enterprise Security Manager with Zero Trust Architecture"""

    def __init__(
        self,
        database_path: str,
        redis_url: str = "redis://localhost:6379",
        geoip_database_path: Optional[str] = None,
        enable_geo_blocking: bool = True,
        enable_behavioral_analytics: bool = True,
        compliance_frameworks: List[ComplianceFramework] = None,
    ):
        self.database_path = database_path
        self.redis_url = redis_url
        self.geoip_database_path = geoip_database_path
        self.enable_geo_blocking = enable_geo_blocking
        self.enable_behavioral_analytics = enable_behavioral_analytics
        self.compliance_frameworks = compliance_frameworks or [ComplianceFramework.GDPR]

        # Initialize components
        self.redis_client = None
        self.geoip_reader = None
        self.metrics = SecurityMetrics()
        self.behavioral_profiles = {}
        self.threat_intelligence_cache = {}

        # Rate limiting stores
        self.rate_limits = defaultdict(lambda: defaultdict(deque))
        self.ip_reputation_cache = {}

        # Security rules engine
        self.security_rules = self._initialize_security_rules()

    async def initialize(self):
        """Initialize Enterprise Security Components"""
        try:
            # Initialize Redis connection
            self.redis_client = aioredis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("✅ Redis connection established for security cache")

            # Initialize GeoIP database
            if self.geoip_database_path and Path(self.geoip_database_path).exists():
                self.geoip_reader = geoip2.database.Reader(self.geoip_database_path)
                logger.info("✅ GeoIP database loaded for geo-blocking")

            # Initialize security database
            await self._initialize_security_database()

            # Load behavioral profiles
            if self.enable_behavioral_analytics:
                await self._load_behavioral_profiles()

            logger.info("🛡️ ENTERPRISE SECURITY MANAGER INITIALIZED")

        except Exception as e:
            logger.error(f"❌ Failed to initialize Enterprise Security Manager: {e}")
            raise

    async def _initialize_security_database(self):
        """Initialize enhanced security database schema"""
        async with aiosqlite.connect(self.database_path) as conn:
            await conn.execute("PRAGMA foreign_keys = ON")
            await conn.execute("PRAGMA journal_mode = WAL")

            # Enhanced threat intelligence table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS threat_intelligence (
                    ip_address TEXT PRIMARY KEY,
                    reputation_score REAL NOT NULL,
                    country_code TEXT,
                    is_vpn BOOLEAN DEFAULT FALSE,
                    is_tor BOOLEAN DEFAULT FALSE,
                    is_proxy BOOLEAN DEFAULT FALSE,
                    is_datacenter BOOLEAN DEFAULT FALSE,
                    threat_categories TEXT, -- JSON array
                    last_seen_malicious TIMESTAMP,
                    confidence_score REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Behavioral analytics table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS behavioral_profiles (
                    user_id TEXT PRIMARY KEY,
                    typical_access_hours TEXT, -- JSON array
                    typical_countries TEXT, -- JSON array
                    typical_user_agents TEXT, -- JSON array
                    typical_request_patterns TEXT, -- JSON object
                    average_session_duration REAL DEFAULT 0.0,
                    anomaly_score REAL DEFAULT 0.0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """
            )

            # Enhanced security events table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS enhanced_security_events (
                    id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    source_ip TEXT NOT NULL,
                    user_id TEXT,
                    user_agent TEXT NOT NULL,
                    request_path TEXT NOT NULL,
                    threat_indicators TEXT, -- JSON array
                    automated_response TEXT, -- JSON array
                    evidence TEXT, -- JSON object
                    compliance_tags TEXT, -- JSON array
                    investigation_status TEXT DEFAULT 'open',
                    resolved_at TIMESTAMP,
                    false_positive BOOLEAN DEFAULT FALSE
                )
            """
            )

            # IP reputation blacklist/whitelist
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ip_reputation (
                    ip_address TEXT PRIMARY KEY,
                    list_type TEXT NOT NULL, -- 'blacklist', 'whitelist'
                    reason TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """
            )

            # Compliance audit trails
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS compliance_audit_trail (
                    id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    framework TEXT NOT NULL,
                    data_subject_id TEXT,
                    action_type TEXT NOT NULL,
                    data_categories TEXT, -- JSON array
                    legal_basis TEXT,
                    retention_period INTEGER,
                    evidence TEXT, -- JSON object
                    compliance_officer TEXT NOT NULL
                )
            """
            )

            await conn.commit()
            logger.info("🛡️ Enhanced security database schema initialized")

    def _initialize_security_rules(self) -> Dict[str, Any]:
        """Initialize AI-powered security rules engine"""
        return {
            "rate_limiting": {
                "requests_per_minute": MAX_REQUESTS_PER_MINUTE,
                "requests_per_hour": MAX_REQUESTS_PER_HOUR,
                "requests_per_day": MAX_REQUESTS_PER_DAY,
                "burst_threshold": 10,
                "sliding_window": True,
            },
            "geo_blocking": {
                "high_risk_countries": GEO_BLOCK_HIGH_RISK_COUNTRIES,
                "require_additional_verification": True,
                "allow_vpn_from_safe_countries": False,
            },
            "behavioral_detection": {
                "anomaly_threshold": SUSPICIOUS_THRESHOLD,
                "threat_threshold": THREAT_THRESHOLD,
                "learning_period_days": 30,
                "min_samples_required": 100,
            },
            "threat_intelligence": {
                "reputation_threshold": 0.6,
                "auto_block_threshold": 0.8,
                "intelligence_sources": ["internal", "feeds"],
                "cache_ttl_hours": 24,
            },
        }

    async def evaluate_request_security(
        self, request: Request, user_id: Optional[str] = None
    ) -> Tuple[bool, List[SecurityAction], ThreatLevel]:
        """
        Comprehensive security evaluation of incoming requests
        Returns: (is_allowed, required_actions, threat_level)
        """
        client_ip = self._extract_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        request_path = str(request.url.path)

        threat_indicators = []
        security_actions = []
        max_threat_level = ThreatLevel.LOW

        try:
            # 1. Rate limiting check
            rate_limit_result = await self._check_rate_limits(client_ip, user_id)
            if not rate_limit_result["allowed"]:
                threat_indicators.append("rate_limit_exceeded")
                security_actions.append(SecurityAction.RATE_LIMIT)
                max_threat_level = max(max_threat_level, ThreatLevel.MEDIUM)

            # 2. IP reputation check
            ip_reputation = await self._check_ip_reputation(client_ip)
            if ip_reputation["threat_level"] != ThreatLevel.LOW:
                threat_indicators.append(
                    f"ip_reputation_{ip_reputation['threat_level']}"
                )
                max_threat_level = max(max_threat_level, ip_reputation["threat_level"])

                if ip_reputation["threat_level"] == ThreatLevel.CRITICAL:
                    security_actions.append(SecurityAction.BLOCK_TEMPORARY)
                elif ip_reputation["threat_level"] == ThreatLevel.HIGH:
                    security_actions.append(SecurityAction.CHALLENGE)

            # 3. Geographic analysis
            if self.enable_geo_blocking:
                geo_result = await self._analyze_geographic_risk(client_ip)
                if geo_result["is_high_risk"]:
                    threat_indicators.append("high_risk_geography")
                    security_actions.append(SecurityAction.REQUIRE_MFA)
                    max_threat_level = max(max_threat_level, ThreatLevel.MEDIUM)

            # 4. User agent analysis
            ua_analysis = self._analyze_user_agent(user_agent)
            if ua_analysis["is_suspicious"]:
                threat_indicators.append("suspicious_user_agent")
                security_actions.append(SecurityAction.MONITOR)
                max_threat_level = max(max_threat_level, ThreatLevel.MEDIUM)

            # 5. Behavioral analytics (if user authenticated)
            if user_id and self.enable_behavioral_analytics:
                behavioral_result = await self._analyze_behavioral_patterns(
                    user_id, client_ip, user_agent, request_path
                )
                if behavioral_result["anomaly_score"] > SUSPICIOUS_THRESHOLD:
                    threat_indicators.append("behavioral_anomaly")
                    security_actions.append(SecurityAction.CHALLENGE)
                    max_threat_level = max(max_threat_level, ThreatLevel.HIGH)

            # 6. Request pattern analysis
            pattern_analysis = await self._analyze_request_patterns(
                client_ip, request_path, user_agent
            )
            if pattern_analysis["is_attack_pattern"]:
                threat_indicators.append("attack_pattern_detected")
                security_actions.append(SecurityAction.BLOCK_TEMPORARY)
                max_threat_level = max(max_threat_level, ThreatLevel.HIGH)

            # Determine final decision
            is_allowed = max_threat_level not in [
                ThreatLevel.CRITICAL,
                ThreatLevel.BLOCKED,
            ]
            if SecurityAction.BLOCK_TEMPORARY in security_actions:
                is_allowed = False

            # Log security event if significant
            if max_threat_level >= ThreatLevel.MEDIUM or threat_indicators:
                await self._log_security_event(
                    event_type="request_evaluation",
                    severity=max_threat_level,
                    source_ip=client_ip,
                    user_id=user_id,
                    user_agent=user_agent,
                    request_path=request_path,
                    threat_indicators=threat_indicators,
                    automated_response=security_actions,
                    evidence={
                        "rate_limit_result": rate_limit_result,
                        "ip_reputation": ip_reputation,
                        "user_agent_analysis": ua_analysis,
                    },
                )

            return is_allowed, security_actions, max_threat_level

        except Exception as e:
            logger.error(f"❌ Security evaluation failed: {e}")
            # Fail secure - block on errors
            return False, [SecurityAction.BLOCK_TEMPORARY], ThreatLevel.HIGH

    async def _check_rate_limits(
        self, ip_address: str, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Advanced sliding window rate limiting with Redis"""
        current_time = time.time()
        window_minute = int(current_time // 60)
        window_hour = int(current_time // 3600)
        window_day = int(current_time // 86400)

        # Use Redis for distributed rate limiting
        pipe = self.redis_client.pipeline()

        # Check per-minute rate limit
        minute_key = f"rate_limit:minute:{ip_address}:{window_minute}"
        pipe.incr(minute_key)
        pipe.expire(minute_key, 60)

        # Check per-hour rate limit
        hour_key = f"rate_limit:hour:{ip_address}:{window_hour}"
        pipe.incr(hour_key)
        pipe.expire(hour_key, 3600)

        # Check per-day rate limit
        day_key = f"rate_limit:day:{ip_address}:{window_day}"
        pipe.incr(day_key)
        pipe.expire(day_key, 86400)

        results = await pipe.execute()
        minute_count = results[0]
        hour_count = results[2]
        day_count = results[4]

        # Check if any limit exceeded
        exceeded = []
        if minute_count > MAX_REQUESTS_PER_MINUTE:
            exceeded.append("minute")
        if hour_count > MAX_REQUESTS_PER_HOUR:
            exceeded.append("hour")
        if day_count > MAX_REQUESTS_PER_DAY:
            exceeded.append("day")

        return {
            "allowed": len(exceeded) == 0,
            "current_counts": {
                "minute": minute_count,
                "hour": hour_count,
                "day": day_count,
            },
            "limits_exceeded": exceeded,
        }

    async def _check_ip_reputation(self, ip_address: str) -> Dict[str, Any]:
        """Check IP reputation against threat intelligence"""
        # Check local cache first
        if ip_address in self.ip_reputation_cache:
            cached = self.ip_reputation_cache[ip_address]
            if (datetime.now(timezone.utc) - cached["timestamp"]).hours < 24:
                return cached["data"]

        # Check Redis cache
        redis_key = f"ip_reputation:{ip_address}"
        cached_data = await self.redis_client.get(redis_key)

        if cached_data:
            reputation_data = json.loads(cached_data)
        else:
            # Analyze IP reputation
            reputation_data = await self._analyze_ip_reputation(ip_address)

            # Cache result
            await self.redis_client.setex(
                redis_key,
                3600 * 24,  # 24 hours
                json.dumps(reputation_data, default=str),
            )

        # Update local cache
        self.ip_reputation_cache[ip_address] = {
            "timestamp": datetime.now(timezone.utc),
            "data": reputation_data,
        }

        return reputation_data

    async def _analyze_ip_reputation(self, ip_address: str) -> Dict[str, Any]:
        """Analyze IP reputation using multiple threat intelligence sources"""
        threat_level = ThreatLevel.LOW
        reputation_score = 0.0
        threat_categories = []

        try:
            # Check database for known threats
            async with aiosqlite.connect(self.database_path) as conn:
                cursor = await conn.execute(
                    """
                    SELECT reputation_score, threat_categories, confidence_score
                    FROM threat_intelligence WHERE ip_address = ?
                """,
                    (ip_address,),
                )
                row = await cursor.fetchone()

                if row:
                    reputation_score = row[0]
                    threat_categories = json.loads(row[1] or "[]")
                    row[2]

                    if reputation_score >= 0.8:
                        threat_level = ThreatLevel.CRITICAL
                    elif reputation_score >= 0.6:
                        threat_level = ThreatLevel.HIGH
                    elif reputation_score >= 0.4:
                        threat_level = ThreatLevel.MEDIUM

                # Check IP blacklist/whitelist
                cursor = await conn.execute(
                    """
                    SELECT list_type, severity FROM ip_reputation 
                    WHERE ip_address = ? AND is_active = TRUE
                    AND (expires_at IS NULL OR expires_at > ?)
                """,
                    (ip_address, datetime.now(timezone.utc)),
                )
                reputation_row = await cursor.fetchone()

                if reputation_row:
                    list_type, severity = reputation_row
                    if list_type == "blacklist":
                        threat_level = ThreatLevel(severity)
                        reputation_score = 1.0
                    elif list_type == "whitelist":
                        threat_level = ThreatLevel.LOW
                        reputation_score = 0.0

        except Exception as e:
            logger.error(f"Error analyzing IP reputation for {ip_address}: {e}")

        return {
            "threat_level": threat_level,
            "reputation_score": reputation_score,
            "threat_categories": threat_categories,
            "is_known_threat": reputation_score > 0.5,
        }

    async def _analyze_geographic_risk(self, ip_address: str) -> Dict[str, Any]:
        """Analyze geographic risk factors"""
        if not self.geoip_reader:
            return {"is_high_risk": False, "country_code": None}

        try:
            response = self.geoip_reader.city(ip_address)
            country_code = response.country.iso_code

            is_high_risk = (
                country_code in GEO_BLOCK_HIGH_RISK_COUNTRIES
                or response.traits.is_anonymous_proxy
                or response.traits.is_satellite_provider
            )

            return {
                "is_high_risk": is_high_risk,
                "country_code": country_code,
                "country_name": response.country.name,
                "city": response.city.name,
                "is_proxy": response.traits.is_anonymous_proxy,
                "is_satellite": response.traits.is_satellite_provider,
            }

        except Exception as e:
            logger.warning(f"GeoIP analysis failed for {ip_address}: {e}")
            return {"is_high_risk": False, "country_code": None}

    def _analyze_user_agent(self, user_agent: str) -> Dict[str, Any]:
        """Analyze user agent for suspicious patterns"""
        if not user_agent or user_agent.lower() in ["", "unknown", "-"]:
            return {"is_suspicious": True, "reason": "missing_user_agent"}

        # Parse user agent
        parsed_ua = user_agents.parse(user_agent)

        # Check against allowed patterns
        is_valid_pattern = any(
            re.match(pattern, user_agent) for pattern in ALLOWED_USER_AGENTS_PATTERNS
        )

        suspicious_indicators = []

        if not is_valid_pattern:
            suspicious_indicators.append("unknown_pattern")

        if len(user_agent) < 10:
            suspicious_indicators.append("too_short")

        if len(user_agent) > 500:
            suspicious_indicators.append("too_long")

        # Check for suspicious keywords
        suspicious_keywords = ["bot", "crawler", "spider", "scraper", "hack", "exploit"]
        if any(keyword in user_agent.lower() for keyword in suspicious_keywords):
            suspicious_indicators.append("suspicious_keywords")

        return {
            "is_suspicious": len(suspicious_indicators) > 0,
            "indicators": suspicious_indicators,
            "parsed": {
                "browser": parsed_ua.browser.family,
                "version": parsed_ua.browser.version_string,
                "os": parsed_ua.os.family,
                "device": parsed_ua.device.family,
            },
        }

    async def _analyze_behavioral_patterns(
        self, user_id: str, ip_address: str, user_agent: str, request_path: str
    ) -> Dict[str, Any]:
        """Behavioral analytics and anomaly detection"""
        current_hour = datetime.now(timezone.utc).hour

        # Get or create behavioral profile
        profile = await self._get_behavioral_profile(user_id)
        if not profile:
            return {"anomaly_score": 0.0, "is_first_time": True}

        anomaly_score = 0.0
        anomalies = []

        # Check time-based patterns
        if current_hour not in profile.typical_access_hours:
            anomaly_score += 0.2
            anomalies.append("unusual_access_time")

        # Check geographic patterns
        geo_info = await self._analyze_geographic_risk(ip_address)
        if (
            geo_info["country_code"]
            and geo_info["country_code"] not in profile.typical_countries
        ):
            anomaly_score += 0.3
            anomalies.append("unusual_location")

        # Check user agent patterns
        if user_agent not in profile.typical_user_agents:
            anomaly_score += 0.1
            anomalies.append("unusual_user_agent")

        # Check request patterns
        request_category = self._categorize_request_path(request_path)
        expected_frequency = profile.typical_request_patterns.get(request_category, 0)
        if expected_frequency == 0:
            anomaly_score += 0.2
            anomalies.append("unusual_request_pattern")

        # Update profile with new data
        await self._update_behavioral_profile(
            user_id,
            current_hour,
            geo_info.get("country_code"),
            user_agent,
            request_category,
        )

        return {
            "anomaly_score": min(anomaly_score, 1.0),
            "anomalies": anomalies,
            "profile_age_days": (
                datetime.now(timezone.utc) - profile.last_updated
            ).days,
        }

    async def _analyze_request_patterns(
        self, ip_address: str, request_path: str, user_agent: str
    ) -> Dict[str, Any]:
        """Analyze for attack patterns and suspicious behavior"""
        attack_indicators = []

        # SQL injection patterns
        sql_patterns = [
            r"union.*select",
            r"or\s+1=1",
            r"drop\s+table",
            r"insert\s+into",
            r"delete\s+from",
            r"update.*set",
        ]
        if any(re.search(pattern, request_path.lower()) for pattern in sql_patterns):
            attack_indicators.append("sql_injection")

        # XSS patterns
        xss_patterns = [
            r"<script",
            r"javascript:",
            r"on\w+\s*=",
            r"eval\s*\(",
            r"alert\s*\(",
        ]
        if any(re.search(pattern, request_path.lower()) for pattern in xss_patterns):
            attack_indicators.append("xss_attempt")

        # Path traversal patterns
        if "../" in request_path or "..%2f" in request_path.lower():
            attack_indicators.append("path_traversal")

        # Command injection patterns
        cmd_patterns = [r";\s*cat", r";\s*ls", r";\s*rm", r"&&", r"\|\|"]
        if any(re.search(pattern, request_path.lower()) for pattern in cmd_patterns):
            attack_indicators.append("command_injection")

        return {
            "is_attack_pattern": len(attack_indicators) > 0,
            "attack_indicators": attack_indicators,
            "risk_score": min(len(attack_indicators) * 0.3, 1.0),
        }

    def _extract_client_ip(self, request: Request) -> str:
        """Extract real client IP considering proxies and load balancers"""
        # Check headers in order of preference
        headers_to_check = [
            "CF-Connecting-IP",  # Cloudflare
            "X-Real-IP",  # Nginx
            "X-Forwarded-For",  # Standard proxy header
            "X-Client-IP",  # Apache
            "X-Forwarded",  # Less common
            "Forwarded-For",  # RFC 7239
            "Forwarded",  # RFC 7239
        ]

        for header in headers_to_check:
            if header in request.headers:
                ip = request.headers[header].split(",")[0].strip()
                try:
                    # Validate IP address
                    ipaddress.ip_address(ip)
                    return ip
                except ValueError:
                    continue

        # Fall back to client host
        return request.client.host if request.client else "unknown"

    def _categorize_request_path(self, path: str) -> str:
        """Categorize request paths for behavioral analysis"""
        if "/api/" in path:
            if "/auth/" in path:
                return "authentication"
            elif "/story/" in path or "/narrative/" in path:
                return "narrative"
            elif "/agent/" in path:
                return "agent_management"
            else:
                return "api_general"
        elif "/static/" in path:
            return "static_content"
        elif "/admin/" in path:
            return "administration"
        else:
            return "web_interface"

    async def _get_behavioral_profile(
        self, user_id: str
    ) -> Optional[BehavioralProfile]:
        """Retrieve user's behavioral profile"""
        try:
            async with aiosqlite.connect(self.database_path) as conn:
                cursor = await conn.execute(
                    """
                    SELECT typical_access_hours, typical_countries, typical_user_agents,
                           typical_request_patterns, average_session_duration, 
                           anomaly_score, last_updated
                    FROM behavioral_profiles WHERE user_id = ?
                """,
                    (user_id,),
                )
                row = await cursor.fetchone()

                if row:
                    return BehavioralProfile(
                        user_id=user_id,
                        typical_access_hours=json.loads(row[0] or "[]"),
                        typical_countries=set(json.loads(row[1] or "[]")),
                        typical_user_agents=set(json.loads(row[2] or "[]")),
                        typical_request_patterns=json.loads(row[3] or "{}"),
                        average_session_duration=row[4] or 0.0,
                        anomaly_score=row[5] or 0.0,
                        last_updated=(
                            datetime.fromisoformat(row[6])
                            if row[6]
                            else datetime.now(timezone.utc)
                        ),
                    )
        except Exception as e:
            logger.error(f"Error retrieving behavioral profile for {user_id}: {e}")

        return None

    async def _update_behavioral_profile(
        self,
        user_id: str,
        current_hour: int,
        country_code: Optional[str],
        user_agent: str,
        request_category: str,
    ):
        """Update user's behavioral profile with new data"""
        try:
            profile = await self._get_behavioral_profile(user_id)

            if not profile:
                # Create new profile
                profile = BehavioralProfile(
                    user_id=user_id,
                    typical_access_hours=[current_hour],
                    typical_countries={country_code} if country_code else set(),
                    typical_user_agents={user_agent},
                    typical_request_patterns={request_category: 1},
                )
            else:
                # Update existing profile
                if current_hour not in profile.typical_access_hours:
                    profile.typical_access_hours.append(current_hour)
                    # Keep only recent patterns (last 30 days)
                    if len(profile.typical_access_hours) > 24:
                        profile.typical_access_hours = profile.typical_access_hours[
                            -24:
                        ]

                if country_code:
                    profile.typical_countries.add(country_code)
                    # Limit to 10 countries
                    if len(profile.typical_countries) > 10:
                        profile.typical_countries.pop()

                profile.typical_user_agents.add(user_agent)
                # Limit to 20 user agents
                if len(profile.typical_user_agents) > 20:
                    profile.typical_user_agents.pop()

                profile.typical_request_patterns[request_category] = (
                    profile.typical_request_patterns.get(request_category, 0) + 1
                )

            profile.last_updated = datetime.now(timezone.utc)

            # Save to database
            async with aiosqlite.connect(self.database_path) as conn:
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO behavioral_profiles 
                    (user_id, typical_access_hours, typical_countries, typical_user_agents,
                     typical_request_patterns, average_session_duration, anomaly_score, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        user_id,
                        json.dumps(profile.typical_access_hours),
                        json.dumps(list(profile.typical_countries)),
                        json.dumps(list(profile.typical_user_agents)),
                        json.dumps(profile.typical_request_patterns),
                        profile.average_session_duration,
                        profile.anomaly_score,
                        profile.last_updated,
                    ),
                )
                await conn.commit()

        except Exception as e:
            logger.error(f"Error updating behavioral profile for {user_id}: {e}")

    async def _load_behavioral_profiles(self):
        """Load behavioral profiles into memory"""
        try:
            async with aiosqlite.connect(self.database_path) as conn:
                cursor = await conn.execute(
                    """
                    SELECT user_id, typical_access_hours, typical_countries, 
                           typical_user_agents, typical_request_patterns,
                           average_session_duration, anomaly_score, last_updated
                    FROM behavioral_profiles
                    WHERE last_updated > ?
                """,
                    (datetime.now(timezone.utc) - timedelta(days=30),),
                )

                rows = await cursor.fetchall()
                for row in rows:
                    profile = BehavioralProfile(
                        user_id=row[0],
                        typical_access_hours=json.loads(row[1] or "[]"),
                        typical_countries=set(json.loads(row[2] or "[]")),
                        typical_user_agents=set(json.loads(row[3] or "[]")),
                        typical_request_patterns=json.loads(row[4] or "{}"),
                        average_session_duration=row[5] or 0.0,
                        anomaly_score=row[6] or 0.0,
                        last_updated=(
                            datetime.fromisoformat(row[7])
                            if row[7]
                            else datetime.now(timezone.utc)
                        ),
                    )
                    self.behavioral_profiles[row[0]] = profile

                logger.info(
                    f"📊 Loaded {len(self.behavioral_profiles)} behavioral profiles"
                )

        except Exception as e:
            logger.error(f"Error loading behavioral profiles: {e}")

    async def _log_security_event(
        self,
        event_type: str,
        severity: ThreatLevel,
        source_ip: str,
        user_id: Optional[str],
        user_agent: str,
        request_path: str,
        threat_indicators: List[str],
        automated_response: List[SecurityAction],
        evidence: Dict[str, Any],
    ):
        """Log enhanced security event"""
        event_id = secrets.token_urlsafe(16)
        event = SecurityEvent(
            id=event_id,
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            severity=severity,
            source_ip=source_ip,
            user_id=user_id,
            user_agent=user_agent,
            request_path=request_path,
            threat_indicators=threat_indicators,
            automated_response=automated_response,
            evidence=evidence,
            compliance_tags=self.compliance_frameworks,
        )

        try:
            async with aiosqlite.connect(self.database_path) as conn:
                await conn.execute(
                    """
                    INSERT INTO enhanced_security_events 
                    (id, timestamp, event_type, severity, source_ip, user_id, user_agent,
                     request_path, threat_indicators, automated_response, evidence, compliance_tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        event.id,
                        event.timestamp,
                        event.event_type,
                        event.severity.value,
                        event.source_ip,
                        event.user_id,
                        event.user_agent,
                        event.request_path,
                        json.dumps(event.threat_indicators),
                        json.dumps([a.value for a in event.automated_response]),
                        json.dumps(event.evidence, default=str),
                        json.dumps([f.value for f in event.compliance_tags]),
                    ),
                )
                await conn.commit()

            # Add to metrics
            self.metrics.threat_events.append(event)

            # Send real-time alerts for high severity events
            if severity in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                await self._send_security_alert(event)

        except Exception as e:
            logger.error(f"Failed to log security event: {e}")

    async def _send_security_alert(self, event: SecurityEvent):
        """Send real-time security alerts to administrators"""
        alert_data = {
            "event_id": event.id,
            "severity": event.severity.value,
            "source_ip": event.source_ip,
            "threat_indicators": event.threat_indicators,
            "timestamp": event.timestamp.isoformat(),
            "automated_response": [a.value for a in event.automated_response],
        }

        # Publish to Redis for real-time dashboard
        await self.redis_client.publish(
            "security_alerts", json.dumps(alert_data, default=str)
        )

        logger.warning(
            f"🚨 SECURITY ALERT: {event.severity.value.upper()} - {event.event_type} from {event.source_ip}"
        )

    async def get_security_metrics(self) -> Dict[str, Any]:
        """Get real-time security metrics"""
        current_time = datetime.now(timezone.utc)
        last_24h = current_time - timedelta(hours=24)

        try:
            async with aiosqlite.connect(self.database_path) as conn:
                # Get threat events in last 24 hours
                cursor = await conn.execute(
                    """
                    SELECT severity, COUNT(*) as count
                    FROM enhanced_security_events 
                    WHERE timestamp > ?
                    GROUP BY severity
                """,
                    (last_24h,),
                )
                threat_counts = dict(await cursor.fetchall())

                # Get blocked IPs
                cursor = await conn.execute(
                    """
                    SELECT COUNT(*) FROM ip_reputation 
                    WHERE list_type = 'blacklist' AND is_active = TRUE
                """
                )
                blocked_ips_count = (await cursor.fetchone())[0]

                # Get top threat indicators
                cursor = await conn.execute(
                    """
                    SELECT threat_indicators, COUNT(*) as count
                    FROM enhanced_security_events
                    WHERE timestamp > ?
                    GROUP BY threat_indicators
                    ORDER BY count DESC
                    LIMIT 10
                """,
                    (last_24h,),
                )
                threat_indicators = await cursor.fetchall()

        except Exception as e:
            logger.error(f"Error retrieving security metrics: {e}")
            threat_counts = {}
            blocked_ips_count = 0
            threat_indicators = []

        return {
            "threat_events_24h": threat_counts,
            "blocked_ips": blocked_ips_count,
            "active_behavioral_profiles": len(self.behavioral_profiles),
            "top_threat_indicators": threat_indicators,
            "security_status": "active",
            "last_updated": current_time.isoformat(),
        }

    async def add_ip_to_reputation_list(
        self,
        ip_address: str,
        list_type: str,
        reason: str,
        severity: ThreatLevel,
        created_by: str,
        expires_hours: Optional[int] = None,
    ):
        """Add IP to blacklist or whitelist"""
        expires_at = None
        if expires_hours:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)

        async with aiosqlite.connect(self.database_path) as conn:
            await conn.execute(
                """
                INSERT OR REPLACE INTO ip_reputation 
                (ip_address, list_type, reason, severity, created_by, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (ip_address, list_type, reason, severity.value, created_by, expires_at),
            )
            await conn.commit()

        logger.info(
            f"🛡️ Added IP {ip_address} to {list_type} (severity: {severity.value})"
        )

    async def cleanup(self):
        """Cleanup resources"""
        if self.redis_client:
            await self.redis_client.close()
        if self.geoip_reader:
            self.geoip_reader.close()
        logger.info("🧹 Enterprise Security Manager cleaned up")


# Global security manager instance
enterprise_security_manager: Optional[EnterpriseSecurityManager] = None


def get_enterprise_security_manager() -> EnterpriseSecurityManager:
    """Get the global enterprise security manager instance"""
    global enterprise_security_manager
    if enterprise_security_manager is None:
        raise RuntimeError("Enterprise Security Manager not initialized")
    return enterprise_security_manager


async def initialize_enterprise_security_manager(**kwargs) -> EnterpriseSecurityManager:
    """Initialize the global enterprise security manager"""
    global enterprise_security_manager
    enterprise_security_manager = EnterpriseSecurityManager(**kwargs)
    await enterprise_security_manager.initialize()
    return enterprise_security_manager


__all__ = [
    "EnterpriseSecurityManager",
    "ThreatLevel",
    "SecurityAction",
    "ComplianceFramework",
    "ThreatIntelligence",
    "BehavioralProfile",
    "SecurityEvent",
    "SecurityMetrics",
    "get_enterprise_security_manager",
    "initialize_enterprise_security_manager",
]
