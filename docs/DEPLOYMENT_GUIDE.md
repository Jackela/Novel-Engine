# Novel Engine Deployment Guide

**Version**: 1.0.0  
**Target Environment**: Production-Ready Deployment  
**Platform**: Multi-platform (Docker/Cloud/VPS)  
**Date**: 2025-08-12

## 🎯 Deployment Overview

Novel Engine is designed for flexible deployment across multiple environments, from local development to cloud production. This guide covers containerized deployment, environment configuration, and monitoring setup.

## 🏗️ Architecture Components

```yaml
Frontend:
  Technology: React/TypeScript + Vite
  Build Output: Static files for CDN/nginx
  Runtime: None (static serving)
  
Backend:
  Technology: FastAPI + Python 3.11+
  Runtime: uvicorn ASGI server
  Dependencies: OpenAI API, file system storage
  
Infrastructure:
  Reverse Proxy: nginx
  Process Management: Docker Compose
  SSL: Let's Encrypt (certbot)
  Monitoring: Health checks + logging
```

## 🐳 Docker Configuration

### Backend Dockerfile
```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for data storage
RUN mkdir -p /app/data/{characters,stories,campaigns,cache,logs}

# Create non-root user
RUN useradd -m -u 1000 novelengine && \
    chown -R novelengine:novelengine /app
USER novelengine

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

### Frontend Dockerfile
```dockerfile
# frontend/Dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci --only=production

# Copy source code and build
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create nginx user and set permissions
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### Docker Compose Configuration
```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: 
      context: .
      dockerfile: backend/Dockerfile
    container_name: novelengine-backend
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=info
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - CORS_ORIGINS=https://app.novelengine.com
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    networks:
      - novelengine-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: novelengine-frontend
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - novelengine-network
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: novelengine-proxy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - frontend
      - backend
    networks:
      - novelengine-network
    restart: unless-stopped

  # Optional: Redis for caching (future enhancement)
  redis:
    image: redis:7-alpine
    container_name: novelengine-redis
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data
    networks:
      - novelengine-network
    restart: unless-stopped
    profiles:
      - with-redis

networks:
  novelengine-network:
    driver: bridge

volumes:
  redis-data:
```

## 🌐 Nginx Configuration

### Main Nginx Configuration
```nginx
# nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    
    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                   '$status $body_bytes_sent "$http_referer" '
                   '"$http_user_agent" "$http_x_forwarded_for"';
    
    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;
    
    # Basic settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 10M;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=uploads:10m rate=1r/s;

    # Upstream backends
    upstream backend {
        server backend:8000;
        keepalive 32;
    }

    upstream frontend {
        server frontend:80;
        keepalive 32;
    }

    # HTTPS redirect
    server {
        listen 80;
        server_name novelengine.com www.novelengine.com;
        return 301 https://novelengine.com$request_uri;
    }

    # Main server
    server {
        listen 443 ssl http2;
        server_name novelengine.com;
        
        # SSL configuration
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_session_timeout 1d;
        ssl_session_cache shared:SSL:50m;
        ssl_session_tickets off;
        
        # Modern configuration
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;
        
        # HSTS
        add_header Strict-Transport-Security "max-age=63072000" always;
        
        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Referrer-Policy "strict-origin-when-cross-origin";
        
        # API routes
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 300s;
            proxy_connect_timeout 75s;
        }
        
        # File upload routes (separate rate limit)
        location /api/characters {
            limit_req zone=uploads burst=5 nodelay;
            proxy_pass http://backend/characters;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 300s;
            client_max_body_size 10M;
        }
        
        # Health check endpoint
        location /health {
            proxy_pass http://backend/health;
            access_log off;
        }
        
        # Frontend routes
        location / {
            proxy_pass http://frontend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Cache static assets
            location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
                expires 1y;
                add_header Cache-Control "public, immutable";
            }
        }
        
        # Handle SPA routing
        location ~ ^/(?:characters|workshop|library|monitor) {
            proxy_pass http://frontend/;
            proxy_set_header Host $host;
        }
    }
}
```

## 🔧 Environment Configuration

