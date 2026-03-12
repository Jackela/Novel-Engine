#!/usr/bin/env python3
"""
Unit tests for config_loader module.

Tests cover:
- Configuration data classes
- ConfigurationError exception
- ConfigLoader singleton behavior
- YAML file loading
- Environment variable overrides
- Configuration validation
- Convenience methods
"""

import os
import threading
from unittest.mock import mock_open, patch

import pytest

from src.core.config.config_loader import (
    AppConfig,
    CharacterConfig,
    ChroniclerConfig,
    ConfigLoader,
    ConfigurationError,
    DirectorConfig,
    FeaturesConfig,
    LLMConfig,
    PathsConfig,
    PerformanceConfig,
    SimulationConfig,
    TestingConfig,
    ValidationConfig,
    example_usage,
    get_campaign_log_filename,
    get_character_sheets_path,
    get_config,
    get_default_character_sheets,
    get_log_file_path,
    get_output_directory,
    get_simulation_turns,
)


class TestSimulationConfig:
    """Tests for SimulationConfig dataclass."""

    def test_default_values(self):
        """Test default values are correctly set."""
        config = SimulationConfig()
        assert config.turns == 3
        assert config.max_agents == 10
        assert config.api_timeout == 30
        assert config.logging_level == "INFO"

    def test_custom_values(self):
        """Test custom values can be set."""
        config = SimulationConfig(
            turns=5, max_agents=20, api_timeout=60, logging_level="DEBUG"
        )
        assert config.turns == 5
        assert config.max_agents == 20
        assert config.api_timeout == 60
        assert config.logging_level == "DEBUG"


class TestPathsConfig:
    """Tests for PathsConfig dataclass."""

    def test_default_values(self):
        """Test default values are correctly set."""
        config = PathsConfig()
        assert config.character_sheets_path == "."
        assert config.log_file_path == "campaign_log.md"
        assert config.output_directory == "demo_narratives"
        assert config.test_narratives_directory == "test_narratives"
        assert config.simulation_logs_directory == "."

    def test_custom_values(self):
        """Test custom values can be set."""
        config = PathsConfig(
            character_sheets_path="/path/to/sheets",
            log_file_path="custom_log.md",
            output_directory="custom_output",
        )
        assert config.character_sheets_path == "/path/to/sheets"
        assert config.log_file_path == "custom_log.md"
        assert config.output_directory == "custom_output"


class TestCharacterConfig:
    """Tests for CharacterConfig dataclass."""

    def test_default_values(self):
        """Test default values are correctly set."""
        config = CharacterConfig()
        assert config.default_sheets == ["character_krieg.md", "character_ork.md"]
        assert config.max_actions_per_turn == 5

    def test_custom_values(self):
        """Test custom values can be set."""
        config = CharacterConfig(
            default_sheets=["custom_char.md"], max_actions_per_turn=10
        )
        assert config.default_sheets == ["custom_char.md"]
        assert config.max_actions_per_turn == 10


class TestDirectorConfig:
    """Tests for DirectorConfig dataclass."""

    def test_default_values(self):
        """Test default values are correctly set."""
        config = DirectorConfig()
        assert config.campaign_log_filename == "campaign_log.md"
        assert config.world_state_file is None
        assert config.max_turn_history == 100
        assert config.error_threshold == 10

    def test_custom_values(self):
        """Test custom values can be set."""
        config = DirectorConfig(
            campaign_log_filename="custom_campaign.md",
            world_state_file="world.yaml",
            max_turn_history=50,
            error_threshold=5,
        )
        assert config.campaign_log_filename == "custom_campaign.md"
        assert config.world_state_file == "world.yaml"
        assert config.max_turn_history == 50
        assert config.error_threshold == 5


class TestChroniclerConfig:
    """Tests for ChroniclerConfig dataclass."""

    def test_default_values(self):
        """Test default values are correctly set."""
        config = ChroniclerConfig()
        assert config.max_events_per_batch == 50
        assert config.narrative_style == "grimdark_dramatic"
        assert config.output_directory == "demo_narratives"

    def test_custom_values(self):
        """Test custom values can be set."""
        config = ChroniclerConfig(
            max_events_per_batch=100,
            narrative_style="tactical",
            output_directory="custom_narratives",
        )
        assert config.max_events_per_batch == 100
        assert config.narrative_style == "tactical"
        assert config.output_directory == "custom_narratives"


