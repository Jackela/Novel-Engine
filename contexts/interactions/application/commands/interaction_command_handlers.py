#!/usr/bin/env python3
"""
Interaction Command Handlers

This module implements command handlers for the Interaction bounded context,
providing the business logic execution layer that coordinates between
application commands and domain objects.
"""

from typing import Any, Dict, List, cast
from uuid import UUID

from ...domain.aggregates.negotiation_session import NegotiationSession
from ...domain.repositories.negotiation_session_repository import (
    NegotiationSessionRepository,
)
from ...domain.services.negotiation_service import NegotiationService
from ...domain.value_objects.interaction_id import InteractionId
from .interaction_commands import (  # Session Commands; Party Commands; Proposal Commands; Response Commands; Analysis Commands; Bulk Commands; Integration Commands; Monitoring Commands
    AddPartyToSessionCommand,
    AdvanceNegotiationPhaseCommand,
    AnalyzeProposalViabilityCommand,
    AssessPartyCompatibilityCommand,
    BatchSubmitResponsesCommand,
    BatchUpdatePartiesCommand,
    CalculateNegotiationMomentumCommand,
    CheckSessionTimeoutCommand,
    CreateNegotiationSessionCommand,
    DetectNegotiationConflictsCommand,
    OptimizeProposalCommand,
    RecommendNegotiationStrategyCommand,
    RemovePartyFromSessionCommand,
    SubmitProposalCommand,
    SubmitProposalResponseCommand,
    TerminateNegotiationSessionCommand,
    UpdatePartyAuthorityCommand,
    UpdatePartyCapabilitiesCommand,
    UpdateProposalCommand,
    UpdateResponseCommand,
    UpdateSessionConfigurationCommand,
    WithdrawProposalCommand,
)


