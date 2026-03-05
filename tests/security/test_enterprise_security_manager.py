"""
Tests for Enterprise Security Manager Module

Coverage targets:
- Permission checks
- Role validation
- Audit logging
- Access control decisions
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import pytest_asyncio

from src.security.enterprise_security_manager import (
    BehavioralProfile,
    ComplianceFramework,
    EnterpriseSecurityManager,
    SecurityAction,
    SecurityEvent,
    SecurityMetrics,
    ThreatIntelligence,
    ThreatLevel,
    get_enterprise_security_manager,
    initialize_enterprise_security_manager,
)


class TestThreatLevel:
    """Tests for ThreatLevel enum."""

    def test_threat_levels(self):
        """Test all threat levels are defined."""
        assert ThreatLevel.LOW.value == "low"
        assert ThreatLevel.MEDIUM.value == "medium"
        assert ThreatLevel.HIGH.value == "high"
        assert ThreatLevel.CRITICAL.value == "critical"
        assert ThreatLevel.BLOCKED.value == "blocked"


class TestSecurityAction:
    """Tests for SecurityAction enum."""

    def test_security_actions(self):
        """Test all security actions are defined."""
        assert SecurityAction.MONITOR.value == "monitor"
        assert SecurityAction.RATE_LIMIT.value == "rate_limit"
        assert SecurityAction.CHALLENGE.value == "challenge"
        assert SecurityAction.BLOCK_TEMPORARY.value == "block_temporary"
        assert SecurityAction.BLOCK_PERMANENT.value == "block_permanent"
        assert SecurityAction.REQUIRE_MFA.value == "require_mfa"
        assert SecurityAction.ALERT_ADMIN.value == "alert_admin"


class TestComplianceFramework:
    """Tests for ComplianceFramework enum."""

    def test_compliance_frameworks(self):
        """Test all compliance frameworks are defined."""
        assert ComplianceFramework.GDPR.value == "gdpr"
        assert ComplianceFramework.SOC2.value == "soc2"
        assert ComplianceFramework.HIPAA.value == "hipaa"
        assert ComplianceFramework.PCI_DSS.value == "pci_dss"
        assert ComplianceFramework.ISO27001.value == "iso27001"
        assert ComplianceFramework.NIST.value == "nist"


class TestThreatIntelligence:
    """Tests for ThreatIntelligence dataclass."""

    def test_threat_intelligence_creation(self):
        """Test ThreatIntelligence creation."""
        intel = ThreatIntelligence(
            ip_address="192.168.1.1",
            reputation_score=0.8,
            country_code="US",
            is_vpn=False,
            is_tor=True,
            is_proxy=False,
            is_datacenter=True,
            threat_categories=["malware", "botnet"],
            confidence_score=0.9,
        )
        
        assert intel.ip_address == "192.168.1.1"
        assert intel.reputation_score == 0.8
        assert intel.country_code == "US"
        assert intel.is_vpn is False
        assert intel.is_tor is True
        assert intel.is_proxy is False
        assert intel.is_datacenter is True
        assert intel.threat_categories == ["malware", "botnet"]
        assert intel.confidence_score == 0.9


class TestBehavioralProfile:
    """Tests for BehavioralProfile dataclass."""

    def test_behavioral_profile_creation(self):
        """Test BehavioralProfile creation."""
        profile = BehavioralProfile(
            user_id="user123",
            typical_access_hours=[9, 10, 11, 14, 15],
            typical_countries={"US", "CA"},
            typical_user_agents={"Chrome/120", "Firefox/120"},
            average_session_duration=3600.0,
            anomaly_score=0.1,
        )
        
        assert profile.user_id == "user123"
        assert 9 in profile.typical_access_hours
        assert "US" in profile.typical_countries
        assert profile.average_session_duration == 3600.0
        assert profile.anomaly_score == 0.1


class TestSecurityEvent:
    """Tests for SecurityEvent dataclass."""

    def test_security_event_creation(self):
        """Test SecurityEvent creation."""
        event = SecurityEvent(
            id="evt123",
            timestamp=datetime.now(timezone.utc),
            event_type="login_failed",
            severity=ThreatLevel.HIGH,
            source_ip="192.168.1.1",
            user_id="user123",
            user_agent="Mozilla/5.0",
            request_path="/api/login",
            threat_indicators=["brute_force"],
            automated_response=[SecurityAction.BLOCK_TEMPORARY],
            evidence={"attempts": 5},
            compliance_tags=[ComplianceFramework.SOC2],
        )
        
        assert event.id == "evt123"
        assert event.event_type == "login_failed"
        assert event.severity == ThreatLevel.HIGH
        assert event.source_ip == "192.168.1.1"
        assert event.investigation_status == "open"  # Default value


class TestSecurityMetrics:
    """Tests for SecurityMetrics class."""

    def test_security_metrics_initialization(self):
        """Test SecurityMetrics initialization."""
        metrics = SecurityMetrics()
        
        assert metrics.requests_per_minute == {}
        assert metrics.blocked_ips == set()
        assert metrics.false_positives == 0
        assert metrics.true_positives == 0


@pytest.mark.asyncio
class TestEnterpriseSecurityManager:
    """Tests for EnterpriseSecurityManager class."""

    @pytest_asyncio.fixture
    async def security_manager(self):
        """Create an EnterpriseSecurityManager instance."""
        manager = EnterpriseSecurityManager(
            database_path=":memory:",
            redis_url="redis://localhost:6379",
            enable_geo_blocking=False,  # Disable for testing
            enable_behavioral_analytics=False,  # Disable for testing
        )
        return manager

    def test_initialization(self, security_manager):
        """Test security manager initialization."""
        assert security_manager.database_path == ":memory:"
        assert security_manager.redis_url == "redis://localhost:6379"
        assert security_manager.enable_geo_blocking is False
        assert security_manager.enable_behavioral_analytics is False
        assert security_manager.compliance_frameworks == [ComplianceFramework.GDPR]
        assert isinstance(security_manager.metrics, SecurityMetrics)

    def test_initialization_with_custom_frameworks(self):
        """Test initialization with custom compliance frameworks."""
        manager = EnterpriseSecurityManager(
            database_path=":memory:",
            compliance_frameworks=[ComplianceFramework.SOC2, ComplianceFramework.HIPAA],
        )
        
        assert ComplianceFramework.SOC2 in manager.compliance_frameworks
        assert ComplianceFramework.HIPAA in manager.compliance_frameworks

    def test_initialize_security_rules(self, security_manager):
        """Test security rules initialization."""
        rules = security_manager._initialize_security_rules()
        
        assert "rate_limiting" in rules
        assert "geo_blocking" in rules
        assert "behavioral_detection" in rules
        assert "threat_intelligence" in rules
        
        # Check rate limiting defaults
        assert rules["rate_limiting"]["requests_per_minute"] == 60
        assert rules["rate_limiting"]["requests_per_hour"] == 1000

    async def test_initialize_security_database(self, security_manager):
        """Test security database initialization."""
        await security_manager._initialize_security_database()
        
        # Check tables are created
        async with security_manager._connection() as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = {row[0] for row in await cursor.fetchall()}
            
            assert "threat_intelligence" in tables
            assert "behavioral_profiles" in tables
            assert "enhanced_security_events" in tables
            assert "ip_reputation" in tables
            assert "compliance_audit_trail" in tables

    def test_extract_client_ip_from_headers(self, security_manager):
        """Test client IP extraction from various headers."""
        # Test Cloudflare header
        request = Mock()
        request.headers = {"CF-Connecting-IP": "1.2.3.4"}
        request.client = Mock(host="10.0.0.1")
        
        ip = security_manager._extract_client_ip(request)
        assert ip == "1.2.3.4"
        
        # Test X-Forwarded-For header
        request.headers = {"X-Forwarded-For": "5.6.7.8, 9.10.11.12"}
        ip = security_manager._extract_client_ip(request)
        assert ip == "5.6.7.8"
        
        # Test fallback to client host
        request.headers = {}
        ip = security_manager._extract_client_ip(request)
        assert ip == "10.0.0.1"

    def test_extract_client_ip_invalid(self, security_manager):
        """Test client IP extraction with invalid IP."""
        request = Mock()
        request.headers = {"X-Real-IP": "not_an_ip"}
        request.client = Mock(host="10.0.0.1")
        
        ip = security_manager._extract_client_ip(request)
        # Should fallback to client host when header IP is invalid
        assert ip == "10.0.0.1"

    def test_analyze_user_agent_valid(self, security_manager):
        """Test user agent analysis with valid UA."""
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        result = security_manager._analyze_user_agent(ua)
        
        assert result["is_suspicious"] is False
        assert "parsed" in result
        assert result["parsed"]["browser"] in ["Chrome", "Other", "Unknown"]

    def test_analyze_user_agent_suspicious(self, security_manager):
        """Test user agent analysis with suspicious UA."""
        # Empty UA
        result = security_manager._analyze_user_agent("")
        assert result["is_suspicious"] is True
        
        # Too short
        result = security_manager._analyze_user_agent("ab")
        assert result["is_suspicious"] is True
        assert "too_short" in result["indicators"]
        
        # Contains suspicious keywords
        result = security_manager._analyze_user_agent("Mozilla/5.0 bot crawler")
        assert result["is_suspicious"] is True
        assert "suspicious_keywords" in result["indicators"]

    def test_analyze_user_agent_unknown(self, security_manager):
        """Test user agent analysis with unknown UA."""
        result = security_manager._analyze_user_agent("unknown")
        
        assert result["is_suspicious"] is True
        assert result["reason"] == "missing_user_agent"

    def test_categorize_request_path(self, security_manager):
        """Test request path categorization."""
        assert security_manager._categorize_request_path("/api/auth/login") == "authentication"
        assert security_manager._categorize_request_path("/api/story/123") == "narrative"
        assert security_manager._categorize_request_path("/api/agent/action") == "agent_management"
        assert security_manager._categorize_request_path("/api/other") == "api_general"
        assert security_manager._categorize_request_path("/static/style.css") == "static_content"
        assert security_manager._categorize_request_path("/admin/users") == "administration"
        assert security_manager._categorize_request_path("/home") == "web_interface"

    async def test_analyze_request_patterns_sql_injection(self, security_manager):
        """Test SQL injection pattern detection."""
        result = await security_manager._analyze_request_patterns(
            "192.168.1.1",
            "/api/data?id=1' OR '1'='1",
            "Mozilla/5.0",
        )
        
        assert result["is_attack_pattern"] is True
        assert "sql_injection" in result["attack_indicators"]

    async def test_analyze_request_patterns_xss(self, security_manager):
        """Test XSS pattern detection."""
        result = await security_manager._analyze_request_patterns(
            "192.168.1.1",
            '/api/data?input=<script>alert("xss")</script>',
            "Mozilla/5.0",
        )
        
        assert result["is_attack_pattern"] is True
        assert "xss_attempt" in result["attack_indicators"]

    async def test_analyze_request_patterns_path_traversal(self, security_manager):
        """Test path traversal pattern detection."""
        result = await security_manager._analyze_request_patterns(
            "192.168.1.1",
            "/api/file?path=../../../etc/passwd",
            "Mozilla/5.0",
        )
        
        assert result["is_attack_pattern"] is True
        assert "path_traversal" in result["attack_indicators"]

    async def test_analyze_request_patterns_command_injection(self, security_manager):
        """Test command injection pattern detection."""
        result = await security_manager._analyze_request_patterns(
            "192.168.1.1",
            "/api/exec?cmd=ls;cat /etc/passwd",
            "Mozilla/5.0",
        )
        
        assert result["is_attack_pattern"] is True
        assert "command_injection" in result["attack_indicators"]

    async def test_analyze_request_patterns_clean(self, security_manager):
        """Test clean request patterns."""
        result = await security_manager._analyze_request_patterns(
            "192.168.1.1",
            "/api/data?id=123",
            "Mozilla/5.0",
        )
        
        assert result["is_attack_pattern"] is False
        assert len(result["attack_indicators"]) == 0

    async def test_get_behavioral_profile_not_found(self, security_manager):
        """Test getting non-existent behavioral profile."""
        profile = await security_manager._get_behavioral_profile("nonexistent_user")
        assert profile is None

    async def test_update_behavioral_profile_create_new(self, security_manager):
        """Test creating new behavioral profile."""
        await security_manager._update_behavioral_profile(
            user_id="new_user",
            current_hour=14,
            country_code="US",
            user_agent="Mozilla/5.0",
            request_category="api_general",
        )
        
        # Profile should now exist
        profile = await security_manager._get_behavioral_profile("new_user")
        assert profile is not None
        assert profile.user_id == "new_user"
        assert 14 in profile.typical_access_hours
        assert "US" in profile.typical_countries

    async def test_add_ip_to_reputation_list(self, security_manager):
        """Test adding IP to reputation list."""
        await security_manager._initialize_security_database()
        
        await security_manager.add_ip_to_reputation_list(
            ip_address="192.168.1.100",
            list_type="blacklist",
            reason="Brute force attack",
            severity=ThreatLevel.HIGH,
            created_by="admin",
            expires_hours=24,
        )
        
        # Verify IP was added
        async with security_manager._connection() as conn:
            cursor = await conn.execute(
                "SELECT ip_address, list_type, severity FROM ip_reputation WHERE ip_address = ?",
                ("192.168.1.100",),
            )
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] == "192.168.1.100"
            assert row[1] == "blacklist"
            assert row[2] == "high"

    async def test_get_security_metrics(self, security_manager):
        """Test getting security metrics."""
        await security_manager._initialize_security_database()
        
        metrics = await security_manager.get_security_metrics()
        
        assert "threat_events_24h" in metrics
        assert "blocked_ips" in metrics
        assert "active_behavioral_profiles" in metrics
        assert "security_status" in metrics
        assert metrics["security_status"] == "active"

    async def test_cleanup(self, security_manager):
        """Test resource cleanup."""
        # Should not raise any errors
        await security_manager.cleanup()


class TestGlobalInstances:
    """Tests for global instances and initialization."""

    async def test_get_enterprise_security_manager_not_initialized(self):
        """Test getting manager before initialization raises error."""
        import src.security.enterprise_security_manager as esm_module
        original = esm_module.enterprise_security_manager
        esm_module.enterprise_security_manager = None
        
        try:
            with pytest.raises(RuntimeError, match="not initialized"):
                get_enterprise_security_manager()
        finally:
            esm_module.enterprise_security_manager = original

    async def test_initialize_enterprise_security_manager(self):
        """Test enterprise security manager initialization."""
        import src.security.enterprise_security_manager as esm_module
        original = esm_module.enterprise_security_manager
        
        try:
            esm_module.enterprise_security_manager = None
            
            # Mock Redis and other external dependencies
            with patch.object(EnterpriseSecurityManager, '_initialize_security_database', AsyncMock()):
                manager = await initialize_enterprise_security_manager(
                    database_path=":memory:",
                    enable_geo_blocking=False,
                    enable_behavioral_analytics=False,
                )
                assert manager is not None
                assert esm_module.enterprise_security_manager is manager
        finally:
            if esm_module.enterprise_security_manager:
                await esm_module.enterprise_security_manager.cleanup()
            esm_module.enterprise_security_manager = original
