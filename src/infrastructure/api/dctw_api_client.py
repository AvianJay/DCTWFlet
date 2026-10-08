"""DCTW API client (API v2)"""

from typing import List, Dict, Any, Optional, Union
import json
import logging
import re
import httpx

from domain.preferences.value_objects import ApiKey
from infrastructure.filesystem import ConfigStorage
from ..config.constants import (
    DCTW_API_BASE_URL,
    DCTW_API_V2_VERSION_PREFIX,
    DCTW_API_VERSION_PREFIX,
)
from .http_client import AsyncHttpClient

logger = logging.getLogger(__name__)


class DctwApiError(Exception):
    """Base error for DCTW API failures"""


class ApiKeyMissingError(DctwApiError):
    """Raised when an API request needs a key but none is configured"""


class InvalidApiKeyError(DctwApiError):
    """Raised when the DCTW API rejects the configured API key"""


class DctwApiClient:
    """DCTW API client.

    The list and detail endpoints (API v1) answer without authentication,
    while API v2 endpoints (voting, key validation) need an API key sent as
    a Bearer token. Users copy the key from the DCTW dashboard
    (https://dctw.xyz) and paste it into the app from the clipboard.
    """

    DEFAULT_BASE_URL = DCTW_API_BASE_URL
    DEFAULT_API_PREFIX = DCTW_API_VERSION_PREFIX
    DEFAULT_API_V2_PREFIX = DCTW_API_V2_VERSION_PREFIX
    MAX_PAGES = 50

    # Server action used by the official website to resolve Discord user ids
    # (bot authors) to their public profile.
    GET_USERS_ACTION = "40d2eecba887e6edbe579ce1858b12b97b66aa318d"

    # Server action the official website uses to read the review list of an
    # item. Writing a review only works with the login session of the site
    # (an API key is rejected), so the app only reads the list.
    COMMENT_LIST_ACTIONS: Dict[str, str] = {
        "bots": "404bfb2f51e44d89bd0ccd5ebce31a4498780e1e59",
        "servers": "409de9f637fd530bbbfc1bfa7e6790c61e6eda895e",
        "templates": "4066734a6de5dc79145de79a9942369ef89eaccf4a",
    }

    # Server action used by the official website to read a single bot record
    # (the public API does not expose the partner flag).
    GET_BOT_ACTION = "601cebfbdd90674fa83db025737892d230455e1ffb"
    BOT_DETAIL_FIELDS = ["id", "partner", "slash", "author", "devs"]

    # Server action used by the official website to read the template list
    # (the public API does not expose the partner flag).
    GET_TEMPLATES_ACTION = "40f4f4dea3c8c435aad6868ff7f72e170885f61f0a"
    TEMPLATE_LIST_FIELDS = [
        "id",
        "name",
        "description",
        "introduce",
        "tags",
        "vote_count",
        "bumped_at",
        "comments",
        "partner",
        "keywords",
    ]

    # Server action used by the official website to read a single server
    # record (the public API does not expose the admin list and only the
    # single item endpoint carries the comments).
    GET_SERVER_ACTION = "604ca02ba1d5f34050d7766e8df0c30010306e7b38"
    SERVER_DETAIL_FIELDS = [
        "id",
        "avatar",
        "banner",
        "name",
        "description",
        "introduce",
        "members",
        "features",
        "tags",
        "vote_count",
        "inviteLink",
        "badge",
        "analytic",
        "viewsAnalytic",
        "gameExtension",
        "partner",
        "emojis",
        "stickers",
        "events",
        "admins",
        "screenshots",
        "author",
        "socialLinks",
        "comments",
        "onlineMembers",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        api_prefix: Optional[str] = None,
        api_v2_prefix: Optional[str] = None,
        user_agent: str = "DCTWFlet/0.1.0",
        config_storage: Optional[ConfigStorage] = None,
    ):
        self._default_api_key = ApiKey.normalize(api_key)
        self._base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self._api_prefix = self._normalize_path_prefix(
            api_prefix or self.DEFAULT_API_PREFIX
        )
        self._api_v2_prefix = self._normalize_path_prefix(
            api_v2_prefix or self.DEFAULT_API_V2_PREFIX
        )
        self._user_agent = user_agent
        self._config_storage = config_storage

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def api_prefix(self) -> str:
        return self._api_prefix

    @property
    def api_v2_prefix(self) -> str:
        return self._api_v2_prefix

    async def get_bots(self) -> List[Dict[str, Any]]:
        """Get all bots."""
        logger.info("Fetching bots from DCTW API")
        return await self._get_collection("/bots/")

    async def get_bot_comments(self, bot_id: int) -> List[Dict[str, Any]]:
        """Get bot comments."""
        logger.info(f"Fetching comments for bot {bot_id}")
        return await self._get_collection(f"/bots/{bot_id}/comments/")

    @classmethod
    def comment_list_action(cls, item_type: str) -> str:
        """Return the review list server action of one item type."""
        return cls.COMMENT_LIST_ACTIONS.get(str(item_type or "").strip().lower(), "")

    async def get_comments(
        self, item_type: str, item_id: Union[int, str]
    ) -> List[Dict[str, Any]]:
        """Read the reviews of an item through the website's own action.

        The public API embeds the reviews in the item itself, but the
        website reads them with a server action; reading that same list
        keeps the app in sync with the website.
        """
        action_id = self.comment_list_action(item_type)
        if not action_id:
            return []

        endpoint = f"/{item_type}/{item_id}/"
        headers = {
            "Next-Action": action_id,
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
                    endpoint, json.dumps([str(item_id)]), headers=headers
                )
        except Exception as error:
            logger.warning(
                f"Failed to load the reviews of {item_type} {item_id}: {error}"
            )
            return []

        data = self._extract_action_payload(payload)
        if not isinstance(data, list):
            return []

        return [item for item in data if isinstance(item, dict)]

    async def get_bot(self, bot_id: int) -> Optional[Dict[str, Any]]:
        """Get a single bot by ID. Returns None when the API answers 404."""
        return await self._get_item(f"/bots/{bot_id}/")

    async def get_user_profiles(
        self, user_ids: List[str], page_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Resolve Discord user ids to their public profile.

        The public API only exposes author ids, so the names and avatars are
        read from the same server action the official website uses. Failures
        are swallowed: a bot page stays usable without the author block.
        ``page_path`` is the detail page the action is called from (the
        website requires a matching Referer, e.g. ``/bots/123/``).
        """
        ids = [str(user_id).strip() for user_id in user_ids if str(user_id).strip()]
        if not ids:
            return []

        endpoint = (page_path or "/bots").strip()
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
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

    async def get_server_details(self, server_id: int) -> Optional[Dict[str, Any]]:
        """Read one server record from the official website detail page.

        Used for the fields the public API does not return (the admin list
        and the comments, which only the single item endpoint carries).
        """
        endpoint = f"/servers/{server_id}/"
        headers = {
            "Next-Action": self.GET_SERVER_ACTION,
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
                    json.dumps([str(server_id), list(self.SERVER_DETAIL_FIELDS)]),
                    headers=headers,
                )
        except Exception as error:
            logger.warning(f"Failed to load server details for {server_id}: {error}")
            return None

        data = self._extract_action_payload(payload)
        item = data.get("item") if isinstance(data, dict) else None
        return item if isinstance(item, dict) else None

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

    async def get_template_flags(self) -> List[Dict[str, Any]]:
        """Read the template list from the official website.

        Used for the fields the public API does not return (partner flag).
        """
        endpoint = "/templates/"
        headers = {
            "Next-Action": self.GET_TEMPLATES_ACTION,
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
                    json.dumps([list(self.TEMPLATE_LIST_FIELDS)]),
                    headers=headers,
                )
        except Exception as error:
            logger.warning(f"Failed to load template flags: {error}")
            return []

        data = self._extract_action_payload(payload)
        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return []

        return [item for item in items if isinstance(item, dict)]

    async def validate_api_key(self, api_key: Optional[str]) -> bool:
        """Check whether the DCTW API accepts the given API key.

        API v2 answers 401/403 for invalid keys (API v1 returns data even
        without a valid key), so the key is verified against /api/v2/bots/.
        """
        key = ApiKey.normalize(api_key)
        if not key:
            return False

        try:
            async with AsyncHttpClient(
                self._base_url, headers=self._build_headers(key)
            ) as client:
                response = await client.get(f"{self._api_v2_prefix}/bots/")
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                logger.info(
                    "API key validation rejected with %s", e.response.status_code
                )
                return False
            raise

        if isinstance(response, dict) and response.get("ok") is False:
            return False

        return True

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

    VOTE_ENDPOINT_TYPES = {
        "bot": "bots",
        "bots": "bots",
        "server": "servers",
        "servers": "servers",
        "template": "templates",
        "templates": "templates",
    }

    async def vote(self, item_type: str, item_id: Union[int, str]) -> Dict[str, Any]:
        """Vote for a bot, server or template.

        The API answers HTTP 200 even for business failures (for example
        while the vote cooldown is still active), so callers must check the
        ok flag of the returned body instead of the status code.

        Voting needs an API key. When none is stored (or the stored key was
        rejected) the result carries a ``needs_key`` flag so the caller can
        ask the user to paste one from the clipboard.

        Returns:
            The response body, e.g. {"ok": True, "message": "已成功投票！"}.
        """
        collection = self.VOTE_ENDPOINT_TYPES.get((item_type or "").strip().lower())
        if collection is None:
            raise ValueError(f"Unsupported item type: {item_type}")

        api_key = await self._load_runtime_api_key()
        endpoint = f"{self._api_v2_prefix}/{collection}/{item_id}/vote"

        try:
            async with AsyncHttpClient(
                self._base_url, headers=self._build_headers(api_key)
            ) as client:
                response = await self._request(client, "POST", endpoint)
        except InvalidApiKeyError:
            return {
                "ok": False,
                "needs_key": True,
                "message": "投票需要 DCTW API Key，請從剪貼簿貼上有效的 API Key。",
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {
                    "ok": False,
                    "message": "找不到該資源，請確認 ID 是否正確無誤。",
                }
            raise

        if isinstance(response, dict):
            return response

        return {"ok": False, "message": "投票失敗：API 回應格式不正確。"}

    async def _get_collection(self, endpoint: str) -> List[Dict[str, Any]]:
        # API v1 is public: a stored key is only sent when one exists.
        api_key = await self._load_runtime_api_key()
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
        api_key = await self._load_runtime_api_key()

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
                    "DCTW API Key 無效或已失效，請到「設定」重新從剪貼簿貼上 API Key。"
                ) from e
            raise

    async def _require_api_key(self) -> str:
        api_key = await self._load_runtime_api_key()
        if not api_key:
            raise ApiKeyMissingError(
                "尚未設定 DCTW API Key，請到「設定」從剪貼簿貼上 API Key。"
            )
        return api_key

    def _build_headers(self, api_key: Optional[str]) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": self._user_agent,
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

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

        # The flight stream marks each row as ``<id>:``. The rows are usually
        # separated by whitespace, but a text row can sit right in front of
        # the JSON row with no separator at all, so any marker that is not
        # part of a number is considered.
        for match in re.finditer(r"(?<![\d$])(\d+):", payload or ""):
            try:
                value, _ = decoder.raw_decode(payload, match.end())
            except ValueError:
                continue
            results.append((int(match.group(1)), value))

        if not results:
            return None

        # The website wraps its answers as {"ok": ..., "item": {...}} or
        # {"ok": ..., "items": [...]}, which is preferred so a JSON looking
        # string inside the payload can never shadow the real answer.
        for _, value in reversed(results):
            if isinstance(value, dict) and ("item" in value or "items" in value):
                return value

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
