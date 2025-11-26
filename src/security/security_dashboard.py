#!/usr/bin/env python3
"""
ENTERPRISE SECURITY MONITORING DASHBOARD
========================================

Real-time security monitoring and compliance dashboard providing:
- Real-time threat detection alerts
- Security metrics visualization
- Compliance framework monitoring
- Incident response management
- Audit trail analysis
- Risk assessment reporting

Architecture: Real-time Analytics + Compliance Monitoring
Security Level: Enterprise SOC (Security Operations Center)
Author: Security Operations Team
System monitors all security events 📊🛡️
"""

import asyncio
import json
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    import aioredis

    AIOREDIS_AVAILABLE = True
except ImportError:
    AIOREDIS_AVAILABLE = False
    aioredis = None

try:
    import aiosqlite

    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False
    aiosqlite = None

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from .enterprise_security_manager import (
    ComplianceFramework,
    get_enterprise_security_manager,
)

# Enhanced logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Security alert severity levels"""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(str, Enum):
    """Security incident status"""

    OPEN = "open"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass
class SecurityAlert:
    """Real-time security alert"""

    id: str
    timestamp: datetime
    severity: AlertSeverity
    title: str
    description: str
    source_ip: str
    user_id: Optional[str]
    threat_indicators: List[str]
    automated_response: List[str]
    incident_id: Optional[str] = None
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    resolved: bool = False


@dataclass
class SecurityIncident:
    """Security incident management"""

    id: str
    title: str
    description: str
    severity: AlertSeverity
    status: IncidentStatus
    created_at: datetime
    created_by: str
    assigned_to: Optional[str] = None
    related_alerts: List[str] = field(default_factory=list)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    resolution_notes: str = ""
    resolved_at: Optional[datetime] = None


@dataclass
class ComplianceReport:
    """Compliance framework report"""

    framework: ComplianceFramework
    report_date: datetime
    compliance_score: float  # 0.0 to 100.0
    passed_controls: int
    failed_controls: int
    findings: List[Dict[str, Any]]
    recommendations: List[str]


class SecurityMetrics(BaseModel):
    """Real-time security metrics"""

    timestamp: datetime
    total_requests: int
    blocked_requests: int
    threat_events: int
    critical_alerts: int
    high_alerts: int
    medium_alerts: int
    low_alerts: int
    active_incidents: int
    compliance_score: float


