"""
Results Aggregation Service

Comprehensive test results aggregation and analysis service for Novel-Engine AI acceptance testing.
Collects, analyzes, and reports results from all testing services with intelligent insights.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import httpx

# Import Novel-Engine patterns
try:
    from config_loader import get_config
    from src.event_bus import EventBus
except ImportError:
    # Fallback for testing
    get_config = lambda: None
    EventBus = lambda: None

# Import AI testing configuration
from ai_testing_config import get_ai_testing_service_config

# Import AI testing contracts
from ai_testing.interfaces.service_contracts import (
    IResultsAggregation, TestResult, TestExecution, TestContext, 
    QualityMetric, TestStatus, ServiceHealthResponse, TestType
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Results Aggregation Models ===

class ReportFormat(str, Enum):
    """Report output formats"""
    JSON = "json"
    HTML = "html"
    PDF = "pdf"
    CSV = "csv"
    MARKDOWN = "markdown"

class AggregationPeriod(str, Enum):
    """Time periods for aggregation"""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    CUSTOM = "custom"

class TrendDirection(str, Enum):
    """Trend analysis directions"""
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    VOLATILE = "volatile"

@dataclass
class TestSummary:
    """Summary statistics for a group of tests"""
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    avg_score: float = 0.0
    avg_duration_ms: float = 0.0
    
    # Quality metrics summary
    quality_scores: Dict[QualityMetric, float] = field(default_factory=dict)
    
    # Performance summary
    avg_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    success_rate: float = 0.0
    
    # Trend analysis
    trend_direction: TrendDirection = TrendDirection.STABLE
    trend_confidence: float = 0.0

class TestTrend(BaseModel):
    """Test trend analysis"""
    metric_name: str
    time_period: str
    trend_direction: TrendDirection
    confidence: float = Field(..., ge=0.0, le=1.0)
    
    # Data points
    timestamps: List[datetime] = Field(default_factory=list)
    values: List[float] = Field(default_factory=list)
    
    # Statistical analysis
    linear_regression_slope: float = 0.0
    correlation_coefficient: float = 0.0
    variance: float = 0.0
    
    # Insights
    insights: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

class QualityInsight(BaseModel):
    """AI quality insight analysis"""
    insight_type: str  # "improvement", "regression", "pattern", "anomaly"
    confidence: float = Field(..., ge=0.0, le=1.0)
    title: str
    description: str
    
    # Supporting data
    affected_metrics: List[QualityMetric] = Field(default_factory=list)
    time_period: str = ""
    evidence: List[str] = Field(default_factory=list)
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list)
    priority: str = "medium"  # low, medium, high, critical

class AggregatedResults(BaseModel):
    """Comprehensive aggregated test results"""
    aggregation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    aggregation_period: AggregationPeriod
    start_time: datetime
    end_time: datetime
    
    # Overall summary
    overall_summary: TestSummary
    
    # Test type breakdowns
    test_type_summaries: Dict[TestType, TestSummary] = Field(default_factory=dict)
    
    # Service-specific results
    service_summaries: Dict[str, TestSummary] = Field(default_factory=dict)
    
    # Trend analysis
    trends: List[TestTrend] = Field(default_factory=list)
    
    # Quality insights
    quality_insights: List[QualityInsight] = Field(default_factory=list)
    
    # Performance analysis
    performance_summary: Dict[str, float] = Field(default_factory=dict)
    
    # Top issues and successes
    top_failures: List[Dict[str, Any]] = Field(default_factory=list)
    top_performers: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list)
    
    # Metadata
    generation_time: datetime = Field(default_factory=datetime.utcnow)
    data_completeness: float = Field(default=1.0, ge=0.0, le=1.0)

class ReportRequest(BaseModel):
    """Request for generating aggregated report"""
    report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    report_format: ReportFormat = ReportFormat.JSON
    
    # Time period
    aggregation_period: AggregationPeriod = AggregationPeriod.DAY
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Filters
    test_types: List[TestType] = Field(default_factory=list)
    service_names: List[str] = Field(default_factory=list)
    quality_metrics: List[QualityMetric] = Field(default_factory=list)
    
    # Analysis options
    include_trends: bool = True
    include_quality_insights: bool = True
    include_performance_analysis: bool = True
    include_recommendations: bool = True
    
    # Output options
    detailed_breakdown: bool = True
    include_charts: bool = True
    max_records: int = 1000

# === Results Analyzer ===

class ResultsAnalyzer:
    """
    Advanced results analysis engine
    
    Features:
    - Statistical trend analysis
    - Quality pattern recognition
    - Performance regression detection
    - Anomaly detection
    - Predictive insights
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Analysis thresholds
        self.trend_detection_window = config.get("trend_detection_window_days", 7)
        self.anomaly_threshold = config.get("anomaly_threshold", 2.0)  # Standard deviations
        self.min_data_points = config.get("min_data_points_for_trend", 5)
        
        logger.info("Results Analyzer initialized")
    
    def analyze_trends(
        self,
        results: List[TestResult],
        time_window_days: int = 7
    ) -> List[TestTrend]:
        """Analyze trends in test results"""
        
        trends = []
        
        if len(results) < self.min_data_points:
            logger.warning(f"Insufficient data points for trend analysis: {len(results)}")
            return trends
        
        # Group results by time
        time_series_data = self._create_time_series(results, time_window_days)
        
        # Analyze different metrics
        metric_trends = [
            ("overall_score", "Overall Test Quality"),
            ("duration_ms", "Test Execution Time"),
            ("success_rate", "Test Success Rate")
        ]
        
        for metric_key, metric_name in metric_trends:
            trend = self._analyze_metric_trend(time_series_data, metric_key, metric_name)
            if trend:
                trends.append(trend)
        
        # Analyze quality metrics trends
        quality_trends = self._analyze_quality_metrics_trends(results)
        trends.extend(quality_trends)
        
        return trends
    
    def detect_quality_insights(
        self,
        results: List[TestResult],
        historical_results: List[TestResult] = None
    ) -> List[QualityInsight]:
        """Detect quality insights and patterns"""
        
        insights = []
        
        # Recent performance analysis
        recent_insights = self._analyze_recent_performance(results)
        insights.extend(recent_insights)
        
        # Pattern detection
        pattern_insights = self._detect_quality_patterns(results)
        insights.extend(pattern_insights)
        
        # Comparative analysis
        if historical_results:
            comparative_insights = self._compare_with_historical(results, historical_results)
            insights.extend(comparative_insights)
        
        # Anomaly detection
        anomaly_insights = self._detect_anomalies(results)
        insights.extend(anomaly_insights)
        
        return insights
    
    def _create_time_series(
        self,
        results: List[TestResult],
        time_window_days: int
    ) -> Dict[datetime, Dict[str, float]]:
        """Create time series data from results"""
        
        # Filter to time window
        cutoff_time = datetime.utcnow() - timedelta(days=time_window_days)
        recent_results = [r for r in results if r.timestamp and r.timestamp >= cutoff_time]
        
        # Group by day
        time_series = {}
        
        for result in recent_results:
            if not result.timestamp:
                continue
            
            day_key = result.timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            
            if day_key not in time_series:
                time_series[day_key] = {
                    "scores": [],
                    "durations": [],
                    "success_count": 0,
                    "total_count": 0
                }
            
            time_series[day_key]["scores"].append(result.score)
            time_series[day_key]["durations"].append(result.duration_ms)
            time_series[day_key]["total_count"] += 1
            if result.passed:
                time_series[day_key]["success_count"] += 1
        
        # Calculate daily aggregates
        aggregated_series = {}
        for day, data in time_series.items():
            aggregated_series[day] = {
                "overall_score": statistics.mean(data["scores"]) if data["scores"] else 0.0,
                "duration_ms": statistics.mean(data["durations"]) if data["durations"] else 0.0,
                "success_rate": data["success_count"] / data["total_count"] if data["total_count"] > 0 else 0.0
            }
        
        return aggregated_series
    
    def _analyze_metric_trend(
        self,
        time_series_data: Dict[datetime, Dict[str, float]],
        metric_key: str,
        metric_name: str
    ) -> Optional[TestTrend]:
        """Analyze trend for a specific metric"""
        
        if len(time_series_data) < self.min_data_points:
            return None
        
        # Extract time series for this metric
        timestamps = sorted(time_series_data.keys())
        values = [time_series_data[ts][metric_key] for ts in timestamps]
        
        # Calculate linear regression
        slope, correlation = self._calculate_linear_regression(timestamps, values)
        
        # Determine trend direction
        if abs(correlation) < 0.3:  # Weak correlation
            trend_direction = TrendDirection.STABLE
            confidence = 0.3
        elif slope > 0:
            trend_direction = TrendDirection.IMPROVING if metric_key != "duration_ms" else TrendDirection.DECLINING
            confidence = abs(correlation)
        else:
            trend_direction = TrendDirection.DECLINING if metric_key != "duration_ms" else TrendDirection.IMPROVING
            confidence = abs(correlation)
        
        # Check for volatility
        if len(values) > 3:
            variance = statistics.variance(values)
            mean_value = statistics.mean(values)
            cv = (variance ** 0.5) / mean_value if mean_value > 0 else 0
            if cv > 0.5:  # High coefficient of variation
                trend_direction = TrendDirection.VOLATILE
                confidence = min(confidence, 0.5)
        
        # Generate insights
        insights = self._generate_trend_insights(metric_name, trend_direction, slope, values)
        recommendations = self._generate_trend_recommendations(metric_name, trend_direction)
        
        return TestTrend(
            metric_name=metric_name,
            time_period=f"{len(timestamps)} days",
            trend_direction=trend_direction,
            confidence=confidence,
            timestamps=timestamps,
            values=values,
            linear_regression_slope=slope,
            correlation_coefficient=correlation,
            variance=statistics.variance(values) if len(values) > 1 else 0.0,
            insights=insights,
            recommendations=recommendations
        )
    
    def _analyze_quality_metrics_trends(self, results: List[TestResult]) -> List[TestTrend]:
        """Analyze trends in quality metrics"""
        
        trends = []
        
        # Group quality scores by metric
        quality_data = {}
        for result in results:
            if not result.quality_scores or not result.timestamp:
                continue
            
            for metric, score in result.quality_scores.items():
                if metric not in quality_data:
                    quality_data[metric] = []
                quality_data[metric].append((result.timestamp, score))
        
        # Analyze each quality metric
        for metric, data_points in quality_data.items():
            if len(data_points) < self.min_data_points:
                continue
            
            # Sort by timestamp
            data_points.sort(key=lambda x: x[0])
            timestamps = [dp[0] for dp in data_points]
            values = [dp[1] for dp in data_points]
            
            # Calculate trend
            slope, correlation = self._calculate_linear_regression(timestamps, values)
            
            trend_direction = TrendDirection.STABLE
            confidence = abs(correlation)
            
            if abs(correlation) > 0.3:
                if slope > 0:
                    trend_direction = TrendDirection.IMPROVING
                else:
                    trend_direction = TrendDirection.DECLINING
            
            insights = self._generate_quality_trend_insights(metric, trend_direction, values)
            recommendations = self._generate_quality_recommendations(metric, trend_direction)
            
            trend = TestTrend(
                metric_name=f"Quality: {metric.value}",
                time_period=f"{len(timestamps)} results",
                trend_direction=trend_direction,
                confidence=confidence,
                timestamps=timestamps,
                values=values,
                linear_regression_slope=slope,
                correlation_coefficient=correlation,
                variance=statistics.variance(values) if len(values) > 1 else 0.0,
                insights=insights,
                recommendations=recommendations
            )
            
            trends.append(trend)
        
        return trends
    
    def _analyze_recent_performance(self, results: List[TestResult]) -> List[QualityInsight]:
        """Analyze recent performance patterns"""
        
        insights = []
        
        if len(results) < 3:
            return insights
        
        # Recent vs older comparison
        recent_results = results[-10:]  # Last 10 results
        older_results = results[:-10] if len(results) > 10 else []
        
        if older_results:
            recent_avg_score = statistics.mean([r.score for r in recent_results])
            older_avg_score = statistics.mean([r.score for r in older_results])
            
            score_change = recent_avg_score - older_avg_score
            
            if score_change > 0.1:
                insights.append(QualityInsight(
                    insight_type="improvement",
                    confidence=min(abs(score_change) * 2, 1.0),
                    title="Recent Quality Improvement",
                    description=f"Quality scores have improved by {score_change:.2f} in recent tests",
                    time_period="recent",
                    evidence=[f"Recent average: {recent_avg_score:.3f}", f"Previous average: {older_avg_score:.3f}"],
                    recommendations=["Continue current testing practices", "Investigate successful patterns"],
                    priority="medium"
                ))
            elif score_change < -0.1:
                insights.append(QualityInsight(
                    insight_type="regression",
                    confidence=min(abs(score_change) * 2, 1.0),
                    title="Recent Quality Regression",
                    description=f"Quality scores have declined by {abs(score_change):.2f} in recent tests",
                    time_period="recent",
                    evidence=[f"Recent average: {recent_avg_score:.3f}", f"Previous average: {older_avg_score:.3f}"],
                    recommendations=["Review recent changes", "Investigate quality degradation", "Consider rollback if severe"],
                    priority="high" if abs(score_change) > 0.2 else "medium"
                ))
        
        return insights
    
    def _detect_quality_patterns(self, results: List[TestResult]) -> List[QualityInsight]:
        """Detect patterns in quality metrics"""
        
        insights = []
        
        # Analyze quality metric consistency
        quality_metrics_data = {}
        for result in results:
            if not result.quality_scores:
                continue
            
            for metric, score in result.quality_scores.items():
                if metric not in quality_metrics_data:
                    quality_metrics_data[metric] = []
                quality_metrics_data[metric].append(score)
        
        for metric, scores in quality_metrics_data.items():
            if len(scores) < 5:
                continue
            
            avg_score = statistics.mean(scores)
            std_dev = statistics.stdev(scores) if len(scores) > 1 else 0.0
            
            # High consistency (low variance)
            if std_dev < 0.05 and avg_score > 0.8:
                insights.append(QualityInsight(
                    insight_type="pattern",
                    confidence=0.8,
                    title=f"Consistent High {metric.value}",
                    description=f"{metric.value} shows consistent high quality (σ={std_dev:.3f})",
                    affected_metrics=[metric],
                    evidence=[f"Average: {avg_score:.3f}", f"Standard deviation: {std_dev:.3f}"],
                    recommendations=["Maintain current quality standards"],
                    priority="low"
                ))
            
            # High variability
            elif std_dev > 0.2:
                insights.append(QualityInsight(
                    insight_type="pattern",
                    confidence=0.7,
                    title=f"Variable {metric.value} Quality",
                    description=f"{metric.value} shows high variability (σ={std_dev:.3f})",
                    affected_metrics=[metric],
                    evidence=[f"Average: {avg_score:.3f}", f"Standard deviation: {std_dev:.3f}"],
                    recommendations=["Investigate quality inconsistency", "Standardize quality processes"],
                    priority="medium"
                ))
        
        return insights
    
    def _compare_with_historical(
        self,
        current_results: List[TestResult],
        historical_results: List[TestResult]
    ) -> List[QualityInsight]:
        """Compare current results with historical baseline"""
        
        insights = []
        
        if len(current_results) < 3 or len(historical_results) < 3:
            return insights
        
        # Compare overall scores
        current_avg = statistics.mean([r.score for r in current_results])
        historical_avg = statistics.mean([r.score for r in historical_results])
        
        score_change = current_avg - historical_avg
        
        if abs(score_change) > 0.05:  # Significant change
            if score_change > 0:
                insights.append(QualityInsight(
                    insight_type="improvement",
                    confidence=min(abs(score_change) * 5, 1.0),
                    title="Quality Improvement vs Historical",
                    description=f"Current quality ({current_avg:.3f}) exceeds historical baseline ({historical_avg:.3f})",
                    evidence=[f"Improvement: +{score_change:.3f}"],
                    recommendations=["Document successful changes", "Maintain improvement trajectory"],
                    priority="medium"
                ))
            else:
                insights.append(QualityInsight(
                    insight_type="regression",
                    confidence=min(abs(score_change) * 5, 1.0),
                    title="Quality Regression vs Historical",
                    description=f"Current quality ({current_avg:.3f}) below historical baseline ({historical_avg:.3f})",
                    evidence=[f"Decline: {score_change:.3f}"],
                    recommendations=["Investigate regression causes", "Consider reverting recent changes"],
                    priority="high"
                ))
        
        return insights
    
    def _detect_anomalies(self, results: List[TestResult]) -> List[QualityInsight]:
        """Detect anomalous test results"""
        
        insights = []
        
        if len(results) < 10:
            return insights
        
        scores = [r.score for r in results]
        durations = [r.duration_ms for r in results]
        
        # Score anomalies
        score_mean = statistics.mean(scores)
        score_std = statistics.stdev(scores) if len(scores) > 1 else 0
        
        if score_std > 0:
            anomalous_scores = [
                (i, score) for i, score in enumerate(scores)
                if abs(score - score_mean) > self.anomaly_threshold * score_std
            ]
            
            if anomalous_scores:
                insights.append(QualityInsight(
                    insight_type="anomaly",
                    confidence=0.8,
                    title="Anomalous Quality Scores Detected",
                    description=f"Found {len(anomalous_scores)} tests with unusual quality scores",
                    evidence=[f"Mean±2σ: {score_mean:.3f}±{2*score_std:.3f}"],
                    recommendations=["Investigate anomalous test results", "Check for test environment issues"],
                    priority="medium"
                ))
        
        # Duration anomalies
        duration_mean = statistics.mean(durations)
        duration_std = statistics.stdev(durations) if len(durations) > 1 else 0
        
        if duration_std > 0:
            anomalous_durations = [
                (i, duration) for i, duration in enumerate(durations)
                if abs(duration - duration_mean) > self.anomaly_threshold * duration_std
            ]
            
            if anomalous_durations:
                insights.append(QualityInsight(
                    insight_type="anomaly",
                    confidence=0.7,
                    title="Anomalous Test Durations Detected",
                    description=f"Found {len(anomalous_durations)} tests with unusual execution times",
                    evidence=[f"Mean±2σ: {duration_mean:.1f}±{2*duration_std:.1f}ms"],
                    recommendations=["Check for performance issues", "Monitor test environment resources"],
                    priority="low"
                ))
        
        return insights
    
    def _calculate_linear_regression(
        self,
        timestamps: List[datetime],
        values: List[float]
    ) -> Tuple[float, float]:
        """Calculate linear regression slope and correlation coefficient"""
        
        if len(timestamps) != len(values) or len(timestamps) < 2:
            return 0.0, 0.0
        
        # Convert timestamps to numeric values (days since first timestamp)
        first_timestamp = timestamps[0]
        x_values = [(ts - first_timestamp).total_seconds() / (24 * 3600) for ts in timestamps]
        
        n = len(x_values)
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(values)
        
        # Calculate slope and correlation
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values))
        x_variance = sum((x - x_mean) ** 2 for x in x_values)
        y_variance = sum((y - y_mean) ** 2 for y in values)
        
        if x_variance == 0:
            return 0.0, 0.0
        
        slope = numerator / x_variance
        
        if x_variance * y_variance > 0:
            correlation = numerator / ((x_variance * y_variance) ** 0.5)
        else:
            correlation = 0.0
        
        return slope, correlation
    
    def _generate_trend_insights(
        self,
        metric_name: str,
        trend_direction: TrendDirection,
        slope: float,
        values: List[float]
    ) -> List[str]:
        """Generate insights for metric trends"""
        
        insights = []
        
        if trend_direction == TrendDirection.IMPROVING:
            insights.append(f"{metric_name} is showing positive improvement")
            if slope > 0.1:
                insights.append("Strong improvement trend detected")
        elif trend_direction == TrendDirection.DECLINING:
            insights.append(f"{metric_name} is showing decline")
            if slope < -0.1:
                insights.append("Significant decline trend detected")
        elif trend_direction == TrendDirection.VOLATILE:
            insights.append(f"{metric_name} shows high variability")
            insights.append("Consider investigating causes of inconsistency")
        else:
            insights.append(f"{metric_name} is stable")
        
        # Add value-specific insights
        if values:
            current_value = values[-1]
            avg_value = statistics.mean(values)
            
            if current_value > avg_value * 1.1:
                insights.append("Current performance above average")
            elif current_value < avg_value * 0.9:
                insights.append("Current performance below average")
        
        return insights
    
    def _generate_trend_recommendations(
        self,
        metric_name: str,
        trend_direction: TrendDirection
    ) -> List[str]:
        """Generate recommendations based on trend direction"""
        
        recommendations = []
        
        if trend_direction == TrendDirection.IMPROVING:
            recommendations.append("Continue current practices")
            recommendations.append("Document successful approaches")
        elif trend_direction == TrendDirection.DECLINING:
            recommendations.append("Investigate causes of decline")
            recommendations.append("Consider corrective actions")
        elif trend_direction == TrendDirection.VOLATILE:
            recommendations.append("Stabilize testing processes")
            recommendations.append("Investigate variability sources")
        else:
            recommendations.append("Monitor for changes")
        
        return recommendations
    
    def _generate_quality_trend_insights(
        self,
        metric: QualityMetric,
        trend_direction: TrendDirection,
        values: List[float]
    ) -> List[str]:
        """Generate insights for quality metric trends"""
        
        insights = []
        
        metric_name = metric.value.title()
        
        if trend_direction == TrendDirection.IMPROVING:
            insights.append(f"{metric_name} quality is improving over time")
        elif trend_direction == TrendDirection.DECLINING:
            insights.append(f"{metric_name} quality is declining")
            insights.append("Immediate attention may be required")
        
        if values:
            avg_value = statistics.mean(values)
            if avg_value > 0.9:
                insights.append(f"Excellent {metric_name.lower()} performance maintained")
            elif avg_value < 0.6:
                insights.append(f"{metric_name} performance below acceptable threshold")
        
        return insights
    
    def _generate_quality_recommendations(
        self,
        metric: QualityMetric,
        trend_direction: TrendDirection
    ) -> List[str]:
        """Generate recommendations for quality metrics"""
        
        recommendations = []
        metric_name = metric.value.title()
        
        if trend_direction == TrendDirection.DECLINING:
            if metric == QualityMetric.SAFETY:
                recommendations.append("Review content safety guidelines")
                recommendations.append("Enhance safety filtering mechanisms")
            elif metric == QualityMetric.ACCURACY:
                recommendations.append("Improve fact-checking processes")
                recommendations.append("Update knowledge base")
            elif metric == QualityMetric.COHERENCE:
                recommendations.append("Review prompt engineering")
                recommendations.append("Enhance logical flow validation")
            else:
                recommendations.append(f"Focus on improving {metric_name.lower()}")
        
        return recommendations

