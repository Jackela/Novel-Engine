"""
Decision Point Detector

Analyzes turn results to detect narrative moments that warrant user intervention.
Uses configurable thresholds based on PlotPoint model attributes.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set

from .models import DecisionOption, DecisionPoint, DecisionPointType

logger = logging.getLogger(__name__)


# Decision point type mappings from PlotPointType
CRITICAL_PLOT_TYPES: Set[str] = {
    "climax",
    "turning_point",
    "crisis",
    "revelation",
    "transformation",
    "confrontation",
    "sacrifice",
}


class DecisionPointDetector:
    """
    Detects narrative decision points that should trigger user interaction.

    Detection is based on:
    1. Plot point types (climax, crisis, revelation, etc.)
    2. Dramatic tension and emotional intensity thresholds
    3. Character relationship changes
    4. Turn interval (for testing/demo purposes)
    """

    def __init__(
        self,
        tension_threshold: float = 7.0,
        intensity_threshold: float = 7.0,
        check_interval: int = 3,  # Check every N turns for demo
        always_detect_interval: Optional[int] = None,  # Force detect every N turns
    ) -> None:
        """
        Initialize the detector.

        Args:
            tension_threshold: Minimum dramatic_tension to trigger (0-10)
            intensity_threshold: Minimum emotional_intensity to trigger (0-10)
            check_interval: How often to analyze turns
            always_detect_interval: Force decision point every N turns (for testing)
        """
        self._tension_threshold = Decimal(str(tension_threshold))
        self._intensity_threshold = Decimal(str(intensity_threshold))
        self._check_interval = check_interval
        self._always_detect_interval = always_detect_interval

        # State
        self._turns_since_last_decision = 0
        self._decision_count = 0

    def analyze_turn(
        self,
        turn_number: int,
        turn_result: Dict[str, Any],
        narrative_context: str = "",
        characters: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[DecisionPoint]:
        """
        Analyze a turn result to determine if a decision point should be created.

        Args:
            turn_number: Current turn number
            turn_result: Result from director.run_turn()
            narrative_context: Recent story summary for context
            characters: List of character data for option generation

        Returns:
            DecisionPoint if one should be created, None otherwise
        """
        self._turns_since_last_decision += 1

        # Check for forced interval (testing/demo mode)
        if self._always_detect_interval:
            if self._turns_since_last_decision >= self._always_detect_interval:
                logger.info(
                    "Forced decision point at turn %d (interval: %d)",
                    turn_number,
                    self._always_detect_interval,
                )
                return self._create_decision_point(
                    turn_number=turn_number,
                    decision_type=DecisionPointType.TURNING_POINT,
                    title="Story Direction",
                    description="What should happen next in the story?",
                    narrative_context=narrative_context,
                    characters=characters,
                )

        # Skip analysis if not at check interval
        if self._turns_since_last_decision < self._check_interval:
            return None

        # Extract metrics from turn result
        decision_point = self._detect_from_turn_result(
            turn_number=turn_number,
            turn_result=turn_result,
            narrative_context=narrative_context,
            characters=characters,
        )

        if decision_point:
            self._turns_since_last_decision = 0
            self._decision_count += 1

        return decision_point

    def _detect_from_turn_result(
        self,
        turn_number: int,
        turn_result: Dict[str, Any],
        narrative_context: str,
        characters: Optional[List[Dict[str, Any]]],
    ) -> Optional[DecisionPoint]:
        """
        Analyze turn result for decision point conditions.

        Detection criteria (any of):
        - Plot point type is critical (climax, crisis, etc.)
        - Dramatic tension >= threshold
        - Emotional intensity >= threshold
        - Character relationships changed
        """
        # Try to extract plot point data
        plot_points = turn_result.get("plot_points", [])
        events = turn_result.get("events", [])

        # Check plot points
        for pp in plot_points:
            pp_type = pp.get("plot_point_type", pp.get("type", ""))
            if pp_type in CRITICAL_PLOT_TYPES:
                return self._create_from_plot_point(
                    turn_number=turn_number,
                    plot_point=pp,
                    narrative_context=narrative_context,
                    characters=characters,
                )

        # Check tension/intensity thresholds
        dramatic_tension = Decimal(str(turn_result.get("dramatic_tension", 5.0)))
        emotional_intensity = Decimal(str(turn_result.get("emotional_intensity", 5.0)))

        if dramatic_tension >= self._tension_threshold:
            return self._create_decision_point(
                turn_number=turn_number,
                decision_type=DecisionPointType.CRISIS,
                title="High Stakes Moment",
                description="The tension is mounting. How should the story proceed?",
                narrative_context=narrative_context,
                characters=characters,
                tension=dramatic_tension,
                intensity=emotional_intensity,
            )

        if emotional_intensity >= self._intensity_threshold:
            return self._create_decision_point(
                turn_number=turn_number,
                decision_type=DecisionPointType.CHARACTER_CHOICE,
                title="Emotional Crossroads",
                description="A deeply emotional moment. What should the characters do?",
                narrative_context=narrative_context,
                characters=characters,
                tension=dramatic_tension,
                intensity=emotional_intensity,
            )

        # Check for relationship changes in events
        for event in events:
            if event.get("changes_relationships", False):
                return self._create_decision_point(
                    turn_number=turn_number,
                    decision_type=DecisionPointType.RELATIONSHIP_CHANGE,
                    title="Relationship Turning Point",
                    description="Character relationships are about to change. Guide the outcome.",
                    narrative_context=narrative_context,
                    characters=characters,
                )

        return None

    def _create_from_plot_point(
        self,
        turn_number: int,
        plot_point: Dict[str, Any],
        narrative_context: str,
        characters: Optional[List[Dict[str, Any]]],
    ) -> DecisionPoint:
        """Create a decision point from a plot point."""
        pp_type = plot_point.get(
            "plot_point_type", plot_point.get("type", "turning_point")
        )

        # Map plot point type to decision point type
        type_mapping = {
            "climax": DecisionPointType.CLIMAX,
            "turning_point": DecisionPointType.TURNING_POINT,
            "crisis": DecisionPointType.CRISIS,
            "revelation": DecisionPointType.REVELATION,
            "transformation": DecisionPointType.TRANSFORMATION,
            "confrontation": DecisionPointType.CONFLICT_ESCALATION,
        }
        decision_type = type_mapping.get(pp_type, DecisionPointType.TURNING_POINT)

        return self._create_decision_point(
            turn_number=turn_number,
            decision_type=decision_type,
            title=plot_point.get("title", "Critical Moment"),
            description=plot_point.get("description", "A pivotal moment in the story."),
            narrative_context=narrative_context,
            characters=characters,
            tension=Decimal(str(plot_point.get("dramatic_tension", 7.0))),
            intensity=Decimal(str(plot_point.get("emotional_intensity", 7.0))),
        )

    def _create_decision_point(
        self,
        turn_number: int,
        decision_type: DecisionPointType,
        title: str,
        description: str,
        narrative_context: str,
        characters: Optional[List[Dict[str, Any]]],
        tension: Decimal = Decimal("7.0"),
        intensity: Decimal = Decimal("7.0"),
    ) -> DecisionPoint:
        """Create a decision point with generated options."""
        options = self._generate_options(decision_type, characters)

        return DecisionPoint(
            decision_type=decision_type,
            turn_number=turn_number,
            title=title,
            description=description,
            narrative_context=narrative_context,
            options=options,
            default_option_id=0 if options else None,
            dramatic_tension=tension,
            emotional_intensity=intensity,
        )

    def _generate_options(
        self,
        decision_type: DecisionPointType,
        characters: Optional[List[Dict[str, Any]]],
    ) -> List[DecisionOption]:
        """Generate contextual options based on decision type."""

        # Base options by decision type
        options_by_type: Dict[DecisionPointType, List[Dict[str, str]]] = {
            DecisionPointType.TURNING_POINT: [
                {
                    "label": "Investigate",
                    "description": "Look deeper into the situation",
                    "icon": "🔍",
                },
                {
                    "label": "Retreat",
                    "description": "Fall back and reassess",
                    "icon": "⬅️",
                },
                {
                    "label": "Confront",
                    "description": "Face the challenge head-on",
                    "icon": "⚔️",
                },
                {
                    "label": "Seek Help",
                    "description": "Call for assistance",
                    "icon": "📡",
                },
            ],
            DecisionPointType.CRISIS: [
                {
                    "label": "Bold Action",
                    "description": "Take decisive, risky action",
                    "icon": "🎯",
                },
                {
                    "label": "Defensive Stance",
                    "description": "Prioritize safety and defense",
                    "icon": "🛡️",
                },
                {
                    "label": "Strategic Retreat",
                    "description": "Withdraw to fight another day",
                    "icon": "🏃",
                },
                {
                    "label": "Negotiate",
                    "description": "Attempt to resolve through dialogue",
                    "icon": "🤝",
                },
            ],
            DecisionPointType.CLIMAX: [
                {
                    "label": "Ultimate Sacrifice",
                    "description": "Risk everything for victory",
                    "icon": "💫",
                },
                {
                    "label": "Unexpected Alliance",
                    "description": "Form a surprising partnership",
                    "icon": "🤝",
                },
                {
                    "label": "Reveal Truth",
                    "description": "Expose hidden information",
                    "icon": "💡",
                },
                {
                    "label": "Final Stand",
                    "description": "Make a last desperate effort",
                    "icon": "🔥",
                },
            ],
            DecisionPointType.REVELATION: [
                {
                    "label": "Accept Truth",
                    "description": "Embrace the new information",
                    "icon": "✅",
                },
                {
                    "label": "Deny It",
                    "description": "Refuse to believe what's revealed",
                    "icon": "❌",
                },
                {
                    "label": "Investigate More",
                    "description": "Seek additional confirmation",
                    "icon": "🔍",
                },
                {
                    "label": "Share Discovery",
                    "description": "Tell others what you've learned",
                    "icon": "📢",
                },
            ],
            DecisionPointType.CHARACTER_CHOICE: [
                {
                    "label": "Follow Heart",
                    "description": "Act on emotional impulse",
                    "icon": "❤️",
                },
                {
                    "label": "Use Logic",
                    "description": "Make a rational decision",
                    "icon": "🧠",
                },
                {
                    "label": "Consult Others",
                    "description": "Seek advice from companions",
                    "icon": "👥",
                },
                {
                    "label": "Wait and See",
                    "description": "Let events unfold naturally",
                    "icon": "⏳",
                },
            ],
            DecisionPointType.RELATIONSHIP_CHANGE: [
                {
                    "label": "Strengthen Bond",
                    "description": "Deepen the relationship",
                    "icon": "💪",
                },
                {
                    "label": "Create Distance",
                    "description": "Pull back emotionally",
                    "icon": "↔️",
                },
                {
                    "label": "Have Confrontation",
                    "description": "Address issues directly",
                    "icon": "💬",
                },
                {
                    "label": "Accept Change",
                    "description": "Let the relationship evolve",
                    "icon": "🌱",
                },
            ],
            DecisionPointType.CONFLICT_ESCALATION: [
                {
                    "label": "Escalate",
                    "description": "Intensify the conflict",
                    "icon": "📈",
                },
                {
                    "label": "De-escalate",
                    "description": "Try to calm things down",
                    "icon": "📉",
                },
                {
                    "label": "Switch Tactics",
                    "description": "Try a different approach",
                    "icon": "🔄",
                },
                {
                    "label": "Call Truce",
                    "description": "Propose a temporary ceasefire",
                    "icon": "🕊️",
                },
            ],
            DecisionPointType.TRANSFORMATION: [
                {
                    "label": "Embrace Change",
                    "description": "Fully accept the transformation",
                    "icon": "🦋",
                },
                {
                    "label": "Resist",
                    "description": "Fight against the change",
                    "icon": "⛔",
                },
                {
                    "label": "Adapt Gradually",
                    "description": "Take a measured approach",
                    "icon": "📊",
                },
                {
                    "label": "Seek Reversal",
                    "description": "Try to undo the change",
                    "icon": "⏪",
                },
            ],
        }

        base_options = options_by_type.get(
            decision_type,
            options_by_type[DecisionPointType.TURNING_POINT],
        )

        return [
            DecisionOption(
                option_id=i,
                label=opt["label"],
                description=opt["description"],
                icon=opt.get("icon", ""),
                impact_preview="This choice will influence the next turn's direction.",
            )
            for i, opt in enumerate(base_options)
        ]

    def reset(self) -> None:
        """Reset the detector state."""
        self._turns_since_last_decision = 0
        self._decision_count = 0

    @property
    def decision_count(self) -> int:
        """Get total number of decision points created."""
        return self._decision_count