### Environment Variables
```bash
# .env.production
# API Configuration
ENVIRONMENT=production
LOG_LEVEL=info
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=https://novelengine.com,https://www.novelengine.com

# AI Service
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=4000

# Storage
DATA_DIR=/app/data
LOG_DIR=/app/logs
CACHE_TTL=3600
MAX_FILE_SIZE=10485760

# Performance
UVICORN_WORKERS=1
UVICORN_WORKER_CONNECTIONS=100
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=your_secret_key_here_generate_random_string
ALLOWED_HOSTS=novelengine.com,www.novelengine.com
SECURE_SSL_REDIRECT=true

# Monitoring
HEALTH_CHECK_INTERVAL=30
LOG_RETENTION_DAYS=30
METRICS_ENABLED=true
```

### Frontend Environment
```bash
# frontend/.env.production
VITE_API_URL=https://novelengine.com/api
VITE_WS_URL=wss://novelengine.com/ws
VITE_APP_VERSION=1.0.0
VITE_ENVIRONMENT=production
VITE_ENABLE_ANALYTICS=true
VITE_SENTRY_DSN=your_sentry_dsn_here
```

## 🚀 Deployment Scripts

### Automated Deployment Script
```bash
#!/bin/bash
# deploy.sh

set -e

# Configuration
APP_NAME="novelengine"
DEPLOY_DIR="/opt/novelengine"
BACKUP_DIR="/backup/novelengine"
LOG_FILE="/var/log/novelengine-deploy.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Pre-deployment validation
validate_environment() {
    log "Validating deployment environment..."
    
    # Check required files
    if [[ ! -f ".env.production" ]]; then
        log "ERROR: .env.production file not found"
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log "ERROR: Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log "ERROR: Docker Compose is not installed"
        exit 1
    fi
    
    # Validate environment variables
    source .env.production
    if [[ -z "$OPENAI_API_KEY" ]]; then
        log "ERROR: OPENAI_API_KEY not set"
        exit 1
    fi
    
    log "Environment validation passed"
}

# Backup current deployment
backup_current() {
    if [[ -d "$DEPLOY_DIR" ]]; then
        log "Creating backup of current deployment..."
        BACKUP_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        mkdir -p "$BACKUP_DIR"
        tar -czf "$BACKUP_DIR/backup_$BACKUP_TIMESTAMP.tar.gz" -C "$DEPLOY_DIR" . || {
            log "WARNING: Backup failed, continuing with deployment"
        }
        log "Backup created: $BACKUP_DIR/backup_$BACKUP_TIMESTAMP.tar.gz"
    fi
}

# Deploy application
deploy() {
    log "Starting deployment..."
    
    # Create deployment directory
    mkdir -p "$DEPLOY_DIR"
    
    # Copy application files
    log "Copying application files..."
    rsync -av --exclude='.git' --exclude='node_modules' --exclude='__pycache__' \
          ./ "$DEPLOY_DIR/"
    
    # Set up data directories
    mkdir -p "$DEPLOY_DIR/data"/{characters,stories,campaigns,cache,logs}
    mkdir -p "$DEPLOY_DIR/logs/nginx"
    
    # Set permissions
    chown -R www-data:www-data "$DEPLOY_DIR/data"
    chown -R www-data:www-data "$DEPLOY_DIR/logs"
    
    # Copy environment file
    cp .env.production "$DEPLOY_DIR/.env"
    
    log "Application files deployed"
}

# Start services
start_services() {
    log "Starting services..."
    
    cd "$DEPLOY_DIR"
    
    # Build and start containers
    docker-compose down --remove-orphans || true
    docker-compose build --no-cache
    docker-compose up -d
    
    # Wait for services to be healthy
    log "Waiting for services to be healthy..."
    sleep 30
    
    # Check health
    for i in {1..12}; do
        if curl -sf http://localhost/health > /dev/null; then
            log "Services are healthy"
            return 0
        fi
        log "Health check attempt $i/12 failed, waiting..."
        sleep 10
    done
    
    log "ERROR: Services failed to start properly"
    return 1
}

# Post-deployment verification
verify_deployment() {
    log "Verifying deployment..."
    
    # Test API endpoints
    if curl -sf http://localhost/health | grep -q "healthy"; then
        log "✓ Health check passed"
    else
        log "✗ Health check failed"
        return 1
    fi
    
    if curl -sf http://localhost/api/characters > /dev/null; then
        log "✓ API endpoints accessible"
    else
        log "✗ API endpoints failed"
        return 1
    fi
    
    # Test frontend
    if curl -sf http://localhost/ | grep -q "Novel Engine"; then
        log "✓ Frontend accessible"
    else
        log "✗ Frontend failed"
        return 1
    fi
    
    log "Deployment verification passed"
}

# Rollback function
rollback() {
    log "Rolling back deployment..."
    
    cd "$DEPLOY_DIR"
    docker-compose down
    
    # Restore from latest backup
    LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/backup_*.tar.gz | head -n1)
    if [[ -n "$LATEST_BACKUP" ]]; then
        log "Restoring from backup: $LATEST_BACKUP"
        rm -rf "$DEPLOY_DIR"/*
        tar -xzf "$LATEST_BACKUP" -C "$DEPLOY_DIR"
        docker-compose up -d
        log "Rollback completed"
    else
        log "ERROR: No backup found for rollback"
        return 1
    fi
}

# SSL certificate setup
setup_ssl() {
    log "Setting up SSL certificates..."
    
    # Install certbot if not present
    if ! command -v certbot &> /dev/null; then
        apt update && apt install -y certbot python3-certbot-nginx
    fi
    
    # Get certificate
    certbot certonly --webroot \
        -w /var/www/html \
        -d novelengine.com \
        -d www.novelengine.com \
        --email admin@novelengine.com \
        --agree-tos \
        --non-interactive
    
    # Copy certificates to nginx directory
    mkdir -p "$DEPLOY_DIR/nginx/ssl"
    cp /etc/letsencrypt/live/novelengine.com/fullchain.pem "$DEPLOY_DIR/nginx/ssl/"
    cp /etc/letsencrypt/live/novelengine.com/privkey.pem "$DEPLOY_DIR/nginx/ssl/"
    
    # Set up renewal cron job
    (crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet && docker-compose -f $DEPLOY_DIR/docker-compose.yml restart nginx") | crontab -
    
    log "SSL certificates configured"
}

# Main deployment flow
main() {
    log "Starting Novel Engine deployment"
    
    case "${1:-deploy}" in
        "deploy")
            validate_environment
            backup_current
            deploy
            start_services
            verify_deployment || {
                log "Deployment verification failed, rolling back..."
                rollback
                exit 1
            }
            log "Deployment completed successfully"
            ;;
        "rollback")
            rollback
            ;;
        "ssl")
            setup_ssl
            ;;
        "verify")
            verify_deployment
            ;;
        *)
            echo "Usage: $0 {deploy|rollback|ssl|verify}"
            exit 1
            ;;
    esac
}

main "$@"
```

