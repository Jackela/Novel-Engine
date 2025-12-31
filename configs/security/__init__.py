"""
Security Configuration Module

Manages security-related configurations including authentication, authorization,
encryption settings, and security policies for the Novel Engine application.

Features:
- Authentication configuration (JWT, OAuth, API keys)
- Encryption and hashing settings
- Security headers and CORS policies
- Certificate and key management
- Rate limiting and security middleware

Example:
    from configs.security import load_auth_config, get_encryption_settings
    
    auth_config = load_auth_config()
    encryption = get_encryption_settings()
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

__version__ = "1.0.0"

# Security configuration utilities
__all__ = [
    "load_security_config",
    "get_auth_settings",
    "get_encryption_settings",
    "validate_security_config",
    "load_certificate_paths",
]


def load_security_config(env: Optional[str] = None) -> Dict[str, Any]:
    """
    Load security configuration for the specified environment.

    Args:
        env: Environment name. If None, uses current environment.

    Returns:
        Dict containing security configuration
    """
    # Placeholder for actual security configuration loading
    # Will be implemented during migration
    return {
        "auth_enabled": True,
        "encryption_enabled": True,
        "cors_enabled": True,
        "rate_limiting_enabled": True,
    }


def get_auth_settings() -> Dict[str, Any]:
    """
    Get authentication settings.

    Returns:
        Dict containing authentication configuration
    """
    return {
        "jwt_secret_key": os.getenv("JWT_SECRET_KEY", "dev-secret"),
        "jwt_algorithm": "HS256",
        "jwt_expiration": 3600,
        "refresh_token_expiration": 86400,
    }


def get_encryption_settings() -> Dict[str, Any]:
    """
    Get encryption and hashing settings.

    Returns:
        Dict containing encryption configuration
    """
    return {
        "password_hash_algorithm": "bcrypt",
        "encryption_key": os.getenv("ENCRYPTION_KEY"),
        "salt_rounds": 12,
    }


def validate_security_config(config: Dict[str, Any]) -> bool:
    """
    Validate security configuration.

    Args:
        config: Security configuration to validate

    Returns:
        bool: True if configuration is valid
    """
    required_keys = ["auth_enabled", "encryption_enabled"]
    return all(key in config for key in required_keys)


def load_certificate_paths() -> Dict[str, Path]:
    """
    Load SSL certificate and key file paths.

    Returns:
        Dict containing certificate file paths
    """
    base_path = Path(__file__).parent
    return {
        "ssl_cert": base_path / "certs" / "server.crt",
        "ssl_key": base_path / "certs" / "server.key",
        "ca_cert": base_path / "certs" / "ca.crt",
    }
