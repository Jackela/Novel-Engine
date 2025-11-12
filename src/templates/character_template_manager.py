#!/usr/bin/env python3
"""
Compatibility shim for legacy imports.

Older code imports CharacterArchetype/CharacterPersona from
`src.templates.character_template_manager`. The modern layout places these
in `src.templates.character.persona_models` and re-exports via
`src.templates.character`.
"""

from src.templates.character import CharacterArchetype, CharacterPersona  # re-export

__all__ = ["CharacterArchetype", "CharacterPersona"]

