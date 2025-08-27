#!/usr/bin/env python3
"""
Negotiation Domain Service

This module implements the core negotiation service that orchestrates
complex negotiation logic, compatibility assessment, and strategic analysis
within the Interaction bounded context.
"""

from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID

from ..value_objects.negotiation_party import NegotiationParty, NegotiationStyle, CommunicationPreference
from ..value_objects.negotiation_status import NegotiationPhase, NegotiationOutcome
from ..value_objects.proposal_terms import ProposalTerms, TermCondition, ProposalPriority
from ..value_objects.proposal_response import ProposalResponse, ResponseType


class NegotiationService:
    """
    Domain service for complex negotiation logic and analysis.
    
    Provides sophisticated negotiation orchestration, compatibility assessment,
    conflict resolution, and strategic analysis capabilities.
    """
    
    def __init__(self):
        """Initialize negotiation service."""
        pass
    
    def assess_party_compatibility(self, party1: NegotiationParty, 
                                 party2: NegotiationParty,
                                 negotiation_domain: Optional[str] = None) -> Decimal:
        """
        Assess compatibility between two negotiation parties.
        
        Returns compatibility score from 0 (completely incompatible) to 100 (perfect match).
        """
        if party1.entity_id == party2.entity_id:
            return Decimal('0')  # Can't negotiate with self
        
        compatibility_score = Decimal('50')  # Base neutral compatibility
        
        # Authority compatibility
        authority_score = self._assess_authority_compatibility(party1, party2)
        compatibility_score += (authority_score - Decimal('50')) * Decimal('0.3')
        
        # Communication style compatibility
        communication_score = self._assess_communication_compatibility(party1, party2)
        compatibility_score += (communication_score - Decimal('50')) * Decimal('0.25')
        
        # Negotiation style compatibility
        style_score = self._assess_negotiation_style_compatibility(party1, party2)
        compatibility_score += (style_score - Decimal('50')) * Decimal('0.2')
        
        # Domain expertise compatibility
        if negotiation_domain:
            domain_score = self._assess_domain_expertise_compatibility(
                party1, party2, negotiation_domain
            )
            compatibility_score += (domain_score - Decimal('50')) * Decimal('0.15')
        
        # Time preferences compatibility
        time_score = self._assess_time_compatibility(party1, party2)
        compatibility_score += (time_score - Decimal('50')) * Decimal('0.1')
        
        return max(Decimal('0'), min(Decimal('100'), compatibility_score))
    
    def analyze_proposal_viability(self, proposal: ProposalTerms,
                                 parties: List[NegotiationParty],
                                 negotiation_domain: Optional[str] = None) -> Dict[str, any]:
        """
        Analyze the viability of a proposal given the negotiating parties.
        
        Returns comprehensive analysis including acceptance probability,
        risk factors, and optimization suggestions.
        """
        analysis = {
            'overall_viability_score': Decimal('0'),
            'acceptance_probability': Decimal('0'),
            'risk_factors': [],
            'optimization_suggestions': [],
            'party_specific_analysis': {},
            'critical_issues': [],
            'success_factors': []
        }
        
        if not parties:
            analysis['critical_issues'].append("No parties to analyze")
            return analysis
        
        # Analyze each party's likely response
        party_scores = []
        for party in parties:
            if party.is_decision_maker:
                party_analysis = self._analyze_party_proposal_fit(
                    proposal, party, negotiation_domain
                )
                analysis['party_specific_analysis'][str(party.party_id)] = party_analysis
                party_scores.append(party_analysis['acceptance_score'])
        
        if party_scores:
            # Overall viability based on decision makers
            analysis['overall_viability_score'] = sum(party_scores) / len(party_scores)
            analysis['acceptance_probability'] = self._calculate_acceptance_probability(
                party_scores, proposal
            )
        
        # Identify risk factors
        analysis['risk_factors'] = self._identify_proposal_risks(proposal, parties)
        
        # Generate optimization suggestions
        analysis['optimization_suggestions'] = self._generate_optimization_suggestions(
            proposal, parties, analysis['party_specific_analysis']
        )
        
        # Identify critical issues
        analysis['critical_issues'] = self._identify_critical_proposal_issues(
            proposal, parties
        )
        
        # Identify success factors
        analysis['success_factors'] = self._identify_success_factors(
            proposal, parties
        )
        
        return analysis
    
    def recommend_negotiation_strategy(self, parties: List[NegotiationParty],
                                     negotiation_domain: Optional[str] = None,
                                     target_outcome: Optional[str] = None) -> Dict[str, any]:
        """
        Recommend negotiation strategy based on party composition and goals.
        
        Returns strategic recommendations including approach, tactics,
        sequence, and risk mitigation.
        """
        strategy = {
            'recommended_approach': 'collaborative',
            'phase_sequence': [],
            'key_tactics': [],
            'risk_mitigation': [],
            'success_metrics': [],
            'timeline_recommendations': {},
            'party_specific_strategies': {}
        }
        
        if not parties:
            return strategy
        
        # Analyze party composition
        decision_makers = [p for p in parties if p.is_decision_maker]
        dominant_styles = self._analyze_dominant_negotiation_styles(parties)
        power_balance = self._analyze_negotiation_power_balance(parties, negotiation_domain)
        
        # Recommend overall approach
        strategy['recommended_approach'] = self._recommend_overall_approach(
            dominant_styles, power_balance
        )
        
        # Recommend phase sequence
        strategy['phase_sequence'] = self._recommend_phase_sequence(
            parties, strategy['recommended_approach']
        )
        
        # Recommend key tactics
        strategy['key_tactics'] = self._recommend_negotiation_tactics(
            parties, dominant_styles, power_balance
        )
        
        # Risk mitigation strategies
        strategy['risk_mitigation'] = self._recommend_risk_mitigation(
            parties, dominant_styles
        )
        
        # Success metrics
        strategy['success_metrics'] = self._define_success_metrics(
            parties, target_outcome
        )
        
        # Timeline recommendations
        strategy['timeline_recommendations'] = self._recommend_timeline(
            parties, strategy['recommended_approach']
        )
        
        # Party-specific strategies
        for party in decision_makers:
            strategy['party_specific_strategies'][str(party.party_id)] = \
                self._recommend_party_specific_strategy(party, parties, negotiation_domain)
        
        return strategy
    
    def detect_negotiation_conflicts(self, parties: List[NegotiationParty],
                                   responses: List[ProposalResponse]) -> List[Dict[str, any]]:
        """
        Detect conflicts in negotiation based on parties and responses.
        
        Returns list of detected conflicts with severity, type, and resolution suggestions.
        """
        conflicts = []
        
        # Style conflicts
        style_conflicts = self._detect_style_conflicts(parties)
        conflicts.extend(style_conflicts)
        
        # Authority conflicts
        authority_conflicts = self._detect_authority_conflicts(parties)
        conflicts.extend(authority_conflicts)
        
        # Response conflicts
        response_conflicts = self._detect_response_conflicts(responses)
        conflicts.extend(response_conflicts)
        
        # Cultural conflicts
        cultural_conflicts = self._detect_cultural_conflicts(parties)
        conflicts.extend(cultural_conflicts)
        
        # Time pressure conflicts
        time_conflicts = self._detect_time_conflicts(parties)
        conflicts.extend(time_conflicts)
        
        return conflicts
    
    def calculate_negotiation_momentum(self, responses: List[ProposalResponse],
                                     phase: NegotiationPhase,
                                     time_factors: Optional[Dict[str, any]] = None) -> Dict[str, any]:
        """
        Calculate negotiation momentum and trajectory.
        
        Returns momentum analysis including direction, velocity, and predictions.
        """
        momentum = {
            'momentum_score': Decimal('0'),
            'direction': 'stagnant',
            'velocity': 'slow',
            'trajectory_prediction': 'uncertain',
            'key_drivers': [],
            'inhibiting_factors': [],
            'recommendations': []
        }
        
        if not responses:
            return momentum
        
        # Calculate response trends
        acceptance_trend = self._calculate_acceptance_trend(responses)
        response_speed = self._calculate_response_speed(responses)
        engagement_level = self._calculate_engagement_level(responses)
        
        # Overall momentum score
        momentum_factors = [acceptance_trend, response_speed, engagement_level]
        momentum['momentum_score'] = sum(momentum_factors) / len(momentum_factors)
        
        # Determine direction
        momentum['direction'] = self._determine_momentum_direction(
            acceptance_trend, responses
        )
        
        # Determine velocity
        momentum['velocity'] = self._determine_momentum_velocity(
            response_speed, engagement_level
        )
        
        # Predict trajectory
        momentum['trajectory_prediction'] = self._predict_negotiation_trajectory(
            momentum['momentum_score'], momentum['direction'], phase
        )
        
        # Identify key drivers
        momentum['key_drivers'] = self._identify_momentum_drivers(responses)
        
        # Identify inhibiting factors
        momentum['inhibiting_factors'] = self._identify_momentum_inhibitors(responses)
        
        # Generate recommendations
        momentum['recommendations'] = self._recommend_momentum_actions(
            momentum, phase
        )
        
        return momentum
    
    def optimize_proposal_terms(self, proposal: ProposalTerms,
                              parties: List[NegotiationParty],
                              negotiation_domain: Optional[str] = None) -> Dict[str, any]:
        """
        Optimize proposal terms for better acceptance chances.
        
        Returns optimization suggestions and predicted improvements.
        """
        optimization = {
            'optimized_terms': [],
            'expected_improvement': Decimal('0'),
            'optimization_rationale': {},
            'risk_assessment': {},
            'implementation_difficulty': 'medium'
        }
        
        decision_makers = [p for p in parties if p.is_decision_maker]
        if not decision_makers:
            return optimization
        
        # Analyze current term performance
        term_analysis = {}
        for term in proposal.terms:
            term_analysis[term.term_id] = self._analyze_term_performance(
                term, decision_makers, negotiation_domain
            )
        
        # Generate optimization suggestions
        optimized_terms = []
        for term in proposal.terms:
            analysis = term_analysis[term.term_id]
            if analysis['optimization_potential'] > Decimal('10'):
                optimized_term = self._optimize_term(term, analysis, decision_makers)
                optimized_terms.append(optimized_term)
                optimization['optimization_rationale'][term.term_id] = analysis['reasoning']
        
        optimization['optimized_terms'] = optimized_terms
        
        # Calculate expected improvement
        if optimized_terms:
            current_acceptance = self._estimate_proposal_acceptance(
                proposal, decision_makers
            )
            optimized_proposal = proposal
            for optimized_term in optimized_terms:
                optimized_proposal = optimized_proposal.update_term(
                    optimized_term.term_id, optimized_term
                )
            optimized_acceptance = self._estimate_proposal_acceptance(
                optimized_proposal, decision_makers
            )
            optimization['expected_improvement'] = optimized_acceptance - current_acceptance
        
        # Risk assessment
        optimization['risk_assessment'] = self._assess_optimization_risks(
            optimized_terms, parties
        )
        
        # Implementation difficulty
        optimization['implementation_difficulty'] = self._assess_implementation_difficulty(
            optimized_terms
        )
        
        return optimization
    
    # Private helper methods
    
    def _assess_authority_compatibility(self, party1: NegotiationParty,
                                      party2: NegotiationParty) -> Decimal:
        """Assess authority level compatibility between parties."""
        if party1.can_make_binding_decisions() and party2.can_make_binding_decisions():
            return Decimal('80')  # Both can make decisions - good compatibility
        elif party1.can_make_binding_decisions() or party2.can_make_binding_decisions():
            return Decimal('60')  # One decision maker - moderate compatibility
        else:
            return Decimal('20')  # No decision makers - poor compatibility
    
    def _assess_communication_compatibility(self, party1: NegotiationParty,
                                          party2: NegotiationParty) -> Decimal:
        """Assess communication style compatibility."""
        style1 = party1.preferences.communication_preference
        style2 = party2.preferences.communication_preference
        
        # Compatibility matrix for communication styles
        compatibility_matrix = {
            (CommunicationPreference.DIRECT, CommunicationPreference.DIRECT): Decimal('90'),
            (CommunicationPreference.DIRECT, CommunicationPreference.DIPLOMATIC): Decimal('60'),
            (CommunicationPreference.DIPLOMATIC, CommunicationPreference.DIPLOMATIC): Decimal('85'),
            (CommunicationPreference.FORMAL, CommunicationPreference.FORMAL): Decimal('80'),
            (CommunicationPreference.INFORMAL, CommunicationPreference.INFORMAL): Decimal('75'),
            (CommunicationPreference.ANALYTICAL, CommunicationPreference.ANALYTICAL): Decimal('90'),
        }
        
        # Try both directions
        key = (style1, style2)
        if key in compatibility_matrix:
            return compatibility_matrix[key]
        
        reverse_key = (style2, style1)
        if reverse_key in compatibility_matrix:
            return compatibility_matrix[reverse_key]
        
        # Default moderate compatibility for unmatched pairs
        return Decimal('50')
    
    def _assess_negotiation_style_compatibility(self, party1: NegotiationParty,
                                              party2: NegotiationParty) -> Decimal:
        """Assess negotiation style compatibility."""
        style1 = party1.preferences.negotiation_style
        style2 = party2.preferences.negotiation_style
        
        # High compatibility pairs
        if (style1 == NegotiationStyle.COLLABORATIVE and 
            style2 == NegotiationStyle.COLLABORATIVE):
            return Decimal('95')
        
        if (style1 == NegotiationStyle.INTEGRATIVE and 
            style2 == NegotiationStyle.INTEGRATIVE):
            return Decimal('90')
        
        # Moderate compatibility
        if style1 == NegotiationStyle.COMPROMISING or style2 == NegotiationStyle.COMPROMISING:
            return Decimal('70')
        
        # Problematic combinations
        if ((style1 == NegotiationStyle.COMPETITIVE and style2 == NegotiationStyle.AVOIDING) or
            (style1 == NegotiationStyle.AVOIDING and style2 == NegotiationStyle.COMPETITIVE)):
            return Decimal('20')
        
        return Decimal('50')  # Default moderate compatibility
    
    def _assess_domain_expertise_compatibility(self, party1: NegotiationParty,
                                             party2: NegotiationParty,
                                             domain: str) -> Decimal:
        """Assess domain expertise compatibility."""
        capabilities1 = party1.get_capabilities_for_domain(domain)
        capabilities2 = party2.get_capabilities_for_domain(domain)
        
        if not capabilities1 and not capabilities2:
            return Decimal('30')  # Both lack expertise - poor compatibility
        
        if not capabilities1 or not capabilities2:
            return Decimal('60')  # Imbalanced expertise - moderate compatibility
        
        # Both have expertise - calculate balance
        power1 = party1.get_negotiation_power(domain)
        power2 = party2.get_negotiation_power(domain)
        
        power_ratio = min(power1, power2) / max(power1, power2) if max(power1, power2) > 0 else Decimal('0')
        
        # More balanced power = better compatibility
        return Decimal('50') + (power_ratio * Decimal('40'))
    
    def _assess_time_compatibility(self, party1: NegotiationParty,
                                 party2: NegotiationParty) -> Decimal:
        """Assess time preference compatibility."""
        pref1 = party1.preferences
        pref2 = party2.preferences
        
        # Check session duration compatibility
        if pref1.maximum_session_duration and pref2.maximum_session_duration:
            min_duration = min(pref1.maximum_session_duration, pref2.maximum_session_duration)
            if min_duration < 30:  # Less than 30 minutes
                return Decimal('30')
        
        # Check time pressure sensitivity
        sensitivity_diff = abs(pref1.time_pressure_sensitivity - pref2.time_pressure_sensitivity)
        if sensitivity_diff > 50:
            return Decimal('40')  # Very different sensitivities
        
        return Decimal('70')  # Generally compatible
    
    def _analyze_party_proposal_fit(self, proposal: ProposalTerms,
                                  party: NegotiationParty,
                                  domain: Optional[str]) -> Dict[str, any]:
        """Analyze how well a proposal fits a specific party."""
        analysis = {
            'acceptance_score': Decimal('50'),
            'concerns': [],
            'positive_factors': [],
            'deal_breakers': [],
            'negotiable_items': []
        }
        
        # Analyze each term
        for term in proposal.terms:
            term_score = self._score_term_for_party(term, party, domain)
            analysis['acceptance_score'] += (term_score - Decimal('50')) / len(proposal.terms)
            
            if term_score < 20:
                analysis['deal_breakers'].append(f"Term {term.term_id}: {term.description}")
            elif term_score < 40:
                analysis['concerns'].append(f"Term {term.term_id}: {term.description}")
            elif term_score > 70:
                analysis['positive_factors'].append(f"Term {term.term_id}: {term.description}")
            
            if term.is_negotiable:
                analysis['negotiable_items'].append(term.term_id)
        
        # Ensure score is within bounds
        analysis['acceptance_score'] = max(Decimal('0'), min(Decimal('100'), analysis['acceptance_score']))
        
        return analysis
    
    def _score_term_for_party(self, term: TermCondition,
                            party: NegotiationParty,
                            domain: Optional[str]) -> Decimal:
        """Score how acceptable a term is for a party."""
        base_score = Decimal('50')
        
        # Priority weighting
        priority_weight = {
            ProposalPriority.CRITICAL: Decimal('2.0'),
            ProposalPriority.HIGH: Decimal('1.5'),
            ProposalPriority.MEDIUM: Decimal('1.0'),
            ProposalPriority.LOW: Decimal('0.7'),
            ProposalPriority.OPTIONAL: Decimal('0.5')
        }
        
        weight = priority_weight.get(term.priority, Decimal('1.0'))
        
        # Domain expertise factor
        if domain:
            expertise = party.get_negotiation_power(domain)
            if expertise > 70:
                base_score += Decimal('10')  # High expertise = better evaluation
            elif expertise < 30:
                base_score -= Decimal('10')  # Low expertise = worse evaluation
        
        # Authority factor
        if not party.can_make_binding_decisions() and not term.is_negotiable:
            base_score -= Decimal('20')  # Non-negotiable terms harder for non-decision makers
        
        return base_score * weight
    
    def _calculate_acceptance_probability(self, party_scores: List[Decimal],
                                        proposal: ProposalTerms) -> Decimal:
        """Calculate overall acceptance probability."""
        if not party_scores:
            return Decimal('0')
        
        # Base probability from average scores
        avg_score = sum(party_scores) / len(party_scores)
        base_probability = avg_score
        
        # Adjust for proposal characteristics
        if proposal.is_expired:
            base_probability *= Decimal('0.1')  # Expired proposals very unlikely
        
        critical_terms = proposal.get_critical_terms()
        if len(critical_terms) > 5:
            base_probability *= Decimal('0.8')  # Too many critical terms reduce probability
        
        return min(Decimal('100'), base_probability)
    
    def _identify_proposal_risks(self, proposal: ProposalTerms,
                               parties: List[NegotiationParty]) -> List[str]:
        """Identify risks in the proposal."""
        risks = []
        
        if proposal.is_expired:
            risks.append("Proposal has expired")
        
        if len(proposal.get_critical_terms()) > 3:
            risks.append("High number of critical terms may reduce flexibility")
        
        non_negotiable = proposal.get_non_negotiable_terms()
        if len(non_negotiable) > len(proposal.terms) * 0.7:
            risks.append("High proportion of non-negotiable terms")
        
        if proposal.total_terms_count > 10:
            risks.append("Complex proposal with many terms may be difficult to evaluate")
        
        return risks
    
    def _generate_optimization_suggestions(self, proposal: ProposalTerms,
                                         parties: List[NegotiationParty],
                                         party_analyses: Dict[str, any]) -> List[str]:
        """Generate suggestions to optimize the proposal."""
        suggestions = []
        
        # Analyze common concerns
        common_concerns = {}
        for analysis in party_analyses.values():
            for concern in analysis.get('concerns', []):
                common_concerns[concern] = common_concerns.get(concern, 0) + 1
        
        # Suggest addressing common concerns
        for concern, count in common_concerns.items():
            if count >= len(party_analyses) // 2:
                suggestions.append(f"Address common concern: {concern}")
        
        # Suggest making terms negotiable
        non_negotiable = proposal.get_non_negotiable_terms()
        if len(non_negotiable) > 2:
            suggestions.append("Consider making some non-critical terms negotiable")
        
        # Suggest breaking down complex proposals
        if proposal.total_terms_count > 8:
            suggestions.append("Consider breaking proposal into phases")
        
        return suggestions
    
    def _identify_critical_proposal_issues(self, proposal: ProposalTerms,
                                         parties: List[NegotiationParty]) -> List[str]:
        """Identify critical issues that could kill the proposal."""
        issues = []
        
        if proposal.is_expired:
            issues.append("Proposal is expired")
        
        # Check for deal-breaker terms
        critical_terms = proposal.get_critical_terms()
        if len(critical_terms) == proposal.total_terms_count:
            issues.append("All terms are marked as critical - no negotiation flexibility")
        
        # Authority issues
        decision_makers = [p for p in parties if p.is_decision_maker]
        if not decision_makers:
            issues.append("No parties have authority to accept proposal")
        
        return issues
    
    def _identify_success_factors(self, proposal: ProposalTerms,
                                parties: List[NegotiationParty]) -> List[str]:
        """Identify factors that could lead to proposal success."""
        factors = []
        
        negotiable_count = proposal.negotiable_terms_count
        if negotiable_count > proposal.total_terms_count // 2:
            factors.append("Good proportion of negotiable terms allows flexibility")
        
        if proposal.proposal_type in [ProposalTerms.ProposalType.ALLIANCE_REQUEST,
                                    ProposalTerms.ProposalType.RESOURCE_EXCHANGE]:
            factors.append("Proposal type typically has good success rate")
        
        decision_makers = [p for p in parties if p.is_decision_maker]
        if len(decision_makers) >= 2:
            factors.append("Multiple decision makers can drive agreement")
        
        return factors
    
    def _analyze_dominant_negotiation_styles(self, parties: List[NegotiationParty]) -> Dict[str, int]:
        """Analyze dominant negotiation styles in the group."""
        style_counts = {}
        for party in parties:
            style = party.preferences.negotiation_style.value
            style_counts[style] = style_counts.get(style, 0) + 1
        
        return style_counts
    
    def _analyze_negotiation_power_balance(self, parties: List[NegotiationParty],
                                         domain: Optional[str]) -> Dict[str, any]:
        """Analyze the balance of negotiation power."""
        power_analysis = {
            'total_power': Decimal('0'),
            'power_distribution': {},
            'imbalance_score': Decimal('0'),
            'dominant_party': None
        }
        
        if not domain:
            return power_analysis
        
        powers = []
        for party in parties:
            power = party.get_negotiation_power(domain)
            powers.append(power)
            power_analysis['power_distribution'][str(party.party_id)] = power
        
        if powers:
            power_analysis['total_power'] = sum(powers)
            max_power = max(powers)
            min_power = min(powers)
            
            if max_power > 0:
                power_analysis['imbalance_score'] = (max_power - min_power) / max_power
                
                # Find dominant party
                for party in parties:
                    if party.get_negotiation_power(domain) == max_power:
                        power_analysis['dominant_party'] = str(party.party_id)
                        break
        
        return power_analysis
    
    def _recommend_overall_approach(self, dominant_styles: Dict[str, int],
                                  power_balance: Dict[str, any]) -> str:
        """Recommend overall negotiation approach."""
        # If collaborative is dominant, recommend collaborative
        if dominant_styles.get('collaborative', 0) > len(dominant_styles) // 2:
            return 'collaborative'
        
        # If power is balanced, recommend integrative
        imbalance = power_balance.get('imbalance_score', Decimal('0'))
        if imbalance < Decimal('0.3'):
            return 'integrative'
        
        # If power is imbalanced, recommend diplomatic
        if imbalance > Decimal('0.7'):
            return 'diplomatic'
        
        return 'balanced'
    
    def _recommend_phase_sequence(self, parties: List[NegotiationParty],
                                approach: str) -> List[str]:
        """Recommend negotiation phase sequence."""
        if approach == 'collaborative':
            return ['preparation', 'opening', 'brainstorming', 'bargaining', 'closing']
        elif approach == 'diplomatic':
            return ['preparation', 'relationship_building', 'opening', 'careful_bargaining', 'closing']
        else:
            return ['preparation', 'opening', 'bargaining', 'closing']
    
    def _recommend_negotiation_tactics(self, parties: List[NegotiationParty],
                                     dominant_styles: Dict[str, int],
                                     power_balance: Dict[str, any]) -> List[str]:
        """Recommend specific negotiation tactics."""
        tactics = []
        
        if dominant_styles.get('analytical', 0) > 0:
            tactics.append("Prepare detailed data and analysis")
        
        if dominant_styles.get('collaborative', 0) > 0:
            tactics.append("Focus on mutual gains and win-win solutions")
        
        if power_balance.get('imbalance_score', Decimal('0')) > Decimal('0.5'):
            tactics.append("Build coalitions to balance power")
        
        tactics.append("Establish clear communication protocols")
        tactics.append("Set realistic timelines and milestones")
        
        return tactics
    
    def _recommend_risk_mitigation(self, parties: List[NegotiationParty],
                                 dominant_styles: Dict[str, int]) -> List[str]:
        """Recommend risk mitigation strategies."""
        mitigations = []
        
        if dominant_styles.get('competitive', 0) > 1:
            mitigations.append("Establish ground rules to prevent adversarial behavior")
        
        if dominant_styles.get('avoiding', 0) > 0:
            mitigations.append("Create structured agenda to encourage participation")
        
        mitigations.append("Plan for timeout scenarios")
        mitigations.append("Establish escalation procedures for deadlocks")
        
        return mitigations
    
    def _define_success_metrics(self, parties: List[NegotiationParty],
                              target_outcome: Optional[str]) -> List[str]:
        """Define success metrics for the negotiation."""
        metrics = [
            "Mutual satisfaction score > 70%",
            "Agreement reached within timeline",
            "All critical issues addressed"
        ]
        
        if target_outcome:
            metrics.append(f"Target outcome achieved: {target_outcome}")
        
        if len(parties) > 2:
            metrics.append("Majority consensus achieved")
        
        return metrics
    
    def _recommend_timeline(self, parties: List[NegotiationParty],
                          approach: str) -> Dict[str, any]:
        """Recommend timeline for negotiation phases."""
        timeline = {}
        
        # Base timeline depends on approach
        if approach == 'diplomatic':
            timeline = {
                'preparation': '2-3 days',
                'relationship_building': '1-2 days',
                'opening': '1 day',
                'bargaining': '3-5 days',
                'closing': '1-2 days'
            }
        else:
            timeline = {
                'preparation': '1-2 days',
                'opening': '0.5-1 day',
                'bargaining': '2-4 days',
                'closing': '1 day'
            }
        
        # Adjust for party time sensitivities
        high_pressure_parties = [
            p for p in parties 
            if p.preferences.time_pressure_sensitivity > 70
        ]
        
        if len(high_pressure_parties) > len(parties) // 2:
            timeline['note'] = "Accelerated timeline recommended due to time pressure"
        
        return timeline
    
    def _recommend_party_specific_strategy(self, party: NegotiationParty,
                                         all_parties: List[NegotiationParty],
                                         domain: Optional[str]) -> Dict[str, any]:
        """Recommend strategy for specific party."""
        strategy = {
            'communication_approach': 'standard',
            'key_motivators': [],
            'potential_concerns': [],
            'influence_tactics': []
        }
        
        # Communication approach based on preferences
        comm_pref = party.preferences.communication_preference
        if comm_pref == CommunicationPreference.DIRECT:
            strategy['communication_approach'] = 'direct and straightforward'
        elif comm_pref == CommunicationPreference.DIPLOMATIC:
            strategy['communication_approach'] = 'diplomatic and respectful'
        elif comm_pref == CommunicationPreference.ANALYTICAL:
            strategy['communication_approach'] = 'data-driven and detailed'
        
        # Key motivators based on negotiation style
        neg_style = party.preferences.negotiation_style
        if neg_style == NegotiationStyle.COLLABORATIVE:
            strategy['key_motivators'].append('mutual benefit')
            strategy['key_motivators'].append('long-term relationship')
        elif neg_style == NegotiationStyle.COMPETITIVE:
            strategy['key_motivators'].append('winning outcomes')
            strategy['key_motivators'].append('competitive advantage')
        
        # Authority-based concerns
        if not party.can_make_binding_decisions():
            strategy['potential_concerns'].append('need for approval from higher authority')
        
        # Domain expertise considerations
        if domain:
            power = party.get_negotiation_power(domain)
            if power < 30:
                strategy['potential_concerns'].append('limited domain expertise')
                strategy['influence_tactics'].append('provide educational support')
        
        return strategy
    
    def _detect_style_conflicts(self, parties: List[NegotiationParty]) -> List[Dict[str, any]]:
        """Detect negotiation style conflicts."""
        conflicts = []
        
        for i, party1 in enumerate(parties):
            for party2 in parties[i+1:]:
                compatibility = self._assess_negotiation_style_compatibility(party1, party2)
                if compatibility < 40:
                    conflicts.append({
                        'type': 'negotiation_style_conflict',
                        'severity': 'high' if compatibility < 20 else 'medium',
                        'parties': [party1.party_id, party2.party_id],
                        'description': f"Incompatible negotiation styles: {party1.preferences.negotiation_style.value} vs {party2.preferences.negotiation_style.value}",
                        'resolution_suggestions': [
                            'Establish common ground rules',
                            'Use mediator to bridge style differences',
                            'Focus on objective criteria'
                        ]
                    })
        
        return conflicts
    
    def _detect_authority_conflicts(self, parties: List[NegotiationParty]) -> List[Dict[str, any]]:
        """Detect authority-related conflicts."""
        conflicts = []
        
        decision_makers = [p for p in parties if p.is_decision_maker]
        
        if not decision_makers:
            conflicts.append({
                'type': 'authority_conflict',
                'severity': 'critical',
                'parties': [p.party_id for p in parties],
                'description': 'No parties have decision-making authority',
                'resolution_suggestions': [
                    'Escalate to decision makers',
                    'Grant limited authority to representatives',
                    'Restructure negotiation with appropriate authorities'
                ]
            })
        
        elif len(decision_makers) == 1 and len(parties) > 2:
            conflicts.append({
                'type': 'authority_imbalance',
                'severity': 'medium',
                'parties': [p.party_id for p in parties if not p.is_decision_maker],
                'description': 'Only one party has decision-making authority',
                'resolution_suggestions': [
                    'Grant conditional authority to other parties',
                    'Restructure as preliminary negotiation',
                    'Include more decision makers'
                ]
            })
        
        return conflicts
    
    def _detect_response_conflicts(self, responses: List[ProposalResponse]) -> List[Dict[str, any]]:
        """Detect conflicts in proposal responses."""
        conflicts = []
        
        # Group responses by proposal
        proposal_responses = {}
        for response in responses:
            if response.proposal_id not in proposal_responses:
                proposal_responses[response.proposal_id] = []
            proposal_responses[response.proposal_id].append(response)
        
        # Analyze each proposal's responses
        for proposal_id, prop_responses in proposal_responses.items():
            if len(prop_responses) < 2:
                continue
            
            # Check for conflicting responses
            acceptance_responses = [r for r in prop_responses if r.is_complete_acceptance()]
            rejection_responses = [r for r in prop_responses if r.is_complete_rejection()]
            
            if len(acceptance_responses) > 0 and len(rejection_responses) > 0:
                conflicts.append({
                    'type': 'response_conflict',
                    'severity': 'high',
                    'parties': [r.responding_party_id for r in prop_responses],
                    'description': f'Conflicting responses to proposal {proposal_id}: some accept, some reject',
                    'resolution_suggestions': [
                        'Focus on negotiable terms',
                        'Seek compromise solutions',
                        'Break down proposal into components'
                    ]
                })
        
        return conflicts
    
    def _detect_cultural_conflicts(self, parties: List[NegotiationParty]) -> List[Dict[str, any]]:
        """Detect cultural conflicts between parties."""
        conflicts = []
        
        # Check for overlapping taboo topics
        all_taboos = set()
        party_taboos = {}
        
        for party in parties:
            party_taboos[party.party_id] = party.preferences.taboo_topics
            all_taboos.update(party.preferences.taboo_topics)
        
        # If there are common taboo topics, that's actually good (compatible)
        # Look for cases where one party's normal topics are another's taboos
        for party1 in parties:
            for party2 in parties:
                if party1.party_id == party2.party_id:
                    continue
                
                # This is a simplified check - in reality would need more sophisticated cultural analysis
                cultural1 = party1.preferences.cultural_considerations
                cultural2 = party2.preferences.cultural_considerations
                
                if cultural1 and cultural2 and not cultural1.intersection(cultural2):
                    conflicts.append({
                        'type': 'cultural_mismatch',
                        'severity': 'medium',
                        'parties': [party1.party_id, party2.party_id],
                        'description': 'Different cultural backgrounds may create misunderstandings',
                        'resolution_suggestions': [
                            'Establish cultural sensitivity protocols',
                            'Use neutral language and concepts',
                            'Consider cultural mediator if needed'
                        ]
                    })
                    break  # Only report once per party pair
        
        return conflicts
    
    def _detect_time_conflicts(self, parties: List[NegotiationParty]) -> List[Dict[str, any]]:
        """Detect time-related conflicts."""
        conflicts = []
        
        # Check for incompatible session durations
        max_durations = [
            p.preferences.maximum_session_duration 
            for p in parties 
            if p.preferences.maximum_session_duration
        ]
        
        if max_durations:
            min_max_duration = min(max_durations)
            if min_max_duration < 60:  # Less than 1 hour
                conflicts.append({
                    'type': 'time_constraint_conflict',
                    'severity': 'high',
                    'parties': [p.party_id for p in parties if p.preferences.maximum_session_duration == min_max_duration],
                    'description': f'Very short maximum session duration ({min_max_duration} minutes) may prevent meaningful negotiation',
                    'resolution_suggestions': [
                        'Break negotiation into multiple short sessions',
                        'Pre-negotiate to narrow scope',
                        'Use asynchronous proposal exchange'
                    ]
                })
        
        # Check for time pressure sensitivity conflicts
        sensitivities = [p.preferences.time_pressure_sensitivity for p in parties]
        if max(sensitivities) - min(sensitivities) > 50:
            conflicts.append({
                'type': 'time_pressure_mismatch',
                'severity': 'medium',
                'parties': [p.party_id for p in parties],
                'description': 'Significantly different time pressure sensitivities may create stress',
                'resolution_suggestions': [
                    'Set clear timeline expectations upfront',
                    'Build in buffer time for high-pressure-sensitive parties',
                    'Use structured agenda to manage time efficiently'
                ]
            })
        
        return conflicts
    
    def _calculate_acceptance_trend(self, responses: List[ProposalResponse]) -> Decimal:
        """Calculate trend in acceptance rates over time."""
        if len(responses) < 2:
            return Decimal('50')
        
        # Sort responses by timestamp
        sorted_responses = sorted(responses, key=lambda r: r.response_timestamp)
        
        # Calculate acceptance percentages
        acceptances = [r.get_acceptance_percentage() for r in sorted_responses]
        
        # Simple linear trend calculation
        if len(acceptances) >= 2:
            recent_avg = sum(acceptances[-2:]) / 2
            older_avg = sum(acceptances[:-2]) / max(1, len(acceptances) - 2) if len(acceptances) > 2 else acceptances[0]
            trend = recent_avg - older_avg
            
            # Convert to 0-100 scale
            return Decimal('50') + Decimal(str(trend / 2))  # Scale trend
        
        return Decimal('50')
    
    def _calculate_response_speed(self, responses: List[ProposalResponse]) -> Decimal:
        """Calculate response speed metric."""
        if not responses:
            return Decimal('50')
        
        # Simple metric based on response count and recency
        recent_responses = [
            r for r in responses 
            if r.age_in_seconds < 3600  # Within last hour
        ]
        
        speed_score = min(len(recent_responses) * 20, 100)
        return Decimal(str(speed_score))
    
    def _calculate_engagement_level(self, responses: List[ProposalResponse]) -> Decimal:
        """Calculate engagement level from responses."""
        if not responses:
            return Decimal('0')
        
        # Factors that indicate engagement
        detailed_responses = [
            r for r in responses 
            if r.overall_comments or len(r.get_terms_with_modifications()) > 0
        ]
        
        engagement_score = len(detailed_responses) / len(responses) * 100
        return Decimal(str(engagement_score))
    
    def _determine_momentum_direction(self, acceptance_trend: Decimal,
                                    responses: List[ProposalResponse]) -> str:
        """Determine momentum direction."""
        if acceptance_trend > 60:
            return 'positive'
        elif acceptance_trend < 40:
            return 'negative'
        else:
            return 'stagnant'
    
    def _determine_momentum_velocity(self, response_speed: Decimal,
                                   engagement_level: Decimal) -> str:
        """Determine momentum velocity."""
        combined_speed = (response_speed + engagement_level) / 2
        
        if combined_speed > 70:
            return 'fast'
        elif combined_speed > 40:
            return 'moderate'
        else:
            return 'slow'
    
    def _predict_negotiation_trajectory(self, momentum_score: Decimal,
                                      direction: str,
                                      phase: NegotiationPhase) -> str:
        """Predict negotiation trajectory."""
        if momentum_score > 70 and direction == 'positive':
            return 'likely_success'
        elif momentum_score < 30 and direction == 'negative':
            return 'likely_failure'
        elif phase in [NegotiationPhase.BARGAINING, NegotiationPhase.CLOSING]:
            if momentum_score > 50:
                return 'cautiously_optimistic'
            else:
                return 'concerning'
        else:
            return 'uncertain'
    
    def _identify_momentum_drivers(self, responses: List[ProposalResponse]) -> List[str]:
        """Identify factors driving momentum."""
        drivers = []
        
        if responses:
            avg_acceptance = sum(r.get_acceptance_percentage() for r in responses) / len(responses)
            if avg_acceptance > 60:
                drivers.append("High average acceptance rate")
            
            collaborative_responses = [
                r for r in responses 
                if r.overall_response in [ResponseType.CONDITIONAL_ACCEPT, ResponseType.COUNTER_PROPOSAL]
            ]
            
            if len(collaborative_responses) > len(responses) / 2:
                drivers.append("Constructive, collaborative responses")
        
        return drivers
    
    def _identify_momentum_inhibitors(self, responses: List[ProposalResponse]) -> List[str]:
        """Identify factors inhibiting momentum."""
        inhibitors = []
        
        if responses:
            rejections = [r for r in responses if r.is_complete_rejection()]
            if len(rejections) > len(responses) / 3:
                inhibitors.append("High rejection rate")
            
            expired_responses = [r for r in responses if r.is_expired()]
            if expired_responses:
                inhibitors.append("Expired responses indicate timing issues")
        
        return inhibitors
    
    def _recommend_momentum_actions(self, momentum: Dict[str, any],
                                  phase: NegotiationPhase) -> List[str]:
        """Recommend actions to improve momentum."""
        recommendations = []
        
        if momentum['direction'] == 'negative':
            recommendations.append("Address key concerns and objections")
            recommendations.append("Consider breaking down complex proposals")
        
        if momentum['velocity'] == 'slow':
            recommendations.append("Set more aggressive timelines")
            recommendations.append("Increase meeting frequency")
        
        if phase == NegotiationPhase.BARGAINING and momentum['momentum_score'] < 40:
            recommendations.append("Consider bringing in mediator")
            recommendations.append("Focus on win-win solutions")
        
        return recommendations
    
    def _analyze_term_performance(self, term: TermCondition,
                                parties: List[NegotiationParty],
                                domain: Optional[str]) -> Dict[str, any]:
        """Analyze how well a term performs with parties."""
        analysis = {
            'optimization_potential': Decimal('0'),
            'reasoning': "",
            'suggested_changes': []
        }
        
        # Simple analysis based on term characteristics
        if not term.is_negotiable and term.priority != ProposalPriority.CRITICAL:
            analysis['optimization_potential'] = Decimal('30')
            analysis['reasoning'] = "Non-critical term could be made negotiable"
            analysis['suggested_changes'].append("Make term negotiable")
        
        if term.priority == ProposalPriority.LOW and len(term.dependencies or []) > 0:
            analysis['optimization_potential'] = Decimal('20')
            analysis['reasoning'] = "Low priority term with dependencies adds complexity"
            analysis['suggested_changes'].append("Remove dependencies or increase priority")
        
        return analysis
    
    def _optimize_term(self, term: TermCondition,
                     analysis: Dict[str, any],
                     parties: List[NegotiationParty]) -> TermCondition:
        """Optimize a term based on analysis."""
        optimized_term = term
        
        for change in analysis['suggested_changes']:
            if change == "Make term negotiable":
                optimized_term = optimized_term.make_non_negotiable()
            elif change.startswith("Remove dependencies"):
                optimized_term = TermCondition(
                    term_id=optimized_term.term_id,
                    term_type=optimized_term.term_type,
                    description=optimized_term.description,
                    value=optimized_term.value,
                    priority=optimized_term.priority,
                    is_negotiable=optimized_term.is_negotiable,
                    constraints=optimized_term.constraints,
                    dependencies=[]  # Remove dependencies
                )
        
        return optimized_term
    
    def _estimate_proposal_acceptance(self, proposal: ProposalTerms,
                                    parties: List[NegotiationParty]) -> Decimal:
        """Estimate proposal acceptance probability."""
        if not parties:
            return Decimal('0')
        
        party_scores = []
        for party in parties:
            if party.is_decision_maker:
                analysis = self._analyze_party_proposal_fit(proposal, party, None)
                party_scores.append(analysis['acceptance_score'])
        
        if party_scores:
            return sum(party_scores) / len(party_scores)
        
        return Decimal('0')
    
    def _assess_optimization_risks(self, optimized_terms: List[TermCondition],
                                 parties: List[NegotiationParty]) -> Dict[str, any]:
        """Assess risks of proposed optimizations."""
        risks = {
            'risk_level': 'low',
            'risk_factors': [],
            'mitigation_strategies': []
        }
        
        if len(optimized_terms) > 3:
            risks['risk_level'] = 'medium'
            risks['risk_factors'].append("Many simultaneous changes may confuse parties")
            risks['mitigation_strategies'].append("Phase implementation of changes")
        
        return risks
    
    def _assess_implementation_difficulty(self, optimized_terms: List[TermCondition]) -> str:
        """Assess difficulty of implementing optimizations."""
        if not optimized_terms:
            return 'none'
        
        if len(optimized_terms) <= 2:
            return 'low'
        elif len(optimized_terms) <= 5:
            return 'medium'
        else:
            return 'high'