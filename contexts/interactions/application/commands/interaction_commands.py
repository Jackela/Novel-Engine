#!/usr/bin/env python3
"""
Interaction Application Commands

This module implements command objects for the Interaction bounded context,
following CQRS principles to encapsulate business operations with their
required data and validation logic.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from ...domain.value_objects.negotiation_party import (
    AuthorityLevel,
    NegotiationCapability,
    NegotiationParty,
)
from ...domain.value_objects.negotiation_status import (
    NegotiationOutcome,
    NegotiationPhase,
    TerminationReason,
)
from ...domain.value_objects.proposal_response import ProposalResponse, TermResponse
from ...domain.value_objects.proposal_terms import ProposalTerms, TermCondition


# Base Command Class
@dataclass(frozen=True)
class InteractionCommand:
    """Base class for all interaction commands."""

    command_id: UUID
    timestamp: datetime
    initiated_by: UUID

    def __post_init__(self):
        """Validate base command data."""
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")


# Session Management Commands


@dataclass(frozen=True)
class CreateNegotiationSessionCommand(InteractionCommand):
    """Command to create a new negotiation session."""

    session_name: str
    session_type: str
    negotiation_domain: Optional[str] = None
    max_parties: int = 10
    session_timeout_hours: int = 72
    auto_advance_phases: bool = True
    require_unanimous_agreement: bool = False
    allow_partial_agreements: bool = True
    session_context: Optional[Dict[str, Any]] = None
    priority_level: str = "medium"
    confidentiality_level: str = "standard"

    def __post_init__(self):
        super().__post_init__()
        if not self.session_name.strip():
            raise ValueError("session_name cannot be empty")
        if not self.session_type.strip():
            raise ValueError("session_type cannot be empty")
        if self.max_parties < 2:
            raise ValueError("max_parties must be at least 2")
        if self.session_timeout_hours <= 0:
            raise ValueError("session_timeout_hours must be positive")
        if self.priority_level not in ["low", "medium", "high", "critical"]:
            raise ValueError(
                "priority_level must be one of: low, medium, high, critical"
            )
        if self.confidentiality_level not in [
            "public",
            "standard",
            "confidential",
            "secret",
        ]:
            raise ValueError(
                "confidentiality_level must be one of: public, standard, confidential, secret"
            )


@dataclass(frozen=True)
class TerminateNegotiationSessionCommand(InteractionCommand):
    """Command to terminate a negotiation session."""

    session_id: UUID
    outcome: NegotiationOutcome
    termination_reason: TerminationReason
    completion_notes: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.outcome, NegotiationOutcome):
            raise ValueError("outcome must be a NegotiationOutcome")
        if not isinstance(self.termination_reason, TerminationReason):
            raise ValueError("termination_reason must be a TerminationReason")


@dataclass(frozen=True)
class AdvanceNegotiationPhaseCommand(InteractionCommand):
    """Command to advance negotiation to a new phase."""

    session_id: UUID
    target_phase: NegotiationPhase
    force_advancement: bool = False
    advancement_reason: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.target_phase, NegotiationPhase):
            raise ValueError("target_phase must be a NegotiationPhase")


@dataclass(frozen=True)
class UpdateSessionConfigurationCommand(InteractionCommand):
    """Command to update session configuration."""

    session_id: UUID
    max_parties: Optional[int] = None
    session_timeout_hours: Optional[int] = None
    auto_advance_phases: Optional[bool] = None
    require_unanimous_agreement: Optional[bool] = None
    allow_partial_agreements: Optional[bool] = None
    priority_level: Optional[str] = None
    confidentiality_level: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        if self.max_parties is not None and self.max_parties < 2:
            raise ValueError("max_parties must be at least 2")
        if self.session_timeout_hours is not None and self.session_timeout_hours <= 0:
            raise ValueError("session_timeout_hours must be positive")
        if self.priority_level is not None and self.priority_level not in [
            "low",
            "medium",
            "high",
            "critical",
        ]:
            raise ValueError(
                "priority_level must be one of: low, medium, high, critical"
            )
        if (
            self.confidentiality_level is not None
            and self.confidentiality_level
            not in ["public", "standard", "confidential", "secret"]
        ):
            raise ValueError(
                "confidentiality_level must be one of: public, standard, confidential, secret"
            )


@dataclass(frozen=True)
class CheckSessionTimeoutCommand(InteractionCommand):
    """Command to check and handle session timeout."""

    session_id: UUID
    warning_hours: int = 24
    auto_terminate_on_timeout: bool = False

    def __post_init__(self):
        super().__post_init__()
        if self.warning_hours <= 0:
            raise ValueError("warning_hours must be positive")


# Party Management Commands


@dataclass(frozen=True)
class AddPartyToSessionCommand(InteractionCommand):
    """Command to add a party to a negotiation session."""

    session_id: UUID
    party: NegotiationParty
    validate_compatibility: bool = True

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.party, NegotiationParty):
            raise ValueError("party must be a NegotiationParty instance")


@dataclass(frozen=True)
class RemovePartyFromSessionCommand(InteractionCommand):
    """Command to remove a party from a negotiation session."""

    session_id: UUID
    party_id: UUID
    removal_reason: Optional[str] = None
    transfer_authority_to: Optional[UUID] = None

    def __post_init__(self):
        super().__post_init__()
        # No additional validation needed beyond base class


@dataclass(frozen=True)
class UpdatePartyCapabilitiesCommand(InteractionCommand):
    """Command to update a party's negotiation capabilities."""

    session_id: UUID
    party_id: UUID
    updated_capabilities: List[NegotiationCapability]
    update_reason: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        if not self.updated_capabilities:
            raise ValueError("updated_capabilities cannot be empty")

        # Validate capability uniqueness
        capability_names = [cap.capability_name for cap in self.updated_capabilities]
        if len(capability_names) != len(set(capability_names)):
            raise ValueError("Capability names must be unique")


