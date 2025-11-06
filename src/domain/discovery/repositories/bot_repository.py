"""Bot repository interface"""

from abc import ABC, abstractmethod
from typing import List, Optional
from ..entities import Bot


class BotRepository(ABC):
    """Bot repository interface"""

    @abstractmethod
    async def find_all(self) -> List[Bot]:
        """Get allBots"""
        pass

    @abstractmethod
    async def find_by_id(self, bot_id: int) -> Optional[Bot]:
        """Find Bot by ID"""
        pass

    @abstractmethod
    async def clear_cache(self) -> None:
        """Clear cache"""
        pass
