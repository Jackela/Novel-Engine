#!/usr/bin/env python3
"""
Speech and format adaptation for personas.
"""

import logging
import re
from typing import Any, Dict

from src.templates.context_renderer import RenderFormat
from src.templates.dynamic_template_engine import TemplateContext

from .persona_models import CharacterArchetype, CharacterPersona

logger = logging.getLogger(__name__)


class SpeechAdapter:
    """Adapts speech patterns and formatting for personas."""

    async def _apply_persona_post_processing(
        self, render_result: Any, persona: CharacterPersona, context: TemplateContext
    ) -> Any:
        """Apply enhanced persona-specific post-processing to render result"""
        if not hasattr(render_result, "rendered_content"):
            return render_result

        content = render_result.rendered_content

        # Apply enhanced speech pattern adaptations
        if persona.speech_patterns:
            for pattern_type, pattern_config in persona.speech_patterns.items():
                if pattern_type == "formality_level":
                    content = self._adjust_formality(content, pattern_config)
                elif pattern_type == "vocabulary_preference":
                    content = self._adjust_vocabulary(content, pattern_config)
                elif pattern_type == "sentence_structure":
                    content = self._adjust_sentence_structure(content, pattern_config)

        # Apply enhanced archetype-specific formatting
        content = self._apply_archetype_formatting(content, persona.archetype)

        # Update enhanced render result
        render_result.rendered_content = content

        return render_result

    def _adjust_formality(self, content: str, formality_config: Any) -> str:
        """Apply enhanced formality adjustments to content"""
        if isinstance(formality_config, str):
            if formality_config == "high":
                # Replace contractions and informal language
                replacements = {
                    "can't": "cannot",
                    "won't": "will not",
                    "don't": "do not",
                    "isn't": "is not",
                    "aren't": "are not",
                    "we'll": "we will",
                    "I'll": "I will",
                }
                for informal, formal in replacements.items():
                    content = content.replace(informal, formal)
            elif formality_config == "low":
                # Add contractions (simplified)
                replacements = {
                    "cannot": "can't",
                    "will not": "won't",
                    "do not": "don't",
                    "is not": "isn't",
                    "are not": "aren't",
                }
                for formal, informal in replacements.items():
                    content = content.replace(formal, informal)

        return content

    def _adjust_vocabulary(self, content: str, vocab_config: Any) -> str:
        """Apply enhanced vocabulary adjustments to content"""
        if isinstance(vocab_config, dict):
            for old_word, new_word in vocab_config.items():
                content = content.replace(old_word, new_word)

        return content

    def _adjust_sentence_structure(self, content: str, structure_config: Any) -> str:
        """Apply enhanced sentence structure adjustments"""
        # This is a simplified implementation - could be enhanced with NLP
        if isinstance(structure_config, str):
            if structure_config == "short":
                # Split long sentences (very basic)
                sentences = content.split(". ")
                short_sentences = []
                for sentence in sentences:
                    if len(sentence) > 100:  # Arbitrary threshold
                        # Try to split on conjunctions
                        parts = sentence.replace(" and ", ". ").replace(" but ", ". ")
                        short_sentences.append(parts)
                    else:
                        short_sentences.append(sentence)
                content = ". ".join(short_sentences)

        return content

    def _apply_archetype_formatting(
        self, content: str, archetype: CharacterArchetype
    ) -> str:
        """Apply enhanced archetype-specific formatting"""
        # Add archetype-specific prefixes or formatting
        archetype_prefixes = {
            CharacterArchetype.WARRIOR: "BATTLE REPORT\n",
            CharacterArchetype.SCHOLAR: "ACADEMIC ANALYSIS\n",
            CharacterArchetype.LEADER: "COMMAND BRIEFING\n",
            CharacterArchetype.MYSTIC: "SPIRITUAL GUIDANCE\n",
            CharacterArchetype.ENGINEER: "TECHNICAL ASSESSMENT\n",
            CharacterArchetype.DIPLOMAT: "DIPLOMATIC COMMUNICATION\n",
            CharacterArchetype.GUARDIAN: "PROTECTION PROTOCOL\n",
            CharacterArchetype.SURVIVOR: "SURVIVAL ASSESSMENT\n",
        }

        if archetype in archetype_prefixes:
            content = archetype_prefixes[archetype] + content

        return content
