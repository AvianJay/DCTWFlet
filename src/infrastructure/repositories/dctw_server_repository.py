"""DCTW Server repository implementation"""

from typing import List, Optional
from datetime import datetime, timezone
import logging

from domain.discovery.repositories import ServerRepository
from domain.discovery.entities import Server, ServerLinks
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

logger = logging.getLogger(__name__)


class DctwServerRepository(ServerRepository):
    """DCTW API-based Server repository implementation"""

    CACHE_KEY = "servers:all"

    def __init__(self, api_client: DctwApiClient, cache_manager: CacheManager):
        self._api_client = api_client
        self._cache = cache_manager

    async def find_all(self) -> List[Server]:
        """Get allServers"""
        cached = await self._cache.get(self.CACHE_KEY)
        if cached:
            logger.info(f"Loading {len(cached)} servers from cache")
            return [self._deserialize_server(data) for data in cached]

        logger.info("Fetching servers from API")
        data = await self._api_client.get_servers()
        servers = [self._map_to_domain(item) for item in data]

        await self._cache.set(
            self.CACHE_KEY, [self._serialize_server(s) for s in servers], ttl=60
        )

        logger.info(f"Loaded {len(servers)} servers from API")
        return servers

    async def find_by_id(self, server_id: int) -> Optional[Server]:
        """Find Server by ID"""
        servers = await self.find_all()
        return next((s for s in servers if s.id == server_id), None)

    async def clear_cache(self) -> None:
        """Clear cache"""
        await self._cache.delete(self.CACHE_KEY)
        logger.info("Server cache cleared")

    def _map_to_domain(self, data: dict) -> Server:
        """Map API data to domain model"""
        server_id = int(data["id"])

        icon_url = data.get("icon_url", "").strip()

        if not icon_url:
            icon_url = "https://cdn.discordapp.com/embed/avatars/0.png"

        invite_url = data.get("invite_url", "").strip()
        name = data.get("name", "").strip()

        if not name:
            name = f"Server {server_id}"
            logger.warning(f"Server {server_id} has empty name, using fallback")

        if not invite_url:
            invite_url = "https://discord.gg/invalid"

        return Server(
            id=server_id,
            name=name,
            icon=AvatarUrl(icon_url),
            description=data["description"],
            introduce=data.get("introduce", ""),
            is_partnered=data.get("is_partnered", False),
            nsfw=data.get("nsfw", False),
            statistics=Statistics(
                votes=data.get("votes", 0), count=data.get("members", 0)
            ),
            tags=[
                ServerTag(tag)
                for tag in data.get("tags", [])
                if tag in ServerTag.VALID_TAGS
            ],
            links=ServerLinks(invite=InviteUrl(invite_url)),
            timestamps=Timestamps(
                created_at=self._parse_datetime(data.get("created_at")),
                bumped_at=self._parse_datetime(data.get("bumped_at")),
            ),
            banner=(
                BannerUrl(data["banner_url"])
                if data.get("banner_url") and data.get("banner_url").strip()
                else None
            ),
        )

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
        }

    def _deserialize_server(self, data: dict) -> Server:
        """Deserialize Server from cache"""
        return self._map_to_domain(data)

    @staticmethod
    def _parse_datetime(value) -> datetime:
        """Parse date and time"""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except:
                pass
        return datetime.now(timezone.utc)