@dataclass(frozen=True)
class UpdatePartyAuthorityCommand(InteractionCommand):
    """Command to update a party's authority level."""

    session_id: UUID
    party_id: UUID
    new_authority_level: AuthorityLevel
    authority_constraints: Optional[Dict[str, Any]] = None
    update_reason: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.new_authority_level, AuthorityLevel):
            raise ValueError("new_authority_level must be an AuthorityLevel")


# Proposal Management Commands


@dataclass(frozen=True)
class SubmitProposalCommand(InteractionCommand):
    """Command to submit a proposal to a negotiation."""

    session_id: UUID
    proposal: ProposalTerms
    submission_notes: Optional[str] = None
    auto_advance_phase: bool = True

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.proposal, ProposalTerms):
            raise ValueError("proposal must be a ProposalTerms instance")
        if self.proposal.is_expired:
            raise ValueError("Cannot submit expired proposal")


@dataclass(frozen=True)
class WithdrawProposalCommand(InteractionCommand):
    """Command to withdraw a proposal from a negotiation."""

    session_id: UUID
    proposal_id: UUID
    withdrawal_reason: Optional[str] = None
    replacement_proposal: Optional[ProposalTerms] = None

    def __post_init__(self):
        super().__post_init__()
        if self.replacement_proposal and self.replacement_proposal.is_expired:
            raise ValueError("Cannot submit expired replacement proposal")


@dataclass(frozen=True)
class UpdateProposalCommand(InteractionCommand):
    """Command to update an existing proposal."""

    session_id: UUID
    proposal_id: UUID
    updated_terms: List[TermCondition]
    update_reason: Optional[str] = None
    notify_parties: bool = True

    def __post_init__(self):
        super().__post_init__()
        if not self.updated_terms:
            raise ValueError("updated_terms cannot be empty")


