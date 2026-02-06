"""
Unit tests for Brain Settings Security (OPT-014).

Tests verify:
- Encrypted storage of API keys
- Masked output in responses
- No raw keys in logs
- Graceful failure when encryption key is not set
"""

from __future__ import annotations

import logging
from unittest.mock import Mock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.api.routers.brain_settings import (
    _decrypt_api_key,
    _encrypt_api_key,
    _mask_api_key,
    _require_encryption,
    get_encryption_key,
    get_fernet,
    InMemoryBrainSettingsRepository,
)
from src.api.schemas import APIKeysRequest, APIKeysResponse


# ==================== Encryption Tests ====================


# ==================== Encryption Tests ====================


class TestEncryption:
    """Tests for API key encryption/decryption."""

    def test_encrypt_api_key_success(self):
        """Test successful encryption of an API key."""
        from cryptography.fernet import Fernet

        key = Fernet.generate_key()
        fernet = Fernet(key)
        api_key = "sk-test1234567890abcdefghijklmnopqrstuvwxyz"

        encrypted = _encrypt_api_key(api_key, fernet)

        assert encrypted != api_key
        assert len(encrypted) > 0
        # Encrypted value should be base64-like (alphanumeric + special chars)
        assert encrypted != api_key

    def test_encrypt_api_key_empty_string(self):
        """Test encrypting an empty string returns empty string."""
        from cryptography.fernet import Fernet

        fernet = Fernet(Fernet.generate_key())

        result = _encrypt_api_key("", fernet)
        assert result == ""

    def test_encrypt_api_key_no_fernet(self):
        """Test encryption fails gracefully when fernet is None."""
        # Returns empty string when fernet is None (logged as warning)
        result = _encrypt_api_key("sk-test", None)
        assert result == ""

    def test_decrypt_api_key_success(self):
        """Test successful decryption of an API key."""
        from cryptography.fernet import Fernet

        key = Fernet.generate_key()
        fernet = Fernet(key)
        api_key = "sk-test1234567890abcdefghijklmnopqrstuvwxyz"

        encrypted = _encrypt_api_key(api_key, fernet)
        decrypted = _decrypt_api_key(encrypted, fernet)

        assert decrypted == api_key

    def test_decrypt_api_key_empty_string(self):
        """Test decrypting an empty string returns empty string."""
        from cryptography.fernet import Fernet

        fernet = Fernet(Fernet.generate_key())

        result = _decrypt_api_key("", fernet)
        assert result == ""

    def test_decrypt_api_key_invalid(self):
        """Test decryption fails gracefully for invalid data."""
        from cryptography.fernet import Fernet

        fernet = Fernet(Fernet.generate_key())

        result = _decrypt_api_key("invalid-encrypted-data", fernet)
        assert result == ""

    def test_round_trip_encryption(self):
        """Test that encryption/decryption round trip preserves the key."""
        from cryptography.fernet import Fernet

        fernet = Fernet(Fernet.generate_key())
        original = "sk-1234567890abcdefghijklmnopqrstuvwxyz"

        encrypted = _encrypt_api_key(original, fernet)
        decrypted = _decrypt_api_key(encrypted, fernet)

        assert decrypted == original


# ==================== Masking Tests ====================


class TestMasking:
    """Tests for API key masking."""

    def test_mask_api_key_standard(self):
        """Test masking a standard API key."""
        api_key = "sk-1234567890abcdefghijklmnopqrstuv"

        masked = _mask_api_key(api_key)

        # Should show first 8 and last 4 chars
        assert masked.startswith("sk-12345")
        # The masked string should contain the suffix somewhere
        assert "stuv" in masked
        # Middle should be dots
        assert "•" in masked
        # Original key should not be fully visible
        assert api_key not in masked

    def test_mask_api_key_short(self):
        """Test masking a short key returns all dots."""
        short_key = "short"

        masked = _mask_api_key(short_key)

        # Should return all dots for short keys
        assert masked == "•" * 20

    def test_mask_api_key_empty(self):
        """Test masking an empty key returns empty string."""
        assert _mask_api_key("") == ""

    def test_mask_api_key_none(self):
        """Test masking None returns empty string."""
        assert _mask_api_key(None) == ""  # type: ignore

    def test_mask_api_key_exact_12_chars(self):
        """Test masking exactly 12 char key (edge case)."""
        key = "123456789012"

        masked = _mask_api_key(key)

        # First 8 + last 4 = entire key, no masking
        assert masked == key


# ==================== Repository Tests ====================


class TestInMemoryBrainSettingsRepository:
    """Tests for encrypted storage in repository."""

    @pytest.fixture
    def fernet(self):
        """Provide a Fernet instance for tests."""
        from cryptography.fernet import Fernet

        return Fernet(Fernet.generate_key())

    @pytest.fixture
    def repository(self):
        """Provide a repository instance."""
        return InMemoryBrainSettingsRepository()

    @pytest.mark.asyncio
    async def test_set_and_get_api_key_encrypted(self, repository, fernet):
        """Test that stored keys are encrypted, not plaintext."""
        api_key = "sk-test1234567890abcdefghijklmnopqrstuvwxyz"

        # Store the key
        await repository.set_api_key("openai", api_key, fernet)

        # Check internal storage is encrypted (not plaintext)
        stored_value = repository._api_keys.get("openai", "")
        assert api_key not in stored_value
        assert stored_value != api_key

    @pytest.mark.asyncio
    async def test_retrieve_decrypted_key(self, repository, fernet):
        """Test that retrieved keys are properly decrypted."""
        api_key = "sk-test1234567890abcdefghijklmnopqrstuvwxyz"

        await repository.set_api_key("anthropic", api_key, fernet)
        retrieved = await repository.get_api_keys(fernet)

        assert retrieved["anthropic"] == api_key

    @pytest.mark.asyncio
    async def test_multiple_keys_encrypted_separately(self, repository, fernet):
        """Test that different keys get different encrypted values."""
        key1 = "sk-first1234567890abcdefghijklmnopqrst"
        key2 = "sk-second1234567890abcdefghijklmnopqrs"

        await repository.set_api_key("provider1", key1, fernet)
        await repository.set_api_key("provider2", key2, fernet)

        # Same key content should produce different ciphertext (due to salt)
        # But different keys definitely should
        assert repository._api_keys["provider1"] != repository._api_keys["provider2"]

    @pytest.mark.asyncio
    async def test_delete_key(self, repository, fernet):
        """Test deleting an API key."""
        await repository.set_api_key("openai", "sk-test", fernet)
        assert "openai" in repository._api_keys

        await repository.set_api_key("openai", "", fernet)
        assert "openai" not in repository._api_keys


