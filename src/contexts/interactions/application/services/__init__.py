#!/usr/bin/env python3
"""
Interaction Application Services

This module exports all application services for the Interaction bounded context.
Services use the Result[T,E] pattern for explicit error handling.
"""

# Core Result imports
from .....core.result import Err, Ok, Result

# Application services (12 services total)
from .analytics_service import AnalyticsService
from .batch_operation_service import BatchOperationService
from .compatibility_service import CompatibilityService
from .conflict_resolution_service import ConflictResolutionService
from .health_monitoring_service import HealthMonitoringService
from .interaction_application_service import InteractionApplicationService
from .negotiation_application_service import NegotiationApplicationService
from .outcome_calculator import OutcomeCalculator
from .proposal_service import ProposalService
from .response_analysis_service import ResponseAnalysisService
from .session_management_service import SessionManagementService

# Shared error types and Result wrapper
from .shared.errors import (
    AuthorizationError,
    CompatibilityError,
    ConflictError,
    InteractionError,
    NegotiationError,
    NotFoundError,
    OutcomeError,
    ProposalError,
    SessionError,
    ValidationError,
)
from .shared.results import InteractionResult, interaction_err, interaction_ok
from .strategy_service import StrategyService

__all__ = [
    # Core Result types
    "Result",
    "Ok",
    "Err",
    # Error types
    "InteractionError",
    "NegotiationError",
    "ProposalError",
    "OutcomeError",
    "CompatibilityError",
    "ConflictError",
    "SessionError",
    "ValidationError",
    "NotFoundError",
    "AuthorizationError",
    # Result helpers
    "InteractionResult",
    "interaction_ok",
    "interaction_err",
    # Services (12 total)
    "InteractionApplicationService",
    "NegotiationApplicationService",
    "ProposalService",
    "OutcomeCalculator",
    "CompatibilityService",
    "SessionManagementService",
    "ResponseAnalysisService",
    "StrategyService",
    "HealthMonitoringService",
    "BatchOperationService",
    "ConflictResolutionService",
    "AnalyticsService",
]
