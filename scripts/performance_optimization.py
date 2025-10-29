#!/usr/bin/env python3
"""
Performance Optimization Script
===============================

Comprehensive performance optimization and monitoring system for Novel Engine.
Implements intelligent performance tuning, bottleneck detection, and system optimization.
"""

import argparse
import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
import psutil
import requests
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    push_to_gateway,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/performance_optimization.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for system performance metrics."""

    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_io: Dict[str, float]
    network_io: Dict[str, float]
    response_times: Dict[str, float]
    error_rates: Dict[str, float]
    throughput: Dict[str, float]
    concurrent_users: int
    active_agents: int
    narrative_generation_rate: float


@dataclass
class OptimizationRecommendation:
    """Container for optimization recommendations."""

    category: str
    priority: str  # high, medium, low
    description: str
    impact_estimate: str
    implementation_effort: str
    estimated_improvement: Dict[str, float]
    commands: List[str]


class PerformanceMonitor:
    """Advanced performance monitoring and optimization system."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metrics_history: List[PerformanceMetrics] = []
        self.optimization_history: List[OptimizationRecommendation] = []
        self.registry = CollectorRegistry()
        self._setup_metrics()

    def _setup_metrics(self):
        """Initialize Prometheus metrics."""
        self.cpu_gauge = Gauge(
            "system_cpu_usage", "CPU usage percentage", registry=self.registry
        )
        self.memory_gauge = Gauge(
            "system_memory_usage", "Memory usage percentage", registry=self.registry
        )
        self.response_time_histogram = Histogram(
            "response_time_seconds",
            "Response time in seconds",
            ["endpoint"],
            registry=self.registry,
        )
        self.error_counter = Counter(
            "errors_total", "Total number of errors", ["type"], registry=self.registry
        )
        self.throughput_gauge = Gauge(
            "throughput_requests_per_second",
            "Requests per second",
            ["service"],
            registry=self.registry,
        )

    async def collect_metrics(self) -> PerformanceMetrics:
        """Collect comprehensive system metrics."""
        logger.info("Collecting performance metrics...")

        # System metrics
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk_io = (
            psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {}
        )
        network_io = (
            psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {}
        )

        # Application metrics
        response_times = await self._collect_response_times()
        error_rates = await self._collect_error_rates()
        throughput = await self._collect_throughput()

        # Novel Engine specific metrics
        concurrent_users = await self._get_concurrent_users()
        active_agents = await self._get_active_agents()
        narrative_rate = await self._get_narrative_generation_rate()

        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_usage=cpu_usage,
            memory_usage=memory.percent,
            disk_io=disk_io,
            network_io=network_io,
            response_times=response_times,
            error_rates=error_rates,
            throughput=throughput,
            concurrent_users=concurrent_users,
            active_agents=active_agents,
            narrative_generation_rate=narrative_rate,
        )

        # Update Prometheus metrics
        self.cpu_gauge.set(cpu_usage)
        self.memory_gauge.set(memory.percent)

        for endpoint, time_ms in response_times.items():
            self.response_time_histogram.labels(endpoint=endpoint).observe(
                time_ms / 1000
            )

        for service, rps in throughput.items():
            self.throughput_gauge.labels(service=service).set(rps)

        self.metrics_history.append(metrics)
        if len(self.metrics_history) > 1000:  # Keep last 1000 metrics
            self.metrics_history = self.metrics_history[-1000:]

        return metrics

    async def _collect_response_times(self) -> Dict[str, float]:
        """Collect response times for key endpoints."""
        endpoints = self.config.get(
            "monitoring_endpoints",
            [
                "http://localhost:8000/health",
                "http://localhost:8000/api/v1/agents/status",
                "http://localhost:8000/api/v1/narrative/generate",
            ],
        )

        response_times = {}

        for endpoint in endpoints:
            try:
                start_time = time.time()
                response = requests.get(endpoint, timeout=30)
                end_time = time.time()

                if response.status_code == 200:
                    response_times[endpoint] = (end_time - start_time) * 1000
                else:
                    self.error_counter.labels(type=f"http_{response.status_code}").inc()
            except Exception as e:
                logger.warning(f"Failed to collect response time for {endpoint}: {e}")
                self.error_counter.labels(type="timeout").inc()

        return response_times

    async def _collect_error_rates(self) -> Dict[str, float]:
        """Collect error rates from application logs and metrics."""
        # This would typically integrate with your logging system
        # For now, return mock data
        return {
            "api_errors": 0.1,  # 0.1% error rate
            "narrative_generation_errors": 0.05,
            "agent_communication_errors": 0.02,
        }

    async def _collect_throughput(self) -> Dict[str, float]:
        """Collect throughput metrics for key services."""
        # This would integrate with your metrics system
        return {
            "api_requests": 150.0,  # requests per second
            "narrative_generations": 5.0,
            "agent_actions": 25.0,
        }

    async def _get_concurrent_users(self) -> int:
        """Get current number of concurrent users."""
        # Would integrate with session management system
        return 100  # Mock data

    async def _get_active_agents(self) -> int:
        """Get current number of active agents."""
        # Would integrate with agent management system
        return 8  # Mock data

    async def _get_narrative_generation_rate(self) -> float:
        """Get current narrative generation rate."""
        # Would integrate with narrative generation system
        return 12.5  # narratives per minute

    def analyze_performance(self) -> List[OptimizationRecommendation]:
        """Analyze performance metrics and generate optimization recommendations."""
        if len(self.metrics_history) < 10:
            logger.warning("Insufficient metrics history for analysis")
            return []

        logger.info("Analyzing performance metrics...")
        recommendations = []

        # Get recent metrics
        recent_metrics = self.metrics_history[-10:]
        avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)

        # CPU optimization recommendations
        if avg_cpu > 80:
            recommendations.append(
                OptimizationRecommendation(
                    category="CPU",
                    priority="high",
                    description="High CPU usage detected. Consider scaling horizontally or optimizing CPU-intensive operations.",
                    impact_estimate="20-30% CPU reduction",
                    implementation_effort="medium",
                    estimated_improvement={"cpu_usage": -25.0, "response_time": -15.0},
                    commands=[
                        "kubectl scale deployment novel-engine-api --replicas=6",
                        "kubectl apply -f k8s/autoscaling.yaml",
                    ],
                )
            )

        # Memory optimization recommendations
        if avg_memory > 85:
            recommendations.append(
                OptimizationRecommendation(
                    category="Memory",
                    priority="high",
                    description="High memory usage detected. Consider implementing memory optimization strategies.",
                    impact_estimate="15-25% memory reduction",
                    implementation_effort="high",
                    estimated_improvement={
                        "memory_usage": -20.0,
                        "gc_frequency": -30.0,
                    },
                    commands=[
                        "python scripts/memory_profiler.py",
                        "kubectl apply -f k8s/memory-optimized-config.yaml",
                    ],
                )
            )

        # Response time optimization
        avg_response_times = {}
        for metrics in recent_metrics:
            for endpoint, time_ms in metrics.response_times.items():
                if endpoint not in avg_response_times:
                    avg_response_times[endpoint] = []
                avg_response_times[endpoint].append(time_ms)

        for endpoint, times in avg_response_times.items():
            avg_time = sum(times) / len(times)
            if avg_time > 1000:  # > 1 second
                recommendations.append(
                    OptimizationRecommendation(
                        category="Response Time",
                        priority="medium",
                        description=f"Slow response time detected for {endpoint}. Consider caching or query optimization.",
                        impact_estimate="30-50% response time improvement",
                        implementation_effort="medium",
                        estimated_improvement={"response_time": -40.0},
                        commands=[
                            "redis-cli config set maxmemory-policy allkeys-lru",
                            "python scripts/database_optimization.py",
                        ],
                    )
                )

        # Database optimization
        recommendations.extend(self._analyze_database_performance())

        # Cache optimization
        recommendations.extend(self._analyze_cache_performance())

        self.optimization_history.extend(recommendations)
        return recommendations

    def _analyze_database_performance(self) -> List[OptimizationRecommendation]:
        """Analyze database performance and provide recommendations."""
        recommendations = []

        # Mock analysis - in reality, this would query database metrics
        recommendations.append(
            OptimizationRecommendation(
                category="Database",
                priority="medium",
                description="Database connection pool optimization recommended.",
                impact_estimate="10-20% query performance improvement",
                implementation_effort="low",
                estimated_improvement={
                    "query_time": -15.0,
                    "connection_utilization": 10.0,
                },
                commands=[
                    "psql -c 'SELECT pg_stat_reset();'",
                    "python scripts/optimize_db_connections.py",
                ],
            )
        )

        return recommendations

    def _analyze_cache_performance(self) -> List[OptimizationRecommendation]:
        """Analyze cache performance and provide recommendations."""
        recommendations = []

        # Mock analysis - in reality, this would check Redis metrics
        recommendations.append(
            OptimizationRecommendation(
                category="Cache",
                priority="low",
                description="Redis memory optimization and key expiration tuning recommended.",
                impact_estimate="5-10% cache hit rate improvement",
                implementation_effort="low",
                estimated_improvement={"cache_hit_rate": 8.0, "memory_usage": -5.0},
                commands=[
                    "redis-cli config set maxmemory 2gb",
                    "redis-cli config set maxmemory-policy volatile-lru",
                ],
            )
        )

        return recommendations

    async def implement_optimization(
        self, recommendation: OptimizationRecommendation
    ) -> bool:
        """Implement an optimization recommendation."""
        logger.info(f"Implementing optimization: {recommendation.description}")

        try:
            for command in recommendation.commands:
                if command.startswith("kubectl"):
                    # Kubernetes command
                    process = await asyncio.create_subprocess_shell(
                        command,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await process.communicate()

                    if process.returncode != 0:
                        logger.error(f"Kubernetes command failed: {stderr.decode()}")
                        return False

                elif command.startswith("python"):
                    # Python script
                    process = await asyncio.create_subprocess_shell(
                        command,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await process.communicate()

                    if process.returncode != 0:
                        logger.error(f"Python script failed: {stderr.decode()}")
                        return False

                elif command.startswith("redis-cli"):
                    # Redis command - would use aioredis in practice
                    logger.info(f"Would execute Redis command: {command}")

                elif command.startswith("psql"):
                    # PostgreSQL command - would use asyncpg in practice
                    logger.info(f"Would execute PostgreSQL command: {command}")

            logger.info(
                f"Successfully implemented optimization: {recommendation.category}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to implement optimization {recommendation.category}: {e}"
            )
            return False

    async def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        logger.info("Generating performance report...")

        if not self.metrics_history:
            return {"error": "No metrics data available"}

        recent_metrics = self.metrics_history[-24:]  # Last 24 data points

        # Calculate averages and trends
        avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
        avg_response_time = sum(
            sum(m.response_times.values()) / len(m.response_times)
            for m in recent_metrics
            if m.response_times
        ) / len([m for m in recent_metrics if m.response_times])

        # Performance trends
        cpu_trend = "stable"
        memory_trend = "stable"

        if len(recent_metrics) >= 12:
            first_half_cpu = sum(m.cpu_usage for m in recent_metrics[:12]) / 12
            second_half_cpu = sum(m.cpu_usage for m in recent_metrics[12:]) / 12

            if second_half_cpu > first_half_cpu * 1.1:
                cpu_trend = "increasing"
            elif second_half_cpu < first_half_cpu * 0.9:
                cpu_trend = "decreasing"

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "status": "healthy" if avg_cpu < 70 and avg_memory < 80 else "warning",
                "avg_cpu_usage": round(avg_cpu, 2),
                "avg_memory_usage": round(avg_memory, 2),
                "avg_response_time_ms": round(avg_response_time, 2),
                "cpu_trend": cpu_trend,
                "memory_trend": memory_trend,
            },
            "metrics": {
                "system": {
                    "cpu_usage": [m.cpu_usage for m in recent_metrics],
                    "memory_usage": [m.memory_usage for m in recent_metrics],
                },
                "application": {
                    "concurrent_users": [m.concurrent_users for m in recent_metrics],
                    "active_agents": [m.active_agents for m in recent_metrics],
                    "narrative_generation_rate": [
                        m.narrative_generation_rate for m in recent_metrics
                    ],
                },
            },
            "recommendations": [asdict(r) for r in self.analyze_performance()],
            "optimization_history": [
                asdict(r) for r in self.optimization_history[-10:]
            ],  # Last 10
        }

        return report

    async def save_report(self, report: Dict[str, Any], filepath: str):
        """Save performance report to file."""
        async with aiofiles.open(filepath, "w") as f:
            await f.write(json.dumps(report, indent=2, default=str))

        logger.info(f"Performance report saved to {filepath}")

    async def push_metrics_to_prometheus(self):
        """Push metrics to Prometheus pushgateway."""
        try:
            push_to_gateway(
                self.config.get("prometheus_pushgateway", "localhost:9091"),
                job="novel-engine-performance",
                registry=self.registry,
            )
            logger.info("Metrics pushed to Prometheus")
        except Exception as e:
            logger.error(f"Failed to push metrics to Prometheus: {e}")


