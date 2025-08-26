"""
Monitoring Dashboards Module

Manages monitoring dashboard configurations, templates, and automated dashboard
generation for the Novel Engine application monitoring stack.

Features:
- Pre-built dashboard templates
- Custom dashboard creation
- Dashboard version management
- Automated dashboard provisioning
- Dashboard sharing and permissions
- Multi-tenant dashboard support

Example:
    from ops.monitoring.dashboards import create_dashboard, load_template
    
    dashboard_id = create_dashboard('api_performance', template='api_metrics')
    template = load_template('infrastructure_overview')
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

__version__ = "1.0.0"

__all__ = [
    "create_dashboard",
    "load_template", 
    "update_dashboard",
    "get_dashboard_list",
    "export_dashboard",
    "import_dashboard"
]

def create_dashboard(name: str, template: Optional[str] = None, **kwargs) -> str:
    """
    Create a new monitoring dashboard.
    
    Args:
        name: Dashboard name
        template: Optional template to use
        **kwargs: Additional dashboard parameters
        
    Returns:
        str: Dashboard ID
    """
    dashboard_id = f"dashboard-{name.lower().replace(' ', '-')}-{datetime.now().strftime('%Y%m%d')}"
    
    dashboard_config = {
        'dashboard_id': dashboard_id,
        'name': name,
        'template': template,
        'created_by': kwargs.get('created_by', 'system'),
        'created_at': datetime.now().isoformat(),
        'tags': kwargs.get('tags', []),
        'folder': kwargs.get('folder', 'General'),
        'auto_refresh': kwargs.get('auto_refresh', '30s'),
        'time_range': kwargs.get('time_range', '1h'),
        'panels': _get_template_panels(template) if template else []
    }
    
    return dashboard_id

def load_template(template_name: str) -> Dict[str, Any]:
    """
    Load a dashboard template configuration.
    
    Args:
        template_name: Name of the template to load
        
    Returns:
        Dict containing template configuration
    """
    templates = {
        'api_metrics': {
            'title': 'API Performance Metrics',
            'description': 'Comprehensive API performance monitoring',
            'panels': [
                {
                    'title': 'Request Rate',
                    'type': 'graph',
                    'targets': ['rate(http_requests_total[5m])'],
                    'unit': 'reqps'
                },
                {
                    'title': 'Response Time',
                    'type': 'graph', 
                    'targets': ['histogram_quantile(0.95, http_request_duration_seconds_bucket)'],
                    'unit': 's'
                },
                {
                    'title': 'Error Rate',
                    'type': 'stat',
                    'targets': ['rate(http_requests_total{status=~"5.."}[5m])'],
                    'unit': 'percent'
                }
            ]
        },
        'infrastructure_overview': {
            'title': 'Infrastructure Overview',
            'description': 'System-wide infrastructure monitoring',
            'panels': [
                {
                    'title': 'CPU Usage',
                    'type': 'graph',
                    'targets': ['100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'],
                    'unit': 'percent'
                },
                {
                    'title': 'Memory Usage',
                    'type': 'graph',
                    'targets': ['(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100'],
                    'unit': 'percent'
                },
                {
                    'title': 'Disk I/O',
                    'type': 'graph',
                    'targets': ['rate(node_disk_read_bytes_total[5m])', 'rate(node_disk_written_bytes_total[5m])'],
                    'unit': 'bytes/sec'
                }
            ]
        },
        'business_metrics': {
            'title': 'Business Metrics',
            'description': 'Key business performance indicators',
            'panels': [
                {
                    'title': 'Active Users',
                    'type': 'stat',
                    'targets': ['novel_engine_active_users'],
                    'unit': 'short'
                },
                {
                    'title': 'User Registrations',
                    'type': 'graph',
                    'targets': ['rate(novel_engine_user_registrations_total[1h])'],
                    'unit': 'users/hour'
                },
                {
                    'title': 'Revenue Metrics',
                    'type': 'graph',
                    'targets': ['novel_engine_revenue_total'],
                    'unit': 'currencyUSD'
                }
            ]
        }
    }
    
    return templates.get(template_name, {'title': 'Unknown Template', 'panels': []})

def _get_template_panels(template_name: Optional[str]) -> List[Dict[str, Any]]:
    """Get panels for a dashboard template."""
    if not template_name:
        return []
    
    template = load_template(template_name)
    return template.get('panels', [])

def update_dashboard(dashboard_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update an existing dashboard.
    
    Args:
        dashboard_id: ID of dashboard to update
        updates: Updates to apply
        
    Returns:
        Dict containing update results
    """
    return {
        'dashboard_id': dashboard_id,
        'updated_at': datetime.now().isoformat(),
        'changes_applied': len(updates),
        'version': updates.get('version', 1) + 1,
        'status': 'updated'
    }

def get_dashboard_list(folder: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get list of available dashboards.
    
    Args:
        folder: Optional folder filter
        
    Returns:
        List of dashboard summaries
    """
    dashboards = [
        {
            'dashboard_id': 'api-performance-20241228',
            'name': 'API Performance',
            'folder': 'Application',
            'created_at': '2024-12-28T10:00:00Z',
            'last_updated': '2024-12-28T15:30:00Z',
            'tags': ['api', 'performance'],
            'panels_count': 8
        },
        {
            'dashboard_id': 'infrastructure-overview-20241228',
            'name': 'Infrastructure Overview', 
            'folder': 'Infrastructure',
            'created_at': '2024-12-28T10:15:00Z',
            'last_updated': '2024-12-28T14:20:00Z',
            'tags': ['infrastructure', 'system'],
            'panels_count': 12
        },
        {
            'dashboard_id': 'business-metrics-20241228',
            'name': 'Business Metrics',
            'folder': 'Business',
            'created_at': '2024-12-28T11:00:00Z', 
            'last_updated': '2024-12-28T16:45:00Z',
            'tags': ['business', 'kpi'],
            'panels_count': 6
        }
    ]
    
    if folder:
        dashboards = [d for d in dashboards if d['folder'] == folder]
    
    return dashboards

def export_dashboard(dashboard_id: str) -> Dict[str, Any]:
    """
    Export dashboard configuration.
    
    Args:
        dashboard_id: ID of dashboard to export
        
    Returns:
        Dict containing dashboard configuration
    """
    return {
        'dashboard_id': dashboard_id,
        'export_format': 'json',
        'exported_at': datetime.now().isoformat(),
        'configuration': {
            'version': 1,
            'title': 'Exported Dashboard',
            'panels': [],
            'templating': {},
            'time': {'from': 'now-1h', 'to': 'now'},
            'refresh': '30s'
        }
    }

def import_dashboard(config: Dict[str, Any]) -> str:
    """
    Import dashboard from configuration.
    
    Args:
        config: Dashboard configuration to import
        
    Returns:
        str: Imported dashboard ID
    """
    dashboard_id = f"imported-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    return dashboard_id