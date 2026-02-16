"""
Prompt Formatter Service

Formats prompts for different LLM families and providers.
Supports DeepSeek, Llama, and other local model prompt formats.

Constitution Compliance:
- Article II (Hexagonal): Application service with no infrastructure dependencies
- Article V (SOLID): SRP - prompt formatting only

Warzone 4: AI Brain - BRAIN-032
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import structlog

from ...domain.models.model_registry import (
    PromptFormat,
    PromptModelFamily,
)

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()


@dataclass(frozen=True, slots=True)
class PromptRequest:
    """
    Request for prompt formatting.

    Attributes:
        system_prompt: System instructions (optional)
        user_prompt: User message/input
        conversation_history: Optional list of (role, content) tuples for context
        model_family: Model family for format selection
        prompt_format: Explicit prompt format (overrides family default)
    """

    system_prompt: str | None = None
    user_prompt: str = ""
    conversation_history: list[tuple[str, str]] | None = None
    model_family: PromptModelFamily = PromptModelFamily.UNKNOWN
    prompt_format: PromptFormat | None = None


@dataclass
class FormattedPrompt:
    """
    Result of prompt formatting.

    Attributes:
        content: The formatted prompt content
        format: The format used
        is_chat_format: Whether this is a chat messages format
        messages: Chat messages if is_chat_format is True
    """

    content: str
    format: PromptFormat
    is_chat_format: bool = False
    messages: list[dict[str, str]] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "content": self.content,
            "format": self.format.value,
            "is_chat_format": self.is_chat_format,
            "messages": self.messages,
        }


class PromptFormatter:
    """
    Service for formatting prompts according to model-specific requirements.

    Why:
        - Different model families require different prompt formats
        - DeepSeek-Coder needs code-instruction format
        - Llama needs Alpaca-style instruction format
        - OpenAI/Claude/Gemini use chat messages format

    The formatter:
    1. Detects the appropriate format from model family or explicit setting
    2. Applies the correct template/pattern
    3. Returns both raw prompt and optional chat messages array

    Example:
        >>> formatter = PromptFormatter()
        >>> request = PromptRequest(
        ...     system_prompt="You are a coder.",
        ...     user_prompt="Write a hello world function.",
        ...     model_family=PromptModelFamily.DEEPSEEK_CODER
        ... )
        >>> result = formatter.format(request)
        >>> print(result.content)
    """

    # Templates for different prompt formats

    # Alpaca-style instruction format (Llama, Mistral, etc.)
    _INSTRUCTION_TEMPLATE = """### Instruction:
{system_prompt}

{user_prompt}

