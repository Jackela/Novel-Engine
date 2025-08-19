# Novel Engine Production Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying Novel Engine to production environments using enterprise-grade infrastructure patterns.

## Architecture Overview

### Infrastructure Components
- **Container Platform**: Kubernetes (EKS)
- **Container Registry**: GitHub Container Registry (GHCR)
- **Infrastructure as Code**: Terraform
- **Monitoring**: Prometheus + Grafana + AlertManager
- **Logging**: Loki + Promtail
- **Load Balancing**: NGINX Ingress Controller
- **Storage**: EBS CSI Driver (Persistent Volumes)
- **Networking**: AWS VPC with private/public subnets

### Security Features
- **Container Security**: Non-root containers, read-only root filesystem
- **Network Security**: Network policies, VPC security groups
- **Secret Management**: Kubernetes secrets, AWS IAM roles
- **SSL/TLS**: Automatic certificate management with cert-manager
- **Image Security**: Vulnerability scanning with Trivy

## Prerequisites

### Infrastructure Requirements
- AWS Account with appropriate permissions
- Domain name for SSL certificates
- S3 bucket for Terraform state
- DynamoDB table for Terraform locks

### Required Tools
```bash
# Install required tools
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
curl -fsSL https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
```

### Environment Setup
```bash
# Configure AWS CLI
aws configure

# Set required environment variables
export AWS_REGION=us-west-2
export CLUSTER_NAME=novel-engine-production-cluster
export DOMAIN_NAME=novel-engine.com
```

## Infrastructure Deployment

### 1. Terraform State Setup
```bash
# Create S3 bucket for Terraform state
aws s3 mb s3://novel-engine-terraform-state

# Create DynamoDB table for state locking
aws dynamodb create-table \
    --table-name novel-engine-terraform-locks \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
```

### 2. Infrastructure Provisioning
```bash
cd terraform

# Initialize Terraform
terraform init \
    -backend-config="bucket=novel-engine-terraform-state" \
    -backend-config="key=production/terraform.tfstate" \
    -backend-config="region=us-west-2"

# Create terraform.tfvars
cat > terraform.tfvars << EOF
project_name = "novel-engine"
environment = "production"
aws_region = "us-west-2"
domain_name = "novel-engine.com"

# EKS Configuration
eks_cluster_version = "1.28"
eks_node_groups = {
  main = {
    desired_capacity = 3
    max_capacity     = 10
    min_capacity     = 3
    instance_types   = ["t3.large"]
    capacity_type    = "ON_DEMAND"
    disk_size        = 100
    labels = {
      role = "main"
    }
    taints = []
  }
}

# Monitoring
enable_prometheus = true
enable_grafana = true
enable_alertmanager = true
grafana_admin_password = "secure-password-change-me"

# Application
app_replicas = 3
app_resources = {
  requests = {
    cpu    = "500m"
    memory = "512Mi"
  }
  limits = {
    cpu    = "1000m"
    memory = "1Gi"
  }
}
EOF

# Plan and apply
terraform plan -out=tfplan
terraform apply tfplan
```

### 3. EKS Cluster Access
```bash
# Update kubeconfig
aws eks update-kubeconfig --region us-west-2 --name novel-engine-production-cluster

# Verify cluster access
kubectl get nodes
kubectl get namespaces
```

## Application Deployment

### 1. Build and Push Container Image
```bash
# Build production image
docker build -t novel-engine:v1.0.0 -f Dockerfile --target production .

# Tag for registry
docker tag novel-engine:v1.0.0 ghcr.io/your-org/novel-engine:v1.0.0

# Push to registry
docker push ghcr.io/your-org/novel-engine:v1.0.0
```

### 2. Deploy Application
```bash
# Create namespace
kubectl create namespace novel-engine-production

# Create secrets
kubectl create secret generic novel-engine-secrets \
    --from-literal=database-url="sqlite:////app/data/novel-engine.db" \
    --from-literal=redis-url="redis://redis:6379/0" \
    --from-literal=jwt-secret="your-secure-jwt-secret" \
    --namespace novel-engine-production

# Deploy application using Kustomize
cd k8s/overlays/production

# Update image tag
kustomize edit set image novel-engine=ghcr.io/your-org/novel-engine:v1.0.0

# Apply manifests
kustomize build . | kubectl apply -f -
```

### 3. Verify Deployment
```bash
# Check deployment status
kubectl get deployments -n novel-engine-production
kubectl get pods -n novel-engine-production
kubectl get services -n novel-engine-production

# Check application health
kubectl port-forward service/novel-engine 8080:8000 -n novel-engine-production &
curl http://localhost:8080/health
```

## Monitoring Setup

### 1. Deploy Monitoring Stack
```bash
# Add Helm repositories
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Deploy Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack \
    --namespace monitoring \
    --create-namespace \
    --values config/monitoring/prometheus-values.yaml

# Verify monitoring stack
kubectl get pods -n monitoring
```

### 2. Configure Dashboards
```bash
# Import Novel Engine dashboards
kubectl apply -f config/grafana/dashboards/ -n monitoring

# Access Grafana
kubectl port-forward service/prometheus-grafana 3000:80 -n monitoring &
# Login: admin / admin123!
```

## Load Balancing and Ingress

### 1. Deploy NGINX Ingress Controller
```bash
# Install NGINX Ingress
helm install ingress-nginx ingress-nginx/ingress-nginx \
    --namespace ingress-nginx \
    --create-namespace \
    --set controller.service.type=LoadBalancer

# Verify ingress controller
kubectl get pods -n ingress-nginx
kubectl get services -n ingress-nginx
```

