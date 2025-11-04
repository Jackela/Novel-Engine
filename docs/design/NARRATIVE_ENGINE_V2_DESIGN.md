# Narrative Engine V2 - Architectural Design

## Executive Summary

The V2 Narrative Engine introduces advanced story arc management to significantly enhance the "novel feel" of generated content. Building upon the existing robust narrative infrastructure, V2 focuses on intelligent story progression, dynamic pacing control, and seamless integration with the DirectorAgent.

**Key Innovations:**
- **Story Arc State Machine**: Tracks narrative progression through classic story structure
- **Intelligent Arc Manager**: Plans and orchestrates story development across turns
- **Dynamic Pacing Manager**: Adjusts narrative rhythm in real-time
- **Narrative Planning Engine**: Generates turn-level narrative guidance
- **Enhanced DirectorAgent Integration**: Bidirectional communication for narrative-aware turn execution

---

## 1. Architecture Overview

### 1.1 System Context

```
┌─────────────────────────────────────────────────────────────┐
│                    DirectorAgent                             │
│  (Turn Orchestration & LLM Coordination)                    │
└────────────┬────────────────────────────────┬───────────────┘
             │                                │
             │ Requests Narrative Context     │ Reports Turn Results
             │                                │
             ▼                                ▼
┌─────────────────────────────────────────────────────────────┐
│              Narrative Engine V2 - Core Layer               │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │  Story Arc       │  │  Narrative       │               │
│  │  Manager         │  │  Planning        │               │
│  │                  │  │  Engine          │               │
│  └────────┬─────────┘  └────────┬─────────┘               │
│           │                     │                          │
│           │    ┌────────────────┴─────────┐               │
│           │    │                          │               │
│           ▼    ▼                          ▼               │
│  ┌──────────────────┐           ┌──────────────────┐     │
│  │  Pacing          │           │  Arc State       │     │
│  │  Manager         │           │  Machine         │     │
│  └──────────────────┘           └──────────────────┘     │
└────────────┬────────────────────────────────┬─────────────┘
             │                                │
             │ Uses                           │ Persists
             ▼                                ▼
┌─────────────────────────────────────────────────────────────┐
│         Existing Narrative Infrastructure                   │
│                                                             │
│  • NarrativeArc (Aggregate)    • NarrativeFlowService      │
│  • PlotPoint (Value Object)    • NarrativeOrchestrator     │
│  • NarrativeTheme (VO)         • Domain Events             │
│  • StoryPacing (VO)            • Repositories              │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Design Principles

1. **Build on Existing Infrastructure**: Leverage existing domain models and services
2. **Single Responsibility**: Each component has one clear purpose
3. **Event-Driven**: Use domain events for loose coupling
4. **Immutable Value Objects**: Maintain data integrity through immutability
5. **Progressive Enhancement**: V2 enhances V1 without breaking existing functionality
6. **Testability**: All components designed for easy unit and integration testing

---

## 2. Data Models

### 2.1 Story Arc Progression Models

#### 2.1.1 StoryArcPhase (Enum)

Represents the classic five-act story structure.

```python
from enum import Enum

class StoryArcPhase(Enum):
    """
    Classic narrative arc phases following the five-act structure.
    """
    EXPOSITION = "exposition"           # Setup: Characters, world, initial situation
    RISING_ACTION = "rising_action"     # Complications and escalating conflict
    CLIMAX = "climax"                   # Turning point and highest tension
    FALLING_ACTION = "falling_action"   # Consequences and resolution beginning
    RESOLUTION = "resolution"           # Conclusion and new equilibrium
    
    @property
    def typical_position_ratio(self) -> tuple[float, float]:
        """
        Get the typical position of this phase in a story (start%, end%).
        
        Returns:
            Tuple of (start_percentage, end_percentage)
        """
        phase_positions = {
            StoryArcPhase.EXPOSITION: (0.0, 0.15),
            StoryArcPhase.RISING_ACTION: (0.15, 0.70),
            StoryArcPhase.CLIMAX: (0.70, 0.80),
            StoryArcPhase.FALLING_ACTION: (0.80, 0.95),
            StoryArcPhase.RESOLUTION: (0.95, 1.0),
        }
        return phase_positions[self]
    
    @property
    def typical_tension_range(self) -> tuple[Decimal, Decimal]:
        """Get typical tension range for this phase (min, max on 0-10 scale)."""
        tension_ranges = {
            StoryArcPhase.EXPOSITION: (Decimal("2.0"), Decimal("4.0")),
            StoryArcPhase.RISING_ACTION: (Decimal("4.0"), Decimal("8.0")),
            StoryArcPhase.CLIMAX: (Decimal("8.0"), Decimal("10.0")),
            StoryArcPhase.FALLING_ACTION: (Decimal("5.0"), Decimal("7.0")),
            StoryArcPhase.RESOLUTION: (Decimal("2.0"), Decimal("4.0")),
        }
        return tension_ranges[self]
    
    @property
    def typical_pacing_intensity(self) -> str:
        """Get typical pacing intensity for this phase."""
        pacing_map = {
            StoryArcPhase.EXPOSITION: "moderate",
            StoryArcPhase.RISING_ACTION: "brisk",
            StoryArcPhase.CLIMAX: "fast",
            StoryArcPhase.FALLING_ACTION: "moderate",
            StoryArcPhase.RESOLUTION: "slow",
        }
        return pacing_map[self]
```

#### 2.1.2 StoryArcState (Value Object)

Represents the current state of story progression.

```python
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

@dataclass(frozen=True)
class StoryArcState:
    """
    Immutable snapshot of current story arc state.
    
    Tracks progression through the narrative arc, providing context
    for turn planning and pacing decisions.
    """
    
    # Current position
    current_phase: StoryArcPhase
    phase_progress: Decimal  # 0.0 to 1.0 within current phase
    overall_progress: Decimal  # 0.0 to 1.0 for entire story
    
    # Arc identification
    arc_id: str  # References NarrativeArc aggregate
    turn_number: int
    sequence_number: int
    
    # Progression metrics
    turns_in_current_phase: int
    estimated_turns_remaining_in_phase: Optional[int]
    estimated_total_turns: Optional[int]
    
    # Narrative state
    current_tension_level: Decimal  # 0-10 scale
    active_plot_thread_count: int
    unresolved_conflict_count: int
    primary_theme_focus: Optional[str]  # Theme ID
    
    # Phase transition
    ready_for_phase_transition: bool = False
    next_phase: Optional[StoryArcPhase] = None
    transition_requirements: list[str] = None  # What needs to happen before transition
    
    # Metadata
    state_timestamp: datetime = None
    previous_phase: Optional[StoryArcPhase] = None
    metadata: dict = None
    
    def __post_init__(self):
        """Initialize defaults and validate."""
        if self.state_timestamp is None:
            object.__setattr__(self, "state_timestamp", datetime.now(timezone.utc))
        
        if self.transition_requirements is None:
            object.__setattr__(self, "transition_requirements", [])
        
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})
        
        self._validate()
    
    def _validate(self):
        """Validate state constraints."""
        if not (Decimal("0") <= self.phase_progress <= Decimal("1")):
            raise ValueError("phase_progress must be between 0 and 1")
        
        if not (Decimal("0") <= self.overall_progress <= Decimal("1")):
            raise ValueError("overall_progress must be between 0 and 1")
        
        if not (Decimal("0") <= self.current_tension_level <= Decimal("10")):
            raise ValueError("current_tension_level must be between 0 and 10")
        
        if self.turn_number < 0 or self.sequence_number < 0:
            raise ValueError("turn and sequence numbers must be non-negative")
    
    @property
    def is_phase_complete(self) -> bool:
        """Check if current phase is complete and ready to transition."""
        return self.phase_progress >= Decimal("0.95") and self.ready_for_phase_transition
    
    @property
    def phase_position_description(self) -> str:
        """Get human-readable description of position in phase."""
        progress = float(self.phase_progress)
        
        if progress < 0.25:
            return "beginning"
        elif progress < 0.5:
            return "early"
        elif progress < 0.75:
            return "middle"
        elif progress < 0.95:
            return "late"
        else:
            return "concluding"
    
    def to_context_dict(self) -> dict:
        """Convert to context dictionary for DirectorAgent."""
        return {
            "current_phase": self.current_phase.value,
            "phase_position": self.phase_position_description,
            "phase_progress": float(self.phase_progress),
            "overall_progress": float(self.overall_progress),
            "turn_number": self.turn_number,
            "sequence_number": self.sequence_number,
            "current_tension": float(self.current_tension_level),
            "active_plot_threads": self.active_plot_thread_count,
            "unresolved_conflicts": self.unresolved_conflict_count,
            "approaching_transition": self.phase_progress > Decimal("0.8"),
            "ready_for_transition": self.ready_for_phase_transition,
        }
