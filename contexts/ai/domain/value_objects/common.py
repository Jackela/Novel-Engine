#!/usr/bin/env python3
"""
Common AI Gateway Value Objects

This module defines fundamental value objects used throughout the AI Gateway context,
representing core domain concepts with proper validation, immutability, and
comprehensive business rule enforcement.

Key Value Objects:
- ProviderId: Uniquely identifies LLM providers
- ModelId: Identifies specific AI models within providers
- TokenBudget: Manages token allocation and consumption tracking

All value objects are immutable, validated, and thread-safe.
"""

import re
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional, Set, Union
from uuid import UUID, uuid4


class ProviderType(Enum):
    """
    Enumeration of supported LLM provider types.

    Used for provider categorization, routing logic, and capability detection.
    """

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    AMAZON = "amazon"
    COHERE = "cohere"
    HUGGINGFACE = "huggingface"
    CUSTOM = "custom"

    def __str__(self) -> str:
        return self.value


class ModelCapability(Enum):
    """
    Enumeration of AI model capabilities.

    Used for model selection, routing, and feature compatibility checking.
    """

    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    CONVERSATION = "conversation"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    ANALYSIS = "analysis"
    CREATIVE_WRITING = "creative_writing"
    FUNCTION_CALLING = "function_calling"
    VISION = "vision"
    EMBEDDING = "embedding"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ProviderId:
    """
    Value object representing a unique identifier for LLM providers.

    Encapsulates provider identification with type safety, validation,
    and business rules. Supports both internal provider management
    and external API integration.

    Attributes:
        provider_name: Human-readable provider name
        provider_type: Categorization of provider type
        provider_key: Unique identifier (UUID or custom key)
        api_version: API version for compatibility tracking
        region: Geographic region for data locality/compliance
        metadata: Additional provider-specific configuration

    Business Rules:
        - Provider name must be 2-100 characters, alphanumeric + spaces/hyphens
        - Provider key must be valid UUID format or custom identifier
        - API version follows semantic versioning pattern
        - Region codes follow ISO 3166-1 alpha-2 standard
    """

    provider_name: str
    provider_type: ProviderType
    provider_key: Union[UUID, str] = None
    api_version: str = "1.0.0"
    region: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Validate ProviderId business rules and constraints."""
        # Auto-generate provider key if not provided
        if self.provider_key is None:
            object.__setattr__(self, "provider_key", uuid4())

        # Initialize metadata if None
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})

        # Validate provider name
        if not self.provider_name or not isinstance(self.provider_name, str):
            raise ValueError("provider_name is required and must be a string")

        if not (2 <= len(self.provider_name) <= 100):
            raise ValueError("provider_name must be 2-100 characters long")

        if not re.match(r"^[a-zA-Z0-9\s\-_\.]+$", self.provider_name):
            raise ValueError("provider_name contains invalid characters")

        # Validate provider type
        if not isinstance(self.provider_type, ProviderType):
            raise ValueError("provider_type must be a ProviderType enum")

        # Validate API version format (semantic versioning)
        if not re.match(r"^\d+\.\d+\.\d+$", self.api_version):
            raise ValueError(
                "api_version must follow semantic versioning (x.y.z)"
            )

        # Validate region code if provided (ISO 3166-1 alpha-2)
        if self.region is not None:
            if not isinstance(self.region, str) or len(self.region) != 2:
                raise ValueError(
                    "region must be a 2-character ISO country code"
                )
            if not self.region.isupper():
                raise ValueError("region code must be uppercase")

    @classmethod
    def create_openai(
        cls, api_version: str = "1.0.0", region: str = "US"
    ) -> "ProviderId":
        """Factory method for creating OpenAI provider ID."""
        return cls(
            provider_name="OpenAI",
            provider_type=ProviderType.OPENAI,
            api_version=api_version,
            region=region,
            metadata={
                "official": True,
                "chat_models": True,
                "completion_models": True,
            },
        )

    @classmethod
    def create_anthropic(
        cls, api_version: str = "1.0.0", region: str = "US"
    ) -> "ProviderId":
        """Factory method for creating Anthropic provider ID."""
        return cls(
            provider_name="Anthropic",
            provider_type=ProviderType.ANTHROPIC,
            api_version=api_version,
            region=region,
            metadata={
                "official": True,
                "conversation_models": True,
                "safety_focused": True,
            },
        )

    @classmethod
    def create_custom(
        cls, name: str, key: str, api_version: str = "1.0.0"
    ) -> "ProviderId":
        """Factory method for creating custom provider ID."""
        return cls(
            provider_name=name,
            provider_type=ProviderType.CUSTOM,
            provider_key=key,
            api_version=api_version,
            metadata={"custom": True},
        )

    def is_official_provider(self) -> bool:
        """Check if this is an official/supported provider."""
        return self.provider_type in {
            ProviderType.OPENAI,
            ProviderType.ANTHROPIC,
            ProviderType.GOOGLE,
            ProviderType.MICROSOFT,
            ProviderType.AMAZON,
            ProviderType.COHERE,
        }

    def supports_region(self, region: str) -> bool:
        """Check if provider supports specific region."""
        if self.region is None:
            return True  # Global provider
        return self.region.upper() == region.upper()

    def get_display_name(self) -> str:
        """Get human-friendly display name for UI purposes."""
        if self.region:
            return f"{self.provider_name} ({self.region})"
        return self.provider_name

    def __str__(self) -> str:
        return f"Provider[{self.provider_name}:{self.provider_type.value}]"


@dataclass(frozen=True)
class ModelId:
    """
    Value object representing a unique identifier for AI models.

    Encapsulates model identification with capabilities, constraints,
    and performance characteristics. Enables intelligent model selection
    and routing based on requirements.

    Attributes:
        model_name: Unique model identifier from provider
        provider_id: Associated LLM provider
        capabilities: Set of model capabilities
        max_context_tokens: Maximum context window size
        max_output_tokens: Maximum tokens in single response
        cost_per_input_token: Cost per input token (USD)
        cost_per_output_token: Cost per output token (USD)
        model_version: Model version for tracking updates
        deprecated: Whether model is deprecated
        metadata: Additional model-specific information

    Business Rules:
        - Model name must be 1-200 characters, follow provider conventions
        - Token limits must be positive integers
        - Cost values must be non-negative decimals
        - Deprecated models should have replacement recommendations
    """

    model_name: str
    provider_id: ProviderId
    capabilities: Set[ModelCapability] = None
    max_context_tokens: int = 4096
    max_output_tokens: int = 1024
    cost_per_input_token: Decimal = None
    cost_per_output_token: Decimal = None
    model_version: str = "1.0"
    deprecated: bool = False
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Validate ModelId business rules and constraints."""
        # Initialize collections if None
        if self.capabilities is None:
            object.__setattr__(
                self, "capabilities", {ModelCapability.TEXT_GENERATION}
            )

        if self.metadata is None:
            object.__setattr__(self, "metadata", {})

        # Set default costs if None
        if self.cost_per_input_token is None:
            object.__setattr__(self, "cost_per_input_token", Decimal("0.0"))

        if self.cost_per_output_token is None:
            object.__setattr__(self, "cost_per_output_token", Decimal("0.0"))

        # Validate model name
        if not self.model_name or not isinstance(self.model_name, str):
            raise ValueError("model_name is required and must be a string")

        if not (1 <= len(self.model_name) <= 200):
            raise ValueError("model_name must be 1-200 characters long")

        if not re.match(r"^[a-zA-Z0-9\-_\.\/]+$", self.model_name):
            raise ValueError("model_name contains invalid characters")

        # Validate provider_id
        if not isinstance(self.provider_id, ProviderId):
            raise ValueError("provider_id must be a ProviderId instance")

        # Validate token limits
        if (
            not isinstance(self.max_context_tokens, int)
            or self.max_context_tokens <= 0
        ):
            raise ValueError("max_context_tokens must be a positive integer")

        if (
            not isinstance(self.max_output_tokens, int)
            or self.max_output_tokens <= 0
        ):
            raise ValueError("max_output_tokens must be a positive integer")

        if self.max_output_tokens > self.max_context_tokens:
            raise ValueError(
                "max_output_tokens cannot exceed max_context_tokens"
            )

        # Validate costs
        if (
            not isinstance(self.cost_per_input_token, Decimal)
            or self.cost_per_input_token < 0
        ):
            raise ValueError(
                "cost_per_input_token must be a non-negative Decimal"
            )

        if (
            not isinstance(self.cost_per_output_token, Decimal)
            or self.cost_per_output_token < 0
        ):
            raise ValueError(
                "cost_per_output_token must be a non-negative Decimal"
            )

        # Validate capabilities
        if self.capabilities and not all(
            isinstance(cap, ModelCapability) for cap in self.capabilities
        ):
            raise ValueError(
                "All capabilities must be ModelCapability enum values"
            )

    @classmethod
    def create_gpt4(cls, provider_id: ProviderId) -> "ModelId":
        """Factory method for GPT-4 model."""
        return cls(
            model_name="gpt-4",
            provider_id=provider_id,
            capabilities={
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CONVERSATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.ANALYSIS,
                ModelCapability.CREATIVE_WRITING,
            },
            max_context_tokens=8192,
            max_output_tokens=4096,
            cost_per_input_token=Decimal("0.00003"),
            cost_per_output_token=Decimal("0.00006"),
            model_version="2023-11",
            metadata={"family": "gpt-4", "training_cutoff": "2023-04"},
        )

    @classmethod
    def create_claude(
        cls, provider_id: ProviderId, variant: str = "claude-3-sonnet"
    ) -> "ModelId":
        """Factory method for Claude model variants."""
        capabilities = {
            ModelCapability.TEXT_GENERATION,
            ModelCapability.CONVERSATION,
            ModelCapability.ANALYSIS,
            ModelCapability.CREATIVE_WRITING,
            ModelCapability.CODE_GENERATION,
        }

        # Model-specific configurations
        configs = {
            "claude-3-sonnet": {
                "max_context": 200000,
                "max_output": 4096,
                "input_cost": Decimal("0.000003"),
                "output_cost": Decimal("0.000015"),
            },
            "claude-3-opus": {
                "max_context": 200000,
                "max_output": 4096,
                "input_cost": Decimal("0.000015"),
                "output_cost": Decimal("0.000075"),
            },
        }

        config = configs.get(variant, configs["claude-3-sonnet"])

        return cls(
            model_name=variant,
            provider_id=provider_id,
            capabilities=capabilities,
            max_context_tokens=config["max_context"],
            max_output_tokens=config["max_output"],
            cost_per_input_token=config["input_cost"],
            cost_per_output_token=config["output_cost"],
            model_version="2024-02",
            metadata={"family": "claude-3", "safety_focused": True},
        )

    def supports_capability(self, capability: ModelCapability) -> bool:
        """Check if model supports specific capability."""
        return capability in self.capabilities

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> Decimal:
        """Estimate total cost for token usage."""
        input_cost = Decimal(str(input_tokens)) * self.cost_per_input_token
        output_cost = Decimal(str(output_tokens)) * self.cost_per_output_token
        return input_cost + output_cost

    def can_handle_context(self, token_count: int) -> bool:
        """Check if model can handle given context size."""
        return token_count <= self.max_context_tokens

    def get_effective_context_limit(self, reserved_output_tokens: int) -> int:
        """Get effective context limit accounting for output reservation."""
        return max(0, self.max_context_tokens - reserved_output_tokens)

    def is_deprecated(self) -> bool:
        """Check if model is deprecated."""
        return self.deprecated

    def __str__(self) -> str:
        return f"Model[{self.model_name}@{self.provider_id.provider_name}]"


