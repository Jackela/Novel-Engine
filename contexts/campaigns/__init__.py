"""
Campaigns Domain Context
=======================

Domain context for campaign management, including session orchestration,
world state management, campaign progression, and persistence coordination.

Domain Responsibilities:
- Campaign lifecycle and session management
- World state coordination and persistence
- Campaign progression and milestone tracking
- Campaign configuration and customization
- Campaign analytics and reporting

Bounded Context: All campaign and session-related domain logic
External Interfaces: Character context, Narrative context, Orchestration context
"""

__version__ = "1.0.0"
__context_name__ = "campaigns"
__description__ = (
    "Campaign Domain Context with Session and World State Management"
)
