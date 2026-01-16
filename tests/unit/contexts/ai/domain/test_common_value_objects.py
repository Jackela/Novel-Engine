#!/usr/bin/env python3
"""
Comprehensive Unit Tests for AI Gateway Common Value Objects

Test suite covering ProviderId, ModelId, and TokenBudget value objects
with creation, validation, business logic, enums, properties, and factory methods
in the AI Gateway Context domain layer.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from src.contexts.ai.domain.value_objects.common import (
    ModelCapability,
    ModelId,
    ProviderId,
    ProviderType,
    TokenBudget,
)


class TestProviderTypeEnum:
    """Test suite for ProviderType enum."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_all_provider_types_exist(self):
        """Test that all expected provider types are defined."""
        expected_types = {
            "OPENAI",
            "ANTHROPIC",
            "GOOGLE",
            "MICROSOFT",
            "AMAZON",
            "COHERE",
            "HUGGINGFACE",
            "CUSTOM",
        }

        actual_types = {item.name for item in ProviderType}
        assert actual_types == expected_types

    @pytest.mark.unit
    @pytest.mark.fast
    def test_provider_type_string_values(self):
        """Test that provider type enum values have correct string representations."""
        assert ProviderType.OPENAI.value == "openai"
        assert ProviderType.ANTHROPIC.value == "anthropic"
        assert ProviderType.GOOGLE.value == "google"
        assert ProviderType.MICROSOFT.value == "microsoft"
        assert ProviderType.AMAZON.value == "amazon"
        assert ProviderType.COHERE.value == "cohere"
        assert ProviderType.HUGGINGFACE.value == "huggingface"
        assert ProviderType.CUSTOM.value == "custom"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_provider_type_str_method(self):
        """Test that __str__ method returns the value."""
        assert str(ProviderType.OPENAI) == "openai"
        assert str(ProviderType.CUSTOM) == "custom"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_provider_type_uniqueness(self):
        """Test that all provider type values are unique."""
        values = [item.value for item in ProviderType]
        assert len(values) == len(set(values))

    @pytest.mark.unit
    @pytest.mark.fast
    def test_provider_type_membership(self):
        """Test provider type membership operations."""
        assert ProviderType.OPENAI in ProviderType
        assert "openai" == ProviderType.OPENAI.value
        assert ProviderType.OPENAI == ProviderType("openai")


class TestModelCapabilityEnum:
    """Test suite for ModelCapability enum."""

    @pytest.mark.unit
    def test_all_model_capabilities_exist(self):
        """Test that all expected model capabilities are defined."""
        expected_capabilities = {
            "TEXT_GENERATION",
            "CODE_GENERATION",
            "CONVERSATION",
            "SUMMARIZATION",
            "TRANSLATION",
            "ANALYSIS",
            "CREATIVE_WRITING",
            "FUNCTION_CALLING",
            "VISION",
            "EMBEDDING",
        }

        actual_capabilities = {item.name for item in ModelCapability}
        assert actual_capabilities == expected_capabilities

    @pytest.mark.unit
    def test_model_capability_string_values(self):
        """Test that model capability enum values have correct string representations."""
        assert ModelCapability.TEXT_GENERATION.value == "text_generation"
        assert ModelCapability.CODE_GENERATION.value == "code_generation"
        assert ModelCapability.CONVERSATION.value == "conversation"
        assert ModelCapability.SUMMARIZATION.value == "summarization"
        assert ModelCapability.TRANSLATION.value == "translation"
        assert ModelCapability.ANALYSIS.value == "analysis"
        assert ModelCapability.CREATIVE_WRITING.value == "creative_writing"
        assert ModelCapability.FUNCTION_CALLING.value == "function_calling"
        assert ModelCapability.VISION.value == "vision"
        assert ModelCapability.EMBEDDING.value == "embedding"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_model_capability_str_method(self):
        """Test that __str__ method returns the value."""
        assert str(ModelCapability.TEXT_GENERATION) == "text_generation"
        assert str(ModelCapability.FUNCTION_CALLING) == "function_calling"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_model_capability_uniqueness(self):
        """Test that all model capability values are unique."""
        values = [item.value for item in ModelCapability]
        assert len(values) == len(set(values))

    @pytest.mark.unit
    @pytest.mark.fast
    def test_model_capability_membership(self):
        """Test model capability membership operations."""
        assert ModelCapability.TEXT_GENERATION in ModelCapability
        assert "text_generation" == ModelCapability.TEXT_GENERATION.value
        assert ModelCapability.TEXT_GENERATION == ModelCapability("text_generation")


