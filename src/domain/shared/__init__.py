"""
Domain shared kernel - 领域共享内核
包含所有领域层的基础类和接口
"""

from .entity import Entity
from .value_object import ValueObject
from .aggregate_root import AggregateRoot
from .domain_event import DomainEvent
from .exceptions import (
    DomainException,
    InvalidArgumentException,
    EntityNotFoundException,
)

__all__ = [
    "Entity",
    "ValueObject",
    "AggregateRoot",
    "DomainEvent",
    "DomainException",
    "InvalidArgumentException",
    "EntityNotFoundException",
]
