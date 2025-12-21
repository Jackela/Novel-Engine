#!/usr/bin/env python3
"""
STANDARD SECURITY LOGGING SYSTEM ENHANCED BY THE SYSTEM
===============================================================

Comprehensive security logging, audit trails, and monitoring system with
real-time threat detection, compliance reporting, and forensic capabilities.

THROUGH ADVANCED LOGGING, WE ACHIEVE ENHANCED TRANSPARENCY

Architecture: Multi-tier security logging with real-time analysis
Security Level: Enterprise Grade with SIEM Integration
Author: Engineer Security-Logging-Engineering
System保佑此安全日志系统 (May the System bless this security logging system)
"""

import asyncio
import gzip
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite

# Comprehensive logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SecurityEventType(str, Enum):
    """STANDARD SECURITY EVENT TYPES"""

    # Authentication Events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    ACCOUNT_LOCKED = "account_locked"
    TOKEN_REFRESH = "token_refresh"

    # Authorization Events
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PERMISSION_ESCALATION = "permission_escalation"
    ROLE_CHANGE = "role_change"

    # Input Validation Events
    VALIDATION_FAILURE = "validation_failure"
    XSS_ATTEMPT = "xss_attempt"
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    COMMAND_INJECTION_ATTEMPT = "command_injection_attempt"
    PATH_TRAVERSAL_ATTEMPT = "path_traversal_attempt"

    # Rate Limiting Events
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    BOT_DETECTION = "bot_detection"
    DDOS_DETECTED = "ddos_detected"

    # Data Protection Events
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_DELETION = "data_deletion"
    DATA_EXPORT = "data_export"
    CONSENT_GIVEN = "consent_given"
    CONSENT_WITHDRAWN = "consent_withdrawn"

    # System Events
    CONFIGURATION_CHANGE = "configuration_change"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    SECURITY_POLICY_VIOLATION = "security_policy_violation"
    INTRUSION_DETECTED = "intrusion_detected"
    MALWARE_DETECTED = "malware_detected"

    # API Security Events
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    API_ABUSE = "api_abuse"
    INVALID_TOKEN = "invalid_token"

    # Compliance Events
    GDPR_REQUEST = "gdpr_request"
    DATA_BREACH = "data_breach"
    AUDIT_LOG_ACCESS = "audit_log_access"


class SecurityEventSeverity(str, Enum):
    """STANDARD SECURITY EVENT SEVERITY"""

    INFO = "info"  # Informational events
    LOW = "low"  # Low risk events
    WARNING = "warning"  # Elevated but non-critical events
    MEDIUM = "medium"  # Medium risk events
    HIGH = "high"  # High risk events
    CRITICAL = "critical"  # Critical security events
    EMERGENCY = "emergency"  # Emergency response required


