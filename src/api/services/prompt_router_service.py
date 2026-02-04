"""
Prompt Router Service

Warzone 4: AI Brain - BRAIN-015
Service layer for prompt management API router.

Constitution Compliance:
- Article II (Hexagonal): Application service uses port, doesn't use infrastructure directly
- Article I (DDD): Business logic for prompt CRUD operations
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from src.contexts.knowledge.application.ports.i_prompt_repository import (
    IPromptRepository,
    PromptNotFoundError,
    PromptRepositoryError,
)
from src.contexts.knowledge.domain.models.prompt_template import (
    ModelConfig,
    PromptTemplate,
    VariableType,
)

logger = logging.getLogger(__name__)


def _estimate_tokens(text: str) -> int:
    """
    Estimate token count for a text string.

    Why: Quick estimation without tiktoken dependency.

    Args:
        text: Text to estimate

    Returns:
        Estimated token count (~4 chars per token)
    """
    return max(1, len(text) // 4)


class PromptRouterService:
    """
    Service layer for prompt management router operations.

    Why:
        - Separates HTTP concerns from business logic
        - Provides reusable methods for router handlers
        - Handles entity-to-response conversions

    Attributes:
        _repository: The prompt repository port
    """

    def __init__(self, repository: IPromptRepository) -> None:
        """
        Initialize the prompt router service.

        Args:
            repository: Prompt repository implementing IPromptRepository
        """
        self._repository = repository

    async def list_prompts(
        self,
        tags: Optional[list[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PromptTemplate]:
        """
        List prompts with optional filtering.

        Args:
            tags: Optional filter by tags (all must match)
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of prompt templates
        """
        return await self._repository.list_all(tags=tags, limit=limit, offset=offset)

    async def search_prompts(
        self, query: str, limit: int = 20
    ) -> list[PromptTemplate]:
        """
        Search prompts by name or description.

        Args:
            query: Search query string
            limit: Maximum results

        Returns:
            List of matching prompt templates
        """
        return await self._repository.search(query=query, limit=limit)

    async def get_prompt_by_id(self, prompt_id: str) -> PromptTemplate:
        """
        Get a prompt by ID.

        Args:
            prompt_id: Prompt template ID

        Returns:
            Prompt template

        Raises:
            PromptNotFoundError: If prompt not found
        """
        template = await self._repository.get_by_id(prompt_id)
        if template is None:
            raise PromptNotFoundError(prompt_id)
        return template

    async def get_prompt_by_name(
        self, name: str, version: Optional[int] = None
    ) -> PromptTemplate:
        """
        Get a prompt by name.

        Args:
            name: Prompt name
            version: Optional version number (latest if None)

        Returns:
            Prompt template

        Raises:
            PromptNotFoundError: If prompt not found
        """
        template = await self._repository.get_by_name(name, version=version)
        if template is None:
            raise PromptNotFoundError(f"Prompt '{name}' not found")
        return template

    async def save_prompt(self, template: PromptTemplate) -> str:
        """
        Save a prompt template.

        Args:
            template: Prompt template to save

        Returns:
            ID of saved template
        """
        return await self._repository.save(template)

    async def delete_prompt(self, prompt_id: str) -> bool:
        """
        Delete a prompt template (soft delete).

        Args:
            prompt_id: Prompt template ID

        Returns:
            True if deleted, False if not found
        """
        return await self._repository.delete(prompt_id)

    async def count_prompts(self) -> int:
        """
        Count total prompt templates.

        Returns:
            Total count
        """
        return await self._repository.count()

    async def get_version_history(self, prompt_id: str) -> list[PromptTemplate]:
        """
        Get version history for a prompt.

        Args:
            prompt_id: Prompt template ID

        Returns:
            List of all versions
        """
        return await self._repository.get_version_history(prompt_id)

    async def get_all_tags(self) -> dict[str, list[str]]:
        """
        Get all unique tags across all prompts.

        Returns:
            Dictionary with tag categories and their values
        """
        prompts = await self._repository.list_all(limit=1000)

        all_tags: set[str] = set()
        model_tags: set[str] = set()
        type_tags: set[str] = set()

        for prompt in prompts:
            for tag in prompt.tags:
                all_tags.add(tag)
                if tag.startswith("model:"):
                    model_tags.add(tag.replace("model:", ""))
                elif tag.startswith("type:"):
                    type_tags.add(tag.replace("type:", ""))

        return {
            "all": sorted(all_tags),
            "model": sorted(model_tags),
            "type": sorted(type_tags),
        }

    async def render_prompt(
        self,
        prompt_id: str,
        variables: dict[str, Any],
        strict: bool = True,
    ) -> dict[str, Any]:
        """
        Render a prompt template with variables.

        Args:
            prompt_id: Prompt template ID
            variables: Variable values for rendering
            strict: Whether to raise errors for missing variables

        Returns:
            Dictionary with rendered content and metadata

        Raises:
            PromptNotFoundError: If prompt not found
            ValueError: If required variables are missing (when strict=True)
        """
        template = await self.get_prompt_by_id(prompt_id)

        # Render the template
        rendered = template.render(variables, strict=strict)

        # Track which variables were used
        variables_used = [
            var.name for var in template.variables if var.name in variables
        ]

        # Check for missing required variables
        variables_missing = []
        if strict:
            for var in template.variables:
                if var.required and var.name not in variables:
                    variables_missing.append(var.name)

        return {
            "rendered": rendered,
            "variables_used": variables_used,
            "variables_missing": variables_missing,
            "template_name": template.name,
            "token_count": _estimate_tokens(rendered),
            "llm_config": {
                "provider": template.model_config.provider,
                "model_name": template.model_config.model_name,
                "temperature": template.model_config.temperature,
                "max_tokens": template.model_config.max_tokens,
            },
        }

    def to_summary(self, template: PromptTemplate) -> dict[str, Any]:
        """
        Convert a PromptTemplate to a summary dictionary.

        Args:
            template: Prompt template entity

        Returns:
            Summary dictionary for API response
        """
        return {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "tags": list(template.tags),
            "version": template.version,
            "model_provider": template.model_config.provider,
            "model_name": template.model_config.model_name,
            "variable_count": len(template.variables),
            "created_at": template.created_at.isoformat(),
            "updated_at": template.updated_at.isoformat(),
        }

    def to_detail(self, template: PromptTemplate) -> dict[str, Any]:
        """
        Convert a PromptTemplate to a detailed dictionary.

        Args:
            template: Prompt template entity

        Returns:
            Detail dictionary for API response
        """
        return {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "content": template.content,
            "tags": list(template.tags),
            "version": template.version,
            "parent_version_id": template.parent_version_id,
            "llm_config": {
                "provider": template.model_config.provider,
                "model_name": template.model_config.model_name,
                "temperature": template.model_config.temperature,
                "max_tokens": template.model_config.max_tokens,
                "top_p": template.model_config.top_p,
                "frequency_penalty": template.model_config.frequency_penalty,
                "presence_penalty": template.model_config.presence_penalty,
            },
            "variables": [
                {
                    "name": var.name,
                    "type": var.type.value,
                    "default_value": var.default_value,
                    "description": var.description,
                    "required": var.required,
                }
                for var in template.variables
            ],
            "created_at": template.created_at.isoformat(),
            "updated_at": template.updated_at.isoformat(),
        }


__all__ = ["PromptRouterService"]
