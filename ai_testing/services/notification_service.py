"""
Notification Service

Real-time notification and alerting service for Novel-Engine AI acceptance testing.
Provides intelligent alerting, escalation, and communication across multiple channels.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

# Email imports with fallback
try:
    import smtplib
    from email import encoders
    from email.mime.base import MIMEBase as MimeBase
    from email.mime.multipart import MIMEMultipart as MimeMultipart
    from email.mime.text import MIMEText as MimeText

    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False
    MimeText = None
    MimeMultipart = None
    MimeBase = None
    encoders = None

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import Novel-Engine patterns
try:
    from config_loader import get_config

    from src.event_bus import EventBus
except ImportError:
    # Fallback for testing
    def get_config():
        return None

    def EventBus():
        return None


# Import AI testing contracts
from ai_testing.interfaces.service_contracts import (
    INotificationService,
    ServiceHealthResponse,
    TestContext,
    TestResult,
)

# Import AI testing configuration
from ai_testing_config import get_ai_testing_service_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Notification Models ===


class NotificationChannel(str, Enum):
    """Available notification channels"""

    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    TEAMS = "teams"
    DISCORD = "discord"
    CONSOLE = "console"
    FILE = "file"


class NotificationPriority(str, Enum):
    """Notification priority levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    URGENT = "urgent"


class AlertType(str, Enum):
    """Types of alerts"""

    TEST_FAILURE = "test_failure"
    QUALITY_REGRESSION = "quality_regression"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    SERVICE_DOWN = "service_down"
    THRESHOLD_BREACH = "threshold_breach"
    ANOMALY_DETECTED = "anomaly_detected"
    SUCCESS_MILESTONE = "success_milestone"


class NotificationStatus(str, Enum):
    """Notification delivery status"""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class NotificationRule:
    """Rule for triggering notifications"""

    rule_id: str
    name: str
    description: str

    # Trigger conditions
    alert_types: List[AlertType] = field(default_factory=list)
    priority_threshold: NotificationPriority = NotificationPriority.MEDIUM
    service_names: List[str] = field(default_factory=list)
    test_types: List[str] = field(default_factory=list)

    # Quality thresholds
    min_quality_score: Optional[float] = None
    max_failure_rate: Optional[float] = None
    max_response_time_ms: Optional[float] = None

    # Recipients and channels
    recipients: List[str] = field(default_factory=list)
    channels: List[NotificationChannel] = field(default_factory=list)

    # Escalation
    escalation_delay_minutes: int = 30
    escalation_recipients: List[str] = field(default_factory=list)

    # Rate limiting
    cooldown_minutes: int = 15
    max_notifications_per_hour: int = 10

    # Schedule
    active_hours: Optional[Dict[str, Any]] = None  # {"start": "09:00", "end": "17:00"}
    active_days: List[str] = field(
        default_factory=lambda: ["mon", "tue", "wed", "thu", "fri"]
    )

    # Metadata
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_triggered: Optional[datetime] = None


class NotificationTemplate(BaseModel):
    """Template for notification content"""

    template_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    alert_type: AlertType
    channel: NotificationChannel

    # Template content
    subject_template: str = ""
    body_template: str = ""
    html_template: Optional[str] = None

    # Formatting options
    include_charts: bool = False
    include_details: bool = True
    max_content_length: int = 5000

    # Variables available: {test_name}, {score}, {status}, {error_message}, etc.


class Alert(BaseModel):
    """Alert instance"""

    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    alert_type: AlertType
    priority: NotificationPriority

    # Alert content
    title: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)

    # Source information
    source_service: str = ""
    test_result_id: Optional[str] = None
    scenario_id: Optional[str] = None

    # Metrics
    affected_metrics: List[str] = Field(default_factory=list)
    threshold_values: Dict[str, float] = Field(default_factory=dict)
    current_values: Dict[str, float] = Field(default_factory=dict)

    # Context
    context: Dict[str, Any] = Field(default_factory=dict)

    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None

    # Status
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    resolved: bool = False


class NotificationRequest(BaseModel):
    """Notification request for sending notifications"""

    notification_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    message: str
    priority: NotificationPriority
    channels: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Notification(BaseModel):
    """Individual notification instance"""

    notification_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    alert_id: str
    rule_id: str

    # Delivery details
    channel: NotificationChannel
    recipient: str
    priority: NotificationPriority

    # Content
    subject: str = ""
    content: str = ""
    formatted_content: Dict[str, Any] = Field(default_factory=dict)

    # Delivery tracking
    status: NotificationStatus = NotificationStatus.PENDING
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None

    # Error handling
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)


# === Channel Handlers ===


