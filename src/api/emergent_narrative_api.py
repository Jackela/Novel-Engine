#!/usr/bin/env python3
"""
Emergent Narrative API Module
=============================

FastAPI endpoints for EmergentNarrativeEngine functionality including
emergent narrative generation, causal graph access, and narrative coherence analysis.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Depends, FastAPI, HTTPException, Path, Query
from pydantic import BaseModel, Field

from src.core.data_models import StandardResponse
from src.security.auth_system import Permission, get_current_user, require_permission

logger = logging.getLogger(__name__)


# Request/Response Models
class EmergentNarrativeRequest(BaseModel):
    """Request for emergent narrative generation"""

    agents: List[str] = Field(..., min_length=1, description="Participating agent IDs")
    time_range: Optional[Tuple[datetime, datetime]] = Field(
        None, description="Time range for narrative"
    )
    narrative_perspective: str = Field(
        "omniscient",
        description="Narrative perspective (omniscient, agent_specific, observer)",
    )
    focus_agent: Optional[str] = Field(
        None, description="Primary focus agent for agent_specific perspective"
    )
    include_predictions: bool = Field(
        True, description="Include predicted future events"
    )
    coherence_threshold: float = Field(
        0.7, ge=0.0, le=1.0, description="Minimum coherence required"
    )
    max_events: int = Field(50, ge=5, le=200, description="Maximum events to include")
    narrative_style: str = Field(
        "dramatic", description="Narrative style (dramatic, documentary, poetic)"
    )


class CausalLinkResponse(BaseModel):
    """Causal relationship in narrative"""

    source_event: str = Field(..., description="Source event ID")
    target_event: str = Field(..., description="Target event ID")
    relation_type: str = Field(..., description="Type of causal relation")
    strength: float = Field(..., ge=0.0, le=1.0, description="Causal strength")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in relation")
    narrative_significance: float = Field(..., description="Significance to narrative")


class NarrativeEventResponse(BaseModel):
    """Event in emergent narrative"""

    event_id: str = Field(..., description="Unique event identifier")
    agent_id: Optional[str] = Field(None, description="Primary agent involved")
    event_type: str = Field(..., description="Type of event")
    narrative_text: str = Field(..., description="Narrative description of event")
    timestamp: datetime = Field(..., description="Event timestamp")
    location: Optional[str] = Field(None, description="Event location")
    participants: List[str] = Field(
        default_factory=list, description="All participants"
    )
    causal_links: List[CausalLinkResponse] = Field(
        default_factory=list, description="Causal relationships"
    )
    narrative_weight: float = Field(..., description="Importance to overall narrative")
    coherence_score: float = Field(..., description="Coherence with surrounding events")


class EmergentNarrativeData(BaseModel):
    """Generated emergent narrative data"""

    narrative_id: str = Field(..., description="Unique narrative identifier")
    title: str = Field(..., description="Generated narrative title")
    summary: str = Field(..., description="Comprehensive narrative summary")
    events: List[NarrativeEventResponse] = Field(
        ..., description="Sequence of narrative events"
    )
    character_arcs: Dict[str, Dict[str, Any]] = Field(
        ..., description="Character development arcs"
    )
    plot_threads: Dict[str, Dict[str, Any]] = Field(
        ..., description="Active plot threads"
    )
    causal_graph_stats: Dict[str, Any] = Field(
        ..., description="Causal graph statistics"
    )
    coherence_report: Dict[str, Any] = Field(
        ..., description="Narrative coherence analysis"
    )
    narrative_patterns: Dict[str, List[str]] = Field(
        ..., description="Detected narrative patterns"
    )
    predicted_events: List[Dict[str, Any]] = Field(
        default_factory=list, description="Predicted future events"
    )
    generation_metadata: Dict[str, Any] = Field(
        ..., description="Generation process metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Narrative creation timestamp"
    )


class NarrativeBuildRequest(BaseModel):
    """Request to build narrative from story elements"""

    story_elements: List[Dict[str, Any]] = Field(
        ..., description="Story elements to incorporate"
    )
    build_strategy: str = Field(
        "chronological",
        description="Build strategy (chronological, thematic, character_focused)",
    )
    coherence_enforcement: bool = Field(True, description="Enforce narrative coherence")
    auto_fill_gaps: bool = Field(True, description="Automatically fill narrative gaps")
    target_length: Optional[int] = Field(
        None, description="Target narrative length in events"
    )
    themes: List[str] = Field(default_factory=list, description="Thematic focuses")


class CausalGraphRequest(BaseModel):
    """Request for causal graph data"""

    time_window: Optional[Tuple[datetime, datetime]] = Field(
        None, description="Time window filter"
    )
    agent_filter: Optional[List[str]] = Field(None, description="Filter by agents")
    include_predictions: bool = Field(
        False, description="Include predicted relationships"
    )
    min_confidence: float = Field(0.3, description="Minimum relationship confidence")
    max_depth: int = Field(5, description="Maximum relationship depth")


class CausalGraphData(BaseModel):
    """Causal graph data"""

    nodes: List[Dict[str, Any]] = Field(..., description="Graph nodes (events)")
    edges: List[CausalLinkResponse] = Field(
        ..., description="Graph edges (causal relationships)"
    )
    statistics: Dict[str, Any] = Field(..., description="Graph statistics")
    influential_events: List[str] = Field(..., description="Most influential event IDs")
    narrative_patterns: Dict[str, List[str]] = Field(
        ..., description="Detected narrative patterns"
    )
    predictions: List[Dict[str, Any]] = Field(
        default_factory=list, description="Event predictions"
    )


class NegotiationRequest(BaseModel):
    """Request to start negotiation"""

    initiator_id: str = Field(..., description="Initiating agent ID")
    target_agents: List[str] = Field(
        ..., min_length=1, description="Target agents for negotiation"
    )
    topic: str = Field(..., min_length=3, description="Negotiation topic")
    initial_proposal: Dict[str, Any] = Field(..., description="Initial proposal data")
    timeout_minutes: int = Field(30, ge=5, le=120, description="Negotiation timeout")


class NegotiationResponse(BaseModel):
    """Multi-agent negotiation data"""

    negotiation_id: str = Field(..., description="Unique negotiation identifier")
    participants: List[str] = Field(..., description="Negotiating agents")
    topic: str = Field(..., description="Negotiation topic")
    status: str = Field(..., description="Current negotiation status")
    proposals: List[Dict[str, Any]] = Field(..., description="All proposals made")
    responses: List[Dict[str, Any]] = Field(..., description="All responses received")
    resolution: Optional[Dict[str, Any]] = Field(
        None, description="Final resolution if completed"
    )
    duration_minutes: float = Field(..., description="Negotiation duration")
    created_at: datetime = Field(..., description="Negotiation start time")
    updated_at: datetime = Field(..., description="Last update time")


class EmergentNarrativeAPI:
    """API endpoints for EmergentNarrativeEngine functionality."""

    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator
        self.emergent_narrative_engine = None

    def setup_routes(self, app: FastAPI):
        """Setup all emergent narrative API routes."""

        @app.post(
            "/api/v1/narratives/emergent/generate",
            response_model=StandardResponse[EmergentNarrativeData],
            summary="Generate Emergent Narrative",
            description="Generate emergent narrative based on agent interactions and causal graph",
        )
        @require_permission(Permission.NARRATIVE_GENERATE)
        async def generate_emergent_narrative(
            request: EmergentNarrativeRequest,
            current_user: Dict = Depends(get_current_user),
        ):
            try:
                if (
                    not self.orchestrator
                    or not self.orchestrator.emergent_narrative_engine
                ):
                    raise HTTPException(
                        status_code=503,
                        detail="Emergent narrative engine not available",
                    )

                # Generate emergent narrative
                narrative_result = await self.orchestrator.emergent_narrative_engine.generate_emergent_narrative(
                    agents=request.agents,
                    time_range=request.time_range,
                    perspective=request.narrative_perspective,
                    focus_agent=request.focus_agent,
                    include_predictions=request.include_predictions,
                    coherence_threshold=request.coherence_threshold,
                    max_events=request.max_events,
                    style=request.narrative_style,
                )

                if not narrative_result.get("success", False):
                    error_msg = narrative_result.get(
                        "error", "Failed to generate narrative"
                    )
                    raise HTTPException(status_code=500, detail=error_msg)

                # Transform to response format
                narrative_data = EmergentNarrativeData(
                    narrative_id=narrative_result.get(
                        "narrative_id", f"narrative_{int(datetime.now().timestamp())}"
                    ),
                    title=narrative_result.get("title", "Generated Narrative"),
                    summary=narrative_result.get("summary", ""),
                    events=narrative_result.get("events", []),
                    character_arcs=narrative_result.get("character_arcs", {}),
                    plot_threads=narrative_result.get("plot_threads", {}),
                    causal_graph_stats=narrative_result.get("causal_graph_stats", {}),
                    coherence_report=narrative_result.get("coherence_report", {}),
                    narrative_patterns=narrative_result.get("narrative_patterns", {}),
                    predicted_events=narrative_result.get("predicted_events", []),
                    generation_metadata=narrative_result.get("metadata", {}),
                )

                return StandardResponse(success=True, data=narrative_data)

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error generating emergent narrative: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")

        @app.post(
            "/api/v1/narratives/build",
            response_model=StandardResponse[EmergentNarrativeData],
            summary="Build Comprehensive Narrative",
            description="Build comprehensive narrative from existing story elements",
        )
        @require_permission(Permission.NARRATIVE_BUILD)
        async def build_narrative(
            request: NarrativeBuildRequest,
            current_user: Dict = Depends(get_current_user),
        ):
            try:
                if (
                    not self.orchestrator
                    or not self.orchestrator.emergent_narrative_engine
                ):
                    raise HTTPException(
                        status_code=503,
                        detail="Emergent narrative engine not available",
                    )

                # Build comprehensive narrative
                narrative_result = await self.orchestrator.emergent_narrative_engine.build_comprehensive_narrative(
                    story_elements=request.story_elements,
                    strategy=request.build_strategy,
                    coherence_enforcement=request.coherence_enforcement,
                    auto_fill_gaps=request.auto_fill_gaps,
                    target_length=request.target_length,
                    themes=request.themes,
                )

                if not narrative_result.get("success", False):
                    error_msg = narrative_result.get(
                        "error", "Failed to build narrative"
                    )
                    raise HTTPException(status_code=500, detail=error_msg)

                # Transform to response format
                built_narrative = narrative_result.get("narrative", {})
                narrative_data = EmergentNarrativeData(
                    narrative_id=built_narrative.get(
                        "narrative_id",
                        f"built_narrative_{int(datetime.now().timestamp())}",
                    ),
                    title=built_narrative.get("title", "Built Narrative"),
                    summary=built_narrative.get("summary", ""),
                    events=built_narrative.get("events", []),
                    character_arcs=built_narrative.get("character_arcs", {}),
                    plot_threads=built_narrative.get("plot_threads", {}),
                    causal_graph_stats=built_narrative.get("causal_graph_stats", {}),
                    coherence_report=built_narrative.get("coherence_report", {}),
                    narrative_patterns=built_narrative.get("narrative_patterns", {}),
                    predicted_events=built_narrative.get("predicted_events", []),
                    generation_metadata=narrative_result.get("build_statistics", {}),
                )

                return StandardResponse(success=True, data=narrative_data)

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error building narrative: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")

        @app.get(
            "/api/v1/causality/graph",
            response_model=StandardResponse[CausalGraphData],
            summary="Get Causal Graph",
            description="Access causal relationship graph",
        )
        @require_permission(Permission.CAUSALITY_READ)
        async def get_causal_graph(
            request_params: CausalGraphRequest = Depends(),
            current_user: Dict = Depends(get_current_user),
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

                # Get causal graph data
                graph_result = await turn_engine.get_causal_graph_data()

                if not graph_result.get("success", False):
                    error_msg = graph_result.get("error", "Failed to get causal graph")
                    raise HTTPException(status_code=500, detail=error_msg)

                # Transform to response format
                graph_data = CausalGraphData(
                    nodes=graph_result.get("nodes", []),
                    edges=graph_result.get("edges", []),
                    statistics=graph_result.get("statistics", {}),
                    influential_events=graph_result.get("influential_events", []),
                    narrative_patterns=graph_result.get("narrative_patterns", {}),
                    predictions=graph_result.get("predictions", []),
                )

                return StandardResponse(success=True, data=graph_data)

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting causal graph: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")

        @app.get(
            "/api/v1/narratives/emergent/{narrative_id}",
            response_model=StandardResponse[EmergentNarrativeData],
            summary="Get Generated Narrative",
            description="Retrieve previously generated emergent narrative",
        )
        @require_permission(Permission.NARRATIVE_READ)
        async def get_emergent_narrative(
            narrative_id: str = Path(..., description="Narrative identifier"),
            include_events: bool = Query(
                True, description="Include detailed event list"
            ),
            include_causal_graph: bool = Query(
                False, description="Include causal relationship data"
            ),
            format: str = Query(
                "structured", description="Response format (structured, text, timeline)"
            ),
            current_user: Dict = Depends(get_current_user),
        ):
            try:
                if (
                    not self.orchestrator
                    or not self.orchestrator.emergent_narrative_engine
                ):
                    raise HTTPException(
                        status_code=503,
                        detail="Emergent narrative engine not available",
                    )

                # Get stored narrative
                narrative_result = await self.orchestrator.emergent_narrative_engine.get_stored_narrative(
                    narrative_id=narrative_id,
                    include_events=include_events,
                    include_causal_graph=include_causal_graph,
                    format=format,
                )

                if not narrative_result.get("success", False):
                    raise HTTPException(
                        status_code=404, detail=f"Narrative {narrative_id} not found"
                    )

                # Transform to response format
                narrative = narrative_result.get("narrative", {})
                narrative_data = EmergentNarrativeData(
                    narrative_id=narrative_id,
                    title=narrative.get("title", "Retrieved Narrative"),
                    summary=narrative.get("summary", ""),
                    events=narrative.get("events", []) if include_events else [],
                    character_arcs=narrative.get("character_arcs", {}),
                    plot_threads=narrative.get("plot_threads", {}),
                    causal_graph_stats=narrative.get("causal_graph_stats", {}),
                    coherence_report=narrative.get("coherence_report", {}),
                    narrative_patterns=narrative.get("narrative_patterns", {}),
                    predicted_events=narrative.get("predicted_events", []),
                    generation_metadata=narrative.get("metadata", {}),
                    created_at=narrative.get("created_at", datetime.now()),
                )

                return StandardResponse(success=True, data=narrative_data)

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting narrative {narrative_id}: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")


def create_emergent_narrative_api(orchestrator=None) -> EmergentNarrativeAPI:
    """Factory function to create EmergentNarrativeAPI instance."""
    return EmergentNarrativeAPI(orchestrator)
