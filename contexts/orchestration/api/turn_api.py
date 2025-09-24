#!/usr/bin/env python3
"""
Turn Orchestration REST API

FastAPI application providing REST endpoints for turn orchestration,
including the main POST /v1/turns:run endpoint and monitoring capabilities.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import uvicorn
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, field_validator

from ..application.services import TurnOrchestrator
from ..domain.services import EnhancedPerformanceTracker
from ..domain.value_objects import TurnConfiguration, TurnId
from ..infrastructure.monitoring import (
    PrometheusMetricsCollector,
    PrometheusMiddleware,
    initialize_tracing,
    setup_fastapi_tracing,
)

logger = logging.getLogger(__name__)


# Request/Response Models


class TurnExecutionRequest(BaseModel):
    """Request model for turn execution."""

    participants: List[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of participant agent IDs (1-10 participants)",
    )
    configuration: Optional[Dict[str, Any]] = Field(
        None, description="Optional turn configuration parameters"
    )
    turn_id: Optional[str] = Field(
        None, description="Optional turn ID (generated if not provided)"
    )
    async_execution: bool = Field(
        False, description="Whether to execute turn asynchronously"
    )

    @field_validator("participants")
    @classmethod
    def validate_participants(cls, v):
        if not all(isinstance(p, str) and p.strip() for p in v):
            raise ValueError("All participants must be non-empty strings")
        if len(set(v)) != len(v):
            raise ValueError("Participants must be unique")
        return v

    @field_validator("turn_id")
    @classmethod
    def validate_turn_id(cls, v):
        if v is not None:
            try:
                UUID(v)
            except ValueError:
                raise ValueError("turn_id must be a valid UUID string")
        return v


class PhaseResultSummary(BaseModel):
    """Summary of phase execution result."""

    phase: str
    success: bool
    execution_time_ms: float
    events_processed: int
    events_generated: int
    artifacts_created: List[str]
    ai_cost: Optional[float] = None
    error_message: Optional[str] = None


class TurnExecutionResponse(BaseModel):
    """Response model for turn execution."""

    turn_id: str
    success: bool
    execution_time_ms: float
    phases_completed: List[str]
    phase_results: Dict[str, PhaseResultSummary]
    compensation_actions: List[Dict[str, Any]]
    performance_metrics: Dict[str, float]
    error_details: Optional[Dict[str, Any]] = None
    completed_at: str


class TurnStatusResponse(BaseModel):
    """Response model for turn status."""

    turn_id: str
    status: str  # 'running', 'completed', 'failed', 'not_found'
    progress: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[float] = None
    current_phase: Optional[str] = None


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    orchestrator_health: Dict[str, Any]
    timestamp: str


# API Application with M10 Observability Enhancement

app = FastAPI(
    title="Novel Engine Turn Orchestration API",
    description="REST API for executing and monitoring turn-based narrative orchestration with M10 Observability & Security",
    version="2.0.0",  # M10 enhanced version
    docs_url="/docs",
    redoc_url="/redoc",
)

# Initialize M10 observability components
prometheus_collector = PrometheusMetricsCollector()
enhanced_performance_tracker = EnhancedPerformanceTracker(prometheus_collector)

# Initialize distributed tracing (M10 requirement)
novel_engine_tracer = initialize_tracing()

# Add M10 observability middleware
app.add_middleware(
    PrometheusMiddleware,
    app_name="novel_engine_orchestration",
    group_paths=True,
    ignored_paths=[
        "/health",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico",
    ],
    metrics_collector=prometheus_collector,
)

# Setup FastAPI distributed tracing middleware (M10 requirement)
setup_fastapi_tracing(
    app=app,
    tracer=novel_engine_tracer,
    excluded_urls=[
        "/health",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico",
    ],
    enable_automatic_instrumentation=True,
)

# Global orchestrator instance with enhanced observability (M10)
turn_orchestrator = TurnOrchestrator(prometheus_collector=prometheus_collector)

# Active turn tracking (in production, this would use a proper database)
active_turns: Dict[str, Dict[str, Any]] = {}


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting Novel Engine Turn Orchestration API")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("Shutting down Novel Engine Turn Orchestration API")

    # Cleanup any active turn resources
    for turn_id in list(active_turns.keys()):
        try:
            await turn_orchestrator.cleanup_turn_resources(
                TurnId.from_string(turn_id)
            )
        except Exception as e:
            logger.error(f"Error cleaning up turn {turn_id}: {e}")


# Dependency injection


async def get_turn_orchestrator() -> TurnOrchestrator:
    """Dependency to get turn orchestrator instance."""
    return turn_orchestrator


# API Endpoints


@app.post("/v1/turns:run", response_model=TurnExecutionResponse)
async def execute_turn(
    request: TurnExecutionRequest,
    background_tasks: BackgroundTasks,
    orchestrator: TurnOrchestrator = Depends(get_turn_orchestrator),
) -> TurnExecutionResponse:
    """
    Execute a complete turn pipeline for the specified participants.

    This endpoint orchestrates the full 5-phase turn pipeline:
    1. World Update - Update world state and advance time
    2. Subjective Brief - Generate AI-powered agent perceptions
    3. Interaction Orchestration - Coordinate agent interactions
    4. Event Integration - Integrate interaction results into world
    5. Narrative Integration - Create narrative content with AI

    The execution includes saga pattern compensation for reliability
    and comprehensive error handling with rollback capabilities.
    """
    try:
        # Parse and validate turn ID
        turn_id = None
        if request.turn_id:
            turn_id = TurnId.from_string(request.turn_id)
        else:
            turn_id = TurnId.generate()

        # Parse configuration
        configuration = None
        if request.configuration:
            try:
                configuration = TurnConfiguration.from_dict(
                    request.configuration
                )
            except Exception as e:
                raise HTTPException(
                    status_code=400, detail=f"Invalid configuration: {e}"
                )
        else:
            configuration = TurnConfiguration.create_default()

        # Validate preconditions
        (
            is_valid,
            validation_errors,
        ) = await orchestrator.validate_turn_preconditions(
            request.participants, configuration
        )

        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Turn precondition validation failed",
                    "errors": validation_errors,
                },
            )

        # Track turn as active
        active_turns[str(turn_id.turn_uuid)] = {
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "participants": request.participants,
            "async_execution": request.async_execution,
        }

        logger.info(f"Starting turn execution: {turn_id}")

        if request.async_execution:
            # Execute asynchronously in background
            background_tasks.add_task(
                _execute_turn_background,
                turn_id,
                request.participants,
                configuration,
            )

            # Return immediate response for async execution
            return TurnExecutionResponse(
                turn_id=str(turn_id.turn_uuid),
                success=True,  # This indicates the request was accepted
                execution_time_ms=0,
                phases_completed=[],
                phase_results={},
                compensation_actions=[],
                performance_metrics={},
                completed_at=datetime.now().isoformat(),
            )

        else:
            # Execute synchronously
            result = await orchestrator.execute_turn(
                participants=request.participants,
                configuration=configuration,
                turn_id=turn_id,
            )

            # Update active turns tracking
            active_turns[str(turn_id.turn_uuid)] = {
                "status": "completed" if result.success else "failed",
                "completed_at": result.completed_at.isoformat(),
                "success": result.success,
            }

            # Convert to response format
            return _convert_to_response(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in execute_turn: {e}")
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        )


@app.get("/v1/turns/{turn_id}/status", response_model=TurnStatusResponse)
async def get_turn_status(
    turn_id: str,
    orchestrator: TurnOrchestrator = Depends(get_turn_orchestrator),
) -> TurnStatusResponse:
    """
    Get the current status of a turn execution.

    Returns information about turn progress, current phase,
    and execution metrics for monitoring purposes.
    """
    try:
        # Validate turn ID format
        try:
            parsed_turn_id = TurnId.from_string(turn_id)
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid turn_id format"
            )

        # Check active turns tracking
        if turn_id in active_turns:
            turn_info = active_turns[turn_id]

            # Get detailed status from orchestrator
            detailed_status = await orchestrator.get_turn_status(
                parsed_turn_id
            )

            return TurnStatusResponse(
                turn_id=turn_id,
                status=turn_info["status"],
                progress=detailed_status,
                execution_time_ms=(
                    detailed_status.get("execution_time_ms")
                    if detailed_status
                    else None
                ),
                current_phase=(
                    detailed_status.get("current_phase")
                    if detailed_status
                    else None
                ),
            )

        else:
            # Try to get status from orchestrator (might be completed/archived)
            detailed_status = await orchestrator.get_turn_status(
                parsed_turn_id
            )

            if detailed_status:
                return TurnStatusResponse(
                    turn_id=turn_id,
                    status=detailed_status.get("status", "unknown"),
                    progress=detailed_status,
                    execution_time_ms=detailed_status.get("execution_time_ms"),
                    current_phase=detailed_status.get("current_phase"),
                )
            else:
                return TurnStatusResponse(turn_id=turn_id, status="not_found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting turn status for {turn_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve turn status"
        )


@app.get("/v1/health", response_model=HealthResponse)
async def health_check(
    orchestrator: TurnOrchestrator = Depends(get_turn_orchestrator),
) -> HealthResponse:
    """
    Get health status of the turn orchestration service.

    Returns information about service health, active turns,
    and system capabilities for monitoring and diagnostics.
    """
    try:
        orchestrator_health = orchestrator.get_orchestrator_health()

        return HealthResponse(
            status="healthy",
            orchestrator_health=orchestrator_health,
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            orchestrator_health={"error": str(e)},
            timestamp=datetime.now().isoformat(),
        )


@app.get("/v1/turns", response_model=List[Dict[str, Any]])
async def list_active_turns() -> List[Dict[str, Any]]:
    """
    List all currently active turns.

    Returns summary information about turns that are currently
    running or recently completed.
    """
    try:
        return [
            {
                "turn_id": turn_id,
                "status": info["status"],
                "started_at": info.get("started_at"),
                "completed_at": info.get("completed_at"),
                "participants": info.get("participants", []),
                "async_execution": info.get("async_execution", False),
            }
            for turn_id, info in active_turns.items()
        ]

    except Exception as e:
        logger.error(f"Error listing active turns: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to list active turns"
        )


@app.delete("/v1/turns/{turn_id}")
async def cleanup_turn(
    turn_id: str,
    orchestrator: TurnOrchestrator = Depends(get_turn_orchestrator),
) -> Dict[str, str]:
    """
    Clean up resources for a completed or failed turn.

    Removes turn from active tracking and cleans up any
    associated resources, temporary files, or cached data.
    """
    try:
        # Validate turn ID format
        try:
            parsed_turn_id = TurnId.from_string(turn_id)
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid turn_id format"
            )

        # Remove from active tracking
        if turn_id in active_turns:
            del active_turns[turn_id]

        # Cleanup orchestrator resources
        await orchestrator.cleanup_turn_resources(parsed_turn_id)

        return {"status": "cleaned_up", "turn_id": turn_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up turn {turn_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to cleanup turn resources"
        )


# Utility Functions


async def _execute_turn_background(
    turn_id: TurnId, participants: List[str], configuration: TurnConfiguration
) -> None:
    """Execute turn in background task for async requests."""
    try:
        logger.info(f"Starting background turn execution: {turn_id}")

        result = await turn_orchestrator.execute_turn(
            participants=participants,
            configuration=configuration,
            turn_id=turn_id,
        )

        # Update active turns tracking
        active_turns[str(turn_id.turn_uuid)] = {
            "status": "completed" if result.success else "failed",
            "completed_at": result.completed_at.isoformat(),
            "success": result.success,
            "execution_time_ms": result.execution_time_ms,
        }

        logger.info(
            f"Background turn execution completed: {turn_id}, success={result.success}"
        )

    except Exception as e:
        logger.error(f"Background turn execution failed: {turn_id}, error={e}")

        # Update tracking with failure status
        active_turns[str(turn_id.turn_uuid)] = {
            "status": "failed",
            "completed_at": datetime.now().isoformat(),
            "success": False,
            "error": str(e),
        }


def _convert_to_response(result) -> TurnExecutionResponse:
    """Convert TurnExecutionResult to API response format."""
    # Convert phase results to response format
    phase_results_dict = {}
    for phase_type, phase_result in result.phase_results.items():
        phase_results_dict[phase_type.value] = PhaseResultSummary(
            phase=phase_type.value,
            success=phase_result.success,
            execution_time_ms=phase_result.performance_metrics.get(
                "execution_time_ms", 0
            ),
            events_processed=phase_result.events_processed,
            events_generated=len(phase_result.events_generated),
            artifacts_created=phase_result.artifacts_created,
            ai_cost=(
                float(phase_result.ai_usage["total_cost"])
                if phase_result.ai_usage
                else None
            ),
            error_message=(
                phase_result.error_details.get("message")
                if phase_result.error_details
                else None
            ),
        )

    # Convert compensation actions
    compensation_actions = []
    for action in result.compensation_actions:
        compensation_actions.append(
            {
                "action_id": str(action.action_id),
                "compensation_type": action.compensation_type.value,
                "target_phase": action.target_phase,
                "triggered_at": action.triggered_at.isoformat(),
                "status": (
                    action.status.value
                    if hasattr(action, "status")
                    else "executed"
                ),
            }
        )

    return TurnExecutionResponse(
        turn_id=str(result.turn_id.turn_uuid),
        success=result.success,
        execution_time_ms=result.execution_time_ms,
        phases_completed=[phase.value for phase in result.phases_completed],
        phase_results=phase_results_dict,
        compensation_actions=compensation_actions,
        performance_metrics=result.performance_metrics,
        error_details=result.error_details,
        completed_at=result.completed_at.isoformat(),
    )


# M10 Observability Endpoints


@app.get("/metrics")
async def get_prometheus_metrics():
    """
    Prometheus metrics endpoint.

    Exposes comprehensive metrics including:
    - Core KPIs: novel_engine_llm_cost_per_request_dollars, novel_engine_turn_duration_seconds
    - HTTP request metrics from middleware
    - Business metrics from enhanced performance tracker
    - Operational metrics for monitoring and alerting

    Returns:
        Prometheus metrics in standard format
    """
    try:
        metrics_data = prometheus_collector.get_metrics_data()
        content_type = prometheus_collector.get_metrics_content_type()

        logger.debug("Prometheus metrics requested and served successfully")

        return Response(content=metrics_data, media_type=content_type)
    except Exception as e:
        logger.error(f"Error serving Prometheus metrics: {e}")
        raise HTTPException(
            status_code=500, detail="Error retrieving metrics data"
        )


@app.get("/v1/metrics/business-kpis")
async def get_business_kpis():
    """
    Business KPIs summary endpoint.

    Provides business-focused metrics summary including:
    - Average LLM cost per request
    - Turn duration statistics (avg, p95)
    - Success rates
    - Throughput metrics

    Returns:
        JSON summary of business KPIs
    """
    try:
        kpi_summary = enhanced_performance_tracker.get_business_kpi_summary()

        return JSONResponse(
            content={
                "business_kpis": kpi_summary,
                "timestamp": datetime.now().isoformat(),
                "description": "Core business KPIs for turn orchestration system",
            }
        )
    except Exception as e:
        logger.error(f"Error retrieving business KPIs: {e}")
        raise HTTPException(
            status_code=500, detail="Error retrieving business KPI data"
        )


# Error Handlers


@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle validation errors."""
    return JSONResponse(
        status_code=400,
        content={
            "detail": f"Validation error: {str(exc)}",
            "error_type": "validation_error",
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected errors."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_type": "internal_error",
        },
    )


# Development Server
if __name__ == "__main__":
    uvicorn.run(
        "turn_api:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True,
    )
