"""Memory cache manager"""

from typing import Optional, Any, Dict
from datetime import datetime, timedelta
from dataclasses import dataclass
from .cache_manager import CacheManager


@dataclass
class CacheEntry:
    """Cache entries"""

    value: Any
    expires_at: datetime


class MemoryCacheManager(CacheManager):
    """Memory Cache Manager"""

    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}

    async def get(self, key: str) -> Optional[Any]:
        """Get cache"""
        if key not in self._cache:
            return None

        entry = self._cache[key]
        if datetime.now() > entry.expires_at:
            del self._cache[key]
            return None

        return entry.value

    async def set(self, key: str, value: Any, ttl: int = 60) -> None:
        """Set cache"""
        expires_at = datetime.now() + timedelta(seconds=ttl)
        self._cache[key] = CacheEntry(value=value, expires_at=expires_at)

    async def delete(self, key: str) -> None:
        """Delete cache"""
        if key in self._cache:
            del self._cache[key]

    async def clear(self) -> None:
        """Clear all cache"""
        self._cache.clear()

    async def exists(self, key: str) -> bool:
        """Check if the cache exists"""
        if key not in self._cache:
            return False

        entry = self._cache[key]
        if datetime.now() > entry.expires_at:
            del self._cache[key]
            return False

        return True

    def cleanup_expired(self) -> None:
        """Clean up expired cache"""
        now = datetime.now()
        expired_keys = [
            key for key, entry in self._cache.items() if now > entry.expires_at
        ]
        for key in expired_keys:
            del self._cache[key]
