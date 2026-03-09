#!/usr/bin/env python3
"""
Unit tests for KnowledgeEntry Aggregate Root

Comprehensive test suite for the KnowledgeEntry domain model including:
- Creation and validation
- Content management
- Access control integration
"""

import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

# Mock problematic dependencies
sys.modules["aioredis"] = MagicMock()

from src.contexts.knowledge.domain.models.access_control_rule import AccessControlRule
from src.contexts.knowledge.domain.models.access_level import AccessLevel
from src.contexts.knowledge.domain.models.agent_identity import AgentIdentity
from src.contexts.knowledge.domain.models.knowledge_entry import (
    KnowledgeEntry,
    _normalize_timestamp,
    _validate_content,
)
from src.contexts.knowledge.domain.models.knowledge_type import KnowledgeType


class TestNormalizeTimestamp:
    """Test suite for _normalize_timestamp helper function."""

    def test_normalize_naive_datetime(self):
        """Test that naive datetime gets UTC timezone."""
        naive_dt = datetime(2024, 1, 15, 10, 30, 0)
        result = _normalize_timestamp(naive_dt)

        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc

    def test_normalize_aware_datetime(self):
        """Test that aware datetime is converted to UTC."""
        from datetime import timedelta as td

        # Create datetime with different timezone
        tz_plus_5 = timezone(td(hours=5))
        aware_dt = datetime(2024, 1, 15, 15, 30, 0, tzinfo=tz_plus_5)
        result = _normalize_timestamp(aware_dt)

        assert result.tzinfo == timezone.utc

    def test_normalize_already_utc(self):
        """Test that UTC datetime stays as UTC."""
        utc_dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = _normalize_timestamp(utc_dt)

        assert result == utc_dt
        assert result.tzinfo == timezone.utc