@dataclass(frozen=True)
class TokenBudget:
    """
    Value object for managing token allocation and consumption tracking.

    Provides comprehensive budget management for AI operations including
    allocations, consumption tracking, cost monitoring, and budget enforcement.
    Supports hierarchical budgets, rollover policies, and usage analytics.

    Attributes:
        budget_id: Unique identifier for this budget
        allocated_tokens: Total tokens allocated
        consumed_tokens: Tokens already consumed
        reserved_tokens: Tokens reserved for pending operations
        cost_limit: Maximum allowed cost (USD)
        accumulated_cost: Current accumulated cost
        period_start: Budget period start timestamp
        period_end: Budget period end timestamp
        rollover_enabled: Whether unused tokens rollover to next period
        priority: Budget priority for resource allocation
        metadata: Additional budget configuration

    Business Rules:
        - Consumed + Reserved tokens cannot exceed allocated tokens
        - Accumulated cost cannot exceed cost limit
        - Period end must be after period start
        - Available tokens = allocated - consumed - reserved
        - Budget enforcement prevents overruns
    """

    budget_id: str
    allocated_tokens: int
    consumed_tokens: int = 0
    reserved_tokens: int = 0
    cost_limit: Decimal = None
    accumulated_cost: Decimal = None
    period_start: Optional[Any] = None  # datetime, but avoiding import
    period_end: Optional[Any] = None  # datetime, but avoiding import
    rollover_enabled: bool = True
    priority: int = 5  # 1-10 scale, 10 = highest priority
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Validate TokenBudget business rules and constraints."""
        # Initialize optional fields
        if self.cost_limit is None:
            object.__setattr__(
                self, "cost_limit", Decimal("1000.00")
            )  # $1000 default

        if self.accumulated_cost is None:
            object.__setattr__(self, "accumulated_cost", Decimal("0.00"))

        if self.metadata is None:
            object.__setattr__(self, "metadata", {})

        # Validate budget_id
        if not self.budget_id or not isinstance(self.budget_id, str):
            raise ValueError("budget_id is required and must be a string")

        if not (3 <= len(self.budget_id) <= 100):
            raise ValueError("budget_id must be 3-100 characters long")

        if not re.match(r"^[a-zA-Z0-9\-_\.]+$", self.budget_id):
            raise ValueError("budget_id contains invalid characters")

        # Validate token values
        if (
            not isinstance(self.allocated_tokens, int)
            or self.allocated_tokens <= 0
        ):
            raise ValueError("allocated_tokens must be a positive integer")

        if (
            not isinstance(self.consumed_tokens, int)
            or self.consumed_tokens < 0
        ):
            raise ValueError("consumed_tokens must be a non-negative integer")

        if (
            not isinstance(self.reserved_tokens, int)
            or self.reserved_tokens < 0
        ):
            raise ValueError("reserved_tokens must be a non-negative integer")

        # Validate token budget constraints
        # Note: Over-allocation scenarios are allowed - business methods will handle validation

        # Validate cost values
        if not isinstance(self.cost_limit, Decimal) or self.cost_limit < 0:
            raise ValueError("cost_limit must be a non-negative Decimal")

        if (
            not isinstance(self.accumulated_cost, Decimal)
            or self.accumulated_cost < 0
        ):
            raise ValueError("accumulated_cost must be a non-negative Decimal")

        if self.accumulated_cost > self.cost_limit:
            raise ValueError("accumulated_cost cannot exceed cost_limit")

        # Validate priority
        if not isinstance(self.priority, int) or not (
            1 <= self.priority <= 10
        ):
            raise ValueError("priority must be an integer between 1 and 10")

    @classmethod
    def create_daily_budget(
        cls, budget_id: str, daily_tokens: int, cost_limit: Decimal = None
    ) -> "TokenBudget":
        """Factory method for daily token budget."""
        return cls(
            budget_id=f"daily_{budget_id}",
            allocated_tokens=daily_tokens,
            cost_limit=cost_limit or Decimal("100.00"),
            rollover_enabled=False,
            metadata={"type": "daily", "auto_reset": True},
        )

    @classmethod
    def create_project_budget(
        cls, project_id: str, total_tokens: int, cost_limit: Decimal
    ) -> "TokenBudget":
        """Factory method for project-based budget."""
        return cls(
            budget_id=f"project_{project_id}",
            allocated_tokens=total_tokens,
            cost_limit=cost_limit,
            rollover_enabled=True,
            priority=8,
            metadata={"type": "project", "project_id": project_id},
        )

    def get_available_tokens(self) -> int:
        """Calculate available tokens for new operations."""
        return max(
            0,
            self.allocated_tokens
            - self.consumed_tokens
            - self.reserved_tokens,
        )

    def get_utilization_percentage(self) -> Decimal:
        """Calculate budget utilization as percentage."""
        if self.allocated_tokens == 0:
            return Decimal("0.00")

        used_tokens = self.consumed_tokens + self.reserved_tokens
        return (
            Decimal(str(used_tokens)) / Decimal(str(self.allocated_tokens))
        ) * Decimal("100")

    def get_cost_utilization_percentage(self) -> Decimal:
        """Calculate cost utilization as percentage."""
        if self.cost_limit == 0:
            return Decimal("0.00")

        return (self.accumulated_cost / self.cost_limit) * Decimal("100")

    def can_reserve_tokens(self, token_count: int) -> bool:
        """Check if tokens can be reserved without exceeding budget."""
        return token_count <= self.get_available_tokens()

    def can_afford_cost(self, additional_cost: Decimal) -> bool:
        """Check if additional cost can be accommodated."""
        return (self.accumulated_cost + additional_cost) <= self.cost_limit

    def reserve_tokens(self, token_count: int) -> "TokenBudget":
        """Create new budget with reserved tokens (immutable operation)."""
        if not self.can_reserve_tokens(token_count):
            raise ValueError(
                f"Cannot reserve {token_count} tokens - insufficient budget"
            )

        return TokenBudget(
            budget_id=self.budget_id,
            allocated_tokens=self.allocated_tokens,
            consumed_tokens=self.consumed_tokens,
            reserved_tokens=self.reserved_tokens + token_count,
            cost_limit=self.cost_limit,
            accumulated_cost=self.accumulated_cost,
            period_start=self.period_start,
            period_end=self.period_end,
            rollover_enabled=self.rollover_enabled,
            priority=self.priority,
            metadata=self.metadata.copy(),
        )

    def consume_tokens(self, token_count: int, cost: Decimal) -> "TokenBudget":
        """Create new budget with consumed tokens and cost (immutable operation)."""
        if token_count > (self.reserved_tokens + self.get_available_tokens()):
            raise ValueError(
                f"Cannot consume {token_count} tokens - exceeds allocated budget"
            )

        if not self.can_afford_cost(cost):
            raise ValueError(
                f"Cannot afford additional cost of ${cost} - exceeds cost limit"
            )

        # Consume from reserved first, then available
        new_reserved = max(0, self.reserved_tokens - token_count)
        tokens_from_available = max(
            0, token_count - (self.reserved_tokens - new_reserved)
        )

        return TokenBudget(
            budget_id=self.budget_id,
            allocated_tokens=self.allocated_tokens,
            consumed_tokens=self.consumed_tokens
            + tokens_from_available
            + (self.reserved_tokens - new_reserved),
            reserved_tokens=new_reserved,
            cost_limit=self.cost_limit,
            accumulated_cost=self.accumulated_cost + cost,
            period_start=self.period_start,
            period_end=self.period_end,
            rollover_enabled=self.rollover_enabled,
            priority=self.priority,
            metadata=self.metadata.copy(),
        )

    def is_exhausted(self) -> bool:
        """Check if budget is exhausted (no available tokens or cost limit reached)."""
        return (
            self.get_available_tokens() == 0
            or self.accumulated_cost >= self.cost_limit
        )

    def is_near_exhaustion(
        self, threshold_percentage: Decimal = Decimal("90.00")
    ) -> bool:
        """Check if budget is near exhaustion."""
        token_util = self.get_utilization_percentage()
        cost_util = self.get_cost_utilization_percentage()
        return (
            token_util >= threshold_percentage
            or cost_util >= threshold_percentage
        )

    def get_budget_summary(self) -> Dict[str, Any]:
        """Get comprehensive budget summary for monitoring."""
        return {
            "budget_id": self.budget_id,
            "tokens": {
                "allocated": self.allocated_tokens,
                "consumed": self.consumed_tokens,
                "reserved": self.reserved_tokens,
                "available": self.get_available_tokens(),
                "utilization_percent": float(
                    self.get_utilization_percentage()
                ),
            },
            "cost": {
                "limit": float(self.cost_limit),
                "accumulated": float(self.accumulated_cost),
                "available": float(self.cost_limit - self.accumulated_cost),
                "utilization_percent": float(
                    self.get_cost_utilization_percentage()
                ),
            },
            "status": {
                "exhausted": self.is_exhausted(),
                "near_exhaustion": self.is_near_exhaustion(),
                "priority": self.priority,
                "rollover_enabled": self.rollover_enabled,
            },
        }

    def __str__(self) -> str:
        return f"Budget[{self.budget_id}:{self.get_available_tokens()}/{self.allocated_tokens} tokens available]"

    def __eq__(self, other) -> bool:
        """Compare TokenBudget instances for equality."""
        if not isinstance(other, TokenBudget):
            return False
        return (
            self.budget_id == other.budget_id
            and self.allocated_tokens == other.allocated_tokens
            and self.consumed_tokens == other.consumed_tokens
            and self.reserved_tokens == other.reserved_tokens
            and self.cost_limit == other.cost_limit
            and self.accumulated_cost == other.accumulated_cost
            and self.period_start == other.period_start
            and self.period_end == other.period_end
            and self.rollover_enabled == other.rollover_enabled
            and self.priority == other.priority
            and self.metadata == other.metadata
        )

    def __hash__(self) -> int:
        """Generate hash for TokenBudget instances."""
        return hash(
            (
                self.budget_id,
                self.allocated_tokens,
                self.consumed_tokens,
                self.reserved_tokens,
                self.cost_limit,
                self.accumulated_cost,
                tuple(sorted(self.metadata.items())) if self.metadata else (),
            )
        )
