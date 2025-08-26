"""
Deployment Management Module

This module provides deployment automation, orchestration, and environment management
for the Novel Engine application across different deployment targets.

Directory Structure:
- staging/: Staging environment deployment configurations and scripts
- production/: Production environment deployment configurations and scripts
- security/: Security-focused deployment configurations and hardening scripts

Features:
- Environment-specific deployment strategies
- Container orchestration (Docker/Kubernetes)
- Infrastructure as Code (Terraform/Ansible)
- Blue-green and canary deployment support
- Rollback and disaster recovery procedures
- Security hardening and compliance

Usage:
    from deploy import staging, production, security
    from deploy.staging import deploy_to_staging
    from deploy.production import deploy_to_production
"""

__version__ = "1.0.0"
__author__ = "Novel Engine DevOps Team"

# Deployment module exports
__all__ = [
    "staging",
    "production", 
    "security",
    "deploy_strategies",
    "rollback_manager"
]

# Import submodules for easier access
try:
    from . import staging
    from . import production
    from . import security
except ImportError:
    # Allow graceful degradation if submodules aren't ready yet
    pass

# Deployment configuration constants
SUPPORTED_ENVIRONMENTS = ['staging', 'production']
DEPLOYMENT_STRATEGIES = ['rolling', 'blue_green', 'canary']
ROLLBACK_RETENTION_DAYS = 30