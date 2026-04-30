"""Image server"""

import asyncio
import json
import logging
import mimetypes
import random
import socket
from contextlib import suppress
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import unquote, urlparse

from .image_cache import ImageCache
from ..api.http_client import AsyncHttpClient

logger = logging.getLogger(__name__)


class ImageServer:
    """Async local image caching server."""

    def __init__(
        self,
        cache_dir: Path,
        port_range: tuple[int, int] = (10000, 60000),
    ):
        self.cache = ImageCache(cache_dir)
        self.port_range = port_range
        self._port: Optional[int] = None
        self._server: Optional[asyncio.Server] = None
        self._url_mapping: Dict[str, str] = {}
        self._download_locks: Dict[str, asyncio.Lock] = {}

    async def _send_response(
        self,
        writer: asyncio.StreamWriter,
        status: int,
        reason: str,
        body: bytes,
        content_type: str = "text/plain; charset=utf-8",
    ) -> None:
        headers = [
            f"HTTP/1.1 {status} {reason}",
            f"Content-Length: {len(body)}",
            f"Content-Type: {content_type}",
            "Connection: close",
            "",
            "",
        ]
        writer.write("\r\n".join(headers).encode("iso-8859-1") + body)
        await writer.drain()

    def _get_content_type(self, url: str) -> str:
        content_type, _ = mimetypes.guess_type(urlparse(url).path)
        return content_type or "application/octet-stream"

    async def _get_image_bytes(self, url: str) -> bytes:
        cached = self.cache.load(url)
        if cached is not None:
            return cached

        lock = self._download_locks.setdefault(url, asyncio.Lock())
        async with lock:
            cached = self.cache.load(url)
            if cached is not None:
                return cached

            async with AsyncHttpClient(base_url="") as client:
                data = await client.download(url)
            self.cache.save(url, data)
            return data

    async def _serve_image(
        self, image_id: str, writer: asyncio.StreamWriter
    ) -> None:
        url = self._url_mapping.get(image_id)
        if not url:
            await self._send_response(writer, 404, "Not Found", b"Not Found")
            return

        try:
            data = await self._get_image_bytes(url)
        except Exception:
            logger.exception("Failed to serve image %s", url)
            await self._send_response(
                writer,
                500,
                "Internal Server Error",
                b"Internal Server Error",
            )
            return

        await self._send_response(
            writer,
            200,
            "OK",
            data,
            content_type=self._get_content_type(url),
        )

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            request_line = await reader.readline()
            if not request_line:
                return

            try:
                method, target, _version = (
                    request_line.decode("iso-8859-1").strip().split()
                )
            except ValueError:
                await self._send_response(
                    writer, 400, "Bad Request", b"Bad Request"
                )
                return

            while True:
                header_line = await reader.readline()
                if not header_line or header_line in (b"\r\n", b"\n"):
                    break

            if method != "GET":
                await self._send_response(
                    writer, 405, "Method Not Allowed", b"Method Not Allowed"
                )
                return

            path = urlparse(target).path
            if path == "/health":
                body = json.dumps({"status": "ok", "port": self._port}).encode(
                    "utf-8"
                )
                await self._send_response(
                    writer,
                    200,
                    "OK",
                    body,
                    content_type="application/json; charset=utf-8",
                )
                return

            if path.startswith("/image/"):
                await self._serve_image(unquote(path.removeprefix("/image/")), writer)
                return

            await self._send_response(writer, 404, "Not Found", b"Not Found")
        except Exception:
            logger.exception("Unhandled error while serving local image request")
            with suppress(Exception):
                await self._send_response(
                    writer,
                    500,
                    "Internal Server Error",
                    b"Internal Server Error",
                )
        finally:
            writer.close()
            with suppress(Exception):
                await writer.wait_closed()

    def register_image(self, url: str) -> str:
        image_id = str(random.randint(100000, 999999))
        while image_id in self._url_mapping:
            image_id = str(random.randint(100000, 999999))

        self._url_mapping[image_id] = url
        return image_id

    def get_image_url(self, image_id: str) -> str:
        if self._port is None:
            return self._url_mapping.get(image_id, "")
        return f"http://127.0.0.1:{self._port}/image/{image_id}"

    def _find_available_port(self) -> int:
        for _ in range(10):
            port = random.randint(*self.port_range)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
                try:
                    server_socket.bind(("127.0.0.1", port))
                    return port
                except OSError:
                    continue

        raise RuntimeError("No available port found")

    async def start(self):
        if self._server is not None:
            return

        self._port = self._find_available_port()
        self._server = await asyncio.start_server(
            self._handle_client,
            host="127.0.0.1",
            port=self._port,
        )
        logger.info("Starting image server on port %s", self._port)
        await self._server.serve_forever()

    @property
    def port(self) -> Optional[int]:
        return self._port

    @property
    def is_running(self) -> bool:
        return self._server is not None
