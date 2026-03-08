"""Relationship history generation strategy."""

from typing import TYPE_CHECKING, Any

import structlog

from .base_strategy import WorldGenerationStrategy

if TYPE_CHECKING:
    from ..llm_world_generator import CharacterData, RelationshipHistoryResult

logger = structlog.get_logger(__name__)


class RelationshipHistoryStrategy(WorldGenerationStrategy):
    """Strategy for generating relationship history between characters."""

    def execute(
        self,
        character_a: "CharacterData",
        character_b: "CharacterData",
        trust: int = 50,
        romance: int = 0,
    ) -> "RelationshipHistoryResult":
        """Generate backstory explaining the relationship between two characters.

        Args:
            character_a: First character
            character_b: Second character
            trust: Current trust level (0-100)
            romance: Current romance level (0-100)

        Returns:
            RelationshipHistoryResult with generated backstory
        """
        from ..llm_world_generator import RelationshipHistoryResult

        log = logger.bind(
            character_a=character_a.name,
            character_b=character_b.name,
            trust=trust,
            romance=romance,
        )
        log.info("Starting relationship history generation")

        try:
            system_prompt = self._load_prompt("relationship_history_gen")
            user_prompt = self._build_user_prompt(
                character_a, character_b, trust, romance
            )

            response_text = self._call_gemini(system_prompt, user_prompt)
            result = self._parse_response(response_text)

            log.info("Relationship history generation completed")
            return result

        except Exception as exc:
            log.error("Relationship history generation failed", error=str(exc))
            return RelationshipHistoryResult(
                backstory="Unable to generate relationship history.",
                error=str(exc),
            )

    def _build_user_prompt(
        self,
        character_a: "CharacterData",
        character_b: "CharacterData",
        trust: int,
        romance: int,
    ) -> str:
        """Build the user prompt for relationship history generation."""

        def format_character(char: "CharacterData", label: str) -> str:
            psychology_section = "Not specified"
            if char.psychology:
                psych = char.psychology
                psychology_section = (
                    f"Openness: {psych.get('openness', 50)}, "
                    f"Conscientiousness: {psych.get('conscientiousness', 50)}, "
                    f"Extraversion: {psych.get('extraversion', 50)}, "
                    f"Agreeableness: {psych.get('agreeableness', 50)}, "
                    f"Neuroticism: {psych.get('neuroticism', 50)}"
                )

            traits_section = "None specified"
            if char.traits:
                traits_section = ", ".join(char.traits)

            return f"""{label}:
  Name: {char.name}
  Psychology (Big Five): {psychology_section}
  Traits: {traits_section}"""

        char_a_section = format_character(character_a, "CHARACTER A")
        char_b_section = format_character(character_b, "CHARACTER B")

        return f"""Generate a relationship history for these two characters:

{char_a_section}

{char_b_section}

CURRENT RELATIONSHIP METRICS:
  Trust Level: {trust}/100
  Romance Level: {romance}/100

Based on these personalities and their current trust/romance levels, create a
backstory that explains how they got to this point. Consider their psychology
and traits when determining what conflicts or connections would naturally arise.

Return valid JSON only with the exact structure specified in the system prompt."""

    def _parse_response(self, content: str) -> "RelationshipHistoryResult":
        """Parse the LLM response into a RelationshipHistoryResult."""
        from ..llm_world_generator import RelationshipHistoryResult

        payload = self._extract_json(content)

        return RelationshipHistoryResult(
            backstory=str(payload.get("backstory", "Unable to generate backstory.")),
            first_meeting=payload.get("first_meeting"),
            defining_moment=payload.get("defining_moment"),
            current_status=payload.get("current_status"),
        )


__all__ = ["RelationshipHistoryStrategy"]
