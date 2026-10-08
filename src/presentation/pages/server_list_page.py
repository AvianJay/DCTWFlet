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
from infrastructure.di import get_container
from presentation.components import (
    TagFilterDialog,
    Toast,
    build_avatar,
    build_partner_badge,
    build_server_type_badge,
)
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
            hint_text="搜尋伺服器...",
            prefix_icon=ft.Icons.SEARCH,
            on_submit=lambda _: self.page.run_task(self._on_search),
        )
        self.sort_dropdown = ft.Dropdown(
            label="排序",
            options=[
                ft.dropdown.Option("default", "預設排序"),
                ft.dropdown.Option("mostVotes", "最多投票"),
                ft.dropdown.Option("mostMembers", "最多人數"),
            ],
            value="default",
            width=150,
            on_select=lambda _: self.page.run_task(self._load_servers),
        )
        self.search_icon = ft.IconButton(
            icon=ft.Icons.SEARCH,
            tooltip="搜尋",
            on_click=self._toggle_search,
        )
        self.search_box = ft.Container(
            self.search_field, expand=True, visible=False
        )

        self.progress = ft.ProgressBar(visible=False)
        self._current_filter: Optional[FilterCriteria] = None
        self._items: list[Server] = []
        self._rendered_count = 0
        self._page_size = 30
        self._load_seq = 0
        self._more_button = ft.Container(
            content=ft.TextButton(
                "顯示更多",
                icon=ft.Icons.EXPAND_MORE,
                on_click=lambda _: self._show_more(),
            ),
            alignment=ft.Alignment(0, 0),
            padding=ft.padding.only(bottom=10),
        )

        # Tag filter state (multi-select, edited in the funnel dialog)
        self._selected_tags: set[str] = set()
        self.filter_icon = ft.IconButton(
            icon=ft.Icons.FILTER_ALT,
            tooltip="篩選標籤",
            icon_color=ft.Colors.ON_SURFACE_VARIANT,
            on_click=self._open_tag_filter,
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
                        self.search_icon,
                        self.filter_icon,
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
                            self.search_box,
                            self.sort_dropdown,
                        ],
                        spacing=10,
                        wrap=False,
                        run_spacing=10,
                        alignment=ft.MainAxisAlignment.END,
                    ),
                    padding=15,
                ),
                self.progress,
                ft.Container(self.server_list, expand=True),
            ],
            expand=True,
        )

    def _open_tag_filter(self, e=None) -> None:
        """Open the funnel dialog that lists every official tag."""
        TagFilterDialog(
            self.page,
            "篩選標籤",
            SERVER_TAGS,
            SERVER_TAG_FILTERS,
            self._selected_tags,
            self._apply_tags,
        ).show()

    def _apply_tags(self, selected: set[str]) -> None:
        """Apply the selection made inside the funnel dialog."""
        self._selected_tags = set(selected)
        self._sync_filter_icon()
        self.page.run_task(self._load_servers)

    def show_related_tag(self, tag_name: str) -> None:
        """Show the servers of one tag (called when a detail page tag is tapped)."""
        tag = (tag_name or "").strip().lower()
        self._selected_tags = {tag} if tag in SERVER_TAG_FILTERS else set()
        if self.search_field.value:
            self.search_field.value = ""
        self._sync_filter_icon()
        self.page.run_task(self._load_servers)

    def _sync_filter_icon(self) -> None:
        """Show the active tag count on the funnel icon."""
        count = len(self._selected_tags)
        self.filter_icon.icon_color = (
            ft.Colors.PRIMARY if count else ft.Colors.ON_SURFACE_VARIANT
        )
        self.filter_icon.tooltip = (
            f"篩選標籤（已選 {count}）" if count else "篩選標籤"
        )
        self.filter_icon.badge = (
            ft.Badge(
                label=str(count),
                bgcolor=ft.Colors.PRIMARY,
                text_color=ft.Colors.ON_PRIMARY,
            )
            if count
            else None
        )
        try:
            self.filter_icon.update()
        except Exception:
            logger.debug("Filter icon is not mounted yet")

    def _toggle_search(self, e=None) -> None:
        """Show or hide the search box (opened from the magnifier icon)."""
        self.search_box.visible = not self.search_box.visible
        if self.search_box.visible:
            self.search_icon.icon = ft.Icons.CLOSE
            self.search_box.update()
            self.search_icon.update()
            self.page.run_task(self.search_field.focus)
            return

        self.search_icon.icon = ft.Icons.SEARCH
        if self.search_field.value:
            self.search_field.value = ""
        self.search_box.update()
        self.search_icon.update()
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
        self._load_seq += 1
        seq = self._load_seq
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

            # A newer load started while this one was in flight: drop the
            # stale result so the latest filter always wins.
            if seq != self._load_seq:
                return

            self._render_server_list(servers)

        except ApiKeyMissingError:
            if seq == self._load_seq:
                self._render_message(
                    "尚未設定 API Key\n"
                    "請到「設定」頁面點擊「從剪貼簿貼上 API Key」。"
                )
        except InvalidApiKeyError:
            if seq == self._load_seq:
                self._render_message(
                    "API Key 無效或已失效\n"
                    "請到 DCTW 後台重新複製 API KEY，再到「設定」頁面貼上。"
                )
        except Exception as e:
            if seq == self._load_seq:
                print(f"Error loading servers: {e}")
                self._render_message(f"載入失敗: {str(e)}")

        finally:
            if seq == self._load_seq:
                self.progress.visible = False
                self.page.update()

    def _render_server_list(self, servers: list[Server]):
        """Render the first page of the list"""
        self._items = list(servers)
        self._rendered_count = 0
        self.server_list.controls.clear()

        if not self._items:
            self.server_list.controls.append(self._create_empty_state())
        else:
            self._append_server_page()

        self.page.update()

    def _has_active_filter(self) -> bool:
        """Is a tag filter or a search text currently applied?"""
        return bool(self._selected_tags) or bool(
            (self.search_field.value or "").strip()
        )

    def _create_empty_state(self) -> ft.Control:
        """Friendly placeholder shown when nothing can be displayed."""
        active = self._has_active_filter()
        children: list[ft.Control] = [
            ft.Icon(
                ft.Icons.SEARCH_OFF, size=44, color=ft.Colors.ON_SURFACE_VARIANT
            ),
            ft.Text(
                "沒有符合條件的伺服器",
                size=16,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Text(
                "試著調整搜尋文字或改用其他標籤。"
                if active
                else "目前沒有可顯示的伺服器，請稍後再試。",
                size=13,
                color=ft.Colors.ON_SURFACE_VARIANT,
                text_align=ft.TextAlign.CENTER,
            ),
        ]
        if active:
            children.append(
                ft.FilledButton(
                    "清除篩選",
                    icon=ft.Icons.FILTER_ALT_OFF,
                    on_click=lambda _: self.page.run_task(self._clear_filters),
                )
            )
        return ft.Container(
            content=ft.Column(
                children,
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            alignment=ft.Alignment(0, 0),
            padding=ft.padding.symmetric(vertical=60, horizontal=24),
        )

    async def _clear_filters(self) -> None:
        """Reset the search text and the tag selection, then reload."""
        self._selected_tags.clear()
        if self.search_field.value:
            self.search_field.value = ""
        self._sync_filter_icon()
        await self._load_servers()

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

        # The type pill mirrors the badge of the official website; it sits
        # right next to the name, where the bot cards show the partner pill.
        badges = [build_server_type_badge(server.features)]
        if server.is_partnered:
            badges.append(build_partner_badge())
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
                                build_avatar(server.icon.value, radius=25),
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
                                        ft.Icon(ft.Icons.HOW_TO_VOTE, size=16),
                                        ft.Text(str(server.statistics.votes), size=14),
                                    ],
                                    spacing=5,
                                ),
                                ft.Row(
                                    [
                                        ft.Icon(ft.Icons.PEOPLE, size=16),
                                        ft.Text(
                                            f"{server.online_members:,}",
                                            size=14,
                                            color=ft.Colors.GREEN,
                                        ),
                                        ft.Text(
                                            "/",
                                            size=14,
                                            color=ft.Colors.ON_SURFACE_VARIANT,
                                        ),
                                        ft.Text(
                                            f"{server.statistics.members:,}",
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
