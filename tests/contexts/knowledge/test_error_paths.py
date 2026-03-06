"""
Error Path Tests for Knowledge Context

Tests error handling, exception cases, and failure scenarios.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from src.core.result import Ok, Err, Error, NotFoundError, ValidationError
from src.contexts.knowledge.domain.models.knowledge_entry import KnowledgeEntry
from src.contexts.knowledge.domain.models.knowledge_type import KnowledgeType
from src.contexts.knowledge.domain.models.access_control_rule import AccessControlRule
from src.contexts.knowledge.domain.models.access_level import AccessLevel
from src.contexts.knowledge.domain.models.agent_identity import AgentIdentity
from src.contexts.knowledge.domain.models.token_usage import TokenUsage, TokenUsageStats


class TestKnowledgeEntryErrorPaths:
    """Error path tests for KnowledgeEntry."""

    def test_update_content_with_empty_string_raises(self):
        """Test that updating with empty content raises ValueError."""
        entry = KnowledgeEntry(
            id=str(uuid4()),
            content="Original content",
            knowledge_type=KnowledgeType.LORE,
            owning_character_id=None,
            access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="test_user",
        )
        
        with pytest.raises(ValueError, match="Content cannot be empty"):
            entry.update_content("", "updater")

    def test_update_content_with_empty_updater_raises(self):
        """Test that updating with empty updater raises ValueError."""
        entry = KnowledgeEntry(
            id=str(uuid4()),
            content="Original content",
            knowledge_type=KnowledgeType.LORE,
            owning_character_id=None,
            access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="test_user",
        )
        
        with pytest.raises(ValueError, match="updated_by is required"):
            entry.update_content("New content", "")


class TestResultTypeErrorPaths:
    """Error path tests for Result type usage."""

    def test_ok_result_is_error_returns_false(self):
        """Test that Ok result is not an error."""
        result = Ok("value")
        assert result.is_error is False
        assert result.is_ok is True

    def test_error_result_is_ok_returns_false(self):
        """Test that Error result is not ok."""
        result = Err(Error(code="TEST", message="Test error"))
        assert result.is_ok is False
        assert result.is_error is True

    def test_ok_result_accessing_error_raises(self):
        """Test that accessing error on Ok result raises ValueError."""
        result = Ok("value")
        with pytest.raises(ValueError, match="Cannot get error from Ok"):
            _ = result.error

    def test_error_result_accessing_value_raises(self):
        """Test that accessing value on Error result raises ValueError."""
        result = Err(Error(code="TEST", message="Test error"))
        with pytest.raises(ValueError, match="Cannot get value from Error"):
            _ = result.value

    def test_error_result_unwrap_returns_default(self):
        """Test that unwrap on Error result returns default."""
        result = Err(Error(code="TEST", message="Test error"))
        assert result.unwrap() is None
        assert result.unwrap(default="default") == "default"

    def test_ok_result_unwrap_returns_value(self):
        """Test that unwrap on Ok result returns value."""
        result = Ok("value")
        assert result.unwrap() == "value"

    def test_error_result_map_returns_self(self):
        """Test that map on Error result returns self."""
        error = Err(Error(code="TEST", message="Test error"))
        result = error.map(lambda x: x.upper())
        assert result.is_error

    def test_ok_result_and_then_chains(self):
        """Test that and_then on Ok result chains functions."""
        result = Ok(5).and_then(lambda x: Ok(x * 2))
        assert result.is_ok
        assert result.value == 10

    def test_error_result_and_then_returns_self(self):
        """Test that and_then on Error result returns self."""
        error = Err(Error(code="TEST", message="Test"))
        result = error.and_then(lambda x: Ok(x * 2))
        assert result.is_error

    def test_ok_result_or_else_returns_self(self):
        """Test that or_else on Ok result returns self."""
        result = Ok("value")
        chained = result.or_else(lambda e: Ok("recovered"))
        assert chained.is_ok
        assert chained.value == "value"

    def test_error_result_or_else_calls_handler(self):
        """Test that or_else on Error result calls handler."""
        error = Err(Error(code="TEST", message="Test"))
        result = error.or_else(lambda e: Ok("recovered"))
        assert result.is_ok
        assert result.value == "recovered"


class TestNotFoundError:
    """Tests for NotFoundError."""

    def test_not_found_error_properties(self):
        """Test NotFoundError has correct properties."""
        error = NotFoundError("Entity not found")
        assert error.code == "NOT_FOUND"
        assert error.recoverable is False
        assert "Entity not found" in error.message

    def test_not_found_error_with_details(self):
        """Test NotFoundError with details."""
        error = NotFoundError("Entity not found", details={"entity_id": "123"})
        assert error.details["entity_id"] == "123"

    def test_not_found_error_with_detail_method(self):
        """Test with_detail method on NotFoundError."""
        error = NotFoundError("Entity not found")
        new_error = error.with_detail("entity_id", "123")
        assert new_error.details["entity_id"] == "123"
        assert new_error.code == error.code  # Original unchanged


class TestValidationError:
    """Tests for ValidationError."""

    def test_validation_error_properties(self):
        """Test ValidationError has correct properties."""
        error = ValidationError("Invalid input")
        assert error.code == "VALIDATION_ERROR"
        assert error.recoverable is True

    def test_validation_error_with_field(self):
        """Test ValidationError with field."""
        error = ValidationError("Invalid value", field="email")
        assert error.details["field"] == "email"

    def test_validation_error_str(self):
        """Test ValidationError string representation."""
        error = ValidationError("Invalid input")
        assert "VALIDATION_ERROR" in str(error)
        assert "Invalid input" in str(error)


class TestTokenUsageErrorPaths:
    """Error path tests for TokenUsage."""

    def test_token_usage_from_dict_missing_fields(self):
        """Test creating TokenUsage from dict with missing fields."""
        data = {
            "id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": "openai",
            "model_name": "gpt-4",
            # Missing optional fields
        }
        usage = TokenUsage.from_dict(data)
        assert usage.input_tokens == 0  # Default value
        assert usage.output_tokens == 0

    def test_token_usage_to_dict_roundtrip(self):
        """Test TokenUsage to_dict and from_dict roundtrip."""
        original = TokenUsage.create(
            provider="openai",
            model_name="gpt-4",
            input_tokens=100,
            output_tokens=50,
        )
        data = original.to_dict()
        restored = TokenUsage.from_dict(data)
        
        assert restored.id == original.id
        assert restored.provider == original.provider
        assert restored.model_name == original.model_name
        assert restored.input_tokens == original.input_tokens

    def test_token_usage_cost_per_million_with_zero_tokens(self):
        """Test cost_per_million_tokens with zero tokens."""
        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4",
            input_tokens=0,
            output_tokens=0,
        )
        assert usage.cost_per_million_tokens == 0.0


class TestAccessControlErrorPaths:
    """Error path tests for AccessControlRule."""

    def test_access_control_empty_allowed_roles_raises(self):
        """Test that role-based with empty roles raises ValueError."""
        with pytest.raises(ValueError, match="requires at least one"):
            AccessControlRule(
                access_level=AccessLevel.ROLE_BASED,
                allowed_roles=(),
            )

    def test_access_control_empty_allowed_ids_raises(self):
        """Test that character-specific with empty IDs raises ValueError."""
        with pytest.raises(ValueError, match="requires at least one"):
            AccessControlRule(
                access_level=AccessLevel.CHARACTER_SPECIFIC,
                allowed_character_ids=(),
            )


class TestErrorEquality:
    """Tests for Error equality."""

    def test_error_equality_same_values(self):
        """Test that errors with same values are equal."""
        error1 = Error(code="TEST", message="Test")
        error2 = Error(code="TEST", message="Test")
        assert error1 == error2

    def test_error_equality_different_values(self):
        """Test that errors with different values are not equal."""
        error1 = Error(code="TEST", message="Test")
        error2 = Error(code="OTHER", message="Other")
        assert error1 != error2

    def test_error_equality_different_types(self):
        """Test that error is not equal to other types."""
        error = Error(code="TEST", message="Test")
        assert error != "TEST"
        assert error != 123


class TestOkEquality:
    """Tests for Ok result equality."""

    def test_ok_equality_same_values(self):
        """Test that Ok results with same values are equal."""
        ok1 = Ok("value")
        ok2 = Ok("value")
        assert ok1 == ok2

    def test_ok_equality_different_values(self):
        """Test that Ok results with different values are not equal."""
        ok1 = Ok("value1")
        ok2 = Ok("value2")
        assert ok1 != ok2

    def test_ok_not_equal_error(self):
        """Test that Ok is not equal to Error."""
        ok = Ok("value")
        error = Err(Error(code="TEST", message="Test"))
        assert ok != error


class TestErrorResultEquality:
    """Tests for Error result equality."""

    def test_error_result_equality_same_errors(self):
        """Test that Error results with same errors are equal."""
        err1 = Err(Error(code="TEST", message="Test"))
        err2 = Err(Error(code="TEST", message="Test"))
        assert err1 == err2

    def test_error_result_equality_different_errors(self):
        """Test that Error results with different errors are not equal."""
        err1 = Err(Error(code="TEST", message="Test"))
        err2 = Err(Error(code="OTHER", message="Other"))
        assert err1 != err2


class TestAgentIdentityErrorPaths:
    """Error path tests for AgentIdentity."""

    def test_agent_identity_empty_character_id_raises(self):
        """Test that empty character_id raises ValueError."""
        with pytest.raises(ValueError, match="character_id is required"):
            AgentIdentity(character_id="")

    def test_agent_identity_whitespace_character_id_behavior(self):
        """Test behavior of whitespace-only character_id."""
        # Note: The current implementation doesn't strip whitespace from character_id
        # It only normalizes roles. Test the actual behavior.
        agent = AgentIdentity(character_id="   ")
        # The character_id is preserved as-is (only validated for empty)
        assert agent.character_id == "   "
