"""Server list page - Server list page

Display list with filtering and sorting support
"""

import logging
from typing import Optional

import flet as ft

from application.services import DiscoveryService, PreferenceService
from domain.discovery.value_objects import (
    FilterCriteria,
    SortOption,
    ServerTag,
)
from domain.discovery.entities import Server
from infrastructure.api import ApiKeyMissingError, InvalidApiKeyError
from infrastructure.config.constants import DEFAULT_AVATAR_URL
from infrastructure.di import get_container
from presentation.components import Toast
from presentation.tag_mappings import SERVER_TAGS, SERVER_TAG_FILTERS
from presentation.url_helper import open_url


logger = logging.getLogger(__name__)


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
        self.toast = Toast(self.page)

        # UI組件
        self.server_list = ft.ListView(
            spacing=10,
            padding=20,
            expand=True,
            scroll_interval=150,
            on_scroll=self._on_list_scroll,
        )
        self.search_field = ft.TextField(
            label="搜尋伺服器...",
            prefix_icon=ft.Icons.SEARCH,
            on_submit=lambda _: self.page.run_task(self._on_search),
        )
        self.sort_dropdown = ft.Dropdown(
            label="排序",
            options=[
                ft.dropdown.Option("default", "預設排序"),
                ft.dropdown.Option("mostVotes", "最多投票"),
                ft.dropdown.Option("mostMembers", "最多人數"),
                ft.dropdown.Option("mostActive", "最高活躍度"),
            ],
            value="default",
            width=150,
            on_select=lambda _: self.page.run_task(self._load_servers),
        )

        self.progress = ft.ProgressBar(visible=False)
        self._current_filter: Optional[FilterCriteria] = None
        self._items: list[Server] = []
        self._rendered_count = 0
        self._page_size = 30
        self._more_button = ft.Container(
            content=ft.TextButton(
                "顯示更多",
                icon=ft.Icons.EXPAND_MORE,
                on_click=lambda _: self._show_more(),
            ),
            alignment=ft.Alignment(0, 0),
            padding=ft.padding.only(bottom=10),
        )

        # Tag filter state
        self._selected_tags: set[str] = set()
        self.tag_chips: dict[str, ft.Chip] = {}
        self.tag_chips_row: Optional[ft.Row] = None
        self.clear_tags_button = ft.TextButton(
            "清除",
            icon=ft.Icons.CLOSE,
            tooltip="清除標籤篩選",
            visible=False,
            on_click=self._clear_tags,
        )

    def build(self) -> ft.Control:
        """Build page UI"""
        self.page.run_task(self._load_servers)

        return ft.Column(
            [
                ft.AppBar(
                    title=ft.Text("DCTW 伺服器清單"),
                    center_title=False,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    actions=[
                        ft.IconButton(
                            icon=ft.Icons.REFRESH,
                            tooltip="重新整理",
                            on_click=lambda _: self.page.run_task(self._refresh),
                        )
                    ],
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
                self._build_tag_filter(),
                self.progress,
                ft.Container(self.server_list, expand=True),
            ],
            expand=True,
        )

    def _build_tag_filter(self) -> ft.Control:
        """Create the tag filter chips (same tags as the official website)."""
        self.tag_chips_row = ft.Row(
            [
                self._create_tag_chip(name, *SERVER_TAGS[name])
                for name in SERVER_TAG_FILTERS
                if name in SERVER_TAGS
            ],
            spacing=6,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        return ft.Container(
            content=ft.Row(
                [self.tag_chips_row, self.clear_tags_button],
                spacing=4,
            ),
            padding=ft.padding.only(left=15, right=15, bottom=6),
        )

    def _create_tag_chip(self, name: str, label: str, icon) -> ft.Chip:
        chip = ft.Chip(
            label=ft.Text(label, size=12),
            leading=ft.Icon(icon, size=16),
            selected=False,
            show_checkmark=True,
            on_select=lambda e, tag_name=name: self._on_tag_select(tag_name, e),
        )
        self.tag_chips[name] = chip
        return chip

    def _on_tag_select(self, name: str, e) -> None:
        chip = self.tag_chips.get(name)
        if chip is None:
            return

        chip.selected = not bool(chip.selected)
        if chip.selected:
            self._selected_tags.add(name)
        else:
            self._selected_tags.discard(name)

        self.clear_tags_button.visible = bool(self._selected_tags)
        self.tag_chips_row.update()
        self.clear_tags_button.update()
        self.page.run_task(self._load_servers)

    def _clear_tags(self, e) -> None:
        if not self._selected_tags:
            return

        self._selected_tags.clear()
        for chip in self.tag_chips.values():
            chip.selected = False

        self.clear_tags_button.visible = False
        self.tag_chips_row.update()
        self.clear_tags_button.update()
        self.page.run_task(self._load_servers)

    async def _refresh(self) -> None:
        """Clear the cached data and reload the list."""
        try:
            await self.discovery_service.clear_all_caches()
        except Exception:
            logger.exception("Failed to clear caches before refresh")

        await self._load_servers()
        self.toast.show("已重新整理")

    async def _load_servers(self):
        """Load list"""
        self.progress.visible = True
        self.page.update()

        try:
            search_text = self.search_field.value if self.search_field.value else None
            preferences = await self.preference_service.load_preferences()
            nsfw_enabled = bool(preferences.nsfw_filter)

            self._current_filter = FilterCriteria(
                tags=[
                    ServerTag(name)
                    for name in SERVER_TAG_FILTERS
                    if name in self._selected_tags
                ],
                search_text=search_text,
                nsfw_enabled=nsfw_enabled,
            )

            sort_option = SortOption.from_string(self.sort_dropdown.value)
            servers = await self.discovery_service.list_servers(
                filter_criteria=self._current_filter,
                sort_option=sort_option,
            )

            self._render_server_list(servers)

        except ApiKeyMissingError:
            self._render_message(
                "尚未設定 API Key\n"
                "請到「設定」頁面點擊「從剪貼簿貼上 API Key」。"
            )
        except InvalidApiKeyError:
            self._render_message(
                "API Key 無效或已失效\n"
                "請到 DCTW 後台重新複製 API KEY，再到「設定」頁面貼上。"
            )
        except Exception as e:
            print(f"Error loading servers: {e}")
            self._render_message(f"載入失敗: {str(e)}")

        finally:
            self.progress.visible = False
            self.page.update()

    def _render_server_list(self, servers: list[Server]):
        """Render the first page of the list"""
        self._items = list(servers)
        self._rendered_count = 0
        self.server_list.controls.clear()

        if not self._items:
            self.server_list.controls.append(
                ft.Container(
                    content=ft.Text("找不到伺服器 :(", size=16, color=ft.Colors.GREY),
                    alignment=ft.Alignment(0, 0),
                    padding=50,
                )
            )
        else:
            self._append_server_page()

        self.page.update()

    def _append_server_page(self):
        """Append the next page of servers to the list"""
        end = min(self._rendered_count + self._page_size, len(self._items))
        for server in self._items[self._rendered_count : end]:
            self.server_list.controls.append(self._create_server_card(server))
        self._rendered_count = end

        if self._more_button in self.server_list.controls:
            self.server_list.controls.remove(self._more_button)
        if self._rendered_count < len(self._items):
            self.server_list.controls.append(self._more_button)

    def _show_more(self):
        """Show the next page of servers"""
        self._append_server_page()
        self.server_list.update()

    def _on_list_scroll(self, e: ft.OnScrollEvent):
        """Load the next page when the list is scrolled to the bottom"""
        if not self._items or self._rendered_count >= len(self._items):
            return

        max_extent = e.max_scroll_extent or 0
        if max_extent and e.pixels >= max_extent - 300:
            self._append_server_page()
            self.server_list.update()

    def _render_message(self, message: str):
        """Render a status message in place of the list"""
        self._items = []
        self._rendered_count = 0
        self.server_list.controls.clear()
        self.server_list.controls.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.ERROR_OUTLINE, size=40, color=ft.Colors.GREY),
                        ft.Text(
                            message,
                            size=15,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    spacing=12,
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                alignment=ft.Alignment(0, 0),
                padding=40,
            )
        )
        self.page.update()

    def _create_server_card(self, server: Server) -> ft.Control:
        """Create card"""
        tag_chips = []
        for tag in server.tags[:3]:
            display_name, icon = SERVER_TAGS.get(tag.name, (tag.name, ft.Icons.TAG))
            tag_chips.append(
                ft.Chip(
                    label=ft.Text(display_name),
                    leading=ft.Icon(icon, size=16),
                    bgcolor=ft.Colors.GREEN_100,
                )
            )

        badges = []
        if server.is_partnered:
            badges.append(
                ft.Icon(ft.Icons.WORKSPACE_PREMIUM, color=ft.Colors.PURPLE, size=16)
            )
        if server.pinned:
            badges.append(
                ft.Icon(ft.Icons.PUSH_PIN, color=ft.Colors.ORANGE, size=16)
            )

        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.CircleAvatar(
                                    foreground_image_src=server.icon.value,
                                    background_image_src=DEFAULT_AVATAR_URL,
                                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
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
                                                    expand=True,
                                                    max_lines=1,
                                                    overflow=ft.TextOverflow.ELLIPSIS,
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
                                    on_click=lambda _, s=server: open_url(
                                        self.page, s.links.invite.value
                                    ),
                                ),
                                ft.OutlinedButton(
                                    "詳情",
                                    on_click=lambda _, s=server: self._show_server_detail(s),
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
        self.page.run_task(self._navigate_to_server_detail, server)

    async def _navigate_to_server_detail(self, server: Server):
        """Navigate to server detail page"""
        await self.page.push_route(f"/server/{server.id}")

    def _show_server_dialog(self, server: Server):
        """Show details dialog"""
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
                    on_click=lambda _, s=server: open_url(
                        self.page, s.links.invite.value
                    ),
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
        self.page.show_dialog(
            ft.SnackBar(
                content=ft.Text(message),
                bgcolor=ft.Colors.ERROR,
            )
        )
