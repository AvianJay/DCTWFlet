"""DCTW API client (API v2)"""

from typing import List, Dict, Any, Optional
import json
import logging
import re
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

    # Server action used by the official website to resolve Discord user ids
    # (bot authors) to their public profile.
    GET_USERS_ACTION = "40d2eecba887e6edbe579ce1858b12b97b66aa318d"

    # Server action used by the official website to read a single bot record
    # (the public API does not expose the partner flag).
    GET_BOT_ACTION = "601cebfbdd90674fa83db025737892d230455e1ffb"
    BOT_DETAIL_FIELDS = ["id", "partner", "slash", "author", "devs"]

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

    async def get_bot(self, bot_id: int) -> Optional[Dict[str, Any]]:
        """Get a single bot by ID. Returns None when the API answers 404."""
        return await self._get_item(f"/bots/{bot_id}/")

    async def get_user_profiles(
        self, user_ids: List[str], page_bot_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Resolve Discord user ids to their public profile.

        The public API only exposes author ids, so the names and avatars are
        read from the same server action the official website uses. Failures
        are swallowed: a bot page stays usable without the author block.
        """
        ids = [str(user_id).strip() for user_id in user_ids if str(user_id).strip()]
        if not ids:
            return []

        endpoint = f"/bots/{page_bot_id}" if page_bot_id else "/bots"
        headers = {
            "Next-Action": self.GET_USERS_ACTION,
            "Content-Type": "text/plain;charset=UTF-8",
            "Accept": "text/x-component",
            "Origin": self._base_url,
            "Referer": f"{self._base_url}{endpoint}",
        }

        try:
            async with AsyncHttpClient(
                self._base_url, headers={"User-Agent": self._user_agent}
            ) as client:
                payload = await client.post_text(
                    endpoint, json.dumps([ids]), headers=headers
                )
        except Exception as error:
            logger.warning(f"Failed to load Discord user profiles: {error}")
            return []

        return self._parse_user_profiles(payload)

    async def get_bot_flags(self, bot_id: int) -> Optional[Dict[str, Any]]:
        """Read one bot record from the official website detail page.

        Used for the fields the public API does not return (partner flag).
        """
        endpoint = f"/bots/{bot_id}"
        headers = {
            "Next-Action": self.GET_BOT_ACTION,
            "Content-Type": "text/plain;charset=UTF-8",
            "Accept": "text/x-component",
            "Origin": self._base_url,
            "Referer": f"{self._base_url}{endpoint}",
        }

        try:
            async with AsyncHttpClient(
                self._base_url, headers={"User-Agent": self._user_agent}
            ) as client:
                payload = await client.post_text(
                    endpoint,
                    json.dumps([str(bot_id), list(self.BOT_DETAIL_FIELDS)]),
                    headers=headers,
                )
        except Exception as error:
            logger.warning(f"Failed to load bot flags for {bot_id}: {error}")
            return None

        data = self._extract_action_payload(payload)
        item = data.get("item") if isinstance(data, dict) else None
        return item if isinstance(item, dict) else None

    async def get_servers(self) -> List[Dict[str, Any]]:
        """Get all servers."""
        logger.info("Fetching servers from DCTW API")
        return await self._get_collection("/servers/")

    async def get_server_comments(self, server_id: int) -> List[Dict[str, Any]]:
        """Get server comments."""
        logger.info(f"Fetching comments for server {server_id}")
        return await self._get_collection(f"/servers/{server_id}/comments/")

    async def get_server(self, server_id: int) -> Optional[Dict[str, Any]]:
        """Get a single server by ID. Returns None when the API answers 404."""
        return await self._get_item(f"/servers/{server_id}/")

    async def get_templates(self) -> List[Dict[str, Any]]:
        """Get all templates."""
        logger.info("Fetching templates from DCTW API")
        return await self._get_collection("/templates/")

    async def get_template_comments(self, template_id: int) -> List[Dict[str, Any]]:
        """Get template comments."""
        logger.info(f"Fetching comments for template {template_id}")
        return await self._get_collection(f"/templates/{template_id}/comments/")

    async def get_template(self, template_id: int) -> Optional[Dict[str, Any]]:
        """Get a single template by ID. Returns None when the API answers 404."""
        return await self._get_item(f"/templates/{template_id}/")

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

    async def _get_item(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Fetch a single resource. Returns None when the API answers 404."""
        api_key = await self._require_api_key()

        async with AsyncHttpClient(
            self._base_url, headers=self._build_headers(api_key)
        ) as client:
            try:
                response = await self._request(
                    client, "GET", self._resolve_endpoint(endpoint)
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.info(f"Resource not found: {endpoint}")
                    return None
                raise

        if isinstance(response, dict):
            data = response.get("data")
            if isinstance(data, dict):
                return data
            return response

        return None

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

    @classmethod
    def _parse_user_profiles(cls, payload: str) -> List[Dict[str, Any]]:
        """Read the profiles out of the server action response."""
        data = cls._extract_action_payload(payload)
        if not isinstance(data, list):
            return []

        profiles: List[Dict[str, Any]] = []
        for item in data:
            if not isinstance(item, dict):
                continue

            user_id = str(item.get("id") or "").strip()
            if not user_id:
                continue

            name = str(item.get("global_name") or item.get("username") or "").strip()
            profiles.append(
                {
                    "id": user_id,
                    "name": name or user_id,
                    "avatar_url": cls._build_user_avatar_url(
                        user_id, item.get("avatar")
                    ),
                }
            )

        return profiles

    @staticmethod
    def _build_user_avatar_url(user_id: str, avatar_hash: Optional[str]) -> str:
        """Build the Discord avatar URL exactly like the official website."""
        if avatar_hash:
            return (
                f"https://cdn.discordapp.com/avatars/{user_id}/"
                f"{avatar_hash}.png?size=64"
            )

        try:
            index = int(user_id[-5:]) % 6
        except ValueError:
            index = 0
        return f"https://cdn.discordapp.com/embed/avatars/{index}.png"

    @staticmethod
    def _extract_action_payload(payload: str):
        """Read the JSON result out of a React flight (RSC) response body."""
        decoder = json.JSONDecoder()
        results = []

        for match in re.finditer(r"(?:^|\s)(\d+):", payload or ""):
            try:
                value, _ = decoder.raw_decode(payload, match.end())
            except ValueError:
                continue
            results.append((int(match.group(1)), value))

        if not results:
            return None

        lists = [value for _, value in results if isinstance(value, list)]
        if lists:
            return lists[-1]

        return results[-1][1]

    @staticmethod
    def _normalize_path_prefix(value: str) -> str:
        stripped = (value or "").strip("/")
        if not stripped:
            return ""
        return f"/{stripped}"
