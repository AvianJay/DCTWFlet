"""Template list page - Template list page

Display list with filtering and sorting support
"""

import logging
from typing import Optional

import flet as ft

from application.services import DiscoveryService, PreferenceService
from domain.discovery.value_objects import (
    FilterCriteria,
    SortOption,
    TemplateTag,
)
from domain.discovery.entities import Template
from infrastructure.api import ApiKeyMissingError, InvalidApiKeyError
from infrastructure.di import get_container
from presentation.components import TagFilterDialog, Toast
from presentation.tag_mappings import TEMPLATE_TAGS, TEMPLATE_TAG_FILTERS
from presentation.url_helper import open_url


logger = logging.getLogger(__name__)


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
        self.toast = Toast(self.page)

        # UI組件
        self.template_list = ft.ListView(
            spacing=10,
            padding=20,
            expand=True,
            scroll_interval=150,
            on_scroll=self._on_list_scroll,
        )
        self.search_field = ft.TextField(
            hint_text="搜尋模板...",
            prefix_icon=ft.Icons.SEARCH,
            on_submit=lambda _: self.page.run_task(self._on_search),
        )
        self.sort_dropdown = ft.Dropdown(
            label="排序",
            options=[
                ft.dropdown.Option("default", "預設排序"),
                ft.dropdown.Option("mostVotes", "最多投票"),
                ft.dropdown.Option("mostActive", "最高活躍度"),
            ],
            value="default",
            width=150,
            on_select=lambda _: self.page.run_task(self._load_templates),
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
        self._items: list[Template] = []
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
        self.page.run_task(self._load_templates)

        return ft.Column(
            [
                ft.AppBar(
                    title=ft.Text("DCTW 模板清單"),
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
                    padding=10,
                ),
                self.progress,
                ft.Container(self.template_list, expand=True),
            ],
            expand=True,
        )

    def _open_tag_filter(self, e=None) -> None:
        """Open the funnel dialog that lists every official tag."""
        TagFilterDialog(
            self.page,
            "篩選標籤",
            TEMPLATE_TAGS,
            TEMPLATE_TAG_FILTERS,
            self._selected_tags,
            self._apply_tags,
        ).show()

    def _apply_tags(self, selected: set[str]) -> None:
        """Apply the selection made inside the funnel dialog."""
        self._selected_tags = set(selected)
        self._sync_filter_icon()
        self.page.run_task(self._load_templates)

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
        self.page.run_task(self._load_templates)

    async def _refresh(self) -> None:
        """Clear the cached data and reload the list."""
        try:
            await self.discovery_service.clear_all_caches()
        except Exception:
            logger.exception("Failed to clear caches before refresh")

        await self._load_templates()
        self.toast.show("已重新整理")

    async def _load_templates(self):
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
                    TemplateTag(name)
                    for name in TEMPLATE_TAG_FILTERS
                    if name in self._selected_tags
                ],
                search_text=search_text,
                nsfw_enabled=nsfw_enabled,
            )

            sort_option = SortOption.from_string(self.sort_dropdown.value)
            templates = await self.discovery_service.list_templates(
                filter_criteria=self._current_filter,
                sort_option=sort_option,
            )

            # A newer load started while this one was in flight: drop the
            # stale result so the latest filter always wins.
            if seq != self._load_seq:
                return

            self._render_template_list(templates)

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
                print(f"Error loading templates: {e}")
                self._render_message(f"載入失敗: {str(e)}")

        finally:
            if seq == self._load_seq:
                self.progress.visible = False
                self.page.update()

    def _render_template_list(self, templates: list[Template]):
        """Render the first page of the list"""
        self._items = list(templates)
        self._rendered_count = 0
        self.template_list.controls.clear()

        if not self._items:
            self.template_list.controls.append(self._create_empty_state())
        else:
            self._append_template_page()

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
                "沒有符合條件的模板",
                size=16,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Text(
                "試著調整搜尋文字或改用其他標籤。"
                if active
                else "目前沒有可顯示的模板，請稍後再試。",
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
        await self._load_templates()

    def _append_template_page(self):
        """Append the next page of templates to the list"""
        end = min(self._rendered_count + self._page_size, len(self._items))
        for template in self._items[self._rendered_count : end]:
            self.template_list.controls.append(self._create_template_card(template))
        self._rendered_count = end

        if self._more_button in self.template_list.controls:
            self.template_list.controls.remove(self._more_button)
        if self._rendered_count < len(self._items):
            self.template_list.controls.append(self._more_button)

    def _show_more(self):
        """Show the next page of templates"""
        self._append_template_page()
        self.template_list.update()

    def _on_list_scroll(self, e: ft.OnScrollEvent):
        """Load the next page when the list is scrolled to the bottom"""
        if not self._items or self._rendered_count >= len(self._items):
            return

        max_extent = e.max_scroll_extent or 0
        if max_extent and e.pixels >= max_extent - 300:
            self._append_template_page()
            self.template_list.update()

    def _render_message(self, message: str):
        """Render a status message in place of the list"""
        self._items = []
        self._rendered_count = 0
        self.template_list.controls.clear()
        self.template_list.controls.append(
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

    def _create_template_card(self, template: Template) -> ft.Control:
        """Create card"""
        tag_chips = []
        for tag in template.tags[:3]:
            display_name, icon = TEMPLATE_TAGS.get(tag.name, (tag.name, ft.Icons.TAG))
            tag_chips.append(
                ft.Chip(
                    label=ft.Text(display_name),
                    leading=ft.Icon(icon, size=16),
                    bgcolor=ft.Colors.ORANGE_100,
                )
            )

        pinned_icon = []
        if template.pinned:
            pinned_icon.append(ft.Icon(ft.Icons.PUSH_PIN, color=ft.Colors.ORANGE, size=16))

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
                                        ft.Row(
                                            [
                                                ft.Text(
                                                    template.name,
                                                    size=18,
                                                    weight=ft.FontWeight.BOLD,
                                                    expand=True,
                                                    max_lines=1,
                                                    overflow=ft.TextOverflow.ELLIPSIS,
                                                ),
                                                *pinned_icon,
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
                                    on_click=lambda _, t=template: open_url(
                                        self.page, t.links.share_url
                                    ),
                                ),
                                ft.OutlinedButton(
                                    "詳情",
                                    on_click=lambda _, t=template: self._show_template_detail(t),
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
        self.page.run_task(self._navigate_to_template_detail, template)

    async def _navigate_to_template_detail(self, template: Template):
        """Navigate to template detail page"""
        await self.page.push_route(f"/template/{template.id}")

    def _show_template_dialog(self, template: Template):
        """Show details dialog"""
        dialog = ft.AlertDialog(
            title=ft.Text(template.name),
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.COPY_ALL, size=80, color=ft.Colors.PRIMARY),
                    ft.Text(f"描述: {template.description}"),
                    ft.Text(f"投票: {template.statistics.votes}"),
                    ft.Text(f"標籤: {', '.join([tag.name for tag in template.tags])}"),
                    ft.Divider(),
                    ft.Text("介紹:", weight=ft.FontWeight.BOLD),
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
                    on_click=lambda _, t=template: open_url(
                        self.page, t.links.share_url
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
        await self._load_templates()

    def _show_error(self, message: str):
        """Show error message"""
        self.page.show_dialog(
            ft.SnackBar(
                content=ft.Text(message),
                bgcolor=ft.Colors.ERROR,
            )
        )
