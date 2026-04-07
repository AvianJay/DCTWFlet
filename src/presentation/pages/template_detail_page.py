
import asyncio
import flet as ft
from typing import Optional
from application.services import DiscoveryService
from domain.discovery.entities import Template
from domain.shared import EntityNotFoundException
from infrastructure.di import get_container
from presentation.tag_mappings import TEMPLATE_TAGS


class TemplateDetailPage:
    """Template detail page"""

    def __init__(self, page: ft.Page, template_id: str):
        self._content_container = None
        self.page = page
        self.template_id = template_id
        self.container = get_container()
        self.discovery_service: DiscoveryService = self.container.resolve(
            DiscoveryService
        )
        self._template: Optional[Template] = None

    def _get_tag_info(self, tag_name: str) -> tuple[str, str]:
        """Get tag display name and icon"""
        return TEMPLATE_TAGS.get(tag_name, (tag_name, ft.Icons.TAG))

    def build(self) -> ft.Control:
        """Build page UI"""
        self._content_container = ft.Container(
            expand=True,
            alignment=ft.Alignment(0, 0),
        )

        self._content_container.content = ft.Column(
            [
                ft.ProgressRing(),
                ft.Text("載入中...", size=16, text_align=ft.TextAlign.CENTER),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        )

        self.page.run_task(self._load_template_data)

        return self._content_container

    async def _load_template_data(self):
        """Load template data asynchronously"""
        try:
            template_id_int = int(self.template_id)
            self._template = await self.discovery_service.get_template_by_id(template_id_int)
            self._render_template_detail()

        except EntityNotFoundException:
            self._show_error(f"找不到此模板 (ID: {self.template_id})")
        except ValueError:
            self._show_error(f"無效的模板 ID: {self.template_id}")
        except Exception as e:
            self._show_error(f"載入失敗: {str(e)}")

    def _render_template_detail(self):
        """Render template detail UI"""
        if not self._template:
            return

        template = self._template

        detail_view = ft.Column(
            [
                ft.Container(height=40),
                # Name
                ft.Row(
                    [
                        ft.Text(
                            template.name,
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                # Description
                ft.Container(
                    content=ft.Text(
                        template.description,
                        size=16,
                        weight=ft.FontWeight.NORMAL,
                        text_align=ft.TextAlign.CENTER,
                        no_wrap=False,
                    ),
                    alignment=ft.Alignment(0, 0),
                    padding=ft.padding.symmetric(horizontal=20),
                ),
                # Action buttons
                ft.Container(
                    content=ft.Row(
                        [
                            ft.ElevatedButton(
                                icon=ft.Icons.ADD,
                                content=ft.Text("使用模板"),
                                on_click=lambda e: self.page.launch_url(template.links.share_url.value),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    alignment=ft.Alignment(0, 0),
                    padding=ft.padding.symmetric(vertical=20),
                ),
                # Tags
                self._create_tags_section(template),
                # Introduction (Markdown)
                ft.Container(
                    content=ft.Markdown(
                        template.introduce,
                        fit_content=False,
                        on_tap_link=lambda e: self.page.launch_url(e.data),
                    ),
                    padding=ft.padding.all(20),
                ),
                # DCTW page link
                ft.Row(
                    [
                        ft.ElevatedButton(
                            content=ft.Text("DCTW 模板頁面"),
                            icon=ft.Icons.OPEN_IN_NEW,
                            on_click=lambda e: self.page.launch_url(
                                f"https://dctw.xyz/templates/{template.id}"
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Container(height=20),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        self._content_container.content = detail_view
        self.page.update()

    def _create_tags_section(self, template: Template) -> ft.Control:
        """Create tags section"""
        tag_buttons = []
        for tag in template.tags:
            display_name, icon = self._get_tag_info(tag.name)
            tag_buttons.append(ft.ElevatedButton(content=ft.Text(display_name), icon=icon))

        if not tag_buttons:
            return ft.Container(height=0)

        return ft.Container(
            content=ft.Row(
                tag_buttons,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                wrap=True,
            ),
            alignment=ft.Alignment(0, 0),
            padding=ft.padding.symmetric(horizontal=20),
        )

    def _show_error(self, message: str):
        """Show error message"""
        error_view = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.ERROR_OUTLINE, size=64, color=ft.Colors.ERROR),
                    ft.Text(message, size=18, text_align=ft.TextAlign.CENTER),
                    ft.ElevatedButton(
                        content=ft.Text("返回"),
                        icon=ft.Icons.ARROW_BACK,
                        on_click=lambda e: asyncio.create_task(self.page.push_route("/")),
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=20,
            ),
            alignment=ft.Alignment(0, 0),
            expand=True,
            padding=ft.padding.all(40),
        )

        self._content_container.content = error_view
        self.page.update()
