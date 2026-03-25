"""
Tracking Context

Context management for tracking individual LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from ...domain.models.model_registry import LLMProvider
from ...domain.models.token_usage import TokenUsage
from .token_counter import TokenCounter


def _utcnow() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


@dataclass
class TrackingContext:
    """
    Context for tracking a single LLM call.

    Attributes:
        provider: LLM provider being used
        model_name: Model name being used
        workspace_id: Optional workspace identifier
        user_id: Optional user identifier
        request_id: Optional request identifier for correlation
        metadata: Additional metadata to attach to the usage record
        start_time: Call start timestamp
        input_tokens: Pre-counted input tokens (if available)
        token_counter: TokenCounter instance for estimation
        _usage: The recorded usage (set after recording)
    """

    provider: str | LLMProvider
    model_name: str
    workspace_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=_utcnow)
    input_tokens: int | None = None
    token_counter: TokenCounter = field(default_factory=TokenCounter)
    _usage: TokenUsage | None = field(default=None, init=False, repr=False)

    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        return (datetime.now(timezone.utc) - self.start_time).total_seconds() * 1000

    def record_success(
        self,
        input_tokens: int | None = None,
        output_tokens: int = 0,
        cost_per_1m_input: float = 0.0,
        cost_per_1m_output: float = 0.0,
        response_text: str | None = None,
    ) -> TokenUsage:
        """
        Record a successful LLM call.

        Args:
            input_tokens: Actual input tokens (uses pre-counted or estimates if None)
            output_tokens: Actual output tokens
            cost_per_1m_input: Cost per 1M input tokens
            cost_per_1m_output: Cost per 1M output tokens
            response_text: Response text (for token estimation if needed)

        Returns:
            TokenUsage record
        """
        # Determine input tokens
        if input_tokens is not None:
            final_input_tokens = input_tokens
        elif self.input_tokens is not None:
            final_input_tokens = self.input_tokens
        elif response_text is not None:
            # Estimate from combined text
            prompt_length = len(str(self.metadata.get("prompt", "")))
            count_result = self.token_counter.count(
                response_text[:prompt_length] if prompt_length > 0 else ""
            )
            if count_result.is_error:
                final_input_tokens = prompt_length // 4  # Fallback
            else:
                count_res = count_result.unwrap()
                if count_res is not None:
                    final_input_tokens = count_res.token_count
                else:
                    final_input_tokens = (
                        prompt_length // 4
                    )  # Fallback when count_res is None
        else:
            final_input_tokens = 0

        # Estimate output tokens from response text if not provided
        if output_tokens == 0 and response_text is not None:
            count_result = self.token_counter.count(response_text)
            if count_result.is_error:
                output_tokens = len(response_text) // 4  # Fallback
            else:
                count_res = count_result.unwrap()
                if count_res is not None:
                    output_tokens = count_res.token_count

        latency_ms = self.elapsed_ms

        # Normalize provider to string
        if isinstance(self.provider, str):
            provider_str = self.provider
        else:
            provider_str = str(self.provider)  # type: ignore[unreachable]

        self._usage = TokenUsage.create(
            provider=provider_str,
            model_name=self.model_name,
            input_tokens=final_input_tokens,
            output_tokens=output_tokens,
            cost_per_1m_input=cost_per_1m_input,
            cost_per_1m_output=cost_per_1m_output,
            latency_ms=latency_ms,
            success=True,
            workspace_id=self.workspace_id,
            user_id=self.user_id,
            request_id=self.request_id,
            metadata=self.metadata,
            timestamp=self.start_time,
        )

        return self._usage

    def record_failure(
        self,
        error_message: str,
        input_tokens: int | None = None,
        cost_per_1m_input: float = 0.0,
        cost_per_1m_output: float = 0.0,
    ) -> TokenUsage:
        """
        Record a failed LLM call.

        Args:
            error_message: Error description
            input_tokens: Actual input tokens (uses pre-counted or estimates if None)
            cost_per_1m_input: Cost per 1M input tokens
            cost_per_1m_output: Cost per 1M output tokens

        Returns:
            TokenUsage record
        """
        # Determine input tokens
        if input_tokens is not None:
            final_input_tokens = input_tokens
        elif self.input_tokens is not None:
            final_input_tokens = self.input_tokens
        else:
            final_input_tokens = 0

        latency_ms = self.elapsed_ms

        # Normalize provider to string
        if isinstance(self.provider, str):
            provider_str = self.provider
        else:
            provider_str = str(self.provider)  # type: ignore[unreachable]

        self._usage = TokenUsage.create(
            provider=provider_str,
            model_name=self.model_name,
            input_tokens=final_input_tokens,
            output_tokens=0,
            cost_per_1m_input=cost_per_1m_input,
            cost_per_1m_output=cost_per_1m_output,
            latency_ms=latency_ms,
            success=False,
            error_message=error_message,
            workspace_id=self.workspace_id,
            user_id=self.user_id,
            request_id=self.request_id,
            metadata=self.metadata,
            timestamp=self.start_time,
        )

        return self._usage

    @property
    def usage(self) -> TokenUsage | None:
        """Get the recorded usage, if any."""
        return self._usage
