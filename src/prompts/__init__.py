#!/usr/bin/env python3
"""
Prompt Template System.

This module provides a decoupled, extensible prompt management system for
the ChroniclerAgent. It supports:

1. Pre-defined prompt templates for different story genres (8 types)
2. Bilingual support (English and Chinese)
3. User-customizable prompts with meta-prompting optimization
4. Persistent storage for user-defined prompts

Key Components:
- PromptTemplate: Base class for prompt templates
- PromptRegistry: Central registry for all templates
- PromptOptimizer: Meta-prompting optimizer for user prompts
- PromptStorage: Persistent storage for user-defined prompts
"""

from __future__ import annotations

# Auto-register all templates on import.
from . import templates
from .base import (
    Language,
    PromptTemplate,
    StoryGenre,
)
from .optimizer import (
    OptimizationResult,
    PromptAnalysis,
    PromptOptimizer,
    analyze_prompt,
    optimize_prompt,
)
from .registry import PromptRegistry
from .storage import PromptStorage, UserPrompt

templates.register_all_templates()

__all__ = [
    "Language",
    "OptimizationResult",
    "PromptAnalysis",
    "PromptOptimizer",
    "PromptRegistry",
    "PromptStorage",
    "PromptTemplate",
    "StoryGenre",
    "UserPrompt",
    "analyze_prompt",
    "optimize_prompt",
]
