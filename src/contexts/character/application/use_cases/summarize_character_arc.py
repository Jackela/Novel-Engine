"""Summarize character arc use case.

This use case generates a comprehensive summary of a character's
journey, personality, and experiences using Honcho's reasoning capabilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.contexts.character.domain.ports.memory_port import (
    CharacterMemoryPort,
    MemoryQueryError,
)


@dataclass(frozen=True)
class SummarizeCharacterArcRequest:
    """Request to summarize a character's arc.

    Attributes:
        character_id: The character to summarize.
        story_id: Optional story/workspace context.
        session_id: Optional specific session to focus on.
        honcho_session_id: Optional Honcho session ID (overrides session_id).
        focus: Optional specific aspect to emphasize.
            Options: "personality", "relationships", "growth", "motivations", "all"
        format_style: Output format preference.
            Options: "narrative", "bullet_points", "structured"
    """

    character_id: UUID
    story_id: str | None = None
    session_id: str | None = None
    honcho_session_id: str | None = None
    focus: str = "all"
    format_style: str = "narrative"

    def __post_init__(self) -> None:
        valid_focus = ("personality", "relationships", "growth", "motivations", "all")
        if self.focus not in valid_focus:
            raise ValueError(
                f"Invalid focus: {self.focus}. Must be one of {valid_focus}"
            )

        valid_formats = ("narrative", "bullet_points", "structured")
        if self.format_style not in valid_formats:
            raise ValueError(f"Invalid format_style: {self.format_style}")


@dataclass(frozen=True)
class CharacterArcSummaryDTO:
    """Data transfer object for character arc summary.

    Attributes:
        character_id: The character's ID.
        summary: Main narrative summary of the character.
        personality_traits: Key personality characteristics.
        key_events: Major events in the character's journey.
        relationships: Important relationships.
        growth_arc: How the character has developed.
        current_motivations: What drives the character now.
        session_count: Number of memory sessions.
        memory_count: Total memories recorded.
    """

    character_id: UUID
    summary: str
    personality_traits: list[str]
    key_events: list[str]
    relationships: list[str]
    growth_arc: str
    current_motivations: str
    session_count: int
    memory_count: int

    def to_prompt_injection(self) -> str:
        """Convert summary to a prompt-friendly format.

        Returns:
            Formatted string for LLM system prompts.
        """
        lines = [
            "## Character Profile",
            "",
            f"{self.summary}",
            "",
            "### Personality",
        ]

        for trait in self.personality_traits:
            lines.append(f"- {trait}")

        lines.extend(
            [
                "",
                "### Key Events",
            ]
        )

        for event in self.key_events[:5]:  # Top 5 events
            lines.append(f"- {event}")

        if self.relationships:
            lines.extend(
                [
                    "",
                    "### Important Relationships",
                ]
            )
            for rel in self.relationships[:5]:
                lines.append(f"- {rel}")

        lines.extend(
            [
                "",
                "### Growth Arc",
                f"{self.growth_arc}",
                "",
                "### Current Motivations",
                f"{self.current_motivations}",
            ]
        )

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "character_id": str(self.character_id),
            "summary": self.summary,
            "personality_traits": self.personality_traits,
            "key_events": self.key_events,
            "relationships": self.relationships,
            "growth_arc": self.growth_arc,
            "current_motivations": self.current_motivations,
            "session_count": self.session_count,
            "memory_count": self.memory_count,
        }


@dataclass(frozen=True)
class SummarizeCharacterArcResponse:
    """Response from character arc summarization.

    Attributes:
        arc_summary: The structured character arc summary.
        raw_representation: Honcho's raw representation text.
        generated_at: Timestamp of generation.
    """

    arc_summary: CharacterArcSummaryDTO
    raw_representation: str
    generated_at: str


class SummarizeCharacterArcUseCase:
    """Use case for summarizing character arcs.

    Leverages Honcho's reasoning capabilities to synthesize a
    comprehensive understanding of a character from their memories.

    Example:
        >>> use_case = SummarizeCharacterArcUseCase(memory_port)
        >>> request = SummarizeCharacterArcRequest(
        ...     character_id=character_id,
        ...     focus="growth",
        ...     format_style="narrative",
        ... )
        >>> response = await use_case.execute(request)
        >>> prompt_context = response.arc_summary.to_prompt_injection()
    """

    def __init__(self, memory_port: CharacterMemoryPort) -> None:
        """Initialize the use case.

        Args:
            memory_port: The memory storage port implementation.
        """
        self._memory_port = memory_port

    async def execute(
        self,
        request: SummarizeCharacterArcRequest,
    ) -> SummarizeCharacterArcResponse:
        """Execute the use case.

        Args:
            request: The summarization request.

        Returns:
            SummarizeCharacterArcResponse containing the character arc summary.

        Raises:
            MemoryQueryError: If query operation fails.
        """
        try:
            # Use honcho_session_id if provided, otherwise use session_id
            effective_session_id = request.honcho_session_id or request.session_id

            # Get the character summary from memory port
            summary = await self._memory_port.get_character_summary(
                character_id=request.character_id,
                story_id=request.story_id,
                session_id=effective_session_id,
            )

            # Optionally query for specific focus areas
            focus_queries = {
                "personality": "What are this character's key personality traits and characteristics?",
                "relationships": "What are this character's most important relationships?",
                "growth": "How has this character grown or changed over time?",
                "motivations": "What are this character's current motivations and goals?",
            }

            personality_traits: list[str] = []
            relationships: list[str] = []
            growth_arc = ""
            motivations = ""

            if request.focus in focus_queries:
                answer = await self._memory_port.query_character(
                    character_id=request.character_id,
                    question=focus_queries[request.focus],
                    story_id=request.story_id,
                    session_id=effective_session_id,
                )

                if request.focus == "personality":
                    personality_traits = self._extract_list_items(answer)
                elif request.focus == "relationships":
                    relationships = self._extract_list_items(answer)
                elif request.focus == "growth":
                    growth_arc = answer
                elif request.focus == "motivations":
                    motivations = answer

            # If querying all aspects
            if request.focus == "all":
                # Query personality
                personality_answer = await self._memory_port.query_character(
                    character_id=request.character_id,
                    question=focus_queries["personality"],
                    story_id=request.story_id,
                    session_id=effective_session_id,
                )
                personality_traits = self._extract_list_items(personality_answer)

                # Query relationships
                rel_answer = await self._memory_port.query_character(
                    character_id=request.character_id,
                    question=focus_queries["relationships"],
                    story_id=request.story_id,
                    session_id=effective_session_id,
                )
                relationships = self._extract_list_items(rel_answer)

                # Query growth
                growth_answer = await self._memory_port.query_character(
                    character_id=request.character_id,
                    question=focus_queries["growth"],
                    story_id=request.story_id,
                    session_id=effective_session_id,
                )
                growth_arc = growth_answer

                # Query motivations
                mot_answer = await self._memory_port.query_character(
                    character_id=request.character_id,
                    question=focus_queries["motivations"],
                    story_id=request.story_id,
                    session_id=effective_session_id,
                )
                motivations = mot_answer

            # Get key events from memory list
            memories = await self._memory_port.get_character_memories(
                character_id=request.character_id,
                story_id=request.story_id,
                session_id=effective_session_id,
                limit=20,
            )

            key_events = [
                m.content
                for m in memories
                if m.metadata.get("importance") in ("high", "critical")
            ][:10]

            # Build the DTO
            arc_summary = CharacterArcSummaryDTO(
                character_id=request.character_id,
                summary=summary,
                personality_traits=personality_traits
                or ["Character personality still developing"],
                key_events=key_events or ["No major events recorded yet"],
                relationships=relationships or [],
                growth_arc=growth_arc or "Character arc in early stages",
                current_motivations=motivations
                or "Character motivations not yet clear",
                session_count=len(memories) // 10 + 1,  # Estimate
                memory_count=len(memories),
            )

            response = SummarizeCharacterArcResponse(
                arc_summary=arc_summary,
                raw_representation=summary,
                generated_at=datetime.utcnow().isoformat(),
            )

            return response

        except MemoryQueryError:
            raise
        except Exception as e:
            raise MemoryQueryError(f"Failed to summarize character arc: {e}")

    def _extract_list_items(self, text: str) -> list[str]:
        """Extract list items from a text response.

        Tries to parse bullet points, numbered lists, etc.
        """
        lines = text.strip().split("\n")
        items = []

        for line in lines:
            line = line.strip()
            # Remove common list markers
            for marker in ("- ", "* ", "• ", "1. ", "2. ", "3. ", "4. ", "5. "):
                if line.startswith(marker):
                    line = line[len(marker) :]
                    break

            if line and len(line) > 3:
                items.append(line)

        return items[:10]  # Limit to top 10
