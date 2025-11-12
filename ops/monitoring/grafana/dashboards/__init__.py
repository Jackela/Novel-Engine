"""
Grafana Dashboard Templates Module

Provides pre-built Grafana dashboard templates and configurations for comprehensive
monitoring of the Novel Engine application and infrastructure components.

Features:
- Application performance dashboard templates
- Infrastructure monitoring templates  
- Business metrics dashboard templates
- Custom panel configurations
- Dashboard variables and templating
- Alert integration templates

Example:
    from ops.monitoring.grafana.dashboards import get_api_dashboard, get_infrastructure_dashboard
    
    api_dashboard = get_api_dashboard()
    infra_dashboard = get_infrastructure_dashboard()
"""

from typing import Any, Dict

__version__ = "1.0.0"

__all__ = [
    "get_api_dashboard",
    "get_infrastructure_dashboard", 
    "get_business_dashboard",
    "get_security_dashboard",
    "get_application_overview",
    "create_custom_panel"
]

def get_api_dashboard() -> Dict[str, Any]:
    """
    Get API performance monitoring dashboard template.
    
    Returns:
        Dict containing API dashboard configuration
    """
    return {
        'dashboard': {
            'id': None,
            'uid': 'novel-engine-api',
            'title': 'Novel Engine API Performance',
            'description': 'Comprehensive API performance monitoring dashboard',
            'tags': ['api', 'performance', 'novel-engine'],
            'timezone': 'UTC',
            'refresh': '30s',
            'time': {
                'from': 'now-1h',
                'to': 'now'
            },
            'timepicker': {
                'refresh_intervals': ['5s', '10s', '30s', '1m', '5m', '15m', '30m', '1h', '2h', '1d'],
                'time_options': ['5m', '15m', '1h', '6h', '12h', '24h', '2d', '7d', '30d']
            },
            'templating': {
                'list': [
                    {
                        'name': 'environment',
                        'type': 'query',
                        'datasource': 'prometheus',
                        'query': 'label_values(environment)',
                        'current': {'text': 'production', 'value': 'production'},
                        'includeAll': False,
                        'multi': False
                    },
                    {
                        'name': 'service',
                        'type': 'query', 
                        'datasource': 'prometheus',
                        'query': 'label_values(http_requests_total{environment="$environment"}, service)',
                        'current': {'text': 'All', 'value': '$__all'},
                        'includeAll': True,
                        'multi': True
                    }
                ]
            },
            'panels': [
                {
                    'id': 1,
                    'title': 'Request Rate',
                    'type': 'graph',
                    'gridPos': {'h': 8, 'w': 12, 'x': 0, 'y': 0},
                    'targets': [
                        {
                            'expr': 'sum(rate(http_requests_total{environment="$environment",service=~"$service"}[5m]))',
                            'legendFormat': 'Total Requests/sec'
                        }
                    ],
                    'yAxes': [
                        {'label': 'Requests/sec', 'min': 0}
                    ],
                    'alert': {
                        'conditions': [
                            {
                                'query': {'params': ['A', '5m', 'now']},
                                'reducer': {'params': [], 'type': 'avg'},
                                'evaluator': {'params': [100], 'type': 'gt'}
                            }
                        ],
                        'executionErrorState': 'alerting',
                        'for': '2m',
                        'frequency': '10s',
                        'handler': 1,
                        'name': 'High Request Rate Alert',
                        'noDataState': 'no_data'
                    }
                },
                {
                    'id': 2,
                    'title': 'Response Time (95th Percentile)',
                    'type': 'graph',
                    'gridPos': {'h': 8, 'w': 12, 'x': 12, 'y': 0},
                    'targets': [
                        {
                            'expr': 'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{environment="$environment",service=~"$service"}[5m])) by (le))',
                            'legendFormat': '95th Percentile'
                        },
                        {
                            'expr': 'histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket{environment="$environment",service=~"$service"}[5m])) by (le))',
                            'legendFormat': '50th Percentile'
                        }
                    ],
                    'yAxes': [
                        {'label': 'Seconds', 'min': 0}
                    ]
                },
                {
                    'id': 3,
                    'title': 'Error Rate',
                    'type': 'stat',
                    'gridPos': {'h': 4, 'w': 6, 'x': 0, 'y': 8},
                    'targets': [
                        {
                            'expr': 'sum(rate(http_requests_total{environment="$environment",service=~"$service",status=~"5.."}[5m])) / sum(rate(http_requests_total{environment="$environment",service=~"$service"}[5m])) * 100',
                            'legendFormat': 'Error Rate %'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'unit': 'percent',
                            'thresholds': {
                                'steps': [
                                    {'color': 'green', 'value': None},
                                    {'color': 'yellow', 'value': 1},
                                    {'color': 'red', 'value': 5}
                                ]
                            }
                        }
                    }
                },
                {
                    'id': 4,
                    'title': 'Active Connections',
                    'type': 'stat',
                    'gridPos': {'h': 4, 'w': 6, 'x': 6, 'y': 8},
                    'targets': [
                        {
                            'expr': 'sum(novel_engine_active_connections{environment="$environment"})',
                            'legendFormat': 'Active Connections'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'unit': 'short',
                            'thresholds': {
                                'steps': [
                                    {'color': 'green', 'value': None},
                                    {'color': 'yellow', 'value': 80},
                                    {'color': 'red', 'value': 100}
                                ]
                            }
                        }
                    }
                }
            ]
        }
    }

