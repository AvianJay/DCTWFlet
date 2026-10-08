from enum import Enum


class SortOption(Enum):
    """Sort options, mirroring the ones offered on dctw.xyz.

    The values match the website's ``?sort=`` query parameter so both
    applications order the lists in exactly the same way.
    """

    DEFAULT = "default"
    MOST_VOTES = "mostVotes"
    MOST_SERVERS = "mostServers"
    MOST_MEMBERS = "mostMembers"
    MOST_ACTIVE = "mostActive"

    @classmethod
    def from_string(cls, value: str) -> "SortOption":
        if not value:
            return cls.DEFAULT

        normalized = value.strip().lower()

        for option in cls:
            if option.value.lower() == normalized:
                return option

        # Values used by older versions of the app.
        legacy = {
            "newest": cls.DEFAULT,
            "votes": cls.MOST_VOTES,
            "servers": cls.MOST_SERVERS,
            "members": cls.MOST_MEMBERS,
            "bumped": cls.MOST_ACTIVE,
        }

        return legacy.get(normalized, cls.DEFAULT)

    @property
    def is_default(self) -> bool:
        return self is SortOption.DEFAULT

    def __str__(self) -> str:
        return self.value
