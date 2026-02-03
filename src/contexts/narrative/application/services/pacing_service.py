"""Pacing Service - Scene-by-scene pacing analysis for chapters.

This service provides pacing analysis capabilities for Director Mode,
enabling authors to visualize and optimize the narrative rhythm of
their chapters through tension and energy metrics.

Why a separate service:
    PacingService operates at the chapter level, aggregating scene-level
    metrics into actionable insights. This differs from the domain-level
    PacingManager which adjusts turn-by-turn pacing in orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .....core.result import Error, Ok, Result

if TYPE_CHECKING:
    from uuid import UUID

    from src.contexts.narrative.domain.entities.scene import Scene


@dataclass(frozen=True)
class ScenePacingMetrics:
    """Pacing metrics for a single scene.

    Attributes:
        scene_id: The scene's unique identifier.
        scene_title: The scene's title for display purposes.
        order_index: The scene's position in the chapter.
        tension_level: Dramatic tension (1-10).
        energy_level: Narrative momentum (1-10).

    Why frozen:
        Metrics are immutable snapshots. Modifications should go through
        the Scene entity and generate new metrics.
    """

    scene_id: UUID
    scene_title: str
    order_index: int
    tension_level: int
    energy_level: int


@dataclass(frozen=True)
class PacingIssue:
    """A detected pacing problem in the chapter.

    Attributes:
        issue_type: Category of the issue (monotony, spike, etc.).
        description: Human-readable description of the problem.
        affected_scenes: List of scene IDs involved in the issue.
        severity: Issue severity (low, medium, high).
        suggestion: Recommendation for addressing the issue.

    Why this structure:
        Provides enough context for UI display and actionable guidance
        for the author without being prescriptive about solutions.
    """

    issue_type: str
    description: str
    affected_scenes: list[UUID]
    severity: str
    suggestion: str


@dataclass(frozen=True)
class ChapterPacingReport:
    """Complete pacing analysis for a chapter.

    Attributes:
        chapter_id: The chapter being analyzed.
        scene_metrics: Ordered list of per-scene metrics.
        issues: Detected pacing problems.
        average_tension: Mean tension across all scenes.
        average_energy: Mean energy across all scenes.
        tension_range: Tuple of (min, max) tension values.
        energy_range: Tuple of (min, max) energy values.
    """

    chapter_id: UUID
    scene_metrics: list[ScenePacingMetrics]
    issues: list[PacingIssue]
    average_tension: float
    average_energy: float
    tension_range: tuple[int, int]
    energy_range: tuple[int, int]


class PacingService:
    """Service for analyzing chapter pacing.

    Analyzes scenes within a chapter to produce pacing metrics and
    identify potential issues like monotonous pacing or abrupt shifts.

    Why application layer:
        This service orchestrates analysis across multiple domain entities
        (scenes) and produces derived insights. It doesn't modify state,
        making it a pure query/analysis service.
    """

    # Threshold for detecting monotonous pacing (same level for N+ consecutive scenes)
    MONOTONY_THRESHOLD: int = 3

    # Threshold for spike detection (change greater than this is a spike)
    SPIKE_THRESHOLD: int = 4

    def calculate_chapter_pacing(
        self, chapter_id: UUID, scenes: list[Scene]
    ) -> Result[ChapterPacingReport, Error]:
        """
        Calculate pacing metrics for a chapter.

        Why Result pattern:
            Allows graceful handling of invalid input data while
            keeping the service pure and testable.

        Args:
            chapter_id: The chapter's unique identifier.
            scenes: List of scenes belonging to the chapter.

        Returns:
            Result with ChapterPacingReport on success, Error on validation failure

        Why scenes as parameter:
            Keeps the service stateless and independent of repositories.
            The caller (router/controller) handles data fetching.
        """
        if not scenes:
            # Empty scenes is not an error, just no pacing to report
            return Ok(
                ChapterPacingReport(
                    chapter_id=chapter_id,
                    scene_metrics=[],
                    issues=[],
                    average_tension=0.0,
                    average_energy=0.0,
                    tension_range=(0, 0),
                    energy_range=(0, 0),
                )
            )

        # Sort scenes by order_index for analysis
        sorted_scenes = sorted(scenes, key=lambda s: s.order_index)

        # Build metrics list
        scene_metrics = [
            ScenePacingMetrics(
                scene_id=scene.id,
                scene_title=scene.title,
                order_index=scene.order_index,
                tension_level=scene.tension_level,
                energy_level=scene.energy_level,
            )
            for scene in sorted_scenes
        ]

        # Calculate aggregates
        tensions = [s.tension_level for s in sorted_scenes]
        energies = [s.energy_level for s in sorted_scenes]

        avg_tension = sum(tensions) / len(tensions)
        avg_energy = sum(energies) / len(energies)
        tension_range = (min(tensions), max(tensions))
        energy_range = (min(energies), max(energies))

        # Analyze for issues
        issues = self.analyze_pacing_issues(sorted_scenes)

        return Ok(
            ChapterPacingReport(
                chapter_id=chapter_id,
                scene_metrics=scene_metrics,
                issues=issues,
                average_tension=round(avg_tension, 2),
                average_energy=round(avg_energy, 2),
                tension_range=tension_range,
                energy_range=energy_range,
            )
        )

    def analyze_pacing_issues(self, scenes: list[Scene]) -> list[PacingIssue]:
        """Detect pacing problems in a sequence of scenes.

        Identifies issues such as monotonous pacing (same level for too
        many consecutive scenes), abrupt spikes, and overall flat arcs.

        Args:
            scenes: List of scenes, assumed to be sorted by order_index.

        Returns:
            List of detected PacingIssue objects.

        Why separate method:
            Can be called independently for incremental analysis as
            scenes are modified.
        """
        if len(scenes) < 2:
            return []

        issues: list[PacingIssue] = []

        # Detect monotonous tension
        issues.extend(self._detect_monotony(scenes, "tension"))

        # Detect monotonous energy
        issues.extend(self._detect_monotony(scenes, "energy"))

        # Detect abrupt tension spikes
        issues.extend(self._detect_spikes(scenes, "tension"))

        # Detect abrupt energy spikes
        issues.extend(self._detect_spikes(scenes, "energy"))

        return issues

    def _detect_monotony(
        self, scenes: list[Scene], metric: str
    ) -> list[PacingIssue]:
        """Detect sequences with same pacing level for too long.

        Args:
            scenes: Sorted list of scenes.
            metric: Either 'tension' or 'energy'.

        Returns:
            List of monotony issues detected.

        Why monotony detection:
            Same tension or energy for 3+ consecutive scenes can bore
            readers or feel like the story isn't progressing.
        """
        issues: list[PacingIssue] = []

        consecutive_count = 1
        consecutive_start = 0

        for i in range(1, len(scenes)):
            current_level = getattr(scenes[i], f"{metric}_level")
            previous_level = getattr(scenes[i - 1], f"{metric}_level")

            if current_level == previous_level:
                consecutive_count += 1
            else:
                # Check if we had a monotonous streak
                if consecutive_count >= self.MONOTONY_THRESHOLD:
                    affected = [
                        scenes[j].id
                        for j in range(consecutive_start, i)
                    ]
                    level = getattr(scenes[consecutive_start], f"{metric}_level")
                    issues.append(
                        PacingIssue(
                            issue_type=f"monotonous_{metric}",
                            description=(
                                f"{consecutive_count} consecutive scenes have "
                                f"the same {metric} level ({level})"
                            ),
                            affected_scenes=affected,
                            severity="medium" if consecutive_count == 3 else "high",
                            suggestion=(
                                f"Consider varying {metric} levels to create "
                                f"narrative rhythm. Try raising or lowering "
                                f"one scene's {metric} to break the pattern."
                            ),
                        )
                    )
                # Reset streak
                consecutive_count = 1
                consecutive_start = i

        # Check final streak
        if consecutive_count >= self.MONOTONY_THRESHOLD:
            affected = [scenes[j].id for j in range(consecutive_start, len(scenes))]
            level = getattr(scenes[consecutive_start], f"{metric}_level")
            issues.append(
                PacingIssue(
                    issue_type=f"monotonous_{metric}",
                    description=(
                        f"{consecutive_count} consecutive scenes have "
                        f"the same {metric} level ({level})"
                    ),
                    affected_scenes=affected,
                    severity="medium" if consecutive_count == 3 else "high",
                    suggestion=(
                        f"Consider varying {metric} levels to create "
                        f"narrative rhythm. Try raising or lowering "
                        f"one scene's {metric} to break the pattern."
                    ),
                )
            )

        return issues

    def _detect_spikes(
        self, scenes: list[Scene], metric: str
    ) -> list[PacingIssue]:
        """Detect abrupt pacing changes between adjacent scenes.

        Args:
            scenes: Sorted list of scenes.
            metric: Either 'tension' or 'energy'.

        Returns:
            List of spike issues detected.

        Why spike detection:
            Large jumps in pacing (>4 levels) can feel jarring to readers
            unless intentional. Highlighting them helps authors decide
            if the shift is desired or needs smoothing.
        """
        issues: list[PacingIssue] = []

        for i in range(1, len(scenes)):
            current = getattr(scenes[i], f"{metric}_level")
            previous = getattr(scenes[i - 1], f"{metric}_level")
            delta = abs(current - previous)

            if delta > self.SPIKE_THRESHOLD:
                direction = "increase" if current > previous else "decrease"
                issues.append(
                    PacingIssue(
                        issue_type=f"{metric}_spike",
                        description=(
                            f"Abrupt {metric} {direction} from {previous} to "
                            f"{current} between '{scenes[i-1].title}' and "
                            f"'{scenes[i].title}'"
                        ),
                        affected_scenes=[scenes[i - 1].id, scenes[i].id],
                        severity="low" if delta == 5 else "medium",
                        suggestion=(
                            f"Consider adding a transitional scene or adjusting "
                            f"the {metric} levels to create a smoother arc, "
                            f"unless the sudden shift is intentional."
                        ),
                    )
                )

        return issues
