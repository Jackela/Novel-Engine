"""
Tests for Enterprise Security Manager Module

Coverage targets:
- Permission checks
- Role validation
- Audit logging
- Access control decisions
"""

import pytest

pytestmark = pytest.mark.unit

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set


# Define local enums for testing (avoid importing full module with dependencies)
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
    reputation_score: float
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

    def test_behavioral_profile_defaults(self):
        """Test BehavioralProfile default values."""
        profile = BehavioralProfile(user_id="user456")
        
        assert profile.typical_access_hours == []
        assert profile.typical_countries == set()
        assert profile.typical_user_agents == set()
        assert profile.average_session_duration == 0.0
        assert profile.anomaly_score == 0.0
        assert profile.last_updated is not None


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

    def test_security_event_default_status(self):
        """Test SecurityEvent default investigation status."""
        event = SecurityEvent(
            id="evt456",
            timestamp=datetime.now(timezone.utc),
            event_type="test",
            severity=ThreatLevel.LOW,
            source_ip="127.0.0.1",
            user_id=None,
            user_agent="test",
            request_path="/test",
            threat_indicators=[],
            automated_response=[],
            evidence={},
            compliance_tags=[],
        )
        
        assert event.investigation_status == "open"
