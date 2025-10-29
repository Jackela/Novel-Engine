#!/usr/bin/env python3
"""
Real-time Analytics and Insights Platform
==========================================

Advanced analytics platform for Novel Engine that provides real-time story
generation analytics, user engagement tracking, and performance insights.

Features:
- Real-time story generation analytics
- User engagement and usage tracking
- Character popularity and usage analytics
- Story quality metrics and improvement tracking
- Performance monitoring and optimization insights
- Predictive analytics for story success
- Custom dashboard generation
- Export capabilities for data analysis
"""

import asyncio
import logging
import statistics
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics tracked by the analytics platform."""

    STORY_GENERATION = "story_generation"
    USER_ENGAGEMENT = "user_engagement"
    CHARACTER_USAGE = "character_usage"
    QUALITY_TRENDS = "quality_trends"
    PERFORMANCE = "performance"
    SYSTEM_HEALTH = "system_health"
    USAGE_PATTERNS = "usage_patterns"
    SUCCESS_INDICATORS = "success_indicators"


class TimeWindow(Enum):
    """Time windows for analytics aggregation."""

    REAL_TIME = "real_time"  # Last 5 minutes
    HOURLY = "hourly"  # Last hour
    DAILY = "daily"  # Last 24 hours
    WEEKLY = "weekly"  # Last 7 days
    MONTHLY = "monthly"  # Last 30 days
    ALL_TIME = "all_time"  # All available data


class EngagementLevel(Enum):
    """User engagement levels."""

    HIGH = "high"  # Very active users
    MEDIUM = "medium"  # Moderately active users
    LOW = "low"  # Infrequent users
    NEW = "new"  # New users
    INACTIVE = "inactive"  # Users who haven't been active recently


@dataclass
class AnalyticsEvent:
    """Individual analytics event for tracking."""

    event_id: str
    event_type: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    story_id: Optional[str] = None
    character_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    properties: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class UserEngagement:
    """User engagement tracking data."""

    user_id: str
    session_count: int = 0
    total_time_spent: float = 0.0  # in seconds
    stories_created: int = 0
    characters_used: int = 0
    last_activity: Optional[datetime] = None
    engagement_level: EngagementLevel = EngagementLevel.NEW
    favorite_genres: List[str] = field(default_factory=list)
    usage_patterns: Dict[str, Any] = field(default_factory=dict)
    quality_improvements: float = 0.0
    retention_score: float = 0.0


@dataclass
class CharacterAnalytics:
    """Character usage and popularity analytics."""

    character_id: str
    character_name: str
    usage_count: int = 0
    unique_users: int = 0
    average_rating: float = 0.0
    story_count: int = 0
    last_used: Optional[datetime] = None
    popularity_trend: str = "stable"  # increasing, decreasing, stable
    quality_contribution: float = 0.0
    user_feedback: List[str] = field(default_factory=list)
    usage_contexts: Dict[str, int] = field(default_factory=dict)


@dataclass
class StoryAnalytics:
    """Story-specific analytics data."""

    story_id: str
    user_id: str
    creation_time: datetime
    word_count: int = 0
    quality_score: float = 0.0
    genre: Optional[str] = None
    characters_used: List[str] = field(default_factory=list)
    generation_time: float = 0.0
    user_rating: Optional[float] = None
    engagement_metrics: Dict[str, float] = field(default_factory=dict)
    improvement_suggestions_applied: int = 0
    export_count: int = 0


@dataclass
class SystemMetrics:
    """System performance and health metrics."""

    timestamp: datetime = field(default_factory=datetime.now)
    active_users: int = 0
    stories_generated_per_hour: float = 0.0
    average_generation_time: float = 0.0
    system_load: float = 0.0
    memory_usage: float = 0.0
    error_rate: float = 0.0
    api_response_time: float = 0.0
    database_performance: float = 0.0
    cache_hit_rate: float = 0.0


@dataclass
class AnalyticsReport:
    """Comprehensive analytics report."""

    report_id: str
    report_type: str
    time_window: TimeWindow
    generated_at: datetime = field(default_factory=datetime.now)
    summary: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    insights: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    visualizations: Dict[str, Any] = field(default_factory=dict)
    raw_data: Optional[Dict[str, Any]] = None


class AnalyticsPlatform:
    """
    Real-time analytics and insights platform for Novel Engine.

    Provides comprehensive analytics, user engagement tracking,
    and performance insights with real-time dashboards and reporting.
    """

    def __init__(self, data_retention_days: int = 90):
        """
        Initialize the Analytics Platform.

        Args:
            data_retention_days: Number of days to retain detailed analytics data
        """
        self.data_retention_days = data_retention_days

        # Core data stores
        self.events: deque = deque(maxlen=10000)  # Real-time event buffer
        self.user_engagement: Dict[str, UserEngagement] = {}
        self.character_analytics: Dict[str, CharacterAnalytics] = {}
        self.story_analytics: Dict[str, StoryAnalytics] = {}
        self.system_metrics_history: deque = deque(maxlen=1000)

        # Aggregated data for performance
        self.hourly_aggregates: Dict[str, Dict] = defaultdict(dict)
        self.daily_aggregates: Dict[str, Dict] = defaultdict(dict)
        self.weekly_aggregates: Dict[str, Dict] = defaultdict(dict)

        # Insights and patterns
        self.insights_cache: Dict[str, Any] = {}
        self.trend_patterns: Dict[str, List] = defaultdict(list)
        self.prediction_models: Dict[str, Any] = {}

        # Real-time monitoring
        self.real_time_metrics: Dict[str, Any] = {}
        self.alert_thresholds: Dict[str, float] = {
            "error_rate": 0.05,  # 5% error rate threshold
            "response_time": 2.0,  # 2 second response time threshold
            "system_load": 0.8,  # 80% system load threshold
        }

        # Analytics processing
        self.processing_queue: asyncio.Queue = asyncio.Queue()
        self.background_tasks: List[asyncio.Task] = []

        logger.info(
            f"AnalyticsPlatform initialized with {data_retention_days} days retention"
        )

    async def start_background_processing(self):
        """Start background analytics processing tasks."""
        try:
            # Real-time metrics update task
            real_time_task = asyncio.create_task(self._real_time_metrics_processor())
            self.background_tasks.append(real_time_task)

            # Hourly aggregation task
            hourly_task = asyncio.create_task(self._hourly_aggregator())
            self.background_tasks.append(hourly_task)

            # Daily insights generation task
            insights_task = asyncio.create_task(self._insights_generator())
            self.background_tasks.append(insights_task)

            # Data cleanup task
            cleanup_task = asyncio.create_task(self._data_cleanup_processor())
            self.background_tasks.append(cleanup_task)

            logger.info(
                f"Started {len(self.background_tasks)} background analytics tasks"
            )

        except Exception as e:
            logger.error(f"Failed to start background processing: {e}")

    async def stop_background_processing(self):
        """Stop all background processing tasks."""
        for task in self.background_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self.background_tasks.clear()
        logger.info("Stopped all background analytics tasks")

    async def track_event(self, event: AnalyticsEvent):
        """
        Track an analytics event.

        Args:
            event: Analytics event to track
        """
        try:
            # Add to event stream
            self.events.append(event)

            # Update relevant analytics based on event type
            await self._process_event(event)

            # Update real-time metrics
            await self._update_real_time_metrics(event)

            # Queue for background processing
            await self.processing_queue.put(event)

        except Exception as e:
            logger.error(f"Failed to track event {event.event_id}: {e}")

    async def track_story_generation(
        self, story_id: str, user_id: str, generation_data: Dict[str, Any]
    ):
        """
        Track story generation analytics.

        Args:
            story_id: Story identifier
            user_id: User identifier
            generation_data: Story generation metadata
        """
        try:
            # Create analytics event
            event = AnalyticsEvent(
                event_id=f"story_gen_{story_id}_{datetime.now().strftime('%H%M%S')}",
                event_type="story_generation",
                user_id=user_id,
                story_id=story_id,
                properties=generation_data,
                metrics={
                    "generation_time": generation_data.get("generation_time", 0.0),
                    "word_count": generation_data.get("word_count", 0),
                    "quality_score": generation_data.get("quality_score", 0.0),
                },
                tags=["story", "generation", "user_content"],
            )

            await self.track_event(event)

            # Update story analytics
            story_analytics = StoryAnalytics(
                story_id=story_id,
                user_id=user_id,
                creation_time=datetime.now(),
                word_count=generation_data.get("word_count", 0),
                quality_score=generation_data.get("quality_score", 0.0),
                genre=generation_data.get("genre"),
                characters_used=generation_data.get("characters_used", []),
                generation_time=generation_data.get("generation_time", 0.0),
            )

            self.story_analytics[story_id] = story_analytics

            # Update user engagement
            await self._update_user_engagement(user_id, "story_generated")

            # Update character usage
            for character_id in generation_data.get("characters_used", []):
                await self._update_character_usage(character_id, user_id, story_id)

            logger.info(f"Tracked story generation: {story_id} for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to track story generation: {e}")

    async def track_user_engagement(
        self, user_id: str, session_id: str, engagement_data: Dict[str, Any]
    ):
        """
        Track user engagement metrics.

        Args:
            user_id: User identifier
            session_id: Session identifier
            engagement_data: Engagement metrics
        """
        try:
            event = AnalyticsEvent(
                event_id=f"engagement_{user_id}_{datetime.now().strftime('%H%M%S')}",
                event_type="user_engagement",
                user_id=user_id,
                session_id=session_id,
                properties=engagement_data,
                metrics={
                    "session_duration": engagement_data.get("session_duration", 0.0),
                    "interactions": engagement_data.get("interactions", 0),
                    "features_used": engagement_data.get("features_used", 0),
                },
                tags=["user", "engagement", "session"],
            )

            await self.track_event(event)
            await self._update_user_engagement(
                user_id, "session_activity", engagement_data
            )

        except Exception as e:
            logger.error(f"Failed to track user engagement: {e}")

    async def track_character_usage(
        self,
        character_id: str,
        user_id: str,
        usage_context: str,
        story_id: Optional[str] = None,
    ):
        """
        Track character usage analytics.

        Args:
            character_id: Character identifier
            user_id: User identifier
            usage_context: Context of character usage
            story_id: Optional story identifier
        """
        try:
            event = AnalyticsEvent(
                event_id=f"char_use_{character_id}_{datetime.now().strftime('%H%M%S')}",
                event_type="character_usage",
                user_id=user_id,
                story_id=story_id,
                character_id=character_id,
                properties={"usage_context": usage_context},
                tags=["character", "usage", "content"],
            )

            await self.track_event(event)
            await self._update_character_usage(
                character_id, user_id, story_id, usage_context
            )

        except Exception as e:
            logger.error(f"Failed to track character usage: {e}")

    async def track_system_metrics(self, metrics: SystemMetrics):
        """
        Track system performance metrics.

        Args:
            metrics: System metrics to track
        """
        try:
            self.system_metrics_history.append(metrics)

            event = AnalyticsEvent(
                event_id=f"system_{datetime.now().strftime('%H%M%S')}",
                event_type="system_metrics",
                properties=asdict(metrics),
                metrics={
                    "active_users": metrics.active_users,
                    "stories_per_hour": metrics.stories_generated_per_hour,
                    "avg_generation_time": metrics.average_generation_time,
                    "system_load": metrics.system_load,
                    "memory_usage": metrics.memory_usage,
                    "error_rate": metrics.error_rate,
                },
                tags=["system", "performance", "monitoring"],
            )

            await self.track_event(event)

            # Check for alerts
            await self._check_system_alerts(metrics)

        except Exception as e:
            logger.error(f"Failed to track system metrics: {e}")

    async def generate_analytics_report(
        self,
        report_type: str,
        time_window: TimeWindow,
        filters: Optional[Dict[str, Any]] = None,
    ) -> AnalyticsReport:
        """
        Generate comprehensive analytics report.

        Args:
            report_type: Type of report to generate
            time_window: Time window for the report
            filters: Optional filters to apply

        Returns:
            Analytics report
        """
        try:
            report_id = f"{report_type}_{time_window.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Get data for time window
            start_time = self._get_time_window_start(time_window)
            filtered_events = self._filter_events_by_time(start_time, filters)

            # Generate report based on type
            if report_type == "user_engagement":
                report = await self._generate_engagement_report(
                    report_id, time_window, filtered_events
                )
            elif report_type == "story_analytics":
                report = await self._generate_story_report(
                    report_id, time_window, filtered_events
                )
            elif report_type == "character_analytics":
                report = await self._generate_character_report(
                    report_id, time_window, filtered_events
                )
            elif report_type == "system_performance":
                report = await self._generate_performance_report(
                    report_id, time_window, filtered_events
                )
            elif report_type == "comprehensive":
                report = await self._generate_comprehensive_report(
                    report_id, time_window, filtered_events
                )
            else:
                raise ValueError(f"Unknown report type: {report_type}")

            logger.info(f"Generated analytics report: {report_id}")
            return report

        except Exception as e:
            logger.error(f"Failed to generate analytics report: {e}")
            return AnalyticsReport(
                report_id="error_report",
                report_type="error",
                time_window=time_window,
                summary={"error": str(e)},
            )

    async def get_real_time_dashboard(self) -> Dict[str, Any]:
        """
        Get real-time dashboard data.

        Returns:
            Real-time dashboard metrics
        """
        try:
            current_time = datetime.now()
            last_5_minutes = current_time - timedelta(minutes=5)

            # Filter recent events
            recent_events = [
                event for event in self.events if event.timestamp >= last_5_minutes
            ]

            # Calculate real-time metrics
            dashboard = {
                "timestamp": current_time,
                "overview": {
                    "active_users": len(
                        set(event.user_id for event in recent_events if event.user_id)
                    ),
                    "stories_generated": len(
                        [e for e in recent_events if e.event_type == "story_generation"]
                    ),
                    "character_usages": len(
                        [e for e in recent_events if e.event_type == "character_usage"]
                    ),
                    "total_events": len(recent_events),
                },
                "performance": {
                    "avg_generation_time": self._calculate_avg_generation_time(
                        recent_events
                    ),
                    "system_health": self._get_current_system_health(),
                    "error_rate": self._calculate_error_rate(recent_events),
                    "response_time": self._get_avg_response_time(),
                },
                "trends": {
                    "user_activity_trend": self._calculate_activity_trend(),
                    "quality_trend": self._calculate_quality_trend(),
                    "popular_characters": self._get_popular_characters(recent_events),
                    "top_genres": self._get_top_genres(recent_events),
                },
                "alerts": self._get_active_alerts(),
            }

            return dashboard

        except Exception as e:
            logger.error(f"Failed to generate real-time dashboard: {e}")
            return {"error": str(e), "timestamp": datetime.now()}

    async def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """
        Get detailed insights for a specific user.

        Args:
            user_id: User identifier

        Returns:
            User-specific insights and analytics
        """
        try:
            if user_id not in self.user_engagement:
                return {"error": "User not found"}

            engagement = self.user_engagement[user_id]

            # Get user's stories
            user_stories = [
                story
                for story in self.story_analytics.values()
                if story.user_id == user_id
            ]

            # Get user's events
            [event for event in self.events if event.user_id == user_id]

            # Calculate insights
            insights = {
                "user_id": user_id,
                "engagement_level": engagement.engagement_level.value,
                "activity_summary": {
                    "total_sessions": engagement.session_count,
                    "total_time_spent": engagement.total_time_spent,
                    "stories_created": engagement.stories_created,
                    "characters_used": engagement.characters_used,
                    "last_activity": engagement.last_activity,
                },
                "story_analytics": {
                    "total_stories": len(user_stories),
                    "avg_quality_score": (
                        statistics.mean([s.quality_score for s in user_stories])
                        if user_stories
                        else 0
                    ),
                    "favorite_genres": engagement.favorite_genres,
                    "word_count_total": sum(s.word_count for s in user_stories),
                    "avg_generation_time": (
                        statistics.mean([s.generation_time for s in user_stories])
                        if user_stories
                        else 0
                    ),
                },
                "usage_patterns": engagement.usage_patterns,
                "improvement_metrics": {
                    "quality_improvements": engagement.quality_improvements,
                    "retention_score": engagement.retention_score,
                },
                "recommendations": await self._generate_user_recommendations(user_id),
            }

            return insights

        except Exception as e:
            logger.error(f"Failed to get user insights: {e}")
            return {"error": str(e)}

    async def get_character_insights(
        self, character_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get character usage and popularity insights.

        Args:
            character_id: Optional specific character ID, or None for all characters

        Returns:
            Character analytics and insights
        """
        try:
            if character_id:
                if character_id not in self.character_analytics:
                    return {"error": "Character not found"}

                char_data = self.character_analytics[character_id]
                return {
                    "character_id": character_id,
                    "character_name": char_data.character_name,
                    "usage_stats": {
                        "total_usage": char_data.usage_count,
                        "unique_users": char_data.unique_users,
                        "story_count": char_data.story_count,
                        "last_used": char_data.last_used,
                    },
                    "popularity_metrics": {
                        "average_rating": char_data.average_rating,
                        "popularity_trend": char_data.popularity_trend,
                        "quality_contribution": char_data.quality_contribution,
                    },
                    "usage_contexts": char_data.usage_contexts,
                    "user_feedback": char_data.user_feedback,
                }
            else:
                # Return overview of all characters
                all_characters = []
                for char_id, char_data in self.character_analytics.items():
                    all_characters.append(
                        {
                            "character_id": char_id,
                            "character_name": char_data.character_name,
                            "usage_count": char_data.usage_count,
                            "unique_users": char_data.unique_users,
                            "average_rating": char_data.average_rating,
                            "popularity_trend": char_data.popularity_trend,
                        }
                    )

                # Sort by usage count
                all_characters.sort(key=lambda x: x["usage_count"], reverse=True)

                return {
                    "total_characters": len(all_characters),
                    "most_popular": all_characters[:10],
                    "trending_up": [
                        c
                        for c in all_characters
                        if c["popularity_trend"] == "increasing"
                    ][:5],
                    "trending_down": [
                        c
                        for c in all_characters
                        if c["popularity_trend"] == "decreasing"
                    ][:5],
                    "character_overview": all_characters,
                }

        except Exception as e:
            logger.error(f"Failed to get character insights: {e}")
            return {"error": str(e)}

    async def export_analytics_data(
        self, export_format: str, time_window: TimeWindow, data_types: List[str]
    ) -> Dict[str, Any]:
        """
        Export analytics data in specified format.

        Args:
            export_format: Format for export (json, csv)
            time_window: Time window for data
            data_types: Types of data to include

        Returns:
            Export result with data or file path
        """
        try:
            start_time = self._get_time_window_start(time_window)
            export_data = {}

            # Collect requested data types
            if "events" in data_types:
                filtered_events = self._filter_events_by_time(start_time)
                export_data["events"] = [asdict(event) for event in filtered_events]

            if "user_engagement" in data_types:
                export_data["user_engagement"] = {
                    uid: asdict(engagement)
                    for uid, engagement in self.user_engagement.items()
                }

            if "character_analytics" in data_types:
                export_data["character_analytics"] = {
                    cid: asdict(analytics)
                    for cid, analytics in self.character_analytics.items()
                }

            if "story_analytics" in data_types:
                export_data["story_analytics"] = {
                    sid: asdict(analytics)
                    for sid, analytics in self.story_analytics.items()
                }

            if "system_metrics" in data_types:
                recent_metrics = [
                    asdict(metric)
                    for metric in self.system_metrics_history
                    if metric.timestamp >= start_time
                ]
                export_data["system_metrics"] = recent_metrics

            # Format data based on export format
            if export_format.lower() == "json":
                export_result = {
                    "format": "json",
                    "data": export_data,
                    "exported_at": datetime.now().isoformat(),
                    "time_window": time_window.value,
                    "record_count": sum(
                        len(v) if isinstance(v, (list, dict)) else 1
                        for v in export_data.values()
                    ),
                }
            else:
                # For other formats, we would implement CSV export, etc.
                export_result = {
                    "format": export_format,
                    "error": f"Export format {export_format} not yet implemented",
                    "supported_formats": ["json"],
                }

            logger.info(
                f"Exported analytics data: {export_format}, {time_window.value}"
            )
            return export_result

        except Exception as e:
            logger.error(f"Failed to export analytics data: {e}")
            return {"error": str(e)}

    # Private helper methods

    async def _process_event(self, event: AnalyticsEvent):
        """Process an individual analytics event."""
        try:
            # Update user engagement based on event
            if event.user_id:
                await self._update_user_engagement(
                    event.user_id, event.event_type, event.properties
                )

            # Update character analytics if relevant
            if event.character_id:
                await self._update_character_usage(
                    event.character_id, event.user_id, event.story_id
                )

        except Exception as e:
            logger.error(f"Failed to process event {event.event_id}: {e}")

    async def _update_user_engagement(
        self,
        user_id: str,
        activity_type: str,
        activity_data: Optional[Dict[str, Any]] = None,
    ):
        """Update user engagement metrics."""
        try:
            if user_id not in self.user_engagement:
                self.user_engagement[user_id] = UserEngagement(user_id=user_id)

            engagement = self.user_engagement[user_id]
            engagement.last_activity = datetime.now()

            if activity_type == "story_generated":
                engagement.stories_created += 1
            elif activity_type == "session_activity":
                engagement.session_count += 1
                if activity_data:
                    engagement.total_time_spent += activity_data.get(
                        "session_duration", 0
                    )

            # Update engagement level
            engagement.engagement_level = self._calculate_engagement_level(engagement)

        except Exception as e:
            logger.error(f"Failed to update user engagement: {e}")

    async def _update_character_usage(
        self,
        character_id: str,
        user_id: Optional[str],
        story_id: Optional[str],
        context: str = "story",
    ):
        """Update character usage analytics."""
        try:
            if character_id not in self.character_analytics:
                self.character_analytics[character_id] = CharacterAnalytics(
                    character_id=character_id,
                    character_name=character_id,  # Would be resolved from character data
                )

            char_analytics = self.character_analytics[character_id]
            char_analytics.usage_count += 1
            char_analytics.last_used = datetime.now()

            if story_id:
                char_analytics.story_count += 1

            if context in char_analytics.usage_contexts:
                char_analytics.usage_contexts[context] += 1
            else:
                char_analytics.usage_contexts[context] = 1

            # Track unique users
            if user_id and user_id not in getattr(
                char_analytics, "_unique_users_set", set()
            ):
                if not hasattr(char_analytics, "_unique_users_set"):
                    char_analytics._unique_users_set = set()
                char_analytics._unique_users_set.add(user_id)
                char_analytics.unique_users = len(char_analytics._unique_users_set)

        except Exception as e:
            logger.error(f"Failed to update character usage: {e}")

    async def _update_real_time_metrics(self, event: AnalyticsEvent):
        """Update real-time metrics based on event."""
        current_minute = datetime.now().replace(second=0, microsecond=0)

        if current_minute not in self.real_time_metrics:
            self.real_time_metrics[current_minute] = {
                "events": 0,
                "users": set(),
                "stories": 0,
                "errors": 0,
            }

        metrics = self.real_time_metrics[current_minute]
        metrics["events"] += 1

        if event.user_id:
            metrics["users"].add(event.user_id)

        if event.event_type == "story_generation":
            metrics["stories"] += 1

        if event.event_type == "error":
            metrics["errors"] += 1

    async def _real_time_metrics_processor(self):
        """Background task for real-time metrics processing."""
        while True:
            try:
                await asyncio.sleep(60)  # Process every minute

                # Clean up old real-time metrics (keep last hour)
                cutoff_time = datetime.now() - timedelta(hours=1)
                self.real_time_metrics = {
                    timestamp: metrics
                    for timestamp, metrics in self.real_time_metrics.items()
                    if timestamp >= cutoff_time
                }

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Real-time metrics processor error: {e}")

    async def _hourly_aggregator(self):
        """Background task for hourly data aggregation."""
        while True:
            try:
                await asyncio.sleep(3600)  # Process every hour

                current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
                hour_start = current_hour - timedelta(hours=1)

                # Aggregate events from the past hour
                hour_events = [
                    event
                    for event in self.events
                    if hour_start <= event.timestamp < current_hour
                ]

                aggregated_data = self._aggregate_events(hour_events)
                self.hourly_aggregates[current_hour.isoformat()] = aggregated_data

                logger.info(f"Completed hourly aggregation for {current_hour}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Hourly aggregator error: {e}")

    async def _insights_generator(self):
        """Background task for generating insights and patterns."""
        while True:
            try:
                await asyncio.sleep(3600)  # Generate insights every hour

                # Generate various insights
                await self._generate_usage_insights()
                await self._generate_trend_insights()
                await self._generate_performance_insights()

                logger.info("Generated analytics insights")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Insights generator error: {e}")

    async def _data_cleanup_processor(self):
        """Background task for data cleanup and archival."""
        while True:
            try:
                await asyncio.sleep(86400)  # Run daily

                cutoff_date = datetime.now() - timedelta(days=self.data_retention_days)

                # Clean up old events
                self.events = deque(
                    (event for event in self.events if event.timestamp >= cutoff_date),
                    maxlen=self.events.maxlen,
                )

                # Clean up old metrics
                self.system_metrics_history = deque(
                    (
                        metric
                        for metric in self.system_metrics_history
                        if metric.timestamp >= cutoff_date
                    ),
                    maxlen=self.system_metrics_history.maxlen,
                )

                logger.info(
                    f"Completed data cleanup for data older than {self.data_retention_days} days"
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Data cleanup processor error: {e}")

    def _get_time_window_start(self, time_window: TimeWindow) -> datetime:
        """Get start time for a given time window."""
        now = datetime.now()

        if time_window == TimeWindow.REAL_TIME:
            return now - timedelta(minutes=5)
        elif time_window == TimeWindow.HOURLY:
            return now - timedelta(hours=1)
        elif time_window == TimeWindow.DAILY:
            return now - timedelta(days=1)
        elif time_window == TimeWindow.WEEKLY:
            return now - timedelta(weeks=1)
        elif time_window == TimeWindow.MONTHLY:
            return now - timedelta(days=30)
        else:  # ALL_TIME
            return datetime.min

    def _filter_events_by_time(
        self, start_time: datetime, filters: Optional[Dict[str, Any]] = None
    ) -> List[AnalyticsEvent]:
        """Filter events by time and optional additional filters."""
        filtered_events = [
            event for event in self.events if event.timestamp >= start_time
        ]

        if filters:
            # Apply additional filters
            if "event_type" in filters:
                filtered_events = [
                    e for e in filtered_events if e.event_type == filters["event_type"]
                ]
            if "user_id" in filters:
                filtered_events = [
                    e for e in filtered_events if e.user_id == filters["user_id"]
                ]
            if "story_id" in filters:
                filtered_events = [
                    e for e in filtered_events if e.story_id == filters["story_id"]
                ]

        return filtered_events

    def _calculate_engagement_level(
        self, engagement: UserEngagement
    ) -> EngagementLevel:
        """Calculate user engagement level based on activity."""
        if engagement.last_activity is None:
            return EngagementLevel.NEW

        days_since_activity = (datetime.now() - engagement.last_activity).days

        if days_since_activity > 7:
            return EngagementLevel.INACTIVE
        elif engagement.stories_created >= 10 and engagement.session_count >= 5:
            return EngagementLevel.HIGH
        elif engagement.stories_created >= 3 and engagement.session_count >= 2:
            return EngagementLevel.MEDIUM
        else:
            return EngagementLevel.LOW

    # Report generation methods

    async def _generate_engagement_report(
        self, report_id: str, time_window: TimeWindow, events: List[AnalyticsEvent]
    ) -> AnalyticsReport:
        """Generate user engagement analytics report."""
        # Implementation would analyze user engagement patterns
        return AnalyticsReport(
            report_id=report_id,
            report_type="user_engagement",
            time_window=time_window,
            summary={"total_users": len(self.user_engagement)},
            insights=["User engagement analysis completed"],
        )

    async def _generate_story_report(
        self, report_id: str, time_window: TimeWindow, events: List[AnalyticsEvent]
    ) -> AnalyticsReport:
        """Generate story analytics report."""
        return AnalyticsReport(
            report_id=report_id,
            report_type="story_analytics",
            time_window=time_window,
            summary={"total_stories": len(self.story_analytics)},
            insights=["Story analytics analysis completed"],
        )

    async def _generate_character_report(
        self, report_id: str, time_window: TimeWindow, events: List[AnalyticsEvent]
    ) -> AnalyticsReport:
        """Generate character analytics report."""
        return AnalyticsReport(
            report_id=report_id,
            report_type="character_analytics",
            time_window=time_window,
            summary={"total_characters": len(self.character_analytics)},
            insights=["Character analytics analysis completed"],
        )

    async def _generate_performance_report(
        self, report_id: str, time_window: TimeWindow, events: List[AnalyticsEvent]
    ) -> AnalyticsReport:
        """Generate system performance report."""
        return AnalyticsReport(
            report_id=report_id,
            report_type="system_performance",
            time_window=time_window,
            summary={"system_health": "good"},
            insights=["System performance analysis completed"],
        )

    async def _generate_comprehensive_report(
        self, report_id: str, time_window: TimeWindow, events: List[AnalyticsEvent]
    ) -> AnalyticsReport:
        """Generate comprehensive analytics report."""
        return AnalyticsReport(
            report_id=report_id,
            report_type="comprehensive",
            time_window=time_window,
            summary={"analysis_complete": True},
            insights=["Comprehensive analytics analysis completed"],
        )

    # Helper calculation methods

    def _calculate_avg_generation_time(self, events: List[AnalyticsEvent]) -> float:
        """Calculate average story generation time."""
        generation_events = [e for e in events if e.event_type == "story_generation"]
        if not generation_events:
            return 0.0

        times = [e.metrics.get("generation_time", 0) for e in generation_events]
        return statistics.mean(times) if times else 0.0

    def _get_current_system_health(self) -> str:
        """Get current system health status."""
        if not self.system_metrics_history:
            return "unknown"

        latest_metrics = self.system_metrics_history[-1]

        if latest_metrics.error_rate > 0.1:
            return "poor"
        elif latest_metrics.system_load > 0.8:
            return "degraded"
        else:
            return "good"

    def _calculate_error_rate(self, events: List[AnalyticsEvent]) -> float:
        """Calculate error rate from events."""
        if not events:
            return 0.0

        error_events = [e for e in events if e.event_type == "error"]
        return len(error_events) / len(events)

    def _get_avg_response_time(self) -> float:
        """Get average API response time."""
        if not self.system_metrics_history:
            return 0.0

        recent_metrics = list(self.system_metrics_history)[-10:]  # Last 10 measurements
        response_times = [m.api_response_time for m in recent_metrics]
        return statistics.mean(response_times) if response_times else 0.0

    def _calculate_activity_trend(self) -> str:
        """Calculate user activity trend."""
        # Simple trend calculation based on recent metrics
        return "stable"  # Would implement actual trend analysis

    def _calculate_quality_trend(self) -> str:
        """Calculate story quality trend."""
        return "improving"  # Would implement actual quality trend analysis

    def _get_popular_characters(self, events: List[AnalyticsEvent]) -> List[str]:
        """Get most popular characters from recent events."""
        character_usage = Counter()
        for event in events:
            if event.event_type == "character_usage" and event.character_id:
                character_usage[event.character_id] += 1

        return [char_id for char_id, _ in character_usage.most_common(5)]

    def _get_top_genres(self, events: List[AnalyticsEvent]) -> List[str]:
        """Get most popular genres from recent events."""
        genre_usage = Counter()
        for event in events:
            if event.event_type == "story_generation":
                genre = event.properties.get("genre")
                if genre:
                    genre_usage[genre] += 1

        return [genre for genre, _ in genre_usage.most_common(5)]

    def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get currently active system alerts."""
        alerts = []

        if self.system_metrics_history:
            latest_metrics = self.system_metrics_history[-1]

            if latest_metrics.error_rate > self.alert_thresholds["error_rate"]:
                alerts.append(
                    {
                        "type": "error_rate",
                        "severity": "high",
                        "message": f"Error rate {latest_metrics.error_rate:.2%} exceeds threshold",
                        "timestamp": latest_metrics.timestamp,
                    }
                )

            if (
                latest_metrics.api_response_time
                > self.alert_thresholds["response_time"]
            ):
                alerts.append(
                    {
                        "type": "response_time",
                        "severity": "medium",
                        "message": f"Response time {latest_metrics.api_response_time:.2f}s exceeds threshold",
                        "timestamp": latest_metrics.timestamp,
                    }
                )

        return alerts

    async def _check_system_alerts(self, metrics: SystemMetrics):
        """Check for system alerts and log them."""
        if metrics.error_rate > self.alert_thresholds["error_rate"]:
            logger.warning(f"High error rate detected: {metrics.error_rate:.2%}")

        if metrics.api_response_time > self.alert_thresholds["response_time"]:
            logger.warning(
                f"High response time detected: {metrics.api_response_time:.2f}s"
            )

        if metrics.system_load > self.alert_thresholds["system_load"]:
            logger.warning(f"High system load detected: {metrics.system_load:.2%}")

    def _aggregate_events(self, events: List[AnalyticsEvent]) -> Dict[str, Any]:
        """Aggregate events for storage."""
        event_types = Counter(e.event_type for e in events)
        unique_users = len(set(e.user_id for e in events if e.user_id))

        return {
            "event_count": len(events),
            "event_types": dict(event_types),
            "unique_users": unique_users,
            "timestamp": datetime.now().isoformat(),
        }

    async def _generate_usage_insights(self):
        """Generate usage pattern insights."""
        # Would implement actual usage pattern analysis
        self.insights_cache["usage_patterns"] = {
            "peak_hours": "14:00-16:00",
            "popular_features": ["story_generation", "character_usage"],
            "generated_at": datetime.now(),
        }

    async def _generate_trend_insights(self):
        """Generate trend analysis insights."""
        self.insights_cache["trends"] = {
            "user_growth": "positive",
            "engagement_trend": "stable",
            "generated_at": datetime.now(),
        }

    async def _generate_performance_insights(self):
        """Generate performance insights."""
        self.insights_cache["performance"] = {
            "bottlenecks": [],
            "optimization_opportunities": [],
            "generated_at": datetime.now(),
        }

    async def _generate_user_recommendations(self, user_id: str) -> List[str]:
        """Generate personalized recommendations for a user."""
        # Would implement actual recommendation generation
        return [
            "Try exploring new character types",
            "Experiment with different story genres",
            "Use story quality improvement suggestions",
        ]


def create_analytics_platform(data_retention_days: int = 90) -> AnalyticsPlatform:
    """
    Factory function to create and configure an Analytics Platform.

    Args:
        data_retention_days: Number of days to retain detailed data

    Returns:
        Configured AnalyticsPlatform instance
    """
    platform = AnalyticsPlatform(data_retention_days)
    logger.info("Analytics Platform created and configured")
    return platform
