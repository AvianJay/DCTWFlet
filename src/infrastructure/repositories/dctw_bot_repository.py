"""DCTW Bot repository implementation"""

from typing import List, Optional
from datetime import datetime, timezone
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
        if cached:
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
        name = data.get("name", "").strip()
        if not name:
            name = f"Bot {bot_id}"
            logger.warning(f"Bot {bot_id} has empty name, using fallback")

        avatar_url = data.get("avatar_url", "").strip()

        if not avatar_url:
            avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png"

        invite_url = data.get("invite_url", "").strip()

        if not invite_url:
            invite_url = "https://discord.com/oauth2/authorize?client_id=0"

        return Bot(
            id=bot_id,
            name=name,
            avatar=AvatarUrl(avatar_url),
            description=data["description"],
            introduce=data.get("introduce", ""),
            status=ContentStatus.from_string(data.get("status", "unknown")),
            verified=data.get("verified", False),
            is_partnered=data.get("is_partnered", False),
            nsfw=data.get("nsfw", False),
            statistics=Statistics(
                votes=data.get("votes", 0), count=data.get("servers", 0)
            ),
            tags=[
                BotTag(tag) for tag in data.get("tags", []) if tag in BotTag.VALID_TAGS
            ],
            links=BotLinks(
                invite=InviteUrl(invite_url),
                support_server=data.get("server_url"),
                website=data.get("web_url"),
            ),
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
        }

    def _deserialize_bot(self, data: dict) -> Bot:
        """Deserialize Bot from cache"""
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
