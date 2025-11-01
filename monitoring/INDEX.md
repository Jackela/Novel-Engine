# Novel Engine Monitoring and Observability Stack

Comprehensive enterprise-grade monitoring and observability platform for Novel Engine, designed for production deployment readiness.

## 🎯 Overview

This monitoring stack provides complete visibility into system health, performance, and security while enabling proactive operations and rapid incident response.

### Key Features

- **Prometheus Metrics Collection**: Application, infrastructure, and business metrics
- **OpenTelemetry Distributed Tracing**: Request tracing across all components
- **Structured Logging**: Centralized log aggregation with analysis
- **Real-time Alerting**: Threshold-based and anomaly detection alerts
- **Health Checks**: Comprehensive endpoint and synthetic monitoring
- **Dashboard System**: Executive, operational, performance, and security dashboards
- **Synthetic Monitoring**: User journey and API endpoint testing

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Application   │    │  Observability  │    │   Dashboards    │
│    Services     │───▶│     Server      │───▶│   & Alerts      │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Metrics      │    │     Tracing     │    │    Logging      │
│  (Prometheus)   │    │ (OpenTelemetry) │    │  (Structured)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📊 Monitoring Targets

| Component | Metric | Target | Alert Threshold |
|-----------|--------|--------|----------------|
| API Response Time | P95 | <100ms | >150ms |
| Error Rate | 5xx Errors | <0.1% | >0.5% |
| Availability | Uptime | 99.9% | <99.5% |
| Memory Usage | Application | <80% | >90% |
| CPU Usage | System | <70% | >85% |
| Database | Query Time | <50ms | >100ms |

## 🚀 Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Additional monitoring dependencies
pip install prometheus-client opentelemetry-api opentelemetry-sdk
pip install opentelemetry-exporter-jaeger opentelemetry-exporter-otlp
pip install opentelemetry-instrumentation-fastapi
pip install aiohttp psutil
```

### 2. Basic Configuration

```python
from monitoring import (
    setup_prometheus_endpoint,
    setup_tracing,
    setup_structured_logging,
    create_health_endpoint
)

# Setup in your FastAPI app
app = FastAPI()

# Enable monitoring
setup_prometheus_endpoint(app)
setup_tracing()
setup_structured_logging()
create_health_endpoint(app)
```

### 3. Start Observability Server

```bash
# Start standalone observability server
python -m monitoring.observability_server --host 0.0.0.0 --port 9090

# Or with configuration file
python -m monitoring.observability_server --config observability_config.json
```

### 4. Access Monitoring

- **Metrics**: http://localhost:9090/metrics
- **Health**: http://localhost:9090/health
- **Dashboards**: http://localhost:9090/api/v1/dashboards
- **Alerts**: http://localhost:9090/api/v1/alerts

## 📈 Metrics Collection

### Application Metrics

```python
from monitoring.prometheus_metrics import metrics_collector

# Record HTTP requests
metrics_collector.record_http_request("GET", "/api/stories", 200, 0.150)

# Record database queries
metrics_collector.record_database_query("SELECT", "stories", 0.025, True)

# Record Novel Engine specific metrics
metrics_collector.record_story_generation("adventure", 2.5, True, 0.85)
metrics_collector.record_agent_coordination("character_interaction", 3, 1.2)
```

### Infrastructure Metrics

Automatically collected:
- CPU usage and load average
- Memory usage and availability
- Disk usage and I/O
- Network traffic and errors
- Process metrics (memory, threads, file descriptors)

### Business Metrics

```python
# Track feature usage
metrics_collector.record_feature_usage("story_generator", user_count=5)

# Set business KPIs
metrics_collector.set_business_metric("daily_active_users", 1250)
metrics_collector.set_business_metric("stories_generated_today", 450)
```

## 🔍 Distributed Tracing

### Automatic Instrumentation

```python
from monitoring.opentelemetry_tracing import setup_tracing, TracingConfig

config = TracingConfig(
    service_name="novel-engine",
    environment="production",
    jaeger_endpoint="http://jaeger:14268/api/traces"
)

setup_tracing(config)
```

### Custom Tracing

```python
from monitoring.opentelemetry_tracing import trace_operation

# Trace story generation
@trace_story_generation("adventure", character_count=3)
async def generate_story(story_type, characters):
    # Your story generation logic
    pass

# Manual tracing
async with trace_operation("database_query", {"table": "users"}) as span:
    result = await db.query("SELECT * FROM users")
    span.set_attribute("result_count", len(result))
```

## 📝 Structured Logging

### Configuration

```python
from monitoring.structured_logging import LoggingConfig, setup_structured_logging

config = LoggingConfig(
    log_level="INFO",
    enable_file=True,
    enable_json=True,
    log_directory="logs",
    enable_remote_logging=True,
    remote_endpoint="http://loki:3100/loki/api/v1/push"
)

