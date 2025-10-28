#!/usr/bin/env python3
"""
Memory Interface
================

Handles agent memory systems and experience processing including:
- Memory system interface for internal and external memory
- Personal interpretation generation from experiences
- Relationship and worldview updates from experience
- Memory processing and persistence management

This component manages how agents learn, adapt, and remember experiences
while maintaining separation from decision-making and character interpretation.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List

# Configure logging
logger = logging.getLogger(__name__)


class MemoryInterface:
    """
    Manages agent memory systems and experience processing.

    Responsibilities:
    - Internal memory management (short-term and long-term)
    - Experience processing and interpretation
    - Relationship updates from experiences
    - Worldview adaptation based on new information
    - Memory persistence to file system
    - Memory retrieval and analysis
    """

    def __init__(self, agent_core: Any, character_directory_path: str):
        """
        Initialize the MemoryInterface.

        Args:
            agent_core: Reference to the PersonaAgentCore instance
            character_directory_path: Path to character directory for persistent memory
        """
        self.agent_core = agent_core
        self.character_directory_path = character_directory_path

        # Memory configuration
        self.short_term_memory_limit = 20
        self.long_term_memory_limit = 200
        self.significance_threshold = 0.6

        # Memory persistence
        self.memory_log_path = os.path.join(character_directory_path, "memory.log")

        # Experience processing counters
        self.experiences_processed = 0
        self.significant_experiences = 0

        logger.info(f"MemoryInterface initialized for agent {self.agent_core.agent_id}")

    def update_internal_memory(self, new_log: Dict[str, Any]) -> None:
        """
        Update the character's internal memory system with new experiences.

        This method simulates how characters learn and adapt from experiences,
        updating their knowledge, relationships, and behavioral patterns over time.

        The memory system manages:
        - Short-term memory: Recent events and observations (limited capacity)
        - Long-term memory: Important events that shape character development
        - Relationship updates: Changes in how character views other entities
        - Belief updates: How experiences modify character's worldview

        Args:
            new_log: Dictionary containing new experience/event information
                    Expected format:
                    {
                        'event_type': str,  # e.g., 'combat', 'dialogue', 'discovery'
                        'description': str,  # Human-readable description
                        'participants': List[str],  # Other entities involved
                        'outcome': str,  # Result of the event
                        'location': str,  # Where it happened
                        'timestamp': float,  # When it occurred
                        'significance': float,  # 0.0-1.0 importance level
                        'emotional_impact': str,  # Character's emotional response
                    }
        """
        try:
            logger.info(
                f"Agent {self.agent_core.agent_id} updating internal memory with new experience"
            )

            # Validate input format
            if not isinstance(new_log, dict):
                logger.warning(
                    f"Invalid memory log format for agent {self.agent_core.agent_id}"
                )
                return

            # Extract key information from the log
            event_type = new_log.get("event_type", "unknown")
            description = new_log.get("description", "")
            participants = new_log.get("participants", [])
            outcome = new_log.get("outcome", "")
            significance = new_log.get("significance", 0.5)
            emotional_impact = new_log.get("emotional_impact", "neutral")

            # Create memory entry
            memory_entry = {
                "timestamp": new_log.get("timestamp", datetime.now().timestamp()),
                "event_type": event_type,
                "description": description,
                "participants": participants,
                "outcome": outcome,
                "personal_interpretation": self._generate_personal_interpretation(
                    new_log
                ),
                "emotional_response": emotional_impact,
                "significance": significance,
                "processed_at": datetime.now().isoformat(),
            }

            # Add to short-term memory
            self.agent_core.short_term_memory.append(memory_entry)
            self._manage_short_term_memory_capacity()

            # Determine if this should be stored in long-term memory
            if self._should_store_in_long_term_memory(memory_entry):
                self.agent_core.long_term_memory.append(memory_entry)
                self.significant_experiences += 1
                self._manage_long_term_memory_capacity()
                logger.info(
                    f"Storing significant event in long-term memory for {self.agent_core.agent_id}"
                )

            # Update relationships based on the experience
            self._update_relationships_from_experience(new_log)

            # Update beliefs and worldview
            self._update_worldview_from_experience(new_log)

            # Update personality traits if this was a significant experience
            if significance > 0.7:
                self._update_personality_from_experience(new_log)

            # Update experience counters
            self.experiences_processed += 1

            # Log the memory update
            logger.info(
                f"Memory updated for {self.agent_core.agent_id}: {event_type} - {description[:50]}..."
            )

        except Exception as e:
            logger.error(
                f"Error updating internal memory for agent {self.agent_core.agent_id}: {str(e)}"
            )

    def update_memory(self, event_string: str) -> None:
        """
        Append a new event string to the memory.log file within the agent's directory.

        This method provides persistent memory logging by writing events to a memory.log
        file in the character's directory for long-term memory persistence across sessions.

        Args:
            event_string: String describing the event to be logged
        """
        try:
            # Create timestamp for the log entry
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Format the log entry
            log_entry = f"[{timestamp}] {event_string}\\n"

            # Append to memory.log file
            with open(self.memory_log_path, "a", encoding="utf-8") as file:
                file.write(log_entry)

            logger.debug(
                f"Persistent memory updated for {self.agent_core.agent_id}: {event_string[:50]}..."
            )

        except Exception as e:
            logger.error(
                f"Error updating persistent memory for agent {self.agent_core.agent_id}: {str(e)}"
            )

    def _generate_personal_interpretation(self, experience: Dict[str, Any]) -> str:
        """
        Generate personal interpretation of an experience based on character traits.

        Args:
            experience: Experience data to interpret

        Returns:
            Personal interpretation string from character's perspective
        """
        try:
            event_type = experience.get("event_type", "unknown")
            description = experience.get("description", "")
            outcome = experience.get("outcome", "")
            emotional_impact = experience.get("emotional_impact", "neutral")

            character_name = self.agent_core.character_name

            # Base interpretation
            interpretation = f"{character_name} experienced {event_type}"

            # Add emotional context
            if emotional_impact != "neutral":
                interpretation += f" and felt {emotional_impact}"

            # Add outcome perspective
            if outcome:
                # Interpret outcome based on character traits
                faction = getattr(self.agent_core, "faction", "Unknown")

                if "success" in outcome.lower():
                    if "entropy_cult" in faction.lower():
                        interpretation += ", viewing this success as another step toward greater entropy alignment"
                    elif "alliance_network" in faction.lower():
                        interpretation += (
                            ", seeing this success as service to the Founders' Council"
                        )
                    else:
                        interpretation += ", considering this a positive outcome"

                elif "failure" in outcome.lower():
                    if self.agent_core.morale_level > 0.5:
                        interpretation += ", but remains determined despite the setback"
                    else:
                        interpretation += ", feeling discouraged by this failure"

            # Add character-specific perspective
            if description:
                if (
                    "combat" in event_type.lower()
                    and self.agent_core.morale_level > 0.7
                ):
                    interpretation += (
                        ". The combat experience reinforced their resolve."
                    )
                elif "dialogue" in event_type.lower():
                    interpretation += ". The conversation provided valuable insights."
                elif "discovery" in event_type.lower():
                    interpretation += ". This discovery could prove useful."

            return interpretation

        except Exception as e:
            logger.error(f"Error generating personal interpretation: {str(e)}")
            return f"Character processed an experience of type {experience.get('event_type', 'unknown')}"

    def _should_store_in_long_term_memory(self, memory_entry: Dict[str, Any]) -> bool:
        """
        Determine if a memory entry should be stored in long-term memory.

        Args:
            memory_entry: Memory entry to evaluate

        Returns:
            bool: True if should be stored in long-term memory
        """
        try:
            significance = memory_entry.get("significance", 0.0)
            event_type = memory_entry.get("event_type", "")
            emotional_response = memory_entry.get("emotional_response", "neutral")
            participants = memory_entry.get("participants", [])

            # High significance events always go to long-term memory
            if significance >= self.significance_threshold:
                return True

            # Events with strong emotional responses
            strong_emotions = ["fear", "anger", "joy", "triumph", "betrayal", "loyalty"]
            if emotional_response.lower() in strong_emotions:
                return True

            # Combat and critical events
            critical_events = ["combat", "betrayal", "alliance", "discovery", "death"]
            if event_type.lower() in critical_events:
                return True

            # Events involving known characters (relationships)
            for participant in participants:
                if participant in self.agent_core.relationships:
                    return True

            return False

        except Exception as e:
            logger.error(f"Error determining long-term memory storage: {str(e)}")
            return False

    def _manage_short_term_memory_capacity(self) -> None:
        """Manage short-term memory capacity by removing oldest entries."""
        try:
            while len(self.agent_core.short_term_memory) > self.short_term_memory_limit:
                removed_entry = self.agent_core.short_term_memory.pop(0)
                logger.debug(
                    f"Removed old short-term memory entry: {removed_entry.get('event_type', 'unknown')}"
                )
        except Exception as e:
            logger.error(f"Error managing short-term memory capacity: {str(e)}")

    def _manage_long_term_memory_capacity(self) -> None:
        """Manage long-term memory capacity by removing less significant entries."""
        try:
            while len(self.agent_core.long_term_memory) > self.long_term_memory_limit:
                # Sort by significance and remove lowest
                self.agent_core.long_term_memory.sort(
                    key=lambda x: x.get("significance", 0.0), reverse=True
                )
                removed_entry = self.agent_core.long_term_memory.pop(-1)
                logger.debug(
                    f"Removed low-significance long-term memory entry: {removed_entry.get('event_type', 'unknown')}"
                )
        except Exception as e:
            logger.error(f"Error managing long-term memory capacity: {str(e)}")

    def _update_relationships_from_experience(self, experience: Dict[str, Any]) -> None:
        """
        Update character relationships based on experience.

        Args:
            experience: Experience data to process for relationship updates
        """
        try:
            event_type = experience.get("event_type", "")
            participants = experience.get("participants", [])
            outcome = experience.get("outcome", "")
            emotional_impact = experience.get("emotional_impact", "neutral")

            # Process relationship changes based on event type and outcome
            for participant in participants:
                if participant == self.agent_core.agent_id:
                    continue  # Skip self

                current_relationship = self.agent_core.get_relationship_strength(
                    participant
                )
                relationship_change = 0.0

                # Determine relationship change based on event type
                if event_type.lower() == "combat":
                    if "victory" in outcome.lower() or "success" in outcome.lower():
                        # Combat ally - strengthen bond
                        relationship_change = 0.1
                    elif "betrayal" in outcome.lower():
                        relationship_change = -0.5

                elif event_type.lower() == "dialogue":
                    if emotional_impact in ["positive", "agreement", "cooperation"]:
                        relationship_change = 0.15
                    elif emotional_impact in ["negative", "conflict", "disagreement"]:
                        relationship_change = -0.1

                elif event_type.lower() == "betrayal":
                    relationship_change = -0.7

                elif event_type.lower() == "alliance":
                    relationship_change = 0.5

                elif event_type.lower() == "cooperation":
                    relationship_change = 0.2

                # Apply relationship change
                if relationship_change != 0.0:
                    new_relationship = max(
                        -1.0, min(1.0, current_relationship + relationship_change)
                    )
                    self.agent_core.add_relationship(participant, new_relationship)

                    logger.debug(
                        f"Relationship with {participant} changed by {relationship_change} to {new_relationship}"
                    )

        except Exception as e:
            logger.error(f"Error updating relationships from experience: {str(e)}")

    def _update_worldview_from_experience(self, experience: Dict[str, Any]) -> None:
        """
        Update character's worldview based on experience.

        Args:
            experience: Experience data to process for worldview updates
        """
        try:
            event_type = experience.get("event_type", "")
            location = experience.get("location", "")
            experience.get("description", "")

            # Update location knowledge
            if location:
                location_info = {
                    "last_visited": datetime.now().isoformat(),
                    "experiences": [event_type],
                    "threat_level": self._assess_location_threat_from_experience(
                        experience
                    ),
                }

                self.agent_core.add_to_subjective_worldview(
                    "location_knowledge", location, location_info
                )

            # Update threat assessment
            if event_type.lower() in ["combat", "ambush", "attack"]:
                threat_info = {
                    "source": experience.get("participants", []),
                    "severity": experience.get("significance", 0.5),
                    "location": location,
                    "timestamp": datetime.now().isoformat(),
                }

                threat_id = f"{event_type}_{datetime.now().strftime('%H%M%S')}"
                self.agent_core.add_to_subjective_worldview(
                    "active_threats", threat_id, threat_info
                )

            # Update faction understanding
            participants = experience.get("participants", [])
            for participant in participants:
                if participant != self.agent_core.agent_id:
                    # Try to infer faction relationships
                    if "entropy_cult" in participant.lower():
                        faction_info = {"activity": "active", "threat_level": "high"}
                        self.agent_core.add_to_subjective_worldview(
                            "faction_relationships", "entropy_cult", faction_info
                        )
                    elif (
                        "alliance_network" in participant.lower()
                        or "alliance_network" in participant.lower()
                    ):
                        faction_info = {
                            "activity": "active",
                            "threat_level": "variable",
                        }
                        self.agent_core.add_to_subjective_worldview(
                            "faction_relationships", "alliance_network", faction_info
                        )

        except Exception as e:
            logger.error(f"Error updating worldview from experience: {str(e)}")

    def _assess_location_threat_from_experience(
        self, experience: Dict[str, Any]
    ) -> str:
        """
        Assess location threat level based on experience.

        Args:
            experience: Experience data

        Returns:
            str: Threat level assessment
        """
        try:
            event_type = experience.get("event_type", "")
            outcome = experience.get("outcome", "")
            significance = experience.get("significance", 0.0)

            if event_type.lower() in ["combat", "ambush", "attack"]:
                if significance > 0.7:
                    return "high"
                elif "failure" in outcome.lower() or "retreat" in outcome.lower():
                    return "high"
                else:
                    return "moderate"

            elif event_type.lower() in ["discovery", "exploration"]:
                return "low"

            else:
                return "unknown"

        except Exception:
            return "unknown"

    def _update_personality_from_experience(self, experience: Dict[str, Any]) -> None:
        """
        Update personality traits based on significant experiences.

        Args:
            experience: Significant experience data
        """
        try:
            event_type = experience.get("event_type", "")
            outcome = experience.get("outcome", "")
            emotional_impact = experience.get("emotional_impact", "neutral")

            # Personality adjustments are small but cumulative
            adjustment_factor = 0.02  # Small incremental changes

            if event_type.lower() == "combat":
                if "victory" in outcome.lower():
                    # Increase confidence/aggression slightly
                    current_aggression = self.agent_core.behavioral_modifiers.get(
                        "aggression", 0.5
                    )
                    self.agent_core.behavioral_modifiers["aggression"] = min(
                        1.0, current_aggression + adjustment_factor
                    )
                elif "defeat" in outcome.lower():
                    # Increase caution slightly
                    current_caution = self.agent_core.behavioral_modifiers.get(
                        "caution", 0.5
                    )
                    self.agent_core.behavioral_modifiers["caution"] = min(
                        1.0, current_caution + adjustment_factor
                    )

            elif event_type.lower() == "betrayal":
                # Increase suspicion/caution
                current_suspicion = self.agent_core.behavioral_modifiers.get(
                    "suspicion", 0.5
                )
                self.agent_core.behavioral_modifiers["suspicion"] = min(
                    1.0, current_suspicion + adjustment_factor * 2
                )

            elif event_type.lower() == "cooperation":
                if emotional_impact in ["positive", "success"]:
                    # Increase trust/cooperation tendency
                    current_cooperation = self.agent_core.behavioral_modifiers.get(
                        "cooperation", 0.5
                    )
                    self.agent_core.behavioral_modifiers["cooperation"] = min(
                        1.0, current_cooperation + adjustment_factor
                    )

        except Exception as e:
            logger.error(f"Error updating personality from experience: {str(e)}")

    def get_recent_memories(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent memories from short-term memory.

        Args:
            count: Number of recent memories to retrieve

        Returns:
            List of recent memory entries
        """
        try:
            recent_memories = (
                self.agent_core.short_term_memory[-count:]
                if self.agent_core.short_term_memory
                else []
            )
            return list(reversed(recent_memories))  # Most recent first
        except Exception as e:
            logger.error(f"Error getting recent memories: {str(e)}")
            return []

    def get_significant_memories(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get most significant memories from long-term memory.

        Args:
            count: Number of significant memories to retrieve

        Returns:
            List of significant memory entries sorted by importance
        """
        try:
            if not self.agent_core.long_term_memory:
                return []

            # Sort by significance and return top entries
            sorted_memories = sorted(
                self.agent_core.long_term_memory,
                key=lambda x: x.get("significance", 0.0),
                reverse=True,
            )
            return sorted_memories[:count]
        except Exception as e:
            logger.error(f"Error getting significant memories: {str(e)}")
            return []

    def search_memories(
        self, search_term: str, memory_type: str = "all"
    ) -> List[Dict[str, Any]]:
        """
        Search memories for specific content.

        Args:
            search_term: Term to search for in memory descriptions
            memory_type: 'short_term', 'long_term', or 'all'

        Returns:
            List of matching memory entries
        """
        try:
            matching_memories = []
            search_lower = search_term.lower()

            memories_to_search = []
            if memory_type in ["short_term", "all"]:
                memories_to_search.extend(self.agent_core.short_term_memory)
            if memory_type in ["long_term", "all"]:
                memories_to_search.extend(self.agent_core.long_term_memory)

            for memory in memories_to_search:
                description = memory.get("description", "").lower()
                event_type = memory.get("event_type", "").lower()
                personal_interpretation = memory.get(
                    "personal_interpretation", ""
                ).lower()

                if (
                    search_lower in description
                    or search_lower in event_type
                    or search_lower in personal_interpretation
                ):
                    matching_memories.append(memory)

            return matching_memories
        except Exception as e:
            logger.error(f"Error searching memories: {str(e)}")
            return []

    def get_memory_metrics(self) -> Dict[str, Any]:
        """
        Get memory system performance metrics.

        Returns:
            Dictionary containing memory metrics and statistics
        """
        try:
            return {
                "short_term_memory_count": len(self.agent_core.short_term_memory),
                "long_term_memory_count": len(self.agent_core.long_term_memory),
                "short_term_memory_limit": self.short_term_memory_limit,
                "long_term_memory_limit": self.long_term_memory_limit,
                "experiences_processed": self.experiences_processed,
                "significant_experiences": self.significant_experiences,
                "significance_threshold": self.significance_threshold,
                "memory_persistence_path": self.memory_log_path,
                "last_updated": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error generating memory metrics: {str(e)}")
            return {"error": str(e)}

    def load_persistent_memories(self) -> List[str]:
        """
        Load memories from persistent memory log file.

        Returns:
            List of memory log entries
        """
        try:
            if not os.path.exists(self.memory_log_path):
                return []

            with open(self.memory_log_path, "r", encoding="utf-8") as file:
                memory_lines = file.readlines()

            # Clean up memory lines
            memories = [line.strip() for line in memory_lines if line.strip()]
            logger.info(
                f"Loaded {len(memories)} persistent memories for {self.agent_core.agent_id}"
            )

            return memories
        except Exception as e:
            logger.error(f"Error loading persistent memories: {str(e)}")
            return []

    def clear_short_term_memory(self) -> None:
        """Clear all short-term memory entries."""
        try:
            count = len(self.agent_core.short_term_memory)
            self.agent_core.short_term_memory.clear()
            logger.info(
                f"Cleared {count} short-term memory entries for {self.agent_core.agent_id}"
            )
        except Exception as e:
            logger.error(f"Error clearing short-term memory: {str(e)}")

    def consolidate_memories(self) -> int:
        """
        Consolidate memories by promoting important short-term memories to long-term.

        Returns:
            Number of memories consolidated
        """
        try:
            consolidated_count = 0

            for memory in self.agent_core.short_term_memory.copy():
                if (
                    memory.get("significance", 0.0) >= self.significance_threshold
                    and memory not in self.agent_core.long_term_memory
                ):
                    self.agent_core.long_term_memory.append(memory)
                    consolidated_count += 1

            # Clean up capacity after consolidation
            self._manage_long_term_memory_capacity()

            logger.info(
                f"Consolidated {consolidated_count} memories to long-term for {self.agent_core.agent_id}"
            )
            return consolidated_count

        except Exception as e:
            logger.error(f"Error consolidating memories: {str(e)}")
            return 0
