#!/usr/bin/env python3
"""
System Orchestrator for Novel Engine
===================================

Unified system orchestrator that coordinates all components
of the dynamic context engineering framework and provides comprehensive
API for intelligent agent interactions.

Architecture Reference: Dynamic Context Engineering - Master Orchestrator
Development Phase: System Integration (S001)
Author: Novel Engine Development Team
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol

import structlog

# Import data models
from src.core.data_models import (
    StandardResponse,
)

# Import core narrative engines

# Import database access - TYPE_CHECKING only to avoid circular dependencies
# At runtime, database is injected via dependency injection
if TYPE_CHECKING:
    pass


# Import all subsystems


# Define Protocol for database interface to enable dependency injection
# This ensures SystemOrchestrator doesn't directly depend on ContextDatabase
class DatabaseInterface(Protocol):
    """Protocol defining database operations required by SystemOrchestrator."""

    async def initialize_standard_temple(self) -> StandardResponse:
        """Initialize database schema and connections."""
        ...

    async def close_standard_temple(self) -> None:
        """Close database connections."""
        ...

    async def health_check(self) -> Dict[str, Any]:
        """Check database health status."""
        ...

    async def register_enhanced_agent(
        self,
        agent_id: str,
        character_name: str,
        faction_data: List[str],
        personality_traits: List[str],
        core_beliefs: List[str],
    ) -> StandardResponse:
        """Register a new agent in the database."""
        ...

    def get_enhanced_connection(self) -> None:
        """Get an async database connection context manager."""
        ...

# Comprehensive logging and monitoring
logger = structlog.get_logger(__name__)


class OrchestratorMode(Enum):
    """Orchestrator Operational Modes"""

    AUTONOMOUS = "autonomous"  # Full autonomous operation
    INTERACTIVE = "interactive"  # Human-guided interactions
    SIMULATION = "simulation"  # Simulation mode for testing
    DEVELOPMENT = "development"  # Development and debugging mode
    PRODUCTION = "production"  # Production deployment mode
    TESTING = "testing"  # Fast startup for E2E/integration tests


class SystemHealth(Enum):
    """System Health Status States"""

    OPTIMAL = "optimal"  # All systems functioning perfectly
    DEGRADED = "degraded"  # Some systems experiencing issues
    CRITICAL = "critical"  # Critical systems failing
    EMERGENCY = "emergency"  # Emergency shutdown required
    MAINTENANCE = "maintenance"  # Scheduled maintenance mode


@dataclass
class OrchestratorConfig:
    """
    Orchestrator Configuration Parameters

    Comprehensive configuration for system orchestrator with performance
    tuning, operational modes, and system integration parameters.
    """

    mode: OrchestratorMode = OrchestratorMode.AUTONOMOUS
    max_concurrent_agents: int = 10
    memory_cleanup_interval: int = 3600  # seconds
    template_cache_size: int = 100
    interaction_queue_size: int = 50
    equipment_maintenance_interval: int = 1800  # seconds
    relationship_decay_interval: int = 86400  # seconds (daily)
    health_check_interval: int = 300  # seconds
    auto_save_interval: int = 600  # seconds
    debug_logging: bool = False
    enable_metrics: bool = True
    enable_auto_backup: bool = True
    backup_interval: int = 7200  # seconds
    max_memory_items_per_agent: int = 10000
    max_interaction_history: int = 1000
    enable_cross_system_validation: bool = True
    performance_monitoring: bool = True


@dataclass
class SystemMetrics:
    """
    System Performance Metrics

    Comprehensive system performance and health metrics for monitoring
    and optimization of the dynamic context engineering framework.
    """

    timestamp: datetime = field(default_factory=datetime.now)
    active_agents: int = 0
    total_memory_items: int = 0
    active_interactions: int = 0
    template_cache_hits: float = 0.0
    average_response_time: float = 0.0
    system_health: SystemHealth = SystemHealth.OPTIMAL
    database_connections: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    error_rate: float = 0.0
    last_backup: Optional[datetime] = None
    uptime_seconds: int = 0
    operations_per_minute: float = 0.0
    relationship_count: int = 0
    equipment_count: int = 0


