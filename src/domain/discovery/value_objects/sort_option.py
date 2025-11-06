from enum import Enum


class SortOption(Enum):
    NEWEST = "newest"
    VOTES = "votes"
    SERVERS = "servers"
    MEMBERS = "members"
    BUMPED = "bumped"

    @classmethod
    def from_string(cls, value: str) -> "SortOption":
        try:
            return cls(value.lower())
        except ValueError:
            return cls.NEWEST

    def __str__(self) -> str:
        return self.value
