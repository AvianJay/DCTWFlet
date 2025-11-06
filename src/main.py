import sys
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import flet as ft
import asyncio
import logging

from presentation.pages import (
    BotListPage,
    ServerListPage,
    TemplateListPage,
    SettingsPage,
)


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def main(page: ft.Page):
    """Application main entry point"""

    page.title = "DCTWFlet"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 0

    current_tab = [0]

    bot_page = BotListPage(page)
    server_page = ServerListPage(page)
    template_page = TemplateListPage(page)
    settings_page = SettingsPage(page)

    content_container = ft.Container(expand=True)

    def on_tab_changed(e):
        """Tab change event handler"""
        index = e.control.selected_index
        current_tab[0] = index

        if index == 0:
            content_container.content = bot_page.build()
        elif index == 1:
            content_container.content = server_page.build()
        elif index == 2:
            content_container.content = template_page.build()
        elif index == 3:
            content_container.content = settings_page.build()

        page.update()

    navigation_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.SMART_TOY_OUTLINED,
                selected_icon=ft.Icons.SMART_TOY,
                label="Bots",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.DNS_OUTLINED, selected_icon=ft.Icons.DNS, label="Servers"
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.COPY_ALL_OUTLINED,
                selected_icon=ft.Icons.COPY_ALL,
                label="Templates",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,
                selected_icon=ft.Icons.SETTINGS,
                label="設置",
            ),
        ],
        on_change=on_tab_changed,
    )

    content_container.content = bot_page.build()

    page.add(
        ft.Column(
            [
                content_container,
                navigation_bar,
            ],
            spacing=0,
            expand=True,
        )
    )


if __name__ == "__main__":
    ft.app(target=main)
