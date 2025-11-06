"""Dependency injection container"""

from typing import Dict, Type, Callable, Any, Optional
import logging
from domain.discovery.repositories import (
    BotRepository,
    ServerRepository,
    TemplateRepository,
)
from domain.preferences.repositories import PreferencesRepository
from ..config import get_settings
from ..api import DctwApiClient
from ..cache import CacheManager, MemoryCacheManager
from ..filesystem import ConfigStorage
from ..image import ImageServer
from ..repositories import (
    DctwBotRepository,
    DctwServerRepository,
    DctwTemplateRepository,
    JsonPreferencesRepository,
)

from application.services import DiscoveryService, PreferenceService

logger = logging.getLogger(__name__)


class DiContainer:
    def __init__(self):
        self._services: Dict[Type, Callable] = {}
        self._singletons: Dict[Type, Any] = {}
        self._singleton_flags: Dict[Type, bool] = {}

    def register(
        self, interface: Type, implementation: Callable, singleton: bool = False
    ):
        """
        Registration Service

        Args:
            interface: Interface type
            implementation: Implement the factory function
            singleton: Is it a singleton?
        """
        self._services[interface] = implementation
        self._singleton_flags[interface] = singleton
        if singleton:
            self._singletons[interface] = None
        logger.debug(f"Registered {interface.__name__} (singleton={singleton})")

    def resolve(self, interface: Type) -> Any:
        """
        resolution service

        Args:
            interface: Interface type

        Returns:
            Service Examples
        """
        if interface not in self._services:
            raise KeyError(f"Service {interface.__name__} not registered")

        if self._singleton_flags.get(interface, False):
            if self._singletons[interface] is None:
                logger.debug(f"Creating singleton instance of {interface.__name__}")
                self._singletons[interface] = self._services[interface](self)
            return self._singletons[interface]

        logger.debug(f"Creating new instance of {interface.__name__}")
        return self._services[interface](self)

    def is_registered(self, interface: Type) -> bool:
        return interface in self._services


_container: Optional[DiContainer] = None


def get_container() -> DiContainer:
    global _container
    if _container is None:
        _container = setup_container()
    return _container


def setup_container() -> DiContainer:
    container = DiContainer()
    settings = get_settings()

    container.register(
        CacheManager,
        lambda c: MemoryCacheManager(),
        singleton=True,
    )

    container.register(
        ImageServer,
        lambda c: ImageServer(
            cache_dir=settings.image_cache_dir,
            port_range=settings.image_server_port_range,
        ),
        singleton=True,
    )

    container.register(
        ConfigStorage,
        lambda c: ConfigStorage(settings.config_file),
        singleton=True,
    )

    container.register(
        DctwApiClient,
        lambda c: DctwApiClient(
            api_key=settings.api_key,
            base_url=settings.api_base_url,
            user_agent=f"{settings.app_name}/{settings.app_version}",
        ),
        singleton=False,
    )

    container.register(
        BotRepository,
        lambda c: DctwBotRepository(
            api_client=c.resolve(DctwApiClient),
            cache_manager=c.resolve(CacheManager),
        ),
        singleton=False,
    )

    container.register(
        ServerRepository,
        lambda c: DctwServerRepository(
            api_client=c.resolve(DctwApiClient),
            cache_manager=c.resolve(CacheManager),
        ),
        singleton=False,
    )

    container.register(
        TemplateRepository,
        lambda c: DctwTemplateRepository(
            api_client=c.resolve(DctwApiClient),
            cache_manager=c.resolve(CacheManager),
        ),
        singleton=False,
    )

    container.register(
        PreferencesRepository,
        lambda c: JsonPreferencesRepository(storage=c.resolve(ConfigStorage)),
        singleton=True,
    )

    container.register(
        DiscoveryService,
        lambda c: DiscoveryService(
            bot_repo=c.resolve(BotRepository),
            server_repo=c.resolve(ServerRepository),
            template_repo=c.resolve(TemplateRepository),
        ),
        singleton=True,
    )

    container.register(
        PreferenceService,
        lambda c: PreferenceService(preferences_repo=c.resolve(PreferencesRepository)),
        singleton=True,
    )

    logger.info("Dependency injection container configured")
    return container
