"""Tests for domain exceptions.

This module contains comprehensive tests for the domain exception hierarchy,
ensuring proper exception behavior and message formatting.
"""

from __future__ import annotations

import pytest

from src.shared.domain.exceptions import (
    BusinessRuleException,
    ConcurrencyException,
    DomainException,
    DuplicateEntityException,
    EntityNotFoundException,
    ValidationException,
)


class TestDomainException:
    """Test cases for base DomainException."""

    def test_exception_creation(self) -> None:
        """Test basic exception creation."""
        exc = DomainException("Something went wrong")

        assert exc.message == "Something went wrong"
        assert exc.code == "DOMAIN_ERROR"

    def test_exception_creation_with_code(self) -> None:
        """Test exception creation with custom code."""
        exc = DomainException("Error", code="CUSTOM_001")

        assert exc.code == "CUSTOM_001"

    def test_exception_str_with_code(self) -> None:
        """Test string representation includes code."""
        exc = DomainException("Error", code="TEST_001")

        assert "[TEST_001]" in str(exc)
        assert "Error" in str(exc)

    def test_exception_str_without_code(self) -> None:
        """Test string representation without code."""
        exc = DomainException("Error message")

        assert str(exc) == "Error message"

    def test_exception_repr(self) -> None:
        """Test repr representation."""
        exc = DomainException("Error", code="TEST_001")

        assert "DomainException" in repr(exc)
        assert "Error" in repr(exc)

    def test_exception_is_catchable(self) -> None:
        """Test that exception can be caught."""
        with pytest.raises(DomainException):
            raise DomainException("Test error")

    def test_exception_is_base_class(self) -> None:
        """Test that all domain exceptions inherit from DomainException."""
        exceptions = [
            ValidationException("test"),
            BusinessRuleException("test"),
            EntityNotFoundException("User", "123"),
            ConcurrencyException("Order", "456", 1, 2),
            DuplicateEntityException("User", "user@example.com"),
        ]

        for exc in exceptions:
            assert isinstance(exc, DomainException)


class TestValidationException:
    """Test cases for ValidationException."""

    def test_validation_exception_creation(self) -> None:
        """Test validation exception creation."""
        exc = ValidationException("Invalid input")

        assert exc.message == "Invalid input"
        assert exc.code == "VALIDATION_ERROR"
        assert exc.field is None

    def test_validation_exception_with_field(self) -> None:
        """Test validation exception with field."""
        exc = ValidationException("Required", field="email", code="VAL_001")

        assert exc.field == "email"
        assert "(field: email)" in str(exc)

    def test_validation_exception_default_code(self) -> None:
        """Test default error code."""
        exc = ValidationException("Error")

        assert exc.code == "VALIDATION_ERROR"


class TestBusinessRuleException:
    """Test cases for BusinessRuleException."""

    def test_business_rule_exception_creation(self) -> None:
        """Test business rule exception creation."""
        exc = BusinessRuleException("Rule violated")

        assert exc.message == "Rule violated"
        assert exc.code == "BUSINESS_RULE_VIOLATION"
        assert exc.rule_name is None

    def test_business_rule_exception_with_rule_name(self) -> None:
        """Test business rule exception with rule name."""
        exc = BusinessRuleException(
            "Cannot publish without chapters",
            rule_name="PUBLISH_REQUIREMENT",
            code="RULE_001",
        )

        assert exc.rule_name == "PUBLISH_REQUIREMENT"
        assert "(rule: PUBLISH_REQUIREMENT)" in str(exc)


class TestEntityNotFoundException:
    """Test cases for EntityNotFoundException."""

    def test_not_found_exception_creation(self) -> None:
        """Test not found exception creation."""
        exc = EntityNotFoundException("User", "123-456")

        assert exc.entity_type == "User"
        assert exc.entity_id == "123-456"
        assert "User with id 123-456 not found" in exc.message

    def test_not_found_exception_default_code(self) -> None:
        """Test default error code."""
        exc = EntityNotFoundException("Novel", "789")

        assert exc.code == "ENTITY_NOT_FOUND"


class TestConcurrencyException:
    """Test cases for ConcurrencyException."""

    def test_concurrency_exception_creation(self) -> None:
        """Test concurrency exception creation."""
        exc = ConcurrencyException("Order", "123", expected_version=5, actual_version=6)

        assert exc.entity_type == "Order"
        assert exc.entity_id == "123"
        assert exc.expected_version == 5
        assert exc.actual_version == 6
        assert "Expected version 5, but found 6" in exc.message

    def test_concurrency_exception_default_code(self) -> None:
        """Test default error code."""
        exc = ConcurrencyException("User", "456", 1, 2)

        assert exc.code == "CONCURRENCY_CONFLICT"


class TestDuplicateEntityException:
    """Test cases for DuplicateEntityException."""

    def test_duplicate_exception_creation(self) -> None:
        """Test duplicate exception creation."""
        exc = DuplicateEntityException("User", "user@example.com")

        assert exc.entity_type == "User"
        assert exc.identifier == "user@example.com"
        assert "User with identifier 'user@example.com' already exists" in exc.message

    def test_duplicate_exception_default_code(self) -> None:
        """Test default error code."""
        exc = DuplicateEntityException("Novel", "My Novel")

        assert exc.code == "DUPLICATE_ENTITY"


class TestExceptionHierarchy:
    """Test cases for exception hierarchy behavior."""

    def test_catch_all_domain_exceptions(self) -> None:
        """Test that all exceptions can be caught as DomainException."""
        exceptions = [
            ValidationException("validation error"),
            BusinessRuleException("business error"),
            EntityNotFoundException("User", "123"),
        ]

        for exc in exceptions:
            with pytest.raises(DomainException):
                raise exc

    def test_specific_exception_not_caught_by_other_types(self) -> None:
        """Test that specific exceptions aren't caught by unrelated types."""
        with pytest.raises(ValidationException):
            try:
                raise ValidationException("test")
            except BusinessRuleException:
                pytest.fail("Should not catch ValidationException")

    def test_exception_message_inheritance(self) -> None:
        """Test that message attribute is properly inherited."""
        exc = ValidationException("Test message")

        # All exceptions should have message attribute
        assert hasattr(exc, "message")
        assert hasattr(exc, "code")

    def test_exception_is_value_error(self) -> None:
        """Test that DomainException is an Exception."""
        exc = DomainException("test")

        assert isinstance(exc, Exception)
        assert not isinstance(exc, ValueError)  # It's not a ValueError
