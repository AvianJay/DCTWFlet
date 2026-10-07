"""DCTW Bot repository implementation"""

import asyncio
from typing import Dict, List, Optional
import logging

from domain.discovery.repositories import BotRepository
from domain.discovery.entities import Bot, BotAuthor, BotDetails, BotLinks
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
    is_listed_bot,
    normalize_optional_url,
    normalize_url,
    parse_author_ids,
    parse_datetime,
    parse_social_links,
    parse_tag_list,
    to_bool,
)

logger = logging.getLogger(__name__)


class DctwBotRepository(BotRepository):
    """DCTW API-based Bot repository implementation"""

    CACHE_KEY = "bots:all"
    PARTNER_CACHE_PREFIX = "bots:partner:"
    USER_CACHE_PREFIX = "users:profile:"

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
        bots = [
            self._map_to_domain(item) for item in data if is_listed_bot(item)
        ]

        await self._cache.set(
            self.CACHE_KEY, [self._serialize_bot(bot) for bot in bots], ttl=300
        )

        logger.info(f"Loaded {len(bots)} bots from API")
        return bots

    async def find_by_id(self, bot_id: int) -> Optional[Bot]:
        """Find Bot by ID.

        The cached list is checked first so opening a detail page from a
        freshly loaded list is instant; otherwise only the single bot is
        fetched instead of the whole collection.
        """
        cached = await self._cache.get(self.CACHE_KEY)
        if cached:
            for item in cached:
                bot = self._deserialize_bot(item)
                if bot.id == bot_id:
                    return bot

        data = await self._api_client.get_bot(bot_id)
        if data is not None:
            return self._map_to_domain(data)

        return None

    async def find_details(
        self, bot_id: int, author_ids: Optional[List[str]] = None
    ) -> BotDetails:
        """Authors and partner flag shown on the official bot page.

        Both requests run in parallel so a detail page can refresh its
        badges right after the (cached) bot data is on screen.
        """
        is_partnered, authors = await asyncio.gather(
            self._load_partner_status(bot_id),
            self._load_authors(bot_id, list(author_ids or [])),
        )

        return BotDetails(is_partnered=is_partnered, authors=authors)

    async def _load_partner_status(self, bot_id: int) -> bool:
        """Read the partner flag from the single bot endpoint."""
        cache_key = f"{self.PARTNER_CACHE_PREFIX}{bot_id}"
        cached = await self._cache.get(cache_key)
        if isinstance(cached, bool):
            return cached

        try:
            data = await self._api_client.get_bot_flags(bot_id)
        except Exception as error:
            logger.warning(f"Failed to load partner status of bot {bot_id}: {error}")
            return False

        if data is None:
            # Older API revisions expose the flag on the bot record itself.
            try:
                data = await self._api_client.get_bot(bot_id)
            except Exception as error:
                logger.warning(
                    f"Failed to load partner status of bot {bot_id}: {error}"
                )
                return False

        if data is None:
            return False

        is_partnered = (
            to_bool(data.get("partnered"))
            or to_bool(data.get("partner"))
            or to_bool(data.get("is_partnered", False))
        )
        await self._cache.set(cache_key, is_partnered, ttl=600)
        return is_partnered

    async def _load_authors(
        self, bot_id: int, author_ids: List[str]
    ) -> List[BotAuthor]:
        """Resolve the Discord author ids to names and avatars."""
        if not author_ids:
            return []

        profiles: Dict[str, dict] = {}
        missing: List[str] = []
        for author_id in author_ids:
            if author_id in profiles or author_id in missing:
                continue
            cached = await self._cache.get(f"{self.USER_CACHE_PREFIX}{author_id}")
            if isinstance(cached, dict) and cached.get("name"):
                profiles[author_id] = cached
            else:
                missing.append(author_id)

        if missing:
            for profile in await self._api_client.get_user_profiles(missing, bot_id):
                profile_id = str(profile.get("id") or "").strip()
                if not profile_id:
                    continue
                profiles[profile_id] = profile
                await self._cache.set(
                    f"{self.USER_CACHE_PREFIX}{profile_id}", profile, ttl=3600
                )

        authors: List[BotAuthor] = []
        for author_id in author_ids:
            profile = profiles.get(author_id)
            name = str((profile or {}).get("name") or "").strip()
            if not name:
                continue
            authors.append(
                BotAuthor(
                    id=author_id,
                    name=name,
                    avatar_url=(profile or {}).get("avatar_url"),
                )
            )

        return authors

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

        cached_author_ids = data.get("author_ids")
        if isinstance(cached_author_ids, list):
            author_ids = [
                str(value).strip()
                for value in cached_author_ids
                if str(value).strip()
            ]
        else:
            author_ids = parse_author_ids(data)

        if not data.get("bumped_at"):
            data["bumped_at"] = "1999-01-01T00:00:00Z"

        if not data.get("created_at"):
            data["created_at"] = "1999-01-01T00:00:00Z"

        # "is_official_verified" is "1" for every listed bot (it only means the
        # bot is published on DCTW), so the blue check must follow the Discord
        # verification flag alone, exactly like the website does.
        verified = to_bool(data.get("is_dc_verified")) or to_bool(
            data.get("verified", False)
        )

        return Bot(
            id=bot_id,
            name=name,
            avatar=AvatarUrl(avatar_url),
            description=data.get("description") or "",
            introduce=data.get("introduce") or "",
            # The website shows bots without a presence sample as online.
            status=ContentStatus.from_string(data.get("status") or "online"),
            verified=verified,
            is_partnered=(
                to_bool(data.get("partnered"))
                or to_bool(data.get("partner"))
                or to_bool(data.get("is_partnered", False))
            ),
            nsfw=to_bool(data.get("nsfw", False)),
            statistics=Statistics(
                votes=int(data.get("vote_count", data.get("votes", 0)) or 0),
                count=int(data.get("servers", data.get("server_count", 0)) or 0),
            ),
            tags=[
                BotTag(tag)
                for tag in parse_tag_list(data.get("tags"))
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
            pinned=to_bool(data.get("pinned", False)),
            author_ids=author_ids,
            social_links=parse_social_links(data.get("socialLinks")),
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
            "author_ids": bot.author_ids,
            "socialLinks": bot.social_links,
            "created_at": bot.timestamps.created_at.isoformat(),
            "bumped_at": bot.timestamps.bumped_at.isoformat(),
            "pinned": bot.pinned,
        }

    def _deserialize_bot(self, data: dict) -> Bot:
        """Deserialize Bot from cache"""
        return self._map_to_domain(data)
