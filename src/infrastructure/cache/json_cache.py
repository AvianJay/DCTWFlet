"""JSON cache manager"""

import json
import aiofiles
from pathlib import Path
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
from .cache_manager import CacheManager


class JsonCacheManager(CacheManager):
    """JSON file-based cache manager"""

    def __init__(self, cache_file: Path):
        self._cache_file = cache_file
        self._cache: Dict[str, dict] = {}
        self._loaded = False

    async def _load(self) -> None:
        """Load cache file"""
        if self._loaded:
            return

        if not self._cache_file.exists():
            self._cache = {}
            self._loaded = True
            return

        try:
            async with aiofiles.open(self._cache_file, "r", encoding="utf-8") as f:
                content = await f.read()
                self._cache = json.loads(content)
            self._loaded = True
        except Exception:
            self._cache = {}
            self._loaded = True

    async def _save(self) -> None:
        """Save cache files"""
        self._cache_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            async with aiofiles.open(self._cache_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(self._cache, indent=2, ensure_ascii=False))
        except Exception:
            pass

    async def get(self, key: str) -> Optional[Any]:
        """Get cache"""
        await self._load()

        if key not in self._cache:
            return None

        entry = self._cache[key]
        expires_at = datetime.fromisoformat(entry["expires_at"])

        if datetime.now() > expires_at:
            del self._cache[key]
            await self._save()
            return None

        return entry["value"]

    async def set(self, key: str, value: Any, ttl: int = 60) -> None:
        """Set cache"""
        await self._load()

        expires_at = datetime.now() + timedelta(seconds=ttl)
        self._cache[key] = {
            "value": value,
            "expires_at": expires_at.isoformat(),
        }

        await self._save()

    async def delete(self, key: str) -> None:
        """Delete cache"""
        await self._load()

        if key in self._cache:
            del self._cache[key]
            await self._save()

    async def clear(self) -> None:
        """Clear all cache"""
        self._cache = {}
        self._loaded = True
        await self._save()

    async def exists(self, key: str) -> bool:
        """Check if the cache exists"""
        value = await self.get(key)
        return value is not None
