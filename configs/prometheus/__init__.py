"""
Prometheus Configuration Module

Manages Prometheus monitoring, metrics collection, and alerting configurations
for the Novel Engine application observability stack.

Features:
- Metrics configuration and collection rules
- Alerting rules and thresholds
- Service discovery configuration
- Grafana dashboard integration
- Custom metric definitions

Example:
    from configs.prometheus import load_metrics_config, generate_alert_rules
    
    metrics_config = load_metrics_config()
    alert_rules = generate_alert_rules('production')
"""

from typing import Any, Dict, List

__version__ = "1.0.0"

# Prometheus configuration utilities
__all__ = [
    "load_prometheus_config",
    "generate_scrape_configs",
    "load_alert_rules",
    "get_metrics_config",
    "validate_prometheus_config"
]

def load_prometheus_config(env: str = 'production') -> Dict[str, Any]:
    """
    Load Prometheus configuration for the specified environment.
    
    Args:
        env: Environment name
        
    Returns:
        Dict containing Prometheus configuration
    """
    return {
        'global': {
            'scrape_interval': '15s',
            'evaluation_interval': '15s'
        },
        'alerting': {
            'alertmanagers': [
                {
                    'static_configs': [
                        {'targets': ['alertmanager:9093']}
                    ]
                }
            ]
        },
        'rule_files': [
            'rules/*.yml'
        ],
        'scrape_configs': generate_scrape_configs(env)
    }

def generate_scrape_configs(env: str) -> List[Dict[str, Any]]:
    """
    Generate scrape configurations for the specified environment.
    
    Args:
        env: Environment name
        
    Returns:
        List of scrape configurations
    """
    base_configs = [
        {
            'job_name': 'novel-engine-api',
            'static_configs': [
                {'targets': ['localhost:8000', 'localhost:8001']}
            ],
            'metrics_path': '/metrics',
            'scrape_interval': '10s'
        },
        {
            'job_name': 'novel-engine-workers',
            'static_configs': [
                {'targets': ['localhost:9000']}
            ],
            'metrics_path': '/metrics'
        },
        {
            'job_name': 'node-exporter',
            'static_configs': [
                {'targets': ['localhost:9100']}
            ]
        }
    ]
    
    if env == 'production':
        # Add production-specific monitoring targets
        base_configs.extend([
            {
                'job_name': 'novel-engine-database',
                'static_configs': [
                    {'targets': ['postgres-exporter:9187']}
                ]
            },
            {
                'job_name': 'novel-engine-redis',
                'static_configs': [
                    {'targets': ['redis-exporter:9121']}
                ]
            }
        ])
    
    return base_configs

def load_alert_rules() -> List[Dict[str, Any]]:
    """
    Load alerting rules configuration.
    
    Returns:
        List of alert rule configurations
    """
    return [
        {
            'alert': 'HighErrorRate',
            'expr': 'rate(http_requests_total{status=~"5.."}[5m]) > 0.1',
            'for': '5m',
            'labels': {
                'severity': 'critical'
            },
            'annotations': {
                'summary': 'High error rate detected',
                'description': 'Error rate is {{ $value }} errors per second'
            }
        },
        {
            'alert': 'HighLatency',
            'expr': 'http_request_duration_seconds{quantile="0.95"} > 1',
            'for': '10m',
            'labels': {
                'severity': 'warning'
            },
            'annotations': {
                'summary': 'High latency detected',
                'description': '95th percentile latency is {{ $value }} seconds'
            }
        },
        {
            'alert': 'ServiceDown',
            'expr': 'up == 0',
            'for': '1m',
            'labels': {
                'severity': 'critical'
            },
            'annotations': {
                'summary': 'Service is down',
                'description': '{{ $labels.job }} service is down'
            }
        }
    ]

def get_metrics_config() -> Dict[str, Any]:
    """
    Get custom metrics configuration.
    
    Returns:
        Dict containing metrics configuration
    """
    return {
        'custom_metrics': [
            'novel_engine_requests_total',
            'novel_engine_request_duration_seconds',
            'novel_engine_active_users',
            'novel_engine_database_connections',
            'novel_engine_queue_size'
        ],
        'metric_labels': [
            'method',
            'endpoint', 
            'status_code',
            'user_type'
        ]
    }

def validate_prometheus_config(config: Dict[str, Any]) -> bool:
    """
    Validate Prometheus configuration.
    
    Args:
        config: Prometheus configuration to validate
        
    Returns:
        bool: True if configuration is valid
    """
    required_keys = ['global', 'scrape_configs']
    return all(key in config for key in required_keys)