"""
Prompt Template Entity

Warzone 4: AI Brain - BRAIN-014A
Domain entity for versioned, manageable prompt templates.

Constitution Compliance:
- Article I (DDD): Entity with identity and behavior
- Article I (DDD): Self-validating with invariants
- Article II (Hexagonal): Domain model independent of infrastructure
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

if TYPE_CHECKING:
    from .prompt_version import VersionDiff, PromptVersion


def _utcnow() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


class VariableType(str, Enum):
    """Supported variable types for prompt templates."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"


@dataclass(frozen=True, slots=True)
class VariableDefinition:
    """
    Definition of a variable in a prompt template.

    Why frozen:
        Immutable definition prevents accidental modification.

    Attributes:
        name: Variable name (must match {{var}} pattern in template)
        type: Data type of the variable
        default_value: Default value if not provided
        description: Human-readable description of what this variable does
        required: Whether this variable must be provided during rendering

    Invariants:
        - name must be non-empty and alphanumeric with underscores
        - required variables cannot have None default_value
    """

    name: str
    type: VariableType
    default_value: Any = None
    description: str = ""
    required: bool = True

    def __post_init__(self) -> None:
        """Validate variable definition invariants."""
        if not self.name or not self.name.strip():
            raise ValueError("VariableDefinition.name cannot be empty")

        # Validate name format (alphanumeric, underscores, no spaces)
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", self.name):
            raise ValueError(
                f"VariableDefinition.name must be alphanumeric with underscores, got: {self.name}"
            )

        # Required variables should have a non-None default for safety
        if self.required and self.default_value is None:
            # We allow this but log a warning - the validation happens at render time
            pass

    def validate_value(self, value: Any) -> bool:
        """
        Validate that a value matches this variable's type.

        Args:
            value: The value to validate

        Returns:
            True if valid, False otherwise
        """
        if value is None:
            return not self.required

        try:
            match self.type:
                case VariableType.STRING:
                    return isinstance(value, str)
                case VariableType.INTEGER:
                    return isinstance(value, int) and not isinstance(value, bool)
                case VariableType.FLOAT:
                    return isinstance(value, (int, float)) and not isinstance(value, bool)
                case VariableType.BOOLEAN:
                    return isinstance(value, bool)
                case VariableType.LIST:
                    return isinstance(value, list)
                case VariableType.DICT:
                    return isinstance(value, dict)
        except Exception:
            return False

        return False

    def coerce_value(self, value: Any) -> Any:
        """
        Coerce a value to this variable's type.

        Args:
            value: The value to coerce

        Returns:
            The coerced value

        Raises:
            ValueError: If coercion fails
        """
        if value is None:
            if self.required:
                raise ValueError(f"Required variable '{self.name}' cannot be None")
            return self.default_value

        # Already correct type
        if self.validate_value(value):
            return value

        # Attempt coercion
        try:
            match self.type:
                case VariableType.STRING:
                    return str(value)
                case VariableType.INTEGER:
                    return int(value)
                case VariableType.FLOAT:
                    return float(value)
                case VariableType.BOOLEAN:
                    if isinstance(value, str):
                        return value.lower() in ("true", "1", "yes", "on")
                    return bool(value)
                case VariableType.LIST:
                    if isinstance(value, str):
                        return [v.strip() for v in value.split(",")]
                    return list(value)
                case VariableType.DICT:
                    if isinstance(value, str):
                        # Simple key=value,key2=value2 format
                        result = {}
                        for pair in value.split(","):
                            if "=" in pair:
                                k, v = pair.split("=", 1)
                                result[k.strip()] = v.strip()
                        return result
                    return dict(value)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"Failed to coerce value '{value}' to type {self.type.value} for variable '{self.name}': {e}"
            )

        return value


