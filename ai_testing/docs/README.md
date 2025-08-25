# Novel-Engine AI Testing Framework

A comprehensive, production-ready AI-driven automated acceptance testing framework for Novel-Engine. This framework implements "LLM as a Judge" methodology combined with traditional testing approaches to provide complete quality assurance for AI-powered applications.

## 🌟 Features

### Core Capabilities
- **End-to-End Testing**: Complete user journey validation from API to UI
- **AI Quality Assessment**: LLM-powered quality evaluation using multiple AI models
- **Browser Automation**: Real user interaction testing with Playwright
- **API Testing**: Comprehensive API testing with performance and security validation
- **Multi-Modal Assessment**: Text, visual, and cross-modal content evaluation
- **Results Aggregation**: Intelligent analysis and reporting with trend detection
- **Real-Time Notifications**: Multi-channel alerting and escalation

### Advanced Features
- **Microservices Architecture**: Scalable, independent service deployment
- **Intelligent Orchestration**: Adaptive execution strategies and failure handling
- **Service Health Monitoring**: Circuit breaker patterns and automatic failover
- **Production Deployment**: Docker containerization and Kubernetes support
- **Comprehensive Observability**: Monitoring, logging, and performance metrics

## 🏗️ Architecture

### Service Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                Master Orchestrator                          │
│              (Port 8000)                                    │
└─────────────────────┬───────────────────────────────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
    ▼                 ▼                 ▼
┌─────────┐    ┌─────────────┐    ┌─────────────┐
│Browser  │    │API Testing  │    │AI Quality   │
│Auto     │    │Service      │    │Assessment   │
│(8001)   │    │(8002)       │    │(8003)       │
└─────────┘    └─────────────┘    └─────────────┘
    │                 │                 │
    └─────────────────┼─────────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
    ▼                 ▼                 ▼
┌─────────────┐  ┌──────────────┐  ┌──────────────┐
│Results      │  │Notification  │  │Multi-Modal   │
│Aggregation  │  │Service       │  │Assessment    │
│(8004)       │  │(8005)        │  │Framework     │
└─────────────┘  └──────────────┘  └──────────────┘
```

### Key Components

#### 1. Master Orchestrator (`ai_testing/orchestration/master_orchestrator.py`)
- Central coordination and workflow management
- Service health monitoring with circuit breaker patterns
- Adaptive execution strategies (sequential, parallel, fail-fast)
- Results aggregation and analysis
- **Port**: 8000

#### 2. Browser Automation Service (`ai_testing/services/browser_automation_service.py`)
- Playwright-based browser testing
- Visual regression detection
- Accessibility compliance testing
- Performance monitoring
- **Port**: 8001

#### 3. API Testing Service (`ai_testing/services/api_testing_service.py`)
- Comprehensive API validation
- Load testing and performance measurement
- Schema validation and security testing
- **Port**: 8002

#### 4. AI Quality Assessment Service (`ai_testing/services/ai_quality_service.py`)
- LLM as a Judge implementation
- Multi-model ensemble evaluation
- Quality dimension scoring (coherence, creativity, accuracy, safety)
- **Port**: 8003

#### 5. Results Aggregation Service (`ai_testing/services/results_aggregation_service.py`)
- Intelligent results analysis
- Trend detection and anomaly identification
- Multi-format reporting (JSON, HTML, PDF)
- **Port**: 8004

#### 6. Notification Service (`ai_testing/services/notification_service.py`)
- Multi-channel alerting (Email, Slack, Webhook)
- Intelligent escalation rules
- Rate limiting and notification management
- **Port**: 8005

#### 7. Multi-Modal Assessment Framework (`ai_testing/framework/multimodal_assessment.py`)
- Cross-modal content evaluation
- Visual quality assessment
- Text-image alignment validation

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- Node.js (for Playwright browsers)
- Access to AI services (OpenAI, Anthropic, Google)

### Option 1: Docker Compose (Recommended)

1. **Clone and setup**:
```bash
cd Novel-Engine
cp ai_testing/deployment/docker/.env.example .env
# Edit .env with your API keys and configuration
```

2. **Start all services**:
```bash
cd ai_testing/deployment/docker
docker-compose up -d
```

3. **Verify deployment**:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/services/health
```

### Option 2: Local Development

