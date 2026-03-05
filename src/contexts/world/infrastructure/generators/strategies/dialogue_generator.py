"""Dialogue generation strategy for character-authentic speech."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

import structlog

from .base_strategy import WorldGenerationStrategy

if TYPE_CHECKING:
    from ..llm_world_generator import CharacterData, DialogueResult

logger = structlog.get_logger(__name__)


class DialogueGeneratorStrategy(WorldGenerationStrategy):
    """Strategy for generating character dialogue."""

    async def execute(
        self,
        character: "CharacterData",
        context: str,
        mood: Optional[str] = None,
        use_rag: bool = True,
    ) -> "DialogueResult":
        """Generate dialogue in character voice.

        Args:
            character: Character data for voice generation
            context: The situation the character is responding to
            mood: Optional current emotional state
            use_rag: Whether to use RAG for context enrichment

        Returns:
            DialogueResult with generated dialogue
        """
        from ..llm_world_generator import DialogueResult

        log = logger.bind(
            character_name=character.name,
            has_psychology=character.psychology is not None,
            mood=mood,
            has_rag=self.generator._rag_service is not None and use_rag,
        )
        log.info("Starting dialogue generation")

        try:
            base_system_prompt = self._load_prompt("dialogue_gen")
            user_prompt = self._build_user_prompt(character, context, mood)

            # Enrich with RAG if enabled
            if use_rag and self.generator._rag_service is not None:
                rag_query = self._extract_keywords(character, context, mood)
                system_prompt, chunks_retrieved, tokens_added = await self._enrich_with_rag(
                    rag_query, base_system_prompt
                )
                log.info(
                    "rag_context_injected",
                    chunks_retrieved=chunks_retrieved,
                    tokens_added=tokens_added,
                )
            else:
                system_prompt = base_system_prompt

            response_text = await self.generator._call_gemini(system_prompt, user_prompt)
            result = self._parse_response(response_text)

            log.info("Dialogue generation completed", tone=result.tone)
            return result

        except Exception as exc:
            log.error("Dialogue generation failed", error=str(exc))
            return DialogueResult(
                dialogue="...",
                tone="uncertain",
                error=str(exc),
            )

    def _build_user_prompt(
        self,
        character: "CharacterData",
        context: str,
        mood: Optional[str],
    ) -> str:
        """Build the user prompt for dialogue generation."""
        # Build psychology section
        psychology_section = "Not specified"
        if character.psychology:
            psych = character.psychology
            psychology_section = f"""Openness: {psych.get('openness', 50)}/100
Conscientiousness: {psych.get('conscientiousness', 50)}/100
Extraversion: {psych.get('extraversion', 50)}/100
Agreeableness: {psych.get('agreeableness', 50)}/100
Neuroticism: {psych.get('neuroticism', 50)}/100"""

        # Build traits section
        traits_section = "None specified"
        if character.traits:
            traits_section = ", ".join(character.traits)

        speaking_style = character.speaking_style or "Natural, conversational"
        mood_section = mood or "Neutral"

        return f"""Generate dialogue for this character:

CHARACTER NAME: {character.name}

PSYCHOLOGY (Big Five):
{psychology_section}

CHARACTER TRAITS:
{traits_section}

SPEAKING STYLE:
{speaking_style}

CURRENT MOOD:
{mood_section}

CONTEXT/SITUATION:
{context}

Generate a response that this character would naturally give in this situation.
Return valid JSON only with the exact structure specified in the system prompt."""

    def _extract_keywords(
        self,
        character: "CharacterData",
        context: str,
        mood: Optional[str],
    ) -> str:
        """Extract keywords from dialogue request for RAG query."""
        parts = [character.name]

        if character.traits:
            parts.extend(character.traits[:3])

        if mood:
            parts.append(mood)

        context_words = context.split()[:5]
        parts.extend(context_words)

        return " ".join(parts)

    async def _enrich_with_rag(
        self, query: str, base_prompt: str
    ) -> tuple[str, int, int]:
        """Enrich a prompt with RAG context if available."""
        if self.generator._rag_service is None:
            return base_prompt, 0, 0

        try:
            result = await self.generator._rag_service.enrich_prompt(
                query=query,
                base_prompt=base_prompt,
            )
            logger.info(
                "rag_enrichment",
                chunks_retrieved=result.chunks_retrieved,
                tokens_added=result.tokens_added,
            )
            return result.prompt, result.chunks_retrieved, result.tokens_added
        except Exception as exc:
            logger.warning(
                "rag_enrichment_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return base_prompt, 0, 0

    def _parse_response(self, content: str) -> "DialogueResult":
        """Parse the LLM response into a DialogueResult."""
        from ..llm_world_generator import DialogueResult

        payload = self._extract_json(content)

        return DialogueResult(
            dialogue=str(payload.get("dialogue", "...")),
            internal_thought=payload.get("internal_thought"),
            tone=str(payload.get("tone", "neutral")),
            body_language=payload.get("body_language"),
        )


__all__ = ["DialogueGeneratorStrategy"]
