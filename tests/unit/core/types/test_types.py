#!/usr/bin/env python3
"""
Unit tests for src/core/types.py module.

Tests cover:
- Enum classes and their values
- Protocol definitions
- Type aliases
- Validation functions
- Conversion utilities
- SacredConstants
- SacredTypeValidator
"""

from enum import IntEnum

import pytest

pytestmark = pytest.mark.unit

from src.core.types import (
    # Type aliases
    AgentID,
    AIProvider,
    BlessedList,
    # Protocols
    BlessedSerializable,
    BlessedTimestamp,
    CacheStrategy,
    ContextData,
    ContextID,
    ContextProvider,
    ContextType,
    DatabaseOperation,
    EffectivenessRating,
    EmotionalWeight,
    EquipmentState,
    EventTrigger,
    InteractionID,
    InteractionScope,
    LogLevel,
    MemoryID,
    MemoryStorable,
    MoodState,
    ProcessingStage,
    RelationshipType,
    RelevanceScore,
    # Constants
    SacredConstants,
    SacredDateTime,
    SacredMapping,
    # Validator
    SacredTypeValidator,
    # Enums
    SystemPriority,
    TemplateID,
    TemplateType,
    ThreatLevel,
    TrustLevel,
    ValidationLevel,
    # Validation functions
    is_valid_agent_id,
    is_valid_emotional_weight,
    is_valid_relevance_score,
    is_valid_trust_level,
)


class TestEnums:
    """Tests for enum class definitions."""

    def test_system_priority_values(self):
        """Test SystemPriority enum has correct values."""
        assert SystemPriority.LOWEST.value == 0
        assert SystemPriority.LOW.value == 1
        assert SystemPriority.NORMAL.value == 2
        assert SystemPriority.HIGH.value == 3
        assert SystemPriority.HIGHEST.value == 4
        assert SystemPriority.CRITICAL.value == 5

    def test_system_priority_is_intenum(self):
        """Test SystemPriority is an IntEnum."""
        assert issubclass(SystemPriority, IntEnum)
        assert SystemPriority.HIGH == 3
        assert SystemPriority.HIGH > SystemPriority.NORMAL

    def test_context_type_values(self):
        """Test ContextType enum values."""
        assert ContextType.CHARACTER.value == "character"
        assert ContextType.ENVIRONMENTAL.value == "environmental"
        assert ContextType.SOCIAL.value == "social"
        assert ContextType.TACTICAL.value == "tactical"
        assert ContextType.HISTORICAL.value == "historical"
        assert ContextType.EQUIPMENT.value == "equipment"
        assert ContextType.PSYCHOLOGICAL.value == "psychological"

    def test_processing_stage_values(self):
        """Test ProcessingStage enum values."""
        assert ProcessingStage.INITIALIZATION.value == "initialization"
        assert ProcessingStage.VALIDATION.value == "validation"
        assert ProcessingStage.PROCESSING.value == "processing"
        assert ProcessingStage.FINALIZATION.value == "finalization"
        assert ProcessingStage.ERROR_HANDLING.value == "error_handling"
        assert ProcessingStage.COMPLETION.value == "completion"

    def test_validation_level_values(self):
        """Test ValidationLevel enum values."""
        assert ValidationLevel.NONE.value == "none"
        assert ValidationLevel.BASIC.value == "basic"
        assert ValidationLevel.STANDARD.value == "standard"
        assert ValidationLevel.STRICT.value == "strict"
        assert ValidationLevel.PARANOID.value == "paranoid"

    def test_cache_strategy_values(self):
        """Test CacheStrategy enum values."""
        assert CacheStrategy.NO_CACHE.value == "no_cache"
        assert CacheStrategy.MEMORY_ONLY.value == "memory_only"
        assert CacheStrategy.PERSISTENT.value == "persistent"
        assert CacheStrategy.HYBRID.value == "hybrid"
        assert CacheStrategy.STANDARD_LRU.value == "standard_lru"

    def test_log_level_values(self):
        """Test LogLevel enum values."""
        assert LogLevel.TRACE.value == "trace"
        assert LogLevel.DEBUG.value == "debug"
        assert LogLevel.INFO.value == "info"
        assert LogLevel.WARNING.value == "warning"
        assert LogLevel.ERROR.value == "error"
        assert LogLevel.CRITICAL.value == "critical"
        assert LogLevel.STANDARD.value == "standard"

    def test_database_operation_values(self):
        """Test DatabaseOperation enum values."""
        assert DatabaseOperation.CREATE.value == "create"
        assert DatabaseOperation.READ.value == "read"
        assert DatabaseOperation.UPDATE.value == "update"
        assert DatabaseOperation.DELETE.value == "delete"
        assert DatabaseOperation.QUERY.value == "query"
        assert DatabaseOperation.BATCH_INSERT.value == "batch_insert"
        assert DatabaseOperation.TRANSACTION.value == "transaction"
        assert DatabaseOperation.STANDARD_BACKUP.value == "standard_backup"

    def test_template_type_values(self):
        """Test TemplateType enum values."""
        assert TemplateType.CHARACTER_SHEET.value == "character_sheet"
        assert TemplateType.MEMORY_ARCHIVE.value == "memory_archive"
        assert TemplateType.CONTEXT_SUMMARY.value == "context_summary"
        assert TemplateType.INTERACTION_LOG.value == "interaction_log"
        assert TemplateType.STATUS_REPORT.value == "status_report"
        assert TemplateType.NARRATIVE_SEGMENT.value == "narrative_segment"
        assert TemplateType.EQUIPMENT_MANIFEST.value == "equipment_manifest"

    def test_ai_provider_values(self):
        """Test AIProvider enum values."""
        assert AIProvider.GEMINI.value == "gemini"
        assert AIProvider.OPENAI.value == "openai"
        assert AIProvider.ANTHROPIC.value == "anthropic"
        assert AIProvider.LOCAL_LLM.value == "local_llm"
        assert AIProvider.ENHANCED_FALLBACK.value == "enhanced_fallback"

    def test_interaction_scope_values(self):
        """Test InteractionScope enum values."""
        assert InteractionScope.PERSONAL.value == "personal"
        assert InteractionScope.BILATERAL.value == "bilateral"
        assert InteractionScope.GROUP.value == "group"
        assert InteractionScope.ENVIRONMENTAL.value == "environmental"
        assert InteractionScope.SYSTEM.value == "system"

    def test_event_trigger_values(self):
        """Test EventTrigger enum values."""
        assert EventTrigger.TIME_BASED.value == "time_based"
        assert EventTrigger.CONDITION_BASED.value == "condition_based"
        assert EventTrigger.INTERACTION_BASED.value == "interaction_based"
        assert EventTrigger.THRESHOLD_BASED.value == "threshold_based"
        assert EventTrigger.MANUAL_TRIGGER.value == "manual_trigger"
        assert EventTrigger.STANDARD_AUTOMATED.value == "standard_automated"