1. **Install dependencies**:
```bash
pip install -r ai_testing/deployment/requirements.txt
pip install -r ai_testing/deployment/requirements-services.txt
playwright install chromium firefox webkit
```

2. **Start services individually**:
```bash
# Terminal 1 - Orchestrator
python -m uvicorn ai_testing.orchestration.master_orchestrator:app --port 8000

# Terminal 2 - Browser Automation
python -m uvicorn ai_testing.services.browser_automation_service:app --port 8001

# Terminal 3 - API Testing
python -m uvicorn ai_testing.services.api_testing_service:app --port 8002

# Terminal 4 - AI Quality
python -m uvicorn ai_testing.services.ai_quality_service:app --port 8003

# Terminal 5 - Results Aggregation
python -m uvicorn ai_testing.services.results_aggregation_service:app --port 8004

# Terminal 6 - Notification
python -m uvicorn ai_testing.services.notification_service:app --port 8005
```

### Option 3: Kubernetes Deployment

1. **Apply Kubernetes manifests**:
```bash
kubectl apply -f ai_testing/deployment/kubernetes/namespace.yml
kubectl apply -f ai_testing/deployment/kubernetes/configmap.yml
kubectl apply -f ai_testing/deployment/kubernetes/deployments.yml
kubectl apply -f ai_testing/deployment/kubernetes/services.yml
```

2. **Verify deployment**:
```bash
kubectl get pods -n ai-testing
kubectl get services -n ai-testing
```

## 📖 Usage

### Basic Usage Example

```python
import httpx
import asyncio

async def run_comprehensive_test():
    async with httpx.AsyncClient() as client:
        # Define comprehensive test
        test_request = {
            "test_name": "Novel-Engine Feature Validation",
            "api_test_specs": [
                {
                    "endpoint": "/api/generate",
                    "method": "POST",
                    "expected_status": 200,
                    "base_url": "http://localhost:3000",
                    "request_body": {
                        "prompt": "Generate a short story about AI",
                        "max_length": 500
                    },
                    "response_time_threshold_ms": 5000
                }
            ],
            "ai_quality_specs": [
                {
                    "input_prompt": "Generate a short story about AI",
                    "quality_dimensions": ["coherence", "creativity", "safety"],
                    "quality_threshold": 0.7
                }
            ],
            "strategy": "adaptive",
            "parallel_execution": True,
            "quality_threshold": 0.8
        }
        
        # Execute comprehensive test
        response = await client.post(
            "http://localhost:8000/test/comprehensive",
            json=test_request
        )
        
        result = response.json()
        print(f"Test completed with score: {result['overall_score']:.3f}")
        print(f"Status: {result['overall_status']}")
        
        return result

# Run the test
result = asyncio.run(run_comprehensive_test())
```

### API Endpoints

#### Master Orchestrator (Port 8000)
- `GET /health` - Service health check
- `POST /test/comprehensive` - Execute comprehensive test
- `GET /test/{session_id}` - Get test results
- `GET /test/{session_id}/status` - Get test status
- `GET /services/health` - Get all services health
- `GET /sessions/active` - Get active test sessions

#### Individual Services
Each service provides:
- `GET /health` - Health check
- Service-specific testing endpoints
- Results and status endpoints

### Configuration

#### Environment Variables
```bash
# AI Service Configuration
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_key

# Notification Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email
SMTP_PASSWORD=your_password
SLACK_WEBHOOK_URL=your_slack_webhook

# Service Configuration
LOG_LEVEL=info
ENVIRONMENT=production
SERVICES_BASE_PORT=8000
```

#### Custom Configuration
See `ai_testing/deployment/kubernetes/configmap.yml` for detailed configuration options.

## 🧪 Testing

### Running Integration Tests
```bash
# Start all services first
docker-compose up -d

# Run integration tests
cd ai_testing
python -m pytest tests/integration/ -v --tb=short

# Run specific test categories
python -m pytest tests/integration/test_comprehensive_integration.py::TestComprehensiveOrchestration -v
```

### Test Categories
- **Service Health Tests**: Validate individual service health
- **API Integration Tests**: Test API testing functionality
- **UI Integration Tests**: Test browser automation
- **AI Quality Tests**: Test AI assessment capabilities
- **Orchestration Tests**: Test end-to-end workflows
- **Resilience Tests**: Test error handling and recovery

