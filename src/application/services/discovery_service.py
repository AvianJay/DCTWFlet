"""Discovery service"""

from typing import List
import logging

from domain.discovery.repositories import (
    BotRepository,
    ServerRepository,
    TemplateRepository,
)
from domain.discovery.entities import Bot, Server, Template
from domain.discovery.value_objects import FilterCriteria, SortOption
from domain.discovery.aggregates import (
    BotCollection,
    ServerCollection,
    TemplateCollection,
)

from domain.shared import EntityNotFoundException, EntityNotFoundException

logger = logging.getLogger(__name__)


class DiscoveryService:
    """Discovery service - Coordinate Bot/Server/Template discovery logic"""

    def __init__(
        self,
        bot_repo: BotRepository,
        server_repo: ServerRepository,
        template_repo: TemplateRepository,
    ):
        self._bot_repo = bot_repo
        self._server_repo = server_repo
        self._template_repo = template_repo

    async def list_bots(
        self,
        filter_criteria: FilterCriteria = None,
        sort_option: SortOption = SortOption.NEWEST,
    ) -> List[Bot]:
        """
        List Bots

        Args:
            filter_criteria: Filtering conditions
            sort_option: Sort options

        Returns:
            Bot List
        """
        logger.info(f"Listing bots with filter={filter_criteria}, sort={sort_option}")

        bots = await self._bot_repo.find_all()

        collection = BotCollection()
        collection.load(bots)

        if filter_criteria:
            filtered = collection.filter_by(filter_criteria)
        else:
            filtered = collection.bots

        sorted_bots = collection.sort_by(filtered, sort_option)

        logger.info(f"Returned {len(sorted_bots)} bots")
        return sorted_bots

    async def get_bot_by_id(self, bot_id: int) -> Bot:
        """
        Retrieve Bot by ID

        Args:
            bot_id: Bot ID

        Returns:
            Bot entity

        Raises:
            EntityNotFoundException: Bot does not exist.
        """
        logger.info(f"Getting bot by id={bot_id}")
        bot = await self._bot_repo.find_by_id(bot_id)

        if not bot:

            raise EntityNotFoundException("Bot", bot_id)

        return bot

    async def list_servers(
        self,
        filter_criteria: FilterCriteria = None,
        sort_option: SortOption = SortOption.NEWEST,
    ) -> List[Server]:
        """List servers"""
        logger.info(
            f"Listing servers with filter={filter_criteria}, sort={sort_option}"
        )

        servers = await self._server_repo.find_all()

        collection = ServerCollection()
        collection.load(servers)

        if filter_criteria:
            filtered = collection.filter_by(filter_criteria)
        else:
            filtered = collection.servers

        sorted_servers = collection.sort_by(filtered, sort_option)

        logger.info(f"Returned {len(sorted_servers)} servers")
        return sorted_servers

    async def get_server_by_id(self, server_id: int) -> Server:
        """Get server by ID"""
        logger.info(f"Getting server by id={server_id}")
        server = await self._server_repo.find_by_id(server_id)

        if not server:
            raise EntityNotFoundException("Server", server_id)

        return server

    async def list_templates(
        self,
        filter_criteria: FilterCriteria = None,
        sort_option: SortOption = SortOption.NEWEST,
    ) -> List[Template]:
        """List templates"""
        logger.info(
            f"Listing templates with filter={filter_criteria}, sort={sort_option}"
        )

        templates = await self._template_repo.find_all()

        collection = TemplateCollection()
        collection.load(templates)

        if filter_criteria:
            filtered = collection.filter_by(filter_criteria)
        else:
            filtered = collection.templates

        sorted_templates = collection.sort_by(filtered, sort_option)

        logger.info(f"Returned {len(sorted_templates)} templates")
        return sorted_templates

    async def get_template_by_id(self, template_id: int) -> Template:
        """Get template by ID"""
        logger.info(f"Getting template by id={template_id}")
        template = await self._template_repo.find_by_id(template_id)

        if not template:

            raise EntityNotFoundException("Template", template_id)

        return template

    async def clear_all_caches(self):
        """Clear all cache"""
        logger.info("Clearing all caches")
        await self._bot_repo.clear_cache()
        await self._server_repo.clear_cache()
        await self._template_repo.clear_cache()
