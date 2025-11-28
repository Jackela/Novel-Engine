#!/usr/bin/env python3
"""
Pre-defined Prompt Templates.

This module contains all pre-defined prompt templates for different story genres,
supporting both English and Chinese languages.

Templates are automatically registered with the PromptRegistry when this module
is imported.
"""

from __future__ import annotations

from ..registry import PromptRegistry

# Import all template modules to trigger registration
from . import (
    fantasy,
    historical,
    horror,
    mystery,
    romance,
    scifi,
    urban,
    wuxia,
)


def register_all_templates() -> None:
    """
    Register all pre-defined templates with the registry.

    This function is called automatically when the module is imported,
    but can also be called manually to re-register templates.
    """
    # Fantasy templates
    PromptRegistry.register(fantasy.FANTASY_EN)
    PromptRegistry.register(fantasy.FANTASY_ZH)

    # Sci-Fi templates
    PromptRegistry.register(scifi.SCIFI_EN)
    PromptRegistry.register(scifi.SCIFI_ZH)

    # Mystery templates
    PromptRegistry.register(mystery.MYSTERY_EN)
    PromptRegistry.register(mystery.MYSTERY_ZH)

    # Wuxia templates
    PromptRegistry.register(wuxia.WUXIA_EN)
    PromptRegistry.register(wuxia.WUXIA_ZH)

    # Romance templates
    PromptRegistry.register(romance.ROMANCE_EN)
    PromptRegistry.register(romance.ROMANCE_ZH)

    # Horror templates
    PromptRegistry.register(horror.HORROR_EN)
    PromptRegistry.register(horror.HORROR_ZH)

    # Historical templates
    PromptRegistry.register(historical.HISTORICAL_EN)
    PromptRegistry.register(historical.HISTORICAL_ZH)

    # Urban templates
    PromptRegistry.register(urban.URBAN_EN)
    PromptRegistry.register(urban.URBAN_ZH)


# Auto-register on import
register_all_templates()

__all__ = [
    "register_all_templates",
    "fantasy",
    "historical",
    "horror",
    "mystery",
    "romance",
    "scifi",
    "urban",
    "wuxia",
]
