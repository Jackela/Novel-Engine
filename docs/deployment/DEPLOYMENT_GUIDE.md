# Novel Engine Deployment Guide

**Version**: 2.0.0  
**Last Updated**: 2024-11-04  
**Status**: Current  
**Audience**: DevOps Engineers, System Administrators

**Navigation**: [Home](../../README.md) > [Docs](../INDEX.md) > [Deployment](../deployment/) > Deployment Guide

---

## Overview

Novel Engine supports multiple deployment strategies from local development to cloud production. This guide covers containerized deployment, environment configuration, and monitoring setup.

---

## Environment Requirements

### Baseline Requirements

**Python Backend**:
- Python 3.11+
- 2+ CPU cores
- 4GB+ RAM
- 10GB+ disk space
- Linux/Windows/macOS

**Frontend**:
- Node.js 18+
- npm 9+
- Modern browser support

**Optional**:
- GPU for local embedding (recommended)
- Redis for caching (optional)

### Key Dependencies

**Backend** (`requirements.txt`):
```
fastapi>=0.116.1
uvicorn>=0.35.0
pydantic>=2.11.7
aiosqlite>=0.17.0
jinja2>=3.0.0
pyyaml>=6.0.0
```

**Frontend** (`frontend/package.json`):
```json
{
  "react": "^18.0.0",
  "typescript": "^5.0.0",
  "vite": "^5.0.0",
  "@mui/material": "^5.0.0"
}
```

---

## Configuration Management

### Configuration Files

**Primary Config** (`config.yaml`):
```yaml
system:
  mode: "production"  # production | development | testing
  log_level: "INFO"
  debug: false

api:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  timeout: 60

ai_services:
  provider: "gemini"  # gemini | openai
  model: "gemini-pro"
  temperature: 0.7
  max_tokens: 2048
  
performance:
  cache_enabled: true
  cache_ttl: 3600
  max_concurrent_requests: 100
  
paths:
  characters: "./characters"
  campaigns: "./campaigns"
  templates: "./templates"
  data: "./data"
  logs: "./logs"

policy:
  monetization: "disabled"  # MUST be disabled
  allow_trademarks: false   # MUST be false for public builds
  fan_mode_requires_local_registry: true
```

### Environment Variables

**Required**:
```bash
# AI Service API Keys (DO NOT commit)
GEMINI_API_KEY=your_api_key_here
OPENAI_API_KEY=your_api_key_here  # fallback

# Application Settings
APP_MODE=production
LOG_LEVEL=INFO

# Frontend (Optional)
VITE_API_URL=http://localhost:8000
```

**Environment File** (`.env.production`):
```bash
# Copy from .env.example
APP_MODE=production
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000

# Security
SECRET_KEY=your_secret_key_here

# Paths
DATA_DIR=./data
LOG_DIR=./logs
```

**Security Notes**:
- ✅ Store API keys in environment variables
- ❌ Never commit API keys to version control
- ✅ Use different keys for dev/staging/prod
- ✅ Rotate keys periodically

---

## Docker Deployment

### Complete Docker Setup

**Directory Structure**:
```
Novel-Engine/
├── docker-compose.yml
├── Dockerfile
├── frontend/
│   └── Dockerfile
├── nginx/
│   └── nginx.conf
└── .env.production
```

### Backend Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p /app/data/{characters,campaigns,logs} && \
    mkdir -p /app/characters /app/campaigns

# Create non-root user
RUN useradd -m -u 1000 novelengine && \
    chown -R novelengine:novelengine /app
USER novelengine

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Dockerfile

```dockerfile
# Build stage
FROM node:18-alpine AS builder

WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci --only=production

COPY frontend/ .
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Set permissions
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### Docker Compose Configuration

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: novel-engine-backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - .env.production
    volumes:
      - ./data:/app/data
      - ./characters:/app/characters
      - ./campaigns:/app/campaigns
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - novel-engine-network

  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    container_name: novel-engine-frontend
    restart: unless-stopped
    ports:
      - "3000:80"
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - novel-engine-network

  nginx:
    image: nginx:alpine
    container_name: novel-engine-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - backend
      - frontend
    networks:
      - novel-engine-network

networks:
  novel-engine-network:
    driver: bridge

volumes:
  novel-data:
    driver: local
```

### Nginx Configuration