```

#### 2.1.3 NarrativeGuidance (Value Object)

Provides turn-level guidance for content generation.

```python
@dataclass(frozen=True)
class NarrativeGuidance:
    """
    Turn-level narrative guidance for the DirectorAgent.
    
    Provides specific recommendations for narrative elements to include
    in the current turn based on story arc position and goals.
    """
    
    # Identification
    guidance_id: str
    turn_number: int
    arc_state: StoryArcState
    
    # Primary objectives
    primary_narrative_goal: str  # e.g., "Escalate main conflict"
    secondary_narrative_goals: list[str]  # Supporting objectives
    
    # Plot and pacing
    suggested_plot_point_type: Optional[PlotPointType] = None
    target_tension_level: Decimal = Decimal("5.0")
    recommended_pacing_intensity: str = "moderate"
    
    # Content guidance
    themes_to_emphasize: list[str] = None  # Theme IDs
    character_development_focus: list[str] = None  # Character IDs
    suggested_setting_type: Optional[str] = None  # e.g., "intimate", "expansive"
    
    # Style and tone
    narrative_tone: str = "balanced"  # e.g., "dark", "hopeful", "tense"
    dialogue_ratio: Decimal = Decimal("0.3")  # Recommended dialogue proportion
    action_ratio: Decimal = Decimal("0.4")  # Recommended action proportion
    reflection_ratio: Decimal = Decimal("0.3")  # Recommended reflection proportion
    
    # Constraints and requirements
    must_include_elements: list[str] = None  # Required narrative elements
    should_avoid_elements: list[str] = None  # Elements to avoid
    
    # Opportunities
    narrative_opportunities: list[dict] = None  # Specific opportunities to explore
    
    # Phase transition
    is_transition_turn: bool = False
    transition_guidance: Optional[str] = None
    
    # Metadata
    created_timestamp: datetime = None
    metadata: dict = None
    
    def __post_init__(self):
        """Initialize defaults."""
        if self.themes_to_emphasize is None:
            object.__setattr__(self, "themes_to_emphasize", [])
        
        if self.character_development_focus is None:
            object.__setattr__(self, "character_development_focus", [])
        
        if self.must_include_elements is None:
            object.__setattr__(self, "must_include_elements", [])
        
        if self.should_avoid_elements is None:
            object.__setattr__(self, "should_avoid_elements", [])
        
        if self.narrative_opportunities is None:
            object.__setattr__(self, "narrative_opportunities", [])
        
        if self.created_timestamp is None:
            object.__setattr__(self, "created_timestamp", datetime.now(timezone.utc))
        
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})
    
    def to_director_context(self) -> dict:
        """Convert to context for DirectorAgent's LLM prompt."""
        return {
            "narrative_goal": self.primary_narrative_goal,
            "secondary_goals": self.secondary_narrative_goals,
            "target_tension": float(self.target_tension_level),
            "pacing": self.recommended_pacing_intensity,
            "tone": self.narrative_tone,
            "content_mix": {
                "dialogue": float(self.dialogue_ratio),
                "action": float(self.action_ratio),
                "reflection": float(self.reflection_ratio),
            },
            "themes_focus": self.themes_to_emphasize,
            "character_focus": self.character_development_focus,
            "required_elements": self.must_include_elements,
            "avoid_elements": self.should_avoid_elements,
            "opportunities": self.narrative_opportunities,
            "is_transition": self.is_transition_turn,
            "transition_note": self.transition_guidance,
        }
```

### 2.2 Pacing Control Models

#### 2.2.1 PacingAdjustment (Value Object)

Represents a real-time pacing adjustment.

```python
@dataclass(frozen=True)
class PacingAdjustment:
    """
    Represents a dynamic pacing adjustment for a turn or sequence.
    
    Unlike StoryPacing which defines pacing for segments, PacingAdjustment
    provides real-time adjustments based on current narrative needs.
    """
    
    adjustment_id: str
    turn_number: int
    
    # Intensity adjustments
    intensity_modifier: Decimal  # -3.0 to +3.0 adjustment to base intensity
    tension_target: Decimal  # 0-10 target tension level
    
    # Content adjustments
    dialogue_adjustment: Decimal = Decimal("0")  # -0.3 to +0.3
    action_adjustment: Decimal = Decimal("0")  # -0.3 to +0.3
    reflection_adjustment: Decimal = Decimal("0")  # -0.3 to +0.3
    
    # Temporal adjustments
    scene_break_recommended: bool = False
    time_jump_recommended: bool = False
    
    # Reason
    adjustment_reason: str = ""
    triggered_by: str = ""  # e.g., "phase_transition", "tension_management"
    
    # Metadata
    created_timestamp: datetime = None
    metadata: dict = None
    
    def __post_init__(self):
        """Initialize and validate."""
        if self.created_timestamp is None:
            object.__setattr__(self, "created_timestamp", datetime.now(timezone.utc))
        
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})
        
        self._validate()
    
    def _validate(self):
        """Validate constraints."""
        if not (Decimal("-3") <= self.intensity_modifier <= Decimal("3")):
            raise ValueError("intensity_modifier must be between -3 and 3")
        
        if not (Decimal("0") <= self.tension_target <= Decimal("10")):
            raise ValueError("tension_target must be between 0 and 10")
        
        for adj_name, adj_value in [
            ("dialogue_adjustment", self.dialogue_adjustment),
            ("action_adjustment", self.action_adjustment),
            ("reflection_adjustment", self.reflection_adjustment),
        ]:
            if not (Decimal("-0.3") <= adj_value <= Decimal("0.3")):
                raise ValueError(f"{adj_name} must be between -0.3 and 0.3")
