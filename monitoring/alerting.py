#!/usr/bin/env python3
"""
AlertManager with Notification Routing for Novel Engine

Implements comprehensive alerting system with:
- Threshold-based alerting for critical metrics
- Anomaly detection for unusual patterns
- Escalation procedures and notification routing
- Incident management and response workflows
"""

import asyncio
import json
import logging
import os
import smtplib
import sqlite3
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp
import aiosqlite

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(Enum):
    """Alert status values"""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class NotificationChannel(Enum):
    """Notification channel types"""

    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    PAGERDUTY = "pagerduty"


@dataclass
class AlertRule:
    """Definition of an alert rule"""

    name: str
    metric_name: str
    condition: str  # e.g., "> 80", "< 0.95", "== 0"
    threshold: float
    severity: AlertSeverity
    description: str

    # Timing configuration
    evaluation_interval: float = 60.0  # seconds
    for_duration: float = 300.0  # seconds (5 minutes)

    # Notification configuration
    notification_channels: List[NotificationChannel] = field(default_factory=list)
    escalation_rules: List["EscalationRule"] = field(default_factory=list)

    # Filtering
    labels: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True

    # Anomaly detection
    use_anomaly_detection: bool = False
    anomaly_sensitivity: float = 2.0  # standard deviations
    baseline_window: int = 1440  # minutes (24 hours)


@dataclass
class EscalationRule:
    """Escalation rule for alerts"""

    delay_minutes: int
    channels: List[NotificationChannel]
    message_template: Optional[str] = None


@dataclass
class Alert:
    """Alert instance"""

    id: str
    rule_name: str
    metric_name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str

    # Timing
    fired_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    # Values
    current_value: float = 0.0
    threshold_value: float = 0.0

    # Context
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)

    # Tracking
    notification_count: int = 0
    last_notification: Optional[datetime] = None
    escalation_level: int = 0


@dataclass
class NotificationConfig:
    """Configuration for notification channels"""

    # Email configuration
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    email_from: str = "alerts@novel-engine.com"
    email_recipients: List[str] = field(default_factory=list)

    # Slack configuration
    slack_webhook_url: Optional[str] = None
    slack_channel: str = "#alerts"
    slack_username: str = "Novel Engine Alerts"

    # Webhook configuration
    webhook_urls: List[str] = field(default_factory=list)
    webhook_timeout: float = 10.0

    # PagerDuty configuration
    pagerduty_integration_key: Optional[str] = None

    # SMS configuration (via webhook/API)
    sms_webhook_url: Optional[str] = None
    sms_recipients: List[str] = field(default_factory=list)