**nginx/nginx.conf**:
```nginx
upstream backend {
    server backend:8000;
}

upstream frontend {
    server frontend:80;
}

server {
    listen 80;
    server_name localhost;

    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Backend API
    location /api/ {
        proxy_pass http://backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # Timeouts for long-running story generation
        proxy_read_timeout 300s;
        proxy_connect_timeout 60s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://backend/health;
        access_log off;
    }
}
```

---

## Deployment Procedures

### 1. Local Development

```bash
# Backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python api_server.py

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### 2. Docker Deployment

```bash
# Build and start services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild specific service
docker-compose up -d --build backend
```

### 3. Production Deployment

```bash
# 1. Clone repository
git clone https://github.com/your-org/Novel-Engine.git
cd Novel-Engine

# 2. Configure environment
cp .env.example .env.production
# Edit .env.production with your settings

# 3. Build and start
docker-compose -f docker-compose.prod.yml up -d --build

# 4. Verify deployment
curl http://localhost/health
curl http://localhost/api/meta/system-status

# 5. Monitor logs
docker-compose logs -f backend
```

---

## Startup Procedures

### Knowledge Base Initialization

**Neutral Mode** (default):
```bash
python scripts/build_kb.py
```

**Fan Mode** (local only):
```bash
# Ensure private/registry.yaml is compliant
python scripts/ingest_local_assets.py
python scripts/build_kb.py --mode fan
```

### API Server Startup

**Development**:
```bash
uvicorn api_server:app --reload --port 8000
```

**Production**:
```bash
# With Gunicorn (recommended)
gunicorn -w 4 -k uvicorn.workers.UvicornWorker api_server:app --bind 0.0.0.0:8000

# Or with uvicorn directly
uvicorn api_server:app --host 0.0.0.0 --port 8000 --workers 4
```

### Startup Guards

The application includes compliance checks:
- ✅ Fan mode requires valid `private/registry.yaml`
- ✅ Monetization must be disabled
- ✅ Trademark restrictions enforced

**Startup fails if**:
- Missing configuration files
- Invalid compliance settings
- Missing required API keys

---

## Monitoring & Health Checks

### Health Check Endpoints

**Liveness Probe**:
```bash
curl http://localhost:8000/health

# Response:
{
  "api": "healthy",
  "config": "loaded",
  "version": "1.0.0",
  "uptime_seconds": 3600
}
```

**Readiness Probe**:
```bash
curl http://localhost:8000/meta/system-status

# Response includes performance metrics
{
  "api": "healthy",
  "performance": {
    "avg_response_time_ms": 150,
    "cache_hit_rate": 0.89,
    "active_connections": 12
  }
}
```

### Logging

**Application Logs**:
```yaml
Format: JSON structured logging
Location: ./logs/app.log
Rotation: Daily, 7-day retention
Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

Example Log Entry:
{
  "timestamp": "2024-11-04T10:30:00Z",
  "level": "INFO",
  "message": "Story generation completed",
  "context": {
    "simulation_id": "sim_123",
    "duration_seconds": 45.2,
    "characters": ["krieg", "ork"]
  }
}
```

**Access Logs** (nginx):
```
Location: ./logs/nginx/access.log
Format: Combined (includes user agent, referrer)
```

**Error Logs** (nginx):
```
Location: ./logs/nginx/error.log
Level: warn
```

### Metrics Collection

**Application Metrics**:
- Request rate and latency
- Error rate by endpoint
- AI service response times
- Cache hit rates
- Memory usage

**Collection Methods**:
```bash
# Prometheus endpoint (if enabled)
curl http://localhost:8000/metrics

# Health check for monitoring
curl http://localhost:8000/health
```

---

## Backup & Recovery

### Backup Strategy

**What to Backup**:
- Character definitions (`./characters/`)
- Campaign data (`./campaigns/`)
- User data (`./data/`)
- Configuration (`config.yaml`, `.env`)
- Logs (`./logs/`)

**Backup Script**:
```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups/$DATE"

mkdir -p $BACKUP_DIR

# Backup data directories
cp -r characters $BACKUP_DIR/
cp -r campaigns $BACKUP_DIR/
cp -r data $BACKUP_DIR/
cp config.yaml $BACKUP_DIR/