@dataclass(frozen=True)
class OptimizeProposalCommand(InteractionCommand):
    """Command to optimize a proposal for better acceptance."""

    session_id: UUID
    proposal_id: UUID
    optimization_target: str = "maximize_acceptance"
    consider_party_preferences: bool = True
    preserve_critical_terms: bool = True
    max_modifications: int = 5

    def __post_init__(self):
        super().__post_init__()
        if self.optimization_target not in [
            "maximize_acceptance",
            "minimize_risk",
            "balance_interests",
            "speed_resolution",
        ]:
            raise ValueError(
                "optimization_target must be one of: maximize_acceptance, minimize_risk, balance_interests, speed_resolution"
            )
        if self.max_modifications <= 0:
            raise ValueError("max_modifications must be positive")


# Response Management Commands


@dataclass(frozen=True)
class SubmitProposalResponseCommand(InteractionCommand):
    """Command to submit a response to a proposal."""

    session_id: UUID
    response: ProposalResponse
    auto_advance_on_completion: bool = True
    notification_preferences: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.response, ProposalResponse):
            raise ValueError("response must be a ProposalResponse instance")
        if self.response.is_expired():
            raise ValueError("Cannot submit expired response")


@dataclass(frozen=True)
class UpdateResponseCommand(InteractionCommand):
    """Command to update an existing response."""

    session_id: UUID
    response_id: UUID
    updated_term_responses: Optional[List[TermResponse]] = None
    updated_overall_response: Optional[str] = None
    updated_conditions: Optional[List[str]] = None
    update_reason: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        if (
            not self.updated_term_responses
            and not self.updated_overall_response
            and not self.updated_conditions
        ):
            raise ValueError("At least one update field must be provided")


# Analysis Commands


@dataclass(frozen=True)
class AnalyzeProposalViabilityCommand(InteractionCommand):
    """Command to analyze proposal viability."""

    session_id: UUID
    proposal_id: UUID
    include_optimization_suggestions: bool = True
    analysis_depth: str = "standard"
    focus_areas: Optional[List[str]] = None

    def __post_init__(self):
        super().__post_init__()
        if self.analysis_depth not in ["basic", "standard", "comprehensive"]:
            raise ValueError(
                "analysis_depth must be one of: basic, standard, comprehensive"
            )


@dataclass(frozen=True)
class AssessPartyCompatibilityCommand(InteractionCommand):
    """Command to assess compatibility between parties."""

    session_id: UUID
    party_ids: Optional[List[UUID]] = None  # If None, assess all parties
    compatibility_factors: Optional[List[str]] = None
    include_recommendations: bool = True

    def __post_init__(self):
        super().__post_init__()
        if self.party_ids is not None and len(self.party_ids) < 2:
            raise ValueError("party_ids must contain at least 2 parties")


@dataclass(frozen=True)
class RecommendNegotiationStrategyCommand(InteractionCommand):
    """Command to recommend negotiation strategy."""

    session_id: UUID
    target_outcome: Optional[str] = None
    strategy_focus: str = "balanced"
    timeline_constraints: Optional[Dict[str, Any]] = None
    include_tactics: bool = True

    def __post_init__(self):
        super().__post_init__()
        if self.strategy_focus not in [
            "aggressive",
            "balanced",
            "conservative",
            "collaborative",
        ]:
            raise ValueError(
                "strategy_focus must be one of: aggressive, balanced, conservative, collaborative"
            )


@dataclass(frozen=True)
class DetectNegotiationConflictsCommand(InteractionCommand):
    """Command to detect conflicts in negotiation."""

    session_id: UUID
    conflict_types: Optional[List[str]] = None
    include_resolution_suggestions: bool = True
    severity_threshold: str = "medium"

    def __post_init__(self):
        super().__post_init__()
        if self.severity_threshold not in ["low", "medium", "high", "critical"]:
            raise ValueError(
                "severity_threshold must be one of: low, medium, high, critical"
            )


@dataclass(frozen=True)
class CalculateNegotiationMomentumCommand(InteractionCommand):
    """Command to calculate negotiation momentum."""

    session_id: UUID
    analysis_window_hours: int = 24
    include_predictions: bool = True
    momentum_factors: Optional[List[str]] = None

    def __post_init__(self):
        super().__post_init__()
        if self.analysis_window_hours <= 0:
            raise ValueError("analysis_window_hours must be positive")


