#!/usr/bin/env python3
"""
Prompt Templates API Router.

This module provides REST API endpoints for managing prompt templates,
including listing templates, optimizing user prompts, and managing
user-defined prompts.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.prompts import (
    Language,
    PromptOptimizer,
    PromptRegistry,
    PromptStorage,
    StoryGenre,
    UserPrompt,
    analyze_prompt,
    optimize_prompt,
)

# Initialize templates on import
from src.prompts.templates import register_all_templates

logger = logging.getLogger(__name__)

# Create the router
router = APIRouter(prefix="/prompts", tags=["Prompts"])

# Global storage instance
_storage: Optional[PromptStorage] = None
_templates_registered = False


def ensure_templates_registered() -> None:
    global _templates_registered
    if _templates_registered:
        return
    if PromptRegistry.count() > 0:
        _templates_registered = True
        return
    try:
        register_all_templates()
        logger.info("Prompt templates registered: %s templates", PromptRegistry.count())
    except Exception as exc:
        logger.warning("Prompt templates registration failed: %s", exc)
    _templates_registered = True


def get_storage() -> PromptStorage:
    """Get or create the prompt storage instance."""
    global _storage
    if _storage is None:
        _storage = PromptStorage()
    return _storage


# ============================================================================
# Request/Response Models
# ============================================================================


class TemplateInfo(BaseModel):
    """Information about a prompt template."""

    id: str
    name: str
    genre: str
    language: str
    description: str


class TemplateDetailResponse(BaseModel):
    """Detailed template information."""

    id: str
    name: str
    genre: str
    language: str
    description: str
    system_prompt: str
    story_requirements: List[str]
    style_guidelines: List[str]
    example_opening: str
    world_building_elements: List[str]
    character_archetypes: List[str]
    plot_devices: List[str]
    tone_descriptors: List[str]


class TemplatesListResponse(BaseModel):
    """Response for listing templates."""

    templates: List[TemplateInfo]
    total: int


class AnalyzeRequest(BaseModel):
    """Request to analyze a user prompt."""

    prompt: str = Field(..., min_length=10, description="The prompt to analyze")
    genre: Optional[str] = Field(None, description="Genre context for analysis")
    language: str = Field("en", description="Language code (en or zh)")


class AnalyzeResponse(BaseModel):
    """Response from prompt analysis."""

    strengths: List[str]
    weaknesses: List[str]
    missing_elements: List[str]
    clarity_score: float
    specificity_score: float
    creativity_score: float
    overall_score: float
    suggestions: List[str]


class OptimizeRequest(BaseModel):
    """Request to optimize a user prompt."""

    prompt: str = Field(..., min_length=10, description="The prompt to optimize")
    genre: Optional[str] = Field(None, description="Genre for optimization")
    language: str = Field("en", description="Language code")
    max_iterations: int = Field(3, ge=1, le=5, description="Maximum iterations")


class OptimizeResponse(BaseModel):
    """Response from prompt optimization."""

    original_prompt: str
    optimized_prompt: str
    suggestions_applied: List[str]
    iteration: int
    improvements_made: List[str]
    final_score: Optional[float]


class ApplySuggestionRequest(BaseModel):
    """Request to apply a single suggestion."""

    prompt: str = Field(..., description="The original prompt")
    suggestion: str = Field(..., description="The suggestion to apply")
    genre: Optional[str] = Field(None)
    language: str = Field("en")


class ApplySuggestionResponse(BaseModel):
    """Response from applying a suggestion."""

    improved_prompt: str


class UserPromptCreate(BaseModel):
    """Request to create a user prompt."""

    user_id: str = Field(..., description="User identifier")
    name: str = Field(..., min_length=1, max_length=255, description="Prompt name")
    content: str = Field(..., min_length=10, description="Prompt content")
    genre: Optional[str] = Field(None)
    language: str = Field("en")


class UserPromptUpdate(BaseModel):
    """Request to update a user prompt."""

    content: Optional[str] = Field(None)
    name: Optional[str] = Field(None)


class UserPromptResponse(BaseModel):
    """Response containing a user prompt."""

    id: str
    user_id: str
    name: str
    content: str
    genre: Optional[str]
    language: str
    is_optimized: bool
    created_at: str
    updated_at: str


class UserPromptsListResponse(BaseModel):
    """Response for listing user prompts."""

    prompts: List[UserPromptResponse]
    total: int


# ============================================================================
# Template Endpoints
# ============================================================================


@router.get("/templates", response_model=TemplatesListResponse)
async def list_templates(
    genre: Optional[str] = Query(None, description="Filter by genre"),
    language: Optional[str] = Query(None, description="Filter by language (en/zh)"),
) -> TemplatesListResponse:
    """
    List all available prompt templates.

    Optionally filter by genre and/or language.
    """
    ensure_templates_registered()
    templates = PromptRegistry.list_all()

    # Apply filters
    if genre:
        try:
            genre_enum = StoryGenre(genre)
            templates = [t for t in templates if t.genre == genre_enum]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid genre: {genre}")

    if language:
        try:
            lang_enum = Language(language)
            templates = [t for t in templates if t.language == lang_enum]
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid language: {language}"
            )

    template_infos = [
        TemplateInfo(
            id=t.id,
            name=t.name,
            genre=t.genre.value,
            language=t.language.value,
            description=t.description,
        )
        for t in templates
    ]

    return TemplatesListResponse(templates=template_infos, total=len(template_infos))


@router.get("/templates/{template_id}", response_model=TemplateDetailResponse)
async def get_template(template_id: str) -> TemplateDetailResponse:
    """Get detailed information about a specific template."""
    ensure_templates_registered()
    template = PromptRegistry.get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")

    return TemplateDetailResponse(
        id=template.id,
        name=template.name,
        genre=template.genre.value,
        language=template.language.value,
        description=template.description,
        system_prompt=template.system_prompt,
        story_requirements=template.story_requirements,
        style_guidelines=template.style_guidelines,
        example_opening=template.example_opening,
        world_building_elements=template.world_building_elements,
        character_archetypes=template.character_archetypes,
        plot_devices=template.plot_devices,
        tone_descriptors=template.tone_descriptors,
    )


@router.get("/genres")
async def list_genres() -> Dict[str, Any]:
    """List all available story genres."""
    return {
        "genres": [
            {
                "id": genre.value,
                "name_en": genre.name.replace("_", " ").title(),
                "name_zh": {
                    "fantasy": "奇幻冒险",
                    "scifi": "科幻太空",
                    "mystery": "悬疑推理",
                    "wuxia": "武侠江湖",
                    "romance": "浪漫爱情",
                    "horror": "恐怖惊悚",
                    "historical": "历史古代",
                    "urban": "都市现代",
                }.get(genre.value, genre.value),
            }
            for genre in StoryGenre
        ]
    }


# ============================================================================
# Optimization Endpoints
# ============================================================================


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_user_prompt(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Analyze a user prompt for quality and improvement opportunities.

    Returns scores and suggestions for improvement.
    """
    try:
        result = await analyze_prompt(
            prompt=request.prompt,
            genre=request.genre,
            language=request.language,
        )
        return AnalyzeResponse(**result)
    except Exception as e:
        logger.error(f"Failed to analyze prompt: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_user_prompt(request: OptimizeRequest) -> OptimizeResponse:
    """
    Optimize a user prompt using multi-round meta-prompting.

    Iteratively improves the prompt based on analysis and suggestions.
    """
    try:
        result = await optimize_prompt(
            prompt=request.prompt,
            genre=request.genre,
            language=request.language,
            iterations=request.max_iterations,
        )
        return OptimizeResponse(**result)
    except Exception as e:
        logger.error(f"Failed to optimize prompt: {e}")
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@router.post("/apply-suggestion", response_model=ApplySuggestionResponse)
async def apply_single_suggestion(
    request: ApplySuggestionRequest,
) -> ApplySuggestionResponse:
    """Apply a single improvement suggestion to a prompt."""
    try:
        optimizer = PromptOptimizer()
        genre_enum = StoryGenre(request.genre) if request.genre else None
        lang_enum = Language(request.language)

        improved = await optimizer.apply_suggestion(
            prompt=request.prompt,
            suggestion=request.suggestion,
            genre=genre_enum,
            language=lang_enum,
        )
        return ApplySuggestionResponse(improved_prompt=improved)
    except Exception as e:
        logger.error(f"Failed to apply suggestion: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to apply suggestion: {str(e)}"
        )


# ============================================================================
# User Prompt Storage Endpoints
# ============================================================================


@router.get("/user", response_model=UserPromptsListResponse)
async def list_user_prompts(
    user_id: str = Query(..., description="User ID"),
    genre: Optional[str] = Query(None, description="Filter by genre"),
    language: Optional[str] = Query(None, description="Filter by language"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> UserPromptsListResponse:
    """List prompts saved by a user."""
    storage = get_storage()

    genre_enum = StoryGenre(genre) if genre else None
    lang_enum = Language(language) if language else None

    prompts = await storage.list_by_user(
        user_id=user_id,
        genre=genre_enum,
        language=lang_enum,
        limit=limit,
        offset=offset,
    )

    return UserPromptsListResponse(
        prompts=[
            UserPromptResponse(
                id=p.id,
                user_id=p.user_id,
                name=p.name,
                content=p.content,
                genre=p.genre.value if p.genre else None,
                language=p.language.value,
                is_optimized=p.is_optimized,
                created_at=p.created_at.isoformat(),
                updated_at=p.updated_at.isoformat(),
            )
            for p in prompts
        ],
        total=len(prompts),
    )


@router.post("/user", response_model=UserPromptResponse)
async def create_user_prompt(request: UserPromptCreate) -> UserPromptResponse:
    """Save a new user prompt."""
    from src.prompts.storage import create_user_prompt as create_prompt

    storage = get_storage()

    genre_enum = StoryGenre(request.genre) if request.genre else None
    lang_enum = Language(request.language)

    prompt = create_prompt(
        user_id=request.user_id,
        name=request.name,
        content=request.content,
        genre=genre_enum,
        language=lang_enum,
    )

    await storage.save(prompt)

    return UserPromptResponse(
        id=prompt.id,
        user_id=prompt.user_id,
        name=prompt.name,
        content=prompt.content,
        genre=prompt.genre.value if prompt.genre else None,
        language=prompt.language.value,
        is_optimized=prompt.is_optimized,
        created_at=prompt.created_at.isoformat(),
        updated_at=prompt.updated_at.isoformat(),
    )


@router.get("/user/{prompt_id}", response_model=UserPromptResponse)
async def get_user_prompt(prompt_id: str) -> UserPromptResponse:
    """Get a specific user prompt by ID."""
    storage = get_storage()
    prompt = await storage.get(prompt_id)

    if not prompt:
        raise HTTPException(status_code=404, detail=f"Prompt not found: {prompt_id}")

    return UserPromptResponse(
        id=prompt.id,
        user_id=prompt.user_id,
        name=prompt.name,
        content=prompt.content,
        genre=prompt.genre.value if prompt.genre else None,
        language=prompt.language.value,
        is_optimized=prompt.is_optimized,
        created_at=prompt.created_at.isoformat(),
        updated_at=prompt.updated_at.isoformat(),
    )


@router.put("/user/{prompt_id}", response_model=UserPromptResponse)
async def update_user_prompt(
    prompt_id: str, request: UserPromptUpdate
) -> UserPromptResponse:
    """Update a user prompt."""
    storage = get_storage()

    success = await storage.update(
        prompt_id=prompt_id,
        content=request.content,
        name=request.name,
    )

    if not success:
        raise HTTPException(status_code=404, detail=f"Prompt not found: {prompt_id}")

    prompt = await storage.get(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail=f"Prompt not found: {prompt_id}")

    return UserPromptResponse(
        id=prompt.id,
        user_id=prompt.user_id,
        name=prompt.name,
        content=prompt.content,
        genre=prompt.genre.value if prompt.genre else None,
        language=prompt.language.value,
        is_optimized=prompt.is_optimized,
        created_at=prompt.created_at.isoformat(),
        updated_at=prompt.updated_at.isoformat(),
    )


@router.delete("/user/{prompt_id}")
async def delete_user_prompt(prompt_id: str) -> Dict[str, Any]:
    """Delete a user prompt."""
    storage = get_storage()
    success = await storage.delete(prompt_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Prompt not found: {prompt_id}")

    return {"success": True, "message": f"Prompt {prompt_id} deleted"}


__all__ = ["router", "ensure_templates_registered"]
