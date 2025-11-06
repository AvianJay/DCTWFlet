"""DCTW API client"""

from typing import List, Dict, Any, Optional
import logging
from .http_client import AsyncHttpClient

logger = logging.getLogger(__name__)


class DctwApiClient:
    """DCTW API client"""

    DEFAULT_BASE_URL = "https://dctw.nyanko.host/api/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = None,
        user_agent: str = "DCTWFlet/0.1.0",
    ):
        self._base_url = base_url or self.DEFAULT_BASE_URL
        self._api_key = api_key
        self._user_agent = user_agent

    def _get_headers(self) -> Dict[str, str]:
        headers = {"User-Agent": self._user_agent}
        if self._api_key:
            headers["x-api-key"] = self._api_key
        return headers

    async def get_bots(self) -> List[Dict[str, Any]]:
        """Get allBots"""
        logger.info("Fetching bots from DCTW API")
        async with AsyncHttpClient(
            self._base_url, headers=self._get_headers()
        ) as client:
            response = await client.get("/bots")
            if isinstance(response, dict) and "data" in response:

                return response["data"] if isinstance(response["data"], list) else []

            return response if isinstance(response, list) else []

    async def get_bot_comments(self, bot_id: int) -> List[Dict[str, Any]]:
        """Get Bot comments"""
        logger.info(f"Fetching comments for bot {bot_id}")
        async with AsyncHttpClient(
            self._base_url, headers=self._get_headers()
        ) as client:
            data = await client.get(f"/bots/{bot_id}/comments")
            return data if isinstance(data, list) else []

    async def get_servers(self) -> List[Dict[str, Any]]:
        """Get allServers"""
        logger.info("Fetching servers from DCTW API")
        async with AsyncHttpClient(
            self._base_url, headers=self._get_headers()
        ) as client:
            response = await client.get("/servers")

            if isinstance(response, dict) and "data" in response:

                return response["data"] if isinstance(response["data"], list) else []

            return response if isinstance(response, list) else []

    async def get_server_comments(self, server_id: int) -> List[Dict[str, Any]]:
        """Get Server comments"""
        logger.info(f"Fetching comments for server {server_id}")
        async with AsyncHttpClient(
            self._base_url, headers=self._get_headers()
        ) as client:
            data = await client.get(f"/servers/{server_id}/comments")
            return data if isinstance(data, list) else []

    async def get_templates(self) -> List[Dict[str, Any]]:
        """Get allTemplates"""
        logger.info("Fetching templates from DCTW API")
        async with AsyncHttpClient(
            self._base_url, headers=self._get_headers()
        ) as client:
            response = await client.get("/templates")

            # API returns {"data": [...], "count": ..., "last_updated": ...}

            if isinstance(response, dict) and "data" in response:

                return response["data"] if isinstance(response["data"], list) else []

            return response if isinstance(response, list) else []

    async def get_template_comments(self, template_id: int) -> List[Dict[str, Any]]:
        """Get Template comments"""
        logger.info(f"Fetching comments for template {template_id}")
        async with AsyncHttpClient(
            self._base_url, headers=self._get_headers()
        ) as client:
            data = await client.get(f"/templates/{template_id}/comments")
            return data if isinstance(data, list) else []
