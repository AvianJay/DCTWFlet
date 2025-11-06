"""Template list page - Template list page

Display list with filtering and sorting support
"""

import flet as ft
import asyncio
from typing import Optional

from application.services import DiscoveryService, PreferenceService
from domain.discovery.value_objects import (
    FilterCriteria,
    SortOption,
    TemplateTag,
)
from domain.discovery.entities import Template
from infrastructure.di import get_container


class TemplateListPage:
    """Template list page"""

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
        self.template_list = ft.ListView(spacing=10, padding=20, expand=True)
        self.search_field = ft.TextField(
            label="搜尋Template",
            prefix_icon=ft.Icons.SEARCH,
            on_submit=lambda _: self.page.run_task(self._on_search),
        )
        self.sort_dropdown = ft.Dropdown(
            label="排序",
            options=[
                ft.dropdown.Option("newest", "最新"),
                ft.dropdown.Option("votes", "投票數"),
                ft.dropdown.Option("bumped", "最近Bump"),
            ],
            value="newest",
            width=150,
            on_change=lambda _: self.page.run_task(self._load_templates),
        )

        self.progress = ft.ProgressBar(visible=False)
        self._current_filter: Optional[FilterCriteria] = None

    def build(self) -> ft.Control:
        """Build page UI"""
        self.page.run_task(self._load_templates)

        return ft.Column(
            [
                ft.Container(
                    content=ft.Text(
                        "Server Templates", size=24, weight=ft.FontWeight.BOLD
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
                    padding=10,
                ),
                self.progress,
                ft.Container(self.template_list, expand=True),
            ],
            expand=True,
        )

    async def _load_templates(self):
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
            templates = await self.discovery_service.list_templates(
                filter_criteria=self._current_filter,
                sort_option=sort_option,
            )

            self._render_template_list(templates)

        except Exception as e:
            print(f"Error loading templates: {e}")
            self._show_error(f"載入失敗: {str(e)}")

        finally:
            self.progress.visible = False
            self.page.update()

    def _render_template_list(self, templates: list[Template]):
        """Render list"""
        self.template_list.controls.clear()

        if not templates:
            self.template_list.controls.append(
                ft.Container(
                    content=ft.Text("沒有找到Template", size=16, color=ft.Colors.GREY),
                    alignment=ft.alignment.center,
                    padding=50,
                )
            )
        else:
            for template in templates:
                self.template_list.controls.append(self._create_template_card(template))

        self.page.update()

    def _create_template_card(self, template: Template) -> ft.Control:
        """Create card"""
        tag_chips = [
            ft.Chip(label=ft.Text(tag.name), bgcolor=ft.Colors.ORANGE_100)
            for tag in template.tags[:3]
        ]

        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.COPY_ALL,
                                    size=40,
                                    color=ft.Colors.PRIMARY,
                                ),
                                ft.Column(
                                    [
                                        ft.Text(
                                            template.name,
                                            size=18,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                            ],
                            spacing=15,
                        ),
                        ft.Text(
                            template.description,
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
                                            str(template.statistics.votes), size=14
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
                                    "使用模板",
                                    icon=ft.Icons.ADD_TO_PHOTOS,
                                    on_click=lambda _: self.page.launch_url(
                                        template.links.share_url
                                    ),
                                ),
                                ft.OutlinedButton(
                                    "詳情",
                                    on_click=lambda _, t=template: self._show_template_detail(
                                        t
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

    def _show_template_detail(self, template: Template):
        """Show details"""
        dialog = ft.AlertDialog(
            title=ft.Text(template.name),
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.COPY_ALL, size=80, color=ft.Colors.PRIMARY),
                    ft.Text(f"描述: {template.description}"),
                    ft.Text(f"投票: {template.statistics.votes}"),
                    ft.Text(f"標籤: {', '.join([tag.name for tag in template.tags])}"),
                    ft.Divider(),
                    ft.Text("介绍:", weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=ft.Text(template.introduce, size=12),
                        padding=10,
                        bgcolor=ft.Colors.SURFACE,
                        border_radius=5,
                    ),
                ],
                tight=True,
                scroll=ft.ScrollMode.AUTO,
                height=400,
            ),
            actions=[
                ft.TextButton("關閉", on_click=lambda _: self._close_dialog(dialog)),
                ft.ElevatedButton(
                    "使用模板",
                    on_click=lambda _: self.page.launch_url(template.links.share_url),
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
        await self._load_templates()

    def _show_error(self, message: str):
        """Show error message"""
        snack = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.Colors.ERROR,
        )
        self.page.snack_bar = snack
        snack.open = True
        self.page.update()
