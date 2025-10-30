#!/usr/bin/env python3
"""
AI Intelligence Integration Orchestrator
========================================

Lightweight coordinator that delegates specialized responsibilities to dedicated
coordinators following the Single Responsibility Principle.

Architecture:
    This class follows the Extract Class refactoring pattern, having been
    decomposed from a God Class (917 lines) into a focused orchestrator (679 lines)
    that delegates to specialized coordinators:

    - AISubsystemCoordinator: AI system lifecycle and narrative engine management
    - TraditionalSystemCoordinator: Traditional Novel Engine system coordination
    - MetricsCoordinator: Performance tracking and health monitoring
    - EventCoordinator: Cross-system event management
    - ContentGenerationCoordinator: Story content generation and enhancement
    - CharacterActionProcessor: Character action processing logic

Responsibilities:
    - High-level integration coordination and lifecycle management
    - Integration mode configuration and routing decisions
    - Coordinator initialization and dependency injection
    - Backward-compatible API access via property delegation
    - System status aggregation across all coordinators

Features:
    - Seamless integration between traditional and AI systems
    - Multiple integration modes (traditional, AI-enhanced, AI-first, full AI)
    - Progressive AI feature activation with feature gates
    - Graceful fallback between system modes
    - Comprehensive performance monitoring
    - Event-driven cross-system coordination
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from src.core.data_models import (
    CharacterState,
    DynamicContext,
    ErrorInfo,
    StandardResponse,
)

# Import Novel Engine core systems
from src.core.event_coordinator import EventCoordinator
from src.core.metrics_coordinator import IntegrationMetrics, MetricsCoordinator
from src.core.system_orchestrator import OrchestratorConfig, SystemOrchestrator
from src.core.traditional_system_coordinator import TraditionalSystemCoordinator
from src.event_bus import EventBus

from .agent_coordination_engine import AgentContext

# Import AI intelligence systems
from .ai_orchestrator import (
    AIIntelligenceOrchestrator,
    AISystemConfig,
    IntelligenceLevel,
)
from .ai_subsystem_coordinator import AISubsystemCoordinator
from .analytics_platform import AnalyticsEvent
from .character_action_processor import CharacterActionProcessor
from .content_generation_coordinator import ContentGenerationCoordinator
from .recommendation_engine import UserProfile

logger = logging.getLogger(__name__)


class IntegrationMode(Enum):
    """Integration operation modes."""

    TRADITIONAL_ONLY = "traditional_only"  # Use only traditional systems
    AI_ENHANCED = "ai_enhanced"  # AI enhancements with traditional fallback
    AI_FIRST = "ai_first"  # AI systems with traditional support
    FULL_AI = "full_ai"  # Complete AI intelligence mode
    EXPERIMENTAL = "experimental"  # Experimental AI features enabled


class SystemIntegrationLevel(Enum):
    """Levels of system integration between traditional and AI systems."""

    ISOLATED = "isolated"  # Systems operate independently
    COORDINATED = "coordinated"  # Basic coordination and data sharing
    INTEGRATED = "integrated"  # Deep integration with shared workflows
    UNIFIED = "unified"  # Fully unified operation


@dataclass
class IntegrationConfig:
    """Configuration for AI intelligence integration."""

    integration_mode: IntegrationMode = IntegrationMode.AI_ENHANCED
    integration_level: SystemIntegrationLevel = SystemIntegrationLevel.INTEGRATED
    enable_progressive_activation: bool = True
    enable_fallback_systems: bool = True
    enable_performance_monitoring: bool = True
    enable_cross_system_validation: bool = True
    ai_feature_gates: Dict[str, bool] = field(
        default_factory=lambda: {
            "agent_coordination": True,
            "story_quality": True,
            "analytics": True,
            "recommendations": True,
            "export_integration": True,
        }
    )
    traditional_system_timeout: float = 30.0  # seconds
    ai_system_timeout: float = 45.0  # seconds
    fallback_threshold: float = 0.1  # Error rate threshold for fallback
    performance_threshold: float = 2.0  # Response time threshold (seconds)


class IntegrationOrchestrator:
    """
    Lightweight integration orchestrator coordinating specialized subsystem coordinators.

    This class serves as the high-level coordinator following the Facade pattern,
    delegating specific responsibilities to specialized coordinators while maintaining
    a unified interface for backward compatibility.

    Architecture Pattern:
        Follows the Extract Class refactoring pattern to eliminate God Class anti-pattern.
        Original class (917 lines) decomposed into focused coordinators with clear
        separation of concerns.

    Coordinators:
        - event_coordinator: Cross-system event management (EventCoordinator)
        - metrics_coordinator: Performance tracking and health (MetricsCoordinator)
        - traditional_coordinator: Traditional system orchestration (TraditionalSystemCoordinator)
        - ai_coordinator: AI system lifecycle management (AISubsystemCoordinator)
        - action_processor: Character action processing (CharacterActionProcessor)
        - content_coordinator: Story content generation (ContentGenerationCoordinator)

    Integration Modes:
        TRADITIONAL_ONLY: Use only traditional Novel Engine systems
        AI_ENHANCED: AI enhancements with traditional fallback (default)
        AI_FIRST: AI systems primary with traditional support
        FULL_AI: Complete AI intelligence mode
        EXPERIMENTAL: Experimental AI features enabled

    Attributes:
        config (IntegrationConfig): Integration configuration and feature gates
        integration_active (bool): Whether integration is currently active

    Example:
        >>> config = IntegrationConfig(integration_mode=IntegrationMode.AI_ENHANCED)
        >>> orchestrator = IntegrationOrchestrator(integration_config=config)
        >>> await orchestrator.startup()
        >>> result = await orchestrator.generate_story_content("Epic quest", "user123")
        >>> await orchestrator.shutdown()
    """

    def __init__(
        self,
        database_path: str = "data/context_engineering.db",
        orchestrator_config: Optional[OrchestratorConfig] = None,
        integration_config: Optional[IntegrationConfig] = None,
    ):
        """
        Initialize the integration orchestrator and all subsystem coordinators.

        Creates and wires all specialized coordinators with proper dependency injection,
        establishing the integration architecture with event bus sharing and configuration
        propagation.

        Args:
            database_path: Path to the Novel Engine database file.
            orchestrator_config: Configuration for traditional SystemOrchestrator.
                                If None, default configuration will be used.
            integration_config: Integration configuration including mode and feature gates.
                               If None, defaults to AI_ENHANCED mode with all features enabled.

        Coordinators Initialized:
            1. EventCoordinator: Manages cross-system event bus and subscriptions
            2. MetricsCoordinator: Tracks performance metrics and system health
            3. TraditionalSystemCoordinator: Manages traditional Novel Engine systems
            4. AISubsystemCoordinator: Manages AI intelligence systems and narrative engine
            5. CharacterActionProcessor: Processes character actions with fallback logic
            6. ContentGenerationCoordinator: Generates and enhances story content

        Note:
            All coordinators share the same event bus instance for cross-system coordination.
            Configuration is propagated to coordinators that need access to integration settings.
        """
        self.config = integration_config or IntegrationConfig()

        # Integration state
        self.integration_active = False

        # Initialize event coordinator (Extract Class pattern)
        self.event_coordinator = EventCoordinator()

        # Initialize metrics coordinator (Extract Class pattern)
        self.metrics_coordinator = MetricsCoordinator()

        # Initialize traditional system coordinator (Extract Class pattern)
        self.traditional_coordinator = TraditionalSystemCoordinator(
            database_path=database_path,
            orchestrator_config=orchestrator_config,
        )

        # Initialize AI subsystem coordinator (Extract Class pattern)
        ai_config = AISystemConfig(
            intelligence_level=self._map_integration_to_intelligence_level(),
            enable_agent_coordination=self.config.ai_feature_gates.get(
                "agent_coordination", True
            ),
            enable_story_quality=self.config.ai_feature_gates.get(
                "story_quality", True
            ),
            enable_analytics=self.config.ai_feature_gates.get("analytics", True),
            enable_recommendations=self.config.ai_feature_gates.get(
                "recommendations", True
            ),
            enable_export_integration=self.config.ai_feature_gates.get(
                "export_integration", True
            ),
        )
        self.ai_coordinator = AISubsystemCoordinator(
            event_bus=self.event_coordinator.get_event_bus(),
            ai_config=ai_config,
            ai_feature_gates=self.config.ai_feature_gates,
        )

        # Initialize character action processor (Extract Class pattern)
        self.action_processor = CharacterActionProcessor(
            system_orchestrator=self.traditional_coordinator.system_orchestrator,
            ai_orchestrator=self.ai_coordinator.ai_orchestrator,
            config=self.config,
        )

        # Initialize content generation coordinator (Extract Class pattern)
        self.content_coordinator = ContentGenerationCoordinator(
            ai_coordinator=self.ai_coordinator,
            config=self.config,
        )

        logger.info("Integration Orchestrator initialized successfully")

    # ===================================================================
    # Property Methods for AI Subsystem Availability (Delegated)
    # ===================================================================

    @property
    def has_recommendation_engine(self) -> bool:
        """Check if recommendation engine is available (delegated to coordinator)."""
        return self.ai_coordinator.has_recommendation_engine

    @property
    def has_story_quality_engine(self) -> bool:
        """Check if story quality engine is available (delegated to coordinator)."""
        return self.ai_coordinator.has_story_quality_engine

    @property
    def has_analytics_platform(self) -> bool:
        """Check if analytics platform is available (delegated to coordinator)."""
        return self.ai_coordinator.has_analytics_platform

    @property
    def narrative_engine_v2(self):
        """Access to narrative engine V2 (delegated to coordinator)."""
        return self.ai_coordinator.narrative_engine_v2

    @property
    def current_arc_state(self):
        """Access to current arc state (delegated to coordinator)."""
        return self.ai_coordinator.current_arc_state

    @property
    def system_orchestrator(self):
        """Access to traditional system orchestrator (delegated to coordinator)."""
        return self.traditional_coordinator.system_orchestrator

    @property
    def startup_time(self):
        """Access to startup time (delegated to metrics coordinator)."""
        return self.metrics_coordinator.startup_time

    @property
    def operation_count(self):
        """Access to operation count (delegated to metrics coordinator)."""
        return self.metrics_coordinator.operation_count

    @property
    def error_count(self):
        """Access to error count (delegated to metrics coordinator)."""
        return self.metrics_coordinator.error_count

    @property
    def response_times(self):
        """Access to response times (delegated to metrics coordinator)."""
        return self.metrics_coordinator.response_times

    @property
    def metrics_history(self):
        """Access to metrics history (delegated to metrics coordinator)."""
        return self.metrics_coordinator.metrics_history

    @property
    def event_bus(self):
        """Access to event bus (delegated to event coordinator)."""
        return self.event_coordinator.get_event_bus()

    # ===================================================================
    # Startup Helper Methods (Extract Method Pattern)
    # ===================================================================
    # These methods break down the complex startup() logic into smaller,
    # focused methods following Single Responsibility Principle.
    # ===================================================================

    async def _startup_traditional_systems(self) -> StandardResponse:
        """
        Start traditional system orchestrator (delegated to coordinator).

        Returns:
            StandardResponse: Result of traditional system startup
        """
        return await self.traditional_coordinator.startup_traditional_systems()

    async def _startup_ai_systems(self) -> StandardResponse:
        """
        Start AI intelligence orchestrator (delegated to coordinator).

        Returns:
            StandardResponse: Result of AI system startup
        """
        return await self.ai_coordinator.startup_ai_systems()

    def _evaluate_integration_success(
        self, traditional_result: StandardResponse, ai_result: StandardResponse
    ) -> tuple[bool, bool]:
        """
        Determine integration success based on integration mode.

        Args:
            traditional_result: Result from traditional system startup
            ai_result: Result from AI system startup

        Returns:
            tuple[bool, bool]: (integration_success, ai_available)
        """
        if self.config.integration_mode == IntegrationMode.TRADITIONAL_ONLY:
            # Traditional only mode - AI failure is acceptable
            integration_success = traditional_result.success
            ai_available = ai_result.success

        elif self.config.integration_mode in [
            IntegrationMode.AI_FIRST,
            IntegrationMode.FULL_AI,
        ]:
            # AI-first modes - both must succeed
            integration_success = traditional_result.success and ai_result.success
            ai_available = ai_result.success

        else:
            # AI-enhanced mode - traditional must succeed, AI failure triggers fallback
            integration_success = traditional_result.success
            ai_available = ai_result.success

            if not ai_result.success:
                logger.warning(
                    "AI systems failed to start, operating in traditional mode"
                )

        return integration_success, ai_available

    async def _finalize_startup(self) -> None:
        """
        Finalize startup by setting up coordination and monitoring.

        Sets integration_active flag and starts monitoring systems.
        """
        self.integration_active = True

        # Set up cross-system event coordination (delegated to coordinator)
        await self.event_coordinator.setup_event_coordination(
            character_state_handler=self.event_coordinator.handle_character_state_change,
            story_generation_handler=self.event_coordinator.handle_story_generation,
            user_interaction_handler=self.event_coordinator.handle_user_interaction,
        )

        # Start integration monitoring
        await self._start_integration_monitoring()

        logger.info("Integration Orchestrator startup completed successfully")

    def _build_startup_success_response(self, ai_available: bool) -> StandardResponse:
        """
        Build successful startup response with system status.

        Args:
            ai_available: Whether AI systems are available

        Returns:
            StandardResponse: Success response with startup details
        """
        return StandardResponse(
            success=True,
            data={
                "integration_mode": self.config.integration_mode.value,
                "traditional_available": True,
                "ai_available": ai_available,
                "integration_level": self.config.integration_level.value,
                "startup_time": self.startup_time,
                "feature_gates": self.config.ai_feature_gates,
            },
        )

    def _build_startup_failure_response(
        self, traditional_success: bool, ai_success: bool
    ) -> StandardResponse:
        """
        Build failure response when integration startup fails.

        Args:
            traditional_success: Whether traditional system started
            ai_success: Whether AI system started

        Returns:
            StandardResponse: Failure response with error details
        """
        return StandardResponse(
            success=False,
            error=ErrorInfo(
                code="INTEGRATION_STARTUP_FAILED",
                message="Integration orchestrator startup failed",
                details={
                    "traditional_success": traditional_success,
                    "ai_success": ai_success,
                },
            ),
        )

    # ===================================================================
    # System Lifecycle Methods
    # ===================================================================

    async def startup(self) -> StandardResponse:
        """Start both traditional and AI systems with integration coordination."""
        try:
            logger.info("Starting Integration Orchestrator startup sequence")

            # Start traditional systems
            traditional_result = await self._startup_traditional_systems()
            if not traditional_result.success:
                return traditional_result

            # Start AI systems
            ai_result = await self._startup_ai_systems()

            # Evaluate integration success based on mode
            integration_success, ai_available = self._evaluate_integration_success(
                traditional_result, ai_result
            )

            # Finalize and return response
            if integration_success:
                await self._finalize_startup()
                return self._build_startup_success_response(ai_available)
            else:
                return self._build_startup_failure_response(
                    traditional_result.success, ai_result.success
                )

        except Exception as e:
            logger.error(f"Critical error during integration startup: {str(e)}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="INTEGRATION_STARTUP_ERROR",
                    message="Integration startup error",
                    details={"exception": str(e)},
                ),
            )

    async def shutdown(self) -> StandardResponse:
        """Gracefully shutdown both system types."""
        try:
            logger.info("Starting Integration Orchestrator shutdown sequence")

            # Stop integration monitoring
            self.integration_active = False

            # Shutdown AI systems first (delegated to coordinator)
            ai_shutdown_response = await self.ai_coordinator.shutdown_ai_systems()

            # Shutdown traditional systems (delegated to coordinator)
            traditional_result = (
                await self.traditional_coordinator.shutdown_traditional_systems()
            )

            # Generate final integration metrics
            final_metrics = await self._generate_integration_metrics()

            logger.info("Integration Orchestrator shutdown completed successfully")

            return StandardResponse(
                success=True,
                data={
                    "shutdown_time": datetime.now(),
                    "uptime_seconds": self.metrics_coordinator.get_uptime_seconds(),
                    "total_operations": self.metrics_coordinator.operation_count,
                    "ai_shutdown": ai_shutdown_response.success,
                    "traditional_shutdown": traditional_result.success,
                    "final_metrics": final_metrics,
                },
            )

        except Exception as e:
            logger.error(f"Error during integration shutdown: {str(e)}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="INTEGRATION_SHUTDOWN_ERROR",
                    message="Integration shutdown error",
                    details={"exception": str(e)},
                ),
            )

    async def process_character_action(
        self, agent_id: str, action: str, context: Optional[Dict[str, Any]] = None
    ) -> StandardResponse:
        """
        Process character action with AI enhancement and fallback coordination.

        Delegates to CharacterActionProcessor for actual processing logic.
        """
        try:
            start_time = datetime.now()

            # Delegate to action processor based on integration mode
            if self.config.integration_mode == IntegrationMode.TRADITIONAL_ONLY:
                result = await self.action_processor.process_traditional_action(
                    agent_id, action, context
                )
            elif self.config.integration_mode == IntegrationMode.FULL_AI:
                result = await self.action_processor.process_ai_enhanced_action(
                    agent_id, action, context
                )
            else:
                # AI_ENHANCED or AI_FIRST - try AI first with fallback
                result = await self.action_processor.process_hybrid_action(
                    agent_id, action, context
                )

            # Track performance (delegated to metrics coordinator)
            response_time = (datetime.now() - start_time).total_seconds()
            self.metrics_coordinator.record_operation(response_time, result.success)

            # Emit integration event (delegated to coordinator)
            await self.event_coordinator.emit_integration_event(
                "character_action_processed",
                {
                    "agent_id": agent_id,
                    "action": action,
                    "success": result.success,
                    "response_time": response_time,
                    "processing_mode": self.config.integration_mode.value,
                },
            )

            return result

        except Exception as e:
            logger.error(f"Error processing character action for {agent_id}: {str(e)}")
            self.metrics_coordinator.record_error()
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="CHARACTER_ACTION_ERROR",
                    message="Character action processing failed",
                    details={
                        "agent_id": agent_id,
                        "action": action,
                        "exception": str(e),
                    },
                ),
            )

    def get_narrative_guidance(self) -> Dict[str, Any]:
        """
        Get current narrative guidance from the V2 Narrative Engine (delegated to coordinator).

        Returns:
            Dictionary containing narrative objectives, tension targets, and pacing info
        """
        return self.ai_coordinator.get_narrative_guidance()

    async def generate_story_content(
        self, prompt: str, user_id: str, preferences: Optional[Dict[str, Any]] = None
    ) -> StandardResponse:
        """
        Generate story content with AI quality analysis and recommendations.

        Demonstrates integration between story generation, quality analysis,
        and user preference systems. Delegates to ContentGenerationCoordinator.
        """
        try:
            start_time = datetime.now()

            # Get narrative guidance from V2 engine
            narrative_guidance = self.get_narrative_guidance()

            # Generate base content using traditional or AI systems (delegated to coordinator)
            if self.config.integration_mode == IntegrationMode.TRADITIONAL_ONLY:
                content_result = (
                    await self.content_coordinator.generate_traditional_content(
                        prompt, user_id
                    )
                )
            else:
                content_result = (
                    await self.content_coordinator.generate_ai_enhanced_content(
                        prompt, user_id, preferences, narrative_guidance
                    )
                )

            if not content_result.success:
                return content_result

            # Apply AI enhancements if available (delegated to coordinator)
            enhanced_result = await self.content_coordinator.apply_ai_enhancements(
                content_result.data, user_id, preferences
            )

            # Track performance and analytics
            response_time = (datetime.now() - start_time).total_seconds()
            self.metrics_coordinator.record_operation(
                response_time, enhanced_result.success
            )
            await self.content_coordinator.track_story_generation_analytics(
                user_id, prompt, response_time, enhanced_result.success
            )

            # Update narrative state after turn completion (delegated to coordinator)
            turn_outcome = {
                "success": enhanced_result.success,
                "response_time": response_time,
                "content_length": len(content_result.data.get("content", "")),
            }
            self.ai_coordinator.report_turn_completion(turn_outcome=turn_outcome)

            return enhanced_result

        except Exception as e:
            logger.error(f"Error generating story content: {str(e)}")
            self.metrics_coordinator.record_error()
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="STORY_GENERATION_ERROR",
                    message="Story generation failed",
                    details={"prompt": prompt[:100], "exception": str(e)},
                ),
            )

    async def get_system_status(self) -> StandardResponse:
        """Get comprehensive status of both traditional and AI systems."""
        try:
            # Get traditional system metrics (delegated to coordinator)
            traditional_metrics = (
                await self.traditional_coordinator.get_traditional_system_metrics()
            )

            # Get AI system status (delegated to coordinator)
            ai_dashboard = await self.ai_coordinator.get_system_dashboard()
            ai_status = StandardResponse(success=True, data=ai_dashboard)

            # Generate integration metrics (delegated to coordinator)
            integration_metrics = (
                await self.metrics_coordinator.generate_integration_metrics(
                    integration_mode=self.config.integration_mode.value
                )
            )
            metrics_summary = self.metrics_coordinator.get_metrics_summary()

            return StandardResponse(
                success=True,
                data={
                    "integration_config": {
                        "mode": self.config.integration_mode.value,
                        "level": self.config.integration_level.value,
                        "active": self.integration_active,
                    },
                    "traditional_system": (
                        traditional_metrics.data
                        if traditional_metrics.success
                        else None
                    ),
                    "ai_system": ai_status.data if ai_status.success else None,
                    "integration_metrics": integration_metrics,
                    **metrics_summary,
                },
            )

        except Exception as e:
            logger.error(f"Error getting system status: {str(e)}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="SYSTEM_STATUS_ERROR",
                    message="System status retrieval failed",
                    details={"exception": str(e)},
                ),
            )

    # Private methods for system coordination and integration

    async def _setup_event_coordination(self):
        """Set up event coordination between traditional and AI systems (delegated to coordinator)."""
        await self.event_coordinator.setup_event_coordination(
            character_state_handler=self.event_coordinator.handle_character_state_change,
            story_generation_handler=self.event_coordinator.handle_story_generation,
            user_interaction_handler=self.event_coordinator.handle_user_interaction,
        )

    async def _start_integration_monitoring(self):
        """Start background monitoring of integration performance."""
        # This would typically start background tasks for monitoring
        pass

    async def _generate_integration_metrics(self) -> IntegrationMetrics:
        """Generate current integration performance metrics (delegated to coordinator)."""
        return await self.metrics_coordinator.generate_integration_metrics(
            integration_mode=self.config.integration_mode.value
        )

    async def _emit_integration_event(self, event_type: str, data: Dict[str, Any]):
        """Emit integration event for monitoring and coordination (delegated to coordinator)."""
        await self.event_coordinator.emit_integration_event(event_type, data)

    def _map_integration_to_intelligence_level(self) -> IntelligenceLevel:
        """Map integration mode to AI intelligence level."""
        mapping = {
            IntegrationMode.TRADITIONAL_ONLY: IntelligenceLevel.BASIC,
            IntegrationMode.AI_ENHANCED: IntelligenceLevel.STANDARD,
            IntegrationMode.AI_FIRST: IntelligenceLevel.ADVANCED,
            IntegrationMode.FULL_AI: IntelligenceLevel.ADVANCED,
            IntegrationMode.EXPERIMENTAL: IntelligenceLevel.EXPERIMENTAL,
        }
        return mapping.get(self.config.integration_mode, IntelligenceLevel.STANDARD)


# Export main class
__all__ = [
    "IntegrationOrchestrator",
    "IntegrationConfig",
    "IntegrationMode",
    "SystemIntegrationLevel",
]
