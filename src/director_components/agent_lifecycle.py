"""
Agent Lifecycle Manager
=======================

Manages the complete lifecycle of agents in the simulation system.
Handles registration, validation, health monitoring, and cleanup.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional



@dataclass
class AgentMetrics:
    """Metrics for agent performance and health."""

    agent_id: str
    registration_time: datetime
    last_activity: datetime
    turn_count: int = 0
    error_count: int = 0
    avg_response_time: float = 0.0
    health_status: str = "healthy"


class AgentLifecycleManager:
    """
    Manages the complete lifecycle of agents in the simulation.

    Responsibilities:
    - Agent registration and deregistration
    - Agent health monitoring
    - Agent validation and diagnostics
    - Performance metrics tracking
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self._agents: Dict[str, Any] = {}
        self._agent_metrics: Dict[str, AgentMetrics] = {}
        self._agent_lock = asyncio.Lock()
        self._max_agents = 50  # Safety limit
        self._validation_cache: Dict[str, Dict[str, Any]] = {}

    async def initialize(self) -> bool:
        """Initialize agent lifecycle manager."""
        try:
            self.logger.info("Agent lifecycle manager initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Agent lifecycle manager initialization failed: {e}")
            return False

    async def register_agent(self, agent: Any) -> bool:
        """
        Register a new agent with comprehensive validation.

        Args:
            agent: Agent instance to register

        Returns:
            bool: True if registration successful, False otherwise
        """
        try:
            async with self._agent_lock:
                # Check if agent has required attributes
                if not hasattr(agent, "agent_id"):
                    self.logger.error("Agent missing required 'agent_id' attribute")
                    return False

                agent_id = agent.agent_id

                # Check for duplicate registration
                if agent_id in self._agents:
                    self.logger.warning(f"Agent {agent_id} already registered")
                    return False

                # Check agent limit
                if len(self._agents) >= self._max_agents:
                    self.logger.error(f"Agent limit reached ({self._max_agents})")
                    return False

                # Validate agent interface
                validation_result = await self._validate_agent_interface(agent)
                if not validation_result["valid"]:
                    self.logger.error(
                        f"Agent {agent_id} failed interface validation: {validation_result['errors']}"
                    )
                    return False

                # Register agent
                self._agents[agent_id] = agent
                self._agent_metrics[agent_id] = AgentMetrics(
                    agent_id=agent_id,
                    registration_time=datetime.now(),
                    last_activity=datetime.now(),
                )

                self.logger.info(f"Agent {agent_id} registered successfully")
                return True

        except Exception as e:
            self.logger.error(f"Failed to register agent: {e}")
            return False

    async def remove_agent(self, agent_id: str) -> bool:
        """
        Remove an agent from the system with cleanup.

        Args:
            agent_id: ID of agent to remove

        Returns:
            bool: True if removal successful, False otherwise
        """
        try:
            async with self._agent_lock:
                if agent_id not in self._agents:
                    self.logger.warning(f"Agent {agent_id} not found for removal")
                    return False

                # Cleanup agent resources
                agent = self._agents[agent_id]
                if hasattr(agent, "cleanup"):
                    try:
                        await agent.cleanup()
                    except Exception as e:
                        self.logger.warning(f"Agent {agent_id} cleanup failed: {e}")

                # Remove from tracking
                del self._agents[agent_id]
                del self._agent_metrics[agent_id]
                if agent_id in self._validation_cache:
                    del self._validation_cache[agent_id]

                self.logger.info(f"Agent {agent_id} removed successfully")
                return True

        except Exception as e:
            self.logger.error(f"Failed to remove agent {agent_id}: {e}")
            return False

    async def get_agent(self, agent_id: str) -> Optional[Any]:
        """Get agent by ID."""
        return self._agents.get(agent_id)

    async def list_agents(self) -> List[Any]:
        """Get list of all registered agents."""
        return list(self._agents.values())

    async def get_agent_ids(self) -> List[str]:
        """Get list of all agent IDs."""
        return list(self._agents.keys())

    async def validate_agents(self) -> Dict[str, Any]:
        """
        Validate all registered agents comprehensively.

        Returns:
            Dict containing validation results and agent health status
        """
        validation_results = {
            "valid_agents": [],
            "invalid_agents": [],
            "agent_count": len(self._agents),
            "health_summary": {},
            "errors": [],
        }

        try:
            for agent_id, agent in self._agents.items():
                agent_validation = await self._validate_single_agent(agent_id, agent)

                if agent_validation["valid"]:
                    validation_results["valid_agents"].append(agent_id)
                else:
                    validation_results["invalid_agents"].append(
                        {"agent_id": agent_id, "errors": agent_validation["errors"]}
                    )

                # Update health status
                metrics = self._agent_metrics.get(agent_id)
                if metrics:
                    if agent_validation["valid"]:
                        metrics.health_status = "healthy"
                    else:
                        metrics.health_status = "unhealthy"
                        metrics.error_count += 1

                validation_results["health_summary"][agent_id] = {
                    "status": metrics.health_status if metrics else "unknown",
                    "last_activity": (
                        metrics.last_activity.isoformat() if metrics else None
                    ),
                    "error_count": metrics.error_count if metrics else 0,
                }

        except Exception as e:
            self.logger.error(f"Agent validation failed: {e}")
            validation_results["errors"].append(str(e))

        return validation_results

    async def get_agent_metrics(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics for specific agent or all agents."""
        if agent_id:
            metrics = self._agent_metrics.get(agent_id)
            if metrics:
                return {
                    "agent_id": metrics.agent_id,
                    "registration_time": metrics.registration_time.isoformat(),
                    "last_activity": metrics.last_activity.isoformat(),
                    "turn_count": metrics.turn_count,
                    "error_count": metrics.error_count,
                    "avg_response_time": metrics.avg_response_time,
                    "health_status": metrics.health_status,
                }
            return {}

        # Return all metrics
        return {
            agent_id: {
                "agent_id": metrics.agent_id,
                "registration_time": metrics.registration_time.isoformat(),
                "last_activity": metrics.last_activity.isoformat(),
                "turn_count": metrics.turn_count,
                "error_count": metrics.error_count,
                "avg_response_time": metrics.avg_response_time,
                "health_status": metrics.health_status,
            }
            for agent_id, metrics in self._agent_metrics.items()
        }

    async def update_agent_activity(self, agent_id: str, response_time: float = 0.0):
        """Update agent activity metrics."""
        metrics = self._agent_metrics.get(agent_id)
        if metrics:
            metrics.last_activity = datetime.now()
            metrics.turn_count += 1
            if response_time > 0:
                # Update running average
                old_avg = metrics.avg_response_time
                count = metrics.turn_count
                metrics.avg_response_time = (
                    (old_avg * (count - 1)) + response_time
                ) / count

    async def _validate_agent_interface(self, agent: Any) -> Dict[str, Any]:
        """Validate agent has required interface methods."""
        required_methods = ["make_decision", "get_status"]
        required_attributes = ["agent_id", "character_data"]

        validation_result = {"valid": True, "errors": []}

        # Check required methods
        for method in required_methods:
            if not hasattr(agent, method) or not callable(getattr(agent, method)):
                validation_result["valid"] = False
                validation_result["errors"].append(
                    f"Missing or invalid method: {method}"
                )

        # Check required attributes
        for attr in required_attributes:
            if not hasattr(agent, attr):
                validation_result["valid"] = False
                validation_result["errors"].append(f"Missing attribute: {attr}")

        return validation_result

    async def _validate_single_agent(self, agent_id: str, agent: Any) -> Dict[str, Any]:
        """Validate a single agent's current state."""
        try:
            # Check if agent is still responsive
            if hasattr(agent, "get_status"):
                try:
                    status = await asyncio.wait_for(agent.get_status(), timeout=5.0)
                    if not status:
                        return {"valid": False, "errors": ["Agent status check failed"]}
                except asyncio.TimeoutError:
                    return {"valid": False, "errors": ["Agent status check timeout"]}
                except Exception as e:
                    return {"valid": False, "errors": [f"Agent status error: {str(e)}"]}

            # Basic interface validation
            return await self._validate_agent_interface(agent)

        except Exception as e:
            return {"valid": False, "errors": [f"Validation exception: {str(e)}"]}

    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        return {
            "total_agents": len(self._agents),
            "max_agents": self._max_agents,
            "utilization": len(self._agents) / self._max_agents,
            "agent_ids": list(self._agents.keys()),
            "healthy_agents": len(
                [
                    m
                    for m in self._agent_metrics.values()
                    if m.health_status == "healthy"
                ]
            ),
            "unhealthy_agents": len(
                [
                    m
                    for m in self._agent_metrics.values()
                    if m.health_status != "healthy"
                ]
            ),
            "avg_response_time": sum(
                m.avg_response_time for m in self._agent_metrics.values()
            )
            / max(1, len(self._agent_metrics)),
            "total_turns": sum(m.turn_count for m in self._agent_metrics.values()),
            "total_errors": sum(m.error_count for m in self._agent_metrics.values()),
        }

    async def cleanup(self) -> None:
        """Cleanup all agents and resources."""
        self.logger.info("Starting agent lifecycle cleanup...")

        async with self._agent_lock:
            for agent_id, agent in list(self._agents.items()):
                try:
                    if hasattr(agent, "cleanup"):
                        await agent.cleanup()
                except Exception as e:
                    self.logger.warning(f"Agent {agent_id} cleanup error: {e}")

            self._agents.clear()
            self._agent_metrics.clear()
            self._validation_cache.clear()

        self.logger.info("Agent lifecycle cleanup completed")
