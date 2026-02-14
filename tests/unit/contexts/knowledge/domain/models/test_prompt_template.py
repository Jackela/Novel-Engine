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

pytestmark = pytest.mark.unit

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


class TestPromptTemplateInheritance:
    """Tests for PromptTemplate inheritance and include functionality."""

    def test_extends_field_initialization(self) -> None:
        """Should initialize with empty extends tuple by default."""
        template = PromptTemplate(
            id="test-1",
            name="Child",
            content="Child content with {{var}}",
            variables=(VariableDefinition(name="var", type=VariableType.STRING),),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )
        assert template.extends == ()

    def test_extends_field_with_parents(self) -> None:
        """Should initialize with parent template references."""
        template = PromptTemplate(
            id="test-1",
            name="Child",
            content="{{> parent_a}} and {{> parent_b}}",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            extends=("parent_a", "parent_b"),
        )
        assert template.extends == ("parent_a", "parent_b")

    def test_extends_normalized_to_tuple(self) -> None:
        """Should convert list extends to tuple."""
        template = PromptTemplate(
            id="test-1",
            name="Child",
            content="{{> parent}}",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            extends=["parent_a", "parent_b"],  # type: ignore[arg-type]
        )
        assert isinstance(template.extends, tuple)
        assert template.extends == ("parent_a", "parent_b")

    def test_cannot_extend_self(self) -> None:
        """Should raise error when template extends itself."""
        with pytest.raises(ValueError, match="cannot extend itself"):
            PromptTemplate(
                id="test-1",
                name="SelfRef",
                content="{{var}}",
                variables=(VariableDefinition(name="var", type=VariableType.STRING),),
                model_config=ModelConfig(provider="openai", model_name="gpt-4"),
                extends=("test-1",),
            )

    def test_get_includes_extracts_template_names(self) -> None:
        """Should extract template names from {{> template}} directives."""
        template = PromptTemplate(
            id="test-1",
            name="Child",
            content="{{> base_prompt}}\nSome content\n{{> another_template}}",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )
        includes = template.get_includes()
        assert includes == {"base_prompt", "another_template"}

    def test_get_includes_empty_when_no_includes(self) -> None:
        """Should return empty set when no includes present."""
        template = PromptTemplate(
            id="test-1",
            name="NoIncludes",
            content="Just {{var}} content",
            variables=(VariableDefinition(name="var", type=VariableType.STRING),),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )
        assert template.get_includes() == set()

    def test_resolve_content_replaces_single_include(self) -> None:
        """Should replace {{> template}} with parent content."""
        parent = PromptTemplate(
            id="parent-1",
            name="BasePrompt",
            content="Base content with {{var}}",
            variables=(VariableDefinition(name="var", type=VariableType.STRING),),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        child = PromptTemplate(
            id="child-1",
            name="ChildPrompt",
            content="{{> BasePrompt}}\nAdditional child content",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        resolved = child.resolve_content({"BasePrompt": parent, "child-1": child})
        assert "Base content with {{var}}" in resolved
        assert "Additional child content" in resolved
        assert "{{>" not in resolved  # Include directive should be replaced

    def test_resolve_content_replaces_multiple_includes(self) -> None:
        """Should replace multiple {{> template}} directives."""
        header = PromptTemplate(
            id="header-1",
            name="Header",
            content="# System Header\nYou are a helpful assistant.",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        footer = PromptTemplate(
            id="footer-1",
            name="Footer",
            content="# System Footer\nEnd of conversation.",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        child = PromptTemplate(
            id="child-1",
            name="Combined",
            content="{{> Header}}\n\nMiddle content\n\n{{> Footer}}",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        resolved = child.resolve_content({
            "Header": header,
            "Footer": footer,
            "child-1": child,
        })

        assert "# System Header" in resolved
        assert "You are a helpful assistant" in resolved
        assert "Middle content" in resolved
        assert "# System Footer" in resolved
        assert "End of conversation" in resolved

    def test_resolve_content_by_id(self) -> None:
        """Should find parent template by ID."""
        parent = PromptTemplate(
            id="parent-id-123",
            name="BasePrompt",
            content="Parent content",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        child = PromptTemplate(
            id="child-1",
            name="ChildPrompt",
            content="{{> parent-id-123}}",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        resolved = child.resolve_content({
            "parent-id-123": parent,
            "child-1": child,
        })

        assert "Parent content" in resolved

    def test_resolve_content_missing_parent_raises_error(self) -> None:
        """Should raise error when parent template not found."""
        child = PromptTemplate(
            id="child-1",
            name="ChildPrompt",
            content="{{> nonexistent}}",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        with pytest.raises(ValueError, match="Parent template 'nonexistent' not found"):
            child.resolve_content({"child-1": child})

    def test_resolve_content_detects_circular_reference(self) -> None:
        """Should detect circular references in includes."""
        template_a = PromptTemplate(
            id="a-1",
            name="TemplateA",
            content="{{> TemplateB}}",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        template_b = PromptTemplate(
            id="b-1",
            name="TemplateB",
            content="{{> TemplateA}}",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        with pytest.raises(ValueError, match="Circular reference detected"):
            template_a.resolve_content({
                "TemplateA": template_a,
                "TemplateB": template_b,
            })

    def test_resolve_variables_merges_parent_variables(self) -> None:
        """Should merge variables from parent templates."""
        parent = PromptTemplate(
            id="parent-1",
            name="BasePrompt",
            content="Base {{parent_var}}",
            variables=(
                VariableDefinition(name="parent_var", type=VariableType.STRING),
                VariableDefinition(name="shared_var", type=VariableType.STRING),
            ),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        child = PromptTemplate(
            id="child-1",
            name="ChildPrompt",
            content="Child {{child_var}} and {{shared_var}}",
            variables=(
                VariableDefinition(name="child_var", type=VariableType.STRING),
                VariableDefinition(name="shared_var", type=VariableType.STRING),  # Override
            ),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            extends=("BasePrompt",),
        )

        resolved = child.resolve_variables({"BasePrompt": parent, "child-1": child})

        var_names = [v.name for v in resolved]
        assert "parent_var" in var_names  # From parent
        assert "child_var" in var_names  # From child
        # shared_var should appear once (child overrides parent)
        assert var_names.count("shared_var") == 1

    def test_resolve_variables_child_overrides_parent(self) -> None:
        """Should allow child to override parent variables."""
        parent_var = VariableDefinition(
            name="context",
            type=VariableType.STRING,
            description="Parent context",
            required=True,
        )

        child_var = VariableDefinition(
            name="context",
            type=VariableType.STRING,
            description="Child context (overrides parent)",
            required=False,
            default_value="default context",
        )

        parent = PromptTemplate(
            id="parent-1",
            name="BasePrompt",
            content="Base {{context}}",
            variables=(parent_var,),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        child = PromptTemplate(
            id="child-1",
            name="ChildPrompt",
            content="Child {{context}}",
            variables=(child_var,),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            extends=("BasePrompt",),
        )

        resolved = child.resolve_variables({"BasePrompt": parent, "child-1": child})

        # Should have only one context variable (child's version)
        context_vars = [v for v in resolved if v.name == "context"]
        assert len(context_vars) == 1
        assert context_vars[0].required is False  # Child's version
        assert context_vars[0].default_value == "default context"

    def test_resolve_variables_multiple_parents(self) -> None:
        """Should merge variables from multiple parent templates."""
        parent_a = PromptTemplate(
            id="parent-a",
            name="ParentA",
            content="A {{var_a}}",
            variables=(
                VariableDefinition(name="var_a", type=VariableType.STRING),
                VariableDefinition(name="shared", type=VariableType.STRING),
            ),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        parent_b = PromptTemplate(
            id="parent-b",
            name="ParentB",
            content="B {{var_b}}",
            variables=(
                VariableDefinition(name="var_b", type=VariableType.STRING),
                VariableDefinition(name="shared", type=VariableType.STRING),
            ),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        child = PromptTemplate(
            id="child-1",
            name="Child",
            content="Child {{var_c}}",
            variables=(VariableDefinition(name="var_c", type=VariableType.STRING),),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            extends=("ParentA", "ParentB"),
        )

        resolved = child.resolve_variables({
            "ParentA": parent_a,
            "ParentB": parent_b,
            "child-1": child,
        })

        var_names = [v.name for v in resolved]
        assert "var_a" in var_names  # From ParentA
        assert "var_b" in var_names  # From ParentB
        assert "var_c" in var_names  # From child
        assert "shared" in var_names  # From parents (first occurrence kept)

    def test_render_with_inheritance_simple(self) -> None:
        """Should render template with inheritance."""
        parent = PromptTemplate(
            id="parent-1",
            name="BasePrompt",
            content="Hello {{name}}, welcome to {{place}}.",
            variables=(
                VariableDefinition(name="name", type=VariableType.STRING),
                VariableDefinition(name="place", type=VariableType.STRING),
            ),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        child = PromptTemplate(
            id="child-1",
            name="Greeting",
            content="{{> BasePrompt}}\nHave a great day!",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        result = child.render_with_inheritance(
            variables={"name": "Alice", "place": "Wonderland"},
            parent_templates={"BasePrompt": parent, "Greeting": child},
        )

        assert "Hello Alice, welcome to Wonderland." in result
        assert "Have a great day!" in result

    def test_render_with_inheritance_variable_override(self) -> None:
        """Should render with child variables overriding parent."""
        parent = PromptTemplate(
            id="parent-1",
            name="BasePrompt",
            content="Tone: {{tone}}\nContent: {{content}}",
            variables=(
                VariableDefinition(
                    name="tone",
                    type=VariableType.STRING,
                    default_value="neutral",
                ),
                VariableDefinition(name="content", type=VariableType.STRING),
            ),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        # Child overrides tone to have different default
        child = PromptTemplate(
            id="child-1",
            name="EnthusiasticPrompt",
            content="{{> BasePrompt}}",
            variables=(
                VariableDefinition(
                    name="tone",
                    type=VariableType.STRING,
                    default_value="enthusiastic",
                    required=False,
                ),
            ),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        result = child.render_with_inheritance(
            variables={"content": "Great news!"},
            parent_templates={"BasePrompt": parent, "EnthusiasticPrompt": child},
            strict=False,
        )

        assert "Tone: enthusiastic" in result  # Child's default used
        assert "Content: Great news!" in result

    def test_render_with_inheritance_composition(self) -> None:
        """Should compose multiple parent templates."""
        header = PromptTemplate(
            id="header-1",
            name="Header",
            content="=== {{title}} ===",
            variables=(VariableDefinition(name="title", type=VariableType.STRING),),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        body = PromptTemplate(
            id="body-1",
            name="Body",
            content="By {{author}}:\n{{text}}",
            variables=(
                VariableDefinition(name="author", type=VariableType.STRING),
                VariableDefinition(name="text", type=VariableType.STRING),
            ),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        child = PromptTemplate(
            id="child-1",
            name="Document",
            content="{{> Header}}\n\n{{> Body}}",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        result = child.render_with_inheritance(
            variables={
                "title": "My Story",
                "author": "Alice",
                "text": "Once upon a time...",
            },
            parent_templates={
                "Header": header,
                "Body": body,
                "Document": child,
            },
        )

        assert "=== My Story ===" in result
        assert "By Alice:" in result
        assert "Once upon a time..." in result

    def test_to_dict_includes_extends(self) -> None:
        """Should serialize extends field to dict."""
        template = PromptTemplate(
            id="test-1",
            name="Child",
            content="{{> parent}}",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            extends=("parent_a", "parent_b"),
        )

        data = template.to_dict()
        assert "extends" in data
        assert data["extends"] == ["parent_a", "parent_b"]

    def test_from_dict_loads_extends(self) -> None:
        """Should load extends field from dict."""
        data = {
            "id": "test-1",
            "name": "Child",
            "content": "{{> parent}}",
            "variables": [],
            "model_config": {
                "provider": "openai",
                "model_name": "gpt-4",
            },
            "extends": ["parent_a", "parent_b"],
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-01T00:00:00+00:00",
        }

        template = PromptTemplate.from_dict(data)
        assert template.extends == ("parent_a", "parent_b")

    def test_create_version_diff_includes_extends(self) -> None:
        """Should include extends_changed in version diff."""
        template = PromptTemplate(
            id="test-1",
            name="Child",
            content="{{> parent}}",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            extends=("parent_a",),
        )

        diff = template.create_version_diff(extends=("parent_a", "parent_b"))
        assert diff["extends_changed"] is True

    def test_create_new_version_preserves_extends(self) -> None:
        """Should preserve extends when creating new version."""
        v1 = PromptTemplate(
            id="v1",
            name="Child",
            content="Original {{> parent}}",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            extends=("parent_a", "parent_b"),
        )

        v2 = v1.create_new_version(content="Updated {{> parent}}")

        assert v2.extends == ("parent_a", "parent_b")
        assert v2.version == 2
        assert v2.parent_version_id == "v1"

    def test_check_circular_extends_chain(self) -> None:
        """Should detect circular references in extends chain."""
        template_a = PromptTemplate(
            id="a-1",
            name="TemplateA",
            content="Content A",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            extends=("TemplateB",),
        )

        template_b = PromptTemplate(
            id="b-1",
            name="TemplateB",
            content="Content B",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            extends=("TemplateC",),
        )

        template_c = PromptTemplate(
            id="c-1",
            name="TemplateC",
            content="Content C",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            extends=("TemplateA",),  # Creates circular chain A -> B -> C -> A
        )

        parent_templates = {
            "TemplateA": template_a,
            "TemplateB": template_b,
            "TemplateC": template_c,
        }

        with pytest.raises(ValueError, match="Circular reference detected"):
            template_a.check_circular_extends(parent_templates)

    def test_check_circular_extends_no_cycles(self) -> None:
        """Should not raise error for valid non-circular extends."""
        base = PromptTemplate(
            id="base-1",
            name="BaseTemplate",
            content="Base content",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        middle = PromptTemplate(
            id="middle-1",
            name="MiddleTemplate",
            content="Middle content",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            extends=("BaseTemplate",),
        )

        child = PromptTemplate(
            id="child-1",
            name="ChildTemplate",
            content="Child content",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            extends=("MiddleTemplate",),
        )

        parent_templates = {
            "BaseTemplate": base,
            "MiddleTemplate": middle,
            "ChildTemplate": child,
        }

        # Should not raise any error
        child.check_circular_extends(parent_templates)

    def test_check_circular_extends_multiple_parents_no_cycle(self) -> None:
        """Should handle multiple extends without cycles."""
        parent_a = PromptTemplate(
            id="parent-a",
            name="ParentA",
            content="Content A",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        parent_b = PromptTemplate(
            id="parent-b",
            name="ParentB",
            content="Content B",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        )

        child = PromptTemplate(
            id="child-1",
            name="Child",
            content="Child content",
            variables=(),
            model_config=ModelConfig(provider="openai", model_name="gpt-4"),
            extends=("ParentA", "ParentB"),
        )

        parent_templates = {
            "ParentA": parent_a,
            "ParentB": parent_b,
            "child-1": child,
        }

        # Should not raise any error
        child.check_circular_extends(parent_templates)

