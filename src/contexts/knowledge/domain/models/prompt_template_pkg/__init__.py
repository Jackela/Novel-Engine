"""Prompt Template Package.

Domain entity for versioned, manageable prompt templates.

Constitution Compliance:
- Article I (DDD): Entity with identity and behavior
- Article I (DDD): Self-validating with invariants
- Article II (Hexagonal): Domain model independent of infrastructure
"""

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