class TestProviderIdCreation:
    """Test suite for ProviderId creation and initialization."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_minimal_provider_id(self):
        """Test creating ProviderId with minimal required fields."""
        provider_id = ProviderId(
            provider_name="Test Provider", provider_type=ProviderType.CUSTOM
        )

        assert provider_id.provider_name == "Test Provider"
        assert provider_id.provider_type == ProviderType.CUSTOM
        assert isinstance(provider_id.provider_key, UUID)  # Auto-generated
        assert provider_id.api_version == "1.0.0"
        assert provider_id.region is None
        assert provider_id.metadata == {}

    @pytest.mark.unit
    def test_create_full_provider_id(self):
        """Test creating ProviderId with all fields specified."""
        provider_key = uuid4()
        metadata = {"custom_field": "value", "enabled": True}

        provider_id = ProviderId(
            provider_name="Full Provider",
            provider_type=ProviderType.OPENAI,
            provider_key=provider_key,
            api_version="2.1.3",
            region="US",
            metadata=metadata,
        )

        assert provider_id.provider_name == "Full Provider"
        assert provider_id.provider_type == ProviderType.OPENAI
        assert provider_id.provider_key == provider_key
        assert provider_id.api_version == "2.1.3"
        assert provider_id.region == "US"
        assert provider_id.metadata == metadata

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_provider_id_with_string_key(self):
        """Test creating ProviderId with string provider key."""
        provider_id = ProviderId(
            provider_name="String Key Provider",
            provider_type=ProviderType.CUSTOM,
            provider_key="custom-string-key-123",
        )

        assert provider_id.provider_key == "custom-string-key-123"

    @pytest.mark.unit
    def test_frozen_dataclass_immutability(self):
        """Test that ProviderId instances are immutable."""
        provider_id = ProviderId(
            provider_name="Immutable Provider", provider_type=ProviderType.CUSTOM
        )

        with pytest.raises(AttributeError):
            provider_id.provider_name = "Modified Name"

        with pytest.raises(AttributeError):
            provider_id.provider_type = ProviderType.OPENAI


class TestProviderIdValidation:
    """Test suite for ProviderId validation and constraints."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_empty_provider_name_raises_error(self):
        """Test that empty provider name raises validation error."""
        with pytest.raises(ValueError, match="provider_name is required"):
            ProviderId(provider_name="", provider_type=ProviderType.CUSTOM)

        with pytest.raises(ValueError, match="provider_name is required"):
            ProviderId(provider_name=None, provider_type=ProviderType.CUSTOM)

    @pytest.mark.unit
    def test_invalid_provider_name_length_raises_errors(self):
        """Test that invalid provider name lengths raise validation errors."""
        # Too short
        with pytest.raises(
            ValueError, match="provider_name must be 2-100 characters long"
        ):
            ProviderId(provider_name="A", provider_type=ProviderType.CUSTOM)

        # Too long
        long_name = "A" * 101
        with pytest.raises(
            ValueError, match="provider_name must be 2-100 characters long"
        ):
            ProviderId(provider_name=long_name, provider_type=ProviderType.CUSTOM)

    @pytest.mark.unit
    def test_invalid_provider_name_characters_raise_errors(self):
        """Test that invalid provider name characters raise validation errors."""
        with pytest.raises(
            ValueError, match="provider_name contains invalid characters"
        ):
            ProviderId(provider_name="Invalid@Name!", provider_type=ProviderType.CUSTOM)

        with pytest.raises(
            ValueError, match="provider_name contains invalid characters"
        ):
            ProviderId(
                provider_name="Name<with>brackets", provider_type=ProviderType.CUSTOM
            )

    @pytest.mark.unit
    def test_valid_provider_name_characters(self):
        """Test that valid provider name characters are accepted."""
        valid_names = [
            "OpenAI Provider",
            "custom-provider_v2",
            "Provider123",
            "My.Provider.Name",
        ]

        for name in valid_names:
            provider_id = ProviderId(
                provider_name=name, provider_type=ProviderType.CUSTOM
            )
            assert provider_id.provider_name == name

    @pytest.mark.unit
    def test_invalid_provider_type_raises_error(self):
        """Test that invalid provider type raises validation error."""
        with pytest.raises(
            ValueError, match="provider_type must be a ProviderType enum"
        ):
            ProviderId(provider_name="Test", provider_type="openai")  # Should be enum

    @pytest.mark.unit
    def test_invalid_api_version_format_raises_error(self):
        """Test that invalid API version format raises validation error."""
        with pytest.raises(
            ValueError, match="api_version must follow semantic versioning"
        ):
            ProviderId(
                provider_name="Test",
                provider_type=ProviderType.CUSTOM,
                api_version="1.0",  # Missing patch version
            )

        with pytest.raises(
            ValueError, match="api_version must follow semantic versioning"
        ):
            ProviderId(
                provider_name="Test",
                provider_type=ProviderType.CUSTOM,
                api_version="v1.0.0",  # Extra 'v' prefix
            )

    @pytest.mark.unit
    @pytest.mark.fast
    def test_valid_api_version_formats(self):
        """Test that valid API version formats are accepted."""
        valid_versions = ["1.0.0", "2.1.3", "10.25.100"]

        for version in valid_versions:
            provider_id = ProviderId(
                provider_name="Test",
                provider_type=ProviderType.CUSTOM,
                api_version=version,
            )
            assert provider_id.api_version == version

    @pytest.mark.unit
    def test_invalid_region_code_raises_errors(self):
        """Test that invalid region codes raise validation errors."""
        # Wrong length
        with pytest.raises(
            ValueError, match="region must be a 2-character ISO country code"
        ):
            ProviderId(
                provider_name="Test",
                provider_type=ProviderType.CUSTOM,
                region="USA",  # Too long
            )

        # Not uppercase
        with pytest.raises(ValueError, match="region code must be uppercase"):
            ProviderId(
                provider_name="Test",
                provider_type=ProviderType.CUSTOM,
                region="us",  # Should be uppercase
            )

    @pytest.mark.unit
    @pytest.mark.fast
    def test_valid_region_codes(self):
        """Test that valid region codes are accepted."""
        valid_regions = ["US", "CA", "EU", "JP", "AU"]

        for region in valid_regions:
            provider_id = ProviderId(
                provider_name="Test", provider_type=ProviderType.CUSTOM, region=region
            )
            assert provider_id.region == region