# Bulk Operation Commands


@dataclass(frozen=True)
class BatchUpdatePartiesCommand(InteractionCommand):
    """Command to update multiple parties in batch."""

    session_id: UUID
    party_updates: List[Dict[str, Any]]
    validate_each_update: bool = True
    stop_on_first_error: bool = False

    def __post_init__(self):
        super().__post_init__()
        if not self.party_updates:
            raise ValueError("party_updates cannot be empty")

        # Validate each update has required fields
        for update in self.party_updates:
            if "party_id" not in update:
                raise ValueError("Each party update must include 'party_id'")


@dataclass(frozen=True)
class BatchSubmitResponsesCommand(InteractionCommand):
    """Command to submit multiple responses in batch."""

    session_id: UUID
    responses: List[ProposalResponse]
    validate_each_response: bool = True
    auto_advance_on_batch_completion: bool = True

    def __post_init__(self):
        super().__post_init__()
        if not self.responses:
            raise ValueError("responses cannot be empty")

        # Validate all responses
        for response in self.responses:
            if not isinstance(response, ProposalResponse):
                raise ValueError("All responses must be ProposalResponse instances")
            if response.is_expired():
                raise ValueError("Cannot submit expired responses")


# Integration Commands


@dataclass(frozen=True)
class SynchronizeExternalDataCommand(InteractionCommand):
    """Command to synchronize external data sources."""

    session_id: UUID
    data_sources: List[str]
    sync_type: str = "incremental"
    conflict_resolution_strategy: str = "merge"

    def __post_init__(self):
        super().__post_init__()
        if not self.data_sources:
            raise ValueError("data_sources cannot be empty")
        if self.sync_type not in ["full", "incremental", "differential"]:
            raise ValueError(
                "sync_type must be one of: full, incremental, differential"
            )
        if self.conflict_resolution_strategy not in ["overwrite", "merge", "manual"]:
            raise ValueError(
                "conflict_resolution_strategy must be one of: overwrite, merge, manual"
            )


@dataclass(frozen=True)
class ExportNegotiationDataCommand(InteractionCommand):
    """Command to export negotiation data."""

    session_id: UUID
    export_format: str = "json"
    include_sensitive_data: bool = False
    export_scope: str = "session"
    anonymize_parties: bool = False

    def __post_init__(self):
        super().__post_init__()
        if self.export_format not in ["json", "xml", "csv", "pdf"]:
            raise ValueError("export_format must be one of: json, xml, csv, pdf")
        if self.export_scope not in ["session", "proposals", "responses", "summary"]:
            raise ValueError(
                "export_scope must be one of: session, proposals, responses, summary"
            )


# Monitoring Commands


@dataclass(frozen=True)
class GenerateSessionReportCommand(InteractionCommand):
    """Command to generate comprehensive session report."""

    session_id: UUID
    report_type: str = "comprehensive"
    include_analytics: bool = True
    include_recommendations: bool = True
    target_audience: str = "technical"

    def __post_init__(self):
        super().__post_init__()
        if self.report_type not in [
            "summary",
            "comprehensive",
            "analytical",
            "executive",
        ]:
            raise ValueError(
                "report_type must be one of: summary, comprehensive, analytical, executive"
            )
        if self.target_audience not in [
            "technical",
            "business",
            "executive",
            "general",
        ]:
            raise ValueError(
                "target_audience must be one of: technical, business, executive, general"
            )


@dataclass(frozen=True)
class SchedulePeriodicAnalysisCommand(InteractionCommand):
    """Command to schedule periodic analysis of negotiation."""

    session_id: UUID
    analysis_frequency_hours: int = 6
    analysis_types: List[str] = None
    alert_thresholds: Optional[Dict[str, Any]] = None
    auto_recommendations: bool = True

    def __post_init__(self):
        super().__post_init__()
        if self.analysis_frequency_hours <= 0:
            raise ValueError("analysis_frequency_hours must be positive")
        if self.analysis_types is None:
            self.analysis_types = ["momentum", "conflicts", "viability"]