class TestValidateContent:
    """Test suite for _validate_content helper function."""

    def test_valid_content(self):
        """Test that valid content is returned unchanged."""
        content = "Valid content"
        result = _validate_content(content)
        assert result == content

    def test_valid_content_with_whitespace(self):
        """Test that content with whitespace is returned."""
        content = "  Valid content with whitespace  "
        result = _validate_content(content)
        assert result == content

    def test_empty_string_raises_error(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            _validate_content("")
        assert "Content cannot be empty" in str(exc_info.value)

    def test_whitespace_only_raises_error(self):
        """Test that whitespace-only string raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            _validate_content("   ")
        assert "Content cannot be empty" in str(exc_info.value)

    def test_none_raises_error(self):
        """Test that None raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            _validate_content(None)
        assert "Content cannot be empty" in str(exc_info.value)


class TestKnowledgeEntry:
    """Test suite for KnowledgeEntry aggregate root."""

    @pytest.fixture
    def sample_access_control(self):
        """Create sample access control rule."""
        return AccessControlRule(
            access_level=AccessLevel.PUBLIC,
        )

    @pytest.fixture
    def valid_entry_data(self, sample_access_control):
        """Create valid data for KnowledgeEntry."""
        now = datetime.now(timezone.utc)
        return {
            "id": "entry_123",
            "content": "Test knowledge content",
            "knowledge_type": KnowledgeType.PROFILE,
            "owning_character_id": "char_456",
            "access_control": sample_access_control,
            "created_at": now,
            "updated_at": now,
            "created_by": "user_123",
        }

    def test_knowledge_entry_creation_success(self, valid_entry_data):
        """Test successful KnowledgeEntry creation."""
        entry = KnowledgeEntry(**valid_entry_data)

        assert entry.id == "entry_123"
        assert entry.content == "Test knowledge content"
        assert entry.knowledge_type == KnowledgeType.PROFILE
        assert entry.owning_character_id == "char_456"
        assert entry.created_by == "user_123"

    def test_knowledge_entry_creation_optional_character_id(self, valid_entry_data):
        """Test creation with optional owning_character_id as None."""
        valid_entry_data["owning_character_id"] = None
        entry = KnowledgeEntry(**valid_entry_data)

        assert entry.owning_character_id is None

    def test_knowledge_entry_creation_strips_content(self, valid_entry_data):
        """Test that content is stripped during creation."""
        valid_entry_data["content"] = "  Content with whitespace  "
        entry = KnowledgeEntry(**valid_entry_data)

        assert entry.content == "Content with whitespace"

    def test_knowledge_entry_empty_id_raises_error(self, valid_entry_data):
        """Test that empty ID raises ValueError."""
        valid_entry_data["id"] = ""
        with pytest.raises(ValueError) as exc_info:
            KnowledgeEntry(**valid_entry_data)
        assert "id is required" in str(exc_info.value)

    def test_knowledge_entry_invalid_knowledge_type_raises_error(self, valid_entry_data):
        """Test that invalid knowledge_type raises ValueError."""
        valid_entry_data["knowledge_type"] = "invalid_type"
        with pytest.raises(ValueError) as exc_info:
            KnowledgeEntry(**valid_entry_data)
        assert "knowledge_type must be a KnowledgeType" in str(exc_info.value)

    def test_knowledge_entry_empty_created_by_raises_error(self, valid_entry_data):
        """Test that empty created_by raises ValueError."""
        valid_entry_data["created_by"] = ""
        with pytest.raises(ValueError) as exc_info:
            KnowledgeEntry(**valid_entry_data)
        assert "created_by is required" in str(exc_info.value)

    def test_knowledge_entry_updated_before_created_raises_error(self, valid_entry_data):
        """Test that updated_at before created_at raises ValueError."""
        now = datetime.now(timezone.utc)
        valid_entry_data["created_at"] = now
        valid_entry_data["updated_at"] = now - timedelta(hours=1)
        with pytest.raises(ValueError) as exc_info:
            KnowledgeEntry(**valid_entry_data)
        assert "updated_at cannot be earlier than created_at" in str(exc_info.value)

    def test_knowledge_entry_normalizes_timestamps(self, valid_entry_data):
        """Test that timestamps are normalized to UTC."""
        # Create naive datetime
        naive_dt = datetime(2024, 1, 15, 10, 30, 0)
        valid_entry_data["created_at"] = naive_dt
        valid_entry_data["updated_at"] = naive_dt

        entry = KnowledgeEntry(**valid_entry_data)

        assert entry.created_at.tzinfo == timezone.utc
        assert entry.updated_at.tzinfo == timezone.utc

    def test_update_content_success(self, valid_entry_data):
        """Test successful content update."""
        entry = KnowledgeEntry(**valid_entry_data)

        with patch(
            "src.contexts.knowledge.domain.models.knowledge_entry.datetime"
        ) as mock_datetime:
            new_time = datetime(2024, 1, 16, 12, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = new_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            event = entry.update_content("New content", "user_456")

        assert entry.content == "New content"
        assert entry.updated_at > entry.created_at
        assert event.entry_id == "entry_123"
        assert event.updated_by == "user_456"

    def test_update_content_empty_raises_error(self, valid_entry_data):
        """Test that empty content update raises ValueError."""
        entry = KnowledgeEntry(**valid_entry_data)

        with pytest.raises(ValueError) as exc_info:
            entry.update_content("", "user_456")
        assert "Content cannot be empty" in str(exc_info.value)

    def test_update_content_empty_updater_raises_error(self, valid_entry_data):
        """Test that empty updater raises ValueError."""
        entry = KnowledgeEntry(**valid_entry_data)

        with pytest.raises(ValueError) as exc_info:
            entry.update_content("New content", "")
        assert "updated_by is required" in str(exc_info.value)

    def test_update_content_timestamp_ensures_order(self, valid_entry_data):
        """Test that timestamp is adjusted to ensure ordering."""
        now = datetime.now(timezone.utc)
        valid_entry_data["created_at"] = now
        valid_entry_data["updated_at"] = now
        entry = KnowledgeEntry(**valid_entry_data)

        # Try to update with timestamp that's not later than current
        event = entry.update_content("New content", "user_456")

        # Updated_at should be later than or equal to previous updated_at
        assert entry.updated_at >= now
        assert event.timestamp == entry.updated_at

    def test_is_accessible_by_delegates_to_access_control(self, valid_entry_data):
        """Test that is_accessible_by delegates to access control rule."""
        entry = KnowledgeEntry(**valid_entry_data)
        agent = AgentIdentity(character_id="char_123")

        # Public access should return True
        result = entry.is_accessible_by(agent)

        assert result is True

    def test_is_accessible_by_with_role_based(self, valid_entry_data):
        """Test access check with role-based control."""
        valid_entry_data["access_control"] = AccessControlRule(
            access_level=AccessLevel.ROLE_BASED,
            allowed_roles=("narrator",),
        )
        entry = KnowledgeEntry(**valid_entry_data)

        # Agent with narrator role should have access
        agent_with_role = AgentIdentity(
            character_id="char_123",
            roles=("narrator",),
        )
        assert entry.is_accessible_by(agent_with_role) is True

        # Agent without narrator role should not have access
        agent_without_role = AgentIdentity(
            character_id="char_456",
            roles=("player",),
        )
        assert entry.is_accessible_by(agent_without_role) is False


class TestKnowledgeType:
    """Test KnowledgeType enum."""

    def test_knowledge_type_values(self):
        """Test that enum has correct values."""
        assert KnowledgeType.PROFILE.value == "profile"
        assert KnowledgeType.OBJECTIVE.value == "objective"
        assert KnowledgeType.MEMORY.value == "memory"
        assert KnowledgeType.LORE.value == "lore"
        assert KnowledgeType.RULES.value == "rules"

    def test_knowledge_type_comparison(self):
        """Test enum comparison."""
        assert KnowledgeType.PROFILE == "profile"
        assert KnowledgeType.MEMORY == "memory"
