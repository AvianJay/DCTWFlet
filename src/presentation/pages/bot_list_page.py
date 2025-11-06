"""Bot list page - Bot list page

Display list with filtering and sorting support
"""

import flet as ft
import asyncio
from typing import Optional

from application.services import DiscoveryService, PreferenceService
from domain.discovery.value_objects import (
    FilterCriteria,
    SortOption,
    BotTag,
)
from domain.discovery.entities import Bot
from infrastructure.di import get_container


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

        # UI組件
        self.bot_list = ft.ListView(spacing=10, padding=20, expand=True)
        self.search_field = ft.TextField(
            label="搜尋Bot",
            prefix_icon=ft.Icons.SEARCH,
            on_submit=lambda _: self.page.run_task(self._on_search),
        )
        self.sort_dropdown = ft.Dropdown(
            label="排序",
            options=[
                ft.dropdown.Option("newest", "最新"),
                ft.dropdown.Option("votes", "投票數"),
                ft.dropdown.Option("servers", "伺服器數"),
                ft.dropdown.Option("bumped", "最近Bump"),
            ],
            value="newest",
            width=150,
            on_change=lambda _: self.page.run_task(self._load_bots),
        )
        self.progress = ft.ProgressBar(visible=False)

        self._current_filter: Optional[FilterCriteria] = None

    def build(self) -> ft.Control:
        """Build page UI"""
        self.page.run_task(self._load_bots)

        return ft.Column(
            [
                # Title bar
                ft.Container(
                    content=ft.Text("Discord Bots", size=24, weight=ft.FontWeight.BOLD),
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
                    padding=10,
                ),
                self.progress,
                ft.Container(self.bot_list, expand=True),
            ],
            expand=True,
        )

    async def _load_bots(self):
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

            bots = await self.discovery_service.list_bots(
                filter_criteria=self._current_filter,
                sort_option=sort_option,
            )

            # Render list
            self._render_bot_list(bots)

        except Exception as e:
            self._show_error(f"載入失敗: {str(e)}")

        finally:
            self.progress.visible = False
            self.page.update()

    def _render_bot_list(self, bots: list[Bot]):
        """Render list"""
        self.bot_list.controls.clear()

        if not bots:
            self.bot_list.controls.append(
                ft.Container(
                    content=ft.Text("沒有找到Bot", size=16, color=ft.Colors.GREY),
                    alignment=ft.alignment.center,
                    padding=50,
                )
            )
        else:
            for bot in bots:
                self.bot_list.controls.append(self._create_bot_card(bot))

        self.page.update()

    def _create_bot_card(self, bot: Bot) -> ft.Control:
        """Create card"""
        status_colors = {
            "online": ft.Colors.GREEN,
            "idle": ft.Colors.YELLOW,
            "dnd": ft.Colors.RED,
            "offline": ft.Colors.GREY,
        }

        tag_chips = [
            ft.Chip(
                label=ft.Text(tag.name),
                bgcolor=ft.Colors.BLUE_100,
            )
            for tag in bot.tags[:3]
        ]

        badges = []
        if bot.verified:
            badges.append(ft.Icon(ft.Icons.VERIFIED, color=ft.Colors.BLUE, size=16))
        if bot.is_partnered:
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
                                    foreground_image_src=bot.avatar.value,
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
                                    on_click=lambda _: self.page.launch_url(
                                        bot.links.invite.value
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
        self.page.go(f"/bot/{bot.id}")

    async def _on_search(self):
        """Search event handler"""
        await self._load_bots()

    def _show_error(self, message: str):
        """Show error message"""
        snack = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.Colors.ERROR,
        )
        self.page.snack_bar = snack
        snack.open = True
        self.page.update()
