#!/usr/bin/env python3
"""
Character Action Processor
==========================

Extracted from IntegrationOrchestrator as part of God Class refactoring.
Handles character action processing with AI enhancement and fallback strategies.

Responsibilities:
- Process character actions through traditional systems
- Process character actions through AI-enhanced systems
- Implement hybrid processing with automatic fallback
- Handle timeouts and error recovery

This class follows the Single Responsibility Principle by focusing solely on
character action processing logic, separate from integration orchestration.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from src.core.data_models import (
    CharacterIdentity,
    CharacterState,
    DynamicContext,
    StandardResponse,
)

from .agent_coordination_engine import AgentContext

logger = logging.getLogger(__name__)


class CharacterActionProcessor:
    """
    Processes character actions using traditional, AI-enhanced, or hybrid approaches.
    
    This class encapsulates the logic for routing character actions through
    different processing pipelines based on integration mode, with automatic
    fallback for resilience.
    """

    def __init__(
        self,
        system_orchestrator,
        ai_orchestrator,
        config,
    ):
        """
        Initialize the character action processor.
        
        Args:
            system_orchestrator: Traditional system orchestrator
            ai_orchestrator: AI intelligence orchestrator
            config: Integration configuration
        """
        self.system_orchestrator = system_orchestrator
        self.ai_orchestrator = ai_orchestrator
        self.config = config

    async def process_traditional_action(
        self, agent_id: str, action: str, context: Optional[Dict[str, Any]]
    ) -> StandardResponse:
        """
        Process action using only traditional systems.
        
        Args:
            agent_id: Identifier for the agent/character
            action: Action to process
            context: Optional context data
            
        Returns:
            StandardResponse with processing result
        """
        character_identity = CharacterIdentity(
            name=agent_id,
            faction="Unknown",
            personality_traits=["default"],
            core_beliefs=["adaptive"],
        )
        character_state = CharacterState(base_identity=character_identity)

        dynamic_context = DynamicContext(
            agent_id=agent_id,
            character_state=character_state,
            situation_description=f"Processing action: {action}",
        )

        return await self.system_orchestrator.process_dynamic_context(dynamic_context)

    async def process_ai_enhanced_action(
        self, agent_id: str, action: str, context: Optional[Dict[str, Any]]
    ) -> StandardResponse:
        """
        Process action using AI-enhanced systems.
        
        Combines AI coordination with traditional processing for consistency.
        
        Args:
            agent_id: Identifier for the agent/character
            action: Action to process
            context: Optional context data
            
        Returns:
            StandardResponse with AI-enhanced processing result
        """
        agent_context = AgentContext(
            agent_id=agent_id,
            current_state="active_character",
            intentions=["perform_action"],
            dependencies=set(),
        )

        coordination_result = (
            await self.ai_orchestrator.agent_coordination.coordinate_agent_action(
                agent_context, action
            )
        )

        if coordination_result.success:
            traditional_result = await self.process_traditional_action(
                agent_id, action, context
            )

            return StandardResponse(
                success=True,
                data={
                    "ai_processing": coordination_result.data,
                    "traditional_processing": (
                        traditional_result.data if traditional_result.success else None
                    ),
                    "processing_mode": "ai_enhanced",
                },
            )
        else:
            return await self.process_traditional_action(agent_id, action, context)

    async def process_hybrid_action(
        self, agent_id: str, action: str, context: Optional[Dict[str, Any]]
    ) -> StandardResponse:
        """
        Process action using hybrid AI + traditional approach with fallback.
        
        Attempts AI processing first with timeout protection, falls back to
        traditional processing on failure or timeout.
        
        Args:
            agent_id: Identifier for the agent/character
            action: Action to process
            context: Optional context data
            
        Returns:
            StandardResponse with processing result
        """
        try:
            ai_result = await asyncio.wait_for(
                self.process_ai_enhanced_action(agent_id, action, context),
                timeout=self.config.ai_system_timeout,
            )

            if ai_result.success:
                return ai_result
            else:
                logger.warning(
                    f"AI processing failed for {agent_id}, falling back to traditional"
                )
                return await self.process_traditional_action(agent_id, action, context)

        except asyncio.TimeoutError:
            logger.warning(
                f"AI processing timeout for {agent_id}, falling back to traditional"
            )
            return await self.process_traditional_action(agent_id, action, context)
        except Exception as e:
            logger.error(f"Hybrid processing error for {agent_id}: {str(e)}")
            return await self.process_traditional_action(agent_id, action, context)


__all__ = ["CharacterActionProcessor"]
