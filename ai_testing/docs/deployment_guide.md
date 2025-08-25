# AI Testing Framework Deployment Guide

Complete deployment guide for the Novel-Engine AI Testing Framework across different environments.

## 📋 Prerequisites

### System Requirements
- **CPU**: 4+ cores recommended
- **Memory**: 8GB+ RAM recommended
- **Storage**: 10GB+ available disk space
- **Network**: Stable internet connection for AI services

### Software Dependencies
- **Docker**: 20.10+ with Docker Compose
- **Kubernetes**: 1.24+ (for K8s deployment)
- **Python**: 3.11+ (for local development)
- **Node.js**: 18+ (for Playwright browsers)

### External Services
- **AI Services**: OpenAI, Anthropic, or Google API access
- **Email**: SMTP server for notifications (optional)
- **Slack**: Webhook URL for notifications (optional)

## 🚀 Production Deployment

### Option 1: Docker Compose (Recommended for Single-Node)

#### 1. Initial Setup
```bash
# Clone the repository
cd Novel-Engine

# Create environment file
cp ai_testing/deployment/docker/.env.example .env

# Edit environment variables
nano .env
```

#### 2. Environment Configuration (.env)
```bash
# AI Service API Keys
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=your-anthropic-key-here
GOOGLE_API_KEY=your-google-key-here

# Email Configuration (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Slack Configuration (Optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/webhook/url

# Database URLs (Optional)
REDIS_URL=redis://ai-testing-redis:6379

# Service Configuration
LOG_LEVEL=info
ENVIRONMENT=production
HEALTH_CHECK_INTERVAL=30

# Resource Limits
MAX_CONCURRENT_TESTS=10
MAX_EXECUTION_TIME_MINUTES=60
```

#### 3. Deploy Services
```bash
cd ai_testing/deployment/docker

# Build and start all services
docker-compose up -d

# Verify deployment
docker-compose ps
docker-compose logs -f orchestrator
```

#### 4. Health Check
```bash
# Check orchestrator health
curl http://localhost:8000/health

# Check all services health
curl http://localhost:8000/services/health | jq

# Verify specific service
curl http://localhost:8001/health  # Browser Automation
curl http://localhost:8002/health  # API Testing
curl http://localhost:8003/health  # AI Quality
curl http://localhost:8004/health  # Results Aggregation
curl http://localhost:8005/health  # Notification
```

#### 5. Access Services
- **Master Orchestrator**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Monitoring (if enabled)**: http://localhost:3000 (Grafana)

### Option 2: Kubernetes Deployment (Recommended for Multi-Node)

#### 1. Prepare Kubernetes Cluster
```bash
# Verify kubectl connection
kubectl cluster-info

# Check node resources
kubectl get nodes
kubectl describe nodes
```

#### 2. Configure Secrets
```bash
# Create namespace
kubectl apply -f ai_testing/deployment/kubernetes/namespace.yml

# Update secrets in configmap.yml with your actual values
nano ai_testing/deployment/kubernetes/configmap.yml

# Apply configuration
kubectl apply -f ai_testing/deployment/kubernetes/configmap.yml
```

#### 3. Deploy Services
```bash
# Apply all Kubernetes manifests
kubectl apply -f ai_testing/deployment/kubernetes/deployments.yml
kubectl apply -f ai_testing/deployment/kubernetes/services.yml

# Verify deployment
kubectl get pods -n ai-testing
kubectl get services -n ai-testing
```

#### 4. Monitor Deployment
```bash
# Watch pod startup
kubectl get pods -n ai-testing -w

# Check service logs
kubectl logs -f deployment/ai-testing-orchestrator -n ai-testing

# Check all pod status
kubectl describe pods -n ai-testing
```

#### 5. Access Services
```bash
# Get external IP (for LoadBalancer)
kubectl get service ai-testing-orchestrator-external -n ai-testing

# Port forward for testing (alternative)
kubectl port-forward service/ai-testing-orchestrator 8000:8000 -n ai-testing

# Access via port forward
curl http://localhost:8000/health
```

#### 6. Scaling Services
```bash
# Scale orchestrator
kubectl scale deployment ai-testing-orchestrator --replicas=3 -n ai-testing

# Scale API testing service
kubectl scale deployment ai-testing-api-testing --replicas=4 -n ai-testing

# Check scaling
kubectl get pods -n ai-testing
```

## 🔧 Development Deployment

### Local Development Setup

#### 1. Environment Setup
```bash
# Create Python virtual environment
python -m venv ai-testing-env
source ai-testing-env/bin/activate  # Linux/Mac
# or
ai-testing-env\Scripts\activate  # Windows

# Install dependencies
pip install -r ai_testing/deployment/requirements.txt
pip install -r ai_testing/deployment/requirements-services.txt

# Install Playwright browsers
playwright install chromium firefox webkit
```

#### 2. Configuration
```bash
# Create local configuration
cp ai_testing/config/config.example.yml ai_testing/config/config.yml

# Edit configuration
nano ai_testing/config/config.yml
```

