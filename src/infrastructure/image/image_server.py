"""Image server"""

import random
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict
from quart import Quart, send_file, abort
from .image_cache import ImageCache
from ..api.http_client import AsyncHttpClient

logger = logging.getLogger(__name__)


class ImageServer:
    """Quart-based async image caching server"""

    def __init__(
        self,
        cache_dir: Path,
        port_range: tuple[int, int] = (10000, 60000),
    ):
        self.app = Quart(__name__)
        self.cache = ImageCache(cache_dir)
        self.port_range = port_range
        self._port: Optional[int] = None
        self._url_mapping: Dict[str, str] = {}  # id -> url
        self._setup_routes()

    def _setup_routes(self):
        """Configure routes"""

        @self.app.route("/image/<image_id>")
        async def serve_image(image_id: str):
            if image_id not in self._url_mapping:
                abort(404)

            url = self._url_mapping[image_id]

            if self.cache.exists(url):
                cache_path = self.cache.get_cache_path(url)
                return await send_file(cache_path)

            try:
                async with AsyncHttpClient(base_url="") as client:
                    data = await client.download(url)
                    cache_path = self.cache.save(url, data)
                    return await send_file(cache_path)
            except Exception as e:
                logger.error(f"Failed to download image {url}: {e}")
                abort(500)

        @self.app.route("/health")
        async def health():
            return {"status": "ok", "port": self._port}

    def register_image(self, url: str) -> str:
        image_id = str(random.randint(100000, 999999))
        while image_id in self._url_mapping:
            image_id = str(random.randint(100000, 999999))

        self._url_mapping[image_id] = url
        return image_id

    def get_image_url(self, image_id: str) -> str:
        return f"http://127.0.0.1:{self._port}/image/{image_id}"

    def _find_available_port(self) -> int:
        import socket

        for _ in range(10):
            port = random.randint(*self.port_range)
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("127.0.0.1", port))
                    return port
            except OSError:
                continue

        raise RuntimeError("No available port found")

    async def start(self):
        self._port = self._find_available_port()
        logger.info(f"Starting image server on port {self._port}")

        config = self.app.config
        config["SERVER_NAME"] = None

        await self.app.run_task(
            host="127.0.0.1",
            port=self._port,
            debug=False,
        )

    @property
    def port(self) -> Optional[int]:
        return self._port

    @property
    def is_running(self) -> bool:
        return self._port is not None
