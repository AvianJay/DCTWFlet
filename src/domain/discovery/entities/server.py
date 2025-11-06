"""Server entity"""

from typing import List, Optional
from dataclasses import dataclass
from domain.shared import Entity
from ..value_objects import (
    Tag,
    ServerTag,
    FilterCriteria,
    Statistics,
    Timestamps,
    AvatarUrl,
    BannerUrl,
    InviteUrl,
)


@dataclass(frozen=True)
class ServerLinks:
    """Server links collection"""

    invite: InviteUrl


class Server(Entity[int]):
    """Discord Server entity"""

    def __init__(
        self,
        id: int,
        name: str,
        icon: AvatarUrl,
        description: str,
        introduce: str,
        is_partnered: bool,
        nsfw: bool,
        statistics: Statistics,
        tags: List[ServerTag],
        links: ServerLinks,
        timestamps: Timestamps,
        banner: Optional[BannerUrl] = None,
    ):
        super().__init__(id)
        self._validate_name(name)
        self._name = name
        self._icon = icon
        self._banner = banner
        self._description = description
        self._introduce = introduce
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
    def icon(self) -> AvatarUrl:
        return self._icon

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
    def is_partnered(self) -> bool:
        return self._is_partnered

    @property
    def nsfw(self) -> bool:
        return self._nsfw

    @property
    def statistics(self) -> Statistics:
        return self._statistics

    @property
    def tags(self) -> List[ServerTag]:
        return self._tags.copy()

    @property
    def links(self) -> ServerLinks:
        return self._links

    @property
    def timestamps(self) -> Timestamps:
        return self._timestamps

    def matches_filter(self, criteria: FilterCriteria) -> bool:
        """Check if the filter conditions are matched."""
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
            raise ValueError("Server name cannot be empty")
