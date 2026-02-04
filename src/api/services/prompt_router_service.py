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

    async def rollback_to_version(
        self,
        prompt_id: str,
        target_version: int,
    ) -> PromptTemplate:
        """
        Rollback a prompt to a specific version.

        Args:
            prompt_id: ID of the current prompt version
            target_version: Version number to rollback to

        Returns:
            New PromptTemplate created from the target version

        Raises:
            PromptNotFoundError: If prompt or target version not found
            ValueError: If target version is the same as current
        """
        # Get current template
        current = await self.get_prompt_by_id(prompt_id)

        if current.version == target_version:
            raise ValueError(
                f"Cannot rollback: already at version {target_version}"
            )

        # Get version history to find target version
        versions = await self.get_version_history(prompt_id)

        # Find the target version
        target = None
        for v in versions:
            if v.version == target_version:
                target = v
                break

        if target is None:
            raise PromptNotFoundError(
                f"Version {target_version} not found in history"
            )

        # Create a new version based on the target version content
        # This preserves history by creating a new version (v4) that copies v2 content
        from uuid import uuid4

        new_version = current.create_new_version(
            content=target.content,
            variables=target.variables,
            model_config=target.model_config,
            name=target.name,
            description=target.description + f" (rolled back from v{current.version})",
            tags=target.tags,
        )

        # Save the new version
        new_id = await self.save_prompt(new_version)

        # Fetch and return the saved template
        return await self.get_prompt_by_id(new_id)

    async def compare_versions(
        self,
        prompt_id: str,
        version_a: int,
        version_b: int,
    ) -> dict[str, Any]:
        """
        Compare two versions of a prompt template.

        Args:
            prompt_id: ID of any version of the prompt
            version_a: First version number
            version_b: Second version number

        Returns:
            Dictionary with comparison results including diffs

        Raises:
            PromptNotFoundError: If prompt or versions not found
        """
        # Get version history
        versions = await self.get_version_history(prompt_id)

        # Find both versions
        template_a = None
        template_b = None

        for v in versions:
            if v.version == version_a:
                template_a = v
            if v.version == version_b:
                template_b = v

        if template_a is None:
            raise PromptNotFoundError(f"Version {version_a} not found")
        if template_b is None:
            raise PromptNotFoundError(f"Version {version_b} not found")

        # Compute diffs
        content_diff = self._compute_character_diff(template_a.content, template_b.content)

        # Check for variable changes
        variables_a = {var.name: var for var in template_a.variables}
        variables_b = {var.name: var for var in template_b.variables}

        added_vars = set(variables_b.keys()) - set(variables_a.keys())
        removed_vars = set(variables_a.keys()) - set(variables_b.keys())
        common_vars = set(variables_a.keys()) & set(variables_b.keys())

        changed_vars = []
        for var_name in common_vars:
            var_a = variables_a[var_name]
            var_b = variables_b[var_name]
            if (
                var_a.type != var_b.type
                or var_a.default_value != var_b.default_value
                or var_a.required != var_b.required
            ):
                changed_vars.append(
                    {
                        "name": var_name,
                        "old": {
                            "type": var_a.type.value,
                            "default_value": var_a.default_value,
                            "required": var_a.required,
                        },
                        "new": {
                            "type": var_b.type.value,
                            "default_value": var_b.default_value,
                            "required": var_b.required,
                        },
                    }
                )

        # Check model config changes
        config_a = template_a.model_config
        config_b = template_b.model_config

        config_changes = []
        if config_a.provider != config_b.provider:
            config_changes.append({"field": "provider", "old": config_a.provider, "new": config_b.provider})
        if config_a.model_name != config_b.model_name:
            config_changes.append({"field": "model_name", "old": config_a.model_name, "new": config_b.model_name})
        if config_a.temperature != config_b.temperature:
            config_changes.append({"field": "temperature", "old": config_a.temperature, "new": config_b.temperature})
        if config_a.max_tokens != config_b.max_tokens:
            config_changes.append({"field": "max_tokens", "old": config_a.max_tokens, "new": config_b.max_tokens})

        # Check metadata changes
        metadata_changes = {}
        if template_a.name != template_b.name:
            metadata_changes["name"] = {"old": template_a.name, "new": template_b.name}
        if template_a.description != template_b.description:
            metadata_changes["description"] = {"old": template_a.description, "new": template_b.description}

        tags_a = set(template_a.tags)
        tags_b = set(template_b.tags)
        if tags_a != tags_b:
            metadata_changes["tags"] = {
                "added": list(tags_b - tags_a),
                "removed": list(tags_a - tags_b),
            }

        return {
            "version_a": {
                "version": template_a.version,
                "id": template_a.id,
                "created_at": template_a.created_at.isoformat(),
            },
            "version_b": {
                "version": template_b.version,
                "id": template_b.id,
                "created_at": template_b.created_at.isoformat(),
            },
            "content_diff": content_diff,
            "variables": {
                "added": list(added_vars),
                "removed": list(removed_vars),
                "changed": changed_vars,
            },
            "model_config": config_changes,
            "metadata": metadata_changes,
        }

    def _compute_character_diff(
        self,
        text_a: str,
        text_b: str,
    ) -> list[dict[str, Any]]:
        """
        Compute character-level diff between two strings.

        Uses a simple line-by-line diff algorithm for efficiency.

        Args:
            text_a: Original text
            text_b: New text

        Returns:
            List of diff hunks with added/removed sections
        """
        import difflib

        lines_a = text_a.splitlines(keepends=True)
        lines_b = text_b.splitlines(keepends=True)

        matcher = difflib.SequenceMatcher(None, lines_a, lines_b, autojunk=False)

        diffs = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue

            hunk = {
                "type": tag,
                "old_start": i1,
                "old_end": i2,
                "new_start": j1,
                "new_end": j2,
            }

            if tag == "replace":
                hunk["old_lines"] = "".join(lines_a[i1:i2])
                hunk["new_lines"] = "".join(lines_b[j1:j2])
            elif tag == "delete":
                hunk["old_lines"] = "".join(lines_a[i1:i2])
            elif tag == "insert":
                hunk["new_lines"] = "".join(lines_b[j1:j2])

            diffs.append(hunk)

        return diffs

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
            "extends": list(template.extends),
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
