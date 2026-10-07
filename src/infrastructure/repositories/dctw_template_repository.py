"""DCTW Template repository implementation"""

from typing import List, Optional
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
from .api_helpers import normalize_url, parse_datetime, parse_tag_list, to_bool

logger = logging.getLogger(__name__)


class DctwTemplateRepository(TemplateRepository):
    """DCTW API-based Template repository implementation"""

    CACHE_KEY = "templates:all"

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
        data = await self._api_client.get_templates()
        templates = [self._map_to_domain(item) for item in data]

        await self._cache.set(
            self.CACHE_KEY, [self._serialize_template(t) for t in templates], ttl=300
        )

        logger.info(f"Loaded {len(templates)} templates from API")
        return templates

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
            "created_at": template.timestamps.created_at.isoformat(),
            "bumped_at": template.timestamps.bumped_at.isoformat(),
        }

    def _deserialize_template(self, data: dict) -> Template:
        """Deserialize Template from cache"""
        return self._map_to_domain(data)
