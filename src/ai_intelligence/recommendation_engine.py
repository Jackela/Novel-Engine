#!/usr/bin/env python3
"""
Intelligent Recommendation and Adaptation Engine
================================================

Advanced recommendation system for Novel Engine that provides personalized
content recommendations, adaptive story generation, and intelligent user
preference learning.

Features:
- User preference learning and profiling
- Personalized content recommendation engine
- Adaptive story generation based on user feedback
- Intelligent character and genre suggestions
- Style and tone adaptation capabilities
- Collaborative filtering and content-based recommendations
- Real-time preference updates and learning
- Context-aware recommendations
"""

import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class RecommendationType(Enum):
    """Types of recommendations the engine can provide."""

    CHARACTER = "character"  # Character suggestions
    GENRE = "genre"  # Genre recommendations
    STORY_THEME = "story_theme"  # Theme and topic suggestions
    WRITING_STYLE = "writing_style"  # Style and tone recommendations
    PLOT_ELEMENT = "plot_element"  # Plot device suggestions
    SETTING = "setting"  # Setting and world recommendations
    COLLABORATION = "collaboration"  # Collaborative story suggestions
    IMPROVEMENT = "improvement"  # Story improvement suggestions


class PreferenceType(Enum):
    """Types of user preferences to track."""

    EXPLICIT = "explicit"  # Directly stated preferences
    IMPLICIT = "implicit"  # Inferred from behavior
    COLLABORATIVE = "collaborative"  # Based on similar users
    CONTEXTUAL = "contextual"  # Context-dependent preferences
    TEMPORAL = "temporal"  # Time-based preferences


class ConfidenceLevel(Enum):
    """Confidence levels for recommendations."""

    VERY_HIGH = "very_high"  # 90%+ confidence
    HIGH = "high"  # 75-89% confidence
    MEDIUM = "medium"  # 50-74% confidence
    LOW = "low"  # 25-49% confidence
    VERY_LOW = "very_low"  # Below 25% confidence


@dataclass
class UserPreference:
    """Individual user preference item."""

    preference_id: str
    user_id: str
    preference_type: PreferenceType
    category: str  # e.g., 'genre', 'character_type', 'writing_style'
    value: str  # The actual preference value
    weight: float = 1.0  # Preference strength (0.0 to 5.0)
    confidence: float = 0.5  # Confidence in this preference (0.0 to 1.0)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)
    evidence: List[str] = field(default_factory=list)
    decay_rate: float = 0.1  # Rate at which preference decays over time


@dataclass
class Recommendation:
    """Individual recommendation item."""

    recommendation_id: str
    user_id: str
    recommendation_type: RecommendationType
    title: str
    description: str
    target_value: str  # The recommended item/value
    confidence: ConfidenceLevel
    score: float  # Recommendation score (0.0 to 1.0)
    reasoning: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    applied: bool = False
    user_feedback: Optional[str] = None  # 'liked', 'disliked', 'neutral'


@dataclass
class UserProfile:
    """Comprehensive user preference profile."""

    user_id: str
    preferences: Dict[str, UserPreference] = field(default_factory=dict)
    preference_vectors: Dict[str, List[float]] = field(default_factory=dict)
    similarity_groups: List[str] = field(default_factory=list)
    behavioral_patterns: Dict[str, Any] = field(default_factory=dict)
    recommendation_history: List[str] = field(default_factory=list)
    feedback_history: Dict[str, str] = field(default_factory=dict)
    adaptation_settings: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)
    profile_completeness: float = 0.0


@dataclass
class RecommendationContext:
    """Context information for generating recommendations."""

    user_id: str
    current_story_context: Optional[Dict[str, Any]] = None
    session_context: Optional[Dict[str, Any]] = None
    temporal_context: Optional[Dict[str, Any]] = None
    collaborative_context: Optional[Dict[str, Any]] = None
    constraint_context: Optional[Dict[str, Any]] = None
    goal_context: Optional[Dict[str, Any]] = None


