"""Template entity"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from domain.shared import Entity
from ..value_objects import (
    Tag,
    TemplateTag,
    Comment,
    FilterCriteria,
    Statistics,
    Timestamps,
)


@dataclass(frozen=True)
class TemplateLinks:
    """Template links collection"""

    share_url: str


class Template(Entity[int]):
    """Discord Server Template entity"""

    def __init__(
        self,
        id: int,
        name: str,
        description: str,
        introduce: str,
        nsfw: bool,
        statistics: Statistics,
        tags: List[TemplateTag],
        links: TemplateLinks,
        timestamps: Timestamps,
        pinned: bool = False,
        social_links: Optional[Dict[str, str]] = None,
        author_ids: Optional[List[str]] = None,
        comments: Optional[List[Comment]] = None,
    ):
        super().__init__(id)
        self._validate_name(name)
        self._name = name
        self._description = description
        self._introduce = introduce
        self._nsfw = nsfw
        self._statistics = statistics
        self._tags = tags
        self._links = links
        self._links = links
        self._timestamps = timestamps
        self._pinned = pinned
        self._social_links = dict(social_links or {})
        self._author_ids = list(author_ids or [])
        self._comments = list(comments or [])

    @property
    def name(self) -> str:
        return self._name

    @property
    def pinned(self) -> bool:
        return self._pinned

    @property
    def description(self) -> str:
        return self._description

    @property
    def introduce(self) -> str:
        return self._introduce

    @property
    def nsfw(self) -> bool:
        return self._nsfw

    @property
    def statistics(self) -> Statistics:
        return self._statistics

    @property
    def tags(self) -> List[TemplateTag]:
        return self._tags.copy()

    @property
    def links(self) -> TemplateLinks:
        return self._links

    @property
    def social_links(self) -> Dict[str, str]:
        return dict(self._social_links)

    @property
    def author_ids(self) -> List[str]:
        return self._author_ids.copy()

    @property
    def comments(self) -> List[Comment]:
        return self._comments.copy()

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
            raise ValueError("Template name cannot be empty")
