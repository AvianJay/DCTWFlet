"""Async HTTP client"""

import httpx
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class AsyncHttpClient:
    """Async HTTP client based on httpx"""

    def __init__(
        self,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._headers = headers or {}
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Asynchronous Context Manager Entry Point"""
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
            timeout=self._timeout,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Asynchronous Context Manager Export"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> dict:
        """Async GET request"""
        if not self._client:
            raise RuntimeError(
                "Client not initialized. Use 'async with' context manager"
            )

        url = f"{self._base_url}/{endpoint.lstrip('/')}"
        logger.debug(f"GET {url}")

        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

    async def post(
        self,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """Async POST request"""
        if not self._client:
            raise RuntimeError(
                "Client not initialized. Use 'async with' context manager"
            )

        url = f"{self._base_url}/{endpoint.lstrip('/')}"
        logger.debug(f"POST {url}")

        try:
            response = await self._client.post(url, json=json, data=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

    async def download(self, url: str) -> bytes:
        """Download file"""
        if not self._client:
            raise RuntimeError(
                "Client not initialized. Use 'async with' context manager"
            )

        logger.debug(f"Download {url}")

        try:
            response = await self._client.get(url)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Download error: {e}")
            raise
