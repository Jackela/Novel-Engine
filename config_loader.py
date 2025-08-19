#!/usr/bin/env python3
"""
Configuration Loader for the Multi-Agent Simulator.

This module provides centralized configuration loading and management for the
simulation system. It handles YAML configuration file parsing, validation,
default value management, and provides thread-safe access to configuration
values throughout the application.

Key Features:
- YAML-based configuration with fallback defaults.
- Thread-safe singleton pattern for global configuration access.
- Type hints and validation for configuration values.
- Comprehensive error handling with graceful degradation.
- Environment variable override support.
- Configuration caching for performance.
"""

import os
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field

# Try to import yaml, handle gracefully if not available
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    yaml = None

# Configure logging for configuration operations
logger = logging.getLogger(__name__)


@dataclass
class SimulationConfig:
    """
    Data class representing simulation configuration parameters.
    
    Provides type-safe access to simulation settings with default values
    and validation support.
    """
    turns: int = 3
    max_agents: int = 10
    api_timeout: int = 30
    logging_level: str = "INFO"


@dataclass
class PathsConfig:
    """
    Data class representing file and directory path configurations.
    
    Centralizes all path-related settings for the simulation system.
    """
    character_sheets_path: str = "."
    log_file_path: str = "campaign_log.md"
    output_directory: str = "demo_narratives"
    test_narratives_directory: str = "test_narratives"
    simulation_logs_directory: str = "."


@dataclass
class CharacterConfig:
    """
    Data class representing character-related configurations.
    
    Contains settings for character sheets, actions, and behavior parameters.
    """
    default_sheets: List[str] = field(default_factory=lambda: ["character_krieg.md", "character_ork.md"])
    max_actions_per_turn: int = 5


@dataclass
class DirectorConfig:
    """
    Data class representing DirectorAgent configuration parameters.
    
    Contains settings specific to the DirectorAgent's operation and behavior.
    """
    campaign_log_filename: str = "campaign_log.md"
    world_state_file: Optional[str] = None
    max_turn_history: int = 100
    error_threshold: int = 10


@dataclass
class ChroniclerConfig:
    """
    Data class representing ChroniclerAgent configuration parameters.
    
    Contains settings for narrative generation and story transcription.
    """
    max_events_per_batch: int = 50
    narrative_style: str = "grimdark_dramatic"
    output_directory: str = "demo_narratives"


@dataclass
class LLMConfig:
    """
    Data class representing LLM integration configuration.
    
    Prepared for future AI/LLM service integration with authentication
    and generation parameters.
    """
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.7


@dataclass
class TestingConfig:
    """
    Data class representing testing configuration parameters.
    
    Contains settings for test mode operation and test output management.
    """
    test_mode: bool = False
    test_output_directory: str = "test_outputs"
    test_timeout: int = 30


@dataclass
class PerformanceConfig:
    """
    Data class representing performance and monitoring settings.
    
    Contains configuration for performance optimization and resource management.
    """
    enable_monitoring: bool = False
    max_memory_mb: int = 512
    enable_caching: bool = True


@dataclass
class FeaturesConfig:
    """
    Data class representing feature flags for optional functionality.
    
    Enables/disables various features for testing and deployment flexibility.
    """
    ai_enhanced_narratives: bool = False
    advanced_world_state: bool = False
    multiplayer_support: bool = False
    realtime_updates: bool = False


@dataclass
class ValidationConfig:
    """
    Data class representing validation rules and requirements.
    
    Contains settings for input validation and error checking behavior.
    """
    require_character_sheets: bool = True
    validate_campaign_log: bool = True
    check_file_permissions: bool = True


