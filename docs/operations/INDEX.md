# Operations Documentation

**Last Updated**: 2024-11-04  
**Status**: Current

**Navigation**: [Home](../../README.md) > [Docs](../INDEX.md) > Operations

---

## Overview

Operational procedures, runbooks, and maintenance guides for Novel Engine production systems.

---

## 📋 Operations Guides

### [Operations Runbook](./OPERATIONS_RUNBOOK.md) ⭐
**Comprehensive operational procedures**
- System startup and shutdown
- Routine maintenance tasks
- Performance monitoring
- Troubleshooting procedures
- Escalation procedures

---

## Quick Reference

### Common Operations

**System Health Check**:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/meta/system-status
```

**Log Monitoring**:
```bash
docker-compose logs -f backend
tail -f logs/app.log
```

**Service Restart**:
```bash
docker-compose restart backend
docker-compose restart frontend
```

---

## Related Documentation

### Deployment
- [Deployment Guide](../deployment/DEPLOYMENT_GUIDE.md)
- [Production Deployment](../deployment/PRODUCTION_DEPLOYMENT_GUIDE.md)

### Runbooks
- [Incident Response](../runbooks/incident-response.md)
- [Cache Observability](../runbooks/cache-observability.md)
- [Feature Flags](../runbooks/feature-flags.md)

### Monitoring
- [Observability](../observability/)
- [Performance Reports](../reports/performance/)

---

**Maintained by**: Novel Engine Operations Team  
**License**: MIT