### 2. Configure SSL Certificates
```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer for Let's Encrypt
cat << EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@novel-engine.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

### 3. Update DNS Records
```bash
# Get LoadBalancer IP
INGRESS_IP=$(kubectl get service ingress-nginx-controller \
    -n ingress-nginx \
    -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "Update DNS records:"
echo "novel-engine.com -> $INGRESS_IP"
echo "api.novel-engine.com -> $INGRESS_IP"
```

## Security Configuration

### 1. Network Policies
```bash
# Apply network policies
kubectl apply -f k8s/overlays/production/network-policy.yaml
```

### 2. Pod Security Standards
```bash
# Enable Pod Security Standards
kubectl label namespace novel-engine-production \
    pod-security.kubernetes.io/enforce=restricted \
    pod-security.kubernetes.io/audit=restricted \
    pod-security.kubernetes.io/warn=restricted
```

### 3. RBAC Configuration
```bash
# Apply RBAC policies
kubectl apply -f k8s/base/serviceaccount.yaml -n novel-engine-production
```

## Backup and Disaster Recovery

### 1. Database Backup
```bash
# Create backup script
cat > backup-database.sh << 'EOF'
#!/bin/bash
NAMESPACE="novel-engine-production"
BACKUP_DIR="/backups/$(date +%Y-%m-%d)"

kubectl exec -n $NAMESPACE deployment/novel-engine -- \
    sqlite3 /app/data/novel-engine.db ".backup /tmp/backup.db"

kubectl cp $NAMESPACE/novel-engine-pod:/tmp/backup.db \
    $BACKUP_DIR/novel-engine-$(date +%Y%m%d-%H%M%S).db
EOF

chmod +x backup-database.sh
```

### 2. Configuration Backup
```bash
# Backup Kubernetes manifests
kubectl get all,configmap,secret,pvc -n novel-engine-production -o yaml > \
    backup-k8s-$(date +%Y%m%d).yaml
```

## Performance Optimization

### 1. Horizontal Pod Autoscaler
```bash
# Verify HPA is working
kubectl get hpa -n novel-engine-production
kubectl describe hpa novel-engine-hpa -n novel-engine-production
```

### 2. Resource Monitoring
```bash
# Monitor resource usage
kubectl top pods -n novel-engine-production
kubectl top nodes
```

### 3. Performance Tuning
```bash
# Check application metrics
kubectl port-forward service/novel-engine 8080:8000 -n novel-engine-production &
curl http://localhost:8080/metrics
```

## Troubleshooting

### Common Issues

#### 1. Pod Not Starting
```bash
# Check pod status and logs
kubectl get pods -n novel-engine-production
kubectl describe pod <pod-name> -n novel-engine-production
kubectl logs <pod-name> -n novel-engine-production
```

#### 2. Service Not Accessible
```bash
# Check service and endpoints
kubectl get services -n novel-engine-production
kubectl get endpoints -n novel-engine-production
kubectl describe ingress novel-engine -n novel-engine-production
```

#### 3. Database Issues
```bash
# Check PVC status
kubectl get pvc -n novel-engine-production
kubectl describe pvc novel-engine-data -n novel-engine-production

# Check database logs
kubectl logs deployment/novel-engine -n novel-engine-production | grep -i database
```

#### 4. Performance Issues
```bash
# Check resource usage
kubectl top pods -n novel-engine-production
kubectl describe hpa novel-engine-hpa -n novel-engine-production

# Check application metrics
curl http://localhost:8080/metrics | grep -E "(response_time|request_count|error_rate)"
```

### Emergency Procedures

#### Rolling Back Deployment
```bash
# Rollback to previous version
kubectl rollout undo deployment/novel-engine -n novel-engine-production

# Check rollout status
kubectl rollout status deployment/novel-engine -n novel-engine-production
```

#### Scaling Emergency
```bash
# Emergency scale up
kubectl scale deployment novel-engine --replicas=10 -n novel-engine-production

# Scale down when resolved
kubectl scale deployment novel-engine --replicas=3 -n novel-engine-production
```

## Maintenance

### Regular Tasks

#### Weekly
- Review monitoring dashboards
- Check resource usage trends
- Verify backup integrity
- Update security patches

#### Monthly
- Review and rotate secrets
- Update dependencies
- Performance optimization review
- Disaster recovery testing

#### Quarterly
- Security audit
- Infrastructure cost optimization
- Capacity planning review
- Documentation updates

### Upgrade Process

#### 1. Prepare Upgrade
```bash
# Create backup
./backup-database.sh

# Test new version in staging
kubectl apply -k k8s/overlays/staging/
```

#### 2. Rolling Upgrade
```bash
# Update production image
kubectl set image deployment/novel-engine \
    novel-engine=ghcr.io/your-org/novel-engine:v1.1.0 \
    -n novel-engine-production

# Monitor rollout
kubectl rollout status deployment/novel-engine -n novel-engine-production
```

#### 3. Verify Upgrade
```bash
# Health check
curl https://novel-engine.com/health

# Check metrics
curl https://novel-engine.com/metrics
```

## Support and Contacts

- **Technical Lead**: [Email]
- **DevOps Team**: [Email]
- **On-Call**: [Phone/Slack]
- **Documentation**: https://docs.novel-engine.com
- **Monitoring**: https://monitoring.novel-engine.com
- **Status Page**: https://status.novel-engine.com