```

---

## 3. Core Components

### 3.1 StoryArcManager

**Purpose**: Central coordinator for story arc progression and state management.

**Responsibilities**:
- Track current position in story arc
- Manage phase transitions
- Calculate progression metrics
- Coordinate with NarrativeArc aggregate
- Emit arc progression events

**Key Methods**:

```python
class StoryArcManager:
    """
    Manages story arc progression and state tracking.
    
    Coordinates between the high-level story structure (phases) and
    the detailed narrative elements (plot points, themes, pacing).
    """
    
    def __init__(
        self,
        arc_repository: NarrativeArcRepository,
        event_publisher: EventPublisher,
        logger: Optional[logging.Logger] = None
    ):
        self._arc_repo = arc_repository
        self._event_publisher = event_publisher
        self.logger = logger or logging.getLogger(__name__)
        
        # State tracking
        self._current_state: Optional[StoryArcState] = None
        self._phase_history: list[tuple[StoryArcPhase, int]] = []  # (phase, turn_entered)
    
    async def initialize_arc(
        self,
        arc_id: str,
        estimated_total_turns: Optional[int] = None
    ) -> StoryArcState:
        """
        Initialize a new story arc tracking.
        
        Args:
            arc_id: ID of the NarrativeArc aggregate to track
            estimated_total_turns: Optional estimate of total turns
            
        Returns:
            Initial StoryArcState
        """
        arc = await self._arc_repo.get_by_id(arc_id)
        
        if not arc:
            raise ValueError(f"NarrativeArc {arc_id} not found")
        
        # Create initial state
        initial_state = StoryArcState(
            current_phase=StoryArcPhase.EXPOSITION,
            phase_progress=Decimal("0.0"),
            overall_progress=Decimal("0.0"),
            arc_id=arc_id,
            turn_number=0,
            sequence_number=0,
            turns_in_current_phase=0,
            estimated_turns_remaining_in_phase=self._estimate_phase_turns(
                StoryArcPhase.EXPOSITION, estimated_total_turns
            ),
            estimated_total_turns=estimated_total_turns,
            current_tension_level=Decimal("3.0"),
            active_plot_thread_count=0,
            unresolved_conflict_count=0,
            primary_theme_focus=None,
        )
        
        self._current_state = initial_state
        self._phase_history.append((StoryArcPhase.EXPOSITION, 0))
        
        # Emit initialization event
        await self._event_publisher.publish(
            ArcInitialized(
                arc_id=arc_id,
                initial_phase=StoryArcPhase.EXPOSITION,
                timestamp=datetime.now(timezone.utc)
            )
        )
        
        return initial_state
    
    async def advance_turn(
        self,
        turn_result: dict
    ) -> StoryArcState:
        """
        Advance the story arc by one turn.
        
        Args:
            turn_result: Results from the completed turn
            
        Returns:
            Updated StoryArcState
        """
        if not self._current_state:
            raise RuntimeError("Arc not initialized")
        
        # Calculate new progression
        new_turn_number = self._current_state.turn_number + 1
        turns_in_phase = self._current_state.turns_in_current_phase + 1
        
        # Update phase progress
        phase_progress = self._calculate_phase_progress(
            self._current_state.current_phase,
            turns_in_phase,
            self._current_state.estimated_turns_remaining_in_phase
        )
        
        # Calculate overall progress
        overall_progress = self._calculate_overall_progress(
            self._current_state.current_phase,
            phase_progress,
            new_turn_number,
            self._current_state.estimated_total_turns
        )
        
        # Analyze turn results for narrative metrics
        tension_level = await self._calculate_tension_from_turn(turn_result)
        plot_thread_count = await self._count_active_plot_threads()
        conflict_count = await self._count_unresolved_conflicts()
        
        # Check if phase transition is needed
        transition_check = await self._check_phase_transition(
            self._current_state.current_phase,
            phase_progress,
            turn_result
        )
        
        # Create new state
        new_state = StoryArcState(
            current_phase=transition_check.get("new_phase", self._current_state.current_phase),
            phase_progress=transition_check.get("new_progress", phase_progress),
            overall_progress=overall_progress,
            arc_id=self._current_state.arc_id,
            turn_number=new_turn_number,
            sequence_number=self._current_state.sequence_number + 1,
            turns_in_current_phase=transition_check.get("turns_in_phase", turns_in_phase),
            estimated_turns_remaining_in_phase=transition_check.get("estimated_remaining"),
            estimated_total_turns=self._current_state.estimated_total_turns,
            current_tension_level=tension_level,
            active_plot_thread_count=plot_thread_count,
            unresolved_conflict_count=conflict_count,
            primary_theme_focus=await self._identify_primary_theme(),
            ready_for_phase_transition=transition_check.get("ready", False),
            next_phase=transition_check.get("next_phase"),
            transition_requirements=transition_check.get("requirements", []),
            previous_phase=self._current_state.current_phase if transition_check.get("transitioned") else None,
        )
        
        # Update internal state
        old_state = self._current_state
        self._current_state = new_state
        
        # Track phase changes
        if transition_check.get("transitioned"):
            self._phase_history.append((new_state.current_phase, new_turn_number))
            
            await self._event_publisher.publish(
                PhaseTransitioned(
                    arc_id=self._current_state.arc_id,
                    from_phase=old_state.current_phase,
                    to_phase=new_state.current_phase,
                    turn_number=new_turn_number,
                    timestamp=datetime.now(timezone.utc)
                )
            )
        
        return new_state
    
    async def get_current_state(self) -> Optional[StoryArcState]:
        """Get the current story arc state."""
        return self._current_state
    
    async def suggest_phase_transition(
        self,
        target_phase: StoryArcPhase,
        reason: str
    ) -> bool:
        """
        Suggest a manual phase transition.
        
        Args:
            target_phase: Desired phase to transition to
            reason: Reason for the transition
            
        Returns:
            True if transition is viable
        """
        if not self._current_state:
            return False
        
        # Validate transition sequence
        if not self._is_valid_transition(
            self._current_state.current_phase,
            target_phase
        ):
            self.logger.warning(
                f"Invalid phase transition: {self._current_state.current_phase} -> {target_phase}"
            )
            return False
        
        # Check if arc is ready
        arc = await self._arc_repo.get_by_id(self._current_state.arc_id)
        transition_readiness = await self._evaluate_transition_readiness(
            arc,
            target_phase
        )
        
        if transition_readiness.is_ready:
            self.logger.info(
                f"Phase transition approved: {target_phase.value}. Reason: {reason}"
            )
            return True
        else:
            self.logger.info(
                f"Phase transition not ready. Missing: {transition_readiness.missing_requirements}"
            )
            return False
    
    # Private helper methods
    
    def _calculate_phase_progress(
        self,
        phase: StoryArcPhase,
        turns_in_phase: int,
        estimated_remaining: Optional[int]
    ) -> Decimal:
        """Calculate progress within current phase."""
        if estimated_remaining is None:
            # Use fixed progression rate
            return min(Decimal("1.0"), Decimal(str(turns_in_phase * 0.05)))
        
        total_estimated = turns_in_phase + estimated_remaining
        return Decimal(str(turns_in_phase)) / Decimal(str(total_estimated))
    
    def _calculate_overall_progress(
        self,
        current_phase: StoryArcPhase,
        phase_progress: Decimal,
        turn_number: int,
        estimated_total: Optional[int]
    ) -> Decimal:
        """Calculate overall story progress."""
        if estimated_total and estimated_total > 0:
            return min(Decimal("1.0"), Decimal(str(turn_number)) / Decimal(str(estimated_total)))
        
        # Use phase-based estimation
        phase_start, phase_end = current_phase.typical_position_ratio
        phase_contribution = Decimal(str(phase_end - phase_start)) * phase_progress
        base_position = Decimal(str(phase_start))
        
        return min(Decimal("1.0"), base_position + phase_contribution)
    
    def _estimate_phase_turns(
        self,
        phase: StoryArcPhase,
        total_turns: Optional[int]
    ) -> Optional[int]:
        """Estimate turns for a phase."""
        if not total_turns:
            return None
        
        phase_start, phase_end = phase.typical_position_ratio
        phase_portion = phase_end - phase_start
        return int(total_turns * phase_portion)
    
    async def _calculate_tension_from_turn(self, turn_result: dict) -> Decimal:
        """Analyze turn result to determine current tension level."""
        # Extract tension indicators from turn result
        # This would analyze: conflicts introduced, stakes raised, revelations, etc.
        base_tension = Decimal(str(turn_result.get("tension_score", 5.0)))
        
        # Adjust based on phase expectations
        expected_min, expected_max = self._current_state.current_phase.typical_tension_range
        
        # Clamp to expected range with some flexibility
        return max(expected_min - Decimal("1"), min(expected_max + Decimal("1"), base_tension))
    
    async def _count_active_plot_threads(self) -> int:
        """Count currently active plot threads."""
        arc = await self._arc_repo.get_by_id(self._current_state.arc_id)
        
        # Count unresolved plot points and active threads
        active_count = 0
        for plot_point in arc.plot_points.values():
            if plot_point.has_consequences and not all(
                c in arc.plot_points for c in plot_point.triggered_consequences
            ):
                active_count += 1
        
        return active_count
    
    async def _count_unresolved_conflicts(self) -> int:
        """Count unresolved conflicts."""
        arc = await self._arc_repo.get_by_id(self._current_state.arc_id)
        
        # Count conflict-type plot points without resolution
        conflict_types = {PlotPointType.CRISIS, PlotPointType.CONFRONTATION, PlotPointType.COMPLICATION}
        
        unresolved = 0
        for plot_point in arc.plot_points.values():
            if plot_point.plot_point_type in conflict_types:
                # Check if there's a resolution plot point referencing this
                has_resolution = any(
                    pp.plot_point_type in {PlotPointType.RESOLUTION, PlotPointType.RECONCILIATION}
                    and plot_point.plot_point_id in pp.prerequisite_events
                    for pp in arc.plot_points.values()
                )
                
                if not has_resolution:
                    unresolved += 1
        
        return unresolved
    
    async def _identify_primary_theme(self) -> Optional[str]:
        """Identify the primary theme for current focus."""
        arc = await self._arc_repo.get_by_id(self._current_state.arc_id)
        
        # Find most prominent active theme
        active_themes = arc.get_themes_at_sequence(self._current_state.sequence_number)
        
        if not active_themes:
            return None
        
        # Sort by intensity and impact
        sorted_themes = sorted(
            active_themes,
            key=lambda t: (t.intensity.value, float(t.narrative_impact_score)),
            reverse=True
        )
        
        return sorted_themes[0].theme_id if sorted_themes else None
    
    async def _check_phase_transition(
        self,
        current_phase: StoryArcPhase,
        phase_progress: Decimal,
        turn_result: dict
    ) -> dict:
        """Check if phase transition should occur."""
        result = {
            "transitioned": False,
            "ready": False,
            "new_phase": current_phase,
            "new_progress": phase_progress,
            "turns_in_phase": self._current_state.turns_in_current_phase + 1,
        }
        
        # Don't transition unless substantial progress
        if phase_progress < Decimal("0.8"):
            return result
        
        # Get next phase
        next_phase = self._get_next_phase(current_phase)
        if not next_phase:
            # Already at end
            return result
        
        # Check transition requirements
        arc = await self._arc_repo.get_by_id(self._current_state.arc_id)
        readiness = await self._evaluate_transition_readiness(arc, next_phase)
        
        result["ready"] = readiness.is_ready
        result["next_phase"] = next_phase
        result["requirements"] = readiness.missing_requirements
        
        # Auto-transition if ready and progress > 95%
        if readiness.is_ready and phase_progress >= Decimal("0.95"):
            result["transitioned"] = True
            result["new_phase"] = next_phase
            result["new_progress"] = Decimal("0.0")
            result["turns_in_phase"] = 0
            result["estimated_remaining"] = self._estimate_phase_turns(
                next_phase,
                self._current_state.estimated_total_turns
            )
        
        return result
    
    def _get_next_phase(self, current: StoryArcPhase) -> Optional[StoryArcPhase]:
        """Get the next phase in sequence."""
        phase_order = [
            StoryArcPhase.EXPOSITION,
            StoryArcPhase.RISING_ACTION,
            StoryArcPhase.CLIMAX,
            StoryArcPhase.FALLING_ACTION,
            StoryArcPhase.RESOLUTION,
        ]
        
        try:
            current_index = phase_order.index(current)
            if current_index < len(phase_order) - 1:
                return phase_order[current_index + 1]
        except ValueError:
            pass
        
        return None
    
    def _is_valid_transition(
        self,
        from_phase: StoryArcPhase,
        to_phase: StoryArcPhase
    ) -> bool:
        """Check if phase transition is valid."""
        phase_order = [
            StoryArcPhase.EXPOSITION,
            StoryArcPhase.RISING_ACTION,
            StoryArcPhase.CLIMAX,
            StoryArcPhase.FALLING_ACTION,
            StoryArcPhase.RESOLUTION,
        ]
        
        try:
            from_index = phase_order.index(from_phase)
            to_index = phase_order.index(to_phase)
            
            # Can only move forward one phase at a time
            return to_index == from_index + 1
        except ValueError:
            return False
    
    async def _evaluate_transition_readiness(
        self,
        arc: NarrativeArc,
        target_phase: StoryArcPhase
    ) -> 'TransitionReadiness':
        """Evaluate if arc is ready for phase transition."""
        missing = []
        
        # Phase-specific requirements
        if target_phase == StoryArcPhase.RISING_ACTION:
            # Need inciting incident
            has_inciting = any(
                pp.plot_point_type == PlotPointType.INCITING_INCIDENT
                for pp in arc.plot_points.values()
            )
            if not has_inciting:
                missing.append("inciting_incident_plot_point")
        
        elif target_phase == StoryArcPhase.CLIMAX:
            # Need sufficient rising action and conflict
            if self._current_state.unresolved_conflict_count < 1:
                missing.append("unresolved_conflicts")
            
            if self._current_state.active_plot_thread_count < 2:
                missing.append("active_plot_threads")
        
        elif target_phase == StoryArcPhase.FALLING_ACTION:
            # Need climax plot point
            has_climax = any(
                pp.plot_point_type == PlotPointType.CLIMAX
                for pp in arc.plot_points.values()
            )
            if not has_climax:
                missing.append("climax_plot_point")
        
        elif target_phase == StoryArcPhase.RESOLUTION:
            # Need to resolve most conflicts
            if self._current_state.unresolved_conflict_count > 1:
                missing.append("resolve_remaining_conflicts")
        
        return TransitionReadiness(
            is_ready=len(missing) == 0,
            missing_requirements=missing,
            target_phase=target_phase
        )


