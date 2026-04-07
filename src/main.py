import sys
from pathlib import Path
import asyncio
import logging

import flet as ft

# Add src directory to Python path
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from presentation.pages import (
    BotListPage,
    BotDetailPage,
    ServerListPage,
    TemplateListPage,
    SettingsPage,
    ServerDetailPage,
    TemplateDetailPage,
)
from infrastructure.di import get_container
from infrastructure.image import ImageServer
from application.services import PreferenceService


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main(page: ft.Page):
    """Application main entry point."""

    def navigate(route: str):
        if hasattr(page, "push_route"):
            asyncio.create_task(page.push_route(route))
        else:
            page.go(route)

    page.title = "DCTW"
    page.padding = 0
    page.bgcolor = ft.Colors.SURFACE

    container = get_container()

    pref_service: PreferenceService = container.resolve(PreferenceService)
    try:
        prefs = await pref_service.load_preferences()
        page.theme_mode = prefs.theme.value
    except Exception as e:
        logger.exception("Failed to load preferences")
        logger.error(str(e))
        page.theme_mode = ft.ThemeMode.SYSTEM

    page.theme = ft.Theme(navigation_bar_theme=ft.NavigationBarTheme(height=80))
    page.dark_theme = ft.Theme(navigation_bar_theme=ft.NavigationBarTheme(height=80))

    image_server: ImageServer = container.resolve(ImageServer)

    async def start_image_server():
        try:
            await image_server.start()
        except Exception:
            logger.exception("Image server failed to start")

    asyncio.create_task(start_image_server())

    current_tab = [0]

    bot_page = BotListPage(page)
    server_page = ServerListPage(page)
    template_page = TemplateListPage(page)
    settings_page = SettingsPage(page)

    def create_home_view() -> ft.View:
        content_container = ft.Container(expand=True)

        def on_tab_changed(e):
            """Tab change event handler"""
            index = e.control.selected_index
            current_tab[0] = index

            if index == 0:
                page.title = "DCTW - 機器人清單"
                content_container.content = bot_page.build()
            elif index == 1:
                page.title = "DCTW - 伺服器清單"
                content_container.content = server_page.build()
            elif index == 2:
                page.title = "DCTW - 模板清單"
                content_container.content = template_page.build()
            elif index == 3:
                page.title = "DCTW - 設置"
                content_container.content = settings_page.build()

            page.update()

        navigation_bar = ft.NavigationBar(
            destinations=[
                ft.NavigationBarDestination(
                    icon=ft.Icons.SMART_TOY_OUTLINED,
                    selected_icon=ft.Icons.SMART_TOY,
                    label="機器人",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.DNS_OUTLINED,
                    selected_icon=ft.Icons.DNS,
                    label="伺服器",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.COPY_ALL_OUTLINED,
                    selected_icon=ft.Icons.COPY_ALL,
                    label="範本",
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

        if current_tab[0] == 0:
            content_container.content = bot_page.build()
        elif current_tab[0] == 1:
            content_container.content = server_page.build()
        elif current_tab[0] == 2:
            content_container.content = template_page.build()
        else:
            content_container.content = settings_page.build()

        return ft.View(
            route="/",
            controls=[
                ft.Column(
                    [content_container, navigation_bar],
                    spacing=0,
                    expand=True,
                )
            ],
            padding=0,
        )

    def create_bot_detail_view(bot_id: str) -> ft.View:
        detail_page = BotDetailPage(page, bot_id)
        return ft.View(
            route=f"/bot/{bot_id}",
            controls=[ft.Container(content=detail_page.build(), expand=True)],
            appbar=ft.AppBar(
                title=ft.Text("機器人詳情"),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                leading=ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: navigate("/"),
                ),
                automatically_imply_leading=False,
            ),
            padding=0,
        )

    def create_server_detail_view(server_id: str) -> ft.View:
        detail_page = ServerDetailPage(page, server_id)
        return ft.View(
            route=f"/server/{server_id}",
            controls=[ft.Container(content=detail_page.build(), expand=True)],
            appbar=ft.AppBar(
                title=ft.Text("伺服器詳情"),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                leading=ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: navigate("/"),
                ),
                automatically_imply_leading=False,
            ),
            padding=0,
        )

    def create_template_detail_view(template_id: str) -> ft.View:
        detail_page = TemplateDetailPage(page, template_id)
        return ft.View(
            route=f"/template/{template_id}",
            controls=[ft.Container(content=detail_page.build(), expand=True)],
            appbar=ft.AppBar(
                title=ft.Text("範本詳情"),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                leading=ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: navigate("/"),
                ),
                automatically_imply_leading=False,
            ),
            padding=0,
        )

    def route_change(e):
        try:
            logger.info("Route change: %s", page.route)
            page.views.clear()

            if page.route in ("", "/"):
                page.views.append(create_home_view())
            elif page.route.startswith("/bot/"):
                bot_id = page.route.split("/bot/")[1]
                page.views.append(create_home_view())
                page.views.append(create_bot_detail_view(bot_id))
            elif page.route.startswith("/server/"):
                server_id = page.route.split("/server/")[1]
                page.views.append(create_home_view())
                page.views.append(create_server_detail_view(server_id))
            elif page.route.startswith("/template/"):
                template_id = page.route.split("/template/")[1]
                page.views.append(create_home_view())
                page.views.append(create_template_detail_view(template_id))
            else:
                page.views.append(create_home_view())

            logger.info("Views rendered: %s", len(page.views))
            page.update()
        except Exception as ex:
            logger.exception("Route rendering failed")
            page.views.clear()
            page.views.append(
                ft.View(
                    route="/",
                    controls=[
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Icon(
                                        ft.Icons.ERROR_OUTLINE,
                                        size=48,
                                        color=ft.Colors.ERROR,
                                    ),
                                    ft.Text(
                                        "UI initialization failed",
                                        size=20,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(str(ex), selectable=True),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=12,
                            ),
                            expand=True,
                            alignment=ft.Alignment(0, 0),
                        )
                    ],
                    padding=20,
                )
            )
            page.update()

    def view_pop(e):
        page.views.pop()
        top_view = page.views[-1]
        navigate(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    if not page.route:
        page.route = "/"
    route_change(None)


if __name__ == "__main__":
    ft.run(main)
