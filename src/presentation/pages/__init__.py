"""Presentation pages"""

from .bot_list_page import BotListPage
from .server_list_page import ServerListPage
from .template_list_page import TemplateListPage
from .settings_page import SettingsPage
from .bot_detail_page import BotDetailPage

__all__ = [
    "BotListPage",
    "BotDetailPage",
    "ServerListPage",
    "TemplateListPage",
    "SettingsPage",
]
