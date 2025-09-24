#!/usr/bin/env python3
"""
Narrative Domain Type Safety Patterns

This module provides type safety utilities and patterns for the narrative domain,
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
    Protocol,
    Type,
    TypeVar,
    Union,
    cast,
)
from uuid import UUID

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from ..domain.aggregates.narrative_arc import NarrativeArc
    from ..domain.value_objects.narrative_id import NarrativeId

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


def ensure_decimal(value: Union[str, int, float, Decimal]) -> Decimal:
    """Type guard to ensure value is a Decimal."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


# Narrative Domain Type Safety Patterns
class NarrativeDomainTyping:
    """Type safety utilities for narrative domain operations."""

    @staticmethod
    def safe_enum_conversion(enum_class: Type[T], value: Union[str, T]) -> T:
        """Type-safe enum conversion with fallback."""
        if isinstance(value, enum_class):
            return value
        if isinstance(value, str):
            try:
                return enum_class(value)
            except ValueError:
                # Try by name if value lookup fails
                try:
                    return enum_class[value.upper()]
                except (KeyError, AttributeError):
                    raise ValueError(
                        f"Invalid {enum_class.__name__} value: {value}"
                    )
        raise TypeError(
            f"Cannot convert {type(value)} to {enum_class.__name__}"
        )

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
        items: Optional[List[Any]], converter_func
    ) -> List[Any]:
        """Type-safe list conversion with element transformation."""
        if items is None:
            return []
        return [converter_func(item) for item in items]

    @staticmethod
    def safe_dict_conversion(
        items: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Type-safe dictionary conversion."""
        if items is None:
            return {}
        return dict(items)


# Value Object Factory Patterns
class ValueObjectFactory:
    """Factory for creating value objects with type safety."""

    @staticmethod
    def create_plot_point_with_validation(
        plot_point_id: str,
        plot_point_type: str,
        importance: str,
        title: str,
        description: str,
        sequence_order: int,
        **kwargs,
    ):
        """Create PlotPoint with type validation and conversion."""
        from ..domain.value_objects.plot_point import (
            PlotPoint,
            PlotPointImportance,
            PlotPointType,
        )

        # Type-safe enum conversions
        safe_type = NarrativeDomainTyping.safe_enum_conversion(
            PlotPointType, plot_point_type
        )
        safe_importance = NarrativeDomainTyping.safe_enum_conversion(
            PlotPointImportance, importance
        )

        # Extract and convert optional parameters
        emotional_intensity = ensure_decimal(
            kwargs.get("emotional_intensity", Decimal("5.0"))
        )
        dramatic_tension = ensure_decimal(
            kwargs.get("dramatic_tension", Decimal("5.0"))
        )
        story_significance = ensure_decimal(
            kwargs.get("story_significance", Decimal("5.0"))
        )

        # Convert character sets
        involved_characters = set()
        if "involved_characters" in kwargs and kwargs["involved_characters"]:
            involved_characters = {
                ensure_uuid(cid) for cid in kwargs["involved_characters"]
            }

        # Convert event sets
        prerequisite_events = set(kwargs.get("prerequisite_events", []))
        consequence_events = set(kwargs.get("consequence_events", []))

        # Convert thematic relevance
        thematic_relevance = {}
        if "thematic_relevance" in kwargs and kwargs["thematic_relevance"]:
            thematic_relevance = {
                k: ensure_decimal(v)
                for k, v in kwargs["thematic_relevance"].items()
            }

        return PlotPoint(
            plot_point_id=plot_point_id,
            plot_point_type=safe_type,
            importance=safe_importance,
            title=title,
            description=description,
            sequence_order=sequence_order,
            emotional_intensity=emotional_intensity,
            dramatic_tension=dramatic_tension,
            story_significance=story_significance,
            involved_characters=involved_characters,
            prerequisite_events=prerequisite_events,
            consequence_events=consequence_events,
            location=kwargs.get("location"),
            time_context=kwargs.get("time_context"),
            pov_character=NarrativeDomainTyping.safe_uuid_conversion(
                kwargs.get("pov_character")
            ),
            outcome=kwargs.get("outcome"),
            conflict_type=kwargs.get("conflict_type"),
            thematic_relevance=thematic_relevance,
            tags=set(kwargs.get("tags", [])),
            notes=kwargs.get("notes", ""),
        )

    @staticmethod
    def create_narrative_theme_with_validation(
        theme_id: str,
        theme_type: str,
        intensity: str,
        name: str,
        description: str,
        **kwargs,
    ):
        """Create NarrativeTheme with type validation and conversion."""
        from ..domain.value_objects.narrative_theme import (
            NarrativeTheme,
            ThemeIntensity,
            ThemeType,
        )

        # Type-safe enum conversions
        safe_type = NarrativeDomainTyping.safe_enum_conversion(
            ThemeType, theme_type
        )
        safe_intensity = NarrativeDomainTyping.safe_enum_conversion(
            ThemeIntensity, intensity
        )

        # Convert decimal fields
        moral_complexity = ensure_decimal(
            kwargs.get("moral_complexity", Decimal("5.0"))
        )
        emotional_resonance = ensure_decimal(
            kwargs.get("emotional_resonance", Decimal("5.0"))
        )
        universal_appeal = ensure_decimal(
            kwargs.get("universal_appeal", Decimal("5.0"))
        )
        cultural_significance = ensure_decimal(
            kwargs.get("cultural_significance", Decimal("5.0"))
        )
        development_potential = ensure_decimal(
            kwargs.get("development_potential", Decimal("5.0"))
        )

        return NarrativeTheme(
            theme_id=theme_id,
            theme_type=safe_type,
            intensity=safe_intensity,
            name=name,
            description=description,
            moral_complexity=moral_complexity,
            emotional_resonance=emotional_resonance,
            universal_appeal=universal_appeal,
            cultural_significance=cultural_significance,
            development_potential=development_potential,
            symbolic_elements=set(kwargs.get("symbolic_elements", [])),
            introduction_sequence=kwargs.get("introduction_sequence"),
            resolution_sequence=kwargs.get("resolution_sequence"),
            tags=set(kwargs.get("tags", [])),
            notes=kwargs.get("notes", ""),
        )

    @staticmethod
    def create_story_pacing_with_validation(
        pacing_id: str,
        pacing_type: str,
        base_intensity: str,
        start_sequence: int,
        end_sequence: int,
        **kwargs,
    ):
        """Create StoryPacing with type validation and conversion."""
        from ..domain.value_objects.story_pacing import (
            PacingIntensity,
            PacingType,
            StoryPacing,
        )

        # Type-safe enum conversions
        safe_type = NarrativeDomainTyping.safe_enum_conversion(
            PacingType, pacing_type
        )
        safe_intensity = NarrativeDomainTyping.safe_enum_conversion(
            PacingIntensity, base_intensity
        )

        # Convert decimal fields with backwards compatibility
        event_density = ensure_decimal(
            kwargs.get("event_density", Decimal("5.0"))
        )
        dialogue_ratio = ensure_decimal(
            kwargs.get("dialogue_ratio", Decimal("0.3"))
        )
        action_ratio = ensure_decimal(
            kwargs.get("action_ratio", Decimal("0.4"))
        )
        reflection_ratio = ensure_decimal(
            kwargs.get("reflection_ratio", Decimal("0.3"))
        )

        # Handle legacy field mapping
        description_density = ensure_decimal(
            kwargs.get("description_density", Decimal("5.0"))
        )

        # Convert lists and sets
        tension_curve = [
            ensure_decimal(t) for t in kwargs.get("tension_curve", [])
        ]
        character_focus = set()
        if "character_focus" in kwargs and kwargs["character_focus"]:
            character_focus = {
                ensure_uuid(cid) for cid in kwargs["character_focus"]
            }

        narrative_techniques = set(kwargs.get("narrative_techniques", []))

        return StoryPacing(
            pacing_id=pacing_id,
            pacing_type=safe_type,
            base_intensity=safe_intensity,
            start_sequence=start_sequence,
            end_sequence=end_sequence,
            segment_name=kwargs.get("segment_name", ""),
            segment_description=kwargs.get("segment_description", ""),
            event_density=event_density,
            dialogue_ratio=dialogue_ratio,
            action_ratio=action_ratio,
            reflection_ratio=reflection_ratio,
            tension_curve=tension_curve,
            reader_engagement_target=kwargs.get(
                "reader_engagement_target", ""
            ),
            pacing_notes=kwargs.get("notes", ""),
            metadata=NarrativeDomainTyping.safe_dict_conversion(
                kwargs.get("metadata")
            ),
        )

    @staticmethod
    def create_narrative_context_with_validation(
        context_id: str,
        context_type: str,
        name: str,
        description: str,
        **kwargs,
    ):
        """Create NarrativeContext with type validation and conversion."""
        from ..domain.value_objects.narrative_context import (
            ContextScope,
            ContextType,
            NarrativeContext,
        )

        # Type-safe enum conversion
        safe_type = NarrativeDomainTyping.safe_enum_conversion(
            ContextType, context_type
        )
        safe_scope = NarrativeDomainTyping.safe_enum_conversion(
            ContextScope, kwargs.get("scope", "scene")
        )

        # Convert decimal fields
        importance = ensure_decimal(kwargs.get("importance", Decimal("5.0")))

        # Convert character sets
        affected_characters = set()
        if "affected_characters" in kwargs and kwargs["affected_characters"]:
            affected_characters = {
                ensure_uuid(cid) for cid in kwargs["affected_characters"]
            }

        # Convert location and theme sets
        locations = set(kwargs.get("locations", []))
        related_themes = set(kwargs.get("related_themes", []))

        # Handle parameter mapping for sequence ranges
        applies_from_sequence = kwargs.get("start_sequence") or kwargs.get(
            "applies_from_sequence"
        )
        applies_to_sequence = kwargs.get("end_sequence") or kwargs.get(
            "applies_to_sequence"
        )

        return NarrativeContext(
            context_id=context_id,
            context_type=safe_type,
            scope=safe_scope,
            name=name,
            description=description,
            applies_from_sequence=applies_from_sequence,
            applies_to_sequence=applies_to_sequence,
            is_persistent=kwargs.get("is_persistent", True),
            locations=locations,
            affected_characters=affected_characters,
            narrative_importance=importance,
            metadata=NarrativeDomainTyping.safe_dict_conversion(
                kwargs.get("metadata")
            ),
        )


# Repository Type Safety Patterns (following P3 Sprint 2)
class RepositoryHelpers:
    """Type-safe helpers for repository operations."""

    @staticmethod
    def safe_entity_conversion(entity_data: Any, target_type: Type[T]) -> T:
        """Type-safe entity conversion with validation."""
        if entity_data is None:
            raise ValueError(f"Cannot convert None to {target_type.__name__}")

        if isinstance(entity_data, target_type):
            return entity_data

        # Apply type conversion based on target type
        return cast(target_type, entity_data)

    @staticmethod
    def safe_session_operation(
        session: "Session", operation_func, *args, **kwargs
    ):
        """Type-safe session operation with error handling."""
        try:
            result = operation_func(session, *args, **kwargs)
            session.commit()
            return result
        except Exception as e:
            session.rollback()
            raise


# Domain Mapper Protocol (following P3 Sprint 2 patterns)
class DomainMapper(Protocol):
    """Protocol for type-safe domain mapping operations."""

    def entity_to_aggregate(self, entity: Any) -> "NarrativeArc":
        """Convert entity to domain aggregate."""
        ...

    def aggregate_to_entity(self, aggregate: "NarrativeArc") -> Any:
        """Convert domain aggregate to entity."""
        ...
