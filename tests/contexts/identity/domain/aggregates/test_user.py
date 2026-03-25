"""Tests for the User aggregate root.

This module contains comprehensive tests for the User domain aggregate,
covering authentication, role management, and account security.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

import pytest

from src.contexts.identity.domain.aggregates.user import User


@pytest.fixture
def valid_user() -> User:
    """Create a valid user for testing."""
    return User(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed_password_123",
    )


class TestUser:
    """Test cases for User aggregate root."""

    def test_create_user_with_valid_data(self) -> None:
        """Test user creation with valid data."""
        user = User(
            email="john@example.com",
            username="johndoe",
            hashed_password="hashed_pw_456",
            status="active",
            roles=["author", "reader"],
            profile={"bio": "A writer"},
            email_verified=True,
        )

        assert user.email == "john@example.com"
        assert user.username == "johndoe"
        assert user.hashed_password == "hashed_pw_456"
        assert user.status == "active"
        assert user.roles == ["author", "reader"]
        assert user.profile == {"bio": "A writer"}
        assert user.email_verified is True
        assert user.failed_login_attempts == 0
        assert user.locked_until is None
        assert isinstance(user.id, UUID)
        assert user.version == 0

    def test_create_user_with_minimal_data(self) -> None:
        """Test user creation with minimal required data."""
        user = User(
            email="jane@example.com",
            username="janedoe",
            hashed_password="hashed_pw",
        )

        assert user.status == "active"  # Default
        assert user.roles == []
        assert user.profile == {}
        assert user.email_verified is False
        assert user.last_login is None

    def test_create_with_invalid_email_raises_error(self) -> None:
        """Test that invalid email raises ValueError."""
        with pytest.raises(ValueError, match="Valid email required"):
            User(email="", username="user", hashed_password="pw")

        with pytest.raises(ValueError, match="Valid email required"):
            User(email="invalid-email", username="user", hashed_password="pw")

    def test_create_with_short_username_raises_error(self) -> None:
        """Test that username shorter than 3 characters raises ValueError."""
        with pytest.raises(ValueError, match="at least 3 characters"):
            User(email="test@example.com", username="ab", hashed_password="pw")

        with pytest.raises(ValueError, match="at least 3 characters"):
            User(email="test@example.com", username="", hashed_password="pw")

    def test_create_with_empty_password_raises_error(self) -> None:
        """Test that empty password hash raises ValueError."""
        with pytest.raises(ValueError, match="Password hash required"):
            User(email="test@example.com", username="user", hashed_password="")


class TestUserAccountLocking:
    """Test cases for account locking."""

    def test_is_locked_property_when_not_locked(self, valid_user: User) -> None:
        """Test is_locked property when account is not locked."""
        assert valid_user.is_locked is False

    def test_is_locked_property_when_locked(self, valid_user: User) -> None:
        """Test is_locked property when account is locked."""
        valid_user.locked_until = datetime.utcnow() + timedelta(hours=1)
        assert valid_user.is_locked is True

    def test_is_locked_property_after_lock_expires(self, valid_user: User) -> None:
        """Test is_locked property after lock expires."""
        valid_user.locked_until = datetime.utcnow() - timedelta(hours=1)
        assert valid_user.is_locked is False

    def test_is_active_property(self, valid_user: User) -> None:
        """Test is_active property."""
        # Active and not locked
        assert valid_user.is_active is True

        # Locked
        valid_user.locked_until = datetime.utcnow() + timedelta(hours=1)
        assert valid_user.is_active is False

        # Inactive status
        valid_user.locked_until = None
        valid_user.status = "inactive"
        assert valid_user.is_active is False


class TestUserLogin:
    """Test cases for login recording."""

    def test_record_successful_login(self, valid_user: User) -> None:
        """Test recording successful login."""
        valid_user.failed_login_attempts = 3
        valid_user.locked_until = datetime.utcnow() + timedelta(hours=1)

        valid_user.record_login(success=True)

        assert valid_user.last_login is not None
        assert valid_user.failed_login_attempts == 0
        assert valid_user.locked_until is None

    def test_record_failed_login(self, valid_user: User) -> None:
        """Test recording failed login."""
        valid_user.record_login(success=False)

        assert valid_user.failed_login_attempts == 1
        assert valid_user.locked_until is None

    def test_record_multiple_failed_logins(self, valid_user: User) -> None:
        """Test recording multiple failed logins."""
        for _ in range(4):
            valid_user.record_login(success=False)

        assert valid_user.failed_login_attempts == 4
        assert valid_user.locked_until is None

    def test_account_locks_after_five_failures(self, valid_user: User) -> None:
        """Test that account locks after 5 failed attempts."""
        for _ in range(5):
            valid_user.record_login(success=False)

        assert valid_user.failed_login_attempts == 5
        assert valid_user.locked_until is not None
        assert valid_user.locked_until > datetime.utcnow()

    def test_lock_duration_is_one_hour(self, valid_user: User) -> None:
        """Test that lock duration is 1 hour."""
        for _ in range(5):
            valid_user.record_login(success=False)

        expected_unlock = datetime.utcnow() + timedelta(seconds=3600)
        # Allow small time difference due to test execution time
        time_diff = abs((valid_user.locked_until - expected_unlock).total_seconds())
        assert time_diff < 5  # Within 5 seconds


class TestUserRoles:
    """Test cases for role management."""

    def test_add_role(self, valid_user: User) -> None:
        """Test adding a role."""
        valid_user.add_role("admin")

        assert "admin" in valid_user.roles
        assert len(valid_user.roles) == 1

    def test_add_multiple_roles(self, valid_user: User) -> None:
        """Test adding multiple roles."""
        valid_user.add_role("author")
        valid_user.add_role("moderator")

        assert "author" in valid_user.roles
        assert "moderator" in valid_user.roles
        assert len(valid_user.roles) == 2

    def test_add_duplicate_role_ignored(self, valid_user: User) -> None:
        """Test that adding duplicate role is ignored."""
        valid_user.add_role("author")
        valid_user.add_role("author")

        assert valid_user.roles.count("author") == 1
        assert len(valid_user.roles) == 1

    def test_remove_role(self, valid_user: User) -> None:
        """Test removing a role."""
        valid_user.add_role("admin")
        valid_user.add_role("author")

        valid_user.remove_role("admin")

        assert "admin" not in valid_user.roles
        assert "author" in valid_user.roles

    def test_remove_nonexistent_role_does_nothing(self, valid_user: User) -> None:
        """Test removing non-existent role does nothing."""
        valid_user.add_role("author")

        valid_user.remove_role("admin")

        assert "author" in valid_user.roles
        assert len(valid_user.roles) == 1

    def test_has_role(self, valid_user: User) -> None:
        """Test checking if user has a role."""
        valid_user.add_role("author")

        assert valid_user.has_role("author") is True
        assert valid_user.has_role("admin") is False


class TestUserPassword:
    """Test cases for password management."""

    def test_change_password(self, valid_user: User) -> None:
        """Test changing password."""
        old_password = valid_user.hashed_password

        valid_user.change_password("new_hashed_password")

        assert valid_user.hashed_password == "new_hashed_password"
        assert valid_user.hashed_password != old_password


class TestUserEmailVerification:
    """Test cases for email verification."""

    def test_verify_email(self, valid_user: User) -> None:
        """Test verifying email."""
        assert valid_user.email_verified is False

        valid_user.verify_email()

        assert valid_user.email_verified is True


class TestUserAccountStatus:
    """Test cases for account status management."""

    def test_deactivate(self, valid_user: User) -> None:
        """Test deactivating account."""
        valid_user.deactivate()

        assert valid_user.status == "inactive"
        assert valid_user.is_active is False

    def test_activate(self, valid_user: User) -> None:
        """Test activating account."""
        valid_user.status = "inactive"

        valid_user.activate()

        assert valid_user.status == "active"
        assert valid_user.is_active is True


class TestUserProfile:
    """Test cases for profile management."""

    def test_update_profile(self, valid_user: User) -> None:
        """Test updating profile fields."""
        valid_user.update_profile(bio="A writer", location="NYC")

        assert valid_user.profile["bio"] == "A writer"
        assert valid_user.profile["location"] == "NYC"

    def test_update_profile_overwrites_existing(self, valid_user: User) -> None:
        """Test that update overwrites existing profile fields."""
        valid_user.update_profile(bio="Old bio")
        valid_user.update_profile(bio="New bio")

        assert valid_user.profile["bio"] == "New bio"

    def test_update_profile_preserves_other_fields(self, valid_user: User) -> None:
        """Test that update preserves other profile fields."""
        valid_user.update_profile(bio="A writer")
        valid_user.update_profile(location="NYC")

        assert valid_user.profile["bio"] == "A writer"
        assert valid_user.profile["location"] == "NYC"


class TestUserSerialization:
    """Test cases for serialization."""

    def test_to_dict(self, valid_user: User) -> None:
        """Test converting to dictionary."""
        valid_user.add_role("author")
        valid_user.update_profile(bio="A writer")
        valid_user.verify_email()

        user_dict = valid_user.to_dict()

        assert user_dict["email"] == "test@example.com"
        assert user_dict["username"] == "testuser"
        assert user_dict["status"] == "active"
        assert user_dict["roles"] == ["author"]
        assert user_dict["profile"] == {"bio": "A writer"}
        assert user_dict["email_verified"] is True
        assert user_dict["last_login"] is None
        assert "id" in user_dict
        assert "created_at" in user_dict
        assert "updated_at" in user_dict
        # Should not include hashed_password
        assert "hashed_password" not in user_dict
        assert "_version" not in user_dict

    def test_to_dict_excludes_sensitive_data(self, valid_user: User) -> None:
        """Test that to_dict excludes sensitive fields."""
        user_dict = valid_user.to_dict()

        assert "hashed_password" not in user_dict
        assert "failed_login_attempts" not in user_dict
        assert "locked_until" not in user_dict


class TestUserInvariants:
    """Test cases for invariant validation."""

    def test_user_email_always_valid(self) -> None:
        """Test that user always has valid email."""
        user = User(
            email="valid@example.com",
            username="user",
            hashed_password="pw",
        )

        assert "@" in user.email

    def test_username_minimum_length(self) -> None:
        """Test that username always meets minimum length."""
        user = User(
            email="test@example.com",
            username="abc",
            hashed_password="pw",
        )

        assert len(user.username) >= 3

    def test_password_hash_never_empty(self) -> None:
        """Test that password hash is never empty."""
        user = User(
            email="test@example.com",
            username="user",
            hashed_password="some_hash",
        )

        assert user.hashed_password

    def test_user_equality(self) -> None:
        """Test user equality based on ID."""
        user1 = User(email="user1@example.com", username="user1", hashed_password="pw")
        user2 = User(email="user2@example.com", username="user2", hashed_password="pw")

        assert user1 != user2

    def test_user_hash(self) -> None:
        """Test user hash based on ID."""
        user1 = User(email="test1@example.com", username="user1", hashed_password="pw")
        user2 = User(email="test2@example.com", username="user2", hashed_password="pw")

        assert hash(user1) != hash(user2)