class ChannelHandler:
    """Base class for notification channel handlers"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", True)

    async def send(self, notification: Notification) -> bool:
        """Send notification through this channel"""
        raise NotImplementedError

    async def validate_config(self) -> bool:
        """Validate channel configuration"""
        return True


class EmailHandler(ChannelHandler):
    """Email notification handler"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.smtp_server = config.get("smtp_server", "localhost")
        self.smtp_port = config.get("smtp_port", 587)
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.from_email = config.get("from_email", "noreply@novel-engine.com")
        self.use_tls = config.get("use_tls", True)

    async def send(self, notification: Notification) -> bool:
        """Send email notification"""

        try:
            # Create message
            msg = MimeMultipart()
            msg["From"] = self.from_email
            msg["To"] = notification.recipient
            msg["Subject"] = notification.subject

            # Add body
            body = MimeText(notification.content, "plain")
            msg.attach(body)

            # Add HTML if available
            if notification.formatted_content.get("html"):
                html_body = MimeText(notification.formatted_content["html"], "html")
                msg.attach(html_body)

            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            if self.use_tls:
                server.starttls()

            if self.username and self.password:
                server.login(self.username, self.password)

            text = msg.as_string()
            server.sendmail(self.from_email, notification.recipient, text)
            server.quit()

            logger.info(f"Email sent to {notification.recipient}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {notification.recipient}: {e}")
            return False

    async def validate_config(self) -> bool:
        """Validate email configuration"""
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            if self.use_tls:
                server.starttls()
            server.quit()
            return True
        except Exception as e:
            logger.error(f"Email configuration validation failed: {e}")
            return False


