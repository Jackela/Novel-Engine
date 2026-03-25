"""Example: Testing with DI Container.

This module demonstrates best practices for testing code that uses
the DI container, including mocking and isolation techniques.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Depends

from src.contexts.identity.application.services.authentication_service import (
    AuthenticationService,
)
from src.shared.infrastructure.auth.jwt_utils import JWTManager
from src.shared.infrastructure.di import (
    get_container,
    reset_container,
    validate_container,
)


class TestWithDIContainer:
    """Example: Unit tests using DI container with mocks."""

    @pytest.fixture(autouse=True)
    def reset_di_container(self):
        """Reset DI container before each test."""
        reset_container()
        yield
        reset_container()

    @pytest.fixture
    def test_config(self) -> dict[str, Any]:
        """Provide test configuration."""
        return {
            "database": {
                "url": "postgresql://test:test@localhost/test_db",
                "max_connections": 5,
            },
            "security": {
                "secret_key": "test-secret-key-32-chars-long!!!",
                "algorithm": "HS256",
                "access_token_expire_minutes": 30,
                "refresh_token_expire_days": 7,
            },
            "honcho": {
                "base_url": "https://api.honcho.dev",
                "api_key": None,
            },
        }

    def test_container_validation(self, test_config: dict):
        """Test that container configuration is valid."""
        container = get_container()
        container.config.from_dict(test_config)

        results = validate_container(container)

        assert results["is_valid"] is True
        assert len(results["errors"]) == 0

    def test_jwt_manager_singleton(self, test_config: dict):
        """Test JWT manager is a singleton."""
        container = get_container()
        container.config.from_dict(test_config)

        jwt1 = container.core.jwt_manager()
        jwt2 = container.core.jwt_manager()

        # Should be the same instance
        assert jwt1 is jwt2
        assert isinstance(jwt1, JWTManager)


class TestWithMockedDependencies:
    """Example: Testing with mocked dependencies."""

    @pytest.fixture
    def mock_user_repository(self):
        """Create a mock user repository."""
        repo = MagicMock()
        repo.get_by_username = AsyncMock(return_value=None)
        repo.get_by_id = AsyncMock(return_value=None)
        repo.save = AsyncMock()
        return repo

    @pytest.fixture
    def mock_jwt_manager(self):
        """Create a mock JWT manager."""
        jwt = MagicMock()
        jwt.create_access_token = MagicMock(return_value="mock_access_token")
        jwt.create_refresh_token = MagicMock(return_value="mock_refresh_token")
        jwt.verify_token = MagicMock(return_value={"sub": "user-123"})
        return jwt

    async def test_authentication_service_with_mocks(
        self, mock_user_repository, mock_jwt_manager
    ):
        """Test authentication service with mocked dependencies."""
        # Create service with mocked dependencies
        auth_service = AuthenticationService(
            user_repository=mock_user_repository,
            jwt_manager=mock_jwt_manager,
        )

        # Configure mock
        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.hashed_password = b"hashed_password"
        mock_user.roles = ["user"]
        mock_user.is_locked = False
        mock_user.record_login = MagicMock()

        mock_user_repository.get_by_username.return_value = mock_user

        # Test authentication
        with patch.object(auth_service, "verify_password", return_value=True):
            result = await auth_service.authenticate_user(
                username="testuser",
                password="correct_password",
            )

        assert result.is_success
        assert "access_token" in result.value
        assert result.value["access_token"] == "mock_access_token"


class TestWithPatchedContainer:
    """Example: Patching container providers for integration tests."""

    def test_with_patched_database(self):
        """Test with patched database provider."""
        reset_container()
        container = get_container()

        # Configure container
        container.config.from_dict(
            {
                "database": {"url": "postgresql://test:test@localhost/test"},
                "security": {
                    "secret_key": "test-secret-key-32-chars-long!!!",
                    "algorithm": "HS256",
                },
            }
        )

        # Mock the database pool
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock()
        mock_pool.close = AsyncMock()

        # Patch the provider
        with patch.object(
            container.core.db_pool,
            "__call__",
            return_value=mock_pool,
        ):
            # Now when code requests db_pool, it gets our mock
            db_pool = container.core.db_pool()
            assert db_pool is mock_pool

        reset_container()


class TestFastAPIIntegration:
    """Example: Testing FastAPI endpoints with DI container."""

    @pytest.fixture
    def test_app(self):
        """Create test FastAPI application with DI."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from src.shared.infrastructure.di.providers import (
            get_authentication_service,
        )

        app = FastAPI()

        @app.get("/protected")
        async def protected_route(
            auth_service=Depends(get_authentication_service),
        ):
            return {"status": "ok"}

        return TestClient(app)

    def test_endpoint_with_container(self, test_app):
        """Test endpoint that uses DI container.

        Note: This test demonstrates the structure but would need
        proper mocking of the database to run successfully.
        """
        # Configure container for test
        reset_container()
        container = get_container()
        container.config.from_dict(
            {
                "database": {"url": "postgresql://test:test@localhost/test"},
                "security": {
                    "secret_key": "test-secret-key-32-chars-long!!!",
                    "algorithm": "HS256",
                },
            }
        )

        # In a real test, you would mock the authentication service
        # or the database pool to avoid needing a real database

        # response = test_app.get("/protected")
        # assert response.status_code == 200

        reset_container()


# Example: Running container validation in CI/CD
def validate_container_in_ci():
    """Validate container configuration for CI/CD pipeline.

    This function can be called in CI/CD to ensure container
    configuration is valid before deployment.
    """
    reset_container()
    container = get_container()

    # Load production-like configuration
    container.config.from_dict(
        {
            "database": {
                "url": "postgresql://user:pass@localhost/db",
                "max_connections": 20,
            },
            "security": {
                "secret_key": "prod-secret-key-32-chars-minimum!!",
                "algorithm": "HS256",
                "access_token_expire_minutes": 30,
            },
        }
    )

    # Validate
    results = validate_container(container, raise_on_error=True)

    print("Container validation passed!")
    print(f"Warnings: {len(results['warnings'])}")
    for warning in results["warnings"]:
        print(f"  - {warning}")

    reset_container()


if __name__ == "__main__":
    # Run container validation
    print("Validating DI container...")
    validate_container_in_ci()
    print("\nAll validations passed!")