logger = setup_structured_logging(config, "novel-engine")
```

### Usage

```python
# Application logs
logger.info("Story generation started", story_type="adventure", user_id="123")

# Performance logs
logger.log_performance_event("story_generation", 2500, True)

# Security logs
logger.log_security_event("authentication_failure", "Invalid credentials", 
                         user_id="456", ip_address="192.168.1.100")

# Business logs
logger.log_business_event("story_completed", "User completed story generation",
                         user_id="123", business_context={"story_id": "story_789"})
```

## 🚨 Alerting

### Alert Rules

```python
from monitoring.alerting import AlertRule, AlertSeverity, NotificationChannel

# High response time alert
response_time_alert = AlertRule(
    name="high_response_time",
    metric_name="http_request_duration_seconds",
    condition="> 0.5",
    threshold=0.5,
    severity=AlertSeverity.WARNING,
    description="HTTP response time is high",
    notification_channels=[NotificationChannel.SLACK, NotificationChannel.EMAIL]
)

alert_manager.add_rule(response_time_alert)
```

### Notification Channels

```python
from monitoring.alerting import NotificationConfig

config = NotificationConfig(
    smtp_host="smtp.company.com",
    smtp_port=587,
    email_recipients=["ops@company.com"],
    slack_webhook_url="https://hooks.slack.com/services/...",
    pagerduty_integration_key="your-pagerduty-key"
)
```

## 🏥 Health Checks

### Built-in Checks

- System memory usage
- Disk space usage
- CPU utilization
- Database connectivity
- Story generation system
- Character interaction system

### Custom Health Checks

```python
from monitoring.health_checks import HealthCheck, health_manager

async def check_external_api():
    # Your custom health check logic
    return {"status": "healthy", "message": "API is responding"}

custom_check = HealthCheck(
    name="external_api",
    check_function=check_external_api,
    timeout_seconds=10.0,
    critical=True
)

health_manager.register_check(custom_check)
```

## 📊 Dashboards

### Available Dashboards

1. **Executive Dashboard**
   - System health overview
   - Active users and request rate
   - Error rates and story generation stats

2. **Operational Dashboard**
   - CPU, memory, and disk usage
   - Network I/O and database connections
   - Active alerts

3. **Performance Dashboard**
   - Response time percentiles
   - Throughput and database performance
   - Cache hit rates

4. **Security Dashboard**
   - Failed authentications
   - Suspicious requests and security alerts
   - Request patterns by IP

### Custom Dashboards

```python
from monitoring.dashboard_data import Dashboard, DashboardWidget

custom_dashboard = Dashboard(
    id="custom",
    title="Custom Dashboard",
    description="Custom monitoring view",
    category="application",
    widgets=[
        DashboardWidget(
            id="custom_metric",
            title="Custom Metric",
            widget_type="gauge",
            metric_queries=["custom_metric_name"],
            config={"max_value": 100}
        )
    ]
)

dashboard_collector.add_dashboard(custom_dashboard)
```

## 🔄 Synthetic Monitoring

### HTTP Checks

```python
from monitoring.synthetic_monitoring import create_http_check

health_check = create_http_check(
    name="api_health",
    url="https://api.novel-engine.com/health",
    expected_status=200,
    interval=60.0
)

synthetic_monitor.add_check(health_check)
```

### API Health Checks

```python
from monitoring.synthetic_monitoring import create_api_health_check

api_check = create_api_health_check(
    name="api_endpoints",
    base_url="https://api.novel-engine.com",
    endpoints=["/health", "/api/stories", "/api/characters"],
    interval=300.0
)

synthetic_monitor.add_check(api_check)
```

### User Journey Tests

```python
from monitoring.synthetic_monitoring import UserJourneyConfig, UserJourneyStep

journey = UserJourneyConfig(
    name="story_creation_journey",
    description="Complete story creation workflow",
    steps=[
        UserJourneyStep(
            name="login",
            action_type="http_request",
            config={
                "url": "https://api.novel-engine.com/auth/login",
                "method": "POST",
                "body": {"username": "test@example.com", "password": "password"}
            }
        ),
        UserJourneyStep(
            name="create_story",
            action_type="http_request",
            config={
                "url": "https://api.novel-engine.com/api/stories",
                "method": "POST",
                "headers": {"Authorization": "Bearer {login_response.token}"}
            }
        )
    ]
)
```

## 🔧 Configuration

### Environment Variables

```bash
# Tracing
JAEGER_ENDPOINT=http://jaeger:14268/api/traces
OTLP_ENDPOINT=http://tempo:4317

# Logging
LOG_LEVEL=INFO
LOG_DIRECTORY=logs
REMOTE_LOG_ENDPOINT=http://loki:3100/loki/api/v1/push

