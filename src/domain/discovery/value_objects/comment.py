"""Comment value object"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


# DCTW stores its timestamps without a timezone offset in UTC+8 (Taipei).
DCTW_TIMEZONE = timezone(timedelta(hours=8))


@dataclass(frozen=True)
class Comment:
    """A single user review of a bot, server or template.

    The DCTW website shows these in the "使用者評論" tab of every detail
    page. ``stars`` is the 1-5 rating the reviewer gave and ``content`` may
    be empty when only the rating was submitted.
    """

    user_id: str
    stars: int
    content: str
    created_at: datetime
    edited: bool = False

    @property
    def local_created_at(self) -> datetime:
        """Creation time in the timezone the DCTW website displays."""
        return self.created_at.astimezone(DCTW_TIMEZONE)

