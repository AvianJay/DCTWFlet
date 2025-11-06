"""DCTW Template repository implementation"""

from typing import List, Optional
from datetime import datetime, timezone
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
        if cached:
            logger.info(f"Loading {len(cached)} templates from cache")
            return [self._deserialize_template(data) for data in cached]

        logger.info("Fetching templates from API")
        data = await self._api_client.get_templates()
        templates = [self._map_to_domain(item) for item in data]

        await self._cache.set(
            self.CACHE_KEY, [self._serialize_template(t) for t in templates], ttl=60
        )

        logger.info(f"Loaded {len(templates)} templates from API")
        return templates

    async def find_by_id(self, template_id: int) -> Optional[Template]:
        """Find Template by ID"""
        templates = await self.find_all()
        return next((t for t in templates if t.id == template_id), None)

    async def clear_cache(self) -> None:
        """Clear cache"""
        await self._cache.delete(self.CACHE_KEY)
        logger.info("Template cache cleared")

    def _map_to_domain(self, data: dict) -> Template:
        """Map API data to domain model"""
        return Template(
            id=int(data["id"]),
            name=data["name"],
            description=data["description"],
            introduce=data.get("introduce", ""),
            nsfw=data.get("nsfw", False),
            statistics=Statistics(votes=data.get("votes", 0), count=0),
            tags=[
                TemplateTag(tag)
                for tag in data.get("tags", [])
                if tag in TemplateTag.VALID_TAGS
            ],
            links=TemplateLinks(share_url=data["share_url"]),
            timestamps=Timestamps(
                created_at=self._parse_datetime(data.get("created_at")),
                bumped_at=self._parse_datetime(data.get("bumped_at")),
            ),
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
