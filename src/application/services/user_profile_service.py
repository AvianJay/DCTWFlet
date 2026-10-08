"""Discord user profile service

Resolves the Discord ids the API returns (bot authors, server admins and
reviewers) to the names and avatars the official website shows.
"""

from typing import Dict, List, Optional, Sequence
import logging

from domain.discovery.entities import UserProfile
from infrastructure.api import DctwApiClient
from infrastructure.cache import CacheManager

logger = logging.getLogger(__name__)


class UserProfileService:
    """Look up public Discord profiles, with a small on-disk cache."""

    CACHE_PREFIX = "users:profile:"
    CACHE_TTL = 3600

    def __init__(self, api_client: DctwApiClient, cache_manager: CacheManager):
        self._api_client = api_client
        self._cache = cache_manager

    async def get_profiles(
        self, user_ids: Sequence[str], page_path: Optional[str] = None
    ) -> List[UserProfile]:
        """Return the profiles of ``user_ids`` that could be resolved.

        ``page_path`` is the detail page the request is made from; the
        website action only answers when the Referer matches it.
        """
        ids: List[str] = []
        for user_id in user_ids or []:
            text = str(user_id or "").strip()
            if text and text not in ids:
                ids.append(text)
        if not ids:
            return []

        profiles: Dict[str, dict] = {}
        missing: List[str] = []
        for user_id in ids:
            cached = await self._cache.get(f"{self.CACHE_PREFIX}{user_id}")
            if isinstance(cached, dict) and cached.get("name"):
                profiles[user_id] = cached
            else:
                missing.append(user_id)

        if missing:
            try:
                fetched = await self._api_client.get_user_profiles(
                    missing, page_path
                )
            except Exception as error:
                logger.warning(f"Failed to resolve Discord profiles: {error}")
                fetched = []

            for profile in fetched:
                profile_id = str(profile.get("id") or "").strip()
                if not profile_id:
                    continue
                profiles[profile_id] = profile
                await self._cache.set(
                    f"{self.CACHE_PREFIX}{profile_id}", profile, ttl=self.CACHE_TTL
                )

        resolved: List[UserProfile] = []
        for user_id in ids:
            entry = profiles.get(user_id) or {}
            name = str(entry.get("name") or "").strip()
            if not name:
                continue
            resolved.append(
                UserProfile(
                    id=user_id,
                    name=name,
                    avatar_url=entry.get("avatar_url"),
                )
            )
        return resolved