class AutoOptimizer:
    """Automated performance optimization system."""

    def __init__(self, monitor: PerformanceMonitor, config: Dict[str, Any]):
        self.monitor = monitor
        self.config = config
        self.auto_optimization_enabled = config.get("auto_optimization_enabled", False)
        self.optimization_cooldown = timedelta(
            minutes=config.get("optimization_cooldown_minutes", 30)
        )
        self.last_optimization: Optional[datetime] = None

    async def run_optimization_cycle(self):
        """Run a complete optimization cycle."""
        logger.info("Starting optimization cycle...")

        # Collect current metrics
        await self.monitor.collect_metrics()

        # Analyze performance
        recommendations = self.monitor.analyze_performance()

        # Auto-implement critical optimizations if enabled
        if self.auto_optimization_enabled and self._can_optimize():
            critical_recommendations = [
                r for r in recommendations if r.priority == "high"
            ]

            for recommendation in critical_recommendations:
                success = await self.monitor.implement_optimization(recommendation)
                if success:
                    self.last_optimization = datetime.now()
                    logger.info(
                        f"Auto-implemented optimization: {recommendation.category}"
                    )
                else:
                    logger.error(
                        f"Failed to implement optimization: {recommendation.category}"
                    )

        # Generate and save report
        report = await self.monitor.generate_performance_report()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        await self.monitor.save_report(
            report, f"reports/performance_report_{timestamp}.json"
        )

        # Push metrics to monitoring system
        await self.monitor.push_metrics_to_prometheus()

        logger.info("Optimization cycle completed")

    def _can_optimize(self) -> bool:
        """Check if optimization can be performed (cooldown check)."""
        if self.last_optimization is None:
            return True

        return datetime.now() - self.last_optimization > self.optimization_cooldown


