"""Tests for the settings module."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from src.shared.infrastructure.config.settings import (
    APISettings,
    DatabaseSettings,
    Environment,
    LLMSettings,
    LoggingSettings,
    LogLevel,
    MonitoringSettings,
    NovelEngineSettings,
    RedisSettings,
    SecuritySettings,
    get_settings,
    reload_settings,
    reset_settings,
)


class TestEnvironment:
    """Test Environment enum."""

    def test_environment_values(self):
        """Test environment enum has correct values."""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.TESTING.value == "testing"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"

    def test_environment_comparison(self):
        """Test environment comparison."""
        assert Environment.DEVELOPMENT == Environment.DEVELOPMENT
        assert Environment.DEVELOPMENT != Environment.PRODUCTION


class TestLogLevel:
    """Test LogLevel enum."""

    def test_log_level_values(self):
        """Test log level enum has correct values."""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"
        assert LogLevel.CRITICAL.value == "CRITICAL"


class TestDatabaseSettings:
    """Test DatabaseSettings class."""

    def test_default_values(self):
        """Test default database settings."""
        settings = DatabaseSettings()
        assert settings.url == "sqlite:///./novel_engine.db"
        assert settings.pool_size == 5
        assert settings.max_overflow == 10
        assert settings.pool_timeout == 30
        assert settings.echo is False

    def test_custom_values(self):
        """Test custom database settings."""
        settings = DatabaseSettings(
            url="postgresql+asyncpg://user:pass@localhost:5432/db",
            pool_size=10,
            max_overflow=20,
            pool_timeout=60,
            echo=True,
        )
        assert settings.url == "postgresql+asyncpg://user:pass@localhost:5432/db"
        assert settings.pool_size == 10
        assert settings.echo is True

    def test_validation_pool_size_min(self):
        """Test pool size minimum validation."""
        with pytest.raises(ValidationError):
            DatabaseSettings(pool_size=0)

    def test_validation_pool_size_max(self):
        """Test pool size maximum validation."""
        with pytest.raises(ValidationError):
            DatabaseSettings(pool_size=101)

    def test_validation_empty_url(self):
        """Test empty URL validation."""
        with pytest.raises(ValidationError):
            DatabaseSettings(url="")

    def test_validation_invalid_url(self):
        """Test invalid URL prefix validation."""
        with pytest.raises(ValidationError) as exc_info:
            DatabaseSettings(url="mysql://localhost/db")
        assert "Database URL must start with" in str(exc_info.value)

    def test_validation_valid_urls(self):
        """Test valid URL prefixes."""
        # SQLite
        db = DatabaseSettings(url="sqlite:///./test.db")
        assert db.url == "sqlite:///./test.db"

        # PostgreSQL
        db = DatabaseSettings(url="postgresql://user:pass@localhost/db")
        assert db.url == "postgresql://user:pass@localhost/db"

        # PostgreSQL with asyncpg
        db = DatabaseSettings(url="postgresql+asyncpg://user:pass@localhost/db")
        assert db.url == "postgresql+asyncpg://user:pass@localhost/db"


class TestRedisSettings:
    """Test RedisSettings class."""

    def test_default_values(self):
        """Test default Redis settings."""
        settings = RedisSettings()
        assert settings.host == "localhost"
        assert settings.port == 6379
        assert settings.db == 0
        assert settings.password is None
        assert settings.ssl is False

    def test_custom_values(self):
        """Test custom Redis settings."""
        settings = RedisSettings(
            host="redis.example.com",
            port=6380,
            db=5,
            password="secret",
            ssl=True,
        )
        assert settings.host == "redis.example.com"
        assert settings.port == 6380
        assert settings.db == 5
        assert settings.password == "secret"
        assert settings.ssl is True

    def test_port_validation_min(self):
        """Test port minimum validation."""
        with pytest.raises(ValidationError):
            RedisSettings(port=0)

    def test_port_validation_max(self):
        """Test port maximum validation."""
        with pytest.raises(ValidationError):
            RedisSettings(port=70000)

    def test_db_validation_max(self):
        """Test database number maximum validation."""
        with pytest.raises(ValidationError):
            RedisSettings(db=16)


class TestAPISettings:
    """Test APISettings class."""

    def test_default_values(self):
        """Test default API settings."""
        settings = APISettings()
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.workers == 1
        assert settings.reload is False
        assert settings.title == "Novel Engine API"

    def test_custom_values(self):
        """Test custom API settings."""
        settings = APISettings(
            host="127.0.0.1",
            port=9000,
            workers=4,
            reload=True,
            title="Custom API",
        )
        assert settings.host == "127.0.0.1"
        assert settings.port == 9000
        assert settings.workers == 4
        assert settings.reload is True
        assert settings.title == "Custom API"

    def test_port_validation_reserved(self):
        """Test reserved port validation."""
        with pytest.raises(ValidationError):
            APISettings(port=80)  # Should fail because < 1024

    def test_workers_validation_min(self):
        """Test workers minimum validation."""
        with pytest.raises(ValidationError):
            APISettings(workers=0)


class TestSecuritySettings:
    """Test SecuritySettings class."""

    def test_default_values(self):
        """Test default security settings."""
        settings = SecuritySettings()
        assert settings.secret_key == "change-me-in-production-32-char-long"
        assert settings.algorithm == "HS256"
        assert settings.access_token_expire_minutes == 30
        assert settings.refresh_token_expire_days == 7
        assert settings.cors_allow_credentials is True

    def test_custom_values(self):
        """Test custom security settings."""
        settings = SecuritySettings(
            secret_key="a-very-long-secret-key-for-testing-only",
            algorithm="HS512",
            access_token_expire_minutes=60,
        )
        assert settings.secret_key == "a-very-long-secret-key-for-testing-only"
        assert settings.algorithm == "HS512"
        assert settings.access_token_expire_minutes == 60

    def test_secret_key_validation_min_length(self):
        """Test secret key minimum length validation."""
        with pytest.raises(ValidationError):
            SecuritySettings(secret_key="short")

    def test_cors_origins_parsing_string(self):
        """Test CORS origins parsing from string."""
        settings = SecuritySettings(
            cors_origins="http://localhost:3000,http://localhost:8080"
        )
        assert settings.cors_origins == [
            "http://localhost:3000",
            "http://localhost:8080",
        ]

    def test_cors_origins_parsing_list(self):
        """Test CORS origins from list."""
        origins = ["http://localhost:3000", "https://example.com"]
        settings = SecuritySettings(cors_origins=origins)
        assert settings.cors_origins == origins

    def test_cors_methods_parsing(self):
        """Test CORS methods parsing."""
        settings = SecuritySettings(cors_allow_methods="GET,POST,DELETE")
        assert settings.cors_allow_methods == ["GET", "POST", "DELETE"]

    def test_cors_headers_parsing(self):
        """Test CORS headers parsing."""
        settings = SecuritySettings(cors_allow_headers="Authorization,Content-Type")
        assert settings.cors_allow_headers == ["Authorization", "Content-Type"]


class TestLLMSettings:
    """Test LLMSettings class."""

    def test_default_values(self):
        """Test default LLM settings."""
        settings = LLMSettings()
        assert settings.provider == "gemini"
        assert settings.model == "gemini-pro"
        assert settings.timeout == 30
        assert settings.max_tokens == 4096
        assert settings.temperature == 0.7

    def test_custom_values(self):
        """Test custom LLM settings."""
        settings = LLMSettings(
            provider="openai",
            model="gpt-4",
            timeout=60,
            max_tokens=2048,
            temperature=0.5,
        )
        assert settings.provider == "openai"
        assert settings.model == "gpt-4"
        assert settings.timeout == 60
        assert settings.temperature == 0.5

    def test_provider_validation(self):
        """Test provider validation."""
        with pytest.raises(ValidationError):
            LLMSettings(provider="invalid-provider")

    def test_temperature_validation_min(self):
        """Test temperature minimum validation."""
        with pytest.raises(ValidationError):
            LLMSettings(temperature=-0.1)

    def test_temperature_validation_max(self):
        """Test temperature maximum validation."""
        with pytest.raises(ValidationError):
            LLMSettings(temperature=2.1)

    def test_top_p_validation(self):
        """Test top_p validation."""
        with pytest.raises(ValidationError):
            LLMSettings(top_p=1.1)


class TestLoggingSettings:
    """Test LoggingSettings class."""

    def test_default_values(self):
        """Test default logging settings."""
        settings = LoggingSettings()
        assert settings.level == LogLevel.INFO
        assert settings.json_format is False
        assert settings.console_output is True
        assert settings.structured is True

    def test_custom_values(self):
        """Test custom logging settings."""
        settings = LoggingSettings(
            level=LogLevel.DEBUG,
            json_format=True,
            file_path=Path("./logs/app.log"),
        )
        assert settings.level == LogLevel.DEBUG
        assert settings.json_format is True
        assert settings.file_path == Path("./logs/app.log")


class TestMonitoringSettings:
    """Test MonitoringSettings class."""

    def test_default_values(self):
        """Test default monitoring settings."""
        settings = MonitoringSettings()
        assert settings.enabled is True
        assert settings.metrics_enabled is True
        assert settings.metrics_port == 9090
        assert settings.tracing_enabled is False

    def test_custom_values(self):
        """Test custom monitoring settings."""
        settings = MonitoringSettings(
            enabled=False,
            metrics_port=9091,
            tracing_enabled=True,
            jaeger_endpoint="http://localhost:14268",
        )
        assert settings.enabled is False
        assert settings.metrics_port == 9091
        assert settings.tracing_enabled is True
        assert settings.jaeger_endpoint == "http://localhost:14268"


class TestNovelEngineSettings:
    """Test NovelEngineSettings class."""

    def test_default_values(self):
        """Test default novel engine settings."""
        settings = NovelEngineSettings()
        assert settings.environment == Environment.DEVELOPMENT
        assert settings.debug is False
        assert settings.project_name == "Novel Engine API"
        assert settings.is_development is True
        assert settings.is_testing is False
        assert settings.is_production is False

    def test_environment_properties(self):
        """Test environment property methods."""
        dev = NovelEngineSettings(environment=Environment.DEVELOPMENT)
        assert dev.is_development is True
        assert dev.is_testing is False
        assert dev.is_staging is False
        assert dev.is_production is False

        test = NovelEngineSettings(environment=Environment.TESTING)
        assert test.is_development is False
        assert test.is_testing is True

        staging = NovelEngineSettings(environment=Environment.STAGING)
        assert test.is_development is False
        assert staging.is_staging is True

        prod = NovelEngineSettings(environment=Environment.PRODUCTION)
        assert prod.is_development is False
        assert prod.is_production is True

    def test_nested_settings(self):
        """Test nested settings objects."""
        settings = NovelEngineSettings()
        assert isinstance(settings.database, DatabaseSettings)
        assert isinstance(settings.redis, RedisSettings)
        assert isinstance(settings.api, APISettings)
        assert isinstance(settings.security, SecuritySettings)
        assert isinstance(settings.llm, LLMSettings)
        assert isinstance(settings.logging, LoggingSettings)
        assert isinstance(settings.monitoring, MonitoringSettings)

    def test_model_dump_safe(self):
        """Test safe model dump masks sensitive fields."""
        settings = NovelEngineSettings(
            llm=LLMSettings(api_key="secret-api-key"),
            security=SecuritySettings(secret_key="secret-key-for-testing-only"),
        )
        data = settings.model_dump_safe()

        # Check that sensitive fields are masked
        assert data["llm"]["api_key"] == "***REDACTED***"
        assert data["security"]["secret_key"] == "***REDACTED***"

    def test_from_environment(self):
        """Test creating settings from specific environment."""
        settings = NovelEngineSettings.from_environment(Environment.TESTING)
        assert settings.environment == Environment.TESTING

    def test_from_environment_string(self):
        """Test creating settings from environment string."""
        settings = NovelEngineSettings.from_environment("production")
        assert settings.environment == Environment.PRODUCTION

    def test_from_environment_none(self):
        """Test creating settings with None environment."""
        settings = NovelEngineSettings.from_environment(None)
        # Should use default or environment variable
        assert isinstance(settings.environment, Environment)


class TestGlobalSettings:
    """Test global settings functions."""

    def setup_method(self):
        """Reset settings before each test."""
        reset_settings()

    def teardown_method(self):
        """Reset settings after each test."""
        reset_settings()

    def test_get_settings_returns_instance(self):
        """Test get_settings returns NovelEngineSettings."""
        settings = get_settings()
        assert isinstance(settings, NovelEngineSettings)

    def test_get_settings_caching(self):
        """Test get_settings caches the instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_reset_settings(self):
        """Test reset_settings clears cached instance."""
        settings1 = get_settings()
        reset_settings()
        settings2 = get_settings()
        assert settings1 is not settings2

    def test_reload_settings(self):
        """Test reload_settings returns new instance."""
        settings1 = get_settings()
        settings2 = reload_settings()
        assert settings1 is not settings2
        assert isinstance(settings2, NovelEngineSettings)

    def test_reload_settings_clears_cache(self):
        """Test reload_settings clears cache and returns fresh instance."""
        settings1 = get_settings()
        reloaded = reload_settings()
        settings2 = get_settings()
        assert reloaded is settings2
        assert settings1 is not settings2


