"""DCTW Template repository implementation"""

import asyncio
from typing import Dict, List, Optional
import logging

from domain.discovery.repositories import TemplateRepository
from domain.discovery.entities import Template, TemplateLinks
from domain.discovery.value_objects import (
    TemplateTag,
    Statistics,
    Timestamps,
)
from ..api import DctwApiClient
from ..cache import CacheManager
from .api_helpers import (
    is_listed_item,
    normalize_url,
    parse_author_ids,
    parse_comments,
    parse_datetime,
    parse_social_links,
    parse_tag_list,
    serialize_comments,
    to_bool,
)

logger = logging.getLogger(__name__)


class DctwTemplateRepository(TemplateRepository):
    """DCTW API-based Template repository implementation"""

    CACHE_KEY = "templates:all"
    FLAGS_CACHE_KEY = "templates:partner_flags"

    # Partner status changes very rarely, so the flag read from the website
    # action is kept for hours instead of minutes.
    PARTNER_TTL = 6 * 60 * 60

    def __init__(self, api_client: DctwApiClient, cache_manager: CacheManager):
        self._api_client = api_client
        self._cache = cache_manager

    async def find_all(self) -> List[Template]:
        """Get allTemplates"""
        cached = await self._cache.get(self.CACHE_KEY)
        if cached is not None:
            logger.info(f"Loading {len(cached)} templates from cache")
            return [self._deserialize_template(data) for data in cached]

        logger.info("Fetching templates from API")
        data, partner_flags = await asyncio.gather(
            self._api_client.get_templates(),
            self._load_partner_flags(),
        )
        for item in data:
            try:
                flag = partner_flags.get(int(item.get("id")))
            except (TypeError, ValueError):
                flag = None
            if flag is not None:
                item["is_partnered"] = flag
        templates = [
            self._map_to_domain(item) for item in data if is_listed_item(item)
        ]

        await self._cache.set(
            self.CACHE_KEY, [self._serialize_template(t) for t in templates], ttl=300
        )

        logger.info(f"Loaded {len(templates)} templates from API")
        return templates

    async def _load_partner_flags(self) -> Dict[int, bool]:
        """Return the partner flag of every template.

        The public list endpoint does not carry the flag, so it is read from
        the same website action the template page uses (in bulk, once).
        """
        cached = await self._cache.get(self.FLAGS_CACHE_KEY)
        if isinstance(cached, dict):
            flags: Dict[int, bool] = {}
            for key, value in cached.items():
                try:
                    flags[int(key)] = to_bool(value)
                except (TypeError, ValueError):
                    continue
            return flags

        items = await self._api_client.get_template_flags()

        flags = {}
        for item in items:
            try:
                template_id = int(item.get("id"))
            except (TypeError, ValueError):
                continue
            flags[template_id] = to_bool(item.get("partner"))

        await self._cache.set(
            self.FLAGS_CACHE_KEY,
            {str(key): value for key, value in flags.items()},
            ttl=self.PARTNER_TTL,
        )
        return flags

    async def find_by_id(self, template_id: int) -> Optional[Template]:
        """Find Template by ID.

        Uses the cached list when possible and falls back to the single
        template endpoint instead of refetching every template.
        """
        cached = await self._cache.get(self.CACHE_KEY)
        if cached:
            for item in cached:
                template = self._deserialize_template(item)
                if template.id == template_id:
                    return template

        data = await self._api_client.get_template(template_id)
        if data is not None:
            return self._map_to_domain(data)

        return None

    async def clear_cache(self) -> None:
        """Clear cache"""
        await self._cache.delete(self.CACHE_KEY)
        logger.info("Template cache cleared")

    def _map_to_domain(self, data: dict) -> Template:
        """Map API data to domain model"""

        if not data.get("bumped_at"):
            data["bumped_at"] = "1999-01-01T00:00:00Z"

        if not data.get("created_at"):
            data["created_at"] = "1999-01-01T00:00:00Z"

        share_url = normalize_url(
            data.get("shareLink") or data.get("url") or data.get("share_url")
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

        return Template(
            id=int(data["id"]),
            name=data.get("name") or f"Template {data['id']}",
            description=data.get("description") or "",
            introduce=data.get("introduce") or "",
            nsfw=to_bool(data.get("nsfw", False)),
            statistics=Statistics(
                votes=int(data.get("vote_count", data.get("votes", 0)) or 0), count=0
            ),
            tags=[
                TemplateTag(tag)
                for tag in parse_tag_list(data.get("tags"))
                if tag in TemplateTag.VALID_TAGS
            ],
            links=TemplateLinks(share_url=share_url),
            timestamps=Timestamps(
                created_at=parse_datetime(
                    data.get("created_at", "1999-01-01T00:00:00Z")
                ),
                bumped_at=parse_datetime(
                    data.get("bumped_at", "1999-01-01T00:00:00Z")
                ),
            ),
            pinned=to_bool(data.get("pinned", False)),
            is_partnered=to_bool(data.get("is_partnered", False)),
            social_links=parse_social_links(data.get("socialLinks")),
            author_ids=author_ids,
            comments=parse_comments(data.get("comments")),
        )

    def _serialize_template(self, template: Template) -> dict:
        """Serialize for cache"""
        return {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "introduce": template.introduce,
            "nsfw": template.nsfw,
            "votes": template.statistics.votes,
            "tags": [tag.name for tag in template.tags],
            "share_url": template.links.share_url,
            "author_ids": template.author_ids,
            "created_at": template.timestamps.created_at.isoformat(),
            "bumped_at": template.timestamps.bumped_at.isoformat(),
            "is_partnered": template.is_partnered,
            "socialLinks": template.social_links,
            "comments": serialize_comments(template.comments),
        }

    def _deserialize_template(self, data: dict) -> Template:
        """Deserialize Template from cache"""
        return self._map_to_domain(data)
