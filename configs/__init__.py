"""
Configuration Management Module

This module provides centralized configuration management for the Novel Engine application.
It includes environment-specific configurations, security settings, and service configurations.

Directory Structure:
- environments/: Environment-specific configuration files (dev, staging, production)
- security/: Security-related configuration files (auth, encryption, certificates)
- nginx/: Nginx reverse proxy and web server configurations
- prometheus/: Prometheus monitoring and alerting configurations

Usage:
    from configs import environments, security
    from configs.nginx import load_nginx_config
    from configs.prometheus import load_monitoring_config
"""

__version__ = "1.0.0"
__author__ = "Novel Engine Team"

# Configuration module exports
__all__ = [
    "environments",
    "security", 
    "nginx",
    "prometheus"
]

# Import submodules for easier access
try:
    from . import environments
    from . import security
    from . import nginx
    from . import prometheus
except ImportError:
    # Allow graceful degradation if submodules aren't ready yet
    pass