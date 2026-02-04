"""
Unit Tests for PromptTemplate Entity

Warzone 4: AI Brain - BRAIN-014A
Tests for PromptTemplate, VariableDefinition, ModelConfig value objects.
"""

from datetime import datetime, timezone

import pytest

from src.contexts.knowledge.domain.models.prompt_template import (
    ModelConfig,
    PromptTemplate,
    VariableDefinition,
    VariableType,
)


class TestVariableDefinition:
    """Tests for VariableDefinition value object."""

    def test_create_valid_string_variable(self) -> None:
        """Should create a valid string variable definition."""
        var = VariableDefinition(
            name="character_name",
            type=VariableType.STRING,
            description="Name of the character",
            required=True,
        )
        assert var.name == "character_name"
        assert var.type == VariableType.STRING
        assert var.required is True

    def test_create_variable_with_default_value(self) -> None:
        """Should create a variable with a default value."""
        var = VariableDefinition(
            name="temperature",
            type=VariableType.FLOAT,
            default_value=0.7,
            required=False,
        )
        assert var.default_value == 0.7
        assert var.required is False

    def test_name_cannot_be_empty(self) -> None:
        """Should raise error for empty variable name."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            VariableDefinition(name="", type=VariableType.STRING)

    def test_name_must_be_valid_identifier(self) -> None:
        """Should raise error for invalid variable name."""
        with pytest.raises(ValueError, match="must be alphanumeric"):
            VariableDefinition(name="invalid-name!", type=VariableType.STRING)

        with pytest.raises(ValueError, match="must be alphanumeric"):
            VariableDefinition(name="123invalid", type=VariableType.STRING)

        with pytest.raises(ValueError, match="must be alphanumeric"):
            VariableDefinition(name="invalid name", type=VariableType.STRING)

    def test_validate_value_string(self) -> None:
        """Should validate string values correctly."""
        var = VariableDefinition(name="text", type=VariableType.STRING)
        assert var.validate_value("hello") is True
        assert var.validate_value("") is True  # Empty string is valid
        assert var.validate_value(123) is False
        assert var.validate_value(None) is False  # Required variable

    def test_validate_value_integer(self) -> None:
        """Should validate integer values correctly."""
        var = VariableDefinition(name="count", type=VariableType.INTEGER)
        assert var.validate_value(42) is True
        assert var.validate_value(0) is True
        assert var.validate_value(-1) is True
        assert var.validate_value(3.14) is False
        assert var.validate_value("42") is False
        assert var.validate_value(True) is False  # bool is not int

    def test_validate_value_float(self) -> None:
        """Should validate float values correctly."""
        var = VariableDefinition(name="ratio", type=VariableType.FLOAT)
        assert var.validate_value(3.14) is True
        assert var.validate_value(42) is True  # int is valid for float
        assert var.validate_value(-0.5) is True
        assert var.validate_value("3.14") is False

    def test_validate_value_boolean(self) -> None:
        """Should validate boolean values correctly."""
        var = VariableDefinition(name="enabled", type=VariableType.BOOLEAN)
        assert var.validate_value(True) is True
        assert var.validate_value(False) is True
        assert var.validate_value(1) is False
        assert var.validate_value("true") is False

    def test_validate_value_list(self) -> None:
        """Should validate list values correctly."""
        var = VariableDefinition(name="items", type=VariableType.LIST)
        assert var.validate_value([1, 2, 3]) is True
        assert var.validate_value([]) is True
        assert var.validate_value(("a", "b")) is False  # tuple is not list
        assert var.validate_value("not a list") is False

    def test_validate_value_dict(self) -> None:
        """Should validate dict values correctly."""
        var = VariableDefinition(name="config", type=VariableType.DICT)
        assert var.validate_value({"key": "value"}) is True
        assert var.validate_value({}) is True
        assert var.validate_value("not a dict") is False

    def test_validate_optional_variable_with_none(self) -> None:
        """Should accept None for optional variables."""
        var = VariableDefinition(
            name="optional", type=VariableType.STRING, required=False
        )
        assert var.validate_value(None) is True

    def test_coerce_value_to_string(self) -> None:
        """Should coerce values to strings."""
        var = VariableDefinition(name="text", type=VariableType.STRING)
        assert var.coerce_value(123) == "123"
        assert var.coerce_value(3.14) == "3.14"
        assert var.coerce_value(True) == "True"

    def test_coerce_value_to_integer(self) -> None:
        """Should coerce values to integers."""
        var = VariableDefinition(name="count", type=VariableType.INTEGER)
        assert var.coerce_value("42") == 42
        assert var.coerce_value(3.14) == 3
        assert var.coerce_value(True) == 1

    def test_coerce_value_to_float(self) -> None:
        """Should coerce values to floats."""
        var = VariableDefinition(name="ratio", type=VariableType.FLOAT)
        assert var.coerce_value("3.14") == 3.14
        assert var.coerce_value(42) == 42.0

    def test_coerce_value_to_boolean(self) -> None:
        """Should coerce values to booleans."""
        var = VariableDefinition(name="enabled", type=VariableType.BOOLEAN)
        assert var.coerce_value("true") is True
        assert var.coerce_value("True") is True
        assert var.coerce_value("false") is False
        assert var.coerce_value("1") is True
        assert var.coerce_value("0") is False

    def test_coerce_required_variable_with_none_raises_error(self) -> None:
        """Should raise error when coercing None to required variable."""
        var = VariableDefinition(name="required", type=VariableType.STRING, required=True)
        with pytest.raises(ValueError, match="cannot be None"):
            var.coerce_value(None)

    def test_coerce_list_from_string(self) -> None:
        """Should coerce comma-separated string to list."""
        var = VariableDefinition(name="items", type=VariableType.LIST)
        result = var.coerce_value("apple, banana, cherry")
        assert result == ["apple", "banana", "cherry"]

    def test_coerce_dict_from_string(self) -> None:
        """Should coerce key=value string to dict."""
        var = VariableDefinition(name="config", type=VariableType.DICT)
        result = var.coerce_value("key1=value1, key2=value2")
        assert result == {"key1": "value1", "key2": "value2"}


class TestModelConfig:
    """Tests for ModelConfig value object."""

    def test_create_valid_model_config(self) -> None:
        """Should create a valid model config."""
        config = ModelConfig(
            provider="openai", model_name="gpt-4", temperature=0.7, max_tokens=1000
        )
        assert config.provider == "openai"
        assert config.model_name == "gpt-4"
        assert config.temperature == 0.7
        assert config.max_tokens == 1000

    def test_provider_cannot_be_empty(self) -> None:
        """Should raise error for empty provider."""
        with pytest.raises(ValueError, match="provider cannot be empty"):
            ModelConfig(provider="", model_name="gpt-4")

    def test_model_name_cannot_be_empty(self) -> None:
        """Should raise error for empty model name."""
        with pytest.raises(ValueError, match="model_name cannot be empty"):
            ModelConfig(provider="openai", model_name="")

    def test_temperature_must_be_valid(self) -> None:
        """Should raise error for invalid temperature."""
        with pytest.raises(ValueError, match="temperature must be between"):
            ModelConfig(provider="openai", model_name="gpt-4", temperature=2.5)

        with pytest.raises(ValueError, match="temperature must be between"):
            ModelConfig(provider="openai", model_name="gpt-4", temperature=-0.1)

    def test_max_tokens_must_be_positive(self) -> None:
        """Should raise error for non-positive max tokens."""
        with pytest.raises(ValueError, match="max_tokens must be positive"):
            ModelConfig(provider="openai", model_name="gpt-4", max_tokens=0)

    def test_top_p_must_be_valid(self) -> None:
        """Should raise error for invalid top_p."""
        with pytest.raises(ValueError, match="top_p must be between"):
            ModelConfig(provider="openai", model_name="gpt-4", top_p=1.5)

    def test_frequency_penalty_must_be_valid(self) -> None:
        """Should raise error for invalid frequency penalty."""
        with pytest.raises(ValueError, match="frequency_penalty must be between"):
            ModelConfig(provider="openai", model_name="gpt-4", frequency_penalty=2.5)

    def test_presence_penalty_must_be_valid(self) -> None:
        """Should raise error for invalid presence penalty."""
        with pytest.raises(ValueError, match="presence_penalty must be between"):
            ModelConfig(provider="openai", model_name="gpt-4", presence_penalty=-2.5)


class TestPromptTemplate:
    """Tests for PromptTemplate entity."""

    def test_create_valid_template(self) -> None:
        """Should create a valid prompt template."""
        variables = (
            VariableDefinition(
                name="character_name",
                type=VariableType.STRING,
                description="Name of the character",
            ),
        )
        model_config = ModelConfig(provider="openai", model_name="gpt-4")

        template = PromptTemplate(
            id="test-1",
            name="Character Generation",
            content="Generate a character named {{character_name}}.",
            variables=variables,
            model_config=model_config,
        )

        assert template.id == "test-1"
        assert template.name == "Character Generation"
        assert template.version == 1

    def test_id_cannot_be_empty(self) -> None:
        """Should raise error for empty ID."""
        with pytest.raises(ValueError, match="id cannot be empty"):
            PromptTemplate(
                id="",
                name="Test",
                content="Content",
                variables=(),
                model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            )

    def test_name_cannot_be_empty(self) -> None:
        """Should raise error for empty name."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            PromptTemplate(
                id="test-1",
                name="",
                content="Content",
                variables=(),
                model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            )

    def test_content_cannot_be_empty(self) -> None:
        """Should raise error for empty content."""
        with pytest.raises(ValueError, match="content cannot be empty"):
            PromptTemplate(
                id="test-1",
                name="Test",
                content="   ",
                variables=(),
                model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            )

    def test_undefined_variable_in_content_raises_error(self) -> None:
        """Should raise error for undefined variables in content."""
        with pytest.raises(ValueError, match="undefined variables"):
            PromptTemplate(
                id="test-1",
                name="Test",
                content="Hello {{name}}, you are {{age}} years old.",
                variables=(
                    VariableDefinition(name="name", type=VariableType.STRING),
                ),
                model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            )

    def test_extract_variables_from_content(self) -> None:
        """Should extract variable names from content."""
        template = PromptTemplate(
            id="test-1",
            name="Test",
            content="Hello {{name}}, you are {{age}} years old.",
            variables=(
                VariableDefinition(name="name", type=VariableType.STRING),
                VariableDefinition(name="age", type=VariableType.INTEGER),
            ),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        variables = template.extract_variables()
        assert variables == {"name", "age"}

    def test_render_template_with_variables(self) -> None:
        """Should render template with provided variables."""
        template = PromptTemplate(
            id="test-1",
            name="Test",
            content="Hello {{name}}, you are {{age}} years old.",
            variables=(
                VariableDefinition(name="name", type=VariableType.STRING),
                VariableDefinition(name="age", type=VariableType.INTEGER),
            ),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        result = template.render({"name": "Alice", "age": 30})
        assert result == "Hello Alice, you are 30 years old."

    def test_render_with_type_coercion(self) -> None:
        """Should coerce variable values during rendering."""
        template = PromptTemplate(
            id="test-1",
            name="Test",
            content="Count: {{count}}",
            variables=(
                VariableDefinition(name="count", type=VariableType.INTEGER),
            ),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        result = template.render({"count": "42"})
        assert result == "Count: 42"

    def test_render_missing_required_variable_raises_error(self) -> None:
        """Should raise error for missing required variables."""
        template = PromptTemplate(
            id="test-1",
            name="Test",
            content="Hello {{name}}",
            variables=(
                VariableDefinition(
                    name="name", type=VariableType.STRING, required=True
                ),
            ),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        with pytest.raises(ValueError, match="not provided"):
            template.render({}, strict=True)

    def test_render_missing_optional_variable_uses_default(self) -> None:
        """Should use default value for missing optional variables."""
        template = PromptTemplate(
            id="test-1",
            name="Test",
            content="Temperature is {{temp}}",
            variables=(
                VariableDefinition(
                    name="temp",
                    type=VariableType.FLOAT,
                    default_value=0.7,
                    required=False,
                ),
            ),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        result = template.render({})
        assert result == "Temperature is 0.7"

    def test_render_list_variable(self) -> None:
        """Should render list variables correctly."""
        template = PromptTemplate(
            id="test-1",
            name="Test",
            content="Items: {{items}}",
            variables=(
                VariableDefinition(name="items", type=VariableType.LIST),
            ),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        result = template.render({"items": ["apple", "banana", "cherry"]})
        assert result == "Items: apple, banana, cherry"

    def test_render_dict_variable(self) -> None:
        """Should render dict variables correctly."""
        template = PromptTemplate(
            id="test-1",
            name="Test",
            content="Config: {{config}}",
            variables=(
                VariableDefinition(name="config", type=VariableType.DICT),
            ),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        result = template.render({"config": {"key1": "value1", "key2": "value2"}})
        assert "key1=value1" in result
        assert "key2=value2" in result

    def test_validate_syntax_with_valid_template(self) -> None:
        """Should return empty list for valid template syntax."""
        template = PromptTemplate(
            id="test-1",
            name="Test",
            content="Valid {{template}} with balanced {{braces}}",
            variables=(
                VariableDefinition(name="template", type=VariableType.STRING),
                VariableDefinition(name="braces", type=VariableType.STRING),
            ),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        issues = template.validate_syntax()
        assert issues == []

    def test_validate_syntax_with_unbalanced_braces(self) -> None:
        """Should detect unbalanced braces."""
        template = PromptTemplate(
            id="test-1",
            name="Test",
            content="Template with {unbalanced brace",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        issues = template.validate_syntax()
        assert len(issues) > 0
        assert any("Unbalanced braces" in issue for issue in issues)

    def test_create_new_version(self) -> None:
        """Should create a new version of the template."""
        original = PromptTemplate(
            id="test-1",
            name="Original",
            content="Original content {{var}}",
            variables=(
                VariableDefinition(name="var", type=VariableType.STRING),
            ),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            version=1,
        )

        new_version = original.create_new_version(
            content="Updated content {{var}}", name="Updated"
        )

        assert new_version.id != original.id
        assert new_version.version == 2
        assert new_version.parent_version_id == original.id
        assert new_version.name == "Updated"
        assert new_version.content == "Updated content {{var}}"

    def test_create_new_version_keeps_original_values(self) -> None:
        """Should keep original values when not specified."""
        original = PromptTemplate(
            id="test-1",
            name="Original",
            content="Original content {{var}}",
            variables=(
                VariableDefinition(name="var", type=VariableType.STRING),
            ),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            version=1,
            tags=("original",),
        )

        new_version = original.create_new_version()

        assert new_version.name == "Original"
        assert new_version.content == "Original content {{var}}"
        assert new_version.tags == ("original",)

    def test_to_dict_and_from_dict(self) -> None:
        """Should serialize and deserialize correctly."""
        original = PromptTemplate(
            id="test-1",
            name="Test Template",
            content="Generate {{name}} with mood {{mood}}.",
            variables=(
                VariableDefinition(
                    name="name",
                    type=VariableType.STRING,
                    description="Character name",
                ),
                VariableDefinition(
                    name="mood",
                    type=VariableType.STRING,
                    default_value="happy",
                    required=False,
                ),
            ),
            model_config=ModelConfig(
                provider="openai",
                model_name="gpt-4",
                temperature=0.8,
                max_tokens=2000,
            ),
            tags=("character", "generation"),
            description="A template for generating characters",
            version=2,
        )

        data = original.to_dict()
        restored = PromptTemplate.from_dict(data)

        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.content == original.content
        assert len(restored.variables) == len(original.variables)
        assert restored.version == original.version
        assert restored.tags == original.tags
        assert restored.model_config.temperature == original.model_config.temperature

    def test_factory_method_create(self) -> None:
        """Should create template using factory method."""
        template = PromptTemplate.create(
            name="Factory Test",
            content="Hello {{name}} from {{location}}.",
            provider="anthropic",
            model_name="claude-3-opus",
            temperature=0.5,
            tags=("greeting",),
        )

        assert template.name == "Factory Test"
        assert len(template.variables) == 2  # Auto-detected
        assert template.model_config.provider == "anthropic"
        assert template.model_config.model_name == "claude-3-opus"
        assert template.model_config.temperature == 0.5

    def test_factory_method_auto_detects_variables(self) -> None:
        """Should auto-detect variables from content."""
        template = PromptTemplate.create(
            name="Auto Detect",
            content="Vars: {{foo}}, {{bar}}, {{baz}}",
        )

        var_names = {v.name for v in template.variables}
        assert var_names == {"foo", "bar", "baz"}

    def test_factory_method_with_explicit_variables(self) -> None:
        """Should use provided variables instead of auto-detecting."""
        variables = [
            VariableDefinition(
                name="foo",
                type=VariableType.STRING,
                description="The foo variable",
            ),
            VariableDefinition(
                name="bar",
                type=VariableType.STRING,
                description="The bar variable",
            ),
        ]

        template = PromptTemplate.create(
            name="Explicit Vars",
            content="Vars: {{foo}}, {{bar}}",
            variables=variables,
        )

        # Should use the explicitly defined variables
        assert len(template.variables) == 2
        var_names = {v.name for v in template.variables}
        assert var_names == {"foo", "bar"}

    def test_value_to_string_converts_list(self) -> None:
        """Should convert list to comma-separated string."""
        template = PromptTemplate(
            id="test-1",
            name="Test",
            content="Items: {{items}}",
            variables=(
                VariableDefinition(name="items", type=VariableType.LIST),
            ),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        result = template._value_to_string(["a", "b", "c"])
        assert result == "a, b, c"

    def test_value_to_string_converts_dict(self) -> None:
        """Should convert dict to key=value pairs."""
        template = PromptTemplate(
            id="test-1",
            name="Test",
            content="Config: {{config}}",
            variables=(
                VariableDefinition(name="config", type=VariableType.DICT),
            ),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        result = template._value_to_string({"key": "value", "num": 42})
        assert "key=value" in result
        assert "num=42" in result

    def test_value_to_string_handles_none(self) -> None:
        """Should convert None to empty string."""
        template = PromptTemplate(
            id="test-1",
            name="Test",
            content="Value: {{value}}",
            variables=(
                VariableDefinition(name="value", type=VariableType.STRING),
            ),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        result = template._value_to_string(None)
        assert result == ""

    def test_normalizes_list_to_tuple(self) -> None:
        """Should normalize list variables to tuple."""
        template = PromptTemplate(
            id="test-1",
            name="Test",
            content="Content",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            tags=["tag1", "tag2"],  # List instead of tuple
        )

        assert isinstance(template.tags, tuple)
        assert template.tags == ("tag1", "tag2")

    def test_normalizes_variables_to_tuple(self) -> None:
        """Should normalize list variables to tuple."""
        variables = [
            VariableDefinition(name="var1", type=VariableType.STRING),
            VariableDefinition(name="var2", type=VariableType.STRING),
        ]

        template = PromptTemplate(
            id="test-1",
            name="Test",
            content="Content with {{var1}} and {{var2}}",
            variables=variables,  # List instead of tuple
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        assert isinstance(template.variables, tuple)
        assert len(template.variables) == 2

    def test_normalizes_timestamps_to_utc(self) -> None:
        """Should normalize timestamps to UTC."""
        from datetime import timedelta

        created_at = datetime.now(tz=None)  # Naive datetime
        updated_at = datetime.now(timezone.utc) + timedelta(hours=1)

        template = PromptTemplate(
            id="test-1",
            name="Test",
            content="Content",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            created_at=created_at,
            updated_at=updated_at,
        )

        assert template.created_at.tzinfo == timezone.utc
        assert template.updated_at.tzinfo == timezone.utc

    def test_render_non_strict_mode_skips_missing_required(self) -> None:
        """Should skip missing required variables in non-strict mode."""
        template = PromptTemplate(
            id="test-1",
            name="Test",
            content="Hello {{name}}",
            variables=(
                VariableDefinition(
                    name="name", type=VariableType.STRING, required=True
                ),
            ),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        # Non-strict mode should use default or leave placeholder
        result = template.render({}, strict=False)
        # With no default, it uses the default_value which is None
        # and _value_to_string converts None to empty string
        assert result == "Hello "

    def test_complex_template_with_multiple_variables(self) -> None:
        """Should handle complex templates with multiple variables."""
        template = PromptTemplate(
            id="test-1",
            name="Complex",
            content="""Character Profile: {{name}}
Age: {{age}}
Traits: {{traits}}
Background: {{background}}

Generate a story scene featuring this character with {{mood}} tone.""",
            variables=(
                VariableDefinition(name="name", type=VariableType.STRING),
                VariableDefinition(name="age", type=VariableType.INTEGER),
                VariableDefinition(name="traits", type=VariableType.LIST),
                VariableDefinition(name="background", type=VariableType.STRING),
                VariableDefinition(name="mood", type=VariableType.STRING),
            ),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        result = template.render({
            "name": "Elena",
            "age": 28,
            "traits": ["brave", "curious", "kind"],
            "background": "A scholar from the capital",
            "mood": "mysterious",
        })

        assert "Character Profile: Elena" in result
        assert "Age: 28" in result
        assert "Traits: brave, curious, kind" in result
        assert "mysterious tone" in result
