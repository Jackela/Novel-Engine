#!/usr/bin/env python3
"""
Orchestration Domain Type Safety Patterns

This module provides type safety utilities and patterns for the orchestration domain,
following P3 Sprint 2 architectural patterns for systematic type safety.
"""

from datetime import datetime
from decimal import Decimal
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    TypeVar,
    Union,
    cast,
)
from uuid import UUID

if TYPE_CHECKING:
    from ..domain.entities.turn import Turn
    from ..domain.value_objects.turn_configuration import TurnConfiguration
    from ..domain.value_objects.turn_id import TurnId

T = TypeVar("T")
ValueObjectType = TypeVar("ValueObjectType")


# Type Guards for Runtime Safety
def ensure_not_none(value: Optional[T]) -> T:
    """Type guard to ensure value is not None."""
    if value is None:
        raise ValueError("Expected non-None value")
    return value


def ensure_uuid(value: Union[str, UUID]) -> UUID:
    """Type guard to ensure value is a UUID."""
    if isinstance(value, str):
        return UUID(value)
    return value


def ensure_list(value: Union[List[T], None]) -> List[T]:
    """Type guard to ensure value is a list."""
    if value is None:
        return []
    return value


def ensure_dict(value: Union[Dict[str, Any], None]) -> Dict[str, Any]:
    """Type guard to ensure value is a dict."""
    if value is None:
        return {}
    return value


