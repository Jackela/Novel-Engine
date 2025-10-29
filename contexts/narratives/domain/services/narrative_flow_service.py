#!/usr/bin/env python3
"""
Narrative Flow Domain Service

This module implements the NarrativeFlowService, which manages story flow,
sequence optimization, and narrative progression within story structures.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List

from ..aggregates.narrative_arc import NarrativeArc
from ..value_objects.plot_point import PlotPoint, PlotPointType
from ..value_objects.story_pacing import StoryPacing

logger = logging.getLogger(__name__)


@dataclass
class FlowAnalysis:
    """Results of narrative flow analysis."""

    pacing_score: Decimal
    tension_progression: List[Decimal]
    climax_positioning: Decimal  # How well positioned climaxes are
    resolution_quality: Decimal
    narrative_momentum: Decimal
    flow_consistency: Decimal
    recommended_adjustments: List[Dict[str, Any]]


@dataclass
class SequenceOptimization:
    """Results of sequence optimization analysis."""

    original_sequence: List[str]
    optimized_sequence: List[str]
    improvement_score: Decimal
    changes_made: List[Dict[str, Any]]
    rationale: str


class NarrativeFlowService:
    """
    Domain service for managing narrative flow and progression.

    Provides analysis and optimization of story pacing, sequence ordering,
    and overall narrative momentum.
    """

    def __init__(self):
        """Initialize the narrative flow service."""
        self._flow_cache: Dict[str, FlowAnalysis] = {}
        self._optimization_cache: Dict[str, SequenceOptimization] = {}

    def analyze_narrative_flow(self, narrative_arc: NarrativeArc) -> FlowAnalysis:
        """
        Analyze the overall narrative flow of a story arc.

        Args:
            narrative_arc: NarrativeArc to analyze

        Returns:
            FlowAnalysis with detailed flow metrics
        """
        arc_key = str(narrative_arc.arc_id)

        if arc_key in self._flow_cache:
            return self._flow_cache[arc_key]

        # Analyze different aspects of narrative flow
        pacing_score = self._analyze_pacing_quality(narrative_arc)
        tension_progression = self._calculate_tension_progression(narrative_arc)
        climax_positioning = self._evaluate_climax_positioning(narrative_arc)
        resolution_quality = self._assess_resolution_quality(narrative_arc)
        narrative_momentum = self._calculate_narrative_momentum(narrative_arc)
        flow_consistency = self._evaluate_flow_consistency(narrative_arc)
        recommended_adjustments = self._generate_flow_recommendations(narrative_arc)

        analysis = FlowAnalysis(
            pacing_score=pacing_score,
            tension_progression=tension_progression,
            climax_positioning=climax_positioning,
            resolution_quality=resolution_quality,
            narrative_momentum=narrative_momentum,
            flow_consistency=flow_consistency,
            recommended_adjustments=recommended_adjustments,
        )

        self._flow_cache[arc_key] = analysis
        return analysis

    def _analyze_pacing_quality(self, arc: NarrativeArc) -> Decimal:
        """Analyze the quality of pacing throughout the arc."""
        if not arc.pacing_segments:
            return Decimal("5.0")  # Neutral score for no pacing data

        pacing_scores = []
        total_coverage = 0

        for pacing in arc.pacing_segments.values():
            # Evaluate individual pacing segment quality
            segment_score = self._evaluate_pacing_segment(pacing)
            segment_length = pacing.segment_length

            pacing_scores.append((segment_score, segment_length))
            total_coverage += segment_length

        if not pacing_scores:
            return Decimal("5.0")

        # Calculate weighted average based on segment lengths
        weighted_score = (
            sum(score * Decimal(str(length)) for score, length in pacing_scores)
            / Decimal(str(total_coverage))
            if total_coverage > 0
            else Decimal("5.0")
        )

        # Bonus for good pacing variety
        pacing_types = {pacing.pacing_type for pacing in arc.pacing_segments.values()}
        variety_bonus = min(Decimal("1.0"), Decimal(str(len(pacing_types) * 0.2)))

        return min(Decimal("10.0"), weighted_score + variety_bonus)

    def _evaluate_pacing_segment(self, pacing: StoryPacing) -> Decimal:
        """Evaluate the quality of an individual pacing segment."""
        base_score = pacing.engagement_score

        # Adjust for appropriateness of pacing type and intensity
        intensity_appropriateness = self._assess_intensity_appropriateness(pacing)
        content_balance = self._assess_content_balance(pacing)

        segment_score = (
            base_score * Decimal("0.6")
            + intensity_appropriateness * Decimal("0.2")
            + content_balance * Decimal("0.2")
        )

        return min(Decimal("10.0"), segment_score)

    def _assess_intensity_appropriateness(self, pacing: StoryPacing) -> Decimal:
        """Assess if pacing intensity is appropriate for the segment type."""
        # High-intensity pacing should be used sparingly and strategically
        intensity_scores = {
            "glacial": Decimal("7.0"),  # Good for reflection
            "slow": Decimal("8.0"),  # Good for buildup
            "moderate": Decimal("9.0"),  # Most versatile
            "brisk": Decimal("8.5"),  # Good for action
            "fast": Decimal("7.5"),  # Should be limited
            "breakneck": Decimal("6.0"),  # Should be very limited
        }

        return intensity_scores.get(pacing.base_intensity.value, Decimal("7.0"))

    def _assess_content_balance(self, pacing: StoryPacing) -> Decimal:
        """Assess the balance of content types in pacing segment."""
        # Check if ratios sum to approximately 1.0
        total_ratio = (
            pacing.dialogue_ratio + pacing.action_ratio + pacing.reflection_ratio
        )
        balance_penalty = abs(total_ratio - Decimal("1.0")) * Decimal("5.0")

        # Assess appropriateness of content mix
        content_score = Decimal("8.0")

        # Penalize extreme imbalances
        if any(
            ratio > Decimal("0.8")
            for ratio in [
                pacing.dialogue_ratio,
                pacing.action_ratio,
                pacing.reflection_ratio,
            ]
        ):
            content_score -= Decimal("2.0")

        if any(
            ratio < Decimal("0.05")
            for ratio in [
                pacing.dialogue_ratio,
                pacing.action_ratio,
                pacing.reflection_ratio,
            ]
        ):
            content_score -= Decimal("1.0")

        return max(Decimal("1.0"), content_score - balance_penalty)

    def _calculate_tension_progression(self, arc: NarrativeArc) -> List[Decimal]:
        """Calculate tension levels throughout the narrative arc."""
        if not arc.plot_points:
            return [Decimal("5.0")]  # Neutral tension

        plot_points = arc.get_plot_points_in_sequence()
        tension_levels = []

        for plot_point in plot_points:
            # Base tension from plot point dramatic tension
            base_tension = plot_point.dramatic_tension

            # Adjust based on plot point type
            type_modifier = self._get_tension_modifier_for_plot_type(
                plot_point.plot_point_type
            )

            # Adjust based on importance
            importance_modifier = self._get_importance_modifier(plot_point.importance)

            tension_level = base_tension * type_modifier * importance_modifier
            tension_levels.append(min(Decimal("10.0"), tension_level))

        return tension_levels

    def _get_tension_modifier_for_plot_type(self, plot_type: PlotPointType) -> Decimal:
        """Get tension modifier based on plot point type."""
        tension_modifiers = {
            PlotPointType.INCITING_INCIDENT: Decimal("1.2"),
            PlotPointType.RISING_ACTION: Decimal("1.1"),
            PlotPointType.CLIMAX: Decimal("1.5"),
            PlotPointType.FALLING_ACTION: Decimal("0.8"),
            PlotPointType.RESOLUTION: Decimal("0.6"),
            PlotPointType.TURNING_POINT: Decimal("1.3"),
            PlotPointType.REVELATION: Decimal("1.4"),
            PlotPointType.CRISIS: Decimal("1.4"),
            PlotPointType.SETBACK: Decimal("1.2"),
            PlotPointType.TRIUMPH: Decimal("1.1"),
            PlotPointType.COMPLICATION: Decimal("1.2"),
            PlotPointType.DISCOVERY: Decimal("1.1"),
            PlotPointType.CONFRONTATION: Decimal("1.3"),
            PlotPointType.RECONCILIATION: Decimal("0.9"),
            PlotPointType.SACRIFICE: Decimal("1.3"),
            PlotPointType.TRANSFORMATION: Decimal("1.2"),
        }
        return tension_modifiers.get(plot_type, Decimal("1.0"))

    def _get_importance_modifier(self, importance) -> Decimal:
        """Get modifier based on plot point importance."""
        importance_modifiers = {
            "critical": Decimal("1.3"),
            "major": Decimal("1.2"),
            "moderate": Decimal("1.0"),
            "minor": Decimal("0.8"),
            "supplemental": Decimal("0.6"),
        }
        return importance_modifiers.get(importance.value, Decimal("1.0"))

    def _evaluate_climax_positioning(self, arc: NarrativeArc) -> Decimal:
        """Evaluate how well climaxes are positioned within the arc."""
        if not arc.plot_points:
            return Decimal("5.0")

        plot_points = arc.get_plot_points_in_sequence()
        total_points = len(plot_points)

        climax_positions = []
        for i, plot_point in enumerate(plot_points):
            if plot_point.plot_point_type == PlotPointType.CLIMAX:
                position_ratio = i / (total_points - 1) if total_points > 1 else 0.5
                climax_positions.append(position_ratio)

        if not climax_positions:
            return Decimal("7.0")  # No explicit climax, but not necessarily bad

        positioning_scores = []
        for pos in climax_positions:
            # Ideal climax position is around 70-80% through the story
            ideal_range_start = 0.65
            ideal_range_end = 0.85

            if ideal_range_start <= pos <= ideal_range_end:
                score = Decimal("10.0")
            elif 0.5 <= pos < ideal_range_start:
                # Slightly early
                distance = ideal_range_start - pos
                score = Decimal("10.0") - Decimal(str(distance * 10))
            elif ideal_range_end < pos <= 0.95:
                # Slightly late
                distance = pos - ideal_range_end
                score = Decimal("10.0") - Decimal(str(distance * 15))
            else:
                # Very poor positioning
                score = Decimal("3.0")

            positioning_scores.append(max(Decimal("1.0"), score))

        return sum(positioning_scores) / Decimal(str(len(positioning_scores)))

    def _assess_resolution_quality(self, arc: NarrativeArc) -> Decimal:
        """Assess the quality of story resolution."""
        if not arc.plot_points:
            return Decimal("5.0")

        plot_points = arc.get_plot_points_in_sequence()

        # Look for resolution-type plot points
        resolution_points = [
            pp
            for pp in plot_points
            if pp.plot_point_type
            in [PlotPointType.RESOLUTION, PlotPointType.FALLING_ACTION]
        ]

        if not resolution_points:
            return Decimal("4.0")  # Penalize lack of explicit resolution

        resolution_quality = Decimal("7.0")  # Base score

        # Check if resolution addresses major plot threads
        major_plot_points = [
            pp for pp in plot_points if pp.importance.value in ["critical", "major"]
        ]

        if major_plot_points:
            # Simple heuristic: resolution should come after major plot points
            last_major_sequence = max(pp.sequence_order for pp in major_plot_points)
            first_resolution_sequence = min(
                pp.sequence_order for pp in resolution_points
            )

            if first_resolution_sequence > last_major_sequence:
                resolution_quality += Decimal("2.0")
            else:
                resolution_quality -= Decimal("1.0")

        # Check for thematic resolution
        if arc.themes:
            themes_with_resolution = sum(
                1
                for theme in arc.themes.values()
                if theme.resolution_sequence is not None
            )
            theme_resolution_ratio = Decimal(str(themes_with_resolution)) / Decimal(
                str(len(arc.themes))
            )
            resolution_quality += theme_resolution_ratio * Decimal("1.5")

        return min(Decimal("10.0"), resolution_quality)

    def _calculate_narrative_momentum(self, arc: NarrativeArc) -> Decimal:
        """Calculate the overall narrative momentum of the arc."""
        if not arc.plot_points:
            return Decimal("5.0")

        plot_points = arc.get_plot_points_in_sequence()
        momentum_score = Decimal("5.0")

        # Momentum from plot point progression
        for i in range(1, len(plot_points)):
            prev_point = plot_points[i - 1]
            curr_point = plot_points[i]

            # Check for consequence relationships
            if any(prev_point.plot_point_id in curr_point.prerequisite_events):
                momentum_score += Decimal("0.5")

            # Check for escalating tension/stakes
            if curr_point.story_significance > prev_point.story_significance:
                momentum_score += Decimal("0.3")

        # Momentum from pacing consistency
        if arc.pacing_segments:
            pacing_consistency = self._calculate_pacing_momentum(arc.pacing_segments)
            momentum_score += pacing_consistency * Decimal("0.3")

        # Momentum from character involvement
        character_momentum = self._calculate_character_momentum(arc, plot_points)
        momentum_score += character_momentum * Decimal("0.2")

        return min(Decimal("10.0"), momentum_score)

    def _calculate_pacing_momentum(
        self, pacing_segments: Dict[str, StoryPacing]
    ) -> Decimal:
        """Calculate momentum from pacing progression."""
        if len(pacing_segments) < 2:
            return Decimal("5.0")

        # Sort segments by sequence
        sorted_segments = sorted(
            pacing_segments.values(), key=lambda p: p.start_sequence
        )

        momentum = Decimal("0")

        for i in range(1, len(sorted_segments)):
            prev_seg = sorted_segments[i - 1]
            curr_seg = sorted_segments[i]

            # Reward appropriate pacing transitions
            if self._is_good_pacing_transition(prev_seg, curr_seg):
                momentum += Decimal("1.0")

            # Penalize jarring transitions
            elif self._is_jarring_pacing_transition(prev_seg, curr_seg):
                momentum -= Decimal("0.5")

        return momentum

    def _is_good_pacing_transition(
        self, prev_seg: StoryPacing, curr_seg: StoryPacing
    ) -> bool:
        """Check if pacing transition is well-executed."""
        # Good transitions: buildup to climax, rest after intense action
        intensity_order = ["glacial", "slow", "moderate", "brisk", "fast", "breakneck"]

        prev_index = intensity_order.index(prev_seg.base_intensity.value)
        curr_index = intensity_order.index(curr_seg.base_intensity.value)

        # Gradual increase in intensity is good
        if curr_index == prev_index + 1:
            return True

        # Rest after high intensity is good
        if (
            prev_index >= 4 and curr_index <= 2
        ):  # fast/breakneck to glacial/slow/moderate
            return True

        return False

    def _is_jarring_pacing_transition(
        self, prev_seg: StoryPacing, curr_seg: StoryPacing
    ) -> bool:
        """Check if pacing transition is jarring."""
        intensity_order = ["glacial", "slow", "moderate", "brisk", "fast", "breakneck"]

        prev_index = intensity_order.index(prev_seg.base_intensity.value)
        curr_index = intensity_order.index(curr_seg.base_intensity.value)

        # Jumps of more than 2 levels are jarring
        return abs(curr_index - prev_index) > 2

    def _calculate_character_momentum(
        self, arc: NarrativeArc, plot_points: List[PlotPoint]
    ) -> Decimal:
        """Calculate momentum from character involvement patterns."""
        if not arc.primary_characters:
            return Decimal("5.0")

        character_appearances = {char_id: [] for char_id in arc.primary_characters}

        # Track character appearances in plot points
        for plot_point in plot_points:
            for char_id in plot_point.involved_characters:
                if char_id in character_appearances:
                    character_appearances[char_id].append(plot_point.sequence_order)

        # Calculate momentum based on character involvement consistency
        momentum = Decimal("0")
        for char_id, appearances in character_appearances.items():
            if len(appearances) >= 2:
                # Check for consistent involvement
                appearance_gaps = [
                    appearances[i] - appearances[i - 1]
                    for i in range(1, len(appearances))
                ]

                # Reward consistent involvement (similar gaps)
                if appearance_gaps:
                    avg_gap = sum(appearance_gaps) / len(appearance_gaps)
                    gap_variance = sum(
                        (gap - avg_gap) ** 2 for gap in appearance_gaps
                    ) / len(appearance_gaps)

                    if gap_variance < avg_gap * 0.5:  # Low variance = consistent
                        momentum += Decimal("1.0")

        return momentum

    def _evaluate_flow_consistency(self, arc: NarrativeArc) -> Decimal:
        """Evaluate overall flow consistency."""
        consistency_score = Decimal("7.0")  # Base consistency

        # Check plot point sequence consistency
        plot_consistency = self._check_plot_sequence_consistency(arc)
        consistency_score += plot_consistency * Decimal("0.3")

        # Check theme development consistency
        theme_consistency = self._check_theme_consistency(arc)
        consistency_score += theme_consistency * Decimal("0.2")

        # Check pacing consistency
        pacing_consistency = self._check_pacing_consistency(arc)
        consistency_score += pacing_consistency * Decimal("0.3")

        # Check character arc consistency
        character_consistency = self._check_character_consistency(arc)
        consistency_score += character_consistency * Decimal("0.2")

        return min(Decimal("10.0"), max(Decimal("1.0"), consistency_score))

    def _check_plot_sequence_consistency(self, arc: NarrativeArc) -> Decimal:
        """Check consistency of plot point sequencing."""
        if not arc.plot_points:
            return Decimal("0")

        plot_points = arc.get_plot_points_in_sequence()
        consistency_bonus = Decimal("0")

        # Check for prerequisite satisfaction
        for plot_point in plot_points:
            satisfied_prereqs = 0
            total_prereqs = len(plot_point.prerequisite_events)

            if total_prereqs > 0:
                for prereq in plot_point.prerequisite_events:
                    # Check if prerequisite appears before this plot point
                    for earlier_point in plot_points:
                        if (
                            earlier_point.sequence_order < plot_point.sequence_order
                            and earlier_point.plot_point_id == prereq
                        ):
                            satisfied_prereqs += 1
                            break

                satisfaction_ratio = satisfied_prereqs / total_prereqs
                consistency_bonus += Decimal(str(satisfaction_ratio))

        return consistency_bonus

    def _check_theme_consistency(self, arc: NarrativeArc) -> Decimal:
        """Check consistency of theme development."""
        if not arc.themes:
            return Decimal("0")

        consistency_bonus = Decimal("0")

        for theme_id, theme in arc.themes.items():
            development_sequences = arc.theme_development.get(theme_id, [])

            if theme.introduction_sequence is not None and development_sequences:
                # Check if theme development follows introduction
                intro_seq = theme.introduction_sequence
                valid_developments = [
                    seq for seq in development_sequences if seq >= intro_seq
                ]

                if len(valid_developments) == len(development_sequences):
                    consistency_bonus += Decimal("1.0")
                else:
                    ratio = len(valid_developments) / len(development_sequences)
                    consistency_bonus += Decimal(str(ratio))

        return consistency_bonus

    def _check_pacing_consistency(self, arc: NarrativeArc) -> Decimal:
        """Check pacing consistency throughout the arc."""
        if not arc.pacing_segments:
            return Decimal("0")

        # Check for gaps or overlaps in pacing coverage
        sorted_segments = sorted(
            arc.pacing_segments.values(), key=lambda p: p.start_sequence
        )

        consistency_bonus = Decimal("0")

        # Check for smooth transitions
        for i in range(1, len(sorted_segments)):
            prev_seg = sorted_segments[i - 1]
            curr_seg = sorted_segments[i]

            # Check for gaps
            if curr_seg.start_sequence > prev_seg.end_sequence + 1:
                consistency_bonus -= Decimal("0.5")  # Gap penalty
            elif curr_seg.start_sequence == prev_seg.end_sequence + 1:
                consistency_bonus += Decimal("0.5")  # Good continuity

        return consistency_bonus

    def _check_character_consistency(self, arc: NarrativeArc) -> Decimal:
        """Check character involvement consistency."""
        if not arc.primary_characters:
            return Decimal("0")

        consistency_bonus = Decimal("0")

        # Simple check: primary characters should appear in multiple plot points
        plot_points = arc.get_plot_points_in_sequence()

        for char_id in arc.primary_characters:
            appearances = sum(
                1 for pp in plot_points if char_id in pp.involved_characters
            )

            if len(plot_points) > 0:
                appearance_ratio = appearances / len(plot_points)
                if appearance_ratio >= 0.3:  # Appears in at least 30% of plot points
                    consistency_bonus += Decimal("0.5")

        return consistency_bonus

    def _generate_flow_recommendations(self, arc: NarrativeArc) -> List[Dict[str, Any]]:
        """Generate recommendations for improving narrative flow."""
        recommendations = []

        # Analyze tension progression
        tension_levels = self._calculate_tension_progression(arc)
        if tension_levels:
            # Check for tension valleys (significant drops)
            for i in range(1, len(tension_levels)):
                if tension_levels[i] < tension_levels[i - 1] - Decimal("3.0"):
                    recommendations.append(
                        {
                            "type": "tension_drop",
                            "position": i,
                            "severity": "moderate",
                            "suggestion": "Consider adding a complication or raising stakes to maintain tension",
                        }
                    )

        # Analyze climax positioning
        climax_score = self._evaluate_climax_positioning(arc)
        if climax_score < Decimal("6.0"):
            recommendations.append(
                {
                    "type": "climax_positioning",
                    "severity": "high",
                    "suggestion": "Consider repositioning climax to 70-80% through the story",
                }
            )

        # Analyze pacing
        pacing_score = self._analyze_pacing_quality(arc)
        if pacing_score < Decimal("6.0"):
            recommendations.append(
                {
                    "type": "pacing_improvement",
                    "severity": "moderate",
                    "suggestion": "Review pacing segments for better intensity variation and content balance",
                }
            )

        return recommendations

    def optimize_sequence_order(self, arc: NarrativeArc) -> SequenceOptimization:
        """
        Optimize the sequence order of plot points for better flow.

        Args:
            arc: NarrativeArc to optimize

        Returns:
            SequenceOptimization with recommended changes
        """
        if not arc.plot_points:
            return SequenceOptimization(
                original_sequence=[],
                optimized_sequence=[],
                improvement_score=Decimal("0"),
                changes_made=[],
                rationale="No plot points to optimize",
            )

        original_sequence = arc.plot_sequence.copy()
        optimized_sequence = self._calculate_optimal_sequence(arc)

        changes_made = self._identify_sequence_changes(
            original_sequence, optimized_sequence
        )
        improvement_score = self._calculate_improvement_score(
            arc, original_sequence, optimized_sequence
        )

        rationale = self._generate_optimization_rationale(
            changes_made, improvement_score
        )

        return SequenceOptimization(
            original_sequence=original_sequence,
            optimized_sequence=optimized_sequence,
            improvement_score=improvement_score,
            changes_made=changes_made,
            rationale=rationale,
        )

    def _calculate_optimal_sequence(self, arc: NarrativeArc) -> List[str]:
        """Calculate optimal sequence order for plot points."""
        plot_points = list(arc.plot_points.values())

        # Sort by sequence order first (preserve existing order as much as possible)
        plot_points.sort(key=lambda pp: pp.sequence_order)

        # Apply optimization rules
        optimized = []

        # Group by importance and type
        critical_points = [
            pp for pp in plot_points if pp.importance.value == "critical"
        ]
        major_points = [pp for pp in plot_points if pp.importance.value == "major"]
        [
            pp for pp in plot_points if pp.importance.value not in ["critical", "major"]
        ]

        # Ensure proper story structure
        # 1. Inciting incident should come early
        inciting_incidents = [
            pp
            for pp in critical_points + major_points
            if pp.plot_point_type == PlotPointType.INCITING_INCIDENT
        ]

        # 2. Climax should come late
        climaxes = [
            pp
            for pp in critical_points + major_points
            if pp.plot_point_type == PlotPointType.CLIMAX
        ]

        # 3. Resolution should come last
        resolutions = [
            pp for pp in plot_points if pp.plot_point_type == PlotPointType.RESOLUTION
        ]

        # Build optimized sequence
        remaining_points = [
            pp
            for pp in plot_points
            if pp not in inciting_incidents + climaxes + resolutions
        ]

        # Add inciting incidents first
        optimized.extend(inciting_incidents)

        # Add remaining points in groups
        remaining_points.sort(key=lambda pp: (pp.sequence_order, pp.importance.value))
        optimized.extend(remaining_points)

        # Add climaxes near the end
        optimized.extend(climaxes)

        # Add resolutions last
        optimized.extend(resolutions)

        return [pp.plot_point_id for pp in optimized]

    def _identify_sequence_changes(
        self, original: List[str], optimized: List[str]
    ) -> List[Dict[str, Any]]:
        """Identify what changes were made in sequence optimization."""
        changes = []

        for i, plot_id in enumerate(optimized):
            original_index = original.index(plot_id) if plot_id in original else -1
            if original_index != i:
                changes.append(
                    {
                        "plot_point_id": plot_id,
                        "original_position": original_index,
                        "new_position": i,
                        "direction": (
                            "moved_forward" if i < original_index else "moved_backward"
                        ),
                    }
                )

        return changes

    def _calculate_improvement_score(
        self, arc: NarrativeArc, original: List[str], optimized: List[str]
    ) -> Decimal:
        """Calculate the improvement score from sequence optimization."""
        if original == optimized:
            return Decimal("0")

        # Create temporary arc with optimized sequence to analyze
        # This is a simplified calculation - in practice, you'd want more sophisticated analysis
        improvement = Decimal("0")

        # Check if story structure rules are better satisfied
        if self._has_better_story_structure(arc, optimized):
            improvement += Decimal("3.0")

        # Check if prerequisite relationships are better satisfied
        if self._has_better_prerequisite_satisfaction(arc, optimized):
            improvement += Decimal("2.0")

        # Check if tension progression is improved
        if self._has_better_tension_progression(arc, optimized):
            improvement += Decimal("2.0")

        return improvement

    def _has_better_story_structure(
        self, arc: NarrativeArc, sequence: List[str]
    ) -> bool:
        """Check if optimized sequence has better story structure."""
        # Simple check: inciting incident early, climax late, resolution last
        if len(sequence) < 3:
            return False

        first_third = len(sequence) // 3
        last_third = (len(sequence) * 2) // 3

        for i, plot_id in enumerate(sequence):
            plot_point = arc.plot_points[plot_id]

            if (
                plot_point.plot_point_type == PlotPointType.INCITING_INCIDENT
                and i <= first_third
            ):
                return True
            elif plot_point.plot_point_type == PlotPointType.CLIMAX and i >= last_third:
                return True
            elif (
                plot_point.plot_point_type == PlotPointType.RESOLUTION
                and i >= last_third
            ):
                return True

        return False

    def _has_better_prerequisite_satisfaction(
        self, arc: NarrativeArc, sequence: List[str]
    ) -> bool:
        """Check if prerequisites are better satisfied in optimized sequence."""
        # Check if more prerequisites are satisfied
        satisfied_count = 0

        for i, plot_id in enumerate(sequence):
            plot_point = arc.plot_points[plot_id]

            for prereq in plot_point.prerequisite_events:
                # Check if prerequisite appears earlier in sequence
                try:
                    prereq_index = sequence.index(prereq)
                    if prereq_index < i:
                        satisfied_count += 1
                except ValueError:
                    continue

        # Compare with some baseline - for simplicity, assume improvement if any satisfied
        return satisfied_count > 0

    def _has_better_tension_progression(
        self, arc: NarrativeArc, sequence: List[str]
    ) -> bool:
        """Check if tension progression is improved."""
        # Simple heuristic: check if high-tension plot points are better distributed
        high_tension_positions = []

        for i, plot_id in enumerate(sequence):
            plot_point = arc.plot_points[plot_id]
            if plot_point.dramatic_tension >= Decimal("7.0"):
                high_tension_positions.append(i / len(sequence))

        # Good distribution has tension points spread throughout
        if len(high_tension_positions) >= 2:
            spread = max(high_tension_positions) - min(high_tension_positions)
            return spread >= 0.5  # Spread across at least half the story

        return False

    def _generate_optimization_rationale(
        self, changes: List[Dict[str, Any]], improvement_score: Decimal
    ) -> str:
        """Generate rationale for sequence optimization."""
        if not changes:
            return "No changes needed - sequence is already optimal"

        rationale_parts = []

        if improvement_score > Decimal("5.0"):
            rationale_parts.append(
                "Significant improvements to story structure and flow."
            )
        elif improvement_score > Decimal("2.0"):
            rationale_parts.append("Moderate improvements to narrative progression.")
        else:
            rationale_parts.append("Minor adjustments to optimize sequence flow.")

        if len(changes) == 1:
            rationale_parts.append(
                "One plot point repositioned for better narrative flow."
            )
        else:
            rationale_parts.append(
                f"{len(changes)} plot points repositioned for better narrative flow."
            )

        return " ".join(rationale_parts)
