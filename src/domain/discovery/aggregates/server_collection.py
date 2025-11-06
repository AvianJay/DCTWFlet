"""Server collection aggregate root"""

from typing import List, Optional
from datetime import datetime, timedelta
from domain.shared import AggregateRoot, DomainEvent
from ..entities import Server
from ..value_objects import FilterCriteria, SortOption


class ServersLoadedEvent(DomainEvent):
    """Servers loaded event"""

    def __init__(self, count: int):
        super().__init__()
        self.count = count


class ServerCollection(AggregateRoot):
    """collection aggregate root"""

    def __init__(self, cache_ttl: timedelta = timedelta(seconds=60)):
        super().__init__()
        self._servers: List[Server] = []
        self._last_updated: Optional[datetime] = None
        self._cache_ttl = cache_ttl

    @property
    def servers(self) -> List[Server]:
        """Get allServers"""
        return self._servers.copy()

    @property
    def count(self) -> int:
        """Server count"""
        return len(self._servers)

    @property
    def last_updated(self) -> Optional[datetime]:
        """Last update time"""
        return self._last_updated

    def load(self, servers: List[Server]) -> None:
        """Load list"""
        self._servers = servers
        self._last_updated = datetime.now()
        self.add_domain_event(ServersLoadedEvent(len(servers)))

    def filter_by(self, criteria: FilterCriteria) -> List[Server]:
        """Filter according to conditions"""
        return [server for server in self._servers if server.matches_filter(criteria)]

    def sort_by(self, servers: List[Server], option: SortOption) -> List[Server]:
        """Sort"""
        if option == SortOption.NEWEST:
            return sorted(servers, key=lambda s: s.timestamps.created_at, reverse=True)
        elif option == SortOption.VOTES:
            return sorted(servers, key=lambda s: s.statistics.votes, reverse=True)
        elif option == SortOption.MEMBERS:
            return sorted(servers, key=lambda s: s.statistics.members, reverse=True)
        elif option == SortOption.BUMPED:
            return sorted(servers, key=lambda s: s.timestamps.bumped_at, reverse=True)
        return servers

    def find_by_id(self, server_id: int) -> Optional[Server]:
        """Find Server by ID"""
        return next((s for s in self._servers if s.id == server_id), None)

    def is_stale(self) -> bool:
        """Check if the data is expired"""
        if not self._last_updated:
            return True
        return datetime.now() - self._last_updated > self._cache_ttl

    def clear(self) -> None:
        """Clear data"""
        self._servers = []
        self._last_updated = None
