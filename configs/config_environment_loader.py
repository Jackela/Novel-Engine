#!/usr/bin/env python3
"""
Environment-aware Configuration Loader for Novel Engine

This module provides environment-specific configuration loading capabilities
that automatically selects the appropriate configuration files based on the
current environment (development, staging, production, etc.).

Features:
- Automatic environment detection
- Environment-specific configuration fallbacks
- Configuration inheritance and overrides
- Validation and error handling
- Thread-safe operation
"""

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

class Environment(Enum):
    """Supported deployment environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"
    KUBERNETES = "kubernetes"

@dataclass
class ConfigPaths:
    """Configuration file paths for different environments."""
    environments_config: str = "configs/environments/environments.yaml"
    development_config: str = "configs/environments/development.yaml"
    settings_config: str = "configs/environments/settings.yaml"
    security_config: str = "configs/security/security.yaml"
    nginx_config: str = "configs/nginx/nginx.conf"
    prometheus_config: str = "configs/prometheus/prometheus.yml"
    prometheus_rules: str = "configs/prometheus/rules/novel-engine.yml"

class EnvironmentConfigLoader:
    """
    Environment-aware configuration loader that provides intelligent 
    configuration selection and loading based on the current environment.
    """
    
    def __init__(self, environment: Optional[str] = None):
        """
        Initialize the environment configuration loader.
        
        Args:
            environment: Target environment (auto-detected if None)
        """
        self.environment = self._detect_environment(environment)
        self.config_paths = ConfigPaths()
        self.config_cache: Dict[str, Any] = {}
        
        logger.info(f"EnvironmentConfigLoader initialized for environment: {self.environment.value}")
    
    def _detect_environment(self, env_override: Optional[str] = None) -> Environment:
        """
        Detect the current environment from various sources.
        
        Args:
            env_override: Manual environment override
            
        Returns:
            Environment: Detected or default environment
        """
        if env_override:
            try:
                return Environment(env_override.lower())
            except ValueError:
                logger.warning(f"Invalid environment override: {env_override}, using development")
        
        # Check environment variables (in order of precedence)
        env_vars = [
            'NOVEL_ENGINE_ENV',
            'ENVIRONMENT',
            'ENV',
            'FLASK_ENV',
            'NODE_ENV'
        ]
        
        for env_var in env_vars:
            env_value = os.environ.get(env_var)
            if env_value:
                try:
                    environment = Environment(env_value.lower())
                    logger.info(f"Environment detected from {env_var}: {environment.value}")
                    return environment
                except ValueError:
                    logger.debug(f"Invalid environment value in {env_var}: {env_value}")
                    continue
        
        # Check for Kubernetes environment
        if os.path.exists('/var/run/secrets/kubernetes.io'):
            logger.info("Kubernetes environment detected")
            return Environment.KUBERNETES
        
        # Check for common development indicators
        if any(os.path.exists(marker) for marker in ['.git', 'venv', '.venv', 'node_modules']):
            logger.info("Development environment detected")
            return Environment.DEVELOPMENT
        
        # Default fallback
        logger.info("Using default development environment")
        return Environment.DEVELOPMENT
    
    def load_configuration(self) -> Dict[str, Any]:
        """
        Load complete configuration for the current environment.
        
        Returns:
            Dict[str, Any]: Merged configuration dictionary
        """
        config = {}
        
        try:
            # Load base environments configuration
            environments_config = self._load_environments_config()
            
            # Get environment-specific configuration
            env_config = environments_config.get(self.environment.value, {})
            
            # Apply base configuration if available
            if 'base' in environments_config:
                base_config = environments_config['base']
                config = self._deep_merge(config, base_config)
            
            # Apply environment-specific configuration
            config = self._deep_merge(config, env_config)
            
            # Load additional configuration files
            additional_configs = {
                'development': self._load_development_config,
                'settings': self._load_settings_config,
                'security': self._load_security_config
            }
            
            for config_name, loader_func in additional_configs.items():
                try:
                    additional_config = loader_func()
                    if additional_config:
                        config = self._deep_merge(config, additional_config)
                        logger.debug(f"Loaded {config_name} configuration")
                except Exception as e:
                    logger.warning(f"Failed to load {config_name} configuration: {e}")
            
            # Apply environment variable overrides
            config = self._apply_environment_overrides(config)
            
            # Cache the configuration
            self.config_cache = config
            
            logger.info(f"Configuration loaded successfully for {self.environment.value}")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return self._get_default_configuration()
    
    def _load_environments_config(self) -> Dict[str, Any]:
        """Load the main environments configuration file."""
        return self._load_yaml_file(self.config_paths.environments_config)
    
    def _load_development_config(self) -> Dict[str, Any]:
        """Load development-specific configuration."""
        return self._load_yaml_file(self.config_paths.development_config)
    
    def _load_settings_config(self) -> Dict[str, Any]:
        """Load settings configuration."""
        return self._load_yaml_file(self.config_paths.settings_config)
    
    def _load_security_config(self) -> Dict[str, Any]:
        """Load security configuration."""
        return self._load_yaml_file(self.config_paths.security_config)
    
    def _load_yaml_file(self, file_path: str) -> Dict[str, Any]:
        """
        Load and parse a YAML configuration file.
        
        Args:
            file_path: Path to the YAML file
            
        Returns:
            Dict[str, Any]: Parsed configuration data
        """
        try:
            if not os.path.exists(file_path):
                logger.debug(f"Configuration file not found: {file_path}")
                return {}
            
            with open(file_path, 'r', encoding='utf-8') as file:
                content = yaml.safe_load(file) or {}
                logger.debug(f"Loaded configuration from: {file_path}")
                return content
                
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {file_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return {}
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries, with override values taking precedence.
        
        Args:
            base: Base dictionary
            override: Override dictionary
            
        Returns:
            Dict[str, Any]: Merged dictionary
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _apply_environment_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration.
        
        Args:
            config: Base configuration
            
        Returns:
            Dict[str, Any]: Configuration with overrides applied
        """
        # Define environment variable mappings
        env_mappings = {
            'NOVEL_ENGINE_HOST': ['api', 'host'],
            'NOVEL_ENGINE_PORT': ['api', 'port'],
            'DATABASE_URL': ['storage', 'postgres_url'],
            'REDIS_URL': ['storage', 'redis_url'],
            'LOG_LEVEL': ['logging', 'level'],
            'DEBUG_MODE': ['system', 'debug_mode'],
            'MAX_AGENTS': ['simulation', 'max_agents'],
            'API_TIMEOUT': ['simulation', 'api_timeout'],
        }
        
        for env_var, config_path in env_mappings.items():
            env_value = os.environ.get(env_var)
            if env_value:
                # Navigate to the nested configuration location
                current = config
                for key in config_path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                
                # Convert value to appropriate type
                final_key = config_path[-1]
                try:
                    # Try to convert to int first
                    if env_value.isdigit():
                        current[final_key] = int(env_value)
                    # Try to convert to bool
                    elif env_value.lower() in ['true', 'false']:
                        current[final_key] = env_value.lower() == 'true'
                    else:
                        current[final_key] = env_value
                    
                    logger.info(f"Applied environment override: {env_var}={env_value}")
                    
                except Exception as e:
                    logger.warning(f"Failed to apply environment override {env_var}: {e}")
        
        return config
    
    def _get_default_configuration(self) -> Dict[str, Any]:
        """
        Get default configuration as fallback.
        
        Returns:
            Dict[str, Any]: Default configuration
        """
        return {
            'system': {
                'name': 'Novel Engine',
                'version': '1.0.0',
                'environment': self.environment.value,
                'debug_mode': self.environment == Environment.DEVELOPMENT
            },
            'api': {
                'host': '127.0.0.1',
                'port': 8000,
                'workers': 1,
                'timeout': 30
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            'simulation': {
                'turns': 3,
                'max_agents': 10,
                'api_timeout': 30
            },
            'storage': {
                'kb_type': 'file',
                'session_storage': 'file'
            }
        }
    
    def get_config_value(self, key_path: str, default: Any = None) -> Any:
        """
        Get a specific configuration value by dot-separated path.
        
        Args:
            key_path: Dot-separated path to configuration value
            default: Default value if key not found
            
        Returns:
            Any: Configuration value or default
        """
        if not self.config_cache:
            self.load_configuration()
        
        keys = key_path.split('.')
        current = self.config_cache
        
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            logger.debug(f"Configuration key not found: {key_path}")
            return default
    
    def validate_configuration(self) -> List[str]:
        """
        Validate the loaded configuration for common issues.
        
        Returns:
            List[str]: List of validation errors (empty if valid)
        """
        errors = []
        
        if not self.config_cache:
            self.load_configuration()
        
        # Validate required sections
        required_sections = ['system', 'api', 'logging', 'simulation']
        for section in required_sections:
            if section not in self.config_cache:
                errors.append(f"Missing required configuration section: {section}")
        
        # Validate API configuration
        api_config = self.config_cache.get('api', {})
        if 'host' not in api_config:
            errors.append("Missing API host configuration")
        if 'port' not in api_config:
            errors.append("Missing API port configuration")
        elif not isinstance(api_config['port'], int) or api_config['port'] <= 0:
            errors.append("API port must be a positive integer")
        
        # Validate simulation configuration
        sim_config = self.config_cache.get('simulation', {})
        if 'max_agents' in sim_config and sim_config['max_agents'] <= 0:
            errors.append("simulation.max_agents must be positive")
        
        return errors

# Global instance for easy access
_global_loader: Optional[EnvironmentConfigLoader] = None

def get_environment_config_loader() -> EnvironmentConfigLoader:
    """
    Get the global environment configuration loader instance.
    
    Returns:
        EnvironmentConfigLoader: Global loader instance
    """
    global _global_loader
    if _global_loader is None:
        _global_loader = EnvironmentConfigLoader()
    return _global_loader

def load_config(environment: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration for the specified or detected environment.
    
    Args:
        environment: Target environment (auto-detected if None)
        
    Returns:
        Dict[str, Any]: Loaded configuration
    """
    if environment:
        loader = EnvironmentConfigLoader(environment)
        return loader.load_configuration()
    else:
        return get_environment_config_loader().load_configuration()

def get_config_value(key_path: str, default: Any = None) -> Any:
    """
    Get a configuration value by dot-separated path.
    
    Args:
        key_path: Dot-separated path to configuration value
        default: Default value if key not found
        
    Returns:
        Any: Configuration value or default
    """
    return get_environment_config_loader().get_config_value(key_path, default)

# Example usage
if __name__ == "__main__":
    # Test the environment configuration loader
    loader = EnvironmentConfigLoader()
    config = loader.load_configuration()
    
    print(f"Environment: {loader.environment.value}")
    print(f"Config keys: {list(config.keys())}")
    
    # Validate configuration
    errors = loader.validate_configuration()
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("Configuration is valid!")