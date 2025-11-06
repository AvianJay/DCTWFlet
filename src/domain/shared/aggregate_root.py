from typing import List
from .entity import Entity
from .domain_event import DomainEvent


class AggregateRoot(Entity[int]):
    def __init__(self, id: int = None):
        super().__init__(id if id is not None else 0)
        self._domain_events: List[DomainEvent] = []

    def add_domain_event(self, event: DomainEvent) -> None:
        self._domain_events.append(event)

    def clear_domain_events(self) -> None:
        self._domain_events.clear()

    def get_domain_events(self) -> List[DomainEvent]:
        return self._domain_events.copy()

    @property
    def has_domain_events(self) -> bool:
        return len(self._domain_events) > 0
