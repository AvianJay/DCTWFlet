"""Content status value object"""

from enum import Enum


class ContentStatus(Enum):
    """Content status (mainly used for Bot)"""

    ONLINE = "online"
    IDLE = "idle"
    DND = "dnd"  # Do Not Disturb
    OFFLINE = "offline"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str) -> "ContentStatus":
        try:
            return cls(value.lower())
        except (ValueError, AttributeError):
            return cls.UNKNOWN

    def __str__(self) -> str:
        return self.value

    @property
    def is_online(self) -> bool:
        return self == ContentStatus.ONLINE

    @property
    def is_available(self) -> bool:
        return self in (ContentStatus.ONLINE, ContentStatus.IDLE)
