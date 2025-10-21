#!/usr/bin/env python3
"""
Core Types Package.

This package contains shared type definitions used across the narrative engine
to avoid circular import issues and maintain type consistency.
"""

__version__ = "1.0.0"

import importlib.util
import os

# Export shared types from this package
from .shared_types import ActionPriority, ActionType

# Direct import from the types.py file
types_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "types.py")
spec = importlib.util.spec_from_file_location("core_types", types_path)
core_types = importlib.util.module_from_spec(spec)

try:
    spec.loader.exec_module(core_types)

    # Import all the types we need
    AgentID = core_types.AgentID
    MemoryID = core_types.MemoryID
    InteractionID = core_types.InteractionID
    ContextID = core_types.ContextID
    TemplateID = core_types.TemplateID
    EntityID = core_types.EntityID

    # Enums
    SystemPriority = core_types.SystemPriority
    ContextType = core_types.ContextType
    ProcessingStage = core_types.ProcessingStage
    ValidationLevel = core_types.ValidationLevel
    CacheStrategy = core_types.CacheStrategy
    LogLevel = core_types.LogLevel
    DatabaseOperation = core_types.DatabaseOperation
    TemplateType = core_types.TemplateType
    AIProvider = core_types.AIProvider
    InteractionScope = core_types.InteractionScope
    EventTrigger = core_types.EventTrigger

    # Value types
    TrustLevel = core_types.TrustLevel
    EmotionalWeight = core_types.EmotionalWeight
    RelevanceScore = core_types.RelevanceScore
    EffectivenessRating = core_types.EffectivenessRating

    # Collection types
    SacredMapping = core_types.SacredMapping
    BlessedList = core_types.BlessedList
    ContextData = core_types.ContextData

    # Result types
    ProcessingResult = core_types.ProcessingResult
    ValidationResult = core_types.ValidationResult
    ContextResult = core_types.ContextResult

    # Value types (additional)
    NumericValue = core_types.NumericValue
    TextValue = core_types.TextValue
    BlessedValue = core_types.BlessedValue

    # Time types
    BlessedTimestamp = core_types.BlessedTimestamp
    SacredDateTime = core_types.SacredDateTime

    # Literal types
    ThreatLevel = getattr(core_types, "ThreatLevel", str)
    MoodState = getattr(core_types, "MoodState", str)
    EquipmentState = getattr(core_types, "EquipmentState", str)
    RelationshipType = getattr(core_types, "RelationshipType", str)

    # Protocols
    BlessedSerializable = core_types.BlessedSerializable
    ContextProvider = core_types.ContextProvider
    MemoryStorable = core_types.MemoryStorable

    # Constants and validators
    SacredConstants = core_types.SacredConstants
    SacredTypeValidator = core_types.SacredTypeValidator

    # Validation functions
    is_valid_agent_id = core_types.is_valid_agent_id
    is_valid_trust_level = core_types.is_valid_trust_level
    is_valid_emotional_weight = core_types.is_valid_emotional_weight
    is_valid_relevance_score = core_types.is_valid_relevance_score

except Exception:
    # Fallback definitions for critical types
    AgentID = str
    MemoryID = str
    InteractionID = str
    ContextID = str
    TemplateID = str
    EntityID = str
    TrustLevel = int
    EmotionalWeight = float
    RelevanceScore = float
    EffectivenessRating = float

    # Fallback validation functions
    def is_valid_agent_id(value: str) -> bool:
        return isinstance(value, str) and 2 <= len(value) <= 100 and value.strip() != ""

    def is_valid_trust_level(value: int) -> bool:
        return isinstance(value, int) and 0 <= value <= 10

    def is_valid_emotional_weight(value: float) -> bool:
        return isinstance(value, (int, float)) and -10.0 <= float(value) <= 10.0

    def is_valid_relevance_score(value: float) -> bool:
        return isinstance(value, (int, float)) and 0.0 <= float(value) <= 1.0

__all__ = [
    # Core ID types
    "AgentID",
    "MemoryID",
    "InteractionID",
    "ContextID",
    "TemplateID",
    "EntityID",
    # Enums
    "SystemPriority",
    "ContextType",
    "ProcessingStage",
    "ValidationLevel",
    "CacheStrategy",
    "LogLevel",
    "DatabaseOperation",
    "TemplateType",
    "AIProvider",
    "InteractionScope",
    "EventTrigger",
    # From shared_types
    "ActionPriority",
    "ActionType",
    # Value types
    "TrustLevel",
    "EmotionalWeight",
    "RelevanceScore",
    "EffectivenessRating",
    "NumericValue",
    "TextValue",
    "BlessedValue",
    # Collection types
    "SacredMapping",
    "BlessedList",
    "ContextData",
    # Result types
    "ProcessingResult",
    "ValidationResult",
    "ContextResult",
    # Time types
    "BlessedTimestamp",
    "SacredDateTime",
    # Literal types
    "ThreatLevel",
    "MoodState",
    "EquipmentState",
    "RelationshipType",
    # Protocols
    "BlessedSerializable",
    "ContextProvider",
    "MemoryStorable",
    # Constants and validators
    "SacredConstants",
    "SacredTypeValidator",
    # Validation functions
    "is_valid_agent_id",
    "is_valid_trust_level",
    "is_valid_emotional_weight",
    "is_valid_relevance_score",
]