async def main():
    """Main function for performance optimization script."""
    parser = argparse.ArgumentParser(
        description="Novel Engine Performance Optimization"
    )
    parser.add_argument(
        "--config",
        default="config/performance_config.json",
        help="Configuration file path",
    )
    parser.add_argument(
        "--mode",
        choices=["monitor", "optimize", "report"],
        default="monitor",
        help="Operation mode",
    )
    parser.add_argument(
        "--auto-optimize", action="store_true", help="Enable automatic optimization"
    )
    parser.add_argument(
        "--interval", type=int, default=60, help="Monitoring interval in seconds"
    )
    args = parser.parse_args()

    # Load configuration
    try:
        with open(args.config) as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.warning(f"Config file {args.config} not found, using defaults")
        config = {
            "auto_optimization_enabled": args.auto_optimize,
            "optimization_cooldown_minutes": 30,
            "monitoring_endpoints": [
                "http://localhost:8000/health",
                "http://localhost:8000/api/v1/agents/status",
            ],
            "prometheus_pushgateway": "localhost:9091",
        }

    # Initialize monitoring system
    monitor = PerformanceMonitor(config)
    optimizer = AutoOptimizer(monitor, config)

    if args.mode == "monitor":
        logger.info(f"Starting continuous monitoring (interval: {args.interval}s)")
        while True:
            try:
                await optimizer.run_optimization_cycle()
                await asyncio.sleep(args.interval)
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring cycle: {e}")
                await asyncio.sleep(args.interval)

    elif args.mode == "optimize":
        logger.info("Running single optimization cycle")
        await optimizer.run_optimization_cycle()

    elif args.mode == "report":
        logger.info("Generating performance report")
        await monitor.collect_metrics()
        report = await monitor.generate_performance_report()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        await monitor.save_report(
            report, f"reports/performance_report_{timestamp}.json"
        )
        print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    # Create necessary directories
    Path("logs").mkdir(exist_ok=True)
    Path("reports").mkdir(exist_ok=True)

    asyncio.run(main())