class ThreatLevel(str, Enum):
    """STANDARD THREAT LEVELS"""

    BENIGN = "benign"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """STANDARD SECURITY EVENT"""

    event_id: str
    event_type: SecurityEventType
    severity: SecurityEventSeverity
    timestamp: datetime
    source_ip: str
    user_id: Optional[str] = None
    username: Optional[str] = None
    user_agent: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    message: str = ""
    details: Dict[str, Any] = None
    threat_level: ThreatLevel = ThreatLevel.BENIGN
    geolocation: Optional[Dict[str, str]] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    tags: List[str] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.tags is None:
            self.tags = []

    def to_dict(self) -> Dict[str, Any]:
        """STANDARD EVENT SERIALIZATION"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    def to_json(self) -> str:
        """STANDARD JSON SERIALIZATION"""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class SecurityAuditLog:
    """STANDARD SECURITY AUDIT LOG"""

    log_id: str
    user_id: str
    action: str
    resource: str
    timestamp: datetime
    ip_address: str
    user_agent: str
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class ThreatIntelligence:
    """STANDARD THREAT INTELLIGENCE"""

    indicator: str
    indicator_type: str  # ip, domain, hash, etc.
    threat_type: str
    confidence: float  # 0.0 to 1.0
    source: str
    first_seen: datetime
    last_seen: datetime
    tags: List[str] = None


class SecurityLogger:
    """STANDARD SECURITY LOGGER ENHANCED BY THE SYSTEM"""

    def __init__(self, database_path: str, log_directory: str = "data/security_logs"):
        self.database_path = database_path
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(parents=True, exist_ok=True)

        self._security_file_handler: Optional[logging.Handler] = None
        self._audit_file_handler: Optional[logging.Handler] = None

        # Threat intelligence
        self.threat_indicators: Dict[str, ThreatIntelligence] = {}
        self.suspicious_ips: Dict[str, Dict[str, Any]] = {}

        # Real-time monitoring
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.failed_attempts: Dict[str, List[float]] = {}

        # Background tasks
        self._log_rotation_task: Optional[asyncio.Task] = None
        self._threat_analysis_task: Optional[asyncio.Task] = None

        self._setup_logging()
        self._start_background_tasks()

    def _setup_logging(self):
        """STANDARD LOGGING SETUP"""
        # Configure security-specific logger
        self.security_logger = logging.getLogger("security")
        self.security_logger.setLevel(logging.INFO)

        # File handler for security events
        security_log_file = self.log_directory / "security.log"
        file_handler = logging.FileHandler(security_log_file)
        file_handler.setLevel(logging.INFO)

        # JSON formatter for structured logging
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": %(message)s}'
        )
        file_handler.setFormatter(formatter)

        self._security_file_handler = file_handler
        self.security_logger.addHandler(file_handler)

        # Audit log file
        self.audit_logger = logging.getLogger("audit")
        audit_log_file = self.log_directory / "audit.log"
        audit_handler = logging.FileHandler(audit_log_file)
        audit_handler.setFormatter(formatter)
        self._audit_file_handler = audit_handler
        self.audit_logger.addHandler(audit_handler)

    def _start_background_tasks(self):
        """STANDARD BACKGROUND TASKS"""
        try:
            loop = asyncio.get_event_loop()
            self._log_rotation_task = loop.create_task(self._log_rotation_loop())
            self._threat_analysis_task = loop.create_task(self._threat_analysis_loop())
        except RuntimeError:
            # No event loop running yet
            pass

    async def initialize_database(self):
        """STANDARD DATABASE INITIALIZATION"""
        async with aiosqlite.connect(self.database_path) as conn:
            await conn.execute("PRAGMA foreign_keys = ON")
            await conn.execute("PRAGMA journal_mode = WAL")
            await conn.execute("PRAGMA synchronous = NORMAL")

            # Security events table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS security_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    source_ip TEXT NOT NULL,
                    user_id TEXT NULL,
                    username TEXT NULL,
                    user_agent TEXT NULL,
                    endpoint TEXT NULL,
                    method TEXT NULL,
                    status_code INTEGER NULL,
                    message TEXT NOT NULL,
                    details TEXT NULL,
                    threat_level TEXT NOT NULL,
                    geolocation TEXT NULL,
                    session_id TEXT NULL,
                    request_id TEXT NULL,
                    tags TEXT NULL
                )
            """
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_security_events_timestamp ON security_events(timestamp)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_security_events_type ON security_events(event_type)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_security_events_severity ON security_events(severity)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_security_events_source_ip ON security_events(source_ip)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_security_events_user_id ON security_events(user_id)"
            )

            # Audit logs table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    log_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    ip_address TEXT NOT NULL,
                    user_agent TEXT NOT NULL,
                    before_state TEXT NULL,
                    after_state TEXT NULL,
                    success BOOLEAN NOT NULL,
                    error_message TEXT NULL
                )
            """
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource)"
            )

            # Threat intelligence table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS threat_intelligence (
                    indicator TEXT PRIMARY KEY,
                    indicator_type TEXT NOT NULL,
                    threat_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    source TEXT NOT NULL,
                    first_seen TIMESTAMP NOT NULL,
                    last_seen TIMESTAMP NOT NULL,
                    tags TEXT NULL
                )
            """
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_threat_intel_type ON threat_intelligence(indicator_type)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_threat_intel_threat ON threat_intelligence(threat_type)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_threat_intel_confidence ON threat_intelligence(confidence)"
            )

            # Session tracking table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS security_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NULL,
                    ip_address TEXT NOT NULL,
                    user_agent TEXT NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    last_activity TIMESTAMP NOT NULL,
                    end_time TIMESTAMP NULL,
                    status TEXT NOT NULL,
                    risk_score REAL DEFAULT 0.0,
                    events_count INTEGER DEFAULT 0
                )
            """
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_security_sessions_user_id ON security_sessions(user_id)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_security_sessions_ip ON security_sessions(ip_address)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_security_sessions_start ON security_sessions(start_time)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_security_sessions_risk ON security_sessions(risk_score)"
            )

            await conn.commit()
            logger.info("SECURITY LOGGING DATABASE INITIALIZED")

    async def log_security_event(self, event: SecurityEvent):
        """STANDARD SECURITY EVENT LOGGING"""
        try:
            # Store in database
            async with aiosqlite.connect(self.database_path) as conn:
                await conn.execute(
                    """
                    INSERT INTO security_events (
                        event_id, event_type, severity, timestamp, source_ip,
                        user_id, username, user_agent, endpoint, method,
                        status_code, message, details, threat_level,
                        geolocation, session_id, request_id, tags
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        event.event_id,
                        event.event_type.value,
                        event.severity.value,
                        event.timestamp,
                        event.source_ip,
                        event.user_id,
                        event.username,
                        event.user_agent,
                        event.endpoint,
                        event.method,
                        event.status_code,
                        event.message,
                        json.dumps(event.details) if event.details else None,
                        event.threat_level.value,
                        json.dumps(event.geolocation) if event.geolocation else None,
                        event.session_id,
                        event.request_id,
                        json.dumps(event.tags) if event.tags else None,
                    ),
                )
                await conn.commit()

            # Log to file
            self.security_logger.info(event.to_json())

            # Real-time threat analysis
            await self._analyze_threat(event)

            # Update session tracking
            await self._update_session_tracking(event)

        except Exception as e:
            logger.error(f"SECURITY EVENT LOGGING ERROR: {e}")

    async def log_audit_event(self, audit_log: SecurityAuditLog):
        """STANDARD AUDIT EVENT LOGGING"""
        try:
            async with aiosqlite.connect(self.database_path) as conn:
                await conn.execute(
                    """
                    INSERT INTO audit_logs (
                        log_id, user_id, action, resource, timestamp,
                        ip_address, user_agent, before_state, after_state,
                        success, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        audit_log.log_id,
                        audit_log.user_id,
                        audit_log.action,
                        audit_log.resource,
                        audit_log.timestamp,
                        audit_log.ip_address,
                        audit_log.user_agent,
                        (
                            json.dumps(audit_log.before_state)
                            if audit_log.before_state
                            else None
                        ),
                        (
                            json.dumps(audit_log.after_state)
                            if audit_log.after_state
                            else None
                        ),
                        audit_log.success,
                        audit_log.error_message,
                    ),
                )
                await conn.commit()

            # Log to audit file
            self.audit_logger.info(json.dumps(asdict(audit_log), default=str))

        except Exception as e:
            logger.error(f"AUDIT EVENT LOGGING ERROR: {e}")

    async def _analyze_threat(self, event: SecurityEvent):
        """STANDARD THREAT ANALYSIS"""
        try:
            risk_score = 0.0

            # Analyze event type risk
            high_risk_events = [
                SecurityEventType.LOGIN_FAILURE,
                SecurityEventType.ACCESS_DENIED,
                SecurityEventType.SQL_INJECTION_ATTEMPT,
                SecurityEventType.XSS_ATTEMPT,
                SecurityEventType.COMMAND_INJECTION_ATTEMPT,
                SecurityEventType.RATE_LIMIT_EXCEEDED,
                SecurityEventType.INTRUSION_DETECTED,
            ]

            if event.event_type in high_risk_events:
                risk_score += 0.3

            # Analyze IP reputation
            if event.source_ip in self.threat_indicators:
                indicator = self.threat_indicators[event.source_ip]
                risk_score += indicator.confidence * 0.4

            # Analyze failed attempts pattern
            if event.event_type == SecurityEventType.LOGIN_FAILURE:
                if event.source_ip not in self.failed_attempts:
                    self.failed_attempts[event.source_ip] = []

                self.failed_attempts[event.source_ip].append(time.time())

                # Check for brute force pattern
                recent_failures = [
                    t
                    for t in self.failed_attempts[event.source_ip]
                    if t > time.time() - 3600  # Last hour
                ]

                if len(recent_failures) > 10:
                    risk_score += 0.5
                    await self._trigger_security_alert(
                        event, "Brute force attack detected", risk_score
                    )

            # Analyze geographic anomalies (placeholder)
            # In production, you would integrate with GeoIP services

            # Update threat level based on risk score
            if risk_score > 0.8:
                event.threat_level = ThreatLevel.CRITICAL
            elif risk_score > 0.6:
                event.threat_level = ThreatLevel.MALICIOUS
            elif risk_score > 0.3:
                event.threat_level = ThreatLevel.SUSPICIOUS

            # Auto-block high-risk IPs
            if risk_score > 0.7:
                await self._auto_block_ip(event.source_ip, risk_score)

        except Exception as e:
            logger.error(f"THREAT ANALYSIS ERROR: {e}")

    async def _trigger_security_alert(
        self, event: SecurityEvent, alert_message: str, risk_score: float
    ):
        """STANDARD SECURITY ALERT TRIGGERING"""
        alert_event = SecurityEvent(
            event_id=f"alert_{int(time.time())}_{hash(alert_message) % 10000}",
            event_type=SecurityEventType.INTRUSION_DETECTED,
            severity=SecurityEventSeverity.CRITICAL,
            timestamp=datetime.now(timezone.utc),
            source_ip=event.source_ip,
            user_id=event.user_id,
            message=alert_message,
            details={
                "triggering_event_id": event.event_id,
                "risk_score": risk_score,
                "automated_response": True,
            },
            threat_level=ThreatLevel.CRITICAL,
        )

        await self.log_security_event(alert_event)

        logger.critical(
            f"SECURITY ALERT: {alert_message} | "
            f"IP: {event.source_ip} | "
            f"Risk Score: {risk_score:.2f}"
        )

    async def _auto_block_ip(self, ip_address: str, risk_score: float):
        """STANDARD AUTOMATIC IP BLOCKING"""
        # In production, this would integrate with firewall/WAF
        self.suspicious_ips[ip_address] = {
            "blocked_at": time.time(),
            "risk_score": risk_score,
            "auto_blocked": True,
            "block_duration": 3600,  # 1 hour
        }

        logger.warning(f"IP AUTO-BLOCKED: {ip_address} | Risk Score: {risk_score:.2f}")

    async def _update_session_tracking(self, event: SecurityEvent):
        """STANDARD SESSION TRACKING UPDATE"""
        if not event.session_id:
            return

        try:
            async with aiosqlite.connect(self.database_path) as conn:
                # Check if session exists
                cursor = await conn.execute(
                    """
                    SELECT events_count, risk_score FROM security_sessions
                    WHERE session_id = ?
                """,
                    (event.session_id,),
                )
                row = await cursor.fetchone()

                if row:
                    # Update existing session
                    events_count, current_risk = row
                    new_risk = (
                        min(current_risk + 0.1, 1.0)
                        if event.severity
                        in [SecurityEventSeverity.HIGH, SecurityEventSeverity.CRITICAL]
                        else current_risk
                    )

                    await conn.execute(
                        """
                        UPDATE security_sessions
                        SET last_activity = ?, events_count = ?, risk_score = ?
                        WHERE session_id = ?
                    """,
                        (event.timestamp, events_count + 1, new_risk, event.session_id),
                    )
                else:
                    # Create new session
                    await conn.execute(
                        """
                        INSERT INTO security_sessions (
                            session_id, user_id, ip_address, user_agent,
                            start_time, last_activity, status, events_count
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            event.session_id,
                            event.user_id,
                            event.source_ip,
                            event.user_agent,
                            event.timestamp,
                            event.timestamp,
                            "active",
                            1,
                        ),
                    )

                await conn.commit()

        except Exception as e:
            logger.error(f"SESSION TRACKING UPDATE ERROR: {e}")

    async def _log_rotation_loop(self):
        """STANDARD LOG ROTATION LOOP"""
        while True:
            try:
                await asyncio.sleep(86400)  # Daily rotation
                await self._rotate_logs()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"LOG ROTATION ERROR: {e}")

    async def _threat_analysis_loop(self):
        """STANDARD THREAT ANALYSIS LOOP"""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                await self._update_threat_intelligence()
                await self._clean_old_data()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"THREAT ANALYSIS LOOP ERROR: {e}")

    async def _rotate_logs(self):
        """STANDARD LOG ROTATION"""
        try:
            current_date = datetime.now().strftime("%Y%m%d")

            # Rotate security log
            security_log = self.log_directory / "security.log"
            if security_log.exists():
                rotated_log = self.log_directory / f"security_{current_date}.log"

                # Compress old log
                with open(security_log, "rb") as f_in:
                    with gzip.open(f"{rotated_log}.gz", "wb") as f_out:
                        f_out.writelines(f_in)

                # Clear current log
                open(security_log, "w").close()

            # Rotate audit log
            audit_log = self.log_directory / "audit.log"
            if audit_log.exists():
                rotated_log = self.log_directory / f"audit_{current_date}.log"

                with open(audit_log, "rb") as f_in:
                    with gzip.open(f"{rotated_log}.gz", "wb") as f_out:
                        f_out.writelines(f_in)

                open(audit_log, "w").close()

            logger.info("LOG ROTATION COMPLETED")

        except Exception as e:
            logger.error(f"LOG ROTATION ERROR: {e}")

    async def _update_threat_intelligence(self):
        """STANDARD THREAT INTELLIGENCE UPDATE"""
        # This would integrate with external threat feeds
        # For now, it's a placeholder
        pass

    async def _clean_old_data(self):
        """STANDARD OLD DATA CLEANUP"""
        try:
            # Clean events older than 90 days
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)

            async with aiosqlite.connect(self.database_path) as conn:
                # Clean old security events
                await conn.execute(
                    """
                    DELETE FROM security_events WHERE timestamp < ?
                """,
                    (cutoff_date,),
                )

                # Clean old audit logs
                await conn.execute(
                    """
                    DELETE FROM audit_logs WHERE timestamp < ?
                """,
                    (cutoff_date,),
                )

                # Clean old sessions
                await conn.execute(
                    """
                    DELETE FROM security_sessions WHERE start_time < ?
                """,
                    (cutoff_date,),
                )

                await conn.commit()

            # Clean old compressed log files (keep 1 year)
            old_date = datetime.now() - timedelta(days=365)
            old_date_str = old_date.strftime("%Y%m%d")

            for log_file in self.log_directory.glob("*.gz"):
                if log_file.stem.split("_")[-1] < old_date_str:
                    log_file.unlink()

        except Exception as e:
            logger.error(f"OLD DATA CLEANUP ERROR: {e}")

    async def get_security_events(
        self,
        limit: int = 100,
        event_type: Optional[SecurityEventType] = None,
        severity: Optional[SecurityEventSeverity] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        source_ip: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """STANDARD SECURITY EVENTS RETRIEVAL"""
        try:
            query = "SELECT * FROM security_events WHERE 1=1"
            params = []

            if event_type:
                query += " AND event_type = ?"
                params.append(event_type.value)

            if severity:
                query += " AND severity = ?"
                params.append(severity.value)

            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)

            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)

            if source_ip:
                query += " AND source_ip = ?"
                params.append(source_ip)

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            async with aiosqlite.connect(self.database_path) as conn:
                cursor = await conn.execute(query, params)
                rows = await cursor.fetchall()

                # Convert to dictionaries
                columns = [description[0] for description in cursor.description]
                events = []

                for row in rows:
                    event_dict = dict(zip(columns, row))

                    # Parse JSON fields
                    if event_dict["details"]:
                        event_dict["details"] = json.loads(event_dict["details"])
                    if event_dict["geolocation"]:
                        event_dict["geolocation"] = json.loads(
                            event_dict["geolocation"]
                        )
                    if event_dict["tags"]:
                        event_dict["tags"] = json.loads(event_dict["tags"])

                    events.append(event_dict)

                return events

        except Exception as e:
            logger.error(f"SECURITY EVENTS RETRIEVAL ERROR: {e}")
            return []

    async def get_security_statistics(
        self, time_range_hours: int = 24
    ) -> Dict[str, Any]:
        """STANDARD SECURITY STATISTICS"""
        try:
            start_time = datetime.now(timezone.utc) - timedelta(hours=time_range_hours)

            async with aiosqlite.connect(self.database_path) as conn:
                # Event counts by type
                cursor = await conn.execute(
                    """
                    SELECT event_type, COUNT(*) as count
                    FROM security_events
                    WHERE timestamp >= ?
                    GROUP BY event_type
                """,
                    (start_time,),
                )
                event_counts = {row[0]: row[1] for row in await cursor.fetchall()}

                # Events by severity
                cursor = await conn.execute(
                    """
                    SELECT severity, COUNT(*) as count
                    FROM security_events
                    WHERE timestamp >= ?
                    GROUP BY severity
                """,
                    (start_time,),
                )
                severity_counts = {row[0]: row[1] for row in await cursor.fetchall()}

                # Top source IPs
                cursor = await conn.execute(
                    """
                    SELECT source_ip, COUNT(*) as count
                    FROM security_events
                    WHERE timestamp >= ?
                    GROUP BY source_ip
                    ORDER BY count DESC
                    LIMIT 10
                """,
                    (start_time,),
                )
                top_ips = {row[0]: row[1] for row in await cursor.fetchall()}

                # Threat levels
                cursor = await conn.execute(
                    """
                    SELECT threat_level, COUNT(*) as count
                    FROM security_events
                    WHERE timestamp >= ?
                    GROUP BY threat_level
                """,
                    (start_time,),
                )
                threat_counts = {row[0]: row[1] for row in await cursor.fetchall()}

                return {
                    "time_range_hours": time_range_hours,
                    "event_counts": event_counts,
                    "severity_counts": severity_counts,
                    "top_source_ips": top_ips,
                    "threat_level_counts": threat_counts,
                    "total_events": sum(event_counts.values()),
                    "critical_events": severity_counts.get("critical", 0),
                    "blocked_ips": len(self.suspicious_ips),
                    "active_sessions": len(self.active_sessions),
                }

        except Exception as e:
            logger.error(f"SECURITY STATISTICS ERROR: {e}")
            return {}

    async def shutdown(self):
        """STANDARD SECURITY LOGGER SHUTDOWN"""
        try:
            # Cancel background tasks
            if self._log_rotation_task:
                self._log_rotation_task.cancel()
                await asyncio.gather(self._log_rotation_task, return_exceptions=True)

            if self._threat_analysis_task:
                self._threat_analysis_task.cancel()
                await asyncio.gather(self._threat_analysis_task, return_exceptions=True)

            # Final log rotation
            await self._rotate_logs()

            logger.info("SECURITY LOGGER SHUTDOWN COMPLETE")

        except Exception as e:
            logger.error(f"SECURITY LOGGER SHUTDOWN ERROR: {e}")
        finally:
            for handler, target_logger in (
                (self._security_file_handler, getattr(self, "security_logger", None)),
                (self._audit_file_handler, getattr(self, "audit_logger", None)),
            ):
                if handler is None or target_logger is None:
                    continue
                try:
                    target_logger.removeHandler(handler)
                finally:
                    try:
                        handler.close()
                    except Exception:
                        pass

            self._security_file_handler = None
            self._audit_file_handler = None


# GLOBAL SECURITY LOGGER INSTANCE
security_logger: Optional[SecurityLogger] = None


def get_security_logger() -> SecurityLogger:
    """STANDARD SECURITY LOGGER GETTER"""
    global security_logger
    if security_logger is None:
        raise RuntimeError("Security logger not initialized")
    return security_logger


def initialize_security_logger(
    database_path: str, log_directory: str = "data/security_logs"
):
    """STANDARD SECURITY LOGGER INITIALIZATION"""
    global security_logger
    security_logger = SecurityLogger(database_path, log_directory)
    return security_logger


__all__ = [
    "SecurityEventType",
    "SecurityEventSeverity",
    "ThreatLevel",
    "SecurityEvent",
    "SecurityAuditLog",
    "ThreatIntelligence",
    "SecurityLogger",
    "get_security_logger",
    "initialize_security_logger",
]
