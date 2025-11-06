"""JSON Preferences repository implementation"""

import logging
from domain.preferences.repositories import PreferencesRepository
from domain.preferences.aggregates import UserPreferences
from ..filesystem import ConfigStorage

logger = logging.getLogger(__name__)


class JsonPreferencesRepository(PreferencesRepository):
    """JSON file-based preferences repository implementation"""

    def __init__(self, storage: ConfigStorage):
        self._storage = storage

    async def load(self) -> UserPreferences:
        data = await self._storage.load()

        if not data:
            logger.info("No config found, using defaults")
            return UserPreferences()

        logger.info("Loading preferences from config file")
        return UserPreferences.from_dict(data)

    async def save(self, preferences: UserPreferences) -> None:
        data = preferences.to_dict()
        await self._storage.save(data)
        preferences.mark_as_saved()
        logger.info("Preferences saved")

    async def exists(self) -> bool:
        return await self._storage.exists()
