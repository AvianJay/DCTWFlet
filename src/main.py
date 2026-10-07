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
            page.run_task(page.push_route, route)
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
    tab_stack = ft.Stack(expand=True)

    def tab_content(index: int) -> ft.Control:
        """Return the content of a tab, building it on first use."""
        control = built_tabs.get(index)
        if control is not None:
            return control

        if index == 0:
            control = bot_page.build()
        elif index == 1:
            control = server_page.build()
        elif index == 2:
            control = template_page.build()
        else:
            control = settings_page.build()

        control.visible = False
        built_tabs[index] = control
        tab_stack.controls.append(control)
        return control

    def reload_data_tabs() -> None:
        """Rebuild the data tabs after the API key changed."""
        for index in (0, 1, 2):
            control = built_tabs.pop(index, None)
            if control in tab_stack.controls:
                tab_stack.controls.remove(control)
        select_tab(current_tab[0])
        page.update()

    settings_page = SettingsPage(page, on_data_changed=reload_data_tabs)

    def select_tab(index: int) -> None:
        current_tab[0] = index
        page.title = tab_titles[index]
        tab_content(index)
        for tab_index, control in built_tabs.items():
            control.visible = tab_index == index
        update_tab_colors()

    # Custom compact bottom bar (the Material one is always too tall).
    tab_icons = (
        (ft.Icons.SMART_TOY_OUTLINED, ft.Icons.SMART_TOY, "機器人"),
        (ft.Icons.DNS_OUTLINED, ft.Icons.DNS, "伺服器"),
        (ft.Icons.COPY_ALL_OUTLINED, ft.Icons.COPY_ALL, "模板"),
        (ft.Icons.SETTINGS_OUTLINED, ft.Icons.SETTINGS, "設置"),
    )
    tab_controls: list[tuple[ft.Container, ft.Icon, ft.Text, ft.Icon, ft.Icon]] = []

    def update_tab_colors() -> None:
        for index, (container, icon, label, icon_off, icon_on) in enumerate(
            tab_controls
        ):
            is_selected = index == current_tab[0]
            color = (
                ft.Colors.ON_SECONDARY_CONTAINER
                if is_selected
                else ft.Colors.ON_SURFACE_VARIANT
            )
            container.bgcolor = ft.Colors.SECONDARY_CONTAINER if is_selected else None
            icon.name = icon_on if is_selected else icon_off
            icon.color = color
            label.color = color

    def create_tab_button(index: int) -> ft.Control:
        icon_off, icon_on, text = tab_icons[index]
        icon = ft.Icon(icon_off, size=26, color=ft.Colors.ON_SURFACE_VARIANT)
        label = ft.Text(text, size=14, color=ft.Colors.ON_SURFACE_VARIANT)

        def on_click(e, tab_index=index):
            select_tab(tab_index)
            page.update()

        container = ft.Container(
            content=ft.Column(
                [icon, label],
                spacing=1,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            expand=True,
            height=62,
            border_radius=14,
            alignment=ft.Alignment(0, 0),
            ink=True,
            on_click=on_click,
        )
        tab_controls.append((container, icon, label, icon_off, icon_on))
        return container

    navigation_bar = ft.Container(
        content=ft.Row(
            [create_tab_button(index) for index in range(len(tab_icons))],
            spacing=4,
        ),
        height=74,
        padding=ft.padding.symmetric(horizontal=6, vertical=6),
        bgcolor=ft.Colors.SURFACE_CONTAINER,
        alignment=ft.Alignment(0, 0),
    )

    def create_home_view() -> ft.View:
        select_tab(current_tab[0])

        return ft.View(
            route="/",
            controls=[
                ft.Column(
                    [tab_stack, navigation_bar],
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

        page.run_task(show_api_key_onboarding)


if __name__ == "__main__":
    ft.run(main)
