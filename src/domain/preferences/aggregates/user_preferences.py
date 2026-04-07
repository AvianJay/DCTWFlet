"""User preferences aggregate root"""

from domain.shared import AggregateRoot, DomainEvent
from ..value_objects import Theme, ApiKey, NsfwFilter, UpdateCheck


class ThemeChangedEvent(DomainEvent):
    """Theme changed event"""

    def __init__(self, old_theme: Theme, new_theme: Theme):
        super().__init__()
        self.old_theme = old_theme
        self.new_theme = new_theme


class ApiKeyUpdatedEvent(DomainEvent):
    """API key updated event"""

    pass


class NsfwFilterToggledEvent(DomainEvent):
    """NSFW filter toggled event"""

    def __init__(self, enabled: bool):
        super().__init__()
        self.enabled = enabled


class PreferencesSavedEvent(DomainEvent):
    """Preferences Save Event"""

    pass


class UserPreferences(AggregateRoot):
    CONFIG_VERSION = 5

    def __init__(
        self,
        theme: Theme = Theme.SYSTEM,
        api_key: ApiKey = None,
        nsfw_filter: NsfwFilter = None,
        update_check: UpdateCheck = UpdateCheck.POPUP,
        home_index: int = 0,
    ):
        super().__init__()
        self._theme = theme
        self._api_key = api_key or ApiKey()
        self._nsfw_filter = nsfw_filter or NsfwFilter(False)
        self._update_check = update_check
        self._home_index = home_index

    @property
    def theme(self) -> Theme:
        return self._theme

    @property
    def api_key(self) -> ApiKey:
        return self._api_key

    @property
    def nsfw_filter(self) -> NsfwFilter:
        return self._nsfw_filter

    @property
    def update_check(self) -> UpdateCheck:
        return self._update_check

    @property
    def home_index(self) -> int:
        return self._home_index

    def change_theme(self, theme: Theme) -> None:
        """Change theme"""
        if self._theme != theme:
            old_theme = self._theme
            self._theme = theme
            self.add_domain_event(ThemeChangedEvent(old_theme, theme))

    def update_api_key(self, api_key: ApiKey) -> None:
        """Update API key"""
        self._api_key = api_key
        self.add_domain_event(ApiKeyUpdatedEvent())

    def toggle_nsfw(self) -> None:
        """Toggle NSFW filter"""
        self._nsfw_filter = self._nsfw_filter.toggle()
        self.add_domain_event(NsfwFilterToggledEvent(self._nsfw_filter.is_enabled))

    def set_nsfw(self, enabled: bool) -> None:
        """Set NSFW filter"""
        if self._nsfw_filter.is_enabled != enabled:
            self._nsfw_filter = NsfwFilter(enabled)
            self.add_domain_event(NsfwFilterToggledEvent(enabled))

    def change_update_check(self, update_check: UpdateCheck) -> None:
        """Change update check settings"""
        self._update_check = update_check

    def set_home_index(self, index: int) -> None:
        """Set homepage index"""
        if 0 <= index <= 2:  # 0=bots, 1=servers, 2=templates
            self._home_index = index

    def mark_as_saved(self) -> None:
        """Marked as saved"""
        self.add_domain_event(PreferencesSavedEvent())

    def to_dict(self) -> dict:
        """Convert to dict"""
        return {
            "config_version": self.CONFIG_VERSION,
            "theme": self._theme.value,
            "apikey": self._api_key.value or "",
            "nsfw": self._nsfw_filter.is_enabled,
            "app_update_check": self._update_check.value,
            "home_index": self._home_index,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserPreferences":
        """From dictionary creation"""
        return cls(
            theme=Theme.from_string(data.get("theme", "system")),
            api_key=ApiKey(data.get("apikey")),
            nsfw_filter=NsfwFilter(data.get("nsfw", False)),
            update_check=UpdateCheck.from_string(data.get("app_update_check", "popup")),
            home_index=data.get("home_index", 0),
        )
