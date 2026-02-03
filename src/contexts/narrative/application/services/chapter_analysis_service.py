"""Chapter Analysis Service - Structural health analysis for chapters.

This service provides comprehensive chapter-level structural analysis for
Director Mode, enabling authors to understand the balance, pacing, and
overall health of their chapters through automated heuristics.

Why a separate service:
    ChapterAnalysisService operates at the chapter level, aggregating
    scene-level data into actionable insights about narrative structure.
    Unlike PacingService which focuses on tension/energy flow, this service
    evaluates overall chapter balance and story structure.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from src.contexts.narrative.domain.entities.scene import Scene


class HealthScore(str, Enum):
    """Overall health classification for a chapter.

    Why this enum:
        Provides a simple, actionable classification that helps authors
        quickly understand if their chapter needs work. The scores map
        to intuitive health states from critical to excellent.
    """

    CRITICAL = "critical"  # Major structural issues
    POOR = "poor"  # Multiple significant issues
    FAIR = "fair"  # Some issues but functional
    GOOD = "good"  # Minor issues or well-balanced
    EXCELLENT = "excellent"  # No issues detected


class WarningCategory(str, Enum):
    """Categories of structural warnings.

    Why this enum:
        Groups warnings by type, enabling UI filtering and prioritization.
        Categories map to specific aspects of narrative structure.
    """

    PACING = "pacing"  # Tension/energy issues
    STRUCTURE = "structure"  # Phase distribution issues
    CONFLICT = "conflict"  # Missing or unresolved conflicts
    BALANCE = "balance"  # Word count and beat count issues
    ARC = "arc"  # Tension arc shape issues


@dataclass(frozen=True)
class PhaseDistribution:
    """Distribution of scenes across story phases.

    Attributes:
        setup: Number of scenes in SETUP phase.
        inciting_incident: Number of scenes in INCITING_INCIDENT phase.
        rising_action: Number of scenes in RISING_ACTION phase.
        climax: Number of scenes in CLIMAX phase.
        resolution: Number of scenes in RESOLUTION phase.

    Why frozen:
        Immutable snapshot of phase distribution for analysis.
    """

    setup: int
    inciting_incident: int
    rising_action: int
    climax: int
    resolution: int


@dataclass(frozen=True)
class WordCountEstimate:
    """Estimated word count metrics for a chapter.

    Attributes:
        total_words: Estimated total word count.
        min_words: Minimum estimated word count.
        max_words: Maximum estimated word count.
        per_scene_average: Average words per scene.

    Why frozen:
        Immutable snapshot of word count estimates.

    Why estimate:
        Actual word count requires content analysis. We estimate based
        on beat counts using a heuristic: ~250 words per beat average.
        This is fast and useful for relative comparisons.
    """

    total_words: int
    min_words: int
    max_words: int
    per_scene_average: float


@dataclass(frozen=True)
class HealthWarning:
    """A detected structural issue in the chapter.

    Attributes:
        category: The type of issue (pacing, structure, conflict, etc.).
        title: Short, human-readable title.
        description: Detailed explanation of the issue.
        severity: Issue severity (low, medium, high, critical).
        affected_scenes: List of scene IDs involved (optional).
        recommendation: Actionable suggestion for fixing the issue.

    Why this structure:
        Provides enough context for UI display and actionable guidance
        without being prescriptive about exact solutions.
    """

    category: WarningCategory
    title: str
    description: str
    severity: str
    affected_scenes: list[UUID]
    recommendation: str


@dataclass(frozen=True)
class TensionArcShape:
    """Analysis of the tension arc shape.

    Attributes:
        shape_type: Descriptive name of the arc shape (e.g., "gradual_rise").
        starts_at: Opening tension level.
        peaks_at: Maximum tension level.
        ends_at: Closing tension level.
        has_clear_climax: Whether there's a distinct tension peak.
        is_monotonic: Whether tension stays flat throughout.

    Why frozen:
        Immutable snapshot of tension arc analysis.
    """

    shape_type: str
    starts_at: int
    peaks_at: int
    ends_at: int
    has_clear_climax: bool
    is_monotonic: bool


@dataclass(frozen=True)
class ChapterHealthReport:
    """Complete structural health analysis for a chapter.

    Attributes:
        chapter_id: The chapter being analyzed.
        health_score: Overall health classification.
        phase_distribution: Scene counts per story phase.
        word_count: Estimated word count metrics.
        total_scenes: Number of scenes in the chapter.
        total_beats: Total number of beats across all scenes.
        tension_arc: Analysis of tension arc shape.
        warnings: List of detected structural issues.
        recommendations: List of improvement suggestions.
    """

    chapter_id: UUID
    health_score: HealthScore
    phase_distribution: PhaseDistribution
    word_count: WordCountEstimate
    total_scenes: int
    total_beats: int
    tension_arc: TensionArcShape
    warnings: list[HealthWarning]
    recommendations: list[str]


class ChapterAnalysisService:
    """Service for analyzing chapter structural health.

    Analyzes scenes within a chapter to produce health metrics and
    identify potential structural issues like missing climax, poor
    phase balance, unresolved conflicts, and flat tension arcs.

    Why application layer:
        This service orchestrates analysis across multiple domain entities
        (scenes, beats) and produces derived insights. It doesn't modify
        state, making it a pure query/analysis service.
    """

    # Heuristic: average words per beat for estimation
    WORDS_PER_BEAT: int = 250

    # Minimum beats per scene for adequate development
    MIN_BEATS_PER_SCENE: int = 3

    # Threshold for "too much action" (consecutive high-energy scenes)
    HIGH_ENERGY_THRESHOLD: int = 7

    # Threshold for "no rest" (consecutive scenes above baseline)
    BASELINE_ENERGY: int = 6

    def analyze_chapter_structure(
        self, chapter_id: UUID, scenes: list[Scene]
    ) -> ChapterHealthReport:
        """Perform comprehensive structural analysis of a chapter.

        Analyzes scene distribution, word counts, tension arc, and
        generates health warnings and recommendations.

        Args:
            chapter_id: The chapter's unique identifier.
            scenes: List of scenes belonging to the chapter.

        Returns:
            ChapterHealthReport with complete analysis.

        Why scenes as parameter:
            Keeps the service stateless and independent of repositories.
            The caller (router/controller) handles data fetching.
        """
        if not scenes:
            return self._empty_report(chapter_id)

        # Sort scenes by order_index for analysis
        sorted_scenes = sorted(scenes, key=lambda s: s.order_index)

        # Calculate basic metrics
        total_scenes = len(sorted_scenes)
        total_beats = sum(len(scene.beats) for scene in sorted_scenes)

        # Analyze phase distribution
        phase_dist = self._analyze_phase_distribution(sorted_scenes)

        # Estimate word count
        word_count = self._estimate_word_count(sorted_scenes)

        # Analyze tension arc
        tension_arc = self._analyze_tension_arc(sorted_scenes)

        # Generate warnings
        warnings = self._generate_warnings(
            sorted_scenes, phase_dist, tension_arc
        )

        # Calculate overall health score
        health_score = self._calculate_health_score(warnings, total_scenes)

        # Generate recommendations
        recommendations = self._generate_recommendations(warnings)

        return ChapterHealthReport(
            chapter_id=chapter_id,
            health_score=health_score,
            phase_distribution=phase_dist,
            word_count=word_count,
            total_scenes=total_scenes,
            total_beats=total_beats,
            tension_arc=tension_arc,
            warnings=warnings,
            recommendations=recommendations,
        )

    def _empty_report(self, chapter_id: UUID) -> ChapterHealthReport:
        """Return an empty report for chapters with no scenes."""
        empty_phase = PhaseDistribution(0, 0, 0, 0, 0)
        empty_words = WordCountEstimate(0, 0, 0, 0.0)
        empty_arc = TensionArcShape("empty", 0, 0, 0, False, True)

        return ChapterHealthReport(
            chapter_id=chapter_id,
            health_score=HealthScore.FAIR,
            phase_distribution=empty_phase,
            word_count=empty_words,
            total_scenes=0,
            total_beats=0,
            tension_arc=empty_arc,
            warnings=[],
            recommendations=["Add scenes to this chapter to begin analysis."],
        )

    def _analyze_phase_distribution(
        self, scenes: list[Scene]
    ) -> PhaseDistribution:
        """Count scenes per story phase.

        Args:
            scenes: Sorted list of scenes.

        Returns:
            PhaseDistribution with counts per phase.
        """
        from src.contexts.narrative.domain.entities.scene import StoryPhase

        counter = Counter(scene.story_phase for scene in scenes)

        return PhaseDistribution(
            setup=counter.get(StoryPhase.SETUP, 0),
            inciting_incident=counter.get(StoryPhase.INCITING_INCIDENT, 0),
            rising_action=counter.get(StoryPhase.RISING_ACTION, 0),
            climax=counter.get(StoryPhase.CLIMAX, 0),
            resolution=counter.get(StoryPhase.RESOLUTION, 0),
        )

    def _estimate_word_count(
        self, scenes: list[Scene]
    ) -> WordCountEstimate:
        """Estimate word count based on beat counts.

        Args:
            scenes: List of scenes.

        Returns:
            WordCountEstimate with min/max/average word counts.

        Why estimation:
            Actual word count requires analyzing beat content text.
            Beat count is a fast proxy that correlates with content length.
        """
        total_beats = sum(len(scene.beats) for scene in scenes)
        total_scenes = len(scenes)

        if total_beats == 0:
            return WordCountEstimate(0, 0, 0, 0.0)

        # Estimate: average 250 words per beat
        estimated_words = total_beats * self.WORDS_PER_BEAT

        # Range: ±20% for uncertainty
        min_words = int(estimated_words * 0.8)
        max_words = int(estimated_words * 1.2)

        per_scene_average = estimated_words / total_scenes if total_scenes > 0 else 0.0

        return WordCountEstimate(
            total_words=estimated_words,
            min_words=min_words,
            max_words=max_words,
            per_scene_average=round(per_scene_average, 1),
        )

    def _analyze_tension_arc(
        self, scenes: list[Scene]
    ) -> TensionArcShape:
        """Analyze the shape of the tension arc.

        Args:
            scenes: Sorted list of scenes.

        Returns:
            TensionArcShape describing the arc pattern.

        Why tension arc analysis:
            A well-structured chapter typically builds tension toward
            a climax, then releases. Flat arcs or monotonic tension
            can indicate pacing problems.
        """
        if not scenes:
            return TensionArcShape("empty", 0, 0, 0, False, True)

        tensions = [scene.tension_level for scene in scenes]

        starts_at = tensions[0]
        peaks_at = max(tensions)
        ends_at = tensions[-1]

        # Check for monotonic tension
        unique_tensions = set(tensions)
        is_monotonic = len(unique_tensions) <= 2

        # Check for clear climax (tension peak in final 40% of chapter)
        climax_zone_start = int(len(scenes) * 0.6)
        climax_zone_tensions = tensions[climax_zone_start:]
        has_clear_climax = peaks_at in climax_zone_tensions and peaks_at >= 7

        # Classify shape
        if is_monotonic:
            shape_type = "flat"
        elif peaks_at == starts_at and peaks_at == ends_at:
            shape_type = "flat"
        elif starts_at < peaks_at and ends_at < peaks_at:
            shape_type = "mountain"  # Rise to climax, then fall
        elif starts_at < peaks_at:
            shape_type = "rising"  # Continuous rise
        elif starts_at > peaks_at and ends_at < peaks_at:
            shape_type = "valley"  # Dip in middle
        else:
            shape_type = "irregular"

        return TensionArcShape(
            shape_type=shape_type,
            starts_at=starts_at,
            peaks_at=peaks_at,
            ends_at=ends_at,
            has_clear_climax=has_clear_climax,
            is_monotonic=is_monotonic,
        )

    def _generate_warnings(
        self,
        scenes: list[Scene],
        phase_dist: PhaseDistribution,
        tension_arc: TensionArcShape,
    ) -> list[HealthWarning]:
        """Generate health warnings based on analysis.

        Args:
            scenes: Sorted list of scenes.
            phase_dist: Phase distribution analysis.
            tension_arc: Tension arc analysis.

        Returns:
            List of HealthWarning objects.
        """
        warnings: list[HealthWarning] = []

        # Check for missing climax
        if phase_dist.climax == 0:
            warnings.append(
                HealthWarning(
                    category=WarningCategory.STRUCTURE,
                    title="Missing Climax",
                    description=(
                        "This chapter has no scenes marked as CLIMAX phase. "
                        "A climax provides the dramatic peak and resolution "
                        "to the chapter's central conflict."
                    ),
                    severity="high",
                    affected_scenes=[],
                    recommendation=(
                        "Consider adding or marking a scene as CLIMAX. This "
                        "should be the moment of highest tension where the "
                        "chapter's central conflict comes to a head."
                    ),
                )
            )

        # Check for missing resolution
        if phase_dist.resolution == 0:
            warnings.append(
                HealthWarning(
                    category=WarningCategory.STRUCTURE,
                    title="Missing Resolution",
                    description=(
                        "This chapter has no scenes marked as RESOLUTION phase. "
                        "Readers need closure after the climax."
                    ),
                    severity="medium",
                    affected_scenes=[],
                    recommendation=(
                        "Consider adding a scene to provide closure and show "
                        "the aftermath of the climax, or mark an existing "
                        "scene as RESOLUTION."
                    ),
                )
            )

        # Check for imbalanced phase distribution (too much in one phase)
        if phase_dist.rising_action > len(scenes) * 0.7:
            warnings.append(
                HealthWarning(
                    category=WarningCategory.BALANCE,
                    title="Overlong Rising Action",
                    description=(
                        f"{phase_dist.rising_action} out of {len(scenes)} scenes "
                        f"are marked as RISING_ACTION ({int(phase_dist.rising_action/len(scenes)*100)}%). "
                        "This may drag the middle of the chapter."
                    ),
                    severity="medium",
                    affected_scenes=[
                        s.id for s in scenes
                        if s.story_phase.value == "rising_action"
                    ],
                    recommendation=(
                        "Consider trimming or combining some rising action "
                        "scenes, or adding more scenes to other phases "
                        "for better balance."
                    ),
                )
            )

        # Check for "too much action, no rest"
        high_energy_count = 0
        high_energy_scenes = []
        for scene in scenes:
            if scene.energy_level >= self.HIGH_ENERGY_THRESHOLD:
                high_energy_count += 1
                high_energy_scenes.append(scene.id)
            else:
                # Reset on low energy scene (rest)
                if high_energy_count >= 3:
                    warnings.append(
                        HealthWarning(
                            category=WarningCategory.PACING,
                            title="Too Much Action, No Rest",
                            description=(
                                f"{high_energy_count} consecutive scenes have "
                                f"high energy (>= {self.HIGH_ENERGY_THRESHOLD}). "
                                "Readers need breathing room between intense moments."
                            ),
                            severity="medium",
                            affected_scenes=high_energy_scenes.copy(),
                            recommendation=(
                                "Consider adding a quieter scene for character "
                                "development or reflection to break up the action."
                            ),
                        )
                    )
                high_energy_count = 0
                high_energy_scens = []

        # Check for flat tension arc
        if tension_arc.is_monotonic and len(scenes) >= 3:
            warnings.append(
                HealthWarning(
                    category=WarningCategory.ARC,
                    title="Flat Tension Arc",
                    description=(
                        f"Tension stays flat throughout the chapter "
                        f"(range: {min(s.tension_level for s in scenes)}-"
                        f"{max(s.tension_level for s in scenes)}). "
                        "This may feel monotonous to readers."
                    ),
                    severity="medium",
                    affected_scenes=[s.id for s in scenes],
                    recommendation=(
                        "Vary tension levels to create narrative rhythm. "
                        "Consider raising tension toward a climax, then "
                        "releasing for resolution."
                    ),
                )
            )

        # Check for underdeveloped scenes (too few beats)
        underdeveloped = [
            s for s in scenes if len(s.beats) < self.MIN_BEATS_PER_SCENE
        ]
        if underdeveloped:
            warnings.append(
                HealthWarning(
                    category=WarningCategory.BALANCE,
                    title="Underdeveloped Scenes",
                    description=(
                        f"{len(underdeveloped)} scene(s) have fewer than "
                        f"{self.MIN_BEATS_PER_SCENE} beats, which may indicate "
                        "insufficient development."
                    ),
                    severity="low",
                    affected_scenes=[s.id for s in underdeveloped],
                    recommendation=(
                        f"Expand underdeveloped scenes to at least "
                        f"{self.MIN_BEATS_PER_SCENE} beats for adequate "
                        "narrative coverage, or combine with other scenes."
                    ),
                )
            )

        return warnings

    def _calculate_health_score(
        self, warnings: list[HealthWarning], scene_count: int
    ) -> HealthScore:
        """Calculate overall health score from warnings.

        Args:
            warnings: List of detected warnings.
            scene_count: Number of scenes (affects severity weighting).

        Returns:
            HealthScore classification.
        """
        if scene_count == 0:
            return HealthScore.FAIR

        # Count warnings by severity
        critical_count = sum(1 for w in warnings if w.severity == "critical")
        high_count = sum(1 for w in warnings if w.severity == "high")
        medium_count = sum(1 for w in warnings if w.severity == "medium")
        low_count = sum(1 for w in warnings if w.severity == "low")

        # Determine health score
        if critical_count > 0 or high_count >= 2:
            return HealthScore.CRITICAL
        if high_count == 1 or medium_count >= 3:
            return HealthScore.POOR
        if medium_count >= 1:
            return HealthScore.FAIR
        if low_count >= 2:
            return HealthScore.GOOD
        return HealthScore.EXCELLENT

    def _generate_recommendations(
        self, warnings: list[HealthWarning]
    ) -> list[str]:
        """Generate summary recommendations from warnings.

        Args:
            warnings: List of health warnings.

        Returns:
            List of high-level recommendations.
        """
        if not warnings:
            return [
                "Chapter structure looks healthy! Continue maintaining "
                "balance across phases and tension levels."
            ]

        # Group by category and extract unique recommendations
        category_map: dict[str, set[str]] = {}
        for warning in warnings:
            cat = warning.category.value
            if cat not in category_map:
                category_map[cat] = set()
            category_map[cat].add(warning.recommendation)

        # Flatten to list
        recommendations = []
        for rec_set in category_map.values():
            recommendations.extend(list(rec_set))

        return recommendations
