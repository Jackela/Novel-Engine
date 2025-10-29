"""
Narrative Orchestrator
======================

Manages narrative events, story context, and narrative flow coordination.
Handles story state, event processing, and narrative context generation.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional



class EventType(Enum):
    """Types of narrative events."""

    CHARACTER_ACTION = "character_action"
    WORLD_CHANGE = "world_change"
    DIALOGUE = "dialogue"
    CONFLICT = "conflict"
    RESOLUTION = "resolution"
    DISCOVERY = "discovery"
    TRANSITION = "transition"


@dataclass
class NarrativeEvent:
    """Represents a narrative event."""

    event_id: str
    event_type: EventType
    timestamp: datetime
    participants: List[str] = field(default_factory=list)
    location: Optional[str] = None
    description: str = ""
    impact_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StoryContext:
    """Context information for story generation."""

    current_scene: str = "unknown"
    active_characters: List[str] = field(default_factory=list)
    location: str = "unknown"
    mood: str = "neutral"
    tension_level: float = 0.5
    narrative_threads: List[str] = field(default_factory=list)
    recent_events: List[str] = field(default_factory=list)


class NarrativeOrchestrator:
    """
    Orchestrates narrative events and manages story flow.

    Responsibilities:
    - Process narrative events
    - Generate story context
    - Manage narrative threads
    - Track story progression
    - Coordinate with world state
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

        # Story state
        self._story_state: Dict[str, Any] = {}
        self._narrative_events: List[NarrativeEvent] = []
        self._active_threads: Dict[str, Any] = {}
        self._character_contexts: Dict[str, StoryContext] = {}

        # Configuration
        self._max_events_history = 500
        self._max_threads = 20
        self._context_window_size = 10  # Recent events to consider

        # Story tracking
        self._story_statistics = {
            "total_events": 0,
            "events_by_type": {},
            "active_characters": set(),
            "story_progression": 0.0,
        }

        # Thread management
        self._thread_lock = asyncio.Lock()

    async def initialize(self) -> bool:
        """Initialize narrative orchestrator."""
        try:
            # Initialize story state
            self._story_state = self._create_default_story_state()

            # Setup event type counters
            for event_type in EventType:
                self._story_statistics["events_by_type"][event_type.value] = 0

            self.logger.info("Narrative orchestrator initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Narrative orchestrator initialization failed: {e}")
            return False

    async def generate_narrative_context(self, agent_id: str) -> Dict[str, Any]:
        """
        Generate narrative context for a specific agent.

        Args:
            agent_id: ID of agent requesting context

        Returns:
            Dict containing narrative context
        """
        try:
            # Get recent events relevant to this agent
            relevant_events = await self._get_relevant_events(agent_id)

            # Get current story context
            story_context = self._character_contexts.get(agent_id, StoryContext())

            # Generate context
            context = {
                "agent_id": agent_id,
                "current_scene": story_context.current_scene,
                "location": story_context.location,
                "mood": story_context.mood,
                "tension_level": story_context.tension_level,
                "recent_events": [
                    {
                        "type": event.event_type.value,
                        "description": event.description,
                        "participants": event.participants,
                        "impact": event.impact_score,
                        "timestamp": event.timestamp.isoformat(),
                    }
                    for event in relevant_events
                ],
                "active_threads": await self._get_agent_threads(agent_id),
                "narrative_opportunities": await self._identify_narrative_opportunities(
                    agent_id
                ),
                "world_context": await self._get_world_narrative_context(),
            }

            self.logger.debug(f"Generated narrative context for agent {agent_id}")
            return context

        except Exception as e:
            self.logger.error(
                f"Failed to generate narrative context for {agent_id}: {e}"
            )
            return {"error": str(e), "agent_id": agent_id}

    async def process_narrative_events(
        self, events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process a batch of narrative events.

        Args:
            events: List of event dictionaries to process

        Returns:
            Dict containing processing results
        """
        try:
            processed_events = []
            failed_events = []

            for event_data in events:
                try:
                    # Create narrative event
                    narrative_event = await self._create_narrative_event(event_data)

                    if narrative_event:
                        # Process the event
                        await self._process_single_event(narrative_event)
                        processed_events.append(narrative_event.event_id)

                        # Update statistics
                        self._update_event_statistics(narrative_event)
                    else:
                        failed_events.append(
                            {"data": event_data, "error": "Failed to create event"}
                        )

                except Exception as e:
                    failed_events.append({"data": event_data, "error": str(e)})

            # Update story progression
            await self._update_story_progression()

            # Manage event history
            await self._manage_event_history()

            result = {
                "success": True,
                "processed_count": len(processed_events),
                "failed_count": len(failed_events),
                "processed_events": processed_events,
                "failed_events": failed_events,
                "story_progression": self._story_statistics["story_progression"],
            }

            self.logger.info(
                f"Processed {len(processed_events)} narrative events, {len(failed_events)} failed"
            )
            return result

        except Exception as e:
            self.logger.error(f"Narrative event processing failed: {e}")
            return {"success": False, "error": str(e)}

    async def update_story_state(self, updates: Dict[str, Any]) -> None:
        """
        Update story state with new information.

        Args:
            updates: Dictionary of story state updates
        """
        try:
            for key, value in updates.items():
                if key in self._story_state:
                    (
                        self._story_state[key].update(value)
                        if isinstance(self._story_state[key], dict)
                        else None
                    )
                    self._story_state[key] = (
                        value
                        if not isinstance(self._story_state[key], dict)
                        else self._story_state[key]
                    )
                else:
                    self._story_state[key] = value

            # Update character contexts if character data changed
            if "characters" in updates:
                await self._update_character_contexts(updates["characters"])

            self.logger.debug(f"Story state updated with {len(updates)} changes")

        except Exception as e:
            self.logger.error(f"Failed to update story state: {e}")
            raise

    async def get_story_summary(self) -> Dict[str, Any]:
        """Get comprehensive story summary."""
        try:
            recent_events = (
                self._narrative_events[-20:] if self._narrative_events else []
            )

            return {
                "story_state": self._story_state.copy(),
                "statistics": self._story_statistics.copy(),
                "active_threads_count": len(self._active_threads),
                "total_events": len(self._narrative_events),
                "recent_events": [
                    {
                        "id": event.event_id,
                        "type": event.event_type.value,
                        "description": event.description,
                        "impact": event.impact_score,
                        "timestamp": event.timestamp.isoformat(),
                    }
                    for event in recent_events
                ],
                "character_count": len(self._character_contexts),
                "narrative_health": await self._calculate_narrative_health(),
            }

        except Exception as e:
            self.logger.error(f"Failed to get story summary: {e}")
            return {"error": str(e)}

    async def _get_relevant_events(
        self, agent_id: str, limit: int = 10
    ) -> List[NarrativeEvent]:
        """Get events relevant to specific agent."""
        relevant_events = []

        for event in reversed(self._narrative_events[-50:]):  # Check last 50 events
            if agent_id in event.participants or event.event_type in [
                EventType.WORLD_CHANGE,
                EventType.TRANSITION,
            ]:
                relevant_events.append(event)

                if len(relevant_events) >= limit:
                    break

        return relevant_events

    async def _get_agent_threads(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get narrative threads involving specific agent."""
        agent_threads = []

        async with self._thread_lock:
            for thread_id, thread_data in self._active_threads.items():
                if agent_id in thread_data.get("participants", []):
                    agent_threads.append(
                        {
                            "thread_id": thread_id,
                            "type": thread_data.get("type", "unknown"),
                            "status": thread_data.get("status", "active"),
                            "description": thread_data.get("description", ""),
                            "urgency": thread_data.get("urgency", 0.5),
                        }
                    )

        return agent_threads

    async def _identify_narrative_opportunities(
        self, agent_id: str
    ) -> List[Dict[str, Any]]:
        """Identify narrative opportunities for agent."""
        opportunities = []

        # Check for unresolved conflicts
        for event in self._narrative_events[-20:]:
            if (
                event.event_type == EventType.CONFLICT
                and agent_id in event.participants
                and event.metadata.get("resolved", False) is False
            ):
                opportunities.append(
                    {
                        "type": "resolve_conflict",
                        "description": f"Resolve conflict: {event.description}",
                        "priority": 0.8,
                        "event_id": event.event_id,
                    }
                )

        # Check for discovery opportunities
        story_context = self._character_contexts.get(agent_id, StoryContext())
        if story_context.tension_level > 0.7:
            opportunities.append(
                {
                    "type": "tension_release",
                    "description": "High tension situation - opportunity for dramatic action",
                    "priority": 0.9,
                }
            )

        return opportunities

    async def _get_world_narrative_context(self) -> Dict[str, Any]:
        """Get world-level narrative context."""
        return {
            "overall_mood": self._story_state.get("mood", "neutral"),
            "time_of_day": self._story_state.get("time", "unknown"),
            "weather": self._story_state.get("weather", "clear"),
            "major_events_today": len(
                [e for e in self._narrative_events[-50:] if e.impact_score > 0.7]
            ),
            "story_phase": self._determine_story_phase(),
        }

    async def _create_narrative_event(
        self, event_data: Dict[str, Any]
    ) -> Optional[NarrativeEvent]:
        """Create narrative event from data."""
        try:
            event_type_str = event_data.get("type", "character_action")
            event_type = EventType(event_type_str)

            event = NarrativeEvent(
                event_id=event_data.get(
                    "id", f"event_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
                ),
                event_type=event_type,
                timestamp=datetime.now(),
                participants=event_data.get("participants", []),
                location=event_data.get("location"),
                description=event_data.get("description", ""),
                impact_score=event_data.get("impact", 0.5),
                metadata=event_data.get("metadata", {}),
            )

            return event

        except (ValueError, KeyError) as e:
            self.logger.warning(f"Invalid event data: {e}")
            return None

    async def _process_single_event(self, event: NarrativeEvent) -> None:
        """Process a single narrative event."""
        # Add to event history
        self._narrative_events.append(event)

        # Update character contexts
        for participant in event.participants:
            await self._update_character_context(participant, event)

        # Update narrative threads
        await self._update_narrative_threads(event)

        # Update story statistics
        self._story_statistics["total_events"] += 1
        self._story_statistics["active_characters"].update(event.participants)

    async def _update_character_context(
        self, character_id: str, event: NarrativeEvent
    ) -> None:
        """Update character context with event information."""
        if character_id not in self._character_contexts:
            self._character_contexts[character_id] = StoryContext()

        context = self._character_contexts[character_id]

        # Update location if specified
        if event.location:
            context.location = event.location

        # Update mood based on event type and impact
        if event.event_type == EventType.CONFLICT:
            context.tension_level = min(
                1.0, context.tension_level + event.impact_score * 0.3
            )
            context.mood = "tense"
        elif event.event_type == EventType.RESOLUTION:
            context.tension_level = max(
                0.0, context.tension_level - event.impact_score * 0.4
            )
            context.mood = "relieved"

        # Add to recent events
        context.recent_events.append(event.event_id)
        if len(context.recent_events) > self._context_window_size:
            context.recent_events = context.recent_events[-self._context_window_size :]

    async def _update_narrative_threads(self, event: NarrativeEvent) -> None:
        """Update narrative threads based on event."""
        async with self._thread_lock:
            # Create new thread for conflicts
            if event.event_type == EventType.CONFLICT:
                thread_id = f"conflict_{event.event_id}"
                self._active_threads[thread_id] = {
                    "type": "conflict",
                    "status": "active",
                    "description": event.description,
                    "participants": event.participants,
                    "created_at": event.timestamp.isoformat(),
                    "urgency": event.impact_score,
                    "source_event": event.event_id,
                }

            # Close threads for resolutions
            elif event.event_type == EventType.RESOLUTION:
                threads_to_close = []
                for thread_id, thread_data in self._active_threads.items():
                    if any(
                        p in event.participants
                        for p in thread_data.get("participants", [])
                    ):
                        threads_to_close.append(thread_id)

                for thread_id in threads_to_close:
                    self._active_threads[thread_id]["status"] = "resolved"
                    self._active_threads[thread_id]["resolved_by"] = event.event_id

    def _update_event_statistics(self, event: NarrativeEvent) -> None:
        """Update event statistics."""
        self._story_statistics["events_by_type"][event.event_type.value] += 1
        self._story_statistics["active_characters"].update(event.participants)

    async def _update_story_progression(self) -> None:
        """Update overall story progression metric."""
        if not self._narrative_events:
            return

        # Simple progression based on event impact
        total_impact = sum(event.impact_score for event in self._narrative_events[-50:])
        event_count = len(self._narrative_events[-50:])

        if event_count > 0:
            avg_impact = total_impact / event_count
            self._story_statistics["story_progression"] = min(1.0, avg_impact * 0.8)

    async def _manage_event_history(self) -> None:
        """Manage event history size."""
        if len(self._narrative_events) > self._max_events_history:
            # Keep most recent events
            self._narrative_events = self._narrative_events[-self._max_events_history :]
            self.logger.debug("Trimmed narrative event history")

        # Clean up resolved threads
        async with self._thread_lock:
            if len(self._active_threads) > self._max_threads:
                resolved_threads = {
                    k: v
                    for k, v in self._active_threads.items()
                    if v.get("status") == "resolved"
                }

                if resolved_threads:
                    # Remove oldest resolved threads
                    sorted_resolved = sorted(
                        resolved_threads.items(),
                        key=lambda x: x[1].get("created_at", ""),
                    )

                    threads_to_remove = len(self._active_threads) - self._max_threads
                    for thread_id, _ in sorted_resolved[:threads_to_remove]:
                        del self._active_threads[thread_id]

    async def _update_character_contexts(
        self, character_updates: Dict[str, Any]
    ) -> None:
        """Update character contexts with new character data."""
        for character_id, character_data in character_updates.items():
            if character_id not in self._character_contexts:
                self._character_contexts[character_id] = StoryContext()

            context = self._character_contexts[character_id]
            context.active_characters.append(character_id)

            # Update context based on character data
            if "location" in character_data:
                context.location = character_data["location"]

    async def _calculate_narrative_health(self) -> Dict[str, Any]:
        """Calculate narrative system health metrics."""
        if not self._narrative_events:
            return {"status": "no_data", "score": 0.0}

        recent_events = self._narrative_events[-20:]

        # Calculate various health metrics
        event_diversity = len(set(e.event_type for e in recent_events)) / len(EventType)
        avg_impact = sum(e.impact_score for e in recent_events) / len(recent_events)
        participant_diversity = len(
            set(p for e in recent_events for p in e.participants)
        )

        health_score = (
            event_diversity * 0.4
            + avg_impact * 0.4
            + min(1.0, participant_diversity / 5.0) * 0.2
        )

        return {
            "status": (
                "healthy"
                if health_score > 0.6
                else "degraded" if health_score > 0.3 else "poor"
            ),
            "score": health_score,
            "event_diversity": event_diversity,
            "average_impact": avg_impact,
            "participant_diversity": participant_diversity,
            "active_threads": len(self._active_threads),
        }

    def _determine_story_phase(self) -> str:
        """Determine current story phase."""
        if not self._narrative_events:
            return "beginning"

        total_events = len(self._narrative_events)
        recent_conflicts = sum(
            1
            for e in self._narrative_events[-20:]
            if e.event_type == EventType.CONFLICT
        )
        recent_resolutions = sum(
            1
            for e in self._narrative_events[-20:]
            if e.event_type == EventType.RESOLUTION
        )

        if total_events < 20:
            return "beginning"
        elif recent_conflicts > recent_resolutions:
            return "rising_action"
        elif recent_resolutions > recent_conflicts:
            return "resolution"
        else:
            return "development"

    def _create_default_story_state(self) -> Dict[str, Any]:
        """Create default story state structure."""
        return {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "story_id": f"story_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "version": "1.0",
            },
            "setting": {
                "time_period": "present",
                "location": "default_location",
                "mood": "neutral",
                "theme": "adventure",
            },
            "plot": {
                "current_act": 1,
                "major_conflicts": [],
                "resolved_conflicts": [],
                "active_subplots": [],
            },
            "characters": {},
            "world": {"locations": {}, "factions": {}, "relationships": {}},
        }

    async def export_narrative_data(self, export_path: str) -> bool:
        """Export narrative data for analysis."""
        try:
            export_data = {
                "story_state": self._story_state,
                "events": [
                    {
                        "id": event.event_id,
                        "type": event.event_type.value,
                        "timestamp": event.timestamp.isoformat(),
                        "participants": event.participants,
                        "location": event.location,
                        "description": event.description,
                        "impact": event.impact_score,
                        "metadata": event.metadata,
                    }
                    for event in self._narrative_events
                ],
                "threads": self._active_threads,
                "statistics": {
                    **self._story_statistics,
                    "active_characters": list(
                        self._story_statistics["active_characters"]
                    ),
                },
                "export_metadata": {
                    "exported_at": datetime.now().isoformat(),
                    "total_events": len(self._narrative_events),
                    "total_threads": len(self._active_threads),
                },
            }

            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Narrative data exported to {export_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to export narrative data: {e}")
            return False

    async def cleanup(self) -> None:
        """Cleanup narrative orchestrator resources."""
        try:
            # Clear data structures
            self._narrative_events.clear()
            self._active_threads.clear()
            self._character_contexts.clear()
            self._story_state.clear()

            self.logger.info("Narrative orchestrator cleanup completed")

        except Exception as e:
            self.logger.error(f"Narrative orchestrator cleanup error: {e}")