class TestProviderIdFactoryMethods:
    """Test suite for ProviderId factory methods."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_create_openai_default(self):
        """Test creating OpenAI provider with default parameters."""
        provider_id = ProviderId.create_openai()

        assert provider_id.provider_name == "OpenAI"
        assert provider_id.provider_type == ProviderType.OPENAI
        assert provider_id.api_version == "1.0.0"
        assert provider_id.region == "US"
        assert provider_id.metadata["official"] is True
        assert provider_id.metadata["chat_models"] is True
        assert provider_id.metadata["completion_models"] is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_openai_custom_params(self):
        """Test creating OpenAI provider with custom parameters."""
        provider_id = ProviderId.create_openai(api_version="2.0.0", region="CA")

        assert provider_id.provider_name == "OpenAI"
        assert provider_id.provider_type == ProviderType.OPENAI
        assert provider_id.api_version == "2.0.0"
        assert provider_id.region == "CA"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_anthropic_default(self):
        """Test creating Anthropic provider with default parameters."""
        provider_id = ProviderId.create_anthropic()

        assert provider_id.provider_name == "Anthropic"
        assert provider_id.provider_type == ProviderType.ANTHROPIC
        assert provider_id.api_version == "1.0.0"
        assert provider_id.region == "US"
        assert provider_id.metadata["official"] is True
        assert provider_id.metadata["conversation_models"] is True
        assert provider_id.metadata["safety_focused"] is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_anthropic_custom_params(self):
        """Test creating Anthropic provider with custom parameters."""
        provider_id = ProviderId.create_anthropic(api_version="1.5.0", region="EU")

        assert provider_id.provider_name == "Anthropic"
        assert provider_id.provider_type == ProviderType.ANTHROPIC
        assert provider_id.api_version == "1.5.0"
        assert provider_id.region == "EU"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_custom_provider(self):
        """Test creating custom provider."""
        provider_id = ProviderId.create_custom(
            name="My Custom Provider", key="custom-key-123", api_version="3.2.1"
        )

        assert provider_id.provider_name == "My Custom Provider"
        assert provider_id.provider_type == ProviderType.CUSTOM
        assert provider_id.provider_key == "custom-key-123"
        assert provider_id.api_version == "3.2.1"
        assert provider_id.metadata["custom"] is True


class TestProviderIdMethods:
    """Test suite for ProviderId methods."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_is_official_provider(self):
        """Test is_official_provider method."""
        # Official providers
        official_types = [
            ProviderType.OPENAI,
            ProviderType.ANTHROPIC,
            ProviderType.GOOGLE,
            ProviderType.MICROSOFT,
            ProviderType.AMAZON,
            ProviderType.COHERE,
        ]

        for provider_type in official_types:
            provider_id = ProviderId(provider_name="Test", provider_type=provider_type)
            assert provider_id.is_official_provider() is True

        # Non-official providers
        non_official_types = [ProviderType.HUGGINGFACE, ProviderType.CUSTOM]

        for provider_type in non_official_types:
            provider_id = ProviderId(provider_name="Test", provider_type=provider_type)
            assert provider_id.is_official_provider() is False

    @pytest.mark.unit
    def test_supports_region(self):
        """Test supports_region method."""
        # Global provider (no region specified)
        global_provider = ProviderId(
            provider_name="Global Provider", provider_type=ProviderType.CUSTOM
        )
        assert global_provider.supports_region("US") is True
        assert global_provider.supports_region("eu") is True
        assert global_provider.supports_region("JP") is True

        # Regional provider
        regional_provider = ProviderId(
            provider_name="Regional Provider",
            provider_type=ProviderType.CUSTOM,
            region="US",
        )
        assert regional_provider.supports_region("US") is True
        assert regional_provider.supports_region("us") is True  # Case insensitive
        assert regional_provider.supports_region("CA") is False
        assert regional_provider.supports_region("EU") is False

    @pytest.mark.unit
    def test_get_display_name(self):
        """Test get_display_name method."""
        # Without region
        provider_no_region = ProviderId(
            provider_name="Test Provider", provider_type=ProviderType.CUSTOM
        )
        assert provider_no_region.get_display_name() == "Test Provider"

        # With region
        provider_with_region = ProviderId(
            provider_name="Test Provider",
            provider_type=ProviderType.CUSTOM,
            region="US",
        )
        assert provider_with_region.get_display_name() == "Test Provider (US)"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_str_representation(self):
        """Test __str__ method."""
        provider_id = ProviderId(
            provider_name="Test Provider", provider_type=ProviderType.OPENAI
        )
        expected = "Provider[Test Provider:openai]"
        assert str(provider_id) == expected


class TestModelIdCreation:
    """Test suite for ModelId creation and initialization."""

    def setup_method(self):
        """Set up test dependencies."""
        self.provider_id = ProviderId(
            provider_name="Test Provider", provider_type=ProviderType.CUSTOM
        )

    @pytest.mark.unit
    @pytest.mark.unit
    def test_create_minimal_model_id(self):
        """Test creating ModelId with minimal required fields."""
        model_id = ModelId(model_name="test-model", provider_id=self.provider_id)

        assert model_id.model_name == "test-model"
        assert model_id.provider_id == self.provider_id
        assert model_id.capabilities == {ModelCapability.TEXT_GENERATION}
        assert model_id.max_context_tokens == 4096
        assert model_id.max_output_tokens == 1024
        assert model_id.cost_per_input_token == Decimal("0.0")
        assert model_id.cost_per_output_token == Decimal("0.0")
        assert model_id.model_version == "1.0"
        assert model_id.deprecated is False
        assert model_id.metadata == {}

    @pytest.mark.unit
    def test_create_full_model_id(self):
        """Test creating ModelId with all fields specified."""
        capabilities = {
            ModelCapability.TEXT_GENERATION,
            ModelCapability.CONVERSATION,
            ModelCapability.CODE_GENERATION,
        }
        metadata = {"family": "gpt", "training_date": "2023-04"}

        model_id = ModelId(
            model_name="advanced-model-v2",
            provider_id=self.provider_id,
            capabilities=capabilities,
            max_context_tokens=32768,
            max_output_tokens=4096,
            cost_per_input_token=Decimal("0.00003"),
            cost_per_output_token=Decimal("0.00006"),
            model_version="2.1",
            deprecated=True,
            metadata=metadata,
        )

        assert model_id.model_name == "advanced-model-v2"
        assert model_id.provider_id == self.provider_id
        assert model_id.capabilities == capabilities
        assert model_id.max_context_tokens == 32768
        assert model_id.max_output_tokens == 4096
        assert model_id.cost_per_input_token == Decimal("0.00003")
        assert model_id.cost_per_output_token == Decimal("0.00006")
        assert model_id.model_version == "2.1"
        assert model_id.deprecated is True
        assert model_id.metadata == metadata

    @pytest.mark.unit
    def test_frozen_dataclass_immutability(self):
        """Test that ModelId instances are immutable."""
        model_id = ModelId(model_name="immutable-model", provider_id=self.provider_id)

        with pytest.raises(AttributeError):
            model_id.model_name = "modified-name"

        with pytest.raises(AttributeError):
            model_id.max_context_tokens = 8192


