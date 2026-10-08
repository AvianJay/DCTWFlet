"""Discord user profile shared by authors, admins and reviewers."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class UserProfile:
    """Public name and avatar of a Discord user referenced by DCTW."""

    id: str
    name: str
    avatar_url: Optional[str] = None

