"""Theme value object"""

from enum import Enum


class Theme(Enum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"

    @classmethod
    def from_string(cls, value: str) -> "Theme":
        try:
            return cls(value.lower())
        except (ValueError, AttributeError):
            return cls.SYSTEM

    def __str__(self) -> str:
        return self.value

    @property
    def is_system(self) -> bool:
        return self == Theme.SYSTEM

    @property
    def is_light(self) -> bool:
        return self == Theme.LIGHT

    @property
    def is_dark(self) -> bool:
        return self == Theme.DARK