class SecurityDashboard:
    """Enterprise Security Monitoring Dashboard"""

    def __init__(self, database_path: str, redis_url: str = "redis://localhost:6379"):
        self.database_path = database_path
        self.redis_url = redis_url

        # Dashboard state
        self.connected_clients: List[WebSocket] = []
        self.alerts_queue = deque(maxlen=1000)
        self.incidents: Dict[str, SecurityIncident] = {}
        self.metrics_history = deque(maxlen=1440)  # 24 hours of minute data

        # Redis connection
        self.redis_client = None

        # Real-time metrics
        self.current_metrics = SecurityMetrics(
            timestamp=datetime.now(timezone.utc),
            total_requests=0,
            blocked_requests=0,
            threat_events=0,
            critical_alerts=0,
            high_alerts=0,
            medium_alerts=0,
            low_alerts=0,
            active_incidents=0,
            compliance_score=0.0,
        )

    async def initialize(self):
        """Initialize security dashboard"""
        try:
            # Connect to Redis
            self.redis_client = aioredis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("✅ Security Dashboard Redis connection established")

            # Initialize database
            await self._initialize_dashboard_database()

            # Load existing incidents
            await self._load_incidents()

            # Start background tasks
            asyncio.create_task(self._security_alert_listener())
            asyncio.create_task(self._metrics_collector())
            asyncio.create_task(self._compliance_monitor())

            logger.info("🚀 SECURITY DASHBOARD INITIALIZED")

        except Exception as e:
            logger.error(f"❌ Failed to initialize Security Dashboard: {e}")
            raise

    async def _initialize_dashboard_database(self):
        """Initialize dashboard-specific database tables"""
        async with aiosqlite.connect(self.database_path) as conn:
            # Security incidents table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS security_incidents (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT NOT NULL,
                    assigned_to TEXT,
                    related_alerts TEXT, -- JSON array
                    timeline TEXT, -- JSON array
                    resolution_notes TEXT,
                    resolved_at TIMESTAMP
                )
            """
            )

            # Security metrics snapshots
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS security_metrics_snapshots (
                    id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metrics_data TEXT NOT NULL, -- JSON object
                    report_type TEXT NOT NULL, -- 'hourly', 'daily', 'weekly'
                    compliance_data TEXT -- JSON object
                )
            """
            )

            # Compliance reports
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS compliance_reports (
                    id TEXT PRIMARY KEY,
                    framework TEXT NOT NULL,
                    report_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    compliance_score REAL NOT NULL,
                    passed_controls INTEGER NOT NULL,
                    failed_controls INTEGER NOT NULL,
                    findings TEXT NOT NULL, -- JSON array
                    recommendations TEXT NOT NULL, -- JSON array
                    generated_by TEXT NOT NULL
                )
            """
            )

            await conn.commit()
            logger.info("📊 Security Dashboard database schema initialized")

    async def _security_alert_listener(self):
        """Listen for real-time security alerts from Redis"""
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe("security_alerts")

        logger.info("👂 Security alert listener started")

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        alert_data = json.loads(message["data"])
                        await self._process_security_alert(alert_data)
                    except Exception as e:
                        logger.error(f"Error processing security alert: {e}")
        except Exception as e:
            logger.error(f"Security alert listener error: {e}")
        finally:
            await pubsub.unsubscribe("security_alerts")

    async def _process_security_alert(self, alert_data: Dict[str, Any]):
        """Process incoming security alert"""
        try:
            severity = AlertSeverity(alert_data.get("severity", "medium"))

            alert = SecurityAlert(
                id=alert_data["event_id"],
                timestamp=datetime.fromisoformat(alert_data["timestamp"]),
                severity=severity,
                title=f"Security Event: {alert_data.get('event_type', 'Unknown')}",
                description=f"Threat detected from {alert_data['source_ip']}",
                source_ip=alert_data["source_ip"],
                user_id=alert_data.get("user_id"),
                threat_indicators=alert_data.get("threat_indicators", []),
                automated_response=alert_data.get("automated_response", []),
            )

            # Add to alerts queue
            self.alerts_queue.append(alert)

            # Update metrics
            if severity == AlertSeverity.CRITICAL:
                self.current_metrics.critical_alerts += 1
            elif severity == AlertSeverity.HIGH:
                self.current_metrics.high_alerts += 1
            elif severity == AlertSeverity.MEDIUM:
                self.current_metrics.medium_alerts += 1
            else:
                self.current_metrics.low_alerts += 1

            # Create incident for high/critical alerts
            if severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
                await self._create_incident_from_alert(alert)

            # Broadcast to connected WebSocket clients
            await self._broadcast_alert(alert)

            logger.info(f"🚨 Processed {severity.upper()} alert: {alert.title}")

        except Exception as e:
            logger.error(f"Error processing security alert: {e}")

    async def _create_incident_from_alert(self, alert: SecurityAlert):
        """Create security incident from high-severity alert"""
        try:
            incident_id = f"INC_{int(datetime.now().timestamp())}"

            incident = SecurityIncident(
                id=incident_id,
                title=f"Security Incident: {alert.title}",
                description=f"Automatic incident created from {alert.severity.upper()} alert",
                severity=alert.severity,
                status=IncidentStatus.OPEN,
                created_at=alert.timestamp,
                created_by="system_auto_escalation",
                related_alerts=[alert.id],
            )

            # Add initial timeline entry
            incident.timeline.append(
                {
                    "timestamp": alert.timestamp.isoformat(),
                    "action": "incident_created",
                    "description": f"Incident auto-created from alert {alert.id}",
                    "user": "system",
                }
            )

            self.incidents[incident_id] = incident
            alert.incident_id = incident_id

            # Save to database
            await self._save_incident(incident)

            # Update active incidents count
            self.current_metrics.active_incidents = len(
                [
                    inc
                    for inc in self.incidents.values()
                    if inc.status
                    not in [IncidentStatus.RESOLVED, IncidentStatus.CLOSED]
                ]
            )

            logger.info(f"📋 Created incident {incident_id} from alert {alert.id}")

        except Exception as e:
            logger.error(f"Error creating incident from alert: {e}")

    async def _save_incident(self, incident: SecurityIncident):
        """Save incident to database"""
        async with aiosqlite.connect(self.database_path) as conn:
            await conn.execute(
                """
                INSERT OR REPLACE INTO security_incidents 
                (id, title, description, severity, status, created_at, created_by,
                 assigned_to, related_alerts, timeline, resolution_notes, resolved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    incident.id,
                    incident.title,
                    incident.description,
                    incident.severity.value,
                    incident.status.value,
                    incident.created_at,
                    incident.created_by,
                    incident.assigned_to,
                    json.dumps(incident.related_alerts),
                    json.dumps(incident.timeline, default=str),
                    incident.resolution_notes,
                    incident.resolved_at,
                ),
            )
            await conn.commit()

    async def _load_incidents(self):
        """Load existing incidents from database"""
        try:
            async with aiosqlite.connect(self.database_path) as conn:
                cursor = await conn.execute(
                    """
                    SELECT id, title, description, severity, status, created_at,
                           created_by, assigned_to, related_alerts, timeline,
                           resolution_notes, resolved_at
                    FROM security_incidents
                    WHERE created_at > ?
                """,
                    (datetime.now(timezone.utc) - timedelta(days=30),),
                )

                rows = await cursor.fetchall()
                for row in rows:
                    incident = SecurityIncident(
                        id=row[0],
                        title=row[1],
                        description=row[2],
                        severity=AlertSeverity(row[3]),
                        status=IncidentStatus(row[4]),
                        created_at=datetime.fromisoformat(row[5]),
                        created_by=row[6],
                        assigned_to=row[7],
                        related_alerts=json.loads(row[8] or "[]"),
                        timeline=json.loads(row[9] or "[]"),
                        resolution_notes=row[10] or "",
                        resolved_at=(
                            datetime.fromisoformat(row[11]) if row[11] else None
                        ),
                    )
                    self.incidents[incident.id] = incident

                logger.info(f"📊 Loaded {len(self.incidents)} security incidents")

        except Exception as e:
            logger.error(f"Error loading incidents: {e}")

    async def _metrics_collector(self):
        """Collect security metrics periodically"""
        while True:
            try:
                await asyncio.sleep(60)  # Collect every minute

                # Get metrics from security manager
                security_manager = get_enterprise_security_manager()
                metrics_data = await security_manager.get_security_metrics()

                # Update current metrics
                self.current_metrics.timestamp = datetime.now(timezone.utc)
                self.current_metrics.threat_events = sum(
                    metrics_data.get("threat_events_24h", {}).values()
                )

                # Add to history
                self.metrics_history.append(self.current_metrics.copy())

                # Broadcast to clients
                await self._broadcast_metrics()

            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(60)

    async def _compliance_monitor(self):
        """Monitor compliance frameworks periodically"""
        while True:
            try:
                await asyncio.sleep(3600)  # Check hourly

                # Generate compliance reports
                for framework in ComplianceFramework:
                    report = await self._generate_compliance_report(framework)
                    if report:
                        await self._save_compliance_report(report)

            except Exception as e:
                logger.error(f"Error in compliance monitoring: {e}")
                await asyncio.sleep(3600)

    async def _generate_compliance_report(
        self, framework: ComplianceFramework
    ) -> Optional[ComplianceReport]:
        """Generate compliance report for framework"""
        try:
            # This would integrate with actual compliance checking logic
            # For now, we'll simulate basic compliance checking

            findings = []
            recommendations = []
            passed_controls = 0
            failed_controls = 0

            if framework == ComplianceFramework.GDPR:
                # GDPR compliance checks
                controls = [
                    ("Data encryption at rest", True),
                    ("Data encryption in transit", True),
                    ("User consent management", True),
                    ("Data retention policies", False),
                    ("Right to be forgotten implementation", False),
                    ("Data processing logging", True),
                    ("Privacy by design", True),
                    ("Data breach notification", True),
                ]

                for control, status in controls:
                    if status:
                        passed_controls += 1
                    else:
                        failed_controls += 1
                        findings.append(
                            {
                                "control": control,
                                "status": "failed",
                                "severity": "medium",
                                "description": f"Control '{control}' is not properly implemented",
                            }
                        )
                        recommendations.append(
                            f"Implement {control} to meet GDPR requirements"
                        )

            elif framework == ComplianceFramework.SOC2:
                # SOC2 Type II compliance checks
                controls = [
                    ("Access controls", True),
                    ("Encryption controls", True),
                    ("Network security", True),
                    ("Monitoring and logging", True),
                    ("Incident response", True),
                    ("Change management", False),
                    ("Vendor management", False),
                    ("Business continuity", False),
                ]

                for control, status in controls:
                    if status:
                        passed_controls += 1
                    else:
                        failed_controls += 1
                        findings.append(
                            {
                                "control": control,
                                "status": "failed",
                                "severity": "high",
                                "description": f"SOC2 control '{control}' needs attention",
                            }
                        )
                        recommendations.append(f"Address {control} for SOC2 compliance")

            # Calculate compliance score
            total_controls = passed_controls + failed_controls
            compliance_score = (
                (passed_controls / total_controls * 100) if total_controls > 0 else 0
            )

            return ComplianceReport(
                framework=framework,
                report_date=datetime.now(timezone.utc),
                compliance_score=compliance_score,
                passed_controls=passed_controls,
                failed_controls=failed_controls,
                findings=findings,
                recommendations=recommendations,
            )

        except Exception as e:
            logger.error(f"Error generating compliance report for {framework}: {e}")
            return None

    async def _save_compliance_report(self, report: ComplianceReport):
        """Save compliance report to database"""
        try:
            async with aiosqlite.connect(self.database_path) as conn:
                await conn.execute(
                    """
                    INSERT INTO compliance_reports 
                    (id, framework, report_date, compliance_score, passed_controls,
                     failed_controls, findings, recommendations, generated_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        f"{report.framework.value}_{int(report.report_date.timestamp())}",
                        report.framework.value,
                        report.report_date,
                        report.compliance_score,
                        report.passed_controls,
                        report.failed_controls,
                        json.dumps(report.findings),
                        json.dumps(report.recommendations),
                        "system_auto_compliance",
                    ),
                )
                await conn.commit()

            # Update current metrics compliance score
            self.current_metrics.compliance_score = report.compliance_score

        except Exception as e:
            logger.error(f"Error saving compliance report: {e}")

    async def _broadcast_alert(self, alert: SecurityAlert):
        """Broadcast alert to all connected WebSocket clients"""
        if not self.connected_clients:
            return

        message = {
            "type": "security_alert",
            "data": {
                "id": alert.id,
                "timestamp": alert.timestamp.isoformat(),
                "severity": alert.severity.value,
                "title": alert.title,
                "description": alert.description,
                "source_ip": alert.source_ip,
                "threat_indicators": alert.threat_indicators,
                "incident_id": alert.incident_id,
            },
        }

        # Send to all connected clients
        disconnected_clients = []
        for client in self.connected_clients:
            try:
                await client.send_text(json.dumps(message))
            except Exception:
                disconnected_clients.append(client)

        # Remove disconnected clients
        for client in disconnected_clients:
            self.connected_clients.remove(client)

    async def _broadcast_metrics(self):
        """Broadcast metrics to all connected WebSocket clients"""
        if not self.connected_clients:
            return

        message = {
            "type": "security_metrics",
            "data": {
                "timestamp": self.current_metrics.timestamp.isoformat(),
                "total_requests": self.current_metrics.total_requests,
                "blocked_requests": self.current_metrics.blocked_requests,
                "threat_events": self.current_metrics.threat_events,
                "critical_alerts": self.current_metrics.critical_alerts,
                "high_alerts": self.current_metrics.high_alerts,
                "medium_alerts": self.current_metrics.medium_alerts,
                "low_alerts": self.current_metrics.low_alerts,
                "active_incidents": self.current_metrics.active_incidents,
                "compliance_score": self.current_metrics.compliance_score,
            },
        }

        # Send to all connected clients
        disconnected_clients = []
        for client in self.connected_clients:
            try:
                await client.send_text(json.dumps(message))
            except Exception:
                disconnected_clients.append(client)

        # Remove disconnected clients
        for client in disconnected_clients:
            self.connected_clients.remove(client)

    # WebSocket endpoints
    async def websocket_endpoint(self, websocket: WebSocket):
        """WebSocket endpoint for real-time dashboard updates"""
        await websocket.accept()
        self.connected_clients.append(websocket)

        try:
            # Send initial data
            await self._send_initial_dashboard_data(websocket)

            # Keep connection alive
            while True:
                await websocket.receive_text()  # Keep connection alive

        except WebSocketDisconnect:
            logger.info("Dashboard WebSocket client disconnected")
        except Exception as e:
            logger.error(f"Dashboard WebSocket error: {e}")
        finally:
            if websocket in self.connected_clients:
                self.connected_clients.remove(websocket)

    async def _send_initial_dashboard_data(self, websocket: WebSocket):
        """Send initial dashboard data to newly connected client"""
        # Send current metrics
        await websocket.send_text(
            json.dumps(
                {
                    "type": "initial_metrics",
                    "data": {
                        "timestamp": self.current_metrics.timestamp.isoformat(),
                        "total_requests": self.current_metrics.total_requests,
                        "blocked_requests": self.current_metrics.blocked_requests,
                        "threat_events": self.current_metrics.threat_events,
                        "critical_alerts": self.current_metrics.critical_alerts,
                        "high_alerts": self.current_metrics.high_alerts,
                        "medium_alerts": self.current_metrics.medium_alerts,
                        "low_alerts": self.current_metrics.low_alerts,
                        "active_incidents": self.current_metrics.active_incidents,
                        "compliance_score": self.current_metrics.compliance_score,
                    },
                }
            )
        )

        # Send recent alerts
        recent_alerts = list(self.alerts_queue)[-10:]  # Last 10 alerts
        await websocket.send_text(
            json.dumps(
                {
                    "type": "recent_alerts",
                    "data": [
                        {
                            "id": alert.id,
                            "timestamp": alert.timestamp.isoformat(),
                            "severity": alert.severity.value,
                            "title": alert.title,
                            "source_ip": alert.source_ip,
                            "threat_indicators": alert.threat_indicators,
                        }
                        for alert in recent_alerts
                    ],
                }
            )
        )

    # HTTP API endpoints
    async def get_dashboard_overview(self) -> Dict[str, Any]:
        """Get dashboard overview data"""
        return {
            "current_metrics": {
                "timestamp": self.current_metrics.timestamp.isoformat(),
                "total_requests": self.current_metrics.total_requests,
                "blocked_requests": self.current_metrics.blocked_requests,
                "threat_events": self.current_metrics.threat_events,
                "alerts": {
                    "critical": self.current_metrics.critical_alerts,
                    "high": self.current_metrics.high_alerts,
                    "medium": self.current_metrics.medium_alerts,
                    "low": self.current_metrics.low_alerts,
                },
                "active_incidents": self.current_metrics.active_incidents,
                "compliance_score": self.current_metrics.compliance_score,
            },
            "recent_alerts": [
                {
                    "id": alert.id,
                    "timestamp": alert.timestamp.isoformat(),
                    "severity": alert.severity.value,
                    "title": alert.title,
                    "source_ip": alert.source_ip,
                }
                for alert in list(self.alerts_queue)[-10:]
            ],
            "active_incidents": [
                {
                    "id": incident.id,
                    "title": incident.title,
                    "severity": incident.severity.value,
                    "status": incident.status.value,
                    "created_at": incident.created_at.isoformat(),
                }
                for incident in self.incidents.values()
                if incident.status
                not in [IncidentStatus.RESOLVED, IncidentStatus.CLOSED]
            ],
        }

    async def get_compliance_summary(self) -> Dict[str, Any]:
        """Get compliance summary"""
        try:
            async with aiosqlite.connect(self.database_path) as conn:
                reports = {}
                for framework in ComplianceFramework:
                    cursor = await conn.execute(
                        """
                        SELECT compliance_score, passed_controls, failed_controls, report_date
                        FROM compliance_reports 
                        WHERE framework = ?
                        ORDER BY report_date DESC
                        LIMIT 1
                    """,
                        (framework.value,),
                    )
                    row = await cursor.fetchone()

                    if row:
                        reports[framework.value] = {
                            "compliance_score": row[0],
                            "passed_controls": row[1],
                            "failed_controls": row[2],
                            "last_updated": row[3],
                        }

                return {"compliance_reports": reports}

        except Exception as e:
            logger.error(f"Error getting compliance summary: {e}")
            return {"compliance_reports": {}}


# Global dashboard instance
security_dashboard: Optional[SecurityDashboard] = None


def get_security_dashboard() -> SecurityDashboard:
    """Get the global security dashboard instance"""
    global security_dashboard
    if security_dashboard is None:
        raise RuntimeError("Security Dashboard not initialized")
    return security_dashboard


async def initialize_security_dashboard(**kwargs) -> SecurityDashboard:
    """Initialize the global security dashboard"""
    global security_dashboard
    security_dashboard = SecurityDashboard(**kwargs)
    await security_dashboard.initialize()
    return security_dashboard


__all__ = [
    "SecurityDashboard",
    "SecurityAlert",
    "SecurityIncident",
    "ComplianceReport",
    "AlertSeverity",
    "IncidentStatus",
    "SecurityMetrics",
    "get_security_dashboard",
    "initialize_security_dashboard",
]
