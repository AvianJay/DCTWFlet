"""Bot entity"""

from typing import List, Optional
from dataclasses import dataclass
from domain.shared import Entity
from ..value_objects import (
    Tag,
    BotTag,
    FilterCriteria,
    ContentStatus,
    Statistics,
    Timestamps,
    AvatarUrl,
    BannerUrl,
    InviteUrl,
)


@dataclass(frozen=True)
class BotLinks:
    """Bot links collection"""

    invite: InviteUrl
    support_server: Optional[str] = None
    website: Optional[str] = None


class Bot(Entity[int]):
    """Discord Bot entity"""

    def __init__(
        self,
        id: int,
        name: str,
        avatar: AvatarUrl,
        description: str,
        introduce: str,
        status: ContentStatus,
        verified: bool,
        is_partnered: bool,
        nsfw: bool,
        statistics: Statistics,
        tags: List[BotTag],
        links: BotLinks,
        timestamps: Timestamps,
        banner: Optional[BannerUrl] = None,
    ):
        super().__init__(id)
        self._validate_name(name)
        self._name = name
        self._avatar = avatar
        self._banner = banner
        self._description = description
        self._introduce = introduce
        self._status = status
        self._verified = verified
        self._is_partnered = is_partnered
        self._nsfw = nsfw
        self._statistics = statistics
        self._tags = tags
        self._links = links
        self._timestamps = timestamps

    @property
    def name(self) -> str:
        return self._name

    @property
    def avatar(self) -> AvatarUrl:
        return self._avatar

    @property
    def banner(self) -> Optional[BannerUrl]:
        return self._banner

    @property
    def description(self) -> str:
        return self._description

    @property
    def introduce(self) -> str:
        return self._introduce

    @property
    def status(self) -> ContentStatus:
        return self._status

    @property
    def verified(self) -> bool:
        return self._verified

    @property
    def is_partnered(self) -> bool:
        return self._is_partnered

    @property
    def nsfw(self) -> bool:
        return self._nsfw

    @property
    def statistics(self) -> Statistics:
        return self._statistics

    @property
    def tags(self) -> List[BotTag]:
        return self._tags.copy()

    @property
    def links(self) -> BotLinks:
        return self._links

    @property
    def timestamps(self) -> Timestamps:
        return self._timestamps

    @property
    def is_online(self) -> bool:
        """Are you online?"""
        return self._status.is_online

    @property
    def is_available(self) -> bool:
        """Is it available?"""
        return self._status.is_available

    def matches_filter(self, criteria: FilterCriteria) -> bool:
        """Check if the filter conditions are matched."""
        # NSFW過濾
        if self._nsfw and not criteria.nsfw_enabled:
            return False

        if criteria.has_tag_filter:
            tag_names = {tag.name for tag in self._tags}
            criteria_tag_names = {tag.name for tag in criteria.tags}
            if not tag_names.intersection(criteria_tag_names):
                return False

        if criteria.has_search_filter:
            search_lower = criteria.search_text.lower()
            if (
                search_lower not in self._name.lower()
                and search_lower not in self._description.lower()
            ):
                return False

        return True

    def has_tag(self, tag: Tag) -> bool:
        """Does it contain the specified tag?"""
        return tag in self._tags

    def _validate_name(self, name: str):
        if not name or len(name.strip()) == 0:
            raise ValueError("Bot name cannot be empty")
