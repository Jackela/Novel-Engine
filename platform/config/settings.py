"""
Configuration Management System
=============================

Comprehensive configuration management with environment-based loading,
validation, secret management, and dynamic updates for Novel Engine platform.
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Type, TypeVar
from dataclasses import dataclass, field
from enum import Enum

import yaml
try:
    from pydantic_settings import BaseSettings
    from typing import Callable, Tuple, Any
    SettingsSourceCallable = Callable[[], Dict[str, Any]]
except ImportError:
    from pydantic import BaseSettings
    from pydantic.env_settings import SettingsSourceCallable
from pydantic import validator, Field

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseSettings)


class Environment(Enum):
    """Supported deployment environments."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(Enum):
    """Supported log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ConfigSource:
    """Configuration source metadata."""
    name: str
    path: Optional[str] = None
    priority: int = 0
    loaded: bool = False
    error: Optional[str] = None


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    url: str = Field(
        default="postgresql://novel_engine:novel_engine_dev_password@localhost:5432/novel_engine",
        description="Database connection URL"
    )
    
    # Connection pool settings
    pool_size: int = Field(default=20, description="Connection pool size")
    max_overflow: int = Field(default=30, description="Maximum pool overflow")
    pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    pool_recycle: int = Field(default=3600, description="Pool recycle time in seconds")
    
    # Query settings
    echo: bool = Field(default=False, description="Echo SQL statements")
    echo_pool: bool = Field(default=False, description="Echo pool events")
    
    # Migration settings
    migration_timeout: int = Field(default=300, description="Migration timeout in seconds")
    
    class Config:
        env_prefix = "DB_"
        case_sensitive = False


class MessagingSettings(BaseSettings):
    """Messaging system configuration settings."""
    
    # Kafka settings
    bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Kafka bootstrap servers"
    )
    
    # Security settings
    use_ssl: bool = Field(default=False, description="Use SSL for Kafka connection")
    ssl_cafile: Optional[str] = Field(default=None, description="SSL CA file path")
    ssl_certfile: Optional[str] = Field(default=None, description="SSL certificate file path")
    ssl_keyfile: Optional[str] = Field(default=None, description="SSL key file path")
    ssl_password: Optional[str] = Field(default=None, description="SSL key password")
    
    use_sasl: bool = Field(default=False, description="Use SASL for Kafka authentication")
    sasl_mechanism: str = Field(default="PLAIN", description="SASL mechanism")
    sasl_username: Optional[str] = Field(default=None, description="SASL username")
    sasl_password: Optional[str] = Field(default=None, description="SASL password")
    
    # Producer settings
    producer_acks: str = Field(default="all", description="Producer acknowledgments")
    producer_retries: int = Field(default=5, description="Producer retry attempts")
    producer_timeout: int = Field(default=30000, description="Producer timeout in ms")
    
    # Consumer settings
    consumer_group_prefix: str = Field(default="novel-engine", description="Consumer group prefix")
    consumer_timeout: int = Field(default=30000, description="Consumer timeout in ms")
    consumer_max_poll_records: int = Field(default=500, description="Max records per poll")
    
    class Config:
        env_prefix = "MESSAGING_"
        case_sensitive = False


class CacheSettings(BaseSettings):
    """Cache configuration settings."""
    
    # Redis settings
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    
    # Connection settings
    max_connections: int = Field(default=20, description="Maximum Redis connections")
    socket_timeout: int = Field(default=5, description="Socket timeout in seconds")
    socket_connect_timeout: int = Field(default=5, description="Socket connect timeout in seconds")
    
    # Cache settings
    default_ttl: int = Field(default=3600, description="Default cache TTL in seconds")
    key_prefix: str = Field(default="novel-engine:", description="Cache key prefix")
    
    # Serialization
    serializer: str = Field(default="json", description="Cache serialization format")
    compression: bool = Field(default=False, description="Enable cache compression")
    
    class Config:
        env_prefix = "CACHE_"
        case_sensitive = False


class SecuritySettings(BaseSettings):
    """Security configuration settings."""
    
    # JWT settings
    jwt_secret_key: str = Field(
        default="development-secret-key-change-in-production",
        description="JWT secret key"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    jwt_access_token_expires: int = Field(default=3600, description="Access token expiration in seconds")
    jwt_refresh_token_expires: int = Field(default=86400, description="Refresh token expiration in seconds")
    
    # Password settings
    password_min_length: int = Field(default=8, description="Minimum password length")
    password_require_uppercase: bool = Field(default=True, description="Require uppercase in passwords")
    password_require_lowercase: bool = Field(default=True, description="Require lowercase in passwords")
    password_require_digits: bool = Field(default=True, description="Require digits in passwords")
    password_require_symbols: bool = Field(default=True, description="Require symbols in passwords")
    
    # Session settings
    session_timeout: int = Field(default=3600, description="Session timeout in seconds")
    max_login_attempts: int = Field(default=5, description="Maximum login attempts")
    lockout_duration: int = Field(default=900, description="Account lockout duration in seconds")
    
    # CORS settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )
    cors_credentials: bool = Field(default=True, description="Allow CORS credentials")
    cors_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed CORS methods"
    )
    
    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, description="Rate limit requests per window")
    rate_limit_window: int = Field(default=60, description="Rate limit window in seconds")
    
    class Config:
        env_prefix = "SECURITY_"
        case_sensitive = False


class MonitoringSettings(BaseSettings):
    """Monitoring and observability settings."""
    
    # Logging settings
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Log level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    log_file: Optional[str] = Field(default=None, description="Log file path")
    log_max_bytes: int = Field(default=10485760, description="Log file max size in bytes")  # 10MB
    log_backup_count: int = Field(default=5, description="Log file backup count")
    
    # Metrics settings
    metrics_enabled: bool = Field(default=True, description="Enable metrics collection")
    metrics_port: int = Field(default=9090, description="Metrics server port")
    metrics_path: str = Field(default="/metrics", description="Metrics endpoint path")
    
    # Health check settings
    health_check_enabled: bool = Field(default=True, description="Enable health checks")
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")
    
    # Distributed tracing settings
    tracing_enabled: bool = Field(default=True, description="Enable distributed tracing")
    tracing_service_name: str = Field(default="novel-engine", description="Tracing service name")
    jaeger_endpoint: str = Field(
        default="http://localhost:14268/api/traces",
        description="Jaeger collector endpoint"
    )
    
    class Config:
        env_prefix = "MONITORING_"
        case_sensitive = False


class StorageSettings(BaseSettings):
    """Object storage configuration settings."""
    
    # MinIO/S3 settings
    endpoint_url: str = Field(default="http://localhost:9000", description="Storage endpoint URL")
    access_key: str = Field(default="novel_engine", description="Storage access key")
    secret_key: str = Field(default="novel_engine_dev_password", description="Storage secret key")
    bucket_name: str = Field(default="novel-engine", description="Default bucket name")
    region: str = Field(default="us-east-1", description="Storage region")
    
    # Upload settings
    max_file_size: int = Field(default=104857600, description="Maximum file size in bytes")  # 100MB
    allowed_extensions: List[str] = Field(
        default=[".jpg", ".jpeg", ".png", ".gif", ".pdf", ".txt", ".md"],
        description="Allowed file extensions"
    )
    
    # CDN settings
    cdn_enabled: bool = Field(default=False, description="Enable CDN")
    cdn_url: Optional[str] = Field(default=None, description="CDN base URL")
    
    class Config:
        env_prefix = "STORAGE_"
        case_sensitive = False


class AppSettings(BaseSettings):
    """Main application configuration."""
    
    # Application metadata
    app_name: str = Field(default="Novel Engine", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    app_description: str = Field(
        default="AI-driven interactive storytelling platform",
        description="Application description"
    )
    
    # Environment settings
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="Deployment environment")
    debug: bool = Field(default=True, description="Enable debug mode")
    
    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=1, description="Number of worker processes")
    
    # Feature flags
    enable_analytics: bool = Field(default=True, description="Enable analytics")
    enable_caching: bool = Field(default=True, description="Enable caching")
    enable_rate_limiting: bool = Field(default=True, description="Enable rate limiting")
    
    # External services
    ai_service_url: str = Field(default="http://localhost:8080", description="AI service URL")
    ai_service_timeout: int = Field(default=30, description="AI service timeout in seconds")
    
    @validator('environment', pre=True)
    def validate_environment(cls, v):
        """Validate environment value."""
        if isinstance(v, str):
            return Environment(v.lower())
        return v
    
    @validator('debug')
    def validate_debug(cls, v, values):
        """Auto-disable debug in production."""
        if values.get('environment') == Environment.PRODUCTION:
            return False
        return v
    
    class Config:
        env_prefix = "APP_"
        case_sensitive = False
        # Custom settings sources
        @classmethod
        def customise_sources(
            cls,
            init_settings: SettingsSourceCallable,
            env_settings: SettingsSourceCallable,
            file_secret_settings: SettingsSourceCallable,
        ) -> tuple[SettingsSourceCallable, ...]:
            return (
                init_settings,
                env_settings,
                yaml_config_settings_source,
                file_secret_settings,
            )


class PlatformConfig:
    """
    Main configuration manager for the Novel Engine platform.
    
    Features:
    - Environment-based configuration loading
    - Multiple configuration sources (env vars, files, secrets)
    - Configuration validation and type safety
    - Dynamic configuration updates
    - Secret management integration
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize platform configuration."""
        self.config_path = config_path or self._detect_config_path()
        self.sources: List[ConfigSource] = []
        
        # Load all configuration sections
        self.app = AppSettings()
        self.database = DatabaseSettings()
        self.messaging = MessagingSettings()
        self.cache = CacheSettings()
        self.security = SecuritySettings()
        self.monitoring = MonitoringSettings()
        self.storage = StorageSettings()
        
        # Track configuration loading
        self._track_config_sources()
        
        logger.info(f"Configuration loaded for environment: {self.app.environment.value}")
    
    def _detect_config_path(self) -> str:
        """Detect configuration file path."""
        # Check common locations
        possible_paths = [
            "config.yaml",
            "config/config.yaml",
            "platform/config/config.yaml",
            os.path.expanduser("~/.novel-engine/config.yaml"),
            "/etc/novel-engine/config.yaml"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return "config.yaml"  # Default
    
    def _track_config_sources(self) -> None:
        """Track configuration sources for debugging."""
        # Environment variables
        self.sources.append(ConfigSource(
            name="Environment Variables",
            loaded=True
        ))
        
        # Configuration file
        config_loaded = os.path.exists(self.config_path)
        self.sources.append(ConfigSource(
            name="Configuration File",
            path=self.config_path,
            loaded=config_loaded,
            error=None if config_loaded else "File not found"
        ))
        
        # Secrets (if available)
        secrets_path = os.environ.get("SECRETS_PATH")
        if secrets_path:
            secrets_loaded = os.path.exists(secrets_path)
            self.sources.append(ConfigSource(
                name="Secrets File",
                path=secrets_path,
                loaded=secrets_loaded,
                error=None if secrets_loaded else "Secrets file not found"
            ))
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration as dictionary."""
        return {
            "url": self.database.url,
            "pool_size": self.database.pool_size,
            "max_overflow": self.database.max_overflow,
            "pool_timeout": self.database.pool_timeout,
            "pool_recycle": self.database.pool_recycle,
            "echo": self.database.echo,
            "echo_pool": self.database.echo_pool
        }
    
    def get_messaging_config(self) -> Dict[str, Any]:
        """Get messaging configuration as dictionary."""
        config = {
            "bootstrap_servers": self.messaging.bootstrap_servers,
            "use_ssl": self.messaging.use_ssl,
            "use_sasl": self.messaging.use_sasl
        }
        
        # Add SSL config if enabled
        if self.messaging.use_ssl:
            config.update({
                "ssl_cafile": self.messaging.ssl_cafile,
                "ssl_certfile": self.messaging.ssl_certfile,
                "ssl_keyfile": self.messaging.ssl_keyfile,
                "ssl_password": self.messaging.ssl_password
            })
        
        # Add SASL config if enabled
        if self.messaging.use_sasl:
            config.update({
                "sasl_mechanism": self.messaging.sasl_mechanism,
                "sasl_username": self.messaging.sasl_username,
                "sasl_password": self.messaging.sasl_password
            })
        
        return config
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app.environment == Environment.PRODUCTION
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app.environment == Environment.DEVELOPMENT
    
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.app.environment == Environment.TESTING
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return any errors."""
        errors = []
        
        # Production-specific validations
        if self.is_production():
            if self.security.jwt_secret_key == "development-secret-key-change-in-production":
                errors.append("JWT secret key must be changed for production")
            
            if self.app.debug:
                errors.append("Debug mode should be disabled in production")
            
            if not self.security.rate_limit_enabled:
                errors.append("Rate limiting should be enabled in production")
        
        # Database URL validation
        if not self.database.url or "localhost" in self.database.url and self.is_production():
            errors.append("Database URL should not use localhost in production")
        
        return errors
    
    def get_status(self) -> Dict[str, Any]:
        """Get configuration status information."""
        validation_errors = self.validate_config()
        
        return {
            "environment": self.app.environment.value,
            "config_sources": [
                {
                    "name": source.name,
                    "path": source.path,
                    "loaded": source.loaded,
                    "error": source.error
                }
                for source in self.sources
            ],
            "validation_errors": validation_errors,
            "is_valid": len(validation_errors) == 0
        }


def yaml_config_settings_source(settings: BaseSettings) -> Dict[str, Any]:
    """Custom settings source for YAML configuration files."""
    config_data = {}
    
    # Try to load from config file
    config_path = os.environ.get("CONFIG_PATH", "config.yaml")
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
            logger.debug(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
    
    return config_data


# Global configuration instance
_platform_config: Optional[PlatformConfig] = None


def get_platform_config(config_path: Optional[str] = None) -> PlatformConfig:
    """Get the global platform configuration instance."""
    global _platform_config
    if _platform_config is None:
        _platform_config = PlatformConfig(config_path)
    return _platform_config


def get_database_settings() -> Dict[str, Any]:
    """Get database configuration settings."""
    config = get_platform_config()
    return config.get_database_config()


def get_messaging_settings() -> Dict[str, Any]:
    """Get messaging configuration settings."""
    config = get_platform_config()
    return config.get_messaging_config()


def get_cache_settings() -> Dict[str, Any]:
    """Get cache configuration settings."""
    config = get_platform_config()
    return {
        "redis_url": config.cache.redis_url,
        "max_connections": config.cache.max_connections,
        "socket_timeout": config.cache.socket_timeout,
        "default_ttl": config.cache.default_ttl,
        "key_prefix": config.cache.key_prefix
    }


def get_security_settings() -> Dict[str, Any]:
    """Get security configuration settings."""
    config = get_platform_config()
    return {
        "jwt_secret_key": config.security.jwt_secret_key,
        "jwt_algorithm": config.security.jwt_algorithm,
        "jwt_access_token_expires": config.security.jwt_access_token_expires,
        "jwt_refresh_token_expires": config.security.jwt_refresh_token_expires,
        "cors_origins": config.security.cors_origins,
        "cors_credentials": config.security.cors_credentials,
        "rate_limit_enabled": config.security.rate_limit_enabled,
        "rate_limit_requests": config.security.rate_limit_requests,
        "rate_limit_window": config.security.rate_limit_window
    }