"""Image cache"""

import hashlib
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ImageCache:
    """Image Cache Manager"""

    def __init__(self, cache_dir: Path):
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_path(self, url: str) -> Path:
        """Get cache file path by URL"""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self._cache_dir / url_hash

    def exists(self, url: str) -> bool:
        """Check if the image is cached."""
        cache_path = self.get_cache_path(url)
        return cache_path.exists()

    def save(self, url: str, data: bytes) -> Path:
        """Save image to cache"""
        cache_path = self.get_cache_path(url)
        try:
            cache_path.write_bytes(data)
            logger.debug(f"Saved image to cache: {cache_path}")
            return cache_path
        except Exception as e:
            logger.error(f"Failed to save image: {e}")
            raise

    def load(self, url: str) -> Optional[bytes]:
        """Load images from cache"""
        cache_path = self.get_cache_path(url)
        if not cache_path.exists():
            return None
        try:
            return cache_path.read_bytes()
        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            return None

    def clear(self) -> None:
        """Clear all cached images"""
        for file in self._cache_dir.glob("*"):
            try:
                file.unlink()
            except Exception as e:
                logger.error(f"Failed to delete {file}: {e}")
