"""
Shared Domain Base Module
"""

from src.shared.domain.base.entity import Entity
from src.shared.domain.base.value_object import ValueObject
from src.shared.domain.base.aggregate import AggregateRoot
from src.shared.domain.base.event import DomainEvent

__all__ = [
    "Entity",
    "ValueObject",
    "AggregateRoot",
    "DomainEvent",
]