#### 3. Start Services Individually
```bash
# Terminal 1 - Master Orchestrator
export PYTHONPATH=$PWD:$PYTHONPATH
python -m uvicorn ai_testing.orchestration.master_orchestrator:app --port 8000 --reload

# Terminal 2 - Browser Automation
python -m uvicorn ai_testing.services.browser_automation_service:app --port 8001 --reload

# Terminal 3 - API Testing
python -m uvicorn ai_testing.services.api_testing_service:app --port 8002 --reload

# Terminal 4 - AI Quality Assessment
python -m uvicorn ai_testing.services.ai_quality_service:app --port 8003 --reload

# Terminal 5 - Results Aggregation
python -m uvicorn ai_testing.services.results_aggregation_service:app --port 8004 --reload

# Terminal 6 - Notification Service
python -m uvicorn ai_testing.services.notification_service:app --port 8005 --reload
```

#### 4. Development Tools
```bash
# Run tests
python -m pytest ai_testing/tests/ -v

# Code formatting
black ai_testing/
flake8 ai_testing/

# Type checking
mypy ai_testing/
```

## 🌐 Cloud Deployment

### AWS EKS Deployment

#### 1. Create EKS Cluster
```bash
# Install eksctl
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin

# Create cluster
eksctl create cluster --name ai-testing-cluster --region us-west-2 --nodegroup-name standard-workers --node-type m5.large --nodes 3 --nodes-min 1 --nodes-max 4
```

#### 2. Configure kubectl
```bash
# Update kubeconfig
aws eks update-kubeconfig --region us-west-2 --name ai-testing-cluster

# Verify connection
kubectl get nodes
```

#### 3. Deploy to EKS
```bash
# Apply Kubernetes manifests
kubectl apply -f ai_testing/deployment/kubernetes/

# Monitor deployment
kubectl get pods -n ai-testing -w
```

### Google GKE Deployment

#### 1. Create GKE Cluster
```bash
# Create cluster
gcloud container clusters create ai-testing-cluster \
    --zone=us-central1-a \
    --num-nodes=3 \
    --machine-type=e2-standard-4

# Get credentials
gcloud container clusters get-credentials ai-testing-cluster --zone=us-central1-a
```

#### 2. Deploy to GKE
```bash
# Apply manifests
kubectl apply -f ai_testing/deployment/kubernetes/

# Get external IP
kubectl get service ai-testing-orchestrator-external -n ai-testing
```

### Azure AKS Deployment

#### 1. Create AKS Cluster
```bash
# Create resource group
az group create --name ai-testing-rg --location eastus

# Create AKS cluster
az aks create \
    --resource-group ai-testing-rg \
    --name ai-testing-cluster \
    --node-count 3 \
    --node-vm-size Standard_D2s_v3 \
    --enable-addons monitoring

# Get credentials
az aks get-credentials --resource-group ai-testing-rg --name ai-testing-cluster
```

#### 2. Deploy to AKS
```bash
# Apply manifests
kubectl apply -f ai_testing/deployment/kubernetes/

# Monitor deployment
kubectl get pods -n ai-testing
```

## 📊 Monitoring and Observability

### Enable Monitoring Stack

#### 1. Prometheus and Grafana
```bash
# Start with monitoring enabled
docker-compose --profile monitoring up -d

# Access Grafana
open http://localhost:3000
# Username: admin
# Password: admin123
```

#### 2. Custom Dashboards
```bash
# Import provided dashboards
cp ai_testing/deployment/monitoring/grafana/dashboards/* /var/lib/grafana/dashboards/

# Restart Grafana
docker-compose restart grafana
```

#### 3. Alerts Configuration
```bash
# Configure Prometheus alerts
nano ai_testing/deployment/monitoring/prometheus/alerts.yml

# Restart Prometheus
docker-compose restart prometheus
```

### Log Aggregation

#### 1. ELK Stack (Optional)
```bash
# Start ELK stack
docker-compose -f ai_testing/deployment/docker/docker-compose.elk.yml up -d

# Access Kibana
open http://localhost:5601
```

#### 2. Centralized Logging
```bash
# Configure log forwarding
nano ai_testing/config/logging.yml

# Restart services to apply logging config
docker-compose restart
```

## 🔒 Security Configuration

### SSL/TLS Setup

#### 1. Generate Certificates
```bash
# Self-signed certificate for testing
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ai_testing/deployment/ssl/tls.key \
    -out ai_testing/deployment/ssl/tls.crt

# Add to Docker Compose
nano ai_testing/deployment/docker/docker-compose.yml
```

#### 2. Kubernetes TLS
```bash
# Create TLS secret
kubectl create secret tls ai-testing-tls \
    --cert=ai_testing/deployment/ssl/tls.crt \
    --key=ai_testing/deployment/ssl/tls.key \
    -n ai-testing

# Apply ingress with TLS
kubectl apply -f ai_testing/deployment/kubernetes/ingress-tls.yml
```

