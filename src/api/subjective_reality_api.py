#!/usr/bin/env python3
"""
Subjective Reality API Module
============================

FastAPI endpoints for SubjectiveRealityEngine functionality including
personalized turn briefs, belief models, and fog-of-war management.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Path
from pydantic import BaseModel, Field

from src.core.data_models import StandardResponse
from src.security.auth_system import Permission, get_current_user, require_permission

logger = logging.getLogger(__name__)


# Request/Response Models
class TurnBriefRequest(BaseModel):
    """Query parameters for turn brief generation"""

    include_context: bool = Field(True, description="Include contextual information")
    confidence_threshold: float = Field(
        0.3, ge=0.0, le=1.0, description="Minimum information confidence"
    )
    time_window_hours: int = Field(2, ge=1, le=24, description="Context time window")


class InformationFragmentResponse(BaseModel):
    """Information fragment in turn brief"""

    fragment_id: str = Field(..., description="Unique fragment identifier")
    content: Dict[str, Any] = Field(..., description="Fragment content")
    source: str = Field(..., description="Information source type")
    reliability: float = Field(
        ..., ge=0.0, le=1.0, description="Information reliability"
    )
    category: str = Field(..., description="Knowledge category")
    timestamp: datetime = Field(..., description="Information timestamp")
    location_context: Optional[str] = Field(None, description="Location context")
    current_reliability: float = Field(..., description="Time-adjusted reliability")


class TurnBriefData(BaseModel):
    """Personalized turn brief data"""

    agent_id: str = Field(..., description="Target agent identifier")
    turn_number: int = Field(..., description="Turn sequence number")
    subjective_world_state: Dict[str, Any] = Field(
        ..., description="Agent's filtered world view"
    )
    available_information: List[InformationFragmentResponse] = Field(
        ..., description="Available information fragments"
    )
    recommended_actions: List[str] = Field(
        ..., description="Recommended actions based on agent personality"
    )
    narrative_context: str = Field(
        ..., description="Narrative description of current situation"
    )
    confidence_levels: Dict[str, float] = Field(
        ..., description="Confidence in different information categories"
    )
    visible_locations: List[str] = Field(..., description="Currently visible locations")
    known_agents: List[Dict[str, Any]] = Field(
        ..., description="Known agents and their visibility"
    )
    personality_factors: Dict[str, float] = Field(
        ..., description="Agent's personality influences"
    )
    fog_of_war_status: Dict[str, Any] = Field(
        ..., description="Information access limitations"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Brief generation timestamp"
    )


class MultiBriefRequest(BaseModel):
    """Request for multiple agent briefs"""

    agent_filter: Optional[List[str]] = Field(
        None, description="Filter to specific agents"
    )
    include_context: bool = Field(True, description="Include contextual information")
    confidence_threshold: float = Field(
        0.3, ge=0.0, le=1.0, description="Minimum information confidence"
    )


class MultiBriefData(BaseModel):
    """Multiple agent brief data"""

    turn_number: int = Field(..., description="Turn sequence number")
    agent_briefs: Dict[str, TurnBriefData] = Field(
        ..., description="Agent ID to brief mapping"
    )
    global_context: Dict[str, Any] = Field(..., description="Shared global context")
    turn_summary: str = Field(..., description="Overall turn situation summary")
    conflicts_detected: List[Dict[str, Any]] = Field(
        default_factory=list, description="Detected agent conflicts"
    )


class TurnBriefGenerationRequest(BaseModel):
    """Request to generate turn briefs"""

    global_world_state: Dict[str, Any] = Field(
        ..., description="Current global world state"
    )
    recent_events: List[Dict[str, Any]] = Field(
        default_factory=list, description="Recent events to process"
    )
    agent_filter: Optional[List[str]] = Field(
        None, description="Generate briefs for specific agents only"
    )
    force_refresh: bool = Field(
        False, description="Force regeneration of cached information"
    )


class BeliefModelRequest(BaseModel):
    """Request for agent belief model"""

    include_fragments: bool = Field(True, description="Include information fragments")
    category_filter: Optional[List[str]] = Field(
        None, description="Filter by knowledge categories"
    )
    reliability_threshold: float = Field(
        0.0, description="Minimum reliability threshold"
    )


class BeliefModelData(BaseModel):
    """Agent belief model data"""

    agent_id: str = Field(..., description="Agent identifier")
    personality_bias: Dict[str, float] = Field(
        ..., description="Personality biases affecting perception"
    )
    trust_network: Dict[str, float] = Field(
        ..., description="Trust levels for other agents"
    )
    information_fragments: List[InformationFragmentResponse] = Field(
        ..., description="Known information fragments"
    )
    active_hypotheses: Dict[str, float] = Field(
        ..., description="Active hypotheses and confidence levels"
    )
    cognitive_filters: Dict[str, float] = Field(
        ..., description="Cognitive filtering preferences"
    )
    total_fragments: int = Field(..., description="Total information fragments")
    average_reliability: float = Field(
        ..., description="Average information reliability"
    )
    last_update: datetime = Field(..., description="Last belief model update")


class BeliefUpdateRequest(BaseModel):
    """Request to update agent beliefs"""

    new_information: List[Dict[str, Any]] = Field(
        ..., description="New information to add"
    )
    trust_updates: Optional[Dict[str, float]] = Field(
        None, description="Trust level updates"
    )
    personality_adjustments: Optional[Dict[str, float]] = Field(
        None, description="Personality bias adjustments"
    )


class SubjectiveRealityAPI:
    """API endpoints for SubjectiveRealityEngine functionality."""

    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator
        self.subjective_reality_engine = None
        self.turn_brief_factory = None

    def setup_routes(self, app: FastAPI):
        """Setup all subjective reality API routes."""

        @app.get(
            "/api/turns/{turn_id}/briefs/{agent_id}",
            response_model=StandardResponse[TurnBriefData],
            summary="Get Agent Turn Brief",
            description="Retrieve personalized turn brief for a specific agent",
        )
        async def get_turn_brief(
            turn_id: int = Path(..., description="Turn identifier"),
            agent_id: str = Path(..., description="Agent identifier"),
            request_params: TurnBriefRequest = Depends(),
            current_user: Dict = Depends(get_current_user),
            _: Any = Depends(require_permission(Permission.NARRATIVE_READ)),
        ):
            try:
                if not self.orchestrator or not hasattr(self.orchestrator, "director"):
                    raise HTTPException(
                        status_code=503, detail="Turn execution engine not available"
                    )

                # Get turn engine from orchestrator
                turn_engine = getattr(self.orchestrator.director, "turn_engine", None)
                if not turn_engine:
                    raise HTTPException(
                        status_code=503, detail="Turn execution engine not initialized"
                    )

                # Generate turn brief
                result = await turn_engine.get_agent_turn_brief(
                    agent_id=agent_id,
                    turn_number=turn_id,
                    world_state=None,  # Could be enhanced to accept world state
                )

                if not result.get("success", False):
                    error_msg = result.get("error", "Failed to generate turn brief")
                    raise HTTPException(status_code=404, detail=error_msg)

                # Transform result to expected format
                brief_data = result["brief"]
                turn_brief = TurnBriefData(
                    agent_id=agent_id,
                    turn_number=turn_id,
                    subjective_world_state=brief_data.get("subjective_world_state", {}),
                    available_information=brief_data.get("available_information", []),
                    recommended_actions=brief_data.get("recommended_actions", []),
                    narrative_context=brief_data.get("narrative_context", ""),
                    confidence_levels=brief_data.get("confidence_levels", {}),
                    visible_locations=brief_data.get("visible_locations", []),
                    known_agents=brief_data.get("known_agents", []),
                    personality_factors=brief_data.get("personality_factors", {}),
                    fog_of_war_status=brief_data.get("fog_of_war_status", {}),
                )

                return StandardResponse(success=True, data=turn_brief)

            except HTTPException:
                raise
            except Exception:
                logger.exception("Error getting turn brief.")
                raise HTTPException(status_code=500, detail="Internal server error")

        @app.get(
            "/api/turns/{turn_id}/briefs",
            response_model=StandardResponse[MultiBriefData],
            summary="Get All Agent Turn Briefs",
            description="Retrieve turn briefs for all agents in a turn",
        )
        async def get_all_turn_briefs(
            turn_id: int = Path(..., description="Turn identifier"),
            request_params: MultiBriefRequest = Depends(),
            current_user: Dict = Depends(get_current_user),
            _: Any = Depends(require_permission(Permission.NARRATIVE_READ)),
        ):
            try:
                if not self.orchestrator or not hasattr(self.orchestrator, "director"):
                    raise HTTPException(
                        status_code=503, detail="Turn execution engine not available"
                    )

                turn_engine = getattr(self.orchestrator.director, "turn_engine", None)
                if not turn_engine:
                    raise HTTPException(
                        status_code=503, detail="Turn execution engine not initialized"
                    )

                # Get all agent briefs
                result = await turn_engine.get_all_agent_briefs(
                    turn_number=turn_id, world_state=None
                )

                if not result.get("success", False):
                    error_msg = result.get("error", "Failed to generate turn briefs")
                    raise HTTPException(status_code=500, detail=error_msg)

                # Transform results
                agent_briefs = {}
                for agent_id, brief_data in result.get("agent_briefs", {}).items():
                    agent_briefs[agent_id] = TurnBriefData(
                        agent_id=agent_id,
                        turn_number=turn_id,
                        subjective_world_state=brief_data.get(
                            "subjective_world_state", {}
                        ),
                        available_information=brief_data.get(
                            "available_information", []
                        ),
                        recommended_actions=brief_data.get("recommended_actions", []),
                        narrative_context=brief_data.get("narrative_context", ""),
                        confidence_levels=brief_data.get("confidence_levels", {}),
                        visible_locations=brief_data.get("visible_locations", []),
                        known_agents=brief_data.get("known_agents", []),
                        personality_factors=brief_data.get("personality_factors", {}),
                        fog_of_war_status=brief_data.get("fog_of_war_status", {}),
                    )

                multi_brief = MultiBriefData(
                    turn_number=turn_id,
                    agent_briefs=agent_briefs,
                    global_context={},
                    turn_summary=f"Turn {turn_id} briefs generated for {len(agent_briefs)} agents",
                )

                return StandardResponse(success=True, data=multi_brief)

            except HTTPException:
                raise
            except Exception:
                logger.exception("Error getting all turn briefs.")
                raise HTTPException(status_code=500, detail="Internal server error")

        @app.get(
            "/api/agents/{agent_id}/beliefs",
            response_model=StandardResponse[BeliefModelData],
            summary="Get Agent Belief Model",
            description="Access agent's subjective belief model",
        )
        async def get_agent_beliefs(
            agent_id: str = Path(..., description="Agent identifier"),
            request_params: BeliefModelRequest = Depends(),
            current_user: Dict = Depends(get_current_user),
            _: Any = Depends(require_permission(Permission.BELIEF_READ)),
        ):
            try:
                if (
                    not self.orchestrator
                    or not self.orchestrator.subjective_reality_engine
                ):
                    raise HTTPException(
                        status_code=503,
                        detail="Subjective reality engine not available",
                    )

                # Get belief model from subjective reality engine
                belief_model = await self.orchestrator.subjective_reality_engine.get_agent_belief_model(
                    agent_id
                )

                if not belief_model:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Belief model not found for agent {agent_id}",
                    )

                # Transform to response format
                belief_data = BeliefModelData(
                    agent_id=agent_id,
                    personality_bias=belief_model.get("personality_bias", {}),
                    trust_network=belief_model.get("trust_network", {}),
                    information_fragments=belief_model.get("information_fragments", []),
                    active_hypotheses=belief_model.get("active_hypotheses", {}),
                    cognitive_filters=belief_model.get("cognitive_filters", {}),
                    total_fragments=belief_model.get("total_fragments", 0),
                    average_reliability=belief_model.get("average_reliability", 0.0),
                    last_update=belief_model.get("last_update", datetime.now()),
                )

                return StandardResponse(success=True, data=belief_data)

            except HTTPException:
                raise
            except Exception:
                logger.exception("Error getting belief model.")
                raise HTTPException(status_code=500, detail="Internal server error")


def create_subjective_reality_api(orchestrator=None) -> SubjectiveRealityAPI:
    """Factory function to create SubjectiveRealityAPI instance."""
    return SubjectiveRealityAPI(orchestrator)
