"""
Goal Manager
============

Advanced goal management system for PersonaAgent character behavior.
Handles goal prioritization, tracking, completion, and dynamic adaptation.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from ..protocols import ThreatLevel, WorldEvent


class GoalType(Enum):
    """Types of goals a character can have."""

    SURVIVAL = "survival"  # Basic survival needs
    COMBAT = "combat"  # Combat-related objectives
    EXPLORATION = "exploration"  # Discovery and exploration
    SOCIAL = "social"  # Relationship and social goals
    RESOURCE = "resource"  # Resource acquisition
    KNOWLEDGE = "knowledge"  # Information gathering
    FACTION = "faction"  # Factional objectives
    PERSONAL = "personal"  # Personal ambitions
    TACTICAL = "tactical"  # Short-term tactical goals
    STRATEGIC = "strategic"  # Long-term strategic goals


class GoalStatus(Enum):
    """Status of goals."""

    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    ABANDONED = "abandoned"


class GoalPriority(Enum):
    """Priority levels for goals."""

    CRITICAL = "critical"  # Must be done immediately
    HIGH = "high"  # Should be done soon
    MEDIUM = "medium"  # Normal priority
    LOW = "low"  # Can be deferred
    MINIMAL = "minimal"  # Optional


@dataclass
class Goal:
    """Represents a character goal with full context."""

    goal_id: str
    goal_type: GoalType
    title: str
    description: str
    priority: GoalPriority = GoalPriority.MEDIUM
    status: GoalStatus = GoalStatus.ACTIVE

    # Progress and completion
    progress: float = 0.0  # 0.0 to 1.0
    required_actions: List[str] = field(default_factory=list)
    completed_actions: List[str] = field(default_factory=list)

    # Timing
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    deadline: Optional[float] = None
    last_updated: float = field(default_factory=lambda: datetime.now().timestamp())

    # Context and conditions
    success_conditions: Dict[str, Any] = field(default_factory=dict)
    failure_conditions: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(
        default_factory=list
    )  # Other goal IDs this depends on

    # Motivation and importance
    importance_score: float = 0.5  # 0.0 to 1.0
    motivation_factors: Dict[str, float] = field(default_factory=dict)

    # Tracking
    attempts: int = 0
    setbacks: List[Dict[str, Any]] = field(default_factory=list)

    def is_overdue(self) -> bool:
        """Check if goal is past its deadline."""
        if self.deadline is None:
            return False
        return datetime.now().timestamp() > self.deadline

    def get_age_hours(self) -> float:
        """Get goal age in hours."""
        return (datetime.now().timestamp() - self.created_at) / 3600

    def get_completion_ratio(self) -> float:
        """Get ratio of completed to required actions."""
        if not self.required_actions:
            return self.progress
        return len(self.completed_actions) / len(self.required_actions)


@dataclass
class GoalContext:
    """Context information for goal management decisions."""

    world_state: Dict[str, Any]
    character_state: Dict[str, Any]
    recent_events: List[WorldEvent]
    threat_level: ThreatLevel
    available_resources: Dict[str, float]
    time_constraints: Dict[str, Any]
    current_location: Optional[str] = None


class GoalManager:
    """
    Advanced goal management system for PersonaAgent.

    Responsibilities:
    - Track character goals and their progress
    - Prioritize goals based on context and character traits
    - Handle goal completion, failure, and abandonment
    - Generate new goals based on world events and character needs
    - Manage goal dependencies and conflicts
    - Provide goal-based decision support
    """

    def __init__(self, character_id: str, logger: Optional[logging.Logger] = None):
        self.character_id = character_id
        self.logger = logger or logging.getLogger(__name__)

        # Active goal tracking
        self._active_goals: Dict[str, Goal] = {}
        self._completed_goals: List[Goal] = []
        self._failed_goals: List[Goal] = []

        # Goal generation templates
        self._goal_templates: Dict[str, Dict[str, Any]] = {}
        self._initialize_goal_templates()

        # Priority calculation weights
        self._priority_weights = {
            "urgency": 0.3,  # How urgent is this goal
            "importance": 0.25,  # Character importance rating
            "feasibility": 0.2,  # How achievable it is
            "alignment": 0.15,  # Alignment with character traits
            "opportunity": 0.1,  # Current opportunity level
        }

        # Goal interaction tracking
        self._goal_relationships: Dict[str, List[str]] = (
            {}
        )  # goal_id -> [related_goal_ids]

        # Performance metrics
        self._metrics = {
            "total_goals_created": 0,
            "goals_completed": 0,
            "goals_failed": 0,
            "average_completion_time": 0.0,
        }

    async def add_goal(self, goal_data: Dict[str, Any]) -> str:
        """
        Add a new goal for the character.

        Args:
            goal_data: Goal information and parameters

        Returns:
            str: Generated goal ID
        """
        try:
            # Generate unique goal ID
            goal_id = f"{self.character_id}_goal_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self._active_goals)}"

            # Create goal object
            goal = Goal(
                goal_id=goal_id,
                goal_type=GoalType(goal_data.get("type", "personal")),
                title=goal_data["title"],
                description=goal_data.get("description", ""),
                priority=GoalPriority(goal_data.get("priority", "medium")),
                required_actions=goal_data.get("required_actions", []),
                success_conditions=goal_data.get("success_conditions", {}),
                failure_conditions=goal_data.get("failure_conditions", {}),
                dependencies=goal_data.get("dependencies", []),
                importance_score=goal_data.get("importance", 0.5),
                motivation_factors=goal_data.get("motivation_factors", {}),
                deadline=goal_data.get("deadline"),
            )

            # Validate dependencies
            await self._validate_goal_dependencies(goal)

            # Add to active goals
            self._active_goals[goal_id] = goal
            self._metrics["total_goals_created"] += 1

            # Update goal relationships
            await self._update_goal_relationships(goal)

            self.logger.info(f"Added new goal: {goal.title} ({goal_id})")
            return goal_id

        except Exception as e:
            self.logger.error(f"Failed to add goal: {e}")
            raise

    async def prioritize_goals(self, context: GoalContext) -> List[Goal]:
        """
        Prioritize active goals based on current context.

        Args:
            context: Current context information

        Returns:
            List of goals sorted by calculated priority
        """
        try:
            if not self._active_goals:
                return []

            # Calculate priority scores for each goal
            scored_goals = []
            for goal in self._active_goals.values():
                priority_score = await self._calculate_goal_priority(goal, context)
                scored_goals.append((goal, priority_score))

            # Sort by priority score (highest first)
            scored_goals.sort(key=lambda x: x[1], reverse=True)

            # Update goal priorities based on scores
            await self._update_goal_priorities(scored_goals)

            prioritized_goals = [goal for goal, score in scored_goals]

            self.logger.debug(f"Prioritized {len(prioritized_goals)} goals")
            return prioritized_goals

        except Exception as e:
            self.logger.error(f"Goal prioritization failed: {e}")
            return list(self._active_goals.values())

    async def update_goal_progress(
        self, goal_id: str, progress_data: Dict[str, Any]
    ) -> bool:
        """
        Update progress on a specific goal.

        Args:
            goal_id: ID of goal to update
            progress_data: Progress information

        Returns:
            bool: True if update successful
        """
        try:
            if goal_id not in self._active_goals:
                self.logger.warning(f"Goal {goal_id} not found in active goals")
                return False

            goal = self._active_goals[goal_id]

            # Update progress value
            if "progress" in progress_data:
                goal.progress = max(0.0, min(1.0, progress_data["progress"]))

            # Update completed actions
            if "completed_action" in progress_data:
                action = progress_data["completed_action"]
                if (
                    action not in goal.completed_actions
                    and action in goal.required_actions
                ):
                    goal.completed_actions.append(action)

            # Record attempts
            if progress_data.get("attempt_made", False):
                goal.attempts += 1

            # Record setbacks
            if "setback" in progress_data:
                setback = {
                    "timestamp": datetime.now().timestamp(),
                    "description": progress_data["setback"],
                    "impact": progress_data.get("setback_impact", "minor"),
                }
                goal.setbacks.append(setback)

            # Update timestamp
            goal.last_updated = datetime.now().timestamp()

            # Check for completion or failure
            await self._check_goal_completion(goal)

            self.logger.debug(
                f"Updated progress for goal {goal_id}: {goal.progress:.2f}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Goal progress update failed: {e}")
            return False

    async def generate_goals_from_events(
        self, events: List[WorldEvent], character_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate new goals based on world events and character context.

        Args:
            events: Recent world events
            character_context: Character state and traits

        Returns:
            List of generated goal data
        """
        try:
            generated_goals = []

            for event in events:
                # Analyze event for goal generation opportunities
                goal_opportunities = await self._analyze_event_for_goals(
                    event, character_context
                )

                for opportunity in goal_opportunities:
                    # Generate goal from template
                    goal_data = await self._generate_goal_from_template(
                        opportunity, event, character_context
                    )
                    if goal_data:
                        generated_goals.append(goal_data)

            # Remove duplicates and conflicts
            filtered_goals = await self._filter_conflicting_goals(generated_goals)

            self.logger.info(
                f"Generated {len(filtered_goals)} new goals from {len(events)} events"
            )
            return filtered_goals

        except Exception as e:
            self.logger.error(f"Goal generation from events failed: {e}")
            return []

    async def get_goals_by_type(self, goal_type: GoalType) -> List[Goal]:
        """Get active goals of specific type."""
        return [
            goal for goal in self._active_goals.values() if goal.goal_type == goal_type
        ]

    async def get_goals_by_priority(self, priority: GoalPriority) -> List[Goal]:
        """Get active goals of specific priority."""
        return [
            goal for goal in self._active_goals.values() if goal.priority == priority
        ]

    async def get_overdue_goals(self) -> List[Goal]:
        """Get goals that are past their deadline."""
        return [goal for goal in self._active_goals.values() if goal.is_overdue()]

    async def abandon_goal(self, goal_id: str, reason: str) -> bool:
        """
        Abandon a goal with reason.

        Args:
            goal_id: ID of goal to abandon
            reason: Reason for abandonment

        Returns:
            bool: True if successful
        """
        try:
            if goal_id not in self._active_goals:
                return False

            goal = self._active_goals[goal_id]
            goal.status = GoalStatus.ABANDONED
            goal.last_updated = datetime.now().timestamp()

            # Record abandonment reason
            setback = {
                "timestamp": datetime.now().timestamp(),
                "description": f"Goal abandoned: {reason}",
                "impact": "major",
            }
            goal.setbacks.append(setback)

            # Move to failed goals (abandoned goals are tracked as failed)
            del self._active_goals[goal_id]
            self._failed_goals.append(goal)
            self._metrics["goals_failed"] += 1

            self.logger.info(f"Abandoned goal {goal_id}: {reason}")
            return True

        except Exception as e:
            self.logger.error(f"Goal abandonment failed: {e}")
            return False

    async def get_goal_statistics(self) -> Dict[str, Any]:
        """Get comprehensive goal statistics."""
        try:
            total_goals = (
                len(self._active_goals)
                + len(self._completed_goals)
                + len(self._failed_goals)
            )

            # Calculate completion rate
            completion_rate = (
                (len(self._completed_goals) / total_goals) if total_goals > 0 else 0.0
            )

            # Calculate average goal age
            if self._active_goals:
                avg_age = sum(
                    goal.get_age_hours() for goal in self._active_goals.values()
                ) / len(self._active_goals)
            else:
                avg_age = 0.0

            # Goal type distribution
            type_distribution = {}
            for goal in self._active_goals.values():
                goal_type = goal.goal_type.value
                type_distribution[goal_type] = type_distribution.get(goal_type, 0) + 1

            # Priority distribution
            priority_distribution = {}
            for goal in self._active_goals.values():
                priority = goal.priority.value
                priority_distribution[priority] = (
                    priority_distribution.get(priority, 0) + 1
                )

            return {
                "total_goals": total_goals,
                "active_goals": len(self._active_goals),
                "completed_goals": len(self._completed_goals),
                "failed_goals": len(self._failed_goals),
                "completion_rate": completion_rate,
                "average_age_hours": avg_age,
                "type_distribution": type_distribution,
                "priority_distribution": priority_distribution,
                "overdue_goals": len(await self.get_overdue_goals()),
                "metrics": self._metrics.copy(),
            }

        except Exception as e:
            self.logger.error(f"Goal statistics calculation failed: {e}")
            return {"error": str(e)}

    async def save_goals_state(self, file_path: str) -> bool:
        """Save goals state to file."""
        try:
            state_data = {
                "character_id": self.character_id,
                "active_goals": {
                    goal_id: self._serialize_goal(goal)
                    for goal_id, goal in self._active_goals.items()
                },
                "completed_goals": [
                    self._serialize_goal(goal) for goal in self._completed_goals
                ],
                "failed_goals": [
                    self._serialize_goal(goal) for goal in self._failed_goals
                ],
                "metrics": self._metrics,
                "saved_at": datetime.now().isoformat(),
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Goals state saved to {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save goals state: {e}")
            return False

    async def load_goals_state(self, file_path: str) -> bool:
        """Load goals state from file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                state_data = json.load(f)

            # Validate character ID
            if state_data.get("character_id") != self.character_id:
                self.logger.error("Character ID mismatch in goals state file")
                return False

            # Load active goals
            self._active_goals = {}
            for goal_id, goal_data in state_data.get("active_goals", {}).items():
                goal = self._deserialize_goal(goal_data)
                self._active_goals[goal_id] = goal

            # Load completed and failed goals
            self._completed_goals = [
                self._deserialize_goal(goal_data)
                for goal_data in state_data.get("completed_goals", [])
            ]
            self._failed_goals = [
                self._deserialize_goal(goal_data)
                for goal_data in state_data.get("failed_goals", [])
            ]

            # Load metrics
            self._metrics.update(state_data.get("metrics", {}))

            self.logger.info(f"Goals state loaded from {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to load goals state: {e}")
            return False

    # Private helper methods

    async def _calculate_goal_priority(self, goal: Goal, context: GoalContext) -> float:
        """Calculate priority score for a goal based on context."""
        try:
            score = 0.0

            # Urgency factor (deadlines, overdue status)
            urgency_score = await self._calculate_urgency_score(goal, context)
            score += urgency_score * self._priority_weights["urgency"]

            # Importance factor (character importance rating)
            importance_score = goal.importance_score
            score += importance_score * self._priority_weights["importance"]

            # Feasibility factor (resources, dependencies)
            feasibility_score = await self._calculate_feasibility_score(goal, context)
            score += feasibility_score * self._priority_weights["feasibility"]

            # Alignment factor (character traits, current state)
            alignment_score = await self._calculate_alignment_score(goal, context)
            score += alignment_score * self._priority_weights["alignment"]

            # Opportunity factor (current world state)
            opportunity_score = await self._calculate_opportunity_score(goal, context)
            score += opportunity_score * self._priority_weights["opportunity"]

            return max(0.0, min(1.0, score))

        except Exception as e:
            self.logger.debug(
                f"Priority calculation failed for goal {goal.goal_id}: {e}"
            )
            return 0.5

    async def _calculate_urgency_score(self, goal: Goal, context: GoalContext) -> float:
        """Calculate urgency score based on deadlines and time pressure."""
        score = 0.5  # Base score

        if goal.deadline:
            time_remaining = goal.deadline - datetime.now().timestamp()
            if time_remaining <= 0:
                score = 1.0  # Overdue
            elif time_remaining < 3600:  # Less than 1 hour
                score = 0.9
            elif time_remaining < 86400:  # Less than 1 day
                score = 0.7
            else:
                score = 0.3

        # Consider threat level for survival goals
        if goal.goal_type == GoalType.SURVIVAL and context.threat_level in [
            ThreatLevel.HIGH,
            ThreatLevel.CRITICAL,
        ]:
            score = max(score, 0.8)

        return score

    async def _calculate_feasibility_score(
        self, goal: Goal, context: GoalContext
    ) -> float:
        """Calculate how feasible the goal is given current resources."""
        score = 0.7  # Optimistic base

        # Check resource requirements vs availability
        # This is a placeholder - would need goal-specific resource analysis

        # Check dependencies
        if goal.dependencies:
            unmet_dependencies = 0
            for dep_id in goal.dependencies:
                if dep_id in self._active_goals:  # Dependency not completed
                    unmet_dependencies += 1

            if unmet_dependencies > 0:
                score *= 1.0 - (unmet_dependencies / len(goal.dependencies)) * 0.5

        return max(0.1, score)

    async def _calculate_alignment_score(
        self, goal: Goal, context: GoalContext
    ) -> float:
        """Calculate how well goal aligns with character state and traits."""
        score = 0.5

        # Threat-based adjustments
        if context.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            if goal.goal_type == GoalType.SURVIVAL:
                score = 0.95  # Survival is critical
            elif goal.goal_type == GoalType.COMBAT:
                score = 0.8  # Combat goals rise in priority
            elif goal.goal_type == GoalType.SOCIAL:
                score = 0.2  # Social goals drop
            elif goal.goal_type == GoalType.EXPLORATION:
                score = 0.15  # Exploration is risky
        elif context.threat_level == ThreatLevel.LOW:
            if goal.goal_type == GoalType.EXPLORATION:
                score = 0.8  # Safe to explore
            elif goal.goal_type == GoalType.SOCIAL:
                score = 0.75  # Good time for social
            elif goal.goal_type == GoalType.PERSONAL_GROWTH:
                score = 0.7  # Can focus on growth

        # Resource-based adjustments
        available_resources = context.available_resources or {}
        if goal.goal_type == GoalType.RESOURCE_GATHERING:
            # Higher priority if resources are low
            avg_resources = sum(available_resources.values()) / max(1, len(available_resources))
            if avg_resources < 0.3:
                score = max(score, 0.85)

        # Goal urgency adjustment
        if hasattr(goal, 'deadline') and goal.deadline:
            # Closer deadlines increase alignment
            score = min(1.0, score + 0.1)

        return max(0.1, min(1.0, score))

    async def _calculate_opportunity_score(
        self, goal: Goal, context: GoalContext
    ) -> float:
        """Calculate current opportunity level for achieving the goal."""
        score = 0.5

        # Location-based opportunities
        if context.current_location:
            if goal.goal_type == GoalType.EXPLORATION:
                # New locations are opportunities for exploration
                score = 0.75
            elif goal.goal_type == GoalType.RESOURCE_GATHERING:
                # Check if location has resources
                score = 0.6

        # Social opportunities
        nearby_entities = context.nearby_entities or []
        if goal.goal_type == GoalType.SOCIAL and len(nearby_entities) > 0:
            # More entities = more social opportunities
            score = min(0.9, 0.5 + len(nearby_entities) * 0.1)

        # Combat opportunities
        if goal.goal_type == GoalType.COMBAT:
            hostile_count = sum(1 for e in nearby_entities if "hostile" in str(e).lower())
            if hostile_count > 0:
                score = 0.8  # Combat targets available
            else:
                score = 0.2  # No combat opportunities

        # Knowledge opportunities
        if goal.goal_type == GoalType.KNOWLEDGE:
            # Check for information sources
            if any("library" in str(context.current_location).lower() or
                   "archive" in str(context.current_location).lower()
                   for _ in [1]):
                score = 0.85

        # Threat reduces most opportunities except survival/combat
        if context.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            if goal.goal_type not in [GoalType.SURVIVAL, GoalType.COMBAT]:
                score *= 0.5

        return max(0.1, min(1.0, score))

    async def _check_goal_completion(self, goal: Goal) -> None:
        """Check if goal should be marked as completed or failed."""
        try:
            # Check completion conditions
            if goal.progress >= 1.0 or self._check_success_conditions(goal):
                goal.status = GoalStatus.COMPLETED
                goal.last_updated = datetime.now().timestamp()

                # Move to completed goals
                if goal.goal_id in self._active_goals:
                    del self._active_goals[goal.goal_id]
                    self._completed_goals.append(goal)
                    self._metrics["goals_completed"] += 1

                self.logger.info(f"Goal completed: {goal.title}")

            # Check failure conditions
            elif self._check_failure_conditions(goal):
                goal.status = GoalStatus.FAILED
                goal.last_updated = datetime.now().timestamp()

                # Move to failed goals
                if goal.goal_id in self._active_goals:
                    del self._active_goals[goal.goal_id]
                    self._failed_goals.append(goal)
                    self._metrics["goals_failed"] += 1

                self.logger.info(f"Goal failed: {goal.title}")

        except Exception as e:
            self.logger.error(f"Goal completion check failed: {e}")

    def _check_success_conditions(self, goal: Goal) -> bool:
        """Check if goal's success conditions are met."""
        # This would check specific success conditions
        # For now, just check if all required actions are completed
        if goal.required_actions:
            return len(goal.completed_actions) >= len(goal.required_actions)
        return False

    def _check_failure_conditions(self, goal: Goal) -> bool:
        """Check if goal's failure conditions are met."""
        # Check for excessive setbacks
        major_setbacks = sum(
            1 for setback in goal.setbacks if setback.get("impact") == "major"
        )
        if major_setbacks >= 3:
            return True

        # Check for excessive time overruns
        if goal.is_overdue() and goal.get_age_hours() > 168:  # 1 week overdue
            return True

        return False

    def _serialize_goal(self, goal: Goal) -> Dict[str, Any]:
        """Serialize goal to dictionary for saving."""
        return {
            "goal_id": goal.goal_id,
            "goal_type": goal.goal_type.value,
            "title": goal.title,
            "description": goal.description,
            "priority": goal.priority.value,
            "status": goal.status.value,
            "progress": goal.progress,
            "required_actions": goal.required_actions,
            "completed_actions": goal.completed_actions,
            "created_at": goal.created_at,
            "deadline": goal.deadline,
            "last_updated": goal.last_updated,
            "success_conditions": goal.success_conditions,
            "failure_conditions": goal.failure_conditions,
            "dependencies": goal.dependencies,
            "importance_score": goal.importance_score,
            "motivation_factors": goal.motivation_factors,
            "attempts": goal.attempts,
            "setbacks": goal.setbacks,
        }

    def _deserialize_goal(self, goal_data: Dict[str, Any]) -> Goal:
        """Deserialize goal from dictionary."""
        return Goal(
            goal_id=goal_data["goal_id"],
            goal_type=GoalType(goal_data["goal_type"]),
            title=goal_data["title"],
            description=goal_data["description"],
            priority=GoalPriority(goal_data["priority"]),
            status=GoalStatus(goal_data["status"]),
            progress=goal_data["progress"],
            required_actions=goal_data["required_actions"],
            completed_actions=goal_data["completed_actions"],
            created_at=goal_data["created_at"],
            deadline=goal_data.get("deadline"),
            last_updated=goal_data["last_updated"],
            success_conditions=goal_data["success_conditions"],
            failure_conditions=goal_data["failure_conditions"],
            dependencies=goal_data["dependencies"],
            importance_score=goal_data["importance_score"],
            motivation_factors=goal_data["motivation_factors"],
            attempts=goal_data["attempts"],
            setbacks=goal_data["setbacks"],
        )

    def _initialize_goal_templates(self) -> None:
        """Initialize goal generation templates."""
        self._goal_templates = {
            "survival_threat": {
                "type": "survival",
                "priority": "critical",
                "title": "Ensure Personal Safety",
                "description": "Respond to immediate threat and ensure survival",
                "required_actions": [
                    "assess_threat",
                    "take_defensive_action",
                    "seek_safety",
                ],
                "motivation_factors": {"self_preservation": 1.0},
            },
            "resource_scarcity": {
                "type": "resource",
                "priority": "high",
                "title": "Acquire Essential Resources",
                "description": "Gather necessary resources for survival and operations",
                "required_actions": [
                    "identify_sources",
                    "plan_acquisition",
                    "execute_gathering",
                ],
                "motivation_factors": {
                    "resource_acquisition": 0.8,
                    "self_preservation": 0.6,
                },
            },
            "faction_mission": {
                "type": "faction",
                "priority": "high",
                "title": "Complete Faction Objective",
                "description": "Fulfill assigned mission or objective from faction leadership",
                "required_actions": [
                    "understand_mission",
                    "plan_approach",
                    "execute_mission",
                ],
                "motivation_factors": {"faction_loyalty": 0.9, "mission_success": 0.8},
            },
        }

    # Placeholder methods for future implementation

    async def _validate_goal_dependencies(self, goal: Goal) -> None:
        """Validate goal dependencies exist and are achievable.

        Checks that all dependency goal IDs exist and are in a state
        that allows the dependent goal to be pursued.
        """
        if not goal.dependencies:
            return

        completed_goal_ids = {g.goal_id for g in self._completed_goals}
        failed_goal_ids = {g.goal_id for g in self._failed_goals}

        for dep_id in goal.dependencies:
            # Check if dependency exists
            if dep_id in completed_goal_ids:
                # Dependency is already completed - good
                continue
            elif dep_id in self._active_goals:
                # Dependency is active - still achievable
                dep_goal = self._active_goals[dep_id]
                if dep_goal.status in (GoalStatus.ABANDONED, GoalStatus.PAUSED):
                    self.logger.warning(
                        f"Goal {goal.goal_id} depends on {dep_id} which is {dep_goal.status.value}"
                    )
            elif dep_id in failed_goal_ids:
                # Dependency failed - this goal may be unachievable
                self.logger.warning(
                    f"Goal {goal.goal_id} depends on failed goal {dep_id}"
                )
            else:
                # Dependency doesn't exist
                self.logger.warning(
                    f"Goal {goal.goal_id} has unknown dependency: {dep_id}"
                )

    async def _update_goal_relationships(self, goal: Goal) -> None:
        """Update relationships between goals.

        Tracks conflicts and synergies between goals based on goal types.
        Updates self._goal_relationships bidirectionally.
        """
        # Define goal type relationships
        # Synergies: goals that support each other
        synergies = {
            GoalType.SURVIVAL: [GoalType.RESOURCE, GoalType.TACTICAL],
            GoalType.COMBAT: [GoalType.TACTICAL, GoalType.STRATEGIC],
            GoalType.EXPLORATION: [GoalType.KNOWLEDGE, GoalType.RESOURCE],
            GoalType.SOCIAL: [GoalType.FACTION, GoalType.PERSONAL],
            GoalType.RESOURCE: [GoalType.SURVIVAL, GoalType.EXPLORATION],
            GoalType.KNOWLEDGE: [GoalType.EXPLORATION, GoalType.STRATEGIC],
            GoalType.FACTION: [GoalType.SOCIAL, GoalType.STRATEGIC],
            GoalType.PERSONAL: [GoalType.SOCIAL, GoalType.KNOWLEDGE],
            GoalType.TACTICAL: [GoalType.COMBAT, GoalType.SURVIVAL],
            GoalType.STRATEGIC: [GoalType.FACTION, GoalType.KNOWLEDGE],
        }

        # Initialize relationship list for this goal if not exists
        if goal.goal_id not in self._goal_relationships:
            self._goal_relationships[goal.goal_id] = []

        # Find related goals based on type synergies
        synergy_types = synergies.get(goal.goal_type, [])

        for other_goal in self._active_goals.values():
            if other_goal.goal_id == goal.goal_id:
                continue

            # Check for synergy
            if other_goal.goal_type in synergy_types:
                # Add bidirectional relationship
                if other_goal.goal_id not in self._goal_relationships[goal.goal_id]:
                    self._goal_relationships[goal.goal_id].append(other_goal.goal_id)

                if other_goal.goal_id not in self._goal_relationships:
                    self._goal_relationships[other_goal.goal_id] = []
                if goal.goal_id not in self._goal_relationships[other_goal.goal_id]:
                    self._goal_relationships[other_goal.goal_id].append(goal.goal_id)

            # Check for explicit dependencies
            if other_goal.goal_id in goal.dependencies:
                if other_goal.goal_id not in self._goal_relationships[goal.goal_id]:
                    self._goal_relationships[goal.goal_id].append(other_goal.goal_id)

    async def _update_goal_priorities(
        self, scored_goals: List[Tuple[Goal, float]]
    ) -> None:
        """Update goal priorities based on calculated scores.

        Maps scores (0.0-1.0) to GoalPriority enum values:
        - 0.8+: CRITICAL
        - 0.6-0.8: HIGH
        - 0.4-0.6: MEDIUM
        - 0.2-0.4: LOW
        - <0.2: MINIMAL

        Also updates the goal's last_updated timestamp.
        """
        for goal, score in scored_goals:
            # Map score to priority
            if score >= 0.8:
                new_priority = GoalPriority.CRITICAL
            elif score >= 0.6:
                new_priority = GoalPriority.HIGH
            elif score >= 0.4:
                new_priority = GoalPriority.MEDIUM
            elif score >= 0.2:
                new_priority = GoalPriority.LOW
            else:
                new_priority = GoalPriority.MINIMAL

            # Only update if priority changed
            if goal.priority != new_priority:
                self.logger.debug(
                    f"Goal {goal.goal_id} priority: {goal.priority.value} -> {new_priority.value} (score: {score:.2f})"
                )
                goal.priority = new_priority
                goal.last_updated = datetime.now().timestamp()

    async def _analyze_event_for_goals(
        self, event: WorldEvent, character_context: Dict[str, Any]
    ) -> List[str]:
        """Analyze event for goal generation opportunities."""
        opportunities = []

        if (
            event.event_type in ["attack", "battle"]
            and self.character_id in event.affected_entities
        ):
            opportunities.append("survival_threat")

        return opportunities

    async def _generate_goal_from_template(
        self, opportunity: str, event: WorldEvent, character_context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Generate goal data from template."""
        if opportunity not in self._goal_templates:
            return None

        template = self._goal_templates[opportunity].copy()
        template["description"] += f" (Generated from event: {event.event_id})"

        return template

    async def _filter_conflicting_goals(
        self, goals: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Filter out conflicting or duplicate goals."""
        # Simple deduplication by title for now
        seen_titles = set()
        filtered = []

        for goal in goals:
            if goal["title"] not in seen_titles:
                seen_titles.add(goal["title"])
                filtered.append(goal)

        return filtered
