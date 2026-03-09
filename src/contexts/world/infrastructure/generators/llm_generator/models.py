"""LLM Generator Models

Data classes for LLM world generation results.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BeatSuggestion:
    """A single beat suggestion from the AI.

    Represents one suggested narrative beat with its type, content, emotional
    impact, and the AI's reasoning for the suggestion.

    Attributes:
        beat_type: Classification of the beat (action, reaction, dialogue, etc.)
        content: The suggested narrative text (1-3 sentences).
        mood_shift: Emotional impact (-5 to +5).
        rationale: AI's explanation of why this beat fits.
    """

    beat_type: str
    content: str
    mood_shift: int = 0
    rationale: Optional[str] = None


@dataclass
class BeatSuggestionResult:
    """Result of beat suggestion generation.

    Contains 3 AI-generated beat suggestions that could follow the current
    sequence, along with optional error information.

    Why 3 suggestions:
        Offering multiple options gives writers creative choice while
        preventing paralysis from too many options. The suggestions represent
        different approaches: expected continuation, dramatic turn, and
        character-focused moment.

    Attributes:
        suggestions: List of 3 BeatSuggestion objects.
        error: Error message if generation failed.
    """

    suggestions: List[BeatSuggestion] = field(default_factory=list)
    error: Optional[str] = None

    def is_error(self) -> bool:
        """Check if this result represents an error."""
        return self.error is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for API responses."""
        result: Dict[str, Any] = {
            "suggestions": [
                {
                    "beat_type": s.beat_type,
                    "content": s.content,
                    "mood_shift": s.mood_shift,
                    "rationale": s.rationale,
                }
                for s in self.suggestions
            ]
        }
        if self.error:
            result["error"] = self.error
        return result


@dataclass
class CharacterData:
    """Data structure for character information needed by dialogue generation.

    This is a simple data transfer object that can be constructed from
    a Character aggregate or from API request data. It contains only the
    fields needed for dialogue generation.

    Why a separate class: The Character aggregate in the character context
    has complex validation and domain logic. For dialogue generation, we
    only need a subset of that data in a simple format.
    """

    name: str
    psychology: Optional[Dict[str, int]] = None
    traits: Optional[List[str]] = None
    speaking_style: Optional[str] = None

    @classmethod
    def from_character_aggregate(cls, character: Any) -> "CharacterData":
        """Create CharacterData from a Character aggregate.

        Args:
            character: A Character aggregate from the character context.

        Returns:
            CharacterData with extracted fields.
        """
        psychology_dict = None
        if hasattr(character, "psychology") and character.psychology:
            psychology_dict = character.psychology.to_dict()

        traits_list = None
        if hasattr(character, "profile") and character.profile:
            if hasattr(character.profile, "traits") and character.profile.traits:
                traits_list = list(character.profile.traits)
            elif hasattr(character.profile, "personality_traits"):
                # Fallback to personality_traits if traits not set
                pt = character.profile.personality_traits
                if hasattr(pt, "quirks") and pt.quirks:
                    traits_list = list(pt.quirks)

        return cls(
            name=(
                character.profile.name
                if hasattr(character, "profile")
                else str(character)
            ),
            psychology=psychology_dict,
            traits=traits_list,
            speaking_style=None,  # Can be extended in future
        )


@dataclass
class DialogueResult:
    """Result of dialogue generation.

    Contains the generated dialogue along with optional metadata about
    the character's internal state and physical expression.

    Attributes:
        dialogue: The character's spoken words (1-3 sentences).
        internal_thought: What the character thinks but doesn't say.
        tone: Emotional tone of the response (e.g., 'defensive', 'excited').
        body_language: Physical description (e.g., 'crosses arms').
        error: Error message if generation failed.
    """

    dialogue: str
    tone: str = "neutral"
    internal_thought: Optional[str] = None
    body_language: Optional[str] = None
    error: Optional[str] = None

    def is_error(self) -> bool:
        """Check if this result represents an error."""
        return self.error is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for API responses."""
        result: Dict[str, Any] = {
            "dialogue": self.dialogue,
            "tone": self.tone,
        }
        if self.internal_thought:
            result["internal_thought"] = self.internal_thought
        if self.body_language:
            result["body_language"] = self.body_language
        if self.error:
            result["error"] = self.error
        return result


@dataclass
class RelationshipHistoryResult:
    """Result of relationship history generation.

    Contains the generated backstory along with structured elements that
    explain how two characters developed their current relationship dynamics.

    Why generate backstory: Relationships in narratives need depth. Rather than
    having writers manually create history for every character pair, the AI can
    infer plausible backstories from the current trust/romance metrics. This
    creates consistent, believable relationship histories on demand.

    Attributes:
        backstory: A 2-4 paragraph narrative explaining the relationship history.
        first_meeting: How the characters first encountered each other.
        defining_moment: The pivotal event that shaped their current dynamic.
        current_status: A summary of where they currently stand.
        error: Error message if generation failed.
    """

    backstory: str
    first_meeting: Optional[str] = None
    defining_moment: Optional[str] = None
    current_status: Optional[str] = None
    error: Optional[str] = None

    def is_error(self) -> bool:
        """Check if this result represents an error."""
        return self.error is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for API responses."""
        result: Dict[str, Any] = {
            "backstory": self.backstory,
        }
        if self.first_meeting:
            result["first_meeting"] = self.first_meeting
        if self.defining_moment:
            result["defining_moment"] = self.defining_moment
        if self.current_status:
            result["current_status"] = self.current_status
        if self.error:
            result["error"] = self.error
        return result


@dataclass
class CritiqueCategoryScore:
    """A category-specific critique score.

    Represents evaluation of a single quality dimension (pacing, voice, showing,
    dialogue) with specific issues and suggestions.

    Attributes:
        category: The quality dimension being evaluated.
        score: Score from 1-10 for this category.
        issues: List of specific problems identified in this category.
        suggestions: List of actionable improvements for this category.
    """

    category: str
    score: int
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class CritiqueResult:
    """Result of scene critique analysis.

    Contains AI-generated feedback on scene quality across multiple dimensions.
    Provides category-specific scores, overall assessment, highlights of what
    works, and actionable suggestions for improvement.

    Why scene critique:
        Writers need objective feedback on their work beyond subjective
        impressions. The AI critique analyzes specific craft elements like
        pacing, voice, showing vs. telling, and dialogue quality, providing
        actionable suggestions to elevate prose to professional standards.

    Attributes:
        overall_score: Overall quality score from 1-10.
        category_scores: List of category-specific evaluations.
        highlights: What works well in the scene.
        summary: Brief 2-3 sentence assessment.
        error: Error message if critique failed.
    """

    overall_score: int
    category_scores: List[CritiqueCategoryScore] = field(default_factory=list)
    highlights: List[str] = field(default_factory=list)
    summary: str = ""
    error: Optional[str] = None

    def is_error(self) -> bool:
        """Check if this result represents an error."""
        return self.error is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for API responses."""
        result: Dict[str, Any] = {
            "overall_score": self.overall_score,
            "category_scores": [
                {
                    "category": cat.category,
                    "score": cat.score,
                    "issues": cat.issues,
                    "suggestions": cat.suggestions,
                }
                for cat in self.category_scores
            ],
            "highlights": self.highlights,
            "summary": self.summary,
        }
        if self.error:
            result["error"] = self.error
        return result
