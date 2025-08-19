# Novel Engine Operations Runbook

## Emergency Response Procedures

### Incident Response Workflow

#### Severity Levels
- **P0 (Critical)**: Service completely down, data loss
- **P1 (High)**: Major functionality impaired, security breach
- **P2 (Medium)**: Minor functionality impaired, performance degraded
- **P3 (Low)**: Minor issues, cosmetic problems

#### Response Times
- **P0**: Immediate response (< 15 minutes)
- **P1**: 1 hour
- **P2**: 4 hours
- **P3**: 24 hours

### Common Emergency Scenarios

#### 1. Service Completely Down (P0)

**Symptoms:**
- Health check endpoints failing
- All requests returning 500/503 errors
- No response from application

**Immediate Actions:**
```bash
# Check cluster status
kubectl get nodes
kubectl get pods -n novel-engine-production --watch

# Check recent events
kubectl get events -n novel-engine-production --sort-by='.lastTimestamp'

# Check application logs
kubectl logs -l app=novel-engine -n novel-engine-production --tail=100

# Emergency scale up if resource issue
kubectl scale deployment novel-engine --replicas=5 -n novel-engine-production
```

**Investigation Steps:**
```bash
# Check infrastructure health
aws eks describe-cluster --name novel-engine-production-cluster

# Check load balancer
kubectl get ingress -n novel-engine-production
kubectl describe ingress novel-engine -n novel-engine-production

# Check database connectivity
kubectl exec -it deployment/novel-engine -n novel-engine-production -- \
    python -c "import sqlite3; conn = sqlite3.connect('/app/data/novel-engine.db'); print('DB OK')"
```

**Recovery Actions:**
```bash
# If application pods are failing
kubectl rollout restart deployment/novel-engine -n novel-engine-production

# If database is corrupted, restore from backup
kubectl cp backup-novel-engine-20240818.db \
    novel-engine-production/novel-engine-pod:/app/data/novel-engine.db

# If DNS issues, check ingress
kubectl get ingress -n novel-engine-production -o yaml
```

#### 2. High Error Rate (P1)

**Symptoms:**
- Error rate > 5%
- 5xx status codes increasing
- Performance degradation

**Investigation:**
```bash
# Check error patterns in logs
kubectl logs -l app=novel-engine -n novel-engine-production | grep -i error | tail -50

# Check metrics
curl -s https://novel-engine.com/metrics | grep -E "(error_total|response_time)"

# Check resource usage
kubectl top pods -n novel-engine-production
```

**Common Causes & Solutions:**

**Database Connection Issues:**
```bash
# Check database connectivity
kubectl exec -it deployment/redis -n novel-engine-production -- redis-cli ping

# Restart Redis if needed
kubectl rollout restart deployment/redis -n novel-engine-production
```

**Memory Issues:**
```bash
# Check memory usage
kubectl top pods -n novel-engine-production

# Scale up if needed
kubectl scale deployment novel-engine --replicas=5 -n novel-engine-production

# Update resource limits if consistently hitting limits
kubectl patch deployment novel-engine -n novel-engine-production -p \
    '{"spec":{"template":{"spec":{"containers":[{"name":"novel-engine","resources":{"limits":{"memory":"1Gi"}}}]}}}}'
```

#### 3. Performance Degradation (P2)

**Symptoms:**
- Response times > 1000ms
- High CPU/memory usage
- Slow database queries

**Investigation:**
```bash
# Check HPA status
kubectl get hpa -n novel-engine-production
kubectl describe hpa novel-engine-hpa -n novel-engine-production

# Check resource utilization
kubectl top pods -n novel-engine-production
kubectl top nodes

# Check database performance
kubectl exec -it deployment/novel-engine -n novel-engine-production -- \
    sqlite3 /app/data/novel-engine.db "EXPLAIN QUERY PLAN SELECT * FROM campaigns LIMIT 1;"
```

