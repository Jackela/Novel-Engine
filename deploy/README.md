# Novel Engine Deployment Scripts

This directory contains organized deployment scripts for the Novel Engine system, migrated from the legacy locations as part of Wave 4 infrastructure refactoring.

## Directory Structure

```
deploy/
├── README.md                    # This documentation
├── staging/
│   ├── __init__.py
│   └── deploy.py               # Staging deployment script (530 lines)
├── production/
│   ├── __init__.py
│   └── deploy.sh               # Production deployment script (578 lines)
└── security/
    ├── __init__.py
    └── deploy.py               # Security-hardened deployment (383 lines)
```

## Migration Summary

The following deployment scripts have been migrated to improve organization and maintainability:

### Migrated Scripts

| Original Location | New Location | Description |
|------------------|--------------|-------------|
| `deployment/deploy_staging.py` | `deploy/staging/deploy.py` | Staging deployment automation with health checks |
| `scripts/production_deployment.sh` | `deploy/production/deploy.sh` | Production Kubernetes deployment |
| `scripts/deploy_secure.py` | `deploy/security/deploy.py` | Security-hardened deployment with SSL/TLS |

### Path Updates

All internal paths within deployment scripts have been updated to reflect the new `configs/` directory structure:
- Configuration file references updated to use `configs/environments/`, `configs/security/`, etc.
- Project root path calculations adjusted for new script locations
- Documentation references updated throughout the codebase

## Deployment Script Usage

### Staging Deployment

Comprehensive staging deployment with validation, backup, and rollback capabilities:

```bash
# Standard staging deployment
python deploy/staging/deploy.py

# Validation only (no deployment)
python deploy/staging/deploy.py --validate-only

# Rollback to previous deployment
python deploy/staging/deploy.py --rollback
```

**Features:**
- Pre-deployment validation
- Configuration backup and restore
- Service health checks
- Automatic rollback scripts
- Environment-specific configuration

### Production Deployment

Enterprise-grade Kubernetes deployment with comprehensive infrastructure setup:

```bash
# Standard production deployment
bash deploy/production/deploy.sh --environment production --cluster prod-cluster

# Dry run deployment (no changes)
bash deploy/production/deploy.sh --dry-run

# Skip tests and force rebuild
bash deploy/production/deploy.sh --skip-tests --force-rebuild
```

**Required Environment Variables:**
- `POSTGRES_URL` - PostgreSQL connection URL
- `REDIS_URL` - Redis connection URL  
- `GEMINI_API_KEY` - Gemini API key for AI integration
- `JWT_SECRET_KEY` - JWT secret for authentication

**Features:**
- Multi-stage Docker builds
- Kubernetes orchestration
- Infrastructure as code
- Monitoring setup with Prometheus
- Security scanning and validation
- Blue-green deployment support
- Comprehensive health checks

### Security Deployment

Security-hardened deployment with SSL/TLS, authentication, and compliance features:

```bash
# Production security deployment
python deploy/security/deploy.py --environment production

# Validate security configuration
python deploy/security/deploy.py --validate-only

# Generate SSL certificates for development
python deploy/security/deploy.py --generate-ssl
```

**Features:**
- SSL/TLS certificate management
- Authentication system setup
- Security headers configuration
- Database security hardening
- OWASP compliance validation
- Environment-specific security policies

## CI/CD Integration

### GitHub Actions Workflows

The following workflows have been updated to use the new deployment script locations:

- `.github/workflows/deploy-staging.yml` - Updated to use `deploy/staging/deploy.py`
- `.github/workflows/deploy-production.yml` - Uses new production deployment patterns
- Security pipelines reference `deploy/security/deploy.py` for secure deployments

### Deployment Strategy

1. **Staging**: Automated deployment on `develop` branch pushes
2. **Production**: Manual or release-triggered deployment with approval gates
3. **Security**: On-demand secure deployment for compliance requirements

## Configuration Integration

All deployment scripts are integrated with the new unified configuration system:

- **Environment Configs**: `configs/environments/` for environment-specific settings
- **Security Configs**: `configs/security/` for security policies and SSL settings
- **Infrastructure Configs**: `configs/nginx/`, `configs/prometheus/` for supporting services

## Rollback and Recovery

### Staging Rollback
```bash
python deploy/staging/deploy.py --rollback
```

### Production Rollback
```bash
# Automatic rollback on deployment failure
kubectl rollout undo deployment/novel-engine-api -n novel-engine

# Manual rollback to specific revision
kubectl rollout undo deployment/novel-engine-api --to-revision=2 -n novel-engine
```

### Security Rollback
Configuration rollback through backup restoration and service restart.

## Validation and Testing

### Pre-deployment Validation
All deployment scripts include comprehensive validation:
- System requirements check
- Configuration validation
- Dependency verification
- Environment setup validation

### Post-deployment Testing
- Health check endpoints
- API functionality verification
- Security configuration validation
- Performance baseline testing

## Migration Verification

To verify the migration was successful:

1. **Script Execution**: All deployment scripts execute without import errors
2. **Path Resolution**: Configuration files load correctly from new paths
3. **CI/CD Integration**: GitHub Actions workflows reference correct paths
4. **Documentation**: All references updated in documentation and README files

## Troubleshooting

### Common Issues

1. **Module Not Found Errors**: Ensure all dependencies are installed
2. **Configuration Not Found**: Verify config files exist in `configs/` directory
3. **Permission Errors**: Ensure deployment scripts are executable (`chmod +x`)
4. **Environment Variables**: Check all required environment variables are set

### Debug Mode

Enable verbose logging for debugging:
```bash
# Staging deployment with debug output
PYTHONPATH=. python -v deploy/staging/deploy.py --validate-only

# Production deployment dry-run with debug
DEBUG=1 bash deploy/production/deploy.sh --dry-run
```

## Security Considerations

- All deployment scripts follow security best practices
- Sensitive information passed via environment variables
- SSL/TLS configuration for production deployments
- Database security hardening included
- Audit logging for all deployment activities

## Future Enhancements

Planned improvements to the deployment system:
1. Automated blue-green deployment strategies
2. Canary deployment support
3. Integration with monitoring and alerting systems
4. Automated security scanning in deployment pipeline
5. Multi-cloud deployment support