class TestModelIdValidation:
    """Test suite for ModelId validation and constraints."""

    def setup_method(self):
        """Set up test dependencies."""
        self.provider_id = ProviderId(
            provider_name="Test Provider", provider_type=ProviderType.CUSTOM
        )

    @pytest.mark.unit
    @pytest.mark.unit
    def test_empty_model_name_raises_error(self):
        """Test that empty model name raises validation error."""
        with pytest.raises(ValueError, match="model_name is required"):
            ModelId(model_name="", provider_id=self.provider_id)

        with pytest.raises(ValueError, match="model_name is required"):
            ModelId(model_name=None, provider_id=self.provider_id)

    @pytest.mark.unit
    def test_invalid_model_name_length_raises_errors(self):
        """Test that invalid model name lengths raise validation errors."""
        # Too long
        long_name = "a" * 201
        with pytest.raises(
            ValueError, match="model_name must be 1-200 characters long"
        ):
            ModelId(model_name=long_name, provider_id=self.provider_id)

    @pytest.mark.unit
    @pytest.mark.unit
    def test_invalid_model_name_characters_raise_errors(self):
        """Test that invalid model name characters raise validation errors."""
        with pytest.raises(ValueError, match="model_name contains invalid characters"):
            ModelId(model_name="invalid@model!", provider_id=self.provider_id)

        with pytest.raises(ValueError, match="model_name contains invalid characters"):
            ModelId(model_name="model with spaces", provider_id=self.provider_id)

    @pytest.mark.unit
    def test_valid_model_name_characters(self):
        """Test that valid model name characters are accepted."""
        valid_names = [
            "gpt-4",
            "claude_3_opus",
            "model-v1.2",
            "custom/model-name",
            "GPT4-Turbo",
            "model123",
        ]

        for name in valid_names:
            model_id = ModelId(model_name=name, provider_id=self.provider_id)
            assert model_id.model_name == name

    @pytest.mark.unit
    def test_invalid_provider_id_raises_error(self):
        """Test that invalid provider_id raises validation error."""
        with pytest.raises(
            ValueError, match="provider_id must be a ProviderId instance"
        ):
            ModelId(model_name="test", provider_id="not-a-provider-id")

    @pytest.mark.unit
    def test_invalid_token_limits_raise_errors(self):
        """Test that invalid token limits raise validation errors."""
        # Negative context tokens
        with pytest.raises(
            ValueError, match="max_context_tokens must be a positive integer"
        ):
            ModelId(
                model_name="test", provider_id=self.provider_id, max_context_tokens=-1
            )

        # Zero context tokens
        with pytest.raises(
            ValueError, match="max_context_tokens must be a positive integer"
        ):
            ModelId(
                model_name="test", provider_id=self.provider_id, max_context_tokens=0
            )

        # Negative output tokens
        with pytest.raises(
            ValueError, match="max_output_tokens must be a positive integer"
        ):
            ModelId(
                model_name="test", provider_id=self.provider_id, max_output_tokens=-1
            )

        # Output tokens exceed context tokens
        with pytest.raises(
            ValueError, match="max_output_tokens cannot exceed max_context_tokens"
        ):
            ModelId(
                model_name="test",
                provider_id=self.provider_id,
                max_context_tokens=1000,
                max_output_tokens=2000,
            )

    @pytest.mark.unit
    def test_invalid_costs_raise_errors(self):
        """Test that invalid costs raise validation errors."""
        # Negative input cost
        with pytest.raises(
            ValueError, match="cost_per_input_token must be a non-negative Decimal"
        ):
            ModelId(
                model_name="test",
                provider_id=self.provider_id,
                cost_per_input_token=Decimal("-0.01"),
            )

        # Negative output cost
        with pytest.raises(
            ValueError, match="cost_per_output_token must be a non-negative Decimal"
        ):
            ModelId(
                model_name="test",
                provider_id=self.provider_id,
                cost_per_output_token=Decimal("-0.01"),
            )

    @pytest.mark.unit
    def test_invalid_capabilities_raise_error(self):
        """Test that invalid capabilities raise validation error."""
        with pytest.raises(
            ValueError, match="All capabilities must be ModelCapability enum values"
        ):
            ModelId(
                model_name="test",
                provider_id=self.provider_id,
                capabilities={
                    "text_generation",
                    "invalid_capability",
                },  # Strings instead of enums
            )


class TestModelIdFactoryMethods:
    """Test suite for ModelId factory methods."""

    def setup_method(self):
        """Set up test dependencies."""
        self.provider_id = ProviderId(
            provider_name="Test Provider", provider_type=ProviderType.OPENAI
        )

    @pytest.mark.unit
    @pytest.mark.unit
    def test_create_gpt4(self):
        """Test creating GPT-4 model."""
        model_id = ModelId.create_gpt4(self.provider_id)

        assert model_id.model_name == "gpt-4"
        assert model_id.provider_id == self.provider_id
        assert ModelCapability.TEXT_GENERATION in model_id.capabilities
        assert ModelCapability.CONVERSATION in model_id.capabilities
        assert ModelCapability.CODE_GENERATION in model_id.capabilities
        assert ModelCapability.ANALYSIS in model_id.capabilities
        assert ModelCapability.CREATIVE_WRITING in model_id.capabilities
        assert model_id.max_context_tokens == 8192
        assert model_id.max_output_tokens == 4096
        assert model_id.cost_per_input_token == Decimal("0.00003")
        assert model_id.cost_per_output_token == Decimal("0.00006")
        assert model_id.model_version == "2023-11"
        assert model_id.metadata["family"] == "gpt-4"
        assert model_id.metadata["training_cutoff"] == "2023-04"

    @pytest.mark.unit
    def test_create_claude_default(self):
        """Test creating Claude model with default variant."""
        anthropic_provider = ProviderId(
            provider_name="Anthropic", provider_type=ProviderType.ANTHROPIC
        )

        model_id = ModelId.create_claude(anthropic_provider)

        assert model_id.model_name == "claude-3-sonnet"
        assert model_id.provider_id == anthropic_provider
        assert ModelCapability.TEXT_GENERATION in model_id.capabilities
        assert ModelCapability.CONVERSATION in model_id.capabilities
        assert ModelCapability.CODE_GENERATION in model_id.capabilities
        assert model_id.max_context_tokens == 200000
        assert model_id.max_output_tokens == 4096
        assert model_id.cost_per_input_token == Decimal("0.000003")
        assert model_id.cost_per_output_token == Decimal("0.000015")
        assert model_id.metadata["family"] == "claude-3"
        assert model_id.metadata["safety_focused"] is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_claude_opus(self):
        """Test creating Claude Opus variant."""
        anthropic_provider = ProviderId(
            provider_name="Anthropic", provider_type=ProviderType.ANTHROPIC
        )

        model_id = ModelId.create_claude(anthropic_provider, variant="claude-3-opus")

        assert model_id.model_name == "claude-3-opus"
        assert model_id.max_context_tokens == 200000
        assert model_id.max_output_tokens == 4096
        assert model_id.cost_per_input_token == Decimal("0.000015")
        assert model_id.cost_per_output_token == Decimal("0.000075")

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_claude_unknown_variant_uses_default(self):
        """Test creating Claude with unknown variant uses default config."""
        anthropic_provider = ProviderId(
            provider_name="Anthropic", provider_type=ProviderType.ANTHROPIC
        )

        model_id = ModelId.create_claude(anthropic_provider, variant="unknown-variant")

        assert model_id.model_name == "unknown-variant"
        # Should use claude-3-sonnet config as default
        assert model_id.cost_per_input_token == Decimal("0.000003")
        assert model_id.cost_per_output_token == Decimal("0.000015")


