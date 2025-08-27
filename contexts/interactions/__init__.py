"""
Interaction Bounded Context

This bounded context handles complex interactions between entities in the
game world. It manages negotiation sessions, diplomatic exchanges, trade
discussions, and other sophisticated inter-entity communications.

Key Components:
- NegotiationSession: Aggregate representing ongoing negotiations between entities
- NegotiationParty: Entity representing participants in negotiations  
- Proposal: Entity representing specific proposals and terms
- NegotiationService: Domain service for managing negotiation logic

The Interaction context is responsible for ensuring that negotiations follow
proper protocols, that proposals are valid and feasible, and that outcomes
are fairly determined based on the participants' capabilities and positions.
"""

__version__ = "2.0.0"
__context_name__ = "interactions"
__description__ = "Interaction Bounded Context with Negotiation and Diplomatic Systems"