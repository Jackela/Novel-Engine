#!/usr/bin/env python3
"""
Character Context Models

This module implements Pydantic models for representing structured character
context data loaded from user-generated content files. These models provide
type safety, validation, and serialization for the Context Engineering Framework.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class TrustLevel(BaseModel):
    """Trust level measurement for relationships."""

    score: int = Field(..., ge=0, le=100, description="Trust score from 0-100")
    category: str = Field(..., description="Trust category (High/Medium/Low)")

    @field_validator("category", mode="before")
    @classmethod
    def categorize_trust(cls, v, info):
        # Access other fields through info.data in Pydantic V2
        data = info.data if hasattr(info, "data") else {}
        score = data.get("score", 0)
        if score >= 70:
            return "High"
        elif score >= 40:
            return "Medium"
        else:
            return "Low"


class MemoryType(str, Enum):
    """Types of character memories."""

    TRAUMATIC_CORE = "traumatic_core"
    FOUNDATIONAL_LEARNING = "foundational_learning"
    IDENTITY_FORMATION = "identity_formation"
    TRUST_VIOLATION = "trust_violation"
    ACHIEVEMENT_MILESTONE = "achievement_milestone"
    TRANSFORMATIONAL_ENCOUNTER = "transformational_encounter"
    STRATEGIC_EVOLUTION = "strategic_evolution"
    PERSPECTIVE_SHIFT = "perspective_shift"


class RelationshipType(str, Enum):
    """Types of character relationships."""

    MENTOR_PARTNER = "mentor_partner"
    STRATEGIC_PARTNER = "strategic_partner"
    PROFESSIONAL_RIVAL = "professional_rival"
    BUSINESS_CONTACT = "business_contact"
    PROFESSIONAL_BROTHERHOOD = "professional_brotherhood"
    PROFESSIONAL_NETWORK = "professional_network"


class FormativeEvent(BaseModel):
    """A formative event in character development."""

    age: int = Field(..., ge=0, le=200, description="Age when event occurred")
    event_name: str = Field(..., max_length=200, description="Name of the event")
    description: str = Field(..., description="Detailed event description")
    memory_type: MemoryType = Field(..., description="Classification of memory type")
    emotional_impact: str = Field(..., description="Emotional impact description")
    decision_influence: str = Field(..., description="How this influences decisions")
    trigger_phrases: List[str] = Field(
        default_factory=list, description="Phrases that trigger this memory"
    )
    key_lesson: Optional[str] = Field(None, description="Primary lesson learned")


class RelationshipMemory(BaseModel):
    """Memory data for a specific relationship."""

    character_name: str = Field(
        ..., max_length=100, description="Name of the related character"
    )
    relationship_type: RelationshipType = Field(..., description="Type of relationship")
    memory_foundation: str = Field(
        ..., description="How the relationship was established"
    )
    trust_level: TrustLevel = Field(..., description="Trust level measurement")
    emotional_dynamics: str = Field(..., description="Emotional relationship patterns")
    shared_experiences: List[str] = Field(
        default_factory=list, description="Key shared experiences"
    )
    conflict_points: List[str] = Field(
        default_factory=list, description="Sources of conflict"
    )
    alliance_strength: Optional[str] = Field(
        None, description="Strength assessment if allied"
    )


class BehavioralTrigger(BaseModel):
    """Behavioral pattern triggered by memories."""

    trigger_name: str = Field(..., max_length=100, description="Name of the trigger")
    memory_origin: str = Field(
        ..., description="Which memory/experience created this trigger"
    )
    trigger_conditions: List[str] = Field(
        ..., description="Conditions that activate trigger"
    )
    behavioral_response: str = Field(..., description="How character responds")
    override_conditions: List[str] = Field(
        default_factory=list, description="What can override this response"
    )


class MemoryContext(BaseModel):
    """Complete memory system for a character."""

    formative_events: List[FormativeEvent] = Field(
        default_factory=list, description="Major formative experiences"
    )
    relationships: List[RelationshipMemory] = Field(
        default_factory=list, description="Key relationship memories"
    )
    behavioral_triggers: List[BehavioralTrigger] = Field(
        default_factory=list, description="Memory-driven behaviors"
    )

    @field_validator("formative_events")
    @classmethod
    def validate_age_progression(cls, events):
        """Ensure events are chronologically reasonable."""
        if len(events) > 1:
            sorted_events = sorted(events, key=lambda x: x.age)
            for i in range(len(sorted_events) - 1):
                age_gap = sorted_events[i + 1].age - sorted_events[i].age
                if age_gap < 0:
                    raise ValueError("Formative events must have chronological ages")
        return events


class ObjectiveTier(str, Enum):
    """Objective hierarchy tiers."""

    CORE_LIFE = "core_life"
    STRATEGIC = "strategic"
    TACTICAL = "tactical"


class ObjectiveStatus(str, Enum):
    """Status of objectives."""

    ACTIVE = "active"
    PENDING = "pending"
    COMPLETED = "completed"
    PAUSED = "paused"
    ABANDONED = "abandoned"


class Objective(BaseModel):
    """Individual objective with full metadata."""

    name: str = Field(..., max_length=200, description="Objective name")
    description: str = Field(..., description="Detailed objective description")
    tier: ObjectiveTier = Field(..., description="Hierarchy tier")
    status: ObjectiveStatus = Field(
        default=ObjectiveStatus.ACTIVE, description="Current status"
    )
    priority: int = Field(..., ge=1, le=10, description="Priority level (1-10)")
    success_metrics: List[str] = Field(
        default_factory=list, description="How success is measured"
    )
    timeline: Optional[str] = Field(None, description="Expected timeline")
    dependencies: List[str] = Field(
        default_factory=list, description="Dependencies on other objectives"
    )
    motivation_source: Optional[str] = Field(
        None, description="What motivates this objective"
    )
    risk_factors: List[str] = Field(
        default_factory=list, description="Potential risk factors"
    )


class ResourceAllocation(BaseModel):
    """Resource allocation for objectives."""

    time_energy_percentages: Dict[str, int] = Field(
        default_factory=dict, description="Time/energy allocation"
    )
    success_thresholds: Dict[str, float] = Field(
        default_factory=dict, description="Success measurement thresholds"
    )

    @field_validator("time_energy_percentages")
    @classmethod
    def validate_percentages(cls, v):
        """Ensure percentages add up to 100."""
        if v and sum(v.values()) != 100:
            raise ValueError("Time/energy percentages must sum to 100")
        return v


class ObjectivesContext(BaseModel):
    """Complete objectives framework for a character."""

    core_objectives: List[Objective] = Field(
        default_factory=list, description="Core life objectives"
    )
    strategic_objectives: List[Objective] = Field(
        default_factory=list, description="Strategic objectives"
    )
    tactical_objectives: List[Objective] = Field(
        default_factory=list, description="Tactical objectives"
    )
    resource_allocation: ResourceAllocation = Field(
        default_factory=ResourceAllocation, description="Resource management"
    )
    current_focus: Optional[str] = Field(None, description="Current primary focus area")


class EmotionalDrive(BaseModel):
    """Core emotional drive with detailed modeling."""

    name: str = Field(..., max_length=100, description="Drive name")
    dominance_level: str = Field(
        ..., description="Dominance level (Dominant/Core/Emerging)"
    )
    foundation: str = Field(..., description="Psychological foundation")
    positive_expression: str = Field(..., description="How it manifests positively")
    negative_expression: str = Field(..., description="How it manifests negatively")
    trigger_events: List[str] = Field(
        default_factory=list, description="Events that trigger this drive"
    )
    soothing_behaviors: List[str] = Field(
        default_factory=list, description="Behaviors that soothe this drive"
    )


class EmotionalResponse(BaseModel):
    """Emotional response pattern for different threat levels."""

    level: int = Field(
        ..., ge=1, le=3, description="Response level (1=Low, 2=Medium, 3=High)"
    )
    level_name: str = Field(..., description="Human-readable level name")
    physiological: str = Field(..., description="Physiological response")
    emotional: str = Field(..., description="Emotional state")
    cognitive: str = Field(..., description="Cognitive patterns")
    behavioral: str = Field(..., description="Behavioral response")
    social: str = Field(..., description="Social interaction changes")
    recovery_time: str = Field(..., description="Time required for recovery")


class PersonalityTrait(BaseModel):
    """Personality trait with emotional context."""

    name: str = Field(..., max_length=50, description="Trait name")
    score: float = Field(..., ge=0.0, le=1.0, description="Trait strength (0.0-1.0)")
    emotional_foundation: str = Field(..., description="Emotional basis for this trait")
    positive_expression: str = Field(..., description="Positive manifestation")
    negative_expression: str = Field(..., description="Negative manifestation")
    emotional_triggers: List[str] = Field(
        default_factory=list, description="What triggers this trait"
    )


class ProfileContext(BaseModel):
    """Complete character profile with emotional modeling."""

    # Basic Identity
    name: str = Field(..., max_length=100, description="Character name")
    age: int = Field(..., ge=0, le=200, description="Character age")
    gender: str = Field(..., max_length=20, description="Character gender")
    race: str = Field(..., max_length=50, description="Character race")
    character_class: str = Field(..., max_length=50, description="Character class")
    title: Optional[str] = Field(None, description="Character title")
    affiliation: Optional[str] = Field(None, description="Primary affiliation")

    # Physical Description
    physical_description: str = Field(
        ..., description="Physical appearance description"
    )
    distinguishing_features: List[str] = Field(
        default_factory=list, description="Notable physical features"
    )

    # Background
    background_summary: str = Field(..., description="Background summary")
    key_life_phases: List[str] = Field(
        default_factory=list, description="Major life phases"
    )

    # Emotional Model
    emotional_drives: List[EmotionalDrive] = Field(
        default_factory=list, description="Core emotional drives"
    )
    emotional_responses: List[EmotionalResponse] = Field(
        default_factory=list, description="Response patterns"
    )
    personality_traits: List[PersonalityTrait] = Field(
        default_factory=list, description="Personality traits"
    )

    # Skills and Capabilities
    core_skills: List[str] = Field(default_factory=list, description="Primary skills")
    specializations: List[str] = Field(
        default_factory=list, description="Areas of specialization"
    )

    # Equipment and Resources
    equipment: List[str] = Field(default_factory=list, description="Notable equipment")
    resources: List[str] = Field(
        default_factory=list, description="Available resources"
    )


class CombatStats(BaseModel):
    """Combat-related statistics."""

    primary_stats: Dict[str, int] = Field(
        default_factory=dict, description="Primary combat statistics"
    )

    @field_validator("primary_stats")
    @classmethod
    def validate_stat_ranges(cls, v):
        """Ensure stats are in reasonable ranges."""
        for stat_name, value in v.items():
            if not (0 <= value <= 10):
                raise ValueError(f"Stat {stat_name} must be between 0-10, got {value}")
        return v


class PsychologicalProfile(BaseModel):
    """Psychological characteristics."""

    traits: Dict[str, int] = Field(
        default_factory=dict, description="Psychological trait scores"
    )

    @field_validator("traits")
    @classmethod
    def validate_trait_ranges(cls, v):
        """Ensure trait scores are in valid ranges."""
        for trait_name, score in v.items():
            if not (0 <= score <= 10):
                raise ValueError(
                    f"Trait {trait_name} must be between 0-10, got {score}"
                )
        return v


class RelationshipEntry(BaseModel):
    """Entry in relationships list."""

    name: str = Field(..., description="Character name")
    trust_level: int = Field(..., ge=0, le=100, description="Trust level 0-100")
    relationship_type: str = Field(..., description="Type of relationship")


class StatsContext(BaseModel):
    """Character statistics from YAML file."""

    # Character Info
    name: str = Field(..., description="Character name")
    age: int = Field(..., ge=0, le=200, description="Character age")
    origin: str = Field(..., description="Character origin")
    faction: str = Field(..., description="Character faction")
    rank: Optional[str] = Field(None, description="Character rank")
    specialization: str = Field(..., description="Primary specialization")

    # Stats
    combat_stats: CombatStats = Field(
        default_factory=CombatStats, description="Combat statistics"
    )
    psychological_profile: PsychologicalProfile = Field(
        default_factory=PsychologicalProfile, description="Psychological traits"
    )

    # Equipment
    equipment: Dict[str, Any] = Field(
        default_factory=dict, description="Equipment data"
    )

    # Relationships
    relationships: Dict[str, List[RelationshipEntry]] = Field(
        default_factory=dict, description="Character relationships"
    )

    # Additional fields for flexibility
    locations: Dict[str, Any] = Field(default_factory=dict, description="Location data")
    objectives: Dict[str, str] = Field(
        default_factory=dict, description="Primary objectives"
    )
    additional_data: Dict[str, Any] = Field(
        default_factory=dict, description="Additional character data"
    )


class LoadedFileInfo(BaseModel):
    """Information about loaded context files."""

    file_name: str = Field(..., description="Name of the loaded file")
    file_path: str = Field(..., description="Full path to the file")
    loaded_successfully: bool = Field(
        ..., description="Whether file loaded successfully"
    )
    file_size_bytes: int = Field(default=0, description="File size in bytes")
    load_timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When file was loaded"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if loading failed"
    )


class CharacterContext(BaseModel):
    """
    Consolidated character context containing all parsed context data.

    This is the primary output model for the ContextLoaderService,
    combining memory, objectives, profile, and stats into a single
    structured representation.
    """

    character_id: str = Field(..., description="Character identifier")
    character_name: str = Field(..., description="Character name")

    # Context Data
    memory_context: Optional[MemoryContext] = Field(
        None, description="Memory system data"
    )
    objectives_context: Optional[ObjectivesContext] = Field(
        None, description="Objectives framework data"
    )
    profile_context: Optional[ProfileContext] = Field(
        None, description="Profile and emotional model data"
    )
    stats_context: Optional[StatsContext] = Field(None, description="Statistics data")

    # File Loading Metadata
    loaded_files: List[LoadedFileInfo] = Field(
        default_factory=list, description="Information about loaded files"
    )
    load_timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When context was loaded"
    )
    load_success: bool = Field(
        default=True, description="Whether all files loaded successfully"
    )
    partial_load: bool = Field(
        default=False, description="Whether this is a partial load due to missing files"
    )

    # Validation and Integration
    context_integrity: bool = Field(
        default=True, description="Whether context data is internally consistent"
    )
    validation_warnings: List[str] = Field(
        default_factory=list, description="Non-critical validation warnings"
    )

    @model_validator(mode="before")
    @classmethod
    def validate_character_consistency(cls, values):
        """Ensure character data is consistent across contexts."""
        warnings = values.get("validation_warnings", [])

        # Extract character names from different contexts
        names_found = []

        profile_ctx = values.get("profile_context")
        if profile_ctx:
            profile_name = (
                profile_ctx.get("name")
                if isinstance(profile_ctx, dict)
                else getattr(profile_ctx, "name", None)
            )
            if profile_name:
                names_found.append(("profile", profile_name))

        stats_ctx = values.get("stats_context")
        if stats_ctx:
            stats_name = (
                stats_ctx.get("name")
                if isinstance(stats_ctx, dict)
                else getattr(stats_ctx, "name", None)
            )
            if stats_name:
                names_found.append(("stats", stats_name))

        character_name = values.get("character_name", "")
        if character_name:
            names_found.append(("primary", character_name))

        # Check for name consistency
        if len(names_found) > 1:
            unique_names = set([name for _, name in names_found])
            if len(unique_names) > 1:
                warnings.append(
                    f"Character name inconsistency detected: {dict(names_found)}"
                )
                values["context_integrity"] = False

        # Check if we have at least one context loaded
        contexts_loaded = sum(
            [
                1 if values.get("memory_context") else 0,
                1 if values.get("objectives_context") else 0,
                1 if values.get("profile_context") else 0,
                1 if values.get("stats_context") else 0,
            ]
        )

        if contexts_loaded == 0:
            values["load_success"] = False
            warnings.append("No context data was successfully loaded")
        elif contexts_loaded < 4:
            values["partial_load"] = True

        values["validation_warnings"] = warnings
        return values

    def get_primary_name(self) -> str:
        """Get the primary character name from available contexts."""
        if self.character_name:
            return self.character_name
        elif self.profile_context:
            return self.profile_context.name
        elif self.stats_context:
            return self.stats_context.name
        else:
            return "Unknown Character"

    def get_context_summary(self) -> Dict[str, Any]:
        """Get a summary of loaded context data."""
        return {
            "character_id": self.character_id,
            "character_name": self.get_primary_name(),
            "contexts_loaded": {
                "memory": self.memory_context is not None,
                "objectives": self.objectives_context is not None,
                "profile": self.profile_context is not None,
                "stats": self.stats_context is not None,
            },
            "files_loaded_count": len(self.loaded_files),
            "successful_files": len(
                [f for f in self.loaded_files if f.loaded_successfully]
            ),
            "load_success": self.load_success,
            "partial_load": self.partial_load,
            "context_integrity": self.context_integrity,
            "warnings_count": len(self.validation_warnings),
        }