@dataclass
class TransitionReadiness:
    """Result of phase transition readiness evaluation."""
    is_ready: bool
    missing_requirements: list[str]
    target_phase: StoryArcPhase
```

### 3.2 NarrativePlanningEngine

**Purpose**: Generate turn-level narrative guidance based on arc state.

**Responsibilities**:
- Analyze current arc state
- Generate narrative objectives for turns
- Provide content recommendations
- Identify narrative opportunities

**Key Methods**:

```python
class NarrativePlanningEngine:
    """
    Generates narrative guidance for turn execution.
    
    Analyzes story arc state and narrative structure to provide
    intelligent recommendations for content generation.
    """
    
    def __init__(
        self,
        arc_repository: NarrativeArcRepository,
        flow_service: NarrativeFlowService,
        logger: Optional[logging.Logger] = None
    ):
        self._arc_repo = arc_repository
        self._flow_service = flow_service
        self.logger = logger or logging.getLogger(__name__)
    
    async def generate_turn_guidance(
        self,
        arc_state: StoryArcState,
        context: dict
    ) -> NarrativeGuidance:
        """
        Generate narrative guidance for the upcoming turn.
        
        Args:
            arc_state: Current story arc state
            context: Additional context (character states, world state, etc.)
            
        Returns:
            NarrativeGuidance for the turn
        """
        arc = await self._arc_repo.get_by_id(arc_state.arc_id)
        
        # Determine primary narrative goal
        primary_goal = await self._determine_primary_goal(arc_state, arc)
        
        # Generate secondary goals
        secondary_goals = await self._generate_secondary_goals(arc_state, arc, context)
        
        # Recommend plot point type if appropriate
        plot_point_type = await self._recommend_plot_point_type(arc_state, arc)
        
        # Calculate target tension
        target_tension = await self._calculate_target_tension(arc_state, arc)
        
        # Get pacing recommendation
        pacing_intensity = await self._recommend_pacing_intensity(arc_state, arc)
        
        # Identify themes to emphasize
        themes = await self._identify_theme_focus(arc_state, arc)
        
        # Determine character development focus
        characters = await self._identify_character_focus(arc_state, arc, context)
        
        # Calculate content ratios
        dialogue, action, reflection = await self._calculate_content_ratios(arc_state, arc)
        
        # Determine tone
        tone = await self._determine_narrative_tone(arc_state, arc)
        
        # Identify must-include elements
        must_include = await self._identify_required_elements(arc_state, arc)
        
        # Identify elements to avoid
        should_avoid = await self._identify_elements_to_avoid(arc_state, arc)
        
        # Find narrative opportunities
        opportunities = await self._identify_narrative_opportunities(arc_state, arc, context)
        
        # Check for phase transition
        is_transition = arc_state.ready_for_phase_transition
        transition_guidance = None
        if is_transition:
            transition_guidance = await self._generate_transition_guidance(arc_state)
        
        # Build guidance
        guidance = NarrativeGuidance(
            guidance_id=f"guidance_{arc_state.turn_number}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            turn_number=arc_state.turn_number,
            arc_state=arc_state,
            primary_narrative_goal=primary_goal,
            secondary_narrative_goals=secondary_goals,
            suggested_plot_point_type=plot_point_type,
            target_tension_level=target_tension,
            recommended_pacing_intensity=pacing_intensity,
            themes_to_emphasize=themes,
            character_development_focus=characters,
            narrative_tone=tone,
            dialogue_ratio=dialogue,
            action_ratio=action,
            reflection_ratio=reflection,
            must_include_elements=must_include,
            should_avoid_elements=should_avoid,
            narrative_opportunities=opportunities,
            is_transition_turn=is_transition,
            transition_guidance=transition_guidance,
        )
        
        return guidance
    
    async def _determine_primary_goal(
        self,
        arc_state: StoryArcState,
        arc: NarrativeArc
    ) -> str:
        """Determine the primary narrative goal for the turn."""
        phase = arc_state.current_phase
        progress = float(arc_state.phase_progress)
        
        # Phase-specific goal templates
        if phase == StoryArcPhase.EXPOSITION:
            if progress < 0.3:
                return "Introduce core characters and establish world"
            elif progress < 0.7:
                return "Develop character motivations and hint at conflicts"
            else:
                return "Set up the inciting incident"
        
        elif phase == StoryArcPhase.RISING_ACTION:
            if progress < 0.3:
                return "Escalate initial conflict and introduce complications"
            elif progress < 0.6:
                return "Deepen stakes and develop subplots"
            else:
                return "Build toward climactic confrontation"
        
        elif phase == StoryArcPhase.CLIMAX:
            return "Deliver on narrative promises and resolve main conflict"
        
        elif phase == StoryArcPhase.FALLING_ACTION:
            if progress < 0.5:
                return "Show immediate consequences of climax"
            else:
                return "Resolve remaining plot threads"
        
        elif phase == StoryArcPhase.RESOLUTION:
            if progress < 0.5:
                return "Establish new equilibrium"
            else:
                return "Provide satisfying conclusion and closure"
        
        return "Advance the narrative"
    
    async def _generate_secondary_goals(
        self,
        arc_state: StoryArcState,
        arc: NarrativeArc,
        context: dict
    ) -> list[str]:
        """Generate secondary narrative goals."""
        goals = []
        
        # Character development
        if arc.primary_characters:
            goals.append("Develop character relationships and dynamics")
        
        # Theme development
        active_themes = arc.get_themes_at_sequence(arc_state.sequence_number)
        if active_themes:
            major_themes = [t for t in active_themes if t.is_major_theme]
            if major_themes:
                goals.append(f"Explore theme: {major_themes[0].name}")
        
        # Pacing variety
        if arc_state.turns_in_current_phase > 3:
            goals.append("Vary narrative rhythm and pacing")
        
        # Conflict management
        if arc_state.unresolved_conflict_count > 2:
            goals.append("Progress or resolve at least one active conflict")
        
        return goals[:3]  # Limit to 3 secondary goals
    
    async def _recommend_plot_point_type(
        self,
        arc_state: StoryArcState,
        arc: NarrativeArc
    ) -> Optional[PlotPointType]:
        """Recommend a plot point type if a major moment should occur."""
        phase = arc_state.current_phase
        progress = float(arc_state.phase_progress)
        
        # Check if we need key plot points
        existing_types = {pp.plot_point_type for pp in arc.plot_points.values()}
        
        if phase == StoryArcPhase.EXPOSITION and progress > 0.8:
            if PlotPointType.INCITING_INCIDENT not in existing_types:
                return PlotPointType.INCITING_INCIDENT
        
        elif phase == StoryArcPhase.RISING_ACTION:
            if progress > 0.8 and PlotPointType.CRISIS not in existing_types:
                return PlotPointType.CRISIS
        
        elif phase == StoryArcPhase.CLIMAX:
            if PlotPointType.CLIMAX not in existing_types:
                return PlotPointType.CLIMAX
        
        elif phase == StoryArcPhase.FALLING_ACTION:
            if arc_state.unresolved_conflict_count > 0:
                return PlotPointType.RESOLUTION
        
        return None
    
    async def _calculate_target_tension(
        self,
        arc_state: StoryArcState,
        arc: NarrativeArc
    ) -> Decimal:
        """Calculate target tension level for the turn."""
        # Get phase-typical tension range
        min_tension, max_tension = arc_state.current_phase.typical_tension_range
        
        # Adjust based on position in phase
        progress = arc_state.phase_progress
        
        # Linear interpolation within range, with peak at 80% through phase
        peak_position = Decimal("0.8")
        
        if progress <= peak_position:
            # Rising to peak
            ratio = progress / peak_position
            target = min_tension + (max_tension - min_tension) * ratio
        else:
            # Falling from peak (slight decrease for variety)
            ratio = (progress - peak_position) / (Decimal("1.0") - peak_position)
            peak_reduction = (max_tension - min_tension) * Decimal("0.2")  # 20% reduction
            target = max_tension - (peak_reduction * ratio)
        
        return target
    
    async def _recommend_pacing_intensity(
        self,
        arc_state: StoryArcState,
        arc: NarrativeArc
    ) -> str:
        """Recommend pacing intensity for the turn."""
        # Start with phase-typical pacing
        base_pacing = arc_state.current_phase.typical_pacing_intensity
        
        # Check for segment-specific pacing
        current_pacing = arc.get_pacing_at_sequence(arc_state.sequence_number)
        if current_pacing:
            return current_pacing.base_intensity.value
        
        return base_pacing
    
    async def _identify_theme_focus(
        self,
        arc_state: StoryArcState,
        arc: NarrativeArc
    ) -> list[str]:
        """Identify themes to emphasize."""
        active_themes = arc.get_themes_at_sequence(arc_state.sequence_number)
        
        if not active_themes:
            return []
        
        # Prioritize by intensity and impact
        sorted_themes = sorted(
            active_themes,
            key=lambda t: (
                t.intensity.value == "central",
                t.intensity.value == "prominent",
                float(t.narrative_impact_score)
            ),
            reverse=True
        )
        
        return [t.theme_id for t in sorted_themes[:2]]  # Top 2 themes
    
    async def _identify_character_focus(
        self,
        arc_state: StoryArcState,
        arc: NarrativeArc,
        context: dict
    ) -> list[str]:
        """Identify characters to focus on for development."""
        # Get primary characters from arc
        primary_chars = list(arc.primary_characters)
        
        if not primary_chars:
            return []
        
        # Rotate focus to ensure all get development
        # Use turn number to cycle through characters
        focus_count = min(3, len(primary_chars))
        start_index = arc_state.turn_number % len(primary_chars)
        
        focused = []
        for i in range(focus_count):
            char_index = (start_index + i) % len(primary_chars)
            focused.append(str(primary_chars[char_index]))
        
        return focused
    
    async def _calculate_content_ratios(
        self,
        arc_state: StoryArcState,
        arc: NarrativeArc
    ) -> tuple[Decimal, Decimal, Decimal]:
        """Calculate recommended content mix (dialogue, action, reflection)."""
        # Get pacing-based ratios
        current_pacing = arc.get_pacing_at_sequence(arc_state.sequence_number)
        
        if current_pacing:
            return (
                current_pacing.dialogue_ratio,
                current_pacing.action_ratio,
                current_pacing.reflection_ratio,
            )
        
        # Phase-based defaults
        phase_ratios = {
            StoryArcPhase.EXPOSITION: (Decimal("0.4"), Decimal("0.3"), Decimal("0.3")),
            StoryArcPhase.RISING_ACTION: (Decimal("0.3"), Decimal("0.5"), Decimal("0.2")),
            StoryArcPhase.CLIMAX: (Decimal("0.3"), Decimal("0.6"), Decimal("0.1")),
            StoryArcPhase.FALLING_ACTION: (Decimal("0.35"), Decimal("0.35"), Decimal("0.3")),
            StoryArcPhase.RESOLUTION: (Decimal("0.4"), Decimal("0.2"), Decimal("0.4")),
        }
        
        return phase_ratios.get(
            arc_state.current_phase,
            (Decimal("0.35"), Decimal("0.35"), Decimal("0.3"))  # Balanced default
        )
    
    async def _determine_narrative_tone(
        self,
        arc_state: StoryArcState,
        arc: NarrativeArc
    ) -> str:
        """Determine appropriate narrative tone."""
        phase = arc_state.current_phase
        tension = float(arc_state.current_tension_level)
        
        # Phase and tension influence tone
        if phase == StoryArcPhase.CLIMAX:
            return "intense"
        elif phase == StoryArcPhase.RESOLUTION:
            return "reflective"
        elif tension > 7.0:
            return "tense"
        elif tension < 4.0:
            return "contemplative"
        else:
            return "balanced"
    
    async def _identify_required_elements(
        self,
        arc_state: StoryArcState,
        arc: NarrativeArc
    ) -> list[str]:
        """Identify narrative elements that must be included."""
        required = []
        
        # Phase-specific requirements
        if arc_state.current_phase == StoryArcPhase.EXPOSITION:
            if arc_state.phase_progress > Decimal("0.8"):
                required.append("setup_for_inciting_incident")
        
        # Transition requirements
        if arc_state.ready_for_phase_transition:
            required.extend(arc_state.transition_requirements)
        
        return required
    
    async def _identify_elements_to_avoid(
        self,
        arc_state: StoryArcState,
        arc: NarrativeArc
    ) -> list[str]:
        """Identify elements to avoid in current turn."""
        avoid = []
        
        # Phase-specific avoidance
        if arc_state.current_phase == StoryArcPhase.EXPOSITION:
            avoid.append("major_character_death")
            avoid.append("climactic_confrontation")
        
        elif arc_state.current_phase == StoryArcPhase.RESOLUTION:
            avoid.append("new_major_conflicts")
            avoid.append("introducing_new_main_characters")
        
        # Pacing-based avoidance
        if arc_state.turns_in_current_phase >= 5:
            # Avoid stagnation
            avoid.append("repetitive_scenes")
        
        return avoid
    
    async def _identify_narrative_opportunities(
        self,
        arc_state: StoryArcState,
        arc: NarrativeArc,
        context: dict
    ) -> list[dict]:
        """Identify specific narrative opportunities."""
        opportunities = []
        
        # Theme development opportunities
        active_themes = arc.get_themes_at_sequence(arc_state.sequence_number)
        for theme in active_themes:
            if theme.is_major_theme:
                opportunities.append({
                    "type": "theme_exploration",
                    "theme_id": theme.theme_id,
                    "theme_name": theme.name,
                    "description": f"Opportunity to explore {theme.name} through character actions or dialogue",
                    "priority": 0.7,
                })
        
        # Character relationship opportunities
        if len(arc.primary_characters) >= 2:
            opportunities.append({
                "type": "character_relationship",
                "description": "Develop relationship dynamics between primary characters",
                "priority": 0.6,
            })
        
        # Plot thread progression
        if arc_state.active_plot_thread_count > 0:
            opportunities.append({
                "type": "plot_progression",
                "description": "Advance one or more active plot threads",
                "priority": 0.8,
            })
        
        return opportunities
    
    async def _generate_transition_guidance(
        self,
        arc_state: StoryArcState
    ) -> str:
        """Generate guidance for phase transition."""
        next_phase = arc_state.next_phase
        
        if not next_phase:
            return ""
        
        transition_templates = {
            StoryArcPhase.RISING_ACTION: "Conclude the setup and introduce the inciting incident that propels the story forward.",
            StoryArcPhase.CLIMAX: "Build to the story's climactic moment. Bring conflicts to their peak.",
            StoryArcPhase.FALLING_ACTION: "Show the immediate aftermath of the climax. Begin resolving plot threads.",
            StoryArcPhase.RESOLUTION: "Wrap up remaining conflicts and establish the new normal.",
        }
        
        return transition_templates.get(
            next_phase,
            f"Prepare to transition to {next_phase.value}"
        )
