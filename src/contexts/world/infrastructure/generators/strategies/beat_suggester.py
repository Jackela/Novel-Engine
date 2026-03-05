"""Beat suggestion strategy for narrative beats."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

import structlog

from .base_strategy import WorldGenerationStrategy

if TYPE_CHECKING:
    from ..llm_world_generator import BeatSuggestion, BeatSuggestionResult

logger = structlog.get_logger(__name__)


class BeatSuggesterStrategy(WorldGenerationStrategy):
    """Strategy for suggesting next narrative beats."""

    async def execute(
        self,
        current_beats: List[Dict[str, Any]],
        scene_context: str,
        mood_target: Optional[int] = None,
        use_rag: bool = True,
    ) -> "BeatSuggestionResult":
        """Suggest next beats for a scene.

        Args:
            current_beats: Existing beat sequence
            scene_context: Scene description
            mood_target: Optional target mood level
            use_rag: Whether to use RAG for context enrichment

        Returns:
            BeatSuggestionResult with suggestions
        """
        from ..llm_world_generator import BeatSuggestionResult

        log = logger.bind(
            num_current_beats=len(current_beats),
            has_mood_target=mood_target is not None,
            has_rag=self.generator._rag_service is not None and use_rag,
        )
        log.info("Starting beat suggestion generation")

        try:
            base_system_prompt = self._load_prompt("beat_suggester")
            user_prompt = self._build_user_prompt(current_beats, scene_context, mood_target)

            # Enrich with RAG if enabled
            if use_rag and self.generator._rag_service is not None:
                rag_query = self._extract_keywords(current_beats, scene_context, mood_target)
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

            log.info("Beat suggestion generation completed", num_suggestions=len(result.suggestions))
            return result

        except Exception as exc:
            log.error("Beat suggestion generation failed", error=str(exc))
            return BeatSuggestionResult(suggestions=[], error=str(exc))

    def _build_user_prompt(
        self,
        current_beats: List[Dict[str, Any]],
        scene_context: str,
        mood_target: Optional[int],
    ) -> str:
        """Build the user prompt for beat suggestion generation."""
        # Build current beats section
        if current_beats:
            beats_section = ""
            for i, beat in enumerate(current_beats, 1):
                beat_type = beat.get("beat_type", "unknown")
                content = beat.get("content", "")
                mood = beat.get("mood_shift", 0)
                beats_section += f"{i}. [{beat_type.upper()}] (mood: {mood:+d}) {content}\n"
        else:
            beats_section = "No beats yet - this is the start of the scene."

        # Analyze beat type balance
        beat_types = [b.get("beat_type", "").lower() for b in current_beats]
        action_count = sum(1 for t in beat_types if t in ("action", "transition"))
        reaction_count = sum(1 for t in beat_types if t in ("reaction", "dialogue"))

        if action_count > reaction_count + 1:
            balance_hint = "The scene is heavy on action - consider a reaction or dialogue."
        elif reaction_count > action_count + 1:
            balance_hint = "The scene is heavy on reaction/dialogue - consider an action."
        else:
            balance_hint = "The action/reaction balance is good."

        # Calculate mood trajectory
        if current_beats:
            mood_shifts = [b.get("mood_shift", 0) for b in current_beats]
            current_mood = sum(mood_shifts)
            mood_trend = (
                "upward" if current_mood > 0 else "downward" if current_mood < 0 else "neutral"
            )
        else:
            current_mood = 0
            mood_trend = "neutral"

        # Build mood target section
        if mood_target is not None:
            mood_diff = mood_target - current_mood
            if mood_diff > 0:
                mood_direction = f"Aim for positive mood shifts (target: {mood_target:+d}, current: {current_mood:+d})"
            elif mood_diff < 0:
                mood_direction = f"Aim for negative mood shifts (target: {mood_target:+d}, current: {current_mood:+d})"
            else:
                mood_direction = f"Maintain current mood level ({current_mood:+d})"
        else:
            mood_direction = "Follow natural story momentum"

        return f"""Suggest 3 beats to continue this scene:

SCENE CONTEXT:
{scene_context}

CURRENT BEAT SEQUENCE:
{beats_section}

PACING ANALYSIS:
- Beat type balance: {balance_hint}
- Current mood trajectory: {mood_trend} (cumulative: {current_mood:+d})
- Mood target: {mood_direction}

Generate 3 suggested beats that could follow this sequence. Each suggestion should:
1. Logically follow from the current beats
2. Move toward the mood target
3. Serve the scene's dramatic purpose

Return valid JSON only with the exact structure specified in the system prompt."""

    def _extract_keywords(
        self,
        current_beats: List[Dict[str, Any]],
        scene_context: str,
        mood_target: Optional[int],
    ) -> str:
        """Extract keywords from beat request for RAG query."""
        parts: List[str] = []
        context_words = scene_context.split()[:8]
        parts.extend(context_words)

        if mood_target is not None:
            if mood_target > 0:
                parts.append("uplifting positive")
            elif mood_target < 0:
                parts.append("tense negative dramatic")

        if current_beats:
            recent_types = [b.get("beat_type", "") for b in current_beats[-3:]]
            parts.extend(recent_types)

        return " ".join(parts)

    async def _enrich_with_rag(
        self, query: str, base_prompt: str
    ) -> tuple[str, int, int]:
        """Enrich a prompt with RAG context if available."""
        if self.generator._rag_service is None:
            return base_prompt, 0, 0

        try:
            result = await self.generator._rag_service.enrich_prompt(
                query=query, base_prompt=base_prompt
            )
            return result.prompt, result.chunks_retrieved, result.tokens_added
        except Exception as exc:
            logger.warning("rag_enrichment_failed", error=str(exc))
            return base_prompt, 0, 0

    def _parse_response(self, content: str) -> "BeatSuggestionResult":
        """Parse the LLM response into a BeatSuggestionResult."""
        from ..llm_world_generator import BeatSuggestion, BeatSuggestionResult

        payload = self._extract_json(content)

        suggestions_data = payload.get("suggestions", [])
        suggestions = []
        for item in suggestions_data[:3]:
            suggestion = BeatSuggestion(
                beat_type=str(item.get("beat_type", "action")).lower(),
                content=str(item.get("content", "")),
                mood_shift=int(item.get("mood_shift", 0)),
                rationale=item.get("rationale"),
            )
            suggestion.mood_shift = max(-5, min(5, suggestion.mood_shift))
            suggestions.append(suggestion)

        return BeatSuggestionResult(suggestions=suggestions)


__all__ = ["BeatSuggesterStrategy"]