class TestProtocols:
    """Tests for protocol definitions."""

    def test_blessed_serializable_is_runtime_checkable(self):
        """Test BlessedSerializable protocol is runtime checkable."""
        assert hasattr(BlessedSerializable, "to_dict")
        assert hasattr(BlessedSerializable, "from_dict")

    def test_context_provider_is_runtime_checkable(self):
        """Test ContextProvider protocol is runtime checkable."""
        assert hasattr(ContextProvider, "get_context_data")

    def test_memory_storable_is_runtime_checkable(self):
        """Test MemoryStorable protocol is runtime checkable."""
        assert hasattr(MemoryStorable, "get_memory_id")
        assert hasattr(MemoryStorable, "get_storage_data")

    def test_blessed_serializable_implementation(self):
        """Test BlessedSerializable protocol implementation check."""
        class GoodImpl:
            def to_dict(self) -> dict:
                return {}
            @classmethod
            def from_dict(cls, data: dict) -> "GoodImpl":
                return cls()

        assert isinstance(GoodImpl(), BlessedSerializable)

    def test_blessed_serializable_non_implementation(self):
        """Test non-implementing class fails protocol check."""
        class BadImpl:
            pass

        assert not isinstance(BadImpl(), BlessedSerializable)


class TestTypeAliases:
    """Tests for type alias definitions."""

    def test_id_types_are_str(self):
        """Test ID type aliases are strings."""
        assert AgentID is str
        assert MemoryID is str
        assert InteractionID is str
        assert ContextID is str
        assert TemplateID is str

    def test_trust_level_is_int(self):
        """Test TrustLevel is int."""
        assert TrustLevel is int

    def test_emotional_weight_is_float(self):
        """Test EmotionalWeight is float."""
        assert EmotionalWeight is float

    def test_relevance_score_is_float(self):
        """Test RelevanceScore is float."""
        assert RelevanceScore is float

    def test_effectiveness_rating_is_float(self):
        """Test EffectivenessRating is float."""
        assert EffectivenessRating is float

    def test_container_types(self):
        """Test container type aliases."""
        assert SacredMapping is dict
        assert BlessedList is list
        assert ContextData is dict

    def test_time_types(self):
        """Test time type aliases."""
        assert BlessedTimestamp is float
        assert SacredDateTime is str


class TestSacredConstants:
    """Tests for SacredConstants class."""

    def test_memory_constants(self):
        """Test memory-related constants."""
        assert SacredConstants.WORKING_MEMORY_CAPACITY == 7
        assert SacredConstants.MAX_MEMORY_ITEMS_PER_QUERY == 50
        assert SacredConstants.MEMORY_DECAY_RATE == 0.95

    def test_relationship_constants(self):
        """Test relationship-related constants."""
        assert SacredConstants.DEFAULT_TRUST_LEVEL == 5
        assert SacredConstants.MAX_TRUST_LEVEL == 10
        assert SacredConstants.RELATIONSHIP_TIMEOUT_DAYS == 30

    def test_performance_constants(self):
        """Test performance-related constants."""
        assert SacredConstants.MAX_CONTEXT_RENDER_TIME_MS == 300
        assert SacredConstants.MAX_MEMORY_QUERY_TIME_MS == 200
        assert SacredConstants.MAX_AI_RESPONSE_TIME_MS == 5000

    def test_database_constants(self):
        """Test database-related constants."""
        assert SacredConstants.MAX_BATCH_INSERT_SIZE == 1000
        assert SacredConstants.MAX_QUERY_RESULT_SIZE == 10000
        assert SacredConstants.CONNECTION_POOL_SIZE == 20

    def test_validation_constants(self):
        """Test validation-related constants."""
        assert SacredConstants.MIN_MEMORY_CONTENT_LENGTH == 10
        assert SacredConstants.MAX_MEMORY_CONTENT_LENGTH == 5000
        assert SacredConstants.MIN_AGENT_NAME_LENGTH == 2
        assert SacredConstants.MAX_AGENT_NAME_LENGTH == 100


