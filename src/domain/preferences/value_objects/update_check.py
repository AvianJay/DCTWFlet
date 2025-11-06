"""Update check value object"""

from enum import Enum


class UpdateCheck(Enum):

    POPUP = "popup"
    NOTIFY = "notify"
    NONE = "none"

    @classmethod
    def from_string(cls, value: str) -> "UpdateCheck":
        try:
            return cls(value.lower())
        except (ValueError, AttributeError):
            return cls.POPUP

    def __str__(self) -> str:
        return self.value

    @property
    def is_enabled(self) -> bool:
        return self != UpdateCheck.NONE
