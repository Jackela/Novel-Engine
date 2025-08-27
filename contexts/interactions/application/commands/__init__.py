#!/usr/bin/env python3
"""
Commands Package for Interaction Application Layer

This package contains command objects that represent business operations
within the Interaction bounded context. Commands follow CQRS principles
and encapsulate all data needed to perform specific business actions.

Key Commands:
- Session Management: Create, configure, and terminate negotiation sessions
- Party Management: Add, remove, and update negotiation participants
- Proposal Management: Submit, withdraw, and modify proposals
- Response Management: Submit and update proposal responses
"""

from .interaction_commands import (
    # Session Commands
    CreateNegotiationSessionCommand,
    TerminateNegotiationSessionCommand,
    AdvanceNegotiationPhaseCommand,
    UpdateSessionConfigurationCommand,
    CheckSessionTimeoutCommand,
    
    # Party Commands
    AddPartyToSessionCommand,
    RemovePartyFromSessionCommand,
    UpdatePartyCapabilitiesCommand,
    UpdatePartyAuthorityCommand,
    
    # Proposal Commands
    SubmitProposalCommand,
    WithdrawProposalCommand,
    UpdateProposalCommand,
    OptimizeProposalCommand,
    
    # Response Commands
    SubmitProposalResponseCommand,
    UpdateResponseCommand,
    
    # Analysis Commands
    AnalyzeProposalViabilityCommand,
    AssessPartyCompatibilityCommand,
    RecommendNegotiationStrategyCommand,
    DetectNegotiationConflictsCommand,
    CalculateNegotiationMomentumCommand
)

__all__ = [
    # Session Commands
    'CreateNegotiationSessionCommand',
    'TerminateNegotiationSessionCommand',
    'AdvanceNegotiationPhaseCommand',
    'UpdateSessionConfigurationCommand',
    'CheckSessionTimeoutCommand',
    
    # Party Commands
    'AddPartyToSessionCommand',
    'RemovePartyFromSessionCommand',
    'UpdatePartyCapabilitiesCommand',
    'UpdatePartyAuthorityCommand',
    
    # Proposal Commands
    'SubmitProposalCommand',
    'WithdrawProposalCommand',
    'UpdateProposalCommand',
    'OptimizeProposalCommand',
    
    # Response Commands
    'SubmitProposalResponseCommand',
    'UpdateResponseCommand',
    
    # Analysis Commands
    'AnalyzeProposalViabilityCommand',
    'AssessPartyCompatibilityCommand',
    'RecommendNegotiationStrategyCommand',
    'DetectNegotiationConflictsCommand',
    'CalculateNegotiationMomentumCommand'
]

__version__ = "1.0.0"
