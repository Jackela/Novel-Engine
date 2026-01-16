#!/usr/bin/env python3
"""
Meta-Prompting Optimizer.

This module provides multi-round iterative optimization of user prompts
using LLM-based meta-prompting techniques.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import Language, StoryGenre

logger = logging.getLogger(__name__)


@dataclass
class PromptAnalysis:
    """Analysis result of a user prompt."""

    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    missing_elements: List[str] = field(default_factory=list)
    clarity_score: float = 0.0  # 0-10
    specificity_score: float = 0.0  # 0-10
    creativity_score: float = 0.0  # 0-10
    overall_score: float = 0.0  # 0-10
    suggestions: List[str] = field(default_factory=list)


@dataclass
class OptimizationResult:
    """Result of prompt optimization."""

    original_prompt: str
    optimized_prompt: str
    suggestions_applied: List[str]
    iteration: int
    improvements_made: List[str]
    final_analysis: Optional[PromptAnalysis] = None


class PromptOptimizer:
    """
    Meta-prompting optimizer for user-defined prompts.

    Uses LLM-based analysis and iterative improvement to help users
    create better story prompts.
    """

    # Analysis prompt templates
    ANALYSIS_PROMPT_EN = """You are an expert prompt engineer specializing in creative writing prompts.
Analyze the following user-written story prompt and provide detailed feedback.

User Prompt:
```
{prompt}
```

Genre Context: {genre}

Provide your analysis in the following JSON format:
{{
    "strengths": ["list of what the prompt does well"],
    "weaknesses": ["list of areas that could be improved"],
    "missing_elements": ["important elements that are missing for this genre"],
    "clarity_score": <0-10>,
    "specificity_score": <0-10>,
    "creativity_score": <0-10>,
    "overall_score": <0-10>,
    "suggestions": ["specific, actionable suggestions for improvement"]
}}

Consider these aspects:
1. Clarity: Is the prompt clear about what kind of story is desired?
2. Specificity: Does it provide enough detail to guide the LLM effectively?
3. Creativity: Does it encourage creative and engaging storytelling?
4. Genre fit: Does it include elements appropriate for {genre}?
5. Structure: Does it set up character, conflict, and setting effectively?

Respond ONLY with the JSON object, no additional text."""

    ANALYSIS_PROMPT_ZH = """你是一位专注于创意写作提示的专家提示工程师。
分析以下用户编写的故事提示并提供详细反馈。

用户提示:
```
{prompt}
```

类型背景: {genre}

请按以下 JSON 格式提供分析:
{{
    "strengths": ["提示做得好的地方列表"],
    "weaknesses": ["可以改进的地方列表"],
    "missing_elements": ["该类型缺少的重要元素"],
    "clarity_score": <0-10>,
    "specificity_score": <0-10>,
    "creativity_score": <0-10>,
    "overall_score": <0-10>,
    "suggestions": ["具体、可操作的改进建议"]
}}

考虑以下方面:
1. 清晰度: 提示是否清楚地表达了想要什么样的故事?
2. 具体性: 是否提供了足够的细节来有效引导 LLM?
3. 创意性: 是否鼓励有创意和吸引人的叙事?
4. 类型契合: 是否包含适合 {genre} 的元素?
5. 结构: 是否有效地设置了角色、冲突和场景?

仅回复 JSON 对象，不要有额外文字。"""

    IMPROVEMENT_PROMPT_EN = """You are an expert prompt engineer. Improve the following story prompt based on the suggestion provided.

Original Prompt:
```
{prompt}
```

Suggestion to Apply:
{suggestion}

Genre: {genre}

Guidelines:
1. Apply ONLY the specific suggestion provided
2. Preserve the original intent and voice of the prompt
3. Keep the improved prompt concise but effective
4. Maintain the same language style as the original

Return ONLY the improved prompt, with no explanations or additional text."""

    IMPROVEMENT_PROMPT_ZH = """你是一位专家提示工程师。根据提供的建议改进以下故事提示。