```

### 3.3 PacingManager

**Purpose**: Dynamically manage and adjust pacing during turn execution.

**Responsibilities**:
- Monitor pacing effectiveness
- Generate pacing adjustments
- Coordinate with StoryPacing segments
- React to narrative events

**Key Methods**:

```python
class PacingManager:
    """
    Manages dynamic pacing adjustments during story execution.
    
    Works in conjunction with StoryPacing segments to provide
    real-time pacing control based on narrative needs.
    """
    
    def __init__(
        self,
        arc_repository: NarrativeArcRepository,
        logger: Optional[logging.Logger] = None
    ):
        self._arc_repo = arc_repository
        self.logger = logger or logging.getLogger(__name__)
        
        # Tracking
        self._recent_adjustments: list[PacingAdjustment] = []
        self._max_history = 10
    
    async def calculate_pacing_adjustment(
        self,
        arc_state: StoryArcState,
        turn_context: dict
    ) -> Optional[PacingAdjustment]:
        """
        Calculate pacing adjustment for the current turn.
        
        Args:
            arc_state: Current story arc state
            turn_context: Context for the turn
            
        Returns:
            PacingAdjustment if adjustment needed, None otherwise
        """
        arc = await self._arc_repo.get_by_id(arc_state.arc_id)
        
        # Get base pacing from segment
        current_pacing = arc.get_pacing_at_sequence(arc_state.sequence_number)
        
        # Determine if adjustment is needed
        adjustment_needed, reason, trigger = await self._evaluate_adjustment_need(
            arc_state,
            arc,
            current_pacing,
            turn_context
        )
        
        if not adjustment_needed:
            return None
        
        # Calculate adjustments
        intensity_modifier = await self._calculate_intensity_modifier(
            arc_state,
            current_pacing,
            reason
        )
        
        tension_target = await self._calculate_tension_target(
            arc_state,
            current_pacing
        )
        
        content_adjustments = await self._calculate_content_adjustments(
            arc_state,
            current_pacing,
            reason
        )
        
        temporal_recommendations = await self._calculate_temporal_adjustments(
            arc_state,
            reason
        )
        
        # Create adjustment
        adjustment = PacingAdjustment(
            adjustment_id=f"pacing_{arc_state.turn_number}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            turn_number=arc_state.turn_number,
            intensity_modifier=intensity_modifier,
            tension_target=tension_target,
            dialogue_adjustment=content_adjustments["dialogue"],
            action_adjustment=content_adjustments["action"],
            reflection_adjustment=content_adjustments["reflection"],
            scene_break_recommended=temporal_recommendations["scene_break"],
            time_jump_recommended=temporal_recommendations["time_jump"],
            adjustment_reason=reason,
            triggered_by=trigger,
        )
        
        # Track adjustment
        self._recent_adjustments.append(adjustment)
        if len(self._recent_adjustments) > self._max_history:
            self._recent_adjustments = self._recent_adjustments[-self._max_history:]
        
        return adjustment
    
    async def _evaluate_adjustment_need(
        self,
        arc_state: StoryArcState,
        arc: NarrativeArc,
        current_pacing: Optional[StoryPacing],
        context: dict
    ) -> tuple[bool, str, str]:
        """
        Evaluate if pacing adjustment is needed.
        
        Returns:
            (adjustment_needed, reason, trigger)
        """
        # Check for phase transition
        if arc_state.ready_for_phase_transition:
            return (True, "Adjust pacing for phase transition", "phase_transition")
        
        # Check tension alignment
        if current_pacing:
            expected_tension = await self._calculate_expected_tension(arc_state)
            tension_diff = abs(arc_state.current_tension_level - expected_tension)
            
            if tension_diff > Decimal("2.0"):
                return (
                    True,
                    f"Tension misalignment: current={arc_state.current_tension_level}, expected={expected_tension}",
                    "tension_management"
                )
        
        # Check for pacing monotony
        if arc_state.turns_in_current_phase > 4:
            if await self._detect_pacing_monotony():
                return (True, "Variety needed to maintain engagement", "monotony_prevention")
        
        # Check for climactic moment
        if arc_state.current_phase == StoryArcPhase.CLIMAX:
            return (True, "Climax requires heightened pacing", "climax_emphasis")
        
        return (False, "", "")
    
    async def _calculate_intensity_modifier(
        self,
        arc_state: StoryArcState,
        current_pacing: Optional[StoryPacing],
        reason: str
    ) -> Decimal:
        """Calculate intensity modifier."""
        modifier = Decimal("0")
        
        # Phase-based modifiers
        if arc_state.current_phase == StoryArcPhase.CLIMAX:
            modifier += Decimal("1.5")
        elif arc_state.current_phase == StoryArcPhase.EXPOSITION:
            modifier -= Decimal("0.5")
        
        # Transition modifiers
        if arc_state.ready_for_phase_transition:
            modifier += Decimal("0.5")
        
        # Clamp to valid range
        return max(Decimal("-3"), min(Decimal("3"), modifier))
    
    async def _calculate_tension_target(
        self,
        arc_state: StoryArcState,
        current_pacing: Optional[StoryPacing]
    ) -> Decimal:
        """Calculate target tension level."""
        # Use phase-typical tension
        min_tension, max_tension = arc_state.current_phase.typical_tension_range
        
        # Adjust based on phase progress
        progress = arc_state.phase_progress
        
        # Peak tension at 80% through phase
        if progress <= Decimal("0.8"):
            ratio = progress / Decimal("0.8")
            target = min_tension + (max_tension - min_tension) * ratio
        else:
            target = max_tension
        
        return target
    
    async def _calculate_content_adjustments(
        self,
        arc_state: StoryArcState,
        current_pacing: Optional[StoryPacing],
        reason: str
    ) -> dict[str, Decimal]:
        """Calculate content ratio adjustments."""
        adjustments = {
            "dialogue": Decimal("0"),
            "action": Decimal("0"),
            "reflection": Decimal("0"),
        }
        
        # Climax: more action, less reflection
        if arc_state.current_phase == StoryArcPhase.CLIMAX:
            adjustments["action"] = Decimal("0.15")
            adjustments["reflection"] = Decimal("-0.15")
        
        # Resolution: more reflection, less action
        elif arc_state.current_phase == StoryArcPhase.RESOLUTION:
            adjustments["reflection"] = Decimal("0.15")
            adjustments["action"] = Decimal("-0.15")
        
        return adjustments
    
    async def _calculate_temporal_adjustments(
        self,
        arc_state: StoryArcState,
        reason: str
    ) -> dict[str, bool]:
        """Calculate temporal adjustment recommendations."""
        return {
            "scene_break": arc_state.ready_for_phase_transition,
            "time_jump": (
                arc_state.current_phase == StoryArcPhase.RISING_ACTION
                and arc_state.phase_progress > Decimal("0.5")
            ),
        }
    
    async def _calculate_expected_tension(
        self,
        arc_state: StoryArcState
    ) -> Decimal:
        """Calculate expected tension for current position."""
        min_tension, max_tension = arc_state.current_phase.typical_tension_range
        progress = arc_state.phase_progress
        
        # Linear interpolation
        return min_tension + (max_tension - min_tension) * progress
    
    async def _detect_pacing_monotony(self) -> bool:
        """Detect if recent pacing has been monotonous."""
        if len(self._recent_adjustments) < 3:
            return False
        
        # Check if last 3 adjustments were similar
        recent = self._recent_adjustments[-3:]
        
        intensity_variance = sum(
            abs(recent[i].intensity_modifier - recent[i+1].intensity_modifier)
            for i in range(len(recent) - 1)
        )
        
        # Low variance suggests monotony
        return intensity_variance < Decimal("0.5")
