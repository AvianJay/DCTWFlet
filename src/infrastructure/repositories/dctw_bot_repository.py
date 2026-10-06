"""DCTW Bot repository implementation"""

from typing import List, Optional
import logging

from domain.discovery.repositories import BotRepository
from domain.discovery.entities import Bot, BotLinks
from domain.discovery.value_objects import (
    BotTag,
    ContentStatus,
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
    normalize_optional_url,
    normalize_url,
    parse_datetime,
)

logger = logging.getLogger(__name__)


class DctwBotRepository(BotRepository):
    """DCTW API-based Bot repository implementation"""

    CACHE_KEY = "bots:all"

    def __init__(self, api_client: DctwApiClient, cache_manager: CacheManager):
        self._api_client = api_client
        self._cache = cache_manager

    async def find_all(self) -> List[Bot]:
        """Get allBots"""
        cached = await self._cache.get(self.CACHE_KEY)
        if cached is not None:
            logger.info(f"Loading {len(cached)} bots from cache")
            return [self._deserialize_bot(data) for data in cached]

        logger.info("Fetching bots from API")
        data = await self._api_client.get_bots()
        bots = [self._map_to_domain(item) for item in data]

        await self._cache.set(
            self.CACHE_KEY, [self._serialize_bot(bot) for bot in bots], ttl=60
        )

        logger.info(f"Loaded {len(bots)} bots from API")
        return bots

    async def find_by_id(self, bot_id: int) -> Optional[Bot]:
        """Find Bot by ID"""
        bots = await self.find_all()
        return next((bot for bot in bots if bot.id == bot_id), None)

    async def clear_cache(self) -> None:
        """Clear cache"""
        await self._cache.delete(self.CACHE_KEY)
        logger.info("Bot cache cleared")

    def _map_to_domain(self, data: dict) -> Bot:
        """Map API data to domain model"""

        bot_id = int(data["id"])
        name = (data.get("name") or "").strip()
        if not name:
            name = f"Bot {bot_id}"
            logger.warning(f"Bot {bot_id} has empty name, using fallback")

        avatar_url = normalize_url(
            data.get("avatar") or data.get("avatar_url"),
            FALLBACK_AVATAR_URL,
        )

        invite_url = normalize_url(
            data.get("inviteLink") or data.get("url") or data.get("invite_url"),
            "https://discord.com/oauth2/authorize?client_id=0",
        )

        banner_url = normalize_optional_url(
            data.get("banner") or data.get("banner_url")
        )

        if not data.get("bumped_at"):
            data["bumped_at"] = "1999-01-01T00:00:00Z"

        if not data.get("created_at"):
            data["created_at"] = "1999-01-01T00:00:00Z"

        verified = bool(
            data.get("is_official_verified")
            or data.get("is_dc_verified")
            or data.get("verified", False)
        )

        return Bot(
            id=bot_id,
            name=name,
            avatar=AvatarUrl(avatar_url),
            description=data.get("description") or "",
            introduce=data.get("introduce") or "",
            status=ContentStatus.from_string(data.get("status", "unknown")),
            verified=verified,
            is_partnered=bool(
                data.get("partnered") or data.get("is_partnered", False)
            ),
            nsfw=bool(data.get("nsfw", False)),
            statistics=Statistics(
                votes=int(data.get("vote_count", data.get("votes", 0)) or 0),
                count=int(data.get("servers", data.get("server_count", 0)) or 0),
            ),
            tags=[
                BotTag(tag)
                for tag in (data.get("tags") or [])
                if tag in BotTag.VALID_TAGS
            ],
            links=BotLinks(
                invite=InviteUrl(invite_url),
                support_server=normalize_optional_url(
                    data.get("serverLink")
                    or data.get("discord_url")
                    or data.get("server_url")
                ),
                website=normalize_optional_url(
                    data.get("webLink")
                    or data.get("website_url")
                    or data.get("web_url")
                ),
            ),
            timestamps=Timestamps(
                created_at=parse_datetime(
                    data.get("created_at", "1999-01-01T00:00:00Z")
                ),
                bumped_at=parse_datetime(
                    data.get("bumped_at", "1999-01-01T00:00:00Z")
                ),
            ),
            banner=BannerUrl(banner_url) if banner_url else None,
            pinned=data.get("pinned", False),
        )

    def _serialize_bot(self, bot: Bot) -> dict:
        """Serialize for cache"""
        return {
            "id": bot.id,
            "name": bot.name,
            "avatar_url": bot.avatar.value,
            "banner_url": bot.banner.value if bot.banner else None,
            "description": bot.description,
            "introduce": bot.introduce,
            "status": bot.status.value,
            "verified": bot.verified,
            "is_partnered": bot.is_partnered,
            "nsfw": bot.nsfw,
            "votes": bot.statistics.votes,
            "servers": bot.statistics.servers,
            "tags": [tag.name for tag in bot.tags],
            "invite_url": bot.links.invite.value,
            "server_url": bot.links.support_server,
            "web_url": bot.links.website,
            "created_at": bot.timestamps.created_at.isoformat(),
            "bumped_at": bot.timestamps.bumped_at.isoformat(),
            "pinned": bot.pinned,
        }

    def _deserialize_bot(self, data: dict) -> Bot:
        """Deserialize Bot from cache"""
        return self._map_to_domain(data)
