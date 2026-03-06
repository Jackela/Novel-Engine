"""
Prompt Template Entity (Shim)

⚠️  DEPRECATION NOTICE:
    This module is kept for backward compatibility.
    Please use `src.contexts.knowledge.domain.models.prompt_template_pkg` instead.

    Old: from src.contexts.knowledge.domain.models.prompt_template import PromptTemplate
    New: from src.contexts.knowledge.domain.models.prompt_template_pkg import PromptTemplate
"""

import warnings

# Emit deprecation warning on import
warnings.warn(
    "prompt_template.py is deprecated. "
    "Use src.contexts.knowledge.domain.models.prompt_template_pkg instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export all symbols from the new package
from src.contexts.knowledge.domain.models.prompt_template_pkg.model_config import (
    ModelConfig,
)
from src.contexts.knowledge.domain.models.prompt_template_pkg.template import (
    PromptTemplate,
)
from src.contexts.knowledge.domain.models.prompt_template_pkg.variable import (
    VariableDefinition,
    VariableType,
)

__all__ = [
    "ModelConfig",
    "PromptTemplate",
    "VariableDefinition",
    "VariableType",
]
