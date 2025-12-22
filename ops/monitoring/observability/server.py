#!/usr/bin/env python3
"""
Novel Engine Observability Server

Central server that integrates all monitoring components:
- Prometheus metrics endpoint
- Health check endpoints  
- Dashboard data APIs
- Alert management APIs
- Synthetic monitoring status
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ..alerts.alerting import (
    AlertManager,
    NotificationConfig,
    create_default_alert_rules,
)
from ..dashboards.data import (
    DashboardConfig,
    DashboardDataCollector,
    MetricData,
    initialize_dashboard_collector,
)
from ..health_checks import create_health_endpoint
from ..logging.structured import (
    LoggingConfig,
    setup_structured_logging,
)
from ..opentelemetry_tracing import TracingConfig, get_tracing_health, setup_tracing

# Import monitoring components
from ..prometheus_metrics import (
    metrics_collector,
    setup_prometheus_endpoint,
    start_background_collection,
)
from ..synthetic.monitoring import (
    SyntheticMonitor,
    create_api_health_check,
    create_http_check,
)

logger = logging.getLogger(__name__)

class ObservabilityServer:
    """Central observability server for Novel Engine"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Initialize components
        self.app = FastAPI(
            title="Novel Engine Observability",
            description="Monitoring and observability platform for Novel Engine",
            version="1.0.0"
        )
        
        # Component instances
        self.alert_manager: Optional[AlertManager] = None
        self.dashboard_collector: Optional[DashboardDataCollector] = None
        self.synthetic_monitor: Optional[SyntheticMonitor] = None
        self.structured_logger = None
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        
        # Setup components
        self._setup_cors()
        self._setup_tracing()
        self._setup_logging()
        self._setup_metrics()
        self._setup_health_checks()
        self._setup_alerting()
        self._setup_dashboard_data()
        self._setup_synthetic_monitoring()
        self._setup_api_routes()
        
        logger.info("Observability server initialized")
    
    def _setup_cors(self):
        """Setup CORS middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_tracing(self):
        """Setup distributed tracing"""
        tracing_config = TracingConfig(
            service_name="novel-engine-observability",
            environment=self.config.get("environment", "production"),
            sampling_rate=self.config.get("tracing_sampling_rate", 1.0),
            console_export=True,
            jaeger_endpoint=self.config.get("jaeger_endpoint"),
            otlp_endpoint=self.config.get("otlp_endpoint")
        )
        
        setup_tracing(tracing_config)
        logger.info("Distributed tracing configured")
    
    def _setup_logging(self):
        """Setup structured logging"""
        logging_config = LoggingConfig(
            log_level=self.config.get("log_level", "INFO"),
            enable_file=True,
            enable_json=True,
            log_directory=self.config.get("log_directory", "logs"),
            enable_remote_logging=self.config.get("enable_remote_logging", False),
            remote_endpoint=self.config.get("logging_remote_endpoint")
        )
        
        self.structured_logger = setup_structured_logging(
            logging_config, 
            "observability-server"
        )
        logger.info("Structured logging configured")
    
    def _setup_metrics(self):
        """Setup Prometheus metrics"""
        setup_prometheus_endpoint(self.app)
        logger.info("Prometheus metrics endpoint configured")
    
    def _setup_health_checks(self):
        """Setup health check endpoints"""
        create_health_endpoint(self.app)
        logger.info("Health check endpoints configured")
    
    def _setup_alerting(self):
        """Setup alert manager"""
        notification_config = NotificationConfig(
            smtp_host=self.config.get("smtp_host", "localhost"),
            smtp_port=self.config.get("smtp_port", 587),
            smtp_username=self.config.get("smtp_username"),
            smtp_password=self.config.get("smtp_password"),
            email_recipients=self.config.get("email_recipients", []),
            slack_webhook_url=self.config.get("slack_webhook_url"),
            webhook_urls=self.config.get("webhook_urls", []),
            pagerduty_integration_key=self.config.get("pagerduty_integration_key")
        )
        
        self.alert_manager = AlertManager(notification_config)
        
        # Add default alert rules
        default_rules = create_default_alert_rules()
        for rule in default_rules:
            self.alert_manager.add_rule(rule)
        
        logger.info("Alert manager configured with default rules")
    
    def _setup_dashboard_data(self):
        """Setup dashboard data collector"""
        dashboard_config = DashboardConfig(
            data_retention_hours=self.config.get("dashboard_retention_hours", 168),
            enable_real_time=True,
            export_enabled=self.config.get("dashboard_export_enabled", False),
            export_path=self.config.get("dashboard_export_path", "data/dashboard_exports")
        )
        
        self.dashboard_collector = initialize_dashboard_collector(dashboard_config)
        logger.info("Dashboard data collector configured")
    
    def _setup_synthetic_monitoring(self):
        """Setup synthetic monitoring"""
        self.synthetic_monitor = SyntheticMonitor()
        
        # Add default synthetic checks
        base_url = self.config.get("base_url", "http://localhost:8000")
        
        # Health check
        health_check = create_http_check(
            name="api_health",
            url=f"{base_url}/health",
            expected_status=200,
            interval=60.0
        )
        self.synthetic_monitor.add_check(health_check)
        
        # API endpoints check
        api_check = create_api_health_check(
            name="api_endpoints",
            base_url=base_url,
            endpoints=["/health", "/health/ready", "/metrics"],
            interval=120.0
        )
        self.synthetic_monitor.add_check(api_check)
        
        logger.info("Synthetic monitoring configured")
    
    def _setup_api_routes(self):
        """Setup API routes"""
        
        @self.app.get("/")
        async def root():
            """Root endpoint with service information"""
            return {
                "service": "Novel Engine Observability",
                "version": "1.0.0",
                "status": "running",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "endpoints": {
                    "metrics": "/metrics",
                    "health": "/health",
                    "alerts": "/api/alerts",
                    "dashboards": "/api/dashboards",
                    "synthetic": "/api/synthetic"
                }
            }
        
        # Alert management APIs
        @self.app.get("/api/alerts")
        async def get_alerts():
            """Get active alerts"""
            if not self.alert_manager:
                raise HTTPException(status_code=503, detail="Alert manager not available")
            
            active_alerts = self.alert_manager.get_active_alerts()
            return {
                "alerts": [
                    {
                        "id": alert.id,
                        "rule_name": alert.rule_name,
                        "metric_name": alert.metric_name,
                        "severity": alert.severity.value,
                        "status": alert.status.value,
                        "message": alert.message,
                        "fired_at": alert.fired_at.isoformat(),
                        "current_value": alert.current_value,
                        "threshold_value": alert.threshold_value,
                        "labels": alert.labels
                    }
                    for alert in active_alerts
                ],
                "count": len(active_alerts)
            }
        
        @self.app.post("/api/alerts/{alert_id}/acknowledge")
        async def acknowledge_alert(alert_id: str, user: str = "api"):
            """Acknowledge an alert"""
            if not self.alert_manager:
                raise HTTPException(status_code=503, detail="Alert manager not available")
            
            success = await self.alert_manager.acknowledge_alert(alert_id, user)
            if success:
                return {"message": "Alert acknowledged", "alert_id": alert_id}
            else:
                raise HTTPException(status_code=404, detail="Alert not found")
        
        @self.app.get("/api/alerts/statistics")
        async def get_alert_statistics():
            """Get alert statistics"""
            if not self.alert_manager:
                raise HTTPException(status_code=503, detail="Alert manager not available")
            
            return self.alert_manager.get_alert_statistics()
        
        # Dashboard APIs
        @self.app.get("/api/dashboards")
        async def list_dashboards():
            """List available dashboards"""
            if not self.dashboard_collector:
                raise HTTPException(status_code=503, detail="Dashboard collector not available")
            
            dashboards = self.dashboard_collector.list_dashboards()
            return {
                "dashboards": [
                    {
                        "id": dashboard.id,
                        "title": dashboard.title,
                        "description": dashboard.description,
                        "category": dashboard.category,
                        "widget_count": len(dashboard.widgets),
                        "tags": dashboard.tags
                    }
                    for dashboard in dashboards
                ]
            }
        
        @self.app.get("/api/dashboards/{dashboard_id}")
        async def get_dashboard(dashboard_id: str):
            """Get dashboard configuration and data"""
            if not self.dashboard_collector:
                raise HTTPException(status_code=503, detail="Dashboard collector not available")
            
            dashboard_data = self.dashboard_collector.get_dashboard_data(dashboard_id)
            if not dashboard_data:
                raise HTTPException(status_code=404, detail="Dashboard not found")
            
            return dashboard_data
        
        @self.app.get("/api/dashboards/{dashboard_id}/export")
        async def export_dashboard(dashboard_id: str):
            """Export dashboard data"""
            if not self.dashboard_collector:
                raise HTTPException(status_code=503, detail="Dashboard collector not available")
            
            filepath = self.dashboard_collector.export_dashboard_data(dashboard_id)
            if filepath:
                return {"message": "Dashboard exported", "filepath": filepath}
            else:
                raise HTTPException(status_code=500, detail="Export failed")
        
        @self.app.get("/api/system/overview")
        async def get_system_overview():
            """Get system overview"""
            if not self.dashboard_collector:
                raise HTTPException(status_code=503, detail="Dashboard collector not available")
            
            return self.dashboard_collector.get_system_overview()
        
        # Synthetic monitoring APIs
        @self.app.get("/api/synthetic/checks")
        async def list_synthetic_checks():
            """List synthetic checks"""
            if not self.synthetic_monitor:
                raise HTTPException(status_code=503, detail="Synthetic monitor not available")
            
            checks = []
            for check_name, check in self.synthetic_monitor.checks.items():
                stats = self.synthetic_monitor.get_check_statistics(check_name, 24)
                checks.append({
                    "name": check.name,
                    "type": check.check_type.value,
                    "enabled": check.enabled,
                    "interval_seconds": check.interval_seconds,
                    "description": check.description,
                    "tags": check.tags,
                    "statistics": stats
                })
            
            return {"checks": checks}
        
        @self.app.get("/api/synthetic/checks/{check_name}/results")
        async def get_check_results(check_name: str, limit: int = 100):
            """Get results for a synthetic check"""
            if not self.synthetic_monitor:
                raise HTTPException(status_code=503, detail="Synthetic monitor not available")
            
            results = self.synthetic_monitor.get_check_results(check_name, limit)
            return {
                "check_name": check_name,
                "results": [
                    {
                        "timestamp": result.timestamp.isoformat(),
                        "status": result.status.value,
                        "duration_ms": result.duration_ms,
                        "status_code": result.status_code,
                        "error_message": result.error_message
                    }
                    for result in results
                ]
            }
        
        @self.app.get("/api/synthetic/statistics")
        async def get_synthetic_statistics():
            """Get overall synthetic monitoring statistics"""
            if not self.synthetic_monitor:
                raise HTTPException(status_code=503, detail="Synthetic monitor not available")
            
            return self.synthetic_monitor.get_overall_statistics()
        
        # Observability status API
        @self.app.get("/api/status")
        async def get_observability_status():
            """Get overall observability system status"""
            status = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "components": {
                    "metrics": {"status": "healthy", "details": "Prometheus metrics active"},
                    "tracing": get_tracing_health(),
                    "logging": {"status": "healthy" if self.structured_logger else "unavailable"},
                    "health_checks": {"status": "healthy", "details": "Health endpoints active"},
                    "alerting": {"status": "healthy" if self.alert_manager else "unavailable"},
                    "dashboards": {"status": "healthy" if self.dashboard_collector else "unavailable"},
                    "synthetic": {"status": "healthy" if self.synthetic_monitor else "unavailable"}
                }
            }
            
            # Determine overall status
            component_statuses = [comp.get("status", "unknown") for comp in status["components"].values()]
            if "unavailable" in component_statuses:
                status["overall_status"] = "degraded"
            elif all(s == "healthy" for s in component_statuses):
                status["overall_status"] = "healthy"
            else:
                status["overall_status"] = "warning"
            
            return status
    
    async def start(self, host: str = "0.0.0.0", port: int = 9090):
        """Start the observability server"""
        logger.info(f"Starting observability server on {host}:{port}")
        
        # Start background components
        if self.alert_manager:
            await self.alert_manager.start()
        
        if self.dashboard_collector:
            await self.dashboard_collector.start()
        
        if self.synthetic_monitor:
            await self.synthetic_monitor.start_monitoring()
        
        # Start metrics collection
        metrics_task = await start_background_collection(interval_seconds=15)
        self.background_tasks.append(metrics_task)
        
        # Start background task to feed dashboard collector with metrics
        dashboard_task = asyncio.create_task(self._feed_dashboard_metrics())
        self.background_tasks.append(dashboard_task)
        
        # Start the server
        config = uvicorn.Config(
            app=self.app,
            host=host,
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    async def stop(self):
        """Stop the observability server"""
        logger.info("Stopping observability server")
        
        # Stop background tasks
        for task in self.background_tasks:
            task.cancel()
        
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        # Stop components
        if self.alert_manager:
            await self.alert_manager.stop()
        
        if self.dashboard_collector:
            await self.dashboard_collector.stop()
        
        if self.synthetic_monitor:
            await self.synthetic_monitor.stop_monitoring()
        
        logger.info("Observability server stopped")
    
    async def _feed_dashboard_metrics(self):
        """Background task to feed metrics to dashboard collector"""
        while True:
            try:
                if self.dashboard_collector:
                    # Get current metrics from Prometheus collector
                    current_metrics = metrics_collector.get_metrics_dict()
                    
                    # Convert to dashboard format
                    for metric_name, metric_list in current_metrics.get("metrics", {}).items():
                        if metric_list:
                            latest_metric = metric_list[-1]  # Get latest value
                            
                            metric_data = MetricData(
                                name=metric_name,
                                value=latest_metric["value"],
                                timestamp=datetime.now(timezone.utc),
                                labels=latest_metric.get("labels", {}),
                                description=f"Metric: {metric_name}"
                            )
                            
                            self.dashboard_collector.add_metric_data(metric_data)
                    
                    # Feed metrics to alert manager
                    if self.alert_manager:
                        for metric_name, metric_list in current_metrics.get("metrics", {}).items():
                            if metric_list:
                                latest_value = metric_list[-1]["value"]
                                self.alert_manager.update_metric(metric_name, latest_value)
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                logger.error(f"Error feeding dashboard metrics: {e}")
                await asyncio.sleep(30)

# Factory function to create observability server
def create_observability_server(config: Optional[Dict[str, Any]] = None) -> ObservabilityServer:
    """Create and configure observability server"""
    return ObservabilityServer(config)

# CLI entry point
async def main():
    """Main entry point for running observability server"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Novel Engine Observability Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=9090, help="Port to bind to")
    parser.add_argument("--config", help="Configuration file path")
    
    args = parser.parse_args()
    
    # Load configuration
    config = {}
    if args.config:
        import json
        with open(args.config, 'r') as f:
            config = json.load(f)
    
    # Create and start server
    server = create_observability_server(config)
    
    try:
        await server.start(host=args.host, port=args.port)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await server.stop()

if __name__ == "__main__":
    asyncio.run(main())
