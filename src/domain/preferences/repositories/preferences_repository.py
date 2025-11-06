"""Preferences repository interface"""

from abc import ABC, abstractmethod
from ..aggregates import UserPreferences


class PreferencesRepository(ABC):
    """Preference settings for storage interface"""

    @abstractmethod
    async def load(self) -> UserPreferences:
        """Load user preferences"""
        pass

    @abstractmethod
    async def save(self, preferences: UserPreferences) -> None:
        """Save user preferences"""
        pass

    @abstractmethod
    async def exists(self) -> bool:
        """Check if the configuration file exists."""
        pass
