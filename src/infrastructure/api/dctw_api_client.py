"""DCTW API client"""

from typing import List, Dict, Any, Optional, Tuple
import logging
import httpx

from domain.preferences.value_objects import ApiKey
from infrastructure.filesystem import ConfigStorage
from ..config.constants import (
    DCTW_API_AUTH_BASE_URL,
    DCTW_API_BASE_URL,
    DCTW_API_OPENAPI_URL,
    DCTW_API_VERSION_PREFIX,
)
from .http_client import AsyncHttpClient

logger = logging.getLogger(__name__)


class DctwApiClient:
    """DCTW API client with automatic proxy/authenticated routing."""

    DEFAULT_PROXY_BASE_URL = DCTW_API_BASE_URL
    DEFAULT_AUTH_BASE_URL = DCTW_API_AUTH_BASE_URL
    DEFAULT_API_PREFIX = DCTW_API_VERSION_PREFIX
    DEFAULT_OPENAPI_URL = DCTW_API_OPENAPI_URL
    DEFAULT_PAGE_LIMIT = 50

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        authenticated_base_url: Optional[str] = None,
        api_prefix: Optional[str] = None,
        openapi_url: Optional[str] = None,
        user_agent: str = "DCTWFlet/0.1.0",
        config_storage: Optional[ConfigStorage] = None,
    ):
        self._default_api_key = ApiKey.normalize(api_key)
        self._proxy_base_url = (base_url or self.DEFAULT_PROXY_BASE_URL).rstrip("/")
        self._authenticated_base_url = (
            authenticated_base_url or self.DEFAULT_AUTH_BASE_URL
        ).rstrip("/")
        self._api_prefix = self._normalize_path_prefix(
            api_prefix or self.DEFAULT_API_PREFIX
        )
        self._openapi_url = openapi_url or self.DEFAULT_OPENAPI_URL
        self._user_agent = user_agent
        self._config_storage = config_storage
        self._openapi_schema: Optional[Dict[str, Any]] = None
        self._page_limit_cache: Dict[str, int] = {}

    @property
    def openapi_url(self) -> str:
        return self._openapi_url

    async def get_bots(self) -> List[Dict[str, Any]]:
        """Get all bots."""
        logger.info("Fetching bots from DCTW API")
        return await self._get_paginated_collection("/bots")

    async def get_bot_comments(self, bot_id: int) -> List[Dict[str, Any]]:
        """Get bot comments."""
        logger.info(f"Fetching comments for bot {bot_id}")
        return await self._get_items(f"/bots/{bot_id}/comments")

    async def get_servers(self) -> List[Dict[str, Any]]:
        """Get all servers."""
        logger.info("Fetching servers from DCTW API")
        return await self._get_paginated_collection("/servers")

    async def get_server_comments(self, server_id: int) -> List[Dict[str, Any]]:
        """Get server comments."""
        logger.info(f"Fetching comments for server {server_id}")
        return await self._get_items(f"/servers/{server_id}/comments")

    async def get_templates(self) -> List[Dict[str, Any]]:
        """Get all templates."""
        logger.info("Fetching templates from DCTW API")
        return await self._get_paginated_collection("/templates")

    async def get_template_comments(self, template_id: int) -> List[Dict[str, Any]]:
        """Get template comments."""
        logger.info(f"Fetching comments for template {template_id}")
        return await self._get_items(f"/templates/{template_id}/comments")

    async def post(
        self,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """POST to an authenticated DCTW endpoint."""
        base_url, headers, is_authenticated = await self._resolve_request_config()
        if not is_authenticated:
            raise RuntimeError(
                "POST endpoints require a user-provided API key because the proxy only allows GET requests."
            )

        resolved_endpoint = self._resolve_endpoint(endpoint, is_authenticated)
        async with AsyncHttpClient(base_url, headers=headers) as client:
            return await client.post(resolved_endpoint, json=json, data=data)

    async def _get_paginated_collection(self, endpoint: str) -> List[Dict[str, Any]]:
        base_url, headers, is_authenticated = await self._resolve_request_config()
        resolved_endpoint = self._resolve_endpoint(endpoint, is_authenticated)
        page_limit = await self._get_page_limit(endpoint)
        items: List[Dict[str, Any]] = []
        cursor: Optional[str] = None

        async with AsyncHttpClient(base_url, headers=headers) as client:
            while True:
                params: Dict[str, Any] = {"limit": page_limit}
                if cursor:
                    params["cursor"] = cursor

                response = await client.get(resolved_endpoint, params=params)
                page_items = self._extract_items(response)
                items.extend(page_items)

                if not isinstance(response, dict):
                    break

                cursor = response.get("next_cursor")
                if not cursor:
                    break

        return items

    async def _get_items(self, endpoint: str) -> List[Dict[str, Any]]:
        base_url, headers, is_authenticated = await self._resolve_request_config()
        resolved_endpoint = self._resolve_endpoint(endpoint, is_authenticated)

        async with AsyncHttpClient(base_url, headers=headers) as client:
            response = await client.get(resolved_endpoint)
            return self._extract_items(response)

    async def _resolve_request_config(self) -> Tuple[str, Dict[str, str], bool]:
        api_key = await self._load_runtime_api_key()
        headers = {"User-Agent": self._user_agent}

        if api_key:
            headers["x-api-key"] = api_key
            return self._authenticated_base_url, headers, True

        return self._proxy_base_url, headers, False

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

    async def _get_page_limit(self, endpoint: str) -> int:
        cache_key = self._normalize_path_prefix(endpoint)
        if cache_key in self._page_limit_cache:
            return self._page_limit_cache[cache_key]

        page_limit = self.DEFAULT_PAGE_LIMIT

        try:
            schema = await self._get_openapi_schema()
            schema_path = f"{self._api_prefix}{cache_key}"
            parameters = schema.get("paths", {}).get(schema_path, {}).get("get", {}).get(
                "parameters",
                [],
            )

            for parameter in parameters:
                if parameter.get("name") != "limit":
                    continue

                parameter_schema = parameter.get("schema", {})
                page_limit = int(
                    parameter_schema.get(
                        "maximum",
                        parameter_schema.get("default", self.DEFAULT_PAGE_LIMIT),
                    )
                )
                break
        except Exception as e:
            logger.warning(
                f"Failed to load page limit from OpenAPI for {endpoint}: {e}"
            )

        self._page_limit_cache[cache_key] = page_limit
        logger.info(
            f"Resolved page limit for {cache_key or '/'} from OpenAPI: {page_limit}"
        )
        return page_limit

    async def _get_openapi_schema(self) -> Dict[str, Any]:
        if self._openapi_schema is not None:
            return self._openapi_schema

        async with httpx.AsyncClient(
            headers={"User-Agent": self._user_agent},
            timeout=30.0,
            follow_redirects=True,
        ) as client:
            response = await client.get(self._openapi_url)
            response.raise_for_status()
            self._openapi_schema = response.json()

        return self._openapi_schema

    def _resolve_endpoint(self, endpoint: str, is_authenticated: bool) -> str:
        normalized_endpoint = self._normalize_path_prefix(endpoint)
        if not is_authenticated:
            return normalized_endpoint

        if normalized_endpoint.startswith(f"{self._api_prefix}/"):
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
    def _normalize_path_prefix(value: str) -> str:
        stripped = (value or "").strip("/")
        if not stripped:
            return ""
        return f"/{stripped}"