@dataclass(frozen=True, slots=True)
class ModelConfig:
    """
    Model configuration for a prompt template.

    Why frozen:
        Immutable configuration prevents accidental modification.

    Attributes:
        provider: LLM provider (openai, anthropic, gemini, ollama)
        model_name: Name of the model to use
        temperature: Sampling temperature (0.0 - 2.0)
        max_tokens: Maximum tokens to generate
        top_p: Nucleus sampling parameter (0.0 - 1.0)
        frequency_penalty: Frequency penalty (-2.0 - 2.0)
        presence_penalty: Presence penalty (-2.0 - 2.0)
        supports_functions: Whether the model supports function calling
        extra: Additional model-specific parameters
    """

    provider: str
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    supports_functions: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate model configuration invariants."""
        if not self.provider or not self.provider.strip():
            raise ValueError("ModelConfig.provider cannot be empty")

        if not self.model_name or not self.model_name.strip():
            raise ValueError("ModelConfig.model_name cannot be empty")

        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(
                f"ModelConfig.temperature must be between 0.0 and 2.0, got: {self.temperature}"
            )

        if self.max_tokens < 1:
            raise ValueError(
                f"ModelConfig.max_tokens must be positive, got: {self.max_tokens}"
            )

        if not 0.0 <= self.top_p <= 1.0:
            raise ValueError(
                f"ModelConfig.top_p must be between 0.0 and 1.0, got: {self.top_p}"
            )

        if not -2.0 <= self.frequency_penalty <= 2.0:
            raise ValueError(
                f"ModelConfig.frequency_penalty must be between -2.0 and 2.0, got: {self.frequency_penalty}"
            )

        if not -2.0 <= self.presence_penalty <= 2.0:
            raise ValueError(
                f"ModelConfig.presence_penalty must be between -2.0 and 2.0, got: {self.presence_penalty}"
            )


@dataclass
class PromptTemplate:
    """
    Entity representing a versioned, manageable prompt template.

    Why not frozen:
        Entity may need to update version and timestamps.

    Why dataclass:
        Simple value-based entity with clear structure.

    Attributes:
        id: Unique identifier for this template (UUID)
        name: Human-readable name for the template
        content: The template content with {{variable}} placeholders
        variables: List of variable definitions for this template
        model_config: Model configuration for using this template
        extends: Template IDs this template extends (inheritance/composition)
        version: Version number of this template
        parent_version_id: ID of the parent version (for version history)
        tags: Tags for categorizing and filtering templates
        description: Human-readable description of what this template does
        created_at: Timestamp when template was created
        updated_at: Timestamp when template was last updated

    Invariants:
        - id must be non-empty
        - name must be non-empty
        - content must be non-empty (after processing includes)
        - All {{variables}} in content must have corresponding definitions
        - All variable definitions must have matching {{variables}} in content (if required)
        - extends cannot contain self-reference (circular inheritance is detected at resolution time)
    """

    id: str
    name: str
    content: str
    variables: tuple[VariableDefinition, ...]
    model_config: ModelConfig
    extends: tuple[str, ...] = ()
    version: int = 1
    parent_version_id: Optional[str] = None
    tags: tuple[str, ...] = ()
    description: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    # Pattern for matching {{variable}} placeholders
    _VARIABLE_PATTERN = re.compile(r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}")

    # Pattern for matching {{> prompt_name}} include directives
    # Supports: names, IDs with dashes, underscores, and alphanumeric chars
    _INCLUDE_PATTERN = re.compile(r"\{\{>\s*([a-zA-Z_][a-zA-Z0-9_-]*)\s*\}\}")

    def __post_init__(self) -> None:
        """Validate template invariants."""
        if not self.id or not self.id.strip():
            raise ValueError("PromptTemplate.id cannot be empty")

        if not self.name or not self.name.strip():
            raise ValueError("PromptTemplate.name cannot be empty")

        if not self.content or not self.content.strip():
            raise ValueError("PromptTemplate.content cannot be empty")

        # Normalize timestamps to UTC
        if self.created_at.tzinfo is None:
            object.__setattr__(self, "created_at", self.created_at.replace(tzinfo=timezone.utc))
        else:
            object.__setattr__(self, "created_at", self.created_at.astimezone(timezone.utc))

        if self.updated_at.tzinfo is None:
            object.__setattr__(self, "updated_at", self.updated_at.replace(tzinfo=timezone.utc))
        else:
            object.__setattr__(self, "updated_at", self.updated_at.astimezone(timezone.utc))

        # Ensure variables is a tuple (immutable)
        if isinstance(self.variables, list):
            object.__setattr__(self, "variables", tuple(self.variables))

        # Ensure tags is a tuple (immutable)
        if isinstance(self.tags, list):
            object.__setattr__(self, "tags", tuple(self.tags))

        # Ensure extends is a tuple (immutable)
        if isinstance(self.extends, list):  # type: ignore[unreachable]
            object.__setattr__(self, "extends", tuple(self.extends))

        # Check for self-reference in extends
        if self.id in self.extends:
            raise ValueError(f"PromptTemplate '{self.name}' cannot extend itself")

        # Validate content against variables (include directives are allowed)
        self._validate_template()

    def _validate_template(self) -> None:
        """
        Validate that the template content is well-formed.

        Note: Include directives {{> prompt_name}} are allowed and will be
        resolved during rendering. Variables from parent templates should be
        defined or will be treated as coming from the parent.

        Raises:
            ValueError: If template has syntax errors or mismatched variables
        """
        # Find all {{variable}} placeholders in content
        content_vars = set(self._VARIABLE_PATTERN.findall(self.content))

        # Find all {{> prompt_name}} include directives
        included_templates = set(self._INCLUDE_PATTERN.findall(self.content))

        # Get defined variable names
        defined_vars = {v.name for v in self.variables}

        # Variables that come from included templates are allowed
        # We only validate variables that are NOT in included templates
        # For now, we allow undefined variables if there are includes
        # Full validation happens during rendering with parent templates

        if not included_templates:
            # No includes - strict validation
            undefined_vars = content_vars - defined_vars
            if undefined_vars:
                raise ValueError(
                    f"Template contains undefined variables: {', '.join(sorted(undefined_vars))}. "
                    f"Define them in the variables list."
                )

        # Check for required variables not used in content (warning only)
        unused_required_vars = defined_vars - content_vars
        required_but_unused = [
            v.name for v in self.variables if v.name in unused_required_vars and v.required
        ]
        if required_but_unused:
            # This is a warning condition, not an error
            pass

    def extract_variables(self) -> set[str]:
        """
        Extract all variable names from the template content.

        Returns:
            Set of variable names found in {{variable}} placeholders
        """
        return set(self._VARIABLE_PATTERN.findall(self.content))

    def render(self, variables: dict[str, Any], strict: bool = True) -> str:
        """
        Render the template with provided variable values.

        Args:
            variables: Dictionary of variable names to values
            strict: If True, raise error for missing required variables

        Returns:
            Rendered template string with variables substituted

        Raises:
            ValueError: If required variables are missing or validation fails
        """
        # Validate and coerce variables
        rendered_vars: dict[str, Any] = {}

        for var_def in self.variables:
            if var_def.name in variables:
                try:
                    rendered_vars[var_def.name] = var_def.coerce_value(
                        variables[var_def.name]
                    )
                except ValueError as e:
                    raise ValueError(
                        f"Failed to coerce value for variable '{var_def.name}': {e}"
                    )
            elif var_def.required:
                if strict:
                    raise ValueError(
                        f"Required variable '{var_def.name}' not provided. "
                        f"Description: {var_def.description}"
                    )
                # Use default value
                rendered_vars[var_def.name] = var_def.default_value
            else:
                # Optional variable, use default
                rendered_vars[var_def.name] = var_def.default_value

        # Perform substitution
        result = self.content

        for var_name, var_value in rendered_vars.items():
            placeholder = f"{{{{{var_name}}}}}"
            # Convert value to string for substitution
            str_value = self._value_to_string(var_value)
            result = result.replace(placeholder, str_value)

        return result

    def _value_to_string(self, value: Any) -> str:
        """
        Convert a value to string for template substitution.

        Args:
            value: The value to convert

        Returns:
            String representation of the value
        """
        if value is None:
            return ""

        if isinstance(value, (list, tuple)):
            return ", ".join(self._value_to_string(v) for v in value)

        if isinstance(value, dict):
            return ", ".join(f"{k}={v}" for k, v in value.items())

        return str(value)

    def validate_syntax(self) -> list[str]:
        """
        Validate template syntax and return list of issues.

        Returns:
            List of validation error messages (empty if valid)
        """
        issues: list[str] = []

        # Check for unbalanced braces
        # Count double braces separately since {{var}} is valid
        double_open = self.content.count("{{")
        double_close = self.content.count("}}")
        single_open = self.content.count("{") - double_open * 2
        single_close = self.content.count("}") - double_close * 2

        if single_open != single_close:
            issues.append(
                f"Unbalanced braces: {single_open} single open, {single_close} single close"
            )

        if double_open != double_close:
            issues.append(
                f"Unbalanced double braces: {double_open} open, {double_close} close"
            )

        # Check for single-brace placeholders (not wrapped in double braces)
        # Use negative lookbehind/lookahead to exclude {{var}}
        single_brace_placeholders = re.findall(
            r"(?<!\{)\{([a-zA-Z_][a-zA-Z0-9_]*)\}(?!\})", self.content
        )
        if single_brace_placeholders:
            issues.append(
                f"Single-brace placeholders detected (use {{{{var}}}} not {{var}}): {single_brace_placeholders[:3]}"
            )

        # Check that variables are properly defined
        for var_def in self.variables:
            if not var_def.required and var_def.default_value is None:
                issues.append(
                    f"Optional variable '{var_def.name}' should have a default value"
                )

        return issues

    def create_new_version(
        self,
        content: str | None = None,
        variables: tuple[VariableDefinition, ...] | None = None,
        model_config: ModelConfig | None = None,
        name: str | None = None,
        description: str | None = None,
        tags: tuple[str, ...] | None = None,
        extends: tuple[str, ...] | None = None,
    ) -> PromptTemplate:
        """
        Create a new version of this template.

        Args:
            content: New content (keeps current if None)
            variables: New variables (keeps current if None)
            model_config: New model config (keeps current if None)
            name: New name (keeps current if None)
            description: New description (keeps current if None)
            tags: New tags (keeps current if None)
            extends: New extends (keeps current if None)

        Returns:
            New PromptTemplate with incremented version
        """
        return PromptTemplate(
            id=str(uuid4()),
            name=name if name is not None else self.name,
            content=content if content is not None else self.content,
            variables=variables if variables is not None else self.variables,
            model_config=model_config if model_config is not None else self.model_config,
            extends=extends if extends is not None else self.extends,
            version=self.version + 1,
            parent_version_id=self.id,
            tags=tags if tags is not None else self.tags,
            description=description if description is not None else self.description,
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert template to dictionary for serialization.

        Returns:
            Dictionary representation of the template
        """
        return {
            "id": self.id,
            "name": self.name,
            "content": self.content,
            "variables": [
                {
                    "name": v.name,
                    "type": v.type.value,
                    "default_value": v.default_value,
                    "description": v.description,
                    "required": v.required,
                }
                for v in self.variables
            ],
            "model_config": {
                "provider": self.model_config.provider,
                "model_name": self.model_config.model_name,
                "temperature": self.model_config.temperature,
                "max_tokens": self.model_config.max_tokens,
                "top_p": self.model_config.top_p,
                "frequency_penalty": self.model_config.frequency_penalty,
                "presence_penalty": self.model_config.presence_penalty,
                "supports_functions": self.model_config.supports_functions,
                "extra": self.model_config.extra,
            },
            "extends": list(self.extends),
            "version": self.version,
            "parent_version_id": self.parent_version_id,
            "tags": list(self.tags),
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PromptTemplate:
        """
        Create template from dictionary.

        Args:
            data: Dictionary containing template data

        Returns:
            PromptTemplate instance
        """
        variables_data = data.get("variables", [])
        variables = tuple(
            VariableDefinition(
                name=v["name"],
                type=VariableType(v["type"]),
                default_value=v.get("default_value"),
                description=v.get("description", ""),
                required=v.get("required", True),
            )
            for v in variables_data
        )

        model_config_data = data.get("model_config", {})
        model_config = ModelConfig(
            provider=model_config_data.get("provider", "openai"),
            model_name=model_config_data.get("model_name", "gpt-4"),
            temperature=model_config_data.get("temperature", 0.7),
            max_tokens=model_config_data.get("max_tokens", 1000),
            top_p=model_config_data.get("top_p", 1.0),
            frequency_penalty=model_config_data.get("frequency_penalty", 0.0),
            presence_penalty=model_config_data.get("presence_penalty", 0.0),
            supports_functions=model_config_data.get("supports_functions", False),
            extra=model_config_data.get("extra", {}),
        )

        tags_data = data.get("tags", [])
        tags = tuple(tags_data) if isinstance(tags_data, list) else ()

        extends_data = data.get("extends", [])
        extends = tuple(extends_data) if isinstance(extends_data, list) else ()

        return cls(
            id=data["id"],
            name=data["name"],
            content=data["content"],
            variables=variables,
            model_config=model_config,
            extends=extends,
            version=data.get("version", 1),
            parent_version_id=data.get("parent_version_id"),
            tags=tags,
            description=data.get("description", ""),
            created_at=datetime.fromisoformat(data["created_at"])
            if "created_at" in data
            else _utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"])
            if "updated_at" in data
            else _utcnow(),
        )

    @classmethod
    def create(
        cls,
        name: str,
        content: str,
        variables: list[VariableDefinition] | tuple[VariableDefinition, ...] | None = None,
        provider: str = "openai",
        model_name: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        tags: list[str] | tuple[str, ...] | None = None,
        description: str = "",
        id: str | None = None,
    ) -> PromptTemplate:
        """
        Factory method to create a new PromptTemplate.

        Args:
            name: Human-readable name
            content: Template content with {{variable}} placeholders
            variables: List of variable definitions (auto-detected if None)
            provider: LLM provider
            model_name: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            tags: Tags for categorization
            description: Description of what this template does
            id: Optional explicit ID (auto-generated if not provided)

        Returns:
            New PromptTemplate instance
        """
        if variables is None:
            # Auto-detect variables from content
            detected_vars = set(re.findall(r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}", content))
            variables = tuple(
                VariableDefinition(
                    name=var_name,
                    type=VariableType.STRING,
                    description=f"Variable: {var_name}",
                    required=True,
                )
                for var_name in sorted(detected_vars)
            )

        if tags is None:
            tags = ()
        elif isinstance(tags, list):
            tags = tuple(tags)

        model_config = ModelConfig(
            provider=provider,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return cls(
            id=id or str(uuid4()),
            name=name,
            content=content,
            variables=tuple(variables) if isinstance(variables, list) else variables,
            model_config=model_config,
            tags=tags,
            description=description,
        )

    def get_includes(self) -> set[str]:
        """
        Extract all template names referenced in {{> prompt_name}} directives.

        Returns:
            Set of template names that this template includes
        """
        return set(self._INCLUDE_PATTERN.findall(self.content))

    def resolve_content(
        self,
        parent_templates: dict[str, PromptTemplate],
        visited: set[str] | None = None,
    ) -> str:
        """
        Resolve all {{> prompt_name}} include directives by replacing them
        with parent template content.

        Args:
            parent_templates: Dictionary mapping template names/IDs to PromptTemplate objects
            visited: Set of already visited template IDs (for circular reference detection)

        Returns:
            Resolved content with all includes replaced

        Raises:
            ValueError: If circular reference is detected or parent template not found
        """
        if visited is None:
            visited = set()

        if self.id in visited:
            raise ValueError(
                f"Circular reference detected: template '{self.name}' (id: {self.id}) "
                f"is referenced multiple times in the inheritance chain"
            )

        visited.add(self.id)
        result = self.content

        # Process includes in order of appearance
        for include_name in self.get_includes():
            # Find parent by name or ID
            parent = None
            for template in parent_templates.values():
                if template.name == include_name or template.id == include_name:
                    parent = template
                    break

            if parent is None:
                raise ValueError(
                    f"Parent template '{include_name}' not found. "
                    f"Available templates: {list(parent_templates.keys())}"
                )

            # Recursively resolve parent content
            parent_content = parent.resolve_content(parent_templates, visited.copy())

            # Replace the include directive with parent content
            include_pattern = re.compile(rf"\{{{{>\s*{re.escape(include_name)}\s*\}}}}")
            result = include_pattern.sub(parent_content, result)

        return result

    def resolve_variables(
        self,
        parent_templates: dict[str, PromptTemplate],
    ) -> tuple[VariableDefinition, ...]:
        """
        Resolve all variables by merging with parent template variables.

        Child variables override parent variables with the same name.
        Variables from all parents (both extends and {{> includes}}) are merged.

        Args:
            parent_templates: Dictionary mapping template names/IDs to PromptTemplate objects

        Returns:
            Tuple of combined variable definitions

        Raises:
            ValueError: If parent template not found
        """
        # Start with parent variables (in order of extends and includes)
        parent_vars: list[VariableDefinition] = []
        child_names = {v.name for v in self.variables}

        # Track visited templates to avoid duplicates
        seen_parents: set[str] = set()

        # Process both extends and {{> includes}}
        parent_refs = list(self.extends) + list(self.get_includes())

        for parent_ref in parent_refs:
            # Find parent by name or ID
            parent = None
            for template in parent_templates.values():
                if template.name == parent_ref or template.id == parent_ref:
                    parent = template
                    break

            if parent is None:
                raise ValueError(
                    f"Parent template '{parent_ref}' not found. "
                    f"Available templates: {list(parent_templates.keys())}"
                )

            if parent.id in seen_parents:
                continue  # Already processed this parent
            seen_parents.add(parent.id)

            # Recursively get parent's variables
            for var_def in parent.variables:
                # Only include if not overridden by child
                if var_def.name not in child_names:
                    parent_vars.append(var_def)

        # Add child variables (they override parents)
        return tuple(parent_vars) + self.variables

    def render_with_inheritance(
        self,
        variables: dict[str, Any],
        parent_templates: dict[str, PromptTemplate],
        strict: bool = True,
    ) -> str:
        """
        Render the template with inheritance support.

        Resolves {{> prompt_name}} includes and merges variables from parent templates.

        Args:
            variables: Dictionary of variable names to values
            parent_templates: Dictionary mapping template names/IDs to PromptTemplate objects
            strict: If True, raise error for missing required variables

        Returns:
            Rendered template string with variables substituted

        Raises:
            ValueError: If circular reference detected, parent not found, or validation fails
        """
        # Resolve content with includes
        resolved_content = self.resolve_content(parent_templates)

        # Resolve variables with inheritance
        resolved_vars = self.resolve_variables(parent_templates)

        # Directly render using resolved content and variables
        # This bypasses PromptTemplate validation since we've already merged
        rendered_vars: dict[str, Any] = {}

        for var_def in resolved_vars:
            if var_def.name in variables:
                try:
                    rendered_vars[var_def.name] = var_def.coerce_value(
                        variables[var_def.name]
                    )
                except ValueError as e:
                    raise ValueError(
                        f"Failed to coerce value for variable '{var_def.name}': {e}"
                    )
            elif var_def.required:
                if strict:
                    raise ValueError(
                        f"Required variable '{var_def.name}' not provided. "
                        f"Description: {var_def.description}"
                    )
                # Use default value
                rendered_vars[var_def.name] = var_def.default_value
            else:
                # Optional variable, use default
                rendered_vars[var_def.name] = var_def.default_value

        # Perform substitution
        result = resolved_content

        for var_name, var_value in rendered_vars.items():
            placeholder = f"{{{{{var_name}}}}}"
            # Convert value to string for substitution
            str_value = self._value_to_string(var_value)
            result = result.replace(placeholder, str_value)

        return result

    def create_version_diff(
        self,
        content: str | None = None,
        variables: tuple[VariableDefinition, ...] | None = None,
        model_config: ModelConfig | None = None,
        name: str | None = None,
        description: str | None = None,
        tags: tuple[str, ...] | None = None,
        extends: tuple[str, ...] | None = None,
    ) -> dict[str, bool]:
        """
        Create a diff of changes from the current template.

        Args:
            content: New content (None means no change)
            variables: New variables (None means no change)
            model_config: New model config (None means no change)
            name: New name (None means no change)
            description: New description (None means no change)
            tags: New tags (None means no change)
            extends: New extends (None means no change)

        Returns:
            Dictionary with boolean flags for each change type
        """
        return {
            "content_changed": content is not None and content != self.content,
            "variables_changed": variables is not None and variables != self.variables,
            "model_config_changed": model_config is not None and model_config != self.model_config,
            "name_changed": name is not None and name != self.name,
            "description_changed": description is not None and description != self.description,
            "tags_changed": tags is not None and tags != self.tags,
            "extends_changed": extends is not None and extends != self.extends,
        }


__all__ = [
    "PromptTemplate",
    "VariableDefinition",
    "VariableType",
    "ModelConfig",
]
