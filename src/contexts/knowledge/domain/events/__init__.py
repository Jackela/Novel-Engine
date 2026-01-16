"""
Domain Events Package

Collection of domain events for the Knowledge Management bounded context.

Constitution Compliance:
- Article VI (EDA): All domain events are immutable and represent state changes
"""

from .knowledge_entry_created import KnowledgeEntryCreated
from .knowledge_entry_deleted import KnowledgeEntryDeleted
from .knowledge_entry_updated import KnowledgeEntryUpdated

__all__ = [
    "KnowledgeEntryCreated",
    "KnowledgeEntryUpdated",
    "KnowledgeEntryDeleted",
]
