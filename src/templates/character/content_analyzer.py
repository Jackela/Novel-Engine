#!/usr/bin/env python3
"""
Content analysis and archetype detection.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple

from src.templates.dynamic_template_engine import TemplateType

from .persona_models import CharacterArchetype, CharacterPersona

logger = logging.getLogger(__name__)


class ContentAnalyzer:
    """Analyzes content to detect archetypes and extract traits."""

    def _detect_archetype_from_template(
        self, template_content: str
    ) -> Optional[CharacterArchetype]:
        """Detect enhanced archetype from template content"""
        content_lower = template_content.lower()

        archetype_keywords = {
            CharacterArchetype.WARRIOR: [
                "battle",
                "combat",
                "fight",
                "warrior",
                "sword",
                "weapon",
            ],
            CharacterArchetype.SCHOLAR: [
                "study",
                "knowledge",
                "learn",
                "research",
                "book",
                "academic",
            ],
            CharacterArchetype.LEADER: [
                "command",
                "lead",
                "order",
                "authority",
                "decision",
                "strategy",
            ],
            CharacterArchetype.MYSTIC: [
                "faith",
                "spiritual",
                "prayer",
                "advanced",
                "enhanced",
                "standard",
            ],
            CharacterArchetype.ENGINEER: [
                "technical",
                "machine",
                "repair",
                "build",
                "construct",
                "tech",
            ],
            CharacterArchetype.DIPLOMAT: [
                "negotiate",
                "diplomacy",
                "alliance",
                "treaty",
                "peace",
                "relations",
            ],
            CharacterArchetype.GUARDIAN: [
                "protect",
                "guard",
                "defend",
                "shield",
                "safety",
                "security",
            ],
            CharacterArchetype.SURVIVOR: [
                "survive",
                "endure",
                "adapt",
                "resourceful",
                "hardy",
                "resilient",
            ],
        }

        archetype_scores = {}
        for archetype, keywords in archetype_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            if score > 0:
                archetype_scores[archetype] = score

        if archetype_scores:
            return max(archetype_scores, key=archetype_scores.get)

        return None

    def _extract_personality_traits(self, template_content: str) -> List[str]:
        """Extract enhanced personality traits from template content"""
        trait_keywords = [
            "brave",
            "loyal",
            "determined",
            "wise",
            "clever",
            "strong",
            "fast",
            "careful",
            "aggressive",
            "peaceful",
            "kind",
            "harsh",
            "disciplined",
            "creative",
            "logical",
            "emotional",
            "calm",
            "energetic",
            "patient",
            "impulsive",
            "methodical",
            "intuitive",
        ]

        content_lower = template_content.lower()
        found_traits = [trait for trait in trait_keywords if trait in content_lower]

        return found_traits[:5]  # Limit to 5 traits

    def _detect_template_type(
        self, template_content: str, template_name: str
    ) -> TemplateType:
        """Detect enhanced template type from content and name"""
        name_lower = template_name.lower()
        template_content.lower()

        if any(keyword in name_lower for keyword in ["prompt", "character", "persona"]):
            return TemplateType.CHARACTER_PROMPT
        elif any(
            keyword in name_lower for keyword in ["dialogue", "conversation", "speak"]
        ):
            return TemplateType.DIALOGUE
        elif any(keyword in name_lower for keyword in ["scene", "narrative", "story"]):
            return TemplateType.NARRATIVE_SCENE
        elif any(keyword in name_lower for keyword in ["summary", "context"]):
            return TemplateType.CONTEXT_SUMMARY
        elif any(keyword in name_lower for keyword in ["equipment", "gear", "status"]):
            return TemplateType.EQUIPMENT_STATUS
        elif any(keyword in name_lower for keyword in ["interaction", "log"]):
            return TemplateType.INTERACTION_LOG
        elif any(
            keyword in name_lower for keyword in ["world", "state", "environment"]
        ):
            return TemplateType.WORLD_STATE
        elif any(keyword in name_lower for keyword in ["memory", "excerpt"]):
            return TemplateType.MEMORY_EXCERPT
        else:
            # Default enhanced determination
            return TemplateType.CHARACTER_PROMPT

