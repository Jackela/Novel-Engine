"""
Prometheus Alert Rules Module

Contains Prometheus alerting rules and rule group definitions for monitoring
the Novel Engine application infrastructure and performance metrics.

Features:
- Application-specific alert rules
- Infrastructure monitoring rules
- Performance threshold alerts
- Business metric alerts
- Rule group organization

Example:
    from configs.prometheus.rules import load_application_rules, load_infrastructure_rules

    app_rules = load_application_rules()
    infra_rules = load_infrastructure_rules()
"""

from typing import Any, Dict, List

__version__ = "1.0.0"

# Alert rules utilities
__all__ = [
    "load_application_rules",
    "load_infrastructure_rules",
    "load_performance_rules",
    "generate_rule_groups",
    "validate_alert_rules",
]


def load_application_rules() -> List[Dict[str, Any]]:
    """
    Load application-specific alert rules.

    Returns:
        List of application alert rules
    """
    return [
        {
            "alert": "NovelEngineHighErrorRate",
            "expr": 'rate(novel_engine_requests_total{status=~"5.."}[5m]) > 0.05',
            "for": "2m",
            "labels": {"severity": "critical", "service": "novel-engine"},
            "annotations": {
                "summary": "Novel Engine API error rate is high",
                "description": "Error rate is {{ $value | humanizePercentage }} for {{ $labels.endpoint }}",
            },
        },
        {
            "alert": "NovelEngineSlowResponse",
            "expr": 'novel_engine_request_duration_seconds{quantile="0.95"} > 2',
            "for": "5m",
            "labels": {"severity": "warning", "service": "novel-engine"},
            "annotations": {
                "summary": "Novel Engine API response time is slow",
                "description": "95th percentile response time is {{ $value }}s for {{ $labels.endpoint }}",
            },
        },
        {
            "alert": "NovelEngineQueueBacklog",
            "expr": "novel_engine_queue_size > 1000",
            "for": "3m",
            "labels": {"severity": "warning", "service": "novel-engine"},
            "annotations": {
                "summary": "Novel Engine queue backlog is high",
                "description": "Queue size is {{ $value }} items",
            },
        },
    ]


def load_infrastructure_rules() -> List[Dict[str, Any]]:
    """
    Load infrastructure monitoring alert rules.

    Returns:
        List of infrastructure alert rules
    """
    return [
        {
            "alert": "HighCPUUsage",
            "expr": '100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80',
            "for": "5m",
            "labels": {"severity": "warning"},
            "annotations": {
                "summary": "High CPU usage detected",
                "description": "CPU usage is {{ $value | humanizePercentage }} on {{ $labels.instance }}",
            },
        },
        {
            "alert": "HighMemoryUsage",
            "expr": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 90",
            "for": "5m",
            "labels": {"severity": "critical"},
            "annotations": {
                "summary": "High memory usage detected",
                "description": "Memory usage is {{ $value | humanizePercentage }} on {{ $labels.instance }}",
            },
        },
        {
            "alert": "DiskSpaceLow",
            "expr": "(1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) * 100 > 85",
            "for": "5m",
            "labels": {"severity": "warning"},
            "annotations": {
                "summary": "Disk space is running low",
                "description": "Disk usage is {{ $value | humanizePercentage }} on {{ $labels.instance }}:{{ $labels.mountpoint }}",
            },
        },
    ]


def load_performance_rules() -> List[Dict[str, Any]]:
    """
    Load performance monitoring alert rules.

    Returns:
        List of performance alert rules
    """
    return [
        {
            "alert": "DatabaseConnectionPoolHigh",
            "expr": "novel_engine_database_connections / novel_engine_database_max_connections > 0.8",
            "for": "3m",
            "labels": {"severity": "warning"},
            "annotations": {
                "summary": "Database connection pool usage is high",
                "description": "Connection pool usage is {{ $value | humanizePercentage }}",
            },
        },
        {
            "alert": "RedisMemoryHigh",
            "expr": "redis_memory_used_bytes / redis_memory_max_bytes > 0.9",
            "for": "5m",
            "labels": {"severity": "critical"},
            "annotations": {
                "summary": "Redis memory usage is critically high",
                "description": "Redis memory usage is {{ $value | humanizePercentage }}",
            },
        },
    ]


def generate_rule_groups() -> Dict[str, Any]:
    """
    Generate rule groups configuration.

    Returns:
        Dict containing rule groups
    """
    return {
        "groups": [
            {
                "name": "novel-engine-application",
                "interval": "30s",
                "rules": load_application_rules(),
            },
            {
                "name": "novel-engine-infrastructure",
                "interval": "60s",
                "rules": load_infrastructure_rules(),
            },
            {
                "name": "novel-engine-performance",
                "interval": "30s",
                "rules": load_performance_rules(),
            },
        ]
    }


def validate_alert_rules(rules: List[Dict[str, Any]]) -> bool:
    """
    Validate alert rules configuration.

    Args:
        rules: List of alert rules to validate

    Returns:
        bool: True if all rules are valid
    """
    required_keys = ["alert", "expr", "labels", "annotations"]
    for rule in rules:
        if not all(key in rule for key in required_keys):
            return False
    return True