### API Security

#### 1. Authentication Setup
```bash
# Configure API keys
export AI_TESTING_API_KEY=your-secure-api-key

# Add to service configuration
nano ai_testing/config/security.yml
```

#### 2. Network Security
```bash
# Configure firewall rules (example for Ubuntu)
sudo ufw allow 8000/tcp  # Orchestrator
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 8001:8005/tcp  # Internal services

# For Kubernetes, use NetworkPolicies
kubectl apply -f ai_testing/deployment/kubernetes/network-policies.yml
```

## 🔧 Configuration Reference

### Service Configuration Options

#### Master Orchestrator
```yaml
orchestration:
  services_base_port: 8000
  health_check_interval_seconds: 30
  health_cache_ttl_seconds: 60
  max_concurrent_sessions: 10
  default_timeout_minutes: 60
```

#### Browser Automation
```yaml
browser_automation:
  default_timeout_seconds: 30
  default_viewport_width: 1920
  default_viewport_height: 1080
  headless: true
  enable_video_recording: true
  screenshot_on_failure: true
  browsers: ["chromium", "firefox", "webkit"]
```

#### API Testing
```yaml
api_testing:
  default_timeout_seconds: 30
  max_retries: 3
  retry_delay_seconds: 1
  default_max_response_time_ms: 2000
  enable_load_testing: true
  max_concurrent_requests: 100
```

#### AI Quality Assessment
```yaml
ai_quality:
  llm_judge:
    default_models: ["gpt-4", "gemini-pro"]
    timeout_seconds: 60
    max_retries: 2
    enable_ensemble: true
    quality_threshold: 0.7
```

### Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key | - | No* |
| `ANTHROPIC_API_KEY` | Anthropic API key | - | No* |
| `GOOGLE_API_KEY` | Google AI API key | - | No* |
| `SMTP_HOST` | SMTP server host | - | No |
| `SMTP_PORT` | SMTP server port | 587 | No |
| `SMTP_USERNAME` | SMTP username | - | No |
| `SMTP_PASSWORD` | SMTP password | - | No |
| `SLACK_WEBHOOK_URL` | Slack webhook URL | - | No |
| `LOG_LEVEL` | Logging level | info | No |
| `ENVIRONMENT` | Environment name | production | No |
| `SERVICES_BASE_PORT` | Base port for services | 8000 | No |

*At least one AI service API key is required for AI quality assessment functionality.

## 🚨 Troubleshooting

### Common Deployment Issues

#### Docker Issues
```bash
# Service won't start
docker-compose logs service-name

# Port conflicts
docker-compose down
sudo netstat -tulpn | grep :8000
sudo kill -9 $(sudo lsof -t -i:8000)

# Image build issues
docker-compose build --no-cache service-name
docker system prune -a
```

#### Kubernetes Issues
```bash
# Pod startup failures
kubectl describe pod pod-name -n ai-testing
kubectl logs pod-name -n ai-testing

# Service connectivity
kubectl get endpoints -n ai-testing
kubectl port-forward service/service-name 8000:8000 -n ai-testing

# Resource constraints
kubectl top nodes
kubectl top pods -n ai-testing
```

#### Service Health Issues
```bash
# Check service dependencies
curl http://localhost:8000/services/health | jq

# Test individual services
curl http://localhost:8001/health  # Browser
curl http://localhost:8002/health  # API
curl http://localhost:8003/health  # AI Quality

# Check logs for errors
docker-compose logs -f orchestrator
kubectl logs -f deployment/ai-testing-orchestrator -n ai-testing
```

### Performance Tuning

#### Resource Optimization
```bash
# Monitor resource usage
docker stats
kubectl top pods -n ai-testing

# Adjust resource limits
nano ai_testing/deployment/kubernetes/deployments.yml
kubectl apply -f ai_testing/deployment/kubernetes/deployments.yml
```

#### Service Scaling
```bash
# Scale Docker Compose services
docker-compose up -d --scale api-testing=3 --scale ai-quality=2

# Scale Kubernetes deployments
kubectl scale deployment ai-testing-api-testing --replicas=3 -n ai-testing
kubectl scale deployment ai-testing-ai-quality --replicas=2 -n ai-testing
```

## 📚 Additional Resources

### Documentation
- [API Reference](./api_reference.md)
- [Configuration Guide](./configuration_guide.md)
- [Testing Guide](./testing_guide.md)
- [Development Guide](./development_guide.md)

### Support
- Check service logs for detailed error information
- Review health check endpoints
- Verify external service connectivity
- Ensure proper resource allocation

### Best Practices
1. Always use environment-specific configurations
2. Monitor resource usage and scale appropriately
3. Implement proper backup and disaster recovery
4. Use TLS encryption for production deployments
5. Regularly update dependencies and security patches
6. Monitor service health and performance metrics
7. Implement proper access controls and authentication