class TestEnvironmentVariables:
    """Test settings from environment variables."""

    def test_environment_from_env_var(self, monkeypatch):
        """Test reading environment from env var."""
        monkeypatch.setenv("APP_ENVIRONMENT", "production")
        settings = NovelEngineSettings()
        assert settings.environment == Environment.PRODUCTION

    def test_database_url_from_env(self, monkeypatch):
        """Test database URL from environment variable."""
        monkeypatch.setenv("DB_URL", "postgresql://user:pass@localhost/db")
        settings = NovelEngineSettings()
        assert settings.database.url == "postgresql://user:pass@localhost/db"

    def test_api_port_from_env(self, monkeypatch):
        """Test API port from environment variable."""
        monkeypatch.setenv("API_PORT", "9000")
        settings = NovelEngineSettings()
        assert settings.api.port == 9000

    def test_llm_api_key_from_env(self, monkeypatch):
        """Test LLM API key from environment variable."""
        monkeypatch.setenv("LLM_API_KEY", "test-api-key")
        settings = NovelEngineSettings()
        assert settings.llm.api_key == "test-api-key"

    def test_log_level_from_env(self, monkeypatch):
        """Test log level from environment variable."""
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        settings = NovelEngineSettings()
        assert settings.logging.level == LogLevel.DEBUG

    def test_cors_origins_from_env(self, monkeypatch):
        """Test CORS origins from environment variable."""
        import json

        origins = ["http://localhost:3000", "https://example.com"]
        monkeypatch.setenv("SECURITY_CORS_ORIGINS", json.dumps(origins))
        settings = NovelEngineSettings()
        assert settings.security.cors_origins == origins
