from domain.shared import ValueObject, InvalidArgumentException


class Statistics(ValueObject):
    def __init__(self, votes: int = 0, count: int = 0):
        """
        Args:
            votes: Number of votes
            count: Count (number of servers in the bot or number of members in the server)
        """

        if votes < 0:
            raise InvalidArgumentException("votes", "Votes cannot be negative")
        if count < 0:
            raise InvalidArgumentException("count", "Count cannot be negative")

        self._votes = votes
        self._count = count

    @property
    def votes(self) -> int:
        return self._votes

    @property
    def count(self) -> int:
        """General count (number of servers or number of members)"""
        return self._count

    @property
    def servers(self) -> int:
        """Server count (used by Bot)"""
        return self._count

    @property
    def members(self) -> int:
        """Member count (used by Server)"""
        return self._count

    def _equality_components(self) -> tuple:
        return (self._votes, self._count)

    def with_votes(self, votes: int) -> "Statistics":
        """Create a new statistics object and modify the vote count."""
        return Statistics(votes, self._count)

    def with_count(self, count: int) -> "Statistics":
        """Create a new statistics object and modify the count."""
        return Statistics(self._votes, count)