@dataclass
class AppConfig:
    """
    Main configuration container that holds all configuration sections.
    
    Provides structured access to all configuration parameters with
    proper typing and default values.
    """
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    characters: CharacterConfig = field(default_factory=CharacterConfig)
    director: DirectorConfig = field(default_factory=DirectorConfig)
    chronicler: ChroniclerConfig = field(default_factory=ChroniclerConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    testing: TestingConfig = field(default_factory=TestingConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    features: FeaturesConfig = field(default_factory=FeaturesConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)


class ConfigurationError(Exception):
    """
    Custom exception for configuration-related errors.
    
    Raised when configuration loading, parsing, or validation fails.
    """
    pass


class ConfigLoader:
    """
    Thread-safe singleton configuration loader for the simulation system.
    
    Provides centralized configuration management with YAML file loading,
    default value fallbacks, environment variable overrides, and caching
    for optimal performance.
    
    Key Features:
    - Singleton pattern ensures single configuration instance
    - Thread-safe configuration access and updates
    - YAML file parsing with comprehensive error handling
    - Environment variable override support
    - Configuration validation and type checking
    - Graceful degradation when configuration files are missing
    
    Usage:
        >>> config = ConfigLoader.get_instance()
        >>> turns = config.get_simulation_turns()
        >>> log_path = config.get_log_file_path()
    """
    
    _instance: Optional['ConfigLoader'] = None
    _lock = threading.Lock()
    _config_cache: Optional[AppConfig] = None
    _last_modified: Optional[float] = None
    
    def __new__(cls) -> 'ConfigLoader':
        """
        Implement singleton pattern with thread-safety.
        
        Returns:
            ConfigLoader: Single instance of the configuration loader
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ConfigLoader, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """
        Initialize the configuration loader if not already initialized.
        
        Prevents multiple initialization in singleton pattern.
        """
        if not getattr(self, '_initialized', False):
            self.config_file_path = "config.yaml"
            self._config: Optional[AppConfig] = None
            self._load_lock = threading.RLock()
            self._initialized = True
            logger.info("ConfigLoader singleton initialized")
    
    @classmethod
    def get_instance(cls) -> 'ConfigLoader':
        """
        Get the singleton instance of ConfigLoader.
        
        Returns:
            ConfigLoader: The singleton configuration loader instance
        """
        return cls()
    
    def load_config(self, config_path: Optional[str] = None, force_reload: bool = False) -> AppConfig:
        """
        Load configuration from YAML file with comprehensive error handling.
        
        Attempts to load configuration from the specified YAML file, falling back
        to default values if the file is missing or malformed. Supports caching
        for performance and thread-safe operation.
        
        Args:
            config_path: Optional path to configuration file (uses default if None)
            force_reload: Force reload even if cached configuration exists
            
        Returns:
            AppConfig: Complete configuration object with all settings
            
        Raises:
            ConfigurationError: If configuration loading fails critically
        """
        with self._load_lock:
            # Use provided path or default
            if config_path:
                self.config_file_path = config_path
            
            # Check if we need to reload based on file modification time
            needs_reload = force_reload or self._config is None
            
            if not needs_reload and self._config is not None:
                current_mtime = self._get_file_mtime(self.config_file_path)
                if current_mtime != self._last_modified:
                    needs_reload = True
            
            if not needs_reload:
                logger.debug("Using cached configuration")
                return self._config
            
            logger.info(f"Loading configuration from: {self.config_file_path}")
            
            try:
                # Check YAML library availability
                if not YAML_AVAILABLE:
                    logger.warning("PyYAML not available, using default configuration")
                    return self._create_default_config()
                
                # Check if config file exists
                if not os.path.exists(self.config_file_path):
                    logger.warning(f"Configuration file not found: {self.config_file_path}")
                    logger.info("Using default configuration values")
                    return self._create_default_config()
                
                # Load and parse YAML file
                config_data = self._load_yaml_file(self.config_file_path)
                
                # Create configuration object from loaded data
                config = self._create_config_from_data(config_data)
                
                # Apply environment variable overrides
                config = self._apply_env_overrides(config)
                
                # Validate configuration
                self._validate_config(config)
                
                # Cache the configuration
                self._config = config
                self._last_modified = self._get_file_mtime(self.config_file_path)
                
                logger.info("Configuration loaded successfully")
                logger.debug(f"Simulation turns: {config.simulation.turns}")
                logger.debug(f"Log file path: {config.paths.log_file_path}")
                logger.debug(f"Output directory: {config.paths.output_directory}")
                
                return config
                
            except Exception as e:
                logger.error(f"Failed to load configuration: {str(e)}")
                logger.info("Falling back to default configuration")
                
                # Return default configuration as fallback
                default_config = self._create_default_config()
                self._config = default_config
                return default_config
    
    def _get_file_mtime(self, file_path: str) -> Optional[float]:
        """
        Get file modification time safely.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File modification time or None if file doesn't exist
        """
        try:
            return os.path.getmtime(file_path)
        except (OSError, IOError):
            return None
    
    def _load_yaml_file(self, file_path: str) -> Dict[str, Any]:
        """
        Load and parse YAML configuration file.
        
        Args:
            file_path: Path to the YAML configuration file
            
        Returns:
            Dictionary containing parsed configuration data
            
        Raises:
            ConfigurationError: If file reading or YAML parsing fails
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            if not content.strip():
                logger.warning("Configuration file is empty")
                return {}
            
            config_data = yaml.safe_load(content)
            
            if config_data is None:
                logger.warning("YAML file contains no data")
                return {}
            
            if not isinstance(config_data, dict):
                raise ConfigurationError(f"Configuration file must contain a dictionary at root level")
            
            logger.debug(f"Successfully parsed YAML configuration: {len(config_data)} sections")
            return config_data
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"YAML parsing error: {str(e)}")
        except (OSError, IOError) as e:
            raise ConfigurationError(f"File reading error: {str(e)}")
        except Exception as e:
            raise ConfigurationError(f"Unexpected error loading configuration: {str(e)}")
    
    def _create_config_from_data(self, config_data: Dict[str, Any]) -> AppConfig:
        """
        Create AppConfig object from parsed configuration data.
        
        Args:
            config_data: Dictionary containing configuration values
            
        Returns:
            AppConfig object populated with configuration values
        """
        config = AppConfig()
        
        # Load simulation configuration
        if 'simulation' in config_data:
            sim_data = config_data['simulation']
            config.simulation = SimulationConfig(
                turns=sim_data.get('turns', 3),
                max_agents=sim_data.get('max_agents', 10),
                api_timeout=sim_data.get('api_timeout', 30),
                logging_level=sim_data.get('logging_level', 'INFO')
            )
        
        # Load paths configuration
        if 'paths' in config_data:
            paths_data = config_data['paths']
            config.paths = PathsConfig(
                character_sheets_path=paths_data.get('character_sheets_path', '.'),
                log_file_path=paths_data.get('log_file_path', 'campaign_log.md'),
                output_directory=paths_data.get('output_directory', 'demo_narratives'),
                test_narratives_directory=paths_data.get('test_narratives_directory', 'test_narratives'),
                simulation_logs_directory=paths_data.get('simulation_logs_directory', '.')
            )
        
        # Load character configuration
        if 'characters' in config_data:
            char_data = config_data['characters']
            config.characters = CharacterConfig(
                default_sheets=char_data.get('default_sheets', ['character_krieg.md', 'character_ork.md']),
                max_actions_per_turn=char_data.get('max_actions_per_turn', 5)
            )
        
        # Load director configuration
        if 'director' in config_data:
            director_data = config_data['director']
            config.director = DirectorConfig(
                campaign_log_filename=director_data.get('campaign_log_filename', 'campaign_log.md'),
                world_state_file=director_data.get('world_state_file'),
                max_turn_history=director_data.get('max_turn_history', 100),
                error_threshold=director_data.get('error_threshold', 10)
            )
        
        # Load chronicler configuration
        if 'chronicler' in config_data:
            chronicler_data = config_data['chronicler']
            config.chronicler = ChroniclerConfig(
                max_events_per_batch=chronicler_data.get('max_events_per_batch', 50),
                narrative_style=chronicler_data.get('narrative_style', 'grimdark_dramatic'),
                output_directory=chronicler_data.get('output_directory', 'demo_narratives')
            )
        
        # Load LLM configuration
        if 'llm' in config_data:
            llm_data = config_data['llm']
            config.llm = LLMConfig(
                api_endpoint=llm_data.get('api_endpoint'),
                api_key=llm_data.get('api_key'),
                model=llm_data.get('model'),
                max_tokens=llm_data.get('max_tokens', 1000),
                temperature=llm_data.get('temperature', 0.7)
            )
        
        # Load testing configuration
        if 'testing' in config_data:
            testing_data = config_data['testing']
            config.testing = TestingConfig(
                test_mode=testing_data.get('test_mode', False),
                test_output_directory=testing_data.get('test_output_directory', 'test_outputs'),
                test_timeout=testing_data.get('test_timeout', 30)
            )
        
        # Load performance configuration
        if 'performance' in config_data:
            perf_data = config_data['performance']
            config.performance = PerformanceConfig(
                enable_monitoring=perf_data.get('enable_monitoring', False),
                max_memory_mb=perf_data.get('max_memory_mb', 512),
                enable_caching=perf_data.get('enable_caching', True)
            )
        
        # Load features configuration
        if 'features' in config_data:
            features_data = config_data['features']
            config.features = FeaturesConfig(
                ai_enhanced_narratives=features_data.get('ai_enhanced_narratives', False),
                advanced_world_state=features_data.get('advanced_world_state', False),
                multiplayer_support=features_data.get('multiplayer_support', False),
                realtime_updates=features_data.get('realtime_updates', False)
            )
        
        # Load validation configuration
        if 'validation' in config_data:
            validation_data = config_data['validation']
            config.validation = ValidationConfig(
                require_character_sheets=validation_data.get('require_character_sheets', True),
                validate_campaign_log=validation_data.get('validate_campaign_log', True),
                check_file_permissions=validation_data.get('check_file_permissions', True)
            )
        
        return config
    
    def _create_default_config(self) -> AppConfig:
        """
        Create default configuration when no config file is available.
        
        Returns:
            AppConfig with all default values
        """
        logger.info("Creating default configuration")
        return AppConfig()
    
    def _apply_env_overrides(self, config: AppConfig) -> AppConfig:
        """
        Apply environment variable overrides to configuration values.
        
        Args:
            config: Base configuration to apply overrides to
            
        Returns:
            Configuration with environment variable overrides applied
        """
        # Environment variable mapping
        env_mappings = {
            'W40K_SIMULATION_TURNS': lambda val: setattr(config.simulation, 'turns', int(val)),
            'W40K_LOG_FILE_PATH': lambda val: setattr(config.paths, 'log_file_path', val),
            'W40K_OUTPUT_DIRECTORY': lambda val: setattr(config.paths, 'output_directory', val),
            'W40K_CHARACTER_SHEETS_PATH': lambda val: setattr(config.paths, 'character_sheets_path', val),
            'W40K_MAX_AGENTS': lambda val: setattr(config.simulation, 'max_agents', int(val)),
            'W40K_API_TIMEOUT': lambda val: setattr(config.simulation, 'api_timeout', int(val)),
            'W40K_LOGGING_LEVEL': lambda val: setattr(config.simulation, 'logging_level', val),
            'W40K_NARRATIVE_STYLE': lambda val: setattr(config.chronicler, 'narrative_style', val),
        }
        
        # Apply environment overrides
        applied_overrides = []
        for env_var, setter in env_mappings.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                try:
                    setter(env_value)
                    applied_overrides.append(f"{env_var}={env_value}")
                    logger.info(f"Applied environment override: {env_var}={env_value}")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid environment variable value for {env_var}: {env_value} ({e})")
        
        if applied_overrides:
            logger.info(f"Applied {len(applied_overrides)} environment overrides")
        
        return config
    
    def _validate_config(self, config: AppConfig) -> None:
        """
        Validate configuration values for consistency and correctness.
        
        Args:
            config: Configuration to validate
            
        Raises:
            ConfigurationError: If configuration contains invalid values
        """
        # Validate simulation parameters
        if config.simulation.turns <= 0:
            raise ConfigurationError("simulation.turns must be positive")
        
        if config.simulation.max_agents <= 0:
            raise ConfigurationError("simulation.max_agents must be positive")
        
        if config.simulation.api_timeout <= 0:
            raise ConfigurationError("simulation.api_timeout must be positive")
        
        # Validate path configurations
        if not config.paths.character_sheets_path:
            raise ConfigurationError("paths.character_sheets_path cannot be empty")
        
        if not config.paths.log_file_path:
            raise ConfigurationError("paths.log_file_path cannot be empty")
        
        # Validate character configuration
        if config.characters.max_actions_per_turn <= 0:
            raise ConfigurationError("characters.max_actions_per_turn must be positive")
        
        # Validate director configuration
        if config.director.max_turn_history <= 0:
            raise ConfigurationError("director.max_turn_history must be positive")
        
        if config.director.error_threshold <= 0:
            raise ConfigurationError("director.error_threshold must be positive")
        
        # Validate chronicler configuration
        if config.chronicler.max_events_per_batch <= 0:
            raise ConfigurationError("chronicler.max_events_per_batch must be positive")
        
        valid_styles = ['grimdark_dramatic', 'tactical', 'philosophical']
        if config.chronicler.narrative_style not in valid_styles:
            raise ConfigurationError(f"chronicler.narrative_style must be one of: {valid_styles}")
        
        # Validate LLM configuration
        if config.llm.max_tokens <= 0:
            raise ConfigurationError("llm.max_tokens must be positive")
        
        if not (0.0 <= config.llm.temperature <= 2.0):
            raise ConfigurationError("llm.temperature must be between 0.0 and 2.0")
        
        logger.debug("Configuration validation passed")
    
    # Convenience methods for accessing common configuration values
    
    def get_simulation_turns(self) -> int:
        """Get the number of simulation turns to execute."""
        config = self.get_config()
        return config.simulation.turns
    
    def get_character_sheets_path(self) -> str:
        """Get the path to character sheet files."""
        config = self.get_config()
        return config.paths.character_sheets_path
    
    def get_log_file_path(self) -> str:
        """Get the path to the campaign log file."""
        config = self.get_config()
        return config.paths.log_file_path
    
    def get_output_directory(self) -> str:
        """Get the output directory for narrative files."""
        config = self.get_config()
        return config.paths.output_directory
    
    def get_default_character_sheets(self) -> List[str]:
        """Get the list of default character sheet files."""
        config = self.get_config()
        return config.characters.default_sheets.copy()
    
    def get_campaign_log_filename(self) -> str:
        """Get the campaign log filename."""
        config = self.get_config()
        return config.director.campaign_log_filename
    
    def get_max_agents(self) -> int:
        """Get the maximum number of agents allowed."""
        config = self.get_config()
        return config.simulation.max_agents
    
    def get_api_timeout(self) -> int:
        """Get the API timeout in seconds."""
        config = self.get_config()
        return config.simulation.api_timeout
    
    def get_logging_level(self) -> str:
        """Get the logging level."""
        config = self.get_config()
        return config.simulation.logging_level
    
    def get_narrative_style(self) -> str:
        """Get the narrative style for chronicler."""
        config = self.get_config()
        return config.chronicler.narrative_style
    
    def get_max_events_per_batch(self) -> int:
        """Get the maximum events per batch for chronicler."""
        config = self.get_config()
        return config.chronicler.max_events_per_batch
    
    def is_test_mode(self) -> bool:
        """Check if test mode is enabled."""
        config = self.get_config()
        return config.testing.test_mode
    
    def get_config(self) -> AppConfig:
        """
        Get the current configuration, loading if necessary.
        
        Returns:
            AppConfig: Current configuration object
        """
        if self._config is None:
            return self.load_config()
        return self._config
    
    def reload_config(self) -> AppConfig:
        """
        Force reload the configuration from file.
        
        Returns:
            AppConfig: Reloaded configuration object
        """
        return self.load_config(force_reload=True)
    
    def set_config_path(self, config_path: str) -> None:
        """
        Set a new configuration file path.
        
        Args:
            config_path: Path to the new configuration file
        """
        self.config_file_path = config_path
        self._config = None  # Clear cache to force reload


# Global convenience functions for easy access to configuration

def get_config() -> AppConfig:
    """
    Global function to get the current configuration.
    
    Returns:
        AppConfig: Current configuration object
    """
    return ConfigLoader.get_instance().get_config()


def get_simulation_turns(config=None) -> int:
    """Global function to get simulation turns."""
    return ConfigLoader.get_instance().get_simulation_turns()


def get_character_sheets_path() -> str:
    """Global function to get character sheets path."""
    return ConfigLoader.get_instance().get_character_sheets_path()


def get_log_file_path() -> str:
    """Global function to get log file path."""
    return ConfigLoader.get_instance().get_log_file_path()


def get_output_directory() -> str:
    """Global function to get output directory."""
    return ConfigLoader.get_instance().get_output_directory()


def get_default_character_sheets(config=None) -> List[str]:
    """Global function to get default character sheets."""
    return ConfigLoader.get_instance().get_default_character_sheets()


def get_campaign_log_filename() -> str:
    """Global function to get campaign log filename."""
    return ConfigLoader.get_instance().get_campaign_log_filename()


# Example usage and testing functions

def example_usage():
    """
    Example usage of the configuration system.
    
    Demonstrates how to use the ConfigLoader and access configuration values.
    """
    print("Configuration System Example Usage:")
    print("==================================")
    
    try:
        # Get configuration loader instance
        config_loader = ConfigLoader.get_instance()
        print("✓ ConfigLoader singleton created")
        
        # Load configuration
        config = config_loader.load_config()
        print("✓ Configuration loaded successfully")
        
        # Access configuration values using convenience methods
        turns = config_loader.get_simulation_turns()
        log_path = config_loader.get_log_file_path()
        output_dir = config_loader.get_output_directory()
        char_sheets = config_loader.get_default_character_sheets()
        
        print(f"✓ Simulation turns: {turns}")
        print(f"✓ Log file path: {log_path}")
        print(f"✓ Output directory: {output_dir}")
        print(f"✓ Character sheets: {char_sheets}")
        
        # Access full configuration object
        full_config = config_loader.get_config()
        print(f"✓ Max agents: {full_config.simulation.max_agents}")
        print(f"✓ API timeout: {full_config.simulation.api_timeout}")
        print(f"✓ Narrative style: {full_config.chronicler.narrative_style}")
        
        # Test global convenience functions
        global_turns = get_simulation_turns()
        global_log_path = get_log_file_path()
        
        print(f"✓ Global function - turns: {global_turns}")
        print(f"✓ Global function - log path: {global_log_path}")
        
        print("\nConfiguration system is ready for use!")
        
    except Exception as e:
        print(f"✗ Configuration example failed: {e}")


if __name__ == "__main__":
    # Run example usage when script is executed directly
    example_usage()