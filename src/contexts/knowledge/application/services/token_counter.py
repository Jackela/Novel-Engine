"""
Token Counter Utility

Provides accurate token counting for multiple LLM providers.
Uses tiktoken for OpenAI models and provides fallbacks for other providers.

Constitution Compliance:
- Article II (Hexagonal): Application service utility
- Article V (SOLID): SRP - token counting only

Warzone 4: AI Brain - BRAIN-011A
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Literal

import structlog

try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

if TYPE_CHECKING:
    pass


logger = structlog.get_logger()


class LLMProvider(str, Enum):
    """LLM providers with different tokenizers.

    Why Enum:
        Type-safe provider selection with string compatibility.
    """

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    COHERE = "cohere"
    GENERIC = "generic"


class ModelFamily(str, Enum):
    """Model families within providers.

    Different model families may use different tokenizers.
    """

    # OpenAI families
    GPT4O = "gpt-4o"
    GPT4 = "gpt-4"
    GPT35 = "gpt-3.5"

    # Anthropic families
    CLAUDE_3 = "claude-3"
    CLAUDE_2 = "claude-2"

    # Gemini families
    GEMINI_1 = "gemini-1.0"
    GEMINI_2 = "gemini-2.0"

    # Generic fallback
    GENERIC = "generic"


# Mapping of model names to their families for automatic detection
MODEL_FAMILY_MAPPING: dict[str, tuple[LLMProvider, ModelFamily]] = {
    # OpenAI models
    "gpt-4o": (LLMProvider.OPENAI, ModelFamily.GPT4O),
    "gpt-4o-mini": (LLMProvider.OPENAI, ModelFamily.GPT4O),
    "gpt-4-turbo": (LLMProvider.OPENAI, ModelFamily.GPT4),
    "gpt-4": (LLMProvider.OPENAI, ModelFamily.GPT4),
    "gpt-3.5-turbo": (LLMProvider.OPENAI, ModelFamily.GPT35),
    # Anthropic models
    "claude-3-5-sonnet": (LLMProvider.ANTHROPIC, ModelFamily.CLAUDE_3),
    "claude-3-5-haiku": (LLMProvider.ANTHROPIC, ModelFamily.CLAUDE_3),
    "claude-3-opus": (LLMProvider.ANTHROPIC, ModelFamily.CLAUDE_3),
    "claude-3-sonnet": (LLMProvider.ANTHROPIC, ModelFamily.CLAUDE_3),
    "claude-3-haiku": (LLMProvider.ANTHROPIC, ModelFamily.CLAUDE_3),
    # Gemini models
    "gemini-2.0-flash": (LLMProvider.GEMINI, ModelFamily.GEMINI_2),
    "gemini-1.5-pro": (LLMProvider.GEMINI, ModelFamily.GEMINI_1),
    "gemini-1.5-flash": (LLMProvider.GEMINI, ModelFamily.GEMINI_1),
    "gemini-pro": (LLMProvider.GEMINI, ModelFamily.GEMINI_1),
}


# Encoding names for tiktoken by model family
TIKTOKEN_ENCODING_MAP: dict[ModelFamily, str] = {
    ModelFamily.GPT4O: "o200k_base",  # GPT-4o encoding
    ModelFamily.GPT4: "cl100k_base",  # GPT-4 encoding
    ModelFamily.GPT35: "cl100k_base",  # GPT-3.5-turbo encoding
}


# Fallback token ratios (chars per token) for different providers
FALLBACK_TOKEN_RATIOS: dict[LLMProvider, float] = {
    LLMProvider.OPENAI: 4.0,
    LLMProvider.ANTHROPIC: 4.0,
    LLMProvider.GEMINI: 4.0,
    LLMProvider.COHERE: 4.0,
    LLMProvider.GENERIC: 4.0,
}


@dataclass(frozen=True, slots=True)
class TokenCountResult:
    """Result of token counting operation.

    Attributes:
        token_count: Number of tokens counted
        method: Method used (tiktoken, estimation, fallback)
        provider: LLM provider used for counting
        model_family: Model family tokenizer used
    """

    token_count: int
    method: Literal["tiktoken", "estimation", "fallback"]
    provider: LLMProvider
    model_family: ModelFamily


class TokenCounter:
    """
    Token counter with support for multiple LLM providers.

    Uses tiktoken for accurate counting when available, with fallback
    to character-based estimation for unsupported providers.

    Provider Tokenization:
        - OpenAI: Uses tiktoken with model-specific encodings
        - Anthropic: Uses tiktoken cl100k_base (close approximation)
        - Gemini: Uses character-based estimation
        - Generic: Uses character-based estimation

    Example:
        >>> counter = TokenCounter()
        >>> result = counter.count("Hello, world!", model="gpt-4")
        >>> print(result.token_count)
        4
        >>> # Count for Anthropic (uses OpenAI encoding as approximation)
        >>> result = counter.count("Hello, world!", provider=LLMProvider.ANTHROPIC)
        >>> print(result.method)
        'tiktoken'
    """

    def __init__(
        self,
        default_provider: LLMProvider = LLMProvider.OPENAI,
        default_model: str | None = None,
        use_tiktoken: bool = True,
    ):
        """
        Initialize the token counter.

        Args:
            default_provider: Default LLM provider for counting
            default_model: Default model name (auto-detects provider/family)
            use_tiktoken: Whether to use tiktoken when available
        """
        self._default_provider = default_provider
        self._default_model = default_model
        self._use_tiktoken = use_tiktoken and TIKTOKEN_AVAILABLE

        # Determine default provider/model from model name if provided
        if default_model:
            provider, family = self._detect_provider_and_family(default_model)
            self._default_provider = provider
            self._default_family = family
        else:
            self._default_family = self._get_default_family(default_provider)

        # Initialize tiktoken cache
        self._tiktoken_cache: dict[ModelFamily, tiktoken.Encoding] = {}

    def count(
        self,
        text: str,
        model: str | None = None,
        provider: LLMProvider | None = None,
        model_family: ModelFamily | None = None,
    ) -> TokenCountResult:
        """
        Count tokens in text.

        Args:
            text: Text to count tokens for
            model: Model name (auto-detects provider/family)
            provider: LLM provider (overrides model detection)
            model_family: Model family (overrides auto-detection)

        Returns:
            TokenCountResult with count and metadata

        Raises:
            ValueError: If text is empty or parameters are invalid
        """
        if not isinstance(text, str):
            raise ValueError(f"text must be a string, got {type(text)}")

        if not text:
            return TokenCountResult(
                token_count=0,
                method="fallback",
                provider=provider or self._default_provider,
                model_family=model_family or self._default_family,
            )

        # Detect provider and family
        detected_provider, detected_family = self._resolve_provider_and_family(
            model, provider, model_family
        )

        # Try tiktoken first for supported providers
        if self._use_tiktoken and detected_provider in {
            LLMProvider.OPENAI,
            LLMProvider.ANTHROPIC,
        }:
            try:
                token_count = self._count_with_tiktoken(text, detected_family)
                return TokenCountResult(
                    token_count=token_count,
                    method="tiktoken",
                    provider=detected_provider,
                    model_family=detected_family,
                )
            except Exception as e:
                logger.warning(
                    "tiktoken_counting_failed",
                    text_length=len(text),
                    provider=detected_provider.value,
                    family=detected_family.value,
                    error=str(e),
                )
                # Fall through to estimation

        # Use character-based estimation
        token_count = self._count_by_estimation(text, detected_provider)

        return TokenCountResult(
            token_count=token_count,
            method="tiktoken" if self._use_tiktoken else "estimation",
            provider=detected_provider,
            model_family=detected_family,
        )

    def count_batch(
        self,
        texts: list[str],
        model: str | None = None,
        provider: LLMProvider | None = None,
        model_family: ModelFamily | None = None,
    ) -> list[TokenCountResult]:
        """
        Count tokens for multiple texts.

        Args:
            texts: List of texts to count
            model: Model name (auto-detects provider/family)
            provider: LLM provider (overrides model detection)
            model_family: Model family (overrides auto-detection)

        Returns:
            List of TokenCountResult in same order as inputs
        """
        detected_provider, detected_family = self._resolve_provider_and_family(
            model, provider, model_family
        )

        results: list[TokenCountResult] = []

        # For tiktoken, we can batch encode
        if self._use_tiktoken and detected_provider in {
            LLMProvider.OPENAI,
            LLMProvider.ANTHROPIC,
        }:
            try:
                encoding = self._get_tiktoken_encoding(detected_family)
                for text in texts:
                    if not text:
                        results.append(
                            TokenCountResult(
                                token_count=0,
                                method="tiktoken",
                                provider=detected_provider,
                                model_family=detected_family,
                            )
                        )
                    else:
                        token_count = len(encoding.encode(text))
                        results.append(
                            TokenCountResult(
                                token_count=token_count,
                                method="tiktoken",
                                provider=detected_provider,
                                model_family=detected_family,
                            )
                        )
                return results
            except Exception as e:
                logger.warning(
                    "tiktoken_batch_counting_failed",
                    text_count=len(texts),
                    provider=detected_provider.value,
                    error=str(e),
                )
                # Fall through to individual estimation

        # Fallback to individual counting
        for text in texts:
            results.append(self.count(text, model, provider, model_family))

        return results

    def count_from_messages(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        provider: LLMProvider | None = None,
    ) -> TokenCountResult:
        """
        Count tokens for chat message format.

        Accounts for message format overhead (role, separators).

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name for tokenization
            provider: LLM provider (overrides model detection)

        Returns:
            Total token count including format overhead
        """
        detected_provider, detected_family = self._resolve_provider_and_family(
            model, provider, None
        )

        # Base tokens for message format (approximate)
        # Each message has ~4 tokens for format: <im_start>{role}\n{content}<im_end>
        format_overhead_per_message = 4

        total_tokens = 0
        for message in messages:
            content = message.get("content", "")
            role = message.get("role", "user")

            # Count content
            content_count = self.count(
                content,
                model,
                provider,
                detected_family,
            ).token_count

            # Count role (typically 1-3 tokens)
            role_count = len(role.split()) + 1

            # Add format overhead
            total_tokens += content_count + role_count + format_overhead_per_message

        # Add reply priming tokens
        total_tokens += 3  # <im_start>assistant\n

        return TokenCountResult(
            token_count=total_tokens,
            method="tiktoken" if self._use_tiktoken else "estimation",
            provider=detected_provider,
            model_family=detected_family,
        )

    def estimate_max_chunks(
        self,
        text: str,
        max_tokens: int,
        model: str | None = None,
    ) -> int:
        """
        Estimate how many chunks of this text fit in token budget.

        Args:
            text: Text to check
            max_tokens: Token budget
            model: Model name for tokenization

        Returns:
            Maximum number of complete chunks that fit
        """
        result = self.count(text, model=model)
        if result.token_count == 0:
            return 0
        return max_tokens // result.token_count

    def truncate_to_tokens(
        self,
        text: str,
        max_tokens: int,
        model: str | None = None,
        add_ellipsis: bool = False,
    ) -> str:
        """
        Truncate text to fit within token budget.

        Args:
            text: Text to truncate
            max_tokens: Maximum tokens allowed
            model: Model name for tokenization
            add_ellipsis: Add "..." if truncated

        Returns:
            Truncated text (or original if under budget)
        """
        result = self.count(text, model=model)
        if result.token_count <= max_tokens:
            return text

        # Estimate character limit (rough approximation)
        chars_per_token = len(text) / result.token_count
        max_chars = int(max_tokens * chars_per_token * 0.9)  # 90% to be safe

        truncated = text[:max_chars]

        if add_ellipsis and len(truncated) < len(text):
            truncated = truncated[: max_chars - 3] + "..."

        return truncated

    def is_available(self) -> dict[str, bool]:
        """
        Check availability of token counting methods.

        Returns:
            Dict with availability status for each method
        """
        return {
            "tiktoken": TIKTOKEN_AVAILABLE,
            "estimation": True,  # Always available
        }

    def _resolve_provider_and_family(
        self,
        model: str | None,
        provider: LLMProvider | None,
        model_family: ModelFamily | None,
    ) -> tuple[LLMProvider, ModelFamily]:
        """Resolve provider and model family from inputs."""
        if model:
            detected_provider, detected_family = self._detect_provider_and_family(model)
            resolved_provider = provider or detected_provider
            resolved_family = model_family or detected_family
        else:
            resolved_provider = provider or self._default_provider
            resolved_family = model_family or self._default_family

        return resolved_provider, resolved_family

    def _detect_provider_and_family(
        self, model: str
    ) -> tuple[LLMProvider, ModelFamily]:
        """Detect provider and family from model name."""
        # Check exact matches
        if model in MODEL_FAMILY_MAPPING:
            return MODEL_FAMILY_MAPPING[model]

        # Check prefix matches
        for model_pattern, (provider, family) in MODEL_FAMILY_MAPPING.items():
            if model.lower().startswith(model_pattern.lower()):
                return provider, family

        # Check provider keywords
        model_lower = model.lower()
        if "gpt" in model_lower:
            if "gpt-4o" in model_lower or "gpt4o" in model_lower:
                return LLMProvider.OPENAI, ModelFamily.GPT4O
            return LLMProvider.OPENAI, ModelFamily.GPT4
        if "claude" in model_lower:
            return LLMProvider.ANTHROPIC, ModelFamily.CLAUDE_3
        if "gemini" in model_lower:
            if "gemini-2" in model_lower or "gemini2" in model_lower:
                return LLMProvider.GEMINI, ModelFamily.GEMINI_2
            return LLMProvider.GEMINI, ModelFamily.GEMINI_1

        # Default fallback
        return LLMProvider.GENERIC, ModelFamily.GENERIC

    def _get_default_family(self, provider: LLMProvider) -> ModelFamily:
        """Get default model family for provider."""
        if provider == LLMProvider.OPENAI:
            return ModelFamily.GPT4
        elif provider == LLMProvider.ANTHROPIC:
            return ModelFamily.CLAUDE_3
        elif provider == LLMProvider.GEMINI:
            return ModelFamily.GEMINI_1
        return ModelFamily.GENERIC

    def _count_with_tiktoken(self, text: str, family: ModelFamily) -> int:
        """Count tokens using tiktoken."""
        encoding = self._get_tiktoken_encoding(family)
        return len(encoding.encode(text))

    def _get_tiktoken_encoding(self, family: ModelFamily) -> tiktoken.Encoding:
        """Get or create tiktoken encoding for model family."""
        if family in self._tiktoken_cache:
            return self._tiktoken_cache[family]

        encoding_name = TIKTOKEN_ENCODING_MAP.get(family, "cl100k_base")
        encoding = tiktoken.get_encoding(encoding_name)
        self._tiktoken_cache[family] = encoding
        return encoding

    def _count_by_estimation(self, text: str, provider: LLMProvider) -> int:
        """Count tokens using character-based estimation."""
        ratio = FALLBACK_TOKEN_RATIOS.get(provider, 4.0)
        return max(1, int(len(text) / ratio))


def create_token_counter(
    model: str | None = None,
    provider: LLMProvider | None = None,
) -> TokenCounter:
    """
    Factory function to create a configured TokenCounter.

    Args:
        model: Default model name (auto-detects provider)
        provider: Default provider (used if model not specified)

    Returns:
        Configured TokenCounter instance

    Example:
        >>> counter = create_token_counter(model="gpt-4")
        >>> result = counter.count("Hello, world!")
        >>> print(result.token_count)
    """
    if provider:
        return TokenCounter(default_provider=provider, use_tiktoken=TIKTOKEN_AVAILABLE)
    if model:
        return TokenCounter(default_model=model, use_tiktoken=TIKTOKEN_AVAILABLE)
    return TokenCounter(use_tiktoken=TIKTOKEN_AVAILABLE)


__all__ = [
    "TokenCounter",
    "LLMProvider",
    "ModelFamily",
    "TokenCountResult",
    "create_token_counter",
    "TIKTOKEN_AVAILABLE",
]