class MetricBuffer:
    """Buffer for storing metric values for anomaly detection"""

    def __init__(self, max_size: int = 1440):  # 24 hours of minute data
        self.max_size = max_size
        self.values: deque = deque(maxlen=max_size)
        self.timestamps: deque = deque(maxlen=max_size)

    def add_value(self, value: float, timestamp: float = None):
        """Add a metric value"""
        if timestamp is None:
            timestamp = time.time()

        self.values.append(value)
        self.timestamps.append(timestamp)

    def get_baseline_stats(self) -> Dict[str, float]:
        """Get baseline statistics"""
        if len(self.values) < 10:
            return {}

        values = list(self.values)
        return {
            "mean": statistics.mean(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "count": len(values),
        }

    def is_anomaly(self, value: float, sensitivity: float = 2.0) -> bool:
        """Check if a value is anomalous"""
        stats = self.get_baseline_stats()
        if not stats or stats["std_dev"] == 0:
            return False

        z_score = abs(value - stats["mean"]) / stats["std_dev"]
        return z_score > sensitivity


class AlertManager:
    """Manages alerts and notifications"""

    def __init__(self, config: NotificationConfig, db_path: str = "data/alerts.db"):
        self.config = config
        self.db_path = db_path

        # Alert rules and state
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []

        # Metric buffers for anomaly detection
        self.metric_buffers: Dict[str, MetricBuffer] = defaultdict(MetricBuffer)

        # Notification tracking
        self.notification_queue: deque = deque()
        self.rate_limits: Dict[str, float] = {}  # channel -> last_sent_time

        # Background tasks
        self.running = False
        self.evaluation_task: Optional[asyncio.Task] = None
        self.notification_task: Optional[asyncio.Task] = None

        # Initialize database
        self._init_database()

        logger.info("Alert manager initialized")

    def _init_database(self):
        """Initialize alerts database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    rule_name TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT NOT NULL,
                    fired_at REAL NOT NULL,
                    acknowledged_at REAL,
                    resolved_at REAL,
                    current_value REAL,
                    threshold_value REAL,
                    labels TEXT,
                    annotations TEXT,
                    notification_count INTEGER DEFAULT 0,
                    last_notification REAL,
                    escalation_level INTEGER DEFAULT 0
                )
            """
            )

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_alerts_rule_name ON alerts(rule_name)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_alerts_fired_at ON alerts(fired_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status)"
            )

    def add_rule(self, rule: AlertRule):
        """Add an alert rule"""
        self.rules[rule.name] = rule
        logger.info(f"Added alert rule: {rule.name}")

    def remove_rule(self, rule_name: str):
        """Remove an alert rule"""
        if rule_name in self.rules:
            del self.rules[rule_name]
            logger.info(f"Removed alert rule: {rule_name}")

    def update_metric(self, metric_name: str, value: float):
        """Update a metric value"""
        self.metric_buffers[metric_name].add_value(value)

    async def start(self):
        """Start the alert manager"""
        if self.running:
            return

        self.running = True

        # Start background tasks
        self.evaluation_task = asyncio.create_task(self._evaluation_loop())
        self.notification_task = asyncio.create_task(self._notification_loop())

        logger.info("Alert manager started")

    async def stop(self):
        """Stop the alert manager"""
        self.running = False

        # Cancel background tasks
        if self.evaluation_task:
            self.evaluation_task.cancel()
            try:
                await self.evaluation_task
            except asyncio.CancelledError:
                pass

        if self.notification_task:
            self.notification_task.cancel()
            try:
                await self.notification_task
            except asyncio.CancelledError:
                pass

        logger.info("Alert manager stopped")

    async def _evaluation_loop(self):
        """Main evaluation loop for alert rules"""
        while self.running:
            try:
                for rule in self.rules.values():
                    if rule.enabled:
                        await self._evaluate_rule(rule)

                await asyncio.sleep(60)  # Evaluate every minute

            except Exception as e:
                logger.error(f"Error in alert evaluation loop: {e}")
                await asyncio.sleep(60)

    async def _evaluate_rule(self, rule: AlertRule):
        """Evaluate a specific alert rule"""
        try:
            # Get current metric value
            if rule.metric_name not in self.metric_buffers:
                return

            buffer = self.metric_buffers[rule.metric_name]
            if not buffer.values:
                return

            current_value = buffer.values[-1]

            # Check threshold condition
            threshold_violated = self._check_threshold(
                current_value, rule.condition, rule.threshold
            )

            # Check anomaly detection if enabled
            anomaly_detected = False
            if rule.use_anomaly_detection:
                anomaly_detected = buffer.is_anomaly(
                    current_value, rule.anomaly_sensitivity
                )

            # Determine if alert should fire
            should_fire = threshold_violated or anomaly_detected

            alert_id = f"{rule.name}_{rule.metric_name}"

            if should_fire:
                if alert_id not in self.active_alerts:
                    # New alert
                    await self._fire_alert(rule, current_value, anomaly_detected)
                else:
                    # Existing alert - update value
                    self.active_alerts[alert_id].current_value = current_value
            else:
                if alert_id in self.active_alerts:
                    # Resolve alert
                    await self._resolve_alert(alert_id)

        except Exception as e:
            logger.error(f"Error evaluating rule {rule.name}: {e}")

    def _check_threshold(self, value: float, condition: str, threshold: float) -> bool:
        """Check if value violates threshold condition"""
        condition = condition.strip()

        if condition.startswith(">="):
            return value >= threshold
        elif condition.startswith("<="):
            return value <= threshold
        elif condition.startswith(">"):
            return value > threshold
        elif condition.startswith("<"):
            return value < threshold
        elif condition.startswith("=="):
            return abs(value - threshold) < 0.001  # Handle floating point comparison
        elif condition.startswith("!="):
            return abs(value - threshold) >= 0.001
        else:
            logger.warning(f"Unknown condition: {condition}")
            return False

    async def _fire_alert(
        self, rule: AlertRule, current_value: float, is_anomaly: bool = False
    ):
        """Fire a new alert"""
        alert_id = f"{rule.name}_{rule.metric_name}"

        # Create alert message
        if is_anomaly:
            message = f"Anomaly detected: {rule.metric_name} = {current_value:.2f} (unusual pattern detected)"
        else:
            message = f"Alert: {rule.metric_name} {rule.condition} {rule.threshold} (current: {current_value:.2f})"

        # Create alert
        alert = Alert(
            id=alert_id,
            rule_name=rule.name,
            metric_name=rule.metric_name,
            severity=rule.severity,
            status=AlertStatus.ACTIVE,
            message=message,
            fired_at=datetime.now(timezone.utc),
            current_value=current_value,
            threshold_value=rule.threshold,
            labels=rule.labels.copy(),
            annotations={"description": rule.description},
        )

        # Store alert
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)

        # Persist to database
        await self._persist_alert(alert)

        # Queue notifications
        await self._queue_notifications(alert, rule)

        logger.warning(f"Alert fired: {alert.message}")

    async def _resolve_alert(self, alert_id: str):
        """Resolve an active alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now(timezone.utc)

            # Remove from active alerts
            del self.active_alerts[alert_id]

            # Persist to database
            await self._persist_alert(alert)

            logger.info(f"Alert resolved: {alert.message}")

    async def _queue_notifications(self, alert: Alert, rule: AlertRule):
        """Queue notifications for an alert"""
        for channel in rule.notification_channels:
            notification = {
                "alert": alert,
                "channel": channel,
                "attempt": 0,
                "scheduled_at": time.time(),
            }
            self.notification_queue.append(notification)

        # Queue escalation notifications
        for escalation in rule.escalation_rules:
            for channel in escalation.channels:
                notification = {
                    "alert": alert,
                    "channel": channel,
                    "attempt": 0,
                    "scheduled_at": time.time() + (escalation.delay_minutes * 60),
                    "escalation": True,
                    "escalation_template": escalation.message_template,
                }
                self.notification_queue.append(notification)

    async def _notification_loop(self):
        """Process notification queue"""
        while self.running:
            try:
                current_time = time.time()

                # Process queued notifications
                notifications_to_send = []
                remaining_notifications = deque()

                while self.notification_queue:
                    notification = self.notification_queue.popleft()

                    if notification["scheduled_at"] <= current_time:
                        notifications_to_send.append(notification)
                    else:
                        remaining_notifications.append(notification)

                # Restore remaining notifications
                self.notification_queue = remaining_notifications

                # Send notifications
                for notification in notifications_to_send:
                    await self._send_notification(notification)

                await asyncio.sleep(10)  # Check every 10 seconds

            except Exception as e:
                logger.error(f"Error in notification loop: {e}")
                await asyncio.sleep(10)

    async def _send_notification(self, notification: Dict[str, Any]):
        """Send a single notification"""
        try:
            alert = notification["alert"]
            channel = notification["channel"]

            # Check rate limiting
            rate_limit_key = f"{channel.value}_{alert.id}"
            if rate_limit_key in self.rate_limits:
                last_sent = self.rate_limits[rate_limit_key]
                if time.time() - last_sent < 300:  # 5 minute rate limit
                    return

            # Send notification based on channel type
            success = False

            if channel == NotificationChannel.EMAIL:
                success = await self._send_email_notification(alert, notification)
            elif channel == NotificationChannel.SLACK:
                success = await self._send_slack_notification(alert, notification)
            elif channel == NotificationChannel.WEBHOOK:
                success = await self._send_webhook_notification(alert, notification)
            elif channel == NotificationChannel.PAGERDUTY:
                success = await self._send_pagerduty_notification(alert, notification)
            elif channel == NotificationChannel.SMS:
                success = await self._send_sms_notification(alert, notification)

            if success:
                # Update rate limit
                self.rate_limits[rate_limit_key] = time.time()

                # Update alert notification tracking
                alert.notification_count += 1
                alert.last_notification = datetime.now(timezone.utc)

                logger.info(f"Notification sent: {channel.value} for alert {alert.id}")
            else:
                # Retry logic
                notification["attempt"] += 1
                if notification["attempt"] < 3:
                    notification["scheduled_at"] = (
                        time.time() + 300
                    )  # Retry in 5 minutes
                    self.notification_queue.append(notification)

        except Exception as e:
            logger.error(f"Error sending notification: {e}")

    async def _send_email_notification(
        self, alert: Alert, notification: Dict[str, Any]
    ) -> bool:
        """Send email notification"""
        try:
            if not self.config.email_recipients:
                return False

            # Create email content
            subject = f"[{alert.severity.value.upper()}] Novel Engine Alert: {alert.rule_name}"

            body = f"""
            Alert Details:
            - Rule: {alert.rule_name}
            - Metric: {alert.metric_name}
            - Severity: {alert.severity.value}
            - Message: {alert.message}
            - Current Value: {alert.current_value}
            - Threshold: {alert.threshold_value}
            - Fired At: {alert.fired_at.isoformat()}
            
            Labels: {json.dumps(alert.labels, indent=2)}
            """

            # Create message
            msg = MIMEMultipart()
            msg["From"] = self.config.email_from
            msg["To"] = ", ".join(self.config.email_recipients)
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            # Send email
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                if self.config.smtp_use_tls:
                    server.starttls()

                if self.config.smtp_username and self.config.smtp_password:
                    server.login(self.config.smtp_username, self.config.smtp_password)

                server.send_message(msg)

            return True

        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            return False

    async def _send_slack_notification(
        self, alert: Alert, notification: Dict[str, Any]
    ) -> bool:
        """Send Slack notification"""
        try:
            if not self.config.slack_webhook_url:
                return False

            # Create Slack message
            color = {
                AlertSeverity.INFO: "good",
                AlertSeverity.WARNING: "warning",
                AlertSeverity.CRITICAL: "danger",
                AlertSeverity.EMERGENCY: "danger",
            }.get(alert.severity, "warning")

            payload = {
                "channel": self.config.slack_channel,
                "username": self.config.slack_username,
                "attachments": [
                    {
                        "color": color,
                        "title": f"Alert: {alert.rule_name}",
                        "text": alert.message,
                        "fields": [
                            {
                                "title": "Metric",
                                "value": alert.metric_name,
                                "short": True,
                            },
                            {
                                "title": "Severity",
                                "value": alert.severity.value,
                                "short": True,
                            },
                            {
                                "title": "Current Value",
                                "value": str(alert.current_value),
                                "short": True,
                            },
                            {
                                "title": "Threshold",
                                "value": str(alert.threshold_value),
                                "short": True,
                            },
                        ],
                        "footer": "Novel Engine Monitoring",
                        "ts": int(alert.fired_at.timestamp()),
                    }
                ],
            }

            # Send to Slack
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.slack_webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    return response.status == 200

        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
            return False

    async def _send_webhook_notification(
        self, alert: Alert, notification: Dict[str, Any]
    ) -> bool:
        """Send webhook notification"""
        try:
            if not self.config.webhook_urls:
                return False

            # Create webhook payload
            payload = {
                "alert": {
                    "id": alert.id,
                    "rule_name": alert.rule_name,
                    "metric_name": alert.metric_name,
                    "severity": alert.severity.value,
                    "status": alert.status.value,
                    "message": alert.message,
                    "fired_at": alert.fired_at.isoformat(),
                    "current_value": alert.current_value,
                    "threshold_value": alert.threshold_value,
                    "labels": alert.labels,
                    "annotations": alert.annotations,
                }
            }

            # Send to all webhook URLs
            success_count = 0

            async with aiohttp.ClientSession() as session:
                for url in self.config.webhook_urls:
                    try:
                        async with session.post(
                            url,
                            json=payload,
                            timeout=aiohttp.ClientTimeout(
                                total=self.config.webhook_timeout
                            ),
                        ) as response:
                            if response.status < 400:
                                success_count += 1
                    except Exception as e:
                        logger.warning(f"Webhook notification failed for {url}: {e}")

            return success_count > 0

        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}")
            return False

    async def _send_pagerduty_notification(
        self, alert: Alert, notification: Dict[str, Any]
    ) -> bool:
        """Send PagerDuty notification"""
        try:
            if not self.config.pagerduty_integration_key:
                return False

            # Create PagerDuty event
            payload = {
                "routing_key": self.config.pagerduty_integration_key,
                "event_action": "trigger",
                "dedup_key": alert.id,
                "payload": {
                    "summary": alert.message,
                    "severity": alert.severity.value,
                    "source": "novel-engine",
                    "component": alert.metric_name,
                    "group": alert.rule_name,
                    "class": "monitoring",
                    "custom_details": {
                        "current_value": alert.current_value,
                        "threshold_value": alert.threshold_value,
                        "labels": alert.labels,
                    },
                },
            }

            # Send to PagerDuty
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://events.pagerduty.com/v2/enqueue",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    return response.status == 202

        except Exception as e:
            logger.error(f"Error sending PagerDuty notification: {e}")
            return False

    async def _send_sms_notification(
        self, alert: Alert, notification: Dict[str, Any]
    ) -> bool:
        """Send SMS notification"""
        try:
            if not self.config.sms_webhook_url or not self.config.sms_recipients:
                return False

            # Create SMS message
            message = f"Novel Engine Alert: {alert.rule_name} - {alert.message}"

            # Send SMS via webhook
            payload = {"recipients": self.config.sms_recipients, "message": message}

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.sms_webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    return response.status < 400

        except Exception as e:
            logger.error(f"Error sending SMS notification: {e}")
            return False

    async def _persist_alert(self, alert: Alert):
        """Persist alert to database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO alerts (
                        id, rule_name, metric_name, severity, status, message,
                        fired_at, acknowledged_at, resolved_at, current_value,
                        threshold_value, labels, annotations, notification_count,
                        last_notification, escalation_level
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        alert.id,
                        alert.rule_name,
                        alert.metric_name,
                        alert.severity.value,
                        alert.status.value,
                        alert.message,
                        alert.fired_at.timestamp(),
                        (
                            alert.acknowledged_at.timestamp()
                            if alert.acknowledged_at
                            else None
                        ),
                        alert.resolved_at.timestamp() if alert.resolved_at else None,
                        alert.current_value,
                        alert.threshold_value,
                        json.dumps(alert.labels),
                        json.dumps(alert.annotations),
                        alert.notification_count,
                        (
                            alert.last_notification.timestamp()
                            if alert.last_notification
                            else None
                        ),
                        alert.escalation_level,
                    ),
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Error persisting alert: {e}")

    async def acknowledge_alert(self, alert_id: str, user: str = "system") -> bool:
        """Acknowledge an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.now(timezone.utc)
            alert.annotations["acknowledged_by"] = user

            await self._persist_alert(alert)
            logger.info(f"Alert acknowledged by {user}: {alert_id}")
            return True

        return False

    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return list(self.active_alerts.values())

    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """Get alert history for specified time period"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        return [alert for alert in self.alert_history if alert.fired_at >= cutoff_time]

    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        active_count = len(self.active_alerts)
        len(self.alert_history)

        # Count by severity
        severity_counts = defaultdict(int)
        for alert in self.alert_history[-100:]:  # Last 100 alerts
            severity_counts[alert.severity.value] += 1

        # Calculate MTTR (Mean Time To Resolution)
        resolved_alerts = [
            alert
            for alert in self.alert_history[-100:]
            if alert.resolved_at and alert.fired_at
        ]

        if resolved_alerts:
            resolution_times = [
                (alert.resolved_at - alert.fired_at).total_seconds()
                for alert in resolved_alerts
            ]
            mttr_seconds = statistics.mean(resolution_times)
        else:
            mttr_seconds = 0

        return {
            "active_alerts": active_count,
            "total_alerts_24h": len(self.get_alert_history(24)),
            "severity_distribution": dict(severity_counts),
            "mttr_seconds": mttr_seconds,
            "mttr_minutes": mttr_seconds / 60,
            "alert_rate_per_hour": len(self.get_alert_history(24)) / 24,
        }


