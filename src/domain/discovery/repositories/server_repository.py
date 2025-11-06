"""Server repository interface"""

from abc import ABC, abstractmethod
from typing import List, Optional
from ..entities import Server


class ServerRepository(ABC):
    """Server repository interface"""

    @abstractmethod
    async def find_all(self) -> List[Server]:
        """Get allServers"""
        pass

    @abstractmethod
    async def find_by_id(self, server_id: int) -> Optional[Server]:
        """Find Server by ID"""
        pass

    @abstractmethod
    async def clear_cache(self) -> None:
        """Clear cache"""
        pass
