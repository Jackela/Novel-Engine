"""
Operations Management Module

This module provides operational tools, monitoring, observability, and site reliability
engineering (SRE) capabilities for the Novel Engine application infrastructure.

Directory Structure:
- monitoring/: Comprehensive monitoring and observability infrastructure
  - observability/: Application performance monitoring and tracing
  - synthetic/: Synthetic monitoring and uptime checks
  - dashboards/: Monitoring dashboard configurations
  - alerts/: Alert management and notification systems
  - logging/: Centralized logging and log analysis
  - docker/: Container monitoring and metrics
  - grafana/: Grafana dashboard and visualization configs

Features:
- Real-time application monitoring
- Infrastructure observability
- Performance metrics and alerting
- Log aggregation and analysis
- Synthetic monitoring and uptime checks
- SRE best practices and runbooks

Usage:
    from ops.monitoring import observability, synthetic, alerts
    from ops.monitoring.grafana import load_dashboards
    from ops.monitoring.logging import configure_logging
"""

__version__ = "1.0.0"
__author__ = "Novel Engine SRE Team"

# Operations module exports
__all__ = ["monitoring"]

# Import submodules for easier access
try:
    from . import monitoring
except ImportError:
    # Allow graceful degradation if submodules aren't ready yet
    pass

# SRE configuration constants
SLO_AVAILABILITY_TARGET = 99.9  # 99.9% uptime SLO
SLO_LATENCY_P95_MS = 200  # 95th percentile latency SLO
SLO_ERROR_RATE_PERCENT = 0.1  # Error rate SLO
MONITORING_RETENTION_DAYS = 90  # Default metrics retention
