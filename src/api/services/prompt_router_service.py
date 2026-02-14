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
import os
import time
from typing import TYPE_CHECKING, Any, Optional

import requests

from src.contexts.knowledge.application.ports.i_prompt_repository import (
    IPromptRepository,
    PromptNotFoundError,
    PromptRepositoryError,
)
from src.contexts.knowledge.application.ports.i_prompt_usage_repository import (
    IPromptUsageRepository,
)
from src.contexts.knowledge.domain.models.prompt_template import (
    ModelConfig,
    PromptTemplate,
    VariableType,
)
from src.contexts.knowledge.domain.models.prompt_usage import PromptUsage

if TYPE_CHECKING:
    pass

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
        _usage_repository: Optional prompt usage repository for analytics
    """

    def __init__(
        self,
        repository: IPromptRepository,
        usage_repository: Optional[IPromptUsageRepository] = None,
    ) -> None:
        """
        Initialize the prompt router service.

        Args:
            repository: Prompt repository implementing IPromptRepository
            usage_repository: Optional usage repository for analytics tracking
        """
        self._repository = repository
        self._usage_repository = usage_repository

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

    async def search_prompts(self, query: str, limit: int = 20) -> list[PromptTemplate]:
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
            raise ValueError(f"Cannot rollback: already at version {target_version}")

        # Get version history to find target version
        versions = await self.get_version_history(prompt_id)

        # Find the target version
        target = None
        for v in versions:
            if v.version == target_version:
                target = v
                break

        if target is None:
            raise PromptNotFoundError(f"Version {target_version} not found in history")

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
        content_diff = self._compute_character_diff(
            template_a.content, template_b.content
        )

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
            config_changes.append(
                {
                    "field": "provider",
                    "old": config_a.provider,
                    "new": config_b.provider,
                }
            )
        if config_a.model_name != config_b.model_name:
            config_changes.append(
                {
                    "field": "model_name",
                    "old": config_a.model_name,
                    "new": config_b.model_name,
                }
            )
        if config_a.temperature != config_b.temperature:
            config_changes.append(
                {
                    "field": "temperature",
                    "old": config_a.temperature,
                    "new": config_b.temperature,
                }
            )
        if config_a.max_tokens != config_b.max_tokens:
            config_changes.append(
                {
                    "field": "max_tokens",
                    "old": config_a.max_tokens,
                    "new": config_b.max_tokens,
                }
            )

        # Check metadata changes
        metadata_changes = {}
        if template_a.name != template_b.name:
            metadata_changes["name"] = {"old": template_a.name, "new": template_b.name}
        if template_a.description != template_b.description:
            metadata_changes["description"] = {
                "old": template_a.description,
                "new": template_b.description,
            }

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

    async def generate_prompt(
        self,
        prompt_id: str,
        variables: dict[str, Any],
        strict: bool = True,
        provider_override: Optional[str] = None,
        model_name_override: Optional[str] = None,
        temperature_override: Optional[float] = None,
        max_tokens_override: Optional[int] = None,
        top_p_override: Optional[float] = None,
        frequency_penalty_override: Optional[float] = None,
        presence_penalty_override: Optional[float] = None,
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Generate output using a prompt template and LLM.

        BRAIN-020B: Frontend: Prompt Playground - Integration
        BRAIN-022A: Backend: Prompt Analytics - Data Model (usage tracking)

        Combines rendering and LLM generation in a single operation.
        Records usage analytics if usage_repository is configured.

        Args:
            prompt_id: Prompt template ID
            variables: Variable values for rendering
            strict: Whether to raise errors for missing variables
            provider_override: Override LLM provider
            model_name_override: Override model name
            temperature_override: Override sampling temperature
            max_tokens_override: Override max tokens to generate
            top_p_override: Override nucleus sampling
            frequency_penalty_override: Override frequency penalty
            presence_penalty_override: Override presence penalty
            workspace_id: Optional workspace identifier for analytics
            user_id: Optional user identifier for analytics

        Returns:
            Dictionary with rendered prompt, LLM output, and metadata

        Raises:
            PromptNotFoundError: If prompt not found
            RuntimeError: If LLM generation fails
        """
        # Get the template
        template = await self.get_prompt_by_id(prompt_id)

        # Render the template
        rendered = template.render(variables, strict=strict)

        # Get model config (use overrides if provided)
        config = template.model_config
        provider = provider_override or config.provider
        model_name = model_name_override or config.model_name
        temperature = (
            temperature_override
            if temperature_override is not None
            else config.temperature
        )
        max_tokens = (
            max_tokens_override
            if max_tokens_override is not None
            else config.max_tokens
        )
        top_p = top_p_override if top_p_override is not None else config.top_p

        # Start timing
        start_time = time.time()
        error_message = None
        success = True
        output = ""

        try:
            # Call LLM
            output = await self._call_llm(
                rendered=rendered,
                provider=provider,
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
            )
        except Exception as e:
            success = False
            error_message = str(e)
            logger.warning(
                f"LLM generation failed for prompt {prompt_id}: {error_message}"
            )
            raise
        finally:
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Estimate tokens
            prompt_tokens = _estimate_tokens(rendered)
            output_tokens = _estimate_tokens(output)

            # Record usage analytics if repository is configured
            if self._usage_repository is not None:
                try:
                    usage = PromptUsage.create(
                        prompt_id=template.id,
                        prompt_name=template.name,
                        prompt_version=template.version,
                        input_tokens=prompt_tokens,
                        output_tokens=output_tokens,
                        latency_ms=latency_ms,
                        model_provider=provider,
                        model_name=model_name,
                        success=success,
                        error_message=error_message,
                        workspace_id=workspace_id,
                        user_id=user_id,
                        # Sanitize variables for storage (exclude sensitive values)
                        variables={k: type(v).__name__ for k, v in variables.items()},
                    )
                    await self._usage_repository.record(usage)
                except Exception as record_error:
                    # Don't fail the request if analytics recording fails
                    logger.debug(f"Failed to record prompt usage: {record_error}")

        return {
            "rendered": rendered,
            "output": output,
            "template_id": template.id,
            "template_name": template.name,
            "prompt_tokens": prompt_tokens,
            "output_tokens": output_tokens,
            "total_tokens": prompt_tokens + output_tokens,
            "latency_ms": latency_ms,
            "model_used": f"{provider}:{model_name}",
            "error": error_message,
        }

    async def _call_llm(
        self,
        rendered: str,
        provider: str,
        model_name: str,
        temperature: float,
        max_tokens: int,
        top_p: float,
    ) -> str:
        """
        Call LLM to generate output from a rendered prompt.

        Currently supports Gemini (default) with placeholder for other providers.

        Why: Isolates LLM calling logic for easy extension to multiple providers.

        Args:
            rendered: The rendered prompt content
            provider: LLM provider (gemini, openai, anthropic, ollama)
            model_name: Model name to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter

        Returns:
            Generated text output

        Raises:
            RuntimeError: If API call fails or provider not supported
        """
        if provider == "gemini":
            return await self._call_gemini(
                rendered, model_name, temperature, max_tokens
            )
        elif provider == "openai":
            return await self._call_openai(
                rendered, model_name, temperature, max_tokens, top_p
            )
        elif provider == "anthropic":
            return await self._call_anthropic(
                rendered, model_name, temperature, max_tokens
            )
        elif provider == "ollama":
            return await self._call_ollama(
                rendered, model_name, temperature, max_tokens
            )
        else:
            raise RuntimeError(f"Unsupported LLM provider: {provider}")

    async def _call_gemini(
        self,
        rendered: str,
        model_name: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        Call Gemini API to generate output.

        Args:
            rendered: Rendered prompt content
            model_name: Gemini model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text

        Raises:
            RuntimeError: If API call fails
        """
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is not set")

        # Default to gemini-2.0-flash if not specified
        if not model_name or model_name == "gpt-4":
            model_name = "gemini-2.0-flash"

        base_url = f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent"

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        }

        request_body = {
            "contents": [{"parts": [{"text": rendered}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        response = requests.post(
            base_url, headers=headers, json=request_body, timeout=120
        )

        if response.status_code == 401:
            raise RuntimeError(
                "Gemini API authentication failed - check GEMINI_API_KEY"
            )
        elif response.status_code == 429:
            raise RuntimeError("Gemini API rate limit exceeded")
        elif response.status_code != 200:
            raise RuntimeError(
                f"Gemini API error {response.status_code}: {response.text}"
            )

        try:
            response_json = response.json()
            content = response_json["candidates"][0]["content"]["parts"][0]["text"]
            return content
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Failed to parse Gemini response: {e}")

    async def _call_openai(
        self,
        rendered: str,
        model_name: str,
        temperature: float,
        max_tokens: int,
        top_p: float,
    ) -> str:
        """
        Call OpenAI API to generate output.

        Args:
            rendered: Rendered prompt content
            model_name: OpenAI model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter

        Returns:
            Generated text

        Raises:
            RuntimeError: If API call fails
        """
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set")

        # Default to gpt-4o-mini if not specified
        if not model_name:
            model_name = "gpt-4o-mini"

        base_url = "https://api.openai.com/v1/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        request_body = {
            "model": model_name,
            "messages": [{"role": "user", "content": rendered}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
        }

        response = requests.post(
            base_url, headers=headers, json=request_body, timeout=120
        )

        if response.status_code == 401:
            raise RuntimeError(
                "OpenAI API authentication failed - check OPENAI_API_KEY"
            )
        elif response.status_code == 429:
            raise RuntimeError("OpenAI API rate limit exceeded")
        elif response.status_code != 200:
            raise RuntimeError(
                f"OpenAI API error {response.status_code}: {response.text}"
            )

        try:
            response_json = response.json()
            content = response_json["choices"][0]["message"]["content"]
            return content
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Failed to parse OpenAI response: {e}")

    async def _call_anthropic(
        self,
        rendered: str,
        model_name: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        Call Anthropic Claude API to generate output.

        Args:
            rendered: Rendered prompt content
            model_name: Claude model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text

        Raises:
            RuntimeError: If API call fails
        """
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")

        # Default to claude-3-haiku if not specified
        if not model_name:
            model_name = "claude-3-5-haiku-20241022"

        base_url = "https://api.anthropic.com/v1/messages"

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }

        request_body = {
            "model": model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": rendered}],
        }

        response = requests.post(
            base_url, headers=headers, json=request_body, timeout=120
        )

        if response.status_code == 401:
            raise RuntimeError(
                "Anthropic API authentication failed - check ANTHROPIC_API_KEY"
            )
        elif response.status_code == 429:
            raise RuntimeError("Anthropic API rate limit exceeded")
        elif response.status_code != 200:
            raise RuntimeError(
                f"Anthropic API error {response.status_code}: {response.text}"
            )

        try:
            response_json = response.json()
            content = response_json["content"][0]["text"]
            return content
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Failed to parse Anthropic response: {e}")

    async def _call_ollama(
        self,
        rendered: str,
        model_name: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        Call Ollama API to generate output.

        Args:
            rendered: Rendered prompt content
            model_name: Ollama model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text

        Raises:
            RuntimeError: If API call fails
        """
        # Default to llama3 if not specified
        if not model_name:
            model_name = "llama3"

        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        endpoint = f"{base_url}/api/generate"

        request_body = {
            "model": model_name,
            "prompt": rendered,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            response = requests.post(endpoint, json=request_body, timeout=120)
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                f"Could not connect to Ollama at {base_url}. Make sure Ollama is running."
            )

        if response.status_code != 200:
            raise RuntimeError(
                f"Ollama API error {response.status_code}: {response.text}"
            )

        try:
            response_json = response.json()
            content = response_json.get("response", "")
            return content
        except (KeyError, TypeError) as e:
            raise RuntimeError(f"Failed to parse Ollama response: {e}")

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

    async def get_prompt_analytics(
        self,
        prompt_id: str,
        period: str = "all",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        workspace_id: Optional[str] = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Get analytics for a prompt template.

        BRAIN-022B: Backend: Prompt Analytics - API
        Provides usage statistics and metrics over time with period aggregation.

        Args:
            prompt_id: Prompt template ID
            period: Time period for aggregation (day, week, month, all)
            start_date: Optional ISO 8601 start date for filtering
            end_date: Optional ISO 8601 end date for filtering
            workspace_id: Optional filter by workspace
            limit: Maximum time series data points

        Returns:
            Dictionary with analytics data including time series

        Raises:
            PromptNotFoundError: If prompt not found
            ValueError: If usage repository is not configured
        """
        from datetime import datetime, timedelta, timezone

        if self._usage_repository is None:
            raise ValueError("Usage repository is not configured for analytics")

        # Verify prompt exists
        template = await self.get_prompt_by_id(prompt_id)

        # Parse date filters
        start_dt: Optional[datetime] = None
        end_dt: Optional[datetime] = None

        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            except ValueError as e:
                raise ValueError(f"Invalid start_date format: {e}")

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            except ValueError as e:
                raise ValueError(f"Invalid end_date format: {e}")

        # Get base stats
        stats = await self._usage_repository.get_stats(
            prompt_id=prompt_id,
            workspace_id=workspace_id,
            start_date=start_dt,
            end_date=end_dt,
        )

        # Get all usages for time series and rating distribution
        usages = await self._usage_repository.list_by_prompt(
            prompt_id=prompt_id,
            limit=limit * 10,  # Get more to allow for grouping
            workspace_id=workspace_id,
        )

        # Filter by date range if specified
        if start_dt:
            usages = [u for u in usages if u.timestamp >= start_dt]
        if end_dt:
            usages = [u for u in usages if u.timestamp <= end_dt]

        # Calculate rating distribution
        rating_dist = self._calculate_rating_distribution(usages)

        # Calculate latency min/max
        latencies = [u.latency_ms for u in usages if u.latency_ms > 0]
        min_latency = min(latencies) if latencies else 0.0
        max_latency = max(latencies) if latencies else 0.0

        # Build time series data
        time_series = self._build_time_series(usages, period, limit)

        return {
            "prompt_id": prompt_id,
            "prompt_name": template.name,
            "period": period,
            # Overall metrics
            "total_uses": stats.total_uses,
            "successful_uses": stats.successful_uses,
            "failed_uses": stats.failed_uses,
            "success_rate": round(stats.success_rate, 2),
            # Token metrics
            "total_tokens": stats.total_tokens,
            "total_input_tokens": stats.total_input_tokens,
            "total_output_tokens": stats.total_output_tokens,
            "avg_tokens_per_use": round(stats.avg_tokens_per_use, 2),
            "avg_input_tokens": round(stats.avg_input_tokens, 2),
            "avg_output_tokens": round(stats.avg_output_tokens, 2),
            # Latency metrics
            "total_latency_ms": round(stats.total_latency_ms, 2),
            "avg_latency_ms": round(stats.avg_latency_ms, 2),
            "min_latency_ms": round(min_latency, 2),
            "max_latency_ms": round(max_latency, 2),
            # Rating metrics
            "rating_sum": round(stats.rating_sum, 2),
            "rating_count": stats.rating_count,
            "avg_rating": round(stats.avg_rating, 2),
            "rating_distribution": rating_dist,
            # Time series
            "time_series": time_series,
            # Metadata
            "first_used": stats.first_used.isoformat() if stats.first_used else None,
            "last_used": stats.last_used.isoformat() if stats.last_used else None,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _calculate_rating_distribution(
        self, usages: list[PromptUsage]
    ) -> dict[str, int]:
        """
        Calculate rating distribution from usage events.

        Args:
            usages: List of PromptUsage events

        Returns:
            Dictionary with rating counts
        """
        distribution = {
            "one_star": 0,
            "two_star": 0,
            "three_star": 0,
            "four_star": 0,
            "five_star": 0,
        }

        for usage in usages:
            if usage.user_rating is not None:
                rating = int(usage.user_rating)
                if rating == 1:
                    distribution["one_star"] += 1
                elif rating == 2:
                    distribution["two_star"] += 1
                elif rating == 3:
                    distribution["three_star"] += 1
                elif rating == 4:
                    distribution["four_star"] += 1
                elif rating == 5:
                    distribution["five_star"] += 1

        return distribution

    def _build_time_series(
        self, usages: list[PromptUsage], period: str, limit: int
    ) -> list[dict[str, Any]]:
        """
        Build time series data from usage events.

        Args:
            usages: List of PromptUsage events
            period: Aggregation period (day, week, month, all)
            limit: Maximum data points to return

        Returns:
            List of time series data points
        """
        from collections import defaultdict
        from datetime import timezone

        if not usages or period == "all":
            return []

        # Sort usages by timestamp
        sorted_usages = sorted(usages, key=lambda u: u.timestamp)

        # Group by period
        grouped: defaultdict[str, list[PromptUsage]] = defaultdict(list)

        for usage in sorted_usages:
            if period == "day":
                # Group by ISO date (YYYY-MM-DD)
                key = usage.timestamp.strftime("%Y-%m-%d")
            elif period == "week":
                # Group by ISO week (YYYY-Www)
                year, week, _ = usage.timestamp.isocalendar()
                key = f"{year}-W{week:02d}"
            elif period == "month":
                # Group by month (YYYY-MM)
                key = usage.timestamp.strftime("%Y-%m")
            else:
                key = "all"

            grouped[key].append(usage)

        # Convert to data points
        data_points = []
        for period_key in sorted(grouped.keys(), reverse=True)[:limit]:
            period_usages = grouped[period_key]

            total = len(period_usages)
            successful = sum(1 for u in period_usages if u.success)
            failed = total - successful
            total_tokens = sum(u.total_tokens for u in period_usages)
            avg_latency = (
                sum(u.latency_ms for u in period_usages) / total if total > 0 else 0
            )

            ratings = [
                u.user_rating for u in period_usages if u.user_rating is not None
            ]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0

            data_points.append(
                {
                    "period": period_key,
                    "total_uses": total,
                    "successful_uses": successful,
                    "failed_uses": failed,
                    "total_tokens": total_tokens,
                    "avg_latency_ms": round(avg_latency, 2),
                    "avg_rating": round(avg_rating, 2),
                }
            )

        # Sort by period (most recent first)
        return sorted(data_points, key=lambda x: x["period"], reverse=True)[:limit]

    async def export_analytics_csv(
        self,
        prompt_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> str:
        """
        Export prompt analytics as CSV.

        BRAIN-022B: Backend: Prompt Analytics - API (CSV export)

        Args:
            prompt_id: Prompt template ID
            start_date: Optional ISO 8601 start date for filtering
            end_date: Optional ISO 8601 end date for filtering
            workspace_id: Optional filter by workspace

        Returns:
            CSV formatted string

        Raises:
            PromptNotFoundError: If prompt not found
            ValueError: If usage repository is not configured
        """
        import csv
        import io
        from datetime import datetime, timezone

        if self._usage_repository is None:
            raise ValueError("Usage repository is not configured for analytics")

        # Verify prompt exists
        template = await self.get_prompt_by_id(prompt_id)

        # Parse date filters
        start_dt: Optional[datetime] = None
        end_dt: Optional[datetime] = None

        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            except ValueError as e:
                raise ValueError(f"Invalid start_date format: {e}")

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            except ValueError as e:
                raise ValueError(f"Invalid end_date format: {e}")

        # Get usages
        usages = await self._usage_repository.list_by_prompt(
            prompt_id=prompt_id,
            limit=10000,  # Large limit for export
            workspace_id=workspace_id,
        )

        # Filter by date range if specified
        if start_dt:
            usages = [u for u in usages if u.timestamp >= start_dt]
        if end_dt:
            usages = [u for u in usages if u.timestamp <= end_dt]

        # Build CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(
            [
                "Timestamp",
                "Prompt ID",
                "Prompt Name",
                "Version",
                "Input Tokens",
                "Output Tokens",
                "Total Tokens",
                "Latency (ms)",
                "Model Provider",
                "Model Name",
                "Success",
                "Error Message",
                "User Rating",
                "Workspace ID",
                "User ID",
            ]
        )

        # Rows
        for usage in sorted(usages, key=lambda u: u.timestamp, reverse=True):
            writer.writerow(
                [
                    usage.timestamp.isoformat(),
                    usage.prompt_id,
                    usage.prompt_name,
                    usage.prompt_version,
                    usage.input_tokens,
                    usage.output_tokens,
                    usage.total_tokens,
                    round(usage.latency_ms, 2),
                    usage.model_provider,
                    usage.model_name,
                    "Yes" if usage.success else "No",
                    usage.error_message or "",
                    usage.user_rating or "",
                    usage.workspace_id or "",
                    usage.user_id or "",
                ]
            )

        return output.getvalue()


__all__ = ["PromptRouterService"]
