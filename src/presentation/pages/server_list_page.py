"""Server list page - Server list page

Display list with filtering and sorting support
"""

import flet as ft
import asyncio
from typing import Optional

from application.services import DiscoveryService, PreferenceService
from domain.discovery.value_objects import (
    FilterCriteria,
    SortOption,
    ServerTag,
)
from domain.discovery.entities import Server
from infrastructure.di import get_container


class ServerListPage:
    """Server list page"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.container = get_container()
        self.discovery_service: DiscoveryService = self.container.resolve(
            DiscoveryService
        )
        self.preference_service: PreferenceService = self.container.resolve(
            PreferenceService
        )

        # UI組件
        self.server_list = ft.ListView(spacing=10, padding=20, expand=True)
        self.search_field = ft.TextField(
            label="搜尋Server",
            prefix_icon=ft.Icons.SEARCH,
            on_submit=lambda _: self.page.run_task(self._on_search),
        )
        self.sort_dropdown = ft.Dropdown(
            label="排序",
            options=[
                ft.dropdown.Option("newest", "最新"),
                ft.dropdown.Option("votes", "投票數"),
                ft.dropdown.Option("members", "成員數"),
                ft.dropdown.Option("bumped", "最近Bump"),
            ],
            value="newest",
            width=150,
            on_change=lambda _: self.page.run_task(self._load_servers),
        )

        self.progress = ft.ProgressBar(visible=False)
        self._current_filter: Optional[FilterCriteria] = None

    def build(self) -> ft.Control:
        """Build page UI"""
        self.page.run_task(self._load_servers)

        return ft.Column(
            [
                ft.Container(
                    content=ft.Text(
                        "Discord Servers", size=24, weight=ft.FontWeight.BOLD
                    ),
                    bgcolor=ft.Colors.SURFACE,
                    padding=15,
                ),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(self.search_field, expand=True),
                            self.sort_dropdown,
                        ],
                        spacing=10,
                        wrap=False,
                        run_spacing=10,
                    ),
                    padding=15,
                ),
                self.progress,
                ft.Container(self.server_list, expand=True),
            ],
            expand=True,
        )

    async def _load_servers(self):
        """Load list"""
        self.progress.visible = True
        self.page.update()

        try:
            search_text = self.search_field.value if self.search_field.value else None
            preferences = await self.preference_service.load_preferences()
            nsfw_enabled = bool(preferences.nsfw_filter)

            self._current_filter = FilterCriteria(
                search_text=search_text,
                nsfw_enabled=nsfw_enabled,
            )

            sort_option = SortOption.from_string(self.sort_dropdown.value)
            servers = await self.discovery_service.list_servers(
                filter_criteria=self._current_filter,
                sort_option=sort_option,
            )

            self._render_server_list(servers)

        except Exception as e:
            print(f"Error loading servers: {e}")
            self._show_error(f"載入失敗: {str(e)}")

        finally:
            self.progress.visible = False
            self.page.update()

    def _render_server_list(self, servers: list[Server]):
        """Render list"""
        self.server_list.controls.clear()

        if not servers:
            self.server_list.controls.append(
                ft.Container(
                    content=ft.Text("沒有找到Server", size=16, color=ft.Colors.GREY),
                    alignment=ft.alignment.center,
                    padding=50,
                )
            )
        else:
            for server in servers:
                self.server_list.controls.append(self._create_server_card(server))

        self.page.update()

    def _create_server_card(self, server: Server) -> ft.Control:
        """Create card"""
        tag_chips = [
            ft.Chip(label=ft.Text(tag.name), bgcolor=ft.Colors.GREEN_100)
            for tag in server.tags[:3]
        ]

        badges = []
        if server.is_partnered:
            badges.append(
                ft.Icon(ft.Icons.WORKSPACE_PREMIUM, color=ft.Colors.PURPLE, size=16)
            )

        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.CircleAvatar(
                                    foreground_image_src=server.icon.value,
                                    radius=25,
                                ),
                                ft.Column(
                                    [
                                        ft.Row(
                                            [
                                                ft.Text(
                                                    server.name,
                                                    size=18,
                                                    weight=ft.FontWeight.BOLD,
                                                ),
                                                *badges,
                                            ],
                                            spacing=5,
                                        ),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                            ],
                            spacing=15,
                        ),
                        ft.Text(
                            server.description,
                            size=14,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Row(tag_chips, spacing=5, wrap=True),
                        ft.Row(
                            [
                                ft.Row(
                                    [
                                        ft.Icon(ft.Icons.STAR, size=16),
                                        ft.Text(str(server.statistics.votes), size=14),
                                    ],
                                    spacing=5,
                                ),
                                ft.Row(
                                    [
                                        ft.Icon(ft.Icons.PEOPLE, size=16),
                                        ft.Text(
                                            f"{server.statistics.members} 成員",
                                            size=14,
                                        ),
                                    ],
                                    spacing=5,
                                ),
                            ],
                            spacing=20,
                        ),
                        ft.Row(
                            [
                                ft.ElevatedButton(
                                    "加入",
                                    icon=ft.Icons.LOGIN,
                                    on_click=lambda _: self.page.launch_url(
                                        server.links.invite.value
                                    ),
                                ),
                                ft.OutlinedButton(
                                    "詳情",
                                    on_click=lambda _, s=server: self._show_server_detail(
                                        s
                                    ),
                                ),
                            ],
                            spacing=10,
                        ),
                    ],
                    spacing=10,
                ),
                padding=15,
            ),
        )

    def _show_server_detail(self, server: Server):
        """Show details"""
        dialog = ft.AlertDialog(
            title=ft.Text(server.name),
            content=ft.Column(
                [
                    ft.Image(src=server.icon.value, width=100, height=100),
                    ft.Text(f"描述: {server.description}"),
                    ft.Text(f"投票: {server.statistics.votes}"),
                    ft.Text(f"成員: {server.statistics.members}"),
                    ft.Text(f"標籤: {', '.join([tag.name for tag in server.tags])}"),
                ],
                tight=True,
                scroll=ft.ScrollMode.AUTO,
                height=300,
            ),
            actions=[
                ft.TextButton("關閉", on_click=lambda _: self._close_dialog(dialog)),
                ft.ElevatedButton(
                    "加入",
                    on_click=lambda _: self.page.launch_url(server.links.invite.value),
                ),
            ],
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def _close_dialog(self, dialog):
        """Close dialog"""
        dialog.open = False
        self.page.update()

    async def _on_search(self):
        """Search event handler"""
        await self._load_servers()

    def _show_error(self, message: str):
        """Show error message"""
        snack = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.Colors.ERROR,
        )
        self.page.snack_bar = snack
        snack.open = True
        self.page.update()
