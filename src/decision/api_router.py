"""
Decision API Router

FastAPI router for decision-related endpoints.
To be imported and included in the main api_server.py.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .models import FeasibilityResult, UserDecision
from .pause_controller import InteractionPauseController
from .decision_point_detector import DecisionPointDetector
from .negotiation_engine import NegotiationEngine

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/decision", tags=["decision"])


# ===================================================================
# Request/Response Models
# ===================================================================


class DecisionResponseRequest(BaseModel):
    """Request body for submitting a decision response."""

    decision_id: str = Field(..., description="ID of the decision point")
    input_type: str = Field(..., description="Type of input: 'option' or 'freetext'")
    selected_option_id: Optional[int] = Field(
        None, description="Selected option ID (for option type)"
    )
    free_text: Optional[str] = Field(
        None, description="Free text input (for freetext type)"
    )


class NegotiationConfirmRequest(BaseModel):
    """Request body for confirming negotiation result."""

    decision_id: str = Field(..., description="ID of the decision point")
    accepted: bool = Field(..., description="Whether user accepts the adjusted action")
    insist_original: bool = Field(
        False, description="Whether user insists on original input"
    )


class SkipDecisionRequest(BaseModel):
    """Request body for skipping a decision."""

    decision_id: str = Field(..., description="ID of the decision point to skip")


# ===================================================================
# Global instances (to be initialized by api_server.py)
# ===================================================================

_pause_controller: Optional[InteractionPauseController] = None
_decision_detector: Optional[DecisionPointDetector] = None
_negotiation_engine: Optional[NegotiationEngine] = None

# SSE broadcast function (to be set by api_server.py)
_broadcast_sse_event = None


def initialize_decision_system(
    pause_controller: InteractionPauseController,
    decision_detector: DecisionPointDetector,
    negotiation_engine: NegotiationEngine,
    broadcast_sse_event,
):
    """
    Initialize the decision system with required components.
    Called by api_server.py during startup.
    """
    global _pause_controller, _decision_detector, _negotiation_engine, _broadcast_sse_event

    _pause_controller = pause_controller
    _decision_detector = decision_detector
    _negotiation_engine = negotiation_engine
    _broadcast_sse_event = broadcast_sse_event

    logger.info("Decision system initialized")


def get_pause_controller() -> InteractionPauseController:
    """Get the pause controller instance."""
    if not _pause_controller:
        raise RuntimeError("Decision system not initialized")
    return _pause_controller


def get_decision_detector() -> DecisionPointDetector:
    """Get the decision detector instance."""
    if not _decision_detector:
        raise RuntimeError("Decision system not initialized")
    return _decision_detector


def get_negotiation_engine() -> NegotiationEngine:
    """Get the negotiation engine instance."""
    if not _negotiation_engine:
        raise RuntimeError("Decision system not initialized")
    return _negotiation_engine


def broadcast_decision_event(event_type: str, data: Dict[str, Any]):
    """Broadcast a decision-related SSE event."""
    if _broadcast_sse_event:
        _broadcast_sse_event(
            {
                "id": f"decision-{data.get('decision_id', 'unknown')}",
                "type": event_type,
                "title": f"Decision: {event_type}",
                "description": data.get("description", ""),
                "severity": "medium",
                "timestamp": data.get("timestamp"),
                "data": data,
            }
        )


# ===================================================================
# API Endpoints
# ===================================================================


@router.get("/status")
async def get_decision_status() -> Dict[str, Any]:
    """
    Get the current status of the decision system.

    Returns the current pause state, pending decision point (if any),
    and negotiation state.
    """
    try:
        controller = get_pause_controller()
        return {
            "success": True,
            "data": controller.get_status(),
        }
    except RuntimeError as e:
        return {
            "success": False,
            "message": str(e),
            "data": None,
        }


@router.post("/respond")
async def submit_decision_response(request: DecisionResponseRequest) -> Dict[str, Any]:
    """
    Submit a response to a pending decision point.

    For option selection, provide selected_option_id.
    For free text input, provide free_text.
    """
    try:
        controller = get_pause_controller()

        if not controller.is_paused:
            raise HTTPException(
                status_code=400,
                detail="No pending decision to respond to",
            )

        # Validate input
        if request.input_type == "option" and request.selected_option_id is None:
            raise HTTPException(
                status_code=400,
                detail="selected_option_id required for option input",
            )

        if request.input_type == "freetext" and not request.free_text:
            raise HTTPException(
                status_code=400,
                detail="free_text required for freetext input",
            )

        # For free text, run negotiation
        if request.input_type == "freetext" and request.free_text:
            engine = get_negotiation_engine()
            decision_point = controller.current_decision_point

            if decision_point:
                user_decision = UserDecision(
                    decision_id=request.decision_id,
                    input_type="freetext",
                    free_text=request.free_text,
                )

                # Evaluate the input
                negotiation_result = await engine.evaluate_input(
                    user_decision=user_decision,
                    decision_point=decision_point,
                )

                # If needs negotiation, start negotiation phase
                if negotiation_result.feasibility != FeasibilityResult.ACCEPTED:
                    await controller.start_negotiation(
                        decision_id=request.decision_id,
                        negotiation_result=negotiation_result,
                    )

                    # Broadcast negotiation event
                    broadcast_decision_event(
                        "negotiation_required",
                        {
                            "decision_id": request.decision_id,
                            "feasibility": negotiation_result.feasibility.value,
                            "explanation": negotiation_result.explanation,
                            "adjusted_action": negotiation_result.adjusted_action,
                            "alternatives": [
                                alt.to_dict() for alt in negotiation_result.alternatives
                            ],
                        },
                    )

                    return {
                        "success": True,
                        "message": "Negotiation required",
                        "data": {
                            "needs_negotiation": True,
                            "negotiation": negotiation_result.to_dict(),
                        },
                    }

        # Submit the response
        success = await controller.submit_response(
            decision_id=request.decision_id,
            input_type=request.input_type,
            selected_option_id=request.selected_option_id,
            free_text=request.free_text,
        )

        if success:
            # Broadcast acceptance event
            broadcast_decision_event(
                "decision_accepted",
                {
                    "decision_id": request.decision_id,
                    "input_type": request.input_type,
                },
            )

            return {
                "success": True,
                "message": "Decision response accepted",
                "data": {
                    "needs_negotiation": False,
                },
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to submit response - decision may have expired",
            )

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/confirm")
async def confirm_negotiation(request: NegotiationConfirmRequest) -> Dict[str, Any]:
    """
    Confirm or reject a negotiation result.

    After free text input is evaluated and needs adjustment,
    the user can accept the adjusted action or insist on original.
    """
    try:
        controller = get_pause_controller()

        success = await controller.confirm_negotiation(
            decision_id=request.decision_id,
            accepted=request.accepted,
            insist_original=request.insist_original,
        )

        if success:
            # Broadcast finalization event
            broadcast_decision_event(
                "decision_finalized",
                {
                    "decision_id": request.decision_id,
                    "accepted_adjustment": request.accepted,
                    "insisted_original": request.insist_original,
                },
            )

            return {
                "success": True,
                "message": "Negotiation confirmed",
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to confirm negotiation",
            )

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/skip")
async def skip_decision(request: SkipDecisionRequest) -> Dict[str, Any]:
    """
    Skip the current decision point, using the default option.
    """
    try:
        controller = get_pause_controller()

        success = await controller.skip_decision(request.decision_id)

        if success:
            # Broadcast skip event
            broadcast_decision_event(
                "decision_resolved",
                {
                    "decision_id": request.decision_id,
                    "resolution": "skipped",
                },
            )

            return {
                "success": True,
                "message": "Decision skipped",
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to skip decision",
            )

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_decision_history() -> Dict[str, Any]:
    """
    Get the history of decision points in the current session.
    """
    try:
        detector = get_decision_detector()
        return {
            "success": True,
            "data": {
                "total_decisions": detector.decision_count,
            },
        }
    except RuntimeError as e:
        return {
            "success": False,
            "message": str(e),
            "data": None,
        }
