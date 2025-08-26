# Novel Engine Configuration System

This document describes the new organized configuration system for Novel Engine, implemented as part of Wave 3 of the infrastructure refactoring.

## Directory Structure

```
configs/
├── __init__.py
├── config_environment_loader.py    # Environment-aware configuration loader
├── README.md                       # This documentation
├── environments/                   # Environment-specific configurations
│   ├── __init__.py
│   ├── development.yaml           # Development environment config (migrated from config.yaml)
│   ├── environments.yaml          # Multi-environment definitions
│   └── settings.yaml             # Application settings (migrated from settings.yaml)
├── security/                      # Security configurations
│   ├── __init__.py
│   └── security.yaml             # Security policies and settings
├── nginx/                         # Web server configurations
│   ├── __init__.py
│   └── nginx.conf                # Nginx reverse proxy configuration
└── prometheus/                    # Monitoring configurations
    ├── __init__.py
    ├── prometheus.yml            # Prometheus monitoring setup
    └── rules/                    # Prometheus alerting rules
        ├── __init__.py
        └── novel-engine.yml      # Application-specific alerts
```

## Configuration Files

### Environment Configurations (`configs/environments/`)

#### development.yaml
Main development configuration, migrated from the root `config.yaml`. Contains:
- Simulation parameters (turns, max_agents, timeouts)
- File paths for character sheets and logs
- DirectorAgent and ChroniclerAgent settings
- LLM integration parameters
- Testing and performance configurations
- Feature flags and validation rules
- Security and production settings

#### settings.yaml
Staging/application settings, migrated from root `settings.yaml`. Contains:
- System configuration (name, version, environment)
- Legal and compliance settings
- IP filtering configuration
- API server settings
- Database and storage configuration
- AI/LLM provider settings
- Performance and monitoring settings
- Feature flags and integrations

#### environments.yaml
Multi-environment configuration matrix, migrated from `config/environments.yaml`. Defines:
- Base configuration shared across environments
- Development-specific overrides
- Testing environment settings
- Staging configuration
- Production environment setup
- Kubernetes deployment configuration

### Security Configuration (`configs/security/`)

#### security.yaml
Comprehensive security configuration, migrated from `config/security.yaml`. Includes:
- Authentication and authorization settings
- Rate limiting and DDoS protection
- Input validation and XSS/SQL injection protection
- Security headers and SSL/TLS configuration
- Database security and audit logging
- IP whitelisting and CORS policies
- Compliance settings (GDPR, OWASP)
- Environment-specific security overrides

### Infrastructure Configurations

#### nginx/nginx.conf
Nginx reverse proxy configuration for production deployment. Features:
- SSL/TLS termination
- Rate limiting and security headers
- Upstream configuration for Novel Engine API
- Static file serving
- Health check endpoints
- WebSocket support for real-time features

#### prometheus/prometheus.yml
Prometheus monitoring configuration. Monitors:
- Novel Engine application metrics
- System metrics (Node Exporter)
- Container metrics (cAdvisor)
- Redis and database metrics
- Nginx performance metrics
- Grafana and Alertmanager integration

#### prometheus/rules/novel-engine.yml
Application-specific Prometheus alerting rules for:
- High error rates
- Performance degradation
- Resource usage thresholds
- Service availability

## Environment-Aware Loading

The new `config_environment_loader.py` provides intelligent configuration loading:

### Automatic Environment Detection
1. Environment variable checks (`NOVEL_ENGINE_ENV`, `ENVIRONMENT`, `ENV`)
2. Kubernetes environment detection
3. Development environment markers (`.git`, `venv`)
4. Fallback to development environment

### Configuration Inheritance
1. Load base configuration from `environments.yaml`
2. Apply environment-specific overrides
3. Merge additional configuration files
4. Apply environment variable overrides

### Usage Examples

```python
# Basic usage
from configs.config_environment_loader import load_config
config = load_config()

# Specific environment
config = load_config(environment='production')

# Get specific values
from configs.config_environment_loader import get_config_value
host = get_config_value('api.host', default='127.0.0.1')
port = get_config_value('api.port', default=8000)
```

## Migration Impact

### Updated Files
The following files have been updated to reference the new configuration paths:

**Core Configuration:**
- `src/core/config/config_loader.py` - Updated default path to `configs/environments/development.yaml`
- `src/core/config_manager.py` - Updated all configuration paths
- `src/infrastructure/state_store.py` - Updated configuration search paths

**Application Files:**
- `api_server.py` - Updated project root detection markers
- `character_factory.py` - Updated project root detection
- `optimized_character_factory.py` - Updated project root detection

**Deployment Files:**
- `deploy/staging/deploy.py` - Updated configuration backup paths
- `production_integration_test_suite.py` - Updated required files list

### Environment Variables
The new system supports these environment variable overrides:
- `NOVEL_ENGINE_ENV` - Target environment
- `NOVEL_ENGINE_HOST` - API host override
- `NOVEL_ENGINE_PORT` - API port override  
- `DATABASE_URL` - Database connection override
- `REDIS_URL` - Redis connection override
- `LOG_LEVEL` - Logging level override
- `DEBUG_MODE` - Debug mode toggle
- `MAX_AGENTS` - Maximum agents override
- `API_TIMEOUT` - API timeout override

## Configuration Validation

The system includes comprehensive validation:
- YAML syntax validation
- Required section checks
- Type validation for critical values
- Environment-specific validation rules

## Backward Compatibility

While the old configuration files (`config.yaml`, `settings.yaml`) are no longer used by the application, they remain in the repository for reference and are backed up in `backup_configs_wave3/`.

## Best Practices

1. **Environment-Specific Configuration**: Use the `environments.yaml` structure for environment-specific settings
2. **Security Settings**: Keep security-sensitive configuration in `configs/security/` 
3. **Infrastructure Settings**: Store deployment configuration in appropriate subdirectories
4. **Environment Variables**: Use environment variables for deployment-specific overrides
5. **Validation**: Always validate configuration after changes

## Troubleshooting

### Configuration Not Loading
1. Check file paths and permissions
2. Validate YAML syntax
3. Verify environment detection
4. Check for missing required sections

### Environment Detection Issues
1. Set `NOVEL_ENGINE_ENV` explicitly
2. Check for conflicting environment variables
3. Verify deployment environment markers

### Migration Issues
1. Verify all configuration files migrated correctly
2. Check that application code references new paths
3. Validate that all configuration keys are preserved

## Future Enhancements

Planned improvements for the configuration system:
1. Configuration schema validation with JSON Schema
2. Hot-reload capability for development
3. Configuration encryption for sensitive values
4. Configuration versioning and rollback
5. Web-based configuration management interface