```

---

## 4. Integration Interfaces

### 4.1 DirectorAgent Integration

The V2 Narrative Engine provides a clean interface for the DirectorAgent to request narrative context and report turn results.

#### 4.1.1 Request Narrative Context

```python
class NarrativeEngineV2:
    """
    Facade for V2 Narrative Engine.
    
    Provides unified interface for DirectorAgent to interact
    with narrative planning and arc management.
    """
    
    def __init__(
        self,
        arc_manager: StoryArcManager,
        planning_engine: NarrativePlanningEngine,
        pacing_manager: PacingManager,
        orchestrator: NarrativeOrchestrator,  # Existing V1 component
    ):
        self._arc_manager = arc_manager
        self._planning_engine = planning_engine
        self._pacing_manager = pacing_manager
        self._orchestrator = orchestrator
    
    async def get_narrative_context_for_turn(
        self,
        turn_number: int,
        world_context: dict,
        character_context: dict
    ) -> dict:
        """
        Get comprehensive narrative context for DirectorAgent.
        
        This is the primary interface method called by DirectorAgent
        before executing a turn.
        
        Args:
            turn_number: Current turn number
            world_context: World state information
            character_context: Character state information
            
        Returns:
            Comprehensive narrative context dictionary
        """
        # Get current arc state
        arc_state = await self._arc_manager.get_current_state()
        
        if not arc_state:
            raise RuntimeError("Story arc not initialized")
        
        # Generate narrative guidance
        guidance = await self._planning_engine.generate_turn_guidance(
            arc_state=arc_state,
            context={
                "world": world_context,
                "characters": character_context,
            }
        )
        
        # Calculate pacing adjustment
        pacing_adjustment = await self._pacing_manager.calculate_pacing_adjustment(
            arc_state=arc_state,
            turn_context={
                "world": world_context,
                "characters": character_context,
            }
        )
        
        # Build comprehensive context
        return {
            "arc_state": arc_state.to_context_dict(),
            "narrative_guidance": guidance.to_director_context(),
            "pacing_adjustment": {
                "intensity_modifier": float(pacing_adjustment.intensity_modifier) if pacing_adjustment else 0,
                "tension_target": float(pacing_adjustment.tension_target) if pacing_adjustment else float(arc_state.current_tension_level),
                "content_adjustments": {
                    "dialogue": float(pacing_adjustment.dialogue_adjustment) if pacing_adjustment else 0,
                    "action": float(pacing_adjustment.action_adjustment) if pacing_adjustment else 0,
                    "reflection": float(pacing_adjustment.reflection_adjustment) if pacing_adjustment else 0,
                } if pacing_adjustment else None,
                "scene_break": pacing_adjustment.scene_break_recommended if pacing_adjustment else False,
                "time_jump": pacing_adjustment.time_jump_recommended if pacing_adjustment else False,
            } if pacing_adjustment else None,
            "turn_number": turn_number,
            "metadata": {
                "engine_version": "v2",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        }
    
    async def report_turn_completion(
        self,
        turn_number: int,
        turn_result: dict
    ) -> dict:
        """
        Report turn completion and update narrative state.
        
        Called by DirectorAgent after turn execution to update
        narrative tracking and progression.
        
        Args:
            turn_number: Completed turn number
            turn_result: Results from turn execution including:
                - generated_content: The actual story text
                - tension_score: Measured tension (0-10)
                - plot_points_introduced: List of plot point IDs
                - themes_explored: List of theme IDs
                - character_developments: Character changes
                
        Returns:
            Updated narrative state and feedback
        """
        # Advance arc state
        updated_state = await self._arc_manager.advance_turn(turn_result)
        
        # Process narrative events through V1 orchestrator
        narrative_events = self._extract_narrative_events(turn_result)
        await self._orchestrator.process_narrative_events(narrative_events)
        
        # Generate feedback
        feedback = {
            "state_updated": True,
            "new_phase": updated_state.current_phase.value,
            "phase_transitioned": (
                updated_state.previous_phase is not None
                and updated_state.previous_phase != updated_state.current_phase
            ),
            "overall_progress": float(updated_state.overall_progress),
            "narrative_health": await self._assess_narrative_health(updated_state),
            "recommendations": await self._generate_continuation_recommendations(updated_state),
        }
        
        return feedback
    
    def _extract_narrative_events(self, turn_result: dict) -> list[dict]:
        """Extract narrative events from turn result."""
        events = []
        
        # Convert turn result into narrative events
        # This bridges V2 turn tracking with V1 event system
        
        if "plot_points_introduced" in turn_result:
            for plot_point_id in turn_result["plot_points_introduced"]:
                events.append({
                    "type": "plot_progression",
                    "plot_point_id": plot_point_id,
                    "participants": turn_result.get("active_characters", []),
                    "impact": turn_result.get("tension_score", 5.0) / 10.0,
                })
        
        if "character_developments" in turn_result:
            for char_id, development in turn_result["character_developments"].items():
                events.append({
                    "type": "character_action",
                    "character_id": char_id,
                    "description": development.get("description", ""),
                    "impact": development.get("significance", 0.5),
                })
        
        return events
    
    async def _assess_narrative_health(self, arc_state: StoryArcState) -> dict:
        """Assess overall narrative health."""
        return {
            "status": "healthy" if arc_state.overall_progress < Decimal("0.95") else "concluding",
            "tension_appropriate": abs(
                arc_state.current_tension_level - await self._pacing_manager._calculate_expected_tension(arc_state)
            ) < Decimal("2.0"),
            "pacing_varied": True,  # Would check actual variety
            "plot_threads_managed": arc_state.active_plot_thread_count <= 5,
        }
    
    async def _generate_continuation_recommendations(self, arc_state: StoryArcState) -> list[str]:
        """Generate recommendations for continuing the story."""
        recommendations = []
        
        if arc_state.unresolved_conflict_count > 3:
            recommendations.append("Consider resolving some conflicts to maintain clarity")
        
        if arc_state.ready_for_phase_transition:
            recommendations.append(f"Ready to transition to {arc_state.next_phase.value}")
        
        if arc_state.overall_progress > Decimal("0.9"):
            recommendations.append("Approaching story conclusion - ensure all threads are addressed")
        
        return recommendations
```

#### 4.1.2 DirectorAgent Usage Example

```python
# In DirectorAgent's execute_turn method:

async def execute_turn(self, turn_number: int) -> dict:
    """Execute a single turn with narrative guidance."""
    
    # 1. Get narrative context from V2 engine
    narrative_context = await self.narrative_engine.get_narrative_context_for_turn(
        turn_number=turn_number,
        world_context=await self.get_world_state(),
        character_context=await self.get_character_states()
    )
    
    # 2. Build LLM prompt with narrative guidance
    prompt = self._build_narrative_aware_prompt(
        turn_number=turn_number,
        narrative_context=narrative_context,
        world_state=await self.get_world_state(),
        character_states=await self.get_character_states()
    )
    
    # 3. Execute turn with LLM
    turn_result = await self._execute_with_llm(prompt)
    
    # 4. Report completion to narrative engine
    narrative_feedback = await self.narrative_engine.report_turn_completion(
        turn_number=turn_number,
        turn_result={
            "generated_content": turn_result["content"],
            "tension_score": self._measure_tension(turn_result["content"]),
            "plot_points_introduced": turn_result.get("plot_points", []),
            "themes_explored": turn_result.get("themes", []),
            "character_developments": turn_result.get("char_changes", {}),
            "active_characters": turn_result.get("characters", []),
        }
    )
    
    # 5. Return combined result
    return {
        **turn_result,
        "narrative_feedback": narrative_feedback,
    }

def _build_narrative_aware_prompt(
    self,
    turn_number: int,
    narrative_context: dict,
    world_state: dict,
    character_states: dict
) -> str:
    """Build prompt with narrative guidance integrated."""
    
    guidance = narrative_context["narrative_guidance"]
    arc_state = narrative_context["arc_state"]
    
    prompt = f"""
You are generating turn {turn_number} of an ongoing narrative.

## Story Context
- **Current Phase**: {arc_state['current_phase']} ({arc_state['phase_position']})
- **Overall Progress**: {arc_state['overall_progress']:.1%}
- **Current Tension**: {arc_state['current_tension']}/10

## Narrative Objectives
**Primary Goal**: {guidance['narrative_goal']}

**Secondary Goals**:
{chr(10).join(f"- {goal}" for goal in guidance['secondary_goals'])}

## Content Guidance
- **Target Tension**: {guidance['target_tension']}/10
- **Pacing**: {guidance['pacing']}
- **Tone**: {guidance['tone']}

**Content Mix**:
- Dialogue: {guidance['content_mix']['dialogue']:.0%}
- Action: {guidance['content_mix']['action']:.0%}
- Reflection: {guidance['content_mix']['reflection']:.0%}

**Focus Themes**: {', '.join(guidance['themes_focus']) or 'None'}
**Character Focus**: {', '.join(guidance['character_focus'][:2]) or 'All'}

{self._format_required_elements(guidance)}
{self._format_opportunities(guidance)}

## World State
{self._format_world_state(world_state)}

## Character States
{self._format_character_states(character_states)}

Generate the next turn of the story following these narrative guidelines.
"""
    
    return prompt
```

---

## 5. Implementation Roadmap

### Phase 1: Core Models and Arc Manager (Week 1)
1. Implement `StoryArcPhase`, `StoryArcState`, `NarrativeGuidance`
2. Implement `PacingAdjustment`
3. Implement `StoryArcManager` with basic progression
4. Unit tests for all models and arc manager

### Phase 2: Planning Engine (Week 2)
1. Implement `NarrativePlanningEngine`
2. Implement goal generation logic
3. Implement content recommendation logic
4. Integration tests with existing `NarrativeArc`

### Phase 3: Pacing Manager (Week 3)
1. Implement `PacingManager`
2. Implement pacing adjustment logic
3. Integration with `StoryPacing` value objects
4. Testing pacing effectiveness

### Phase 4: Integration Layer (Week 4)
1. Implement `NarrativeEngineV2` facade
2. Create DirectorAgent integration points
3. Build prompt construction helpers
4. End-to-end integration testing

### Phase 5: Testing and Refinement (Week 5)
1. Comprehensive integration testing
2. Generate test narratives
3. Evaluate "novel feel" improvements
4. Tune algorithms and thresholds
5. Performance optimization

### Phase 6: Documentation and Deployment (Week 6)
1. API documentation
2. Usage examples
3. Migration guide from V1
4. Deployment and monitoring

---

## 6. Testing Strategy

### 6.1 Unit Tests

- **Data Models**: Validation, constraints, property calculations
- **StoryArcManager**: Progression, transitions, state tracking
- **NarrativePlanningEngine**: Goal generation, guidance creation
- **PacingManager**: Adjustment calculations, monotony detection

### 6.2 Integration Tests

- **Arc Progression**: Multi-turn progression through full arc
- **Phase Transitions**: Automated transitions at appropriate times
- **DirectorAgent Integration**: Full turn execution with narrative context
- **Event System**: V1/V2 event coordination

### 6.3 End-to-End Tests

- **Complete Story Generation**: Generate 50-turn story with V2 guidance
- **Quality Metrics**: Measure coherence, pacing variety, tension curves
- **Comparison Tests**: V1 vs V2 "novel feel" evaluation

### 6.4 Performance Tests

- **Context Generation Speed**: < 100ms per turn
- **State Update Speed**: < 50ms per turn
- **Memory Usage**: Track state growth over long stories

---

## 7. Success Criteria

### 7.1 Functional Requirements
- ✅ Track story progression through 5-act structure
- ✅ Generate turn-level narrative guidance
- ✅ Manage dynamic pacing adjustments
- ✅ Integrate seamlessly with DirectorAgent
- ✅ Maintain backward compatibility with V1

### 7.2 Quality Requirements
- **Narrative Coherence**: 8.5/10 or higher (measured via NarrativeFlowService)
- **Pacing Variety**: Demonstrable variation in intensity across turns
- **Tension Progression**: Clear arc matching story structure
- **Theme Development**: Consistent theme presence and progression

### 7.3 Performance Requirements
- **Context Generation**: < 100ms per turn
- **State Updates**: < 50ms per turn
- **Memory Efficiency**: < 50MB additional overhead for 100-turn story

### 7.4 User Experience
- **Novel Feel**: Qualitative improvement in story structure
- **Predictable Pacing**: Appropriate pacing for each phase
- **Satisfying Arcs**: Clear beginning, middle, and end
- **Character Development**: Consistent character focus and growth

---

## 8. Future Enhancements (V3)

### 8.1 Advanced Features
- **Multi-Arc Support**: Parallel storylines with separate arc tracking
- **Sub-Arc Management**: Character-specific arcs within main arc
- **Adaptive Arc Lengths**: Dynamic adjustment of phase durations
- **Genre-Specific Templates**: Pre-configured arcs for different genres

### 8.2 AI Enhancements
- **Predictive Planning**: ML-based prediction of optimal next plot points
- **Quality Scoring**: Automated evaluation of generated content quality
- **Style Adaptation**: Learn user preferences for pacing and style

### 8.3 Analytics
- **Arc Visualization**: Graphical representation of tension/pacing curves
- **Quality Dashboards**: Real-time narrative health metrics
- **Comparative Analysis**: Compare different arc strategies

---

## 9. Conclusion

The V2 Narrative Engine represents a significant architectural enhancement to the Novel Engine, introducing intelligent story arc management while building upon the solid foundation of existing narrative infrastructure. By providing the DirectorAgent with rich narrative context and guidance, V2 enables the generation of content that feels more like a carefully crafted novel rather than disconnected scenes.

The modular design ensures that V2 components can be adopted incrementally, with clear interfaces and separation of concerns. The architecture supports future enhancements while maintaining backward compatibility with V1 systems.

**Key Innovations**:
1. **Story Arc State Machine** - Intelligent progression through narrative structure
2. **Turn-Level Planning** - Specific narrative objectives for each turn
3. **Dynamic Pacing Control** - Real-time adjustments for optimal rhythm
4. **Seamless Integration** - Clean interfaces with DirectorAgent

**Expected Outcomes**:
- Improved narrative coherence and structure
- More engaging pacing and tension progression
- Better character and theme development
- Enhanced "novel feel" in generated content

The V2 architecture provides a strong foundation for continued enhancement of the Novel Engine's narrative capabilities, enabling the creation of compelling, well-structured stories through AI-driven generation.

---

## Appendix A: Domain Events

```python
@dataclass
class ArcInitialized(NarrativeEvent):
    """Raised when a new arc tracking is initialized."""
    arc_id: str
    initial_phase: StoryArcPhase
    timestamp: datetime

@dataclass
class PhaseTransitioned(NarrativeEvent):
    """Raised when story transitions between phases."""
    arc_id: str
    from_phase: StoryArcPhase
    to_phase: StoryArcPhase
    turn_number: int
    timestamp: datetime

@dataclass
class GuidanceGenerated(NarrativeEvent):
    """Raised when narrative guidance is generated."""
    guidance_id: str
    turn_number: int
    primary_goal: str
    timestamp: datetime

@dataclass
class PacingAdjusted(NarrativeEvent):
    """Raised when pacing adjustment is made."""
    adjustment_id: str
    turn_number: int
    intensity_change: Decimal
    reason: str
    timestamp: datetime
```

## Appendix B: Configuration

```python
@dataclass
class NarrativeEngineConfig:
    """Configuration for V2 Narrative Engine."""
    
    # Arc progression
    auto_phase_transitions: bool = True
    transition_threshold: Decimal = Decimal("0.95")
    
    # Pacing
    enable_dynamic_pacing: bool = True
    pacing_adjustment_sensitivity: Decimal = Decimal("0.7")  # 0-1
    
    # Planning
    planning_depth: str = "standard"  # minimal, standard, detailed
    theme_focus_strategy: str = "rotating"  # rotating, prominence, adaptive
    
    # Integration
    event_publishing_enabled: bool = True
    v1_compatibility_mode: bool = True
```
