"""Bot list page - Bot list page

Display list with filtering and sorting support
"""

import logging
from typing import Optional

import flet as ft

from application.services import DiscoveryService, PreferenceService
from domain.discovery.value_objects import (
    BotTag,
    FilterCriteria,
    SortOption,
)
from domain.discovery.entities import Bot
from infrastructure.api import ApiKeyMissingError, InvalidApiKeyError
from infrastructure.config.constants import DEFAULT_AVATAR_URL
from infrastructure.di import get_container
from presentation.components import Toast
from presentation.tag_mappings import BOT_TAGS, BOT_TAG_FILTERS
from presentation.url_helper import open_url


logger = logging.getLogger(__name__)


class BotListPage:
    """Bot list page"""

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
        self.bot_list = ft.ListView(
            spacing=10,
            padding=20,
            expand=True,
            scroll_interval=150,
            on_scroll=self._on_list_scroll,
        )
        self.search_field = ft.TextField(
            label="搜尋機器人...",
            prefix_icon=ft.Icons.SEARCH,
            on_submit=lambda _: self.page.run_task(self._on_search),
        )
        self.sort_dropdown = ft.Dropdown(
            label="排序",
            options=[
                ft.dropdown.Option("default", "預設排序"),
                ft.dropdown.Option("mostVotes", "最多投票"),
                ft.dropdown.Option("mostServers", "最多伺服器"),
                ft.dropdown.Option("mostActive", "最高活躍度"),
            ],
            value="default",
            width=150,
            on_select=lambda _: self.page.run_task(self._load_bots),
        )
        self.progress = ft.ProgressBar(visible=False)

        self._current_filter: Optional[FilterCriteria] = None
        self._items: list[Bot] = []
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
        self.page.run_task(self._load_bots)

        return ft.Column(
            [
                ft.AppBar(
                    title=ft.Text("DCTW 機器人清單"),
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
                    padding=10,
                ),
                self._build_tag_filter(),
                self.progress,
                ft.Container(self.bot_list, expand=True),
            ],
            expand=True,
        )

    def _build_tag_filter(self) -> ft.Control:
        """Create the tag filter chips (same tags as the official website)."""
        self.tag_chips_row = ft.Row(
            [
                self._create_tag_chip(name, *BOT_TAGS[name])
                for name in BOT_TAG_FILTERS
                if name in BOT_TAGS
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
            padding=ft.padding.only(left=10, right=10, bottom=6),
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
        self.page.run_task(self._load_bots)

    def _clear_tags(self, e) -> None:
        if not self._selected_tags:
            return

        self._selected_tags.clear()
        for chip in self.tag_chips.values():
            chip.selected = False

        self.clear_tags_button.visible = False
        self.tag_chips_row.update()
        self.clear_tags_button.update()
        self.page.run_task(self._load_bots)

    async def _refresh(self) -> None:
        """Clear the cached data and reload the list."""
        try:
            await self.discovery_service.clear_all_caches()
        except Exception:
            logger.exception("Failed to clear caches before refresh")

        await self._load_bots()
        self.toast.show("已重新整理")

    async def _load_bots(self):
        """Load list"""
        self.progress.visible = True
        self.page.update()

        try:
            search_text = self.search_field.value if self.search_field.value else None
            preferences = await self.preference_service.load_preferences()
            nsfw_enabled = bool(preferences.nsfw_filter)

            self._current_filter = FilterCriteria(
                tags=[
                    BotTag(name)
                    for name in BOT_TAG_FILTERS
                    if name in self._selected_tags
                ],
                search_text=search_text,
                nsfw_enabled=nsfw_enabled,
            )

            sort_option = SortOption.from_string(self.sort_dropdown.value)

            bots = await self.discovery_service.list_bots(
                filter_criteria=self._current_filter,
                sort_option=sort_option,
            )

            # Render list
            self._render_bot_list(bots)

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
            self._render_message(f"載入失敗: {str(e)}")

        finally:
            self.progress.visible = False
            self.page.update()

    def _render_bot_list(self, bots: list[Bot]):
        """Render the first page of the list"""
        self._items = list(bots)
        self._rendered_count = 0
        self.bot_list.controls.clear()

        if not self._items:
            self.bot_list.controls.append(
                ft.Container(
                    content=ft.Text("找不到機器人 :(", size=16, color=ft.Colors.GREY),
                    alignment=ft.Alignment(0, 0),
                    padding=50,
                )
            )
        else:
            self._append_bot_page()

        self.page.update()

    def _append_bot_page(self):
        """Append the next page of bots to the list"""
        end = min(self._rendered_count + self._page_size, len(self._items))
        for bot in self._items[self._rendered_count : end]:
            self.bot_list.controls.append(self._create_bot_card(bot))
        self._rendered_count = end

        if self._more_button in self.bot_list.controls:
            self.bot_list.controls.remove(self._more_button)
        if self._rendered_count < len(self._items):
            self.bot_list.controls.append(self._more_button)

    def _show_more(self):
        """Show the next page of bots"""
        self._append_bot_page()
        self.bot_list.update()

    def _on_list_scroll(self, e: ft.OnScrollEvent):
        """Load the next page when the list is scrolled to the bottom"""
        if not self._items or self._rendered_count >= len(self._items):
            return

        max_extent = e.max_scroll_extent or 0
        if max_extent and e.pixels >= max_extent - 300:
            self._append_bot_page()
            self.bot_list.update()

    def _render_message(self, message: str):
        """Render a status message in place of the list"""
        self._items = []
        self._rendered_count = 0
        self.bot_list.controls.clear()
        self.bot_list.controls.append(
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

    def _create_bot_card(self, bot: Bot) -> ft.Control:
        """Create card"""
        status_colors = {
            "online": ft.Colors.GREEN,
            "idle": ft.Colors.YELLOW,
            "dnd": ft.Colors.RED,
            "offline": ft.Colors.GREY,
        }

        tag_chips = []
        for tag in bot.tags[:3]:
            display_name, icon = BOT_TAGS.get(tag.name, (tag.name, ft.Icons.TAG))
            tag_chips.append(
                ft.Chip(
                    label=ft.Text(display_name),
                    leading=ft.Icon(icon, size=16),
                    bgcolor=ft.Colors.BLUE_100,
                )
            )

        badges = []
        if bot.verified:
            badges.append(ft.Icon(ft.Icons.VERIFIED, color=ft.Colors.BLUE, size=16))
        if bot.is_partnered:
            badges.append(
                ft.Icon(ft.Icons.WORKSPACE_PREMIUM, color=ft.Colors.PURPLE, size=16)
            )
        if bot.pinned:
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
                                    foreground_image_src=bot.avatar.value,
                                    background_image_src=DEFAULT_AVATAR_URL,
                                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                                    radius=25,
                                ),
                                ft.Column(
                                    [
                                        ft.Row(
                                            [
                                                ft.Text(
                                                    bot.name,
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
                                        ft.Row(
                                            [
                                                ft.Icon(
                                                    ft.Icons.CIRCLE,
                                                    size=10,
                                                    color=status_colors.get(
                                                        bot.status.value, ft.Colors.GREY
                                                    ),
                                                ),
                                                ft.Text(
                                                    bot.status.value.upper(),
                                                    size=12,
                                                    color=ft.Colors.GREY,
                                                ),
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
                            bot.description,
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
                                        ft.Text(
                                            str(bot.statistics.votes),
                                            size=14,
                                        ),
                                    ],
                                    spacing=5,
                                ),
                                ft.Row(
                                    [
                                        ft.Icon(ft.Icons.DNS, size=16),
                                        ft.Text(
                                            f"{bot.statistics.servers} 伺服器",
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
                                ft.OutlinedButton(
                                    "邀請",
                                    icon=ft.Icons.ADD,
                                    on_click=lambda _, b=bot: open_url(
                                        self.page, b.links.invite.value
                                    ),
                                ),
                                ft.OutlinedButton(
                                    "詳情",
                                    on_click=lambda _, b=bot: self._show_bot_detail(b),
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

    def _show_bot_detail(self, bot: Bot):
        """Show details"""
        self.page.run_task(self._navigate_to_bot_detail, bot)

    async def _navigate_to_bot_detail(self, bot: Bot):
        """Navigate to bot detail page"""
        await self.page.push_route(f"/bot/{bot.id}")

    async def _on_search(self):
        """Search event handler"""
        await self._load_bots()

    def _show_error(self, message: str):
        """Show error message"""
        self.page.show_dialog(
            ft.SnackBar(
                content=ft.Text(message),
                bgcolor=ft.Colors.ERROR,
            )
        )
