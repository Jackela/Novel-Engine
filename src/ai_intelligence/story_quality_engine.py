#!/usr/bin/env python3
"""
Story Quality Analysis Engine
=============================

Advanced story generation intelligence with quality scoring, validation,
and improvement recommendations for the Novel Engine.

Features:
- Multi-dimensional story quality scoring
- Genre-specific quality templates and validation
- Character development analysis
- Plot coherence and pacing analysis
- Dialogue quality assessment
- Real-time story improvement suggestions
- Quality trend analysis and optimization
"""

import json
import logging
import re
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, Counter
import math

logger = logging.getLogger(__name__)


class QualityDimension(Enum):
    """Dimensions for story quality analysis."""
    PLOT_COHERENCE = "plot_coherence"
    CHARACTER_DEVELOPMENT = "character_development"
    DIALOGUE_QUALITY = "dialogue_quality"
    PACING = "pacing"
    WORLD_BUILDING = "world_building"
    EMOTIONAL_IMPACT = "emotional_impact"
    ORIGINALITY = "originality"
    GENRE_CONSISTENCY = "genre_consistency"
    NARRATIVE_VOICE = "narrative_voice"
    CONFLICT_RESOLUTION = "conflict_resolution"


class StoryGenre(Enum):
    """Supported story genres for quality analysis."""
    SCIENCE_FICTION = "science_fiction"
    FANTASY = "fantasy"
    HORROR = "horror"
    MYSTERY = "mystery"
    ROMANCE = "romance"
    THRILLER = "thriller"
    ADVENTURE = "adventure"
    DRAMA = "drama"
    COMEDY = "comedy"
    HISTORICAL = "historical"
    CYBERPUNK = "cyberpunk"
    STEAMPUNK = "steampunk"


class QualityLevel(Enum):
    """Quality level classifications."""
    EXCEPTIONAL = "exceptional"  # 90-100%
    EXCELLENT = "excellent"      # 80-89%
    GOOD = "good"               # 70-79%
    ACCEPTABLE = "acceptable"    # 60-69%
    POOR = "poor"               # 40-59%
    VERY_POOR = "very_poor"     # Below 40%


@dataclass
class QualityScore:
    """Individual quality score for a specific dimension."""
    dimension: QualityDimension
    score: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    evidence: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    analysis_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StoryQualityReport:
    """Comprehensive story quality analysis report."""
    story_id: str
    overall_score: float
    quality_level: QualityLevel
    dimension_scores: Dict[QualityDimension, QualityScore] = field(default_factory=dict)
    genre: Optional[StoryGenre] = None
    genre_compliance: float = 0.0
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    improvement_recommendations: List[str] = field(default_factory=list)
    word_count: int = 0
    reading_level: str = "unknown"
    sentiment_analysis: Dict[str, float] = field(default_factory=dict)
    character_analysis: Dict[str, Any] = field(default_factory=dict)
    plot_analysis: Dict[str, Any] = field(default_factory=dict)
    analysis_timestamp: datetime = field(default_factory=datetime.now)
    processing_time: float = 0.0


@dataclass
class GenreTemplate:
    """Template defining quality criteria for specific genres."""
    genre: StoryGenre
    required_elements: List[str]
    dimension_weights: Dict[QualityDimension, float]
    quality_thresholds: Dict[str, float]
    style_guidelines: Dict[str, Any]
    common_patterns: List[str]
    genre_specific_metrics: Dict[str, Any]