class InteractionCommandHandler:
    """
    Main command handler for Interaction bounded context operations.

    Orchestrates business logic execution by coordinating between
    application commands, domain services, and repository operations.
    """

    def __init__(
        self,
        session_repository: NegotiationSessionRepository,
        negotiation_service: NegotiationService,
    ):
        """Initialize command handler with required dependencies."""
        self.session_repository = session_repository
        self.negotiation_service = negotiation_service

    # Session Management Command Handlers

    async def handle_create_negotiation_session(
        self, command: CreateNegotiationSessionCommand
    ) -> Dict[str, Any]:
        """Handle creation of new negotiation session."""
        # Create new negotiation session aggregate
        session = NegotiationSession.create(
            session_name=command.session_name,
            session_type=command.session_type,
            created_by=command.initiated_by,
            negotiation_domain=command.negotiation_domain,
            max_parties=command.max_parties,
            session_timeout_hours=command.session_timeout_hours,
            session_context=command.session_context or {},
        )

        # Configure session based on command parameters
        if not command.auto_advance_phases:
            session.auto_advance_phases = False

        if command.require_unanimous_agreement:
            session.require_unanimous_agreement = True

        if not command.allow_partial_agreements:
            session.allow_partial_agreements = False

        session.priority_level = command.priority_level
        session.confidentiality_level = command.confidentiality_level

        # Persist the session
        await self.session_repository.save(session)

        return {
            "session_id": str(session.session_id),
            "session_name": session.session_name,
            "created_at": session.created_at,
            "status": session.status.phase.value,
            "max_parties": session.max_parties,
            "events": [
                event.__class__.__name__
                for event in session.get_uncommitted_events()
            ],
        }

    async def handle_terminate_negotiation_session(
        self, command: TerminateNegotiationSessionCommand
    ) -> Dict[str, Any]:
        """Handle termination of negotiation session."""
        # Retrieve session
        session = await self.session_repository.get_by_id(
            InteractionId(command.session_id)
        )

        if not session:
            raise ValueError(f"Session {command.session_id} not found")

        # Terminate session
        session.terminate_negotiation(
            outcome=command.outcome,
            termination_reason=command.termination_reason,
            terminated_by=command.initiated_by,
        )

        # Persist changes
        await self.session_repository.save(session)

        return {
            "session_id": str(session.session_id),
            "outcome": command.outcome.value,
            "termination_reason": command.termination_reason.value,
            "terminated_at": session.status.actual_completion_at,
            "duration": session.status.duration,
            "events": [
                event.__class__.__name__
                for event in session.get_uncommitted_events()
            ],
        }

    async def handle_advance_negotiation_phase(
        self, command: AdvanceNegotiationPhaseCommand
    ) -> Dict[str, Any]:
        """Handle advancement of negotiation phase."""
        # Retrieve session
        session = await self.session_repository.get_by_id(
            InteractionId(command.session_id)
        )

        if not session:
            raise ValueError(f"Session {command.session_id} not found")

        # Advance phase
        old_phase = session.status.phase
        session.advance_phase(
            target_phase=command.target_phase, forced=command.force_advancement
        )

        # Persist changes
        await self.session_repository.save(session)

        return {
            "session_id": str(session.session_id),
            "from_phase": old_phase.value,
            "to_phase": command.target_phase.value,
            "forced": command.force_advancement,
            "advancement_reason": command.advancement_reason,
            "events": [
                event.__class__.__name__
                for event in session.get_uncommitted_events()
            ],
        }

    async def handle_update_session_configuration(
        self, command: UpdateSessionConfigurationCommand
    ) -> Dict[str, Any]:
        """Handle update of session configuration."""
        # Retrieve session
        session = await self.session_repository.get_by_id(
            InteractionId(command.session_id)
        )

        if not session:
            raise ValueError(f"Session {command.session_id} not found")

        # Update configuration fields
        updates_made = []

        if command.max_parties is not None:
            session.max_parties = command.max_parties
            updates_made.append("max_parties")

        if command.session_timeout_hours is not None:
            session.session_timeout_hours = command.session_timeout_hours
            updates_made.append("session_timeout_hours")

        if command.auto_advance_phases is not None:
            session.auto_advance_phases = command.auto_advance_phases
            updates_made.append("auto_advance_phases")

        if command.require_unanimous_agreement is not None:
            session.require_unanimous_agreement = (
                command.require_unanimous_agreement
            )
            updates_made.append("require_unanimous_agreement")

        if command.allow_partial_agreements is not None:
            session.allow_partial_agreements = command.allow_partial_agreements
            updates_made.append("allow_partial_agreements")

        if command.priority_level is not None:
            session.priority_level = command.priority_level
            updates_made.append("priority_level")

        if command.confidentiality_level is not None:
            session.confidentiality_level = command.confidentiality_level
            updates_made.append("confidentiality_level")

        # Persist changes
        await self.session_repository.save(session)

        return {
            "session_id": str(session.session_id),
            "updates_made": updates_made,
            "current_config": {
                "max_parties": session.max_parties,
                "session_timeout_hours": session.session_timeout_hours,
                "auto_advance_phases": session.auto_advance_phases,
                "require_unanimous_agreement": session.require_unanimous_agreement,
                "allow_partial_agreements": session.allow_partial_agreements,
                "priority_level": session.priority_level,
                "confidentiality_level": session.confidentiality_level,
            },
        }

    async def handle_check_session_timeout(
        self, command: CheckSessionTimeoutCommand
    ) -> Dict[str, Any]:
        """Handle checking and processing session timeout."""
        # Retrieve session
        session = await self.session_repository.get_by_id(
            InteractionId(command.session_id)
        )

        if not session:
            raise ValueError(f"Session {command.session_id} not found")

        # Check timeout
        was_active_before = session.is_active
        timeout_approaching = session.is_timeout_approaching(
            command.warning_hours
        )

        # Handle timeout
        session.check_timeout()

        # Auto-terminate if configured and timed out
        if (
            command.auto_terminate_on_timeout
            and was_active_before
            and not session.is_active
        ):
            # Session was auto-terminated due to timeout
            pass

        # Persist changes
        await self.session_repository.save(session)

        return {
            "session_id": str(session.session_id),
            "timeout_approaching": timeout_approaching,
            "was_terminated": was_active_before and not session.is_active,
            "is_active": session.is_active,
            "time_since_last_activity": session.status.time_since_last_activity,
            "events": [
                event.__class__.__name__
                for event in session.get_uncommitted_events()
            ],
        }

    # Party Management Command Handlers

    async def handle_add_party_to_session(
        self, command: AddPartyToSessionCommand
    ) -> Dict[str, Any]:
        """Handle adding party to negotiation session."""
        # Retrieve session
        session = await self.session_repository.get_by_id(
            InteractionId(command.session_id)
        )

        if not session:
            raise ValueError(f"Session {command.session_id} not found")

        # Validate compatibility if requested
        compatibility_score = None
        if command.validate_compatibility and session.parties:
            # Check compatibility with existing parties
            existing_parties = list(session.parties.values())
            compatibility_scores = []

            for existing_party in existing_parties:
                score = self.negotiation_service.assess_party_compatibility(
                    command.party, existing_party, session.negotiation_domain
                )
                compatibility_scores.append(float(score))

            compatibility_score = sum(compatibility_scores) / len(
                compatibility_scores
            )

            # Reject if very poor compatibility
            if compatibility_score < 20:
                raise ValueError(
                    f"Party {command.party.party_name} has very poor compatibility with existing parties (score: {compatibility_score:.1f})"
                )

        # Add party to session
        session.add_party(command.party)

        # Persist changes
        await self.session_repository.save(session)

        return {
            "session_id": str(session.session_id),
            "party_id": str(command.party.party_id),
            "party_name": command.party.party_name,
            "party_role": command.party.role.value,
            "compatibility_score": compatibility_score,
            "total_parties": len(session.parties),
            "events": [
                event.__class__.__name__
                for event in session.get_uncommitted_events()
            ],
        }

    async def handle_remove_party_from_session(
        self, command: RemovePartyFromSessionCommand
    ) -> Dict[str, Any]:
        """Handle removing party from negotiation session."""
        # Retrieve session
        session = await self.session_repository.get_by_id(
            InteractionId(command.session_id)
        )

        if not session:
            raise ValueError(f"Session {command.session_id} not found")

        # Get party info before removal
        party = session.parties.get(command.party_id)
        if not party:
            raise ValueError(f"Party {command.party_id} not found in session")

        party_name = party.party_name
        party_role = party.role.value

        # Handle authority transfer if specified
        if command.transfer_authority_to:
            transfer_party = session.parties.get(command.transfer_authority_to)
            if not transfer_party:
                raise ValueError(
                    f"Transfer target party {command.transfer_authority_to} not found"
                )

            # This would require domain logic to transfer authority
            # For now, just document the intent

        # Remove party from session
        session.remove_party(command.party_id, command.removal_reason)

        # Persist changes
        await self.session_repository.save(session)

        return {
            "session_id": str(session.session_id),
            "removed_party_id": str(command.party_id),
            "removed_party_name": party_name,
            "removed_party_role": party_role,
            "removal_reason": command.removal_reason,
            "authority_transferred_to": (
                str(command.transfer_authority_to)
                if command.transfer_authority_to
                else None
            ),
            "remaining_parties": len(session.parties),
            "events": [
                event.__class__.__name__
                for event in session.get_uncommitted_events()
            ],
        }

    async def handle_update_party_capabilities(
        self, command: UpdatePartyCapabilitiesCommand
    ) -> Dict[str, Any]:
        """Handle updating party capabilities."""
        # Retrieve session
        session = await self.session_repository.get_by_id(
            InteractionId(command.session_id)
        )

        if not session:
            raise ValueError(f"Session {command.session_id} not found")

        # Get existing party
        existing_party = session.parties.get(command.party_id)
        if not existing_party:
            raise ValueError(f"Party {command.party_id} not found in session")

        # Update party capabilities
        updated_party = existing_party
        for capability in command.updated_capabilities:
            updated_party = updated_party.with_updated_capability(capability)

        # Update party in session
        session.parties[command.party_id] = updated_party

        # Persist changes
        await self.session_repository.save(session)

        return {
            "session_id": str(session.session_id),
            "party_id": str(command.party_id),
            "updated_capabilities": [
                cap.capability_name for cap in command.updated_capabilities
            ],
            "total_capabilities": len(updated_party.capabilities),
            "update_reason": command.update_reason,
            "average_proficiency": float(updated_party.average_proficiency),
        }

    async def handle_update_party_authority(
        self, command: UpdatePartyAuthorityCommand
    ) -> Dict[str, Any]:
        """Handle updating party authority level."""
        # Retrieve session
        session = await self.session_repository.get_by_id(
            InteractionId(command.session_id)
        )

        if not session:
            raise ValueError(f"Session {command.session_id} not found")

        # Get existing party
        existing_party = session.parties.get(command.party_id)
        if not existing_party:
            raise ValueError(f"Party {command.party_id} not found in session")

        old_authority = existing_party.authority_level

        # Update party authority
        updated_party = existing_party.with_updated_authority(
            command.new_authority_level
        )

        # Update party in session
        session.parties[command.party_id] = updated_party

        # Persist changes
        await self.session_repository.save(session)

        return {
            "session_id": str(session.session_id),
            "party_id": str(command.party_id),
            "old_authority": old_authority.value,
            "new_authority": command.new_authority_level.value,
            "can_make_decisions": updated_party.can_make_binding_decisions(),
            "update_reason": command.update_reason,
            "authority_constraints": command.authority_constraints,
        }

    # Proposal Management Command Handlers

    async def handle_submit_proposal(
        self, command: SubmitProposalCommand
    ) -> Dict[str, Any]:
        """Handle submission of proposal to negotiation."""
        # Retrieve session
        session = await self.session_repository.get_by_id(
            InteractionId(command.session_id)
        )

        if not session:
            raise ValueError(f"Session {command.session_id} not found")

        # Validate submitter is in session
        if command.initiated_by not in session.parties:
            raise ValueError(
                f"Submitting party {command.initiated_by} not in session"
            )

        # Submit proposal
        session.submit_proposal(command.proposal, command.initiated_by)

        # Persist changes
        await self.session_repository.save(session)

        return {
            "session_id": str(session.session_id),
            "proposal_id": str(command.proposal.proposal_id),
            "proposal_title": command.proposal.title,
            "proposal_type": command.proposal.proposal_type.value,
            "terms_count": len(command.proposal.terms),
            "submitted_by": str(command.initiated_by),
            "submission_notes": command.submission_notes,
            "current_phase": session.status.phase.value,
            "events": [
                event.__class__.__name__
                for event in session.get_uncommitted_events()
            ],
        }

    async def handle_withdraw_proposal(
        self, command: WithdrawProposalCommand
    ) -> Dict[str, Any]:
        """Handle withdrawal of proposal from negotiation."""
        # Retrieve session
        session = await self.session_repository.get_by_id(
            InteractionId(command.session_id)
        )

        if not session:
            raise ValueError(f"Session {command.session_id} not found")

        # Check if proposal exists and is active
        if command.proposal_id not in session.active_proposals:
            raise ValueError(
                f"Proposal {command.proposal_id} not found or not active"
            )

        proposal = session.active_proposals[command.proposal_id]
        proposal_title = proposal.title

        # Remove from active proposals (simplified withdrawal logic)
        del session.active_proposals[command.proposal_id]

        # Submit replacement if provided
        replacement_submitted = False
        if command.replacement_proposal:
            session.submit_proposal(
                command.replacement_proposal, command.initiated_by
            )
            replacement_submitted = True

        # Persist changes
        await self.session_repository.save(session)

        return {
            "session_id": str(session.session_id),
            "withdrawn_proposal_id": str(command.proposal_id),
            "withdrawn_proposal_title": proposal_title,
            "withdrawal_reason": command.withdrawal_reason,
            "replacement_submitted": replacement_submitted,
            "replacement_proposal_id": (
                str(command.replacement_proposal.proposal_id)
                if command.replacement_proposal
                else None
            ),
            "active_proposals_count": len(session.active_proposals),
        }

    async def handle_update_proposal(
        self, command: UpdateProposalCommand
    ) -> Dict[str, Any]:
        """Handle update of existing proposal."""
        # Retrieve session
        session = await self.session_repository.get_by_id(
            InteractionId(command.session_id)
        )

        if not session:
            raise ValueError(f"Session {command.session_id} not found")

        # Check if proposal exists and is active
        if command.proposal_id not in session.active_proposals:
            raise ValueError(
                f"Proposal {command.proposal_id} not found or not active"
            )

        existing_proposal = session.active_proposals[command.proposal_id]

        # Update proposal with new terms
        updated_proposal = existing_proposal
        for term in command.updated_terms:
            updated_proposal = updated_proposal.update_term(term.term_id, term)

        session.active_proposals[command.proposal_id] = updated_proposal

        # Persist changes
        await self.session_repository.save(session)

        return {
            "session_id": str(session.session_id),
            "proposal_id": str(command.proposal_id),
            "updated_terms_count": len(command.updated_terms),
            "total_terms_count": len(updated_proposal.terms),
            "update_reason": command.update_reason,
            "notify_parties": command.notify_parties,
        }

    async def handle_optimize_proposal(
        self, command: OptimizeProposalCommand
    ) -> Dict[str, Any]:
        """Handle optimization of proposal for better acceptance."""
        # Retrieve session
        session = await self.session_repository.get_by_id(
            InteractionId(command.session_id)
        )

        if not session:
            raise ValueError(f"Session {command.session_id} not found")

        # Check if proposal exists and is active
        if command.proposal_id not in session.active_proposals:
            raise ValueError(
                f"Proposal {command.proposal_id} not found or not active"
            )

        proposal = session.active_proposals[command.proposal_id]
        parties = list(session.parties.values())

        # Use negotiation service to optimize proposal
        optimization_result = self.negotiation_service.optimize_proposal_terms(
            proposal=proposal,
            parties=parties,
            negotiation_domain=session.negotiation_domain,
        )

        # Apply optimizations if they meet criteria
        optimizations_applied: List[str] = []
        if (
            optimization_result["expected_improvement"] > 10
        ):  # 10% improvement threshold
            for optimized_term in optimization_result["optimized_terms"]:
                if len(optimizations_applied) < command.max_modifications:
                    proposal = proposal.update_term(
                        optimized_term.term_id, optimized_term
                    )
                    optimizations_applied.append(optimized_term.term_id)

        session.active_proposals[command.proposal_id] = proposal

        # Persist changes
        await self.session_repository.save(session)

        return {
            "session_id": str(session.session_id),
            "proposal_id": str(command.proposal_id),
            "optimization_target": command.optimization_target,
            "optimizations_applied": optimizations_applied,
            "expected_improvement": float(
                optimization_result.get("expected_improvement", 0)
            ),
            "risk_level": optimization_result.get("risk_assessment", {}).get(
                "risk_level", "unknown"
            ),
            "implementation_difficulty": optimization_result.get(
                "implementation_difficulty", "unknown"
            ),
        }

    # Response Management Command Handlers

    async def handle_submit_proposal_response(
        self, command: SubmitProposalResponseCommand
    ) -> Dict[str, Any]:
        """Handle submission of proposal response."""
        # Retrieve session
        session = await self.session_repository.get_by_id(
            InteractionId(command.session_id)
        )

        if not session:
            raise ValueError(f"Session {command.session_id} not found")

        # Validate responding party is in session
        if command.response.responding_party_id not in session.parties:
            raise ValueError(
                f"Responding party {command.response.responding_party_id} not in session"
            )

        # Submit response
        session.submit_response(command.response)

        # Persist changes
        await self.session_repository.save(session)

        return {
            "session_id": str(session.session_id),
            "response_id": str(command.response.response_id),
            "proposal_id": str(command.response.proposal_id),
            "responding_party_id": str(command.response.responding_party_id),
            "overall_response": command.response.overall_response.value,
            "acceptance_percentage": command.response.get_acceptance_percentage(),
            "requires_follow_up": command.response.requires_negotiation(),
            "current_phase": session.status.phase.value,
            "events": [
                event.__class__.__name__
                for event in session.get_uncommitted_events()
            ],
        }

    async def handle_update_response(
        self, command: UpdateResponseCommand
    ) -> Dict[str, Any]:
        """Handle update of existing response."""
        # Retrieve session
        session = await self.session_repository.get_by_id(
            InteractionId(command.session_id)
        )

        if not session:
            raise ValueError(f"Session {command.session_id} not found")

        # Find and update response
        response_found = False
        updated_response = None

        for party_id, party_responses in session.responses.items():
            for i, response in enumerate(party_responses):
                if response.response_id == command.response_id:
                    response_found = True
                    updated_response = response

                    # Apply updates
                    if command.updated_term_responses:
                        for term_response in command.updated_term_responses:
                            updated_response = (
                                updated_response.with_updated_term_response(
                                    term_response.term_id, term_response
                                )
                            )

                    if command.updated_overall_response:
                        from ...domain.value_objects.proposal_response import (
                            ResponseType,
                        )

                        overall_response = ResponseType(
                            command.updated_overall_response
                        )
                        updated_response = (
                            updated_response.with_updated_overall_response(
                                overall_response
                            )
                        )

                    # Replace response in list
                    session.responses[party_id][i] = updated_response
                    break

            if response_found:
                break

        if not response_found:
            raise ValueError(f"Response {command.response_id} not found")

        # Persist changes
        await self.session_repository.save(session)

        return {
            "session_id": str(session.session_id),
            "response_id": str(command.response_id),
            "updated_fields": {
                "term_responses": len(command.updated_term_responses or []),
                "overall_response": command.updated_overall_response
                is not None,
                "conditions": len(command.updated_conditions or []),
            },
            "update_reason": command.update_reason,
            "new_acceptance_percentage": updated_response.get_acceptance_percentage()
            if updated_response is not None
            else 0.0,
        }

    # Analysis Command Handlers

    async def handle_analyze_proposal_viability(
        self, command: AnalyzeProposalViabilityCommand
    ) -> Dict[str, Any]:
        """Handle analysis of proposal viability."""
        # Retrieve session
        session = await self.session_repository.get_by_id(
            InteractionId(command.session_id)
        )

        if not session:
            raise ValueError(f"Session {command.session_id} not found")

        # Check if proposal exists
        if command.proposal_id not in session.active_proposals:
            raise ValueError(
                f"Proposal {command.proposal_id} not found or not active"
            )

        proposal = session.active_proposals[command.proposal_id]
        parties = list(session.parties.values())

        # Analyze proposal viability
        analysis = self.negotiation_service.analyze_proposal_viability(
            proposal=proposal,
            parties=parties,
            negotiation_domain=session.negotiation_domain,
        )

        # Convert Decimal values to float for JSON serialization
        analysis["overall_viability_score"] = float(
            analysis["overall_viability_score"]
        )
        analysis["acceptance_probability"] = float(
            analysis["acceptance_probability"]
        )

        # Convert party-specific analysis
        for party_id, party_analysis in analysis[
            "party_specific_analysis"
        ].items():
            party_analysis["acceptance_score"] = float(
                party_analysis["acceptance_score"]
            )

        return {
            "session_id": str(session.session_id),
            "proposal_id": str(command.proposal_id),
            "analysis_depth": command.analysis_depth,
            "analysis_result": analysis,
            "include_optimization_suggestions": command.include_optimization_suggestions,
            "focus_areas": command.focus_areas,
        }

    async def handle_assess_party_compatibility(
        self, command: AssessPartyCompatibilityCommand
    ) -> Dict[str, Any]:
        """Handle assessment of party compatibility."""
        # Retrieve session
        session = await self.session_repository.get_by_id(
            InteractionId(command.session_id)
        )

        if not session:
            raise ValueError(f"Session {command.session_id} not found")

        # Get parties to assess
        parties_to_assess = []
        if command.party_ids:
            for party_id in command.party_ids:
                if party_id not in session.parties:
                    raise ValueError(f"Party {party_id} not found in session")
                parties_to_assess.append(session.parties[party_id])
        else:
            parties_to_assess = list(session.parties.values())

        # Assess compatibility between all party pairs
        compatibility_matrix = {}
        for i, party1 in enumerate(parties_to_assess):
            for j, party2 in enumerate(parties_to_assess[i + 1 :], i + 1):
                compatibility_score = (
                    self.negotiation_service.assess_party_compatibility(
                        party1, party2, session.negotiation_domain
                    )
                )

                pair_key = f"{party1.party_id}_{party2.party_id}"
                compatibility_matrix[pair_key] = {
                    "party1_id": str(party1.party_id),
                    "party1_name": party1.party_name,
                    "party2_id": str(party2.party_id),
                    "party2_name": party2.party_name,
                    "compatibility_score": float(compatibility_score),
                }

        # Calculate overall compatibility
        if compatibility_matrix:
            scores: List[float] = [
                cast(float, comp["compatibility_score"])
                for comp in compatibility_matrix.values()
            ]
            overall_compatibility = sum(scores) / len(scores)
        else:
            overall_compatibility = 100.0  # Single party or no comparisons

        return {
            "session_id": str(session.session_id),
            "assessed_parties": [str(p.party_id) for p in parties_to_assess],
            "compatibility_matrix": compatibility_matrix,
            "overall_compatibility": overall_compatibility,
            "compatibility_factors": command.compatibility_factors,
            "include_recommendations": command.include_recommendations,
        }

    async def handle_recommend_negotiation_strategy(
        self, command: RecommendNegotiationStrategyCommand
    ) -> Dict[str, Any]:
        """Handle recommendation of negotiation strategy."""
        # Retrieve session
        session = await self.session_repository.get_by_id(
            InteractionId(command.session_id)
        )

        if not session:
            raise ValueError(f"Session {command.session_id} not found")

        parties = list(session.parties.values())

        # Get strategy recommendation
        strategy = self.negotiation_service.recommend_negotiation_strategy(
            parties=parties,
            negotiation_domain=session.negotiation_domain,
            target_outcome=command.target_outcome,
        )

        return {
            "session_id": str(session.session_id),
            "target_outcome": command.target_outcome,
            "strategy_focus": command.strategy_focus,
            "strategy_recommendation": strategy,
            "include_tactics": command.include_tactics,
            "timeline_constraints": command.timeline_constraints,
        }

    async def handle_detect_negotiation_conflicts(
        self, command: DetectNegotiationConflictsCommand
    ) -> Dict[str, Any]:
        """Handle detection of negotiation conflicts."""
        # Retrieve session
        session = await self.session_repository.get_by_id(
            InteractionId(command.session_id)
        )

        if not session:
            raise ValueError(f"Session {command.session_id} not found")

        parties = list(session.parties.values())
        all_responses = []
        for party_responses in session.responses.values():
            all_responses.extend(party_responses)

        # Detect conflicts
        conflicts = self.negotiation_service.detect_negotiation_conflicts(
            parties=parties, responses=all_responses
        )

        # Filter by severity threshold
        severity_order = ["low", "medium", "high", "critical"]
        threshold_index = severity_order.index(command.severity_threshold)

        filtered_conflicts = [
            conflict
            for conflict in conflicts
            if severity_order.index(conflict.get("severity", "low"))
            >= threshold_index
        ]

        # Convert UUID objects to strings for JSON serialization
        for conflict in filtered_conflicts:
            if "parties" in conflict:
                conflict["parties"] = [
                    str(party_id) for party_id in conflict["parties"]
                ]

        return {
            "session_id": str(session.session_id),
            "conflict_types": command.conflict_types,
            "severity_threshold": command.severity_threshold,
            "conflicts_detected": filtered_conflicts,
            "total_conflicts": len(filtered_conflicts),
            "include_resolution_suggestions": command.include_resolution_suggestions,
        }

    async def handle_calculate_negotiation_momentum(
        self, command: CalculateNegotiationMomentumCommand
    ) -> Dict[str, Any]:
        """Handle calculation of negotiation momentum."""
        # Retrieve session
        session = await self.session_repository.get_by_id(
            InteractionId(command.session_id)
        )

        if not session:
            raise ValueError(f"Session {command.session_id} not found")

        # Get recent responses within analysis window
        from datetime import datetime, timedelta, timezone

        cutoff_time = datetime.now(timezone.utc) - timedelta(
            hours=command.analysis_window_hours
        )
        recent_responses = []

        for party_responses in session.responses.values():
            for response in party_responses:
                if response.response_timestamp >= cutoff_time:
                    recent_responses.append(response)

        # Calculate momentum
        momentum = self.negotiation_service.calculate_negotiation_momentum(
            responses=recent_responses, phase=session.status.phase
        )

        # Convert Decimal values to float for JSON serialization
        momentum["momentum_score"] = float(momentum["momentum_score"])

        return {
            "session_id": str(session.session_id),
            "analysis_window_hours": command.analysis_window_hours,
            "responses_analyzed": len(recent_responses),
            "current_phase": session.status.phase.value,
            "momentum_analysis": momentum,
            "include_predictions": command.include_predictions,
            "momentum_factors": command.momentum_factors,
        }

    # Bulk Operations Command Handlers

    async def handle_batch_update_parties(
        self, command: BatchUpdatePartiesCommand
    ) -> Dict[str, Any]:
        """Handle batch update of multiple parties."""
        # Retrieve session
        session = await self.session_repository.get_by_id(
            InteractionId(command.session_id)
        )

        if not session:
            raise ValueError(f"Session {command.session_id} not found")

        successful_updates = []
        failed_updates = []

        for update_data in command.party_updates:
            try:
                party_id = UUID(update_data["party_id"])

                if party_id not in session.parties:
                    failed_updates.append(
                        {
                            "party_id": str(party_id),
                            "error": "Party not found in session",
                        }
                    )
                    continue

                # Apply updates based on update_data content
                party = session.parties[party_id]

                # Example update logic - extend as needed
                if "authority_level" in update_data:
                    from ...domain.value_objects.negotiation_party import (
                        AuthorityLevel,
                    )

                    new_authority = AuthorityLevel(
                        update_data["authority_level"]
                    )
                    party = party.with_updated_authority(new_authority)
                    session.parties[party_id] = party

                successful_updates.append(
                    {
                        "party_id": str(party_id),
                        "updates_applied": list(update_data.keys()),
                    }
                )

            except Exception as e:
                failed_updates.append(
                    {
                        "party_id": update_data.get("party_id", "unknown"),
                        "error": str(e),
                    }
                )

                if command.stop_on_first_error:
                    break

        # Persist changes
        await self.session_repository.save(session)

        return {
            "session_id": str(session.session_id),
            "total_updates_requested": len(command.party_updates),
            "successful_updates": successful_updates,
            "failed_updates": failed_updates,
            "stop_on_first_error": command.stop_on_first_error,
        }

    async def handle_batch_submit_responses(
        self, command: BatchSubmitResponsesCommand
    ) -> Dict[str, Any]:
        """Handle batch submission of multiple responses."""
        # Retrieve session
        session = await self.session_repository.get_by_id(
            InteractionId(command.session_id)
        )

        if not session:
            raise ValueError(f"Session {command.session_id} not found")

        successful_submissions = []
        failed_submissions = []

        for response in command.responses:
            try:
                # Validate response
                if command.validate_each_response:
                    if response.responding_party_id not in session.parties:
                        raise ValueError(
                            f"Responding party {response.responding_party_id} not in session"
                        )

                    if response.proposal_id not in session.active_proposals:
                        raise ValueError(
                            f"Proposal {response.proposal_id} not found or not active"
                        )

                # Submit response
                session.submit_response(response)

                successful_submissions.append(
                    {
                        "response_id": str(response.response_id),
                        "proposal_id": str(response.proposal_id),
                        "responding_party_id": str(
                            response.responding_party_id
                        ),
                    }
                )

            except Exception as e:
                failed_submissions.append(
                    {"response_id": str(response.response_id), "error": str(e)}
                )

        # Persist changes
        await self.session_repository.save(session)

        return {
            "session_id": str(session.session_id),
            "total_responses_submitted": len(command.responses),
            "successful_submissions": successful_submissions,
            "failed_submissions": failed_submissions,
            "auto_advance_on_completion": command.auto_advance_on_batch_completion,
            "current_phase": session.status.phase.value,
            "events": [
                event.__class__.__name__
                for event in session.get_uncommitted_events()
            ],
        }