# === Results Aggregation Service ===

class ResultsAggregationService(IResultsAggregation):
    """
    Comprehensive results aggregation and analysis service
    
    Features:
    - Multi-service result collection
    - Statistical analysis and trending
    - Quality insights generation
    - Performance analytics
    - Comprehensive reporting
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.event_bus = EventBus()
        self.analyzer = ResultsAnalyzer(config)
        
        # Storage
        self.all_results: List[TestResult] = []
        self.aggregated_reports: Dict[str, AggregatedResults] = {}
        
        # Service endpoints for result collection
        self.service_endpoints = config.get("service_endpoints", {
            "orchestrator": "http://localhost:8000",
            "browser_automation": "http://localhost:8001",
            "api_testing": "http://localhost:8002",
            "ai_quality": "http://localhost:8003"
        })
        
        self.http_client: Optional[httpx.AsyncClient] = None
        
        logger.info("Results Aggregation Service initialized")
    
    async def initialize(self):
        """Initialize service resources"""
        self.http_client = httpx.AsyncClient(timeout=30.0)
        logger.info("Results Aggregation Service ready")
    
    async def cleanup(self):
        """Clean up service resources"""
        if self.http_client:
            await self.http_client.aclose()
        logger.info("Results Aggregation Service cleanup complete")
    
    # === IResultsAggregation Interface Implementation ===
    
    async def collect_test_results(
        self,
        time_period: timedelta,
        service_names: List[str] = None
    ) -> List[TestResult]:
        """Collect test results from all services"""
        
        logger.info(f"Collecting test results for period: {time_period}")
        
        all_results = []
        target_services = service_names or list(self.service_endpoints.keys())
        
        for service_name in target_services:
            try:
                service_results = await self._collect_from_service(service_name, time_period)
                all_results.extend(service_results)
                logger.info(f"Collected {len(service_results)} results from {service_name}")
                
            except Exception as e:
                logger.error(f"Failed to collect results from {service_name}: {e}")
        
        # Store collected results
        self.all_results.extend(all_results)
        
        # Remove duplicates and sort by timestamp
        self.all_results = self._deduplicate_results(self.all_results)
        
        logger.info(f"Total collected results: {len(all_results)}")
        return all_results
    
    async def generate_aggregated_report(
        self,
        request: ReportRequest
    ) -> AggregatedResults:
        """Generate comprehensive aggregated report"""
        
        logger.info(f"Generating aggregated report: {request.report_id}")
        
        try:
            # Determine time period
            end_time = request.end_time or datetime.utcnow()
            
            if request.start_time:
                start_time = request.start_time
            else:
                if request.aggregation_period == AggregationPeriod.HOUR:
                    start_time = end_time - timedelta(hours=1)
                elif request.aggregation_period == AggregationPeriod.DAY:
                    start_time = end_time - timedelta(days=1)
                elif request.aggregation_period == AggregationPeriod.WEEK:
                    start_time = end_time - timedelta(weeks=1)
                elif request.aggregation_period == AggregationPeriod.MONTH:
                    start_time = end_time - timedelta(days=30)
                else:
                    start_time = end_time - timedelta(days=1)
            
            # Collect results for the time period
            time_period = end_time - start_time
            results = await self.collect_test_results(time_period, request.service_names)
            
            # Filter results by time and other criteria
            filtered_results = self._filter_results(results, request, start_time, end_time)
            
            # Generate overall summary
            overall_summary = self._generate_overall_summary(filtered_results)
            
            # Generate test type summaries
            test_type_summaries = self._generate_test_type_summaries(filtered_results)
            
            # Generate service summaries
            service_summaries = self._generate_service_summaries(filtered_results)
            
            # Generate trends analysis
            trends = []
            if request.include_trends:
                trends = self.analyzer.analyze_trends(filtered_results)
            
            # Generate quality insights
            quality_insights = []
            if request.include_quality_insights:
                quality_insights = self.analyzer.detect_quality_insights(filtered_results)
            
            # Generate performance summary
            performance_summary = {}
            if request.include_performance_analysis:
                performance_summary = self._generate_performance_summary(filtered_results)
            
            # Generate recommendations
            recommendations = []
            if request.include_recommendations:
                recommendations = self._generate_recommendations(
                    filtered_results, trends, quality_insights
                )
            
            # Identify top issues and performers
            top_failures = self._identify_top_failures(filtered_results)
            top_performers = self._identify_top_performers(filtered_results)
            
            # Calculate data completeness
            data_completeness = self._calculate_data_completeness(filtered_results, time_period)
            
            # Create aggregated results
            aggregated_results = AggregatedResults(
                aggregation_id=request.report_id,
                aggregation_period=request.aggregation_period,
                start_time=start_time,
                end_time=end_time,
                overall_summary=overall_summary,
                test_type_summaries=test_type_summaries,
                service_summaries=service_summaries,
                trends=trends,
                quality_insights=quality_insights,
                performance_summary=performance_summary,
                top_failures=top_failures,
                top_performers=top_performers,
                recommendations=recommendations,
                data_completeness=data_completeness
            )
            
            # Store report
            self.aggregated_reports[request.report_id] = aggregated_results
            
            logger.info(f"Aggregated report generated: {request.report_id}")
            return aggregated_results
            
        except Exception as e:
            logger.error(f"Failed to generate aggregated report: {e}")
            raise
    
    async def export_report(
        self,
        report_id: str,
        format: ReportFormat = ReportFormat.JSON
    ) -> str:
        """Export report in specified format"""
        
        if report_id not in self.aggregated_reports:
            raise ValueError(f"Report {report_id} not found")
        
        report = self.aggregated_reports[report_id]
        
        if format == ReportFormat.JSON:
            return report.json(indent=2)
        elif format == ReportFormat.CSV:
            return self._export_to_csv(report)
        elif format == ReportFormat.MARKDOWN:
            return self._export_to_markdown(report)
        elif format == ReportFormat.HTML:
            return self._export_to_html(report)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    # === Helper Methods ===
    
    async def _collect_from_service(
        self,
        service_name: str,
        time_period: timedelta
    ) -> List[TestResult]:
        """Collect results from a specific service"""
        
        endpoint = self.service_endpoints.get(service_name)
        if not endpoint:
            logger.warning(f"No endpoint configured for service: {service_name}")
            return []
        
        try:
            # This would make actual HTTP calls to service APIs
            # For now, return mock data
            
            # Mock results based on service type
            mock_results = []
            for i in range(5):  # 5 mock results per service
                result = TestResult(
                    execution_id=f"{service_name}_test_{i}",
                    scenario_id=f"scenario_{i}",
                    status=TestStatus.COMPLETED,
                    passed=True,
                    score=0.8 + (i * 0.05),
                    duration_ms=1000 + (i * 100),
                    timestamp=datetime.utcnow() - timedelta(hours=i)
                )
                mock_results.append(result)
            
            return mock_results
            
        except Exception as e:
            logger.error(f"Error collecting from {service_name}: {e}")
            return []
    
    def _deduplicate_results(self, results: List[TestResult]) -> List[TestResult]:
        """Remove duplicate results and sort by timestamp"""
        
        # Remove duplicates based on execution_id
        seen_ids = set()
        unique_results = []
        
        for result in results:
            if result.execution_id not in seen_ids:
                seen_ids.add(result.execution_id)
                unique_results.append(result)
        
        # Sort by timestamp (newest first)
        unique_results.sort(key=lambda r: r.timestamp or datetime.min, reverse=True)
        
        return unique_results
    
    def _filter_results(
        self,
        results: List[TestResult],
        request: ReportRequest,
        start_time: datetime,
        end_time: datetime
    ) -> List[TestResult]:
        """Filter results based on request criteria"""
        
        filtered = []
        
        for result in results:
            # Time filter
            if result.timestamp:
                if not (start_time <= result.timestamp <= end_time):
                    continue
            
            # Test type filter
            if request.test_types:
                # Would need to add test_type to TestResult model
                # For now, skip this filter
                pass
            
            filtered.append(result)
        
        # Limit results
        if request.max_records and len(filtered) > request.max_records:
            filtered = filtered[:request.max_records]
        
        return filtered
    
    def _generate_overall_summary(self, results: List[TestResult]) -> TestSummary:
        """Generate overall summary statistics"""
        
        if not results:
            return TestSummary()
        
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.passed)
        failed_tests = total_tests - passed_tests
        
        scores = [r.score for r in results]
        durations = [r.duration_ms for r in results]
        
        avg_score = statistics.mean(scores) if scores else 0.0
        avg_duration = statistics.mean(durations) if durations else 0.0
        
        # Calculate quality scores summary
        quality_scores = {}
        quality_data = {}
        
        for result in results:
            if result.quality_scores:
                for metric, score in result.quality_scores.items():
                    if metric not in quality_data:
                        quality_data[metric] = []
                    quality_data[metric].append(score)
        
        for metric, scores_list in quality_data.items():
            quality_scores[metric] = statistics.mean(scores_list)
        
        # Calculate performance metrics
        response_times = []
        for result in results:
            if result.performance_metrics and "avg_response_time_ms" in result.performance_metrics:
                response_times.append(result.performance_metrics["avg_response_time_ms"])
        
        avg_response_time = statistics.mean(response_times) if response_times else 0.0
        p95_response_time = self._calculate_percentile(response_times, 95) if response_times else 0.0
        
        success_rate = passed_tests / total_tests if total_tests > 0 else 0.0
        
        return TestSummary(
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            avg_score=avg_score,
            avg_duration_ms=avg_duration,
            quality_scores=quality_scores,
            avg_response_time_ms=avg_response_time,
            p95_response_time_ms=p95_response_time,
            success_rate=success_rate
        )
    
    def _generate_test_type_summaries(self, results: List[TestResult]) -> Dict[TestType, TestSummary]:
        """Generate summaries by test type"""
        
        # Group results by test type (would need test_type field in TestResult)
        # For now, return empty dict
        return {}
    
    def _generate_service_summaries(self, results: List[TestResult]) -> Dict[str, TestSummary]:
        """Generate summaries by service"""
        
        # Group results by service (extract from execution_id)
        service_results = {}
        
        for result in results:
            # Extract service name from execution_id
            service_name = result.execution_id.split('_')[0] if '_' in result.execution_id else "unknown"
            
            if service_name not in service_results:
                service_results[service_name] = []
            
            service_results[service_name].append(result)
        
        # Generate summaries for each service
        summaries = {}
        for service_name, service_results_list in service_results.items():
            summaries[service_name] = self._generate_overall_summary(service_results_list)
        
        return summaries
    
    def _generate_performance_summary(self, results: List[TestResult]) -> Dict[str, float]:
        """Generate performance analysis summary"""
        
        durations = [r.duration_ms for r in results]
        scores = [r.score for r in results]
        
        summary = {}
        
        if durations:
            summary["avg_duration_ms"] = statistics.mean(durations)
            summary["max_duration_ms"] = max(durations)
            summary["min_duration_ms"] = min(durations)
            summary["p95_duration_ms"] = self._calculate_percentile(durations, 95)
        
        if scores:
            summary["avg_score"] = statistics.mean(scores)
            summary["min_score"] = min(scores)
            summary["max_score"] = max(scores)
        
        # Calculate throughput (tests per hour)
        if results and results[0].timestamp and results[-1].timestamp:
            time_span = results[0].timestamp - results[-1].timestamp
            if time_span.total_seconds() > 0:
                tests_per_hour = len(results) * 3600 / time_span.total_seconds()
                summary["tests_per_hour"] = tests_per_hour
        
        return summary
    
    def _generate_recommendations(
        self,
        results: List[TestResult],
        trends: List[TestTrend],
        quality_insights: List[QualityInsight]
    ) -> List[str]:
        """Generate comprehensive recommendations"""
        
        recommendations = []
        
        # Based on overall performance
        if results:
            avg_score = statistics.mean([r.score for r in results])
            success_rate = sum(1 for r in results if r.passed) / len(results)
            
            if avg_score < 0.7:
                recommendations.append("Overall quality below target - review testing standards")
            elif avg_score > 0.9:
                recommendations.append("Excellent overall quality - maintain current practices")
            
            if success_rate < 0.8:
                recommendations.append("Test success rate needs improvement")
        
        # Based on trends
        declining_trends = [t for t in trends if t.trend_direction == TrendDirection.DECLINING]
        if declining_trends:
            recommendations.append("Address declining trends in key metrics")
        
        # Based on quality insights
        high_priority_insights = [i for i in quality_insights if i.priority == "high"]
        if high_priority_insights:
            recommendations.append("Address high-priority quality issues")
        
        # Add specific recommendations from insights
        for insight in quality_insights[:3]:  # Top 3 insights
            recommendations.extend(insight.recommendations[:1])  # First recommendation from each
        
        return list(set(recommendations))  # Remove duplicates
    
    def _identify_top_failures(self, results: List[TestResult]) -> List[Dict[str, Any]]:
        """Identify top failing test scenarios"""
        
        failures = [r for r in results if not r.passed]
        
        # Group by scenario_id
        failure_counts = {}
        for failure in failures:
            scenario_id = failure.scenario_id
            if scenario_id not in failure_counts:
                failure_counts[scenario_id] = {
                    "scenario_id": scenario_id,
                    "failure_count": 0,
                    "latest_error": "",
                    "avg_score": 0.0
                }
            
            failure_counts[scenario_id]["failure_count"] += 1
            if failure.error_message:
                failure_counts[scenario_id]["latest_error"] = failure.error_message
            
        # Calculate average scores for failing scenarios
        for scenario_data in failure_counts.values():
            scenario_failures = [f for f in failures if f.scenario_id == scenario_data["scenario_id"]]
            if scenario_failures:
                scenario_data["avg_score"] = statistics.mean([f.score for f in scenario_failures])
        
        # Sort by failure count and return top 5
        top_failures = sorted(
            failure_counts.values(),
            key=lambda x: x["failure_count"],
            reverse=True
        )[:5]
        
        return top_failures
    
    def _identify_top_performers(self, results: List[TestResult]) -> List[Dict[str, Any]]:
        """Identify top performing test scenarios"""
        
        successes = [r for r in results if r.passed]
        
        # Group by scenario_id
        performance_data = {}
        for success in successes:
            scenario_id = success.scenario_id
            if scenario_id not in performance_data:
                performance_data[scenario_id] = {
                    "scenario_id": scenario_id,
                    "success_count": 0,
                    "scores": [],
                    "durations": []
                }
            
            performance_data[scenario_id]["success_count"] += 1
            performance_data[scenario_id]["scores"].append(success.score)
            performance_data[scenario_id]["durations"].append(success.duration_ms)
        
        # Calculate performance metrics
        for scenario_data in performance_data.values():
            scores = scenario_data["scores"]
            durations = scenario_data["durations"]
            
            scenario_data["avg_score"] = statistics.mean(scores) if scores else 0.0
            scenario_data["avg_duration_ms"] = statistics.mean(durations) if durations else 0.0
            
            # Calculate performance index (higher score, lower duration = better)
            scenario_data["performance_index"] = scenario_data["avg_score"] / max(scenario_data["avg_duration_ms"] / 1000, 0.1)
        
        # Sort by performance index and return top 5
        top_performers = sorted(
            performance_data.values(),
            key=lambda x: x["performance_index"],
            reverse=True
        )[:5]
        
        return top_performers
    
    def _calculate_data_completeness(
        self,
        results: List[TestResult],
        time_period: timedelta
    ) -> float:
        """Calculate data completeness score"""
        
        if not results:
            return 0.0
        
        # Calculate expected vs actual data points
        # This is a simplified calculation
        expected_tests_per_hour = 10  # Configurable
        expected_total = expected_tests_per_hour * (time_period.total_seconds() / 3600)
        
        actual_total = len(results)
        completeness = min(actual_total / expected_total, 1.0) if expected_total > 0 else 1.0
        
        return completeness
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100.0) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower_index = int(index)
            upper_index = lower_index + 1
            weight = index - lower_index
            return sorted_values[lower_index] * (1 - weight) + sorted_values[upper_index] * weight
    
    def _export_to_csv(self, report: AggregatedResults) -> str:
        """Export report to CSV format"""
        # Would implement CSV export
        return "CSV export not implemented"
    
    def _export_to_markdown(self, report: AggregatedResults) -> str:
        """Export report to Markdown format"""
        
        md_content = []
        
        # Header
        md_content.append(f"# Test Results Report")
        md_content.append(f"**Period:** {report.start_time} to {report.end_time}")
        md_content.append(f"**Generated:** {report.generation_time}")
        md_content.append("")
        
        # Overall Summary
        summary = report.overall_summary
        md_content.append("## Overall Summary")
        md_content.append(f"- **Total Tests:** {summary.total_tests}")
        md_content.append(f"- **Passed:** {summary.passed_tests}")
        md_content.append(f"- **Failed:** {summary.failed_tests}")
        md_content.append(f"- **Success Rate:** {summary.success_rate:.1%}")
        md_content.append(f"- **Average Score:** {summary.avg_score:.3f}")
        md_content.append("")
        
        # Trends
        if report.trends:
            md_content.append("## Trends")
            for trend in report.trends:
                md_content.append(f"### {trend.metric_name}")
                md_content.append(f"- **Direction:** {trend.trend_direction.value}")
                md_content.append(f"- **Confidence:** {trend.confidence:.2f}")
                for insight in trend.insights:
                    md_content.append(f"- {insight}")
                md_content.append("")
        
        # Quality Insights
        if report.quality_insights:
            md_content.append("## Quality Insights")
            for insight in report.quality_insights:
                md_content.append(f"### {insight.title}")
                md_content.append(f"**Priority:** {insight.priority}")
                md_content.append(f"{insight.description}")
                md_content.append("")
        
        # Recommendations
        if report.recommendations:
            md_content.append("## Recommendations")
            for rec in report.recommendations:
                md_content.append(f"- {rec}")
            md_content.append("")
        
        return "\n".join(md_content)
    
    def _export_to_html(self, report: AggregatedResults) -> str:
        """Export report to HTML format"""
        # Would implement HTML export with charts
        return "HTML export not implemented"
    
    # === IResultsAggregation Interface Implementation ===
    
    async def store_test_result(self, result: TestResult) -> str:
        """Store test result with indexing"""
        result_id = f"result_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # Store in memory (in production would use database)
        if not hasattr(self, '_stored_results'):
            self._stored_results = {}
        
        self._stored_results[result_id] = result
        
        # Trigger real-time aggregation if enabled
        if self.enable_real_time_aggregation:
            # Update current session aggregation
            if hasattr(self, '_current_aggregation'):
                # Add to current results
                pass
        
        logger.info(f"Stored test result: {result_id}")
        return result_id
    
    async def get_test_results(
        self, 
        filters: Dict[str, Any],
        limit: int = 100
    ) -> List[TestResult]:
        """Retrieve test results with filtering"""
        if not hasattr(self, '_stored_results'):
            return []
        
        results = list(self._stored_results.values())
        
        # Apply filters
        if 'status' in filters:
            results = [r for r in results if r.status == filters['status']]
        
        if 'session_id' in filters:
            results = [r for r in results if r.scenario_id == filters['session_id']]
        
        if 'test_type' in filters:
            # Filter by test type if available in metadata
            test_type = filters['test_type']
            results = [r for r in results if (
                (test_type == 'ui' and r.ui_results is not None) or
                (test_type == 'api' and r.api_results is not None) or
                (test_type == 'ai_quality' and r.ai_quality_results is not None)
            )]
        
        # Apply limit
        return results[:limit]
    
    async def generate_analytics(
        self, 
        time_range: Dict[str, datetime],
        grouping: str = "daily"
    ) -> Dict[str, Any]:
        """Generate test analytics and trends"""
        if not hasattr(self, '_stored_results'):
            return {"message": "No test results available"}
        
        results = list(self._stored_results.values())
        
        # Filter by time range
        start_time = time_range.get('start')
        end_time = time_range.get('end')
        
        if start_time or end_time:
            filtered_results = []
            for result in results:
                # Use created_at timestamp if available in metadata
                result_time = datetime.now()  # Fallback
                
                if start_time and result_time < start_time:
                    continue
                if end_time and result_time > end_time:
                    continue
                    
                filtered_results.append(result)
            results = filtered_results
        
        # Generate analytics
        total_tests = len(results)
        passed_tests = len([r for r in results if r.passed])
        failed_tests = total_tests - passed_tests
        
        # Calculate averages
        avg_score = statistics.mean([r.score for r in results]) if results else 0.0
        avg_duration = statistics.mean([r.duration_ms for r in results]) if results else 0.0
        
        # Test type distribution
        ui_tests = len([r for r in results if r.ui_results is not None])
        api_tests = len([r for r in results if r.api_results is not None])
        ai_quality_tests = len([r for r in results if r.ai_quality_results is not None])
        
        return {
            "time_range": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None,
                "grouping": grouping
            },
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "pass_rate": passed_tests / total_tests if total_tests > 0 else 0.0,
                "average_score": avg_score,
                "average_duration_ms": avg_duration
            },
            "test_types": {
                "ui_tests": ui_tests,
                "api_tests": api_tests,
                "ai_quality_tests": ai_quality_tests
            },
            "trends": {
                "score_trend": "stable",  # Would calculate actual trends
                "duration_trend": "stable",
                "failure_rate_trend": "stable"
            }
        }
    
    async def create_dashboard_data(self, dashboard_type: str) -> Dict[str, Any]:
        """Create real-time dashboard data"""
        if not hasattr(self, '_stored_results'):
            results = []
        else:
            results = list(self._stored_results.values())
        
        # Get recent results (last 24 hours)
        recent_results = results[-100:] if results else []
        
        if dashboard_type == "overview":
            return {
                "dashboard_type": "overview",
                "last_updated": datetime.now().isoformat(),
                "summary": {
                    "total_tests": len(results),
                    "recent_tests": len(recent_results),
                    "pass_rate": len([r for r in recent_results if r.passed]) / len(recent_results) if recent_results else 0.0,
                    "average_score": statistics.mean([r.score for r in recent_results]) if recent_results else 0.0,
                    "average_duration": statistics.mean([r.duration_ms for r in recent_results]) if recent_results else 0.0
                },
                "status_distribution": {
                    "completed": len([r for r in recent_results if r.status == TestStatus.COMPLETED]),
                    "failed": len([r for r in recent_results if r.status == TestStatus.FAILED]),
                    "running": len([r for r in recent_results if r.status == TestStatus.RUNNING])
                }
            }
        
        elif dashboard_type == "performance":
            return {
                "dashboard_type": "performance",
                "last_updated": datetime.now().isoformat(),
                "metrics": {
                    "response_times": [r.duration_ms for r in recent_results[-10:]],
                    "scores": [r.score for r in recent_results[-10:]],
                    "test_counts_by_hour": self._get_hourly_test_counts(recent_results)
                }
            }
        
        elif dashboard_type == "quality":
            return {
                "dashboard_type": "quality",
                "last_updated": datetime.now().isoformat(),
                "quality_metrics": {
                    "overall_score": statistics.mean([r.score for r in recent_results]) if recent_results else 0.0,
                    "ui_quality": statistics.mean([r.score for r in recent_results if r.ui_results]) if recent_results else 0.0,
                    "api_quality": statistics.mean([r.score for r in recent_results if r.api_results]) if recent_results else 0.0,
                    "ai_quality": statistics.mean([r.score for r in recent_results if r.ai_quality_results]) if recent_results else 0.0
                }
            }
        
        else:
            return {"error": f"Unknown dashboard type: {dashboard_type}"}
    
    def _get_hourly_test_counts(self, results: List[TestResult]) -> Dict[str, int]:
        """Get test counts grouped by hour"""
        hourly_counts = {}
        
        for result in results:
            # Use current hour as fallback since we don't have timestamps
            hour_key = datetime.now().strftime("%Y-%m-%d %H:00")
            hourly_counts[hour_key] = hourly_counts.get(hour_key, 0) + 1
        
        return hourly_counts

# === FastAPI Application ===

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan management"""
    # Initialize results aggregation service
    aggregation_config = get_ai_testing_service_config("results_aggregation")
    
    service = ResultsAggregationService(aggregation_config)
    await service.initialize()
    
    app.state.aggregation_service = service
    
    logger.info("Results Aggregation Service started")
    yield
    
    await service.cleanup()
    logger.info("Results Aggregation Service stopped")