class TestValidationFunctions:
    """Tests for validation functions."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("valid_agent", True),
            ("a" * 100, True),
            ("ab", True),
            ("a", False),
            ("a" * 101, False),
            ("", False),
            ("  ", False),
            (" valid ", True),
            (123, False),
            (None, False),
        ],
    )
    def test_is_valid_agent_id(self, value, expected):
        """Test is_valid_agent_id function."""
        assert is_valid_agent_id(value) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            (0, True),
            (5, True),
            (10, True),
            (-1, False),
            (11, False),
            (5.5, False),
            ("5", False),
            (None, False),
        ],
    )
    def test_is_valid_trust_level(self, value, expected):
        """Test is_valid_trust_level function."""
        assert is_valid_trust_level(value) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            (-10.0, True),
            (0.0, True),
            (10.0, True),
            (7.5, True),
            (-10.1, False),
            (10.1, False),
            (5, True),
            ("5", False),
            (None, False),
        ],
    )
    def test_is_valid_emotional_weight(self, value, expected):
        """Test is_valid_emotional_weight function."""
        assert is_valid_emotional_weight(value) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            (0.0, True),
            (0.5, True),
            (1.0, True),
            (-0.1, False),
            (1.1, False),
            (0, True),
            (1, True),
            ("0.5", False),
            (None, False),
        ],
    )
    def test_is_valid_relevance_score(self, value, expected):
        """Test is_valid_relevance_score function."""
        assert is_valid_relevance_score(value) == expected


class TestSacredTypeValidator:
    """Tests for SacredTypeValidator class."""

    def test_validate_type_with_correct_type(self):
        """Test validate_type with matching type."""
        assert SacredTypeValidator.validate_type("test", str) is True
        assert SacredTypeValidator.validate_type(123, int) is True
        assert SacredTypeValidator.validate_type(3.14, float) is True
        assert SacredTypeValidator.validate_type([1, 2, 3], list) is True
        assert SacredTypeValidator.validate_type({"a": 1}, dict) is True

    def test_validate_type_with_wrong_type(self):
        """Test validate_type with non-matching type."""
        assert SacredTypeValidator.validate_type("test", int) is False
        assert SacredTypeValidator.validate_type(123, str) is False
        assert SacredTypeValidator.validate_type(None, str) is False

    def test_validate_enum_with_enum_member(self):
        """Test validate_enum with actual enum member."""
        assert SacredTypeValidator.validate_enum(SystemPriority.HIGH, SystemPriority) is True
        assert SacredTypeValidator.validate_enum(ContextType.CHARACTER, ContextType) is True

    def test_validate_enum_with_value(self):
        """Test validate_enum with enum value."""
        assert SacredTypeValidator.validate_enum(3, SystemPriority) is True
        assert SacredTypeValidator.validate_enum("character", ContextType) is True

    def test_validate_enum_with_invalid_value(self):
        """Test validate_enum with invalid value."""
        assert SacredTypeValidator.validate_enum("invalid", ContextType) is False
        assert SacredTypeValidator.validate_enum(999, SystemPriority) is False

    def test_validate_enum_with_invalid_enum_class(self):
        """Test validate_enum with non-enum class."""
        result = SacredTypeValidator.validate_enum("test", str)
        assert isinstance(result, bool)

    def test_validate_protocol_with_implementation(self):
        """Test validate_protocol with implementing class."""
        class TestImpl:
            def to_dict(self) -> dict:
                return {}
            @classmethod
            def from_dict(cls, data: dict) -> "TestImpl":
                return cls()

        assert SacredTypeValidator.validate_protocol(TestImpl(), BlessedSerializable) is True

    def test_validate_protocol_with_non_implementation(self):
        """Test validate_protocol with non-implementing class."""
        class NonImpl:
            pass

        assert SacredTypeValidator.validate_protocol(NonImpl(), BlessedSerializable) is False


class TestLiteralTypes:
    """Tests for literal type definitions."""

    def test_threat_level_values(self):
        """Test ThreatLevel literal values."""
        assert ThreatLevel is not None

    def test_mood_state_values(self):
        """Test MoodState literal values."""
        assert MoodState is not None

    def test_equipment_state_values(self):
        """Test EquipmentState literal values."""
        assert EquipmentState is not None

    def test_relationship_type_values(self):
        """Test RelationshipType literal values."""
        assert RelationshipType is not None