**Optimization Actions:**
```bash
# Enable HPA if not already
kubectl autoscale deployment novel-engine \
    --cpu-percent=70 --min=3 --max=10 \
    -n novel-engine-production

# Clear Redis cache
kubectl exec -it deployment/redis -n novel-engine-production -- redis-cli FLUSHALL

# Restart application to clear memory leaks
kubectl rollout restart deployment/novel-engine -n novel-engine-production
```

## Monitoring and Alerting

### Key Metrics to Monitor

#### Application Metrics
- **Request Rate**: requests/second
- **Error Rate**: percentage of 5xx responses
- **Response Time**: 95th percentile latency
- **Active Users**: concurrent sessions
- **Queue Depth**: pending narrative generations

#### Infrastructure Metrics
- **CPU Usage**: per pod and cluster-wide
- **Memory Usage**: per pod and cluster-wide
- **Disk Usage**: persistent volume utilization
- **Network I/O**: ingress/egress traffic

#### Database Metrics
- **Connection Count**: active database connections
- **Query Performance**: average query execution time
- **Lock Wait Time**: database lock contention
- **Cache Hit Rate**: Redis cache efficiency

### Alert Thresholds

```yaml
# Prometheus Alert Rules
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "High error rate detected"

- alert: HighResponseTime
  expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High response time detected"

- alert: PodCrashLooping
  expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Pod is crash looping"
```

### Monitoring Dashboard URLs
- **Application Dashboard**: https://monitoring.novel-engine.com/d/novel-engine-app
- **Infrastructure Dashboard**: https://monitoring.novel-engine.com/d/novel-engine-infra
- **Database Dashboard**: https://monitoring.novel-engine.com/d/novel-engine-db

## Maintenance Procedures

### Daily Checklist
- [ ] Check service health (automated)
- [ ] Review error logs for anomalies
- [ ] Verify backup completion
- [ ] Monitor resource usage trends

### Weekly Checklist
- [ ] Review performance metrics
- [ ] Check security alerts
- [ ] Verify SSL certificate status
- [ ] Update dependency vulnerability reports
- [ ] Test backup restoration procedure

### Monthly Checklist
- [ ] Review and rotate secrets
- [ ] Update system dependencies
- [ ] Performance optimization review
- [ ] Capacity planning assessment
- [ ] Disaster recovery test

### Quarterly Checklist
- [ ] Security audit and penetration testing
- [ ] Infrastructure cost optimization
- [ ] Documentation review and updates
- [ ] Team training and knowledge transfer

## Backup and Recovery

### Automated Backup Schedule
- **Database**: Every 6 hours
- **Configuration**: Daily
- **Application Data**: Daily
- **Infrastructure State**: Weekly

### Backup Verification
```bash
# Daily backup verification script
#!/bin/bash
BACKUP_DATE=$(date +%Y-%m-%d)
BACKUP_FILE="/backups/$BACKUP_DATE/novel-engine-backup.db"

if [ -f "$BACKUP_FILE" ]; then
    # Test backup integrity
    sqlite3 "$BACKUP_FILE" "PRAGMA integrity_check;"
    if [ $? -eq 0 ]; then
        echo "✅ Backup verified: $BACKUP_FILE"
    else
        echo "❌ Backup corrupted: $BACKUP_FILE"
        # Send alert
    fi
else
    echo "❌ Backup missing: $BACKUP_FILE"
    # Send alert
fi
```

### Recovery Procedures

#### Database Recovery
```bash
# Stop application
kubectl scale deployment novel-engine --replicas=0 -n novel-engine-production

# Copy backup to pod
kubectl cp backup-novel-engine-latest.db \
    novel-engine-production/novel-engine-pod:/app/data/novel-engine.db

# Restart application
kubectl scale deployment novel-engine --replicas=3 -n novel-engine-production

# Verify recovery
kubectl port-forward service/novel-engine 8080:8000 -n novel-engine-production &
curl http://localhost:8080/health
```

#### Full System Recovery
```bash
# Restore infrastructure using Terraform
cd terraform
terraform apply -auto-approve

# Restore Kubernetes manifests
kubectl apply -f backup-k8s-20240818.yaml

# Restore application data
kubectl cp backup-data/ novel-engine-production/novel-engine-pod:/app/data/
```