# Compress
tar -czf backups/novel-engine-$DATE.tar.gz $BACKUP_DIR
rm -rf $BACKUP_DIR

echo "Backup created: novel-engine-$DATE.tar.gz"
```

**Automated Backups** (cron):
```cron
# Daily backup at 2 AM
0 2 * * * /path/to/Novel-Engine/backup.sh
```

### Recovery Procedure

```bash
# 1. Stop services
docker-compose down

# 2. Extract backup
tar -xzf backups/novel-engine-YYYYMMDD_HHMMSS.tar.gz

# 3. Restore data
cp -r backup/characters ./
cp -r backup/campaigns ./
cp -r backup/data ./

# 4. Restart services
docker-compose up -d

# 5. Verify
curl http://localhost/health
```

---

## Security Hardening

### Application Security

**Environment Variables**:
```bash
# Use strong secrets
SECRET_KEY=$(openssl rand -hex 32)

# API keys from secure vault
export GEMINI_API_KEY=$(vault kv get secret/gemini-api-key)
```

**File Permissions**:
```bash
# Restrict config files
chmod 600 .env.production
chmod 600 config.yaml

# Data directories
chmod 750 data/
chmod 750 logs/
```

### Network Security

**Firewall Rules**:
```bash
# Allow only necessary ports
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 22/tcp    # SSH (admin only)
ufw enable
```

**SSL/TLS** (Let's Encrypt):
```bash
# Install certbot
apt-get install certbot python3-certbot-nginx

# Obtain certificate
certbot --nginx -d yourdomain.com

# Auto-renewal (cron)
0 12 * * * certbot renew --quiet
```

---

## Troubleshooting

### Common Issues

**Issue**: Backend won't start
```bash
# Check logs
docker-compose logs backend

# Common causes:
# - Missing API keys
# - Invalid config.yaml
# - Port 8000 already in use

# Solutions:
docker-compose down
lsof -i :8000  # Find process using port
kill <PID>
docker-compose up -d
```

**Issue**: Frontend can't connect to backend
```bash
# Check VITE_API_URL in frontend/.env
# Should match backend URL

# Verify backend is running
curl http://localhost:8000/health

# Check nginx proxy configuration
docker-compose logs nginx
```

**Issue**: Story generation fails
```bash
# Check AI service API key
echo $GEMINI_API_KEY

# Check logs for API errors
docker-compose logs backend | grep ERROR

# Test AI service connectivity
curl https://generativelanguage.googleapis.com/v1/models
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run backend with verbose output
python api_server.py --log-level DEBUG

# Check all environment variables
docker-compose config
```

---

## Performance Tuning

### Backend Optimization

```python
# config.yaml
performance:
  cache_enabled: true
  cache_ttl: 3600
  max_concurrent_requests: 100
  worker_processes: 4  # CPU cores
  worker_connections: 1000
```

### Database Optimization

```python
# Connection pooling
database:
  pool_size: 20
  max_overflow: 10
  pool_timeout: 30
```

### Resource Limits

**Docker** (docker-compose.yml):
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

---

## Scaling Strategies

### Horizontal Scaling

```yaml
# docker-compose.scale.yml
services:
  backend:
    deploy:
      replicas: 3
    
  nginx:
    # Load balancer configuration
    volumes:
      - ./nginx/load-balance.conf:/etc/nginx/nginx.conf
```

### Vertical Scaling

```bash
# Increase resources
docker-compose up -d --scale backend=1 --force-recreate

# Update resource limits in docker-compose.yml
```

---

## Release & Versioning

**Strategy**: Semantic Versioning (SemVer)

**Process**:
```bash
# 1. Update version
vi pyproject.toml  # Update version field

# 2. Create changelog entry
vi CHANGELOG.md

# 3. Commit and tag
git commit -am "Release v2.0.0"
git tag v2.0.0
git push origin main --tags

# 4. CI/CD builds and tests automatically
# 5. Manual production deployment
```

---

## Related Documentation

- [Operations Runbook](../operations/OPERATIONS_RUNBOOK.md)
- [API Reference](../api/API_REFERENCE.md)
- [System Architecture](../architecture/SYSTEM_ARCHITECTURE.md)
- [Security Guide](./security-guide.md) (Coming Soon)

---

**Last Updated**: 2024-11-04  
**Maintained by**: Novel Engine DevOps Team  
**License**: MIT
