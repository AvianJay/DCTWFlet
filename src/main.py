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
from presentation.components import ApiKeyDialog
from infrastructure.di import get_container
from infrastructure.api import DctwApiClient
from infrastructure.image import ImageServer
from application.services import DiscoveryService, PreferenceService
from infrastructure.config import initialize_settings


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _show_startup_error(
    page: ft.Page, error: Exception, console_log_file: str | None = None
) -> None:
    controls = [
        ft.Icon(
            ft.Icons.ERROR_OUTLINE,
            size=56,
            color=ft.Colors.ERROR,
        ),
        ft.Text(
            "App startup failed",
            size=22,
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER,
        ),
        ft.Text(str(error), selectable=True, text_align=ft.TextAlign.CENTER),
    ]

    if console_log_file:
        controls.append(
            ft.Text(
                f"console.log: {console_log_file}",
                selectable=True,
                text_align=ft.TextAlign.CENTER,
            )
        )

    page.views.clear()
    page.views.append(
        ft.View(
            route="/",
            controls=[
                ft.Container(
                    content=ft.Column(
                        controls,
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
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


async def _configure_runtime_settings(page: ft.Page) -> str | None:
    console_log_file = None

    if page.web:
        initialize_settings()
        return console_log_file

    storage_paths = ft.StoragePaths()
    support_dir = await storage_paths.get_application_support_directory()
    cache_dir = await storage_paths.get_application_cache_directory()
    console_log_file = await storage_paths.get_console_log_filename()

    support_path = Path(support_dir)
    cache_path = Path(cache_dir)

    initialize_settings(
        data_dir=support_path,
        cache_dir=cache_path,
        image_cache_dir=cache_path / "images",
        log_dir=cache_path / "logs",
    )

    logger.info("Configured runtime storage: support=%s cache=%s", support_path, cache_path)
    return console_log_file


async def main(page: ft.Page):
    """Application main entry point."""

    console_log_file = None

    try:
        logger.info("Starting app on platform: %s", page.platform)
        console_log_file = await _configure_runtime_settings(page)
        container = get_container()
    except Exception as ex:
        logger.exception("Startup initialization failed")
        _show_startup_error(page, ex, console_log_file)
        return

    def navigate(route: str):
        if hasattr(page, "push_route"):
            asyncio.create_task(page.push_route(route))
        else:
            page.go(route)

    page.title = "DCTW"
    page.padding = 0
    page.bgcolor = ft.Colors.SURFACE

    pref_service: PreferenceService = container.resolve(PreferenceService)
    prefs = None
    try:
        prefs = await pref_service.load_preferences()
        page.theme_mode = prefs.theme.value
    except Exception as e:
        logger.exception("Failed to load preferences")
        logger.error(str(e))
        page.theme_mode = ft.ThemeMode.SYSTEM

    page.theme = ft.Theme(navigation_bar_theme=ft.NavigationBarTheme(height=56))
    page.dark_theme = ft.Theme(navigation_bar_theme=ft.NavigationBarTheme(height=56))

    image_server: ImageServer = container.resolve(ImageServer)

    async def start_image_server():
        try:
            await image_server.start()
        except Exception:
            logger.exception("Image server failed to start")

    asyncio.create_task(start_image_server())

    current_tab = [0]

    tab_titles = (
        "DCTW - 機器人清單",
        "DCTW - 伺服器清單",
        "DCTW - 模板清單",
        "DCTW - 設置",
    )

    bot_page = BotListPage(page)
    server_page = ServerListPage(page)
    template_page = TemplateListPage(page)

    # Every tab is built once and kept alive. Rebuilding the pages on each tab
    # switch re-parented the same widgets and started competing background
    # tasks, which could leave the UI stuck on the previous tab.
    built_tabs: dict[int, ft.Control] = {}
    content_container = ft.Container(expand=True)

    def tab_content(index: int) -> ft.Control:
        """Return the content of a tab, building it on first use."""
        if index not in built_tabs:
            if index == 0:
                built_tabs[index] = bot_page.build()
            elif index == 1:
                built_tabs[index] = server_page.build()
            elif index == 2:
                built_tabs[index] = template_page.build()
            else:
                built_tabs[index] = settings_page.build()
        return built_tabs[index]

    def reload_data_tabs() -> None:
        """Rebuild the data tabs after the API key changed."""
        for index in (0, 1, 2):
            built_tabs.pop(index, None)
        if current_tab[0] in (0, 1, 2):
            content_container.content = tab_content(current_tab[0])
            page.update()

    settings_page = SettingsPage(page, on_data_changed=reload_data_tabs)

    def select_tab(index: int) -> None:
        current_tab[0] = index
        page.title = tab_titles[index]
        content_container.content = tab_content(index)

    def on_tab_changed(e):
        """Tab change event handler"""
        select_tab(e.control.selected_index)
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
                label="模板",
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

    def create_home_view() -> ft.View:
        navigation_bar.selected_index = current_tab[0]
        select_tab(current_tab[0])

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
                title=ft.Text("模板詳情"),
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

    if prefs is not None and not prefs.api_key.is_set:

        async def show_api_key_onboarding():
            await asyncio.sleep(1.0)
            try:
                dialog = ApiKeyDialog(
                    page=page,
                    preference_service=pref_service,
                    discovery_service=container.resolve(DiscoveryService),
                    api_client=container.resolve(DctwApiClient),
                    on_saved=reload_data_tabs,
                )
                dialog.show(dismissible=True)
            except Exception:
                logger.exception("Failed to show API key onboarding dialog")

        asyncio.create_task(show_api_key_onboarding())


if __name__ == "__main__":
    ft.run(main)