## Security Operations

### Security Monitoring
- **Failed Authentication Attempts**: Monitor login failures
- **Suspicious API Usage**: Rate limiting violations
- **Container Vulnerabilities**: Daily security scans
- **Network Traffic**: Unusual outbound connections
- **File System Changes**: Unauthorized file modifications

### Security Incident Response

#### Suspected Breach (P0)
```bash
# Immediate isolation
kubectl patch networkpolicy novel-engine-network-policy \
    -n novel-engine-production \
    --type='json' -p='[{"op": "replace", "path": "/spec/ingress", "value": []}]'

# Capture forensic data
kubectl exec -it deployment/novel-engine -n novel-engine-production -- \
    tar -czf /tmp/forensic-$(date +%Y%m%d-%H%M%S).tar.gz /app/logs /app/data

# Review audit logs
kubectl logs -l app=novel-engine -n novel-engine-production --since=24h | \
    grep -E "(auth|login|admin|unauthorized)"
```

#### Vulnerability Response
```bash
# Scan for vulnerabilities
trivy image ghcr.io/your-org/novel-engine:latest

# Check running containers
kubectl get pods -n novel-engine-production -o jsonpath='{.items[*].spec.containers[*].image}'

# Force update if critical vulnerabilities found
kubectl set image deployment/novel-engine \
    novel-engine=ghcr.io/your-org/novel-engine:latest-patched \
    -n novel-engine-production
```

## Performance Tuning

### Database Optimization
```bash
# Analyze query performance
kubectl exec -it deployment/novel-engine -n novel-engine-production -- \
    sqlite3 /app/data/novel-engine.db "EXPLAIN QUERY PLAN SELECT * FROM campaigns ORDER BY created_at DESC LIMIT 10;"

# Rebuild database statistics
kubectl exec -it deployment/novel-engine -n novel-engine-production -- \
    sqlite3 /app/data/novel-engine.db "ANALYZE;"

# Vacuum database
kubectl exec -it deployment/novel-engine -n novel-engine-production -- \
    sqlite3 /app/data/novel-engine.db "VACUUM;"
```

### Cache Optimization
```bash
# Check Redis memory usage
kubectl exec -it deployment/redis -n novel-engine-production -- \
    redis-cli INFO memory

# Monitor cache hit rate
kubectl exec -it deployment/redis -n novel-engine-production -- \
    redis-cli INFO stats | grep -E "(keyspace_hits|keyspace_misses)"

# Adjust cache policies if needed
kubectl exec -it deployment/redis -n novel-engine-production -- \
    redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### Application Performance
```bash
# Profile application performance
kubectl port-forward service/novel-engine 8080:8000 -n novel-engine-production &
curl http://localhost:8080/metrics | grep -E "(python_gc|process_)"

# Monitor memory usage
kubectl exec -it deployment/novel-engine -n novel-engine-production -- \
    python -c "import psutil; print(f'Memory: {psutil.virtual_memory().percent}%')"
```

## Cost Optimization

### Resource Right-Sizing
```bash
# Analyze resource usage over time
kubectl top pods -n novel-engine-production --sort-by=cpu
kubectl top pods -n novel-engine-production --sort-by=memory

# Check HPA recommendations
kubectl describe hpa novel-engine-hpa -n novel-engine-production

# Adjust resource requests/limits based on usage
kubectl patch deployment novel-engine -n novel-engine-production -p \
    '{"spec":{"template":{"spec":{"containers":[{"name":"novel-engine","resources":{"requests":{"cpu":"400m","memory":"400Mi"}}}]}}}}'
```

### Infrastructure Optimization
```bash
# Review AWS costs
aws ce get-cost-and-usage \
    --time-period Start=2024-08-01,End=2024-08-31 \
    --granularity MONTHLY \
    --metrics BlendedCost \
    --group-by Type=DIMENSION,Key=SERVICE

# Optimize EBS volumes
kubectl get pvc -n novel-engine-production -o yaml | grep -A5 -B5 storage
```

## Communication Procedures

### Incident Communication Template
```
Subject: [P{severity}] Novel Engine - {Brief Description}