# Create FastAPI app
app = FastAPI(
    title="Results Aggregation Service",
    description="Comprehensive test results aggregation and analysis for Novel-Engine AI acceptance testing",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# === API Endpoints ===

@app.get("/health", response_model=ServiceHealthResponse)
async def health_check():
    """Service health check"""
    service: ResultsAggregationService = app.state.aggregation_service
    
    analyzer_status = "connected" if service.analyzer else "disconnected"
    total_results = len(service.all_results)
    
    status = "healthy" if analyzer_status == "connected" else "unhealthy"
    
    return ServiceHealthResponse(
        service_name="results-aggregation",
        status=status,
        version="1.0.0",
        database_status="not_applicable",
        message_queue_status="connected",
        external_dependencies={"analyzer": analyzer_status},
        response_time_ms=25.0,
        memory_usage_mb=220.0,
        cpu_usage_percent=15.0,
        active_tests=0,
        completed_tests_24h=total_results,
        error_rate_percent=0.0
    )

@app.post("/collect", response_model=List[TestResult])
async def collect_results(
    time_period_hours: int = 24,
    service_names: Optional[List[str]] = None
):
    """Collect test results from all services"""
    service: ResultsAggregationService = app.state.aggregation_service
    
    time_period = timedelta(hours=time_period_hours)
    results = await service.collect_test_results(time_period, service_names)
    
    return results

@app.post("/report", response_model=AggregatedResults)
async def generate_report(
    request: ReportRequest
):
    """Generate aggregated test report"""
    service: ResultsAggregationService = app.state.aggregation_service
    
    report = await service.generate_aggregated_report(request)
    return report

@app.get("/report/{report_id}", response_model=AggregatedResults)
async def get_report(report_id: str):
    """Get aggregated report by ID"""
    service: ResultsAggregationService = app.state.aggregation_service
    
    if report_id not in service.aggregated_reports:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return service.aggregated_reports[report_id]

@app.get("/export/{report_id}")
async def export_report(
    report_id: str,
    format: ReportFormat = ReportFormat.JSON
):
    """Export report in specified format"""
    service: ResultsAggregationService = app.state.aggregation_service
    
    try:
        exported_content = await service.export_report(report_id, format)
        
        if format == ReportFormat.JSON:
            return JSONResponse(content=json.loads(exported_content))
        else:
            return JSONResponse(content={"content": exported_content})
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/insights/trends")
async def get_trends(
    time_window_days: int = 7
):
    """Get trend analysis for recent results"""
    service: ResultsAggregationService = app.state.aggregation_service
    
    # Get recent results
    cutoff_time = datetime.utcnow() - timedelta(days=time_window_days)
    recent_results = [r for r in service.all_results if r.timestamp and r.timestamp >= cutoff_time]
    
    trends = service.analyzer.analyze_trends(recent_results, time_window_days)
    return trends

@app.get("/insights/quality")
async def get_quality_insights():
    """Get quality insights for recent results"""
    service: ResultsAggregationService = app.state.aggregation_service
    
    # Get recent results (last 24 hours)
    cutoff_time = datetime.utcnow() - timedelta(hours=24)
    recent_results = [r for r in service.all_results if r.timestamp and r.timestamp >= cutoff_time]
    
    insights = service.analyzer.detect_quality_insights(recent_results)
    return insights

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004, log_level="info")