def get_infrastructure_dashboard() -> Dict[str, Any]:
    """
    Get infrastructure monitoring dashboard template.
    
    Returns:
        Dict containing infrastructure dashboard configuration
    """
    return {
        'dashboard': {
            'id': None,
            'uid': 'novel-engine-infrastructure',
            'title': 'Novel Engine Infrastructure',
            'description': 'System-wide infrastructure monitoring',
            'tags': ['infrastructure', 'system', 'novel-engine'],
            'timezone': 'UTC',
            'refresh': '1m',
            'time': {
                'from': 'now-1h',
                'to': 'now'
            },
            'templating': {
                'list': [
                    {
                        'name': 'instance',
                        'type': 'query',
                        'datasource': 'prometheus',
                        'query': 'label_values(node_uname_info, instance)',
                        'current': {'text': 'All', 'value': '$__all'},
                        'includeAll': True,
                        'multi': True
                    }
                ]
            },
            'panels': [
                {
                    'id': 1,
                    'title': 'CPU Usage',
                    'type': 'graph',
                    'gridPos': {'h': 8, 'w': 12, 'x': 0, 'y': 0},
                    'targets': [
                        {
                            'expr': '100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle",instance=~"$instance"}[5m])) * 100)',
                            'legendFormat': '{{instance}}'
                        }
                    ],
                    'yAxes': [
                        {'label': 'Percent', 'min': 0, 'max': 100}
                    ]
                },
                {
                    'id': 2,
                    'title': 'Memory Usage',
                    'type': 'graph',
                    'gridPos': {'h': 8, 'w': 12, 'x': 12, 'y': 0},
                    'targets': [
                        {
                            'expr': '(1 - (node_memory_MemAvailable_bytes{instance=~"$instance"} / node_memory_MemTotal_bytes{instance=~"$instance"})) * 100',
                            'legendFormat': '{{instance}}'
                        }
                    ],
                    'yAxes': [
                        {'label': 'Percent', 'min': 0, 'max': 100}
                    ]
                },
                {
                    'id': 3,
                    'title': 'Disk I/O',
                    'type': 'graph',
                    'gridPos': {'h': 8, 'w': 12, 'x': 0, 'y': 8},
                    'targets': [
                        {
                            'expr': 'rate(node_disk_read_bytes_total{instance=~"$instance"}[5m])',
                            'legendFormat': '{{instance}} - Read'
                        },
                        {
                            'expr': 'rate(node_disk_written_bytes_total{instance=~"$instance"}[5m])',
                            'legendFormat': '{{instance}} - Write'
                        }
                    ],
                    'yAxes': [
                        {'label': 'Bytes/sec', 'min': 0}
                    ]
                },
                {
                    'id': 4,
                    'title': 'Network I/O',
                    'type': 'graph',
                    'gridPos': {'h': 8, 'w': 12, 'x': 12, 'y': 8},
                    'targets': [
                        {
                            'expr': 'rate(node_network_receive_bytes_total{instance=~"$instance"}[5m])',
                            'legendFormat': '{{instance}} - Receive'
                        },
                        {
                            'expr': 'rate(node_network_transmit_bytes_total{instance=~"$instance"}[5m])',
                            'legendFormat': '{{instance}} - Transmit'
                        }
                    ],
                    'yAxes': [
                        {'label': 'Bytes/sec', 'min': 0}
                    ]
                }
            ]
        }
    }

def get_business_dashboard() -> Dict[str, Any]:
    """
    Get business metrics dashboard template.
    
    Returns:
        Dict containing business dashboard configuration
    """
    return {
        'dashboard': {
            'id': None,
            'uid': 'novel-engine-business',
            'title': 'Novel Engine Business Metrics',
            'description': 'Key business performance indicators and metrics',
            'tags': ['business', 'kpi', 'novel-engine'],
            'timezone': 'UTC',
            'refresh': '5m',
            'time': {
                'from': 'now-24h',
                'to': 'now'
            },
            'panels': [
                {
                    'id': 1,
                    'title': 'Active Users',
                    'type': 'stat',
                    'gridPos': {'h': 6, 'w': 6, 'x': 0, 'y': 0},
                    'targets': [
                        {
                            'expr': 'novel_engine_active_users',
                            'legendFormat': 'Active Users'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'unit': 'short',
                            'color': {'mode': 'thresholds'},
                            'thresholds': {
                                'steps': [
                                    {'color': 'red', 'value': 0},
                                    {'color': 'yellow', 'value': 100},
                                    {'color': 'green', 'value': 500}
                                ]
                            }
                        }
                    }
                },
                {
                    'id': 2,
                    'title': 'User Registrations Today',
                    'type': 'stat',
                    'gridPos': {'h': 6, 'w': 6, 'x': 6, 'y': 0},
                    'targets': [
                        {
                            'expr': 'increase(novel_engine_user_registrations_total[24h])',
                            'legendFormat': 'New Registrations'
                        }
                    ]
                },
                {
                    'id': 3,
                    'title': 'Daily Revenue',
                    'type': 'stat',
                    'gridPos': {'h': 6, 'w': 6, 'x': 12, 'y': 0},
                    'targets': [
                        {
                            'expr': 'increase(novel_engine_revenue_total[24h])',
                            'legendFormat': 'Daily Revenue'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'unit': 'currencyUSD'
                        }
                    }
                }
            ]
        }
    }