class TestModelIdMethods:
    """Test suite for ModelId methods."""

    def setup_method(self):
        """Set up test dependencies."""
        self.provider_id = ProviderId(
            provider_name="Test Provider", provider_type=ProviderType.CUSTOM
        )

    @pytest.mark.unit
    @pytest.mark.unit
    def test_supports_capability(self):
        """Test supports_capability method."""
        capabilities = {
            ModelCapability.TEXT_GENERATION,
            ModelCapability.CONVERSATION,
            ModelCapability.CODE_GENERATION,
        }

        model_id = ModelId(
            model_name="test-model",
            provider_id=self.provider_id,
            capabilities=capabilities,
        )

        # Supported capabilities
        assert model_id.supports_capability(ModelCapability.TEXT_GENERATION) is True
        assert model_id.supports_capability(ModelCapability.CONVERSATION) is True
        assert model_id.supports_capability(ModelCapability.CODE_GENERATION) is True

        # Unsupported capabilities
        assert model_id.supports_capability(ModelCapability.VISION) is False
        assert model_id.supports_capability(ModelCapability.EMBEDDING) is False

    @pytest.mark.unit
    def test_estimate_cost(self):
        """Test estimate_cost method."""
        model_id = ModelId(
            model_name="test-model",
            provider_id=self.provider_id,
            cost_per_input_token=Decimal("0.00001"),
            cost_per_output_token=Decimal("0.00002"),
        )

        cost = model_id.estimate_cost(input_tokens=1000, output_tokens=500)
        expected_cost = Decimal("1000") * Decimal("0.00001") + Decimal("500") * Decimal(
            "0.00002"
        )
        assert cost == expected_cost

    @pytest.mark.unit
    @pytest.mark.fast
    def test_estimate_cost_zero_tokens(self):
        """Test estimate_cost method with zero tokens."""
        model_id = ModelId(
            model_name="test-model",
            provider_id=self.provider_id,
            cost_per_input_token=Decimal("0.00001"),
            cost_per_output_token=Decimal("0.00002"),
        )

        cost = model_id.estimate_cost(input_tokens=0, output_tokens=0)
        assert cost == Decimal("0.00000")

    @pytest.mark.unit
    @pytest.mark.fast
    def test_can_handle_context(self):
        """Test can_handle_context method."""
        model_id = ModelId(
            model_name="test-model",
            provider_id=self.provider_id,
            max_context_tokens=4096,
        )

        assert model_id.can_handle_context(2000) is True
        assert model_id.can_handle_context(4096) is True
        assert model_id.can_handle_context(4097) is False
        assert model_id.can_handle_context(8000) is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_effective_context_limit(self):
        """Test get_effective_context_limit method."""
        model_id = ModelId(
            model_name="test-model",
            provider_id=self.provider_id,
            max_context_tokens=4096,
        )

        assert model_id.get_effective_context_limit(0) == 4096
        assert model_id.get_effective_context_limit(1024) == 3072
        assert model_id.get_effective_context_limit(4096) == 0
        assert model_id.get_effective_context_limit(5000) == 0  # Cannot go negative

    @pytest.mark.unit
    @pytest.mark.fast
    def test_is_deprecated(self):
        """Test is_deprecated method."""
        # Non-deprecated model
        current_model = ModelId(
            model_name="current-model", provider_id=self.provider_id, deprecated=False
        )
        assert current_model.is_deprecated() is False

        # Deprecated model
        old_model = ModelId(
            model_name="old-model", provider_id=self.provider_id, deprecated=True
        )
        assert old_model.is_deprecated() is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_str_representation(self):
        """Test __str__ method."""
        model_id = ModelId(model_name="gpt-4", provider_id=self.provider_id)
        expected = "Model[gpt-4@Test Provider]"
        assert str(model_id) == expected


class TestTokenBudgetCreation:
    """Test suite for TokenBudget creation and initialization."""

    @pytest.mark.unit
    def test_create_minimal_token_budget(self):
        """Test creating TokenBudget with minimal required fields."""
        budget = TokenBudget(budget_id="test-budget", allocated_tokens=10000)

        assert budget.budget_id == "test-budget"
        assert budget.allocated_tokens == 10000
        assert budget.consumed_tokens == 0
        assert budget.reserved_tokens == 0
        assert budget.cost_limit == Decimal("1000.00")
        assert budget.accumulated_cost == Decimal("0.00")
        assert budget.period_start is None
        assert budget.period_end is None
        assert budget.rollover_enabled is True
        assert budget.priority == 5
        assert budget.metadata == {}

    @pytest.mark.unit
    def test_create_full_token_budget(self):
        """Test creating TokenBudget with all fields specified."""
        period_start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        period_end = datetime(2024, 1, 31, tzinfo=timezone.utc)
        metadata = {"project": "test", "department": "engineering"}

        budget = TokenBudget(
            budget_id="full-budget-123",
            allocated_tokens=50000,
            consumed_tokens=5000,
            reserved_tokens=2000,
            cost_limit=Decimal("500.00"),
            accumulated_cost=Decimal("50.25"),
            period_start=period_start,
            period_end=period_end,
            rollover_enabled=False,
            priority=8,
            metadata=metadata,
        )

        assert budget.budget_id == "full-budget-123"
        assert budget.allocated_tokens == 50000
        assert budget.consumed_tokens == 5000
        assert budget.reserved_tokens == 2000
        assert budget.cost_limit == Decimal("500.00")
        assert budget.accumulated_cost == Decimal("50.25")
        assert budget.period_start == period_start
        assert budget.period_end == period_end
        assert budget.rollover_enabled is False
        assert budget.priority == 8
        assert budget.metadata == metadata

    @pytest.mark.unit
    def test_frozen_dataclass_immutability(self):
        """Test that TokenBudget instances are immutable."""
        budget = TokenBudget(budget_id="immutable-budget", allocated_tokens=1000)

        with pytest.raises(AttributeError):
            budget.budget_id = "modified-id"

        with pytest.raises(AttributeError):
            budget.allocated_tokens = 2000