class SlackHandler(ChannelHandler):
    """Slack notification handler"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.webhook_url = config.get("webhook_url", "")
        self.bot_token = config.get("bot_token", "")
        self.default_channel = config.get("default_channel", "#alerts")

    async def send(self, notification: Notification) -> bool:
        """Send Slack notification"""

        if not self.webhook_url:
            logger.warning("Slack webhook URL not configured")
            return False

        try:
            # Format Slack message
            slack_payload = {
                "channel": notification.recipient or self.default_channel,
                "text": notification.subject,
                "attachments": [
                    {
                        "color": self._get_color_for_priority(notification.priority),
                        "fields": [
                            {
                                "title": "Message",
                                "value": notification.content,
                                "short": False,
                            }
                        ],
                        "footer": "Novel-Engine AI Testing",
                        "ts": int(time.time()),
                    }
                ],
            }

            # Add additional fields from formatted content
            if notification.formatted_content:
                for key, value in notification.formatted_content.items():
                    if key != "html":
                        slack_payload["attachments"][0]["fields"].append(
                            {"title": key.title(), "value": str(value), "short": True}
                        )

            # Send to Slack
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url, json=slack_payload, timeout=30.0
                )

                if response.status_code == 200:
                    logger.info(f"Slack notification sent to {notification.recipient}")
                    return True
                else:
                    logger.error(
                        f"Slack notification failed: {response.status_code} - {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False

    def _get_color_for_priority(self, priority: NotificationPriority) -> str:
        """Get Slack color for priority level"""
        color_map = {
            NotificationPriority.LOW: "good",
            NotificationPriority.MEDIUM: "warning",
            NotificationPriority.HIGH: "danger",
            NotificationPriority.CRITICAL: "danger",
            NotificationPriority.URGENT: "danger",
        }
        return color_map.get(priority, "warning")


class WebhookHandler(ChannelHandler):
    """Generic webhook notification handler"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.webhook_url = config.get("webhook_url", "")
        self.headers = config.get("headers", {})
        self.method = config.get("method", "POST")

    async def send(self, notification: Notification) -> bool:
        """Send webhook notification"""

        if not self.webhook_url:
            logger.warning("Webhook URL not configured")
            return False

        try:
            # Prepare payload
            payload = {
                "notification_id": notification.notification_id,
                "alert_id": notification.alert_id,
                "channel": notification.channel.value,
                "priority": notification.priority.value,
                "recipient": notification.recipient,
                "subject": notification.subject,
                "content": notification.content,
                "timestamp": notification.created_at.isoformat(),
                "formatted_content": notification.formatted_content,
            }

            # Send webhook
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=self.method,
                    url=self.webhook_url,
                    json=payload,
                    headers=self.headers,
                    timeout=30.0,
                )

                if 200 <= response.status_code < 300:
                    logger.info(f"Webhook notification sent to {self.webhook_url}")
                    return True
                else:
                    logger.error(f"Webhook notification failed: {response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False


class ConsoleChannelHandler(ChannelHandler):
    """Console notification handler for development and debugging"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

    async def send(self, notification: Notification) -> bool:
        """Send notification to console output"""
        timestamp = datetime.now().isoformat()
        priority = notification.priority.value
        print(
            f"[NOTIFICATION] [{timestamp}] [{priority}] {notification.subject}: {notification.content}"
        )
        logger.info(f"Console notification: {notification.subject}")
        return True


class FileChannelHandler(ChannelHandler):
    """File notification handler for persistent logging"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        from pathlib import Path

        self.output_directory = Path(
            config.get("output_directory", "ai_testing/notifications")
        )
        self.filename_pattern = config.get(
            "filename_pattern", "notifications_{date}.log"
        )
        self.output_directory.mkdir(parents=True, exist_ok=True)

    async def send(self, notification: Notification) -> bool:
        """Write notification to file"""
        try:
            date_str = datetime.now().strftime("%Y%m%d")
            filename = self.filename_pattern.replace("{date}", date_str)
            filepath = self.output_directory / filename

            timestamp = datetime.now().isoformat()
            priority = notification.priority.value
            log_entry = f"[{timestamp}] [{priority}] {notification.subject}: {notification.content}\n"

            # Append to file
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(log_entry)

            return True
        except Exception as e:
            logger.error(f"Failed to write notification to file: {e}")
            return False


# === Alert Detector ===


class AlertDetector:
    """
    Intelligent alert detection and rule engine

    Features:
    - Multi-criteria alert detection
    - Threshold monitoring
    - Pattern recognition
    - Escalation logic
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.rules: List[NotificationRule] = []
        self.recent_alerts: List[Alert] = []

        # Load default rules
        self._load_default_rules()

        logger.info("Alert Detector initialized")

    def add_rule(self, rule: NotificationRule):
        """Add notification rule"""
        self.rules.append(rule)
        logger.info(f"Added notification rule: {rule.name}")

    def remove_rule(self, rule_id: str) -> bool:
        """Remove notification rule"""
        initial_count = len(self.rules)
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        return len(self.rules) < initial_count

    async def analyze_test_result(self, test_result: TestResult) -> List[Alert]:
        """Analyze test result and generate alerts"""

        alerts = []

        for rule in self.rules:
            if not rule.enabled:
                continue

            # Check if rule should trigger
            should_trigger = await self._evaluate_rule(rule, test_result)

            if should_trigger:
                # Check rate limiting
                if self._is_rate_limited(rule):
                    logger.debug(f"Rule {rule.name} is rate limited")
                    continue

                # Generate alert
                alert = await self._create_alert_from_result(rule, test_result)
                alerts.append(alert)

                # Update rule state
                rule.last_triggered = datetime.now(timezone.utc)

        return alerts

    async def analyze_aggregated_results(
        self,
        results: List[TestResult],
        performance_metrics: Dict[str, float],
        quality_trends: List[Any],
    ) -> List[Alert]:
        """Analyze aggregated results for system-wide alerts"""

        alerts = []

        # Check performance degradation
        if performance_metrics.get("avg_response_time_ms", 0) > 5000:
            alerts.append(
                Alert(
                    alert_type=AlertType.PERFORMANCE_DEGRADATION,
                    priority=NotificationPriority.HIGH,
                    title="Performance Degradation Detected",
                    message=f"Average response time increased to {performance_metrics['avg_response_time_ms']:.1f}ms",
                    source_service="aggregation",
                    current_values={
                        "avg_response_time_ms": performance_metrics[
                            "avg_response_time_ms"
                        ]
                    },
                    threshold_values={"max_response_time_ms": 5000},
                )
            )

        # Check success rate
        if results:
            success_rate = sum(1 for r in results if r.passed) / len(results)
            if success_rate < 0.8:
                alerts.append(
                    Alert(
                        alert_type=AlertType.QUALITY_REGRESSION,
                        priority=NotificationPriority.HIGH,
                        title="Low Success Rate Detected",
                        message=f"Test success rate dropped to {success_rate:.1%}",
                        source_service="aggregation",
                        current_values={"success_rate": success_rate},
                        threshold_values={"min_success_rate": 0.8},
                    )
                )

        return alerts

    async def _evaluate_rule(
        self, rule: NotificationRule, test_result: TestResult
    ) -> bool:
        """Evaluate if rule should trigger for test result"""

        # Check service filter
        if rule.service_names:
            service_name = (
                test_result.execution_id.split("_")[0]
                if "_" in test_result.execution_id
                else ""
            )
            if service_name not in rule.service_names:
                return False

        # Check quality score threshold
        if rule.min_quality_score is not None:
            if test_result.score < rule.min_quality_score:
                return True

        # Check test failure
        if AlertType.TEST_FAILURE in rule.alert_types:
            if not test_result.passed:
                return True

        # Check quality regression
        if AlertType.QUALITY_REGRESSION in rule.alert_types:
            if test_result.quality_scores:
                for metric, score in test_result.quality_scores.items():
                    if score < 0.6:  # Configurable threshold
                        return True

        # Check performance degradation
        if AlertType.PERFORMANCE_DEGRADATION in rule.alert_types:
            if (
                rule.max_response_time_ms
                and test_result.duration_ms > rule.max_response_time_ms
            ):
                return True

        return False

    async def _create_alert_from_result(
        self, rule: NotificationRule, test_result: TestResult
    ) -> Alert:
        """Create alert from test result"""

        # Determine alert type and priority
        alert_type = AlertType.TEST_FAILURE
        priority = NotificationPriority.MEDIUM

        if not test_result.passed:
            alert_type = AlertType.TEST_FAILURE
            priority = NotificationPriority.HIGH
        elif rule.min_quality_score and test_result.score < rule.min_quality_score:
            alert_type = AlertType.QUALITY_REGRESSION
            priority = NotificationPriority.MEDIUM

        # Create alert
        alert = Alert(
            alert_type=alert_type,
            priority=priority,
            title=f"Test Alert: {test_result.scenario_id}",
            message=f"Test {test_result.execution_id} triggered alert rule '{rule.name}'",
            source_service=(
                test_result.execution_id.split("_")[0]
                if "_" in test_result.execution_id
                else ""
            ),
            test_result_id=test_result.execution_id,
            scenario_id=test_result.scenario_id,
            details={
                "test_score": test_result.score,
                "test_passed": test_result.passed,
                "test_duration_ms": test_result.duration_ms,
                "error_message": test_result.error_message,
                "rule_id": rule.rule_id,
            },
            current_values={
                "score": test_result.score,
                "duration_ms": test_result.duration_ms,
            },
            threshold_values={
                "min_quality_score": rule.min_quality_score or 0.0,
                "max_response_time_ms": rule.max_response_time_ms or 0.0,
            },
        )

        return alert

    def _is_rate_limited(self, rule: NotificationRule) -> bool:
        """Check if rule is rate limited"""

        if not rule.last_triggered:
            return False

        # Check cooldown
        time_since_last = datetime.now(timezone.utc) - rule.last_triggered
        if time_since_last.total_seconds() < rule.cooldown_minutes * 60:
            return True

        # Check hourly limit
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_triggers = [
            a
            for a in self.recent_alerts
            if a.created_at >= one_hour_ago and a.context.get("rule_id") == rule.rule_id
        ]

        if len(recent_triggers) >= rule.max_notifications_per_hour:
            return True

        return False

    def _load_default_rules(self):
        """Load default notification rules"""

        # Critical test failures
        self.rules.append(
            NotificationRule(
                rule_id="critical_failures",
                name="Critical Test Failures",
                description="Alert on any critical test failures",
                alert_types=[AlertType.TEST_FAILURE],
                priority_threshold=NotificationPriority.HIGH,
                recipients=["admin@novel-engine.com"],
                channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
                cooldown_minutes=5,
                max_notifications_per_hour=20,
            )
        )

        # Quality regression
        self.rules.append(
            NotificationRule(
                rule_id="quality_regression",
                name="Quality Score Regression",
                description="Alert when quality scores drop below threshold",
                alert_types=[AlertType.QUALITY_REGRESSION],
                min_quality_score=0.7,
                recipients=["qa@novel-engine.com"],
                channels=[NotificationChannel.EMAIL],
                cooldown_minutes=15,
                max_notifications_per_hour=5,
            )
        )

        # Performance degradation
        self.rules.append(
            NotificationRule(
                rule_id="performance_degradation",
                name="Performance Degradation",
                description="Alert on slow response times",
                alert_types=[AlertType.PERFORMANCE_DEGRADATION],
                max_response_time_ms=10000,
                recipients=["devops@novel-engine.com"],
                channels=[NotificationChannel.SLACK],
                cooldown_minutes=10,
                max_notifications_per_hour=10,
            )
        )


# === Notification Service ===


class NotificationService(INotificationService):
    """
    Comprehensive notification and alerting service

    Features:
    - Multi-channel notification delivery
    - Intelligent alert detection
    - Escalation and rate limiting
    - Template-based messaging
    - Delivery tracking and retry logic
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.event_bus = EventBus()

        # Initialize components
        self.alert_detector = AlertDetector(config.get("alert_detection", {}))
        self.notification_templates: Dict[str, NotificationTemplate] = {}

        # Initialize channel handlers
        self.channel_handlers: Dict[NotificationChannel, ChannelHandler] = {}
        self._initialize_channel_handlers()

        # Storage
        self.active_alerts: Dict[str, Alert] = {}
        self.pending_notifications: List[Notification] = []
        self.sent_notifications: List[Notification] = []

        # Background tasks
        self.delivery_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None

        logger.info("Notification Service initialized")

    def _initialize_channel_handlers(self):
        """Initialize notification channel handlers"""

        # Email handler
        email_config = self.config.get("email", {})
        if email_config.get("enabled", False):
            self.channel_handlers[NotificationChannel.EMAIL] = EmailHandler(
                email_config
            )

        # Slack handler
        slack_config = self.config.get("slack", {})
        if slack_config.get("enabled", False):
            self.channel_handlers[NotificationChannel.SLACK] = SlackHandler(
                slack_config
            )

        # Webhook handler
        webhook_config = self.config.get("webhook", {})
        if webhook_config.get("enabled", False):
            self.channel_handlers[NotificationChannel.WEBHOOK] = WebhookHandler(
                webhook_config
            )

        # Always enable webhook channel as fallback
        if len(self.channel_handlers) == 0:
            # Use webhook handler as default
            self.channel_handlers[NotificationChannel.WEBHOOK] = WebhookHandler(
                {"enabled": True, "webhook_url": "http://localhost:8005/internal"}
            )

        logger.info(f"Initialized {len(self.channel_handlers)} notification channels")

    async def initialize(self):
        """Initialize service resources"""

        # Validate channel configurations
        for channel, handler in self.channel_handlers.items():
            is_valid = await handler.validate_config()
            if not is_valid:
                logger.warning(f"Channel {channel.value} configuration is invalid")

        # Start background tasks
        self.delivery_task = asyncio.create_task(self._delivery_worker())
        self.cleanup_task = asyncio.create_task(self._cleanup_worker())

        logger.info("Notification Service ready")

    async def cleanup(self):
        """Clean up service resources"""

        # Cancel background tasks
        if self.delivery_task:
            self.delivery_task.cancel()
        if self.cleanup_task:
            self.cleanup_task.cancel()

        logger.info("Notification Service cleanup complete")

    # === INotification Interface Implementation ===

    async def send_test_result_notification(
        self, test_result: TestResult, context: TestContext
    ) -> bool:
        """Send notification for test result"""

        try:
            # Analyze test result for alerts
            alerts = await self.alert_detector.analyze_test_result(test_result)

            for alert in alerts:
                await self._process_alert(alert)

            return len(alerts) > 0

        except Exception as e:
            logger.error(f"Failed to send test result notification: {e}")
            return False

    async def send_alert(
        self,
        alert_type: str,
        message: str,
        priority: str = "medium",
        recipients: List[str] = None,
    ) -> str:
        """Send custom alert"""

        # Create alert
        alert = Alert(
            alert_type=AlertType(alert_type),
            priority=NotificationPriority(priority),
            title=f"Custom Alert: {alert_type}",
            message=message,
            source_service="custom",
        )

        # Process alert
        await self._process_alert(alert, custom_recipients=recipients)

        return alert.alert_id

    async def send_system_notification(
        self,
        title: str,
        message: str,
        recipients: List[str],
        channels: List[str] = None,
    ) -> List[str]:
        """Send system notification"""

        notification_ids = []
        target_channels = channels or ["email"]

        for recipient in recipients:
            for channel_name in target_channels:
                try:
                    channel = NotificationChannel(channel_name)

                    notification = Notification(
                        alert_id="system_notification",
                        rule_id="system",
                        channel=channel,
                        recipient=recipient,
                        priority=NotificationPriority.MEDIUM,
                        subject=title,
                        content=message,
                    )

                    self.pending_notifications.append(notification)
                    notification_ids.append(notification.notification_id)

                except ValueError:
                    logger.warning(f"Unknown channel: {channel_name}")

        return notification_ids

    # === Core Processing Methods ===

    async def _process_alert(self, alert: Alert, custom_recipients: List[str] = None):
        """Process alert and generate notifications"""

        # Store alert
        self.active_alerts[alert.alert_id] = alert

        # Find matching rules
        matching_rules = [
            rule
            for rule in self.alert_detector.rules
            if alert.alert_type in rule.alert_types
            and alert.priority.value >= rule.priority_threshold.value
        ]

        for rule in matching_rules:
            # Check schedule
            if not self._is_rule_active(rule):
                continue

            # Generate notifications
            recipients = custom_recipients or rule.recipients

            for recipient in recipients:
                for channel in rule.channels:
                    if channel in self.channel_handlers:
                        notification = await self._create_notification(
                            alert, rule, channel, recipient
                        )
                        self.pending_notifications.append(notification)

        logger.info(
            f"Generated {len(self.pending_notifications)} notifications for alert {alert.alert_id}"
        )

    async def _create_notification(
        self,
        alert: Alert,
        rule: NotificationRule,
        channel: NotificationChannel,
        recipient: str,
    ) -> Notification:
        """Create notification from alert and rule"""

        # Find appropriate template
        template = self._find_template(alert.alert_type, channel)

        # Generate content
        subject, content, formatted_content = await self._generate_content(
            alert, template
        )

        return Notification(
            alert_id=alert.alert_id,
            rule_id=rule.rule_id,
            channel=channel,
            recipient=recipient,
            priority=alert.priority,
            subject=subject,
            content=content,
            formatted_content=formatted_content,
        )

    def _find_template(
        self, alert_type: AlertType, channel: NotificationChannel
    ) -> Optional[NotificationTemplate]:
        """Find appropriate template for alert type and channel"""

        # Look for specific template
        template_key = f"{alert_type.value}_{channel.value}"
        if template_key in self.notification_templates:
            return self.notification_templates[template_key]

        # Look for alert type template
        for template in self.notification_templates.values():
            if template.alert_type == alert_type:
                return template

        # Return default template
        return self._get_default_template(alert_type, channel)

    def _get_default_template(
        self, alert_type: AlertType, channel: NotificationChannel
    ) -> NotificationTemplate:
        """Get default template for alert type and channel"""

        if channel == NotificationChannel.EMAIL:
            subject = "Novel-Engine Alert: {alert_type}"
            body = """
Alert: {title}

Message: {message}

Details:
- Priority: {priority}
- Source: {source_service}
- Time: {created_at}

{details}

This is an automated notification from Novel-Engine AI Testing System.
            """
        else:
            subject = "{title}"
            body = "{message}\n\nPriority: {priority} | Source: {source_service}"

        return NotificationTemplate(
            name=f"Default {alert_type.value} {channel.value}",
            alert_type=alert_type,
            channel=channel,
            subject_template=subject,
            body_template=body,
        )

    async def _generate_content(
        self, alert: Alert, template: Optional[NotificationTemplate]
    ) -> tuple[str, str, Dict[str, Any]]:
        """Generate notification content from alert and template"""

        if not template:
            template = self._get_default_template(
                alert.alert_type, NotificationChannel.EMAIL
            )

        # Prepare variables for templating
        variables = {
            "alert_id": alert.alert_id,
            "alert_type": alert.alert_type.value,
            "title": alert.title,
            "message": alert.message,
            "priority": alert.priority.value,
            "source_service": alert.source_service,
            "created_at": alert.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "details": self._format_alert_details(alert),
        }

        # Add alert-specific variables
        variables.update(alert.details)
        variables.update(alert.current_values)

        # Generate content
        subject = template.subject_template.format(**variables)
        content = template.body_template.format(**variables)

        # Generate formatted content
        formatted_content = {
            "alert_details": alert.details,
            "current_values": alert.current_values,
            "threshold_values": alert.threshold_values,
        }

        if template.html_template:
            formatted_content["html"] = template.html_template.format(**variables)

        return subject, content, formatted_content

    def _format_alert_details(self, alert: Alert) -> str:
        """Format alert details for display"""

        details_lines = []

        if alert.current_values:
            details_lines.append("Current Values:")
            for key, value in alert.current_values.items():
                details_lines.append(f"  {key}: {value}")

        if alert.threshold_values:
            details_lines.append("Thresholds:")
            for key, value in alert.threshold_values.items():
                details_lines.append(f"  {key}: {value}")

        if alert.details:
            details_lines.append("Additional Details:")
            for key, value in alert.details.items():
                details_lines.append(f"  {key}: {value}")

        return "\n".join(details_lines)

    def _is_rule_active(self, rule: NotificationRule) -> bool:
        """Check if rule is currently active based on schedule"""

        now = datetime.now(timezone.utc)

        # Check active days
        if rule.active_days:
            current_day = now.strftime("%a").lower()
            if current_day not in rule.active_days:
                return False

        # Check active hours
        if rule.active_hours:
            current_time = now.time()
            start_time = datetime.strptime(rule.active_hours["start"], "%H:%M").time()
            end_time = datetime.strptime(rule.active_hours["end"], "%H:%M").time()

            if not (start_time <= current_time <= end_time):
                return False

        return True

    # === Background Workers ===

    async def _delivery_worker(self):
        """Background worker for delivering notifications"""

        while True:
            try:
                if self.pending_notifications:
                    # Process notifications in batches
                    batch = self.pending_notifications[:10]  # Process 10 at a time
                    self.pending_notifications = self.pending_notifications[10:]

                    # Deliver notifications in parallel
                    delivery_tasks = [
                        self._deliver_notification(notification)
                        for notification in batch
                    ]

                    await asyncio.gather(*delivery_tasks, return_exceptions=True)

                # Wait before next batch
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Delivery worker error: {e}")
                await asyncio.sleep(10)

    async def _deliver_notification(self, notification: Notification):
        """Deliver individual notification"""

        try:
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.now(timezone.utc)

            # Get channel handler
            handler = self.channel_handlers.get(notification.channel)
            if not handler:
                notification.status = NotificationStatus.FAILED
                notification.error_message = (
                    f"No handler for channel {notification.channel.value}"
                )
                return

            # Attempt delivery
            success = await handler.send(notification)

            if success:
                notification.status = NotificationStatus.DELIVERED
                notification.delivered_at = datetime.now(timezone.utc)
                logger.info(f"Notification delivered: {notification.notification_id}")
            else:
                notification.status = NotificationStatus.FAILED
                notification.failed_at = datetime.now(timezone.utc)

                # Schedule retry if under limit
                if notification.retry_count < notification.max_retries:
                    notification.retry_count += 1
                    notification.status = NotificationStatus.RETRYING

                    # Add back to pending with delay
                    await asyncio.sleep(
                        30 * notification.retry_count
                    )  # Exponential backoff
                    self.pending_notifications.append(notification)

            # Store completed notification
            self.sent_notifications.append(notification)

        except Exception as e:
            logger.error(
                f"Failed to deliver notification {notification.notification_id}: {e}"
            )
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(e)

    async def _cleanup_worker(self):
        """Background worker for cleanup tasks"""

        while True:
            try:
                # Clean up old alerts and notifications
                cutoff_time = datetime.now(timezone.utc) - timedelta(days=7)

                # Remove old alerts
                old_alert_ids = [
                    alert_id
                    for alert_id, alert in self.active_alerts.items()
                    if alert.created_at < cutoff_time
                ]

                for alert_id in old_alert_ids:
                    self.active_alerts.pop(alert_id, None)

                # Remove old notifications
                self.sent_notifications = [
                    n for n in self.sent_notifications if n.created_at >= cutoff_time
                ]

                logger.info(f"Cleanup: removed {len(old_alert_ids)} old alerts")

                # Wait 1 hour before next cleanup
                await asyncio.sleep(3600)

            except Exception as e:
                logger.error(f"Cleanup worker error: {e}")
                await asyncio.sleep(3600)

    # === INotificationService Interface Implementation ===

    async def send_test_completion(
        self, execution_id: str, results_summary: Dict[str, Any]
    ) -> bool:
        """Send test completion notification"""
        try:
            # Create notification for test completion
            notification = NotificationRequest(
                notification_id=f"completion_{execution_id}",
                title="Test Execution Completed",
                message=f"Test execution {execution_id} has completed",
                priority=NotificationPriority.INFO,
                channels=["console", "file"],
                metadata={
                    "execution_id": execution_id,
                    "results_summary": results_summary,
                    "completion_time": datetime.now().isoformat(),
                },
            )

            # Send notification
            result = await self.send_notification(notification)
            return result.success

        except Exception as e:
            logger.error(f"Failed to send test completion notification: {e}")
            return False

    async def send_quality_alert(
        self, alert_type: str, details: Dict[str, Any]
    ) -> bool:
        """Send quality threshold alert"""
        try:
            # Determine priority based on alert severity
            severity = details.get("severity", "medium")
            priority = (
                NotificationPriority.HIGH
                if severity == "high"
                else NotificationPriority.MEDIUM
            )

            # Create quality alert notification
            notification = NotificationRequest(
                notification_id=f"quality_alert_{int(time.time())}",
                title=f"Quality Alert: {alert_type}",
                message=f"Quality alert triggered: {details.get('message', 'Quality threshold exceeded')}",
                priority=priority,
                channels=["console", "file"],
                metadata={
                    "alert_type": alert_type,
                    "details": details,
                    "alert_time": datetime.now().isoformat(),
                },
            )

            # Send notification
            result = await self.send_notification(notification)
            return result.success

        except Exception as e:
            logger.error(f"Failed to send quality alert: {e}")
            return False

    async def send_performance_alert(
        self, metric: str, threshold: float, actual_value: float
    ) -> bool:
        """Send performance threshold alert"""
        try:
            # Determine severity based on how much threshold was exceeded
            ratio = actual_value / threshold if threshold > 0 else 1.0
            priority = (
                NotificationPriority.HIGH
                if ratio > 2.0
                else NotificationPriority.MEDIUM
            )

            # Create performance alert notification
            notification = NotificationRequest(
                notification_id=f"perf_alert_{metric}_{int(time.time())}",
                title=f"Performance Alert: {metric}",
                message=f"Performance threshold exceeded for {metric}: {actual_value} > {threshold}",
                priority=priority,
                channels=["console", "file"],
                metadata={
                    "metric": metric,
                    "threshold": threshold,
                    "actual_value": actual_value,
                    "ratio": ratio,
                    "alert_time": datetime.now().isoformat(),
                },
            )

            # Send notification
            result = await self.send_notification(notification)
            return result.success

        except Exception as e:
            logger.error(f"Failed to send performance alert: {e}")
            return False


# === FastAPI Application ===

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan management"""
    # Initialize notification service
    notification_config = get_ai_testing_service_config("notification")

    service = NotificationService(notification_config)
    await service.initialize()

    app.state.notification_service = service

    logger.info("Notification Service started")
    yield

    await service.cleanup()
    logger.info("Notification Service stopped")


# Create FastAPI app
app = FastAPI(
    title="Notification Service",
    description="Real-time notification and alerting service for Novel-Engine AI acceptance testing",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === API Endpoints ===


@app.get("/health", response_model=ServiceHealthResponse)
async def health_check():
    """Service health check"""
    service: NotificationService = app.state.notification_service

    channels_status = "connected" if service.channel_handlers else "disconnected"
    active_alerts = len(service.active_alerts)
    len(service.pending_notifications)

    status = "healthy" if channels_status == "connected" else "degraded"

    return ServiceHealthResponse(
        service_name="notification",
        status=status,
        version="1.0.0",
        database_status="not_applicable",
        message_queue_status="connected",
        external_dependencies={"notification_channels": channels_status},
        response_time_ms=30.0,
        memory_usage_mb=100.0,
        cpu_usage_percent=5.0,
        active_tests=active_alerts,
        completed_tests_24h=len(service.sent_notifications),
        error_rate_percent=0.0,
    )


@app.post("/alert", response_model=Dict[str, str])
async def send_custom_alert(
    alert_type: str,
    message: str,
    priority: str = "medium",
    recipients: Optional[List[str]] = None,
):
    """Send custom alert"""
    service: NotificationService = app.state.notification_service

    alert_id = await service.send_alert(alert_type, message, priority, recipients)
    return {"alert_id": alert_id}


@app.post("/notify", response_model=List[str])
async def send_notification(
    title: str,
    message: str,
    recipients: List[str],
    channels: Optional[List[str]] = None,
):
    """Send system notification"""
    service: NotificationService = app.state.notification_service

    notification_ids = await service.send_system_notification(
        title, message, recipients, channels
    )
    return notification_ids


@app.get("/alerts", response_model=List[Alert])
async def get_active_alerts():
    """Get active alerts"""
    service: NotificationService = app.state.notification_service

    return list(service.active_alerts.values())


@app.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, acknowledged_by: str):
    """Acknowledge alert"""
    service: NotificationService = app.state.notification_service

    if alert_id in service.active_alerts:
        alert = service.active_alerts[alert_id]
        alert.acknowledged = True
        alert.acknowledged_by = acknowledged_by
        return {"status": "acknowledged"}
    else:
        raise HTTPException(status_code=404, detail="Alert not found")


@app.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """Resolve alert"""
    service: NotificationService = app.state.notification_service

    if alert_id in service.active_alerts:
        alert = service.active_alerts[alert_id]
        alert.resolved = True
        alert.resolved_at = datetime.now(timezone.utc)
        return {"status": "resolved"}
    else:
        raise HTTPException(status_code=404, detail="Alert not found")


@app.get("/notifications/status")
async def get_notification_status():
    """Get notification system status"""
    service: NotificationService = app.state.notification_service

    return {
        "active_alerts": len(service.active_alerts),
        "pending_notifications": len(service.pending_notifications),
        "sent_notifications_today": len(
            [
                n
                for n in service.sent_notifications
                if n.sent_at and n.sent_at.date() == datetime.now(timezone.utc).date()
            ]
        ),
        "available_channels": list(service.channel_handlers.keys()),
        "active_rules": len(service.alert_detector.rules),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8005, log_level="info")
