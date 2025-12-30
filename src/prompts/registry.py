#!/usr/bin/env python3
"""
Prompt Template Registry.

This module provides a central registry for managing all prompt templates,
both pre-defined and user-created.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from .base import Language, PromptTemplate, StoryGenre

logger = logging.getLogger(__name__)


class PromptRegistry:
    """
    Central registry for prompt templates.

    This class manages registration, lookup, and filtering of prompt templates.
    It follows the singleton pattern to ensure a single source of truth.
    """

    _instance: Optional["PromptRegistry"] = None
    _templates: Dict[str, PromptTemplate] = {}

    def __new__(cls) -> "PromptRegistry":
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._templates = {}
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the registry (useful for testing)."""
        cls._templates = {}
        cls._instance = None

    @classmethod
    def register(cls, template: PromptTemplate) -> None:
        """
        Register a prompt template.

        Args:
            template: The template to register

        Raises:
            ValueError: If a template with the same ID already exists
        """
        if template.id in cls._templates:
            logger.warning(f"Template '{template.id}' already exists, overwriting")
        cls._templates[template.id] = template
        logger.debug(f"Registered template: {template.id}")

    @classmethod
    def register_many(cls, templates: List[PromptTemplate]) -> None:
        """
        Register multiple templates at once.

        Args:
            templates: List of templates to register
        """
        for template in templates:
            cls.register(template)

    @classmethod
    def unregister(cls, template_id: str) -> bool:
        """
        Unregister a template by ID.

        Args:
            template_id: The ID of the template to remove

        Returns:
            True if the template was removed, False if not found
        """
        if template_id in cls._templates:
            del cls._templates[template_id]
            logger.debug(f"Unregistered template: {template_id}")
            return True
        return False

    @classmethod
    def get(cls, template_id: str) -> Optional[PromptTemplate]:
        """
        Get a template by ID.

        Args:
            template_id: The template ID to look up

        Returns:
            The template if found, None otherwise
        """
        return cls._templates.get(template_id)

    @classmethod
    def get_or_raise(cls, template_id: str) -> PromptTemplate:
        """
        Get a template by ID, raising if not found.

        Args:
            template_id: The template ID to look up

        Returns:
            The template

        Raises:
            KeyError: If template not found
        """
        template = cls._templates.get(template_id)
        if template is None:
            raise KeyError(f"Template '{template_id}' not found")
        return template

    @classmethod
    def list_all(cls) -> List[PromptTemplate]:
        """
        List all registered templates.

        Returns:
            List of all templates
        """
        return list(cls._templates.values())

    @classmethod
    def list_by_genre(cls, genre: StoryGenre) -> List[PromptTemplate]:
        """
        List templates by genre.

        Args:
            genre: The genre to filter by

        Returns:
            List of templates matching the genre
        """
        return [t for t in cls._templates.values() if t.genre == genre]

    @classmethod
    def list_by_language(cls, language: Language) -> List[PromptTemplate]:
        """
        List templates by language.

        Args:
            language: The language to filter by

        Returns:
            List of templates matching the language
        """
        return [t for t in cls._templates.values() if t.language == language]

    @classmethod
    def list_by_genre_and_language(
        cls, genre: StoryGenre, language: Language
    ) -> List[PromptTemplate]:
        """
        List templates by both genre and language.

        Args:
            genre: The genre to filter by
            language: The language to filter by

        Returns:
            List of templates matching both criteria
        """
        return [
            t
            for t in cls._templates.values()
            if t.genre == genre and t.language == language
        ]

    @classmethod
    def get_by_genre_and_language(
        cls, genre: StoryGenre, language: Language
    ) -> Optional[PromptTemplate]:
        """
        Get a single template by genre and language.

        Args:
            genre: The genre to find
            language: The language to find

        Returns:
            The first matching template, or None
        """
        templates = cls.list_by_genre_and_language(genre, language)
        return templates[0] if templates else None

    @classmethod
    def get_template_id(cls, genre: StoryGenre, language: Language) -> str:
        """
        Generate a standard template ID from genre and language.

        Args:
            genre: The story genre
            language: The language

        Returns:
            The standardized template ID
        """
        return f"{genre.value}_{language.value}"

    @classmethod
    def count(cls) -> int:
        """
        Get the total number of registered templates.

        Returns:
            Number of templates
        """
        return len(cls._templates)

    @classmethod
    def genres(cls) -> List[StoryGenre]:
        """
        Get list of genres that have registered templates.

        Returns:
            List of unique genres
        """
        return list(set(t.genre for t in cls._templates.values()))

    @classmethod
    def to_dict_list(cls) -> List[Dict]:
        """
        Convert all templates to a list of dictionaries.

        Returns:
            List of template dictionaries
        """
        return [t.to_dict() for t in cls._templates.values()]


__all__ = ["PromptRegistry"]
