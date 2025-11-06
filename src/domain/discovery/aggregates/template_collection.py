from typing import List, Optional
from datetime import datetime, timedelta
from domain.shared import AggregateRoot, DomainEvent
from ..entities import Template
from ..value_objects import FilterCriteria, SortOption


class TemplatesLoadedEvent(DomainEvent):
    """Templates loaded event"""

    def __init__(self, count: int):
        super().__init__()
        self.count = count


class TemplateCollection(AggregateRoot):
    """collection aggregate root"""

    def __init__(self, cache_ttl: timedelta = timedelta(seconds=60)):
        super().__init__()
        self._templates: List[Template] = []
        self._last_updated: Optional[datetime] = None
        self._cache_ttl = cache_ttl

    @property
    def templates(self) -> List[Template]:
        """Get allTemplates"""
        return self._templates.copy()

    @property
    def count(self) -> int:
        """Template count"""
        return len(self._templates)

    @property
    def last_updated(self) -> Optional[datetime]:
        """Last update time"""
        return self._last_updated

    def load(self, templates: List[Template]) -> None:
        """Load list"""
        self._templates = templates
        self._last_updated = datetime.now()
        self.add_domain_event(TemplatesLoadedEvent(len(templates)))

    def filter_by(self, criteria: FilterCriteria) -> List[Template]:
        """Filter according to conditions"""
        return [t for t in self._templates if t.matches_filter(criteria)]

    def sort_by(self, templates: List[Template], option: SortOption) -> List[Template]:
        """Sort"""
        if option == SortOption.NEWEST:
            return sorted(
                templates, key=lambda t: t.timestamps.created_at, reverse=True
            )
        elif option == SortOption.VOTES:
            return sorted(templates, key=lambda t: t.statistics.votes, reverse=True)
        elif option == SortOption.BUMPED:
            return sorted(templates, key=lambda t: t.timestamps.bumped_at, reverse=True)
        return templates

    def find_by_id(self, template_id: int) -> Optional[Template]:
        """Find Template by ID"""
        return next((t for t in self._templates if t.id == template_id), None)

    def is_stale(self) -> bool:
        """Check if the data is expired"""
        if not self._last_updated:
            return True
        return datetime.now() - self._last_updated > self._cache_ttl

    def clear(self) -> None:
        """Clear data"""
        self._templates = []
        self._last_updated = None
