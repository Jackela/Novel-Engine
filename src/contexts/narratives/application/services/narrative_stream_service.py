"""
Narrative Stream Service

Provides streaming narrative generation with SSE support.
Follows the Hexagonal Architecture pattern - pure business logic,
no framework dependencies.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Iterator, List, Protocol


@dataclass(frozen=True)
class NarrativeStreamInput:
    """Input for narrative stream generation."""

    prompt: str
    world_context_summary: str
    chapter_title: str | None = None
    tone: str | None = None
    max_tokens: int = 2000


@dataclass(frozen=True)
class NarrativeChunk:
    """A single chunk of generated narrative."""

    content: str
    sequence: int
    is_final: bool = False


@dataclass(frozen=True)
class NarrativeStreamResult:
    """Metadata about the completed stream."""

    total_chunks: int
    total_characters: int
    generation_time_ms: int
    model_used: str


class NarrativeGeneratorPort(Protocol):
    """Port for narrative generation adapters."""

    def generate_stream(self, request: NarrativeStreamInput) -> Iterator[NarrativeChunk]:
        """
        Generate narrative content as a stream of chunks.

        Why streaming: Reduces perceived latency for the user. They see
        content appearing immediately rather than waiting for full generation.
        """
        ...


def _build_context_summary(
    characters: List[dict],
    locations: List[dict],
    entities: List[dict],
    current_scene: str | None,
    narrative_style: str | None,
) -> str:
    """
    Compress world context into a concise system prompt fragment.

    Why: LLM context windows are limited. We need to convey the essential
    world state without overwhelming the model or consuming too many tokens.
    """
    parts: List[str] = []

    if characters:
        char_names = [c.get("name", "Unknown") for c in characters[:5]]
        parts.append(f"Characters: {', '.join(char_names)}")

    if locations:
        loc_names = [loc.get("name", "Unknown") for loc in locations[:3]]
        parts.append(f"Locations: {', '.join(loc_names)}")

    if entities:
        entity_names = [e.get("name", "Unknown") for e in entities[:3]]
        parts.append(f"Notable entities: {', '.join(entity_names)}")

    if current_scene:
        parts.append(f"Current scene: {current_scene}")

    if narrative_style:
        parts.append(f"Style: {narrative_style}")

    return "; ".join(parts) if parts else "A new story begins..."


class DeterministicNarrativeGenerator:
    """
    Fallback narrative generator using deterministic templates.

    Why fallback: Ensures the system works without LLM access during
    development, testing, and when API limits are reached.
    """

    STORY_TEMPLATES = [
        (
            "In the depths of the ancient forest, where shadows danced with moonlight, "
            "a figure emerged from the mist. "
        ),
        (
            "The wind carried whispers of forgotten legends, "
            "tales that had been buried beneath centuries of silence. "
        ),
        (
            "She paused at the crossroads, her breath visible in the cold morning air, "
            "weighing the paths before her. "
        ),
        (
            "The old keeper spoke in riddles, his words painting pictures "
            "of worlds that existed only in memory. "
        ),
        (
            "And so the journey continued, "
            "each step bringing new revelations about the nature of destiny itself."
        ),
    ]

    def generate_stream(self, request: NarrativeStreamInput) -> Iterator[NarrativeChunk]:
        """
        Generate narrative chunks from deterministic templates.

        Simulates streaming by yielding chunks with small delays.
        """
        # Build story content from templates, incorporating prompt elements
        chunks: List[str] = []

        # Opening - incorporate chapter title if provided
        if request.chapter_title:
            chunks.append(f"## {request.chapter_title}\n\n")

        # Add context-aware opening
        if request.world_context_summary:
            chunks.append(f"*{request.world_context_summary}*\n\n")

        # Add template content
        for template in self.STORY_TEMPLATES:
            chunks.append(template)

        # Add prompt-influenced content
        if request.prompt:
            prompt_lower = request.prompt.lower()
            if "adventure" in prompt_lower:
                chunks.append(
                    "The adventure called to them, an irresistible pull toward the unknown. "
                )
            elif "mystery" in prompt_lower:
                chunks.append(
                    "But beneath the surface, secrets stirred, waiting to be uncovered. "
                )
            elif "battle" in prompt_lower or "conflict" in prompt_lower:
                chunks.append(
                    "Tension crackled in the air as adversaries faced one another. "
                )
            else:
                chunks.append(
                    "The story unfolded in ways none could have predicted. "
                )

        # Apply tone modifier
        if request.tone:
            tone_lower = request.tone.lower()
            if tone_lower == "dark":
                chunks.append("Darkness gathered at the edges, a reminder of what was at stake.")
            elif tone_lower == "hopeful":
                chunks.append("Yet hope persisted, a fragile flame against the night.")
            elif tone_lower == "mysterious":
                chunks.append("Questions multiplied, each answer spawning a dozen more.")

        # Yield chunks with sequence numbers
        for seq, chunk in enumerate(chunks):
            is_final = seq == len(chunks) - 1
            yield NarrativeChunk(content=chunk, sequence=seq, is_final=is_final)


def _select_narrative_generator() -> NarrativeGeneratorPort:
    """
    Select the appropriate narrative generator based on environment config.

    Why: Allows switching between LLM and deterministic generation
    without code changes - controlled via environment variables.
    """
    if os.getenv("ENABLE_LLM_GENERATION", "").lower() == "true":
        try:
            from src.contexts.narratives.infrastructure.generators.llm_narrative_generator import (
                LLMNarrativeGenerator,
            )

            return LLMNarrativeGenerator()
        except ImportError:
            return DeterministicNarrativeGenerator()
    return DeterministicNarrativeGenerator()


def generate_narrative_stream(
    prompt: str,
    world_context: dict,
    chapter_title: str | None = None,
    tone: str | None = None,
    max_tokens: int = 2000,
    generator: NarrativeGeneratorPort | None = None,
) -> Iterator[NarrativeChunk]:
    """
    Generate a narrative stream from the given prompt and context.

    This is the main entry point for the narrative streaming feature.

    Args:
        prompt: The user's narrative prompt/direction
        world_context: Dictionary containing characters, locations, entities
        chapter_title: Optional title for the chapter being generated
        tone: Optional tone modifier (dark, hopeful, mysterious, etc.)
        max_tokens: Maximum tokens to generate
        generator: Optional custom generator (for testing)

    Yields:
        NarrativeChunk objects containing generated content
    """
    # Build context summary from world state
    context_summary = _build_context_summary(
        characters=world_context.get("characters", []),
        locations=world_context.get("locations", []),
        entities=world_context.get("entities", []),
        current_scene=world_context.get("current_scene"),
        narrative_style=world_context.get("narrative_style"),
    )

    # Create input
    stream_input = NarrativeStreamInput(
        prompt=prompt,
        world_context_summary=context_summary,
        chapter_title=chapter_title,
        tone=tone,
        max_tokens=max_tokens,
    )

    # Select generator and stream
    selected_generator = generator or _select_narrative_generator()
    yield from selected_generator.generate_stream(stream_input)


def measure_stream_generation(
    chunks: Iterator[NarrativeChunk],
) -> tuple[List[NarrativeChunk], NarrativeStreamResult]:
    """
    Measure stream generation and collect all chunks.

    Why: Allows capturing metadata about the generation process
    for analytics and debugging.

    Returns:
        Tuple of (list of chunks, result metadata)
    """
    start_time = time.perf_counter()
    collected_chunks: List[NarrativeChunk] = []
    total_chars = 0

    for chunk in chunks:
        collected_chunks.append(chunk)
        total_chars += len(chunk.content)

    end_time = time.perf_counter()
    generation_time_ms = int((end_time - start_time) * 1000)

    result = NarrativeStreamResult(
        total_chunks=len(collected_chunks),
        total_characters=total_chars,
        generation_time_ms=generation_time_ms,
        model_used="deterministic-fallback",
    )

    return collected_chunks, result