原始提示:
```
{prompt}
```

要应用的建议:
{suggestion}

类型: {genre}

指南:
1. 仅应用提供的特定建议
2. 保留提示的原始意图和语气
3. 保持改进后的提示简洁但有效
4. 保持与原文相同的语言风格

仅返回改进后的提示，不要解释或额外文字。"""

    OPTIMIZATION_PROMPT_EN = """You are an expert prompt engineer optimizing a story prompt for {genre} stories.

Original User Prompt:
```
{prompt}
```

Analysis of the prompt:
- Strengths: {strengths}
- Weaknesses: {weaknesses}
- Missing elements: {missing}

Create an optimized version that:
1. Keeps the core intent and creative vision
2. Addresses the weaknesses identified
3. Incorporates missing genre elements naturally
4. Improves clarity and specificity
5. Enhances creativity triggers

Return ONLY the optimized prompt, no explanations."""

    OPTIMIZATION_PROMPT_ZH = """你是一位专家提示工程师，正在优化 {genre} 故事的提示。

原始用户提示:
```
{prompt}
```

提示分析:
- 优点: {strengths}
- 缺点: {weaknesses}
- 缺失元素: {missing}

创建优化版本:
1. 保持核心意图和创意愿景
2. 解决发现的缺点
3. 自然地融入缺失的类型元素
4. 提高清晰度和具体性
5. 增强创意触发点

