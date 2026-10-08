"""DCTW Server repository implementation"""

from typing import List, Optional
import logging

from domain.discovery.repositories import ServerRepository
from domain.discovery.entities import (
    Server,
    ServerAdmin,
    ServerDetails,
    ServerLinks,
)
from domain.discovery.value_objects import (
    ServerTag,
    Statistics,
    Timestamps,
    AvatarUrl,
    BannerUrl,
    InviteUrl,
)
from ..api import DctwApiClient
from ..cache import CacheManager
from .api_helpers import (
    FALLBACK_AVATAR_URL,
    is_listed_item,
    normalize_optional_url,
    normalize_url,
    parse_admin_entries,
    parse_comments,
    parse_datetime,
    parse_features,
    parse_social_links,
    parse_tag_list,
    serialize_comments,
    to_bool,
)

logger = logging.getLogger(__name__)


class DctwServerRepository(ServerRepository):
    """DCTW API-based Server repository implementation"""

    CACHE_KEY = "servers:all"
    DETAIL_CACHE_PREFIX = "servers:details:"

    def __init__(self, api_client: DctwApiClient, cache_manager: CacheManager):
        self._api_client = api_client
        self._cache = cache_manager

    async def find_all(self) -> List[Server]:
        """Get allServers"""
        cached = await self._cache.get(self.CACHE_KEY)
        if cached is not None:
            logger.info(f"Loading {len(cached)} servers from cache")
            return [self._deserialize_server(data) for data in cached]

        logger.info("Fetching servers from API")
        data = await self._api_client.get_servers()
        servers = [
            self._map_to_domain(item) for item in data if is_listed_item(item)
        ]

        await self._cache.set(
            self.CACHE_KEY, [self._serialize_server(s) for s in servers], ttl=300
        )

        logger.info(f"Loaded {len(servers)} servers from API")
        return servers

    async def find_by_id(self, server_id: int) -> Optional[Server]:
        """Find Server by ID.

        Uses the cached list when possible and falls back to the single
        server endpoint, avoiding multi-megabyte list downloads.
        """
        cached = await self._cache.get(self.CACHE_KEY)
        if cached:
            for item in cached:
                server = self._deserialize_server(item)
                if server.id == server_id:
                    return server

        data = await self._api_client.get_server(server_id)
        if data is not None:
            return self._map_to_domain(data)

        return None

    async def clear_cache(self) -> None:
        """Clear cache"""
        await self._cache.delete(self.CACHE_KEY)
        logger.info("Server cache cleared")

    async def find_details(self, server_id: int) -> ServerDetails:
        """Admins and comments of the official server page.

        Both live outside the public list payload: the website reads them
        through its own detail action, with the single item endpoint as a
        fallback for the comments.
        """
        cache_key = f"{self.DETAIL_CACHE_PREFIX}{server_id}"
        cached = await self._cache.get(cache_key)
        if isinstance(cached, dict):
            data = cached
        else:
            data = None
            try:
                data = await self._api_client.get_server_details(server_id)
            except Exception as error:
                logger.warning(
                    f"Failed to load the detail data of server {server_id}: {error}"
                )

            if data is None:
                try:
                    data = await self._api_client.get_server(server_id)
                except Exception as error:
                    logger.warning(
                        f"Failed to load the detail data of server {server_id}: {error}"
                    )

            if isinstance(data, dict):
                await self._cache.set(cache_key, data, ttl=300)
            else:
                data = {}

        return ServerDetails(
            admins=[
                ServerAdmin(id=entry["id"], job=entry["job"])
                for entry in parse_admin_entries(data.get("admins"))
            ],
            comments=parse_comments(data.get("comments")),
        )

    def _map_to_domain(self, data: dict) -> Server:
        """Map API data to domain model"""
        server_id = int(data["id"])

        icon_url = normalize_url(
            data.get("avatar") or data.get("icon_url"),
            FALLBACK_AVATAR_URL,
        )

        invite_url = normalize_url(
            data.get("inviteLink") or data.get("url") or data.get("invite_url"),
            "https://discord.gg/invalid",
        )
        name = (data.get("name") or "").strip()

        if not name:
            name = f"Server {server_id}"
            logger.warning(f"Server {server_id} has empty name, using fallback")

        banner_url = normalize_optional_url(
            data.get("banner") or data.get("banner_url")
        )
        badge = data.get("badge") if isinstance(data.get("badge"), dict) else {}
        is_partnered = (
            to_bool(badge.get("partner"))
            or to_bool(data.get("partnered"))
            or to_bool(data.get("is_partnered", False))
        )

        if not data.get("bumped_at"):
            data["bumped_at"] = "1999-01-01T00:00:00Z"

        if not data.get("created_at"):
            data["created_at"] = "1999-01-01T00:00:00Z"

        return Server(
            id=server_id,
            name=name,
            icon=AvatarUrl(icon_url),
            description=data.get("description") or "",
            introduce=data.get("introduce") or "",
            is_partnered=is_partnered,
            nsfw=to_bool(data.get("nsfw", False)),
            statistics=Statistics(
                votes=int(data.get("vote_count", data.get("votes", 0)) or 0),
                count=int(data.get("members", data.get("member_count", 0)) or 0),
            ),
            tags=self._map_tags(data.get("tags")),
            links=ServerLinks(invite=InviteUrl(invite_url)),
            timestamps=Timestamps(
                created_at=parse_datetime(
                    data.get("created_at", "1999-01-01T00:00:00Z")
                ),
                bumped_at=parse_datetime(
                    data.get("bumped_at", "1999-01-01T00:00:00Z")
                ),
            ),
            banner=BannerUrl(banner_url) if banner_url else None,
            pinned=to_bool(data.get("pinned", False)),
            social_links=parse_social_links(data.get("socialLinks")),
            online_members=int(
                data.get("onlineMembers", data.get("online_members", 0)) or 0
            ),
            features=parse_features(data.get("features")),
            admins=[
                ServerAdmin(id=entry["id"], job=entry["job"])
                for entry in parse_admin_entries(data.get("admins"))
            ],
            comments=parse_comments(data.get("comments")),
        )

    @staticmethod
    def _map_tags(value) -> list[ServerTag]:
        """Map raw tags, merging the two spellings of "programing"."""
        tags: list[ServerTag] = []
        for tag in parse_tag_list(value):
            normalized = "programing" if tag == "programming" else tag
            if normalized in ServerTag.VALID_TAGS:
                tags.append(ServerTag(normalized))
        return tags

    def _serialize_server(self, server: Server) -> dict:
        """Serialize for cache"""
        return {
            "id": server.id,
            "name": server.name,
            "icon_url": server.icon.value,
            "banner_url": server.banner.value if server.banner else None,
            "description": server.description,
            "introduce": server.introduce,
            "is_partnered": server.is_partnered,
            "nsfw": server.nsfw,
            "votes": server.statistics.votes,
            "members": server.statistics.members,
            "tags": [tag.name for tag in server.tags],
            "invite_url": server.links.invite.value,
            "created_at": server.timestamps.created_at.isoformat(),
            "bumped_at": server.timestamps.bumped_at.isoformat(),
            "pinned": server.pinned,
            "socialLinks": server.social_links,
            "online_members": server.online_members,
            "features": server.features,
            "admins": [
                {"id": admin.id, "job": admin.job} for admin in server.admins
            ],
            "comments": serialize_comments(server.comments),
        }

    def _deserialize_server(self, data: dict) -> Server:
        """Deserialize Server from cache"""
        return self._map_to_domain(data)
