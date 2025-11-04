# Deployment Documentation

**Last Updated**: 2024-11-04  
**Status**: Current

**Navigation**: [Home](../../README.md) > [Docs](../INDEX.md) > Deployment

---

## Overview

Deployment guides and infrastructure documentation for Novel Engine production and staging environments.

---

## 📦 Deployment Guides

### [Deployment Guide](./DEPLOYMENT_GUIDE.md) ⭐
**Comprehensive deployment and operations guide (v2.0.0)**
- Environment requirements
- Configuration management
- Docker deployment
- Monitoring and health checks
- Backup and recovery
- Security hardening
- Troubleshooting

- **Audience**: DevOps Engineers, System Administrators
- **Last Updated**: 2024-11-04

### [Production Deployment Guide](./PRODUCTION_DEPLOYMENT_GUIDE.md)
**Production-specific deployment procedures**
- Production environment setup
- CI/CD pipeline configuration
- Release procedures
- Production monitoring

---

## Quick Start

### Local Development
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python api_server.py
```

### Docker Deployment
```bash
docker-compose up -d --build
curl http://localhost/health
```

### Production Deployment
```bash
docker-compose -f docker-compose.prod.yml up -d --build
curl http://localhost/api/meta/system-status
```

---

## Related Documentation

### Operations
- [Operations Runbook](../operations/OPERATIONS_RUNBOOK.md)
- [Runbooks](../runbooks/)
- [Incident Response](../runbooks/incident-response.md)

### Architecture
- [System Architecture](../architecture/SYSTEM_ARCHITECTURE.md)
- [Resiliency Patterns](../architecture/resiliency.md)

### Monitoring
- [Observability](../observability/)
- [Cache Observability](../runbooks/cache-observability.md)

---

**Maintained by**: Novel Engine DevOps Team  
**License**: MIT