仅返回优化后的提示，不要解释。"""

    def __init__(self, llm_service: Optional[Any] = None):
        """
        Initialize the optimizer.

        Args:
            llm_service: Optional LLM service instance. If not provided,
                        will lazily initialize when needed.
        """
        self._llm_service = llm_service

    def _get_llm_service(self) -> Any:
        """Get or create the LLM service."""
        if self._llm_service is None:
            from src.core.llm_service import UnifiedLLMService

            self._llm_service = UnifiedLLMService()
        return self._llm_service

    async def analyze(
        self,
        user_prompt: str,
        genre: Optional[StoryGenre] = None,
        language: Language = Language.ENGLISH,
    ) -> PromptAnalysis:
        """
        Analyze a user prompt for quality and improvement opportunities.

        Args:
            user_prompt: The prompt to analyze
            genre: Optional genre for context-aware analysis
            language: Language for analysis

        Returns:
            PromptAnalysis with detailed feedback
        """
        import json

        from src.core.llm_service import LLMProvider, LLMRequest, ResponseFormat

        genre_name = genre.value if genre else "general fiction"

        # Select analysis prompt based on language
        if language == Language.CHINESE:
            analysis_prompt = self.ANALYSIS_PROMPT_ZH.format(
                prompt=user_prompt, genre=genre_name
            )
        else:
            analysis_prompt = self.ANALYSIS_PROMPT_EN.format(
                prompt=user_prompt, genre=genre_name
            )

        llm_service = self._get_llm_service()

        request = LLMRequest(
            prompt=analysis_prompt,
            provider=LLMProvider.GEMINI,
            response_format=ResponseFormat.NARRATIVE_FORMAT,
            temperature=0.3,  # Low temperature for consistent analysis
            max_tokens=2000,
            cache_enabled=True,
            requester="prompt_optimizer",
        )

        response = await llm_service.generate(request)

        # Parse the JSON response
        try:
            # Clean up response content
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            analysis_data = json.loads(content)

            return PromptAnalysis(
                strengths=analysis_data.get("strengths", []),
                weaknesses=analysis_data.get("weaknesses", []),
                missing_elements=analysis_data.get("missing_elements", []),
                clarity_score=float(analysis_data.get("clarity_score", 5.0)),
                specificity_score=float(analysis_data.get("specificity_score", 5.0)),
                creativity_score=float(analysis_data.get("creativity_score", 5.0)),
                overall_score=float(analysis_data.get("overall_score", 5.0)),
                suggestions=analysis_data.get("suggestions", []),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse analysis response: {e}")
            # Return a basic analysis on failure
            return PromptAnalysis(
                strengths=["User prompt provided"],
                weaknesses=["Analysis parsing failed"],
                suggestions=["Please try again or simplify the prompt"],
                overall_score=5.0,
            )

    async def suggest_improvements(
        self,
        user_prompt: str,
        genre: Optional[StoryGenre] = None,
        language: Language = Language.ENGLISH,
    ) -> List[str]:
        """
        Get specific improvement suggestions for a prompt.

        Args:
            user_prompt: The prompt to improve
            genre: Optional genre for context
            language: Language for suggestions

        Returns:
            List of improvement suggestions
        """
        analysis = await self.analyze(user_prompt, genre, language)
        return analysis.suggestions

    async def apply_suggestion(
        self,
        prompt: str,
        suggestion: str,
        genre: Optional[StoryGenre] = None,
        language: Language = Language.ENGLISH,
    ) -> str:
        """
        Apply a single improvement suggestion to a prompt.

        Args:
            prompt: The original prompt
            suggestion: The suggestion to apply
            genre: Optional genre for context
            language: Language of the prompt

        Returns:
            The improved prompt
        """
        from src.core.llm_service import LLMProvider, LLMRequest, ResponseFormat

        genre_name = genre.value if genre else "general fiction"

        if language == Language.CHINESE:
            improvement_prompt = self.IMPROVEMENT_PROMPT_ZH.format(
                prompt=prompt, suggestion=suggestion, genre=genre_name
            )
        else:
            improvement_prompt = self.IMPROVEMENT_PROMPT_EN.format(
                prompt=prompt, suggestion=suggestion, genre=genre_name
            )

        llm_service = self._get_llm_service()

        request = LLMRequest(
            prompt=improvement_prompt,
            provider=LLMProvider.GEMINI,
            response_format=ResponseFormat.NARRATIVE_FORMAT,
            temperature=0.5,
            max_tokens=2000,
            cache_enabled=False,  # Don't cache creative improvements
            requester="prompt_optimizer",
        )

        response = await llm_service.generate(request)
        return response.content.strip()

    async def optimize(
        self,
        user_prompt: str,
        genre: Optional[StoryGenre] = None,
        language: Language = Language.ENGLISH,
        max_iterations: int = 3,
        target_score: float = 8.0,
    ) -> OptimizationResult:
        """
        Perform multi-round iterative optimization of a prompt.

        Args:
            user_prompt: The prompt to optimize
            genre: Optional genre for context-aware optimization
            language: Language of the prompt
            max_iterations: Maximum optimization iterations
            target_score: Target overall score to achieve (0-10)

        Returns:
            OptimizationResult with the optimized prompt and details
        """
        from src.core.llm_service import LLMProvider, LLMRequest, ResponseFormat

        current_prompt = user_prompt
        improvements_made: List[str] = []
        suggestions_applied: List[str] = []

        for iteration in range(1, max_iterations + 1):
            logger.info("Optimization iteration in progress")

            # Analyze current prompt
            analysis = await self.analyze(current_prompt, genre, language)

            # Check if we've reached the target score
            if analysis.overall_score >= target_score:
                logger.info(
                    f"Target score {target_score} achieved at iteration {iteration}"
                )
                break

            # If no suggestions, we're done
            if not analysis.suggestions:
                logger.info("No more suggestions available")
                break

            # Apply optimization using analyzed strengths/weaknesses
            genre_name = genre.value if genre else "general fiction"

            if language == Language.CHINESE:
                opt_prompt = self.OPTIMIZATION_PROMPT_ZH.format(
                    genre=genre_name,
                    prompt=current_prompt,
                    strengths=", ".join(analysis.strengths) or "None identified",
                    weaknesses=", ".join(analysis.weaknesses) or "None identified",
                    missing=", ".join(analysis.missing_elements) or "None",
                )
            else:
                opt_prompt = self.OPTIMIZATION_PROMPT_EN.format(
                    genre=genre_name,
                    prompt=current_prompt,
                    strengths=", ".join(analysis.strengths) or "None identified",
                    weaknesses=", ".join(analysis.weaknesses) or "None identified",
                    missing=", ".join(analysis.missing_elements) or "None",
                )

            llm_service = self._get_llm_service()

            request = LLMRequest(
                prompt=opt_prompt,
                provider=LLMProvider.GEMINI,
                response_format=ResponseFormat.NARRATIVE_FORMAT,
                temperature=0.6,
                max_tokens=3000,
                cache_enabled=False,
                requester="prompt_optimizer",
            )

            response = await llm_service.generate(request)
            optimized = response.content.strip()

            # Track what was done
            if analysis.weaknesses:
                improvements_made.extend(
                    [f"Addressed: {w}" for w in analysis.weaknesses[:2]]
                )
            if analysis.suggestions:
                suggestions_applied.extend(analysis.suggestions[:2])

            current_prompt = optimized

        # Final analysis
        final_analysis = await self.analyze(current_prompt, genre, language)

        return OptimizationResult(
            original_prompt=user_prompt,
            optimized_prompt=current_prompt,
            suggestions_applied=suggestions_applied,
            iteration=iteration,
            improvements_made=improvements_made,
            final_analysis=final_analysis,
        )

    async def quick_optimize(
        self,
        user_prompt: str,
        genre: Optional[StoryGenre] = None,
        language: Language = Language.ENGLISH,
    ) -> str:
        """
        Perform a single-pass quick optimization.

        Args:
            user_prompt: The prompt to optimize
            genre: Optional genre for context
            language: Language of the prompt

        Returns:
            The optimized prompt
        """
        result = await self.optimize(
            user_prompt=user_prompt,
            genre=genre,
            language=language,
            max_iterations=1,
        )
        return result.optimized_prompt


# Convenience functions for common operations
async def analyze_prompt(
    prompt: str,
    genre: Optional[str] = None,
    language: str = "en",
) -> Dict[str, Any]:
    """
    Analyze a prompt and return analysis as dictionary.

    Args:
        prompt: The prompt to analyze
        genre: Optional genre string
        language: Language code ("en" or "zh")

    Returns:
        Analysis dictionary
    """
    optimizer = PromptOptimizer()
    genre_enum = StoryGenre(genre) if genre else None
    lang_enum = Language(language)

    analysis = await optimizer.analyze(prompt, genre_enum, lang_enum)

    return {
        "strengths": analysis.strengths,
        "weaknesses": analysis.weaknesses,
        "missing_elements": analysis.missing_elements,
        "clarity_score": analysis.clarity_score,
        "specificity_score": analysis.specificity_score,
        "creativity_score": analysis.creativity_score,
        "overall_score": analysis.overall_score,
        "suggestions": analysis.suggestions,
    }


async def optimize_prompt(
    prompt: str,
    genre: Optional[str] = None,
    language: str = "en",
    iterations: int = 3,
) -> Dict[str, Any]:
    """
    Optimize a prompt and return result as dictionary.

    Args:
        prompt: The prompt to optimize
        genre: Optional genre string
        language: Language code
        iterations: Maximum iterations

    Returns:
        Optimization result dictionary
    """
    optimizer = PromptOptimizer()
    genre_enum = StoryGenre(genre) if genre else None
    lang_enum = Language(language)

    result = await optimizer.optimize(prompt, genre_enum, lang_enum, iterations)

    return {
        "original_prompt": result.original_prompt,
        "optimized_prompt": result.optimized_prompt,
        "suggestions_applied": result.suggestions_applied,
        "iteration": result.iteration,
        "improvements_made": result.improvements_made,
        "final_score": (
            result.final_analysis.overall_score if result.final_analysis else None
        ),
    }


__all__ = [
    "OptimizationResult",
    "PromptAnalysis",
    "PromptOptimizer",
    "analyze_prompt",
    "optimize_prompt",
]

