#!/usr/bin/env python3
"""
Agent Lifecycle Manager
=======================

Manages agent registration, deregistration, and lifecycle events.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional


class AgentLifecycleManager:
    """
    Manages agent registration, deregistration, and lifecycle events.

    Responsibilities:
    - Agent registration and validation
    - Lifecycle tracking and monitoring
    - Agent health checks
    - Resource cleanup
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize agent lifecycle manager."""
        self.logger = logger or logging.getLogger(__name__)
        self.agents = {}  # agent_id -> agent instance
        self.agent_metadata = {}  # agent_id -> metadata
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize the agent manager."""
        try:
            self.logger.info("Initializing AgentLifecycleManager")
            self._initialized = True
            return True
        except Exception as e:
            self.logger.error(
                f"AgentLifecycleManager initialization failed: {e}"
            )
            return False

    async def register_agent(self, agent: Any) -> bool:
        """
        Register a new agent.

        Args:
            agent: Agent instance to register

        Returns:
            bool: True if registration successful
        """
        try:
            if not hasattr(agent, "agent_id"):
                self.logger.error("Agent missing agent_id attribute")
                return False

            agent_id = agent.agent_id

            if agent_id in self.agents:
                self.logger.warning(
                    f"Agent {agent_id} already registered, replacing"
                )

            self.agents[agent_id] = agent
            self.agent_metadata[agent_id] = {
                "registration_time": datetime.now(),
                "last_activity": datetime.now(),
                "status": "active",
                "error_count": 0,
            }

            self.logger.info(f"Agent {agent_id} registered successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to register agent: {e}")
            return False

    async def deregister_agent(self, agent_id: str) -> bool:
        """Deregister an agent."""
        try:
            if agent_id in self.agents:
                del self.agents[agent_id]
                del self.agent_metadata[agent_id]
                self.logger.info(f"Agent {agent_id} deregistered")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to deregister agent {agent_id}: {e}")
            return False

    async def get_system_status(self) -> Dict[str, Any]:
        """Get system status for all agents."""
        return {
            "agent_count": len(self.agents),
            "active_agents": [
                aid
                for aid, meta in self.agent_metadata.items()
                if meta["status"] == "active"
            ],
            "initialized": self._initialized,
        }

    async def cleanup(self) -> None:
        """Cleanup all agents."""
        self.logger.info("Cleaning up AgentLifecycleManager")
        self.agents.clear()
        self.agent_metadata.clear()
