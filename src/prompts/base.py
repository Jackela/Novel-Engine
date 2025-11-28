#!/usr/bin/env python3
"""
Prompt Template Base Classes.

This module defines the core data structures for prompt templates,
including the base PromptTemplate class and supporting enums.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Language(Enum):
    """Supported languages for prompt templates."""

    ENGLISH = "en"
    CHINESE = "zh"


class StoryGenre(Enum):
    """Supported story genres with their identifiers."""

    FANTASY = "fantasy"  # 奇幻冒险
    SCIFI = "scifi"  # 科幻太空
    MYSTERY = "mystery"  # 悬疑推理
    WUXIA = "wuxia"  # 武侠江湖
    ROMANCE = "romance"  # 浪漫爱情
    HORROR = "horror"  # 恐怖惊悚
    HISTORICAL = "historical"  # 历史古代
    URBAN = "urban"  # 都市现代


@dataclass
class PromptTemplate:
    """
    Base class for story prompt templates.

    A prompt template encapsulates all the information needed to generate
    story prompts for a specific genre, including bilingual support.

    Attributes:
        id: Unique identifier for the template (e.g., "fantasy_en")
        genre: The story genre this template belongs to
        language: The language of this template variant
        name: Display name in the template's language
        description: Description of what this template produces
        system_prompt: The main system prompt for the LLM
        story_requirements: List of requirements for the story
        style_guidelines: List of style guidelines
        example_opening: An example story opening for reference
        world_building_elements: Key elements for world building
        character_archetypes: Suggested character archetypes
        plot_devices: Common plot devices for this genre
        tone_descriptors: Words describing the desired tone
        metadata: Additional metadata for extensibility
    """

    id: str
    genre: StoryGenre
    language: Language
    name: str
    description: str
    system_prompt: str
    story_requirements: List[str] = field(default_factory=list)
    style_guidelines: List[str] = field(default_factory=list)
    example_opening: str = ""
    world_building_elements: List[str] = field(default_factory=list)
    character_archetypes: List[str] = field(default_factory=list)
    plot_devices: List[str] = field(default_factory=list)
    tone_descriptors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate the template after initialization."""
        if not self.id:
            raise ValueError("Template id cannot be empty")
        if not self.name:
            raise ValueError("Template name cannot be empty")
        if not self.system_prompt:
            raise ValueError("System prompt cannot be empty")

    def render(
        self,
        characters: List[str],
        events: str,
        world_state: Optional[Dict[str, Any]] = None,
        user_additions: str = "",
        custom_instructions: Optional[str] = None,
    ) -> str:
        """
        Render the complete prompt with provided context.

        Args:
            characters: List of character names/descriptions involved
            events: Description of events to incorporate
            world_state: Optional world state information
            user_additions: Optional user-provided additions to the prompt
            custom_instructions: Optional custom instructions to append

        Returns:
            The fully rendered prompt string
        """
        # Build character section
        if self.language == Language.CHINESE:
            char_section = "## 角色\n" + "\n".join(f"- {c}" for c in characters)
            events_section = f"## 事件\n{events}"
        else:
            char_section = "## Characters\n" + "\n".join(f"- {c}" for c in characters)
            events_section = f"## Events\n{events}"

        # Build world state section if provided
        world_section = ""
        if world_state:
            if self.language == Language.CHINESE:
                world_section = "\n## 世界状态\n"
                for key, value in world_state.items():
                    world_section += f"- {key}: {value}\n"
            else:
                world_section = "\n## World State\n"
                for key, value in world_state.items():
                    world_section += f"- {key}: {value}\n"

        # Build requirements section
        if self.story_requirements:
            if self.language == Language.CHINESE:
                req_section = "\n## 故事要求\n" + "\n".join(
                    f"- {r}" for r in self.story_requirements
                )
            else:
                req_section = "\n## Story Requirements\n" + "\n".join(
                    f"- {r}" for r in self.story_requirements
                )
        else:
            req_section = ""

        # Build style section
        if self.style_guidelines:
            if self.language == Language.CHINESE:
                style_section = "\n## 风格指南\n" + "\n".join(
                    f"- {s}" for s in self.style_guidelines
                )
            else:
                style_section = "\n## Style Guidelines\n" + "\n".join(
                    f"- {s}" for s in self.style_guidelines
                )
        else:
            style_section = ""

        # User additions
        user_section = ""
        if user_additions:
            if self.language == Language.CHINESE:
                user_section = f"\n## 用户补充\n{user_additions}"
            else:
                user_section = f"\n## User Additions\n{user_additions}"

        # Custom instructions
        custom_section = ""
        if custom_instructions:
            if self.language == Language.CHINESE:
                custom_section = f"\n## 自定义指令\n{custom_instructions}"
            else:
                custom_section = f"\n## Custom Instructions\n{custom_instructions}"

        # Assemble the full prompt
        prompt_parts = [
            self.system_prompt,
            "",
            char_section,
            "",
            events_section,
            world_section,
            req_section,
            style_section,
            user_section,
            custom_section,
        ]

        return "\n".join(part for part in prompt_parts if part)

    def get_genre_keywords(self) -> List[str]:
        """
        Get keywords associated with this genre for optimization.

        Returns:
            List of relevant keywords
        """
        return (
            self.world_building_elements
            + self.character_archetypes
            + self.plot_devices
            + self.tone_descriptors
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert template to dictionary for serialization.

        Returns:
            Dictionary representation of the template
        """
        return {
            "id": self.id,
            "genre": self.genre.value,
            "language": self.language.value,
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "story_requirements": self.story_requirements,
            "style_guidelines": self.style_guidelines,
            "example_opening": self.example_opening,
            "world_building_elements": self.world_building_elements,
            "character_archetypes": self.character_archetypes,
            "plot_devices": self.plot_devices,
            "tone_descriptors": self.tone_descriptors,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptTemplate":
        """
        Create template from dictionary.

        Args:
            data: Dictionary containing template data

        Returns:
            PromptTemplate instance
        """
        return cls(
            id=data["id"],
            genre=StoryGenre(data["genre"]),
            language=Language(data["language"]),
            name=data["name"],
            description=data["description"],
            system_prompt=data["system_prompt"],
            story_requirements=data.get("story_requirements", []),
            style_guidelines=data.get("style_guidelines", []),
            example_opening=data.get("example_opening", ""),
            world_building_elements=data.get("world_building_elements", []),
            character_archetypes=data.get("character_archetypes", []),
            plot_devices=data.get("plot_devices", []),
            tone_descriptors=data.get("tone_descriptors", []),
            metadata=data.get("metadata", {}),
        )


__all__ = [
    "Language",
    "PromptTemplate",
    "StoryGenre",
]