### Quick Start Script
```bash
#!/bin/bash
# quick-start.sh

set -e

echo "🚀 Novel Engine Quick Start"
echo "=========================="

# Check prerequisites
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

# Environment setup
if [[ ! -f ".env" ]]; then
    echo "📝 Creating environment configuration..."
    read -p "Enter your OpenAI API key: " -s OPENAI_API_KEY
    echo
    
    cat > .env << EOF
ENVIRONMENT=development
OPENAI_API_KEY=$OPENAI_API_KEY
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
LOG_LEVEL=info
EOF
    echo "✅ Environment file created"
fi

# Start services
echo "🐳 Starting Novel Engine services..."
docker-compose up -d

# Wait for services
echo "⏳ Waiting for services to start..."
sleep 20

# Health check
if curl -sf http://localhost:8000/health > /dev/null; then
    echo "✅ Backend is healthy"
else
    echo "❌ Backend health check failed"
    docker-compose logs backend
    exit 1
fi

echo ""
echo "🎉 Novel Engine is ready!"
echo ""
echo "📱 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "📊 API Docs: http://localhost:8000/docs"
echo "💻 Health Check: http://localhost:8000/health"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down"
```

## 📊 Monitoring and Logging

### Health Check Configuration
```python
# health_check.py
import asyncio
import aiohttp
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthMonitor:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.health_log = Path("/var/log/novelengine/health.log")
        
    async def check_health(self):
        """Comprehensive health check"""
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "healthy",
            "checks": {}
        }
        
        async with aiohttp.ClientSession() as session:
            # API health check
            try:
                async with session.get(f"{self.base_url}/health", timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results["checks"]["api"] = {
                            "status": "healthy",
                            "response_time_ms": resp.headers.get("X-Response-Time", "unknown"),
                            "details": data
                        }
                    else:
                        results["checks"]["api"] = {"status": "unhealthy", "code": resp.status}
                        results["overall_status"] = "degraded"
            except Exception as e:
                results["checks"]["api"] = {"status": "error", "error": str(e)}
                results["overall_status"] = "error"
            
            # Characters endpoint check
            try:
                async with session.get(f"{self.base_url}/characters", timeout=5) as resp:
                    if resp.status == 200:
                        results["checks"]["characters"] = {"status": "healthy"}
                    else:
                        results["checks"]["characters"] = {"status": "unhealthy", "code": resp.status}
                        results["overall_status"] = "degraded"
            except Exception as e:
                results["checks"]["characters"] = {"status": "error", "error": str(e)}
                if results["overall_status"] == "healthy":
                    results["overall_status"] = "degraded"
        
        # Log results
        logger.info(f"Health check: {results['overall_status']}")
        
        return results
    
    async def monitor_loop(self, interval: int = 60):
        """Continuous monitoring loop"""
        while True:
            try:
                health = await self.check_health()
                
                # Write to health log
                with open(self.health_log, "a") as f:
                    f.write(f"{health['timestamp']},{health['overall_status']}\n")
                
                # Alert on errors
                if health["overall_status"] == "error":
                    logger.error(f"System health critical: {health}")
                    # Send alert (email, Slack, etc.)
                    
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
            
            await asyncio.sleep(interval)

if __name__ == "__main__":
    monitor = HealthMonitor()
    asyncio.run(monitor.monitor_loop())
```