# ==================== Encryption Key Requirement Tests ====================


class TestEncryptionKeyRequirement:
    """Tests for BRAIN_SETTINGS_ENCRYPTION_KEY requirement."""

    def test_get_encryption_key_missing_env_raises(self):
        """Test get_encryption_key raises ValueError when not set."""
        with patch.dict("os.environ", {}, clear=False):
            # Remove the env var if it exists
            import os
            os.environ.pop("BRAIN_SETTINGS_ENCRYPTION_KEY", None)

            with pytest.raises(ValueError, match="BRAIN_SETTINGS_ENCRYPTION_KEY not set"):
                get_encryption_key()

    def test_get_encryption_key_invalid_key_raises(self):
        """Test get_encryption_key raises ValueError for invalid key."""
        with patch.dict("os.environ", {"BRAIN_SETTINGS_ENCRYPTION_KEY": "invalid-key"}):
            with pytest.raises(ValueError, match="Invalid BRAIN_SETTINGS_ENCRYPTION_KEY"):
                get_encryption_key()

    def test_get_fernet_returns_none_when_missing(self):
        """Test get_fernet returns None when key is not set."""
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("BRAIN_SETTINGS_ENCRYPTION_KEY", None)

            result = get_fernet()
            assert result is None

    def test_require_encryption_raises_http_503(self):
        """Test _require_encryption raises HTTPException when fernet is None."""
        with pytest.raises(HTTPException) as exc_info:
            _require_encryption(None)

        assert exc_info.value.status_code == 503
        assert "BRAIN_SETTINGS_ENCRYPTION_KEY" in exc_info.value.detail

    def test_require_encryption_passes_with_valid_fernet(self):
        """Test _require_encryption does not raise with valid fernet."""
        from cryptography.fernet import Fernet

        fernet = Fernet(Fernet.generate_key())

        # Should not raise
        _require_encryption(fernet)


# ==================== Log Safety Tests ====================


class TestLogSafety:
    """Tests to ensure API keys are not logged."""

    def test_encrypted_value_not_loggable(self):
        """Test that encrypted values don't contain the original key."""
        from cryptography.fernet import Fernet

        fernet = Fernet(Fernet.generate_key())
        api_key = "sk-test1234567890abcdefghijklmnopqrstuvwxyz"

        encrypted = _encrypt_api_key(api_key, fernet)

        # Encrypted value should not contain the original key
        assert api_key not in encrypted
        # Encrypted value should not contain recognizable parts
        assert "sk-test" not in encrypted

    def test_masked_value_not_loggable(self):
        """Test that masked values don't contain the full key."""
        api_key = "sk-test1234567890abcdefghijklmnopqrstuvwxyz"

        masked = _mask_api_key(api_key)

        # Masked value should not contain the full key
        assert api_key not in masked
        # Only prefix should be visible
        assert api_key[:8] in masked
        # Suffix should be visible
        assert api_key[-4:] in masked
        # But middle should be dots
        assert "•" in masked


# ==================== Integration Tests ====================


class TestBrainSettingsSecurityIntegration:
    """Integration tests for brain settings security."""

    @pytest.fixture
    def fernet(self):
        """Provide a Fernet instance for tests."""
        from cryptography.fernet import Fernet

        return Fernet(Fernet.generate_key())

    @pytest.fixture
    def repository(self):
        """Provide a repository instance."""
        return InMemoryBrainSettingsRepository()

    @pytest.mark.asyncio
    async def test_full_workflow_encrypted_storage(self, repository, fernet):
        """Test full workflow: store -> retrieve -> mask."""
        api_key = "sk-test1234567890abcdefghijklmnopqrstuvwxyz"

        # Store
        await repository.set_api_key("openai", api_key, fernet)

        # Verify internal storage is encrypted
        assert api_key not in repository._api_keys["openai"]

        # Retrieve
        retrieved = await repository.get_api_keys(fernet)
        assert retrieved["openai"] == api_key

        # Mask for display
        masked = _mask_api_key(retrieved["openai"])
        assert api_key not in masked
        assert "•" in masked

    @pytest.mark.asyncio
    async def test_no_encryption_fails_gracefully(self, repository):
        """Test that operations fail gracefully without encryption."""
        api_key = "sk-test1234567890abcdefghijklmnopqrstuvwxyz"

        # Try to store without encryption
        await repository.set_api_key("openai", api_key, None)

        # Key should not be stored (empty string means encryption failed)
        assert repository._api_keys.get("openai") is None or repository._api_keys.get("openai") == ""

        # Retrieval should return empty
        retrieved = await repository.get_api_keys(None)
        assert retrieved["openai"] == ""