### Response:"""

    _INSTRUCTION_NO_SYSTEM_TEMPLATE = """### Instruction:
{user_prompt}

### Response:"""

    # DeepSeek-Coder specific format
    _CODE_INSTRUCTION_TEMPLATE = """You are an AI programming assistant.

{system_prompt}

### Instruction:
{user_prompt}

### Response:"""

    _CODE_INSTRUCTION_NO_SYSTEM_TEMPLATE = """### Instruction:
{user_prompt}

### Response:"""

    def __init__(
        self, default_format: PromptFormat = PromptFormat.CHAT_MESSAGES
    ) -> None:
        """
        Initialize the prompt formatter.

        Args:
            default_format: Default format to use when family detection fails
        """
        self._default_format = default_format

        log = logger.bind(default_format=default_format.value)
        log.info("prompt_formatter_initialized")

    def format(self, request: PromptRequest) -> FormattedPrompt:
        """
        Format a prompt according to the model family's requirements.

        Args:
            request: PromptRequest with system/user prompts and model info

        Returns:
            FormattedPrompt with formatted content and optional chat messages

        Raises:
            ValueError: If prompt format is not supported
        """
        # Determine the format to use
        prompt_format = self._determine_format(request)

        log = logger.bind(
            format=prompt_format.value,
            model_family=request.model_family.value,
            has_system_prompt=bool(request.system_prompt),
            has_history=bool(request.conversation_history),
        )

        # Format based on type (initialize result for type safety)
        result: FormattedPrompt = self._format_chat_messages(request)  # default
        match prompt_format:
            case PromptFormat.INSTRUCTION:
                result = self._format_instruction(request)
            case PromptFormat.CODE_INSTRUCTION:
                result = self._format_code_instruction(request)
            case PromptFormat.COMPLETION:
                result = self._format_completion(request)
            case PromptFormat.CHAT_MESSAGES | _:
                # CHAT_MESSAGES is the default, already set above
                if prompt_format not in (PromptFormat.CHAT_MESSAGES,):
                    log.warning("unknown_prompt_format", format=prompt_format.value)

        log.debug(
            "prompt_formatted",
            format_used=result.format.value,
            is_chat=result.is_chat_format,
            content_length=len(result.content),
        )

        return result

    def _determine_format(self, request: PromptRequest) -> PromptFormat:
        """
        Determine the prompt format to use.

        Args:
            request: PromptRequest with format hints

        Returns:
            PromptFormat to use
        """
        # Explicit format takes precedence
        if request.prompt_format:
            return request.prompt_format

        # Use model family's default
        if request.model_family != PromptModelFamily.UNKNOWN:
            return request.model_family.default_prompt_format

        # Fall back to default
        return self._default_format

    def _format_chat_messages(self, request: PromptRequest) -> FormattedPrompt:
        """
        Format as chat messages (OpenAI, Claude, Gemini style).

        Args:
            request: PromptRequest with system/user prompts

        Returns:
            FormattedPrompt with chat messages array
        """
        messages: list[dict[str, str]] = []

        # Add system message if provided
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})

        # Add conversation history if provided
        if request.conversation_history:
            for role, content in request.conversation_history:
                # Map common role names to standard format
                normalized_role = self._normalize_role(role)
                messages.append({"role": normalized_role, "content": content})

        # Add user message
        messages.append({"role": "user", "content": request.user_prompt})

        return FormattedPrompt(
            content=request.user_prompt,
            format=PromptFormat.CHAT_MESSAGES,
            is_chat_format=True,
            messages=messages,
        )

    def _format_instruction(self, request: PromptRequest) -> FormattedPrompt:
        """
        Format as instruction template (Alpaca/Llama style).

        Args:
            request: PromptRequest with system/user prompts

        Returns:
            FormattedPrompt with instruction-formatted content
        """
        if request.system_prompt:
            template = self._INSTRUCTION_TEMPLATE
            content = template.format(
                system_prompt=request.system_prompt,
                user_prompt=request.user_prompt,
            )
        else:
            template = self._INSTRUCTION_NO_SYSTEM_TEMPLATE
            content = template.format(user_prompt=request.user_prompt)

        return FormattedPrompt(
            content=content,
            format=PromptFormat.INSTRUCTION,
            is_chat_format=False,
            messages=None,
        )

    def _format_code_instruction(self, request: PromptRequest) -> FormattedPrompt:
        """
        Format as code instruction template (DeepSeek-Coder style).

        Args:
            request: PromptRequest with system/user prompts

        Returns:
            FormattedPrompt with code-instruction-formatted content
        """
        if request.system_prompt:
            template = self._CODE_INSTRUCTION_TEMPLATE
            content = template.format(
                system_prompt=request.system_prompt,
                user_prompt=request.user_prompt,
            )
        else:
            template = self._CODE_INSTRUCTION_NO_SYSTEM_TEMPLATE
            content = template.format(user_prompt=request.user_prompt)

        return FormattedPrompt(
            content=content,
            format=PromptFormat.CODE_INSTRUCTION,
            is_chat_format=False,
            messages=None,
        )

    def _format_completion(self, request: PromptRequest) -> FormattedPrompt:
        """
        Format as simple completion (single prompt string).

        Args:
            request: PromptRequest with system/user prompts

        Returns:
            FormattedPrompt with simple completion format
        """
        parts: list[str] = []

        if request.system_prompt:
            parts.append(request.system_prompt)

        parts.append(request.user_prompt)

        content = "\n\n".join(parts)

        return FormattedPrompt(
            content=content,
            format=PromptFormat.COMPLETION,
            is_chat_format=False,
            messages=None,
        )

    def _normalize_role(self, role: str) -> str:
        """
        Normalize role names to standard chat format.

        Args:
            role: Role name to normalize

        Returns:
            Normalized role name (system, user, assistant)
        """
        role_lower = role.lower().strip()

        # Map various role names to standard ones
        role_mapping: dict[str, str] = {
            "system": "system",
            "sys": "system",
            "user": "user",
            "human": "user",
            "assistant": "assistant",
            "ai": "assistant",
            "bot": "assistant",
            "model": "assistant",
        }

        return role_mapping.get(role_lower, "user")

    def format_for_model(
        self,
        system_prompt: str | None,
        user_prompt: str,
        model_name: str,
        model_family: PromptModelFamily | None = None,
        conversation_history: list[tuple[str, str]] | None = None,
    ) -> FormattedPrompt:
        """
        Convenience method to format a prompt for a specific model.

        Args:
            system_prompt: System instructions
            user_prompt: User message/input
            model_name: Model identifier for family detection
            model_family: Optional explicit model family
            conversation_history: Optional conversation history

        Returns:
            FormattedPrompt formatted for the model

        Example:
            >>> result = formatter.format_for_model(
            ...     "You are a coder.",
            ...     "Write hello world",
            ...     "deepseek-coder-v2:16b"
            ... )
        """
        # Detect family from model name if not provided
        if model_family is None:
            model_family = PromptModelFamily.from_model_name(model_name)

        request = PromptRequest(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            conversation_history=conversation_history,
            model_family=model_family,
        )

        return self.format(request)

    def get_format_for_model(self, model_name: str) -> PromptFormat:
        """
        Get the prompt format for a given model name.

        Args:
            model_name: Model identifier

        Returns:
            PromptFormat for the model
        """
        family = PromptModelFamily.from_model_name(model_name)
        return family.default_prompt_format


def create_prompt_formatter(
    default_format: PromptFormat = PromptFormat.CHAT_MESSAGES,
) -> PromptFormatter:
    """
    Factory function to create a PromptFormatter.

    Why factory:
        - Provides convenient instantiation
        - Allows for future dependency injection
        - Consistent with other service factories

    Args:
        default_format: Default format to use

    Returns:
        Configured PromptFormatter instance
    """
    return PromptFormatter(default_format=default_format)


__all__ = [
    "PromptFormatter",
    "PromptRequest",
    "FormattedPrompt",
    "create_prompt_formatter",
]
