"""Timestamps value object"""

from datetime import datetime
from domain.shared import ValueObject


class Timestamps(ValueObject):

    def __init__(self, created_at: datetime, bumped_at: datetime = None):
        if not created_at:
            raise ValueError("created_at is required")

        self._created_at = created_at
        self._bumped_at = bumped_at or created_at

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def bumped_at(self) -> datetime:
        return self._bumped_at

    def _equality_components(self) -> tuple:
        return self._created_at, self._bumped_at

    def with_bump(self, bumped_at: datetime) -> "Timestamps":
        """Create new timestamp object with updated bump time"""
        return Timestamps(self._created_at, bumped_at)