class TestLLMConfig:
    """Tests for LLMConfig dataclass."""

    def test_default_values(self):
        """Test default values are correctly set."""
        config = LLMConfig()
        assert config.api_endpoint is None
        assert config.api_key is None
        assert config.model is None
        assert config.max_tokens == 1000
        assert config.temperature == 0.7

    def test_custom_values(self):
        """Test custom values can be set."""
        config = LLMConfig(
            api_endpoint="https://api.example.com",
            api_key="secret_key",
            model="gpt-4",
            max_tokens=2000,
            temperature=0.5,
        )
        assert config.api_endpoint == "https://api.example.com"
        assert config.api_key == "secret_key"
        assert config.model == "gpt-4"
        assert config.max_tokens == 2000
        assert config.temperature == 0.5


class TestTestingConfig:
    """Tests for TestingConfig dataclass."""

    def test_default_values(self):
        """Test default values are correctly set."""
        config = TestingConfig()
        assert config.test_mode is False
        assert config.test_output_directory == "test_outputs"
        assert config.test_timeout == 30

    def test_custom_values(self):
        """Test custom values can be set."""
        config = TestingConfig(
            test_mode=True, test_output_directory="custom_tests", test_timeout=60
        )
        assert config.test_mode is True
        assert config.test_output_directory == "custom_tests"
        assert config.test_timeout == 60


class TestPerformanceConfig:
    """Tests for PerformanceConfig dataclass."""

    def test_default_values(self):
        """Test default values are correctly set."""
        config = PerformanceConfig()
        assert config.enable_monitoring is False
        assert config.max_memory_mb == 512
        assert config.enable_caching is True

    def test_custom_values(self):
        """Test custom values can be set."""
        config = PerformanceConfig(
            enable_monitoring=True, max_memory_mb=1024, enable_caching=False
        )
        assert config.enable_monitoring is True
        assert config.max_memory_mb == 1024
        assert config.enable_caching is False


class TestFeaturesConfig:
    """Tests for FeaturesConfig dataclass."""

    def test_default_values(self):
        """Test default values are correctly set."""
        config = FeaturesConfig()
        assert config.ai_enhanced_narratives is False
        assert config.advanced_world_state is False
        assert config.multiplayer_support is False
        assert config.realtime_updates is False

    def test_custom_values(self):
        """Test custom values can be set."""
        config = FeaturesConfig(
            ai_enhanced_narratives=True,
            advanced_world_state=True,
            multiplayer_support=True,
            realtime_updates=True,
        )
        assert config.ai_enhanced_narratives is True
        assert config.advanced_world_state is True
        assert config.multiplayer_support is True
        assert config.realtime_updates is True


class TestValidationConfig:
    """Tests for ValidationConfig dataclass."""

    def test_default_values(self):
        """Test default values are correctly set."""
        config = ValidationConfig()
        assert config.require_character_sheets is True
        assert config.validate_campaign_log is True
        assert config.check_file_permissions is True

    def test_custom_values(self):
        """Test custom values can be set."""
        config = ValidationConfig(
            require_character_sheets=False,
            validate_campaign_log=False,
            check_file_permissions=False,
        )
        assert config.require_character_sheets is False
        assert config.validate_campaign_log is False
        assert config.check_file_permissions is False


class TestAppConfig:
    """Tests for AppConfig dataclass."""

    def test_default_values(self):
        """Test default values create instances of all sub-configs."""
        config = AppConfig()
        assert isinstance(config.simulation, SimulationConfig)
        assert isinstance(config.paths, PathsConfig)
        assert isinstance(config.characters, CharacterConfig)
        assert isinstance(config.director, DirectorConfig)
        assert isinstance(config.chronicler, ChroniclerConfig)
        assert isinstance(config.llm, LLMConfig)
        assert isinstance(config.testing, TestingConfig)
        assert isinstance(config.performance, PerformanceConfig)
        assert isinstance(config.features, FeaturesConfig)
        assert isinstance(config.validation, ValidationConfig)


