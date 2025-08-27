#!/usr/bin/env python3
"""
Interaction Query Handlers

This module implements query handlers for the Interaction bounded context,
providing the read-side implementation of CQRS that retrieves and formats
data for various query scenarios.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
from uuid import UUID

from ...domain.repositories.negotiation_session_repository import NegotiationSessionRepository
from ...domain.services.negotiation_service import NegotiationService
from ...domain.value_objects.interaction_id import InteractionId

from .interaction_queries import (
    # Session Queries
    GetNegotiationSessionQuery,
    ListNegotiationSessionsQuery,
    GetSessionSummaryQuery,
    GetSessionTimelineQuery,
    
    # Party Queries
    GetSessionPartiesQuery,
    GetPartyDetailsQuery,
    GetPartyCompatibilityQuery,
    
    # Proposal Queries
    GetSessionProposalsQuery,
    GetProposalDetailsQuery,
    GetProposalResponsesQuery,
    
    # Analysis Queries
    GetNegotiationAnalyticsQuery,
    GetMomentumAnalysisQuery,
    GetConflictAnalysisQuery,
    GetStrategyRecommendationsQuery,
    
    # Performance Queries
    GetSessionPerformanceQuery,
    GenerateSessionReportQuery,
    
    # Search Queries
    SearchNegotiationSessionsQuery,
    SearchProposalsQuery,
    
    # Historical Queries
    GetNegotiationTrendsQuery,
    GetHistoricalAnalysisQuery,
    
    # Monitoring Queries
    GetActiveSessionsQuery,
    GetSessionHealthQuery,
    GetNotificationsQuery
)


class InteractionQueryHandler:
    """
    Main query handler for Interaction bounded context read operations.
    
    Implements the read-side of CQRS by providing optimized data retrieval
    and formatting for various query scenarios.
    """
    
    def __init__(self, 
                 session_repository: NegotiationSessionRepository,
                 negotiation_service: Optional[NegotiationService] = None):
        """Initialize query handler with required dependencies."""
        self.session_repository = session_repository
        self.negotiation_service = negotiation_service or NegotiationService()
    
    # Session Query Handlers
    
    async def handle_get_negotiation_session(self, 
                                           query: GetNegotiationSessionQuery) -> Dict[str, Any]:
        """Handle retrieval of a specific negotiation session."""
        session = await self.session_repository.get_by_id(InteractionId(query.session_id))
        
        if not session:
            return {
                'found': False,
                'session_id': str(query.session_id),
                'error': 'Session not found'
            }
        
        result = {
            'found': True,
            'session_id': str(session.session_id),
            'session_name': session.session_name,
            'session_type': session.session_type,
            'status': {
                'phase': session.status.phase.value,
                'outcome': session.status.outcome.value,
                'is_active': session.status.is_active,
                'started_at': session.status.started_at,
                'last_activity_at': session.status.last_activity_at,
                'expected_completion_at': session.status.expected_completion_at,
                'actual_completion_at': session.status.actual_completion_at
            },
            'created_at': session.created_at,
            'created_by': str(session.created_by),
            'configuration': {
                'max_parties': session.max_parties,
                'session_timeout_hours': session.session_timeout_hours,
                'auto_advance_phases': session.auto_advance_phases,
                'require_unanimous_agreement': session.require_unanimous_agreement,
                'allow_partial_agreements': session.allow_partial_agreements,
                'priority_level': session.priority_level,
                'confidentiality_level': session.confidentiality_level
            },
            'negotiation_domain': session.negotiation_domain,
            'session_context': session.session_context
        }
        
        if query.include_parties:
            result['parties'] = []
            for party_id, party in session.parties.items():
                party_data = {
                    'party_id': str(party_id),
                    'entity_id': str(party.entity_id),
                    'party_name': party.party_name,
                    'role': party.role.value,
                    'authority_level': party.authority_level.value,
                    'can_make_decisions': party.can_make_binding_decisions(),
                    'total_capabilities': party.total_capabilities_count,
                    'average_proficiency': float(party.average_proficiency)
                }
                result['parties'].append(party_data)
        
        if query.include_proposals:
            result['proposals'] = {
                'active': [],
                'history_count': len(session.proposal_history)
            }
            
            for proposal_id, proposal in session.active_proposals.items():
                proposal_data = {
                    'proposal_id': str(proposal_id),
                    'title': proposal.title,
                    'proposal_type': proposal.proposal_type.value,
                    'summary': proposal.summary,
                    'terms_count': proposal.total_terms_count,
                    'negotiable_terms_count': proposal.negotiable_terms_count,
                    'critical_terms_count': proposal.critical_terms_count,
                    'created_at': proposal.created_at,
                    'validity_period': proposal.validity_period,
                    'is_expired': proposal.is_expired
                }
                result['proposals']['active'].append(proposal_data)
        
        if query.include_responses:
            result['responses'] = {
                'total_responses': session.total_responses,
                'by_party': {}
            }
            
            for party_id, responses in session.responses.items():
                result['responses']['by_party'][str(party_id)] = []
                for response in responses:
                    response_data = {
                        'response_id': str(response.response_id),
                        'proposal_id': str(response.proposal_id),
                        'overall_response': response.overall_response.value,
                        'acceptance_percentage': response.get_acceptance_percentage(),
                        'response_timestamp': response.response_timestamp,
                        'requires_follow_up': response.requires_negotiation()
                    }
                    result['responses']['by_party'][str(party_id)].append(response_data)
        
        if query.include_events:
            result['uncommitted_events'] = [
                {
                    'event_type': event.__class__.__name__,
                    'event_data': str(event)[:200] + '...' if len(str(event)) > 200 else str(event)
                }
                for event in session.get_uncommitted_events()
            ]
        
        return result
    
    async def handle_list_negotiation_sessions(self, 
                                             query: ListNegotiationSessionsQuery) -> Dict[str, Any]:
        """Handle listing of negotiation sessions with filters."""
        # Build filter criteria
        filters = {}
        
        if query.created_by:
            filters['created_by'] = query.created_by
        
        if query.session_type:
            filters['session_type'] = query.session_type
        
        if query.negotiation_domain:
            filters['negotiation_domain'] = query.negotiation_domain
        
        if query.priority_level:
            filters['priority_level'] = query.priority_level
        
        if query.created_after:
            filters['created_after'] = query.created_after
        
        if query.created_before:
            filters['created_before'] = query.created_before
        
        # Get sessions from repository
        sessions = await self.session_repository.find_by_filters(
            filters=filters,
            limit=query.limit,
            offset=query.offset,
            order_by=query.order_by,
            order_direction=query.order_direction
        )
        
        # Format results
        session_list = []
        for session in sessions:
            # Apply status filter if specified
            if query.status_filter:
                if query.status_filter == 'active' and not session.status.is_active:
                    continue
                elif query.status_filter == 'completed' and session.status.outcome.value == 'pending':
                    continue
                elif query.status_filter == 'terminated' and session.status.phase.value != 'terminated':
                    continue
            
            # Apply participant filter if specified
            if query.participant_id and query.participant_id not in session.parties:
                continue
            
            session_data = {
                'session_id': str(session.session_id),
                'session_name': session.session_name,
                'session_type': session.session_type,
                'created_at': session.created_at,
                'created_by': str(session.created_by),
                'status': {
                    'phase': session.status.phase.value,
                    'outcome': session.status.outcome.value,
                    'is_active': session.status.is_active
                },
                'party_count': len(session.parties),
                'proposal_count': len(session.active_proposals),
                'priority_level': session.priority_level,
                'negotiation_domain': session.negotiation_domain
            }
            session_list.append(session_data)
        
        return {
            'sessions': session_list,
            'total_count': len(session_list),
            'limit': query.limit,
            'offset': query.offset,
            'filters_applied': filters,
            'status_filter': query.status_filter
        }
    
    async def handle_get_session_summary(self, 
                                       query: GetSessionSummaryQuery) -> Dict[str, Any]:
        """Handle generation of comprehensive session summary."""
        session = await self.session_repository.get_by_id(InteractionId(query.session_id))
        
        if not session:
            return {
                'found': False,
                'session_id': str(query.session_id),
                'error': 'Session not found'
            }
        
        summary = session.get_session_summary()
        
        # Enhance with additional details based on depth
        if query.summary_depth in ['standard', 'detailed']:
            # Add negotiation insights
            if query.include_analytics and session.parties:
                parties = list(session.parties.values())
                
                # Calculate compatibility matrix
                compatibility_scores = {}
                party_list = list(parties)
                for i, party1 in enumerate(party_list):
                    for j, party2 in enumerate(party_list[i+1:], i+1):
                        score = self.negotiation_service.assess_party_compatibility(
                            party1, party2, session.negotiation_domain
                        )
                        compatibility_scores[f"{party1.party_name}-{party2.party_name}"] = float(score)
                
                summary['analytics'] = {
                    'party_compatibility': compatibility_scores,
                    'average_compatibility': sum(compatibility_scores.values()) / len(compatibility_scores) if compatibility_scores else 0,
                }
                
                # Add momentum analysis if there are responses
                if session.total_responses > 0:
                    all_responses = []
                    for party_responses in session.responses.values():
                        all_responses.extend(party_responses)
                    
                    momentum = self.negotiation_service.calculate_negotiation_momentum(
                        responses=all_responses,
                        phase=session.status.phase
                    )
                    
                    summary['analytics']['momentum'] = {
                        'momentum_score': float(momentum['momentum_score']),
                        'direction': momentum['direction'],
                        'velocity': momentum['velocity'],
                        'trajectory_prediction': momentum['trajectory_prediction']
                    }
        
        if query.summary_depth == 'detailed':
            # Add detailed party information
            if query.include_party_details:
                summary['detailed_parties'] = []
                for party in session.parties.values():
                    party_detail = {
                        'party_id': str(party.party_id),
                        'party_name': party.party_name,
                        'role': party.role.value,
                        'authority_level': party.authority_level.value,
                        'capabilities': [
                            {
                                'name': cap.capability_name,
                                'proficiency': float(cap.get_effective_proficiency()),
                                'domains': list(cap.applicable_domains)
                            }
                            for cap in party.capabilities
                        ],
                        'preferences': {
                            'negotiation_style': party.preferences.negotiation_style.value,
                            'communication_preference': party.preferences.communication_preference.value,
                            'risk_tolerance': float(party.preferences.risk_tolerance),
                            'time_pressure_sensitivity': float(party.preferences.time_pressure_sensitivity)
                        },
                        'negotiation_power': float(party.get_negotiation_power(session.negotiation_domain)) if session.negotiation_domain else 0
                    }
                    summary['detailed_parties'].append(party_detail)
            
            # Add timeline if requested
            if query.include_timeline:
                timeline_events = []
                
                # Session creation
                timeline_events.append({
                    'timestamp': session.created_at,
                    'event_type': 'session_created',
                    'description': f"Session '{session.session_name}' created"
                })
                
                # Party additions (simplified - would need event sourcing for full timeline)
                for party in session.parties.values():
                    timeline_events.append({
                        'timestamp': session.created_at,  # Approximation
                        'event_type': 'party_joined',
                        'description': f"Party '{party.party_name}' joined as {party.role.value}"
                    })
                
                # Proposals (simplified)
                for proposal in session.proposal_history:
                    timeline_events.append({
                        'timestamp': proposal.created_at,
                        'event_type': 'proposal_submitted',
                        'description': f"Proposal '{proposal.title}' submitted"
                    })
                
                # Sort by timestamp
                timeline_events.sort(key=lambda x: x['timestamp'])
                summary['timeline'] = timeline_events
        
        return {
            'found': True,
            'session_id': str(query.session_id),
            'summary_depth': query.summary_depth,
            'summary': summary
        }
    
    async def handle_get_session_timeline(self, 
                                        query: GetSessionTimelineQuery) -> Dict[str, Any]:
        """Handle retrieval of session timeline."""
        session = await self.session_repository.get_by_id(InteractionId(query.session_id))
        
        if not session:
            return {
                'found': False,
                'session_id': str(query.session_id),
                'error': 'Session not found'
            }
        
        # Build timeline from available data (would be more comprehensive with event sourcing)
        timeline_events = []
        
        # Session events
        timeline_events.append({
            'timestamp': session.created_at,
            'event_type': 'session_created',
            'phase': 'initiation',
            'description': f"Negotiation session '{session.session_name}' created",
            'metadata': {
                'session_type': session.session_type,
                'created_by': str(session.created_by),
                'max_parties': session.max_parties
            }
        })
        
        # Party events (approximated)
        for party in session.parties.values():
            timeline_events.append({
                'timestamp': session.created_at,  # Approximation - would have actual join time with event sourcing
                'event_type': 'party_joined',
                'phase': 'preparation',
                'description': f"Party '{party.party_name}' joined as {party.role.value}",
                'metadata': {
                    'party_id': str(party.party_id),
                    'authority_level': party.authority_level.value
                }
            })
        
        # Proposal events
        for proposal in session.proposal_history:
            timeline_events.append({
                'timestamp': proposal.created_at,
                'event_type': 'proposal_submitted',
                'phase': 'bargaining',
                'description': f"Proposal '{proposal.title}' submitted",
                'metadata': {
                    'proposal_id': str(proposal.proposal_id),
                    'proposal_type': proposal.proposal_type.value,
                    'terms_count': len(proposal.terms)
                }
            })
        
        # Response events (approximated)
        for party_id, responses in session.responses.items():
            party_name = session.parties.get(party_id, type('Party', (), {'party_name': 'Unknown'})).party_name
            for response in responses:
                timeline_events.append({
                    'timestamp': response.response_timestamp,
                    'event_type': 'response_received',
                    'phase': 'bargaining',
                    'description': f"Response from '{party_name}': {response.overall_response.value}",
                    'metadata': {
                        'response_id': str(response.response_id),
                        'proposal_id': str(response.proposal_id),
                        'acceptance_percentage': response.get_acceptance_percentage()
                    }
                })
        
        # Filter events by date range
        if query.start_date:
            timeline_events = [e for e in timeline_events if e['timestamp'] >= query.start_date]
        
        if query.end_date:
            timeline_events = [e for e in timeline_events if e['timestamp'] <= query.end_date]
        
        # Filter by event types
        if query.event_types:
            timeline_events = [e for e in timeline_events if e['event_type'] in query.event_types]
        
        # Sort by timestamp
        timeline_events.sort(key=lambda x: x['timestamp'])
        
        # Group by phase if requested
        if query.group_by_phase:
            grouped_events = {}
            for event in timeline_events:
                phase = event['phase']
                if phase not in grouped_events:
                    grouped_events[phase] = []
                grouped_events[phase].append(event)
            
            return {
                'found': True,
                'session_id': str(query.session_id),
                'timeline_grouped': grouped_events,
                'total_events': len(timeline_events),
                'phases': list(grouped_events.keys())
            }
        
        return {
            'found': True,
            'session_id': str(query.session_id),
            'timeline': timeline_events,
            'total_events': len(timeline_events)
        }
    
    # Party Query Handlers
    
    async def handle_get_session_parties(self, 
                                       query: GetSessionPartiesQuery) -> Dict[str, Any]:
        """Handle retrieval of session parties."""
        session = await self.session_repository.get_by_id(InteractionId(query.session_id))
        
        if not session:
            return {
                'found': False,
                'session_id': str(query.session_id),
                'error': 'Session not found'
            }
        
        parties_data = []
        
        for party in session.parties.values():
            # Apply role filter
            if query.role_filter and party.role.value != query.role_filter:
                continue
            
            # Apply authority filter
            if query.authority_filter and party.authority_level.value != query.authority_filter:
                continue
            
            party_data = {
                'party_id': str(party.party_id),
                'entity_id': str(party.entity_id),
                'party_name': party.party_name,
                'role': party.role.value,
                'authority_level': party.authority_level.value,
                'can_make_decisions': party.can_make_binding_decisions(),
                'is_decision_maker': party.is_decision_maker
            }
            
            if query.include_capabilities:
                party_data['capabilities'] = [
                    {
                        'name': cap.capability_name,
                        'proficiency_level': float(cap.proficiency_level),
                        'confidence_modifier': float(cap.confidence_modifier),
                        'effective_proficiency': float(cap.get_effective_proficiency()),
                        'applicable_domains': list(cap.applicable_domains)
                    }
                    for cap in party.capabilities
                ]
                party_data['total_capabilities'] = len(party.capabilities)
                party_data['average_proficiency'] = float(party.average_proficiency)
            
            if query.include_preferences:
                party_data['preferences'] = {
                    'negotiation_style': party.preferences.negotiation_style.value,
                    'communication_preference': party.preferences.communication_preference.value,
                    'risk_tolerance': float(party.preferences.risk_tolerance),
                    'time_pressure_sensitivity': float(party.preferences.time_pressure_sensitivity),
                    'preferred_session_duration': party.preferences.preferred_session_duration,
                    'maximum_session_duration': party.preferences.maximum_session_duration
                }
            
            if query.include_activity_summary:
                # Calculate activity summary
                party_responses = session.responses.get(party.party_id, [])
                party_data['activity_summary'] = {
                    'total_responses': len(party_responses),
                    'avg_acceptance_rate': sum(r.get_acceptance_percentage() for r in party_responses) / len(party_responses) if party_responses else 0,
                    'last_activity': max(r.response_timestamp for r in party_responses) if party_responses else None
                }
            
            parties_data.append(party_data)
        
        return {
            'found': True,
            'session_id': str(query.session_id),
            'parties': parties_data,
            'total_parties': len(parties_data),
            'role_filter': query.role_filter,
            'authority_filter': query.authority_filter
        }
    
    async def handle_get_party_compatibility(self, 
                                           query: GetPartyCompatibilityQuery) -> Dict[str, Any]:
        """Handle party compatibility analysis."""
        session = await self.session_repository.get_by_id(InteractionId(query.session_id))
        
        if not session:
            return {
                'found': False,
                'session_id': str(query.session_id),
                'error': 'Session not found'
            }
        
        # Get parties to analyze
        if query.party_ids:
            parties = [session.parties[party_id] for party_id in query.party_ids if party_id in session.parties]
        else:
            parties = list(session.parties.values())
        
        if len(parties) < 2:
            return {
                'found': True,
                'session_id': str(query.session_id),
                'error': 'At least 2 parties required for compatibility analysis'
            }
        
        # Calculate compatibility matrix
        compatibility_matrix = []
        compatibility_scores = []
        
        for i, party1 in enumerate(parties):
            for j, party2 in enumerate(parties[i+1:], i+1):
                compatibility_score = self.negotiation_service.assess_party_compatibility(
                    party1, party2, session.negotiation_domain
                )
                
                compatibility_data = {
                    'party1_id': str(party1.party_id),
                    'party1_name': party1.party_name,
                    'party2_id': str(party2.party_id),
                    'party2_name': party2.party_name,
                    'compatibility_score': float(compatibility_score)
                }
                
                compatibility_matrix.append(compatibility_data)
                compatibility_scores.append(float(compatibility_score))
        
        # Calculate overall compatibility
        overall_compatibility = sum(compatibility_scores) / len(compatibility_scores) if compatibility_scores else 0
        
        result = {
            'found': True,
            'session_id': str(query.session_id),
            'analyzed_parties': [str(p.party_id) for p in parties],
            'overall_compatibility': overall_compatibility,
            'compatibility_pairs': len(compatibility_matrix)
        }
        
        if query.matrix_format:
            result['compatibility_matrix'] = compatibility_matrix
        else:
            # Alternative format - by party
            result['compatibility_by_party'] = {}
            for party in parties:
                party_compatibilities = [
                    cm for cm in compatibility_matrix 
                    if cm['party1_id'] == str(party.party_id) or cm['party2_id'] == str(party.party_id)
                ]
                if party_compatibilities:
                    avg_compatibility = sum(cm['compatibility_score'] for cm in party_compatibilities) / len(party_compatibilities)
                    result['compatibility_by_party'][str(party.party_id)] = {
                        'party_name': party.party_name,
                        'average_compatibility': avg_compatibility,
                        'individual_scores': party_compatibilities
                    }
        
        if query.include_recommendations:
            recommendations = []
            
            # Low compatibility warnings
            low_compatibility_pairs = [cm for cm in compatibility_matrix if cm['compatibility_score'] < 30]
            for pair in low_compatibility_pairs:
                recommendations.append(
                    f"Low compatibility detected between {pair['party1_name']} and {pair['party2_name']} "
                    f"(score: {pair['compatibility_score']:.1f}) - consider mediation strategies"
                )
            
            # High compatibility opportunities
            high_compatibility_pairs = [cm for cm in compatibility_matrix if cm['compatibility_score'] > 80]
            for pair in high_compatibility_pairs:
                recommendations.append(
                    f"High compatibility between {pair['party1_name']} and {pair['party2_name']} "
                    f"(score: {pair['compatibility_score']:.1f}) - leverage this partnership"
                )
            
            if overall_compatibility < 50:
                recommendations.append("Overall compatibility is low - consider restructuring negotiation approach")
            
            result['recommendations'] = recommendations
        
        return result
    
    # Proposal Query Handlers
    
    async def handle_get_session_proposals(self, 
                                         query: GetSessionProposalsQuery) -> Dict[str, Any]:
        """Handle retrieval of session proposals."""
        session = await self.session_repository.get_by_id(InteractionId(query.session_id))
        
        if not session:
            return {
                'found': False,
                'session_id': str(query.session_id),
                'error': 'Session not found'
            }
        
        proposals_data = []
        
        # Determine which proposals to include
        proposals_to_include = []
        
        if query.proposal_status in ['active', 'all']:
            proposals_to_include.extend(session.active_proposals.values())
        
        if query.proposal_status in ['all']:
            # Would need additional tracking for withdrawn/expired proposals
            # For now, include proposal history
            for proposal in session.proposal_history:
                if proposal not in session.active_proposals.values():
                    proposals_to_include.append(proposal)
        
        for proposal in proposals_to_include:
            # Apply filters
            if query.proposal_type and proposal.proposal_type.value != query.proposal_type:
                continue
            
            # Note: submitted_by would need to be tracked in proposal metadata
            
            proposal_data = {
                'proposal_id': str(proposal.proposal_id),
                'title': proposal.title,
                'proposal_type': proposal.proposal_type.value,
                'summary': proposal.summary,
                'created_at': proposal.created_at,
                'validity_period': proposal.validity_period,
                'is_expired': proposal.is_expired,
                'total_terms': proposal.total_terms_count,
                'negotiable_terms': proposal.negotiable_terms_count,
                'critical_terms': proposal.critical_terms_count,
                'is_active': proposal in session.active_proposals.values()
            }
            
            if query.include_terms:
                proposal_data['terms'] = [
                    {
                        'term_id': term.term_id,
                        'term_type': term.term_type.value,
                        'description': term.description,
                        'priority': term.priority.value,
                        'is_negotiable': term.is_negotiable,
                        'has_dependencies': bool(term.dependencies)
                    }
                    for term in proposal.terms
                ]
            
            if query.include_responses:
                # Get responses for this proposal
                proposal_responses = []
                for party_responses in session.responses.values():
                    for response in party_responses:
                        if response.proposal_id == proposal.proposal_id:
                            proposal_responses.append({
                                'response_id': str(response.response_id),
                                'responding_party_id': str(response.responding_party_id),
                                'overall_response': response.overall_response.value,
                                'acceptance_percentage': response.get_acceptance_percentage(),
                                'response_timestamp': response.response_timestamp
                            })
                
                proposal_data['responses'] = proposal_responses
                proposal_data['response_count'] = len(proposal_responses)
            
            if query.include_viability_analysis:
                # Use negotiation service to analyze viability
                parties = list(session.parties.values())
                analysis = self.negotiation_service.analyze_proposal_viability(
                    proposal=proposal,
                    parties=parties,
                    negotiation_domain=session.negotiation_domain
                )
                
                proposal_data['viability_analysis'] = {
                    'overall_viability_score': float(analysis['overall_viability_score']),
                    'acceptance_probability': float(analysis['acceptance_probability']),
                    'risk_factors_count': len(analysis['risk_factors']),
                    'success_factors_count': len(analysis['success_factors'])
                }
            
            proposals_data.append(proposal_data)
        
        return {
            'found': True,
            'session_id': str(query.session_id),
            'proposals': proposals_data,
            'total_proposals': len(proposals_data),
            'proposal_status_filter': query.proposal_status,
            'active_proposals_count': len(session.active_proposals),
            'total_history_count': len(session.proposal_history)
        }
    
    async def handle_get_proposal_details(self, 
                                        query: GetProposalDetailsQuery) -> Dict[str, Any]:
        """Handle retrieval of detailed proposal information."""
        session = await self.session_repository.get_by_id(InteractionId(query.session_id))
        
        if not session:
            return {
                'found': False,
                'session_id': str(query.session_id),
                'error': 'Session not found'
            }
        
        # Find the proposal
        proposal = session.active_proposals.get(query.proposal_id)
        if not proposal:
            # Check proposal history
            proposal = next(
                (p for p in session.proposal_history if p.proposal_id == query.proposal_id),
                None
            )
        
        if not proposal:
            return {
                'found': False,
                'session_id': str(query.session_id),
                'proposal_id': str(query.proposal_id),
                'error': 'Proposal not found'
            }
        
        # Basic proposal details
        proposal_data = {
            'proposal_id': str(proposal.proposal_id),
            'title': proposal.title,
            'proposal_type': proposal.proposal_type.value,
            'summary': proposal.summary,
            'created_at': proposal.created_at,
            'validity_period': proposal.validity_period,
            'is_expired': proposal.is_expired,
            'is_active': proposal in session.active_proposals.values(),
            'metadata': proposal.metadata,
            'terms': [
                {
                    'term_id': term.term_id,
                    'term_type': term.term_type.value,
                    'description': term.description,
                    'priority': term.priority.value,
                    'is_negotiable': term.is_negotiable,
                    'value': term.value,
                    'constraints': term.constraints,
                    'dependencies': term.dependencies
                }
                for term in proposal.terms
            ],
            'term_counts': {
                'total': proposal.total_terms_count,
                'negotiable': proposal.negotiable_terms_count,
                'critical': proposal.critical_terms_count
            }
        }
        
        if query.include_viability_analysis:
            parties = list(session.parties.values())
            analysis = self.negotiation_service.analyze_proposal_viability(
                proposal=proposal,
                parties=parties,
                negotiation_domain=session.negotiation_domain
            )
            
            # Convert Decimal values for JSON serialization
            analysis['overall_viability_score'] = float(analysis['overall_viability_score'])
            analysis['acceptance_probability'] = float(analysis['acceptance_probability'])
            
            for party_analysis in analysis['party_specific_analysis'].values():
                party_analysis['acceptance_score'] = float(party_analysis['acceptance_score'])
            
            proposal_data['viability_analysis'] = analysis
        
        if query.include_response_summary:
            # Collect all responses to this proposal
            responses = []
            for party_responses in session.responses.values():
                for response in party_responses:
                    if response.proposal_id == query.proposal_id:
                        responses.append(response)
            
            if responses:
                total_acceptance = sum(r.get_acceptance_percentage() for r in responses)
                avg_acceptance = total_acceptance / len(responses)
                
                response_types = {}
                for response in responses:
                    resp_type = response.overall_response.value
                    response_types[resp_type] = response_types.get(resp_type, 0) + 1
                
                proposal_data['response_summary'] = {
                    'total_responses': len(responses),
                    'average_acceptance_percentage': avg_acceptance,
                    'response_types': response_types,
                    'complete_acceptances': len([r for r in responses if r.is_complete_acceptance()]),
                    'complete_rejections': len([r for r in responses if r.is_complete_rejection()]),
                    'requires_follow_up': len([r for r in responses if r.requires_negotiation()])
                }
            else:
                proposal_data['response_summary'] = {
                    'total_responses': 0,
                    'average_acceptance_percentage': 0,
                    'response_types': {},
                    'complete_acceptances': 0,
                    'complete_rejections': 0,
                    'requires_follow_up': 0
                }
        
        if query.include_optimization_suggestions:
            parties = list(session.parties.values())
            optimization = self.negotiation_service.optimize_proposal_terms(
                proposal=proposal,
                parties=parties,
                negotiation_domain=session.negotiation_domain
            )
            
            proposal_data['optimization_suggestions'] = {
                'optimized_terms_count': len(optimization['optimized_terms']),
                'expected_improvement': float(optimization['expected_improvement']),
                'risk_level': optimization['risk_assessment'].get('risk_level', 'unknown'),
                'implementation_difficulty': optimization['implementation_difficulty'],
                'optimization_rationale': optimization['optimization_rationale']
            }
        
        return {
            'found': True,
            'session_id': str(query.session_id),
            'analysis_depth': query.analysis_depth,
            'proposal': proposal_data
        }
    
    # Additional query handlers would continue here...
    # For brevity, I'll implement a few more key ones
    
    async def handle_get_momentum_analysis(self, 
                                         query: GetMomentumAnalysisQuery) -> Dict[str, Any]:
        """Handle momentum analysis query."""
        session = await self.session_repository.get_by_id(InteractionId(query.session_id))
        
        if not session:
            return {
                'found': False,
                'session_id': str(query.session_id),
                'error': 'Session not found'
            }
        
        # Get recent responses within analysis window
        cutoff_time = query.timestamp - timedelta(hours=query.analysis_window_hours)
        recent_responses = []
        
        for party_responses in session.responses.values():
            for response in party_responses:
                if response.response_timestamp >= cutoff_time:
                    recent_responses.append(response)
        
        if not recent_responses:
            return {
                'found': True,
                'session_id': str(query.session_id),
                'momentum_analysis': {
                    'momentum_score': 0,
                    'direction': 'stagnant',
                    'velocity': 'none',
                    'trajectory_prediction': 'uncertain',
                    'analysis_note': 'No recent responses to analyze'
                },
                'responses_analyzed': 0,
                'analysis_window_hours': query.analysis_window_hours
            }
        
        # Calculate momentum using domain service
        momentum = self.negotiation_service.calculate_negotiation_momentum(
            responses=recent_responses,
            phase=session.status.phase
        )
        
        # Convert Decimal values for JSON serialization
        momentum['momentum_score'] = float(momentum['momentum_score'])
        
        return {
            'found': True,
            'session_id': str(query.session_id),
            'momentum_analysis': momentum,
            'responses_analyzed': len(recent_responses),
            'analysis_window_hours': query.analysis_window_hours,
            'current_phase': session.status.phase.value
        }