### Log Rotation Configuration
```bash
# /etc/logrotate.d/novelengine
/var/log/novelengine/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    postrotate
        docker-compose -f /opt/novelengine/docker-compose.yml restart backend
    endscript
}

/opt/novelengine/logs/nginx/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    postrotate
        docker-compose -f /opt/novelengine/docker-compose.yml exec nginx nginx -s reload
    endscript
}
```

## 🔐 Security Hardening

### System Security
```bash
#!/bin/bash
# security-hardening.sh

# Update system
apt update && apt upgrade -y

# Install security tools
apt install -y fail2ban ufw

# Configure firewall
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw --force enable

# Configure fail2ban
cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[nginx-http-auth]
enabled = true

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
action = iptables-multiport[name=ReqLimit, port="http,https", protocol=tcp]
logpath = /opt/novelengine/logs/nginx/error.log
maxretry = 10
findtime = 600
bantime = 7200
EOF

systemctl enable fail2ban
systemctl start fail2ban

# Set up automatic security updates
echo 'Unattended-Upgrade::Automatic-Reboot "false";' >> /etc/apt/apt.conf.d/50unattended-upgrades

# Configure Docker security
echo '{"log-driver": "json-file", "log-opts": {"max-size": "10m", "max-file": "3"}}' > /etc/docker/daemon.json
systemctl reload docker

echo "Security hardening completed"
```

## 📈 Performance Optimization

### Production Optimizations
```yaml
# docker-compose.production.yml
version: '3.8'

services:
  backend:
    build: 
      context: .
      dockerfile: backend/Dockerfile
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
    environment:
      - UVICORN_WORKERS=2
      - UVICORN_WORKER_CONNECTIONS=50
      - CACHE_TTL=1800
    ulimits:
      nofile:
        soft: 65536
        hard: 65536

  frontend:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 128M
    
  nginx:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 128M
    volumes:
      - ./nginx/nginx.production.conf:/etc/nginx/nginx.conf

  redis:
    deploy:
      resources:
        limits:
          cpus: '0.25'
          memory: 64M
    command: >
      redis-server
      --maxmemory 50mb
      --maxmemory-policy allkeys-lru
      --save 900 1
      --save 300 10
```

---

This deployment guide provides production-ready configurations for Novel Engine. The setup includes containerization, security hardening, monitoring, and automated deployment scripts suitable for VPS or cloud environments.

**Next Steps**:
1. Customize environment variables for your deployment
2. Set up domain and SSL certificates
3. Configure monitoring and alerting
4. Test deployment with staging environment
5. Set up backup and disaster recovery procedures