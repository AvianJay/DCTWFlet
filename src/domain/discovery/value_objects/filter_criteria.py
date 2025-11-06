from typing import List, Optional
from domain.shared import ValueObject
from .tag import Tag


class FilterCriteria(ValueObject):
    def __init__(
        self,
        tags: Optional[List[Tag]] = None,
        nsfw_enabled: bool = False,
        search_text: Optional[str] = None,
    ):
        self._tags = tags or []
        self._nsfw_enabled = nsfw_enabled
        self._search_text = search_text

    @property
    def tags(self) -> List[Tag]:
        return self._tags.copy()

    @property
    def nsfw_enabled(self) -> bool:
        return self._nsfw_enabled

    @property
    def search_text(self) -> Optional[str]:
        return self._search_text

    @property
    def has_tag_filter(self) -> bool:
        return len(self._tags) > 0

    @property
    def has_search_filter(self) -> bool:
        return self._search_text is not None and len(self._search_text.strip()) > 0

    def _equality_components(self) -> tuple:
        return (tuple(self._tags), self._nsfw_enabled, self._search_text)

    def with_tags(self, tags: List[Tag]) -> "FilterCriteria":
        """Create new filter conditions and modify labels."""
        return FilterCriteria(tags, self._nsfw_enabled, self._search_text)

    def with_nsfw(self, enabled: bool) -> "FilterCriteria":
        """Create new filter criteria with modified NSFW"""
        return FilterCriteria(self._tags, enabled, self._search_text)

    def with_search_text(self, text: str) -> "FilterCriteria":
        """Create new filter criteria and modify the search text."""
        return FilterCriteria(self._tags, self._nsfw_enabled, text)
