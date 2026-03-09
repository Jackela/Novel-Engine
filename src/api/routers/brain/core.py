"""
Brain Router Core Utilities

Shared encryption utilities and helper functions.
OPT-014: Security hardening for API key management.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import structlog
from cryptography.fernet import Fernet

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)

# OPT-014: Security hardening - No random fallback key
# Encryption key MUST be provided via BRAIN_SETTINGS_ENCRYPTION_KEY env var
_ENCRYPTION_KEY_WARNING_SHOWN = False


def get_encryption_key() -> bytes:
    """
    Get the encryption key for API keys.

    OPT-014: Security hardening - Require BRAIN_SETTINGS_ENCRYPTION_KEY.
    No random fallback is provided. If the key is not set, a warning is logged
    once and operations will fail gracefully.

    Why: Dependency injection for testability and security enforcement.

    Returns:
        The encryption key as bytes

    Raises:
        ValueError: If the key is not set or invalid
    """
    global _ENCRYPTION_KEY_WARNING_SHOWN

    key = os.getenv("BRAIN_SETTINGS_ENCRYPTION_KEY")
    if not key:
        if not _ENCRYPTION_KEY_WARNING_SHOWN:
            logger.warning(
                "security_encryption_key_not_set",
                message="BRAIN_SETTINGS_ENCRYPTION_KEY not set. API keys will not be persisted securely.",
            )
            _ENCRYPTION_KEY_WARNING_SHOWN = True
        # Return a placeholder that will cause encryption to fail
        raise ValueError(
            "BRAIN_SETTINGS_ENCRYPTION_KEY not set. "
            "Cannot securely store API keys. "
            "Please set the BRAIN_SETTINGS_ENCRYPTION_KEY environment variable."
        )

    # Ensure key is bytes
    key_bytes = key.encode() if isinstance(key, str) else key

    # Validate key is a valid Fernet key (44 bytes base64-encoded)
    try:
        Fernet(key_bytes)
    except Exception as e:
        raise ValueError(
            f"Invalid BRAIN_SETTINGS_ENCRYPTION_KEY: {e}. "
            "Generate a valid key with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        ) from e

    return key_bytes


def get_fernet() -> Fernet | None:
    """
    Get the Fernet encryptor for API keys.

    OPT-014: Returns None if encryption is not configured,
    allowing callers to fail gracefully with a clear error message.

    Returns:
        Fernet encryptor instance, or None if encryption key is not set

    Why:
        - Graceful degradation when encryption key is missing
        - Clear error messages to users about security configuration
    """
    global _ENCRYPTION_KEY_WARNING_SHOWN

    key = os.getenv("BRAIN_SETTINGS_ENCRYPTION_KEY")
    if not key:
        if not _ENCRYPTION_KEY_WARNING_SHOWN:
            logger.warning(
                "security_encryption_key_not_set",
                message="BRAIN_SETTINGS_ENCRYPTION_KEY not set. API keys cannot be stored securely.",
            )
            _ENCRYPTION_KEY_WARNING_SHOWN = True
        return None

    key_bytes = key.encode() if isinstance(key, str) else key

    try:
        return Fernet(key_bytes)
    except Exception as e:
        logger.error(
            "invalid_encryption_key", error=str(e), error_type=type(e).__name__
        )
        return None


def encrypt_api_key(key: str, fernet: Fernet | None) -> str:
    """
    Encrypt an API key.

    OPT-014: Returns empty string if encryption is not available.

    Args:
        key: The API key to encrypt
        fernet: Fernet encryptor instance (may be None)

    Returns:
        Encrypted key as string, or empty string if encryption failed
    """
    if not key:
        return ""
    if fernet is None:
        logger.warning(
            "cannot_encrypt_api_key", message="BRAIN_SETTINGS_ENCRYPTION_KEY not set"
        )
        return ""
    try:
        return fernet.encrypt(key.encode()).decode()
    except Exception as e:
        logger.error(
            "failed_to_encrypt_api_key", error=str(e), error_type=type(e).__name__
        )
        return ""


def decrypt_api_key(encrypted: str, fernet: Fernet | None) -> str:
    """
    Decrypt an API key.

    OPT-014: Returns empty string if decryption fails or encryption not available.

    Args:
        encrypted: The encrypted API key
        fernet: Fernet encryptor instance (may be None)

    Returns:
        Decrypted key as string, or empty string if decryption failed
    """
    if not encrypted:
        return ""
    if fernet is None:
        logger.warning(
            "cannot_decrypt_api_key", message="BRAIN_SETTINGS_ENCRYPTION_KEY not set"
        )
        return ""
    try:
        return fernet.decrypt(encrypted.encode()).decode()
    except Exception as e:
        logger.error(
            "failed_to_decrypt_api_key", error=str(e), error_type=type(e).__name__
        )
        return ""


def mask_api_key(key: str) -> str:
    """Mask an API key for display (show first 8 and last 4 chars)."""
    if not key or len(key) < 12:
        return "•" * 20 if key else ""
    return f"{key[:8]}{'•' * (len(key) - 12)}{key[-4:]}"


def require_encryption(fernet: Fernet | None) -> None:
    """
    Raise HTTPException if encryption is not available.

    OPT-014: Security hardening helper.

    Args:
        fernet: Fernet encryptor instance (may be None)

    Raises:
        HTTPException: 503 Service Unavailable if encryption key is not set
    """
    from fastapi import HTTPException

    if fernet is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "API key storage is not available. "
                "Please set BRAIN_SETTINGS_ENCRYPTION_KEY environment variable. "
                "Generate a key with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            ),
        )


__all__ = [
    "get_encryption_key",
    "get_fernet",
    "encrypt_api_key",
    "decrypt_api_key",
    "mask_api_key",
    "require_encryption",
]