class TestTokenBudgetValidation:
    """Test suite for TokenBudget validation and constraints."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_empty_budget_id_raises_error(self):
        """Test that empty budget ID raises validation error."""
        with pytest.raises(ValueError, match="budget_id is required"):
            TokenBudget(budget_id="", allocated_tokens=1000)

        with pytest.raises(ValueError, match="budget_id is required"):
            TokenBudget(budget_id=None, allocated_tokens=1000)

    @pytest.mark.unit
    def test_invalid_budget_id_length_raises_errors(self):
        """Test that invalid budget ID lengths raise validation errors."""
        # Too short
        with pytest.raises(ValueError, match="budget_id must be 3-100 characters long"):
            TokenBudget(budget_id="ab", allocated_tokens=1000)

        # Too long
        long_id = "a" * 101
        with pytest.raises(ValueError, match="budget_id must be 3-100 characters long"):
            TokenBudget(budget_id=long_id, allocated_tokens=1000)

    @pytest.mark.unit
    def test_invalid_budget_id_characters_raise_error(self):
        """Test that invalid budget ID characters raise validation error."""
        with pytest.raises(ValueError, match="budget_id contains invalid characters"):
            TokenBudget(budget_id="invalid@budget!", allocated_tokens=1000)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_valid_budget_id_characters(self):
        """Test that valid budget ID characters are accepted."""
        valid_ids = ["budget-123", "project_budget", "Budget.v1.0", "dailyBudget2024"]

        for budget_id in valid_ids:
            budget = TokenBudget(budget_id=budget_id, allocated_tokens=1000)
            assert budget.budget_id == budget_id

    @pytest.mark.unit
    @pytest.mark.unit
    def test_invalid_token_values_raise_errors(self):
        """Test that invalid token values raise validation errors."""
        # Zero allocated tokens
        with pytest.raises(
            ValueError, match="allocated_tokens must be a positive integer"
        ):
            TokenBudget(budget_id="test", allocated_tokens=0)

        # Negative allocated tokens
        with pytest.raises(
            ValueError, match="allocated_tokens must be a positive integer"
        ):
            TokenBudget(budget_id="test", allocated_tokens=-1000)

        # Negative consumed tokens
        with pytest.raises(
            ValueError, match="consumed_tokens must be a non-negative integer"
        ):
            TokenBudget(budget_id="test", allocated_tokens=1000, consumed_tokens=-100)

        # Negative reserved tokens
        with pytest.raises(
            ValueError, match="reserved_tokens must be a non-negative integer"
        ):
            TokenBudget(budget_id="test", allocated_tokens=1000, reserved_tokens=-100)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_token_budget_over_allocation_allowed(self):
        """Test that over-allocation scenarios are allowed (handled by business methods)."""
        # Over-allocation should be allowed during construction
        budget = TokenBudget(
            budget_id="test",
            allocated_tokens=1000,
            consumed_tokens=600,
            reserved_tokens=500,  # 600 + 500 > 1000
        )
        # Business methods should handle this appropriately
        assert budget.get_available_tokens() == 0  # Protected to return 0, not negative

    @pytest.mark.unit
    def test_invalid_cost_values_raise_errors(self):
        """Test that invalid cost values raise validation errors."""
        # Negative cost limit
        with pytest.raises(
            ValueError, match="cost_limit must be a non-negative Decimal"
        ):
            TokenBudget(
                budget_id="test", allocated_tokens=1000, cost_limit=Decimal("-100.00")
            )

        # Negative accumulated cost
        with pytest.raises(
            ValueError, match="accumulated_cost must be a non-negative Decimal"
        ):
            TokenBudget(
                budget_id="test",
                allocated_tokens=1000,
                accumulated_cost=Decimal("-50.00"),
            )

        # Accumulated cost exceeds limit
        with pytest.raises(
            ValueError, match="accumulated_cost cannot exceed cost_limit"
        ):
            TokenBudget(
                budget_id="test",
                allocated_tokens=1000,
                cost_limit=Decimal("100.00"),
                accumulated_cost=Decimal("150.00"),
            )

    @pytest.mark.unit
    def test_invalid_priority_raises_error(self):
        """Test that invalid priority raises validation error."""
        # Priority too low
        with pytest.raises(
            ValueError, match="priority must be an integer between 1 and 10"
        ):
            TokenBudget(budget_id="test", allocated_tokens=1000, priority=0)

        # Priority too high
        with pytest.raises(
            ValueError, match="priority must be an integer between 1 and 10"
        ):
            TokenBudget(budget_id="test", allocated_tokens=1000, priority=11)


class TestTokenBudgetFactoryMethods:
    """Test suite for TokenBudget factory methods."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_create_daily_budget_default(self):
        """Test creating daily budget with default parameters."""
        budget = TokenBudget.create_daily_budget("user123", 5000)

        assert budget.budget_id == "daily_user123"
        assert budget.allocated_tokens == 5000
        assert budget.cost_limit == Decimal("100.00")
        assert budget.rollover_enabled is False
        assert budget.metadata["type"] == "daily"
        assert budget.metadata["auto_reset"] is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_daily_budget_with_cost_limit(self):
        """Test creating daily budget with custom cost limit."""
        budget = TokenBudget.create_daily_budget("user456", 10000, Decimal("200.00"))

        assert budget.budget_id == "daily_user456"
        assert budget.allocated_tokens == 10000
        assert budget.cost_limit == Decimal("200.00")

    @pytest.mark.unit
    @pytest.mark.unit
    def test_create_project_budget(self):
        """Test creating project budget."""
        budget = TokenBudget.create_project_budget(
            "proj789", 100000, Decimal("1000.00")
        )

        assert budget.budget_id == "project_proj789"
        assert budget.allocated_tokens == 100000
        assert budget.cost_limit == Decimal("1000.00")
        assert budget.rollover_enabled is True
        assert budget.priority == 8
        assert budget.metadata["type"] == "project"
        assert budget.metadata["project_id"] == "proj789"