def get_security_dashboard() -> Dict[str, Any]:
    """
    Get security monitoring dashboard template.
    
    Returns:
        Dict containing security dashboard configuration
    """
    return {
        'dashboard': {
            'id': None,
            'uid': 'novel-engine-security',
            'title': 'Novel Engine Security Monitoring',
            'description': 'Security events, authentication, and threat monitoring',
            'tags': ['security', 'auth', 'novel-engine'],
            'timezone': 'UTC',
            'refresh': '1m',
            'time': {
                'from': 'now-1h',
                'to': 'now'
            },
            'panels': [
                {
                    'id': 1,
                    'title': 'Failed Login Attempts',
                    'type': 'graph',
                    'gridPos': {'h': 8, 'w': 12, 'x': 0, 'y': 0},
                    'targets': [
                        {
                            'expr': 'rate(novel_engine_auth_failures_total[5m])',
                            'legendFormat': 'Failed Logins/sec'
                        }
                    ]
                },
                {
                    'id': 2,
                    'title': 'Security Events',
                    'type': 'table',
                    'gridPos': {'h': 8, 'w': 12, 'x': 12, 'y': 0},
                    'targets': [
                        {
                            'expr': 'novel_engine_security_events',
                            'format': 'table'
                        }
                    ]
                }
            ]
        }
    }

def get_application_overview() -> Dict[str, Any]:
    """
    Get application overview dashboard template.
    
    Returns:
        Dict containing application overview dashboard
    """
    return {
        'dashboard': {
            'id': None,
            'uid': 'novel-engine-overview',
            'title': 'Novel Engine Application Overview',
            'description': 'High-level application health and performance overview',
            'tags': ['overview', 'health', 'novel-engine'],
            'timezone': 'UTC',
            'refresh': '30s',
            'time': {
                'from': 'now-1h',
                'to': 'now'
            },
            'panels': [
                {
                    'id': 1,
                    'title': 'Service Health',
                    'type': 'stat',
                    'gridPos': {'h': 4, 'w': 24, 'x': 0, 'y': 0},
                    'targets': [
                        {
                            'expr': 'up{job=~"novel-engine.*"}',
                            'legendFormat': '{{job}}'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'mappings': [
                                {'options': {'0': {'text': 'DOWN'}, '1': {'text': 'UP'}}, 'type': 'value'}
                            ],
                            'color': {'mode': 'thresholds'},
                            'thresholds': {
                                'steps': [
                                    {'color': 'red', 'value': 0},
                                    {'color': 'green', 'value': 1}
                                ]
                            }
                        }
                    }
                }
            ]
        }
    }

def create_custom_panel(panel_type: str, **kwargs) -> Dict[str, Any]:
    """
    Create a custom panel configuration.
    
    Args:
        panel_type: Type of panel (graph, stat, table, etc.)
        **kwargs: Panel configuration options
        
    Returns:
        Dict containing panel configuration
    """
    panel_id = kwargs.get('id', 1)
    
    base_panel = {
        'id': panel_id,
        'title': kwargs.get('title', 'Custom Panel'),
        'type': panel_type,
        'gridPos': kwargs.get('gridPos', {'h': 8, 'w': 12, 'x': 0, 'y': 0}),
        'targets': kwargs.get('targets', []),
        'datasource': kwargs.get('datasource', 'prometheus')
    }
    
    # Add panel-type specific configurations
    if panel_type == 'graph':
        base_panel.update({
            'yAxes': kwargs.get('yAxes', [{'label': 'Value', 'min': 0}]),
            'legend': kwargs.get('legend', {'show': True}),
            'tooltip': kwargs.get('tooltip', {'shared': True})
        })
    elif panel_type == 'stat':
        base_panel.update({
            'fieldConfig': kwargs.get('fieldConfig', {
                'defaults': {
                    'unit': kwargs.get('unit', 'short'),
                    'color': {'mode': 'thresholds'}
                }
            })
        })
    elif panel_type == 'table':
        base_panel.update({
            'styles': kwargs.get('styles', []),
            'columns': kwargs.get('columns', [])
        })
    
    return base_panel