class RecommendationEngine:
    """
    Intelligent recommendation and adaptation engine that learns user preferences
    and provides personalized content recommendations for story generation.
    """

    def __init__(self, learning_rate: float = 0.1, decay_factor: float = 0.95):
        """
        Initialize the Recommendation Engine.

        Args:
            learning_rate: Rate at which to update preferences based on feedback
            decay_factor: Factor for temporal decay of preferences
        """
        self.learning_rate = learning_rate
        self.decay_factor = decay_factor

        # Core data structures
        self.user_profiles: Dict[str, UserProfile] = {}
        self.recommendations_cache: Dict[str, List[Recommendation]] = defaultdict(list)
        self.similarity_matrix: Dict[Tuple[str, str], float] = {}

        # Content knowledge base
        self.content_features: Dict[str, Dict[str, Any]] = {}
        self.genre_characteristics: Dict[str, Dict[str, Any]] = {}
        self.character_archetypes: Dict[str, Dict[str, Any]] = {}
        self.style_patterns: Dict[str, Dict[str, Any]] = {}

        # Learning and adaptation
        self.feedback_weights: Dict[str, float] = {
            "liked": 1.0,
            "loved": 1.5,
            "disliked": -1.0,
            "hated": -1.5,
            "neutral": 0.0,
        }
        self.collaborative_groups: Dict[str, List[str]] = defaultdict(list)
        self.trend_patterns: Dict[str, List[float]] = defaultdict(list)

        # Performance optimization
        self.recommendation_cache_ttl = 3600  # 1 hour cache TTL
        self.batch_update_queue: List[Tuple[str, str, Any]] = []

        # Initialize content knowledge
        self._initialize_content_knowledge()

        logger.info(
            "RecommendationEngine initialized with adaptive learning capabilities"
        )

    def _initialize_content_knowledge(self):
        """Initialize the content knowledge base with predefined patterns."""
        # Genre characteristics
        self.genre_characteristics = {
            "science_fiction": {
                "themes": ["technology", "future", "space", "artificial_intelligence"],
                "settings": [
                    "spaceship",
                    "alien_world",
                    "future_city",
                    "space_station",
                ],
                "character_types": ["scientist", "explorer", "robot", "alien"],
                "plot_elements": [
                    "discovery",
                    "technological_conflict",
                    "first_contact",
                ],
                "tone": ["analytical", "wonder", "philosophical"],
                "complexity": "high",
            },
            "fantasy": {
                "themes": ["magic", "quest", "good_vs_evil", "transformation"],
                "settings": [
                    "medieval_world",
                    "magical_forest",
                    "castle",
                    "mythical_realm",
                ],
                "character_types": ["wizard", "warrior", "elf", "dragon"],
                "plot_elements": ["hero_journey", "magical_conflict", "prophecy"],
                "tone": ["epic", "mystical", "adventurous"],
                "complexity": "medium",
            },
            "mystery": {
                "themes": ["investigation", "secrets", "justice", "deduction"],
                "settings": ["crime_scene", "city", "mansion", "small_town"],
                "character_types": ["detective", "suspect", "witness", "victim"],
                "plot_elements": ["clues", "red_herrings", "revelation", "twist"],
                "tone": ["suspenseful", "analytical", "dark"],
                "complexity": "high",
            },
            "romance": {
                "themes": ["love", "relationships", "passion", "commitment"],
                "settings": ["romantic_location", "everyday_setting", "exotic_place"],
                "character_types": ["lover", "romantic_interest", "friend", "rival"],
                "plot_elements": [
                    "meet_cute",
                    "conflict",
                    "resolution",
                    "happy_ending",
                ],
                "tone": ["emotional", "warm", "intimate"],
                "complexity": "medium",
            },
        }

        # Character archetypes
        self.character_archetypes = {
            "hero": {
                "traits": ["brave", "determined", "moral", "protective"],
                "motivations": ["save_others", "fight_evil", "achieve_justice"],
                "growth_arcs": ["reluctant_hero", "fallen_hero", "chosen_one"],
            },
            "mentor": {
                "traits": ["wise", "experienced", "guidance", "sacrifice"],
                "motivations": ["teach", "guide", "protect_knowledge"],
                "growth_arcs": ["passing_torch", "final_lesson", "redemption"],
            },
            "villain": {
                "traits": ["ambitious", "ruthless", "intelligent", "charismatic"],
                "motivations": ["power", "revenge", "ideology", "survival"],
                "growth_arcs": ["corruption", "downfall", "redemption"],
            },
            "companion": {
                "traits": ["loyal", "supportive", "complementary", "growth"],
                "motivations": ["friendship", "shared_goal", "personal_growth"],
                "growth_arcs": ["coming_of_age", "finding_purpose", "sacrifice"],
            },
        }

        # Writing style patterns
        self.style_patterns = {
            "descriptive": {
                "characteristics": [
                    "rich_imagery",
                    "sensory_details",
                    "world_building",
                ],
                "sentence_structure": "varied_complex",
                "vocabulary": "rich_varied",
                "pacing": "deliberate",
            },
            "action_packed": {
                "characteristics": ["fast_paced", "dynamic", "tension"],
                "sentence_structure": "short_punchy",
                "vocabulary": "active_verbs",
                "pacing": "rapid",
            },
            "dialogue_heavy": {
                "characteristics": ["character_interaction", "voice", "personality"],
                "sentence_structure": "conversational",
                "vocabulary": "character_specific",
                "pacing": "character_driven",
            },
            "introspective": {
                "characteristics": ["internal_thoughts", "psychological", "depth"],
                "sentence_structure": "flowing_reflective",
                "vocabulary": "emotional_nuanced",
                "pacing": "contemplative",
            },
        }

    async def learn_user_preferences(
        self, user_id: str, interaction_data: Dict[str, Any]
    ):
        """
        Learn and update user preferences based on interaction data.

        Args:
            user_id: User identifier
            interaction_data: Data about user interaction/feedback
        """
        try:
            if user_id not in self.user_profiles:
                self.user_profiles[user_id] = UserProfile(user_id=user_id)

            profile = self.user_profiles[user_id]

            # Extract preferences from interaction data
            extracted_preferences = await self._extract_preferences_from_interaction(
                interaction_data
            )

            # Update existing preferences or create new ones
            for pref_data in extracted_preferences:
                await self._update_or_create_preference(profile, pref_data)

            # Update behavioral patterns
            await self._update_behavioral_patterns(profile, interaction_data)

            # Recalculate preference vectors
            await self._update_preference_vectors(profile)

            # Update similarity groups
            await self._update_similarity_groups(user_id)

            # Update profile completeness
            profile.profile_completeness = self._calculate_profile_completeness(profile)
            profile.last_updated = datetime.now()

            logger.info(
                f"Updated user preferences for {user_id} (completeness: {profile.profile_completeness:.2f})"
            )

        except Exception as e:
            logger.error(f"Failed to learn user preferences for {user_id}: {e}")

    async def generate_recommendations(
        self,
        context: RecommendationContext,
        recommendation_types: Optional[List[RecommendationType]] = None,
        max_recommendations: int = 10,
    ) -> List[Recommendation]:
        """
        Generate personalized recommendations for a user.

        Args:
            context: Recommendation context
            recommendation_types: Types of recommendations to generate
            max_recommendations: Maximum number of recommendations

        Returns:
            List of personalized recommendations
        """
        try:
            user_id = context.user_id

            if user_id not in self.user_profiles:
                # Create basic profile for new user
                self.user_profiles[user_id] = UserProfile(user_id=user_id)
                # Generate basic recommendations for new users
                return await self._generate_new_user_recommendations(
                    context, max_recommendations
                )

            profile = self.user_profiles[user_id]

            # Check cache first
            cache_key = self._generate_cache_key(context, recommendation_types)
            if cache_key in self.recommendations_cache:
                cached_recommendations = self.recommendations_cache[cache_key]
                if self._is_cache_valid(cached_recommendations):
                    logger.info(f"Returning cached recommendations for {user_id}")
                    return cached_recommendations[:max_recommendations]

            # Generate fresh recommendations
            recommendations = []

            # Default to all types if none specified
            if recommendation_types is None:
                recommendation_types = list(RecommendationType)

            for rec_type in recommendation_types:
                type_recommendations = await self._generate_typed_recommendations(
                    profile, context, rec_type
                )
                recommendations.extend(type_recommendations)

            # Score and rank recommendations
            scored_recommendations = await self._score_recommendations(
                recommendations, profile, context
            )

            # Filter and limit results
            final_recommendations = self._filter_and_limit_recommendations(
                scored_recommendations, max_recommendations
            )

            # Cache results
            self.recommendations_cache[cache_key] = final_recommendations

            logger.info(
                f"Generated {len(final_recommendations)} recommendations for {user_id}"
            )
            return final_recommendations

        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            return []

    async def apply_recommendation_feedback(
        self,
        user_id: str,
        recommendation_id: str,
        feedback: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Apply user feedback to improve future recommendations.

        Args:
            user_id: User identifier
            recommendation_id: Recommendation identifier
            feedback: User feedback ('liked', 'disliked', 'neutral', etc.)
            context: Optional context about the feedback
        """
        try:
            if user_id not in self.user_profiles:
                logger.warning(f"No profile found for user {user_id}")
                return

            profile = self.user_profiles[user_id]

            # Find the recommendation
            recommendation = await self._find_recommendation(recommendation_id)
            if not recommendation:
                logger.warning(f"Recommendation {recommendation_id} not found")
                return

            # Update recommendation with feedback
            recommendation.user_feedback = feedback
            recommendation.applied = True

            # Store feedback in profile
            profile.feedback_history[recommendation_id] = feedback

            # Learn from feedback
            await self._learn_from_feedback(profile, recommendation, feedback, context)

            # Update preference weights based on feedback
            await self._update_preference_weights(profile, recommendation, feedback)

            # Update collaborative filtering data
            await self._update_collaborative_data(user_id, recommendation, feedback)

            logger.info(
                f"Applied feedback '{feedback}' for recommendation {recommendation_id}"
            )

        except Exception as e:
            logger.error(f"Failed to apply recommendation feedback: {e}")

    async def adapt_story_generation(
        self, user_id: str, story_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Adapt story generation parameters based on user preferences.

        Args:
            user_id: User identifier
            story_context: Current story generation context

        Returns:
            Adapted story generation parameters
        """
        try:
            if user_id not in self.user_profiles:
                return story_context  # Return unchanged for new users

            profile = self.user_profiles[user_id]
            adapted_context = story_context.copy()

            # Adapt genre preferences
            if "genre" not in adapted_context or adapted_context["genre"] is None:
                preferred_genre = await self._get_preferred_genre(profile)
                if preferred_genre:
                    adapted_context["genre"] = preferred_genre

            # Adapt character preferences
            adapted_context["character_suggestions"] = (
                await self._get_preferred_characters(profile)
            )

            # Adapt writing style
            preferred_style = await self._get_preferred_style(profile)
            if preferred_style:
                adapted_context["writing_style"] = preferred_style

            # Adapt complexity level
            preferred_complexity = await self._get_preferred_complexity(profile)
            if preferred_complexity:
                adapted_context["complexity"] = preferred_complexity

            # Adapt tone and mood
            preferred_tone = await self._get_preferred_tone(profile)
            if preferred_tone:
                adapted_context["tone"] = preferred_tone

            # Adapt length preferences
            preferred_length = await self._get_preferred_length(profile)
            if preferred_length:
                adapted_context["target_length"] = preferred_length

            # Add personalization metadata
            adapted_context["personalization"] = {
                "user_id": user_id,
                "profile_completeness": profile.profile_completeness,
                "adaptation_confidence": self._calculate_adaptation_confidence(profile),
                "applied_adaptations": list(adapted_context.keys()),
            }

            logger.info(f"Adapted story generation for {user_id}")
            return adapted_context

        except Exception as e:
            logger.error(f"Failed to adapt story generation: {e}")
            return story_context

    async def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """
        Get detailed insights about a user's preferences and patterns.

        Args:
            user_id: User identifier

        Returns:
            User insights and analytics
        """
        try:
            if user_id not in self.user_profiles:
                return {"error": "User profile not found"}

            profile = self.user_profiles[user_id]

            # Analyze preference patterns
            preference_analysis = await self._analyze_preference_patterns(profile)

            # Analyze behavioral patterns
            behavior_analysis = await self._analyze_behavioral_patterns(profile)

            # Calculate recommendation effectiveness
            rec_effectiveness = await self._calculate_recommendation_effectiveness(
                profile
            )

            # Generate improvement suggestions
            suggestions = await self._generate_profile_improvement_suggestions(profile)

            insights = {
                "user_id": user_id,
                "profile_summary": {
                    "completeness": profile.profile_completeness,
                    "preference_count": len(profile.preferences),
                    "last_updated": profile.last_updated,
                    "similarity_groups": len(profile.similarity_groups),
                },
                "preference_analysis": preference_analysis,
                "behavioral_patterns": behavior_analysis,
                "recommendation_effectiveness": rec_effectiveness,
                "top_preferences": self._get_top_preferences(profile),
                "preference_evolution": await self._analyze_preference_evolution(
                    profile
                ),
                "similarity_insights": await self._get_similarity_insights(user_id),
                "improvement_suggestions": suggestions,
            }

            return insights

        except Exception as e:
            logger.error(f"Failed to get user insights: {e}")
            return {"error": str(e)}

    async def update_preferences_batch(
        self, preference_updates: List[Tuple[str, str, Any]]
    ):
        """
        Update multiple user preferences in batch for performance.

        Args:
            preference_updates: List of (user_id, preference_type, data) tuples
        """
        try:
            for user_id, preference_type, data in preference_updates:
                if user_id not in self.user_profiles:
                    self.user_profiles[user_id] = UserProfile(user_id=user_id)

                await self._update_single_preference(user_id, preference_type, data)

            # Recalculate similarity matrix for affected users
            affected_users = list(set(user_id for user_id, _, _ in preference_updates))
            await self._batch_update_similarity_matrix(affected_users)

            logger.info(f"Batch updated preferences for {len(affected_users)} users")

        except Exception as e:
            logger.error(f"Failed to batch update preferences: {e}")

    # Private helper methods

    async def _extract_preferences_from_interaction(
        self, interaction_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract preference data from user interaction."""
        preferences = []

        # Extract explicit preferences
        if "explicit_preferences" in interaction_data:
            for category, value in interaction_data["explicit_preferences"].items():
                preferences.append(
                    {
                        "type": PreferenceType.EXPLICIT,
                        "category": category,
                        "value": value,
                        "weight": 2.0,  # Explicit preferences get higher weight
                        "confidence": 0.9,
                    }
                )

        # Extract implicit preferences from behavior
        if "story_data" in interaction_data:
            story_data = interaction_data["story_data"]

            # Genre preference
            if "genre" in story_data:
                preferences.append(
                    {
                        "type": PreferenceType.IMPLICIT,
                        "category": "genre",
                        "value": story_data["genre"],
                        "weight": 1.0,
                        "confidence": 0.6,
                    }
                )

            # Character type preferences
            if "characters_used" in story_data:
                for character in story_data["characters_used"]:
                    preferences.append(
                        {
                            "type": PreferenceType.IMPLICIT,
                            "category": "character_type",
                            "value": character,
                            "weight": 0.8,
                            "confidence": 0.5,
                        }
                    )

            # Style preferences from quality feedback
            if (
                "quality_feedback" in story_data
                and story_data["quality_feedback"] > 0.7
            ):
                if "writing_style" in story_data:
                    preferences.append(
                        {
                            "type": PreferenceType.IMPLICIT,
                            "category": "writing_style",
                            "value": story_data["writing_style"],
                            "weight": 1.2,
                            "confidence": 0.7,
                        }
                    )

        return preferences

    async def _update_or_create_preference(
        self, profile: UserProfile, pref_data: Dict[str, Any]
    ):
        """Update existing preference or create new one."""
        category = pref_data["category"]
        value = pref_data["value"]
        pref_key = f"{category}:{value}"

        if pref_key in profile.preferences:
            # Update existing preference
            existing_pref = profile.preferences[pref_key]

            # Update weight using learning rate
            new_weight = existing_pref.weight + (
                self.learning_rate * pref_data["weight"]
            )
            existing_pref.weight = max(
                0.0, min(5.0, new_weight)
            )  # Clamp to valid range

            # Update confidence
            existing_pref.confidence = min(1.0, existing_pref.confidence + 0.1)
            existing_pref.last_updated = datetime.now()

        else:
            # Create new preference
            preference = UserPreference(
                preference_id=f"{profile.user_id}_{pref_key}_{datetime.now().strftime('%H%M%S')}",
                user_id=profile.user_id,
                preference_type=pref_data["type"],
                category=category,
                value=value,
                weight=pref_data["weight"],
                confidence=pref_data["confidence"],
            )
            profile.preferences[pref_key] = preference

    async def _update_behavioral_patterns(
        self, profile: UserProfile, interaction_data: Dict[str, Any]
    ):
        """Update user behavioral patterns."""
        if "session_data" in interaction_data:
            session_data = interaction_data["session_data"]

            # Update usage patterns
            if "usage_patterns" not in profile.behavioral_patterns:
                profile.behavioral_patterns["usage_patterns"] = {}

            patterns = profile.behavioral_patterns["usage_patterns"]

            # Time of day preferences
            current_hour = datetime.now().hour
            if "preferred_hours" not in patterns:
                patterns["preferred_hours"] = {}
            if str(current_hour) not in patterns["preferred_hours"]:
                patterns["preferred_hours"][str(current_hour)] = 0
            patterns["preferred_hours"][str(current_hour)] += 1

            # Session length preferences
            if "session_duration" in session_data:
                if "session_durations" not in patterns:
                    patterns["session_durations"] = []
                patterns["session_durations"].append(session_data["session_duration"])
                # Keep only last 20 sessions
                patterns["session_durations"] = patterns["session_durations"][-20:]

    async def _update_preference_vectors(self, profile: UserProfile):
        """Update user preference vectors for similarity calculation."""
        vectors = {}

        # Create vectors for different categories
        categories = set(pref.category for pref in profile.preferences.values())

        for category in categories:
            category_prefs = [
                pref
                for pref in profile.preferences.values()
                if pref.category == category
            ]

            # Create a vector representation
            vector = {}
            for pref in category_prefs:
                vector[pref.value] = pref.weight * pref.confidence

            vectors[category] = vector

        profile.preference_vectors = vectors

    async def _update_similarity_groups(self, user_id: str):
        """Update user similarity groups based on preferences."""
        if user_id not in self.user_profiles:
            return

        current_profile = self.user_profiles[user_id]
        similarities = []

        # Calculate similarity with other users
        for other_user_id, other_profile in self.user_profiles.items():
            if other_user_id == user_id:
                continue

            similarity = await self._calculate_user_similarity(
                current_profile, other_profile
            )
            if similarity > 0.3:  # Threshold for similarity
                similarities.append((other_user_id, similarity))

        # Sort by similarity and keep top matches
        similarities.sort(key=lambda x: x[1], reverse=True)
        current_profile.similarity_groups = [
            user_id for user_id, _ in similarities[:10]
        ]

    async def _generate_new_user_recommendations(
        self, context: RecommendationContext, max_recommendations: int
    ) -> List[Recommendation]:
        """Generate recommendations for new users based on popular trends."""
        recommendations = []

        # Popular genre recommendations
        popular_genres = ["fantasy", "science_fiction", "mystery", "romance"]
        for i, genre in enumerate(popular_genres[:3]):
            rec = Recommendation(
                recommendation_id=f"new_user_genre_{i}_{datetime.now().strftime('%H%M%S')}",
                user_id=context.user_id,
                recommendation_type=RecommendationType.GENRE,
                title=f"Try {genre.replace('_', ' ').title()}",
                description=f"Popular {genre.replace('_', ' ')} stories are trending",
                target_value=genre,
                confidence=ConfidenceLevel.MEDIUM,
                score=0.7 - (i * 0.1),
                reasoning=["Popular genre for new users", "High engagement rates"],
                metadata={"is_trending": True, "new_user_rec": True},
            )
            recommendations.append(rec)

        # Popular character archetypes
        popular_archetypes = ["hero", "mentor", "companion"]
        for i, archetype in enumerate(popular_archetypes[:2]):
            rec = Recommendation(
                recommendation_id=f"new_user_char_{i}_{datetime.now().strftime('%H%M%S')}",
                user_id=context.user_id,
                recommendation_type=RecommendationType.CHARACTER,
                title=f"Start with a {archetype.title()}",
                description=f"{archetype.title()} characters are easy to develop",
                target_value=archetype,
                confidence=ConfidenceLevel.MEDIUM,
                score=0.6 - (i * 0.1),
                reasoning=["Beginner-friendly archetype", "High success rate"],
                metadata={"beginner_friendly": True, "new_user_rec": True},
            )
            recommendations.append(rec)

        return recommendations[:max_recommendations]

    async def _generate_typed_recommendations(
        self,
        profile: UserProfile,
        context: RecommendationContext,
        rec_type: RecommendationType,
    ) -> List[Recommendation]:
        """Generate recommendations of a specific type."""
        recommendations = []

        if rec_type == RecommendationType.GENRE:
            recommendations = await self._generate_genre_recommendations(
                profile, context
            )
        elif rec_type == RecommendationType.CHARACTER:
            recommendations = await self._generate_character_recommendations(
                profile, context
            )
        elif rec_type == RecommendationType.WRITING_STYLE:
            recommendations = await self._generate_style_recommendations(
                profile, context
            )
        elif rec_type == RecommendationType.STORY_THEME:
            recommendations = await self._generate_theme_recommendations(
                profile, context
            )
        elif rec_type == RecommendationType.IMPROVEMENT:
            recommendations = await self._generate_improvement_recommendations(
                profile, context
            )

        return recommendations

    async def _generate_genre_recommendations(
        self, profile: UserProfile, context: RecommendationContext
    ) -> List[Recommendation]:
        """Generate genre recommendations."""
        recommendations = []

        # Get current genre preferences
        genre_preferences = {
            pref.value: pref.weight * pref.confidence
            for pref in profile.preferences.values()
            if pref.category == "genre"
        }

        # Get similar users' preferences
        similar_genres = await self._get_collaborative_genre_preferences(profile)

        # Combine content-based and collaborative filtering
        all_genres = set(self.genre_characteristics.keys())

        for genre in all_genres:
            if genre in genre_preferences:
                continue  # Skip already preferred genres

            # Calculate recommendation score
            content_score = await self._calculate_genre_content_score(profile, genre)
            collaborative_score = similar_genres.get(genre, 0.0)

            final_score = content_score * 0.6 + collaborative_score * 0.4

            if final_score > 0.4:  # Threshold for recommendation
                rec = Recommendation(
                    recommendation_id=f"genre_{genre}_{datetime.now().strftime('%H%M%S')}",
                    user_id=profile.user_id,
                    recommendation_type=RecommendationType.GENRE,
                    title=f"Try {genre.replace('_', ' ').title()}",
                    description=f"Based on your interests, you might enjoy {genre.replace('_', ' ')} stories",
                    target_value=genre,
                    confidence=self._score_to_confidence(final_score),
                    score=final_score,
                    reasoning=self._generate_genre_reasoning(
                        profile, genre, content_score, collaborative_score
                    ),
                    metadata={
                        "content_score": content_score,
                        "collaborative_score": collaborative_score,
                    },
                )
                recommendations.append(rec)

        return sorted(recommendations, key=lambda x: x.score, reverse=True)[:5]

    async def _generate_character_recommendations(
        self, profile: UserProfile, context: RecommendationContext
    ) -> List[Recommendation]:
        """Generate character recommendations."""
        recommendations = []

        # Analyze preferred character types
        character_preferences = {
            pref.value: pref.weight * pref.confidence
            for pref in profile.preferences.values()
            if pref.category == "character_type"
        }

        # Recommend complementary character types
        for archetype, characteristics in self.character_archetypes.items():
            if archetype in character_preferences:
                continue

            # Calculate compatibility with user preferences
            compatibility_score = await self._calculate_character_compatibility(
                profile, archetype
            )

            if compatibility_score > 0.5:
                rec = Recommendation(
                    recommendation_id=f"char_{archetype}_{datetime.now().strftime('%H%M%S')}",
                    user_id=profile.user_id,
                    recommendation_type=RecommendationType.CHARACTER,
                    title=f"Add a {archetype.title()} Character",
                    description=f"A {archetype} could add depth to your stories",
                    target_value=archetype,
                    confidence=self._score_to_confidence(compatibility_score),
                    score=compatibility_score,
                    reasoning=[
                        "Complements your existing preferences",
                        "Popular in similar stories",
                    ],
                    metadata={"archetype_traits": characteristics.get("traits", [])},
                )
                recommendations.append(rec)

        return sorted(recommendations, key=lambda x: x.score, reverse=True)[:3]

    async def _generate_style_recommendations(
        self, profile: UserProfile, context: RecommendationContext
    ) -> List[Recommendation]:
        """Generate writing style recommendations."""
        recommendations = []

        # Analyze current style preferences
        style_preferences = {
            pref.value: pref.weight * pref.confidence
            for pref in profile.preferences.values()
            if pref.category == "writing_style"
        }

        # Recommend new styles based on genre preferences
        genre_preferences = {
            pref.value: pref.weight
            for pref in profile.preferences.values()
            if pref.category == "genre"
        }

        for style, characteristics in self.style_patterns.items():
            if style in style_preferences:
                continue

            # Calculate style recommendation score
            style_score = await self._calculate_style_compatibility(
                profile, style, genre_preferences
            )

            if style_score > 0.4:
                rec = Recommendation(
                    recommendation_id=f"style_{style}_{datetime.now().strftime('%H%M%S')}",
                    user_id=profile.user_id,
                    recommendation_type=RecommendationType.WRITING_STYLE,
                    title=f"Try {style.replace('_', ' ').title()} Style",
                    description=f"Experiment with {style.replace('_', ' ')} writing",
                    target_value=style,
                    confidence=self._score_to_confidence(style_score),
                    score=style_score,
                    reasoning=[
                        "Matches your genre preferences",
                        "Could enhance your storytelling",
                    ],
                    metadata={"style_characteristics": characteristics},
                )
                recommendations.append(rec)

        return sorted(recommendations, key=lambda x: x.score, reverse=True)[:3]

    async def _generate_theme_recommendations(
        self, profile: UserProfile, context: RecommendationContext
    ) -> List[Recommendation]:
        """Generate story theme recommendations."""
        # This would implement theme recommendation logic
        return []

    async def _generate_improvement_recommendations(
        self, profile: UserProfile, context: RecommendationContext
    ) -> List[Recommendation]:
        """Generate story improvement recommendations."""
        # This would implement improvement recommendation logic
        return []

    async def _score_recommendations(
        self,
        recommendations: List[Recommendation],
        profile: UserProfile,
        context: RecommendationContext,
    ) -> List[Recommendation]:
        """Score and rank recommendations."""
        for rec in recommendations:
            # Adjust score based on user feedback history
            feedback_adjustment = await self._calculate_feedback_adjustment(
                profile, rec
            )

            # Adjust score based on context
            context_adjustment = await self._calculate_context_adjustment(context, rec)

            # Apply adjustments
            rec.score = max(
                0.0, min(1.0, rec.score + feedback_adjustment + context_adjustment)
            )

            # Update confidence based on final score
            rec.confidence = self._score_to_confidence(rec.score)

        return sorted(recommendations, key=lambda x: x.score, reverse=True)

    def _filter_and_limit_recommendations(
        self, recommendations: List[Recommendation], max_recommendations: int
    ) -> List[Recommendation]:
        """Filter and limit recommendations."""
        # Remove duplicates
        seen_targets = set()
        filtered_recs = []

        for rec in recommendations:
            target_key = f"{rec.recommendation_type.value}:{rec.target_value}"
            if target_key not in seen_targets:
                seen_targets.add(target_key)
                filtered_recs.append(rec)

        # Limit to max count
        return filtered_recs[:max_recommendations]

    # Utility methods

    def _generate_cache_key(
        self,
        context: RecommendationContext,
        recommendation_types: Optional[List[RecommendationType]],
    ) -> str:
        """Generate cache key for recommendations."""
        types_str = (
            "_".join(rt.value for rt in recommendation_types)
            if recommendation_types
            else "all"
        )
        context_hash = hash(str(context.current_story_context))
        return f"{context.user_id}_{types_str}_{context_hash}"

    def _is_cache_valid(self, recommendations: List[Recommendation]) -> bool:
        """Check if cached recommendations are still valid."""
        if not recommendations:
            return False

        oldest_rec = min(recommendations, key=lambda x: x.created_at)
        age_seconds = (datetime.now() - oldest_rec.created_at).total_seconds()
        return age_seconds < self.recommendation_cache_ttl

    def _score_to_confidence(self, score: float) -> ConfidenceLevel:
        """Convert numeric score to confidence level."""
        if score >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif score >= 0.75:
            return ConfidenceLevel.HIGH
        elif score >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif score >= 0.25:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

    def _calculate_profile_completeness(self, profile: UserProfile) -> float:
        """Calculate profile completeness score."""
        total_categories = 10  # Expected number of preference categories
        categories_with_prefs = len(
            set(pref.category for pref in profile.preferences.values())
        )

        completeness = categories_with_prefs / total_categories

        # Bonus for behavioral patterns
        if profile.behavioral_patterns:
            completeness += 0.1

        # Bonus for feedback history
        if len(profile.feedback_history) > 5:
            completeness += 0.1

        return min(1.0, completeness)

    # Additional helper methods would be implemented here...

    async def _calculate_user_similarity(
        self, profile1: UserProfile, profile2: UserProfile
    ) -> float:
        """Calculate similarity between two user profiles."""
        if not profile1.preference_vectors or not profile2.preference_vectors:
            return 0.0

        common_categories = set(profile1.preference_vectors.keys()) & set(
            profile2.preference_vectors.keys()
        )
        if not common_categories:
            return 0.0

        similarities = []
        for category in common_categories:
            vec1 = profile1.preference_vectors[category]
            vec2 = profile2.preference_vectors[category]

            # Calculate cosine similarity
            similarity = self._cosine_similarity(vec1, vec2)
            similarities.append(similarity)

        return sum(similarities) / len(similarities) if similarities else 0.0

    def _cosine_similarity(
        self, vec1: Dict[str, float], vec2: Dict[str, float]
    ) -> float:
        """Calculate cosine similarity between two vectors."""
        common_keys = set(vec1.keys()) & set(vec2.keys())
        if not common_keys:
            return 0.0

        dot_product = sum(vec1[key] * vec2[key] for key in common_keys)
        norm1 = math.sqrt(sum(vec1[key] ** 2 for key in vec1))
        norm2 = math.sqrt(sum(vec2[key] ** 2 for key in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    # Additional methods for specific recommendation types...

    async def _get_preferred_genre(self, profile: UserProfile) -> Optional[str]:
        """Get user's most preferred genre."""
        genre_prefs = [
            (pref.value, pref.weight * pref.confidence)
            for pref in profile.preferences.values()
            if pref.category == "genre"
        ]

        if not genre_prefs:
            return None

        return max(genre_prefs, key=lambda x: x[1])[0]

    async def _get_preferred_characters(self, profile: UserProfile) -> List[str]:
        """Get user's preferred character types."""
        char_prefs = [
            (pref.value, pref.weight * pref.confidence)
            for pref in profile.preferences.values()
            if pref.category == "character_type"
        ]

        # Sort by preference strength and return top characters
        char_prefs.sort(key=lambda x: x[1], reverse=True)
        return [char for char, _ in char_prefs[:5]]

    async def _get_preferred_style(self, profile: UserProfile) -> Optional[str]:
        """Get user's preferred writing style."""
        style_prefs = [
            (pref.value, pref.weight * pref.confidence)
            for pref in profile.preferences.values()
            if pref.category == "writing_style"
        ]

        if not style_prefs:
            return None

        return max(style_prefs, key=lambda x: x[1])[0]

    async def _get_preferred_complexity(self, profile: UserProfile) -> Optional[str]:
        """Get user's preferred complexity level."""
        complexity_prefs = [
            (pref.value, pref.weight * pref.confidence)
            for pref in profile.preferences.values()
            if pref.category == "complexity"
        ]

        if not complexity_prefs:
            return "medium"  # Default complexity

        return max(complexity_prefs, key=lambda x: x[1])[0]

    async def _get_preferred_tone(self, profile: UserProfile) -> Optional[str]:
        """Get user's preferred tone."""
        tone_prefs = [
            (pref.value, pref.weight * pref.confidence)
            for pref in profile.preferences.values()
            if pref.category == "tone"
        ]

        if not tone_prefs:
            return None

        return max(tone_prefs, key=lambda x: x[1])[0]

    async def _get_preferred_length(self, profile: UserProfile) -> Optional[int]:
        """Get user's preferred story length."""
        if "usage_patterns" not in profile.behavioral_patterns:
            return None

        patterns = profile.behavioral_patterns["usage_patterns"]
        if "preferred_lengths" not in patterns:
            return None

        lengths = patterns["preferred_lengths"]
        if not lengths:
            return None

        # Return average preferred length
        return int(sum(lengths) / len(lengths))

    def _calculate_adaptation_confidence(self, profile: UserProfile) -> float:
        """Calculate confidence in adaptations made."""
        base_confidence = profile.profile_completeness

        # Increase confidence with more feedback history
        feedback_bonus = min(0.2, len(profile.feedback_history) * 0.02)

        # Increase confidence with more behavioral data
        pattern_bonus = 0.1 if profile.behavioral_patterns else 0.0

        return min(1.0, base_confidence + feedback_bonus + pattern_bonus)

    # Placeholder methods that would be fully implemented

    async def _find_recommendation(
        self, recommendation_id: str
    ) -> Optional[Recommendation]:
        """Find a recommendation by ID."""
        for recommendations in self.recommendations_cache.values():
            for rec in recommendations:
                if rec.recommendation_id == recommendation_id:
                    return rec
        return None

    async def _learn_from_feedback(
        self,
        profile: UserProfile,
        recommendation: Recommendation,
        feedback: str,
        context: Optional[Dict[str, Any]],
    ):
        """Learn from user feedback."""
        recommendation.user_feedback = feedback
        profile.feedback_history[recommendation.recommendation_id] = feedback

        await self._update_preference_weights(profile, recommendation, feedback)
        await self._update_collaborative_data(profile.user_id, recommendation, feedback)

    async def _update_preference_weights(
        self, profile: UserProfile, recommendation: Recommendation, feedback: str
    ):
        """Update preference weights based on feedback."""
        delta = self.learning_rate
        if feedback.lower() in {"liked", "positive", "thumbs_up"}:
            delta *= 1.0
        elif feedback.lower() in {"disliked", "negative", "thumbs_down"}:
            delta *= -1.0
        else:
            delta = 0.0

        if delta == 0.0:
            return

        key = (
            f"{recommendation.recommendation_type.value}:{recommendation.target_value}"
        )
        pref = profile.preferences.get(
            key,
            UserPreference(
                preference_id=key,
                user_id=profile.user_id,
                preference_type=PreferenceType.EXPLICIT,
                category=recommendation.recommendation_type.value,
                value=recommendation.target_value,
                weight=1.0,
                confidence=0.5,
            ),
        )

        pref.weight = max(0.0, min(5.0, pref.weight + delta))
        pref.confidence = max(0.0, min(1.0, pref.confidence + abs(delta) / 5))
        pref.last_updated = datetime.now()
        profile.preferences[key] = pref

    async def _update_collaborative_data(
        self, user_id: str, recommendation: Recommendation, feedback: str
    ):
        """Update collaborative filtering data."""
        # Basic implicit collaborative scoring: store similarity seed per target
        key = (user_id, recommendation.target_value)
        current = self.similarity_matrix.get(key, 0.0)
        adjustment = 0.05 if feedback.lower() in {"liked", "positive"} else -0.05
        self.similarity_matrix[key] = max(0.0, min(1.0, current + adjustment))

    # Additional analysis methods...

    async def _analyze_preference_patterns(
        self, profile: UserProfile
    ) -> Dict[str, Any]:
        """Analyze user preference patterns."""
        by_category: Dict[str, List[float]] = defaultdict(list)
        for pref in profile.preferences.values():
            by_category[pref.category].append(pref.weight * pref.confidence)

        category_scores = {
            cat: sum(scores) / len(scores) if scores else 0.0
            for cat, scores in by_category.items()
        }
        top_category = (
            max(category_scores.items(), key=lambda x: x[1])[0]
            if category_scores
            else None
        )
        return {"category_scores": category_scores, "top_category": top_category}

    async def _analyze_behavioral_patterns(
        self, profile: UserProfile
    ) -> Dict[str, Any]:
        """Analyze user behavioral patterns."""
        patterns = profile.behavioral_patterns or {}
        session_lengths = patterns.get("session_lengths", [])
        avg_session = (
            sum(session_lengths) / len(session_lengths) if session_lengths else 0.0
        )
        return {
            "avg_session_length": avg_session,
            "preferred_hours": patterns.get("preferred_hours", []),
        }

    async def _calculate_recommendation_effectiveness(
        self, profile: UserProfile
    ) -> Dict[str, Any]:
        """Calculate recommendation effectiveness metrics."""
        total = len(profile.feedback_history)
        positive = len(
            [fb for fb in profile.feedback_history.values() if fb == "liked"]
        )
        effectiveness = (positive / total) if total else 0.0
        return {"effectiveness": effectiveness, "total_feedback": total}

    async def _generate_profile_improvement_suggestions(
        self, profile: UserProfile
    ) -> List[str]:
        """Generate suggestions for improving user profile."""
        suggestions = []
        if profile.profile_completeness < 0.6:
            suggestions.append("Provide more explicit genre and tone preferences.")
        if not profile.behavioral_patterns.get("usage_patterns"):
            suggestions.append("Record a few sessions to refine behavioral patterns.")
        if not profile.similarity_groups:
            suggestions.append(
                "Engage with community content to build similarity data."
            )
        return suggestions or ["Profile is sufficiently populated."]

    def _get_top_preferences(self, profile: UserProfile) -> List[Dict[str, Any]]:
        """Get top user preferences."""
        top_prefs = sorted(
            profile.preferences.values(),
            key=lambda p: p.weight * p.confidence,
            reverse=True,
        )[:10]

        return [
            {
                "category": pref.category,
                "value": pref.value,
                "weight": pref.weight,
                "confidence": pref.confidence,
            }
            for pref in top_prefs
        ]

    async def _analyze_preference_evolution(
        self, profile: UserProfile
    ) -> Dict[str, Any]:
        """Analyze how user preferences have evolved."""
        history = profile.feedback_history
        return {
            "total_feedback": len(history),
            "recent_feedback": list(history.items())[-5:],
        }

    async def _get_similarity_insights(self, user_id: str) -> Dict[str, Any]:
        """Get insights about user similarity to others."""
        related = {
            other: score
            for (uid, other), score in self.similarity_matrix.items()
            if uid == user_id
        }
        top = sorted(related.items(), key=lambda x: x[1], reverse=True)[:5]
        return {"similar_users": top}

    async def _update_single_preference(
        self, user_id: str, preference_type: str, data: Any
    ):
        """Update a single preference."""
        # Implementation would update individual preference

    async def _batch_update_similarity_matrix(self, user_ids: List[str]):
        """Update similarity matrix for multiple users."""
        # Implementation would update similarity calculations

    # Additional placeholder methods for completeness...

    async def _get_collaborative_genre_preferences(
        self, profile: UserProfile
    ) -> Dict[str, float]:
        """Get genre preferences from similar users."""
        preferences: Dict[str, float] = defaultdict(float)
        for (uid, target), score in self.similarity_matrix.items():
            if uid == profile.user_id and "genre:" in target:
                _, genre = target.split(":", 1)
                preferences[genre] += score
        return dict(preferences)

    async def _calculate_genre_content_score(
        self, profile: UserProfile, genre: str
    ) -> float:
        """Calculate content-based score for a genre."""
        base = profile.preference_vectors.get(genre, [])
        return float(sum(base) / len(base)) if base else 0.0

    def _generate_genre_reasoning(
        self,
        profile: UserProfile,
        genre: str,
        content_score: float,
        collaborative_score: float,
    ) -> List[str]:
        """Generate reasoning for genre recommendation."""
        return [
            f"Content match: {content_score:.2f}",
            f"Similar users like this: {collaborative_score:.2f}",
        ]

    async def _calculate_character_compatibility(
        self, profile: UserProfile, archetype: str
    ) -> float:
        """Calculate character compatibility score."""
        key = f"character:{archetype}"
        base = profile.preference_vectors.get(key, [])
        return float(sum(base) / len(base)) if base else 0.0

    async def _calculate_style_compatibility(
        self, profile: UserProfile, style: str, genre_preferences: Dict[str, float]
    ) -> float:
        """Calculate writing style compatibility."""
        style_pref = next(
            (
                p
                for p in profile.preferences.values()
                if p.category == "writing_style" and p.value == style
            ),
            None,
        )
        base_score = style_pref.weight * style_pref.confidence if style_pref else 0.0
        genre_boost = max(genre_preferences.values()) if genre_preferences else 0.0
        return min(1.0, base_score + genre_boost / 10)

    async def _calculate_feedback_adjustment(
        self, profile: UserProfile, recommendation: Recommendation
    ) -> float:
        """Calculate score adjustment based on feedback history."""
        feedback = profile.feedback_history.get(recommendation.recommendation_id)
        if feedback == "liked":
            return 0.1
        if feedback == "disliked":
            return -0.1
        return 0.0

    async def _calculate_context_adjustment(
        self, context: RecommendationContext, recommendation: Recommendation
    ) -> float:
        """Calculate score adjustment based on context."""
        adjustment = 0.0
        if context.current_story_context:
            tags = context.current_story_context.get("tags", [])
            if recommendation.target_value in tags:
                adjustment += 0.1
        if context.temporal_context and context.temporal_context.get("mood") == "low":
            adjustment -= 0.05
        return adjustment


def create_recommendation_engine(
    learning_rate: float = 0.1, decay_factor: float = 0.95
) -> RecommendationEngine:
    """
    Factory function to create and configure a Recommendation Engine.

    Args:
        learning_rate: Rate at which to update preferences
        decay_factor: Factor for temporal decay of preferences

    Returns:
        Configured RecommendationEngine instance
    """
    engine = RecommendationEngine(learning_rate, decay_factor)
    logger.info("Recommendation Engine created and configured")
    return engine
