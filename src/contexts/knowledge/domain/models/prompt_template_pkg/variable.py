"""Prompt Template Variable Types.

Variable type definitions for prompt templates.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


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
        description: Human-readable description
        required: Whether this variable must be provided
        validation_pattern: Optional regex pattern for validation
        enum_values: Optional list of allowed values
    """

    name: str
    type: VariableType = VariableType.STRING
    default_value: Optional[Any] = None
    description: str = ""
    required: bool = True
    validation_pattern: Optional[str] = None
    enum_values: Optional[tuple[str, ...]] = None

    def __post_init__(self) -> None:
        """Validate variable definition."""
        # Validate name format
        if not self.name:
            raise ValueError("Variable name cannot be empty")
        if not self.name.replace("_", "").isalnum():
            raise ValueError(
                f"Variable name '{self.name}' must be alphanumeric or underscore"
            )

        # Validate default value matches type
        if self.default_value is not None:
            self._validate_value(self.default_value)

        # Validate enum values
        if self.enum_values is not None:
            if not isinstance(self.enum_values, tuple):
                object.__setattr__(  # type: ignore[unreachable]
                    self, "enum_values", tuple(self.enum_values)
                )
            for val in self.enum_values:
                self._validate_value(val)

    def coerce_value(self, value: Any) -> Any:
        """Coerce a value to match this variable's type.
        
        Args:
            value: The value to coerce
            
        Returns:
            The coerced value
            
        Raises:
            ValueError: If the value cannot be coerced
        """
        if value is None:
            return self.default_value
            
        coercers = {
            VariableType.STRING: lambda v: str(v),
            VariableType.INTEGER: lambda v: int(v) if isinstance(v, (int, float, str)) and not isinstance(v, bool) else (_ for _ in ()).throw(ValueError(f"Cannot coerce {v!r} to int")),
            VariableType.FLOAT: lambda v: float(v) if isinstance(v, (int, float, str)) and not isinstance(v, bool) else (_ for _ in ()).throw(ValueError(f"Cannot coerce {v!r} to float")),
            VariableType.BOOLEAN: lambda v: bool(v) if not isinstance(v, str) else v.lower() in ('true', '1', 'yes', 'on'),
            VariableType.LIST: lambda v: list(v) if isinstance(v, (list, tuple)) else [v],
            VariableType.DICT: lambda v: dict(v) if isinstance(v, dict) else (_ for _ in ()).throw(ValueError(f"Cannot coerce {v!r} to dict")),
        }
        
        coercer = coercers.get(self.type)
        if coercer:
            result = coercer(value)
            # Validate after coercion
            self._validate_value(result)
            return result
        return value
    
    def _validate_value(self, value: Any) -> None:
        """Validate a value against this variable's type."""
        type_validators = {
            VariableType.STRING: lambda v: isinstance(v, str),
            VariableType.INTEGER: lambda v: isinstance(v, int) and not isinstance(
                v, bool
            ),
            VariableType.FLOAT: lambda v: isinstance(v, (int, float))
            and not isinstance(v, bool),
            VariableType.BOOLEAN: lambda v: isinstance(v, bool),
            VariableType.LIST: lambda v: isinstance(v, list),
            VariableType.DICT: lambda v: isinstance(v, dict),
        }

        validator = type_validators.get(self.type)
        if validator and not validator(value):
            raise ValueError(
                f"Value {value!r} does not match type {self.type.value}"
            )

    def validate(self, value: Any) -> tuple[bool, Optional[str]]:
        """
        Validate a value against this definition.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required
        if value is None:
            if self.required and self.default_value is None:
                return False, f"Required variable '{self.name}' is missing"
            return True, None

        # Check type
        try:
            self._validate_value(value)
        except ValueError as e:
            return False, str(e)

        # Check pattern
        if self.validation_pattern and isinstance(value, str):
            import re

            if not re.match(self.validation_pattern, value):
                return (
                    False,
                    f"Value '{value}' does not match pattern '{self.validation_pattern}'",
                )

        # Check enum
        if self.enum_values is not None and value not in self.enum_values:
            return False, f"Value '{value}' not in allowed values {self.enum_values}"

        return True, None

    def with_default(self, value: Any) -> VariableDefinition:
        """Create a new definition with different default value."""
        return VariableDefinition(
            name=self.name,
            type=self.type,
            default_value=value,
            description=self.description,
            required=self.required,
            validation_pattern=self.validation_pattern,
            enum_values=self.enum_values,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.type.value,
            "default_value": self.default_value,
            "description": self.description,
            "required": self.required,
            "validation_pattern": self.validation_pattern,
            "enum_values": list(self.enum_values) if self.enum_values else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VariableDefinition:
        """Create from dictionary."""
        return cls(
            name=data["name"],
            type=VariableType(data.get("type", "string")),
            default_value=data.get("default_value"),
            description=data.get("description", ""),
            required=data.get("required", True),
            validation_pattern=data.get("validation_pattern"),
            enum_values=tuple(data["enum_values"]) if data.get("enum_values") else None,
        )
