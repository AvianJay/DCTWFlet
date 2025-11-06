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
    BotDetailPage,
    ServerListPage,
    TemplateListPage,
    SettingsPage,
)
from infrastructure.di import get_container
from infrastructure.image import ImageServer


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def main(page: ft.Page):
    """Application main entry point"""

    page.title = "DCTWFlet"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 0

    # Configure theme with consistent NavigationBar height across light and dark modes
    page.theme = ft.Theme(
        navigation_bar_theme=ft.NavigationBarTheme(
            height=80,
        )
    )
    page.dark_theme = ft.Theme(
        navigation_bar_theme=ft.NavigationBarTheme(
            height=80,
        )
    )

    # Start ImageServer in background
    container = get_container()
    image_server: ImageServer = container.resolve(ImageServer)

    # Start image server asynchronously
    asyncio.create_task(image_server.start())

    # Wait a moment for server to start
    await asyncio.sleep(0.5)
    logger.info(f"Image server started on port {image_server.port}")

    # Current tab state
    current_tab = [0]

    # Create page instances
    bot_page = BotListPage(page)
    server_page = ServerListPage(page)
    template_page = TemplateListPage(page)
    settings_page = SettingsPage(page)

    def create_home_view() -> ft.View:
        """Create home view with navigation bar"""
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
                    icon=ft.Icons.DNS_OUTLINED,
                    selected_icon=ft.Icons.DNS,
                    label="Servers",
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
            selected_index=current_tab[0],
            on_change=on_tab_changed,
        )

        # Set initial content based on current tab
        if current_tab[0] == 0:
            content_container.content = bot_page.build()
        elif current_tab[0] == 1:
            content_container.content = server_page.build()
        elif current_tab[0] == 2:
            content_container.content = template_page.build()
        elif current_tab[0] == 3:
            content_container.content = settings_page.build()

        return ft.View(
            "/",
            [
                ft.Column(
                    [
                        content_container,
                        navigation_bar,
                    ],
                    spacing=0,
                    expand=True,
                )
            ],
            padding=0,
        )

    def create_bot_detail_view(bot_id: str) -> ft.View:
        """Create bot detail view"""
        detail_page = BotDetailPage(page, bot_id)

        return ft.View(
            f"/bot/{bot_id}",
            [
                ft.Container(
                    content=detail_page.build(),
                    expand=True,
                )
            ],
            appbar=ft.AppBar(
                title=ft.Text("機器人詳情"),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                leading=ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: page.go("/"),
                ),
                automatically_imply_leading=False,
            ),
            padding=0,
        )

    def route_change(e):
        """Handle route changes"""
        page.views.clear()

        # Always add home view
        if page.route == "/" or page.route == "":
            page.views.append(create_home_view())
        elif page.route.startswith("/bot/"):
            # Extract bot ID from route
            bot_id = page.route.split("/bot/")[1]
            page.views.append(create_home_view())
            page.views.append(create_bot_detail_view(bot_id))
        else:
            # Unknown route
            page.views.append(create_home_view())

        page.update()

    def view_pop(e):
        """Handle view pop (back button)"""
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    # Navigate to home
    page.go(page.route if page.route else "/")


if __name__ == "__main__":
    ft.app(target=main)
