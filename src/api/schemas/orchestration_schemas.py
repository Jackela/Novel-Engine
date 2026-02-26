"""Orchestration API schemas for the Novel Engine.

This module contains schemas for the orchestration system that manages
multi-character narrative generation and turn-based storytelling.

Schemas:
- OrchestrationStep: Individual step within orchestration progress
- OrchestrationStatusData: Detailed status information
- OrchestrationStatusResponse: Status endpoint response
- OrchestrationStartRequest: Request to start orchestration
- OrchestrationStartResponse: Response after starting
- OrchestrationStopResponse: Response after stopping

Created as part of PREP-002 (Operation Vanguard).
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class OrchestrationStep(BaseModel):
    """Step within orchestration progress."""

    id: str = Field(..., description="Unique identifier for this step")
    name: str = Field(..., description="Human-readable name of the step")
    status: str = Field(
        ..., description="Current status: pending, running, completed, failed"
    )
    progress: float = Field(ge=0, le=100, description="Completion percentage (0-100)")


class OrchestrationStatusData(BaseModel):
    """Orchestration status data structure."""

    status: str = Field(
        ...,
        description="Overall orchestration status: idle, running, paused, completed",
    )
    current_turn: int = Field(0, description="Current turn number being processed")
    total_turns: int = Field(0, description="Total number of turns to process")
    queue_length: int = Field(
        0, description="Number of pending operations in the queue"
    )
    average_processing_time: float = Field(
        0.0, description="Average time per turn in seconds"
    )
    steps: List[OrchestrationStep] = Field(
        default_factory=list, description="Detailed step breakdown"
    )
    last_updated: Optional[str] = Field(
        None, description="ISO 8601 timestamp of last status update"
    )


class OrchestrationStatusResponse(BaseModel):
    """Response for orchestration status endpoint."""

    success: bool
    data: OrchestrationStatusData
    message: Optional[str] = None


class OrchestrationStartRequest(BaseModel):
    """Request to start orchestration."""

    character_names: Optional[List[str]] = Field(
        None,
        min_length=2,
        max_length=6,
        description="List of character names to include (2-6 characters)",
    )
    total_turns: Optional[int] = Field(
        3, ge=1, le=10, description="Number of narrative turns to generate (1-10)"
    )
    setting: Optional[str] = Field(None, description="World setting name or ID")
    scenario: Optional[str] = Field(None, description="Initial scenario description")


class OrchestrationStartResponse(BaseModel):
    """Response after starting orchestration."""

    success: bool
    status: str
    task_id: Optional[str] = None
    message: Optional[str] = None


class OrchestrationStopResponse(BaseModel):
    """Response after stopping orchestration."""

    success: bool
    message: Optional[str] = None
