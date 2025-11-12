#!/usr/bin/env python3
"""
Content Generation Coordinator
===============================

Extracted from IntegrationOrchestrator as part of God Class refactoring.
Manages story content generation using traditional and AI-enhanced systems.

Responsibilities:
- Generate traditional story content
- Generate AI-enhanced story content with recommendations
- Apply AI enhancements (quality analysis, analytics)
- Track story generation analytics
- Integrate with user preference and narrative guidance systems

This class follows the Single Responsibility Principle by focusing solely on
content generation, separate from integration orchestration.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from src.core.data_models import StandardResponse

from .analytics_platform import AnalyticsEvent
from .recommendation_engine import UserProfile

logger = logging.getLogger(__name__)


class ContentGenerationCoordinator:
    """
    Coordinates story content generation using traditional and AI-enhanced systems.

    This class encapsulates all content generation logic, providing a clean
    interface for generating story content with various enhancement levels,
    quality analysis, and analytics tracking.
    """

    def __init__(self, ai_coordinator, config):
        """
        Initialize the content generation coordinator.

        Args:
            ai_coordinator: AISubsystemCoordinator instance for AI systems access
            config: IntegrationConfig instance for mode and feature gate checking
        """
        self.ai_coordinator = ai_coordinator
        self.config = config

        logger.info("Content Generation Coordinator initialized successfully")

    # ===================================================================
    # Feature Gate Properties (Delegated to AI Coordinator)
    # ===================================================================

    @property
    def has_recommendation_engine(self) -> bool:
        """Check if recommendation engine is available."""
        return self.ai_coordinator.has_recommendation_engine

    @property
    def has_story_quality_engine(self) -> bool:
        """Check if story quality engine is available."""
        return self.ai_coordinator.has_story_quality_engine

    @property
    def has_analytics_platform(self) -> bool:
        """Check if analytics platform is available."""
        return self.ai_coordinator.has_analytics_platform

    # ===================================================================
    # Content Generation Methods
    # ===================================================================

    async def generate_traditional_content(
        self, prompt: str, user_id: str
    ) -> StandardResponse:
        """
        Generate content using traditional Novel Engine systems.

        Args:
            prompt: Story generation prompt
            user_id: User identifier

        Returns:
            StandardResponse: Generated traditional content
        """
        # Use traditional template system and character generation
        return StandardResponse(
            success=True,
            data={
                "content": f"Traditional story content based on: {prompt}",
                "generation_method": "traditional",
                "user_id": user_id,
                "timestamp": datetime.now(),
            },
        )

    async def generate_ai_enhanced_content(
        self,
        prompt: str,
        user_id: str,
        preferences: Optional[Dict[str, Any]],
        narrative_guidance: Optional[Dict[str, Any]] = None,
    ) -> StandardResponse:
        """
        Generate content using AI-enhanced systems with recommendations.

        Args:
            prompt: Story generation prompt
            user_id: User identifier
            preferences: User preferences for personalization
            narrative_guidance: Narrative guidance from V2 engine

        Returns:
            StandardResponse: Generated AI-enhanced content
        """
        # Get user preferences for personalization
        if preferences and self.has_recommendation_engine:
            user_profile = UserProfile(
                user_id=user_id,
                preferences={},
                behavior_patterns={},
                preference_history=[],
            )

            # Get recommendations for story elements
            await self.ai_coordinator.ai_orchestrator.recommendation_engine.get_personalized_recommendations(
                user_profile, limit=5
            )

        # Enhance content with narrative guidance
        content_data = {
            "content": f"AI-enhanced story content based on: {prompt}",
            "generation_method": "ai_enhanced",
            "user_id": user_id,
            "personalization_applied": preferences is not None,
            "timestamp": datetime.now(),
        }

        if narrative_guidance:
            content_data["narrative_guidance"] = {
                "primary_goal": narrative_guidance.get("primary_goal"),
                "target_tension": narrative_guidance.get("target_tension"),
                "pacing": narrative_guidance.get("pacing_intensity"),
                "tone": narrative_guidance.get("narrative_tone"),
                "current_phase": narrative_guidance.get("phase"),
            }

        return StandardResponse(success=True, data=content_data)

    # ===================================================================
    # Content Enhancement Methods
    # ===================================================================

    async def apply_ai_enhancements(
        self,
        content_data: Dict[str, Any],
        user_id: str,
        preferences: Optional[Dict[str, Any]],
    ) -> StandardResponse:
        """
        Apply AI enhancements like quality analysis and analytics tracking.

        Args:
            content_data: Base content data to enhance
            user_id: User identifier
            preferences: User preferences

        Returns:
            StandardResponse: Enhanced content with quality analysis and analytics
        """
        enhanced_data = content_data.copy()

        # Apply story quality analysis if available
        if self.has_story_quality_engine:
            quality_report = await self.ai_coordinator.ai_orchestrator.story_quality_engine.analyze_story_quality(
                content_data.get("content", ""),
                story_id=f"story_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            )

            if quality_report.success:
                enhanced_data["quality_analysis"] = quality_report.data

        # Track analytics if available
        if self.has_analytics_platform:
            analytics_event = AnalyticsEvent(
                event_id=f"content_gen_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                event_type="story_generation",
                user_id=user_id,
                properties={"content_length": len(content_data.get("content", ""))},
            )

            await self.ai_coordinator.ai_orchestrator.analytics_platform.track_event(
                analytics_event
            )
            enhanced_data["analytics_tracked"] = True

        return StandardResponse(success=True, data=enhanced_data)

    # ===================================================================
    # Analytics Tracking Methods
    # ===================================================================

    async def track_story_generation_analytics(
        self, user_id: str, prompt: str, response_time: float, success: bool
    ):
        """
        Track story generation analytics.

        Args:
            user_id: User identifier
            prompt: Story generation prompt
            response_time: Time taken to generate content
            success: Whether generation succeeded
        """
        if self.has_analytics_platform:
            analytics_event = AnalyticsEvent(
                event_id=f"gen_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                event_type="story_generation_complete",
                user_id=user_id,
                properties={
                    "prompt_length": len(prompt),
                    "response_time": response_time,
                    "success": success,
                },
                metrics={"response_time": response_time},
            )

            await self.ai_coordinator.ai_orchestrator.analytics_platform.track_event(
                analytics_event
            )


__all__ = ["ContentGenerationCoordinator"]
