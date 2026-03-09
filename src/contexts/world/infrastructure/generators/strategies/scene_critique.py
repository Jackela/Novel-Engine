"""Scene critique strategy for analyzing scene quality."""

from typing import TYPE_CHECKING, List, Optional

import structlog

from .base_strategy import WorldGenerationStrategy

if TYPE_CHECKING:
    from ..llm_world_generator import CritiqueResult

logger = structlog.get_logger(__name__)


class SceneCritiqueStrategy(WorldGenerationStrategy):
    """Strategy for analyzing and critiquing scene quality."""

    def execute(
        self,
        scene_text: str,
        scene_goals: Optional[List[str]] = None,
    ) -> "CritiqueResult":
        """Analyze scene quality across multiple craft dimensions.

        Args:
            scene_text: The full text content of the scene
            scene_goals: Optional list of writer's goals for the scene

        Returns:
            CritiqueResult with analysis and suggestions
        """
        from ..llm_world_generator import CritiqueResult

        log = logger.bind(
            scene_text_length=len(scene_text),
            has_scene_goals=scene_goals is not None,
        )
        log.info("Starting scene critique")

        try:
            system_prompt = self._load_prompt("scene_critique")
            user_prompt = self._build_user_prompt(scene_text, scene_goals)

            response_text = self._call_gemini(system_prompt, user_prompt)
            result = self._parse_response(response_text)

            log.info(
                "Scene critique completed",
                overall_score=result.overall_score,
                num_categories=len(result.category_scores),
            )
            return result

        except Exception as exc:
            log.error("Scene critique failed", error=str(exc))
            return CritiqueResult(
                overall_score=0,
                category_scores=[],
                highlights=[],
                summary="Unable to generate critique.",
                error=str(exc),
            )

    def _build_user_prompt(
        self,
        scene_text: str,
        scene_goals: Optional[List[str]],
    ) -> str:
        """Build the user prompt for scene critique generation."""
        # Truncate scene text if too long
        max_length = 12000
        truncated_text = (
            scene_text[:max_length] + "..."
            if len(scene_text) > max_length
            else scene_text
        )

        # Build goals section
        if scene_goals:
            goals_section = "\n".join(f"- {goal}" for goal in scene_goals)
        else:
            goals_section = "No specific goals provided - evaluate general quality."

        return f"""Critique the following scene:

SCENE TEXT:
{truncated_text}

SCENE GOALS:
{goals_section}

Analyze this scene across the four quality dimensions (pacing, voice, showing, dialogue)
and provide specific, actionable feedback. Consider how well the scene achieves its
stated goals.

Return valid JSON only with the exact structure specified in the system prompt."""

    def _parse_response(self, content: str) -> "CritiqueResult":
        """Parse the LLM response into a CritiqueResult."""
        from ..llm_world_generator import CritiqueCategoryScore, CritiqueResult

        payload = self._extract_json(content)

        # Parse overall score
        overall_score = int(payload.get("overall_score", 5))
        overall_score = max(1, min(10, overall_score))

        # Parse category scores
        category_scores_data = payload.get("category_scores", [])
        category_scores = []
        valid_categories = {"pacing", "voice", "showing", "dialogue"}

        for cat_data in category_scores_data:
            category = str(cat_data.get("category", "")).lower()
            if category not in valid_categories:
                continue

            score = int(cat_data.get("score", 5))
            score = max(1, min(10, score))

            issues = cat_data.get("issues", []) or []
            suggestions = cat_data.get("suggestions", []) or []

            if not isinstance(issues, list):
                issues = []
            if not isinstance(suggestions, list):
                suggestions = []

            category_scores.append(
                CritiqueCategoryScore(
                    category=category,
                    score=score,
                    issues=issues,
                    suggestions=suggestions,
                )
            )

        # Parse highlights
        highlights_data = payload.get("highlights", []) or []
        if not isinstance(highlights_data, list):
            highlights_data = []
        highlights = [str(h) for h in highlights_data]

        # Parse summary
        summary = str(payload.get("summary", ""))

        return CritiqueResult(
            overall_score=overall_score,
            category_scores=category_scores,
            highlights=highlights,
            summary=summary,
        )


__all__ = ["SceneCritiqueStrategy"]
