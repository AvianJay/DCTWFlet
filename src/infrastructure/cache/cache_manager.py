"""Cache manager interface"""

from abc import ABC, abstractmethod
from typing import Optional, Any


class CacheManager(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get cache"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 60) -> None:
        """Set cache

        Args:
            key: Cache key
            value: Cache value
            ttl: Expiration time (seconds)
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete cache"""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if the cache exists"""
        pass
