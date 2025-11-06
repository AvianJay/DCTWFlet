from abc import ABC
from datetime import datetime
from typing import Any
import uuid


class DomainEvent(ABC):

    def __init__(self):
        self._event_id = str(uuid.uuid4())
        self._occurred_at = datetime.now()

    @property
    def event_id(self) -> str:
        return self._event_id

    @property
    def occurred_at(self) -> datetime:
        return self._occurred_at

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(event_id={self._event_id}, occurred_at={self._occurred_at})"