class TestConfigurationError:
    """Tests for ConfigurationError exception."""

    def test_exception_inheritance(self):
        """Test that ConfigurationError inherits from Exception."""
        assert issubclass(ConfigurationError, Exception)

    def test_exception_can_be_raised(self):
        """Test that ConfigurationError can be raised and caught."""
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("Test error message")

    def test_exception_message(self):
        """Test that exception message is preserved."""
        try:
            raise ConfigurationError("Custom message")
        except ConfigurationError as e:
            assert str(e) == "Custom message"


class TestConfigLoaderSingleton:
    """Tests for ConfigLoader singleton behavior."""

    def setup_method(self):
        """Reset singleton before each test."""
        ConfigLoader._instance = None
        ConfigLoader._config_cache = None
        ConfigLoader._last_modified = None

    def teardown_method(self):
        """Clean up after each test."""
        ConfigLoader._instance = None
        ConfigLoader._config_cache = None
        ConfigLoader._last_modified = None

    def test_singleton_instance(self):
        """Test that ConfigLoader is a singleton."""
        loader1 = ConfigLoader.get_instance()
        loader2 = ConfigLoader.get_instance()
        assert loader1 is loader2

    def test_singleton_via_constructor(self):
        """Test that constructor returns same instance."""
        loader1 = ConfigLoader()
        loader2 = ConfigLoader()
        assert loader1 is loader2

    def test_thread_safety(self):
        """Test thread-safe singleton creation."""
        instances = []

        def create_instance():
            instances.append(ConfigLoader.get_instance())

        threads = [threading.Thread(target=create_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All instances should be the same object
        assert all(i is instances[0] for i in instances)


class TestConfigLoaderLoadConfig:
    """Tests for ConfigLoader.load_config method."""

    def setup_method(self):
        """Reset singleton before each test."""
        ConfigLoader._instance = None
        ConfigLoader._config_cache = None
        ConfigLoader._last_modified = None

    def teardown_method(self):
        """Clean up after each test."""
        ConfigLoader._instance = None
        ConfigLoader._config_cache = None
        ConfigLoader._last_modified = None

    @patch("os.path.exists")
    @patch("builtins.open", mock_open(read_data="simulation:\n  turns: 5"))
    @patch.object(ConfigLoader, "_get_file_mtime")
    def test_load_config_from_file(self, mock_mtime, mock_exists):
        """Test loading configuration from YAML file."""
        mock_exists.return_value = True
        mock_mtime.return_value = 12345.0

        loader = ConfigLoader()
        config = loader.load_config()

        assert isinstance(config, AppConfig)
        assert config.simulation.turns == 5

    @patch("os.path.exists")
    def test_load_config_file_not_found(self, mock_exists):
        """Test fallback to defaults when file not found."""
        mock_exists.return_value = False

        loader = ConfigLoader()
        config = loader.load_config()

        assert isinstance(config, AppConfig)
        assert config.simulation.turns == 3  # Default value

    @patch("os.path.exists")
    @patch("builtins.open", mock_open(read_data=""))
    def test_load_config_empty_file(self, mock_exists):
        """Test handling of empty configuration file."""
        mock_exists.return_value = True

        loader = ConfigLoader()
        config = loader.load_config()

        assert isinstance(config, AppConfig)

    @patch("os.path.exists")
    @patch("builtins.open", mock_open(read_data="invalid: yaml: content:"))
    def test_load_config_invalid_yaml(self, mock_exists):
        """Test handling of invalid YAML."""
        mock_exists.return_value = True

        loader = ConfigLoader()
        config = loader.load_config()

        # Should fall back to defaults
        assert isinstance(config, AppConfig)

    def test_load_config_force_reload(self):
        """Test force reload functionality."""
        loader = ConfigLoader()
        config1 = loader.load_config()
        config2 = loader.load_config(force_reload=True)

        assert isinstance(config1, AppConfig)
        assert isinstance(config2, AppConfig)

    @patch("os.path.exists")
    @patch("builtins.open", mock_open(read_data="simulation:\n  turns: 5"))
    @patch.object(ConfigLoader, "_get_file_mtime")
    def test_load_config_caching(self, mock_mtime, mock_exists):
        """Test configuration caching."""
        mock_exists.return_value = True
        mock_mtime.return_value = 12345.0

        loader = ConfigLoader()
        config1 = loader.load_config()
        config2 = loader.load_config()

        assert config1 is config2


class TestConfigLoaderYAMLLoading:
    """Tests for YAML file loading."""

    def setup_method(self):
        """Reset singleton before each test."""
        ConfigLoader._instance = None
        ConfigLoader._config_cache = None
        ConfigLoader._last_modified = None

    def teardown_method(self):
        """Clean up after each test."""
        ConfigLoader._instance = None
        ConfigLoader._config_cache = None
        ConfigLoader._last_modified = None

    @patch("builtins.open", mock_open(read_data="key: value"))
    def test_load_yaml_file_success(self):
        """Test successful YAML file loading."""
        loader = ConfigLoader()
        data = loader._load_yaml_file("test.yaml")
        assert data == {"key": "value"}

    @patch("builtins.open", mock_open(read_data=""))
    def test_load_yaml_file_empty(self):
        """Test loading empty YAML file."""
        loader = ConfigLoader()
        data = loader._load_yaml_file("test.yaml")
        assert data == {}

    @patch("builtins.open", mock_open(read_data="not a dict"))
    def test_load_yaml_file_not_dict(self):
        """Test YAML file with non-dict content."""
        loader = ConfigLoader()
        with pytest.raises(ConfigurationError) as exc_info:
            loader._load_yaml_file("test.yaml")
        assert "dictionary" in str(exc_info.value)

    @patch("builtins.open", side_effect=IOError("File not found"))
    def test_load_yaml_file_io_error(self, mock_open):
        """Test YAML file loading with IO error."""
        loader = ConfigLoader()
        with pytest.raises(ConfigurationError) as exc_info:
            loader._load_yaml_file("test.yaml")
        assert "File reading error" in str(exc_info.value)


class TestConfigLoaderConfigCreation:
    """Tests for configuration creation from data."""

    def setup_method(self):
        """Reset singleton before each test."""
        ConfigLoader._instance = None

    def teardown_method(self):
        """Clean up after each test."""
        ConfigLoader._instance = None

    def test_create_config_from_empty_data(self):
        """Test creating config from empty data."""
        loader = ConfigLoader()
        config = loader._create_config_from_data({})
        assert isinstance(config, AppConfig)
        assert config.simulation.turns == 3  # Default

    def test_create_config_from_partial_data(self):
        """Test creating config from partial data."""
        loader = ConfigLoader()
        data = {"simulation": {"turns": 10}}
        config = loader._create_config_from_data(data)
        assert config.simulation.turns == 10
        assert config.simulation.max_agents == 10  # Default

    def test_create_config_complete_data(self):
        """Test creating config from complete data."""
        loader = ConfigLoader()
        data = {
            "simulation": {
                "turns": 5,
                "max_agents": 20,
                "api_timeout": 60,
                "logging_level": "DEBUG",
            },
            "paths": {
                "character_sheets_path": "/sheets",
                "log_file_path": "log.md",
                "output_directory": "output",
            },
            "characters": {
                "default_sheets": ["char1.md"],
                "max_actions_per_turn": 10,
            },
            "director": {
                "campaign_log_filename": "campaign.md",
                "world_state_file": "world.yaml",
                "max_turn_history": 50,
                "error_threshold": 5,
            },
            "chronicler": {
                "max_events_per_batch": 100,
                "narrative_style": "tactical",
                "output_directory": "narratives",
            },
            "llm": {
                "api_endpoint": "https://api.example.com",
                "api_key": "key",
                "model": "gpt-4",
                "max_tokens": 2000,
                "temperature": 0.5,
            },
            "testing": {
                "test_mode": True,
                "test_output_directory": "tests",
                "test_timeout": 60,
            },
            "performance": {
                "enable_monitoring": True,
                "max_memory_mb": 1024,
                "enable_caching": False,
            },
            "features": {
                "ai_enhanced_narratives": True,
                "advanced_world_state": True,
                "multiplayer_support": True,
                "realtime_updates": True,
            },
            "validation": {
                "require_character_sheets": False,
                "validate_campaign_log": False,
                "check_file_permissions": False,
            },
        }
        config = loader._create_config_from_data(data)
        assert config.simulation.turns == 5
        assert config.paths.character_sheets_path == "/sheets"
        assert config.characters.default_sheets == ["char1.md"]
        assert config.director.campaign_log_filename == "campaign.md"
        assert config.chronicler.narrative_style == "tactical"
        assert config.llm.api_endpoint == "https://api.example.com"
        assert config.testing.test_mode is True
        assert config.performance.enable_monitoring is True
        assert config.features.ai_enhanced_narratives is True
        assert config.validation.require_character_sheets is False


class TestConfigLoaderEnvOverrides:
    """Tests for environment variable overrides."""

    def setup_method(self):
        """Reset singleton and clear env vars before each test."""
        ConfigLoader._instance = None
        self._clear_env_vars()

    def teardown_method(self):
        """Clean up after each test."""
        ConfigLoader._instance = None
        self._clear_env_vars()

    def _clear_env_vars(self):
        """Clear all known environment variables."""
        env_vars = [
            "W40K_SIMULATION_TURNS",
            "W40K_LOG_FILE_PATH",
            "W40K_OUTPUT_DIRECTORY",
            "W40K_CHARACTER_SHEETS_PATH",
            "W40K_MAX_AGENTS",
            "W40K_API_TIMEOUT",
            "W40K_LOGGING_LEVEL",
            "W40K_NARRATIVE_STYLE",
        ]
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]

    @patch.dict(os.environ, {"W40K_SIMULATION_TURNS": "10"})
    def test_env_override_turns(self):
        """Test environment override for simulation turns."""
        loader = ConfigLoader()
        config = AppConfig()
        result = loader._apply_env_overrides(config)
        assert result.simulation.turns == 10

    @patch.dict(os.environ, {"W40K_MAX_AGENTS": "50"})
    def test_env_override_max_agents(self):
        """Test environment override for max agents."""
        loader = ConfigLoader()
        config = AppConfig()
        result = loader._apply_env_overrides(config)
        assert result.simulation.max_agents == 50

    @patch.dict(os.environ, {"W40K_LOG_FILE_PATH": "/custom/log.md"})
    def test_env_override_log_path(self):
        """Test environment override for log file path."""
        loader = ConfigLoader()
        config = AppConfig()
        result = loader._apply_env_overrides(config)
        assert result.paths.log_file_path == "/custom/log.md"

    @patch.dict(os.environ, {"W40K_OUTPUT_DIRECTORY": "/custom/output"})
    def test_env_override_output_dir(self):
        """Test environment override for output directory."""
        loader = ConfigLoader()
        config = AppConfig()
        result = loader._apply_env_overrides(config)
        assert result.paths.output_directory == "/custom/output"

    @patch.dict(os.environ, {"W40K_API_TIMEOUT": "120"})
    def test_env_override_api_timeout(self):
        """Test environment override for API timeout."""
        loader = ConfigLoader()
        config = AppConfig()
        result = loader._apply_env_overrides(config)
        assert result.simulation.api_timeout == 120

    @patch.dict(os.environ, {"W40K_LOGGING_LEVEL": "DEBUG"})
    def test_env_override_logging_level(self):
        """Test environment override for logging level."""
        loader = ConfigLoader()
        config = AppConfig()
        result = loader._apply_env_overrides(config)
        assert result.simulation.logging_level == "DEBUG"

    @patch.dict(os.environ, {"W40K_NARRATIVE_STYLE": "philosophical"})
    def test_env_override_narrative_style(self):
        """Test environment override for narrative style."""
        loader = ConfigLoader()
        config = AppConfig()
        result = loader._apply_env_overrides(config)
        assert result.chronicler.narrative_style == "philosophical"

    @patch.dict(os.environ, {"W40K_SIMULATION_TURNS": "invalid"})
    def test_env_override_invalid_value(self):
        """Test handling of invalid environment variable value."""
        loader = ConfigLoader()
        config = AppConfig()
        result = loader._apply_env_overrides(config)
        # Should keep default value when conversion fails
        assert result.simulation.turns == 3


class TestConfigLoaderValidation:
    """Tests for configuration validation."""

    def setup_method(self):
        """Reset singleton before each test."""
        ConfigLoader._instance = None

    def teardown_method(self):
        """Clean up after each test."""
        ConfigLoader._instance = None

    def test_valid_config_passes(self):
        """Test that valid configuration passes validation."""
        loader = ConfigLoader()
        config = AppConfig()
        # Should not raise
        loader._validate_config(config)

    def test_invalid_turns_zero(self):
        """Test validation fails with zero turns."""
        loader = ConfigLoader()
        config = AppConfig()
        config.simulation.turns = 0
        with pytest.raises(ConfigurationError) as exc_info:
            loader._validate_config(config)
        assert "turns must be positive" in str(exc_info.value)

    def test_invalid_turns_negative(self):
        """Test validation fails with negative turns."""
        loader = ConfigLoader()
        config = AppConfig()
        config.simulation.turns = -1
        with pytest.raises(ConfigurationError) as exc_info:
            loader._validate_config(config)
        assert "turns must be positive" in str(exc_info.value)

    def test_invalid_max_agents_zero(self):
        """Test validation fails with zero max_agents."""
        loader = ConfigLoader()
        config = AppConfig()
        config.simulation.max_agents = 0
        with pytest.raises(ConfigurationError) as exc_info:
            loader._validate_config(config)
        assert "max_agents must be positive" in str(exc_info.value)

    def test_invalid_api_timeout_zero(self):
        """Test validation fails with zero api_timeout."""
        loader = ConfigLoader()
        config = AppConfig()
        config.simulation.api_timeout = 0
        with pytest.raises(ConfigurationError) as exc_info:
            loader._validate_config(config)
        assert "api_timeout must be positive" in str(exc_info.value)

    def test_invalid_character_sheets_path_empty(self):
        """Test validation fails with empty character_sheets_path."""
        loader = ConfigLoader()
        config = AppConfig()
        config.paths.character_sheets_path = ""
        with pytest.raises(ConfigurationError) as exc_info:
            loader._validate_config(config)
        assert "character_sheets_path cannot be empty" in str(exc_info.value)

    def test_invalid_log_file_path_empty(self):
        """Test validation fails with empty log_file_path."""
        loader = ConfigLoader()
        config = AppConfig()
        config.paths.log_file_path = ""
        with pytest.raises(ConfigurationError) as exc_info:
            loader._validate_config(config)
        assert "log_file_path cannot be empty" in str(exc_info.value)

    def test_invalid_max_actions_per_turn_zero(self):
        """Test validation fails with zero max_actions_per_turn."""
        loader = ConfigLoader()
        config = AppConfig()
        config.characters.max_actions_per_turn = 0
        with pytest.raises(ConfigurationError) as exc_info:
            loader._validate_config(config)
        assert "max_actions_per_turn must be positive" in str(exc_info.value)

    def test_invalid_max_turn_history_zero(self):
        """Test validation fails with zero max_turn_history."""
        loader = ConfigLoader()
        config = AppConfig()
        config.director.max_turn_history = 0
        with pytest.raises(ConfigurationError) as exc_info:
            loader._validate_config(config)
        assert "max_turn_history must be positive" in str(exc_info.value)

    def test_invalid_error_threshold_zero(self):
        """Test validation fails with zero error_threshold."""
        loader = ConfigLoader()
        config = AppConfig()
        config.director.error_threshold = 0
        with pytest.raises(ConfigurationError) as exc_info:
            loader._validate_config(config)
        assert "error_threshold must be positive" in str(exc_info.value)

    def test_invalid_max_events_per_batch_zero(self):
        """Test validation fails with zero max_events_per_batch."""
        loader = ConfigLoader()
        config = AppConfig()
        config.chronicler.max_events_per_batch = 0
        with pytest.raises(ConfigurationError) as exc_info:
            loader._validate_config(config)
        assert "max_events_per_batch must be positive" in str(exc_info.value)

    def test_invalid_narrative_style(self):
        """Test validation fails with invalid narrative style."""
        loader = ConfigLoader()
        config = AppConfig()
        config.chronicler.narrative_style = "invalid_style"
        with pytest.raises(ConfigurationError) as exc_info:
            loader._validate_config(config)
        assert "narrative_style must be one of" in str(exc_info.value)

    def test_invalid_llm_max_tokens_zero(self):
        """Test validation fails with zero llm max_tokens."""
        loader = ConfigLoader()
        config = AppConfig()
        config.llm.max_tokens = 0
        with pytest.raises(ConfigurationError) as exc_info:
            loader._validate_config(config)
        assert "llm.max_tokens must be positive" in str(exc_info.value)

    def test_invalid_temperature_negative(self):
        """Test validation fails with negative temperature."""
        loader = ConfigLoader()
        config = AppConfig()
        config.llm.temperature = -0.5
        with pytest.raises(ConfigurationError) as exc_info:
            loader._validate_config(config)
        assert "temperature must be between" in str(exc_info.value)

    def test_invalid_temperature_too_high(self):
        """Test validation fails with temperature > 2.0."""
        loader = ConfigLoader()
        config = AppConfig()
        config.llm.temperature = 2.5
        with pytest.raises(ConfigurationError) as exc_info:
            loader._validate_config(config)
        assert "temperature must be between" in str(exc_info.value)

    def test_valid_temperature_boundary_low(self):
        """Test validation passes with temperature = 0.0."""
        loader = ConfigLoader()
        config = AppConfig()
        config.llm.temperature = 0.0
        loader._validate_config(config)  # Should not raise

    def test_valid_temperature_boundary_high(self):
        """Test validation passes with temperature = 2.0."""
        loader = ConfigLoader()
        config = AppConfig()
        config.llm.temperature = 2.0
        loader._validate_config(config)  # Should not raise


class TestConfigLoaderConvenienceMethods:
    """Tests for ConfigLoader convenience methods."""

    def setup_method(self):
        """Reset singleton before each test."""
        ConfigLoader._instance = None

    def teardown_method(self):
        """Clean up after each test."""
        ConfigLoader._instance = None

    def test_get_simulation_turns(self):
        """Test get_simulation_turns method."""
        loader = ConfigLoader()
        turns = loader.get_simulation_turns()
        assert turns == 3  # Default

    def test_get_character_sheets_path(self):
        """Test get_character_sheets_path method."""
        loader = ConfigLoader()
        path = loader.get_character_sheets_path()
        assert path == "."  # Default

    def test_get_log_file_path(self):
        """Test get_log_file_path method."""
        loader = ConfigLoader()
        path = loader.get_log_file_path()
        assert path == "campaign_log.md"  # Default

    def test_get_output_directory(self):
        """Test get_output_directory method."""
        loader = ConfigLoader()
        directory = loader.get_output_directory()
        assert directory == "demo_narratives"  # Default

    def test_get_default_character_sheets(self):
        """Test get_default_character_sheets method."""
        loader = ConfigLoader()
        sheets = loader.get_default_character_sheets()
        # Should return a list of character sheets
        assert isinstance(sheets, list)
        assert len(sheets) > 0

    def test_get_default_character_sheets_returns_copy(self):
        """Test that get_default_character_sheets returns a copy."""
        loader = ConfigLoader()
        sheets1 = loader.get_default_character_sheets()
        sheets2 = loader.get_default_character_sheets()
        assert sheets1 is not sheets2
        sheets1.append("new.md")
        assert len(sheets2) == 2

    def test_get_campaign_log_filename(self):
        """Test get_campaign_log_filename method."""
        loader = ConfigLoader()
        filename = loader.get_campaign_log_filename()
        assert filename == "campaign_log.md"

    def test_get_max_agents(self):
        """Test get_max_agents method."""
        loader = ConfigLoader()
        max_agents = loader.get_max_agents()
        assert max_agents == 10

    def test_get_api_timeout(self):
        """Test get_api_timeout method."""
        loader = ConfigLoader()
        timeout = loader.get_api_timeout()
        assert timeout == 30

    def test_get_logging_level(self):
        """Test get_logging_level method."""
        loader = ConfigLoader()
        level = loader.get_logging_level()
        assert level == "INFO"

    def test_get_narrative_style(self):
        """Test get_narrative_style method."""
        loader = ConfigLoader()
        style = loader.get_narrative_style()
        assert style == "grimdark_dramatic"

    def test_get_max_events_per_batch(self):
        """Test get_max_events_per_batch method."""
        loader = ConfigLoader()
        max_events = loader.get_max_events_per_batch()
        assert max_events == 50

    def test_is_test_mode(self):
        """Test is_test_mode method."""
        loader = ConfigLoader()
        test_mode = loader.is_test_mode()
        assert test_mode is False

    def test_get_config(self):
        """Test get_config method."""
        loader = ConfigLoader()
        config = loader.get_config()
        assert isinstance(config, AppConfig)

    def test_reload_config(self):
        """Test reload_config method."""
        loader = ConfigLoader()
        config = loader.reload_config()
        assert isinstance(config, AppConfig)

    def test_set_config_path(self):
        """Test set_config_path method."""
        loader = ConfigLoader()
        loader.set_config_path("/custom/path.yaml")
        assert loader.config_file_path == "/custom/path.yaml"
        assert loader._config is None


class TestGlobalFunctions:
    """Tests for global convenience functions."""

    def setup_method(self):
        """Reset singleton before each test."""
        ConfigLoader._instance = None

    def teardown_method(self):
        """Clean up after each test."""
        ConfigLoader._instance = None

    def test_get_config(self):
        """Test global get_config function."""
        config = get_config()
        assert isinstance(config, AppConfig)

    def test_get_simulation_turns(self):
        """Test global get_simulation_turns function."""
        turns = get_simulation_turns()
        assert turns == 3

    def test_get_character_sheets_path(self):
        """Test global get_character_sheets_path function."""
        path = get_character_sheets_path()
        assert path == "."

    def test_get_log_file_path(self):
        """Test global get_log_file_path function."""
        path = get_log_file_path()
        assert path == "campaign_log.md"

    def test_get_output_directory(self):
        """Test global get_output_directory function."""
        directory = get_output_directory()
        assert directory == "demo_narratives"

    def test_get_default_character_sheets(self):
        """Test global get_default_character_sheets function."""
        sheets = get_default_character_sheets()
        # Should return a list of character sheets
        assert isinstance(sheets, list)
        assert len(sheets) > 0

    def test_get_campaign_log_filename(self):
        """Test global get_campaign_log_filename function."""
        filename = get_campaign_log_filename()
        assert filename == "campaign_log.md"


class TestExampleUsage:
    """Tests for example_usage function."""

    def setup_method(self):
        """Reset singleton before each test."""
        ConfigLoader._instance = None

    def teardown_method(self):
        """Clean up after each test."""
        ConfigLoader._instance = None

    @patch("src.core.config.config_loader.logger")
    def test_example_usage_runs(self, mock_logger):
        """Test that example_usage runs without errors."""
        example_usage()
        # Should log success messages
        assert mock_logger.info.called


class TestConfigLoaderFileMtime:
    """Tests for _get_file_mtime method."""

    def setup_method(self):
        """Reset singleton before each test."""
        ConfigLoader._instance = None

    def teardown_method(self):
        """Clean up after each test."""
        ConfigLoader._instance = None

    @patch("os.path.getmtime")
    def test_get_file_mtime_success(self, mock_getmtime):
        """Test successful file mtime retrieval."""
        mock_getmtime.return_value = 12345.0
        loader = ConfigLoader()
        mtime = loader._get_file_mtime("test.yaml")
        assert mtime == 12345.0

    @patch("os.path.getmtime", side_effect=OSError("File not found"))
    def test_get_file_mtime_os_error(self, mock_getmtime):
        """Test file mtime retrieval with OSError."""
        loader = ConfigLoader()
        mtime = loader._get_file_mtime("test.yaml")
        assert mtime is None

    @patch("os.path.getmtime", side_effect=IOError("IO error"))
    def test_get_file_mtime_io_error(self, mock_getmtime):
        """Test file mtime retrieval with IOError."""
        loader = ConfigLoader()
        mtime = loader._get_file_mtime("test.yaml")
        assert mtime is None