## 📊 Monitoring and Observability

### Health Monitoring
- Service-level health checks with circuit breakers
- Dependency health tracking
- Performance metrics collection
- Automatic failover and recovery

### Logging
- Structured logging with correlation IDs
- Centralized log aggregation
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Performance and security audit trails

### Metrics
- Test execution metrics
- Service performance metrics
- Quality score trends
- Error rates and patterns

### Optional Monitoring Stack
The framework includes optional Prometheus and Grafana setup:
```bash
# Start with monitoring
docker-compose --profile monitoring up -d

# Access Grafana
open http://localhost:3000
# Default credentials: admin/admin123
```

## 🔧 Development

### Adding New Services
1. Create service in `ai_testing/services/`
2. Implement service interface from `ai_testing/interfaces/service_contracts.py`
3. Add service registration to Master Orchestrator
4. Update Docker and Kubernetes configurations
5. Add integration tests

### Extending AI Quality Assessment
1. Add new quality dimensions to `QualityMetric` enum
2. Implement assessment logic in `ai_quality_service.py`
3. Add specialized prompts and criteria
4. Update multi-modal assessment if needed

### Custom Orchestration Strategies
1. Add new strategy to `OrchestrationStrategy` enum
2. Implement strategy logic in `master_orchestrator.py`
3. Add configuration options
4. Test with integration tests

## 🚨 Troubleshooting

### Common Issues

#### Services Not Starting
```bash
# Check service logs
docker-compose logs orchestrator
docker-compose logs browser-automation

# Check port conflicts
netstat -tulpn | grep :8000
```

#### Browser Automation Issues
```bash
# Reinstall Playwright browsers
playwright install --force

# Check browser dependencies
apt-get update && apt-get install -y libnss3 libatk-bridge2.0-0
```

#### AI Service Connection Issues
```bash
# Verify API keys
echo $OPENAI_API_KEY | wc -c
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models

# Check network connectivity
curl -v https://api.openai.com/v1/models
```

#### Performance Issues
```bash
# Monitor resource usage
docker stats
kubectl top pods -n ai-testing

# Check service health
curl http://localhost:8000/services/health | jq
```

### Debug Mode
Enable debug logging:
```bash
export LOG_LEVEL=debug
docker-compose restart
```

## 📚 API Reference

### Comprehensive Test Request Schema
```json
{
  "test_name": "string",
  "api_test_specs": [...],
  "ui_test_specs": [...],
  "ai_quality_specs": [...],
  "strategy": "sequential|parallel|adaptive|fail_fast|comprehensive",
  "parallel_execution": true,
  "fail_fast": false,
  "quality_threshold": 0.7,
  "test_environment": "string",
  "max_execution_time_minutes": 60
}
```

### Test Result Schema
```json
{
  "test_session_id": "string",
  "overall_status": "COMPLETED|FAILED|TIMEOUT",
  "overall_passed": true,
  "overall_score": 0.85,
  "phase_results": [...],
  "total_tests_executed": 10,
  "total_duration_ms": 45000,
  "quality_dimensions": {...},
  "service_health_snapshot": {...},
  "recommendations": [...]
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Guidelines
- Follow existing code patterns and naming conventions
- Add comprehensive tests for new features
- Update documentation for API changes
- Ensure all services have proper health checks
- Follow microservices best practices

## 📄 License

This project is part of Novel-Engine and follows the same licensing terms.

## 🙋‍♂️ Support

For support and questions:
1. Check the [Troubleshooting](#-troubleshooting) section
2. Review integration test examples
3. Check service logs for detailed error information
4. Open an issue with detailed reproduction steps

## 🗺️ Roadmap

### Planned Features
- [ ] GraphQL API testing support
- [ ] Advanced visual regression algorithms
- [ ] Real-time collaboration testing
- [ ] Custom AI model integration
- [ ] Advanced performance profiling
- [ ] Mobile app testing support
- [ ] Chaos engineering integration
- [ ] Advanced security testing

### Integration Enhancements
- [ ] Novel-Engine story generation testing
- [ ] Character consistency validation
- [ ] Narrative coherence assessment
- [ ] User engagement measurement
- [ ] Content safety validation