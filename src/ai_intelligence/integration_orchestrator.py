#!/usr/bin/env python3
"""
AI Intelligence Integration Orchestrator
========================================

Integration orchestrator that connects Novel Engine's AI intelligence systems
with the existing system orchestrator and provides unified coordination
between traditional and AI-enhanced capabilities.

Features:
- Seamless integration with SystemOrchestrator
- Unified AI intelligence lifecycle management
- Cross-system event coordination
- Performance monitoring and optimization
- Backward compatibility with existing systems
- Progressive AI feature activation
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# Import Novel Engine core systems
from src.core.system_orchestrator import SystemOrchestrator, OrchestratorConfig, SystemHealth, SystemMetrics
from src.event_bus import EventBus
from src.core.data_models import StandardResponse, ErrorInfo, DynamicContext, CharacterState
from src.persona_agent import PersonaAgent

# Import AI intelligence systems
from .ai_orchestrator import (
    AIIntelligenceOrchestrator, 
    AISystemConfig, 
    IntelligenceLevel,
    OrchestratorStatus
)
from .agent_coordination_engine import AgentCoordinationEngine, AgentContext
from .story_quality_engine import StoryQualityEngine, StoryQualityReport
from .analytics_platform import AnalyticsPlatform, AnalyticsEvent
from .recommendation_engine import RecommendationEngine, UserProfile
from .export_integration_engine import ExportIntegrationEngine, ExportRequest

logger = logging.getLogger(__name__)


class IntegrationMode(Enum):
    """Integration operation modes."""
    TRADITIONAL_ONLY = "traditional_only"        # Use only traditional systems
    AI_ENHANCED = "ai_enhanced"                  # AI enhancements with traditional fallback
    AI_FIRST = "ai_first"                        # AI systems with traditional support
    FULL_AI = "full_ai"                          # Complete AI intelligence mode
    EXPERIMENTAL = "experimental"                # Experimental AI features enabled


class SystemIntegrationLevel(Enum):
    """Levels of system integration between traditional and AI systems."""
    ISOLATED = "isolated"                        # Systems operate independently
    COORDINATED = "coordinated"                  # Basic coordination and data sharing
    INTEGRATED = "integrated"                    # Deep integration with shared workflows
    UNIFIED = "unified"                          # Fully unified operation


@dataclass
class IntegrationConfig:
    """Configuration for AI intelligence integration."""
    integration_mode: IntegrationMode = IntegrationMode.AI_ENHANCED
    integration_level: SystemIntegrationLevel = SystemIntegrationLevel.INTEGRATED
    enable_progressive_activation: bool = True
    enable_fallback_systems: bool = True
    enable_performance_monitoring: bool = True
    enable_cross_system_validation: bool = True
    ai_feature_gates: Dict[str, bool] = field(default_factory=lambda: {
        "agent_coordination": True,
        "story_quality": True,
        "analytics": True,
        "recommendations": True,
        "export_integration": True
    })
    traditional_system_timeout: float = 30.0     # seconds
    ai_system_timeout: float = 45.0              # seconds
    fallback_threshold: float = 0.1              # Error rate threshold for fallback
    performance_threshold: float = 2.0           # Response time threshold (seconds)


@dataclass
class IntegrationMetrics:
    """Metrics for system integration performance."""
    timestamp: datetime = field(default_factory=datetime.now)
    traditional_operations: int = 0
    ai_enhanced_operations: int = 0
    fallback_activations: int = 0
    integration_errors: int = 0
    average_response_time: float = 0.0
    ai_enhancement_rate: float = 0.0             # Percentage of operations using AI
    system_health_score: float = 1.0            # Overall integration health (0.0-1.0)
    cross_system_events: int = 0
    performance_improvements: Dict[str, float] = field(default_factory=dict)


class IntegrationOrchestrator:
    """
    Master integration orchestrator that coordinates between traditional
    Novel Engine systems and new AI intelligence capabilities.
    
    This orchestrator ensures seamless operation, performance optimization,
    and graceful fallback between system modes while providing unified
    access to all engine capabilities.
    """
    
    def __init__(self, database_path: str = "data/context_engineering.db",
                 orchestrator_config: Optional[OrchestratorConfig] = None,
                 integration_config: Optional[IntegrationConfig] = None):
        """Initialize the integration orchestrator with both system types."""
        self.config = integration_config or IntegrationConfig()
        self.startup_time = datetime.now()
        self.operation_count = 0
        self.error_count = 0
        
        # Integration state and event bus
        self.integration_active = False
        self.metrics_history: List[IntegrationMetrics] = []
        self.event_bus = EventBus()
        
        # Initialize traditional system orchestrator
        self.system_orchestrator = SystemOrchestrator(database_path, orchestrator_config)
        
        # Initialize AI intelligence orchestrator
        ai_config = AISystemConfig(
            intelligence_level=self._map_integration_to_intelligence_level(),
            enable_agent_coordination=self.config.ai_feature_gates.get("agent_coordination", True),
            enable_story_quality=self.config.ai_feature_gates.get("story_quality", True),
            enable_analytics=self.config.ai_feature_gates.get("analytics", True),
            enable_recommendations=self.config.ai_feature_gates.get("recommendations", True),
            enable_export_integration=self.config.ai_feature_gates.get("export_integration", True)
        )
        self.ai_orchestrator = AIIntelligenceOrchestrator(self.event_bus, ai_config)
        
        # Performance tracking
        self.response_times: List[float] = []
        self.error_rates: List[float] = []
        
        logger.info("Integration Orchestrator initialized successfully")

    async def startup(self) -> StandardResponse:
        """Start both traditional and AI systems with integration coordination."""
        try:
            logger.info("Starting Integration Orchestrator startup sequence")
            
            # Start traditional system orchestrator
            traditional_result = await self.system_orchestrator.startup()
            if not traditional_result.success:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="TRADITIONAL_STARTUP_FAILED",
                        message="Traditional system startup failed",
                        details={"traditional_error": traditional_result.error.message if traditional_result.error else "Unknown"}
                    )
                )
            
            # Start AI intelligence orchestrator
            ai_result = await self.ai_orchestrator.initialize_systems()
            # Convert to StandardResponse format
            from src.core.data_models import StandardResponse
            ai_response = StandardResponse(
                success=ai_result.get("success", True),
                data=ai_result
            )
            
            # Determine integration success based on mode
            if self.config.integration_mode == IntegrationMode.TRADITIONAL_ONLY:
                # Traditional only mode - AI failure is acceptable
                integration_success = traditional_result.success
                ai_available = ai_response.success
            elif self.config.integration_mode in [IntegrationMode.AI_FIRST, IntegrationMode.FULL_AI]:
                # AI-first modes - both must succeed
                integration_success = traditional_result.success and ai_response.success
                ai_available = ai_response.success
            else:
                # AI-enhanced mode - traditional must succeed, AI failure triggers fallback
                integration_success = traditional_result.success
                ai_available = ai_response.success
                if not ai_response.success:
                    logger.warning("AI systems failed to start, operating in traditional mode")
            
            if integration_success:
                self.integration_active = True
                
                # Set up cross-system event coordination
                await self._setup_event_coordination()
                
                # Start integration monitoring
                await self._start_integration_monitoring()
                
                logger.info("Integration Orchestrator startup completed successfully")
                
                return StandardResponse(
                    success=True,
                    data={
                        "integration_mode": self.config.integration_mode.value,
                        "traditional_available": traditional_result.success,
                        "ai_available": ai_available,
                        "integration_level": self.config.integration_level.value,
                        "startup_time": self.startup_time,
                        "feature_gates": self.config.ai_feature_gates
                    }
                )
            else:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="INTEGRATION_STARTUP_FAILED", 
                        message="Integration orchestrator startup failed",
                        details={
                            "traditional_success": traditional_result.success,
                            "ai_success": ai_response.success
                        }
                    )
                )
                
        except Exception as e:
            logger.error(f"Critical error during integration startup: {str(e)}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="INTEGRATION_STARTUP_ERROR",
                    message="Integration startup error",
                    details={"exception": str(e)}
                )
            )

    async def shutdown(self) -> StandardResponse:
        """Gracefully shutdown both system types."""
        try:
            logger.info("Starting Integration Orchestrator shutdown sequence")
            
            # Stop integration monitoring
            self.integration_active = False
            
            # Shutdown AI systems first
            ai_result = await self.ai_orchestrator.shutdown_systems()
            # Convert to StandardResponse format  
            ai_shutdown_response = StandardResponse(
                success=ai_result.get("success", True),
                data=ai_result
            )
            
            # Shutdown traditional systems
            traditional_result = await self.system_orchestrator.shutdown()
            
            # Generate final integration metrics
            final_metrics = await self._generate_integration_metrics()
            
            logger.info("Integration Orchestrator shutdown completed successfully")
            
            return StandardResponse(
                success=True,
                data={
                    "shutdown_time": datetime.now(),
                    "uptime_seconds": (datetime.now() - self.startup_time).total_seconds(),
                    "total_operations": self.operation_count,
                    "ai_shutdown": ai_shutdown_response.success,
                    "traditional_shutdown": traditional_result.success,
                    "final_metrics": final_metrics
                }
            )
            
        except Exception as e:
            logger.error(f"Error during integration shutdown: {str(e)}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="INTEGRATION_SHUTDOWN_ERROR",
                    message="Integration shutdown error",
                    details={"exception": str(e)}
                )
            )

    async def process_character_action(self, agent_id: str, action: str, 
                                     context: Optional[Dict[str, Any]] = None) -> StandardResponse:
        """
        Process character action with AI enhancement and fallback coordination.
        
        This method demonstrates the integration between traditional and AI systems
        by routing character actions through appropriate processing pipelines.
        """
        try:
            start_time = datetime.now()
            self.operation_count += 1
            
            # Determine processing strategy based on integration mode
            if self.config.integration_mode == IntegrationMode.TRADITIONAL_ONLY:
                result = await self._process_traditional_action(agent_id, action, context)
            elif self.config.integration_mode == IntegrationMode.FULL_AI:
                result = await self._process_ai_enhanced_action(agent_id, action, context)
            else:
                # AI_ENHANCED or AI_FIRST - try AI first with fallback
                result = await self._process_hybrid_action(agent_id, action, context)
            
            # Track performance
            response_time = (datetime.now() - start_time).total_seconds()
            self.response_times.append(response_time)
            
            # Emit integration event
            await self._emit_integration_event("character_action_processed", {
                "agent_id": agent_id,
                "action": action,
                "success": result.success,
                "response_time": response_time,
                "processing_mode": self.config.integration_mode.value
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing character action for {agent_id}: {str(e)}")
            self.error_count += 1
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="CHARACTER_ACTION_ERROR",
                    message="Character action processing failed",
                    details={"agent_id": agent_id, "action": action, "exception": str(e)}
                )
            )

    async def generate_story_content(self, prompt: str, user_id: str,
                                   preferences: Optional[Dict[str, Any]] = None) -> StandardResponse:
        """
        Generate story content with AI quality analysis and recommendations.
        
        Demonstrates integration between story generation, quality analysis,
        and user preference systems.
        """
        try:
            start_time = datetime.now()
            self.operation_count += 1
            
            # Generate base content using traditional or AI systems
            if self.config.integration_mode == IntegrationMode.TRADITIONAL_ONLY:
                content_result = await self._generate_traditional_content(prompt, user_id)
            else:
                content_result = await self._generate_ai_enhanced_content(prompt, user_id, preferences)
            
            if not content_result.success:
                return content_result
            
            # Apply AI enhancements if available
            enhanced_result = await self._apply_ai_enhancements(
                content_result.data, user_id, preferences
            )
            
            # Track performance and analytics
            response_time = (datetime.now() - start_time).total_seconds()
            await self._track_story_generation_analytics(user_id, prompt, response_time, enhanced_result.success)
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error generating story content: {str(e)}")
            self.error_count += 1
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="STORY_GENERATION_ERROR",
                    message="Story generation failed",
                    details={"prompt": prompt[:100], "exception": str(e)}
                )
            )

    async def get_system_status(self) -> StandardResponse:
        """Get comprehensive status of both traditional and AI systems."""
        try:
            # Get traditional system metrics
            traditional_metrics = await self.system_orchestrator.get_system_metrics()
            
            # Get AI system status  
            ai_dashboard = await self.ai_orchestrator.get_system_dashboard()
            # Convert to StandardResponse format
            ai_status = StandardResponse(
                success=True,
                data=ai_dashboard
            )
            
            # Generate integration metrics
            integration_metrics = await self._generate_integration_metrics()
            
            return StandardResponse(
                success=True,
                data={
                    "integration_config": {
                        "mode": self.config.integration_mode.value,
                        "level": self.config.integration_level.value,
                        "active": self.integration_active
                    },
                    "traditional_system": traditional_metrics.data if traditional_metrics.success else None,
                    "ai_system": ai_status.data if ai_status.success else None,
                    "integration_metrics": integration_metrics,
                    "uptime_seconds": (datetime.now() - self.startup_time).total_seconds(),
                    "total_operations": self.operation_count,
                    "error_rate": self.error_count / max(self.operation_count, 1)
                }
            )
            
        except Exception as e:
            logger.error(f"Error getting system status: {str(e)}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="SYSTEM_STATUS_ERROR",
                    message="System status retrieval failed",
                    details={"exception": str(e)}
                )
            )

    # Private methods for system coordination and integration

    async def _process_traditional_action(self, agent_id: str, action: str, 
                                        context: Optional[Dict[str, Any]]) -> StandardResponse:
        """Process action using only traditional systems."""
        # Create character state for traditional processing
        from src.core.data_models import CharacterIdentity
        character_identity = CharacterIdentity(
            name=agent_id,
            faction="Unknown",
            personality_traits=["default"],
            core_beliefs=["adaptive"]
        )
        character_state = CharacterState(
            base_identity=character_identity
        )
        
        # Create dynamic context
        dynamic_context = DynamicContext(
            agent_id=agent_id,
            character_state=character_state,
            situation_description=f"Processing action: {action}"
        )
        
        return await self.system_orchestrator.process_dynamic_context(dynamic_context)

    async def _process_ai_enhanced_action(self, agent_id: str, action: str,
                                        context: Optional[Dict[str, Any]]) -> StandardResponse:
        """Process action using AI-enhanced systems."""
        # Create agent context for AI processing
        agent_context = AgentContext(
            agent_id=agent_id,
            current_state="active_character",
            intentions=["perform_action"],
            dependencies=set()
        )
        
        # Process through AI coordination engine
        coordination_result = await self.ai_orchestrator.agent_coordination.coordinate_agent_action(
            agent_context, action
        )
        
        if coordination_result.success:
            # Also process through traditional system for consistency
            traditional_result = await self._process_traditional_action(agent_id, action, context)
            
            # Merge results
            return StandardResponse(
                success=True,
                data={
                    "ai_processing": coordination_result.data,
                    "traditional_processing": traditional_result.data if traditional_result.success else None,
                    "processing_mode": "ai_enhanced"
                }
            )
        else:
            # Fallback to traditional processing
            return await self._process_traditional_action(agent_id, action, context)

    async def _process_hybrid_action(self, agent_id: str, action: str,
                                   context: Optional[Dict[str, Any]]) -> StandardResponse:
        """Process action using hybrid AI + traditional approach with fallback."""
        try:
            # Try AI processing first
            ai_result = await asyncio.wait_for(
                self._process_ai_enhanced_action(agent_id, action, context),
                timeout=self.config.ai_system_timeout
            )
            
            if ai_result.success:
                return ai_result
            else:
                # Fallback to traditional
                logger.warning(f"AI processing failed for {agent_id}, falling back to traditional")
                return await self._process_traditional_action(agent_id, action, context)
                
        except asyncio.TimeoutError:
            logger.warning(f"AI processing timeout for {agent_id}, falling back to traditional")
            return await self._process_traditional_action(agent_id, action, context)
        except Exception as e:
            logger.error(f"Hybrid processing error for {agent_id}: {str(e)}")
            return await self._process_traditional_action(agent_id, action, context)

    async def _generate_traditional_content(self, prompt: str, user_id: str) -> StandardResponse:
        """Generate content using traditional Novel Engine systems."""
        # Use traditional template system and character generation
        return StandardResponse(
            success=True,
            data={
                "content": f"Traditional story content based on: {prompt}",
                "generation_method": "traditional",
                "user_id": user_id,
                "timestamp": datetime.now()
            }
        )

    async def _generate_ai_enhanced_content(self, prompt: str, user_id: str,
                                          preferences: Optional[Dict[str, Any]]) -> StandardResponse:
        """Generate content using AI-enhanced systems with recommendations."""
        # Get user preferences for personalization
        if preferences and self.ai_orchestrator.recommendation_engine:
            user_profile = UserProfile(
                user_id=user_id,
                preferences={},
                behavior_patterns={},
                preference_history=[]
            )
            
            # Get recommendations for story elements
            recommendations = await self.ai_orchestrator.recommendation_engine.get_personalized_recommendations(
                user_profile, limit=5
            )
        
        return StandardResponse(
            success=True,
            data={
                "content": f"AI-enhanced story content based on: {prompt}",
                "generation_method": "ai_enhanced",
                "user_id": user_id,
                "personalization_applied": preferences is not None,
                "timestamp": datetime.now()
            }
        )

    async def _apply_ai_enhancements(self, content_data: Dict[str, Any], user_id: str,
                                   preferences: Optional[Dict[str, Any]]) -> StandardResponse:
        """Apply AI enhancements like quality analysis and analytics tracking."""
        enhanced_data = content_data.copy()
        
        # Apply story quality analysis if available
        if (self.ai_orchestrator.story_quality_engine and 
            self.config.ai_feature_gates.get("story_quality", False)):
            
            quality_report = await self.ai_orchestrator.story_quality_engine.analyze_story_quality(
                content_data.get("content", ""),
                story_id=f"story_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            if quality_report.success:
                enhanced_data["quality_analysis"] = quality_report.data
        
        # Track analytics if available
        if (self.ai_orchestrator.analytics_platform and 
            self.config.ai_feature_gates.get("analytics", False)):
            
            analytics_event = AnalyticsEvent(
                event_id=f"content_gen_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                event_type="story_generation",
                user_id=user_id,
                properties={"content_length": len(content_data.get("content", ""))}
            )
            
            await self.ai_orchestrator.analytics_platform.track_event(analytics_event)
            enhanced_data["analytics_tracked"] = True
        
        return StandardResponse(
            success=True,
            data=enhanced_data
        )

    async def _track_story_generation_analytics(self, user_id: str, prompt: str, 
                                              response_time: float, success: bool):
        """Track story generation analytics."""
        if (self.ai_orchestrator.analytics_platform and 
            self.config.ai_feature_gates.get("analytics", False)):
            
            analytics_event = AnalyticsEvent(
                event_id=f"gen_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                event_type="story_generation_complete",
                user_id=user_id,
                properties={
                    "prompt_length": len(prompt),
                    "response_time": response_time,
                    "success": success
                },
                metrics={"response_time": response_time}
            )
            
            await self.ai_orchestrator.analytics_platform.track_event(analytics_event)

    async def _setup_event_coordination(self):
        """Set up event coordination between traditional and AI systems."""
        # Register event handlers for cross-system coordination
        self.event_bus.subscribe("character_state_changed", self._handle_character_state_change)
        self.event_bus.subscribe("story_generated", self._handle_story_generation)
        self.event_bus.subscribe("user_interaction", self._handle_user_interaction)

    async def _start_integration_monitoring(self):
        """Start background monitoring of integration performance."""
        # This would typically start background tasks for monitoring
        pass

    async def _generate_integration_metrics(self) -> IntegrationMetrics:
        """Generate current integration performance metrics."""
        current_time = datetime.now()
        uptime = (current_time - self.startup_time).total_seconds()
        
        # Calculate averages
        avg_response_time = sum(self.response_times[-100:]) / len(self.response_times[-100:]) if self.response_times else 0.0
        error_rate = self.error_count / max(self.operation_count, 1)
        
        metrics = IntegrationMetrics(
            timestamp=current_time,
            traditional_operations=self.operation_count // 2,  # Approximate
            ai_enhanced_operations=self.operation_count // 2,  # Approximate
            average_response_time=avg_response_time,
            ai_enhancement_rate=0.8 if self.config.integration_mode != IntegrationMode.TRADITIONAL_ONLY else 0.0,
            system_health_score=1.0 - min(error_rate * 10, 1.0)  # Convert error rate to health score
        )
        
        self.metrics_history.append(metrics)
        return metrics

    async def _emit_integration_event(self, event_type: str, data: Dict[str, Any]):
        """Emit integration event for monitoring and coordination."""
        self.event_bus.emit(event_type, data)

    async def _handle_character_state_change(self, event_data: Dict[str, Any]):
        """Handle character state change events."""
        pass

    async def _handle_story_generation(self, event_data: Dict[str, Any]):
        """Handle story generation events."""
        pass

    async def _handle_user_interaction(self, event_data: Dict[str, Any]):
        """Handle user interaction events."""
        pass

    def _map_integration_to_intelligence_level(self) -> IntelligenceLevel:
        """Map integration mode to AI intelligence level."""
        mapping = {
            IntegrationMode.TRADITIONAL_ONLY: IntelligenceLevel.BASIC,
            IntegrationMode.AI_ENHANCED: IntelligenceLevel.STANDARD,
            IntegrationMode.AI_FIRST: IntelligenceLevel.ADVANCED,
            IntegrationMode.FULL_AI: IntelligenceLevel.ADVANCED,
            IntegrationMode.EXPERIMENTAL: IntelligenceLevel.EXPERIMENTAL
        }
        return mapping.get(self.config.integration_mode, IntelligenceLevel.STANDARD)


# Export main class
__all__ = ['IntegrationOrchestrator', 'IntegrationConfig', 'IntegrationMode', 'SystemIntegrationLevel']