Status: INVESTIGATING | IDENTIFIED | MONITORING | RESOLVED
Start Time: {timestamp}
Impact: {description of user impact}
Affected Components: {list of affected services}

Updates:
- {timestamp}: {update description}

Next Update: {timestamp}
Contact: {on-call engineer}
```

### Escalation Contacts
- **Level 1**: DevOps Team (Slack: #novel-engine-ops)
- **Level 2**: Technical Lead (+1-555-0123)
- **Level 3**: Engineering Manager (+1-555-0124)
- **Level 4**: CTO (+1-555-0125)

### Status Page Updates
```bash
# Update status page (example using statuspage.io API)
curl -X PATCH "https://api.statuspage.io/v1/pages/{page_id}/incidents/{incident_id}" \
    -H "Authorization: OAuth {token}" \
    -H "Content-Type: application/json" \
    -d '{
        "incident": {
            "status": "investigating",
            "message": "We are investigating reports of degraded performance."
        }
    }'
```

## Tools and Scripts

### Quick Diagnosis Script
```bash
#!/bin/bash
# quick-health-check.sh

echo "🏥 Novel Engine Health Check"
echo "=============================="

# Cluster health
echo "Cluster Nodes:"
kubectl get nodes --no-headers | wc -l

# Application status
echo "Application Pods:"
kubectl get pods -n novel-engine-production -l app=novel-engine --no-headers | wc -l

# Service health
echo "Service Endpoints:"
kubectl get endpoints -n novel-engine-production novel-engine -o jsonpath='{.subsets[*].addresses[*].ip}' | wc -w

# Quick health check
echo "Health Check:"
kubectl port-forward service/novel-engine 8080:8000 -n novel-engine-production >/dev/null 2>&1 &
PF_PID=$!
sleep 3
if curl -s http://localhost:8080/health >/dev/null; then
    echo "✅ Application responding"
else
    echo "❌ Application not responding"
fi
kill $PF_PID 2>/dev/null

echo "=============================="
```

### Log Analysis Script
```bash
#!/bin/bash
# analyze-logs.sh

NAMESPACE="novel-engine-production"
TIME_RANGE="1h"

echo "📋 Log Analysis - Last $TIME_RANGE"
echo "================================="

# Error summary
echo "Error Summary:"
kubectl logs -l app=novel-engine -n $NAMESPACE --since=$TIME_RANGE | \
    grep -i error | \
    awk '{print $NF}' | \
    sort | uniq -c | sort -nr | head -10

# Response time analysis
echo "Response Time Analysis:"
kubectl logs -l app=novel-engine -n $NAMESPACE --since=$TIME_RANGE | \
    grep "response_time" | \
    awk '{print $NF}' | \
    sort -n | \
    awk 'BEGIN{sum=0; count=0} {sum+=$1; count++} END{if(count>0) print "Average:", sum/count "ms"}'

echo "================================="
```

## Knowledge Base

### Common Issues and Solutions

#### Issue: Pod Stuck in Pending State
**Cause**: Insufficient cluster resources
**Solution**: 
```bash
kubectl describe pod <pod-name> -n novel-engine-production
# Scale down other workloads or add nodes
```

#### Issue: Database Lock Timeout
**Cause**: Long-running transactions
**Solution**:
```bash
# Check for long-running transactions
kubectl exec -it deployment/novel-engine -n novel-engine-production -- \
    sqlite3 /app/data/novel-engine.db ".timeout 30000"
```

#### Issue: Memory Leak
**Cause**: Application not releasing memory
**Solution**:
```bash
# Restart application
kubectl rollout restart deployment/novel-engine -n novel-engine-production
# Monitor memory usage
kubectl top pods -n novel-engine-production --sort-by=memory
```

### Performance Baselines
- **Response Time**: 95th percentile < 500ms
- **Error Rate**: < 0.1%
- **CPU Usage**: < 70% average
- **Memory Usage**: < 80% of limit
- **Database Response**: < 50ms average