# Orchestration Domain Type Safety Patterns
class OrchestrationDomainTyping:
    """Type safety utilities for orchestration domain operations."""

    @staticmethod
    def safe_enum_conversion(enum_class, value):
        """Type-safe enum conversion with fallback."""
        # Handle case where value is already correct enum type
        if hasattr(value, "__class__") and value.__class__ == enum_class:
            return value

        # Handle string to enum conversion
        if isinstance(value, str):
            try:
                # Try direct value lookup first
                if hasattr(enum_class, "__members__"):
                    for member in enum_class.__members__.values():
                        if hasattr(member, "value") and member.value == value:
                            return member

                # Try constructor with value
                return enum_class(value)
            except (ValueError, KeyError):
                try:
                    # Try by name lookup
                    if (
                        hasattr(enum_class, "__members__")
                        and value.upper() in enum_class.__members__
                    ):
                        return enum_class.__members__[value.upper()]
                except (KeyError, AttributeError):
                    pass
                raise ValueError(
                    f"Invalid {getattr(enum_class, '__name__', 'enum')} value: {value}"
                )

        # Return as-is if it seems to be the right type
        return value

    @staticmethod
    def safe_uuid_conversion(value: Union[str, UUID, None]) -> Optional[UUID]:
        """Type-safe UUID conversion."""
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        if isinstance(value, str):
            try:
                return UUID(value)
            except ValueError:
                raise ValueError(f"Invalid UUID format: {value}")
        raise TypeError(f"Cannot convert {type(value)} to UUID")

    @staticmethod
    def safe_list_conversion(
        items: Optional[List[Any]], converter_func=None
    ) -> List[Any]:
        """Type-safe list conversion with element transformation."""
        if items is None:
            return []
        if converter_func is None:
            return list(items)
        return [converter_func(item) for item in items]

    @staticmethod
    def safe_dict_conversion(
        items: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Type-safe dictionary conversion."""
        if items is None:
            return {}
        return dict(items)

    @staticmethod
    def safe_optional_list_parameter(
        items: Optional[List[Any]],
    ) -> Optional[List[Any]]:
        """Handle optional list parameters properly for PEP 484 compliance."""
        return items

    @staticmethod
    def enum_to_string_key(enum_value) -> str:
        """Convert enum value to string for use as dict key."""
        if hasattr(enum_value, "value"):
            return enum_value.value
        return str(enum_value)


# Value Object Factory Patterns
class ValueObjectFactory:
    """Factory for creating value objects with type safety."""

    @staticmethod
    def create_turn_configuration_with_validation(
        world_time_advance: int = 300,
        ai_integration_enabled: bool = True,
        narrative_analysis_depth: str = "standard",
        **kwargs,
    ):
        """Create TurnConfiguration with type validation and conversion."""
        from ..domain.value_objects.turn_configuration import TurnConfiguration

        # Handle optional list parameters properly
        participants: List[str] = ensure_list(kwargs.get("participants"))
        excluded_agents = set(kwargs.get("excluded_agents", []))
        required_agents = set(kwargs.get("required_agents", []))

        # Handle optional dict parameters
        phase_timeouts = ensure_dict(kwargs.get("phase_timeouts"))
        phase_enabled = ensure_dict(kwargs.get("phase_enabled"))
        ai_prompt_templates = ensure_dict(kwargs.get("ai_prompt_templates"))
        ai_model_preferences = ensure_dict(kwargs.get("ai_model_preferences"))
        world_constraints = ensure_dict(kwargs.get("world_constraints"))
        interaction_rules = ensure_dict(kwargs.get("interaction_rules"))
        performance_targets = ensure_dict(kwargs.get("performance_targets"))
        quality_thresholds = ensure_dict(kwargs.get("quality_thresholds"))
        metadata = ensure_dict(kwargs.get("metadata"))

        # Handle narrative themes list
        narrative_themes: List[str] = ensure_list(
            kwargs.get("narrative_themes")
        )

        # Handle optional Decimal fields
        max_ai_cost = kwargs.get("max_ai_cost")
        if max_ai_cost is not None and not isinstance(max_ai_cost, Decimal):
            max_ai_cost = Decimal(str(max_ai_cost))

        return TurnConfiguration(
            world_time_advance=world_time_advance,
            ai_integration_enabled=ai_integration_enabled,
            narrative_analysis_depth=narrative_analysis_depth,
            max_execution_time_ms=kwargs.get("max_execution_time_ms", 30000),
            rollback_enabled=kwargs.get("rollback_enabled", True),
            max_ai_cost=max_ai_cost,
            max_memory_usage_mb=kwargs.get("max_memory_usage_mb", 512),
            max_concurrent_operations=kwargs.get(
                "max_concurrent_operations", 10
            ),
            participants=participants,
            excluded_agents=excluded_agents,
            required_agents=required_agents,
            phase_timeouts=phase_timeouts,
            phase_enabled=phase_enabled,
            ai_prompt_templates=ai_prompt_templates,
            ai_model_preferences=ai_model_preferences,
            ai_temperature=kwargs.get("ai_temperature", 0.7),
            ai_max_tokens=kwargs.get("ai_max_tokens", 1000),
            world_constraints=world_constraints,
            allow_entity_creation=kwargs.get("allow_entity_creation", True),
            allow_entity_deletion=kwargs.get("allow_entity_deletion", False),
            allow_time_manipulation=kwargs.get(
                "allow_time_manipulation", True
            ),
            interaction_rules=interaction_rules,
            negotiation_timeout_seconds=kwargs.get(
                "negotiation_timeout_seconds", 300
            ),
            allow_multi_party_negotiations=kwargs.get(
                "allow_multi_party_negotiations", True
            ),
            require_consensus=kwargs.get("require_consensus", False),
            narrative_themes=narrative_themes,
            maintain_narrative_consistency=kwargs.get(
                "maintain_narrative_consistency", True
            ),
            generate_plot_summaries=kwargs.get(
                "generate_plot_summaries", True
            ),
            performance_targets=performance_targets,
            quality_thresholds=quality_thresholds,
            metadata=metadata,
        )

    @staticmethod
    def create_turn_id_with_validation(
        turn_uuid: Union[str, UUID, None] = None,
        sequence_number: Optional[int] = None,
        campaign_id: Union[str, UUID, None] = None,
        custom_name: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ):
        """Create TurnId with type validation and conversion."""
        from uuid import uuid4

        from ..domain.value_objects.turn_id import TurnId

        # Type-safe UUID conversion
        if turn_uuid is None:
            safe_uuid = uuid4()
        else:
            safe_uuid = ensure_uuid(turn_uuid)

        # Type-safe campaign ID conversion
        safe_campaign_id = OrchestrationDomainTyping.safe_uuid_conversion(
            campaign_id
        )

        # Validate sequence number if provided
        if sequence_number is not None:
            if not isinstance(sequence_number, int) or sequence_number < 1:
                raise ValueError("sequence_number must be a positive integer")

        # Validate custom name if provided
        if custom_name is not None:
            if not isinstance(custom_name, str):
                raise ValueError("custom_name must be a string")

            import re

            name_pattern = r"^[a-zA-Z0-9_-]{1,50}$"
            reserved_names = {
                "test",
                "debug",
                "system",
                "admin",
                "root",
                "api",
            }

            if not re.match(name_pattern, custom_name):
                raise ValueError(
                    "custom_name must contain only alphanumeric characters, "
                    "hyphens, and underscores (1-50 characters)"
                )

            if custom_name.lower() in reserved_names:
                raise ValueError(f"custom_name '{custom_name}' is reserved")

        # Set created_at if not provided
        if created_at is None:
            created_at = datetime.now()

        return TurnId(
            turn_uuid=safe_uuid,
            sequence_number=sequence_number,
            campaign_id=safe_campaign_id,
            custom_name=custom_name,
            created_at=created_at,
        )

    @staticmethod
    def create_phase_status_with_validation(
        phase_type,
        status,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        duration_ms: Optional[int] = None,
        progress_percentage: int = 0,
        events_processed: int = 0,
        error_message: Optional[str] = None,
        compensation_actions: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Create PhaseStatus with type validation and conversion."""
        from ..domain.value_objects.phase_status import (
            PhaseStatus,
            PhaseStatusEnum,
            PhaseType,
        )

        # Type-safe enum conversion
        safe_phase_type = OrchestrationDomainTyping.safe_enum_conversion(
            PhaseType, phase_type
        )
        safe_status = OrchestrationDomainTyping.safe_enum_conversion(
            PhaseStatusEnum, status
        )

        # Validate progress percentage
        if not 0 <= progress_percentage <= 100:
            raise ValueError("progress_percentage must be between 0 and 100")

        # Validate events processed
        if events_processed < 0:
            raise ValueError("events_processed cannot be negative")

        # Type-safe list and dict initialization
        safe_compensation_actions = ensure_list(compensation_actions)
        safe_metadata = ensure_dict(metadata)

        return PhaseStatus(
            phase_type=safe_phase_type,
            status=safe_status,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            progress_percentage=progress_percentage,
            events_processed=events_processed,
            error_message=error_message,
            compensation_actions=safe_compensation_actions,
            metadata=safe_metadata,
        )


# Interface Extension Patterns (P3 Sprint 2)
class InterfaceExtensions:
    """Extensions for missing interface methods and attributes."""

    @staticmethod
    def add_turn_configuration_extensions():
        """Add missing methods to TurnConfiguration class."""
        from ..domain.value_objects.turn_configuration import TurnConfiguration

        # Add missing attributes through property descriptors
        if not hasattr(TurnConfiguration, "fail_fast_on_phase_failure"):
            setattr(
                TurnConfiguration,
                "fail_fast_on_phase_failure",
                property(
                    lambda self: getattr(
                        self, "_fail_fast_on_phase_failure", True
                    )
                ),
            )

        if not hasattr(TurnConfiguration, "max_participants"):
            setattr(
                TurnConfiguration,
                "max_participants",
                property(
                    lambda self: getattr(
                        self, "_max_participants", len(self.participants) or 10
                    )
                ),
            )

        # Add missing from_dict class method
        if not hasattr(TurnConfiguration, "from_dict"):

            def create_from_dict(cls, data: Dict[str, Any]):
                """Create TurnConfiguration from dictionary."""
                return ValueObjectFactory.create_turn_configuration_with_validation(
                    **data
                )

            # Bind as classmethod
            setattr(
                TurnConfiguration, "from_dict", classmethod(create_from_dict)
            )

    @staticmethod
    def add_turn_id_extensions():
        """Add missing methods to TurnId class."""
        from ..domain.value_objects.turn_id import TurnId

        # Add missing parse class method
        if not hasattr(TurnId, "parse"):

            def create_parse_method(cls, turn_string: str):
                """Parse TurnId from string - alias for from_string."""
                return cls.from_string(turn_string)

            # Bind as classmethod
            setattr(TurnId, "parse", classmethod(create_parse_method))


# Repository Type Safety Patterns (following P3 Sprint 2)
class RepositoryHelpers:
    """Type-safe helpers for repository operations."""

    @staticmethod
    def safe_entity_conversion(entity_data: Any, target_type) -> Any:
        """Type-safe entity conversion with validation."""
        if entity_data is None:
            type_name = getattr(target_type, "__name__", "target type")
            raise ValueError(f"Cannot convert None to {type_name}")

        # Return as-is if already correct type
        if (
            hasattr(entity_data, "__class__")
            and entity_data.__class__ == target_type
        ):
            return entity_data

        # Apply type conversion with cast
        return cast(target_type, entity_data)


# Dataclass Validation Patterns
class DataclassValidationPatterns:
    """Patterns for fixing dataclass validation issues."""

    @staticmethod
    def safe_none_assignment_pattern(
        target_dict: Dict[str, Any], field_name: str, default_value: Any
    ) -> Any:
        """Safely handle None assignments to typed dataclass fields."""
        value = target_dict.get(field_name)
        if value is None:
            return default_value
        return value

    @staticmethod
    def safe_list_field_initialization(
        value: Optional[List[Any]],
    ) -> List[Any]:
        """Safely initialize list fields in dataclasses."""
        return value if value is not None else []

    @staticmethod
    def safe_dict_field_initialization(
        value: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Safely initialize dict fields in dataclasses."""
        return value if value is not None else {}


# Auto-initialization for Interface Extensions
def initialize_orchestration_extensions():
    """Initialize all interface extensions automatically."""
    InterfaceExtensions.add_turn_configuration_extensions()
    InterfaceExtensions.add_turn_id_extensions()


# Call initialization when module is imported
initialize_orchestration_extensions()