# Helper function to create default alert rules
def create_default_alert_rules() -> List[AlertRule]:
    """Create default alert rules for Novel Engine"""
    return [
        # System resource alerts
        AlertRule(
            name="high_memory_usage",
            metric_name="system_memory_usage_percent",
            condition="> 90",
            threshold=90.0,
            severity=AlertSeverity.CRITICAL,
            description="System memory usage is critically high",
            notification_channels=[
                NotificationChannel.EMAIL,
                NotificationChannel.SLACK,
            ],
        ),
        AlertRule(
            name="high_cpu_usage",
            metric_name="system_cpu_usage_percent",
            condition="> 85",
            threshold=85.0,
            severity=AlertSeverity.WARNING,
            description="System CPU usage is high",
            for_duration=600.0,  # 10 minutes
            notification_channels=[NotificationChannel.SLACK],
        ),
        AlertRule(
            name="low_disk_space",
            metric_name="system_disk_usage_percent",
            condition="> 90",
            threshold=90.0,
            severity=AlertSeverity.CRITICAL,
            description="Disk space is running low",
            notification_channels=[
                NotificationChannel.EMAIL,
                NotificationChannel.SLACK,
            ],
        ),
        # Application performance alerts
        AlertRule(
            name="high_response_time",
            metric_name="http_request_duration_seconds",
            condition="> 5.0",
            threshold=5.0,
            severity=AlertSeverity.WARNING,
            description="HTTP response time is high",
            use_anomaly_detection=True,
            notification_channels=[NotificationChannel.SLACK],
        ),
        AlertRule(
            name="high_error_rate",
            metric_name="http_errors_total",
            condition="> 10",
            threshold=10.0,
            severity=AlertSeverity.CRITICAL,
            description="HTTP error rate is high",
            notification_channels=[
                NotificationChannel.EMAIL,
                NotificationChannel.SLACK,
            ],
            escalation_rules=[
                EscalationRule(
                    delay_minutes=15, channels=[NotificationChannel.PAGERDUTY]
                )
            ],
        ),
        # Novel Engine specific alerts
        AlertRule(
            name="story_generation_failures",
            metric_name="story_generation_errors_total",
            condition="> 5",
            threshold=5.0,
            severity=AlertSeverity.WARNING,
            description="Story generation failure rate is high",
            notification_channels=[NotificationChannel.SLACK],
        ),
        AlertRule(
            name="database_connection_failures",
            metric_name="database_connection_errors_total",
            condition="> 0",
            threshold=0.0,
            severity=AlertSeverity.CRITICAL,
            description="Database connection failures detected",
            notification_channels=[
                NotificationChannel.EMAIL,
                NotificationChannel.SLACK,
            ],
        ),
    ]


__all__ = [
    "AlertSeverity",
    "AlertStatus",
    "NotificationChannel",
    "AlertRule",
    "EscalationRule",
    "Alert",
    "NotificationConfig",
    "AlertManager",
    "create_default_alert_rules",
]
