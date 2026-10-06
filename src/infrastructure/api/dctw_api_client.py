"""DCTW API client (API v2)"""

from typing import List, Dict, Any, Optional
import logging
import httpx

from domain.preferences.value_objects import ApiKey
from infrastructure.filesystem import ConfigStorage
from ..config.constants import DCTW_API_BASE_URL, DCTW_API_VERSION_PREFIX
from .http_client import AsyncHttpClient

logger = logging.getLogger(__name__)


class DctwApiError(Exception):
    """Base error for DCTW API failures"""


class ApiKeyMissingError(DctwApiError):
    """Raised when an API request needs a key but none is configured"""


class InvalidApiKeyError(DctwApiError):
    """Raised when the DCTW API rejects the configured API key"""


class DctwApiClient:
    """DCTW API v2 client.

    All API v2 endpoints require an API key sent as a Bearer token.
    Users get their key by logging in with Discord on https://dctw.xyz
    and copying it from the dashboard.
    """

    DEFAULT_BASE_URL = DCTW_API_BASE_URL
    DEFAULT_API_PREFIX = DCTW_API_VERSION_PREFIX
    MAX_PAGES = 50

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        api_prefix: Optional[str] = None,
        user_agent: str = "DCTWFlet/0.1.0",
        config_storage: Optional[ConfigStorage] = None,
    ):
        self._default_api_key = ApiKey.normalize(api_key)
        self._base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self._api_prefix = self._normalize_path_prefix(
            api_prefix or self.DEFAULT_API_PREFIX
        )
        self._user_agent = user_agent
        self._config_storage = config_storage

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def api_prefix(self) -> str:
        return self._api_prefix

    async def get_bots(self) -> List[Dict[str, Any]]:
        """Get all bots."""
        logger.info("Fetching bots from DCTW API")
        return await self._get_collection("/bots/")

    async def get_bot_comments(self, bot_id: int) -> List[Dict[str, Any]]:
        """Get bot comments."""
        logger.info(f"Fetching comments for bot {bot_id}")
        return await self._get_collection(f"/bots/{bot_id}/comments/")

    async def get_servers(self) -> List[Dict[str, Any]]:
        """Get all servers."""
        logger.info("Fetching servers from DCTW API")
        return await self._get_collection("/servers/")

    async def get_server_comments(self, server_id: int) -> List[Dict[str, Any]]:
        """Get server comments."""
        logger.info(f"Fetching comments for server {server_id}")
        return await self._get_collection(f"/servers/{server_id}/comments/")

    async def get_templates(self) -> List[Dict[str, Any]]:
        """Get all templates."""
        logger.info("Fetching templates from DCTW API")
        return await self._get_collection("/templates/")

    async def get_template_comments(self, template_id: int) -> List[Dict[str, Any]]:
        """Get template comments."""
        logger.info(f"Fetching comments for template {template_id}")
        return await self._get_collection(f"/templates/{template_id}/comments/")

    async def validate_api_key(self, api_key: Optional[str]) -> bool:
        """Check whether the DCTW API accepts the given API key."""
        key = ApiKey.normalize(api_key)
        if not key:
            return False

        try:
            async with AsyncHttpClient(
                self._base_url, headers=self._build_headers(key)
            ) as client:
                await client.get(self._resolve_endpoint("/bots/"))
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                logger.info("API key validation rejected with %s", e.response.status_code)
                return False
            raise

    async def post(
        self,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """POST to an authenticated DCTW endpoint."""
        api_key = await self._require_api_key()
        resolved_endpoint = self._resolve_endpoint(endpoint)

        async with AsyncHttpClient(
            self._base_url, headers=self._build_headers(api_key)
        ) as client:
            return await self._request(
                client, "POST", resolved_endpoint, json=json, data=data
            )

    async def _get_collection(self, endpoint: str) -> List[Dict[str, Any]]:
        api_key = await self._require_api_key()
        items: List[Dict[str, Any]] = []
        cursor: Optional[str] = None

        async with AsyncHttpClient(
            self._base_url, headers=self._build_headers(api_key)
        ) as client:
            for _ in range(self.MAX_PAGES):
                params: Optional[Dict[str, Any]] = {"cursor": cursor} if cursor else None
                response = await self._request(
                    client, "GET", self._resolve_endpoint(endpoint), params=params
                )
                items.extend(self._extract_items(response))

                cursor = self._extract_cursor(response)
                if not cursor:
                    break

        return items

    async def _request(self, client: AsyncHttpClient, method: str, endpoint: str, **kwargs):
        """Send a request and translate auth failures into domain errors."""
        try:
            if method == "GET":
                return await client.get(endpoint, **kwargs)
            if method == "POST":
                return await client.post(endpoint, **kwargs)
            raise ValueError(f"Unsupported method: {method}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                raise InvalidApiKeyError(
                    "DCTW API Key 無效或已失效，請重新登入取得新的 API Key。"
                ) from e
            raise

    async def _require_api_key(self) -> str:
        api_key = await self._load_runtime_api_key()
        if not api_key:
            raise ApiKeyMissingError(
                "尚未設定 DCTW API Key，請使用 Discord 登入取得 API Key。"
            )
        return api_key

    def _build_headers(self, api_key: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": self._user_agent,
        }

    async def _load_runtime_api_key(self) -> Optional[str]:
        if self._config_storage is not None:
            try:
                config_data = await self._config_storage.load()
                api_key = ApiKey.normalize(config_data.get("apikey"))
                if api_key:
                    return api_key
                return None
            except Exception as e:
                logger.warning(f"Failed to load API key from config storage: {e}")

        return self._default_api_key

    def _resolve_endpoint(self, endpoint: str) -> str:
        normalized_endpoint = self._normalize_path_prefix(endpoint)
        if normalized_endpoint.startswith(f"{self._api_prefix}/"):
            return normalized_endpoint
        if normalized_endpoint == self._api_prefix:
            return normalized_endpoint
        return f"{self._api_prefix}{normalized_endpoint}"

    @staticmethod
    def _extract_items(response: Any) -> List[Dict[str, Any]]:
        if isinstance(response, dict):
            if isinstance(response.get("items"), list):
                return response["items"]
            if isinstance(response.get("data"), list):
                return response["data"]
            return []

        if isinstance(response, list):
            return response

        return []

    @staticmethod
    def _extract_cursor(response: Any) -> Optional[str]:
        if isinstance(response, dict):
            for key in ("next_cursor", "next", "cursor"):
                value = response.get(key)
                if isinstance(value, str) and value:
                    return value
        return None

    @staticmethod
    def _normalize_path_prefix(value: str) -> str:
        stripped = (value or "").strip("/")
        if not stripped:
            return ""
        return f"/{stripped}"