# Alerting
SMTP_HOST=smtp.company.com
SMTP_PORT=587
EMAIL_RECIPIENTS=ops@company.com,alerts@company.com
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
PAGERDUTY_INTEGRATION_KEY=your-key-here

# Database
ALERT_DB_PATH=data/alerts.db
METRICS_DB_PATH=data/performance_metrics.db
```

### Configuration File

```json
{
  "environment": "production",
  "log_level": "INFO",
  "tracing_sampling_rate": 1.0,
  "jaeger_endpoint": "http://jaeger:14268/api/traces",
  "base_url": "https://api.novel-engine.com",
  "email_recipients": ["ops@company.com"],
  "slack_webhook_url": "https://hooks.slack.com/services/...",
  "dashboard_retention_hours": 168,
  "dashboard_export_enabled": true
}
```

## 🐳 Docker Deployment

### Docker Compose

```yaml
version: '3.8'
services:
  novel-engine:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OBSERVABILITY_ENDPOINT=http://observability:9090
    depends_on:
      - observability

  observability:
    build:
      context: .
      dockerfile: monitoring/Dockerfile
    ports:
      - "9090:9090"
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    environment:
      - JAEGER_ENDPOINT=http://jaeger:14268/api/traces
      - LOG_LEVEL=INFO

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9091:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--web.external-url=http://localhost:9091'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana-storage:/var/lib/grafana
      - ./monitoring/grafana:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"
      - "14268:14268"

volumes:
  grafana-storage:
```

## 📋 Operational Procedures

### Daily Operations

1. **Monitor System Health**
   ```bash
   curl http://localhost:9090/health/detailed
   ```

2. **Check Active Alerts**
   ```bash
   curl http://localhost:9090/api/v1/alerts
   ```

3. **Review Performance Metrics**
   ```bash
   curl http://localhost:9090/api/v1/system/overview
   ```

### Incident Response

1. **Alert Investigation**
   - Check alert details in `/api/v1/alerts`
   - Review related logs and traces
   - Examine performance dashboards

2. **Root Cause Analysis**
   - Use distributed tracing to identify bottlenecks
   - Analyze structured logs for error patterns
   - Review system resource utilization

3. **Resolution and Recovery**
   - Apply fixes based on analysis
   - Monitor recovery through dashboards
   - Acknowledge alerts when resolved

### Performance Optimization

1. **Identify Bottlenecks**
   - Review P95/P99 response times
   - Analyze database query performance
   - Check cache hit rates

2. **Resource Optimization**
   - Monitor CPU and memory trends
   - Analyze garbage collection patterns
   - Review connection pool utilization

3. **Capacity Planning**
   - Track growth trends in dashboards
   - Monitor resource utilization patterns
   - Plan scaling based on projections

## 🔐 Security Monitoring

### Security Events

- Authentication failures
- Suspicious request patterns
- Rate limiting violations
- SQL injection attempts
- XSS attack patterns

### Security Alerts

- Multiple failed login attempts
- Unusual traffic patterns
- High error rates from specific IPs
- Privilege escalation attempts

## 📈 Performance Tuning

### Optimization Areas

1. **Response Time Optimization**
   - Database query optimization
   - Caching strategy improvements
   - API endpoint performance

2. **Resource Utilization**
   - Memory usage optimization
   - CPU utilization improvements
   - I/O performance tuning

3. **Scalability Improvements**
   - Load balancing optimization
   - Database connection pooling
   - Async processing efficiency

## 🧪 Testing

### Unit Tests

```bash
python -m pytest monitoring/tests/ -v
```

### Integration Tests

```bash
python -m pytest monitoring/tests/integration/ -v
```

### Load Testing

```bash
# Test observability server under load
artillery run monitoring/tests/load/observability_load_test.yml
```

## 📚 Troubleshooting

### Common Issues

1. **Metrics Not Appearing**
   - Check Prometheus endpoint accessibility
   - Verify metrics registration
   - Review scrape configuration

2. **Traces Missing**
   - Verify OpenTelemetry configuration
   - Check Jaeger connectivity
   - Review sampling settings

3. **Alerts Not Firing**
   - Verify alert rule configuration
   - Check metric availability
   - Review notification settings

4. **High Resource Usage**
   - Adjust retention periods
   - Optimize collection intervals
   - Review buffer sizes

### Debug Commands

```bash
# Check metrics endpoint
curl http://localhost:9090/metrics

# Verify health status
curl http://localhost:9090/api/v1/status

# Test alert manager
curl http://localhost:9090/api/v1/alerts/statistics

# Check synthetic monitoring
curl http://localhost:9090/api/v1/synthetic/statistics
```

## 🤝 Contributing

1. Follow the established code patterns
2. Add comprehensive tests for new features
3. Update documentation for changes
4. Ensure observability for new components

## 📄 License

This monitoring stack is part of Novel Engine and follows the same licensing terms.
