"""Preference service"""

import logging

from domain.preferences.repositories import PreferencesRepository
from domain.preferences.aggregates import UserPreferences
from domain.preferences.value_objects import (
    Theme,
    ApiKey,
    NsfwFilter,
    UpdateCheck,
)

logger = logging.getLogger(__name__)


class PreferenceService:
    """Preference settings service"""

    def __init__(self, preferences_repo: PreferencesRepository):
        self._repo = preferences_repo
        self._current: UserPreferences = None

    async def load_preferences(self) -> UserPreferences:
        """Load user preferences"""
        logger.info("Loading user preferences")
        self._current = await self._repo.load()
        return self._current

    async def save_preferences(self) -> None:
        """Save current preferences"""
        if not self._current:
            logger.warning("No preferences to save")
            return

        logger.info("Saving user preferences")
        await self._repo.save(self._current)

    async def change_theme(self, theme: Theme) -> None:
        """Change theme"""
        if not self._current:
            await self.load_preferences()

        logger.info(f"Changing theme to {theme}")
        self._current.change_theme(theme)
        await self.save_preferences()

    async def update_api_key(self, api_key: str) -> None:
        """Update API key"""
        if not self._current:
            await self.load_preferences()

        logger.info("Updating API key")
        self._current.update_api_key(ApiKey(api_key))
        await self.save_preferences()

    async def toggle_nsfw(self) -> bool:
        """Toggle NSFW filter"""
        if not self._current:
            await self.load_preferences()

        logger.info("Toggling NSFW filter")
        self._current.toggle_nsfw()
        await self.save_preferences()
        return self._current.nsfw_filter.is_enabled

    async def set_nsfw(self, enabled: bool) -> None:
        """Set NSFW filter"""
        if not self._current:
            await self.load_preferences()

        logger.info(f"Setting NSFW filter to {enabled}")
        self._current.set_nsfw(enabled)
        await self.save_preferences()

    async def change_update_check(self, update_check: UpdateCheck) -> None:
        """Change update check settings"""
        if not self._current:
            await self.load_preferences()

        logger.info(f"Changing update check to {update_check}")
        self._current.change_update_check(update_check)
        await self.save_preferences()

    async def set_home_index(self, index: int) -> None:
        """Set homepage index"""
        if not self._current:
            await self.load_preferences()

        logger.info(f"Setting home index to {index}")
        self._current.set_home_index(index)
        await self.save_preferences()

    def get_current_preferences(self) -> UserPreferences:
        """Get current preferences"""
        return self._current