class StoryQualityEngine:
    """
    Advanced story quality analysis engine that provides comprehensive
    quality scoring, validation, and improvement recommendations.
    """
    
    def __init__(self):
        """Initialize the Story Quality Engine."""
        # Quality analysis components
        self.genre_templates: Dict[StoryGenre, GenreTemplate] = {}
        self.quality_history: Dict[str, List[StoryQualityReport]] = defaultdict(list)
        self.improvement_patterns: Dict[str, List[str]] = defaultdict(list)
        
        # Analysis caches for performance
        self.analysis_cache: Dict[str, Any] = {}
        self.pattern_cache: Dict[str, Any] = {}
        
        # Quality benchmarks and standards
        self.quality_benchmarks: Dict[QualityDimension, Dict[str, float]] = {}
        self.genre_standards: Dict[StoryGenre, Dict[str, Any]] = {}
        
        # Initialize genre templates and quality standards
        self._initialize_genre_templates()
        self._initialize_quality_benchmarks()
        
        logger.info("StoryQualityEngine initialized with comprehensive analysis capabilities")
    
    def _initialize_genre_templates(self):
        """Initialize genre-specific quality templates."""
        # Science Fiction template
        self.genre_templates[StoryGenre.SCIENCE_FICTION] = GenreTemplate(
            genre=StoryGenre.SCIENCE_FICTION,
            required_elements=["scientific_concepts", "futuristic_setting", "technology_integration"],
            dimension_weights={
                QualityDimension.WORLD_BUILDING: 1.2,
                QualityDimension.ORIGINALITY: 1.1,
                QualityDimension.PLOT_COHERENCE: 1.0,
                QualityDimension.CHARACTER_DEVELOPMENT: 0.9,
                QualityDimension.DIALOGUE_QUALITY: 0.8
            },
            quality_thresholds={"world_consistency": 0.8, "scientific_plausibility": 0.7},
            style_guidelines={"pacing": "moderate", "complexity": "high"},
            common_patterns=["exploration", "discovery", "technological_conflict"],
            genre_specific_metrics={"tech_density": 0.3, "future_elements": 0.6}
        )
        
        # Fantasy template
        self.genre_templates[StoryGenre.FANTASY] = GenreTemplate(
            genre=StoryGenre.FANTASY,
            required_elements=["magical_system", "world_building", "hero_journey"],
            dimension_weights={
                QualityDimension.WORLD_BUILDING: 1.3,
                QualityDimension.CHARACTER_DEVELOPMENT: 1.1,
                QualityDimension.PLOT_COHERENCE: 1.0,
                QualityDimension.EMOTIONAL_IMPACT: 1.0,
                QualityDimension.ORIGINALITY: 0.9
            },
            quality_thresholds={"magic_consistency": 0.8, "world_depth": 0.7},
            style_guidelines={"pacing": "epic", "complexity": "moderate"},
            common_patterns=["quest", "transformation", "good_vs_evil"],
            genre_specific_metrics={"magic_density": 0.4, "mythic_elements": 0.5}
        )
        
        # Horror template
        self.genre_templates[StoryGenre.HORROR] = GenreTemplate(
            genre=StoryGenre.HORROR,
            required_elements=["suspense_building", "fear_elements", "atmosphere"],
            dimension_weights={
                QualityDimension.EMOTIONAL_IMPACT: 1.3,
                QualityDimension.PACING: 1.2,
                QualityDimension.NARRATIVE_VOICE: 1.1,
                QualityDimension.CHARACTER_DEVELOPMENT: 0.9,
                QualityDimension.DIALOGUE_QUALITY: 0.8
            },
            quality_thresholds={"tension_buildup": 0.8, "fear_effectiveness": 0.7},
            style_guidelines={"pacing": "variable", "complexity": "psychological"},
            common_patterns=["escalating_threat", "isolation", "revelation"],
            genre_specific_metrics={"fear_density": 0.5, "suspense_curve": 0.7}
        )
        
        # Add more genres as needed
        logger.info(f"Initialized {len(self.genre_templates)} genre templates")
    
    def _initialize_quality_benchmarks(self):
        """Initialize quality benchmarks for different dimensions."""
        self.quality_benchmarks = {
            QualityDimension.PLOT_COHERENCE: {
                "excellent": 0.9, "good": 0.75, "acceptable": 0.6, "poor": 0.4
            },
            QualityDimension.CHARACTER_DEVELOPMENT: {
                "excellent": 0.85, "good": 0.7, "acceptable": 0.55, "poor": 0.35
            },
            QualityDimension.DIALOGUE_QUALITY: {
                "excellent": 0.8, "good": 0.65, "acceptable": 0.5, "poor": 0.3
            },
            QualityDimension.PACING: {
                "excellent": 0.85, "good": 0.7, "acceptable": 0.55, "poor": 0.35
            },
            QualityDimension.WORLD_BUILDING: {
                "excellent": 0.9, "good": 0.75, "acceptable": 0.6, "poor": 0.4
            },
            QualityDimension.EMOTIONAL_IMPACT: {
                "excellent": 0.8, "good": 0.65, "acceptable": 0.5, "poor": 0.3
            }
        }
    
    async def analyze_story_quality(self, story_text: str, story_id: str,
                                  genre: Optional[StoryGenre] = None,
                                  context: Optional[Dict[str, Any]] = None) -> StoryQualityReport:
        """
        Perform comprehensive story quality analysis.
        
        Args:
            story_text: The story text to analyze
            story_id: Unique identifier for the story
            genre: Optional genre classification
            context: Optional context information
            
        Returns:
            Comprehensive quality analysis report
        """
        try:
            analysis_start = datetime.now()
            
            # Auto-detect genre if not provided
            if genre is None:
                genre = await self.detect_genre(story_text)
            
            # Initialize quality report
            report = StoryQualityReport(
                story_id=story_id,
                overall_score=0.0,
                quality_level=QualityLevel.POOR,
                genre=genre,
                word_count=len(story_text.split())
            )
            
            # Analyze each quality dimension
            dimension_scores = {}
            
            # Plot coherence analysis
            plot_score = await self._analyze_plot_coherence(story_text, genre)
            dimension_scores[QualityDimension.PLOT_COHERENCE] = plot_score
            
            # Character development analysis
            character_score = await self._analyze_character_development(story_text, genre)
            dimension_scores[QualityDimension.CHARACTER_DEVELOPMENT] = character_score
            
            # Dialogue quality analysis
            dialogue_score = await self._analyze_dialogue_quality(story_text, genre)
            dimension_scores[QualityDimension.DIALOGUE_QUALITY] = dialogue_score
            
            # Pacing analysis
            pacing_score = await self._analyze_pacing(story_text, genre)
            dimension_scores[QualityDimension.PACING] = pacing_score
            
            # World building analysis
            world_score = await self._analyze_world_building(story_text, genre)
            dimension_scores[QualityDimension.WORLD_BUILDING] = world_score
            
            # Emotional impact analysis
            emotion_score = await self._analyze_emotional_impact(story_text, genre)
            dimension_scores[QualityDimension.EMOTIONAL_IMPACT] = emotion_score
            
            # Additional analyses
            originality_score = await self._analyze_originality(story_text, genre)
            dimension_scores[QualityDimension.ORIGINALITY] = originality_score
            
            genre_consistency_score = await self._analyze_genre_consistency(story_text, genre)
            dimension_scores[QualityDimension.GENRE_CONSISTENCY] = genre_consistency_score
            
            # Store dimension scores
            report.dimension_scores = dimension_scores
            
            # Calculate overall score using genre-specific weights
            overall_score = await self._calculate_overall_score(dimension_scores, genre)
            report.overall_score = overall_score
            
            # Determine quality level
            report.quality_level = self._determine_quality_level(overall_score)
            
            # Generate insights and recommendations
            report.strengths = self._identify_strengths(dimension_scores)
            report.weaknesses = self._identify_weaknesses(dimension_scores)
            report.improvement_recommendations = await self._generate_recommendations(
                dimension_scores, genre, story_text
            )
            
            # Additional analyses
            report.reading_level = self._analyze_reading_level(story_text)
            report.sentiment_analysis = await self._analyze_sentiment(story_text)
            report.character_analysis = await self._analyze_characters(story_text)
            report.plot_analysis = await self._analyze_plot_structure(story_text)
            
            # Genre compliance
            if genre and genre in self.genre_templates:
                report.genre_compliance = await self._analyze_genre_compliance(story_text, genre)
            
            # Calculate processing time
            processing_time = (datetime.now() - analysis_start).total_seconds()
            report.processing_time = processing_time
            
            # Store in history
            self.quality_history[story_id].append(report)
            
            logger.info(f"Story quality analysis completed for {story_id} "
                       f"(Score: {overall_score:.2f}, Level: {report.quality_level.value})")
            
            return report
            
        except Exception as e:
            logger.error(f"Story quality analysis failed: {e}")
            # Return minimal report on error
            return StoryQualityReport(
                story_id=story_id,
                overall_score=0.0,
                quality_level=QualityLevel.VERY_POOR,
                weaknesses=["Analysis failed"],
                improvement_recommendations=["Retry analysis with valid input"]
            )
    
    async def detect_genre(self, story_text: str) -> Optional[StoryGenre]:
        """
        Automatically detect the genre of a story.
        
        Args:
            story_text: The story text to analyze
            
        Returns:
            Detected genre or None if uncertain
        """
        try:
            text_lower = story_text.lower()
            word_frequencies = Counter(text_lower.split())
            
            # Genre keyword patterns
            genre_keywords = {
                StoryGenre.SCIENCE_FICTION: [
                    'spaceship', 'alien', 'robot', 'technology', 'future', 'laser',
                    'galaxy', 'planet', 'android', 'cybernetic', 'quantum'
                ],
                StoryGenre.FANTASY: [
                    'magic', 'wizard', 'dragon', 'sword', 'castle', 'kingdom',
                    'spell', 'enchanted', 'mystical', 'quest', 'prophecy'
                ],
                StoryGenre.HORROR: [
                    'ghost', 'monster', 'terrifying', 'scream', 'blood', 'death',
                    'nightmare', 'haunted', 'evil', 'darkness', 'fear'
                ],
                StoryGenre.MYSTERY: [
                    'detective', 'clue', 'murder', 'investigation', 'suspect',
                    'evidence', 'mystery', 'crime', 'solve', 'witness'
                ],
                StoryGenre.ROMANCE: [
                    'love', 'heart', 'kiss', 'romantic', 'passion', 'wedding',
                    'relationship', 'couple', 'romance', 'affection'
                ]
            }
            
            # Calculate genre scores
            genre_scores = {}
            for genre, keywords in genre_keywords.items():
                score = sum(word_frequencies.get(keyword, 0) for keyword in keywords)
                # Normalize by text length
                genre_scores[genre] = score / len(story_text.split()) if story_text.split() else 0
            
            # Find the highest scoring genre
            if genre_scores:
                best_genre = max(genre_scores.items(), key=lambda x: x[1])
                if best_genre[1] > 0.01:  # Threshold for detection confidence
                    return best_genre[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Genre detection failed: {e}")
            return None
    
    async def get_quality_trends(self, story_id: str) -> Dict[str, Any]:
        """
        Get quality trends for a specific story over time.
        
        Args:
            story_id: Story identifier
            
        Returns:
            Quality trend analysis
        """
        try:
            if story_id not in self.quality_history:
                return {"error": "No quality history found for story"}
            
            history = self.quality_history[story_id]
            if len(history) < 2:
                return {"trend": "insufficient_data", "reports": len(history)}
            
            # Calculate trends
            scores = [report.overall_score for report in history]
            timestamps = [report.analysis_timestamp for report in history]
            
            # Overall trend
            trend_direction = "improving" if scores[-1] > scores[0] else "declining"
            if abs(scores[-1] - scores[0]) < 0.05:
                trend_direction = "stable"
            
            # Dimension trends
            dimension_trends = {}
            for dimension in QualityDimension:
                if all(dimension in report.dimension_scores for report in history):
                    dim_scores = [report.dimension_scores[dimension].score for report in history]
                    if dim_scores[-1] > dim_scores[0]:
                        dimension_trends[dimension.value] = "improving"
                    elif dim_scores[-1] < dim_scores[0]:
                        dimension_trends[dimension.value] = "declining"
                    else:
                        dimension_trends[dimension.value] = "stable"
            
            return {
                "story_id": story_id,
                "overall_trend": trend_direction,
                "score_change": scores[-1] - scores[0],
                "analysis_count": len(history),
                "dimension_trends": dimension_trends,
                "latest_score": scores[-1],
                "best_score": max(scores),
                "average_score": sum(scores) / len(scores),
                "analysis_period": {
                    "start": timestamps[0],
                    "end": timestamps[-1]
                }
            }
            
        except Exception as e:
            logger.error(f"Quality trend analysis failed: {e}")
            return {"error": str(e)}
    
    async def generate_improvement_plan(self, story_id: str) -> Dict[str, Any]:
        """
        Generate a detailed improvement plan for a story.
        
        Args:
            story_id: Story identifier
            
        Returns:
            Detailed improvement plan
        """
        try:
            if story_id not in self.quality_history:
                return {"error": "No quality history found for story"}
            
            latest_report = self.quality_history[story_id][-1]
            
            # Prioritize improvements based on impact and effort
            improvement_priorities = []
            
            for dimension, score in latest_report.dimension_scores.items():
                if score.score < 0.7:  # Needs improvement
                    priority_score = (1.0 - score.score) * score.confidence
                    improvement_priorities.append({
                        "dimension": dimension.value,
                        "current_score": score.score,
                        "priority": priority_score,
                        "suggestions": score.suggestions,
                        "effort_estimate": self._estimate_improvement_effort(dimension, score.score)
                    })
            
            # Sort by priority
            improvement_priorities.sort(key=lambda x: x["priority"], reverse=True)
            
            # Generate actionable plan
            plan = {
                "story_id": story_id,
                "current_overall_score": latest_report.overall_score,
                "target_score": min(latest_report.overall_score + 0.2, 1.0),
                "improvement_areas": improvement_priorities[:5],  # Top 5 priorities
                "quick_wins": [],
                "major_improvements": [],
                "estimated_timeline": "2-4 weeks",
                "success_metrics": []
            }
            
            # Categorize improvements
            for improvement in improvement_priorities:
                if improvement["effort_estimate"] == "low":
                    plan["quick_wins"].append(improvement)
                else:
                    plan["major_improvements"].append(improvement)
            
            # Define success metrics
            plan["success_metrics"] = [
                f"Increase overall score to {plan['target_score']:.2f}",
                f"Improve {improvement_priorities[0]['dimension']} by 0.15 points"
            ]
            
            return plan
            
        except Exception as e:
            logger.error(f"Improvement plan generation failed: {e}")
            return {"error": str(e)}
    
    # Quality analysis methods for each dimension
    
    async def _analyze_plot_coherence(self, story_text: str, genre: Optional[StoryGenre]) -> QualityScore:
        """Analyze plot coherence and logical flow."""
        try:
            # Basic plot coherence metrics
            sentences = story_text.split('.')
            paragraphs = story_text.split('\n\n')
            
            # Check for basic story structure
            has_beginning = len(sentences) > 0
            has_middle = len(paragraphs) > 2
            has_end = story_text.strip().endswith(('.', '!', '?'))
            
            # Basic coherence score
            structure_score = (has_beginning + has_middle + has_end) / 3
            
            # Check for transition quality (simple heuristic)
            transition_words = ['however', 'meanwhile', 'suddenly', 'then', 'next', 'finally']
            transition_count = sum(story_text.lower().count(word) for word in transition_words)
            transition_score = min(transition_count / (len(paragraphs) * 0.5), 1.0)
            
            # Overall plot coherence
            plot_score = (structure_score * 0.6 + transition_score * 0.4)
            
            evidence = []
            suggestions = []
            
            if structure_score < 0.7:
                suggestions.append("Strengthen story structure with clear beginning, middle, and end")
            if transition_score < 0.5:
                suggestions.append("Add more transitional elements between scenes")
            
            if plot_score > 0.8:
                evidence.append("Strong narrative structure and flow")
            
            return QualityScore(
                dimension=QualityDimension.PLOT_COHERENCE,
                score=plot_score,
                confidence=0.7,
                evidence=evidence,
                suggestions=suggestions,
                analysis_details={
                    "structure_score": structure_score,
                    "transition_score": transition_score,
                    "paragraph_count": len(paragraphs)
                }
            )
            
        except Exception as e:
            logger.error(f"Plot coherence analysis failed: {e}")
            return QualityScore(
                dimension=QualityDimension.PLOT_COHERENCE,
                score=0.5,
                confidence=0.1
            )
    
    async def _analyze_character_development(self, story_text: str, genre: Optional[StoryGenre]) -> QualityScore:
        """Analyze character development and depth."""
        try:
            # Extract potential character names (capitalized words not at sentence start)
            import re
            character_pattern = r'\b[A-Z][a-z]+\b'
            potential_characters = re.findall(character_pattern, story_text)
            character_frequency = Counter(potential_characters)
            
            # Filter to likely character names (appear multiple times)
            main_characters = [name for name, count in character_frequency.items() if count >= 3]
            
            # Character development indicators
            development_words = ['thought', 'felt', 'realized', 'understood', 'changed', 'grew']
            development_count = sum(story_text.lower().count(word) for word in development_words)
            
            # Character interaction indicators
            interaction_words = ['said', 'asked', 'replied', 'spoke', 'whispered', 'shouted']
            interaction_count = sum(story_text.lower().count(word) for word in interaction_words)
            
            # Calculate character development score
            character_presence = min(len(main_characters) / 3, 1.0)  # Ideal: 2-3 main characters
            development_density = min(development_count / (len(story_text.split()) * 0.02), 1.0)
            interaction_density = min(interaction_count / (len(story_text.split()) * 0.03), 1.0)
            
            overall_score = (character_presence * 0.4 + development_density * 0.3 + interaction_density * 0.3)
            
            evidence = []
            suggestions = []
            
            if len(main_characters) >= 2:
                evidence.append(f"Multiple well-developed characters identified: {', '.join(main_characters[:3])}")
            else:
                suggestions.append("Develop more distinct character voices and personalities")
            
            if development_density < 0.5:
                suggestions.append("Show more character growth and internal development")
            
            if interaction_density < 0.5:
                suggestions.append("Include more character dialogue and interactions")
            
            return QualityScore(
                dimension=QualityDimension.CHARACTER_DEVELOPMENT,
                score=overall_score,
                confidence=0.6,
                evidence=evidence,
                suggestions=suggestions,
                analysis_details={
                    "main_characters": main_characters,
                    "character_count": len(main_characters),
                    "development_density": development_density,
                    "interaction_density": interaction_density
                }
            )
            
        except Exception as e:
            logger.error(f"Character development analysis failed: {e}")
            return QualityScore(
                dimension=QualityDimension.CHARACTER_DEVELOPMENT,
                score=0.5,
                confidence=0.1
            )
    
    async def _analyze_dialogue_quality(self, story_text: str, genre: Optional[StoryGenre]) -> QualityScore:
        """Analyze dialogue quality and naturalness."""
        try:
            # Extract dialogue (text between quotes)
            dialogue_pattern = r'"([^"]*)"'
            dialogues = re.findall(dialogue_pattern, story_text)
            
            if not dialogues:
                return QualityScore(
                    dimension=QualityDimension.DIALOGUE_QUALITY,
                    score=0.3,
                    confidence=0.8,
                    suggestions=["Add dialogue to improve character interaction and story engagement"]
                )
            
            # Dialogue quality metrics
            avg_dialogue_length = sum(len(d.split()) for d in dialogues) / len(dialogues)
            dialogue_variety = len(set(dialogues)) / len(dialogues)  # Uniqueness ratio
            
            # Check for dialogue tags and variety
            dialogue_tags = ['said', 'asked', 'replied', 'whispered', 'shouted', 'exclaimed']
            tag_count = sum(story_text.lower().count(tag) for tag in dialogue_tags)
            tag_variety = len([tag for tag in dialogue_tags if tag in story_text.lower()])
            
            # Calculate dialogue score
            length_score = 1.0 - min(abs(avg_dialogue_length - 8) / 8, 1.0)  # Ideal: ~8 words
            variety_score = dialogue_variety
            tag_score = min(tag_variety / 4, 1.0)  # Use variety of dialogue tags
            
            overall_score = (length_score * 0.3 + variety_score * 0.4 + tag_score * 0.3)
            
            evidence = []
            suggestions = []
            
            if dialogue_variety > 0.8:
                evidence.append("Good dialogue variety and uniqueness")
            else:
                suggestions.append("Make dialogue more distinct between characters")
            
            if tag_variety < 3:
                suggestions.append("Use more varied dialogue tags to enhance readability")
            
            if avg_dialogue_length > 15:
                suggestions.append("Keep dialogue shorter and more natural")
            
            return QualityScore(
                dimension=QualityDimension.DIALOGUE_QUALITY,
                score=overall_score,
                confidence=0.7,
                evidence=evidence,
                suggestions=suggestions,
                analysis_details={
                    "dialogue_count": len(dialogues),
                    "avg_length": avg_dialogue_length,
                    "variety_ratio": dialogue_variety,
                    "tag_variety": tag_variety
                }
            )
            
        except Exception as e:
            logger.error(f"Dialogue quality analysis failed: {e}")
            return QualityScore(
                dimension=QualityDimension.DIALOGUE_QUALITY,
                score=0.5,
                confidence=0.1
            )
    
    async def _analyze_pacing(self, story_text: str, genre: Optional[StoryGenre]) -> QualityScore:
        """Analyze story pacing and rhythm."""
        try:
            sentences = [s.strip() for s in story_text.split('.') if s.strip()]
            paragraphs = [p.strip() for p in story_text.split('\n\n') if p.strip()]
            
            if not sentences:
                return QualityScore(
                    dimension=QualityDimension.PACING,
                    score=0.2,
                    confidence=0.8
                )
            
            # Sentence length analysis
            sentence_lengths = [len(s.split()) for s in sentences]
            avg_sentence_length = sum(sentence_lengths) / len(sentence_lengths)
            sentence_variety = len(set(sentence_lengths)) / len(sentence_lengths)
            
            # Paragraph length analysis
            paragraph_lengths = [len(p.split()) for p in paragraphs]
            avg_paragraph_length = sum(paragraph_lengths) / len(paragraph_lengths) if paragraph_lengths else 0
            
            # Pacing indicators
            action_words = ['ran', 'jumped', 'fought', 'rushed', 'quickly', 'suddenly']
            action_density = sum(story_text.lower().count(word) for word in action_words)
            
            slow_words = ['slowly', 'carefully', 'thoughtfully', 'peacefully', 'gently']
            slow_density = sum(story_text.lower().count(word) for word in slow_words)
            
            # Calculate pacing score
            length_score = 1.0 - min(abs(avg_sentence_length - 12) / 12, 1.0)  # Ideal: ~12 words
            variety_score = sentence_variety
            rhythm_score = min((action_density + slow_density) / (len(story_text.split()) * 0.01), 1.0)
            
            overall_score = (length_score * 0.4 + variety_score * 0.3 + rhythm_score * 0.3)
            
            evidence = []
            suggestions = []
            
            if sentence_variety > 0.5:
                evidence.append("Good sentence length variety creates natural rhythm")
            else:
                suggestions.append("Vary sentence lengths to improve pacing and flow")
            
            if avg_sentence_length > 20:
                suggestions.append("Consider shorter sentences for better readability")
            elif avg_sentence_length < 8:
                suggestions.append("Mix in some longer sentences for better flow")
            
            return QualityScore(
                dimension=QualityDimension.PACING,
                score=overall_score,
                confidence=0.6,
                evidence=evidence,
                suggestions=suggestions,
                analysis_details={
                    "avg_sentence_length": avg_sentence_length,
                    "sentence_variety": sentence_variety,
                    "avg_paragraph_length": avg_paragraph_length,
                    "action_density": action_density,
                    "slow_density": slow_density
                }
            )
            
        except Exception as e:
            logger.error(f"Pacing analysis failed: {e}")
            return QualityScore(
                dimension=QualityDimension.PACING,
                score=0.5,
                confidence=0.1
            )
    
    async def _analyze_world_building(self, story_text: str, genre: Optional[StoryGenre]) -> QualityScore:
        """Analyze world building and setting development."""
        try:
            # Setting descriptors
            sensory_words = ['saw', 'heard', 'felt', 'smelled', 'tasted']
            sensory_count = sum(story_text.lower().count(word) for word in sensory_words)
            
            # Descriptive adjectives
            descriptive_pattern = r'\b[A-Za-z]+ly\b'  # Adverbs
            adverb_count = len(re.findall(descriptive_pattern, story_text))
            
            # Setting elements
            setting_words = ['room', 'house', 'building', 'city', 'forest', 'mountain', 'ocean', 'sky']
            setting_count = sum(story_text.lower().count(word) for word in setting_words)
            
            # Environmental details
            detail_words = ['light', 'dark', 'warm', 'cold', 'loud', 'quiet', 'bright', 'dim']
            detail_count = sum(story_text.lower().count(word) for word in detail_words)
            
            # Calculate world building score
            word_count = len(story_text.split())
            sensory_density = min(sensory_count / (word_count * 0.01), 1.0)
            descriptive_density = min(adverb_count / (word_count * 0.02), 1.0)
            setting_density = min(setting_count / (word_count * 0.005), 1.0)
            detail_density = min(detail_count / (word_count * 0.01), 1.0)
            
            overall_score = (sensory_density * 0.3 + descriptive_density * 0.2 + 
                           setting_density * 0.3 + detail_density * 0.2)
            
            evidence = []
            suggestions = []
            
            if sensory_density > 0.7:
                evidence.append("Rich sensory details enhance immersion")
            else:
                suggestions.append("Add more sensory details to bring the world to life")
            
            if setting_density < 0.5:
                suggestions.append("Develop the setting with more environmental details")
            
            if descriptive_density < 0.5:
                suggestions.append("Use more descriptive language to paint vivid scenes")
            
            return QualityScore(
                dimension=QualityDimension.WORLD_BUILDING,
                score=overall_score,
                confidence=0.6,
                evidence=evidence,
                suggestions=suggestions,
                analysis_details={
                    "sensory_density": sensory_density,
                    "descriptive_density": descriptive_density,
                    "setting_density": setting_density,
                    "detail_density": detail_density
                }
            )
            
        except Exception as e:
            logger.error(f"World building analysis failed: {e}")
            return QualityScore(
                dimension=QualityDimension.WORLD_BUILDING,
                score=0.5,
                confidence=0.1
            )
    
    async def _analyze_emotional_impact(self, story_text: str, genre: Optional[StoryGenre]) -> QualityScore:
        """Analyze emotional impact and engagement."""
        try:
            # Emotion words
            positive_emotions = ['happy', 'joy', 'love', 'excited', 'hope', 'proud', 'amazed']
            negative_emotions = ['sad', 'angry', 'fear', 'worried', 'disappointed', 'hurt', 'despair']
            intense_emotions = ['rage', 'terror', 'ecstasy', 'devastated', 'furious', 'thrilled']
            
            # Count emotional words
            positive_count = sum(story_text.lower().count(word) for word in positive_emotions)
            negative_count = sum(story_text.lower().count(word) for word in negative_emotions)
            intense_count = sum(story_text.lower().count(word) for word in intense_emotions)
            
            # Emotional indicators
            exclamations = story_text.count('!')
            questions = story_text.count('?')
            word_count = len(story_text.split())
            
            # Calculate emotional impact score
            emotional_variety = min((positive_count + negative_count + intense_count) / (word_count * 0.02), 1.0)
            emotional_intensity = min(intense_count / (word_count * 0.005), 1.0)
            punctuation_impact = min((exclamations + questions) / (word_count * 0.01), 1.0)
            
            overall_score = (emotional_variety * 0.5 + emotional_intensity * 0.3 + punctuation_impact * 0.2)
            
            evidence = []
            suggestions = []
            
            if emotional_variety > 0.7:
                evidence.append("Good emotional range creates engaging narrative")
            else:
                suggestions.append("Include more emotional depth and variety")
            
            if intense_count == 0:
                suggestions.append("Add moments of high emotional intensity")
            
            if exclamations + questions < 3:
                suggestions.append("Use punctuation to enhance emotional expression")
            
            return QualityScore(
                dimension=QualityDimension.EMOTIONAL_IMPACT,
                score=overall_score,
                confidence=0.6,
                evidence=evidence,
                suggestions=suggestions,
                analysis_details={
                    "emotional_variety": emotional_variety,
                    "emotional_intensity": emotional_intensity,
                    "punctuation_impact": punctuation_impact,
                    "positive_emotions": positive_count,
                    "negative_emotions": negative_count,
                    "intense_emotions": intense_count
                }
            )
            
        except Exception as e:
            logger.error(f"Emotional impact analysis failed: {e}")
            return QualityScore(
                dimension=QualityDimension.EMOTIONAL_IMPACT,
                score=0.5,
                confidence=0.1
            )
    
    async def _analyze_originality(self, story_text: str, genre: Optional[StoryGenre]) -> QualityScore:
        """Analyze story originality and uniqueness."""
        try:
            # This is a simplified originality analysis
            # In a real implementation, this would check against a database of existing stories
            
            # Check for clichés and overused phrases
            common_cliches = [
                'it was a dark and stormy night', 'once upon a time',
                'suddenly', 'little did he know', 'all hell broke loose'
            ]
            
            cliche_count = sum(story_text.lower().count(cliche) for cliche in common_cliches)
            
            # Unique word usage
            words = story_text.lower().split()
            unique_words = len(set(words))
            word_variety = unique_words / len(words) if words else 0
            
            # Calculate originality score
            cliche_penalty = min(cliche_count * 0.2, 0.5)
            variety_bonus = min(word_variety * 2, 1.0)
            
            overall_score = max(variety_bonus - cliche_penalty, 0.1)
            
            evidence = []
            suggestions = []
            
            if cliche_count > 0:
                suggestions.append("Avoid common clichés and overused phrases")
            else:
                evidence.append("Avoids common clichés and stereotypes")
            
            if word_variety > 0.6:
                evidence.append("Rich vocabulary demonstrates originality")
            else:
                suggestions.append("Use more varied vocabulary and expressions")
            
            return QualityScore(
                dimension=QualityDimension.ORIGINALITY,
                score=overall_score,
                confidence=0.5,
                evidence=evidence,
                suggestions=suggestions,
                analysis_details={
                    "cliche_count": cliche_count,
                    "word_variety": word_variety,
                    "unique_words": unique_words,
                    "total_words": len(words)
                }
            )
            
        except Exception as e:
            logger.error(f"Originality analysis failed: {e}")
            return QualityScore(
                dimension=QualityDimension.ORIGINALITY,
                score=0.5,
                confidence=0.1
            )
    
    async def _analyze_genre_consistency(self, story_text: str, genre: Optional[StoryGenre]) -> QualityScore:
        """Analyze consistency with genre conventions."""
        try:
            if not genre or genre not in self.genre_templates:
                return QualityScore(
                    dimension=QualityDimension.GENRE_CONSISTENCY,
                    score=0.5,
                    confidence=0.1,
                    suggestions=["Genre not specified or template not available"]
                )
            
            template = self.genre_templates[genre]
            text_lower = story_text.lower()
            
            # Check for required genre elements
            elements_present = 0
            missing_elements = []
            
            for element in template.required_elements:
                # Simple keyword check (would be more sophisticated in practice)
                if element.replace('_', ' ') in text_lower:
                    elements_present += 1
                else:
                    missing_elements.append(element)
            
            element_score = elements_present / len(template.required_elements)
            
            # Check genre-specific metrics if available
            metric_scores = []
            for metric_name, expected_value in template.genre_specific_metrics.items():
                # This would be calculated based on actual content analysis
                # For now, use a placeholder
                metric_scores.append(0.7)
            
            avg_metric_score = sum(metric_scores) / len(metric_scores) if metric_scores else 0.5
            
            overall_score = (element_score * 0.7 + avg_metric_score * 0.3)
            
            evidence = []
            suggestions = []
            
            if element_score > 0.8:
                evidence.append(f"Contains most required {genre.value} elements")
            else:
                suggestions.append(f"Include more {genre.value} genre elements: {', '.join(missing_elements)}")
            
            return QualityScore(
                dimension=QualityDimension.GENRE_CONSISTENCY,
                score=overall_score,
                confidence=0.6,
                evidence=evidence,
                suggestions=suggestions,
                analysis_details={
                    "genre": genre.value,
                    "elements_present": elements_present,
                    "total_elements": len(template.required_elements),
                    "missing_elements": missing_elements,
                    "element_score": element_score
                }
            )
            
        except Exception as e:
            logger.error(f"Genre consistency analysis failed: {e}")
            return QualityScore(
                dimension=QualityDimension.GENRE_CONSISTENCY,
                score=0.5,
                confidence=0.1
            )
    
    # Helper methods
    
    async def _calculate_overall_score(self, dimension_scores: Dict[QualityDimension, QualityScore], 
                                     genre: Optional[StoryGenre]) -> float:
        """Calculate weighted overall quality score."""
        if not dimension_scores:
            return 0.0
        
        # Get genre-specific weights if available
        weights = {}
        if genre and genre in self.genre_templates:
            weights = self.genre_templates[genre].dimension_weights
        
        # Calculate weighted average
        total_score = 0.0
        total_weight = 0.0
        
        for dimension, score in dimension_scores.items():
            weight = weights.get(dimension, 1.0)
            total_score += score.score * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def _determine_quality_level(self, overall_score: float) -> QualityLevel:
        """Determine quality level from overall score."""
        if overall_score >= 0.9:
            return QualityLevel.EXCEPTIONAL
        elif overall_score >= 0.8:
            return QualityLevel.EXCELLENT
        elif overall_score >= 0.7:
            return QualityLevel.GOOD
        elif overall_score >= 0.6:
            return QualityLevel.ACCEPTABLE
        elif overall_score >= 0.4:
            return QualityLevel.POOR
        else:
            return QualityLevel.VERY_POOR
    
    def _identify_strengths(self, dimension_scores: Dict[QualityDimension, QualityScore]) -> List[str]:
        """Identify story strengths based on dimension scores."""
        strengths = []
        for dimension, score in dimension_scores.items():
            if score.score >= 0.8:
                strengths.append(f"Strong {dimension.value.replace('_', ' ')}")
        return strengths
    
    def _identify_weaknesses(self, dimension_scores: Dict[QualityDimension, QualityScore]) -> List[str]:
        """Identify story weaknesses based on dimension scores."""
        weaknesses = []
        for dimension, score in dimension_scores.items():
            if score.score < 0.6:
                weaknesses.append(f"Weak {dimension.value.replace('_', ' ')}")
        return weaknesses
    
    async def _generate_recommendations(self, dimension_scores: Dict[QualityDimension, QualityScore], 
                                      genre: Optional[StoryGenre], story_text: str) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []
        
        # Collect suggestions from each dimension
        for dimension, score in dimension_scores.items():
            if score.score < 0.7 and score.suggestions:
                recommendations.extend(score.suggestions)
        
        # Add genre-specific recommendations
        if genre and genre in self.genre_templates:
            template = self.genre_templates[genre]
            # Add style guidelines
            if 'pacing' in template.style_guidelines:
                pacing_style = template.style_guidelines['pacing']
                recommendations.append(f"Consider {pacing_style} pacing typical of {genre.value}")
        
        # Remove duplicates and limit to top recommendations
        unique_recommendations = list(set(recommendations))
        return unique_recommendations[:8]
    
    def _analyze_reading_level(self, story_text: str) -> str:
        """Analyze reading level/complexity."""
        words = story_text.split()
        sentences = story_text.split('.')
        
        if not words or not sentences:
            return "unknown"
        
        avg_words_per_sentence = len(words) / len(sentences)
        
        # Simple reading level estimation
        if avg_words_per_sentence < 10:
            return "elementary"
        elif avg_words_per_sentence < 15:
            return "middle_school"
        elif avg_words_per_sentence < 20:
            return "high_school"
        else:
            return "college"
    
    async def _analyze_sentiment(self, story_text: str) -> Dict[str, float]:
        """Analyze sentiment distribution in the story."""
        # Simplified sentiment analysis
        positive_words = ['good', 'great', 'wonderful', 'amazing', 'beautiful', 'love', 'happy']
        negative_words = ['bad', 'terrible', 'awful', 'horrible', 'ugly', 'hate', 'sad']
        
        text_lower = story_text.lower()
        positive_count = sum(text_lower.count(word) for word in positive_words)
        negative_count = sum(text_lower.count(word) for word in negative_words)
        
        total_sentiment_words = positive_count + negative_count
        if total_sentiment_words == 0:
            return {"positive": 0.5, "negative": 0.5, "neutral": 0.0}
        
        positive_ratio = positive_count / total_sentiment_words
        negative_ratio = negative_count / total_sentiment_words
        
        return {
            "positive": positive_ratio,
            "negative": negative_ratio,
            "neutral": 1.0 - positive_ratio - negative_ratio
        }
    
    async def _analyze_characters(self, story_text: str) -> Dict[str, Any]:
        """Analyze character presence and development."""
        # Extract potential character names
        character_pattern = r'\b[A-Z][a-z]+\b'
        potential_characters = re.findall(character_pattern, story_text)
        character_frequency = Counter(potential_characters)
        
        # Filter to likely character names
        main_characters = [name for name, count in character_frequency.items() if count >= 3]
        
        return {
            "main_characters": main_characters,
            "character_count": len(main_characters),
            "total_name_mentions": sum(character_frequency.values()),
            "character_distribution": dict(character_frequency.most_common(5))
        }
    
    async def _analyze_plot_structure(self, story_text: str) -> Dict[str, Any]:
        """Analyze plot structure and narrative elements."""
        paragraphs = [p.strip() for p in story_text.split('\n\n') if p.strip()]
        sentences = [s.strip() for s in story_text.split('.') if s.strip()]
        
        # Simple story arc detection
        total_length = len(story_text)
        exposition_end = int(total_length * 0.25)
        climax_start = int(total_length * 0.75)
        
        exposition = story_text[:exposition_end]
        rising_action = story_text[exposition_end:climax_start]
        climax_resolution = story_text[climax_start:]
        
        return {
            "total_paragraphs": len(paragraphs),
            "total_sentences": len(sentences),
            "structure_analysis": {
                "exposition_length": len(exposition.split()),
                "rising_action_length": len(rising_action.split()),
                "climax_resolution_length": len(climax_resolution.split())
            },
            "avg_paragraph_length": sum(len(p.split()) for p in paragraphs) / len(paragraphs) if paragraphs else 0,
            "avg_sentence_length": sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        }
    
    async def _analyze_genre_compliance(self, story_text: str, genre: StoryGenre) -> float:
        """Analyze compliance with genre conventions."""
        if genre not in self.genre_templates:
            return 0.5
        
        template = self.genre_templates[genre]
        compliance_scores = []
        
        # Check required elements
        text_lower = story_text.lower()
        for element in template.required_elements:
            element_keywords = element.replace('_', ' ').split()
            presence_score = sum(1 for keyword in element_keywords if keyword in text_lower)
            compliance_scores.append(min(presence_score / len(element_keywords), 1.0))
        
        # Check genre-specific patterns
        for pattern in template.common_patterns:
            pattern_keywords = pattern.replace('_', ' ').split()
            presence_score = sum(1 for keyword in pattern_keywords if keyword in text_lower)
            compliance_scores.append(min(presence_score / len(pattern_keywords), 1.0))
        
        return sum(compliance_scores) / len(compliance_scores) if compliance_scores else 0.5
    
    def _estimate_improvement_effort(self, dimension: QualityDimension, current_score: float) -> str:
        """Estimate effort required to improve a dimension."""
        effort_map = {
            QualityDimension.DIALOGUE_QUALITY: "low",
            QualityDimension.PACING: "low",
            QualityDimension.CHARACTER_DEVELOPMENT: "medium",
            QualityDimension.PLOT_COHERENCE: "high",
            QualityDimension.WORLD_BUILDING: "high",
            QualityDimension.EMOTIONAL_IMPACT: "medium"
        }
        
        base_effort = effort_map.get(dimension, "medium")
        
        # Adjust based on current score
        if current_score < 0.3:
            return "high"  # Major rewrite needed
        elif current_score < 0.5 and base_effort == "high":
            return "high"
        elif current_score < 0.5:
            return "medium"
        else:
            return base_effort


def create_story_quality_engine() -> StoryQualityEngine:
    """
    Factory function to create and configure a Story Quality Engine.
    
    Returns:
        Configured StoryQualityEngine instance
    """
    engine = StoryQualityEngine()
    logger.info("Story Quality Engine created and configured")
    return engine