class TestTokenBudgetMethods:
    """Test suite for TokenBudget methods."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_get_available_tokens(self):
        """Test get_available_tokens method."""
        budget = TokenBudget(
            budget_id="test",
            allocated_tokens=10000,
            consumed_tokens=3000,
            reserved_tokens=2000,
        )

        available = budget.get_available_tokens()
        assert available == 5000  # 10000 - 3000 - 2000

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_available_tokens_negative_protected(self):
        """Test that get_available_tokens returns 0 when result would be negative."""
        budget = TokenBudget(
            budget_id="test",
            allocated_tokens=1000,
            consumed_tokens=800,
            reserved_tokens=300,
        )

        available = budget.get_available_tokens()
        assert available == 0  # max(0, 1000 - 800 - 300)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_utilization_percentage(self):
        """Test get_utilization_percentage method."""
        budget = TokenBudget(
            budget_id="test",
            allocated_tokens=10000,
            consumed_tokens=3000,
            reserved_tokens=2000,
        )

        utilization = budget.get_utilization_percentage()
        expected = Decimal("50.00")  # (3000 + 2000) / 10000 * 100
        assert utilization == expected

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_utilization_percentage_zero_allocation(self):
        """Test get_utilization_percentage with zero allocation."""
        # This should not happen in practice due to validation, but test the edge case
        budget = TokenBudget(budget_id="test", allocated_tokens=1)  # Minimum allocation
        # Manually set to zero to test edge case
        object.__setattr__(budget, "allocated_tokens", 0)

        utilization = budget.get_utilization_percentage()
        assert utilization == Decimal("0.00")

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_cost_utilization_percentage(self):
        """Test get_cost_utilization_percentage method."""
        budget = TokenBudget(
            budget_id="test",
            allocated_tokens=10000,
            cost_limit=Decimal("100.00"),
            accumulated_cost=Decimal("25.00"),
        )

        cost_util = budget.get_cost_utilization_percentage()
        expected = Decimal("25.00")  # 25.00 / 100.00 * 100
        assert cost_util == expected

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_cost_utilization_percentage_zero_limit(self):
        """Test get_cost_utilization_percentage with zero cost limit."""
        budget = TokenBudget(
            budget_id="test", allocated_tokens=10000, cost_limit=Decimal("0.00")
        )

        cost_util = budget.get_cost_utilization_percentage()
        assert cost_util == Decimal("0.00")

    @pytest.mark.unit
    @pytest.mark.unit
    def test_can_reserve_tokens(self):
        """Test can_reserve_tokens method."""
        budget = TokenBudget(
            budget_id="test",
            allocated_tokens=10000,
            consumed_tokens=3000,
            reserved_tokens=2000,
        )  # 5000 available tokens

        assert budget.can_reserve_tokens(4000) is True
        assert budget.can_reserve_tokens(5000) is True
        assert budget.can_reserve_tokens(5001) is False
        assert budget.can_reserve_tokens(10000) is False

    @pytest.mark.unit
    def test_can_afford_cost(self):
        """Test can_afford_cost method."""
        budget = TokenBudget(
            budget_id="test",
            allocated_tokens=10000,
            cost_limit=Decimal("100.00"),
            accumulated_cost=Decimal("60.00"),
        )  # 40.00 remaining

        assert budget.can_afford_cost(Decimal("30.00")) is True
        assert budget.can_afford_cost(Decimal("40.00")) is True
        assert budget.can_afford_cost(Decimal("40.01")) is False
        assert budget.can_afford_cost(Decimal("100.00")) is False

    @pytest.mark.unit
    def test_reserve_tokens(self):
        """Test reserve_tokens method (immutable operation)."""
        original_budget = TokenBudget(
            budget_id="test",
            allocated_tokens=10000,
            consumed_tokens=3000,
            reserved_tokens=2000,
        )

        new_budget = original_budget.reserve_tokens(1000)

        # Original budget unchanged
        assert original_budget.reserved_tokens == 2000

        # New budget has updated reserved tokens
        assert new_budget.reserved_tokens == 3000
        assert new_budget.consumed_tokens == 3000  # Unchanged
        assert new_budget.allocated_tokens == 10000  # Unchanged
        assert new_budget.budget_id == "test"  # Unchanged

    @pytest.mark.unit
    def test_reserve_tokens_insufficient_budget(self):
        """Test reserve_tokens with insufficient budget."""
        budget = TokenBudget(
            budget_id="test",
            allocated_tokens=10000,
            consumed_tokens=8000,
            reserved_tokens=1000,
        )  # Only 1000 available

        with pytest.raises(
            ValueError, match="Cannot reserve 2000 tokens - insufficient budget"
        ):
            budget.reserve_tokens(2000)

    @pytest.mark.unit
    def test_consume_tokens(self):
        """Test consume_tokens method (immutable operation)."""
        original_budget = TokenBudget(
            budget_id="test",
            allocated_tokens=10000,
            consumed_tokens=3000,
            reserved_tokens=2000,
            cost_limit=Decimal("100.00"),
            accumulated_cost=Decimal("30.00"),
        )

        new_budget = original_budget.consume_tokens(1500, Decimal("15.00"))

        # Original budget unchanged
        assert original_budget.consumed_tokens == 3000
        assert original_budget.reserved_tokens == 2000
        assert original_budget.accumulated_cost == Decimal("30.00")

        # New budget has updated values
        # Should consume from reserved first: 1500 from 2000 reserved = 500 reserved remaining
        assert new_budget.consumed_tokens == 4500  # 3000 + 1500
        assert new_budget.reserved_tokens == 500  # 2000 - 1500
        assert new_budget.accumulated_cost == Decimal("45.00")  # 30.00 + 15.00

    @pytest.mark.unit
    def test_consume_tokens_more_than_reserved(self):
        """Test consuming more tokens than reserved (consume from available too)."""
        original_budget = TokenBudget(
            budget_id="test",
            allocated_tokens=10000,
            consumed_tokens=3000,
            reserved_tokens=1000,  # Only 1000 reserved
            cost_limit=Decimal("100.00"),
            accumulated_cost=Decimal("30.00"),
        )

        # Try to consume 2000 tokens (1000 from reserved + 1000 from available)
        new_budget = original_budget.consume_tokens(2000, Decimal("20.00"))

        assert new_budget.consumed_tokens == 5000  # 3000 + 2000
        assert new_budget.reserved_tokens == 0  # All reserved consumed
        assert new_budget.accumulated_cost == Decimal("50.00")

    @pytest.mark.unit
    def test_consume_tokens_exceeds_budget(self):
        """Test consume_tokens with insufficient budget."""
        budget = TokenBudget(
            budget_id="test",
            allocated_tokens=10000,
            consumed_tokens=8000,
            reserved_tokens=1000,
            cost_limit=Decimal("100.00"),
        )  # Only 1000 available + 1000 reserved = 2000 max consumable

        with pytest.raises(
            ValueError, match="Cannot consume 3000 tokens - exceeds allocated budget"
        ):
            budget.consume_tokens(3000, Decimal("30.00"))

    @pytest.mark.unit
    def test_consume_tokens_exceeds_cost_limit(self):
        """Test consume_tokens exceeding cost limit."""
        budget = TokenBudget(
            budget_id="test",
            allocated_tokens=10000,
            consumed_tokens=3000,
            reserved_tokens=2000,
            cost_limit=Decimal("100.00"),
            accumulated_cost=Decimal("90.00"),
        )  # Only 10.00 cost remaining

        with pytest.raises(
            ValueError, match="Cannot afford additional cost of .* - exceeds cost limit"
        ):
            budget.consume_tokens(1000, Decimal("15.00"))

    @pytest.mark.unit
    def test_is_exhausted(self):
        """Test is_exhausted method."""
        # Not exhausted (tokens and cost available)
        budget1 = TokenBudget(
            budget_id="test1",
            allocated_tokens=10000,
            consumed_tokens=5000,
            cost_limit=Decimal("100.00"),
            accumulated_cost=Decimal("50.00"),
        )
        assert budget1.is_exhausted() is False

        # Exhausted by tokens
        budget2 = TokenBudget(
            budget_id="test2",
            allocated_tokens=10000,
            consumed_tokens=10000,
            cost_limit=Decimal("100.00"),
            accumulated_cost=Decimal("50.00"),
        )
        assert budget2.is_exhausted() is True

        # Exhausted by cost
        budget3 = TokenBudget(
            budget_id="test3",
            allocated_tokens=10000,
            consumed_tokens=5000,
            cost_limit=Decimal("100.00"),
            accumulated_cost=Decimal("100.00"),
        )
        assert budget3.is_exhausted() is True

    @pytest.mark.unit
    def test_is_near_exhaustion(self):
        """Test is_near_exhaustion method."""
        # Not near exhaustion
        budget1 = TokenBudget(
            budget_id="test1",
            allocated_tokens=10000,
            consumed_tokens=5000,  # 50% utilization
            cost_limit=Decimal("100.00"),
            accumulated_cost=Decimal("50.00"),  # 50% cost utilization
        )
        assert budget1.is_near_exhaustion() is False
        assert (
            budget1.is_near_exhaustion(Decimal("40.00")) is True
        )  # Custom threshold (50% > 40%)

        # Near exhaustion by tokens
        budget2 = TokenBudget(
            budget_id="test2",
            allocated_tokens=10000,
            consumed_tokens=9100,  # 91% utilization
            cost_limit=Decimal("100.00"),
            accumulated_cost=Decimal("50.00"),
        )
        assert budget2.is_near_exhaustion() is True

        # Near exhaustion by cost
        budget3 = TokenBudget(
            budget_id="test3",
            allocated_tokens=10000,
            consumed_tokens=5000,
            cost_limit=Decimal("100.00"),
            accumulated_cost=Decimal("95.00"),  # 95% cost utilization
        )
        assert budget3.is_near_exhaustion() is True

    @pytest.mark.unit
    def test_get_budget_summary(self):
        """Test get_budget_summary method."""
        budget = TokenBudget(
            budget_id="summary-test",
            allocated_tokens=10000,
            consumed_tokens=3000,
            reserved_tokens=2000,
            cost_limit=Decimal("100.00"),
            accumulated_cost=Decimal("30.00"),
            rollover_enabled=True,
            priority=7,
        )

        summary = budget.get_budget_summary()

        assert summary["budget_id"] == "summary-test"
        assert summary["tokens"]["allocated"] == 10000
        assert summary["tokens"]["consumed"] == 3000
        assert summary["tokens"]["reserved"] == 2000
        assert summary["tokens"]["available"] == 5000
        assert summary["tokens"]["utilization_percent"] == 50.0

        assert summary["cost"]["limit"] == 100.0
        assert summary["cost"]["accumulated"] == 30.0
        assert summary["cost"]["available"] == 70.0
        assert summary["cost"]["utilization_percent"] == 30.0

        assert summary["status"]["exhausted"] is False
        assert summary["status"]["near_exhaustion"] is False
        assert summary["status"]["priority"] == 7
        assert summary["status"]["rollover_enabled"] is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_str_representation(self):
        """Test __str__ method."""
        budget = TokenBudget(
            budget_id="test-budget",
            allocated_tokens=10000,
            consumed_tokens=3000,
            reserved_tokens=2000,
        )

        expected = "Budget[test-budget:5000/10000 tokens available]"
        assert str(budget) == expected


class TestTokenBudgetEquality:
    """Test suite for TokenBudget equality and hashing."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_equality_same_values(self):
        """Test equality with same values."""
        budget1 = TokenBudget(
            budget_id="test-budget",
            allocated_tokens=10000,
            consumed_tokens=3000,
            reserved_tokens=2000,
        )

        budget2 = TokenBudget(
            budget_id="test-budget",
            allocated_tokens=10000,
            consumed_tokens=3000,
            reserved_tokens=2000,
        )

        assert budget1 == budget2
        assert hash(budget1) == hash(budget2)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_inequality_different_values(self):
        """Test inequality with different values."""
        budget1 = TokenBudget(budget_id="test-budget-1", allocated_tokens=10000)

        budget2 = TokenBudget(budget_id="test-budget-2", allocated_tokens=10000)

        assert budget1 != budget2
        assert hash(budget1) != hash(budget2)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_equality_in_collections(self):
        """Test that equality works correctly in collections."""
        budget1 = TokenBudget(budget_id="collection-test", allocated_tokens=10000)

        budget2 = TokenBudget(budget_id="collection-test", allocated_tokens=10000)

        budget_set = {budget1}
        assert budget2 in budget_set

        budget_list = [budget1]
        assert budget2 in budget_list
