#!/usr/bin/env python3
"""
Character persona data models and enums.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List

from src.templates.dynamic_template_engine import TemplateMetadata, TemplateType

if TYPE_CHECKING:
    from src.templates.context_renderer import RenderFormat


class CharacterArchetype(Enum):
    """ENHANCED CHARACTER ARCHETYPES SANCTIFIED BY PERSONALITY CLASSIFICATION"""

    WARRIOR = "warrior"  # Combat-focused, brave, direct
    SCHOLAR = "scholar"  # Knowledge-focused, analytical, cautious
    LEADER = "leader"  # Command-focused, charismatic, decisive
    MYSTIC = "mystic"  # Faith-focused, intuitive, spiritual
    ENGINEER = "engineer"  # Tech-focused, logical, problem-solver
    DIPLOMAT = "diplomat"  # Social-focused, persuasive, adaptable
    GUARDIAN = "guardian"  # Protection-focused, loyal, steadfast
    SURVIVOR = "survivor"  # Adaptability-focused, resourceful, pragmatic


@dataclass
class CharacterPersona:
    """
    STANDARD CHARACTER PERSONA ENHANCED BY COMPREHENSIVE IDENTITY

    Complete character persona definition with behavioral patterns,
    speech characteristics, and contextual preferences.
    """

    persona_id: str
    name: str
    archetype: CharacterArchetype
    description: str = ""
    personality_traits: List[str] = field(default_factory=list)
    speech_patterns: Dict[str, Any] = field(default_factory=dict)
    behavioral_preferences: Dict[str, Any] = field(default_factory=dict)
    memory_priorities: Dict[str, float] = field(default_factory=dict)
    emotional_tendencies: Dict[str, float] = field(default_factory=dict)
    faction_data: List[str] = field(default_factory=list)
    core_beliefs: List[str] = field(default_factory=list)
    template_preferences: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    usage_statistics: Dict[str, int] = field(default_factory=dict)


@dataclass
class CharacterTemplate:
    """
    ENHANCED CHARACTER TEMPLATE SANCTIFIED BY PERSONA INTEGRATION

    Character-specific template with persona awareness and
    adaptive content generation capabilities.
    """

    template_id: str
    persona_id: str
    template_type: TemplateType
    base_template: str  # Jinja2 template content
    persona_adaptations: Dict[str, str] = field(
        default_factory=dict
    )  # Archetype -> template variation
    context_requirements: List[str] = field(default_factory=list)
    dynamic_elements: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    metadata: TemplateMetadata = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = TemplateMetadata(
                template_id=self.template_id,
                template_type=self.template_type,
                description=f"Character template for {self.persona_id}",
            )


@dataclass
class CharacterContextProfile:
    """
    STANDARD CHARACTER CONTEXT PROFILE ENHANCED BY BEHAVIORAL INTELLIGENCE

    Dynamic profile that tracks character context preferences and
    behavioral patterns for intelligent template selection.
    """

    persona_id: str
    preferred_formats: Dict["RenderFormat", float] = field(default_factory=dict)
    context_emphasis: Dict[str, float] = field(
        default_factory=dict
    )  # memory, emotion, relationship, etc.
    situational_adaptations: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    interaction_patterns: Dict[str, List[str]] = field(default_factory=dict)
    learning_history: List[Dict[str, Any]] = field(default_factory=list)
    optimization_suggestions: List[str] = field(default_factory=list)
