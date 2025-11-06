"""Bot collection aggregate root"""

from typing import List, Optional
from datetime import datetime, timedelta
from domain.shared import AggregateRoot, DomainEvent
from ..entities import Bot
from ..value_objects import FilterCriteria, SortOption


class BotsLoadedEvent(DomainEvent):
    """Bots loaded event"""

    def __init__(self, count: int):
        super().__init__()
        self.count = count


class BotCollection(AggregateRoot):
    """collection aggregate root"""

    def __init__(self, cache_ttl: timedelta = timedelta(seconds=60)):
        super().__init__()
        self._bots: List[Bot] = []
        self._last_updated: Optional[datetime] = None
        self._cache_ttl = cache_ttl

    @property
    def bots(self) -> List[Bot]:
        """Get allBots"""
        return self._bots.copy()

    @property
    def count(self) -> int:
        """Bot count"""
        return len(self._bots)

    @property
    def last_updated(self) -> Optional[datetime]:
        """Last update time"""
        return self._last_updated

    def load(self, bots: List[Bot]) -> None:
        """Load list"""
        self._bots = bots
        self._last_updated = datetime.now()
        self.add_domain_event(BotsLoadedEvent(len(bots)))

    def filter_by(self, criteria: FilterCriteria) -> List[Bot]:
        """Filter according to conditions"""
        return [bot for bot in self._bots if bot.matches_filter(criteria)]

    def sort_by(self, bots: List[Bot], option: SortOption) -> List[Bot]:
        """Sort"""
        if option == SortOption.NEWEST:
            return sorted(bots, key=lambda b: b.timestamps.created_at, reverse=True)
        elif option == SortOption.VOTES:
            return sorted(bots, key=lambda b: b.statistics.votes, reverse=True)
        elif option == SortOption.SERVERS:
            return sorted(bots, key=lambda b: b.statistics.servers, reverse=True)
        elif option == SortOption.BUMPED:
            return sorted(bots, key=lambda b: b.timestamps.bumped_at, reverse=True)
        return bots

    def find_by_id(self, bot_id: int) -> Optional[Bot]:
        """Find Bot by ID"""
        return next((bot for bot in self._bots if bot.id == bot_id), None)

    def is_stale(self) -> bool:
        """Check if the data is expired"""
        if not self._last_updated:
            return True
        return datetime.now() - self._last_updated > self._cache_ttl

    def clear(self) -> None:
        """Clear data"""
        self._bots = []
        self._last_updated = None
